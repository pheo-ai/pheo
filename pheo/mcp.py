from __future__ import annotations

import json
import os
import sys
from typing import Any

from pheo import Pheo, __version__


TOOLS = [
    {
        "name": "pheo_create_store",
        "description": "Create or select a Pheo Data Store for one governed workflow.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "business_area": {"type": "string"},
                "goal": {"type": "string"},
                "description": {"type": "string"},
                "quality_dimensions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name"],
        },
    },
    {
        "name": "pheo_list_stores",
        "description": "List Pheo Data Stores in the local Pheo project.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "pheo_add_source",
        "description": "Add source material to a Pheo Data Store and draft review rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "store": {"type": "string"},
                "title": {"type": "string"},
                "text": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["store", "text"],
        },
    },
    {
        "name": "pheo_draft_methodology",
        "description": "Draft review rules from active source material. Does not approve them.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "store": {"type": "string"},
                "actor": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["store"],
        },
    },
    {
        "name": "pheo_review_methodology",
        "description": "Show draft review rules, events, and gate status for human review.",
        "inputSchema": {
            "type": "object",
            "properties": {"store": {"type": "string"}},
            "required": ["store"],
        },
    },
    {
        "name": "pheo_update_methodology",
        "description": "Edit draft review rules before approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "store": {"type": "string"},
                "summary": {"type": "string"},
                "rules": {"type": "array", "items": {"type": "string"}},
                "avoid": {"type": "array", "items": {"type": "string"}},
                "actor": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["store"],
        },
    },
    {
        "name": "pheo_approve_methodology",
        "description": "Approve draft review rules. Required before observation or scoring.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "store": {"type": "string"},
                "actor": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["store"],
        },
    },
    {
        "name": "pheo_reject_methodology",
        "description": "Reject draft review rules so they must be edited or rebuilt before use.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "store": {"type": "string"},
                "actor": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["store"],
        },
    },
    {
        "name": "pheo_create_review_point",
        "description": "Create a review point where AI or workflow outputs become governed outcomes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "store": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "dimensions": {"type": "array", "items": {"type": "string"}},
                "human_review": {"type": "string"},
            },
            "required": ["store", "name"],
        },
    },
    {
        "name": "pheo_add_endpoint_connection",
        "description": "Register an OpenAI-compatible endpoint connection for a Pheo Data Store. API keys are read from env.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "store": {"type": "string"},
                "name": {"type": "string"},
                "endpoint_url": {"type": "string"},
                "model": {"type": "string"},
                "api_key_env": {"type": "string"},
            },
            "required": ["store", "name", "endpoint_url", "model"],
        },
    },
    {
        "name": "pheo_observe_output",
        "description": "Capture one AI or agent output at a Pheo review point.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_point": {"type": "string"},
                "output": {"type": "string"},
                "context": {"type": "object"},
                "source": {"type": "object"},
                "use_memory": {"type": "boolean"},
            },
            "required": ["review_point", "output"],
        },
    },
    {
        "name": "pheo_observe_endpoint",
        "description": "Call an OpenAI-compatible endpoint through a configured connection and observe the output.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "review_point": {"type": "string"},
                "connection": {"type": "string"},
                "prompt": {"type": "string"},
                "system": {"type": "string"},
                "context": {"type": "object"},
                "source": {"type": "object"},
                "temperature": {"type": "number"},
            },
            "required": ["review_point", "connection", "prompt"],
        },
    },
    {
        "name": "pheo_capture_review",
        "description": "Capture a human review decision for a Pheo review packet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "packet_id": {"type": "string"},
                "selected_index": {"type": "integer"},
                "action": {"type": "string"},
                "reason": {"type": "string"},
                "corrected_output": {"type": "string"},
                "author_id": {"type": "string"},
            },
            "required": ["packet_id", "selected_index"],
        },
    },
    {
        "name": "pheo_export_memory",
        "description": "Export a Pheo memory pack and generated workflow graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "store": {"type": "string"},
                "out": {"type": "string"},
            },
            "required": ["store", "out"],
        },
    },
    {
        "name": "pheo_get_memory",
        "description": "Compile judgment memory for a Pheo Data Store.",
        "inputSchema": {
            "type": "object",
            "properties": {"store": {"type": "string"}},
            "required": ["store"],
        },
    },
    {
        "name": "pheo_get_release_receipts",
        "description": "List release receipts for reviewed outcomes.",
        "inputSchema": {
            "type": "object",
            "properties": {"store": {"type": "string"}},
            "required": ["store"],
        },
    },
    {
        "name": "pheo_get_training_manifest",
        "description": "Show the training manifest for exported preference data.",
        "inputSchema": {
            "type": "object",
            "properties": {"store": {"type": "string"}},
            "required": ["store"],
        },
    },
    {
        "name": "pheo_get_cycle_diff",
        "description": "Compare two workflow cycles by cycle_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "store": {"type": "string"},
                "before": {"type": "string"},
                "after": {"type": "string"},
            },
            "required": ["store"],
        },
    },
]


