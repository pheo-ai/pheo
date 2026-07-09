# Attach PHEO Grow To Coding Agents

Use this pattern when Codex, Claude Code, Cursor, or another coding agent already produces a final answer, patch summary, trace, or merge recommendation.

PHEO does not replace the coding tool. It attaches after the tool proposes work.

```text
coding agent proposes work
  -> PHEO observes the output
  -> PHEO branches and scores alternatives
  -> maintainer approves, edits, rejects, or escalates
  -> decision becomes receipt + preference data
  -> next similar coding-agent output gets prior judgment memory
```

## Quick Demo

```bash
pheo demo code-agent --reset
```

## Codex

Use PHEO as the review boundary after Codex produces an implementation summary or patch.

```bash
pheo store create \
  --name code_agent_review \
  --business-area software_development \
  --goal "Review coding-agent outputs before accepting them as project guidance or merge-ready work."

pheo source add \
  --store code_agent_review \
  AGENTS.md CONTRIBUTING.md

pheo methodology review --workflow code_agent_review --format human
pheo methodology approve --workflow code_agent_review --author maintainer@example.com

pheo review-point add \
  --store code_agent_review \
  --name code_agent_output_review \
  --description "Review final coding-agent output before accepting it." \
  --dimension "test evidence" \
  --dimension "scope control" \
  --dimension "risk handling" \
  --dimension "release clarity"
```

Then observe a final answer or patch summary:

```bash
pheo observe output \
  --review-point code_agent_output_review \
  --output "Implemented parser behavior change. No tests were added." \
  --context '{"task":"Fix parser escaped delimiters","files_changed":["src/parser.py"],"test_evidence":"not provided"}' \
  --source '{"connector":"codex","cycle_id":"cycle_1","case_id":"parser-no-tests"}'
```

Open the local review UI:

```bash
pheo start --store code_agent_review
```

## Claude Code

Claude Code can use PHEO through MCP and hooks.

Example `.mcp.json`:

```json
{
  "mcpServers": {
    "pheo": {
      "command": "pheo",
      "args": ["mcp"]
    }
  }
}
```

Example hook shape:

```bash
#!/usr/bin/env bash
set -euo pipefail

payload_file="${1:-}"
final_text="$(jq -r '.transcript // .summary // .message // empty' "$payload_file")"

pheo observe output \
  --review-point code_agent_output_review \
  --output "$final_text" \
  --context "$(jq -c '{task, cwd, files_changed, test_evidence}' "$payload_file")" \
  --source '{"connector":"claude_code","cycle_id":"cycle_1"}'
```

Keep this in your own project hooks, not inside PHEO. PHEO only needs the final output plus enough context to review it.

## Cursor

Cursor users can use the same CLI or MCP path:

1. Add repo rules as source material.
2. Create `code_agent_output_review`.
3. Observe final assistant output, trace export, or patch summary.
4. Review in the local PHEO UI.
5. Export the memory pack.

## What PHEO Stores

- source snapshot active during review
- observed coding-agent output
- generated candidates and scores
- maintainer action and reason
- release receipt
- preference tuple and pairs
- workflow memory for the next similar case

Raw agent output is never treated as released project guidance until a reviewer captures a decision.
