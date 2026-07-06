from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from pheo.core.candidates import normalize_candidates
from pheo.core.corpus import File, Folder, Text, content_hash, normalize_sources
from pheo.core.endpoint import call_openai_compatible_endpoint, safe_endpoint
from pheo.core.memory import (
    apply_judgment_memory,
    build_cycle_diff,
    build_enriched_preference_tuples,
    build_released_examples,
    build_training_manifest,
    compile_judgment_memory,
    sha256_text,
    stable_hash,
)
from pheo.core.notifications import deliver_review_packet
from pheo.core.text import summarize
from pheo.core.traces import normalize_trace_runs
from pheo.kernels import kernel_runtime
from pheo.sinks import sink_for
from pheo.storage.sqlite import SQLiteStore


class Pheo:
    def __init__(self, store: SQLiteStore):
        self.store = store
        self.store.migrate()
        self._current_workflow_id: str | None = None
        self.source = SourceNamespace(self)
        self.connection = ConnectionNamespace(self)
        self.observe = ObserveNamespace(self)
        self.review_point = ReviewPointNamespace(self)
        self.review_channel = ReviewChannelNamespace(self)
        self.export = ExportNamespace(self)

    @classmethod
    def open(cls, project: str | Path = "./.pheo"):
        return cls(SQLiteStore(project))

    def create_store(
        self,
        name: str,
        business_area: str = "",
        description: str = "",
        quality_dimensions=None,
        goal: str = "",
    ):
        return self.workflow(name, domain=business_area, objective=goal or description, quality_dimensions=quality_dimensions)

    def use_store(self, store_ref: str):
        workflow = self.get_workflow(store_ref)
        self._current_workflow_id = workflow["id"]
        return workflow

    def workflow(
        self,
        name: str,
        domain: str = "",
        objective: str = "",
        skill: str = "",
        quality_dimensions=None,
        force_new: bool = False,
    ):
        workflow = self.store.create_workflow(
            name,
            domain,
            objective,
            skill,
            quality_dimensions or [],
            force_new=force_new,
        )
        self._current_workflow_id = workflow["id"]
        return workflow

    def workflows(self):
        return self.store.list_workflows()

    def get_workflow(self, workflow_id: str | None = None):
        workflow_id = workflow_id or self._current_workflow_id
        if not workflow_id:
            workflows = self.workflows()
            if len(workflows) == 1:
                workflow_id = workflows[0]["id"]
            else:
                raise ValueError("Choose a workflow first")
        workflow = self.store.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        self._current_workflow_id = workflow["id"]
        return workflow

    def attach_corpus(self, workflow_id: str, items: list[Any], rebuild_methodology: bool | None = None):
        workflow = self.get_workflow(workflow_id)
        records = []
        for record in normalize_sources(items):
            record["content_hash"] = content_hash(record.get("text", ""))
            records.append(self.store.create_corpus_item(workflow["id"], record))
        if records:
            should_rebuild = rebuild_methodology
            if should_rebuild is None:
                methodology = self.methodology(workflow["id"]) or {}
                should_rebuild = methodology.get("status") != "approved"
            if should_rebuild:
                self.build_methodology(workflow["id"])
        return records

    def corpus(self, workflow_id: str, active_only: bool = False):
        workflow = self.get_workflow(workflow_id)
        return self.store.list_corpus(workflow["id"], active_only=active_only)

    def deactivate_corpus(self, corpus_id: str):
        return self.store.deactivate_corpus(corpus_id)

    def clear_corpus(self, workflow_id: str):
        workflow = self.get_workflow(workflow_id)
        self.store.deactivate_workflow_corpus(workflow["id"])
        if self.methodology(workflow["id"]):
            self.update_methodology(
                workflow["id"],
                summary="No active source material. Add source data and create review rules before reviewing outputs.",
                rules=[],
                avoid=[],
                actor="pheo",
                note="Active source material cleared; review rules reset to draft.",
            )
        return self.corpus(workflow["id"])

    def build_methodology(self, workflow_id: str, actor: str = "pheo", note: str = "Draft review rules generated from source material."):
        workflow = self.get_workflow(workflow_id)
        profile = kernel_runtime.synthesize_methodology(workflow, self.corpus(workflow["id"], active_only=True))
        profile = _format_methodology_profile(profile, self.corpus(workflow["id"], active_only=True), workflow)
        return self.store.save_methodology(
            workflow["id"],
            profile,
            status=profile.get("status", "draft"),
            actor=actor,
            note=note,
            metadata={
                "source_count": len(self.corpus(workflow["id"], active_only=True)),
                "goal_snapshot": workflow.get("objective") or "",
            },
        )

    def review_methodology(self, workflow_id: str, actor: str = "human", note: str = "Methodology draft reviewed.", record_event: bool = True):
        workflow = self.get_workflow(workflow_id)
        methodology = self.methodology(workflow["id"])
        if not methodology:
            methodology = self.build_methodology(workflow["id"])
        if record_event:
            self.store.record_methodology_event(
                workflow["id"],
                methodology["id"],
                "reviewed",
                actor=actor,
                note=note,
                metadata={"status": methodology.get("status")},
            )
        events = self.store.list_methodology_events(workflow["id"])
        human = _human_methodology_review(methodology, self.corpus(workflow["id"], active_only=True), workflow, events)
        return {
            "methodology": _public_methodology(methodology),
            "human_review": human,
            "events": [_public_methodology_event(item) for item in events],
            "gate": {
                "status": methodology.get("status"),
                "approved": methodology.get("status") == "approved",
                "required_before": ["observe", "score", "endpoint", "trace-import"],
                "next": "approve" if methodology.get("status") == "draft" else "update_or_rebuild",
            },
        }

    def approve_methodology(self, workflow_id: str, actor: str = "human", note: str = "", require_human_review: bool = True):
        workflow = self.get_workflow(workflow_id)
        current = self.methodology(workflow["id"]) or {}
        if current.get("status") == "approved":
            return current
        if not current:
            raise ValueError("Draft review rules before approval")
        if current.get("status") != "draft":
            raise ValueError("Review rules must be in draft status before approval")
        if require_human_review and not _has_methodology_signoff(self.store.list_methodology_events(workflow["id"]), current["id"]):
            raise ValueError(
                "Review the current methodology draft before approval. "
                f"Run: pheo methodology review --workflow {workflow['name']} --format human"
            )
        methodology = self.store.approve_methodology(
            workflow["id"],
            actor=actor,
            note=note,
            metadata={"review_pairs": len(current.get("review_pairs") or [])},
        )
        for pair in methodology.get("review_pairs") or []:
            tuple_record = self._capture_virtual_tuple(
                workflow,
                task={"goal": pair.get("prompt") or "Methodology onboarding"},
                candidates=[pair.get("chosen", ""), pair.get("rejected", "")],
                selected_index=0,
                chosen=pair.get("chosen", ""),
                rejected=[pair.get("rejected", "")],
                radar_scores={},
                reason=pair.get("rationale", ""),
                weight=float(pair.get("weight") or 0.7),
                provenance="methodology_onboarding",
            )
            self.store.create_preference_pair(
                workflow["id"],
                tuple_record["id"],
                tuple_record["run_id"],
                pair.get("prompt") or "Methodology onboarding",
                pair.get("chosen", ""),
                pair.get("rejected", ""),
                workflow.get("skill") or workflow["name"],
                float(pair.get("weight") or 0.7),
                "methodology_onboarding",
            )
        return methodology

    def reject_methodology(self, workflow_id: str, actor: str = "human", note: str = ""):
        workflow = self.get_workflow(workflow_id)
        current = self.methodology(workflow["id"])
        if not current:
            raise ValueError("Draft review rules before rejection")
        return self.store.update_methodology_status(
            workflow["id"],
            "rejected",
            actor=actor,
            note=note,
            metadata={"previous_status": current.get("status"), "status": "rejected"},
        )

    def update_methodology(
        self,
        workflow_id: str,
        summary: str = "",
        rules: list[str] | None = None,
        avoid: list[str] | None = None,
        actor: str = "human",
        note: str = "Review rules edited by reviewer.",
    ):
        workflow = self.get_workflow(workflow_id)
        current = self.methodology(workflow["id"])
        if not current:
            raise ValueError("Create review rules before editing them")
        profile = {
            **current,
            "summary": summary or current.get("summary") or "",
            "rules": rules if rules is not None else current.get("rules") or [],
            "avoid": avoid if avoid is not None else current.get("avoid") or [],
            "status": "draft",
        }
        old_rules = current.get("rules") or []
        old_avoid = current.get("avoid") or []
        new_rules = profile["rules"]
        new_avoid = profile["avoid"]
        return self.store.save_methodology(
            workflow["id"],
            profile,
            status="draft",
            actor=actor,
            note=note,
            metadata={
                "edited_from": current.get("id"),
                "previous_status": current.get("status"),
                "rule_diff": _list_diff(old_rules, new_rules),
                "avoid_diff": _list_diff(old_avoid, new_avoid),
            },
            event_type="updated",
        )

    def methodology(self, workflow_id: str):
        workflow = self.get_workflow(workflow_id)
        return self.store.get_methodology(workflow["id"])

    def governance_snapshot(self, workflow_id: str):
        workflow = self.get_workflow(workflow_id)
        methodology = self.methodology(workflow["id"]) or {}
        return {
            "schema": "pheo.snapshot.v1",
            "methodology_id": methodology.get("id") or "",
            "methodology_hash": _methodology_hash(methodology),
            "methodology_status": methodology.get("status") or "",
            "source_snapshot": [
                {
                    "id": item.get("id") or "",
                    "title": item.get("title") or item.get("source_uri") or "",
                    "content_hash": item.get("content_hash") or sha256_text(item.get("text") or ""),
                    "active": bool(item.get("active")),
                }
                for item in self.corpus(workflow["id"], active_only=True)
            ],
        }

    def create_connection(
        self,
        name: str,
        connector_type: str,
        config: dict[str, Any] | None = None,
        store_id: str | None = None,
    ):
        workflow = self.get_workflow(store_id)
        return self.store.create_connection(workflow["id"], name, connector_type, config or {})

    def connections(self, store_id: str | None = None, active_only: bool = False):
        workflow = self.get_workflow(store_id)
        return self.store.list_connections(workflow["id"], active_only=active_only)

    def get_connection(self, connection_ref: str, store_id: str | None = None):
        workflow_id = ""
        if store_id or self._current_workflow_id:
            workflow_id = self.get_workflow(store_id)["id"]
        connection = self.store.get_connection(workflow_id, connection_ref)
        if not connection:
            raise ValueError(f"Connection not found: {connection_ref}")
        self._current_workflow_id = connection["workflow_id"]
        return connection

    def create_review_point(
        self,
        name: str,
        description: str = "",
        dimensions: list[str] | None = None,
        human_review: str = "required",
        branching: str = "kernel",
        store_id: str | None = None,
        connection: str | None = None,
        connector_type: str = "",
        connector_config: dict[str, Any] | None = None,
    ):
        workflow = self.get_workflow(store_id)
        config = dict(connector_config or {})
        if connection:
            connection_record = self.get_connection(connection, workflow["id"])
            connector_type = connection_record.get("connector_type") or connector_type
            config = {**(connection_record.get("config") or {}), **config, "connection_id": connection_record["id"], "connection_name": connection_record["name"]}
        return self.store.create_review_point(
            workflow["id"],
            name,
            description=description,
            dimensions=dimensions or workflow.get("quality_dimensions") or [],
            human_review=human_review,
            branching=branching,
            connector_type=connector_type,
            connector_config=config,
        )

    def review_points(self, store_id: str | None = None, active_only: bool = False):
        workflow = self.get_workflow(store_id)
        return self.store.list_review_points(workflow["id"], active_only=active_only)

    def get_review_point(self, review_point_ref: str, store_id: str | None = None):
        workflow_id = ""
        if store_id or self._current_workflow_id:
            workflow_id = self.get_workflow(store_id)["id"]
        point = self.store.get_review_point(workflow_id, review_point_ref)
        if not point:
            raise ValueError(f"Review point not found: {review_point_ref}")
        self._current_workflow_id = point["workflow_id"]
        return point

    def set_review_channel(self, review_point: str, channel: str, **config):
        point = self.get_review_point(review_point)
        connector_config = dict(point.get("connector_config") or {})
        channels = dict(connector_config.get("review_channels") or {})
        channels[channel] = config
        connector_config["review_channels"] = channels
        return self.store.update_review_point(point["id"], connector_config=connector_config)

    def _observe_packet(
        self,
        review_point: str,
        output: str,
        context: dict[str, Any] | None = None,
        source: dict[str, Any] | None = None,
        candidates: list[Any] | None = None,
        mode: str | None = None,
        memory: dict[str, Any] | None = None,
    ):
        point = self.get_review_point(review_point)
        workflow = self.get_workflow(point["workflow_id"])
        self._ensure_approved_methodology(workflow["id"])
        observation = self.store.create_observation(
            workflow["id"],
            point["id"],
            output,
            context=context or {},
            source=source or {},
            status="observed",
        )
        candidate_items = candidates or [{"output": output, "generator": (source or {}).get("system") or "observed_output"}]
        run_task = {
            "goal": point.get("description") or f"Review output at {point['name']}",
            "review_point": point["name"],
            "context": context or {},
            "source": source or {},
            "pheo_snapshot": self.governance_snapshot(workflow["id"]),
        }
        run_mode = mode or point.get("branching") or "kernel"
        run = self.run_candidates(workflow["id"], run_task, candidate_items, mode=run_mode)
        scored = self.score_run(run["id"], memory=memory)
        self.store.update_observation_run(observation["id"], scored["id"])
        packet = self.store.create_review_packet(
            workflow["id"],
            point["id"],
            observation["id"],
            scored["id"],
            status="pending_review" if point.get("human_review") != "optional" else "review_available",
            review_url="/review/{packet_id}",
            delivery=_review_delivery(point),
        )
        payload = self._review_packet_payload(packet["id"])
        delivery = deliver_review_packet(payload)
        if delivery != (packet.get("delivery") or {}):
            self.store.update_review_packet_delivery(packet["id"], delivery)
            payload = self._review_packet_payload(packet["id"])
        return payload

    def observe_endpoint(
        self,
        review_point: str,
        connection: str | None = None,
        prompt: str = "",
        messages: list[dict[str, Any]] | None = None,
        system: str = "",
        context: dict[str, Any] | None = None,
        source: dict[str, Any] | None = None,
        endpoint_url: str = "",
        model: str = "",
        api_key: str = "",
        api_key_env: str = "OPENROUTER_API_KEY",
        temperature: float = 0.7,
        memory: dict[str, Any] | None = None,
    ):
        point = self.get_review_point(review_point)
        config = dict(point.get("connector_config") or {})
        if connection:
            config = {**(self.get_connection(connection, point["workflow_id"]).get("config") or {}), **config}
        endpoint_url = endpoint_url or config.get("endpoint_url") or ""
        model = model or config.get("model") or ""
        api_key_env = config.get("api_key_env") or api_key_env or "OPENROUTER_API_KEY"
        api_key = api_key or os.environ.get(api_key_env, "")
        if not model:
            raise ValueError("Model is required for an OpenAI-compatible endpoint connection")
        if not api_key:
            raise ValueError(f"API key is required. Pass api_key or set ${api_key_env}.")
        payload_messages = messages or _messages(system, prompt, context or {})
        output = call_openai_compatible_endpoint(
            {
                "endpoint_url": endpoint_url,
                "api_key": api_key,
                "model": model,
                "messages": payload_messages,
                "temperature": temperature,
                "task": context or {},
            }
        )
        return self._observe_packet(
            point["id"],
            output=output,
            context=context or {},
            source={
                "connector": "openai_compatible_endpoint",
                "endpoint": safe_endpoint(endpoint_url),
                "model": model,
                **(source or {}),
            },
            mode="kernel",
            memory=memory,
        )

    def observe_traces(self, review_point: str, source_type: str, payload: Any, task: dict[str, Any] | None = None):
        point = self.get_review_point(review_point)
        packets = []
        for spec in normalize_trace_runs(source_type, payload):
            run_task = task or spec.get("task") or {}
            for candidate in spec.get("candidates") or []:
                packets.append(
                    self._observe_packet(
                        point["id"],
                        candidate.get("output", ""),
                        context=run_task,
                        source={
                            "connector": source_type,
                            "generator": candidate.get("generator") or source_type,
                            **(candidate.get("metadata") or {}),
                        },
                        candidates=spec.get("candidates") or [candidate],
                        mode=f"trace:{source_type}",
                    )
                )
                break
        return packets

    def review(
        self,
        packet_id: str,
        selected_index: int,
        action: str = "approve",
        reason: str = "",
        corrected_output: str = "",
        weight: float | None = None,
        author_id: str = "",
    ):
        packet = self.store.get_review_packet(packet_id)
        if not packet:
            raise ValueError(f"Review packet not found: {packet_id}")
        if packet.get("status") == "reviewed":
            existing = self._review_result_for_packet(packet)
            if existing:
                return existing
            raise ValueError(f"Review packet already reviewed: {packet_id}")
        result = self.capture_decision(
            packet["run_id"],
            selected_index,
            action=action,
            reason=reason,
            corrected_output=corrected_output,
            weight=weight,
            author_id=author_id,
            packet_id=packet_id,
        )
        self.store.update_review_packet_status(packet_id, "reviewed")
        result["packet"] = self.store.get_review_packet(packet_id)
        return result

    def _review_result_for_packet(self, packet: dict[str, Any]):
        run = self.store.get_run(packet["run_id"])
        if not run:
            return None
        workflow = self.get_workflow(run["workflow_id"])
        decisions = [item for item in self.store.list_decisions(workflow["id"]) if item.get("run_id") == run["id"]]
        if not decisions:
            return None
        decision = decisions[0]
        tuples = [item for item in self.store.list_preference_tuples(workflow["id"]) if item.get("decision_id") == decision["id"]]
        tuple_record = tuples[0] if tuples else None
        return {
            "decision": decision,
            "tuple": tuple_record,
            "pairs": self.store.list_preference_pairs(workflow["id"]),
            "receipt": self.store.get_release_receipt_for_decision(decision["id"]),
            "packet": packet,
        }

    def run_candidates(self, workflow_id: str, task: dict[str, Any], candidates: list[Any], mode: str = "external"):
        workflow = self.get_workflow(workflow_id)
        task = dict(task or {})
        if mode != "methodology" and "pheo_snapshot" not in task:
            methodology = self.methodology(workflow["id"]) or {}
            if methodology.get("status") == "approved":
                task["pheo_snapshot"] = self.governance_snapshot(workflow["id"])
        normalized = normalize_candidates(candidates)
        if mode == "kernel" and len(normalized) == 1:
            methodology = self.methodology(workflow["id"]) or {}
            normalized.extend(kernel_runtime.branch_candidates(normalized[0]["output"], task, methodology))
            normalized = normalize_candidates(normalized)
            mode = "kernel"
        run = self.store.create_run(workflow["id"], task or {}, mode=mode)
        for index, candidate in enumerate(normalized):
            self.store.create_candidate(
                workflow["id"],
                run["id"],
                index,
                candidate["output"],
                candidate.get("generator", "external"),
                candidate.get("metadata") or {},
            )
        return {**run, "candidates": self.store.list_candidates(run["id"])}

    def import_traces(self, workflow_id: str, source_type: str, payload: Any, task: dict[str, Any] | None = None, score: bool = True):
        workflow = self.get_workflow(workflow_id)
        specs = normalize_trace_runs(source_type, payload)
        runs = []
        for spec in specs:
            run_task = task or spec.get("task") or {}
            run = self.run_candidates(
                workflow["id"],
                run_task,
                spec.get("candidates") or [],
                mode=f"trace:{source_type}",
            )
            runs.append(self.score_run(run["id"]) if score else run)
        return runs

    def runs(self, workflow_id: str):
        workflow = self.get_workflow(workflow_id)
        return self.store.list_runs(workflow["id"])

    def run(self, run_id: str):
        run = self.store.get_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")
        return {**run, "candidates": self.store.list_candidates(run_id)}

    def score_run(self, run_id: str, memory: dict[str, Any] | None = None):
        run = self.store.get_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")
        workflow = self.get_workflow(run["workflow_id"])
        if run.get("mode") != "methodology":
            self._ensure_approved_methodology(workflow["id"])
        candidates = self.store.list_candidates(run_id)
        corpus_texts = [item["text"] for item in self.corpus(workflow["id"], active_only=True)]
        methodology = self.methodology(workflow["id"]) or {}
        ranked = kernel_runtime.score_candidates(candidates, run["task"], corpus_texts, methodology)
        if memory:
            ranked = apply_judgment_memory(ranked, run["task"], memory)
        updated = []
        for item in ranked:
            scores = dict(item.get("scores") or {})
            scores["explanation"] = _score_explanation(item, run["task"], corpus_texts, methodology)
            updated.append(self.store.update_candidate_scores(item["id"], scores, item.get("rank"), item.get("recommended", False)))
        self.store.update_run_status(run_id, "scored")
        return {**self.store.get_run(run_id), "candidates": sorted(updated, key=lambda item: item["index"])}

    def capture_decision(
        self,
        run_id: str,
        selected_index: int,
        action: str = "approve",
        reason: str = "",
        corrected_output: str = "",
        weight: float | None = None,
        author_id: str = "",
        packet_id: str = "",
    ):
        run = self.store.get_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")
        workflow = self.get_workflow(run["workflow_id"])
        candidates = self.store.list_candidates(run_id)
        if selected_index < 0 or selected_index >= len(candidates):
            raise ValueError("selected_index is outside the candidate list")
        selected = candidates[selected_index]
        provenance = "human_correction" if action in {"edit", "correct"} or corrected_output else "human_triage"
        chosen = corrected_output.strip() if corrected_output else selected["output"]
        if action == "reject" and not corrected_output:
            alternatives = [candidate for candidate in candidates if candidate["index"] != selected_index]
            alternatives = sorted(alternatives, key=lambda item: item.get("scores", {}).get("mean_score", 0), reverse=True)
            chosen = alternatives[0]["output"] if alternatives else ""
            rejected = [selected["output"]]
            selected_for_tuple = alternatives[0]["index"] if alternatives else selected_index
        else:
            rejected = [candidate["output"] for candidate in candidates if candidate["index"] != selected_index]
            selected_for_tuple = selected_index
        if corrected_output:
            rejected = [candidate["output"] for candidate in candidates]
        decision_weight = weight if weight is not None else (1.0 if provenance == "human_correction" else 0.9 if action == "approve" else 0.6)
        decision = self.store.create_decision(
            workflow["id"],
            run_id,
            action,
            selected_index,
            chosen,
            rejected,
            reason,
            decision_weight,
            provenance,
            author_id,
        )
        radar_scores = {str(candidate["index"]): candidate.get("scores", {}) for candidate in candidates}
        tuple_record = self.store.create_preference_tuple(
            workflow["id"],
            run_id,
            decision["id"],
            run["task"],
            [candidate["output"] for candidate in candidates],
            selected_for_tuple,
            chosen,
            rejected,
            radar_scores,
            decision_weight,
            provenance,
            reason,
        )
        for rejected_output in rejected:
            self.store.create_preference_pair(
                workflow["id"],
                tuple_record["id"],
                run_id,
                _task_prompt(run["task"]),
                chosen,
                rejected_output,
                workflow.get("skill") or workflow["name"],
                _pair_weight(chosen, rejected_output, decision_weight),
                provenance,
            )
        receipt = None
        if packet_id:
            receipt = self._create_release_receipt(packet_id, run, candidates, decision, tuple_record)
        self.store.update_run_status(run_id, "decision_captured")
        return {
            "decision": decision,
            "tuple": tuple_record,
            "pairs": self.store.list_preference_pairs(workflow["id"]),
            "receipt": receipt,
        }

    def preference_store(self, workflow_id: str):
        workflow = self.get_workflow(workflow_id)
        runs = [self.run(item["id"]) for item in self.store.list_runs(workflow["id"])]
        return {
            "workflow": workflow,
            "connections": self.connections(workflow["id"]),
            "review_points": self.store.list_review_points(workflow["id"]),
            "observations": self.store.list_observations(workflow["id"]),
            "review_packets": self.store.list_review_packets(workflow["id"]),
            "corpus": self.corpus(workflow["id"]),
            "methodology": self.methodology(workflow["id"]),
            "methodology_events": self.store.list_methodology_events(workflow["id"]),
            "runs": runs,
            "decisions": self.store.list_decisions(workflow["id"]),
            "preference_tuples": self.store.list_preference_tuples(workflow["id"]),
            "preference_pairs": self.store.list_preference_pairs(workflow["id"]),
            "release_receipts": self.store.list_release_receipts(workflow["id"]),
        }

    def release_receipts(self, workflow_id: str):
        workflow = self.get_workflow(workflow_id)
        return self.store.list_release_receipts(workflow["id"])

    def memory(self, workflow_id: str, organic_only: bool = True):
        workflow = self.get_workflow(workflow_id)
        return compile_judgment_memory(workflow, self._enriched_tuples(workflow["id"]), organic_only=organic_only)

    def training_manifest(self, workflow_id: str, filters: dict[str, Any] | None = None):
        workflow = self.get_workflow(workflow_id)
        enriched = self._enriched_tuples(workflow["id"])
        examples = build_released_examples(workflow, self.store.list_review_points(workflow["id"]), self.methodology(workflow["id"]), enriched)
        return build_training_manifest(
            workflow,
            enriched,
            self.store.list_preference_pairs(workflow["id"]),
            examples,
            self.store.list_release_receipts(workflow["id"]),
            filters,
            current_methodology_hash=_methodology_hash(self.methodology(workflow["id"])),
        )

    def cycle_diff(self, workflow_id: str, before: str = "cycle_1", after: str = "cycle_2"):
        workflow = self.get_workflow(workflow_id)
        runs = []
        for run in self.runs(workflow["id"]):
            runs.append({**run, "candidates": self.store.list_candidates(run["id"])})
        return build_cycle_diff(workflow, runs, before=before, after=after)

    def apply_memory(self, run_id: str, memory: dict[str, Any] | None = None):
        run = self.store.get_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")
        workflow = self.get_workflow(run["workflow_id"])
        return self.score_run(run_id, memory=memory or self.memory(workflow["id"]))

    def memory_pack(self, workflow_id: str, organic_only: bool = False):
        workflow = self.get_workflow(workflow_id)
        runs = []
        for run in self.runs(workflow["id"]):
            runs.append({**run, "candidates": self.store.list_candidates(run["id"])})
        all_runs = list(runs)
        decisions = self.store.list_decisions(workflow["id"])
        pairs = self.store.list_preference_pairs(workflow["id"])
        tuples = self.store.list_preference_tuples(workflow["id"])
        receipts = self.store.list_release_receipts(workflow["id"])
        if organic_only:
            decisions = _organic_items(decisions)
            pairs = _organic_items(pairs)
            tuples = _organic_items(tuples)
            organic_run_ids = {item.get("run_id") for item in decisions} | {item.get("run_id") for item in pairs} | {item.get("run_id") for item in tuples}
            runs = [run for run in runs if run["id"] in organic_run_ids]
        memory_summary = _memory_summary(decisions, pairs, tuples)
        corpus = self.corpus(workflow["id"])
        methodology = self.methodology(workflow["id"])
        methodology_events = self.store.list_methodology_events(workflow["id"])
        review_points = self.store.list_review_points(workflow["id"])
        connections = self.connections(workflow["id"])
        observations = self.store.list_observations(workflow["id"])
        review_packets = self.store.list_review_packets(workflow["id"])
        enriched_tuples = build_enriched_preference_tuples(workflow, runs, decisions, tuples, receipts)
        preferences = [
            {
                "pair_id": pair.get("id"),
                "tuple_id": pair.get("source_tuple_id"),
                "prompt": _public_text(pair["prompt"]),
                "chosen": _public_text(pair["chosen_output"]),
                "rejected": _public_text(pair["rejected_output"]),
                "weight": pair.get("organic_weight"),
                "skill": pair.get("skill"),
                "provenance": pair.get("provenance"),
                "methodology_id": _tuple_methodology_id(pair.get("source_tuple_id"), enriched_tuples),
                "methodology_hash": _tuple_methodology_hash(pair.get("source_tuple_id"), enriched_tuples),
            }
            for pair in pairs
        ]
        examples = build_released_examples(workflow, review_points, methodology, enriched_tuples)
        judgment_memory = compile_judgment_memory(workflow, enriched_tuples, organic_only=organic_only)
        training_manifest = build_training_manifest(
            workflow,
            enriched_tuples,
            pairs,
            examples,
            receipts,
            current_methodology_hash=_methodology_hash(methodology),
        )
        cycle_diff = build_cycle_diff(workflow, all_runs)
        check_cases = [
            {
                "workflow_id": workflow["id"],
                "run_id": run["id"],
                "task": _safe_public_json(run["task"]),
                "candidate_count": len(run["candidates"]),
                "recommended_candidate": _recommended_index(run["candidates"]),
            }
            for run in runs
        ]
        return {
            "pack_type": "pheo_pack",
            "workflow": workflow,
            "store": workflow,
            "readiness": _readiness(decisions, pairs, corpus, runs),
            "memory_summary": memory_summary,
            "export_filter": {"organic_only": organic_only},
            "methodology": _public_methodology(methodology),
            "workflow_graph": _workflow_graph(workflow, connections, review_points, observations, review_packets, runs, decisions),
            "artifacts": {
                "connections": connections,
                "review_points": review_points,
                "observations": [_public_observation(item) for item in observations],
                "review_packets": review_packets,
                "preference_pairs": preferences,
                "sft_jsonl": _sft_rows(examples),
                "dpo_jsonl": _dpo_rows(preferences),
                "review_examples": examples,
                "check_cases": check_cases,
                "candidate_quality": [_public_candidate(candidate) for run in runs for candidate in run["candidates"]],
                "decision_log": [_public_decision(item) for item in decisions],
                "methodology_events": [_public_methodology_event(item) for item in methodology_events],
                "preference_tuples": enriched_tuples,
                "release_receipts": receipts,
                "judgment_memory": judgment_memory,
                "training_manifest": training_manifest,
                "cycle_diff": cycle_diff,
                "source_corpus": corpus,
                "workflow_runs": [_public_run(item) for item in runs],
            },
            "critique": _critique(decisions, pairs, corpus, runs),
        }

    def export_memory_pack(self, workflow_id: str, out: str | Path, organic_only: bool = False):
        pack = self.memory_pack(workflow_id, organic_only=organic_only)
        sink = sink_for(out)
        if hasattr(sink, "write_pack"):
            sink.write_pack(pack)
            return pack
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "memory_pack.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
        (out_path / "workflow.graph.json").write_text(json.dumps(pack["workflow_graph"], indent=2), encoding="utf-8")
        _write_jsonl(out_path / "preference_pairs.jsonl", pack["artifacts"]["preference_pairs"])
        _write_jsonl(out_path / "sft.jsonl", pack["artifacts"]["sft_jsonl"])
        _write_jsonl(out_path / "dpo.jsonl", pack["artifacts"]["dpo_jsonl"])
        _write_jsonl(out_path / "preference_tuples.jsonl", pack["artifacts"]["preference_tuples"])
        _write_jsonl(out_path / "review_examples.jsonl", pack["artifacts"]["review_examples"])
        _write_jsonl(out_path / "check_cases.jsonl", pack["artifacts"]["check_cases"])
        _write_jsonl(out_path / "observations.jsonl", pack["artifacts"]["observations"])
        _write_jsonl(out_path / "decisions.jsonl", pack["artifacts"]["decision_log"])
        _write_jsonl(out_path / "methodology_events.jsonl", pack["artifacts"]["methodology_events"])
        _write_jsonl(out_path / "release_receipts.jsonl", pack["artifacts"]["release_receipts"])
        (out_path / "judgment_memory.json").write_text(json.dumps(pack["artifacts"]["judgment_memory"], indent=2), encoding="utf-8")
        (out_path / "training_manifest.json").write_text(json.dumps(pack["artifacts"]["training_manifest"], indent=2), encoding="utf-8")
        (out_path / "cycle_diff.json").write_text(json.dumps(pack["artifacts"]["cycle_diff"], indent=2), encoding="utf-8")
        return pack

    def backfill_release_receipts(self, workflow_id: str):
        workflow = self.get_workflow(workflow_id)
        created = []
        for decision in self.store.list_decisions(workflow["id"]):
            if self.store.get_release_receipt_for_decision(decision["id"]):
                continue
            run = self.store.get_run(decision["run_id"])
            if not run:
                continue
            candidates = self.store.list_candidates(run["id"])
            tuple_ = next((item for item in self.store.list_preference_tuples(workflow["id"]) if item.get("decision_id") == decision["id"]), None)
            if not tuple_:
                continue
            packet = next((item for item in self.store.list_review_packets(workflow["id"]) if item.get("run_id") == run["id"]), {})
            created.append(self._create_release_receipt(packet.get("id", ""), run, candidates, decision, tuple_, backfilled=True))
        return [item for item in created if item]

    def _enriched_tuples(self, workflow_id: str):
        workflow = self.get_workflow(workflow_id)
        runs = []
        for run in self.runs(workflow["id"]):
            runs.append({**run, "candidates": self.store.list_candidates(run["id"])})
        return build_enriched_preference_tuples(
            workflow,
            runs,
            self.store.list_decisions(workflow["id"]),
            self.store.list_preference_tuples(workflow["id"]),
            self.store.list_release_receipts(workflow["id"]),
        )

    def _create_release_receipt(self, packet_id: str, run: dict[str, Any], candidates: list[dict[str, Any]], decision: dict[str, Any], tuple_record: dict[str, Any], backfilled: bool = False):
        workflow = self.get_workflow(run["workflow_id"])
        packet = self.store.get_review_packet(packet_id) if packet_id else {}
        observation = self.store.get_observation(packet.get("observation_id")) if packet else {}
        recommended = next((candidate for candidate in candidates if candidate.get("recommended")), None)
        if not recommended and candidates:
            recommended = candidates[int(decision.get("selected_index") or 0)] if int(decision.get("selected_index") or 0) < len(candidates) else candidates[0]
        snapshot = (run.get("task") or {}).get("pheo_snapshot") or self.governance_snapshot(workflow["id"])
        released_output = decision.get("chosen_output") if _is_released_action(decision.get("action"), decision.get("chosen_output")) else ""
        return self.store.create_release_receipt(
            workflow["id"],
            packet_id,
            run["id"],
            tuple_record["id"],
            decision["id"],
            raw_observed_output=(observation or {}).get("output") or "",
            recommended_output=(recommended or {}).get("output") or "",
            reviewer_action=decision.get("action") or "",
            reviewer_reason=decision.get("reason") or "",
            released_output=released_output,
            methodology_snapshot={key: snapshot.get(key) for key in ("schema", "methodology_id", "methodology_hash", "methodology_status")},
            source_snapshot=snapshot.get("source_snapshot") or [],
            candidate_count=len(candidates),
            memory_entry_id="decision_" + decision["id"],
            reviewer_id=decision.get("author_id") or "",
            backfilled=backfilled,
            created_at=decision.get("created_at") or "",
        )

    def export_preferences(self, workflow_id: str, organic_only: bool = False) -> str:
        return _jsonl(self.memory_pack(workflow_id, organic_only=organic_only)["artifacts"]["preference_pairs"])

    def export_examples(self, workflow_id: str, organic_only: bool = False) -> str:
        return _jsonl(self.memory_pack(workflow_id, organic_only=organic_only)["artifacts"]["review_examples"])

    def export_sft(self, workflow_id: str, organic_only: bool = False) -> str:
        return _jsonl(self.memory_pack(workflow_id, organic_only=organic_only)["artifacts"]["sft_jsonl"])

    def export_dpo(self, workflow_id: str, organic_only: bool = False) -> str:
        return _jsonl(self.memory_pack(workflow_id, organic_only=organic_only)["artifacts"]["dpo_jsonl"])

    def export_check_cases(self, workflow_id: str, organic_only: bool = False) -> str:
        return _jsonl(self.memory_pack(workflow_id, organic_only=organic_only)["artifacts"]["check_cases"])

    def _capture_virtual_tuple(self, workflow, task, candidates, selected_index, chosen, rejected, radar_scores, reason, weight, provenance):
        run = self.store.create_run(workflow["id"], task, mode="methodology")
        for index, output in enumerate(candidates):
            self.store.create_candidate(workflow["id"], run["id"], index, output, "methodology_onboarding", {})
        decision = self.store.create_decision(workflow["id"], run["id"], "approve", selected_index, chosen, rejected, reason, weight, provenance)
        return self.store.create_preference_tuple(
            workflow["id"],
            run["id"],
            decision["id"],
            task,
            candidates,
            selected_index,
            chosen,
            rejected,
            radar_scores,
            weight,
            provenance,
            reason,
        )

    def _ensure_methodology(self, workflow_id: str):
        if not self.methodology(workflow_id):
            return self.build_methodology(workflow_id)
        return self.methodology(workflow_id)

    def _ensure_approved_methodology(self, workflow_id: str):
        methodology = self._ensure_methodology(workflow_id)
        if methodology.get("status") != "approved":
            raise ValueError("Approve review rules before observing outputs at a review point")
        return methodology

    def _review_packet_payload(self, packet_id: str):
        packet = self.store.get_review_packet(packet_id)
        if not packet:
            raise ValueError(f"Review packet not found: {packet_id}")
        point = self.store.get_review_point(packet["workflow_id"], packet["review_point_id"])
        observation = self.store.get_observation(packet["observation_id"])
        run = self.run(packet["run_id"])
        recommended = next((candidate for candidate in run["candidates"] if candidate.get("recommended")), None)
        return {
            "workflow": self.store.get_workflow(packet["workflow_id"]),
            "packet": packet,
            "review_point": point,
            "observation": observation,
            "run": run,
            "candidates": run["candidates"],
            "recommended": recommended,
            "review_url": packet.get("review_url"),
            "status": packet.get("status"),
        }


