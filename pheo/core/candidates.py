from __future__ import annotations

from typing import Any


def normalize_candidates(candidates: list[Any]) -> list[dict[str, Any]]:
    normalized = []
    for index, candidate in enumerate(candidates or []):
        if isinstance(candidate, dict):
            output = str(candidate.get("output") or candidate.get("text") or "").strip()
            if output:
                normalized.append(
                    {
                        "index": index,
                        "output": output,
                        "generator": candidate.get("generator") or candidate.get("model") or "external",
                        "metadata": candidate.get("metadata") or {},
                    }
                )
        elif str(candidate).strip():
            normalized.append({"index": index, "output": str(candidate).strip(), "generator": "external", "metadata": {}})
    return normalized


__all__ = ["normalize_candidates"]
