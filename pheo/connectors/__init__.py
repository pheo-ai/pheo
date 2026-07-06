from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pheo.core.traces import normalize_trace_runs


@dataclass
class ObservationInput:
    review_point: str
    output: str
    context: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    candidates: list[dict[str, Any]] = field(default_factory=list)


class InputConnector(Protocol):
    def observations(self) -> list[ObservationInput]:
        ...


class JsonlConnector:
    def __init__(self, path: str | Path, review_point: str):
        self.path = Path(path)
        self.review_point = review_point

    def observations(self) -> list[ObservationInput]:
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(_observation_from_dict(json.loads(line), self.review_point, "jsonl"))
        return rows


class TraceConnector:
    def __init__(self, source_type: str, payload: Any, review_point: str):
        self.source_type = source_type
        self.payload = payload
        self.review_point = review_point

    def observations(self) -> list[ObservationInput]:
        observations = []
        for spec in normalize_trace_runs(self.source_type, self.payload):
            candidates = spec.get("candidates") or []
            if not candidates:
                continue
            observations.append(
                ObservationInput(
                    review_point=self.review_point,
                    output=candidates[0].get("output", ""),
                    context=spec.get("task") or {},
                    source={"connector": self.source_type},
                    candidates=candidates,
                )
            )
        return observations


class LangChainConnector(TraceConnector):
    def __init__(self, payload: Any, review_point: str):
        super().__init__("langchain", payload, review_point)


class LangSmithConnector(TraceConnector):
    def __init__(self, payload: Any, review_point: str):
        super().__init__("langsmith", payload, review_point)


class LlamaIndexConnector(TraceConnector):
    def __init__(self, payload: Any, review_point: str):
        super().__init__("llamaindex", payload, review_point)


class WeaveConnector(TraceConnector):
    def __init__(self, payload: Any, review_point: str):
        super().__init__("weave", payload, review_point)


class NoveumConnector(TraceConnector):
    def __init__(self, payload: Any, review_point: str):
        super().__init__("noveum", payload, review_point)


class OpenTelemetryConnector(TraceConnector):
    def __init__(self, payload: Any, review_point: str):
        super().__init__("opentelemetry", payload, review_point)


class VllmConnector(TraceConnector):
    def __init__(self, payload: Any, review_point: str):
        super().__init__("vllm", payload, review_point)


class HuggingFaceConnector(TraceConnector):
    def __init__(self, payload: Any, review_point: str):
        super().__init__("huggingface", payload, review_point)


def _observation_from_dict(row: dict[str, Any], review_point: str, connector: str) -> ObservationInput:
    output = row.get("output") or row.get("text") or row.get("result") or ""
    return ObservationInput(
        review_point=row.get("review_point") or review_point,
        output=output,
        context=row.get("context") or row.get("task") or {},
        source={"connector": connector, **(row.get("source") or {})},
        candidates=row.get("candidates") or [],
    )


__all__ = [
    "InputConnector",
    "ObservationInput",
    "JsonlConnector",
    "TraceConnector",
    "LangChainConnector",
    "LangSmithConnector",
    "LlamaIndexConnector",
    "WeaveConnector",
    "NoveumConnector",
    "OpenTelemetryConnector",
    "VllmConnector",
    "HuggingFaceConnector",
]
