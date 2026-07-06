from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


def jsonl(rows: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + ("\n" if rows else "")


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]):
    Path(path).write_text(jsonl(rows), encoding="utf-8")


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "into", "is", "it", "its", "not", "of", "on", "or", "that", "the", "their",
    "this", "to", "was", "were", "with", "which", "will", "should", "can", "may",
}


DEFAULT_FILTERS = {
    "organic_only": True,
    "min_tuple_weight": 0.8,
    "min_pair_weight": 0.3,
    "actions": ["approve", "edit", "correct"],
    "require_released": True,
    "exclude_unresolved_escalations": True,
    "methodology_scope": "current_approved",
}


def normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sha256_text(value: Any) -> str:
    return "sha256:" + hashlib.sha256(normalize_text(value).encode("utf-8")).hexdigest()


def stable_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def released_for_action(action: str, released_output: str) -> bool:
    return action in {"approve", "edit", "correct"} and bool(str(released_output or "").strip())


def build_enriched_preference_tuples(
    workflow: dict[str, Any],
    runs: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    tuples: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    run_map = {run["id"]: run for run in runs}
    decision_map = {decision["id"]: decision for decision in decisions}
    receipt_map = {receipt.get("tuple_id"): receipt for receipt in receipts}
    output = []
    for tuple_ in tuples:
        run = run_map.get(tuple_.get("run_id"), {})
        decision = decision_map.get(tuple_.get("decision_id"), {})
        receipt = receipt_map.get(tuple_.get("id"), {})
        task = run.get("task") or tuple_.get("task") or {}
        snapshot = task.get("pheo_snapshot") or {}
        action = decision.get("action") or ""
        released_output = receipt.get("released_output") or tuple_.get("chosen_output") or ""
        output.append(
            {
                "schema": "pheo.preference_tuple.v1",
                "tuple_id": tuple_.get("id"),
                "workflow_id": workflow.get("id"),
                "run_id": tuple_.get("run_id"),
                "decision_id": tuple_.get("decision_id"),
                "task": task,
                "context": (task or {}).get("context") or {},
                "candidates": tuple_.get("candidates") or [],
                "selected_index": tuple_.get("selected_index"),
                "chosen_output": tuple_.get("chosen_output") or "",
                "released_output": released_output if released_for_action(action, released_output) else "",
                "rejected_outputs": tuple_.get("rejected_outputs") or [],
                "action": action,
                "reason": decision.get("reason") or tuple_.get("reason") or "",
                "weight": float(tuple_.get("weight") or decision.get("weight") or 0.0),
                "provenance": decision.get("provenance") or tuple_.get("provenance") or "",
                "methodology_id": snapshot.get("methodology_id") or "",
                "methodology_hash": snapshot.get("methodology_hash") or "",
                "source_snapshot": snapshot.get("source_snapshot") or [],
                "released": released_for_action(action, released_output),
                "created_at": decision.get("created_at") or tuple_.get("created_at") or "",
                "author_id": decision.get("author_id") or "",
            }
        )
    return sorted(output, key=lambda row: str(row.get("created_at", "")))


def build_released_examples(
    workflow: dict[str, Any],
    review_points: list[dict[str, Any]],
    methodology: dict[str, Any] | None,
    enriched_tuples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    point = review_points[0] if review_points else {}
    methodology = methodology or {}
    rules = [str(item) for item in methodology.get("rules") or []][:6]
    avoid = [str(item) for item in methodology.get("avoid") or []][:4]
    rule_text = "\n".join([f"- {item}" for item in rules] + [f"- Do not: {item}" for item in avoid])
    output = []
    for tuple_ in enriched_tuples:
        if not tuple_.get("released"):
            continue
        prompt = "\n\n".join(
            [
                f"Review goal:\n{point.get('description') or workflow.get('objective') or workflow.get('name')}",
                f"Approved rules:\n{rule_text or 'Use the approved workflow methodology.'}",
                f"Context:\n{json.dumps(tuple_.get('context') or {}, sort_keys=True)}",
                "Instruction:\nProduce the released output a human reviewer would approve for this workflow.",
            ]
        )
        output.append(
            {
                "prompt": prompt,
                "completion": tuple_.get("released_output") or "",
                "action": tuple_.get("action") or "",
                "reason": tuple_.get("reason") or "",
                "weight": tuple_.get("weight") or 0.0,
                "provenance": tuple_.get("provenance") or "",
                "methodology_id": tuple_.get("methodology_id") or "",
                "methodology_hash": tuple_.get("methodology_hash") or "",
                "tuple_id": tuple_.get("tuple_id") or "",
            }
        )
    return output


def compile_judgment_memory(workflow: dict[str, Any], enriched_tuples: list[dict[str, Any]], organic_only: bool = True) -> dict[str, Any]:
    entries = []
    for tuple_ in enriched_tuples:
        provenance = tuple_.get("provenance") or ""
        if organic_only and not provenance.startswith("human"):
            continue
        reason = tuple_.get("reason") or ""
        if not reason:
            continue
        action = tuple_.get("action") or ""
        feature_text = " ".join(
            [
                json.dumps(tuple_.get("context") or {}, sort_keys=True),
                tuple_.get("chosen_output") or "",
                " ".join(tuple_.get("rejected_outputs") or []),
                reason,
            ]
        )
        entries.append(
            {
                "entry_id": "decision_" + str(tuple_.get("decision_id") or ""),
                "tuple_id": tuple_.get("tuple_id") or "",
                "action": action,
                "reason": reason,
                "feature_text": normalize_text(feature_text),
                "methodology_id": tuple_.get("methodology_id") or "",
                "methodology_hash": tuple_.get("methodology_hash") or "",
                "weight": tuple_.get("weight") or 0.0,
                "released": bool(tuple_.get("released")),
            }
        )
    payload = {
        "schema": "pheo.judgment_memory.v1",
        "workflow_id": workflow.get("id") or "",
        "entries": entries,
    }
    payload["memory_hash"] = stable_hash(
        [
            {
                "entry_id": item["entry_id"],
                "action": item["action"],
                "reason": normalize_text(item["reason"]),
                "feature_text": normalize_text(item["feature_text"]),
                "methodology_hash": item["methodology_hash"],
            }
            for item in entries
        ]
    )
    return payload


def apply_judgment_memory(candidates: list[dict[str, Any]], task: dict[str, Any], memory: dict[str, Any] | None) -> list[dict[str, Any]]:
    entries = (memory or {}).get("entries") or []
    if not entries:
        return candidates
    original_recommended = next((candidate for candidate in candidates if candidate.get("recommended")), None)
    original_recommended_index = original_recommended.get("index") if original_recommended else None
    texts = [_candidate_feature(candidate, task) for candidate in candidates] + [entry.get("feature_text", "") for entry in entries]
    idf = _idf(texts)
    entry_vectors = [(entry, _tfidf(entry.get("feature_text", ""), idf)) for entry in entries]
    updated = []
    for candidate in candidates:
        feature = _candidate_feature(candidate, task)
        vector = _tfidf(feature, idf)
        best_entry, best_score = None, 0.0
        for entry, entry_vector in entry_vectors:
            score = _cosine(vector, entry_vector)
            if score > best_score:
                best_entry, best_score = entry, score
        item = dict(candidate)
        scores = dict(item.get("scores") or {})
        if best_entry and best_score >= 0.24:
            suggestion = _suggestion(best_entry)
            scores["judgment_memory"] = {
                "applied": True,
                "baseline_recommended_index": original_recommended_index,
                "baseline_rank": candidate.get("rank"),
                "was_recommended_before_memory": bool(candidate.get("recommended")),
                "nearest_entry_id": best_entry.get("entry_id"),
                "nearest_tuple_id": best_entry.get("tuple_id"),
                "similarity": round(best_score, 4),
                "prior_action": best_entry.get("action"),
                "prior_reason": best_entry.get("reason"),
                "suggestion": suggestion,
                "explanation": f"Similar to prior reviewer judgment: {best_entry.get('reason')}",
            }
            scores["mean_score"] = min(1.0, float(scores.get("mean_score") or 0.0) + _memory_delta(best_entry, best_score))
        else:
            scores["judgment_memory"] = {"applied": False, "suggestion": "no_match"}
        item["scores"] = scores
        updated.append(item)
    ranked = sorted(updated, key=lambda row: float((row.get("scores") or {}).get("mean_score") or 0.0), reverse=True)
    final_recommended_index = ranked[0].get("index") if ranked else None
    for rank, item in enumerate(ranked):
        item["rank"] = rank
        item["recommended"] = rank == 0
        memory_scores = (item.get("scores") or {}).get("judgment_memory") or {}
        if memory_scores.get("applied"):
            memory_scores["final_recommended_index"] = final_recommended_index
            memory_scores["recommendation_changed_by_memory"] = original_recommended_index != final_recommended_index
    return ranked


def build_training_manifest(
    workflow: dict[str, Any],
    enriched_tuples: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    filters: dict[str, Any] | None = None,
    current_methodology_hash: str = "",
) -> dict[str, Any]:
    filters = {**DEFAULT_FILTERS, **(filters or {})}
    included, excluded = [], []
    actions = set(filters.get("actions") or [])
    methodology_scope = filters.get("methodology_scope") or "current_approved"
    explicit_hashes = set(filters.get("methodology_hashes") or [])
    for tuple_ in enriched_tuples:
        reasons = []
        if filters.get("organic_only") and not str(tuple_.get("provenance") or "").startswith("human"):
            reasons.append("non_organic")
        if float(tuple_.get("weight") or 0.0) < float(filters.get("min_tuple_weight") or 0.0):
            reasons.append("below_min_tuple_weight")
        if actions and tuple_.get("action") not in actions:
            reasons.append("action_not_selected")
        if filters.get("require_released") and not tuple_.get("released"):
            reasons.append("not_released")
        if tuple_.get("action") == "escalate" and filters.get("exclude_unresolved_escalations"):
            reasons.append("unresolved_escalation")
        tuple_hash = tuple_.get("methodology_hash") or ""
        if methodology_scope == "current_approved" and current_methodology_hash and tuple_hash != current_methodology_hash:
            reasons.append("stale_methodology")
        if methodology_scope == "explicit" and explicit_hashes and tuple_hash not in explicit_hashes:
            reasons.append("methodology_not_selected")
        if reasons:
            excluded.append({"tuple_id": tuple_.get("tuple_id"), "reasons": sorted(set(reasons))})
        else:
            included.append(tuple_.get("tuple_id"))
    pair_excluded = []
    min_pair_weight = float(filters.get("min_pair_weight") or 0.0)
    for pair in pairs:
        if float(pair.get("organic_weight") or pair.get("weight") or 0.0) < min_pair_weight:
            pair_excluded.append({"pair_id": pair.get("id") or pair.get("pair_id"), "reasons": ["below_min_pair_weight"]})
    return {
        "schema": "pheo.training_manifest.v1",
        "workflow_id": workflow.get("id"),
        "filters": filters,
        "counts": {
            "tuples_total": len(enriched_tuples),
            "tuples_included": len(included),
            "tuples_excluded": len(excluded),
            "pairs_total": len(pairs),
            "pairs_excluded": len(pair_excluded),
            "released_examples": len(examples),
            "release_receipts": len(receipts),
        },
        "included_tuple_ids": included,
        "excluded_tuples": excluded,
        "excluded_pairs": pair_excluded,
        "methodology_hashes": sorted({item.get("methodology_hash") for item in enriched_tuples if item.get("methodology_hash")}),
        "split_guidance": {
            "strategy": "cycle_or_time_grouped",
            "business_id_hint": "Use invoice_id, paper_id, or another stable object id when present.",
            "leakage_warning": "Do not split related business objects across train and validation sets.",
        },
        "memory_richness": _memory_richness(enriched_tuples),
    }


def build_cycle_diff(workflow: dict[str, Any], runs: list[dict[str, Any]], before: str = "cycle_1", after: str = "cycle_2") -> dict[str, Any]:
    grouped = {before: [], after: []}
    for run in runs:
        cycle_id = ((run.get("task") or {}).get("source") or {}).get("cycle_id") or ((run.get("task") or {}).get("context") or {}).get("cycle_id")
        if cycle_id in grouped:
            grouped[cycle_id].append(run)
    if not grouped[before] or not grouped[after]:
        return {}
    def stats(items):
        memory_match_cases = 0
        candidate_matches = 0
        recommendations_changed = 0
        pending_review = 0
        cases = []
        for run in items:
            has_match = False
            changed = False
            candidates = run.get("candidates") or []
            if candidates:
                pending_review += 1
            for candidate in run.get("candidates") or []:
                memory_scores = ((candidate.get("scores") or {}).get("judgment_memory") or {})
                if memory_scores.get("applied"):
                    candidate_matches += 1
                    has_match = True
                    changed = changed or bool(memory_scores.get("recommendation_changed_by_memory"))
            if has_match:
                memory_match_cases += 1
            if changed:
                recommendations_changed += 1
            cases.append(
                {
                    "run_id": run.get("id"),
                    "business_object_id": _business_object_id(run),
                    "memory_applied": has_match,
                    "recommendation_changed_by_memory": changed,
                }
            )
        return {
            "runs": len(items),
            "pending_review_count": pending_review,
            "memory_match_cases": memory_match_cases,
            "memory_matches": candidate_matches,
            "recommendations_changed_by_memory": recommendations_changed,
            "cases": cases,
        }
    before_stats = stats(grouped[before])
    after_stats = stats(grouped[after])
    return {
        "schema": "pheo.cycle_diff.v1",
        "workflow_id": workflow.get("id"),
        "before": before,
        "after": after,
        "before_stats": before_stats,
        "after_stats": after_stats,
        "pending_review_delta": before_stats["pending_review_count"] - after_stats["pending_review_count"],
        "note": "Pheo does not auto-release outputs. Memory match counts show prior judgments available before review.",
    }


def _memory_richness(enriched_tuples: list[dict[str, Any]]) -> dict[str, Any]:
    cycles = sorted(
        {
            (((item.get("task") or {}).get("source") or {}).get("cycle_id") or ((item.get("context") or {}).get("cycle_id") or "uncycled"))
            for item in enriched_tuples
        }
    )
    with_reasons = [item for item in enriched_tuples if item.get("reason")]
    return {
        "tuple_count": len(enriched_tuples),
        "reasoned_tuple_count": len(with_reasons),
        "released_tuple_count": len([item for item in enriched_tuples if item.get("released")]),
        "escalation_tuple_count": len([item for item in enriched_tuples if item.get("action") == "escalate"]),
        "cycles_seen": cycles,
    }


def _business_object_id(run: dict[str, Any]) -> str:
    context = ((run.get("task") or {}).get("context") or {})
    for key in ("invoice_id", "paper_id", "case_id", "ticket_id", "contract_id"):
        if context.get(key):
            return str(context[key])
    source = ((run.get("task") or {}).get("source") or {})
    return str(source.get("case_id") or source.get("trace_id") or run.get("id") or "")


def _candidate_feature(candidate: dict[str, Any], task: dict[str, Any]) -> str:
    return normalize_text(json.dumps(_memory_task_view(task), sort_keys=True) + " " + str(candidate.get("output") or ""))


def _memory_task_view(task: dict[str, Any] | None) -> dict[str, Any]:
    task = dict(task or {})
    task.pop("pheo_snapshot", None)
    context = dict(task.get("context") or {})
    context.pop("pheo_snapshot", None)
    task["context"] = context
    return task


def _suggestion(entry: dict[str, Any]) -> str:
    action = entry.get("action")
    if action in {"approve", "edit", "correct"}:
        return "similar_prior_release"
    if action == "reject":
        return "similar_prior_reject"
    if action == "escalate":
        return "similar_prior_escalate"
    return "similar_prior_judgment"


def _memory_delta(entry: dict[str, Any], score: float) -> float:
    action = entry.get("action")
    if action in {"approve", "edit", "correct"}:
        return min(0.18, score * 0.18)
    if action == "reject":
        return max(-0.18, -score * 0.18)
    return 0.0


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", normalize_text(text)) if token not in STOPWORDS]


def _idf(texts: list[str]) -> dict[str, float]:
    df = Counter()
    for text in texts:
        df.update(set(_tokens(text)))
    total = max(1, len(texts))
    return {term: math.log((1 + total) / (1 + count)) + 1 for term, count in df.items()}


def _tfidf(text: str, idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(_tokens(text))
    total = max(1, sum(counts.values()))
    vector = {term: (count / total) * idf.get(term, 0.0) for term, count in counts.items()}
    norm = math.sqrt(sum(value * value for value in vector.values()))
    return {term: value / norm for term, value in vector.items()} if norm else vector


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return max(0.0, min(1.0, sum(value * right.get(term, 0.0) for term, value in left.items())))
