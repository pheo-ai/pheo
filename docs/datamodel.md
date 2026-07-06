# Pheo Data Model

Pheo stores review memory in the active project database.

## Hierarchy

```text
Project
  Pheo Data Store
    Source material
    Connections
    Review points
    Observations
    Review cases
    Human reviews
    Preference pairs
    Memory exports
```

## Tables

The local SQLite database includes tables for:

- projects through the local registry
- workflows / Pheo Data Stores
- source corpus items
- review methodologies
- methodology audit events
- connections
- review points
- observations
- review packets
- runs and candidates
- human decisions
- preference tuples
- preference pairs

## Export Artifacts

The memory pack exports:

- `memory_pack.json`: full public memory artifact
- `workflow.graph.json`: workflow lineage graph
- `observations.jsonl`: captured workflow outputs
- `decisions.jsonl`: human decisions and reasons
- `methodology_events.jsonl`: rule creation and approval audit trail
- `preference_pairs.jsonl`: chosen-over-rejected training/evaluation data
- `review_examples.jsonl`: reviewed examples
- `quality_scores.jsonl`: candidate-level quality records

Internal kernel working state is not part of the public data contract.
