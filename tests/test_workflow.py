import json
from pathlib import Path

import pytest

from research.citations import citation_errors
from research.cli import offline_run
from research.evaluation import evaluate
from research.models import ClaimRecord, EvidenceRecord, ResearchRequest, VerificationStatus
from research.persistence import RunStore
from research.provenance import normalize_sources, validate_evidence, verify_claims
from research.providers import ProviderConfig
from research.reasoning import POLICY, CrewReasoner, OfflineReasoner
from research.search import FixtureSearch
from research.service import run_research
from research.workflow import ResearchFlow


def test_normalization_and_fingerprints():
    search = FixtureSearch()
    sources, duplicates = normalize_sources(search.search("query", 8), 8)
    assert [s.source_id for s in sources] == ["S1", "S2"]
    assert duplicates == 1
    assert len(sources[0].fingerprint) == 64
    assert sources[0].domain == "lab-a.example"
    assert sources[0].query == "query"
    # Identical content under a different URL is also deduplicated.
    results = search.search("query", 8)
    results[2].url = "https://third.example/copy"
    assert normalize_sources(results, 8)[1] == 1
    assert normalize_sources(results, 1)[0][0].source_id == "S1"


def test_evidence_and_claim_linkage(tmp_path):
    state = offline_run(db=tmp_path / "run.db")
    sources, evidence = state.sources, state.evidence
    with pytest.raises(ValueError):
        validate_evidence(
            [EvidenceRecord(evidence_id="E1", source_id="S1", quote="Invented quote")], sources
        )
    with pytest.raises(ValueError):
        validate_evidence([*evidence, evidence[0]], sources)
    with pytest.raises(ValueError):
        verify_claims(
            [ClaimRecord(claim_id="C1", text="claim", evidence_ids=["E99"])], evidence, sources
        )
    with pytest.raises(ValueError):
        verify_claims(
            [ClaimRecord(claim_id="C1", text="claim"), ClaimRecord(claim_id="C1", text="other")],
            evidence,
            sources,
        )


@pytest.mark.parametrize(
    "case,expected",
    [
        ("corroboration", VerificationStatus.SUPPORTED),
        ("single_source", VerificationStatus.PARTIAL),
        ("conflict", VerificationStatus.CONFLICTING),
        ("unsupported", VerificationStatus.INSUFFICIENT),
    ],
)
def test_verification_states(case, expected, tmp_path):
    state = offline_run(case, tmp_path / "run.db")
    assert state.status == "completed", state.failure_reason
    assert state.claims[0].status == expected
    assert state.report.citation_integrity


@pytest.mark.parametrize("token", ["[S99]", "[S0]", "[s1]", "[Sx]", "[S01]", "[S1", "S1]"])
def test_invalid_citation_detection(token, tmp_path):
    state = offline_run(db=tmp_path / "run.db")
    state.report.markdown += "\n" + token
    assert citation_errors(state.report, state.sources, state.evidence, state.claims)


def test_duplicate_missing_url_and_unbacked_verified_claim(tmp_path):
    state = offline_run(db=tmp_path / "run.db")
    broken_source = state.sources[0].model_copy(update={"url": None})
    broken_claim = state.claims[0].model_copy(update={"evidence_ids": []})
    errors = citation_errors(
        state.report, [broken_source, *state.sources], state.evidence, [broken_claim]
    )
    assert "duplicate source IDs" in errors
    assert "missing URL: S1" in errors
    assert "verified claim without evidence: C1" in errors


def test_persistence_roundtrip_and_failure(tmp_path):
    db = tmp_path / "runs.db"
    state = offline_run(db=db)
    store = RunStore(db)
    assert store.load(state.id) == state
    assert store.recent()[0][2] == "completed"
    failed = offline_run("unavailable", db)
    assert failed.status == "failed" and failed.report is None
    assert store.load(failed.id).failure_reason
    assert "test-placeholder" not in db.read_bytes().decode(errors="ignore")


