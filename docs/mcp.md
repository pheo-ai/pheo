# Pheo MCP

Pheo includes a local MCP stdio server so coding agents can set up and use review memory without moving work into a new platform.

Run:

```bash
pheo mcp
```

The MCP server uses the same local project, SQLite database, review gates, and export formats as the SDK and CLI. It does not send data to Pheo and does not require a Pheo-owned model.

## Agent Flow

```text
1. Create or select a Pheo Data Store.
2. Add source material.
3. Draft review rules from the source material.
4. Show the draft methodology to the human.
5. Let the human approve, edit, or reject the methodology.
6. Create a review point.
7. Observe an AI, agent, endpoint, trace, or workflow output.
8. Send the review packet or local review URL to the human.
9. Capture approve/edit/reject/escalate.
10. Export the memory pack.
11. On the next cycle, apply compiled judgment memory before review.
```

Observation and scoring are blocked until review rules are approved. This makes setup-time governance a real gate, not just runtime review.

Captured reviews create release receipts and preference data in the local memory pack. Agents can inspect compiled judgment memory, release receipts, training manifest, and cycle diff through MCP before handing results back to the user.

Score responses include public explanations under `candidate.scores.explanation`, so agents can tell humans why a candidate needs review without exposing private implementation details.

The same normalized trace path supports LangChain, LangSmith, LangGraph runs exported as LangSmith-style records, LlamaIndex, W&B Weave, Noveum trace batches, OpenTelemetry, vLLM, Hugging Face, JSONL batches, REST ingest, and MCP tool calls.

## Tools

### `pheo_create_store`

Create or select a Pheo Data Store.

```json
{
  "name": "ap_invoice_exception_review",
  "business_area": "finance",
  "goal": "Prepare AP invoice exception summaries for human review before any payment-related action is approved.",
  "quality_dimensions": ["evidence support", "approval clarity", "exception risk", "next step"]
}
```

### `pheo_add_source`

Add source text and draft review rules.

```json
{
  "store": "ap_invoice_exception_review",
  "title": "AP policy",
  "text": "Human review is required before an invoice exception is cleared or any payment-related action is approved.",
  "tags": ["policy"]
}
```

### `pheo_draft_methodology`

Regenerate draft review rules from active source material.

```json
{
  "store": "ap_invoice_exception_review",
  "actor": "agent",
  "note": "Drafted after source update."
}
```

### `pheo_review_methodology`

Return the public methodology draft, review goal/protocol, event history, and gate status.

```json
{
  "store": "ap_invoice_exception_review"
}
```

### `pheo_update_methodology`

Edit draft review rules before approval.

```json
{
  "store": "ap_invoice_exception_review",
  "summary": "Review AP invoice exception summaries before payment-related action.",
  "rules": ["Name missing evidence.", "Escalate unclear approval or sensitive items."],
  "avoid": ["Do not imply payment can be approved without human review."],
  "actor": "controller@example.com"
}
```

### `pheo_approve_methodology`

Approve draft review rules. This unlocks observation and scoring.

```json
{
  "store": "ap_invoice_exception_review",
  "actor": "controller@example.com",
  "note": "Rules reviewed for beta test."
}
```

### `pheo_reject_methodology`

Reject draft review rules. The agent must edit or rebuild before approval.

```json
{
  "store": "ap_invoice_exception_review",
  "actor": "controller@example.com",
  "note": "Too broad for this workflow."
}
```

### `pheo_create_review_point`

Create a control point where outputs become governed outcomes.

```json
{
  "store": "ap_invoice_exception_review",
  "name": "ap_exception_review",
  "description": "Review AP invoice exception summaries before clearing or payment-related action.",
  "dimensions": ["evidence support", "approval clarity", "exception risk", "next step"],
  "human_review": "required"
}
```

### `pheo_observe_output`

Observe one AI or workflow output at a review point. Set `use_memory` on later cycles when prior decisions should inform candidate ordering and review context.

```json
{
  "review_point": "ap_exception_review",
  "output": "Invoice AP-1007 can proceed after review.",
  "context": {"invoice_id": "AP-1007", "approval_status": "unclear"},
  "source": {"connector": "mcp_agent", "cycle_id": "cycle_1"},
  "use_memory": false
}
```

### `pheo_add_endpoint_connection`

Register an OpenAI-compatible endpoint for a review point to call through Pheo.

```json
{
  "store": "ap_invoice_exception_review",
  "name": "openrouter",
  "endpoint_url": "https://openrouter.ai/api/v1",
  "model": "openai/gpt-4o-mini",
  "api_key_env": "OPENROUTER_API_KEY"
}
```

### `pheo_observe_endpoint`

Call the configured endpoint, prepare governed candidates, and return a review packet.

```json
{
  "review_point": "ap_exception_review",
  "connection": "openrouter",
  "prompt": "Draft a factual AP invoice exception review note. Do not approve payment.",
  "context": {"invoice_id": "AP-1007", "approval_status": "unclear"}
}
```

### `pheo_capture_review`

Capture the human review decision.

```json
{
  "packet_id": "packet_...",
  "selected_index": 2,
  "action": "edit",
  "reason": "Human added evidence requirement.",
  "corrected_output": "Invoice AP-1007 should be escalated because support is missing and no approver is identified.",
  "author_id": "controller@example.com"
}
```

### `pheo_export_memory`

Export the local memory pack.

```json
{
  "store": "ap_invoice_exception_review",
  "out": "./pack"
}
```

### `pheo_get_memory`

Return compiled judgment memory for a Pheo Data Store.

```json
{
  "store": "ap_invoice_exception_review",
  "organic_only": true
}
```

### `pheo_get_release_receipts`

Return release receipts frozen at review capture.

```json
{
  "store": "ap_invoice_exception_review"
}
```

### `pheo_get_training_manifest`

Return export filters, included rows, excluded rows, and split guidance.

```json
{
  "store": "ap_invoice_exception_review"
}
```

### `pheo_get_cycle_diff`

Compare two source cycles such as `cycle_1` and `cycle_2`.

```json
{
  "store": "ap_invoice_exception_review",
  "before": "cycle_1",
  "after": "cycle_2"
}
```

## Minimal MCP Messages

List tools:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

Call a tool:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "pheo_review_methodology",
    "arguments": {"store": "ap_invoice_exception_review"}
  }
}
```

The response content is JSON text so agents can parse it directly.