class PendingReview(RuntimeError):
    def __init__(self, outcome_id: str, review_url: str = "", status: str = "pending_review"):
        self.outcome_id = outcome_id
        self.review_url = review_url
        self.status = status
        message = f"Outcome {outcome_id} is {status}; human release is required."
        if review_url:
            message += f" Review at {review_url}."
        super().__init__(message)


class GovernedOutcome:
    """Developer-facing result for an observed control point."""

    def __init__(self, pheo: Pheo, payload: dict[str, Any]):
        self._pheo = pheo
        self._payload = payload

    def __getitem__(self, key: str):
        return self._payload[key]

    def get(self, key: str, default: Any = None):
        return self._payload.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload,
            "outcome": {
                "id": self.id,
                "status": self.status,
                "review_url": self.review_url,
                "observed_output": self.observed_output,
                "recommended_output": self.recommended_output,
                "released_output": self.released_output,
            },
        }

    def refresh(self):
        self._payload = self._pheo._review_packet_payload(self.id)
        return self

    @property
    def id(self) -> str:
        return (self._payload.get("packet") or {}).get("id", "")

    @property
    def status(self) -> str:
        return (self._payload.get("packet") or {}).get("status") or self._payload.get("status") or ""

    @property
    def review_url(self) -> str:
        return self._payload.get("review_url") or (self._payload.get("packet") or {}).get("review_url") or ""

    @property
    def observed_output(self) -> str:
        return (self._payload.get("observation") or {}).get("output") or ""

    @property
    def candidates(self) -> list[dict[str, Any]]:
        return [_record(candidate) for candidate in self._payload.get("candidates") or []]

    @property
    def recommended(self) -> dict[str, Any] | None:
        recommended = self._payload.get("recommended")
        return _record(recommended) if recommended else None

    @property
    def recommended_output(self) -> str:
        recommended = self.recommended or {}
        return recommended.get("output") or self.observed_output

    @property
    def scores(self) -> dict[str, Any]:
        return {str(candidate.get("index")): candidate.get("scores") or {} for candidate in self.candidates}

    @property
    def decision(self) -> dict[str, Any] | None:
        packet = self._payload.get("packet") or {}
        workflow_id = packet.get("workflow_id")
        run_id = packet.get("run_id")
        if not workflow_id or not run_id:
            return None
        for decision in self._pheo.store.list_decisions(workflow_id):
            if decision.get("run_id") == run_id:
                return decision
        return None

    @property
    def released_output(self) -> str | None:
        decision = self.decision
        if not decision:
            return None
        if decision.get("action") in {"approve", "edit", "correct", "reject"}:
            return decision.get("chosen_output") or None
        return None

    def require_released(self) -> str:
        self.refresh()
        output = self.released_output
        if output:
            return output
        raise PendingReview(self.id, self.review_url, self.status)

    def require_approved(self) -> str:
        return self.require_released()