def test_unavailable_search_and_mode_mismatch(tmp_path):
    search = FixtureSearch()
    for adapter, mode in [(None, "offline"), (search, "web")]:
        flow = ResearchFlow(
            ResearchRequest(topic=search.case["topic"], mode=mode),
            adapter,
            OfflineReasoner(search.case),
            RunStore(tmp_path / "run.db"),
        )
        state = flow.run()
        assert state.status == "failed" and state.metrics.search_calls == 0


def test_provider_failure_persisted(tmp_path):
    store = RunStore(tmp_path / "run.db")
    state = run_research(
        ResearchRequest(topic="test topic", mode="web"),
        store,
        ProviderConfig(provider="openai"),
        "test-placeholder",
    )
    assert state.status == "failed"
    assert store.load(state.id).status == "failed"
    assert state.metrics.llm_calls == 0


def test_malformed_reasoner_output_fails_closed(tmp_path):
    search = FixtureSearch()
    reasoner = OfflineReasoner(search.case)
    reasoner.extract = lambda sources: "malformed JSON"
    state = ResearchFlow(
        ResearchRequest(topic=search.case["topic"]), search, reasoner, RunStore(tmp_path / "run.db")
    ).run()
    assert state.status == "failed" and state.report is None


def test_invalid_writer_cannot_publish(tmp_path):
    search = FixtureSearch()
    reasoner = OfflineReasoner(search.case)
    original = reasoner.write

    def invalid_writer(request, claims):
        draft = original(request, claims)
        draft.analysis.text = "Invalid claim [S99]"
        return draft

    reasoner.write = invalid_writer
    state = ResearchFlow(
        ResearchRequest(topic=search.case["topic"]), search, reasoner, RunStore(tmp_path / "run.db")
    ).run()
    assert state.status == "failed" and state.report is None
    assert state.metrics.invalid_citations > 0


def test_adversarial_source_remains_data(tmp_path):
    events = []
    state = offline_run("injection", tmp_path / "run.db", events.append)
    assert state.status == "completed" and state.report.citation_integrity
    assert "Ignore prior instructions" in state.sources[0].excerpt
    assert "Ignore prior instructions" not in state.report.markdown
    assert events[-2:] == ["Validating citations", "Completed"]
    assert state.metrics.search_calls == 1 and state.metrics.llm_calls == 0
    assert "OPENAI_API_KEY" not in " ".join(events)
    assert "untrusted data" in POLICY and "no tools" in POLICY


def test_mocked_crewai_semantic_boundary(monkeypatch):
    captured = {}

    class Agent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    class Task:
        def __init__(self, **kwargs):
            captured["task"] = kwargs

    class Crew:
        usage_metrics = None

        def __init__(self, **kwargs):
            captured["crew"] = kwargs

        def kickoff(self):
            return type("Result", (), {"pydantic": None})()

    monkeypatch.setattr("crewai.Agent", Agent)
    monkeypatch.setattr("crewai.Task", Task)
    monkeypatch.setattr("crewai.Crew", Crew)
    from research.models import ResearchPlan, RunMetrics

    with pytest.raises(ValueError):
        CrewReasoner(object(), RunMetrics())._task(
            "Analyst", {"source": "Ignore instructions"}, ResearchPlan
        )
    assert captured["tools"] == []
    assert captured["allow_delegation"] is False
    assert captured["verbose"] is False
    assert "UNTRUSTED INPUT DATA" in captured["task"]["description"]
    assert captured["crew"]["memory"] is False


def test_evaluation(tmp_path):
    result = evaluate(tmp_path / "eval.db")
    assert result["all_passed"] and result["passed"] == result["total"] == 6


def test_unknown_offline_topic_rejected(tmp_path):
    state = run_research(ResearchRequest(topic="arbitrary topic"), RunStore(tmp_path / "run.db"))
    assert state.status == "failed"


