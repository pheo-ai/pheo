from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def project_db_path(project: str | os.PathLike[str]) -> Path:
    value = str(project)
    if value.startswith("sqlite:///"):
        return Path(value.replace("sqlite:///", "", 1))
    path = Path(value)
    if path.suffix == ".db":
        return path
    return path / "pheo.db"


class SQLiteStore:
    def __init__(self, project: str | os.PathLike[str]):
        self.db_path = project_db_path(project)

    @contextmanager
    def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def migrate(self):
        with self.connect() as conn:
            for statement in SCHEMA:
                conn.execute(statement)
            _migrate_methodology_columns(conn)

    def create_workflow(self, name: str, domain: str = "", objective: str = "", skill: str = "", quality_dimensions=None):
        existing = self.get_workflow(name)
        if existing:
            return existing
        workflow_id = new_id("wf")
        timestamp = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO workflows (id, name, domain, objective, skill, quality_dimensions, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [workflow_id, name, domain, objective, skill or name, json.dumps(quality_dimensions or []), timestamp, timestamp],
            )
        return self.get_workflow(workflow_id)

    def get_workflow(self, workflow_ref: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM workflows WHERE id = ? OR name = ?", [workflow_ref, workflow_ref]).fetchone()
        return _decode_workflow(row) if row else None

    def list_workflows(self):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM workflows ORDER BY created_at DESC").fetchall()
        return [_decode_workflow(row) for row in rows]

    def create_connection(self, workflow_id: str, name: str, connector_type: str, config: dict[str, Any] | None = None):
        existing = self.get_connection(workflow_id, name)
        if existing:
            return existing
        connection_id = new_id("conn")
        timestamp = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO connections (
                    id, workflow_id, name, connector_type, config, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [connection_id, workflow_id, name, connector_type, json.dumps(config or {}), 1, timestamp, timestamp],
            )
        return self.get_connection(workflow_id, connection_id)

    def get_connection(self, workflow_id: str, connection_ref: str):
        query = "SELECT * FROM connections WHERE (id = ? OR name = ?)"
        params = [connection_ref, connection_ref]
        if workflow_id:
            query += " AND workflow_id = ?"
            params.append(workflow_id)
        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()
        return _decode_connection(row) if row else None

    def list_connections(self, workflow_id: str, active_only: bool = False):
        query = "SELECT * FROM connections WHERE workflow_id = ?"
        params = [workflow_id]
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_decode_connection(row) for row in rows]

    def create_review_point(
        self,
        workflow_id: str,
        name: str,
        description: str = "",
        dimensions: list[str] | None = None,
        human_review: str = "required",
        branching: str = "kernel",
        connector_type: str = "",
        connector_config: dict[str, Any] | None = None,
    ):
        existing = self.get_review_point(workflow_id, name)
        if existing:
            return existing
        point_id = new_id("rp")
        timestamp = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO review_points (
                    id, workflow_id, name, description, dimensions, human_review,
                    branching, connector_type, connector_config, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    point_id,
                    workflow_id,
                    name,
                    description,
                    json.dumps(dimensions or []),
                    human_review,
                    branching,
                    connector_type,
                    json.dumps(connector_config or {}),
                    1,
                    timestamp,
                    timestamp,
                ],
            )
        return self.get_review_point(workflow_id, point_id)

    def update_review_point(self, review_point_id: str, **updates):
        allowed = {
            "description",
            "dimensions",
            "human_review",
            "branching",
            "connector_type",
            "connector_config",
            "active",
        }
        assignments = []
        values = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            column_value = value
            if key in {"dimensions", "connector_config"}:
                column_value = json.dumps(value or ([] if key == "dimensions" else {}))
            if key == "active":
                column_value = 1 if value else 0
            assignments.append(f"{key} = ?")
            values.append(column_value)
        if not assignments:
            return self.get_review_point("", review_point_id)
        assignments.append("updated_at = ?")
        values.append(now_iso())
        values.append(review_point_id)
        with self.connect() as conn:
            conn.execute(f"UPDATE review_points SET {', '.join(assignments)} WHERE id = ?", values)
        return self.get_review_point("", review_point_id)

    def get_review_point(self, workflow_id: str, review_point_ref: str):
        query = "SELECT * FROM review_points WHERE (id = ? OR name = ?)"
        params = [review_point_ref, review_point_ref]
        if workflow_id:
            query += " AND workflow_id = ?"
            params.append(workflow_id)
        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()
        return _decode_review_point(row) if row else None

    def list_review_points(self, workflow_id: str, active_only: bool = False):
        query = "SELECT * FROM review_points WHERE workflow_id = ?"
        params = [workflow_id]
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_decode_review_point(row) for row in rows]

    def create_observation(
        self,
        workflow_id: str,
        review_point_id: str,
        output: str,
        context: dict[str, Any] | None = None,
        source: dict[str, Any] | None = None,
        run_id: str = "",
        status: str = "observed",
    ):
        observation_id = new_id("obs")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO observations (
                    id, workflow_id, review_point_id, output, context, source,
                    run_id, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    observation_id,
                    workflow_id,
                    review_point_id,
                    output,
                    json.dumps(context or {}),
                    json.dumps(source or {}),
                    run_id,
                    status,
                    now_iso(),
                ],
            )
        return self.get_observation(observation_id)

    def update_observation_run(self, observation_id: str, run_id: str, status: str = "packet_created"):
        with self.connect() as conn:
            conn.execute("UPDATE observations SET run_id = ?, status = ? WHERE id = ?", [run_id, status, observation_id])
        return self.get_observation(observation_id)

    def get_observation(self, observation_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM observations WHERE id = ?", [observation_id]).fetchone()
        return _decode_observation(row) if row else None

    def list_observations(self, workflow_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM observations WHERE workflow_id = ? ORDER BY created_at DESC", [workflow_id]).fetchall()
        return [_decode_observation(row) for row in rows]

    def create_review_packet(
        self,
        workflow_id: str,
        review_point_id: str,
        observation_id: str,
        run_id: str,
        status: str = "pending_review",
        review_url: str = "",
        delivery: dict[str, Any] | None = None,
    ):
        packet_id = new_id("packet")
        if review_url and "{packet_id}" in review_url:
            review_url = review_url.format(packet_id=packet_id)
        timestamp = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO review_packets (
                    id, workflow_id, review_point_id, observation_id, run_id,
                    status, review_url, delivery, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    packet_id,
                    workflow_id,
                    review_point_id,
                    observation_id,
                    run_id,
                    status,
                    review_url,
                    json.dumps(delivery or {}),
                    timestamp,
                    timestamp,
                ],
            )
        return self.get_review_packet(packet_id)

    def update_review_packet_status(self, packet_id: str, status: str):
        with self.connect() as conn:
            conn.execute("UPDATE review_packets SET status = ?, updated_at = ? WHERE id = ?", [status, now_iso(), packet_id])
        return self.get_review_packet(packet_id)

    def update_review_packet_delivery(self, packet_id: str, delivery: dict[str, Any]):
        with self.connect() as conn:
            conn.execute(
                "UPDATE review_packets SET delivery = ?, updated_at = ? WHERE id = ?",
                [json.dumps(delivery or {}), now_iso(), packet_id],
            )
        return self.get_review_packet(packet_id)

    def get_review_packet(self, packet_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM review_packets WHERE id = ?", [packet_id]).fetchone()
        return _decode_review_packet(row) if row else None

    def list_review_packets(self, workflow_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM review_packets WHERE workflow_id = ? ORDER BY created_at DESC", [workflow_id]).fetchall()
        return [_decode_review_packet(row) for row in rows]

    def create_corpus_item(self, workflow_id: str, record: dict[str, Any]):
        item_id = new_id("corpus")
        timestamp = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO corpus_items (
                    id, workflow_id, title, text, source_type, source_uri, tags,
                    content_hash, active, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    item_id,
                    workflow_id,
                    record.get("title") or "Corpus item",
                    record.get("text") or "",
                    record.get("source_type") or "text",
                    record.get("source_uri") or "",
                    json.dumps(record.get("tags") or []),
                    record.get("content_hash") or "",
                    1 if record.get("active", True) else 0,
                    json.dumps(record.get("metadata") or {}),
                    timestamp,
                ],
            )
        return self.get_corpus_item(item_id)

    def list_corpus(self, workflow_id: str, active_only: bool = False):
        query = "SELECT * FROM corpus_items WHERE workflow_id = ?"
        params = [workflow_id]
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_decode_corpus(row) for row in rows]

    def get_corpus_item(self, item_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM corpus_items WHERE id = ?", [item_id]).fetchone()
        return _decode_corpus(row) if row else None

    def deactivate_corpus(self, item_id: str):
        with self.connect() as conn:
            conn.execute("UPDATE corpus_items SET active = 0 WHERE id = ?", [item_id])
        return self.get_corpus_item(item_id)

    def save_methodology(
        self,
        workflow_id: str,
        profile: dict[str, Any],
        status: str = "draft",
        actor: str = "pheo",
        note: str = "Review rules generated from source material.",
        metadata: dict[str, Any] | None = None,
        event_type: str = "drafted",
    ):
        method_id = new_id("method")
        event_id = new_id("meth_event")
        timestamp = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO methodologies (
                    id, workflow_id, summary, rules, avoid, runtime_profile, runtime_state,
                    review_pairs, status, confidence, approved_at, approved_by, approval_note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    method_id,
                    workflow_id,
                    profile.get("summary") or "",
                    json.dumps(profile.get("rules") or []),
                    json.dumps(profile.get("avoid") or []),
                    json.dumps(profile.get("runtime_profile") or []),
                    json.dumps(profile.get("runtime_state") or []),
                    json.dumps(profile.get("review_pairs") or []),
                    status,
                    float(profile.get("confidence") or 0.0),
                    timestamp if status == "approved" else None,
                    actor if status == "approved" else "",
                    note if status == "approved" else "",
                    timestamp,
                    timestamp,
                ],
            )
            conn.execute(
                """
                INSERT INTO methodology_events (
                    id, workflow_id, methodology_id, event_type, actor, note, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    event_id,
                    workflow_id,
                    method_id,
                    "approved" if status == "approved" else event_type,
                    actor,
                    note,
                    json.dumps(metadata or {"status": status, "confidence": float(profile.get("confidence") or 0.0)}),
                    timestamp,
                ],
            )
        return self.get_methodology(workflow_id)

    def record_methodology_event(
        self,
        workflow_id: str,
        methodology_id: str,
        event_type: str,
        actor: str = "human",
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        event_id = new_id("meth_event")
        timestamp = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO methodology_events (
                    id, workflow_id, methodology_id, event_type, actor, note, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    event_id,
                    workflow_id,
                    methodology_id,
                    event_type,
                    actor,
                    note,
                    json.dumps(metadata or {}),
                    timestamp,
                ],
            )
        return self.list_methodology_events(workflow_id)[0]

    def update_methodology_status(
        self,
        workflow_id: str,
        status: str,
        actor: str = "human",
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        methodology = self.get_methodology(workflow_id)
        if not methodology:
            raise ValueError("Methodology not found")
        event_id = new_id("meth_event")
        timestamp = now_iso()
        approved_at = timestamp if status == "approved" else methodology.get("approved_at")
        approved_by = actor if status == "approved" else methodology.get("approved_by", "")
        approval_note = note if status == "approved" else methodology.get("approval_note", "")
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE methodologies
                SET status = ?, approved_at = ?, approved_by = ?, approval_note = ?, updated_at = ?
                WHERE id = ?
                """,
                [status, approved_at, approved_by, approval_note, timestamp, methodology["id"]],
            )
            conn.execute(
                """
                INSERT INTO methodology_events (
                    id, workflow_id, methodology_id, event_type, actor, note, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    event_id,
                    workflow_id,
                    methodology["id"],
                    status,
                    actor,
                    note,
                    json.dumps(metadata or {"previous_status": methodology.get("status"), "status": status}),
                    timestamp,
                ],
            )
        return self.get_methodology(workflow_id)

    def get_methodology(self, workflow_id: str):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM methodologies WHERE workflow_id = ? ORDER BY updated_at DESC LIMIT 1",
                [workflow_id],
            ).fetchone()
        return _decode_methodology(row) if row else None

    def approve_methodology(self, workflow_id: str, actor: str = "human", note: str = "", metadata: dict[str, Any] | None = None):
        methodology = self.get_methodology(workflow_id)
        if not methodology:
            raise ValueError("Methodology not found")
        event_id = new_id("meth_event")
        timestamp = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE methodologies
                SET status = ?, approved_at = ?, approved_by = ?, approval_note = ?, updated_at = ?
                WHERE id = ?
                """,
                ["approved", timestamp, actor, note, timestamp, methodology["id"]],
            )
            conn.execute(
                """
                INSERT INTO methodology_events (
                    id, workflow_id, methodology_id, event_type, actor, note, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    event_id,
                    workflow_id,
                    methodology["id"],
                    "approved",
                    actor,
                    note,
                    json.dumps(metadata or {"previous_status": methodology.get("status"), "status": "approved"}),
                    timestamp,
                ],
            )
        return self.get_methodology(workflow_id)

    def list_methodology_events(self, workflow_id: str):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM methodology_events WHERE workflow_id = ? ORDER BY created_at DESC",
                [workflow_id],
            ).fetchall()
        return [_decode_methodology_event(row) for row in rows]

    def create_run(self, workflow_id: str, task: dict[str, Any], mode: str = "external"):
        run_id = new_id("run")
        timestamp = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (id, workflow_id, task, mode, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [run_id, workflow_id, json.dumps(task or {}), mode, "created", timestamp, timestamp],
            )
        return self.get_run(run_id)

    def update_run_status(self, run_id: str, status: str):
        with self.connect() as conn:
            conn.execute("UPDATE runs SET status = ?, updated_at = ? WHERE id = ?", [status, now_iso(), run_id])
        return self.get_run(run_id)

    def get_run(self, run_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", [run_id]).fetchone()
        return _decode_run(row) if row else None

    def list_runs(self, workflow_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM runs WHERE workflow_id = ? ORDER BY created_at DESC", [workflow_id]).fetchall()
        return [_decode_run(row) for row in rows]

    def create_candidate(self, workflow_id: str, run_id: str, index: int, output: str, generator: str = "", metadata=None):
        candidate_id = new_id("cand")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO candidates (
                    id, workflow_id, run_id, idx, output, generator, scores, rank, recommended, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    candidate_id,
                    workflow_id,
                    run_id,
                    index,
                    output,
                    generator,
                    json.dumps({}),
                    None,
                    0,
                    json.dumps(metadata or {}),
                    now_iso(),
                ],
            )
        return self.get_candidate(candidate_id)

    def update_candidate_scores(self, candidate_id: str, scores: dict[str, Any], rank: int | None, recommended: bool):
        with self.connect() as conn:
            conn.execute(
                "UPDATE candidates SET scores = ?, rank = ?, recommended = ? WHERE id = ?",
                [json.dumps(scores or {}), rank, 1 if recommended else 0, candidate_id],
            )
        return self.get_candidate(candidate_id)

    def get_candidate(self, candidate_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM candidates WHERE id = ?", [candidate_id]).fetchone()
        return _decode_candidate(row) if row else None

    def list_candidates(self, run_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM candidates WHERE run_id = ? ORDER BY idx ASC", [run_id]).fetchall()
        return [_decode_candidate(row) for row in rows]

    def create_decision(
        self,
        workflow_id: str,
        run_id: str,
        action: str,
        selected_index: int,
        chosen_output: str,
        rejected_outputs: list[str],
        reason: str = "",
        weight: float = 1.0,
        provenance: str = "human_triage",
        author_id: str = "",
    ):
        decision_id = new_id("decision")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO decisions (
                    id, workflow_id, run_id, action, selected_index, chosen_output,
                    rejected_outputs, reason, weight, provenance, author_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    decision_id,
                    workflow_id,
                    run_id,
                    action,
                    selected_index,
                    chosen_output,
                    json.dumps(rejected_outputs or []),
                    reason,
                    weight,
                    provenance,
                    author_id,
                    now_iso(),
                ],
            )
        return self.get_decision(decision_id)

    def get_decision(self, decision_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM decisions WHERE id = ?", [decision_id]).fetchone()
        return _decode_decision(row) if row else None

    def list_decisions(self, workflow_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM decisions WHERE workflow_id = ? ORDER BY created_at DESC", [workflow_id]).fetchall()
        return [_decode_decision(row) for row in rows]

    def create_preference_tuple(self, workflow_id: str, run_id: str, decision_id: str, task, candidates, selected_index, chosen, rejected, radar_scores, weight, provenance, reason):
        tuple_id = new_id("tuple")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO preference_tuples (
                    id, workflow_id, run_id, decision_id, task, candidates, selected_index,
                    chosen_output, rejected_outputs, radar_scores, weight, weight_class,
                    provenance, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    tuple_id,
                    workflow_id,
                    run_id,
                    decision_id,
                    json.dumps(task or {}),
                    json.dumps(candidates or []),
                    selected_index,
                    chosen,
                    json.dumps(rejected or []),
                    json.dumps(radar_scores or {}),
                    weight,
                    "human" if provenance.startswith("human") else "organic",
                    provenance,
                    reason,
                    now_iso(),
                ],
            )
        return self.get_preference_tuple(tuple_id)

    def get_preference_tuple(self, tuple_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM preference_tuples WHERE id = ?", [tuple_id]).fetchone()
        return _decode_tuple(row) if row else None

    def list_preference_tuples(self, workflow_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM preference_tuples WHERE workflow_id = ? ORDER BY created_at DESC", [workflow_id]).fetchall()
        return [_decode_tuple(row) for row in rows]

    def create_preference_pair(self, workflow_id: str, source_tuple_id: str, run_id: str, prompt: str, chosen: str, rejected: str, skill: str, weight: float, provenance: str):
        pair_id = new_id("pair")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO preference_pairs (
                    id, workflow_id, source_tuple_id, run_id, prompt, chosen_output,
                    rejected_output, skill, organic_weight, provenance, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [pair_id, workflow_id, source_tuple_id, run_id, prompt, chosen, rejected, skill, weight, provenance, now_iso()],
            )
        return self.get_preference_pair(pair_id)

    def get_preference_pair(self, pair_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM preference_pairs WHERE id = ?", [pair_id]).fetchone()
        return _decode_pair(row) if row else None

    def list_preference_pairs(self, workflow_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM preference_pairs WHERE workflow_id = ? ORDER BY created_at DESC", [workflow_id]).fetchall()
        return [_decode_pair(row) for row in rows]

    def create_release_receipt(
        self,
        workflow_id: str,
        packet_id: str,
        run_id: str,
        tuple_id: str,
        decision_id: str,
        raw_observed_output: str = "",
        recommended_output: str = "",
        reviewer_action: str = "",
        reviewer_reason: str = "",
        released_output: str = "",
        methodology_snapshot: dict[str, Any] | None = None,
        source_snapshot: list[dict[str, Any]] | None = None,
        candidate_count: int = 0,
        memory_entry_id: str = "",
        reviewer_id: str = "",
        backfilled: bool = False,
        created_at: str = "",
    ):
        existing = self.get_release_receipt_for_decision(decision_id)
        if existing:
            return existing
        receipt_id = new_id("receipt")
        timestamp = created_at or now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO release_receipts (
                    id, workflow_id, packet_id, run_id, tuple_id, decision_id,
                    raw_observed_output, recommended_output, reviewer_action,
                    reviewer_reason, released_output, methodology_snapshot,
                    source_snapshot, candidate_count, memory_entry_id, reviewer_id,
                    backfilled, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    receipt_id,
                    workflow_id,
                    packet_id,
                    run_id,
                    tuple_id,
                    decision_id,
                    raw_observed_output,
                    recommended_output,
                    reviewer_action,
                    reviewer_reason,
                    released_output,
                    json.dumps(methodology_snapshot or {}),
                    json.dumps(source_snapshot or []),
                    int(candidate_count or 0),
                    memory_entry_id,
                    reviewer_id,
                    1 if backfilled else 0,
                    timestamp,
                ],
            )
        return self.get_release_receipt(receipt_id)

    def get_release_receipt(self, receipt_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM release_receipts WHERE id = ?", [receipt_id]).fetchone()
        return _decode_release_receipt(row) if row else None

    def get_release_receipt_for_decision(self, decision_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM release_receipts WHERE decision_id = ?", [decision_id]).fetchone()
        return _decode_release_receipt(row) if row else None

    def list_release_receipts(self, workflow_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM release_receipts WHERE workflow_id = ? ORDER BY created_at DESC", [workflow_id]).fetchall()
        return [_decode_release_receipt(row) for row in rows]


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS workflows (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        domain TEXT,
        objective TEXT,
        skill TEXT,
        quality_dimensions TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS corpus_items (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        title TEXT NOT NULL,
        text TEXT NOT NULL,
        source_type TEXT,
        source_uri TEXT,
        tags TEXT,
        content_hash TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        metadata TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS methodologies (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        rules TEXT,
        avoid TEXT,
        runtime_profile TEXT,
        runtime_state TEXT,
        review_pairs TEXT,
        status TEXT NOT NULL,
        confidence REAL NOT NULL DEFAULT 0.0,
        approved_at TEXT,
        approved_by TEXT,
        approval_note TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS methodology_events (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        methodology_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        actor TEXT,
        note TEXT,
        metadata TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS connections (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        name TEXT NOT NULL,
        connector_type TEXT NOT NULL,
        config TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(workflow_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS review_points (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        dimensions TEXT,
        human_review TEXT NOT NULL DEFAULT 'required',
        branching TEXT NOT NULL DEFAULT 'kernel',
        connector_type TEXT,
        connector_config TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(workflow_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS observations (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        review_point_id TEXT NOT NULL,
        output TEXT NOT NULL,
        context TEXT,
        source TEXT,
        run_id TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS review_packets (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        review_point_id TEXT NOT NULL,
        observation_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        status TEXT NOT NULL,
        review_url TEXT,
        delivery TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        task TEXT NOT NULL,
        mode TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS candidates (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        idx INTEGER NOT NULL,
        output TEXT NOT NULL,
        generator TEXT,
        scores TEXT,
        rank INTEGER,
        recommended INTEGER NOT NULL DEFAULT 0,
        metadata TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS decisions (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        action TEXT NOT NULL,
        selected_index INTEGER NOT NULL,
        chosen_output TEXT NOT NULL,
        rejected_outputs TEXT,
        reason TEXT,
        weight REAL NOT NULL DEFAULT 1.0,
        provenance TEXT NOT NULL,
        author_id TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS preference_tuples (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        decision_id TEXT NOT NULL,
        task TEXT NOT NULL,
        candidates TEXT NOT NULL,
        selected_index INTEGER NOT NULL,
        chosen_output TEXT NOT NULL,
        rejected_outputs TEXT,
        radar_scores TEXT,
        weight REAL NOT NULL DEFAULT 1.0,
        weight_class TEXT NOT NULL,
        provenance TEXT NOT NULL,
        reason TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS preference_pairs (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        source_tuple_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        prompt TEXT NOT NULL,
        chosen_output TEXT NOT NULL,
        rejected_output TEXT NOT NULL,
        skill TEXT,
        organic_weight REAL NOT NULL DEFAULT 1.0,
        provenance TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS release_receipts (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        packet_id TEXT NOT NULL,
        run_id TEXT NOT NULL,
        tuple_id TEXT NOT NULL,
        decision_id TEXT NOT NULL UNIQUE,
        raw_observed_output TEXT,
        recommended_output TEXT,
        reviewer_action TEXT,
        reviewer_reason TEXT,
        released_output TEXT,
        methodology_snapshot TEXT,
        source_snapshot TEXT,
        candidate_count INTEGER NOT NULL DEFAULT 0,
        memory_entry_id TEXT,
        reviewer_id TEXT,
        backfilled INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_corpus_workflow ON corpus_items(workflow_id, active)",
    "CREATE INDEX IF NOT EXISTS idx_connections_workflow ON connections(workflow_id, active)",
    "CREATE INDEX IF NOT EXISTS idx_review_points_workflow ON review_points(workflow_id, active)",
    "CREATE INDEX IF NOT EXISTS idx_observations_workflow ON observations(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_packets_workflow ON review_packets(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_runs_workflow ON runs(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_candidates_run ON candidates(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_pairs_workflow ON preference_pairs(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_receipts_workflow ON release_receipts(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_receipts_run ON release_receipts(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_methodology_events_workflow ON methodology_events(workflow_id)",
]


def _table_columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate_methodology_columns(conn) -> None:
    columns = _table_columns(conn, "methodologies")
    if "runtime_profile" not in columns:
        conn.execute("ALTER TABLE methodologies ADD COLUMN runtime_profile TEXT")
    if "runtime_state" not in columns:
        conn.execute("ALTER TABLE methodologies ADD COLUMN runtime_state TEXT")
    if "approved_at" not in columns:
        conn.execute("ALTER TABLE methodologies ADD COLUMN approved_at TEXT")
    if "approved_by" not in columns:
        conn.execute("ALTER TABLE methodologies ADD COLUMN approved_by TEXT")
    if "approval_note" not in columns:
        conn.execute("ALTER TABLE methodologies ADD COLUMN approval_note TEXT")
    columns = _table_columns(conn, "methodologies")
    if "legacy_profile" in columns:
        conn.execute(
            """
            UPDATE methodologies
            SET runtime_profile = COALESCE(runtime_profile, legacy_profile, '[]')
            WHERE runtime_profile IS NULL OR runtime_profile = ''
            """
        )
    if "legacy_state" in columns:
        conn.execute(
            """
            UPDATE methodologies
            SET runtime_state = COALESCE(runtime_state, legacy_state, '[]')
            WHERE runtime_state IS NULL OR runtime_state = ''
            """
        )


def _decode_workflow(row):
    item = dict(row)
    item["quality_dimensions"] = json.loads(item.get("quality_dimensions") or "[]")
    return item


def _decode_corpus(row):
    item = dict(row)
    item["tags"] = json.loads(item.get("tags") or "[]")
    item["metadata"] = json.loads(item.get("metadata") or "{}")
    item["active"] = bool(item.get("active"))
    return item


def _decode_connection(row):
    item = dict(row)
    item["config"] = json.loads(item.get("config") or "{}")
    item["active"] = bool(item.get("active"))
    return item


def _decode_methodology(row):
    item = dict(row)
    for key in ("rules", "avoid", "runtime_profile", "runtime_state", "review_pairs"):
        item[key] = json.loads(item.get(key) or "[]")
    return item


def _decode_methodology_event(row):
    item = dict(row)
    item["metadata"] = json.loads(item.get("metadata") or "{}")
    return item


def _decode_review_point(row):
    item = dict(row)
    item["dimensions"] = json.loads(item.get("dimensions") or "[]")
    item["connector_config"] = json.loads(item.get("connector_config") or "{}")
    item["active"] = bool(item.get("active"))
    return item


def _decode_observation(row):
    item = dict(row)
    item["context"] = json.loads(item.get("context") or "{}")
    item["source"] = json.loads(item.get("source") or "{}")
    return item


def _decode_review_packet(row):
    item = dict(row)
    item["delivery"] = json.loads(item.get("delivery") or "{}")
    return item


def _decode_run(row):
    item = dict(row)
    item["task"] = json.loads(item.get("task") or "{}")
    return item


def _decode_candidate(row):
    item = dict(row)
    item["index"] = item.pop("idx")
    item["scores"] = json.loads(item.get("scores") or "{}")
    item["recommended"] = bool(item.get("recommended"))
    item["metadata"] = json.loads(item.get("metadata") or "{}")
    return item


def _decode_decision(row):
    item = dict(row)
    item["rejected_outputs"] = json.loads(item.get("rejected_outputs") or "[]")
    return item


def _decode_tuple(row):
    item = dict(row)
    item["task"] = json.loads(item.get("task") or "{}")
    item["candidates"] = json.loads(item.get("candidates") or "[]")
    item["rejected_outputs"] = json.loads(item.get("rejected_outputs") or "[]")
    item["radar_scores"] = json.loads(item.get("radar_scores") or "{}")
    return item


def _decode_pair(row):
    return dict(row)


def _decode_release_receipt(row):
    item = dict(row)
    item["methodology_snapshot"] = json.loads(item.get("methodology_snapshot") or "{}")
    item["source_snapshot"] = json.loads(item.get("source_snapshot") or "[]")
    item["candidate_count"] = int(item.get("candidate_count") or 0)
    item["backfilled"] = bool(item.get("backfilled"))
    return item
