# Pheo API

Pheo exposes a local REST surface for agents, SDKs, CLIs, and browser review.
Humans can use the browser UI served by `pheo start`; agents and external
systems can use the REST routes below, MCP, or the Python SDK.

Machine-readable spec:

```text
GET /openapi.json
```

The checked-in copy is [`openapi.json`](openapi.json).

## Local Auth Boundary

The built-in REST server is a localhost development and integration surface. It
does not implement authentication by itself. The default host is `127.0.0.1`.
If you bind it to another interface or deploy it for a team, put it behind your
own auth layer, reverse proxy, or internal gateway.

## Core Routes

```text
GET  /health
GET  /openapi.json

GET  /v1/projects
POST /v1/projects
POST /v1/projects/current

GET  /v1/workflows
POST /v1/workflows
GET  /v1/workflows/{workflow}

POST /v1/workflows/{workflow}/corpus
GET  /v1/workflows/{workflow}/methodology
POST /v1/workflows/{workflow}/methodology/build
POST /v1/workflows/{workflow}/methodology/update
POST /v1/workflows/{workflow}/methodology/approve
POST /v1/workflows/{workflow}/methodology/reject
GET  /v1/workflows/{workflow}/runs
POST /v1/workflows/{workflow}/runs
POST /v1/workflows/{workflow}/endpoint-runs
POST /v1/workflows/{workflow}/trace-runs
GET  /v1/workflows/{workflow}/preference-store

POST /v1/stores/{store}/connections
POST /v1/stores/{store}/review-points
POST /v1/review-points/{point}/observations
POST /v1/review-points/{point}/endpoint-observations
POST /v1/review-points/{point}/trace-observations
POST /v1/stores/{store}/review-points/{point}/observations
POST /v1/stores/{store}/review-points/{point}/endpoint-observations
POST /v1/stores/{store}/review-points/{point}/trace-observations

GET  /v1/review-packets/{packet}
POST /v1/review-packets/{packet}/reviews
GET  /v1/runs/{run}
POST /v1/runs/{run}/score
POST /v1/runs/{run}/decisions
DELETE /v1/corpus/{corpus}

GET  /v1/workflows/{workflow}/memory-pack
GET  /v1/export/preferences?workflow={workflow}
GET  /v1/export/examples?workflow={workflow}
GET  /v1/export/checks?workflow={workflow}
```

## Main Objects

```text
Project
Pheo Data Store
Source material
Connection
Review point
Observation
Review case
Human review
Memory pack
Release receipt
Preference tuple
Judgment memory
Training manifest
```

## Methodology Gate

Review rules are drafted from the Pheo Data Store review goal/protocol plus source material, then explicitly reviewed and approved by a human. `POST /v1/workflows` accepts `goal`, `objective`, or legacy `description`; all are stored as the workflow objective. Observation and scoring routes reject work until the methodology status is `approved`.

```text
drafted -> reviewed by human -> approved -> observe/score
drafted -> rejected -> update or rebuild -> approved
```

## Review Actions

```text
approve
edit
reject
escalate
```

Each review stores the selected output, optional corrected output, reviewer reason, provenance, and timestamps.

Released outcomes also create an immutable release receipt. The receipt links the raw observed output, recommended output, reviewer decision, released output, active methodology hash, source snapshot hashes, tuple id, and reviewer timestamp. Escalate and reject actions have an empty released output unless a later resolution creates a new reviewed outcome.

## Preference Data And Memory

Memory pack export includes:

```text
memory_pack.json
workflow.graph.json
observations.jsonl
decisions.jsonl
release_receipts.jsonl
preference_tuples.jsonl
preference_pairs.jsonl
review_examples.jsonl
judgment_memory.json
training_manifest.json
cycle_diff.json
sft.jsonl
dpo.jsonl
```

SDK entry points:

```python
memory = store.memory(workflow_id)
outcome = store.observe.output("review_point", output="...", context={}, source={"cycle_id": "cycle_2"}, memory=memory)
receipts = store.release_receipts(workflow_id)
manifest = store.training_manifest(workflow_id)
diff = store.cycle_diff(workflow_id, before="cycle_1", after="cycle_2")
```

`review_examples.jsonl` and `sft.jsonl` use released output only. `dpo.jsonl` is a thin chosen/rejected adapter derived from `preference_pairs.jsonl`. `training_manifest.json` records filters, included and excluded rows, methodology scope, memory richness, and split guidance. `cycle_diff.json` is present when comparable cycles exist.

## Score Observability

Candidate scores include a public explanation alongside numeric dimensions:

```text
candidate.scores.explanation.verdict
candidate.scores.explanation.summary
candidate.scores.explanation.drivers[]
candidate.scores.explanation.thresholds
```

These fields explain review-facing drivers such as grounding, clarity, actionability, and safety. They do not expose private implementation details.

## Trace And Inference Connectors

Trace import supports these `source_type` values:

```text
generic
langchain
langsmith
llamaindex
weave
wandb-weave
noveum
opentelemetry
otel
vllm
huggingface
huggingface-endpoint
```

LangGraph is supported when its runs are exported in LangChain/LangSmith-style records and imported with `source_type=langsmith` or `source_type=langchain`. W&B Weave exports can use `source_type=weave` or `source_type=wandb-weave`. Noveum trace batches can use `source_type=noveum`. Vercel AI SDK is not first-class yet; use REST or JSONL output capture for JavaScript workflows.

## Data Custody

The local API stores data in the active project database. It does not send source material, observations, reviews, or exports to Pheo.

Endpoint observations call the endpoint configured by the customer. API keys should be provided through local environment variables or request-time secrets and are not written to the Pheo Data Store.

See `README.md` for end-to-end examples.
