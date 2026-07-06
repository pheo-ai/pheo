# Pattern: Import Trace Or Inference Logs

Use this when the workflow already emits traces or inference logs.

Pheo does not need to become the workflow runner. Import the output records and review them at the chosen review point.

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

Current support:

- LangGraph through LangChain/LangSmith-style exported records.
- W&B Weave through `source_type=weave` or `source_type=wandb-weave`.
- Noveum trace batches through `source_type=noveum`.
- OpenTelemetry spans through `source_type=opentelemetry` or `otel`.
- vLLM and Hugging Face inference logs.
- Generic JSON/JSONL output batches.

Vercel AI SDK is not first-class yet. Use REST or JSONL output capture for JavaScript workflows.
