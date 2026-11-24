# Decisions

This record captures current constraints that future work should preserve. Details and implementation locations are in `docs/ARCHITECTURE.md`, `docs/EVALUATION.md`, and `docs/SECURITY.md`.

## D-001: Python controls workflow integrity

CrewAI Flow sequences the explicit stages. Python validates request/state contracts, retrieval results, evidence links, claim status, citations, persistence, and failure handling. Agent output cannot select a new stage or bypass deterministic validation.

## D-002: Offline fixtures are the default verification baseline

Offline mode uses frozen synthetic scenarios and scripted reasoning through the same Flow. Keep evaluation expectations stable unless a task explicitly revises the baseline and explains why. Fixture success is not evidence of live model quality.

## D-003: Dependencies are locked

`pyproject.toml` sets supported ranges and `uv.lock` records the resolved graph. Install and run with locked `uv` commands; dependency changes require an explicit task and corresponding lock update.

## D-004: Citation integrity is deterministic; semantic truth is not

The renderer and validator check known claim/source/evidence references and citation structure. They do not prove that a claim is true, that sources are independent, or that free-form prose is entailed by its citations.

## D-005: Production deployment is out of scope

The repository has no production authentication, tenant isolation, encrypted database, or complete operational controls. Do not describe the application as production-ready or deploy it based only on offline checks.
