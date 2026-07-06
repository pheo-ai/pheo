# Pattern: Observe An OpenAI-Compatible Endpoint

Use this when the existing workflow calls OpenAI, OpenRouter, vLLM, or another OpenAI-compatible endpoint.

The API key stays in the local environment. Pheo stores the observed output, candidates, scores, review packet, and human judgment.

```bash
export OPENROUTER_API_KEY="..."

pheo connection add \
  --store ap_invoice_exception_review \
  --name openrouter \
  --type openai-compatible-endpoint \
  --endpoint-url https://openrouter.ai/api/v1 \
  --model openai/gpt-4o-mini \
  --api-key-env OPENROUTER_API_KEY

pheo observe endpoint \
  --review-point ap_exception_review \
  --connection openrouter \
  --context '{"invoice_id":"AP-1007","vendor":"Northstar Office Supplies","amount":"8420","approval_status":"Unclear - no approver identified"}' \
  --prompt "Draft a factual AP invoice exception review note. Do not approve payment. Do not clear the exception."
```

Every endpoint observation returns a pending review packet. Capture the reviewer decision through the local UI, CLI, REST API, or MCP.
