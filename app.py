"""Streamlit front end with session credentials and safe operational events."""

import os
import queue
import threading

import streamlit as st
from dotenv import dotenv_values

from research.models import ResearchRequest
from research.persistence import RunStore
from research.providers import DEFAULT_MODELS, ProviderConfig, check_providers
from research.search import FixtureSearch
from research.service import run_research

st.set_page_config(page_title="Deep Research Agent", layout="wide")
st.title("Deep Research Agent")
st.caption("Explicit retrieval → evidence → claim analysis → report → citation validation")
settings = {**dotenv_values(".env"), **os.environ}
for key, value in {"running": False, "state": None, "events": [], "queue": None}.items():
    if key not in st.session_state:
        st.session_state[key] = value

mode = st.sidebar.selectbox("Research mode", ["offline", "web"], disabled=st.session_state.running)
if mode == "offline":
    st.info("Offline demo: frozen synthetic fixtures, no web research or paid model calls.")
    case = st.sidebar.selectbox(
        "Fixture",
        ["corroboration", "single_source", "conflict", "unsupported", "injection"],
        disabled=st.session_state.running,
    )
    topic = FixtureSearch(case=case).case["topic"]
    st.text_input("Topic", value=topic, disabled=True)
    config, search_key = None, ""
else:
    case = "corroboration"
    topic = st.text_area("Research topic", disabled=st.session_state.running)
    provider = st.sidebar.selectbox(
        "Model provider",
        ["auto", "openai", "anthropic", "ollama"],
        disabled=st.session_state.running,
    )
    model = st.sidebar.text_input(
        "Model (optional)",
        placeholder=DEFAULT_MODELS.get(provider, "Choose provider default"),
        disabled=st.session_state.running,
    )
    with st.sidebar.expander("Session credentials"):
        openai_key = st.text_input(
            "OpenAI key",
            value=settings.get("OPENAI_API_KEY", ""),
            type="password",
            key="openai_key",
        )
        anthropic_key = st.text_input(
            "Anthropic key",
            value=settings.get("ANTHROPIC_API_KEY", ""),
            type="password",
            key="anthropic_key",
        )
        search_key = st.text_input(
            "Serper search key",
            value=settings.get("SERPER_API_KEY", ""),
            type="password",
            key="search_key",
        )
    config = ProviderConfig(
        provider=provider,
        model=model or None,
        openai_key=openai_key,
        anthropic_key=anthropic_key,
        ollama_url=settings.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    )
    probe = st.sidebar.button("Check local Ollama")
    for status in check_providers(config, probe_local=probe):
        st.sidebar.caption(f"{status.provider}: {status.status} — {status.detail}")
    st.caption(
        "Web mode retrieves search excerpts. Citation integrity does not prove factual accuracy."
    )


def worker(request, config, search_key, case, channel, db):
    try:
        state = run_research(
            request,
            RunStore(db),
            config,
            search_key,
            case,
            lambda message: channel.put(("event", message)),
        )
        channel.put(("done", state))
    except Exception:
        channel.put(("error", "Run failed during persistence or initialization"))


if st.button(
    "Run research", type="primary", disabled=st.session_state.running or len(topic.strip()) < 3
):
    try:
        request = ResearchRequest(topic=topic, mode=mode)
    except ValueError:
        st.error("Enter a topic between 3 and 1000 characters.")
    else:
        channel = queue.Queue()
        st.session_state.update(running=True, state=None, events=[], queue=channel)
        threading.Thread(
            target=worker,
            args=(
                request,
                config,
                search_key,
                case,
                channel,
                settings.get("RESEARCH_DB", "data/research.sqlite3"),
            ),
            daemon=True,
        ).start()
        st.rerun()


@st.fragment(run_every=0.5)
def activity():
    if st.session_state.queue:
        while True:
            try:
                kind, payload = st.session_state.queue.get_nowait()
            except queue.Empty:
                break
            if kind == "event":
                st.session_state.events.append(payload)
            elif kind == "done":
                st.session_state.state = payload
                st.session_state.running = False
                st.rerun()
            elif kind == "error":
                st.session_state.events.append(payload)
                st.session_state.running = False
                st.session_state.queue = None
                st.rerun()
    if st.session_state.events:
        with st.expander("Workflow activity", expanded=st.session_state.running):
            for event in st.session_state.events:
                st.text(event)


activity()
state = st.session_state.state
if state:
    st.caption(f"Run {state.id} • {state.provider} / {state.model} • {state.status}")
    if state.status == "failed":
        st.error(state.failure_reason)
    report_tab, sources_tab, evidence_tab, metrics_tab = st.tabs(
        ["Report", "Sources", "Evidence and claims", "Metrics"]
    )
    with report_tab:
        if state.report and state.report.citation_integrity and state.status == "completed":
            st.success(
                "Citation integrity passed. Review evidence and uncertainty before relying on findings."
            )
            st.markdown(state.report.markdown)
            st.download_button(
                "Download Markdown",
                state.report.markdown,
                file_name=f"research-{state.id}.md",
                mime="text/markdown",
            )
    with sources_tab:
        st.dataframe([s.model_dump(mode="json") for s in state.sources])
    with evidence_tab:
        st.dataframe([e.model_dump() for e in state.evidence])
        st.dataframe([c.model_dump() for c in state.claims])
    with metrics_tab:
        st.json(state.metrics.model_dump())
        st.caption("Null token values mean unavailable; offline mode makes zero model calls.")
with st.expander("Recent persisted runs"):
    st.dataframe(
        RunStore(settings.get("RESEARCH_DB", "data/research.sqlite3")).recent(), column_order=None
    )