class ObserveNamespace:
    def __init__(self, pheo: Pheo):
        self._pheo = pheo

    def __call__(
        self,
        review_point: str,
        output: str,
        context: dict[str, Any] | None = None,
        source: dict[str, Any] | None = None,
        candidates: list[Any] | None = None,
        mode: str | None = None,
        memory: dict[str, Any] | None = None,
    ):
        packet = self._pheo._observe_packet(
            review_point,
            output=output,
            context=context,
            source=source,
            candidates=candidates,
            mode=mode,
            memory=memory,
        )
        return GovernedOutcome(self._pheo, packet)

    def output(
        self,
        review_point: str,
        output: str,
        context: dict[str, Any] | None = None,
        source: dict[str, Any] | None = None,
        candidates: list[Any] | None = None,
        mode: str | None = None,
        memory: dict[str, Any] | None = None,
    ) -> GovernedOutcome:
        packet = self._pheo._observe_packet(
            review_point,
            output=output,
            context=context,
            source=source,
            candidates=candidates,
            mode=mode,
            memory=memory,
        )
        return GovernedOutcome(self._pheo, packet)

    def endpoint(
        self,
        review_point: str,
        connection: str | None = None,
        prompt: str = "",
        messages: list[dict[str, Any]] | None = None,
        system: str = "",
        context: dict[str, Any] | None = None,
        source: dict[str, Any] | None = None,
        endpoint_url: str = "",
        model: str = "",
        api_key: str = "",
        api_key_env: str = "OPENROUTER_API_KEY",
        temperature: float = 0.7,
        memory: dict[str, Any] | None = None,
    ) -> GovernedOutcome:
        packet = self._pheo.observe_endpoint(
            review_point,
            connection=connection,
            prompt=prompt,
            messages=messages,
            system=system,
            context=context,
            source=source,
            endpoint_url=endpoint_url,
            model=model,
            api_key=api_key,
            api_key_env=api_key_env,
            temperature=temperature,
            memory=memory,
        )
        return GovernedOutcome(self._pheo, packet)


