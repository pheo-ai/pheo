# Hello World: Bring Your Own Endpoint

This is the smallest Pheo loop without LangChain:

```text
your endpoint -> PHEO Go/Grow -> human judgment -> Decisions -> memory on the next cycle
```

Pheo does not own the model call. The example uses a simple finance receipt
review workflow so the loop is easy to see: an AI drafts a receipt exception
note, a human decides whether to approve, edit, reject, or escalate it, and that
judgment becomes local memory.

## OpenRouter

```bash
export OPENAI_COMPATIBLE_BASE_URL="https://openrouter.ai/api/v1"
export OPENAI_COMPATIBLE_API_KEY="..."
export OPENAI_COMPATIBLE_MODEL="openai/gpt-4o-mini"
pheo demo --reset
```

By default, the demo starts a persistent local PHEO UI. If your endpoint key is
set, you can call that endpoint from the PHEO Grow step. If the key is
not set, you can still use the demo finance receipt policy and paste outputs by
hand.

In the UI you can:

1. Use **PHEO Go** to inspect or replace the demo finance receipt policy.
2. Build and approve review rules.
3. Use **PHEO Grow** to review endpoint output or paste your own output.
4. Capture a human judgment with a reason.
5. Use **Decisions** to inspect memory and export files.

The server stays open until you press `Ctrl-C`.

If you want to review fully in the terminal instead of the browser:

```bash
pheo demo --reset --review-mode cli
```

For CI or a fully automated smoke test:

```bash
pheo demo --reset --review-mode scripted
```

Claude works through OpenRouter:

```bash
export OPENAI_COMPATIBLE_MODEL="anthropic/claude-3.5-sonnet"
pheo demo --reset
```

To also mirror the memory pack into a customer-owned destination during the demo:

```bash
pheo demo \
  --reset \
  --review-mode scripted \
  --customer-sink /tmp/customer-owned-pheo-pack
```

To sync the same pack into your Google Cloud Storage bucket:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

pheo demo \
  --reset \
  --customer-sink gs://YOUR_BUCKET/pheo/hello-world/run-001
```

The default local path still exists. The GCS path receives the same receipts,
preference tuples, decision log, released examples, and judgment memory files.
For Postgres, S3, a warehouse, or an internal webhook, replace only
`sync_customer_sink(...)` in `run_demo.py` with your tenancy writer.

## OpenAI

```bash
export OPENAI_COMPATIBLE_BASE_URL="https://api.openai.com/v1"
export OPENAI_COMPATIBLE_API_KEY="..."
export OPENAI_COMPATIBLE_MODEL="gpt-4o-mini"
pheo demo --reset
```

## Windows PowerShell

```powershell
$env:OPENAI_COMPATIBLE_BASE_URL="https://openrouter.ai/api/v1"
$env:OPENAI_COMPATIBLE_API_KEY="..."
$env:OPENAI_COMPATIBLE_MODEL="openai/gpt-4o-mini"
pheo demo --reset
```

## Expected Output

```text
Resetting local Hello World project and export folder.
Opening the Hello World apprentice.
Use the demo finance receipt policy or replace it with your own notes.
Starting local PHEO apprentice.
Workflow: finance_receipt_review
Local UI: http://127.0.0.1:8787/?hello=1
The server stays open until you press Ctrl-C.
```

Open the local review UI after the demo:

```bash
pheo --project /tmp/pheo-hello-world
```

To use a non-OpenAI-compatible endpoint, replace only `call_openai_compatible_endpoint(...)` in `run_demo.py`. Keep the Pheo calls unchanged.
