from __future__ import annotations

from typing import Any, Protocol


class PheoKernelRuntime(Protocol):
    name: str

    def synthesize_methodology(self, workflow: dict[str, Any], corpus_items: list[dict[str, Any]]) -> dict[str, Any]:
        ...

    def branch_candidates(self, anchor: str, task: dict[str, Any], methodology: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        ...

    def score_candidates(
        self,
        candidates: list[dict[str, Any]],
        task: dict[str, Any],
        corpus_texts: list[str],
        methodology: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        ...


def _load_runtime() -> PheoKernelRuntime:
    try:
        from pheo_kernels import KernelRuntime  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Pheo requires its bundled compiled kernel runtime. Install a supported Pheo wheel "
            "that includes pheo_kernels before running runtime workflows."
        ) from exc
    return KernelRuntime()


kernel_runtime = _load_runtime()


__all__ = ["PheoKernelRuntime", "kernel_runtime"]
