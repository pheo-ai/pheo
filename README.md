# Pheo

[![CI](https://github.com/pheo-ai/pheo/actions/workflows/ci.yml/badge.svg)](https://github.com/pheo-ai/pheo/actions/workflows/ci.yml)

Pheo is a Python library that adds human review gates to existing AI agent pipelines.

Every AI output goes through a review surface before release. Approved or edited decisions become receipts, preference pairs, released examples, and reusable judgment memory. Pheo runs locally with SQLite, exports JSON/JSONL memory packs, and ships with its compiled kernel runtime.

It is not an agent framework, model provider, or hosted memory database.

## Why It Exists

Generated output is becoming cheap. Judgment is not.

Pheo helps answer:

- What AI output was proposed?
- Which version was approved, edited, or rejected?
- Why did a human make that decision?
- Which source material and review rules were active?
- Can the decisions become evaluation data, preference data, private training data, or judgment memory for the next cycle?

## Install (Beta)

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python3.13 -m pip install --upgrade pip
python3.13 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "pheo[langchain]==0.1.0"
pheo init
```

TestPyPI hosts the `pheo` wheel. Dependencies such as `langchain-core` resolve from PyPI — both indexes are required.

## Try in 60 seconds

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python3.13 -m pip install --upgrade pip
python3.13 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "pheo[langchain]==0.1.0"
pheo init
pheo
```

`pheo` opens the local UI at `http://127.0.0.1:8787`. The terminal keeps running until you press `Ctrl+C`.

Or run the bundled demo (no repo clone needed):

```bash
pheo demo hello-world --reset
```

For the full AP finance walkthrough, clone this repo and follow [Getting Started](docs/getting-started.md).

For contributors installing from source: `python3.13 -m pip install -e ".[langchain,dev]"`. See [docs/deployment.md](docs/deployment.md) and [docs/release.md](docs/release.md).

Using a coding agent? Start with [docs/agents.md](docs/agents.md).
First time here? Use [docs/getting-started.md](docs/getting-started.md).

## Local Data Custody

By default, Pheo runs locally.

- Pheo does not receive customer data.
- Pheo does not call a Pheo-owned LLM.
- Your source material, observations, reviews, and exports stay in your configured project.
- The default store is local SQLite plus JSON/JSONL export.
- Customers can add their own sinks for S3, GCS, Postgres, warehouses, or internal systems.

Pheo ships with its compiled kernel runtime. The SDK and exports stay stable while the review engine improves behind the scenes.

## Kernel Boundary

Pheo is a two-layer product: an **open harness** (MIT) and a **compiled kernel runtime** (separate license).

See [docs/kernel-boundary.md](docs/kernel-boundary.md) for what is open, what is not, and which PRs are welcome.

## License

- **Harness source** in this repository: [MIT License](LICENSE)
- **Compiled kernel binaries** in official packages: [Kernel License](legal/KERNEL_LICENSE.md)
- **Commercial / enterprise terms:** [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md)
- **Trademark:** [TRADEMARK.md](TRADEMARK.md)

## Core Loop

```text
Add source material
  -> Approve review rules
  -> Observe workflow output
  -> Capture human judgment with a reason
  -> Freeze a release receipt
  -> Export preference data
  -> Apply judgment memory on the next similar case
```

## Patterns

Use these when adding Pheo to an existing workflow:

- [Wrap an existing Python function](patterns/wrap-python-function.md)
- [Attach after LangChain or LangGraph](patterns/langchain-attach.md)
- [Observe an OpenAI-compatible endpoint](patterns/openai-compatible-endpoint.md)
- [Import LangSmith, Weave, or Noveum traces](patterns/import-traces.md)
- [Drive setup from a coding agent with MCP](patterns/mcp-agent-checklist.md)

For a business workflow example, see [Finance Exception Example](examples/finance_exception/README.md).
For a live LangChain attach demo, see [LangChain Attach Demo](examples/langchain_attach/README.md).

For existing LangChain apps, wrap the runnable at the release boundary:

```python
from pheo.integrations.langchain import with_pheo_review

reviewed_chain = with_pheo_review(
    existing_chain,
    store=store,
    review_point="ap_exception_review",
    output_key="final_answer",
)

result = reviewed_chain.invoke(invoice)
released_text = result.require_released()
```

For LangGraph, add `pheo_review_node(...)` as the final node before a business side effect. See [Attach after LangChain or LangGraph](patterns/langchain-attach.md).

## Ten-Minute Path

Application code imports only `pheo`.

Run the finance example:

```bash
pheo store create \
  --name ap_invoice_exception_review \
  --business-area finance \
  --goal "Prepare AP invoice exception summaries for human review before any payment-related action is approved."

pheo source add \
  --store ap_invoice_exception_review \
  examples/finance_exception/ap-policy.md

pheo methodology review \
  --workflow ap_invoice_exception_review \
  --format human

pheo methodology approve \
  --workflow ap_invoice_exception_review \
  --author reviewer@example.com \
  --note "Approved AP exception review policy for local test."

pheo review-point add \
  --store ap_invoice_exception_review \
  --name ap_exception_review \
  --description "Review AP invoice exception summaries before clearing or payment-related action." \
  --dimension "evidence support" \
  --dimension "approval clarity" \
  --dimension "exception risk" \
  --dimension "next step"

python examples/finance_exception/observe_cases.py
pheo start --store ap_invoice_exception_review
```

Open `http://127.0.0.1:8787`, review a packet, then export memory.

To prove the full preference-factory loop in one command:

```bash
python examples/finance_exception/run_preference_factory.py \
  --project /tmp/pheo-preference-factory \
  --out /tmp/pheo-preference-factory-pack
```

The script creates Cycle 1 AP reviews with seeded demo reviewer decisions, compiles judgment memory, applies it on Cycle 2, and exports receipts, preference tuples, preference pairs, released examples, a training manifest, and a cycle diff. In production, replace the seeded decisions with real human review capture.

## Five-Minute SDK Example

```python
import pheo

store = pheo.open("./.pheo")

workflow = store.create_store(
    "ap_invoice_exception_review",
    business_area="finance",
    goal="Prepare AP invoice exception summaries for human review before any payment-related action is approved.",
)

store.source.add_text(
    "AP policy",
    "AI may draft factual invoice exception notes, but a human reviewer must approve, edit, reject, or escalate before payment-related action.",
)

store.review_methodology(workflow["id"], actor="controller@example.com")
store.approve_methodology(workflow["id"], actor="controller@example.com")

store.review_point.create(
    "ap_exception_review",
    description="Review AP invoice exception summaries before clearing or payment-related action.",
    dimensions=["evidence support", "approval clarity", "exception risk", "next step"],
)

outcome = store.observe.output(
    "ap_exception_review",
    output="Invoice AP-1007 can proceed after review.",
    context={
        "invoice_id": "AP-1007",
        "vendor": "Northstar Office Supplies",
        "approval_status": "Unclear - no approver identified",
    },
    source={"connector": "ap_agent", "trace_id": "trace-1"},
)

print(outcome.status)       # pending_review
print(outcome.review_url)   # /review/packet_...

# Do not treat the observed model output as final business output.
# This raises until a reviewer approves or edits the outcome.
final_output = outcome.require_released()
```

After human review:

```python
store.review(
    outcome.id,
    selected_index=outcome.recommended["index"],
    action="edit",
    corrected_output="Invoice AP-1007 should be escalated because support is missing and no approver is identified.",
    reason="Human correction added missing evidence and approval rationale.",
    author_id="reviewer@example.com",
)

final_output = outcome.require_released()
```

Use prior judgment memory on the next cycle:

```python
memory = store.memory(workflow["id"])

next_outcome = store.observe.output(
    "ap_exception_review",
    output="Invoice AP-1042 can proceed after review.",
    context={"invoice_id": "AP-1042", "approval_status": "Unclear - no approver identified"},
    source={"connector": "ap_agent", "cycle_id": "cycle_2"},
    memory=memory,
)
```

Memory does not auto-release output. It surfaces prior similar judgments and reasons before the next human review.

## Decorator Example

Observe an existing agent function without moving to a new workflow platform:

```python
@store.review_point("ap_exception_review")
def draft_invoice_review(invoice):
    return ap_agent.run(invoice)

outcome = draft_invoice_review({"invoice_id": "AP-1007", "approval_status": "unclear"})

print(outcome.status)
print(outcome.review_url)
```

The function return value becomes a governed outcome. The raw observed output is available for audit as `outcome.observed_output`, but the release path is `outcome.require_released()`.

## OpenAI-Compatible Endpoint Example

Connect an OpenAI/OpenRouter-compatible endpoint:

```bash
export OPENROUTER_API_KEY="..."

pheo connection add \
  --store ap_invoice_exception_review \
  --name openrouter \
  --type openai-compatible-endpoint \
  --endpoint-url https://openrouter.ai/api/v1 \
  --model openai/gpt-4o-mini \
  --api-key-env OPENROUTER_API_KEY
```

Observe an endpoint output:

```bash
pheo observe endpoint \
  --review-point ap_exception_review \
  --connection openrouter \
  --context '{"invoice_id":"AP-1007","vendor":"Northstar Office Supplies","approval_status":"Unclear - no approver identified"}' \
  --prompt "Draft a factual AP invoice exception review note. Do not approve payment."
```

The API key is read from the environment and is not stored in Pheo.

Python SDK equivalent:

```python
outcome = store.observe.endpoint(
    review_point="ap_exception_review",
    connection="openrouter",
    prompt="Draft a factual AP invoice exception review note. Do not approve payment.",
    context={"invoice_id": "AP-1007", "approval_status": "unclear"},
)
```

## Integration Examples

Register the systems that feed review points:

```python
store.connection.add_langchain(store_id="support_review", workspace="customer-support")
store.connection.add_weave(store_id="agent_review", workspace="wandb")
store.connection.add_noveum(store_id="agent_review", workspace="noveum")
store.connection.add_llamaindex(store_id="research_review")
store.connection.add_vllm(store_id="local_model_review", endpoint_url="http://localhost:8000/v1", model="local/vllm")
store.connection.add_huggingface(store_id="hf_review", endpoint_url="https://api-inference.huggingface.co/models/...", model="custom-support")
```

Import trace or inference logs:

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

These connectors normalize outputs into the same governed outcome loop: score, prepare candidates, wait for review, capture judgment, export memory.

LangGraph is supported through LangChain/LangSmith-style trace exports, not a separate live callback yet. W&B Weave is supported with `source_type=weave` or `source_type=wandb-weave`. Noveum trace batches are supported with `source_type=noveum`. Vercel AI SDK is not first-class yet; use REST or JSONL output capture for JavaScript workflows.

## Score Explanations

Every scored candidate stores both numeric scores and a public explanation:

```json
{
  "mean_score": 0.69,
  "grounding": 0.58,
  "clarity": 0.81,
  "explanation": {
    "verdict": "reviewable_candidate",
    "summary": "Reviewable candidate. Strongest signals: Clarity; weakest signals: Grounding.",
    "weakest_dimensions": [
      {
        "label": "Grounding",
        "reason": "The output does not visibly reference source support, evidence, policy, or owner context."
      }
    ]
  }
}
```

The explanation is review-facing observability. It does not expose private implementation details.

## CLI Flow

```bash
pheo init

pheo store create \
  --name ap_invoice_exception_review \
  --business-area finance \
  --goal "Prepare AP invoice exception summaries for human review before any payment-related action is approved."

pheo source add \
  --store ap_invoice_exception_review \
  examples/finance_exception/ap-policy.md

pheo methodology review \
  --workflow ap_invoice_exception_review \
  --format human

pheo methodology approve \
  --workflow ap_invoice_exception_review \
  --author reviewer@example.com \
  --note "Approved AP exception review policy for local test."

pheo review-point add \
  --store ap_invoice_exception_review \
  --name ap_exception_review \
  --description "Review AP invoice exception summaries before clearing or payment-related action." \
  --dimension "evidence support" \
  --dimension "approval clarity" \
  --dimension "exception risk" \
  --dimension "next step"

pheo observe output \
  --review-point ap_exception_review \
  --context '{"invoice_id":"AP-1007","vendor":"Northstar Office Supplies","amount":"8420","approval_status":"Unclear - no approver identified"}' \
  --source '{"connector":"ap_invoice_example","case_id":"AP-1007"}' \
  --output "Invoice AP-1007 from Northstar Office Supplies requires AP exception review. No PO match was found and the approver is not identified. Recommend confirming approval reference and support before clearing."

pheo start --store ap_invoice_exception_review
```

`pheo observe`, `pheo observe endpoint`, trace import scoring, and `pheo run score` require approved review rules. If rules are still draft or rejected, Pheo stops before scoring and asks for methodology approval.

Use `pheo export preferences --organic-only` or `pheo export pack --organic-only` when you want only human-derived review memory. Bootstrap pairs from methodology onboarding remain visible in full exports but are labeled separately.

Use compiled memory on a later observation:

```bash
pheo observe output \
  --review-point ap_exception_review \
  --use-memory \
  --context '{"invoice_id":"AP-1042","vendor":"Northstar Office Supplies","approval_status":"Unclear - no approver identified"}' \
  --source '{"connector":"ap_invoice_example","case_id":"AP-1042","cycle_id":"cycle_2"}' \
  --output "Invoice AP-1042 from Northstar Office Supplies can proceed after review."
```

Inspect memory and cycle proof:

```bash
pheo memory show --store ap_invoice_exception_review
pheo cycle-diff --store ap_invoice_exception_review --before cycle_1 --after cycle_2
pheo export sft --workflow ap_invoice_exception_review --organic-only
pheo export dpo --workflow ap_invoice_exception_review --organic-only
```

## Projects And Stores

```text
Project
  local workspace and SQLite database

Pheo Data Store
  one governed workflow memory inside a project

Review Point
  where an AI, agent, trace, or workflow output becomes reviewable

Outcome
  observed output, candidates, scores, review URL, review status, and released output

Memory Pack
  source provenance, review rules, decisions, release receipts, preference tuples,
  preference pairs, released examples, judgment memory, checks, and graph
```

Useful commands:

```bash
pheo project create finance-pilot
pheo project list
pheo project use finance-pilot
pheo store list
pheo start --store ap_invoice_exception_review
```

## Input Paths

Pheo can observe outputs from:

- Python decorators
- SDK calls
- REST ingest
- OpenAI-compatible endpoints
- LangChain / LangSmith traces, including LangGraph runs exported through LangSmith-style records
- LlamaIndex traces
- vLLM and Hugging Face inference logs
- W&B Weave traces
- Noveum trace batches
- OpenTelemetry-style traces
- JSONL or log batches
- MCP stdio tools

## Review Paths

Default local review paths:

- CLI
- REST
- local browser UI

Optional notification adapters:

- customer SMTP
- Slack webhook
- Telegram bot
- generic webhook

Pheo does not ship Pheo credentials. Customer notification secrets stay in the customer environment.

## Export

```bash
pheo export pack \
  --store ap_invoice_exception_review \
  --out ./pack
```

Exported artifacts:

```text
memory_pack.json
workflow.graph.json
observations.jsonl
decisions.jsonl
methodology_events.jsonl
release_receipts.jsonl
preference_tuples.jsonl
preference_pairs.jsonl
review_examples.jsonl
judgment_memory.json
training_manifest.json
cycle_diff.json
sft.jsonl
dpo.jsonl
check_cases.jsonl
```

## Development

```bash
python3.13 -m pip install -e ".[langchain,dev]"
python -m unittest discover -s tests -p 'test_*.py'
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CHANGELOG.md](CHANGELOG.md), and [docs/](docs/README.md).

Pheo's public SDK, CLI, UI, and export formats stay stable while the review engine improves behind the scenes.
