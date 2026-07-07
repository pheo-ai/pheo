# Kernel Boundary

Pheo is a two-layer product: an **open harness** and a **compiled kernel runtime**.

This page defines what is open, what is not, and which contributions are welcome.

## Architecture

```text
┌─────────────────────────────────────────────────────────┐
│  OPEN HARNESS (MIT, this repository)                    │
│  SDK · CLI · REST · MCP · UI · SQLite store · exports   │
│  integrations · connectors · examples · tests           │
└───────────────────────────┬─────────────────────────────┘
                            │ stable protocol
                            ▼
┌─────────────────────────────────────────────────────────┐
│  COMPILED KERNEL (separate license, binary only)        │
│  methodology synthesis · branching · scoring · ranking    │
└─────────────────────────────────────────────────────────┘
```

The harness calls the kernel through `pheo.kernels.runtime.PheoKernelRuntime`:

- `synthesize_methodology(...)`
- `branch_candidates(...)`
- `score_candidates(...)`

Application and contributor code should use the SDK, CLI, MCP, or REST surfaces — not reimplement kernel behavior in the harness.

## Open in This Repository

| Area | Location | Contribution welcome |
|------|----------|---------------------|
| SDK | `pheo/sdk.py` | Yes |
| CLI | `pheo/cli.py` | Yes |
| REST API | `pheo/api.py`, `openapi.json` | Yes |
| MCP | `pheo/mcp.py` | Yes |
| Local UI | `pheo/ui/` | Yes |
| Storage | `pheo/storage/` | Yes |
| Export / memory pack assembly | `pheo/core/memory.py`, SDK export paths | Yes, if not duplicating kernel scoring |
| Integrations | `pheo/integrations/` | Yes |
| Trace connectors | `pheo/core/traces.py` | Yes |
| Examples | `examples/` | Yes |
| Patterns / docs | `patterns/`, `*.md` | Yes |
| Tests | `tests/` | Yes |
| Kernel loader | `pheo/kernels/runtime.py`, `pheo_kernels/__init__.py` | Interface fixes only |

## Not Open (Binary Kernel)

Shipped as compiled artifacts in `pheo_kernels/`:

- `_runtime.pyc`
- `_bundle/*.pyc`

These implement:

- methodology synthesis from corpus material
- candidate branching from observed output
- multi-dimensional candidate scoring and ranking
- kernel-side review signals used before human judgment

**Kernel source is not published.** Do not submit PRs that reimplement these algorithms in the open harness.

## Gray Area (Harness Logic That Is Open)

Some post-kernel orchestration is intentionally open:

- judgment memory compilation and application (`pheo/core/memory.py`)
- release receipts, preference tuples/pairs, training manifest assembly
- workflow storage, review capture, export formatting

These are harness responsibilities. Changes should preserve the kernel boundary and must not replace kernel scoring or branching.

## Pull Requests We Want

- New connectors (trace sources, sinks, notification channels)
- Documentation, examples, and marketplace templates
- SDK/CLI/API ergonomics and bug fixes
- Tests for harness behavior and export schemas
- Deployment and packaging improvements

## Pull Requests We Will Decline

- Public reimplementations of kernel scoring, branching, or methodology synthesis
- Changes that bypass human review gates or release receipts
- Storing customer API keys in the Pheo Data Store
- Adding Pheo-owned LLM calls

## Enterprise / Custom Kernels

Commercial support, enterprise terms, and custom domain kernels are handled by Pheo Inc. See [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md).

## Questions

Open a [Question issue](https://github.com/pheo-ai/pheo/issues/new?template=question.yml) or email **apprentice@pheo.ai** for boundary clarifications before large PRs.
