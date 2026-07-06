from __future__ import annotations

import json
from typing import Any


def normalize_trace_runs(source_type: str, payload: Any) -> list[dict[str, Any]]:
    source_type = (source_type or "generic").lower().replace("_", "-")
    records = _records(payload)
    runs = []
    for index, record in enumerate(records):
        task = _task_from_record(record, source_type, index)
        outputs = _outputs_from_record(record, source_type)
        candidates = []
        for output_index, output in enumerate(outputs):
            text = _as_text(output)
            if text:
                candidates.append(
                    {
                        "output": text,
                        "generator": _generator_from_record(record, source_type),
                        "metadata": {
                            "connector": source_type,
                            "trace_index": index,
                            "output_index": output_index,
                            "trace_id": _trace_id(record),
                        },
                    }
                )
        if candidates:
            runs.append({"task": task, "candidates": candidates})
    return runs


def _records(payload: Any) -> list[Any]:
    if isinstance(payload, str):
        payload = payload.strip()
        if not payload:
            return []
        if "\n" in payload and not payload.startswith(("[", "{")):
            return [json.loads(line) for line in payload.splitlines() if line.strip()]
        payload = json.loads(payload)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "traces" in payload and isinstance(payload["traces"], list):
            return payload["traces"]
        if "runs" in payload and isinstance(payload["runs"], list):
            return payload["runs"]
        if "calls" in payload and isinstance(payload["calls"], list):
            return payload["calls"]
        if "spans" in payload and isinstance(payload["spans"], list):
            return payload["spans"]
        otel_spans = _otel_spans(payload)
        if otel_spans:
            return otel_spans
        return [payload]
    return []


