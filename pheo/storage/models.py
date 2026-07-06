from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass
class Workflow:
    id: str
    name: str
    domain: str = ""
    objective: str = ""
    skill: str = ""
    quality_dimensions: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class CorpusItem:
    id: str
    workflow_id: str
    title: str
    text: str
    source_type: str = "text"
    source_uri: str = ""
    tags: list[str] = field(default_factory=list)
    content_hash: str = ""
    active: bool = True
    metadata: JsonDict = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class Methodology:
    id: str
    workflow_id: str
    summary: str
    rules: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    runtime_profile: list[str] = field(default_factory=list)
    runtime_state: list[float] = field(default_factory=list)
    review_pairs: list[JsonDict] = field(default_factory=list)
    status: str = "draft"
    confidence: float = 0.0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class Run:
    id: str
    workflow_id: str
    task: JsonDict
    mode: str = "external"
    status: str = "created"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class ReviewPoint:
    id: str
    workflow_id: str
    name: str
    description: str = ""
    dimensions: list[str] = field(default_factory=list)
    human_review: str = "required"
    branching: str = "kernel"
    connector_type: str = ""
    connector_config: JsonDict = field(default_factory=dict)
    active: bool = True
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class Connection:
    id: str
    workflow_id: str
    name: str
    connector_type: str
    config: JsonDict = field(default_factory=dict)
    active: bool = True
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class Observation:
    id: str
    workflow_id: str
    review_point_id: str
    output: str
    context: JsonDict = field(default_factory=dict)
    source: JsonDict = field(default_factory=dict)
    run_id: str = ""
    status: str = "observed"
    created_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class ReviewPacket:
    id: str
    workflow_id: str
    review_point_id: str
    observation_id: str
    run_id: str
    status: str = "pending_review"
    review_url: str = ""
    delivery: JsonDict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class Candidate:
    id: str
    run_id: str
    workflow_id: str
    index: int
    output: str
    generator: str = ""
    scores: JsonDict = field(default_factory=dict)
    rank: int | None = None
    recommended: bool = False
    metadata: JsonDict = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class Decision:
    id: str
    run_id: str
    workflow_id: str
    action: str
    selected_index: int
    chosen_output: str
    rejected_outputs: list[str] = field(default_factory=list)
    reason: str = ""
    weight: float = 1.0
    provenance: str = "human_triage"
    author_id: str = ""
    created_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class PreferenceTuple:
    id: str
    workflow_id: str
    run_id: str
    decision_id: str
    task: JsonDict
    candidates: list[str]
    selected_index: int
    chosen_output: str
    rejected_outputs: list[str]
    radar_scores: JsonDict = field(default_factory=dict)
    weight: float = 1.0
    weight_class: str = "human"
    provenance: str = "human_triage"
    reason: str = ""
    created_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class PreferencePair:
    id: str
    workflow_id: str
    source_tuple_id: str
    run_id: str
    prompt: str
    chosen_output: str
    rejected_output: str
    skill: str = ""
    organic_weight: float = 1.0
    provenance: str = "human_triage"
    created_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class ReleaseReceipt:
    id: str
    workflow_id: str
    packet_id: str
    run_id: str
    tuple_id: str
    decision_id: str
    raw_observed_output: str = ""
    recommended_output: str = ""
    reviewer_action: str = ""
    reviewer_reason: str = ""
    released_output: str = ""
    methodology_snapshot: JsonDict = field(default_factory=dict)
    source_snapshot: list[JsonDict] = field(default_factory=list)
    candidate_count: int = 0
    memory_entry_id: str = ""
    reviewer_id: str = ""
    backfilled: bool = False
    created_at: str = ""

    def to_dict(self) -> JsonDict:
        return asdict(self)
