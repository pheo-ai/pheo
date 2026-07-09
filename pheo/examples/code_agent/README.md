# Code Agent Demo

Attach PHEO Grow after a coding agent has produced a final answer, diff, or merge recommendation.

```bash
pheo demo code-agent --reset
```

The demo does not run Codex, Claude Code, or Cursor. It simulates the output those tools already produce, then shows the PHEO loop:

```text
coding-agent output
  -> PHEO observe
  -> branch and score
  -> human judgment with reason
  -> release receipt + preference tuple
  -> workflow memory
  -> Cycle 2 suggestion from prior judgment
```

This is the attachment point for coding tools: the agent keeps doing the work, and PHEO governs what becomes accepted project memory.
