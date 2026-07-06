#!/usr/bin/env python3
"""Show how Pheo attaches after a LangChain/LangGraph-style workflow.

The demo is local and API-key free:

1. Run the same LangChain runnable without Pheo.
2. Attach Pheo after the runnable output.
3. Show that raw output cannot become business output until reviewed.
4. Capture reviewer decisions with reasons.
5. Export receipts, preference data, and judgment memory.
6. Apply that memory on a second cycle.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import warnings
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parents[1]
FINANCE_ROOT = REPO_ROOT / "examples" / "finance_exception"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pheo
from pheo import PendingReview
from pheo.integrations.langchain import with_pheo_review


def load_langchain():
    warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL", category=Warning)
    try:
        from langchain_core.runnables import RunnableLambda
    except ImportError as exc:
        raise SystemExit(
            "Install the optional demo dependency first:\n"
            "  python3.13 -m pip install -r examples/langchain_attach/requirements.txt"
        ) from exc
    return RunnableLambda


def load_cases() -> list[dict[str, Any]]:
    path = FINANCE_ROOT / "invoice_cases.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def draft_ap_exception(case: dict[str, Any]) -> dict[str, Any]:
    """Pretend this is the final LangChain/LangGraph node output."""
    focus = str(case.get("expected_review_focus") or "support and approval").rstrip(".")
    final_answer = (
        f"Invoice {case['invoice_id']} from {case['vendor']} for {case.get('amount', 'the stated amount')} "
        f"can proceed after AP exception review. Approval status: {case.get('approval_status', 'not supplied')}. "
        f"Reviewer should check: {focus}."
    )
    return {
        "final_answer": final_answer,
        "run_id": f"langchain-{case['invoice_id']}",
        "state": {"invoice": case, "final_answer": final_answer},
    }


def corrected_output(case: dict[str, Any]) -> str:
    focus = case.get("expected_review_focus") or "support and approval"
    action = case.get("suggested_action")
    if action == "approve":
        return f"Invoice {case['invoice_id']} can proceed after review because support appears complete. Verify: {focus}."
    if action == "escalate":
        return f"Invoice {case['invoice_id']} should be escalated before any payment-related action because {focus}."
    return f"Invoice {case['invoice_id']} should remain on hold until AP resolves: {focus}."


def review_action(case: dict[str, Any]) -> str:
    return {"approve": "approve", "edit": "edit", "escalate": "escalate"}.get(case.get("suggested_action"), "edit")


def setup_pheo(project: Path) -> tuple[pheo.Pheo, dict[str, Any]]:
    store = pheo.open(project)
    workflow = store.create_store(
        "ap_invoice_exception_review",
        business_area="finance",
        goal="Prepare AP invoice exception summaries for human review before any payment-related action is approved.",
    )
    if not store.corpus(workflow["id"], active_only=True):
        store.source.add(FINANCE_ROOT / "ap-policy.md", store_id=workflow["id"])
    if not store.methodology(workflow["id"]):
        store.build_methodology(workflow["id"], actor="demo")
    if store.methodology(workflow["id"]).get("status") != "approved":
        store.review_methodology(workflow["id"], actor="controller@example.com")
        store.approve_methodology(
            workflow["id"],
            actor="controller@example.com",
            note="Approved AP exception review methodology for LangChain attach demo.",
        )
    if not any(point["name"] == "ap_exception_review" for point in store.review_points(workflow["id"])):
        store.review_point.create(
            "ap_exception_review",
            description="Review AP invoice exception summaries before clearing or payment-related action.",
            dimensions=["evidence support", "approval clarity", "exception risk", "next step"],
            store_id=workflow["id"],
        )
    return store, workflow


def run_without_pheo(chain, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw = []
    for case in cases:
        result = chain.invoke(case)
        raw.append({"invoice_id": case["invoice_id"], "raw_output": result["final_answer"]})
    return raw


def run_with_pheo(
    store: pheo.Pheo,
    workflow: dict[str, Any],
    chain,
    cycle_1: list[dict[str, Any]],
    cycle_2: list[dict[str, Any]],
    out: Path,
) -> dict[str, Any]:
    released = []
    blocked = []
    reviewed_cycle_1 = with_pheo_review(
        chain,
        store=store,
        review_point="ap_exception_review",
        output_key="final_answer",
        cycle_id="cycle_1",
    )
    for case in cycle_1:
        reviewed = reviewed_cycle_1.invoke(case)
        outcome = reviewed.outcome
        try:
            reviewed.require_released()
        except PendingReview:
            blocked.append(case["invoice_id"])
        action = review_action(case)
        store.review(
            outcome.id,
            selected_index=outcome.recommended["index"],
            action=action,
            corrected_output=corrected_output(case) if action in {"edit", "escalate"} else "",
            reason=case.get("expected_review_focus") or "Reviewed AP exception support and approval.",
            author_id="controller@example.com",
        )
        if action in {"approve", "edit"}:
            released.append({"invoice_id": case["invoice_id"], "released_output": outcome.require_released()})

    memory = store.memory(workflow["id"])
    reviewed_cycle_2 = with_pheo_review(
        chain,
        store=store,
        review_point="ap_exception_review",
        output_key="final_answer",
        cycle_id="cycle_2",
        memory=memory,
    )
    cycle_2_outcomes = [reviewed_cycle_2.invoke(case).outcome for case in cycle_2]
    pack = store.export_memory_pack(workflow["id"], out, organic_only=True)
    diff = store.cycle_diff(workflow["id"], before="cycle_1", after="cycle_2")

    return {
        "blocked_before_review": blocked,
        "released_after_review": released,
        "cycle_2_review_urls": [outcome.review_url for outcome in cycle_2_outcomes],
        "memory_entries": len(memory.get("entries") or []),
        "receipts": len(pack["artifacts"]["release_receipts"]),
        "preference_tuples": len(pack["artifacts"]["preference_tuples"]),
        "sft_rows": len(pack["artifacts"]["sft_jsonl"]),
        "dpo_rows": len(pack["artifacts"]["dpo_jsonl"]),
        "cycle_2_memory_match_cases": diff.get("after_stats", {}).get("memory_match_cases", 0),
        "cycle_2_candidate_matches": diff.get("after_stats", {}).get("memory_matches", 0),
        "export_path": str(out),
        "project_path": str(store.store.db_path.parent),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LangChain output with and without Pheo release governance.")
    parser.add_argument("--project", default="/tmp/pheo-langchain-attach-demo")
    parser.add_argument("--out", default="/tmp/pheo-langchain-attach-pack")
    parser.add_argument("--reset", action="store_true", help="Delete prior demo project/export before running.")
    parser.add_argument("--cycle-size", type=int, default=6)
    args = parser.parse_args()

    project = Path(args.project)
    out = Path(args.out)
    if args.reset:
        shutil.rmtree(project, ignore_errors=True)
        shutil.rmtree(out, ignore_errors=True)

    RunnableLambda = load_langchain()
    chain = RunnableLambda(draft_ap_exception)
    cases = load_cases()
    cycle_1 = cases[: args.cycle_size]
    cycle_2 = cases[args.cycle_size : args.cycle_size * 2]

    raw = run_without_pheo(chain, cycle_1[:3])
    store, workflow = setup_pheo(project)
    governed = run_with_pheo(store, workflow, chain, cycle_1, cycle_2, out)

    print("Without Pheo:")
    print(f"  LangChain produced {len(raw)} raw outputs.")
    print("  No methodology gate, release receipt, reviewer reason, memory pack, or next-cycle judgment memory.")
    print(f"  Example raw output: {raw[0]['raw_output']}")

    print("\nWith Pheo attached after LangChain:")
    print("  Integration: `reviewed_chain = with_pheo_review(existing_chain, store=store, review_point=...)`")
    print(f"  Review UI: run `pheo start --project {governed['project_path']} --store {workflow['name']}`")
    print(f"  Blocked before review: {len(governed['blocked_before_review'])} outputs")
    print(f"  Released after review: {len(governed['released_after_review'])} outputs")
    print(f"  Release receipts: {governed['receipts']}")
    print(f"  Preference tuples: {governed['preference_tuples']}")
    print(f"  SFT rows: {governed['sft_rows']}")
    print(f"  DPO rows: {governed['dpo_rows']}")
    print(f"  Judgment memory entries: {governed['memory_entries']}")
    print(f"  Cycle 2 cases with prior judgment match: {governed['cycle_2_memory_match_cases']}")
    print(f"  Cycle 2 candidate-level matches: {governed['cycle_2_candidate_matches']}")
    print(f"  Export path: {governed['export_path']}")
    print(f"  First Cycle 2 review URL: {governed['cycle_2_review_urls'][0] if governed['cycle_2_review_urls'] else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
