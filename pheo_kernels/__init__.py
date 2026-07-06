from __future__ import annotations

try:
    from ._runtime import KernelRuntime  # type: ignore
except ImportError as exc:  # pragma: no cover - exercised by broken package installs
    raise RuntimeError(
        "The bundled Pheo kernel runtime is missing or incompatible with this Python version. "
        "Install a supported Pheo wheel that includes pheo_kernels."
    ) from exc


__all__ = ["KernelRuntime"]
