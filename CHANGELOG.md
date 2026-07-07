# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.4] - 2026-07-07

### Fixed

- Publish workflow skips TestPyPI uploads when a version already exists (release retriggers no longer fail)

### Changed

- Public contact email unified to `apprentice@pheo.ai`
- GitHub Actions: `actions/checkout@v7`, `actions/setup-python@v6`

## [0.1.3] - 2026-07-06

### Fixed

- Marketplace and workflow re-entry resume onboarding state instead of forcing PHEO Go
- Corpus attach no longer supersedes approved methodology unless explicitly rebuilt
- Review queue refreshes after capture and shows reviewed status with decision metadata
- Grow tab re-fetches preference-store when reopened or when review completes in another tab

### Changed

- `force_new` on workflow create now creates a distinct workflow record
- Session remembers the active workflow across page reload via `sessionStorage`

## [0.1.2] - 2026-07-06

### Fixed

- `pheo --project /path` now defaults to `start` (opens UI without explicit subcommand)

## [0.1.1] - 2026-07-06

### Fixed

- CLI accepts `--project` after subcommands (e.g. `pheo store list --project /path`)
- Restored `deactivate_workflow_corpus` used by SDK `clear_corpus`
- Aligned package `__version__` with published metadata
- Publish workflow grants `contents: read` for private-repo checkout

### Changed

- README adds a 60-second try path (`pheo init` → `pheo` → bundled demo)

## [0.1.0] - 2026-07-06

### Added

- Public harness repository structure (SDK, CLI, REST, MCP, local UI)
- Bundled compiled kernel runtime (`pheo_kernels/_runtime.pyc`, `_bundle/` artifacts)
- Finance exception example and preference-factory proof script
- LangChain attach integration and trace import adapters
- Memory pack export: DPO, SFT, preference pairs/tuples, release receipts, training manifest
- Marketplace workflow templates in local UI
- OpenAPI spec and headless review capture via CLI/API

### Changed

- Compiled kernel runtime requires Python 3.13 for v0.1.0
- TestPyPI install requires PyPI as extra index for optional dependencies

### Security

- Local data custody by default; no Pheo-owned LLM calls
- Methodology approval gate before observe/score workflows

## [Unreleased]

### Planned

- PyPI stable release promotion process
- CLA Assistant automation for external contributors
- Additional marketplace templates

[0.1.4]: https://github.com/pheo-ai/pheo/releases/tag/v0.1.4
[0.1.3]: https://github.com/pheo-ai/pheo/releases/tag/v0.1.3
[0.1.2]: https://github.com/pheo-ai/pheo/releases/tag/v0.1.2
[0.1.1]: https://github.com/pheo-ai/pheo/releases/tag/v0.1.1
[0.1.0]: https://github.com/pheo-ai/pheo/releases/tag/v0.1.0
