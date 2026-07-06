# Release Process

This document describes how Pheo releases move from source to installable packages.

## Channels

| Channel | Purpose | Audience |
|---------|---------|----------|
| **GitHub `main`** | Source of truth for open harness | Contributors, design partners |
| **TestPyPI** | Pre-release validation | Beta testers |
| **PyPI** | Stable public install | General availability |

## Versioning

Pheo uses [Semantic Versioning](https://semver.org/):

- **MAJOR:** incompatible API or export schema changes
- **MINOR:** backward-compatible features
- **PATCH:** backward-compatible fixes

Update version in:

- `pyproject.toml`
- `setup.cfg`
- `CHANGELOG.md`

Tag releases as `vX.Y.Z` on GitHub.

## Build

From a clean checkout:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python3.13 -m pip install --upgrade pip build twine
python -m build
twine check dist/*
```

The wheel must include:

- `pheo/` harness source
- `pheo_kernels/` loader and compiled `_bundle/` artifacts
- License files listed in `MANIFEST.in`

## TestPyPI (Beta)

```bash
twine upload --repository testpypi dist/*
```

Beta install command (document this in README):

```bash
python3.13 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "pheo[langchain]==X.Y.Z"
```

**Why two indexes:** TestPyPI hosts the `pheo` wheel; dependencies such as `langchain-core` come from PyPI.

Validate before announcing:

```bash
python3.13 -m pip install -e ".[langchain,dev]"
python -m unittest discover -s tests -p 'test_*.py'
python examples/finance_exception/run_preference_factory.py \
  --project /tmp/pheo-release-check \
  --out /tmp/pheo-release-check-pack
```

## PyPI (Stable)

After TestPyPI validation and design-partner sign-off:

```bash
twine upload dist/*
```

Stable install:

```bash
python3.13 -m pip install "pheo[langchain]"
```

## Signed Releases

GitHub Releases should attach:

- Source distribution (`*.tar.gz`)
- Wheel (`*.whl`)
- `SHA256SUMS` file for artifact verification

Generate checksums:

```bash
shasum -a 256 dist/* > SHA256SUMS
```

## Kernel Updates

Kernel binary updates ship inside the wheel. Kernel source is not published in this repository. See [kernel-boundary.md](kernel-boundary.md).

## Rollback

If a release is bad:

1. Yank the TestPyPI/PyPI version (`twine yank` or PyPI web UI)
2. Publish a patched version
3. Document in `CHANGELOG.md` and GitHub Security Advisories if applicable
