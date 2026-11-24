# Handoff

## Current context

The integration pilot is documentation and repository-skill work on `fde/integration-roadmap`, based on the clean `main` baseline at `d2d2fa61b2e03cea154334d1d4d8bc142176aa5e`. The intended change set is `AGENTS.md`, the project state/decision/handoff docs, and five skills under `.agents/skills/`. Preserve application behavior, dependency locks, tests, CI, and evaluation expectations.

## Useful commands

```sh
uv sync --locked --python 3.13
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -q
uv run --locked python -m compileall -q research app.py
uv run --locked python -c "import research.workflow, research.reasoning, research.providers"
uv run --locked python -m research.evaluation --output data/evaluation.json
uv run --locked python -m research.cli --db data/offline.sqlite3
uv run --locked python scripts/check_secrets.py
git diff --check
git diff --cached --check
```

`data/` is ignored. Do not inspect or expose `.env`; the offline suite needs no credentials. The workflow in `.github/workflows/verify.yml` is the authoritative list of existing CI checks.

## Read before changing behavior

- `docs/ARCHITECTURE.md` describes stage ownership and data flow.
- `docs/EVALUATION.md` describes fixture expectations and what they do not prove.
- `docs/SECURITY.md` describes untrusted input, credentials, persistence, and deployment gaps.
- `docs/DECISIONS.md` records constraints to preserve.

For current repository state, locked package versions, or known limitations, see `docs/PROJECT_STATE.md`. Update this handoff only with observed branch status, verification output, blockers, and concrete next actions; never turn intended checks into claimed results.

## Integration pilot verification

- Skill discovery and YAML frontmatter validation passed for all five requested skills.
- The installed Python 3.13 environment matches the checked relevant `uv.lock` package versions. `uv` itself is not on `PATH`, so the locked CI commands were run directly through `.venv` where possible.
- Ruff check, Ruff format check, compile/import checks, and `scripts/check_secrets.py` passed.
- The full pytest run could not complete in this Windows sandbox. CrewAI Flow initialization stalls in `socket.socketpair()`'s loopback `accept()` while constructing the asyncio self-pipe; the repository test fixture permits this internal socketpair, but the host environment does not complete it.
- A focused configuration/search run reported 22 passed and one failure: the OpenAI provider construction test observed `OPENAI_API_KEY` reappear during CrewAI import/use, although it was unset in the parent shell. No key value was recorded here.
- `uv sync --locked --python 3.13`, fixture evaluation, and offline CLI execution remain unverified because `uv` is unavailable and Flow startup is blocked by the socketpair issue. Do not report the full suite as passing.
