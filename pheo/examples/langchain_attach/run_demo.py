"""Run the bundled LangChain attach demo.

This module is packaged with Pheo so beta testers can run:

    pheo demo langchain-attach --reset

without cloning the repository.
"""

from __future__ import annotations

import argparse
import json
import shutil
import warnings
from importlib.resources import files
from pathlib import Path
from typing import Any

import pheo
from pheo import PendingReview
from pheo.integrations.langchain import with_pheo_review


def load_langchain():
    warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL", category=Warning)
    try:
        from langchain_core.runnables import RunnableLambda
    except ImportError as exc:
        raise SystemExit('Install the optional LangChain dependency first:\n  python3.13 -m pip install "pheo[langchain]"') from exc
    return RunnableLambda


def finance_asset(name: str):
    return files("pheo.examples.finance_exception").joinpath(name)


def load_cases() -> list[dict[str, Any]]:
    path = finance_asset("invoice_cases.jsonl")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def draft_ap_exception(case: dict[str, Any]) -> dict[str, Any]:
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


def concise(value: Any, limit: int = 150) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def decision_memory_record(case: dict[str, Any], outcome, review_result: dict[str, Any]) -> dict[str, Any]:
    decision = review_result.get("decision") or {}
    tuple_record = review_result.get("tuple") or {}
    receipt = review_result.get("receipt") or {}
    methodology = receipt.get("methodology_snapshot") or {}
    source_snapshot = receipt.get("source_snapshot") or []
    reason = decision.get("reason") or ""
    action = decision.get("action") or ""
    return {
        "context": {
            "invoice_id": case.get("invoice_id"),
            "vendor": case.get("vendor"),
            "approval_status": case.get("approval_status"),
        },
        "model_proposed": outcome.observed_output,
        "human_action": action,
        "corrected_or_released_output": decision.get("chosen_output") or "",
        "reason": reason,
        "learned_preference": f"When a similar case appears, prefer `{action}` because: {reason}",
        "methodology_hash": methodology.get("methodology_hash") or "",
        "source_snapshot_count": len(source_snapshot),
        "stored_as": {
            "decision_id": decision.get("id"),
            "tuple_id": tuple_record.get("id"),
            "receipt_id": receipt.get("id"),
            "memory_entry_id": receipt.get("memory_entry_id"),
        },
    }


def memory_application_record(outcomes: list[Any]) -> dict[str, Any]:
    best: dict[str, Any] = {}
    for outcome in outcomes:
        run = outcome.get("run", {}) or {}
        context = ((run.get("task") or {}).get("context") or {})
        for candidate in outcome.candidates:
            memory_scores = ((candidate.get("scores") or {}).get("judgment_memory") or {})
            if memory_scores.get("applied"):
                record = {
                    "context": {
                        "invoice_id": context.get("invoice_id"),
                        "vendor": context.get("vendor"),
                        "approval_status": context.get("approval_status"),
                    },
                    "candidate": candidate.get("output") or "",
                    "nearest_memory": memory_scores.get("nearest_entry_id") or "",
                    "prior_action": memory_scores.get("prior_action") or "",
                    "prior_reason": memory_scores.get("prior_reason") or "",
                    "suggestion": memory_scores.get("suggestion") or "",
                    "similarity": memory_scores.get("similarity"),
                    "explanation": memory_scores.get("explanation") or "",
                    "recommendation_changed": bool(memory_scores.get("recommendation_changed_by_memory")),
                }

                def priority(item: dict[str, Any]) -> tuple[int, float]:
                    status = str((item.get("context") or {}).get("approval_status") or "").lower()
                    reason = str(item.get("prior_reason") or "").lower()
                    suggestion = str(item.get("suggestion") or "")
                    score = 0
                    if suggestion == "similar_prior_escalate" or item.get("prior_action") == "escalate":
                        score += 100
                    if item.get("recommendation_changed"):
                        score += 80
                    if any(term in status for term in ("unclear", "not identified", "blank", "pending")):
                        score += 50
                    if any(term in reason for term in ("unclear", "missing", "pending", "approval")):
                        score += 20
                    return score, float(item.get("similarity") or 0.0)

                if not best or priority(record) > priority(best):
                    best = record
    return best


