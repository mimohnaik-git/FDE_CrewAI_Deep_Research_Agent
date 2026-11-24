---
name: fde-orchestrator
description: Coordinate bounded feature delivery in this repository while preserving its architecture, locked environment, and evidence trail.
---

# FDE orchestrator

1. Read `docs/PROJECT_STATE.md`, `docs/DECISIONS.md`, and `docs/HANDOFF.md`; inspect branch, HEAD, and working tree.
2. Translate the request into a small file-level plan. Keep application behavior, dependencies, tests, CI, and evaluation baselines unchanged unless explicitly in scope.
3. Use the focused skill in `.agents/skills/` for repository audits, handoffs, AI evaluation, or deployment readiness as needed.
4. Make only requested changes. Do not use paid APIs, expose credentials, or deploy during offline work.
5. Run the relevant locked checks, inspect their output and the complete diff, then update handoff/state documentation with observed results only.

## Completion evidence

Report changed paths, executed commands and outcomes, unresolved issues, and the exact branch/commit state. A green fixture suite does not establish live model accuracy or production readiness.
