# Pheo Product Spec

Pheo adds governed review points to existing AI, agent, and business workflows.

It does four things:

1. Connect source material reviewers already trust.
2. Propose review rules for a repeated workflow.
3. Capture model, agent, API, trace, or batch outputs at the point where human judgment matters.
4. Store approvals, edits, rejections, reasons, provenance, and exports as durable review memory.

Pheo local is customer-controlled:

- No Pheo-hosted model is required.
- No Pheo data custody is required.
- Default storage is local SQLite.
- Customers can connect their own endpoints, traces, logs, notification channels, and data sinks.

The public surface is the SDK, CLI, REST API, local browser UI, storage model, connectors, and export formats. These stay stable while the review engine improves behind the scenes.

See `README.md` for the current workflow.