class SourceNamespace:
    def __init__(self, pheo: Pheo):
        self._pheo = pheo

    def add(self, items: Any, store_id: str | None = None):
        workflow = self._pheo.get_workflow(store_id)
        if not isinstance(items, list):
            items = [items]
        return self._pheo.attach_corpus(workflow["id"], items)

    def add_text(self, title: str, text: str, tags: list[str] | None = None, store_id: str | None = None):
        return self.add(Text(title, text, tags or []), store_id=store_id)

    def list(self, store_id: str | None = None, active_only: bool = False):
        workflow = self._pheo.get_workflow(store_id)
        return self._pheo.corpus(workflow["id"], active_only=active_only)

    def deactivate(self, source_id: str):
        return self._pheo.deactivate_corpus(source_id)


class ConnectionNamespace:
    def __init__(self, pheo: Pheo):
        self._pheo = pheo

    def add(
        self,
        name: str,
        connector_type: str,
        config: dict[str, Any] | None = None,
        store_id: str | None = None,
    ):
        return self._pheo.create_connection(name, connector_type, config or {}, store_id=store_id)

    def add_endpoint(
        self,
        name: str,
        endpoint_url: str,
        model: str = "",
        api_key_env: str = "OPENROUTER_API_KEY",
        store_id: str | None = None,
    ):
        return self.add(
            name,
            "openai_compatible_endpoint",
            {"endpoint_url": endpoint_url, "model": model, "api_key_env": api_key_env},
            store_id=store_id,
        )

    def add_langchain(self, name: str = "langchain", store_id: str | None = None, **config):
        return self.add(name, "langchain", config, store_id=store_id)

    def add_langsmith(self, name: str = "langsmith", store_id: str | None = None, **config):
        return self.add(name, "langsmith", config, store_id=store_id)

    def add_weave(self, name: str = "weave", store_id: str | None = None, **config):
        return self.add(name, "weave", config, store_id=store_id)

    def add_noveum(self, name: str = "noveum", store_id: str | None = None, **config):
        return self.add(name, "noveum", config, store_id=store_id)

    def add_llamaindex(self, name: str = "llamaindex", store_id: str | None = None, **config):
        return self.add(name, "llamaindex", config, store_id=store_id)

    def add_vllm(self, name: str = "vllm", endpoint_url: str = "", model: str = "", store_id: str | None = None, **config):
        return self.add(name, "vllm", {"endpoint_url": endpoint_url, "model": model, **config}, store_id=store_id)

    def add_huggingface(self, name: str = "huggingface", endpoint_url: str = "", model: str = "", store_id: str | None = None, **config):
        return self.add(name, "huggingface", {"endpoint_url": endpoint_url, "model": model, **config}, store_id=store_id)

    def list(self, store_id: str | None = None):
        return self._pheo.connections(store_id)

    def get(self, name: str, store_id: str | None = None):
        return self._pheo.get_connection(name, store_id=store_id)


