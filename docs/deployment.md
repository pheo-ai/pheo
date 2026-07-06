# Deployment Notes

Pheo is an MIT-licensed harness that ships with a bundled compiled kernel runtime under [legal/KERNEL_LICENSE.md](legal/KERNEL_LICENSE.md).

## Install (Beta — TestPyPI)

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python3.13 -m pip install --upgrade pip
python3.13 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "pheo[langchain]==0.1.0"
pheo init
```

**Why two indexes:** TestPyPI hosts the `pheo` wheel. Dependencies such as `langchain-core` are resolved from PyPI.

## Install (Stable — PyPI, when available)

```bash
python3.13 -m pip install "pheo[langchain]"
```

## Install (From Source — Contributors)

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python3.13 -m pip install -e ".[langchain,dev]"
pheo init
```

Application code imports only `pheo`.

## Python Versions

Supported for **v0.1.0**: **3.13 only**.

The bundled compiled kernel (`pheo_kernels/_runtime.pyc`) ships as a CPython 3.13 bytecode artifact. Older Python versions fail at import with a kernel compatibility error. Broader Python support requires additional kernel builds in a future release.

## Local Run

```bash
pheo start --store your_workflow
```

Default UI: `http://127.0.0.1:8787`

Headless workflows use CLI, SDK, REST, or MCP — no browser required.

## Data Custody

By default:

- project data lives in local SQLite (`.pheo/` or configured project path)
- exports are JSON/JSONL memory packs on disk
- customer LLM API keys stay in environment variables

Pheo does not call a Pheo-owned LLM.

## Production Considerations

| Topic | Guidance |
|-------|----------|
| **Secrets** | Keep API keys in env vars or secret managers; never commit them |
| **Backups** | Back up project SQLite and export directories |
| **Upgrades** | Pin package version; read [CHANGELOG.md](CHANGELOG.md) before upgrading |
| **Kernel updates** | Ship with official wheels only; do not mix kernel binaries across versions |
| **Enterprise** | Contact Pheo Inc. for commercial support and custom kernels |

## Release Process

See [docs/release.md](release.md).

## Kernel Boundary

See [docs/kernel-boundary.md](docs/kernel-boundary.md).
