# Evaluation

Run `uv run --locked python -m research.evaluation --output data/evaluation.json`.
It uses frozen synthetic data in `research/fixtures.json`, a fixture search adapter,
scripted reasoning and the real CrewAI Flow. No paid API, dotenv credentials or
model-memory answer is used. A temporary SQLite database is cleaned up after each
CLI evaluation. The harness exits nonzero when expectations fail.

The six cases cover two-domain corroboration and URL duplication, single-source
support, conflicting measurements, an unsupported forecast, source text instructing
the system to read a key/add tools/skip validation, and unavailable retrieval.
Expected source counts, duplicate counts, claim statuses and workflow results are
frozen separately from observed metrics. These are contract scenarios, not an
independent estimate of live LLM research quality.

Metrics:

- Schema validity: observed state serializes and revalidates through the schema.
- Citation integrity: completed report passes deterministic checks.
- Invalid citation count: number of integrity errors on the completed artifact.
- Source coverage: distinct sources cited in report body / accepted sources;
  bibliography references do not inflate this metric.
- Evidence linkage: claims with supporting or contradictory evidence / all claims.
- Supported/unsupported rates: supported claims / all claims and all other statuses
  / all claims. “Unsupported” here includes partial and conflicting claims.
- Duplicate handling: number of duplicate URL/content results removed.
- Workflow completion/failure, logical query calls and observed model calls.

Null denotes a non-applicable denominator or absent report. A deliberately failed
retrieval is an evaluation pass when the expected outcome is failure; it is not
counted as a successfully completed research run.

Executed fixture results during this rebuild: 6/6 expectations passed, 5 completed
runs and 1 expected failure. All states were schema-valid; all completed reports
passed citation integrity with zero invalid citations. Body source coverage and
evidence linkage were 1.0 for corroboration, single-source, conflict and injection,
and 0.0 for the unsupported forecast. Supported rates were 1.0 for corroboration
and injection, 0.0 for the other three completed cases. One duplicate was removed
in corroboration; all cases made zero model calls. Regenerate the JSON to assess
future changes; these values apply only to this tiny frozen dataset.

The unit suite separately mutates reports with nonexistent/malformed IDs, missing
URLs, duplicate IDs and unsupported verified claims. Integration tests reject bad
semantic output and writer citations, persist provider/retrieval failures, and
prove injected source instructions do not alter the fixed stage sequence. Mocked
CrewAI boundary tests assert no tools, no delegation, no verbose thoughts, and
structured output enforcement. Streamlit tests check report/source/evidence/metrics
views and absence of export for a failed run.

The suite removes model/search credential environment variables and blocks socket
connections, except Windows's internal standard-library socketpair for asyncio.
Live OpenAI, Anthropic, Ollama and Serper interactions are not validated by these
fixtures. Semantic citation correctness, model resilience to injection and general
research quality require separate live evaluation and human review.
