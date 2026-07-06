# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.13] - 2026-07-05

### Added

- Public harness repository structure (SDK, CLI, REST, MCP, local UI)
- Bundled compiled kernel runtime (`pheo_kernels/_runtime.pyc`, `_bundle/` artifacts)
- Finance exception example and preference-factory proof script
- LangChain attach integration and trace import adapters
- Memory pack export: DPO, SFT, preference pairs/tuples, release receipts, training manifest
- Marketplace workflow templates in local UI
- OpenAPI spec and headless review capture via CLI/API

### Changed

- Compiled kernel runtime requires Python 3.13 for v0.1.13
- TestPyPI install requires PyPI as extra index for optional dependencies

### Security

- Local data custody by default; no Pheo-owned LLM calls
- Methodology approval gate before observe/score workflows

## [Unreleased]

### Planned

- PyPI stable release promotion process
- CLA Assistant automation for external contributors
- Additional marketplace templates

[0.1.13]: https://github.com/pheo-ai/pheo/releases/tag/v0.1.13
