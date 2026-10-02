# Architecture

The prototype entry files remain: `app.py` is Streamlit, `crew_setup.py` re-exports
the research Flow and CrewAI reasoner, and `llm_config.py` re-exports provider
configuration. The old implicit model-memory research path has been replaced.

```text
Validated request
  └─ ResearchFlow[WorkflowState]
       planning → retrieval/normalization → extraction → analysis/verification
       → synthesis/writing → citation validation
  └─ SQLite state and metadata, including failures
```

- `models.py`: strict Pydantic contracts, constrained IDs, bounded text/counts,
  timezone-aware retrieval dates, quote and claim/report linkage structures.
- `search.py`: adapter protocol, frozen fixtures and Serper excerpt retrieval.
  Fixed API endpoint, no redirects, timeouts, response size cap, bounded retries.
- `provenance.py`: normalized HTTP(S) URLs, tracking parameter removal, SHA-256
  normalized-excerpt fingerprints, URL/content deduplication, run-local S1… IDs.
  Evidence must quote a contiguous substring of the stored normalized excerpt.
- `reasoning.py`: tool-free CrewAI agents for planner, researcher, analyst and
  writer, each with Pydantic task output. The offline reasoner reads frozen
  annotations and intentionally refuses arbitrary topics.
- `workflow.py`: explicit start/listen transitions; models never select the next
  stage. A request/search mode mismatch, empty retrieval, invalid evidence,
  malformed output or bad citation fails the run.
- `citations.py`: render known claims/statuses and build source metadata from
  provenance, then validate inline IDs, URLs, duplicates and evidence links.
- `persistence.py`: SQLite transactions with connections closed deterministically;
  saves structured state and queryable metadata, validated report content only.
- `service.py`: session configuration/client lifecycle and persisted setup failures.

Verification statuses are supported, partially supported, conflicting and
insufficient evidence. Evidence relationship labels come from semantic analysis;
Python then assigns statuses based on those links and distinct source domains.
Domain corroboration does not establish publisher ownership, independence or truth.

Every report section references known claim IDs. The deterministic renderer appends
claim text, source references and status labels. The writer's additional prose is
not subject to automated semantic entailment testing. Citation integrity means
references and links passed checks, never that all prose is correct.

The UI's background worker emits only fixed operational messages. Streamlit's
fragment drains a queue while the run proceeds; report, provenance, evidence/status
and metrics have separate tabs. Hidden agent thought fields are never inspected.

Provider/search credentials are excluded from serialized configuration and never
included in workflow state. UI credentials do not mutate process environment.
Runtime-only storage/telemetry settings are configured before CrewAI imports.

Underlying Flow and structured-task APIs:
[Flows](https://docs.crewai.com/en/concepts/flows),
[Tasks](https://docs.crewai.com/en/concepts/tasks).
