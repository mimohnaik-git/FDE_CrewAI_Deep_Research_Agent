# Deep Research Agent

A rebuild of the CrewAI Research → Analyst → Writer prototype with explicit
retrieval, evidence provenance, structured outputs, claim status, citation
validation and SQLite run history. Streamlit, OpenAI/Anthropic/Ollama selection,
live operational events, usage visibility and Markdown download are retained.

This is a portfolio research application, not a production service or a factual
accuracy guarantee. Web mode currently researches **search excerpts**, not full
webpages. Offline mode uses clearly labeled synthetic fixtures.

## Setup

Use **Python 3.13** (the project excludes 3.14). Install
[uv](https://docs.astral.sh/uv/getting-started/installation/), then from this repository:

```sh
uv sync --locked --python 3.13
uv run --locked streamlit run app.py
```

`pyproject.toml` defines the package; `uv.lock` pins the complete dependency graph,
including development tools. `.python-version` selects 3.13. The compatibility
`requirements.txt` installs the package without the lock; prefer uv for reproducibility.

The default UI is an offline demo and requires no credentials. Select a frozen
fixture and run it. The topic is intentionally fixed to the selected dataset;
offline mode does not answer arbitrary questions from model memory.

## Web search and model configuration

Copy `.env.example` to `.env` or enter keys in the UI's session credential fields.
Never commit `.env`. The application reads dotenv values without loading them into
process environment. UI-entered credentials are passed explicitly to clients.

Web mode requires `SERPER_API_KEY` plus a configured model provider:

| Provider | Configuration | Default model |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Anthropic | `ANTHROPIC_API_KEY` | `anthropic/claude-haiku-4-5-20251001` |
| Ollama | Local server and installed model | `ollama/llama3.1` |

`LLM_PROVIDER=auto` chooses a configured OpenAI key, then Anthropic, then reachable
local Ollama. It fails when none is available. `LLM_MODEL` or the UI model field
can override defaults. Ollama is restricted to a loopback HTTP endpoint, default
`http://localhost:11434`; install Ollama separately and pull the selected model.
The UI exposes an intentional local reachability check. A cloud key's presence
means **configured**, not authenticated or verified. Live provider authentication
and model availability have not been exercised by the offline test suite.

Serper is called through a replaceable `SearchAdapter` protocol. It returns URL,
title and excerpt metadata. HTTP failures are bounded with retries only for
transient network errors, 429 and server errors; there is no silent fallback.
Queries and excerpts are sent to the chosen remote services in web mode.

## Architecture

`ResearchRequest` → CrewAI Flow planning → explicit search → normalization and
URL/content deduplication → exact-quote evidence extraction → claim analysis →
cross-source status assignment → synthesis/report writing → deterministic
citation validation → persisted final report.

CrewAI agents perform semantic planning, extraction, analysis and writing in web
mode. Ordinary Python controls validation, IDs, provenance, retrieval, transitions,
metrics, persistence and evaluation. Frozen scripted reasoning replaces model
calls in offline mode, while exercising the same Flow and integrity checks.

Important claims with support from only one source domain are partially supported;
two domains meet the corroboration threshold. Contradictions and missing evidence
have separate statuses. Domain counts are a heuristic, not proof of independent
publishers or factual truth. Every report section names its claim IDs; rendered
claim statements include citations and their status. Free-form synthesis is
model-authored and cannot be semantically verified by the citation checker.

See [architecture](docs/ARCHITECTURE.md), [evaluation](docs/EVALUATION.md) and
[security](docs/SECURITY.md).

## Run and verify

```sh
uv run --locked python -m research.cli --case corroboration --db data/offline.sqlite3
uv run --locked pytest -q
uv run --locked python -m research.evaluation --output data/evaluation.json
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m compileall -q research app.py crew_setup.py llm_config.py
uv run --locked python -c "import research.workflow, crew_setup, llm_config"
uv run --locked python scripts/check_secrets.py
git diff --check
```

Evaluation includes corroboration, single-source support, conflict, unsupported
claims, duplicate URLs and injected instructions inside source text, plus expected
retrieval failure. Metrics come from execution; no external factual benchmark is
claimed. Default tests strip provider/search keys and block application networking.
Windows asyncio's internal socketpair is the only network-block exemption.

GitHub Actions performs a locked clean install, lint/format, tests, compile/import,
evaluation, offline run, secret checks and diff checks without API credentials.

## Persistence and limitations

`RESEARCH_DB` defaults to `data/research.sqlite3`. SQLite stores run metadata,
normalized sources, exact quotes, claim status, metrics and validated report
content. Failed runs retain a safe failure category and never offer report export.
The UI shows recent run summaries; it does not yet reopen old reports.

Tokens are recorded when CrewAI provides usage; null means unknown. Search-call
counts measure logical queries, not retry attempts. Latency measures workflow time.
Tracing/telemetry are disabled and CrewAI storage is kept under ignored `data/`.
CrewAI itself may initialize per-user credential storage during import even with
tracing disabled; sandboxed Windows verification redirected LOCALAPPDATA locally.

Limitations: search snippets can omit context; source dates/publisher ownership
are not independently verified; semantic evidence relevance and synthesis can be
wrong; domain corroboration cannot guarantee independence; injection tests prove
fixed workflow/tool boundaries, not universal model resistance. No hosted-service
authentication, per-user run isolation, cancellation, crawl/PDF ingestion, resumable
runs or production deployment is implemented. Reports need human review. Do not
enter credentials into research topics or source content; those are persisted data.

The rebuild is merged into `main`. The `prototype-baseline-v1` tag preserves the
prototype baseline.
