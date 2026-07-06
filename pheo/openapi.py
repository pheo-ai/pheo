from __future__ import annotations


def _operation(
    tag: str,
    summary: str,
    *,
    params: list[str] | None = None,
    query: list[str] | None = None,
    body_ref: str | None = None,
    content_type: str = "application/json",
) -> dict:
    responses = {
        "200": {"description": "OK", "content": {content_type: {"schema": {"$ref": "#/components/schemas/AnyObject"}}}},
        "400": {"description": "Bad request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
        "404": {"description": "Not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
    }
    operation = {
        "tags": [tag],
        "summary": summary,
        "parameters": [_path_param(name) for name in params or []] + [_query_param(name) for name in query or []],
        "responses": responses,
    }
    if body_ref:
        operation["requestBody"] = {
            "required": False,
            "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{body_ref}"}}},
        }
    return operation


def _path_param(name: str) -> dict:
    return {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}


def _query_param(name: str) -> dict:
    schema = {"type": "boolean"} if name == "organic_only" else {"type": "string"}
    return {"name": name, "in": "query", "required": name == "workflow", "schema": schema}


def _schema(fields: list[str]) -> dict:
    return {
        "type": "object",
        "additionalProperties": True,
        "properties": {field: {"description": f"{field} value"} for field in fields},
    }