class ReviewPointNamespace:
    def __init__(self, pheo: Pheo):
        self._pheo = pheo

    def __call__(self, name: str):
        def decorator(function):
            def wrapped(*args, **kwargs):
                output = function(*args, **kwargs)
                return self._pheo.observe.output(
                    name,
                    output=str(output),
                    context={"args": _safe_json(args), "kwargs": _safe_json(kwargs)},
                    source={"connector": "python_decorator", "function": getattr(function, "__name__", "callable")},
                )

            wrapped.__name__ = getattr(function, "__name__", "pheo_wrapped")
            wrapped.__doc__ = getattr(function, "__doc__", None)
            return wrapped

        return decorator

    def create(
        self,
        name: str,
        description: str = "",
        dimensions: list[str] | None = None,
        human_review: str = "required",
        branching: str = "kernel",
        connection: str | None = None,
        store_id: str | None = None,
    ):
        return self._pheo.create_review_point(
            name,
            description=description,
            dimensions=dimensions,
            human_review=human_review,
            branching=branching,
            connection=connection,
            store_id=store_id,
        )

    def list(self, store_id: str | None = None):
        return self._pheo.review_points(store_id)

    def get(self, name: str, store_id: str | None = None):
        return self._pheo.get_review_point(name, store_id=store_id)


