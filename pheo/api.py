import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from pheo import Pheo, __version__
from pheo.core.endpoint import call_openai_compatible_endpoint, safe_endpoint
from pheo.openapi import OPENAPI_SPEC
from pheo.projects import create_project, list_projects, project_summary, set_current_project
from pheo.ui import PREFERENCE_STORE_HTML


def create_handler(project="./.pheo"):
    state = {
        "project": str(project),
        "factory": Pheo.open(project),
    }

    class Handler(BaseHTTPRequestHandler):
        server_version = "Pheo/0.1"

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                if path == "/" or path == "/preference-store":
                    return self.html(PREFERENCE_STORE_HTML)
                if path.startswith("/review/"):
                    return self.html(PREFERENCE_STORE_HTML)
                if path == "/health":
                    return self.json({"status": "healthy", "version": __version__})
                if path == "/openapi.json":
                    return self.json(OPENAPI_SPEC)
                if path == "/v1/projects":
                    return self.json(_projects_payload(state["project"]))
                if path == "/v1/stores":
                    return self.json({"stores": state["factory"].workflows()})
                if path.startswith("/v1/stores/") and len(_parts(path)) == 3:
                    store_id = _path_part(path, 2)
                    return self.json({"store": state["factory"].get_workflow(store_id)})
                if path.startswith("/v1/stores/") and path.endswith("/sources"):
                    store_id = _path_part(path, 2)
                    return self.json({"sources": state["factory"].corpus(store_id)})
                if path.startswith("/v1/stores/") and path.endswith("/connections"):
                    store_id = _path_part(path, 2)
                    return self.json({"connections": state["factory"].connections(store_id)})
                if path.startswith("/v1/stores/") and path.endswith("/review-points"):
                    store_id = _path_part(path, 2)
                    return self.json({"review_points": state["factory"].review_points(store_id)})
                if path.startswith("/v1/stores/") and path.endswith("/memory-pack"):
                    store_id = _path_part(path, 2)
                    return self.json(state["factory"].memory_pack(store_id, organic_only=_truthy_query(parsed, "organic_only")))
                if path.startswith("/v1/review-packets/") and len(_parts(path)) == 3:
                    packet_id = _path_part(path, 2)
                    return self.json(state["factory"]._review_packet_payload(packet_id))
                if path == "/v1/workflows":
                    return self.json({"workflows": state["factory"].workflows()})
                if path.startswith("/v1/workflows/") and len([part for part in path.split("/") if part]) == 3:
                    workflow_id = _path_part(path, 2)
                    return self.json({"workflow": state["factory"].get_workflow(workflow_id)})
                if path.startswith("/v1/workflows/") and path.endswith("/methodology"):
                    workflow_id = _path_part(path, 2)
                    return self.json(state["factory"].review_methodology(workflow_id))
                if path.startswith("/v1/workflows/") and path.endswith("/runs"):
                    workflow_id = _path_part(path, 2)
                    return self.json({"runs": state["factory"].runs(workflow_id)})
                if path.startswith("/v1/workflows/") and path.endswith("/corpus"):
                    workflow_id = _path_part(path, 2)
                    return self.json({"items": state["factory"].corpus(workflow_id)})
                if path.startswith("/v1/workflows/") and path.endswith("/preference-store"):
                    workflow_id = _path_part(path, 2)
                    return self.json(state["factory"].preference_store(workflow_id))
                if path.startswith("/v1/workflows/") and path.endswith("/memory-pack"):
                    workflow_id = _path_part(path, 2)
                    return self.json(state["factory"].memory_pack(workflow_id, organic_only=_truthy_query(parsed, "organic_only")))
                if path.startswith("/v1/runs/"):
                    run_id = _path_part(path, 2)
                    return self.json({"run": state["factory"].run(run_id)})
                if path == "/v1/export/preferences":
                    workflow_id = _query(parsed, "workflow")
                    return self.text(state["factory"].export_preferences(workflow_id, organic_only=_truthy_query(parsed, "organic_only")), "application/jsonl; charset=utf-8")
                if path == "/v1/export/examples":
                    workflow_id = _query(parsed, "workflow")
                    return self.text(state["factory"].export_examples(workflow_id, organic_only=_truthy_query(parsed, "organic_only")), "application/jsonl; charset=utf-8")
                if path == "/v1/export/checks":
                    workflow_id = _query(parsed, "workflow")
                    return self.text(state["factory"].export_check_cases(workflow_id, organic_only=_truthy_query(parsed, "organic_only")), "application/jsonl; charset=utf-8")
                return self.error("NOT_FOUND", "Not found", HTTPStatus.NOT_FOUND)
            except Exception as exc:
                return self.error("PROCESSING_ERROR", str(exc), HTTPStatus.BAD_REQUEST)

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                body = self.read_json()
                if path == "/v1/projects":
                    record = create_project(
                        body.get("name") or "project",
                        path=body.get("path") or None,
                        make_current=bool(body.get("make_current", True)),
                    )
                    if body.get("activate", True):
                        state["project"] = record["path"]
                        state["factory"] = Pheo.open(record["path"])
                    return self.json({"project": record, **_projects_payload(state["project"])}, HTTPStatus.CREATED)
                if path == "/v1/projects/current":
                    record = set_current_project(body.get("ref") or body.get("name") or body.get("path") or "")
                    state["project"] = record["path"]
                    state["factory"] = Pheo.open(record["path"])
                    return self.json({"project": record, **_projects_payload(state["project"])})
                if path == "/v1/stores":
                    store = state["factory"].create_store(
                        body.get("name") or "preference_store",
                        business_area=body.get("business_area") or body.get("domain") or "",
                        description=body.get("description") or body.get("objective") or "",
                        goal=body.get("goal") or "",
                        quality_dimensions=body.get("quality_dimensions") or [],
                    )
                    return self.json({"store": store}, HTTPStatus.CREATED)
                if path.startswith("/v1/stores/") and path.endswith("/sources"):
                    store_id = _path_part(path, 2)
                    sources = state["factory"].attach_corpus(store_id, body.get("items") or body.get("sources") or [])
                    return self.json({"sources": sources}, HTTPStatus.CREATED)
                if path.startswith("/v1/stores/") and path.endswith("/connections"):
                    store_id = _path_part(path, 2)
                    config = body.get("config") or {}
                    if body.get("connector_type") in {"openai-compatible-endpoint", "openai_compatible_endpoint"}:
                        config = {
                            **config,
                            "endpoint_url": body.get("endpoint_url") or config.get("endpoint_url") or "",
                            "model": body.get("model") or config.get("model") or "",
                            "api_key_env": body.get("api_key_env") or config.get("api_key_env") or "OPENROUTER_API_KEY",
                        }
                    connection = state["factory"].create_connection(
                        body.get("name") or "connection",
                        (body.get("connector_type") or "rest-ingest").replace("-", "_"),
                        config,
                        store_id=store_id,
                    )
                    return self.json({"connection": connection}, HTTPStatus.CREATED)
                if path.startswith("/v1/stores/") and path.endswith("/review-points"):
                    store_id = _path_part(path, 2)
                    point = state["factory"].create_review_point(
                        body.get("name") or "review_point",
                        description=body.get("description") or "",
                        dimensions=body.get("dimensions") or [],
                        human_review=body.get("human_review") or "required",
                        branching=body.get("branching") or "kernel",
                        store_id=store_id,
                        connection=body.get("connection") or "",
                        connector_type=body.get("connector_type") or "",
                        connector_config=body.get("connector_config") or {},
                    )
                    return self.json({"review_point": point}, HTTPStatus.CREATED)
                if _is_store_review_point_route(path, "observations"):
                    parts = _parts(path)
                    store_id = parts[2]
                    review_point = parts[4]
                    state["factory"].use_store(store_id)
                    packet = state["factory"].observe(
                        review_point,
                        output=body.get("output") or "",
                        context=body.get("context") or {},
                        source=body.get("source") or {},
                        candidates=body.get("candidates") or None,
                        mode=body.get("mode") or None,
                    )
                    return self.json(_payload(packet), HTTPStatus.CREATED)
                if _is_review_point_route(path, "observations"):
                    review_point = _path_part(path, 2)
                    packet = state["factory"].observe(
                        review_point,
                        output=body.get("output") or "",
                        context=body.get("context") or {},
                        source=body.get("source") or {},
                        candidates=body.get("candidates") or None,
                        mode=body.get("mode") or None,
                    )
                    return self.json(_payload(packet), HTTPStatus.CREATED)
                if _is_store_review_point_route(path, "trace-observations"):
                    parts = _parts(path)
                    state["factory"].use_store(parts[2])
                    packets = state["factory"].observe_traces(parts[4], body.get("source_type") or "generic", body.get("payload"), task=body.get("task") or None)
                    return self.json({"packets": [_payload(packet) for packet in packets]}, HTTPStatus.CREATED)
                if _is_review_point_route(path, "trace-observations"):
                    review_point = _path_part(path, 2)
                    packets = state["factory"].observe_traces(review_point, body.get("source_type") or "generic", body.get("payload"), task=body.get("task") or None)
                    return self.json({"packets": [_payload(packet) for packet in packets]}, HTTPStatus.CREATED)
                if _is_store_review_point_route(path, "endpoint-observations"):
                    parts = _parts(path)
                    state["factory"].use_store(parts[2])
                    packet = state["factory"].observe_endpoint(
                        parts[4],
                        connection=body.get("connection") or None,
                        endpoint_url=body.get("endpoint_url") or "",
                        model=body.get("model") or "",
                        api_key=body.get("api_key") or "",
                        api_key_env=body.get("api_key_env") or "OPENROUTER_API_KEY",
                        messages=body.get("messages") or None,
                        prompt=body.get("prompt") or "",
                        system=body.get("system") or "",
                        context=body.get("task") or {},
                        source={
                            "connector": "openai_compatible_endpoint",
                            **(body.get("source") or {}),
                        },
                    )
                    return self.json(_payload(packet), HTTPStatus.CREATED)
                if _is_review_point_route(path, "endpoint-observations"):
                    review_point = _path_part(path, 2)
                    packet = state["factory"].observe_endpoint(
                        review_point,
                        connection=body.get("connection") or None,
                        endpoint_url=body.get("endpoint_url") or "",
                        model=body.get("model") or "",
                        api_key=body.get("api_key") or "",
                        api_key_env=body.get("api_key_env") or "OPENROUTER_API_KEY",
                        messages=body.get("messages") or None,
                        prompt=body.get("prompt") or "",
                        system=body.get("system") or "",
                        context=body.get("task") or {},
                        source={
                            "connector": "openai_compatible_endpoint",
                            **(body.get("source") or {}),
                        },
                    )
                    return self.json(_payload(packet), HTTPStatus.CREATED)
                if path.startswith("/v1/review-packets/") and path.endswith("/reviews"):
                    packet_id = _path_part(path, 2)
                    result = state["factory"].review(
                        packet_id,
                        int(body.get("selected_index", -1)),
                        action=body.get("action") or "approve",
                        reason=body.get("reason") or "",
                        corrected_output=body.get("corrected_output") or "",
                        weight=body.get("weight"),
                        author_id=body.get("author_id") or "",
                    )
                    return self.json(result, HTTPStatus.CREATED)
                if path == "/v1/workflows":
                    workflow = state["factory"].workflow(
                        body.get("name") or "workflow",
                        body.get("domain") or "",
                        body.get("goal") or body.get("objective") or body.get("description") or "",
                        body.get("skill") or "",
                        body.get("quality_dimensions") or [],
                    )
                    return self.json({"workflow": workflow}, HTTPStatus.CREATED)
                if path.startswith("/v1/workflows/") and path.endswith("/corpus"):
                    workflow_id = _path_part(path, 2)
                    items = state["factory"].attach_corpus(workflow_id, body.get("items") or [])
                    return self.json({"items": items}, HTTPStatus.CREATED)
                if path.startswith("/v1/workflows/") and path.endswith("/methodology/build"):
                    workflow_id = _path_part(path, 2)
                    return self.json(
                        {
                            "methodology": _methodology_payload(
                                state["factory"].build_methodology(
                                    workflow_id,
                                    actor=body.get("author") or body.get("actor") or "pheo",
                                    note=body.get("note") or "Draft review rules generated from source material.",
                                )
                            )
                        }
                    )
                if path.startswith("/v1/workflows/") and path.endswith("/methodology/reject"):
                    workflow_id = _path_part(path, 2)
                    return self.json(
                        {
                            "methodology": _methodology_payload(
                                state["factory"].reject_methodology(
                                    workflow_id,
                                    actor=body.get("author") or body.get("actor") or "human",
                                    note=body.get("note") or "",
                                )
                            )
                        }
                    )
                if path.startswith("/v1/workflows/") and path.endswith("/methodology/update"):
                    workflow_id = _path_part(path, 2)
                    return self.json(
                        {
                            "methodology": _methodology_payload(
                                state["factory"].update_methodology(
                                    workflow_id,
                                    summary=body.get("summary") or "",
                                    rules=body.get("rules") or [],
                                    avoid=body.get("avoid") or [],
                                    actor=body.get("author") or body.get("actor") or "human",
                                    note=body.get("note") or "Review rules edited by reviewer.",
                                )
                            )
                        }
                    )
                if path.startswith("/v1/workflows/") and path.endswith("/methodology/approve"):
                    workflow_id = _path_part(path, 2)
                    return self.json(
                        {
                            "methodology": _methodology_payload(
                                state["factory"].approve_methodology(
                                    workflow_id,
                                    actor=body.get("author") or body.get("actor") or "human",
                                    note=body.get("note") or "",
                                )
                            )
                        }
                    )
                if path.startswith("/v1/workflows/") and path.endswith("/runs"):
                    workflow_id = _path_part(path, 2)
                    run = state["factory"].run_candidates(
                        workflow_id,
                        body.get("task") or {},
                        body.get("candidates") or [],
                        mode=body.get("mode") or "external",
                    )
                    return self.json({"run": run}, HTTPStatus.CREATED)
                if path.startswith("/v1/workflows/") and path.endswith("/endpoint-runs"):
                    workflow_id = _path_part(path, 2)
                    output = call_openai_compatible_endpoint(body)
                    run = state["factory"].run_candidates(
                        workflow_id,
                        body.get("task") or {},
                        [
                            {
                                "output": output,
                                "generator": body.get("model") or "openai_compatible_endpoint",
                                "metadata": {"connector": "openai_compatible_endpoint", "endpoint": safe_endpoint(body.get("endpoint_url") or "")},
                            }
                        ],
                        mode="kernel",
                    )
                    return self.json({"run": state["factory"].score_run(run["id"])}, HTTPStatus.CREATED)
                if path.startswith("/v1/workflows/") and path.endswith("/trace-runs"):
                    workflow_id = _path_part(path, 2)
                    runs = state["factory"].import_traces(
                        workflow_id,
                        body.get("source_type") or "generic",
                        body.get("payload"),
                        task=body.get("task") or None,
                        score=bool(body.get("score", True)),
                    )
                    return self.json({"runs": runs}, HTTPStatus.CREATED)
                if path.startswith("/v1/runs/") and path.endswith("/score"):
                    run_id = _path_part(path, 2)
                    return self.json({"run": state["factory"].score_run(run_id)})
                if path.startswith("/v1/runs/") and path.endswith("/decisions"):
                    run_id = _path_part(path, 2)
                    result = state["factory"].capture_decision(
                        run_id,
                        int(body.get("selected_index", -1)),
                        action=body.get("action") or "approve",
                        reason=body.get("reason") or "",
                        corrected_output=body.get("corrected_output") or "",
                        weight=body.get("weight"),
                        author_id=body.get("author_id") or "",
                    )
                    return self.json(result, HTTPStatus.CREATED)
                return self.error("NOT_FOUND", "Not found", HTTPStatus.NOT_FOUND)
            except Exception as exc:
                return self.error("PROCESSING_ERROR", str(exc), HTTPStatus.BAD_REQUEST)

        def do_DELETE(self):
            path = urlparse(self.path).path
            try:
                if path.startswith("/v1/corpus/"):
                    corpus_id = _path_part(path, 2)
                    return self.json({"item": state["factory"].deactivate_corpus(corpus_id)})
                return self.error("NOT_FOUND", "Not found", HTTPStatus.NOT_FOUND)
            except Exception as exc:
                return self.error("PROCESSING_ERROR", str(exc), HTTPStatus.BAD_REQUEST)

        def read_json(self):
            length = int(self.headers.get("Content-Length", 0))
            if not length:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def json(self, payload, status=HTTPStatus.OK):
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(payload, default=str).encode("utf-8"))

        def html(self, content, status=HTTPStatus.OK):
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        def text(self, content, content_type="text/plain; charset=utf-8", status=HTTPStatus.OK):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        def error(self, code, message, status):
            return self.json({"error": code, "message": message}, status)

        def log_message(self, fmt, *args):
            return None

    return Handler