OPENAPI_SPEC = {
    "openapi": "3.1.0",
    "info": {
        "title": "Pheo Local API",
        "version": "0.1.11",
        "description": (
            "Local REST API for Pheo projects, stores, source material, methodology gates, "
            "review points, observations, human reviews, release receipts, and memory exports."
        ),
    },
    "servers": [{"url": "http://127.0.0.1:8787", "description": "Local Pheo server"}],
    "tags": [
        {"name": "Health"},
        {"name": "Projects"},
        {"name": "Stores"},
        {"name": "Methodology"},
        {"name": "Review Points"},
        {"name": "Observations"},
        {"name": "Reviews"},
        {"name": "Runs"},
        {"name": "Exports"},
    ],
    "paths": {
        "/health": {"get": _operation("Health", "Check server health")},
        "/openapi.json": {"get": _operation("Health", "Fetch the machine-readable OpenAPI spec")},
        "/v1/projects": {
            "get": _operation("Projects", "List known local projects"),
            "post": _operation("Projects", "Create a project", body_ref="ProjectCreate"),
        },
        "/v1/projects/current": {
            "post": _operation("Projects", "Switch the active project", body_ref="ProjectCurrent")
        },
        "/v1/stores": {
            "get": _operation("Stores", "List stores in the active project"),
            "post": _operation("Stores", "Create a Pheo Data Store", body_ref="StoreCreate"),
        },
        "/v1/stores/{store}": {"get": _operation("Stores", "Get a store", params=["store"])},
        "/v1/stores/{store}/sources": {
            "get": _operation("Stores", "List source material for a store", params=["store"]),
            "post": _operation("Stores", "Attach source material to a store", params=["store"], body_ref="CorpusAttach"),
        },
        "/v1/stores/{store}/connections": {
            "get": _operation("Stores", "List endpoint or ingest connections for a store", params=["store"]),
            "post": _operation("Stores", "Create a connection", params=["store"], body_ref="ConnectionCreate"),
        },
        "/v1/stores/{store}/review-points": {
            "get": _operation("Review Points", "List review points for a store", params=["store"]),
            "post": _operation("Review Points", "Create a review point", params=["store"], body_ref="ReviewPointCreate"),
        },
        "/v1/stores/{store}/memory-pack": {
            "get": _operation("Exports", "Export a memory pack for a store", params=["store"], query=["organic_only"])
        },
        "/v1/stores/{store}/review-points/{point}/observations": {
            "post": _operation("Observations", "Observe an existing workflow output", params=["store", "point"], body_ref="ObservationCreate")
        },
        "/v1/stores/{store}/review-points/{point}/endpoint-observations": {
            "post": _operation("Observations", "Call an OpenAI-compatible endpoint and observe the output", params=["store", "point"], body_ref="EndpointObservationCreate")
        },
        "/v1/stores/{store}/review-points/{point}/trace-observations": {
            "post": _operation("Observations", "Import trace records as review packets", params=["store", "point"], body_ref="TraceObservationCreate")
        },
        "/v1/review-points/{point}/observations": {
            "post": _operation("Observations", "Observe an output using the active store", params=["point"], body_ref="ObservationCreate")
        },
        "/v1/review-points/{point}/endpoint-observations": {
            "post": _operation("Observations", "Observe endpoint output using the active store", params=["point"], body_ref="EndpointObservationCreate")
        },
        "/v1/review-points/{point}/trace-observations": {
            "post": _operation("Observations", "Import traces using the active store", params=["point"], body_ref="TraceObservationCreate")
        },
        "/v1/review-packets/{packet}": {
            "get": _operation("Reviews", "Get a review packet", params=["packet"])
        },
        "/v1/review-packets/{packet}/reviews": {
            "post": _operation("Reviews", "Capture a human review decision", params=["packet"], body_ref="ReviewCapture")
        },
        "/v1/workflows": {
            "get": _operation("Stores", "List workflows"),
            "post": _operation("Stores", "Create a workflow", body_ref="WorkflowCreate"),
        },
        "/v1/workflows/{workflow}": {
            "get": _operation("Stores", "Get a workflow", params=["workflow"])
        },
        "/v1/workflows/{workflow}/corpus": {
            "get": _operation("Stores", "List workflow corpus", params=["workflow"]),
            "post": _operation("Stores", "Attach corpus to a workflow", params=["workflow"], body_ref="CorpusAttach"),
        },
        "/v1/corpus/{corpus}": {
            "delete": _operation("Stores", "Deactivate a corpus item", params=["corpus"])
        },
        "/v1/workflows/{workflow}/methodology": {
            "get": _operation("Methodology", "Review methodology draft/status", params=["workflow"])
        },
        "/v1/workflows/{workflow}/methodology/build": {
            "post": _operation("Methodology", "Build methodology from source material", params=["workflow"], body_ref="MethodologyBuild")
        },
        "/v1/workflows/{workflow}/methodology/update": {
            "post": _operation("Methodology", "Save edited methodology rules", params=["workflow"], body_ref="MethodologyUpdate")
        },
        "/v1/workflows/{workflow}/methodology/approve": {
            "post": _operation("Methodology", "Approve methodology before runtime", params=["workflow"], body_ref="Approval")
        },
        "/v1/workflows/{workflow}/methodology/reject": {
            "post": _operation("Methodology", "Reject methodology draft", params=["workflow"], body_ref="Approval")
        },
        "/v1/workflows/{workflow}/runs": {
            "get": _operation("Runs", "List runs for a workflow", params=["workflow"]),
            "post": _operation("Runs", "Create a candidate run", params=["workflow"], body_ref="RunCreate"),
        },
        "/v1/workflows/{workflow}/endpoint-runs": {
            "post": _operation("Runs", "Call an OpenAI-compatible endpoint and create a run", params=["workflow"], body_ref="EndpointRunCreate")
        },
        "/v1/workflows/{workflow}/trace-runs": {
            "post": _operation("Runs", "Import trace records as runs", params=["workflow"], body_ref="TraceRunCreate")
        },
        "/v1/workflows/{workflow}/preference-store": {
            "get": _operation("Exports", "Inspect Pheo Data Store memory", params=["workflow"])
        },
        "/v1/workflows/{workflow}/memory-pack": {
            "get": _operation("Exports", "Export workflow memory pack", params=["workflow"], query=["organic_only"])
        },
        "/v1/runs/{run}": {"get": _operation("Runs", "Get a run", params=["run"])},
        "/v1/runs/{run}/score": {"post": _operation("Runs", "Score a run", params=["run"])},
        "/v1/runs/{run}/decisions": {
            "post": _operation("Reviews", "Capture a run-level decision", params=["run"], body_ref="ReviewCapture")
        },
        "/v1/export/preferences": {
            "get": _operation("Exports", "Export preference pairs as JSONL", query=["workflow", "organic_only"], content_type="application/jsonl")
        },
        "/v1/export/examples": {
            "get": _operation("Exports", "Export released examples as JSONL", query=["workflow", "organic_only"], content_type="application/jsonl")
        },
        "/v1/export/checks": {
            "get": _operation("Exports", "Export check cases as JSONL", query=["workflow", "organic_only"], content_type="application/jsonl")
        },
    },
    "components": {
        "schemas": {
            "AnyObject": {"type": "object", "additionalProperties": True},
            "ProjectCreate": _schema(["name", "path", "make_current", "activate"]),
            "ProjectCurrent": _schema(["ref", "name", "path"]),
            "StoreCreate": _schema(["name", "business_area", "domain", "description", "goal", "quality_dimensions"]),
            "WorkflowCreate": _schema(["name", "domain", "goal", "objective", "description", "skill", "quality_dimensions"]),
            "CorpusAttach": _schema(["items", "sources"]),
            "ConnectionCreate": _schema(["name", "connector_type", "endpoint_url", "model", "api_key_env", "config"]),
            "ReviewPointCreate": _schema(["name", "description", "dimensions", "human_review", "branching", "connection", "connector_type", "connector_config"]),
            "ObservationCreate": _schema(["output", "context", "source", "candidates", "mode"]),
            "EndpointObservationCreate": _schema(["connection", "endpoint_url", "model", "api_key", "api_key_env", "messages", "prompt", "system", "task", "source"]),
            "TraceObservationCreate": _schema(["source_type", "payload", "task"]),
            "MethodologyBuild": _schema(["author", "actor", "note"]),
            "MethodologyUpdate": _schema(["summary", "rules", "avoid", "author", "actor", "note"]),
            "Approval": _schema(["author", "actor", "note"]),
            "RunCreate": _schema(["task", "candidates", "mode"]),
            "EndpointRunCreate": _schema(["endpoint_url", "model", "api_key", "api_key_env", "messages", "prompt", "system", "task", "source"]),
            "TraceRunCreate": _schema(["source_type", "payload", "task", "score"]),
            "ReviewCapture": _schema(["selected_index", "action", "reason", "corrected_output", "weight", "author_id"]),
            "Error": {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "message": {"type": "string"},
                },
            },
        }
    },
}
