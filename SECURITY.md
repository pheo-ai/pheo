# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

Security fixes are published for the latest release on TestPyPI/PyPI and in this repository.

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues privately to:

- **Email:** apprentice@pheo.ai
- **Subject:** `[SECURITY] Pheo`

Include:

1. Affected version
2. Steps to reproduce
3. Impact assessment
4. Any suggested fix or mitigation

We aim to acknowledge reports within **2 business days** and provide an initial assessment within **5 business days**.

## Scope

In scope:

- This repository (`pheo-ai/pheo`)
- The Pheo CLI, SDK, REST API, and MCP server
- Local data handling, export paths, and review capture flows
- Bundled kernel runtime behavior that affects data integrity, authorization, or release safety

Out of scope:

- Customer-managed LLM endpoints and API keys
- Third-party integrations (LangChain, LangSmith, OpenRouter, etc.) outside Pheo attachment points
- Legacy private repositories not maintained under `pheo-ai`

## Safe Defaults

Pheo is designed for local data custody by default:

- Review data stays in the configured local project (SQLite by default)
- Pheo does not call a Pheo-owned LLM
- API keys for customer endpoints should remain in environment variables, not in the Pheo Data Store

## Disclosure

We coordinate disclosure with reporters before public announcement. Credit is given when desired and appropriate.
