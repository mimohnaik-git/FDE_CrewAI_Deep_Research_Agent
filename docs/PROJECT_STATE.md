# Project state

## Purpose and current shape

This repository contains a Streamlit research application. A CrewAI Flow sequences planning, explicit retrieval, evidence extraction, claim verification, report writing, and citation validation. Python owns stage transitions, source normalization, evidence checks, citation acceptance, persistence, and fixture evaluation. SQLite stores run state. Offline mode uses frozen synthetic fixtures; web mode uses search excerpts and a configured model provider.

Key areas:

- `app.py`: Streamlit entry point.
- `research/`: workflow, retrieval, provider configuration, provenance, persistence, reports, and evaluation.
- `research/fixtures.json`: frozen offline scenarios and expected evaluation outcomes.
- `tests/`: unit and integration checks for workflow, UI, and configuration/search boundaries.
- `.github/workflows/verify.yml`: locked offline verification workflow.
- `docs/ARCHITECTURE.md`, `docs/EVALUATION.md`, and `docs/SECURITY.md`: detailed design, evaluation limits, and security model.

## Locked runtime

`uv.lock` specifies Python 3.13 and currently resolves these relevant packages:

| Package | Locked version |
| --- | --- |
| CrewAI | 1.15.23 |
| Streamlit | 1.62.0 |
| Pydantic | 2.12.5 |
| httpx | 0.28.1 |
| python-dotenv | 1.2.4 |
| pytest | 8.4.2 |
| Ruff | 0.16.10 |

Use `uv sync --locked --python 3.13`; do not resolve or upgrade packages during documentation or workflow work. Context7 confirms the public Flow concepts used here (`Flow`, `@start`, and `@listen`), but its CrewAI index does not provide a `1.15.23` documentation snapshot. The repository imports these APIs from `crewai.flow.flow` and implements the ordered stages in `research/workflow.py`. For version-specific behavior, inspect `crewai/flow/flow.py` from the installed locked CrewAI package; the [upstream Flow API](https://github.com/crewaiinc/crewai/blob/main/lib/crewai/src/crewai/flow/flow.py) is a general reference and may have moved beyond the locked version.

## Verification entry points

The default locked suite is documented in `README.md` and `.github/workflows/verify.yml`. It includes Ruff, pytest, compile/import checks, frozen evaluation, offline CLI execution, and secret-pattern checks. Tests block application networking and remove provider/search keys. Routine verification must not require paid API calls or deployment.

## Known limitations

- Web retrieval processes search excerpts, not fetched full pages.
- Offline evaluation validates six frozen synthetic cases, not general factual accuracy or live model quality.
- Evidence relevance, source independence, source freshness, and generated prose are not fully verified by deterministic checks.
- Provider authentication, live model behavior, and hosted-service operation are not established by the offline suite.
- The app is a portfolio project, not a production service; see `docs/SECURITY.md` for deployment gaps.

## Integration pilot scope

This pilot adds repository guidance and local skills. It does not change application behavior, dependencies, tests, evaluation expectations, or CI.
