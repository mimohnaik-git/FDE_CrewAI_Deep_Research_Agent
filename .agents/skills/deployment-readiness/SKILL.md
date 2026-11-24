---
name: deployment-readiness
description: Assess this repository's operational and security gaps before a proposed deployment, without treating offline checks as production evidence.
---

# Deployment readiness

1. Read `docs/SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/PROJECT_STATE.md`, and the deployment request.
2. Review authentication and authorization, tenant isolation, persistence and encryption, secrets handling, network boundaries, observability, failure behavior, dependency locking, and operational ownership.
3. Separate verified controls from gaps and assumptions. Use repository evidence and relevant locked-version documentation; do not infer production safety from passing tests.
4. Return a prioritized readiness assessment with the evidence needed to close each material gap.

This skill is an assessment workflow, not deployment authorization. Never deploy, expose the app, create credentials, or make paid service calls as part of an assessment.
