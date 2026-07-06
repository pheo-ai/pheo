# Pattern: Wrap An Existing Python Function

Use this when a workflow already has a Python function that returns an AI or agent output.

Do not rebuild the workflow inside Pheo. Add a review point at the function boundary.

```python
import pheo

store = pheo.open("./.pheo")

workflow = store.create_store(
    "ap_invoice_exception_review",
    business_area="finance",
    goal="Prepare AP invoice exception summaries for human review before any payment-related action is approved.",
)

store.source.add("examples/finance_exception/ap-policy.md", store_id=workflow["id"])
store.review_methodology(workflow["id"], actor="reviewer@example.com")
store.approve_methodology(workflow["id"], actor="reviewer@example.com")

store.review_point.create(
    "ap_exception_review",
    description="Review AP invoice exception summaries before clearing or payment-related action.",
    dimensions=["evidence support", "approval clarity", "exception risk", "next step"],
)

@store.review_point("ap_exception_review")
def draft_invoice_review(invoice):
    return existing_invoice_agent.run(invoice)

outcome = draft_invoice_review({
    "invoice_id": "AP-1007",
    "vendor": "Northstar Office Supplies",
    "amount": "8420",
    "approval_status": "Unclear - no approver identified",
})

print(outcome.status)
print(outcome.review_url)

# This blocks until a human approves or edits the outcome.
released = outcome.require_released()
```

Use the released output downstream. Keep the raw observed output for audit only.