class ReviewChannelNamespace:
    def __init__(self, pheo: Pheo):
        self._pheo = pheo

    def email(self, review_point: str, to: list[str] | str, subject: str = "", instructions: str = ""):
        recipients = [to] if isinstance(to, str) else list(to)
        return self._pheo.set_review_channel(review_point, "email", to=recipients, subject=subject, instructions=instructions)

    def webhook(
        self,
        review_point: str,
        url: str = "",
        url_env: str = "",
        headers: dict[str, str] | None = None,
        headers_env: str = "",
        instructions: str = "",
    ):
        return self._pheo.set_review_channel(
            review_point,
            "webhook",
            url=url,
            url_env=url_env,
            headers=headers or {},
            headers_env=headers_env,
            instructions=instructions,
        )

    def slack(self, review_point: str, webhook_url: str = "", webhook_url_env: str = "PHEO_SLACK_WEBHOOK_URL", instructions: str = ""):
        return self._pheo.set_review_channel(
            review_point,
            "slack",
            webhook_url=webhook_url,
            webhook_url_env=webhook_url_env,
            instructions=instructions,
        )

    def telegram(
        self,
        review_point: str,
        chat_id: str = "",
        bot_token: str = "",
        bot_token_env: str = "PHEO_TELEGRAM_BOT_TOKEN",
        chat_id_env: str = "",
        instructions: str = "",
    ):
        return self._pheo.set_review_channel(
            review_point,
            "telegram",
            chat_id=chat_id,
            chat_id_env=chat_id_env,
            bot_token=bot_token,
            bot_token_env=bot_token_env,
            instructions=instructions,
        )


class ExportNamespace:
    def __init__(self, pheo: Pheo):
        self._pheo = pheo

    def memory_pack(self, out: str | Path, store_id: str | None = None, organic_only: bool = False):
        workflow = self._pheo.get_workflow(store_id)
        return self._pheo.export_memory_pack(workflow["id"], out, organic_only=organic_only)

    def graph(self, out: str | Path, store_id: str | None = None):
        workflow = self._pheo.get_workflow(store_id)
        pack = self._pheo.memory_pack(workflow["id"])
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(pack["workflow_graph"], indent=2), encoding="utf-8")
        return pack["workflow_graph"]


def _review_delivery(point: dict[str, Any]) -> dict[str, Any]:
    channels = (point.get("connector_config") or {}).get("review_channels") or {}
    return {
        "human_review": point.get("human_review") or "required",
        "channels": channels,
        "delivery_status": "configured" if channels else "local_review",
    }


def _messages(system: str, prompt: str, context: dict[str, Any]) -> list[dict[str, str]]:
    user_prompt = prompt or context.get("goal") or context.get("client_request") or "Generate a workflow output for review."
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": str(user_prompt)})
    return messages


def _safe_json(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, tuple):
            return [_safe_json(item) for item in value]
        if isinstance(value, list):
            return [_safe_json(item) for item in value]
        if isinstance(value, dict):
            return {str(key): _safe_json(item) for key, item in value.items()}
        return repr(value)


def _public_methodology(methodology: dict[str, Any] | None):
    if not methodology:
        return None
    allowed = {
        "id",
        "workflow_id",
        "summary",
        "rules",
        "avoid",
        "status",
        "confidence",
        "approved_at",
        "approved_by",
        "approval_note",
        "created_at",
        "updated_at",
        "source_map",
    }
    output = {key: methodology.get(key) for key in allowed if key in methodology}
    for key in ("summary", "approval_note"):
        if key in output:
            output[key] = _public_text(output[key])
    for key in ("rules", "avoid"):
        if key in output:
            output[key] = [_public_text(item) for item in output[key] or []]
    if "source_map" in output:
        output["source_map"] = {str(key): _public_text(value) for key, value in (output.get("source_map") or {}).items()}
    return output


def _format_methodology_profile(profile: dict[str, Any], corpus_items: list[dict[str, Any]], workflow: dict[str, Any]) -> dict[str, Any]:
    formatted = dict(profile or {})
    formatted["rules"] = _normalize_rule_list(formatted.get("rules") or [], limit=8)
    formatted["avoid"] = _normalize_rule_list(formatted.get("avoid") or [], limit=8)
    formatted["source_map"] = _source_map(formatted["rules"] + formatted["avoid"], corpus_items)
    if not formatted.get("summary"):
        formatted["summary"] = f"Review outputs for {workflow.get('name') or 'this workflow'} before release."
    formatted["summary"] = _public_text(formatted["summary"])
    return formatted


def _normalize_rule_list(items: list[Any], limit: int = 8) -> list[str]:
    normalized = []
    seen = set()
    for item in items:
        text = _imperative_sentence(_public_text(item))
        key = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def _imperative_sentence(text: str) -> str:
    text = re.sub(r"^[\-•\d\.\)\s]+", "", text or "").strip()
    text = text[:1].upper() + text[1:] if text else text
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _source_map(rules: list[str], corpus_items: list[dict[str, Any]]) -> dict[str, str]:
    output = {}
    for rule in rules:
        source = _best_source_for_rule(rule, corpus_items)
        if source:
            output[rule] = source
    return output


def _best_source_for_rule(rule: str, corpus_items: list[dict[str, Any]]) -> str:
    rule_terms = set(re.findall(r"[a-z0-9]{4,}", rule.lower()))
    best = None
    best_score = 0
    for item in corpus_items:
        text = (item.get("text") or "").lower()
        terms = set(re.findall(r"[a-z0-9]{4,}", text))
        score = len(rule_terms & terms)
        if score > best_score:
            best = item
            best_score = score
    if not best or best_score == 0:
        return ""
    title = best.get("title") or best.get("source_uri") or "source"
    return summarize(title, 80)


def _human_methodology_review(methodology: dict[str, Any], corpus_items: list[dict[str, Any]], workflow: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    source_map = methodology.get("source_map") or _source_map((methodology.get("rules") or []) + (methodology.get("avoid") or []), corpus_items)
    must_do = [{"text": rule, "source": source_map.get(rule, "")} for rule in _normalize_rule_list(methodology.get("rules") or [], limit=8)]
    must_avoid = [{"text": rule, "source": source_map.get(rule, "")} for rule in _normalize_rule_list(methodology.get("avoid") or [], limit=8)]
    escalate_terms = ("escalate", "human", "review", "approval", "missing", "risk", "unsafe")
    escalate = [item for item in must_do + must_avoid if any(term in item["text"].lower() for term in escalate_terms)]
    dimensions = workflow.get("quality_dimensions") or ["Rules fit", "Grounding", "Actionability", "Context", "Safety", "Clarity"]
    goal = _public_text(workflow.get("objective") or "")
    return {
        "store": workflow.get("name"),
        "status": methodology.get("status"),
        "goal": goal,
        "goal_warning": "" if goal else "No review goal/protocol was supplied; rules may be corpus-generic.",
        "summary": _public_text(methodology.get("summary") or ""),
        "must_do": must_do,
        "must_avoid": must_avoid,
        "escalate_when": escalate[:6],
        "dimensions": dimensions,
        "source_count": len(corpus_items),
        "last_events": [_public_methodology_event(item) for item in events[:5]],
    }


def _has_methodology_signoff(events: list[dict[str, Any]], methodology_id: str) -> bool:
    for event in events:
        if event.get("methodology_id") == methodology_id and event.get("event_type") in {"reviewed", "updated"}:
            return True
    return False


def _list_diff(before: list[str], after: list[str]) -> dict[str, list[str]]:
    before_set = set(before or [])
    after_set = set(after or [])
    return {
        "added": sorted(after_set - before_set),
        "removed": sorted(before_set - after_set),
        "unchanged": sorted(before_set & after_set),
    }


def _organic_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if str(item.get("provenance") or "").startswith("human")]


def _memory_summary(decisions: list[dict[str, Any]], pairs: list[dict[str, Any]], tuples: list[dict[str, Any]]) -> dict[str, Any]:
    def counts(rows):
        output: dict[str, int] = {}
        for row in rows:
            provenance = row.get("provenance") or "unknown"
            output[provenance] = output.get(provenance, 0) + 1
        return output

    decision_counts = counts(decisions)
    pair_counts = counts(pairs)
    tuple_counts = counts(tuples)
    organic_decisions = sum(count for provenance, count in decision_counts.items() if provenance.startswith("human"))
    bootstrap_pairs = pair_counts.get("methodology_onboarding", 0)
    organic_pairs = sum(count for provenance, count in pair_counts.items() if provenance.startswith("human"))
    return {
        "organic_reviews": organic_decisions,
        "organic_pairs": organic_pairs,
        "bootstrap_pairs": bootstrap_pairs,
        "decision_counts_by_provenance": decision_counts,
        "pair_counts_by_provenance": pair_counts,
        "tuple_counts_by_provenance": tuple_counts,
        "fine_tune_guidance": f"{organic_decisions} human reviews and {organic_pairs} human-derived pairs. Use bootstrap pairs as seed data; wait for more organic reviews before treating this as final tuning data.",
    }


