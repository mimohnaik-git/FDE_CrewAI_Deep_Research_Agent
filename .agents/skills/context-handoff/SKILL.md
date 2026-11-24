---
name: context-handoff
description: Prepare or update a factual handoff for work in this repository, with enough context and commands for the next contributor to continue safely.
---

# Context handoff

1. Read `docs/PROJECT_STATE.md`, `docs/DECISIONS.md`, and the relevant architecture, evaluation, or security docs.
2. Inspect branch, HEAD, working-tree status, changed paths, and actual verification output before describing progress.
3. Record the goal, current state, important constraints, useful file paths and commands, blockers, and next concrete action in `docs/HANDOFF.md`.
4. Mark assumptions as assumptions. Do not include secrets, `.env` values, fabricated results, or claims that a check ran when it did not.

Keep the handoff short and task-specific. Link deeper background instead of copying those documents. Remove stale branch status or next steps when they stop being true.
