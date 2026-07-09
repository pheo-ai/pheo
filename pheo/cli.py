import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote

from pheo import Pheo, File, Folder, Text
from pheo.connectors import JsonlConnector, TraceConnector
from pheo.projects import create_project, current_project, list_projects, register_project, remove_project, resolve_project, set_current_project
from pheo.storage.sqlite import project_db_path


def main(argv=None):
    argv = _normalize_argv(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="pheo",
        description="PHEO local apprentice for reviewed AI workflows. Run `pheo` to open the local UI.",
    )
    parser.add_argument("--project", default=None, help="Project directory or sqlite:/// path")
    parser.add_argument("--cli", action="store_true", help="Show the terminal guide for PHEO Go, Grow, Govern, and Do")
    subparsers = parser.add_subparsers(dest="command")

    project_parser = subparsers.add_parser("project", help="Local project registry commands")
    project_sub = project_parser.add_subparsers(dest="project_command", required=True)
    project_create = project_sub.add_parser("create", help="Create and register a local Pheo project")
    project_create.add_argument("name")
    project_create.add_argument("--path", default="", help="Project directory or sqlite:/// path. Defaults to PHEO_HOME/projects/<name>.")
    project_create.add_argument("--no-use", action="store_true", help="Register without making it current")
    project_list = project_sub.add_parser("list", help="List registered local projects")
    project_current = project_sub.add_parser("current", help="Show the current local project")
    project_use = project_sub.add_parser("use", help="Set the current local project")
    project_use.add_argument("ref", help="Project name, path, or sqlite:/// database")
    project_remove = project_sub.add_parser("remove", help="Remove a project from the registry without deleting its database")
    project_remove.add_argument("ref")

    init = subparsers.add_parser("init", help="Initialize a local PHEO project")
    init.add_argument("--project", dest="command_project", help="Project directory or sqlite:/// path")

    mcp = subparsers.add_parser("mcp", help="Run Pheo MCP stdio server")
    mcp.add_argument("--project", dest="command_project", help="Project directory or sqlite:/// path")

    demo = subparsers.add_parser(
        "demo",
        help="Run packaged Pheo demos. Defaults to Hello World.",
        description="Run a packaged PHEO demo. Omit the demo name to run Hello World.",
    )
    demo.add_argument("--project", default="/tmp/pheo-hello-world")
    demo.add_argument("--out", default="/tmp/pheo-hello-world-pack")
    demo.add_argument("--customer-sink", default="")
    demo.add_argument("--review-mode", choices=["ui", "manual", "cli", "scripted"], default="ui")
    demo.add_argument("--port", type=int, default=8787)
    demo.add_argument("--no-browser", action="store_true")
    demo.add_argument("--reset", action="store_true", help="Delete prior demo project/export before running")
    demo_sub = demo.add_subparsers(dest="demo_command", metavar="[demo]")
    langchain_demo = demo_sub.add_parser("langchain-attach", help="Run the bundled LangChain attach demo")
    langchain_demo.add_argument("--project", default="/tmp/pheo-langchain-attach-demo")
    langchain_demo.add_argument("--out", default="/tmp/pheo-langchain-attach-pack")
    langchain_demo.add_argument("--reset", action="store_true", help="Delete prior demo project/export before running")
    langchain_demo.add_argument("--cycle-size", type=int, default=6)
    hello_world_demo = demo_sub.add_parser("hello-world", help="Run the bring-your-own-endpoint Hello World demo")
    hello_world_demo.add_argument("--project", default="/tmp/pheo-hello-world")
    hello_world_demo.add_argument("--out", default="/tmp/pheo-hello-world-pack")
    hello_world_demo.add_argument("--customer-sink", default="")
    hello_world_demo.add_argument("--review-mode", choices=["ui", "manual", "cli", "scripted"], default="ui")
    hello_world_demo.add_argument("--port", type=int, default=8787)
    hello_world_demo.add_argument("--no-browser", action="store_true")
    hello_world_demo.add_argument("--reset", action="store_true", help="Delete prior demo project/export before running")

    for command_name in ("start", "studio"):
        start = subparsers.add_parser(command_name, help="Start the local PHEO apprentice")
        start.add_argument("--project", dest="command_project", help="Project directory or sqlite:/// path")
        start.add_argument("--port", type=int, default=8787)
        start.add_argument("--host", default="127.0.0.1")
        start.add_argument("--store", default="", help="Open the local UI directly into a workflow")
        start.add_argument("--no-browser", action="store_true")

    store = subparsers.add_parser("store", help="Workflow commands")
    store_sub = store.add_subparsers(dest="store_command", required=True)
    store_create = store_sub.add_parser("create", help="Create or retrieve a workflow")
    store_create.add_argument("--name", required=True)
    store_create.add_argument("--business-area", default="")
    store_create.add_argument("--description", default="")
    store_create.add_argument("--goal", default="", help="Review goal or protocol the methodology should be built against")
    store_list = store_sub.add_parser("list", help="List workflows")

    source = subparsers.add_parser("source", help="Source material commands")
    source_sub = source.add_subparsers(dest="source_command", required=True)
    source_add = source_sub.add_parser("add", help="Add source material used for review methodology")
    source_add.add_argument("--store", required=True)
    source_add.add_argument("sources", nargs="+")
    source_add.add_argument("--tag", action="append", default=[])
    source_list = source_sub.add_parser("list", help="List source material")
    source_list.add_argument("--store", required=True)
    source_deactivate = source_sub.add_parser("deactivate", help="Deactivate source material without deleting memory")
    source_deactivate.add_argument("source_id")

    connection = subparsers.add_parser("connection", help="Review connection commands")
    connection_sub = connection.add_subparsers(dest="connection_command", required=True)
    connection_add = connection_sub.add_parser("add", help="Add a connection that feeds review points")
    connection_add.add_argument("--store", required=True)
    connection_add.add_argument("--name", required=True)
    connection_add.add_argument(
        "--type",
        required=True,
        choices=[
            "openai-compatible-endpoint",
            "langchain",
            "langsmith",
            "llamaindex",
            "vllm",
            "huggingface",
            "huggingface-endpoint",
            "weave",
            "noveum",
            "opentelemetry",
            "mcp",
            "python-decorator",
            "rest-ingest",
            "trace-import",
            "jsonl-batch",
        ],
    )
    connection_add.add_argument("--endpoint-url", default="")
    connection_add.add_argument("--model", default="")
    connection_add.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    connection_add.add_argument("--config", default="", help="Additional JSON config")
    connection_list = connection_sub.add_parser("list", help="List output connections")
    connection_list.add_argument("--store", required=True)

    review_point = subparsers.add_parser("review-point", help="Review point commands")
    review_point_sub = review_point.add_subparsers(dest="review_point_command", required=True)
    review_point_add = review_point_sub.add_parser("add", help="Define a business review point")
    review_point_add.add_argument("--store", required=True)
    review_point_add.add_argument("--name", required=True)
    review_point_add.add_argument("--description", default="")
    review_point_add.add_argument("--dimension", action="append", default=[])
    review_point_add.add_argument("--human-review", default="required", choices=["required", "optional"])
    review_point_add.add_argument("--branching", default="kernel", choices=["kernel", "none"], help=argparse.SUPPRESS)
    review_point_add.add_argument("--connection", default="")
    review_point_list = review_point_sub.add_parser("list", help="List review points")
    review_point_list.add_argument("--store", required=True)
    review_point_email = review_point_sub.add_parser("email", help="Attach a customer SMTP email notification channel")
    review_point_email.add_argument("--review-point", required=True)
    review_point_email.add_argument("--to", action="append", required=True)
    review_point_email.add_argument("--subject", default="")
    review_point_email.add_argument("--instructions", default="")
    review_point_webhook = review_point_sub.add_parser("webhook", help="Attach a generic webhook notification channel")
    review_point_webhook.add_argument("--review-point", required=True)
    review_point_webhook.add_argument("--url", default="")
    review_point_webhook.add_argument("--url-env", default="")
    review_point_webhook.add_argument("--header", action="append", default=[], help="HTTP header as 'Name: value'")
    review_point_webhook.add_argument("--headers-env", default="", help="Env var containing a JSON object of headers")
    review_point_webhook.add_argument("--instructions", default="")
    review_point_slack = review_point_sub.add_parser("slack", help="Attach a Slack incoming-webhook notification channel")
    review_point_slack.add_argument("--review-point", required=True)
    review_point_slack.add_argument("--webhook-url", default="")
    review_point_slack.add_argument("--webhook-url-env", default="PHEO_SLACK_WEBHOOK_URL")
    review_point_slack.add_argument("--instructions", default="")
    review_point_telegram = review_point_sub.add_parser("telegram", help="Attach a Telegram bot notification channel")
    review_point_telegram.add_argument("--review-point", required=True)
    review_point_telegram.add_argument("--chat-id", default="")
    review_point_telegram.add_argument("--chat-id-env", default="")
    review_point_telegram.add_argument("--bot-token", default="")
    review_point_telegram.add_argument("--bot-token-env", default="PHEO_TELEGRAM_BOT_TOKEN")
    review_point_telegram.add_argument("--instructions", default="")

    observe = subparsers.add_parser("observe", help="Observe AI/agent outputs at review points")
    observe_sub = observe.add_subparsers(dest="observe_command", required=True)
    observe_output = observe_sub.add_parser("output", help="Observe one output")
    observe_output.add_argument("--review-point", required=True)
    observe_output.add_argument("--output", default="")
    observe_output.add_argument("--file", default="")
    observe_output.add_argument("--context", default="", help="Plain text note, JSON object, or path to JSON")
    observe_output.add_argument("--source", default="", help="Plain text source name, JSON object, or path to JSON")
    observe_output.add_argument("--use-memory", action="store_true", help="Apply existing judgment memory while scoring this output")
    observe_endpoint = observe_sub.add_parser("endpoint", help="Call an OpenAI-compatible endpoint and observe its output")
    observe_endpoint.add_argument("--review-point", required=True)
    observe_endpoint.add_argument("--connection", default="")
    observe_endpoint.add_argument("--endpoint-url", default="")
    observe_endpoint.add_argument("--model", default="")
    observe_endpoint.add_argument("--api-key", default="")
    observe_endpoint.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    observe_endpoint.add_argument("--prompt", default="")
    observe_endpoint.add_argument("--system", default="")
    observe_endpoint.add_argument("--messages", default="", help="JSON file or JSON string with chat messages")
    observe_endpoint.add_argument("--temperature", type=float, default=0.7)
    observe_endpoint.add_argument("--context", default="", help="Plain text note, JSON object, or path to JSON")
    observe_endpoint.add_argument("--source", default="", help="Plain text source name, JSON object, or path to JSON")
    observe_traces = observe_sub.add_parser("traces", help="Observe outputs from trace export")
    observe_traces.add_argument("--review-point", required=True)
    observe_traces.add_argument(
        "--source-type",
        required=True,
        choices=[
            "generic",
            "langchain",
            "langsmith",
            "llamaindex",
            "weave",
            "wandb-weave",
            "noveum",
            "opentelemetry",
            "otel",
            "vllm",
            "huggingface",
            "huggingface-endpoint",
        ],
    )
    observe_traces.add_argument("--file", required=True)
    observe_batch = observe_sub.add_parser("batch", help="Observe outputs from JSONL logs")
    observe_batch.add_argument("--review-point", required=True)
    observe_batch.add_argument("--file", required=True)
    observe_batch.add_argument("--use-memory", action="store_true", help="Apply existing judgment memory while scoring this batch")

    review = subparsers.add_parser("review", help="Capture human review decisions")
    review_sub = review.add_subparsers(dest="review_command", required=True)
    review_capture = review_sub.add_parser("capture", help="Capture a review decision for a packet")
    review_capture.add_argument("--packet", required=True)
    review_capture.add_argument("--selected", type=int, required=True)
    review_capture.add_argument("--action", default="approve", choices=["approve", "reject", "edit", "correct", "escalate"])
    review_capture.add_argument("--reason", default="")
    review_capture.add_argument("--corrected-output", default="")
    review_capture.add_argument("--author", default="")

    workflow = subparsers.add_parser("workflow", help="Workflow commands")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_create = workflow_sub.add_parser("create", help="Create or retrieve a workflow")
    workflow_create.add_argument("--name", required=True)
    workflow_create.add_argument("--domain", default="")
    workflow_create.add_argument("--objective", default="")
    workflow_create.add_argument("--skill", default="")

    corpus = subparsers.add_parser("corpus", help="Corpus commands")
    corpus_sub = corpus.add_subparsers(dest="corpus_command", required=True)
    corpus_add = corpus_sub.add_parser("add", help="Attach corpus data to a workflow")
    corpus_add.add_argument("--workflow", required=True)
    corpus_add.add_argument("sources", nargs="+")
    corpus_add.add_argument("--tag", action="append", default=[])
    corpus_list = corpus_sub.add_parser("list", help="List corpus data")
    corpus_list.add_argument("--workflow", required=True)
    corpus_delete = corpus_sub.add_parser("deactivate", help="Deactivate corpus data without deleting decisions")
    corpus_delete.add_argument("corpus_id")

    methodology = subparsers.add_parser("methodology", help="Review-rule commands")
    methodology_sub = methodology.add_subparsers(dest="methodology_command", required=True)
    for command_name in ("build", "draft"):
        methodology_build = methodology_sub.add_parser(command_name, help="Draft review rules from active corpus")
        methodology_build.add_argument("--workflow", required=True)
        methodology_build.add_argument("--author", default="pheo")
        methodology_build.add_argument("--note", default="Draft review rules generated from source material.")
    methodology_review = methodology_sub.add_parser("review", help="Show draft review rules and approval status")
    methodology_review.add_argument("--workflow", required=True)
    methodology_review.add_argument("--format", choices=["json", "human"], default="json")
    methodology_review.add_argument("--author", default="human")
    methodology_review.add_argument("--note", default="Methodology draft reviewed.")
    methodology_update = methodology_sub.add_parser("update", help="Edit draft review rules before approval")
    methodology_update.add_argument("--workflow", required=True)
    methodology_update.add_argument("--summary", default="")
    methodology_update.add_argument("--rule", action="append", default=[])
    methodology_update.add_argument("--avoid", action="append", default=[])
    methodology_update.add_argument("--author", default="human")
    methodology_update.add_argument("--note", default="Review rules edited by reviewer.")
    methodology_reject = methodology_sub.add_parser("reject", help="Reject draft review rules")
    methodology_reject.add_argument("--workflow", required=True)
    methodology_reject.add_argument("--author", default="human")
    methodology_reject.add_argument("--note", default="")
    methodology_approve = methodology_sub.add_parser("approve", help="Approve review rules and create initial preference pairs")
    methodology_approve.add_argument("--workflow", required=True)
    methodology_approve.add_argument("--author", default="human")
    methodology_approve.add_argument("--note", default="")
    methodology_approve.add_argument("--no-require-human-review", action="store_true", help="Allow approval without a review/update event")

    run = subparsers.add_parser("run", help="Run commands")
    run_sub = run.add_subparsers(dest="run_command", required=True)
    run_create = run_sub.add_parser("create", help="Create a workflow review from task and output JSON")
    run_create.add_argument("--workflow", required=True)
    run_create.add_argument("--task", required=True)
    run_create.add_argument("--candidates", required=True)
    run_create.add_argument("--mode", default="external")
    run_score = run_sub.add_parser("score", help="Score a run")
    run_score.add_argument("run_id")
    run_score.add_argument("--use-memory", action="store_true")

    memory = subparsers.add_parser("memory", help="Judgment memory commands")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)
    memory_show = memory_sub.add_parser("show", help="Show compiled judgment memory")
    memory_show.add_argument("--workflow", "--store", dest="workflow", required=True)

    receipts = subparsers.add_parser("receipts", help="Release receipt commands")
    receipts_sub = receipts.add_subparsers(dest="receipts_command", required=True)
    receipts_backfill = receipts_sub.add_parser("backfill", help="Backfill receipts for legacy reviewed packets")
    receipts_backfill.add_argument("--workflow", "--store", dest="workflow", required=True)

    cycle_diff = subparsers.add_parser("cycle-diff", help="Compare two labeled workflow cycles")
    cycle_diff.add_argument("--workflow", "--store", dest="workflow", required=True)
    cycle_diff.add_argument("--before", default="cycle_1")
    cycle_diff.add_argument("--after", default="cycle_2")

    decision = subparsers.add_parser("decision", help="Decision commands")
    decision_sub = decision.add_subparsers(dest="decision_command", required=True)
    decision_capture = decision_sub.add_parser("capture", help="Capture a human decision")
    decision_capture.add_argument("--run", required=True)
    decision_capture.add_argument("--selected", type=int, required=True)
    decision_capture.add_argument("--action", default="approve", choices=["approve", "reject", "edit", "correct"])
    decision_capture.add_argument("--reason", default="")
    decision_capture.add_argument("--corrected-output", default="")

    export = subparsers.add_parser("export", help="Export commands")
    export_sub = export.add_subparsers(dest="export_command", required=True)
    export_pack = export_sub.add_parser("pack", help="Export full workflow memory pack")
    export_pack.add_argument("--workflow", "--store", dest="workflow", required=True)
    export_pack.add_argument("--out", required=True)
    export_pack.add_argument("--organic-only", action="store_true", help="Export only human review/correction memory")
    export_graph = export_sub.add_parser("graph", help="Export generated workflow graph")
    export_graph.add_argument("--workflow", "--store", dest="workflow", required=True)
    export_graph.add_argument("--out", required=True)
    export_preferences = export_sub.add_parser("preferences", help="Print preference-pair JSONL")
    export_preferences.add_argument("--workflow", required=True)
    export_preferences.add_argument("--organic-only", action="store_true")
    export_examples = export_sub.add_parser("examples", help="Print review-example JSONL")
    export_examples.add_argument("--workflow", required=True)
    export_examples.add_argument("--organic-only", action="store_true")
    export_sft = export_sub.add_parser("sft", help="Print released-example chat JSONL")
    export_sft.add_argument("--workflow", required=True)
    export_sft.add_argument("--organic-only", action="store_true")
    export_dpo = export_sub.add_parser("dpo", help="Print chosen/rejected preference JSONL")
    export_dpo.add_argument("--workflow", required=True)
    export_dpo.add_argument("--organic-only", action="store_true")
    export_checks = export_sub.add_parser("checks", help="Print check-case JSONL")
    export_checks.add_argument("--workflow", required=True)
    export_checks.add_argument("--organic-only", action="store_true")

    if not _has_subcommand(argv):
        argv = [*argv, "start"]
    args = parser.parse_args(argv)
    if args.cli:
        print(_cli_mode_text())
        return 0
    if args.command == "project":
        if args.project_command == "create":
            record = create_project(args.name, path=args.path or None, make_current=not args.no_use)
            Pheo.open(record["path"])
            print(json.dumps({"project": record, "database": record["database"], "next": "pheo store create --name <store_name>"}, indent=2))
            return 0
        if args.project_command == "list":
            print(json.dumps({"projects": list_projects()}, indent=2))
            return 0
        if args.project_command == "current":
            print(json.dumps({"project": current_project()}, indent=2))
            return 0
        if args.project_command == "use":
            record = set_current_project(args.ref)
            Pheo.open(record["path"])
            print(json.dumps({"project": record, "next": "pheo store list"}, indent=2))
            return 0
        removed = remove_project(args.ref)
        print(json.dumps({"removed": removed, "projects": list_projects()}, indent=2))
        return 0

    if args.command == "demo":
        if not args.demo_command:
            from pheo.examples.hello_world.run_demo import main as run_hello_world_demo

            demo_args = [
                "--project",
                args.project,
                "--out",
                args.out,
                "--review-mode",
                args.review_mode,
                "--port",
                str(args.port),
            ]
            if args.customer_sink:
                demo_args.extend(["--customer-sink", args.customer_sink])
            if args.no_browser:
                demo_args.append("--no-browser")
            if args.reset:
                demo_args.append("--reset")
            return run_hello_world_demo(demo_args)
        if args.demo_command == "langchain-attach":
            from pheo.examples.langchain_attach.run_demo import main as run_langchain_attach_demo

            demo_args = [
                "--project",
                args.project,
                "--out",
                args.out,
                "--cycle-size",
                str(args.cycle_size),
            ]
            if args.reset:
                demo_args.append("--reset")
            return run_langchain_attach_demo(demo_args)
        if args.demo_command == "hello-world":
            from pheo.examples.hello_world.run_demo import main as run_hello_world_demo

            demo_args = [
                "--project",
                args.project,
                "--out",
                args.out,
                "--review-mode",
                args.review_mode,
                "--port",
                str(args.port),
            ]
            if args.customer_sink:
                demo_args.extend(["--customer-sink", args.customer_sink])
            if args.no_browser:
                demo_args.append("--no-browser")
            if args.reset:
                demo_args.append("--reset")
            return run_hello_world_demo(demo_args)

    explicit_project = getattr(args, "command_project", None) or args.project
    project = explicit_project or ("./.pheo" if args.command == "init" else resolve_project())
    factory = Pheo.open(project)

    if args.command == "init":
        record = register_project(project, make_current=True)
        print(
            json.dumps(
                {
                    "status": "initialized",
                    "project": record,
                    "database": str(project_db_path(project)),
                    "next": "pheo start",
                },
                indent=2,
            )
        )
        return 0
    if args.command == "mcp":
        from pheo.mcp import run

        run(project)
        return 0
    if args.command in {"start", "studio"}:
        from pheo.api import run_server

        record = register_project(project, make_current=True)
        url = f"http://{args.host}:{args.port}"
        if args.store:
            url = f"{url}/?store={quote(args.store)}"
        if not args.no_browser:
            webbrowser.open(url)
        print(json.dumps({"project": record, "url": url}, indent=2))
        run_server(project=project, host=args.host, port=args.port)
        return 0
    if args.command == "store":
        if args.store_command == "create":
            store_record = factory.create_store(
                args.name,
                business_area=args.business_area,
                description=args.description,
                goal=args.goal,
            )
            print(json.dumps({"store": store_record}, indent=2))
            return 0
        print(json.dumps({"stores": factory.workflows()}, indent=2))
        return 0
    if args.command == "source":
        if args.source_command == "add":
            factory.use_store(args.store)
            items = [_source(source, args.tag) for source in args.sources]
            print(json.dumps({"sources": factory.source.add(items)}, indent=2))
            return 0
        if args.source_command == "list":
            factory.use_store(args.store)
            print(json.dumps({"sources": factory.source.list()}, indent=2))
            return 0
        print(json.dumps({"source": factory.source.deactivate(args.source_id)}, indent=2))
        return 0
    if args.command == "connection":
        if args.connection_command == "add":
            factory.use_store(args.store)
            config = _optional_json(args.config)
            connector_type = args.type.replace("-", "_")
            if args.type == "openai-compatible-endpoint":
                config = {
                    **config,
                    "endpoint_url": args.endpoint_url,
                    "model": args.model,
                    "api_key_env": args.api_key_env,
                }
            connection_record = factory.connection.add(args.name, connector_type, config)
            print(json.dumps({"connection": connection_record}, indent=2))
            return 0
        factory.use_store(args.store)
        print(json.dumps({"connections": factory.connection.list()}, indent=2))
        return 0
    if args.command == "review-point":
        if args.review_point_command == "add":
            factory.use_store(args.store)
            point = factory.review_point.create(
                args.name,
                description=args.description,
                dimensions=args.dimension,
                human_review=args.human_review,
                branching=args.branching,
                connection=args.connection or None,
            )
            print(json.dumps({"review_point": point}, indent=2))
            return 0
        if args.review_point_command == "list":
            factory.use_store(args.store)
            print(json.dumps({"review_points": factory.review_point.list()}, indent=2))
            return 0
        if args.review_point_command == "email":
            point = factory.review_channel.email(args.review_point, args.to, subject=args.subject, instructions=args.instructions)
        elif args.review_point_command == "webhook":
            point = factory.review_channel.webhook(
                args.review_point,
                url=args.url,
                url_env=args.url_env,
                headers=_headers(args.header),
                headers_env=args.headers_env,
                instructions=args.instructions,
            )
        elif args.review_point_command == "slack":
            point = factory.review_channel.slack(
                args.review_point,
                webhook_url=args.webhook_url,
                webhook_url_env=args.webhook_url_env,
                instructions=args.instructions,
            )
        else:
            point = factory.review_channel.telegram(
                args.review_point,
                chat_id=args.chat_id,
                chat_id_env=args.chat_id_env,
                bot_token=args.bot_token,
                bot_token_env=args.bot_token_env,
                instructions=args.instructions,
            )
        print(json.dumps({"review_point": point}, indent=2))
        return 0
    if args.command == "observe":
        if args.observe_command == "output":
            output = args.output or (Path(args.file).read_text(encoding="utf-8") if args.file else "")
            if not output:
                raise SystemExit("--output or --file is required")
            context = _optional_json(args.context, fallback_key="note")
            source = _optional_json(args.source, fallback_key="name")
            memory = factory.memory(factory.get_review_point(args.review_point)["workflow_id"]) if args.use_memory else None
            packet = factory.observe(args.review_point, output=output, context=context, source=source, memory=memory)
            print(json.dumps(_payload(packet), indent=2))
            return 0
        if args.observe_command == "endpoint":
            context = _optional_json(args.context, fallback_key="note")
            source = _optional_json(args.source, fallback_key="name")
            messages = _messages(args.messages, args.system, args.prompt, context)
            packet = factory.observe_endpoint(
                args.review_point,
                connection=args.connection or None,
                endpoint_url=args.endpoint_url,
                model=args.model,
                api_key=args.api_key,
                api_key_env=args.api_key_env,
                messages=messages,
                temperature=args.temperature,
                context=context,
                source=source,
            )
            print(json.dumps(packet, indent=2))
            return 0
        if args.observe_command == "traces":
            payload = Path(args.file).read_text(encoding="utf-8")
            connector = TraceConnector(args.source_type, payload, args.review_point)
            packets = [
                factory.observe(item.review_point, item.output, context=item.context, source=item.source, candidates=item.candidates, mode=f"trace:{args.source_type}")
                for item in connector.observations()
            ]
            print(json.dumps({"packets": [_payload(packet) for packet in packets]}, indent=2))
            return 0
        connector = JsonlConnector(args.file, args.review_point)
        point = factory.get_review_point(args.review_point)
        memory = factory.memory(point["workflow_id"]) if args.use_memory else None
        packets = [
            factory.observe(item.review_point, item.output, context=item.context, source=item.source, candidates=item.candidates, memory=memory)
            for item in connector.observations()
        ]
        print(json.dumps({"packets": [_payload(packet) for packet in packets]}, indent=2))
        return 0
    if args.command == "review":
        result = factory.review(
            args.packet,
            args.selected,
            action=args.action,
            reason=args.reason,
            corrected_output=args.corrected_output,
            author_id=args.author,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "workflow":
        workflow = factory.workflow(args.name, args.domain, args.objective, args.skill)
        print(json.dumps(workflow, indent=2))
        return 0
    if args.command == "corpus":
        if args.corpus_command == "add":
            workflow = _workflow(factory, args.workflow)
            items = [_source(source, args.tag) for source in args.sources]
            print(json.dumps({"items": factory.attach_corpus(workflow["id"], items)}, indent=2))
            return 0
        if args.corpus_command == "list":
            workflow = _workflow(factory, args.workflow)
            print(json.dumps({"items": factory.corpus(workflow["id"])}, indent=2))
            return 0
        print(json.dumps({"item": factory.deactivate_corpus(args.corpus_id)}, indent=2))
        return 0
    if args.command == "methodology":
        workflow = _workflow(factory, args.workflow)
        if args.methodology_command in {"build", "draft"}:
            result = factory.build_methodology(workflow["id"], actor=args.author, note=args.note)
        elif args.methodology_command == "review":
            result = factory.review_methodology(workflow["id"], actor=args.author, note=args.note)
            if args.format == "human":
                print(_human_methodology_text(result["human_review"]))
                return 0
            print(json.dumps(result, indent=2))
            return 0
        elif args.methodology_command == "update":
            result = factory.update_methodology(
                workflow["id"],
                summary=args.summary,
                rules=args.rule or None,
                avoid=args.avoid or None,
                actor=args.author,
                note=args.note,
            )
        elif args.methodology_command == "reject":
            result = factory.reject_methodology(workflow["id"], actor=args.author, note=args.note)
        else:
            result = factory.approve_methodology(
                workflow["id"],
                actor=args.author,
                note=args.note,
                require_human_review=not args.no_require_human_review,
            )
        print(json.dumps({"methodology": _methodology_payload(result)}, indent=2))
        return 0
    if args.command == "run":
        if args.run_command == "create":
            workflow = _workflow(factory, args.workflow)
            task = _load_json(args.task)
            candidates = _load_json(args.candidates)
            result = factory.run_candidates(workflow["id"], task, candidates, mode=args.mode)
            print(json.dumps({"run": result}, indent=2))
            return 0
        print(json.dumps({"run": factory.apply_memory(args.run_id) if args.use_memory else factory.score_run(args.run_id)}, indent=2))
        return 0
    if args.command == "memory":
        workflow = _workflow(factory, args.workflow)
        print(json.dumps(factory.memory(workflow["id"]), indent=2))
        return 0
    if args.command == "receipts":
        workflow = _workflow(factory, args.workflow)
        created = factory.backfill_release_receipts(workflow["id"])
        print(json.dumps({"created": len(created), "receipts": created}, indent=2))
        return 0
    if args.command == "cycle-diff":
        workflow = _workflow(factory, args.workflow)
        print(json.dumps(factory.cycle_diff(workflow["id"], before=args.before, after=args.after), indent=2))
        return 0
    if args.command == "decision":
        result = factory.capture_decision(
            args.run,
            args.selected,
            action=args.action,
            reason=args.reason,
            corrected_output=args.corrected_output,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "export":
        workflow = _workflow(factory, args.workflow)
        if args.export_command == "pack":
            factory.export_memory_pack(workflow["id"], args.out, organic_only=args.organic_only)
            print(json.dumps({"status": "exported", "out": args.out}, indent=2))
            return 0
        if args.export_command == "graph":
            graph = factory.export.graph(args.out, store_id=workflow["id"])
            print(json.dumps({"status": "exported", "out": args.out, "nodes": len(graph["nodes"]), "edges": len(graph["edges"])}, indent=2))
            return 0
        if args.export_command == "preferences":
            sys.stdout.write(factory.export_preferences(workflow["id"], organic_only=args.organic_only))
            return 0
        if args.export_command == "examples":
            sys.stdout.write(factory.export_examples(workflow["id"], organic_only=args.organic_only))
            return 0
        if args.export_command == "sft":
            sys.stdout.write(factory.export_sft(workflow["id"], organic_only=args.organic_only))
            return 0
        if args.export_command == "dpo":
            sys.stdout.write(factory.export_dpo(workflow["id"], organic_only=args.organic_only))
            return 0
        sys.stdout.write(factory.export_check_cases(workflow["id"], organic_only=args.organic_only))
        return 0
    return 1


def _normalize_argv(argv):
    argv = list(argv)
    project_flags: list[str] = []
    cleaned: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--project" and index + 1 < len(argv):
            project_flags.extend(["--project", argv[index + 1]])
            index += 2
            continue
        if token.startswith("--project="):
            project_flags.append(token)
            index += 1
            continue
        cleaned.append(token)
        index += 1
    argv = project_flags + cleaned
    try:
        review_index = argv.index("review")
    except ValueError:
        return argv
    if len(argv) > review_index + 1 and argv[review_index + 1] != "capture" and not argv[review_index + 1].startswith("-"):
        packet_id = argv[review_index + 1]
        return argv[: review_index + 1] + ["capture", "--packet", packet_id] + argv[review_index + 2 :]
    return argv


_SUBCOMMANDS = {
    "project",
    "init",
    "mcp",
    "demo",
    "start",
    "studio",
    "store",
    "source",
    "connection",
    "review-point",
    "observe",
    "review",
    "workflow",
    "corpus",
    "methodology",
    "run",
    "memory",
    "receipts",
    "cycle-diff",
    "decision",
    "export",
}


def _has_subcommand(argv):
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in _SUBCOMMANDS:
            return True
        if token == "--project" and index + 1 < len(argv):
            index += 2
            continue
        if token.startswith("--project="):
            index += 1
            continue
        index += 1
    return False


def _cli_mode_text() -> str:
    return """\
 ____  _   _ _____ ___
|  _ \\| | | | ____/ _ \\
| |_) | |_| |  _|| | | |
|  __/|  _  | |__| |_| |
|_|   |_| |_|_____\\___/

PHEO CLI mode
Build a governed learning loop around AI work you already have.

The loop
1. PHEO Go
   Ingest source material, criteria, and examples. PHEO reshapes them to infer your method.

2. PHEO Grow
   Observe outputs from your agent, endpoint, or workflow. PHEO branches, scores, and routes the work.

3. PHEO Govern
   Humans approve, edit, reject, or escalate. Every judgment becomes decision memory with a reason and receipt.

4. PHEO Do
   Run the next action with the learned workflow, instead of rediscovering the path each time.

Start with the local UI
  pheo

Start from templates
  pheo demo hello-world --reset
  pheo demo langchain-attach --reset

Build your own workflow
  pheo workflow create --name my_workflow --domain operations --objective "Review AI output before release."
  pheo corpus add --workflow my_workflow policy.md examples.jsonl
  pheo methodology build --workflow my_workflow
  pheo methodology review --workflow my_workflow --format human
  pheo methodology approve --workflow my_workflow --author reviewer@example.com
  pheo review-point add --store my_workflow --name my_review --description "Review outputs before release."
  pheo observe output --review-point my_review --file output.txt --use-memory
  pheo start --store my_workflow
  pheo export pack --workflow my_workflow --out ./pheo-memory-pack

Endpoint path
  pheo connection add --store my_workflow --name openrouter --type openai-compatible-endpoint --endpoint-url https://openrouter.ai/api/v1 --model openai/gpt-4o-mini --api-key-env OPENROUTER_API_KEY
  pheo observe endpoint --review-point my_review --connection openrouter --prompt "Review this work before release."

Plain `pheo` opens the local apprentice. Use `pheo --help` for every command.
"""


def _payload(value):
    return value.to_dict() if hasattr(value, "to_dict") else value


def _methodology_payload(methodology: dict) -> dict:
    allowed = {
        "id",
        "workflow_id",
        "summary",
        "rules",
        "avoid",
        "status",
        "confidence",
        "approved_at",
        "approved_by",
        "approval_note",
        "created_at",
        "updated_at",
    }
    output = {key: methodology.get(key) for key in allowed if key in methodology}
    output["bootstrap_pair_count"] = len(methodology.get("review_pairs") or [])
    return output


def _human_methodology_text(review: dict) -> str:
    lines = []
    lines.append(f"Workflow: {review.get('store') or ''}")
    lines.append(f"Status: {review.get('status') or 'draft'}")
    lines.append("")
    lines.append("Review goal / protocol")
    goal = review.get("goal") or ""
    if goal:
        lines.append(goal)
    else:
        lines.append("- Not supplied.")
    if review.get("goal_warning"):
        lines.append(f"Warning: {review['goal_warning']}")
    lines.append("")
    for title, key in (
        ("Must do", "must_do"),
        ("Must avoid", "must_avoid"),
        ("Escalate when", "escalate_when"),
        ("Dimensions", "dimensions"),
    ):
        lines.append(title)
        items = review.get(key) or []
        if not items:
            lines.append("- None drafted yet.")
        for item in items:
            if isinstance(item, dict):
                source = f" [{item.get('source')}]" if item.get("source") else ""
                lines.append(f"- {item.get('text') or ''}{source}")
            else:
                lines.append(f"- {item}")
        lines.append("")
    lines.append("Next")
    lines.append("- Edit with `pheo methodology update ...` if these rules are wrong.")
    lines.append("- Approve with `pheo methodology approve ...` only after human review.")
    return "\n".join(lines).strip()


def _workflow(factory: Pheo, ref: str):
    return factory.store.get_workflow(ref) or factory.workflow(ref, skill=ref)


def _source(source: str, tags: list[str]):
    path = Path(source)
    if path.is_dir():
        return Folder(str(path), tags=tags)
    if path.exists():
        return File(str(path), tags=tags)
    return Text(source[:60] or "Text", source, tags=tags)


def _load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _optional_json(value: str, fallback_key: str = "value"):
    if not value:
        return {}
    path = Path(value)
    text = path.read_text(encoding="utf-8") if path.exists() else value
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return {fallback_key: text}
    if isinstance(loaded, dict):
        return loaded
    return {fallback_key: loaded}


def _headers(values: list[str]) -> dict[str, str]:
    headers = {}
    for value in values or []:
        if ":" not in value:
            raise SystemExit("--header must be formatted as 'Name: value'")
        name, header_value = value.split(":", 1)
        headers[name.strip()] = header_value.strip()
    return headers


def _messages(messages_value: str, system: str, prompt: str, context: dict):
    if messages_value:
        path = Path(messages_value)
        text = path.read_text(encoding="utf-8") if path.exists() else messages_value
        loaded = json.loads(text)
        if isinstance(loaded, list):
            return loaded
        if isinstance(loaded, dict) and isinstance(loaded.get("messages"), list):
            return loaded["messages"]
        raise SystemExit("--messages must be a JSON list or an object with a messages list")
    user_prompt = prompt or context.get("goal") or context.get("client_request") or "Generate a workflow output for review."
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_prompt})
    return messages


def entrypoint(argv=None):
    try:
        return main(argv)
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"error": {"type": exc.__class__.__name__, "message": str(exc)}}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint())