def _public_candidate(candidate: dict[str, Any]):
    output = dict(candidate or {})
    if "output" in output:
        output["output"] = _public_text(output["output"])
    metadata = dict(output.get("metadata") or {})
    for key in list(metadata):
        lowered = key.lower()
        if "signal" in lowered or "vector" in lowered or "kernel" in lowered:
            metadata.pop(key, None)
    output["metadata"] = metadata
    return output


def _public_observation(observation: dict[str, Any]):
    output = dict(observation or {})
    if "output" in output:
        output["output"] = _public_text(output["output"])
    output["context"] = _safe_public_json(output.get("context") or {})
    output["source"] = _safe_public_json(output.get("source") or {})
    return output


def _public_decision(decision: dict[str, Any]):
    output = dict(decision or {})
    for key in ("chosen_output", "reason", "author_id"):
        if key in output:
            output[key] = _public_text(output[key])
    if "rejected_outputs" in output:
        output["rejected_outputs"] = [_public_text(item) for item in output.get("rejected_outputs") or []]
    return output


def _public_tuple(tuple_record: dict[str, Any]):
    output = dict(tuple_record or {})
    for key in ("chosen_output", "reason", "provenance"):
        if key in output:
            output[key] = _public_text(output[key])
    if "task" in output:
        output["task"] = _safe_public_json(output["task"])
    if "candidates" in output:
        output["candidates"] = [_public_text(item) for item in output.get("candidates") or []]
    if "rejected_outputs" in output:
        output["rejected_outputs"] = [_public_text(item) for item in output.get("rejected_outputs") or []]
    return output


def _public_methodology_event(event: dict[str, Any]):
    output = dict(event or {})
    output["actor"] = _public_text(output.get("actor") or "")
    output["note"] = _public_text(output.get("note") or "")
    output["metadata"] = _safe_public_json(output.get("metadata") or {})
    return output


def _public_run(run: dict[str, Any]):
    output = dict(run or {})
    if "task" in output:
        output["task"] = _safe_public_json(output["task"])
    output["candidates"] = [_public_candidate(candidate) for candidate in output.get("candidates") or []]
    return output


def _public_text(value: Any) -> str:
    text = str(value or "")
    old_focus_label = "methodology " + "signals"
    text = re.sub(rf"\s*Dominant {re.escape(old_focus_label)}:[^.]*\.", "", text, flags=re.I)
    text = re.sub(rf"{old_focus_label.capitalize()}:[^\n]*", "Review focus captured from source material.", text, flags=re.I)
    text = re.sub(rf"discovered {re.escape(old_focus_label)}", "source-specific review guidance", text, flags=re.I)
    text = re.sub(old_focus_label, "review guidance", text, flags=re.I)
    text = re.sub("pheo-" + "kernel", "pheo", text, flags=re.I)
    return re.sub(r"\s{2,}", " ", text).strip()


def _safe_public_json(value: Any) -> Any:
    if isinstance(value, str):
        return _public_text(value)
    if isinstance(value, list):
        return [_safe_public_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _safe_public_json(item) for key, item in value.items()}
    return value


def _score_explanation(candidate: dict[str, Any], task: dict[str, Any], corpus_texts: list[str], methodology: dict[str, Any] | None) -> dict[str, Any]:
    scores = candidate.get("scores") or {}
    output = _public_text(candidate.get("output") or "")
    mean = float(scores.get("mean_score") or 0.0)
    if mean >= 0.78:
        verdict = "strong_candidate"
    elif mean >= 0.62:
        verdict = "reviewable_candidate"
    else:
        verdict = "needs_human_attention"

    dimensions = [
        ("methodology_fit", "Rules fit"),
        ("grounding", "Grounding"),
        ("actionability", "Actionability"),
        ("context_sensitivity", "Context"),
        ("safety", "Safety"),
        ("clarity", "Clarity"),
    ]
    drivers = []
    for key, label in dimensions:
        if key not in scores:
            continue
        value = float(scores.get(key) or 0.0)
        linked_rule = _linked_rule_for_dimension(key, output, methodology or {})
        drivers.append(
            {
                "dimension": key,
                "label": label,
                "score": round(value, 3),
                "level": _score_level(value),
                "reason": _dimension_reason(key, value, output, task, corpus_texts, methodology or {}, linked_rule),
                "linked_rule": linked_rule,
            }
        )
    drivers = sorted(drivers, key=lambda item: item["score"])
    weakest = drivers[:2]
    strongest = sorted(drivers, key=lambda item: item["score"], reverse=True)[:2]
    return {
        "verdict": verdict,
        "summary": _score_summary(verdict, weakest, strongest),
        "drivers": drivers,
        "weakest_dimensions": weakest,
        "strongest_dimensions": strongest,
        "thresholds": {
            "strong_candidate": 0.78,
            "reviewable_candidate": 0.62,
            "human_attention_below": 0.62,
        },
        "note": "Explanation is generated from review signals and stored scores; it does not expose private implementation details.",
    }


def _score_level(value: float) -> str:
    if value >= 0.78:
        return "strong"
    if value >= 0.62:
        return "reviewable"
    return "weak"


def _dimension_reason(key: str, value: float, output: str, task: dict[str, Any], corpus_texts: list[str], methodology: dict[str, Any], linked_rule: str = "") -> str:
    level = _score_level(value)
    lowered = output.lower()
    rules = methodology.get("rules") or []
    avoid = methodology.get("avoid") or []
    prefix = f"Low fit for approved rule: {linked_rule} " if linked_rule and level == "weak" else ""
    if key == "methodology_fit":
        if level == "weak":
            return prefix + "The output appears under-aligned with the approved review rules and should be checked against the methodology."
        return f"The output is reasonably aligned with the approved review rules ({len(rules)} active rules)."
    if key == "grounding":
        evidence_words = ("source", "evidence", "support", "cite", "according", "based on", "owner", "policy")
        if not any(word in lowered for word in evidence_words):
            return "The output does not visibly reference source support, evidence, policy, or owner context."
        return "The output includes visible source-support or evidence language."
    if key == "actionability":
        action_words = ("ask", "confirm", "review", "escalate", "check", "next", "recommend", "approve")
        if not any(word in lowered for word in action_words):
            return "The output gives limited next-step guidance for the reviewer or workflow owner."
        return "The output includes a concrete next step or review action."
    if key == "context_sensitivity":
        context_text = _public_text(_task_prompt(task)).lower()
        if context_text and not _shares_terms(lowered, context_text):
            return "The output may not reflect the supplied task/context closely enough."
        return "The output reflects the supplied task or review context."
    if key == "safety":
        risky = ("final", "guarantee", "always", "never", "without review", "no review", "approved")
        if any(word in lowered for word in risky):
            return prefix + "The output contains language that may overstate certainty or bypass review."
        return "The output avoids obvious overclaiming and review-bypass language."
    if key == "clarity":
        if len(output.split()) < 8:
            return "The output is very short, which may make the reasoning hard to inspect."
        if len(output.split()) > 140:
            return "The output is long enough that reviewers may need a tighter explanation."
        return "The output is within a reviewable length range."
    if avoid:
        return "Review against the approved avoid rules before release."
    if corpus_texts:
        return "Review against the attached source corpus before release."
    return "Review this dimension before release."


def _linked_rule_for_dimension(key: str, output: str, methodology: dict[str, Any]) -> str:
    rules = list(methodology.get("rules") or []) + list(methodology.get("avoid") or [])
    if not rules:
        return ""
    keywords_by_dimension = {
        "methodology_fit": (),
        "grounding": ("source", "evidence", "support", "ground", "provenance", "policy"),
        "actionability": ("ask", "confirm", "review", "escalate", "next", "recommend"),
        "context_sensitivity": ("context", "domain", "workflow", "customer", "account", "ticket"),
        "safety": ("human", "approval", "risk", "safe", "avoid", "do not", "escalate"),
        "clarity": ("clear", "concise", "format", "explain"),
    }
    keywords = keywords_by_dimension.get(key) or ()
    scored = []
    output_terms = set(re.findall(r"[a-z0-9]{4,}", output.lower()))
    for rule in rules:
        text = str(rule)
        lowered = text.lower()
        score = sum(1 for keyword in keywords if keyword in lowered)
        score += len(output_terms & set(re.findall(r"[a-z0-9]{4,}", lowered)))
        scored.append((score, text))
    scored.sort(reverse=True)
    return _public_text(scored[0][1]) if scored and scored[0][0] > 0 else _public_text(rules[0])


def _shares_terms(left: str, right: str) -> bool:
    left_terms = {term for term in re.findall(r"[a-z0-9]{4,}", left.lower())}
    right_terms = {term for term in re.findall(r"[a-z0-9]{4,}", right.lower())}
    return bool(left_terms & right_terms)


