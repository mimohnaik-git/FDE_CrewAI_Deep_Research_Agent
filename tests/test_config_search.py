import os
from datetime import datetime

import httpx
import pytest
from pydantic import ValidationError

from research.models import ClaimRecord, ResearchPlan, ResearchRequest, SearchResult
from research.providers import ProviderConfig, check_providers, get_llm, resolve_provider
from research.search import (
    FixtureSearch,
    SearchUnavailable,
    SerperSearch,
    local_ollama_url,
    normalize_url,
)


@pytest.mark.parametrize("topic", ["", "ab", " " * 5, "a" * 1001])
def test_invalid_request(topic):
    with pytest.raises(ValidationError):
        ResearchRequest(topic=topic)


def test_model_link_validation():
    with pytest.raises(ValidationError):
        ResearchPlan(
            questions=[{"question_id": "Q1", "question": "Why?"}],
            queries=[{"question_id": "Q2", "text": "query"}],
        )
    with pytest.raises(ValidationError):
        ClaimRecord(
            claim_id="C1", text="A claim", evidence_ids=["E1"], contradicting_evidence_ids=["E1"]
        )
    with pytest.raises(ValidationError):
        SearchResult(
            url="https://example.com",
            title="title",
            excerpt="text",
            query="query",
            retrieved_at=datetime(2020, 1, 1),
        )


def test_config_and_provider_resolution(monkeypatch):
    config = ProviderConfig.from_env(
        {"OPENAI_API_KEY": "test-placeholder", "LLM_MODEL": "custom-model"}
    )
    assert resolve_provider(config) == "openai"
    assert "test-placeholder" not in config.model_dump_json()
    assert "test-placeholder" not in repr(config)
    assert "OPENAI_API_KEY" not in os.environ
    assert check_providers(config)[0].status == "configured"
    with pytest.raises(ValidationError):
        ProviderConfig(provider="unknown")
    with pytest.raises(RuntimeError):
        resolve_provider(ProviderConfig(provider="anthropic"))
    monkeypatch.setattr("research.providers.ollama_reachable", lambda url: False)
    with pytest.raises(RuntimeError):
        resolve_provider(ProviderConfig())
    with pytest.raises(RuntimeError):
        resolve_provider(ProviderConfig(provider="ollama"))


@pytest.mark.parametrize(
    "provider,field", [("openai", "openai_key"), ("anthropic", "anthropic_key"), ("ollama", None)]
)
def test_explicit_provider_construction(provider, field, monkeypatch):
    captured = {}
    monkeypatch.setattr("crewai.LLM", lambda **kwargs: captured.update(kwargs) or object())
    monkeypatch.setattr("research.providers.ollama_reachable", lambda url: True)
    config = ProviderConfig(provider=provider, **({field: "test-placeholder"} if field else {}))
    _, resolved, _ = get_llm(config)
    assert resolved == provider
    assert (
        captured["api_key"] == "test-placeholder"
        if field
        else captured["base_url"].startswith("http://localhost")
    )
    assert "OPENAI_API_KEY" not in os.environ


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/a",
        "http://169.254.169.254/",
        "http://localhost/",
        "https://user:password@example.com/",
        "https://example.com:8443/",
    ],
)
def test_unsafe_sources(url):
    with pytest.raises(ValueError):
        normalize_url(url)


def test_url_normalization():
    assert (
        normalize_url("https://EXAMPLE.com:443/a?utm_source=x&b=2&a=1#frag")
        == "https://example.com/a?a=1&b=2"
    )
    with pytest.raises(ValueError):
        local_ollama_url("https://external.example/api")


def test_fixture_search_failure():
    with pytest.raises(SearchUnavailable):
        FixtureSearch(case="unavailable").search("test", 3)


def test_search_missing_key():
    with pytest.raises(SearchUnavailable):
        SerperSearch("")


def test_serper_search_and_retry():
    calls, waits = [], []

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={
                "organic": [
                    {"link": "https://example.com/x", "title": "Result", "snippet": "An excerpt."}
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = SerperSearch("test-placeholder", client, waits.append)
    results = adapter.search("query", 2)
    assert len(results) == 1 and results[0].query == "query"
    assert waits == [0.5, 1.0]
    assert calls[0].headers["X-API-KEY"] == "test-placeholder"


@pytest.mark.parametrize("status,payload", [(401, {}), (200, []), (200, {"organic": "bad"})])
def test_malformed_search(status, payload):
    client = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(status, json=payload))
    )
    with pytest.raises(SearchUnavailable):
        SerperSearch("test-placeholder", client).search("query", 3)


def test_network_failure_retries():
    calls = []

    def handler(req):
        calls.append(req)
        raise httpx.ConnectError("not reachable")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(SearchUnavailable):
        SerperSearch("test-placeholder", client, lambda _: None).search("query", 3)
    assert len(calls) == 3
