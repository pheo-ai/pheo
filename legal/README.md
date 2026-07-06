# Legal Documents

| Document | Purpose |
|----------|---------|
| [pheo-contributor-agreement.md](pheo-contributor-agreement.md) | Required for non-trivial code contributions |
| [KERNEL_LICENSE.md](KERNEL_LICENSE.md) | Terms for compiled kernel binaries in official packages |
| [../COMMERCIAL_LICENSE.md](../COMMERCIAL_LICENSE.md) | Summary of open harness vs kernel commercial model |
| [../TRADEMARK.md](../TRADEMARK.md) | Trademark use policy |

## Contributor Agreement

Before opening a code PR:

1. Read [pheo-contributor-agreement.md](pheo-contributor-agreement.md)
2. Comment on your PR: `I have read and agree to the Pheo Contributor Agreement v1.0`

Enterprise contributors may request a PDF signature workflow via **legal@pheo.ai**.

## Regenerate PDF (maintainers)

If `build-contributor-agreement-pdf.py` is present:

```bash
python3.13 legal/build-contributor-agreement-pdf.py
```

Do not commit contributor signatures or personally identifiable information to the public repository.

## Kernel Binaries

Compiled artifacts in `pheo_kernels/` are **not** MIT-licensed. See [KERNEL_LICENSE.md](KERNEL_LICENSE.md).

## Questions

Email **legal@pheo.ai**.
