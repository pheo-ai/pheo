# Pattern: Agent-Driven Setup With MCP

Use this when Claude Code, Cursor, Codex, Copilot, or another coding agent should add Pheo to a repo.

Give the agent this instruction:

```text
Read docs/agents.md. Add Pheo review and export to this existing workflow.
Do not rebuild the app inside Pheo.
Use the current workflow's source material, create a review point where the AI output is produced, keep human review required, and export memory after decisions.
```

Agent checklist:

1. Create or select a Pheo Data Store with a clear `goal`.
2. Add source material such as policy, SOP, examples, or review criteria.
3. Draft review rules and show them to the human.
4. Approve, edit, or reject the rules before observing outputs.
5. Create the review point.
6. Observe one output from the existing workflow.
7. Capture a human approve/edit/reject/escalate decision with a reason.
8. Export the memory pack, preferably with `--organic-only` for human-derived review memory.

The agent should not add a Pheo-owned model call or store API keys in the Pheo Data Store.
