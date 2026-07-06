# Finance Exception Example

This example shows how to use Pheo for AP invoice exception review.

The workflow is intentionally narrow:

```text
Review goal / protocol
  -> AP policy source
  -> Review and approve rules
  -> Observe invoice exception outputs
  -> Capture human judgments
  -> Export customer-owned preference data
  -> Apply judgment memory on the next cycle
```

## Files

- `ap-policy.md` contains source material for the review methodology.
- `invoice_cases.jsonl` contains 25 synthetic AP invoice exception cases.
- `run_preference_factory.py` proves Cycle 1 review memory changing Cycle 2 review context with seeded demo reviewer decisions.

No company-specific data is included.

## CLI Setup

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
```

## Observe One Case

```bash
pheo observe output \
  --review-point ap_exception_review \
  --context '{"invoice_id":"AP-1007","vendor":"Northstar Office Supplies","amount":"8420","approval_status":"Unclear - no approver identified"}' \
  --source '{"connector":"ap_invoice_example","case_id":"AP-1007"}' \
  --output "Invoice AP-1007 from Northstar Office Supplies requires AP exception review. No PO match was found and the approver is not identified. Recommend confirming approval reference and support before clearing."
```

Then capture a human judgment:

```bash
pheo review capture \
  --packet <packet_id> \
  --selected 0 \
  --action edit \
  --corrected-output "Invoice AP-1007 should be escalated because support is missing and no approver is identified. Confirm PO match and approval owner before any payment-related action." \
  --reason "Added explicit escalation and missing-evidence rationale." \
  --author reviewer@example.com
```

## Observe The JSONL Cases

Seed all 25 synthetic cases into the review queue:

```bash
python examples/finance_exception/observe_cases.py
```

This creates pending review packets. Open the local UI and review them:

```bash
pheo start --store ap_invoice_exception_review
```

Observing cases does not create training memory by itself. Reviewers must approve, edit, reject, or escalate with reasons before exports contain useful human judgment.

## Preference Factory Proof

Run the full loop without opening the UI:

```bash
python examples/finance_exception/run_preference_factory.py \
  --project /tmp/pheo-preference-factory \
  --out /tmp/pheo-preference-factory-pack
```

The script:

1. Creates and approves an AP exception workflow.
2. Observes Cycle 1 invoice outputs.
3. Captures seeded demo reviewer decisions with free-text reasons.
4. Exports release receipts, preference tuples, preference pairs, released examples, and a training manifest.
5. Applies compiled judgment memory to Cycle 2.
6. Writes `cycle_diff.json` so the run has a proof artifact.

The observed output is never treated as released business output until the review step records an approve or edit decision.

For production, replace the seeded reviewer action/reason logic with the local review UI, REST review capture, CLI `pheo review capture`, or MCP `pheo_capture_review`.