def _task_from_record(record: Any, source_type: str, index: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {"goal": f"Review {source_type} trace {index + 1}"}
    inputs = record.get("inputs") or record.get("input") or record.get("attributes") or {}
    if isinstance(inputs, dict):
        for key in ("prompt", "question", "query", "goal", "input", "messages"):
            if key in inputs:
                return {"goal": _as_text(inputs[key]), "connector": source_type}
    if source_type == "noveum":
        attrs = _attributes(record)
        for key in ("review.goal", "llm.input.prompt", "input.prompt", "prompt", "query"):
            if attrs.get(key):
                return {"goal": _as_text(attrs[key]), "connector": source_type}
        for child in record.get("spans") or []:
            child_attrs = _attributes(child)
            for key in ("review.goal", "llm.input.prompt", "input.prompt", "prompt", "query"):
                if child_attrs.get(key):
                    return {"goal": _as_text(child_attrs[key]), "connector": source_type}
    for key in ("name", "operation_name", "span_name"):
        if record.get(key):
            return {"goal": f"Review output from {record[key]}", "connector": source_type}
    return {"goal": f"Review {source_type} trace {index + 1}", "connector": source_type}


def _outputs_from_record(record: Any, source_type: str) -> list[Any]:
    if not isinstance(record, dict):
        return [record]
    outputs = []
    for key in ("output", "outputs", "result", "response", "completion"):
        if key in record:
            outputs.extend(_flatten_outputs(record[key]))
    if source_type in {"langchain", "langsmith"}:
        outputs.extend(_langsmith_outputs(record))
    if source_type in {"llamaindex", "llama-index"}:
        outputs.extend(_llamaindex_outputs(record))
    if source_type in {"weave", "wandb-weave", "w&b-weave"}:
        outputs.extend(_weave_outputs(record))
    if source_type in {"opentelemetry", "otel"}:
        outputs.extend(_otel_outputs(record))
    if source_type == "noveum":
        outputs.extend(_noveum_outputs(record))
    if source_type in {"vllm", "huggingface", "huggingface-endpoint", "hf"}:
        outputs.extend(_inference_outputs(record))
    for child_key in ("child_runs", "children", "spans", "calls"):
        for child in record.get(child_key) or []:
            outputs.extend(_outputs_from_record(child, source_type))
    return _unique_outputs(outputs)


def _langsmith_outputs(record: dict[str, Any]) -> list[Any]:
    outputs = []
    raw = record.get("outputs") or {}
    if isinstance(raw, dict):
        for key in ("output", "result", "text", "generations"):
            if key in raw:
                outputs.extend(_flatten_outputs(raw[key]))
    return outputs


def _weave_outputs(record: dict[str, Any]) -> list[Any]:
    outputs = []
    summary = record.get("summary") or {}
    if isinstance(summary, dict):
        outputs.extend(_flatten_outputs(summary.get("output")))
    return outputs


def _llamaindex_outputs(record: dict[str, Any]) -> list[Any]:
    outputs = []
    for key in ("response", "response_text", "completion", "output", "text"):
        if key in record:
            outputs.extend(_flatten_outputs(record[key]))
    event = record.get("event") or record.get("payload") or {}
    if isinstance(event, dict):
        for key in ("response", "response_text", "output", "text"):
            if key in event:
                outputs.extend(_flatten_outputs(event[key]))
    return outputs


def _inference_outputs(record: dict[str, Any]) -> list[Any]:
    outputs = []
    for key in ("generated_text", "text", "output_text", "completion", "response", "choices", "outputs"):
        if key in record:
            outputs.extend(_flatten_outputs(record[key]))
    if "results" in record:
        outputs.extend(_flatten_outputs(record["results"]))
    return outputs


def _otel_outputs(record: dict[str, Any]) -> list[Any]:
    attrs = _attributes(record)
    outputs = []
    for key, value in attrs.items():
        normalized_key = key.replace(".", "_").lower()
        if any(token in normalized_key for token in ("response", "completion", "output")):
            outputs.extend(_flatten_outputs(value))
    return outputs


def _noveum_outputs(record: dict[str, Any]) -> list[Any]:
    attrs = _attributes(record)
    outputs = []
    for key, value in attrs.items():
        normalized_key = key.replace(".", "_").lower()
        if any(token in normalized_key for token in ("llm_output", "response", "completion", "output")):
            outputs.extend(_flatten_outputs(value))
    return outputs


def _flatten_outputs(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        output = []
        for item in value:
            output.extend(_flatten_outputs(item))
        return output
    if isinstance(value, dict):
        for key in ("text", "content", "output", "message", "completion", "result", "generated_text", "response_text"):
            if key in value:
                return _flatten_outputs(value[key])
        if "choices" in value:
            return _flatten_outputs(value["choices"])
        if "generations" in value:
            return _flatten_outputs(value["generations"])
        return [value]
    return [value]


def _attributes(record: dict[str, Any]) -> dict[str, Any]:
    attrs = record.get("attributes") or {}
    if isinstance(attrs, dict):
        return attrs
    if isinstance(attrs, list):
        output = {}
        for item in attrs:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            value = item.get("value")
            if not key:
                continue
            output[key] = _otel_value(value)
        return output
    return {}


def _otel_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if key in value:
            return value[key]
    if "arrayValue" in value:
        values = value["arrayValue"].get("values") or []
        return [_otel_value(item) for item in values]
    if "kvlistValue" in value:
        return {item.get("key"): _otel_value(item.get("value")) for item in value["kvlistValue"].get("values") or []}
    return value


def _otel_spans(payload: dict[str, Any]) -> list[dict[str, Any]]:
    spans = []
    for resource in payload.get("resourceSpans") or []:
        for scope in resource.get("scopeSpans") or []:
            spans.extend(scope.get("spans") or [])
    return spans


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(_as_text(item) for item in value if _as_text(item)).strip()
    if isinstance(value, dict):
        for key in ("content", "text", "output", "result", "message"):
            if key in value:
                return _as_text(value[key])
        return json.dumps(value, sort_keys=True)
    return str(value).strip()


def _unique_outputs(outputs: list[Any]) -> list[Any]:
    unique = []
    seen = set()
    for output in outputs:
        text = _as_text(output)
        if text and text not in seen:
            seen.add(text)
            unique.append(output)
    return unique


def _generator_from_record(record: dict[str, Any], source_type: str) -> str:
    if source_type == "noveum":
        attrs = _attributes(record)
        for key in ("llm.model", "llm.model_name", "model", "model_name", "llm.provider"):
            if attrs.get(key):
                return str(attrs[key])
        for child in record.get("spans") or []:
            child_attrs = _attributes(child)
            for key in ("llm.model", "llm.model_name", "model", "model_name", "llm.provider"):
                if child_attrs.get(key):
                    return str(child_attrs[key])
    for key in ("model", "model_name", "serialized", "name", "operation_name", "provider"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict) and value.get("name"):
            return str(value["name"])
    attrs = _attributes(record)
    for key in ("gen_ai.request.model", "gen_ai.response.model", "llm.model", "llm.model_name", "model", "model_name"):
        if attrs.get(key):
            return str(attrs[key])
    return source_type


def _trace_id(record: Any) -> str:
    if not isinstance(record, dict):
        return ""
    for key in ("id", "run_id", "trace_id", "span_id", "spanId"):
        if record.get(key):
            return str(record[key])
    return ""