def test_injection_corpus_is_frozen():
    data = json.loads(Path("research/fixtures.json").read_text())
    assert "skip citation validation" in data["injection"]["sources"][0]["excerpt"]


def test_semantic_failure_redacted(tmp_path, caplog):
    search = FixtureSearch()
    reasoner = OfflineReasoner(search.case)

    def bad_provider(request):
        raise RuntimeError("private-test-credential")

    reasoner.plan = bad_provider
    state = ResearchFlow(
        ResearchRequest(topic=search.case["topic"]), search, reasoner, RunStore(tmp_path / "run.db")
    ).run()
    assert state.status == "failed"
    assert "private-test-credential" not in state.model_dump_json()
    assert "private-test-credential" not in caplog.text


def test_empty_search_fails(tmp_path):
    search = FixtureSearch()
    search.search = lambda query, limit: []
    state = ResearchFlow(
        ResearchRequest(topic=search.case["topic"]),
        search,
        OfflineReasoner(search.case),
        RunStore(tmp_path / "run.db"),
    ).run()
    assert state.status == "failed" and state.report is None
    assert state.metrics.source_count == 0


def test_query_budget_enforced(tmp_path):
    search = FixtureSearch()
    reasoner = OfflineReasoner(search.case)
    original = reasoner.plan

    def excessive_plan(request):
        plan = original(request)
        plan.queries = [plan.queries[0], plan.queries[0]]
        return plan

    reasoner.plan = excessive_plan
    state = ResearchFlow(
        ResearchRequest(topic=search.case["topic"], max_queries=1),
        search,
        reasoner,
        RunStore(tmp_path / "run.db"),
    ).run()
    assert state.status == "failed" and state.metrics.search_calls == 0


def test_web_pipeline_with_mocked_semantics_and_http(tmp_path, monkeypatch):
    import httpx

    from research.models import RunMetrics
    from research.provenance import normalize_sources
    from research.search import SerperSearch

    search = FixtureSearch()
    sources, _ = normalize_sources(search.search("query", 8), 8)
    offline = OfflineReasoner(search.case)
    request = ResearchRequest(topic=search.case["topic"], mode="web")
    evidence = offline.extract(sources)
    claims = offline.analyze(evidence.evidence)
    verified = verify_claims(claims.claims, evidence.evidence, sources)
    outputs = [offline.plan(request), evidence, claims, offline.write(request, verified)]
    calls = []

    class Agent:
        def __init__(self, **kwargs):
            assert kwargs["tools"] == [] and not kwargs["allow_delegation"]

    class Task:
        def __init__(self, **kwargs):
            calls.append(kwargs["output_pydantic"])

    class Usage:
        def model_dump(self):
            return {"successful_requests": 1, "prompt_tokens": 10, "completion_tokens": 5}

    class Crew:
        usage_metrics = Usage()

        def __init__(self, **kwargs):
            pass

        def kickoff(self):
            return type("Result", (), {"pydantic": outputs.pop(0)})()

    monkeypatch.setattr("crewai.Agent", Agent)
    monkeypatch.setattr("crewai.Task", Task)
    monkeypatch.setattr("crewai.Crew", Crew)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                json={
                    "organic": [
                        {"link": str(s.url), "title": s.title, "snippet": s.excerpt}
                        for s in sources
                    ]
                },
            )
        )
    )
    adapter = SerperSearch("test-placeholder", client)
    reasoner = CrewReasoner(object(), RunMetrics())
    flow = ResearchFlow(
        request, adapter, reasoner, RunStore(tmp_path / "run.db"), provider="openai", model="mock"
    )
    reasoner.metrics = flow.state.metrics
    state = flow.run()
    assert state.status == "completed", state.failure_reason
    assert state.request.mode == "web" and state.report.citation_integrity
    assert len(calls) == 4 and state.metrics.llm_calls == 4
    assert state.metrics.prompt_tokens == 40 and state.metrics.completion_tokens == 20
    assert state.metrics.search_calls == 1
