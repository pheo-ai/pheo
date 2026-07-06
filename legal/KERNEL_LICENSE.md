# Kernel License

Copyright (c) 2026 Pheo Inc. All rights reserved.

This document governs the **compiled Pheo kernel runtime** distributed inside official `pheo` Python packages. It applies to binary artifacts under `pheo_kernels/`, including `_runtime.pyc` and `_bundle/*.pyc`.

## 1. Grant of Use

Pheo Inc. grants you a non-exclusive, non-transferable license to:

- install official `pheo` packages from TestPyPI, PyPI, or Pheo Inc.
- execute the bundled kernel runtime as part of the Pheo product
- use the kernel output (scores, candidates, methodology drafts) within your workflows subject to your own compliance requirements

This grant is included when you install an official package from Pheo Inc. No separate kernel download is required. The license continues until terminated for breach.

## 2. Restrictions

Except where applicable law gives you rights that cannot be waived, you may not:

- copy, modify, adapt, translate, or create derivative works of the kernel binaries
- reverse engineer, decompile, disassemble, or attempt to derive source code from the kernel binaries
- redistribute the kernel binaries separately from an official `pheo` package
- use the kernel binaries to build a competing scoring, branching, or review-engine product
- remove or alter proprietary notices embedded in official packages

## 3. Open Harness vs Kernel

Source code in this repository outside `pheo_kernels/*.pyc` is licensed under the [MIT License](../LICENSE).

The MIT License does **not** apply to the compiled kernel binaries.

## 4. Redistribution of Official Packages

You may redistribute official `pheo` wheels and source distributions unmodified, provided you include:

- `LICENSE`
- this file
- `COMMERCIAL_LICENSE.md`

Do not represent modified packages as official Pheo releases.

## 5. Commercial and Enterprise Terms

Commercial support, enterprise deployment, custom domain kernels, SLA-backed releases, and managed rollout are available under separate agreement with Pheo Inc.

Contact: **legal@pheo.ai**

## 6. Disclaimer

THE KERNEL RUNTIME IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

## 7. Termination

This license terminates automatically if you breach its terms. Upon termination, you must stop using and delete copies of the kernel binaries except where retention is required by law.

## 8. Governing Law

This license is governed by the laws of the State of Delaware, USA, excluding conflict-of-law rules.

---

For trademark use, see [TRADEMARK.md](../TRADEMARK.md).

For contribution terms, see [legal/pheo-contributor-agreement.md](pheo-contributor-agreement.md).
