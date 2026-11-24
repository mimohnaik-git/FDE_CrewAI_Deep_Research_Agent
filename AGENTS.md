# Repository guidance

## Project boundaries

- Read `docs/PROJECT_STATE.md`, `docs/DECISIONS.md`, and `docs/HANDOFF.md` before substantial work.
- Preserve the research workflow's behavior, locked dependencies, CI, tests, and frozen evaluation expectations unless the task explicitly changes them.
- Keep offline runs deterministic and credential-free. Do not make paid provider, search, or deployment calls for routine validation.
- Treat topics, retrieved excerpts, local databases, and `.env` as potentially sensitive. Never print secrets; use `.env.example` for configuration shape.
- Keep changes focused. Do not add dependencies, fixtures, or refactors without a task requirement.

## Repository conventions

- Python is constrained to 3.13. Use `uv sync --locked --python 3.13` and `uv run --locked ...`.
- Ruff uses a 100-character line length. Keep tests under `tests/`; documentation belongs under `docs/`.
- `pyproject.toml` and `uv.lock` are the dependency sources of truth. Do not hand-edit the lockfile.
- Research stages, evidence links, citation checks, and evaluation contracts are described in `docs/ARCHITECTURE.md` and `docs/EVALUATION.md`.

## Working and validation

- Check the current branch, HEAD, and working tree before editing; inspect the diff and run `git diff --check` plus `git diff --cached --check` before committing.
- Prefer offline checks from `.github/workflows/verify.yml`: locked Ruff checks, pytest, compile/import checks, fixture evaluation, offline CLI, and secret scanning.
- Do not claim a check passed unless its command ran and its output was inspected. Clearly separate fixture results from live-provider quality.
- Use the focused repository skills in `.agents/skills/` when they match the task. Each skill points to the relevant project documentation for deeper context.
