# Pheo Glossary

## Project

A local workspace and database. A project can contain multiple Pheo Data Stores.

## Pheo Data Store

A governed memory for one workflow. It stores source material, review rules, observations, decisions, preference pairs, examples, checks, and exportable memory packs.

## Source Material

Policies, examples, notes, documents, or other reference material used to create review rules.

## Review Rules

The operating standards a reviewer approves before Pheo observes outputs at a review point.

## Review Point

A business control point where an AI, agent, trace, or workflow output becomes reviewable.

## Observation

One captured output event from an agent, endpoint, trace, log, or workflow.

## Governed Outcome

The developer-facing result of an observation. It includes the observed output, prepared candidates, scores, review URL, review status, and released output after human approval or edit.

## Human Review

The approval, edit, rejection, or escalation decision that turns a review case into durable judgment memory.

## Memory Pack

The exported artifact containing source provenance, review rules, observations, decisions, preference pairs, review examples, check cases, and a workflow graph.

## Review Engine

The component that prepares reviewable candidates and scores them against approved review rules. The public SDK, CLI, REST API, UI, data model, and exports stay stable as this engine improves.
