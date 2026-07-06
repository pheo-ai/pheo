# Getting Started

This guide is for a developer, platform engineer, or coding agent testing Pheo locally.

For agent-led integration into an existing repo, start with [agents.md](agents.md). For copy-paste implementation recipes, see the [`patterns/`](../patterns/) directory.

## 1. Install

Beta install from TestPyPI:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python3.13 -m pip install --upgrade pip
python3.13 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "pheo[langchain]==0.1.13"
pheo init
```

Contributors installing from this repository:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python3.13 -m pip install -e ".[langchain,dev]"
pheo init
```

Application code imports only `pheo`. The compiled Pheo kernel runtime is bundled into the package.

## 2. Create A Pheo Data Store

```bash
pheo store create \
  --name ap_invoice_exception_review \
  --business-area finance \
  --goal "Prepare AP invoice exception summaries for human review before any payment-related action is approved."
```

## 3. Add Source Material

```bash
pheo source add \
  --store ap_invoice_exception_review \
  examples/finance_exception/ap-policy.md
```

## 4. Review Rules

Adding source material creates draft review rules against the Pheo Data Store goal/protocol.

Inspect the draft before approving it:

```bash
pheo methodology review \
  --workflow ap_invoice_exception_review \
  --format human
```

If the rules need edits:

```bash
pheo methodology update \
  --workflow ap_invoice_exception_review \
  --rule "Name missing invoice support, approval gaps, and inconsistent evidence." \
  --rule "Escalate sensitive, duplicate, high-risk, or unclear approval cases." \
  --avoid "Do not imply payment can be approved without human review." \
  --author reviewer@example.com
```

If the draft is wrong:

```bash
pheo methodology reject \
  --workflow ap_invoice_exception_review \
  --author reviewer@example.com \
  --note "Needs a narrower AP policy source."
```

## 5. Approve Review Rules

```bash
pheo methodology approve \
  --workflow ap_invoice_exception_review \
  --author reviewer@example.com \
  --note "Approved AP exception review policy for local test."
```

Pheo will not observe or score workflow outputs until the review rules are approved.

## 6. Add A Review Point

```bash
pheo review-point add \
  --store ap_invoice_exception_review \
  --name ap_exception_review \
  --description "Review AP invoice exception summaries before clearing or payment-related action." \
  --dimension "evidence support" \
  --dimension "approval clarity" \
  --dimension "exception risk" \
  --dimension "next step"
```

## 7. Observe An Output

```bash
pheo observe output \
  --review-point ap_exception_review \
  --context '{"invoice_id":"AP-1007","vendor":"Northstar Office Supplies","amount":"8420","approval_status":"Unclear - no approver identified"}' \
  --source '{"connector":"ap_invoice_example","case_id":"AP-1007"}' \
  --output "Invoice AP-1007 from Northstar Office Supplies requires AP exception review. No PO match was found and the approver is not identified. Recommend confirming approval reference and support before clearing."
```

To seed the full synthetic review queue:

```bash
python examples/finance_exception/observe_cases.py
```

This creates pending review packets. Memory export gets useful after reviewers capture decisions with reasons.

## 8. Review In The Browser

```bash
pheo start --store ap_invoice_exception_review
```

Open:

```text
http://127.0.0.1:8787
```

Approve, edit, reject, or escalate the review case.

## 8b. Review From CLI Or Agent

If you are testing through Cursor, Copilot, MCP, or another agent, you do not have to open the browser. Use the `packet.id` and candidate index returned by `pheo observe ...`.

```bash
pheo review capture \
  --packet <packet_id> \
  --selected 0 \
  --action edit \
  --corrected-output "Invoice AP-1007 should be escalated because support is missing and no approver is identified. Confirm PO match and approval owner before any payment-related action." \
  --reason "Added explicit escalation and missing-evidence rationale." \
  --author you@company.com
```

Use `--action approve`, `reject`, `edit`, or `escalate`. Reject or edit at least one case and include a reason so the export contains real human judgment.

## 9. Export Memory

```bash
pheo export pack \
  --store ap_invoice_exception_review \
  --out ./pack
```

The pack contains review decisions, preference pairs, review examples, check cases, and a workflow graph.

To export only human-derived review memory:

```bash
pheo export pack \
  --store ap_invoice_exception_review \
  --out ./pack-organic \
  --organic-only
```

`--organic-only` means the export includes human-reviewed decisions only, not bootstrap examples created during setup.

## Endpoint Test

If you have an OpenAI/OpenRouter-compatible endpoint:

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
  --context '{"invoice_id":"AP-1007","vendor":"Northstar Office Supplies","approval_status":"Unclear - no approver identified"}' \
  --prompt "Draft a factual AP invoice exception review note. Do not approve payment."
```

## Trace And Inference Import Test

If your agent stack already emits traces or inference logs, import them into the same review point:

```bash
pheo observe traces --review-point ap_exception_review --source-type langsmith --file examples/traces/langgraph-langsmith-run.json
pheo observe traces --review-point ap_exception_review --source-type langchain --file ./langchain-runs.json
pheo observe traces --review-point ap_exception_review --source-type llamaindex --file ./llamaindex-events.json
pheo observe traces --review-point ap_exception_review --source-type weave --file examples/traces/weave-call.json
pheo observe traces --review-point ap_exception_review --source-type noveum --file examples/traces/noveum-trace.json
pheo observe traces --review-point ap_exception_review --source-type vllm --file ./vllm-output.jsonl
pheo observe traces --review-point ap_exception_review --source-type huggingface --file ./hf-output.jsonl
pheo observe traces --review-point ap_exception_review --source-type opentelemetry --file ./otel-spans.json
```

Every candidate includes numeric scores plus `scores.explanation`, which gives the reviewer a plain-English reason for the score.

The endpoint key stays in the local environment and is not stored in Pheo.

LangGraph is supported through LangChain/LangSmith-style trace exports. W&B Weave is supported with `source_type=weave` or `source_type=wandb-weave`. Noveum trace batches are supported with `source_type=noveum`.
