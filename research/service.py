"""Application service: create persisted runs, including configuration failures."""

import time

from research.models import WorkflowState, now
from research.providers import get_llm
from research.reasoning import CrewReasoner, OfflineReasoner
from research.search import FixtureSearch, SearchUnavailable, SerperSearch
from research.workflow import ResearchFlow


def run_research(request, store, config=None, search_key="", case="corroboration", event=None):
    started = time.monotonic()
    state = WorkflowState(request=request)
    store.save(state)
    search = None
    try:
        if request.mode == "offline":
            search = FixtureSearch(case=case)
            reasoner = OfflineReasoner(search.case)
            provider, model = "offline", "fixture-v1"
        else:
            if config is None:
                raise ValueError("Web mode requires explicit model configuration")
            state.provider = config.provider
            state.model = config.model or "default"
            search = SerperSearch(search_key)
            llm, provider, model = get_llm(config)
            reasoner = CrewReasoner(llm, state.metrics)
        flow = ResearchFlow(request, search, reasoner, store, event, provider, model)
        flow.state.id = state.id
        flow.state.started_at = state.started_at
        if isinstance(reasoner, CrewReasoner):
            reasoner.metrics = flow.state.metrics
        return flow.run()
    except Exception as exc:
        state.status = "failed"
        if isinstance(exc, SearchUnavailable):
            state.failure_reason = "Search unavailable: web mode requires a configured Serper key"
        elif isinstance(exc, RuntimeError):
            state.failure_reason = (
                "Provider unavailable: configure a cloud key or start local Ollama"
            )
        else:
            state.failure_reason = f"{type(exc).__name__}: configuration or initialization failed"
        state.finished_at = now()
        state.metrics.latency_seconds = time.monotonic() - started
        store.save(state)
        if event:
            event("Failed")
        return state
    finally:
        if isinstance(search, SerperSearch):
            search.close()
