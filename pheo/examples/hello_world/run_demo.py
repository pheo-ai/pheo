#!/usr/bin/env python3
"""Hello World: bring your own OpenAI-compatible endpoint to Pheo.

This demo keeps the endpoint call customer-owned:

    customer endpoint -> Pheo observe -> human judgment -> memory -> Cycle 2

Default storage is local SQLite plus a local memory-pack folder. If you pass
--customer-sink gs://bucket/prefix, the same memory pack is synced into GCS in
your Google Cloud tenancy using the installed gcloud CLI.

It uses stdlib urllib so there is no OpenAI, Anthropic, or LangChain dependency.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pheo
from pheo import PendingReview
from pheo.api import create_handler
from pheo.sinks import LocalFolderSink


DEFAULT_PROJECT = "/tmp/pheo-hello-world"
DEFAULT_EXPORT = "/tmp/pheo-hello-world-pack"
STORE_NAME = "finance_receipt_review"
REVIEW_POINT = "finance_receipt_review"


AP_POLICY = """\
Finance receipt review policy.

AI may draft short finance receipt exception notes, but a human reviewer must
approve, edit, reject, or escalate before any note is used for payment,
reconciliation, or audit follow-up.

Must check:
- Escalate when approval status is unclear or no approver is identified.
- Escalate when receipt, purchase order, or vendor support is missing.
- Flag possible duplicate receipts before saying the item is clear.
- Keep the final output factual and tied to the receipt context.