def _score_summary(verdict: str, weakest: list[dict[str, Any]], strongest: list[dict[str, Any]]) -> str:
    weak = ", ".join(item["label"] for item in weakest) or "no weak dimensions"
    strong = ", ".join(item["label"] for item in strongest) or "no strong dimensions"
    if verdict == "strong_candidate":
        return f"Strong candidate. Best signals: {strong}. Still review: {weak}."
    if verdict == "reviewable_candidate":
        return f"Reviewable candidate. Strongest signals: {strong}; weakest signals: {weak}."
    return f"Needs human attention before release. Weakest signals: {weak}; strongest signals: {strong}."


def _workflow_graph(workflow, connections, review_points, observations, packets, runs, decisions) -> dict[str, Any]:
    nodes = [
        {
            "id": workflow["id"],
            "type": "preference_store",
            "label": workflow["name"],
            "metadata": {"domain": workflow.get("domain"), "objective": _public_text(workflow.get("objective") or "")},
        }
    ]
    edges = []
    for connection in connections:
        nodes.append(
            {
                "id": connection["id"],
                "type": "connection",
                "label": connection["name"],
                "metadata": {
                    "connector_type": connection.get("connector_type"),
                    "config": _redacted_config(connection.get("config") or {}),
                },
            }
        )
        edges.append({"from": workflow["id"], "to": connection["id"], "type": "has_connection"})
    for point in review_points:
        nodes.append(
            {
                "id": point["id"],
                "type": "review_point",
                "label": point["name"],
                "metadata": {
                    "dimensions": point.get("dimensions") or [],
                    "human_review": point.get("human_review"),
                },
            }
        )
        edges.append({"from": workflow["id"], "to": point["id"], "type": "has_review_point"})
        connection_id = (point.get("connector_config") or {}).get("connection_id")
        if connection_id:
            edges.append({"from": connection_id, "to": point["id"], "type": "feeds_review_point"})
    for observation in observations:
        nodes.append(
            {
                "id": observation["id"],
                "type": "observation",
                "label": summarize(_public_text(observation.get("output", "")), 80),
                "metadata": {"source": _safe_public_json(observation.get("source") or {}), "status": observation.get("status")},
            }
        )
        edges.append({"from": observation["review_point_id"], "to": observation["id"], "type": "observed_output"})
        if observation.get("run_id"):
            edges.append({"from": observation["id"], "to": observation["run_id"], "type": "created_candidate_set"})
    for run in runs:
        nodes.append(
            {
                "id": run["id"],
                "type": "candidate_set",
                "label": _public_text(_task_prompt(run.get("task") or {})),
                "metadata": {"status": run.get("status")},
            }
        )
    for packet in packets:
        nodes.append(
            {
                "id": packet["id"],
                "type": "review_packet",
                "label": packet.get("status") or "review_packet",
                "metadata": {"delivery": packet.get("delivery") or {}},
            }
        )
        edges.append({"from": packet["run_id"], "to": packet["id"], "type": "sent_for_review"})
    for decision in decisions:
        nodes.append(
            {
                "id": decision["id"],
                "type": "decision",
                "label": decision.get("action") or "decision",
                "metadata": {"reason": _public_text(decision.get("reason") or ""), "provenance": _public_text(decision.get("provenance") or "")},
            }
        )
        edges.append({"from": decision["run_id"], "to": decision["id"], "type": "human_judgment"})
    return {
        "schema": "pheo.workflow_graph.v1",
        "store_id": workflow["id"],
        "store_name": workflow["name"],
        "nodes": nodes,
        "edges": edges,
    }


def _redacted_config(config: dict[str, Any]) -> dict[str, Any]:
    output = {}
    for key, value in config.items():
        if "key" in key.lower() or "secret" in key.lower() or "token" in key.lower():
            output[key] = "[redacted]"
        else:
            output[key] = value
    return output


def _task_prompt(task: dict[str, Any]) -> str:
    if isinstance(task, dict):
        return task.get("goal") or task.get("prompt") or json.dumps(task, sort_keys=True)
    return str(task)


def _pair_weight(chosen: str, rejected: str, base_weight: float) -> float:
    chosen_terms = set(chosen.lower().split())
    rejected_terms = set(rejected.lower().split())
    overlap = len(chosen_terms & rejected_terms) / max(1, min(len(chosen_terms), len(rejected_terms), 40))
    informative = 0.35 + min(0.25, overlap * 0.25)
    return round(max(0.2, min(1.0, informative * base_weight)), 3)


def _recommended_index(candidates):
    recommended = next((candidate for candidate in candidates if candidate.get("recommended")), None)
    return recommended["index"] if recommended else None


def _is_released_action(action: str | None, released_output: str | None) -> bool:
    return action in {"approve", "edit", "correct"} and bool(str(released_output or "").strip())


def _methodology_hash(methodology: dict[str, Any] | None) -> str:
    methodology = methodology or {}
    payload = {
        "summary": methodology.get("summary") or "",
        "rules": methodology.get("rules") or [],
        "avoid": methodology.get("avoid") or [],
        "runtime_profile": methodology.get("runtime_profile") or [],
    }
    return stable_hash(payload)


def _tuple_by_id(tuple_id: str | None, enriched_tuples: list[dict[str, Any]]) -> dict[str, Any]:
    return next((item for item in enriched_tuples if item.get("tuple_id") == tuple_id), {})


def _tuple_methodology_id(tuple_id: str | None, enriched_tuples: list[dict[str, Any]]) -> str:
    return _tuple_by_id(tuple_id, enriched_tuples).get("methodology_id") or ""


def _tuple_methodology_hash(tuple_id: str | None, enriched_tuples: list[dict[str, Any]]) -> str:
    return _tuple_by_id(tuple_id, enriched_tuples).get("methodology_hash") or ""


def _sft_rows(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in examples:
        completion = item.get("completion") or ""
        if not completion:
            continue
        rows.append(
            {
                "messages": [
                    {"role": "user", "content": item.get("prompt") or ""},
                    {"role": "assistant", "content": completion},
                ],
                "metadata": {
                    "tuple_id": item.get("tuple_id") or "",
                    "methodology_id": item.get("methodology_id") or "",
                    "methodology_hash": item.get("methodology_hash") or "",
                    "provenance": item.get("provenance") or "",
                    "weight": item.get("weight") or 0.0,
                    "reason": item.get("reason") or "",
                },
            }
        )
    return rows


def _dpo_rows(preference_pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in preference_pairs:
        rows.append(
            {
                "prompt": item.get("prompt") or "",
                "chosen": item.get("chosen") or "",
                "rejected": item.get("rejected") or "",
                "metadata": {
                    "pair_id": item.get("pair_id") or item.get("id") or "",
                    "tuple_id": item.get("tuple_id") or "",
                    "methodology_id": item.get("methodology_id") or "",
                    "methodology_hash": item.get("methodology_hash") or "",
                    "provenance": item.get("provenance") or "",
                    "weight": item.get("weight") or item.get("organic_weight") or 0.0,
                },
            }
        )
    return rows


def _readiness(decisions, pairs, corpus, runs) -> dict[str, Any]:
    human_decisions = _organic_items(decisions)
    human_pairs = _organic_items(pairs)
    seed_pairs = [item for item in pairs if item not in human_pairs]
    score = 0
    if corpus:
        score += 20
    if runs:
        score += 20
    if human_decisions:
        score += 20
    if human_pairs:
        score += 20
    if len(human_decisions) >= 5:
        score += 10
    if len(human_pairs) >= 10:
        score += 10
    seed_note = f" {len(seed_pairs)} method seed pairs are kept separate." if seed_pairs else ""
    return {
        "score": score,
        "label": "inspection_ready" if score >= 60 else "seed_data",
        "summary": f"{len(human_decisions)} human decisions, {len(human_pairs)} human preference pairs, {len(corpus)} corpus items, {len(runs)} runs.{seed_note}",
    }


def _critique(decisions, pairs, corpus, runs) -> dict[str, list[str]]:
    human_decisions = _organic_items(decisions)
    human_pairs = _organic_items(pairs)
    strengths = []
    gaps = []
    next_steps = []
    if corpus:
        strengths.append("Corpus provenance is present.")
    else:
        gaps.append("No corpus attached yet.")
    if human_decisions:
        strengths.append("Human decisions are captured as durable review records.")
    else:
        gaps.append("No human decisions captured yet.")
    if human_pairs:
        strengths.append("Chosen-over-rejected preference pairs are available.")
    else:
        gaps.append("No preference pairs available yet.")
    if any(candidate.get("scores") for run in runs for candidate in run.get("candidates", [])):
        strengths.append("Candidate quality scores are stored with run lineage.")
    else:
        gaps.append("Candidate quality scoring has not run yet.")
    if len(pairs) < 10:
        next_steps.append("Capture more decisions before treating this as model-tuning data.")
    if human_decisions and sum(1 for item in human_decisions if item.get("reason")) < max(1, len(human_decisions) // 2):
        next_steps.append("Ask reviewers for reasons so preference labels are more explainable.")
    next_steps.append("Keep this as preference memory until enough high-quality examples exist for private model tuning.")
    return {"strengths": strengths, "gaps": gaps, "next_steps": next_steps}


def _jsonl(rows: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + ("\n" if rows else "")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]):
    path.write_text(_jsonl(rows), encoding="utf-8")


class _Record(dict):
    def __getattr__(self, key: str):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc


def _record(value):
    if isinstance(value, _Record):
        return value
    if isinstance(value, dict):
        return _Record({key: _record(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_record(item) for item in value]
    return value


__all__ = ["Pheo", "GovernedOutcome", "PendingReview", "File", "Folder", "Text"]