def run_server(project="./.pheo", host="127.0.0.1", port=8787):
    server = ThreadingHTTPServer((host, port), create_handler(project))
    print(f"Pheo Data Store running at http://{host}:{port}")
    server.serve_forever()


def _path_part(path: str, index: int) -> str:
    return _parts(path)[index]


def _parts(path: str) -> list[str]:
    return [part for part in path.split("/") if part]


def _is_review_point_route(path: str, leaf: str) -> bool:
    parts = _parts(path)
    return len(parts) == 4 and parts[0] == "v1" and parts[1] == "review-points" and parts[3] == leaf


def _is_store_review_point_route(path: str, leaf: str) -> bool:
    parts = _parts(path)
    return len(parts) == 6 and parts[0] == "v1" and parts[1] == "stores" and parts[3] == "review-points" and parts[5] == leaf


def _query(parsed, key: str) -> str:
    values = parse_qs(parsed.query).get(key) or []
    if not values:
        raise ValueError(f"Missing query parameter: {key}")
    return values[0]


def _truthy_query(parsed, key: str) -> bool:
    values = parse_qs(parsed.query).get(key) or []
    if not values:
        return False
    return values[0].lower() in {"1", "true", "yes", "on"}


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


def _projects_payload(active_project: str) -> dict:
    current = project_summary(active_project)
    projects = list_projects()
    matched = False
    for index, item in enumerate(projects):
        if item["path"] == current["path"] or item["database"] == current["database"]:
            projects[index] = {**item, "current": True}
            current = projects[index]
            matched = True
        else:
            projects[index] = {**item, "current": False}
    if not matched:
        current = {**current, "current": True}
        projects = [current, *projects]
    return {"current_project": current, "projects": projects}


if __name__ == "__main__":
    run_server()