def setup_pheo(project: Path) -> tuple[pheo.Pheo, dict[str, Any]]:
    store = pheo.open(project)
    workflow = store.create_store(
        "ap_invoice_exception_review",
        business_area="finance",
        goal="Prepare AP invoice exception summaries for human review before any payment-related action is approved.",
    )
    if not store.corpus(workflow["id"], active_only=True):
        store.source.add_text("AP exception policy", finance_asset("ap-policy.md").read_text(encoding="utf-8"), store_id=workflow["id"])
    methodology = store.methodology(workflow["id"])
    if not methodology:
        methodology = store.build_methodology(workflow["id"], actor="demo")
    if methodology.get("status") != "approved":
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
    apprentice_memory_records = []
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
        review_result = store.review(
            outcome.id,
            selected_index=outcome.recommended["index"],
            action=action,
            corrected_output=corrected_output(case) if action in {"edit", "escalate"} else "",
            reason=case.get("expected_review_focus") or "Reviewed AP exception support and approval.",
            author_id="controller@example.com",
        )
        apprentice_memory_records.append(decision_memory_record(case, outcome, review_result))
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
    memory_application = memory_application_record(cycle_2_outcomes)

    return {
        "blocked_before_review": blocked,
        "released_after_review": released,
        "apprentice_memory_record": apprentice_memory_records[0] if apprentice_memory_records else {},
        "cycle_2_memory_application": memory_application,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LangChain output with and without Pheo release governance.")
    parser.add_argument("--project", default="/tmp/pheo-langchain-attach-demo")
    parser.add_argument("--out", default="/tmp/pheo-langchain-attach-pack")
    parser.add_argument("--reset", action="store_true", help="Delete prior demo project/export before running.")
    parser.add_argument("--cycle-size", type=int, default=6)
    args = parser.parse_args(argv)

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
    if not cycle_1 or not cycle_2:
        raise SystemExit("Need at least two demo cycles. Reduce --cycle-size or add cases.")

    raw = run_without_pheo(chain, cycle_1[:3])
    store, workflow = setup_pheo(project)
    governed = run_with_pheo(store, workflow, chain, cycle_1, cycle_2, out)

    print("Without Pheo:")
    print(f"  LangChain produced {len(raw)} raw outputs.")
    print("  No methodology gate, release receipt, reviewer reason, memory pack, or next-cycle judgment memory.")
    print(f"  Example raw output: {raw[0]['raw_output']}")

    print("\nWith Pheo attached after LangChain:")
    print("  Integration: reviewed_chain = with_pheo_review(existing_chain, store=store, review_point=...)")
    print(f"  Review UI: pheo start --project {governed['project_path']} --store {workflow['name']}")
    print(f"  Blocked before review: {len(governed['blocked_before_review'])} outputs")
    print(f"  Released after review: {len(governed['released_after_review'])} outputs")
    print(f"  Release receipts: {governed['receipts']}")
    print(f"  Preference tuples: {governed['preference_tuples']}")
    print(f"  SFT rows: {governed['sft_rows']}")
    print(f"  DPO rows: {governed['dpo_rows']}")
    print(f"  Judgment memory entries: {governed['memory_entries']}")
    print(f"  Cycle 2 cases with prior judgment match: {governed['cycle_2_memory_match_cases']}")
    print(f"  Cycle 2 candidate-level matches: {governed['cycle_2_candidate_matches']}")

    memory_record = governed.get("apprentice_memory_record") or {}
    if memory_record:
        print("\nApprentice memory record created:")
        print(f"  Context: {json.dumps(memory_record['context'], sort_keys=True)}")
        print(f"  Model proposed: {concise(memory_record['model_proposed'])}")
        print(f"  Human action: {memory_record['human_action']}")
        print(f"  Corrected/released output: {concise(memory_record['corrected_or_released_output'])}")
        print(f"  Reason: {memory_record['reason']}")
        print(f"  Learned preference: {memory_record['learned_preference']}")
        print(f"  Methodology hash: {memory_record['methodology_hash']}")
        print(f"  Source snapshots: {memory_record['source_snapshot_count']}")
        print(f"  Stored as: {json.dumps(memory_record['stored_as'], sort_keys=True)}")

    applied = governed.get("cycle_2_memory_application") or {}
    if applied:
        print("\nExample memory signal on Cycle 2:")
        print(f"  Context: {json.dumps(applied['context'], sort_keys=True)}")
        print(f"  Candidate: {concise(applied['candidate'])}")
        print(f"  Matched memory: {applied['nearest_memory']} similarity={applied['similarity']}")
        print(f"  Prior action/reason: {applied['prior_action']} - {applied['prior_reason']}")
        print(f"  Suggestion: {applied['suggestion']}")
        print(f"  Explanation: {applied['explanation']}")
        print("  Release rule: human review is still required.")
        print(f"  Recommendation changed by memory: {applied['recommendation_changed']}")

    print(f"  Export path: {governed['export_path']}")
    print(f"  First Cycle 2 review URL: {governed['cycle_2_review_urls'][0] if governed['cycle_2_review_urls'] else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
