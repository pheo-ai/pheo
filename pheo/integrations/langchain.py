from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Callable

from pheo.sdk import GovernedOutcome, PendingReview, Pheo


Selector = Callable[[Any, Any], Any]
BUSINESS_CONTEXT_KEYS = {
    "account",
    "amount",
    "approval_status",
    "approver",
    "business_unit",
    "case_id",
    "country",
    "currency",
    "customer_id",
    "document_id",
    "goal",
    "invoice_id",
    "owner",
    "paper_id",
    "period",
    "priority",
    "region",
    "source_id",
    "status",
    "task",
    "ticket_id",
    "vendor",
    "workflow",
}


@dataclass
class PheoLangChainResult:
    """Result returned by a LangChain runnable wrapped with Pheo review."""

    raw: Any
    outcome: GovernedOutcome | None
    error: Exception | None = None

    @property
    def review_url(self) -> str:
        if self.outcome is None:
            return ""
        return self.outcome.review_url

    @property
    def status(self) -> str:
        if self.outcome is None:
            return "review_unavailable"
        return self.outcome.status

    def require_released(self) -> str:
        if self.outcome is None:
            raise PheoReviewUnavailable(
                "Pheo review could not be recorded, so the raw LangChain output is not released. "
                "Check the Pheo store/API configuration and retry observation."
            ) from self.error
        return self.outcome.require_released()

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "error": str(self.error) if self.error else None,
        }


class PheoReviewUnavailable(RuntimeError):
    """Raised when Pheo could not record review metadata for a LangChain output."""


class PheoReviewedRunnable:
    """Duck-typed wrapper for LangChain runnables.

    The wrapper calls the user's existing runnable first, then observes the
    final business output in Pheo. LangChain remains the runner.
    """

    def __init__(
        self,
        runnable: Any,
        *,
        store: Pheo,
        review_point: str,
        output_key: str = "final_answer",
        output_selector: Selector | None = None,
        context_selector: Selector | None = None,
        source_selector: Selector | None = None,
        memory: dict[str, Any] | Callable[[], dict[str, Any]] | None = None,
        cycle_id: str | None = None,
        source_connector: str = "langchain",
    ):
        self.runnable = runnable
        self.store = store
        self.review_point = review_point
        self.output_key = output_key
        self.output_selector = output_selector
        self.context_selector = context_selector
        self.source_selector = source_selector
        self.memory = memory
        self.cycle_id = cycle_id
        self.source_connector = source_connector

    def invoke(self, input: Any, config: Any | None = None, **kwargs: Any) -> PheoLangChainResult:
        raw = _invoke(self.runnable, input, config=config, **kwargs)
        return self._observe_raw(raw, input)

    async def ainvoke(self, input: Any, config: Any | None = None, **kwargs: Any) -> PheoLangChainResult:
        raw = await _ainvoke(self.runnable, input, config=config, **kwargs)
        return self._observe_raw(raw, input)

    def batch(self, inputs: list[Any], config: Any | None = None, **kwargs: Any) -> list[PheoLangChainResult]:
        return [self.invoke(item, config=config, **kwargs) for item in inputs]

    async def abatch(self, inputs: list[Any], config: Any | None = None, **kwargs: Any) -> list[PheoLangChainResult]:
        return [await self.ainvoke(item, config=config, **kwargs) for item in inputs]

    def stream(self, input: Any, config: Any | None = None, **kwargs: Any):
        raise NotImplementedError(
            "Pheo's LangChain adapter wraps final runnable outputs. Streaming is not supported yet; "
            "call the underlying runnable's stream directly and observe the final assembled output."
        )

    async def astream(self, input: Any, config: Any | None = None, **kwargs: Any):
        raise NotImplementedError(
            "Pheo's LangChain adapter wraps final runnable outputs. Async streaming is not supported yet; "
            "call the underlying runnable's astream directly and observe the final assembled output."
        )

    def _observe_raw(self, raw: Any, input: Any) -> PheoLangChainResult:
        try:
            outcome = _observe_result(
                self.store,
                self.review_point,
                raw,
                input,
                output_key=self.output_key,
                output_selector=self.output_selector,
                context_selector=self.context_selector,
                source_selector=self.source_selector,
                memory=self.memory,
                cycle_id=self.cycle_id,
                source_connector=self.source_connector,
            )
            return PheoLangChainResult(raw=raw, outcome=outcome)
        except Exception as exc:
            return PheoLangChainResult(raw=raw, outcome=None, error=exc)


