#!/usr/bin/env python3
"""PHEO Grow for coding agents.

This demo shows the attach point for Codex, Claude Code, Cursor, or any agent
that already produces a final answer/diff. PHEO does not run the coding agent.
It observes the proposed work at the release boundary, branches and scores it,
captures reviewer judgment, then applies that judgment memory on the next
similar case.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import pheo
from pheo import PendingReview


DEFAULT_PROJECT = "/tmp/pheo-code-agent-demo"
DEFAULT_EXPORT = "/tmp/pheo-code-agent-pack"
STORE_NAME = "code_agent_review"
REVIEW_POINT = "code_agent_output_review"


REPO_STANDARDS = """\
Code-agent release rules.

PHEO reviews final coding-agent work before it becomes accepted project memory,
merge guidance, or training data.

Must check:
- Require test evidence for parser, control-flow, data migration, auth, payment,
  or security-related changes.
- Require the final response to name modified files and verification performed.
- Escalate when the agent claims tests passed without showing a command or
  reliable test output.
- Keep the change scoped to the requested task.

Must not do:
- Do not accept code changes that modify behavior without relevant tests.
- Do not accept broad refactors hidden inside a small bug-fix request.
- Do not treat raw agent output as released project guidance until reviewed.
"""


CYCLE_1_CONTEXT = {
    "task": "Fix the markdown table parser so escaped pipes do not split columns.",
    "repo": "acme/docs-renderer",
    "files_changed": ["src/parser/table.py"],
    "risk": "parser_behavior",
    "test_evidence": "not provided",
}

CYCLE_1_OUTPUT = """\
Implemented the markdown table parser fix in src/parser/table.py.

Changed split_row() so it scans characters and ignores escaped pipes.
This should fix tables that contain `\\|` inside cells.

No tests were added because the change is small.
"""


CYCLE_2_CONTEXT = {
    "task": "Fix CSV import so quoted commas do not split fields.",
    "repo": "acme/data-tools",
    "files_changed": ["src/importer/csv_reader.py"],
    "risk": "parser_behavior",
    "test_evidence": "not provided",
}

CYCLE_2_OUTPUT = """\
Implemented quoted-comma handling in src/importer/csv_reader.py.

The parser now walks the line and ignores commas inside quotes.
I did not run tests because this is a straightforward parser change.
"""


def setup_pheo(project: Path) -> tuple[pheo.Pheo, dict[str, Any]]:
    store = pheo.open(project)
    workflow = store.create_store(
        STORE_NAME,
        business_area="software_development",
        goal="Review coding-agent outputs before accepting them as project guidance or merge-ready work.",
    )
    if not store.corpus(workflow["id"], active_only=True):
        store.source.add_text(
            "Repo review standards",
            REPO_STANDARDS,
            tags=["code_agent_review", "repo_rules"],
            store_id=workflow["id"],
        )
    methodology = store.methodology(workflow["id"])
    if not methodology:
        methodology = store.build_methodology(workflow["id"], actor="code_agent_demo")
    if methodology.get("status") != "approved":
        store.review_methodology(workflow["id"], actor="maintainer@example.com")
        store.approve_methodology(
            workflow["id"],
            actor="maintainer@example.com",
            note="Approved coding-agent review rules for the bundled demo.",
        )
    if not any(point["name"] == REVIEW_POINT for point in store.review_points(workflow["id"])):
        store.review_point.create(
            REVIEW_POINT,
            description="Review final coding-agent output before accepting it.",
            dimensions=["test evidence", "scope control", "risk handling", "release clarity"],
            store_id=workflow["id"],
        )
    return store, workflow


def best_memory_signal(outcome: pheo.GovernedOutcome) -> dict[str, Any]:
    best: dict[str, Any] = {}
    for candidate in outcome.candidates:
        signal = ((candidate.get("scores") or {}).get("judgment_memory") or {})
        if not signal.get("applied"):
            continue
        if not best or float(signal.get("similarity") or 0.0) > float(best.get("similarity") or 0.0):
            best = dict(signal)
    return best


def concise(text: str, limit: int = 180) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def print_ids(review: dict[str, Any]) -> None:
    decision = review.get("decision") or {}
    tuple_record = review.get("tuple") or {}
    receipt = review.get("receipt") or {}
    print(
        "Decision stored: "
        f"decision_id={decision.get('id')} "
        f"tuple_id={tuple_record.get('id')} "
        f"receipt_id={receipt.get('id')}"
    )


def run_demo(project: Path, out: Path, reset: bool = False) -> dict[str, Any]:
    if reset:
        shutil.rmtree(project, ignore_errors=True)
        shutil.rmtree(out, ignore_errors=True)

    store, workflow = setup_pheo(project)

    print("PHEO Grow: coding-agent attachment")
    print("Existing agent output is observed at the release boundary.")
    print()

    cycle_1 = store.observe.output(
        REVIEW_POINT,
        output=CYCLE_1_OUTPUT,
        context=CYCLE_1_CONTEXT,
        source={
            "connector": "coding_agent",
            "system": "codex_or_claude_or_cursor",
            "cycle_id": "cycle_1",
            "case_id": "parser-no-tests",
        },
    )
    print("Cycle 1 observed.")
    print(f"Raw agent output: {concise(cycle_1.observed_output)}")
    try:
        cycle_1.require_released()
    except PendingReview:
        print("Release blocked until human review.")

    review = store.review(
        cycle_1.id,
        selected_index=(cycle_1.recommended or {}).get("index", 0),
        action="reject",
        reason="Parser behavior changed without relevant tests or command output.",
        author_id="maintainer@example.com",
    )
    print_ids(review)
    print()

    memory = store.memory(workflow["id"])
    print(f"Compiled workflow memory entries: {len(memory.get('entries') or [])}")

    cycle_2 = store.observe.output(
        REVIEW_POINT,
        output=CYCLE_2_OUTPUT,
        context=CYCLE_2_CONTEXT,
        source={
            "connector": "coding_agent",
            "system": "codex_or_claude_or_cursor",
            "cycle_id": "cycle_2",
            "case_id": "parser-no-tests-cycle-2",
        },
        memory=memory,
    )
    signal = best_memory_signal(cycle_2)
    print("Cycle 2 observed with judgment memory applied.")
    if signal:
        print(
            "Memory signal: "
            f"{signal.get('suggestion')} "
            f"prior_action={signal.get('prior_action')} "
            f"prior_reason={signal.get('prior_reason')}"
        )
    else:
        print("Memory signal: none")

    pack = store.export_memory_pack(workflow["id"], out)
    artifacts = pack["artifacts"]
    print(
        "Export: "
        f"receipts={len(artifacts['release_receipts'])} "
        f"tuples={len(artifacts['preference_tuples'])} "
        f"judgment_memory={len((artifacts['judgment_memory'].get('entries') or []))}"
    )
    print(f"Export path: {out}")
    print(f"Open UI: pheo start --project {project} --store {workflow['id']}")
    return {
        "workflow": workflow,
        "cycle_1": cycle_1.to_dict(),
        "cycle_2": cycle_2.to_dict(),
        "memory_signal": signal,
        "pack": pack,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the PHEO code-agent attachment demo.")
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--out", default=DEFAULT_EXPORT)
    parser.add_argument("--reset", action="store_true", help="Delete prior demo project/export before running")
    args = parser.parse_args(argv)

    run_demo(Path(args.project), Path(args.out), reset=args.reset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
