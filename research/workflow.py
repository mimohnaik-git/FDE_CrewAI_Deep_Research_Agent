"""CrewAI Flow controls stages; models cannot change transitions or use tools."""

import time

from crewai.flow.flow import Flow, listen, start

from research.citations import citation_errors, render_report
from research.models import (
    ClaimBatch,
    EvidenceBatch,
    ReportDraft,
    ResearchPlan,
    VerificationStatus,
    WorkflowState,
    now,
)
from research.provenance import normalize_sources, validate_evidence, verify_claims
from research.search import SearchUnavailable


class ResearchFlow(Flow[WorkflowState]):
    def __init__(
        self, request, search, reasoner, store, event=None, provider="offline", model="fixture-v1"
    ):
        super().__init__(tracing=False)
        self.suppress_flow_events = True
        self.state.request = request
        self.state.provider = provider
        self.state.model = model
        self.search = search
        self.reasoner = reasoner
        self.store = store
        self.event = event or (lambda message: None)
        self._started = 0.0

    def emit(self, message):
        # Callers receive fixed stage messages only, never LLM outputs/thoughts.
        self.event(message)

    def semantic(self, method, *args):
        try:
            return method(*args)
        except Exception:
            raise ValueError(
                "Semantic stage failed: provider request or structured output invalid"
            ) from None

    @start()
    def planning(self):
        self.state.status = "running"
        self.store.save(self.state)
        if self.search is None or self.search.mode != self.state.request.mode:
            raise SearchUnavailable("Requested retrieval mode is unavailable")
        self.emit("Planning research")
        self.state.plan = ResearchPlan.model_validate(
            self.semantic(self.reasoner.plan, self.state.request).model_dump()
        )
        if len(self.state.plan.queries) > self.state.request.max_queries:
            raise ValueError("Plan exceeded query budget")

    @listen(planning)
    def retrieval(self):
        results = []
        for index, query in enumerate(self.state.plan.queries, 1):
            self.emit(f"Executing query {index}")
            self.state.metrics.search_calls += 1
            results.extend(self.search.search(query.text, self.state.request.max_sources))
        self.state.sources, duplicates = normalize_sources(results, self.state.request.max_sources)
        self.state.metrics.duplicate_sources = duplicates
        self.state.metrics.source_count = len(self.state.sources)
        if not self.state.sources:
            raise SearchUnavailable("Retrieval returned no usable sources")
        self.emit(f"Sources retrieved: {len(self.state.sources)}")
        self.store.save(self.state)

    @listen(retrieval)
    def extraction(self):
        batch = EvidenceBatch.model_validate(
            self.semantic(self.reasoner.extract, self.state.sources).model_dump()
        )
        validate_evidence(batch.evidence, self.state.sources)
        self.state.evidence = batch.evidence
        self.state.metrics.evidence_count = len(batch.evidence)
        self.emit(f"Evidence extracted: {len(batch.evidence)}")

    @listen(extraction)
    def verification(self):
        batch = ClaimBatch.model_validate(
            self.semantic(self.reasoner.analyze, self.state.evidence).model_dump()
        )
        self.state.claims = verify_claims(batch.claims, self.state.evidence, self.state.sources)
        self.state.metrics.supported_claims = sum(
            c.status == VerificationStatus.SUPPORTED for c in self.state.claims
        )
        self.state.metrics.unverified_claims = (
            len(self.state.claims) - self.state.metrics.supported_claims
        )
        self.emit(
            f"Claims checked: {len(self.state.claims)}; supported: {self.state.metrics.supported_claims}"
        )

    @listen(verification)
    def writing(self):
        self.emit("Synthesizing analysis and drafting report")
        draft = ReportDraft.model_validate(
            self.semantic(self.reasoner.write, self.state.request, self.state.claims).model_dump()
        )
        self.state.report = render_report(
            draft, self.state.claims, self.state.sources, self.state.request.mode
        )

    @listen(writing)
    def validation(self):
        self.emit("Validating citations")
        errors = citation_errors(
            self.state.report, self.state.sources, self.state.evidence, self.state.claims
        )
        self.state.metrics.invalid_citations = len(errors)
        if errors:
            raise ValueError("Report citation integrity failed")
        self.state.report.citation_integrity = True
        self.state.status = "completed"
        self.emit("Completed")
        return WorkflowState.model_validate(self.state.model_dump())

    def run(self):
        self._started = time.monotonic()
        try:
            self.kickoff()
        except Exception as exc:
            self.state.status = "failed"
            # Never expose/persist upstream exception bodies, which can contain secrets.
            self.state.failure_reason = f"{type(exc).__name__}: research failed; check configuration, retrieval and structured output contracts"
            self.state.report = None
            self.emit("Failed")
        finally:
            self.state.finished_at = now()
            self.state.metrics.latency_seconds = time.monotonic() - self._started
            self.store.save(self.state)
        return WorkflowState.model_validate(self.state.model_dump())
