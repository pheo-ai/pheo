# PHEO Platform Harness

Developer/tester harness for hardening PHEO before design-partner runs.

It checks the platform as a loop, not as isolated unit tests:

1. **Kernel runtime**: bundled kernel imports, synthesizes methodology, branches, and scores.
2. **PHEO Go**: workflows ingest source material and approve methodology with onboarding seed data.
3. **Isolation**: medical and finance workflows do not share corpus, packets, decisions, or human pairs.
4. **PHEO Grow**: observed items are branched/scored and blocked before release.
5. **PHEO Govern**: multiple human reviews create decisions, tuples, preference pairs, and release receipts.
6. **Retry safety**: double-submitting a reviewed packet returns the original result instead of duplicating training rows.
7. **Cycle 2**: compiled judgment memory is applied to a similar next case.
8. **Persistence**: reopening the same project hydrates packets, decisions, and memory.
9. **Count taxonomy**: seed rule rows and human rows add up and remain distinguishable.
10. **Export**: organic memory pack contains receipts, tuples, pairs, graph, and judgment memory.
11. **UI smoke**: optional local server E2E checks home, review, and workflow data routes.
12. **Wheel smoke**: optional clean install from a built wheel verifies packaged kernels and CLI.

Run a baseline smoke:

```bash
python3.13 scripts/platform_harness.py \
  --project /private/tmp/pheo-platform-harness-smoke \
  --reset \
  --stress 1
```

Run a heavier local pass:

```bash
python3.13 scripts/platform_harness.py \
  --project /private/tmp/pheo-platform-harness-stress \
  --reset \
  --stress 25 \
  --review-count 10 \
  --ui-smoke \
  --wheel-smoke
```

The harness writes a JSON report:

```text
<project>/platform-harness-report.json
```

Use `--stress` to multiply observed cases. Use `--review-count` to force more than one human judgment through Govern. Keep both low for functional debugging; raise them when testing persistence, export size, and latency.
