# Pattern: Attach After LangChain Or LangGraph

Use this when LangChain or LangGraph already runs the agent and you only need governance after the agent produces an output.

Pheo does not replace the chain, graph, tools, callbacks, or trace stack. Attach Pheo where the workflow output would otherwise become business action:

```text
LangChain / LangGraph runs
  -> agent output
  -> Pheo observe.output(...)
  -> human review
  -> require_released()
  -> memory pack export
  -> memory= on the next similar case
```

## SDK Example

Use one of three attach points:

| Existing shape | Pheo attach |
| --- | --- |
| Runnable / agent with `.invoke(...)` | `with_pheo_review(...)` |
| LangGraph state machine | `pheo_review_node(...)` as the final node before side effects |
| LangSmith traces already captured | `pheo observe traces --source-type langsmith` |

`with_pheo_review(...)` wraps the outer runnable. It is not an LCEL pipe element, so use `with_pheo_review(existing_chain | postprocess, ...)`, not `existing_chain | with_pheo_review(...)`.

## Runnable Attach

Approve methodology once before observing outputs. See `docs/getting-started.md` for first-time store setup.

```python
import pheo
from pheo import PendingReview
from pheo.integrations.langchain import with_pheo_review

store = pheo.open("./.pheo")

# Existing LangChain or LangGraph code.
reviewed_graph = with_pheo_review(
    graph,
    store=store,
    review_point="ap_exception_review",
    output_key="final_answer",
    cycle_id="cycle_1",
)

result = reviewed_graph.invoke({
    "invoice_id": "AP-1007",
    "vendor": "Northstar Office Supplies",
    "approval_status": "Unclear - no approver identified",
})

print(result.review_url)

# Downstream business code should use the release gate. This raises until
# a human approves or edits the output in the local UI or through the SDK/CLI/MCP.
try:
    released_output = result.require_released()
except PendingReview:
    released_output = None
```

Run `pheo start --store ap_invoice_exception_review` and open the review URL, or capture the review in code:

```python
store.review(
    result.outcome.id,
    selected_index=result.outcome.recommended["index"],
    action="edit",
    corrected_output="Invoice AP-1007 should be escalated because support is missing and no approver is identified.",
    reason="Human reviewer added the missing evidence and approval rationale.",
    author_id="reviewer@example.com",
)

released_output = result.require_released()
```

## Apply Prior Judgment On The Next Cycle

```python
memory = store.memory("ap_invoice_exception_review")

reviewed_graph_cycle_2 = with_pheo_review(
    graph,
    store=store,
    review_point="ap_exception_review",
    output_key="final_answer",
    cycle_id="cycle_2",
    memory=memory,
)

next_result = reviewed_graph_cycle_2.invoke({
    "invoice_id": "AP-1249",
    "approval_status": "Unclear - no approver identified",
})
```

Memory does not auto-release output. It surfaces prior similar human judgments and reasons before the next review.

## LangGraph Final Node

If your app is graph-native, add Pheo as the final node before the node that sends email, writes a database row, clears an invoice, or performs another business side effect.

```python
from pheo.integrations.langchain import pheo_review_node

graph.add_node(
    "pheo_review",
    pheo_review_node(
        store=store,
        review_point="ap_exception_review",
        output_key="final_answer",
        cycle_id="cycle_1",
    ),
)

graph.add_edge("draft_exception_note", "pheo_review")
```

The node returns:

```python
{
    "pheo_review": {
        "outcome_id": "...",
        "status": "pending_review",
        "review_url": "/review/packet_...",
        "recommended_output": "...",
    }
}
```

Your downstream side-effect node should read only `released_output`, which is present only after review.

## If You Already Use LangSmith

Keep LangSmith for traces and observability. Use Pheo for the release boundary:

```text
LangSmith trace export
  -> pheo observe traces --source-type langsmith
  -> Pheo review / release / receipts / preference export
```

See `patterns/import-traces.md` for trace-file import.

## Do Not

- Do not rebuild the graph inside Pheo.
- Do not replace LangChain tool approval with Pheo.
- Do not treat observed output as released business output.
- Do not store LangChain or model API keys in the Pheo Data Store.