Must not do:
- Do not say a receipt can proceed when approval or support is unclear.
- Do not invent approvers, purchase-order matches, or payment clearance.
"""


def chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def endpoint_config() -> dict[str, str]:
    return {
        "base_url": os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "https://openrouter.ai/api/v1"),
        "api_key": os.environ.get("OPENAI_COMPATIBLE_API_KEY", ""),
        "model": os.environ.get("OPENAI_COMPATIBLE_MODEL", "openai/gpt-4o-mini"),
    }


def safe_endpoint(base_url: str) -> str:
    return base_url.split("?")[0].rstrip("/")


def message_content(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        return "\n".join(part for part in parts if part)
    return str(content)


def call_openai_compatible_endpoint(prompt: str, context: dict[str, Any]) -> str:
    config = endpoint_config()
    if not config["api_key"]:
        raise RuntimeError(
            "Set OPENAI_COMPATIBLE_API_KEY before running the endpoint demo. "
            "For OpenRouter, set OPENAI_COMPATIBLE_BASE_URL=https://openrouter.ai/api/v1."
        )
    if not config["model"]:
        raise RuntimeError("Set OPENAI_COMPATIBLE_MODEL before running the endpoint demo.")

    payload = {
        "model": config["model"],
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You draft short finance receipt exception notes. Be factual. "
                    "Use plain finance receipt review language. "
                    "Do not approve payment."
                ),
            },
            {
                "role": "user",
                "content": prompt + "\n\nContext:\n" + json.dumps(context, indent=2, sort_keys=True),
            },
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        chat_completions_url(config["base_url"]),
        data=data,
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pheo-ai/pheo",
            "X-OpenRouter-Title": "Pheo Hello World",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Endpoint returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Endpoint request failed: {exc}") from exc

    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("Endpoint response had no choices.")
    output = message_content((choices[0].get("message") or {})).strip()
    if not output:
        raise RuntimeError("Endpoint response had an empty message.")
    return output


def setup_pheo(project: Path, approve_methodology: bool = True) -> tuple[pheo.Pheo, dict[str, Any]]:
    store = pheo.open(project)
    workflow = store.create_store(
        STORE_NAME,
        business_area="finance",
        goal="Review finance receipt exception notes before payment-related action is released.",
    )
    if not store.corpus(workflow["id"], active_only=True):
        store.source.add_text(
            "Demo finance receipt review policy",
            AP_POLICY,
            tags=["demo_finance_receipt_policy"],
            store_id=workflow["id"],
        )
    methodology = store.methodology(workflow["id"])
    if not methodology:
        methodology = store.build_methodology(workflow["id"], actor="hello_world")
    if approve_methodology and methodology.get("status") != "approved":
        store.review_methodology(workflow["id"], actor="controller@example.com")
        store.approve_methodology(
            workflow["id"],
            actor="controller@example.com",
            note="Approved finance receipt review rules for Hello World endpoint demo.",
        )
    if not any(point["name"] == REVIEW_POINT for point in store.review_points(workflow["id"])):
        store.review_point.create(
            REVIEW_POINT,
            description="Review finance receipt exception notes before release.",
            dimensions=["evidence support", "approval clarity", "exception risk", "next step"],
            store_id=workflow["id"],
        )
    return store, workflow


def observe_customer_endpoint(
    store: pheo.Pheo,
    context: dict[str, Any],
    cycle_id: str,
    memory: dict[str, Any] | None = None,
) -> pheo.GovernedOutcome:
    prompt = "Draft one short finance receipt exception note. Do not approve payment."
    raw_output = call_openai_compatible_endpoint(prompt, context)
    config = endpoint_config()
    return store.observe.output(
        REVIEW_POINT,
        output=raw_output,
        context=context,
        source={
            "connector": "customer_openai_compatible_endpoint",
            "endpoint": safe_endpoint(config["base_url"]),
            "model": config["model"],
            "cycle_id": cycle_id,
            "case_id": context.get("invoice_id", ""),
        },
        memory=memory,
    )


def best_memory_signal(outcome: pheo.GovernedOutcome) -> dict[str, Any]:
    best: dict[str, Any] = {}
    for candidate in outcome.candidates:
        signal = ((candidate.get("scores") or {}).get("judgment_memory") or {})
        if not signal.get("applied"):
            continue
        if not best or float(signal.get("similarity") or 0) > float(best.get("similarity") or 0):
            best = dict(signal)
    return best


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


def result_for_decision(store: pheo.Pheo, workflow_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    tuple_record = next(
        (item for item in store.store.list_preference_tuples(workflow_id) if item.get("decision_id") == decision.get("id")),
        {},
    )
    receipt = store.store.get_release_receipt_for_decision(decision.get("id") or "") or {}
    return {"decision": decision, "tuple": tuple_record, "receipt": receipt}


def scripted_review(store: pheo.Pheo, outcome: pheo.GovernedOutcome) -> dict[str, Any]:
    return store.review(
        outcome.id,
        selected_index=outcome.recommended["index"],
        action="escalate",
        corrected_output="",
        reason="Missing PO match and unclear approval.",
        author_id="controller@example.com",
    )


def launch_persistent_ui(project: Path, workflow: dict[str, Any], port: int, path: str = "", open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), create_handler(project))
    target_path = path or f"/?store={workflow['id']}"
    url = f"http://127.0.0.1:{port}{target_path}"
    print("Starting local PHEO apprentice.")
    print(f"Workflow: {workflow['name']}")
    print(f"Local UI: {url}")
    print("Today: finance receipt review. Use PHEO Go to inspect or replace the source policy, PHEO Grow to review an output, and Decisions to inspect memory.")
    print("The server stays open until you press Ctrl-C.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local Pheo UI.")
    finally:
        server.server_close()


def cli_review(store: pheo.Pheo, outcome: pheo.GovernedOutcome) -> dict[str, Any]:
    print("CLI review required.")
    print("Candidates:")
    for candidate in outcome.candidates:
        scores = candidate.get("scores") or {}
        marker = "recommended" if candidate.get("recommended") else ""
        output = " ".join(str(candidate.get("output") or "").split())
        print(f"[{candidate.get('index')}] {marker} score={scores.get('mean_score')}")
        print(f"    {output[:300]}")

    recommended_index = outcome.recommended["index"]
    selected_text = input(f"Selected candidate [{recommended_index}]: ").strip()
    selected_index = int(selected_text) if selected_text else int(recommended_index)
    action = input("Action approve/edit/reject/escalate [escalate]: ").strip().lower() or "escalate"
    if action not in {"approve", "edit", "reject", "escalate"}:
        raise ValueError("Action must be approve, edit, reject, or escalate")
    reason = input("Reason: ").strip()
    if not reason:
        raise ValueError("Reason is required")
    corrected_output = ""
    if action == "edit":
        corrected_output = input("Corrected output: ").strip()
        if not corrected_output:
            raise ValueError("Corrected output is required for edit")
    return store.review(
        outcome.id,
        selected_index=selected_index,
        action=action,
        corrected_output=corrected_output,
        reason=reason,
        author_id="cli-reviewer@example.com",
    )


def sync_customer_sink(pack: dict[str, Any], local_export_dir: Path, customer_sink: str) -> str:
    """Mirror the exported memory pack into a customer-owned destination.

    Local folders work with no cloud credentials. A gs:// URI uses the user's
    active gcloud credentials and copies the same exported files into GCS.
    """
    if not customer_sink:
        return ""
    if customer_sink.startswith("gs://"):
        subprocess.run(
            ["gcloud", "storage", "rsync", "--recursive", str(local_export_dir), customer_sink],
            check=True,
            text=True,
        )
        return f"GCS sink mirror: {customer_sink}"
    if customer_sink.startswith(("s3://", "postgres://", "postgresql://", "http://", "https://")):
        raise NotImplementedError(
            f"{customer_sink} is not built into this Hello World yet. "
            "Use a local folder or gs:// bucket/prefix, or replace sync_customer_sink(...) "
            "with your own tenancy writer."
        )
    LocalFolderSink(customer_sink).write_pack(pack)
    return f"Customer-owned sink mirror: {customer_sink}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Pheo Hello World with your OpenAI-compatible endpoint.")
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--out", default=DEFAULT_EXPORT)
    parser.add_argument(
        "--customer-sink",
        default="",
        help="Optional customer-owned folder or gs://bucket/prefix to mirror the exported memory pack.",
    )
    parser.add_argument(
        "--review-mode",
        choices=["ui", "manual", "cli", "scripted"],
        default="ui",
        help="ui starts the local browser app; cli reviews in terminal; scripted captures a demo judgment for CI.",
    )
    parser.add_argument("--port", type=int, default=8787, help="Local UI port")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser in UI mode")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Start fresh by deleting the local Hello World project and export folder before running.",
    )
    args = parser.parse_args(argv)

    project = Path(args.project)
    export_dir = Path(args.out)
    if args.reset:
        print("Resetting local Hello World project and export folder.")
        shutil.rmtree(project, ignore_errors=True)
        shutil.rmtree(export_dir, ignore_errors=True)
        if args.customer_sink and not args.customer_sink.startswith(("gs://", "s3://", "postgres://", "postgresql://", "http://", "https://")):
            shutil.rmtree(Path(args.customer_sink), ignore_errors=True)

    if args.review_mode in {"ui", "manual"}:
        store, workflow = setup_pheo(project, approve_methodology=False)
        target_path = "/?hello=1"
        print("Opening the Hello World apprentice.")
        print("Use PHEO Go to inspect the demo finance receipt policy or replace it with your own notes.")
        print("Then approve rules, use PHEO Grow to review one output, and open Decisions to inspect memory.")
        launch_persistent_ui(project, workflow, args.port, path=target_path, open_browser=not args.no_browser)
        return 0

    store, workflow = setup_pheo(project, approve_methodology=True)

    cycle_1_context = {
        "invoice_id": "FIN-1007",
        "vendor": "Northstar Office Supplies",
        "amount": "18420.00",
        "approval_status": "Unclear - no approver identified",
        "support": "Purchase-order match missing",
    }
    outcome_1 = observe_customer_endpoint(store, cycle_1_context, cycle_id="cycle_1")
    print("Cycle 1 raw endpoint output was observed by Pheo.")
    print(f"Review URL: {outcome_1.review_url}")
    try:
        outcome_1.require_released()
    except PendingReview:
        print("Release blocked until human review.")

    if args.review_mode == "cli":
        review = cli_review(store, outcome_1)
    else:
        review = scripted_review(store, outcome_1)
    print_ids(review)

    memory = store.memory(workflow["id"])

    cycle_2_context = {
        "invoice_id": "FIN-1104",
        "vendor": "Northstar Office Supplies",
        "amount": "19280.00",
        "approval_status": "Approver not identified",
        "support": "Change-order evidence missing",
    }
    outcome_2 = observe_customer_endpoint(store, cycle_2_context, cycle_id="cycle_2", memory=memory)
    print("Cycle 2 observed with judgment memory applied.")
    signal = best_memory_signal(outcome_2)
    print(
        "Memory signal: "
        f"{signal.get('suggestion') or 'none'} "
        f"prior_action={signal.get('prior_action') or 'none'} "
        f"prior_reason={signal.get('prior_reason') or 'none'}"
    )

    pack = store.export_memory_pack(workflow["id"], export_dir, organic_only=True)
    artifacts = pack["artifacts"]
    print(
        "Decisions export: "
        f"receipts={len(artifacts['release_receipts'])} "
        f"tuples={len(artifacts['preference_tuples'])} "
        f"judgment_memory={len(artifacts['judgment_memory'].get('entries', []))}"
    )
    print(f"Export path: {export_dir}")
    if args.customer_sink:
        print(sync_customer_sink(pack, export_dir, args.customer_sink))
    print(f"Open UI: pheo start --project {project.resolve()} --store {workflow['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