def run(project: str | None = None) -> None:
    store = Pheo.open(project or os.environ.get("PHEO_PROJECT") or "./.pheo")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle(store, request)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(exc)}}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def handle(store: Pheo, request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}
    if method == "initialize":
        return _result(request_id, {"protocolVersion": "2024-11-05", "serverInfo": {"name": "pheo", "version": __version__}, "capabilities": {"tools": {}}})
    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        return _result(request_id, {"content": [{"type": "text", "text": json.dumps(call_tool(store, name, args), indent=2)}]})
    if method == "notifications/initialized":
        return _result(request_id, {})
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def call_tool(store: Pheo, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "pheo_create_store":
        return {
            "store": store.create_store(
                args["name"],
                business_area=args.get("business_area") or "",
                description=args.get("description") or "",
                goal=args.get("goal") or "",
                quality_dimensions=args.get("quality_dimensions") or [],
            )
        }
    if name == "pheo_list_stores":
        return {"stores": store.workflows()}
    if name == "pheo_add_source":
        store.use_store(args["store"])
        return {
            "sources": store.source.add_text(
                args.get("title") or "MCP source",
                args["text"],
                tags=args.get("tags") or [],
            ),
            "methodology_gate": store.review_methodology(args["store"])["gate"],
        }
    if name == "pheo_draft_methodology":
        return {
            "methodology": _methodology_payload(
                store.build_methodology(
                    args["store"],
                    actor=args.get("actor") or "mcp",
                    note=args.get("note") or "Draft review rules generated from source material.",
                )
            )
        }
    if name == "pheo_review_methodology":
        return store.review_methodology(args["store"], actor=args.get("actor") or "human", note=args.get("note") or "Methodology draft reviewed.")
    if name == "pheo_update_methodology":
        return {
            "methodology": _methodology_payload(
                store.update_methodology(
                    args["store"],
                    summary=args.get("summary") or "",
                    rules=args.get("rules"),
                    avoid=args.get("avoid"),
                    actor=args.get("actor") or "human",
                    note=args.get("note") or "Review rules edited by reviewer.",
                )
            )
        }
    if name == "pheo_approve_methodology":
        return {
            "methodology": _methodology_payload(
                store.approve_methodology(
                    args["store"],
                    actor=args.get("actor") or "human",
                    note=args.get("note") or "",
                    require_human_review=bool(args.get("require_human_review", True)),
                )
            )
        }
    if name == "pheo_reject_methodology":
        return {
            "methodology": _methodology_payload(
                store.reject_methodology(
                    args["store"],
                    actor=args.get("actor") or "human",
                    note=args.get("note") or "",
                )
            )
        }
    if name == "pheo_create_review_point":
        store.use_store(args["store"])
        return {
            "review_point": store.review_point.create(
                args["name"],
                description=args.get("description") or "",
                dimensions=args.get("dimensions") or [],
                human_review=args.get("human_review") or "required",
            )
        }
    if name == "pheo_add_endpoint_connection":
        store.use_store(args["store"])
        return {
            "connection": store.connection.add_endpoint(
                args["name"],
                args["endpoint_url"],
                model=args["model"],
                api_key_env=args.get("api_key_env") or "OPENROUTER_API_KEY",
            )
        }
    if name == "pheo_observe_output":
        memory = None
        if args.get("use_memory"):
            point = store.get_review_point(args["review_point"])
            memory = store.memory(point["workflow_id"])
        return _payload(
            store.observe(
                args["review_point"],
                args["output"],
                context=args.get("context") or {},
                source=args.get("source") or {"connector": "mcp"},
                memory=memory,
            )
        )
    if name == "pheo_observe_endpoint":
        return store.observe_endpoint(
            args["review_point"],
            connection=args.get("connection") or None,
            prompt=args.get("prompt") or "",
            system=args.get("system") or "",
            context=args.get("context") or {},
            source={"connector": "mcp_endpoint", **(args.get("source") or {})},
            temperature=float(args.get("temperature", 0.7)),
        )
    if name == "pheo_capture_review":
        return store.review(
            args["packet_id"],
            int(args["selected_index"]),
            action=args.get("action") or "approve",
            reason=args.get("reason") or "",
            corrected_output=args.get("corrected_output") or "",
            author_id=args.get("author_id") or "",
        )
    if name == "pheo_export_memory":
        return store.export.memory_pack(args["out"], store_id=args["store"])
    if name == "pheo_get_memory":
        workflow = store.get_workflow(args["store"])
        return store.memory(workflow["id"])
    if name == "pheo_get_release_receipts":
        workflow = store.get_workflow(args["store"])
        return {"release_receipts": store.release_receipts(workflow["id"])}
    if name == "pheo_get_training_manifest":
        workflow = store.get_workflow(args["store"])
        return store.training_manifest(workflow["id"])
    if name == "pheo_get_cycle_diff":
        workflow = store.get_workflow(args["store"])
        return store.cycle_diff(workflow["id"], before=args.get("before") or "cycle_1", after=args.get("after") or "cycle_2")
    raise ValueError(f"Unknown tool: {name}")


def _payload(value: Any) -> Any:
    return value.to_dict() if hasattr(value, "to_dict") else value


def _methodology_payload(methodology: dict[str, Any]) -> dict[str, Any]:
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


def _result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


if __name__ == "__main__":
    run()
