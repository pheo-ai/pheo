# Pheo Agent Instructions

## What This Is

Pheo adds a governed review and learning loop to AI workflows that already exist.

Use Pheo when an agent, LLM endpoint, trace, batch job, or business workflow produces an output that should be reviewed before it becomes business memory, evaluation data, or training data.

Pheo does not replace the workflow. It observes the places where AI work already happens, prepares reviewable outcomes, captures human judgment with reasons, freezes release receipts, and stores those decisions in a local Pheo Data Store.

Pheo source is MIT-licensed and ships with its compiled kernel runtime. The kernel is the product: do not add reference scoring, branching, methodology synthesis, or memory-application logic in app code. Call the Pheo SDK/CLI/MCP surfaces and let the bundled runtime score, branch, or apply memory.

## Copy-Paste Agent Instruction

```text
Use Pheo to add a human review and learning loop to this existing workflow.
Do not rebuild the workflow inside Pheo.
Identify the output that needs review, create a Pheo review point, capture human approve/edit/reject/escalate decisions, and export the resulting memory.
When a later cycle runs, compile workflow memory and pass it to observe so prior human judgments can guide the next review.
Use local data custody by default. Do not add a Pheo-owned LLM call.
```

For an existing repo, this is usually enough:

```text
Read AGENTS.md. Add Pheo review and export to [WORKFLOW].
Do not rebuild the app inside Pheo.
Use the existing workflow output as the review point.
```

## Product Shape

```text
Project
  local workspace and SQLite database

Pheo Data Store
  governed memory for one workflow

Source material
  policies, examples, operating rules, evidence, documents

Review point
  where an AI/workflow output becomes reviewable

Outcome
  observed output, generated candidates, scores, review URL, status, released output

Memory pack
  source provenance, review rules, decisions, release receipts, preference tuples,
  preference pairs, released examples, judgment memory, checks, graph
```

## Install

Install from this repo:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python3.13 -m pip install -e ".[langchain]"
pheo init
```

Application code imports only `pheo`.

The compiled Pheo kernel runtime is bundled into the package.

## Fast Path

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
```

Open the local review UI:

```bash
pheo start --store ap_invoice_exception_review
```

Then visit:

```text
http://127.0.0.1:8787
```

The script seeds 25 AP invoice exception packets so reviewers can approve, edit, reject, or escalate real-looking cases before exporting memory.

To prove the complete loop in one command:

```bash
python examples/finance_exception/run_preference_factory.py \
  --project /tmp/pheo-preference-factory \
  --out /tmp/pheo-preference-factory-pack
```

This creates Cycle 1 reviews with seeded demo reviewer decisions, compiles judgment memory, applies it on Cycle 2, and exports receipts, preference tuples, preference pairs, released examples, a training manifest, and a cycle diff. In production, replace seeded reasons and actions with real human review capture.

## SDK Pattern

Use the SDK when you are editing Python code directly:

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

store.review_methodology(workflow["id"], actor="reviewer@example.com")
store.approve_methodology(workflow["id"], actor="reviewer@example.com")

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

print(outcome.status)
print(outcome.review_url)
```

Do not treat the raw observed output as released business output. The release path is through review:

```python
store.review(
    outcome.id,
    selected_index=outcome.recommended["index"],
    action="edit",
    corrected_output="Invoice AP-1007 should be escalated because support is missing and no approver is identified.",
    reason="Human correction added missing evidence and approval rationale.",
    author_id="reviewer@example.com",
)
```

Apply the same review memory on a later cycle:

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

Memory never bypasses review. It surfaces prior similar judgments and reasons before a reviewer decides.

## Choose The Integration Path

- Existing Python function: use the decorator pattern.
- LangChain app: wrap the existing runnable with `pheo.integrations.langchain.with_pheo_review(...)`; see `patterns/langchain-attach.md`.
- LangGraph app: add `pheo.integrations.langchain.pheo_review_node(...)` as the final node before a business side effect.
- OpenAI/OpenRouter-compatible model call: use `pheo connection add` and `pheo observe endpoint`.
- LangChain, LangGraph, or LangSmith trace export: use `pheo observe traces --source-type langsmith`.
- W&B Weave export: use `pheo observe traces --source-type weave` or `wandb-weave`.
- Noveum trace export: use `pheo observe traces --source-type noveum`.
- OpenTelemetry spans: use `pheo observe traces --source-type opentelemetry`.
- Vercel AI SDK or another JavaScript workflow: send outputs through REST or JSONL until a first-class adapter exists.
- Coding agent setup: use `pheo mcp`.
- REST integration: see `API.md` and `GET /openapi.json` from `pheo start`.
- Copy-paste implementation recipes: see the `patterns/` directory.
- Finance/AP example data: see `examples/finance_exception/`.
- Live LangChain attach demo: see `examples/langchain_attach/`.

## Endpoint Pattern

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

The API key is read from the environment and is not stored in Pheo.

## Trace Pattern

```bash
pheo observe traces \
  --review-point ap_exception_review \
  --source-type langsmith \
  --file examples/traces/langgraph-langsmith-run.json

pheo observe traces \
  --review-point ap_exception_review \
  --source-type weave \
  --file examples/traces/weave-call.json

pheo observe traces \
  --review-point ap_exception_review \
  --source-type noveum \
  --file examples/traces/noveum-trace.json
```

Pheo normalizes the trace output into the same governed outcome loop: score, prepare candidates, wait for review, capture judgment, export memory.

## MCP Pattern

Run the local MCP server:

```bash
pheo mcp
```

Use MCP when a coding agent should create stores, add source material, review/approve methodology, create review points, observe outputs, capture decisions, and export memory without shelling out for every step.

Preference-factory MCP tools include memory, release receipts, training manifest, and cycle diff inspection. Use them after capture to verify what the customer gets back.

## Development Rules For Agents

- Keep the developer journey simple: one install, one import, one CLI.
- Preserve local data custody by default.
- Do not add a Pheo-owned LLM call.
- Do not store API keys in the Pheo Data Store.
- Keep raw observed output separate from reviewed/released output.
- Prefer business terms in public docs: review point, outcome, decision, Pheo Data Store, release receipt, memory pack.
- Keep algorithm and private review-engine details out of public docs.
