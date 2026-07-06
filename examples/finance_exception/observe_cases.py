#!/usr/bin/env python3
"""Seed AP invoice exception review packets from invoice_cases.jsonl."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pheo
from pheo.projects import resolve_project


def draft_note(case: dict) -> str:
    focus = case.get("expected_review_focus") or "Review evidence and approval status."
    return (
        f"Invoice {case['invoice_id']} from {case['vendor']} for {case.get('amount', 'the stated amount')} "
        f"requires AP exception review. Approval status: {case.get('approval_status', 'not supplied')}. "
        f"Review focus: {focus} Human review is required before any payment-related action."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe synthetic AP invoice cases into a Pheo review queue.")
    parser.add_argument("--project", default="", help="Project path or registered project name. Defaults to the active Pheo project.")
    parser.add_argument("--store", default="ap_invoice_exception_review")
    parser.add_argument("--review-point", default="ap_exception_review")
    parser.add_argument("--file", default=str(Path(__file__).with_name("invoice_cases.jsonl")))
    args = parser.parse_args()

    project = resolve_project(args.project or None)
    store = pheo.open(project)
    workflow = store.get_workflow(args.store)
    methodology = store.methodology(workflow["id"]) or {}
    if methodology.get("status") != "approved":
        raise SystemExit(f"Approve review rules first: pheo methodology review --workflow {args.store} --format human")

    packets = []
    for line in Path(args.file).read_text().splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        outcome = store.observe.output(
            args.review_point,
            output=draft_note(case),
            context=case,
            source={"connector": "finance_exception_example", "case_id": case["invoice_id"]},
        )
        packets.append((case["invoice_id"], outcome.id, outcome.review_url))

    for invoice_id, packet_id, review_url in packets:
        print(f"{invoice_id}\t{packet_id}\t{review_url}")
    print(f"\nObserved {len(packets)} cases. Open the queue: pheo start --store {args.store}")
    print("Memory export gets useful after reviewers capture approve/edit/reject/escalate decisions with reasons.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
