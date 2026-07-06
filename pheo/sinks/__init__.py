from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class Sink(Protocol):
    def write_pack(self, pack: dict[str, Any]) -> None:
        ...


class LocalFolderSink:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def write_pack(self, pack: dict[str, Any]) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "memory_pack.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
        (self.path / "workflow.graph.json").write_text(json.dumps(pack.get("workflow_graph") or {}, indent=2), encoding="utf-8")
        _write_jsonl(self.path / "observations.jsonl", pack["artifacts"].get("observations") or [])
        _write_jsonl(self.path / "decisions.jsonl", pack["artifacts"].get("decision_log") or [])
        _write_jsonl(self.path / "preference_tuples.jsonl", pack["artifacts"].get("preference_tuples") or [])
        _write_jsonl(self.path / "preference_pairs.jsonl", pack["artifacts"].get("preference_pairs") or [])
        _write_jsonl(self.path / "sft.jsonl", pack["artifacts"].get("sft_jsonl") or [])
        _write_jsonl(self.path / "dpo.jsonl", pack["artifacts"].get("dpo_jsonl") or [])
        _write_jsonl(self.path / "review_examples.jsonl", pack["artifacts"].get("review_examples") or [])
        _write_jsonl(self.path / "release_receipts.jsonl", pack["artifacts"].get("release_receipts") or [])
        _write_jsonl(self.path / "check_cases.jsonl", pack["artifacts"].get("check_cases") or [])
        _write_jsonl(self.path / "quality_scores.jsonl", pack["artifacts"].get("candidate_quality") or [])
        _write_jsonl(self.path / "methodology_events.jsonl", pack["artifacts"].get("methodology_events") or [])
        (self.path / "judgment_memory.json").write_text(json.dumps(pack["artifacts"].get("judgment_memory") or {}, indent=2), encoding="utf-8")
        (self.path / "training_manifest.json").write_text(json.dumps(pack["artifacts"].get("training_manifest") or {}, indent=2), encoding="utf-8")
        (self.path / "cycle_diff.json").write_text(json.dumps(pack["artifacts"].get("cycle_diff") or {}, indent=2), encoding="utf-8")


class CustomerControlledSink:
    """Template hook for customer-owned export destinations.

    The public package writes memory packs to local folders. S3, GCS, warehouse,
    database, and webhook delivery should be implemented as customer or
    enterprise adapters that satisfy the Sink protocol.
    """

    def __init__(self, uri: str):
        self.uri = uri

    def write_pack(self, pack: dict[str, Any]) -> None:
        raise NotImplementedError(
            "Customer-controlled remote sinks are adapter hooks, not built-in public "
            "connectors. Provide a Sink adapter for your S3, GCS, Postgres, warehouse, "
            "or webhook destination."
        )


def sink_for(uri: str | Path) -> Sink:
    value = str(uri)
    if value.startswith(("s3://", "gs://", "postgres://", "postgresql://", "https://", "http://")):
        return CustomerControlledSink(value)
    return LocalFolderSink(value)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


__all__ = ["Sink", "LocalFolderSink", "CustomerControlledSink", "sink_for"]