def with_pheo_review(
    runnable: Any,
    *,
    store: Pheo,
    review_point: str,
    output_key: str = "final_answer",
    output_selector: Selector | None = None,
    context_selector: Selector | None = None,
    source_selector: Selector | None = None,
    memory: dict[str, Any] | Callable[[], dict[str, Any]] | None = None,
    cycle_id: str | None = None,
    source_connector: str = "langchain",
) -> PheoReviewedRunnable:
    """Attach Pheo review after an existing LangChain runnable.

    Example:

        reviewed_chain = with_pheo_review(
            chain,
            store=store,
            review_point="ap_exception_review",
            output_key="final_answer",
        )
        result = reviewed_chain.invoke(invoice)
        released_text = result.require_released()
    """

    return PheoReviewedRunnable(
        runnable,
        store=store,
        review_point=review_point,
        output_key=output_key,
        output_selector=output_selector,
        context_selector=context_selector,
        source_selector=source_selector,
        memory=memory,
        cycle_id=cycle_id,
        source_connector=source_connector,
    )


def pheo_review_node(
    *,
    store: Pheo,
    review_point: str,
    output_key: str = "final_answer",
    output_selector: Selector | None = None,
    context_selector: Selector | None = None,
    source_selector: Selector | None = None,
    memory: dict[str, Any] | Callable[[], dict[str, Any]] | None = None,
    cycle_id: str | None = None,
    source_connector: str = "langgraph",
    state_key: str = "pheo_review",
    released_key: str = "released_output",
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return a LangGraph-style final node that observes graph state in Pheo.

    Add this as the last node before a business side effect. It returns a small
    state update containing the review URL and outcome id. If a reviewer has
    already released the outcome, the update also includes ``released_key``.
    """

    def node(state: dict[str, Any]) -> dict[str, Any]:
        outcome = _outcome_from_state(store, state, state_key)
        if outcome is None:
            try:
                outcome = _observe_result(
                    store,
                    review_point,
                    state,
                    state,
                    output_key=output_key,
                    output_selector=output_selector,
                    context_selector=context_selector or _default_graph_context,
                    source_selector=source_selector,
                    memory=memory,
                    cycle_id=cycle_id,
                    source_connector=source_connector,
                )
            except Exception as exc:
                return {state_key: {"status": "review_unavailable", "error": str(exc)}}
        update = _node_update(outcome, state_key)
        try:
            update[released_key] = outcome.require_released()
        except PendingReview:
            pass
        return update

    return node


def _outcome_from_state(store: Pheo, state: dict[str, Any], state_key: str) -> GovernedOutcome | None:
    review_state = state.get(state_key)
    if not isinstance(review_state, dict):
        return None
    outcome_id = review_state.get("outcome_id")
    if not outcome_id:
        return None
    try:
        return GovernedOutcome(store, store._review_packet_payload(str(outcome_id)))
    except ValueError:
        return None


def _node_update(outcome: GovernedOutcome, state_key: str) -> dict[str, Any]:
    return {
        state_key: {
            "outcome_id": outcome.id,
            "status": outcome.status,
            "review_url": outcome.review_url,
            "recommended_output": outcome.recommended_output,
        }
    }


def _invoke(runnable: Any, input: Any, config: Any | None = None, **kwargs: Any) -> Any:
    if hasattr(runnable, "invoke"):
        if config is None:
            return runnable.invoke(input, **kwargs)
        return runnable.invoke(input, config=config, **kwargs)
    if callable(runnable):
        return runnable(input)
    raise TypeError("Expected a LangChain Runnable with .invoke(...) or a callable")


async def _ainvoke(runnable: Any, input: Any, config: Any | None = None, **kwargs: Any) -> Any:
    if hasattr(runnable, "ainvoke"):
        if config is None:
            return await runnable.ainvoke(input, **kwargs)
        return await runnable.ainvoke(input, config=config, **kwargs)
    return _invoke(runnable, input, config=config, **kwargs)


def _observe_result(
    store: Pheo,
    review_point: str,
    raw: Any,
    input: Any,
    *,
    output_key: str,
    output_selector: Selector | None,
    context_selector: Selector | None,
    source_selector: Selector | None,
    memory: dict[str, Any] | Callable[[], dict[str, Any]] | None,
    cycle_id: str | None,
    source_connector: str,
) -> GovernedOutcome:
    output = _select_output(raw, input, output_key, output_selector)
    context = _select_context(raw, input, context_selector)
    source = _select_source(raw, input, source_selector, source_connector, cycle_id)
    memory_payload = memory() if callable(memory) else memory
    return store.observe.output(
        review_point,
        output=output,
        context=context,
        source=source,
        memory=memory_payload,
    )


def _select_output(raw: Any, input: Any, output_key: str, selector: Selector | None) -> str:
    if selector:
        value = selector(raw, input)
        return _stringify_output(value)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in [output_key, "structured_response", "output", "answer", "response", "result", "final", "text", "content"]:
            if key in raw and raw[key] is not None:
                return _stringify_output(raw[key])
        messages = raw.get("messages")
        if isinstance(messages, list) and messages:
            return _stringify_output(_message_content(messages[-1]))
    return _stringify_output(_message_content(raw))


def _select_context(raw: Any, input: Any, selector: Selector | None) -> dict[str, Any]:
    if selector:
        selected = selector(raw, input)
        return selected if isinstance(selected, dict) else {"context": selected}
    if isinstance(input, dict):
        return input
    return {"input": _jsonable(input)}


def _default_graph_context(raw: Any, input: Any) -> dict[str, Any]:
    if not isinstance(input, dict):
        return {"input": _jsonable(input)}
    context = {key: value for key, value in input.items() if key in BUSINESS_CONTEXT_KEYS}
    return context or {"context_keys": []}


def _select_source(
    raw: Any,
    input: Any,
    selector: Selector | None,
    connector: str,
    cycle_id: str | None,
) -> dict[str, Any]:
    source = {"connector": connector}
    if cycle_id:
        source["cycle_id"] = cycle_id
    if isinstance(raw, dict):
        for key in ["run_id", "trace_id", "id"]:
            if raw.get(key):
                source["trace_id"] = str(raw[key])
                break
    if isinstance(input, dict):
        for key in ["case_id", "invoice_id", "ticket_id", "paper_id"]:
            if input.get(key):
                source["case_id"] = str(input[key])
                break
    if selector:
        selected = selector(raw, input)
        if isinstance(selected, dict):
            source.update(selected)
    return source


def _message_content(value: Any) -> Any:
    if hasattr(value, "content"):
        return _content_value(value.content)
    if hasattr(value, "content_blocks"):
        return _content_blocks_text(value.content_blocks)
    if isinstance(value, dict) and "content_blocks" in value:
        return _content_blocks_text(value["content_blocks"])
    if isinstance(value, dict) and "content" in value:
        return _content_value(value["content"])
    return value


def _stringify_output(value: Any) -> str:
    value = _message_content(value)
    if isinstance(value, str):
        return value
    return json.dumps(_jsonable(value), sort_keys=True)


def _content_value(value: Any) -> Any:
    if isinstance(value, list):
        flattened = _content_blocks_text(value)
        if flattened:
            return flattened
    return value


def _content_blocks_text(blocks: Any) -> str:
    if not isinstance(blocks, list):
        return ""
    texts = []
    for block in blocks:
        if isinstance(block, str):
            texts.append(block)
            continue
        if isinstance(block, dict):
            text = block.get("text") or block.get("content")
            if isinstance(text, str):
                texts.append(text)
            continue
        text = getattr(block, "text", None) or getattr(block, "content", None)
        if isinstance(text, str):
            texts.append(text)
    return "\n".join(texts)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)
