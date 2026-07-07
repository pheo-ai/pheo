# Contributing to Pheo

Thank you for helping improve Pheo.

## Before You Start

1. Read [docs/kernel-boundary.md](docs/kernel-boundary.md) — know what belongs in the open harness.
2. Read [docs/agents.md](docs/agents.md) — understand the product loop and integration rules.
3. For non-trivial code changes, complete the [Contributor Agreement](legal/pheo-contributor-agreement.md) **before** we merge your PR.

## Contributor License Agreement (Required)

Non-trivial contributions require CLA acceptance:

| Contribution type | CLA required |
|-------------------|--------------|
| Docs, typos, examples | Encouraged but maintainers may merge without formal CLA |
| Code, tests, schemas, packaging, API changes | **Required** |
| New connectors or export formats | **Required** |

### How to Sign

1. Open your pull request.
2. Comment: `I have read and agree to the Pheo Contributor Agreement at legal/pheo-contributor-agreement.md`
3. Include your full name and GitHub username in the comment.

Maintainers may also request a signed PDF for enterprise contributors. See [legal/README.md](legal/README.md).

We plan to automate CLA tracking with CLA Assistant. Until then, maintainers record acceptance in the PR thread.

## Development Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python3.13 -m pip install -e ".[langchain,dev]"
python -m unittest discover -s tests -p 'test_*.py'
```

The compiled kernel runtime is bundled in `pheo_kernels/`. Do not add public reference implementations for scoring, branching, or methodology synthesis.

## Pull Request Guidelines

- Keep Pheo as an attach layer; do not rebuild agent frameworks inside Pheo.
- Keep raw observed output separate from reviewed/released output.
- Preserve local data custody by default.
- Do not add a Pheo-owned LLM call.
- Do not store API keys in the Pheo Data Store.
- Add or update tests for SDK, CLI, export, and connector behavior.
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes.

## What We Welcome

See [docs/kernel-boundary.md](docs/kernel-boundary.md#pull-requests-we-want).

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Report issues to **apprentice@pheo.ai**.

## License

By contributing, you agree that accepted contributions may be distributed under the MIT License and that Pheo Inc. may also use them in the compiled kernel and commercial offerings per the Contributor Agreement.
