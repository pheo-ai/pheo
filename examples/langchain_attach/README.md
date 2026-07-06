# LangChain Attach Demo

This demo shows the value of attaching Pheo to an existing LangChain or LangGraph workflow.

It does not replace the chain. A LangChain user keeps their existing `.invoke(...)` path and wraps the runnable at the release boundary:

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

That adds:

- methodology approval before runtime
- review URLs and local reviewer UI
- `require_released()` release gate
- human approve/edit/escalate decisions with reasons
- frozen release receipts
- preference tuples, SFT rows, DPO rows, and memory pack export
- judgment memory applied on the next similar case

The demo is local and API-key free. It uses `langchain-core` `RunnableLambda` to avoid model setup.

## Install

From the repo root:

```bash
python3.13 -m pip install -r examples/langchain_attach/requirements.txt
python3.13 -m pip install -e ".[langchain]"
```

For a package-index install after release:

```bash
python3.13 -m pip install "pheo[langchain]"
```

The compiled Pheo kernel runtime is bundled into the package. Production and commercial deployment are governed by the repository license and commercial license terms.

## Run

```bash
python examples/langchain_attach/run_demo.py --reset
```

The script runs the same AP exception workflow twice:

```text
Without Pheo
  LangChain returns raw output.
  There is no release gate, receipt, reviewer reason, or memory export.

With Pheo
  The existing LangChain runnable is wrapped with `with_pheo_review(...)`.
  Pheo observes the final output, blocks release until review, captures decisions,
  exports the memory pack, and applies prior judgments on Cycle 2.
```

## Open The Review UI

After running the script:

```bash
pheo start --project /tmp/pheo-langchain-attach-demo --store ap_invoice_exception_review
```

Open `http://127.0.0.1:8787` and inspect the review packets.

## Exported Files

The default export path is `/tmp/pheo-langchain-attach-pack`.

Useful files:

```text
release_receipts.jsonl
preference_tuples.jsonl
sft.jsonl
dpo.jsonl
judgment_memory.json
training_manifest.json
cycle_diff.json
```

## What This Proves

LangChain remains the runner. Pheo attaches to the runnable after output and governs what may ship.

That is the lane:

```text
agent output -> review/release -> customer-owned preference data -> next-cycle judgment memory
```
