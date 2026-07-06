#!/usr/bin/env python3
"""Run the governed preference-factory proof for AP invoice review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pheo


def load_cases() -> list[dict]:
    return [json.loads(line) for line in (ROOT / "invoice_cases.jsonl").read_text().splitlines() if line.strip()]


def draft_note(case: dict) -> str:
    return (
        f"Invoice {case['invoice_id']} from {case['vendor']} for {case.get('amount', 'the stated amount')} "
        f"requires AP exception review. Approval status: {case.get('approval_status', 'not supplied')}. "
        f"Review focus: {case.get('expected_review_focus') or 'Check support and approval.'} "
        "Human review is required before any payment-related action."
    )


def reviewed_output(case: dict) -> str:
    action = case.get("suggested_action")
    focus = case.get("expected_review_focus") or "review support and approval"
    if action == "approve":
        return f"Invoice {case['invoice_id']} can proceed after review because support appears complete. Verify: {focus}."
    if action == "edit":
        return f"Invoice {case['invoice_id']} should be held until AP resolves: {focus}."
    if action == "escalate":
        return f"Invoice {case['invoice_id']} should be escalated before any payment-related action because {focus}."
    return f"Invoice {case['invoice_id']} should remain in AP review because {focus}."


def review_action(case: dict) -> str:
    return {"approve": "approve", "edit": "edit", "escalate": "escalate"}.get(case.get("suggested_action"), "edit")


def ensure_setup(store: pheo.Pheo):
    workflow = store.create_store(
        "ap_invoice_exception_review",
        business_area="finance",
        goal="Prepare AP invoice exception summaries for human review before any payment-related action is approved.",
    )
    if not store.corpus(workflow["id"], active_only=True):
        store.source.add(ROOT / "ap-policy.md", store_id=workflow["id"])
    methodology = store.methodology(workflow["id"])
    if not methodology:
        store.build_methodology(workflow["id"])
        store.review_methodology(workflow["id"], actor="demo_reviewer")
        methodology = store.approve_methodology(workflow["id"], actor="demo_reviewer", note="Approved for preference-factory demo.")
    elif methodology.get("status") != "approved":
        store.review_methodology(workflow["id"], actor="demo_reviewer")
        methodology = store.approve_methodology(workflow["id"], actor="demo_reviewer", note="Approved for preference-factory demo.")
    points = store.review_points(workflow["id"])
    if not any(point["name"] == "ap_exception_review" for point in points):
        store.review_point.create(
            "ap_exception_review",
            description="Review AP invoice exception summaries before clearing or payment-related action.",
            dimensions=["evidence support", "approval clarity", "exception risk", "next step"],
            store_id=workflow["id"],
        )
    return workflow


def run_cycle(store: pheo.Pheo, cases: list[dict], cycle_id: str, memory: dict | None = None, review: bool = False):
    outcomes = []
    for case in cases:
        outcome = store.observe.output(
            "ap_exception_review",
            output=draft_note(case),
            context=case,
            source={"connector": "finance_exception_example", "case_id": case["invoice_id"], "cycle_id": cycle_id},
            memory=memory,
        )
        outcomes.append(outcome)
        if review:
            action = review_action(case)
            store.review(
                outcome.id,
                selected_index=outcome.recommended["index"],
                action=action,
                corrected_output=reviewed_output(case) if action in {"edit", "escalate"} else "",
                reason=case.get("expected_review_focus") or "Reviewed AP support and approval.",
                author_id="demo_reviewer",
            )
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove Pheo preference factory with seeded AP invoice review cycles.")
    parser.add_argument("--project", default=".pheo-preference-factory-demo")
    parser.add_argument("--out", default="output/preference_factory")
    parser.add_argument("--cycle-size", type=int, default=12)
    args = parser.parse_args()

    store = pheo.open(args.project)
    workflow = ensure_setup(store)
    cases = load_cases()
    cycle_1 = cases[: args.cycle_size]
    cycle_2 = cases[args.cycle_size : args.cycle_size * 2]

    before = run_cycle(store, cycle_1, "cycle_1", review=True)
    memory = store.memory(workflow["id"])
    after = run_cycle(store, cycle_2, "cycle_2", memory=memory, review=False)
    pack = store.export_memory_pack(workflow["id"], args.out, organic_only=True)
    diff = store.cycle_diff(workflow["id"], before="cycle_1", after="cycle_2")

    print("Cycle 1:")
    print("  reviewer mode: seeded demo reviewer decisions; replace with real human review in production")
    human_decisions = [item for item in store.store.list_decisions(workflow["id"]) if str(item.get("provenance") or "").startswith("human")]
    print(f"  decisions: {len(human_decisions)}")
    print(f"  preference tuples: {len(pack['artifacts']['preference_tuples'])}")
    print(f"  preference pairs: {len(pack['artifacts']['preference_pairs'])}")
    print(f"  released examples: {len(pack['artifacts']['review_examples'])}")
    print("\nCycle 2:")
    print("  memory applied: yes")
    print(f"  cases with prior judgment match: {diff.get('after_stats', {}).get('memory_match_cases', 0)}")
    print(f"  candidate-level prior judgment matches: {diff.get('after_stats', {}).get('memory_matches', 0)}")
    print(f"  recommendations changed by memory: {diff.get('after_stats', {}).get('recommendations_changed_by_memory', 0)}")
    print(f"  pending review delta: {diff.get('pending_review_delta', 0)}")
    print("\nExport:")
    print(f"  {args.out}/release_receipts.jsonl")
    print(f"  {args.out}/judgment_memory.json")
    print(f"  {args.out}/training_manifest.json")
    print(f"  {args.out}/cycle_diff.json")
    print(f"\nObserved Cycle 1 packets: {len(before)}")
    print(f"Observed Cycle 2 packets: {len(after)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
