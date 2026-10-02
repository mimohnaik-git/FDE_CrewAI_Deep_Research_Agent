"""
app.py
------
Streamlit front-end for the CrewAI Research -> Analyst -> Writer demo.

Run with:
    streamlit run app.py

What it shows in class / in a client demo:
  1. A sidebar to pick which LLM backs the crew — a paid OpenAI or
     Anthropic key, or a free local Ollama model — with a live status
     check so it's obvious which options are actually usable right now.
  2. A text box where you paste/type a topic.
  3. A live-updating log of what each agent is doing (thoughts, tool
     calls, results) as the crew runs, in real time.
  4. Once the crew finishes, the final article is streamed onto the
     page word-by-word (like a typewriter / ChatGPT-style effect),
     followed by a token-usage summary for the run.
"""

import os
import time
import queue
import threading

import streamlit as st
from dotenv import load_dotenv

from crew_setup import build_crew
from llm_config import DEFAULT_MODELS, check_providers, resolve_provider

load_dotenv()

st.set_page_config(page_title="CrewAI Demo — Research | Analyst | Writer", layout="wide")

st.title("🤖 CrewAI Demo — Research → Analyze → Write")
st.caption(
    "Paste a topic below. Three agents (Researcher, Analyst, Writer) will work "
    "on it one after another. You'll see their steps live, then the final "
    "article streams in word by word."
)

# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------
defaults = {
    "running": False,
    "result": None,
    "error": None,
    "logs": [],
    "log_queue": None,
    "worker_thread": None,
    "result_holder": None,
    "stream_done": False,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ----------------------------------------------------------------------
# Sidebar: LLM provider picker
# ----------------------------------------------------------------------
st.sidebar.title("⚙️ Model")

PROVIDER_LABELS = {
    "auto": "Auto (use whichever is available)",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "ollama": "Ollama (free, local)",
}
provider_choice = st.sidebar.selectbox(
    "LLM provider",
    options=list(PROVIDER_LABELS.keys()),
    format_func=lambda p: PROVIDER_LABELS[p],
    index=0,
    disabled=st.session_state.running,
    help="Auto picks the first available option: OpenAI key -> Anthropic key -> local Ollama.",
)

statuses = {s.provider: s for s in check_providers()}
icon = {"openai": "🟢", "anthropic": "🟣", "ollama": "🖥️"}
for name in ("openai", "anthropic", "ollama"):
    s = statuses[name]
    mark = "✅" if s.available else "⚠️"
    st.sidebar.caption(f"{icon[name]} **{PROVIDER_LABELS[name]}** {mark} — {s.detail}")

with st.sidebar.expander("Add / change API keys"):
    openai_key_input = st.text_input(
        "OpenAI API key", value=os.environ.get("OPENAI_API_KEY", ""), type="password"
    )
    if openai_key_input:
        os.environ["OPENAI_API_KEY"] = openai_key_input

    anthropic_key_input = st.text_input(
        "Anthropic API key", value=os.environ.get("ANTHROPIC_API_KEY", ""), type="password"
    )
    if anthropic_key_input:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_key_input

    st.caption(
        "No key handy? Install [Ollama](https://ollama.com), run "
        "`ollama pull llama3.1`, then pick **Ollama (free, local)** above — "
        "no API key or cost required."
    )

active_provider = resolve_provider(provider_choice)
model_override = st.sidebar.text_input(
    "Model override (optional)",
    value="",
    placeholder=DEFAULT_MODELS[active_provider],
    disabled=st.session_state.running,
    help="Leave blank to use the provider's default model.",
)

# ----------------------------------------------------------------------
# Input
# ----------------------------------------------------------------------
topic = st.text_area(
    "Topic",
    height=90,
    placeholder="e.g. The impact of quantum computing on cybersecurity",
    disabled=st.session_state.running,
)

run_clicked = st.button(
    "🚀 Run Crew",
    type="primary",
    disabled=st.session_state.running or not topic.strip(),
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def describe_step(step) -> str:
    """Turn a CrewAI step object into a short, readable log line."""
    agent_role = getattr(getattr(step, "agent", None), "role", None) or "Agent"

    thought = getattr(step, "thought", None) or getattr(step, "text", None)
    if thought:
        return f"**{agent_role}**  {str(thought).strip()[:500]}"

    tool = getattr(step, "tool", None)
    if tool:
        tool_input = getattr(step, "tool_input", "")
        return f"**{agent_role}**  using tool `{tool}` → `{str(tool_input)[:200]}`"

    result = getattr(step, "result", None) or getattr(step, "output", None)
    if result:
        return f"**{agent_role}**  {str(result).strip()[:500]}"

    return f"**{agent_role}** {str(step).strip()[:500]}"


def run_crew_worker(topic_text, prov, model, log_q, result_holder):
    """Runs in a background thread so Streamlit's UI thread stays responsive."""

    def step_callback(step):
        try:
            log_q.put(describe_step(step))
        except Exception as exc:  # keep the crew running even if logging fails
            log_q.put(f"[log formatting error: {exc}]")

    try:
        crew, provider_name, model_name = build_crew(
            topic_text, step_callback=step_callback, provider=prov, model=model or None
        )
        result_holder["provider"] = provider_name
        result_holder["model"] = model_name
        log_q.put(f"__PROVIDER__:{provider_name}:{model_name}")

        final_output = crew.kickoff()
        result_holder["output"] = str(final_output)

        if crew.usage_metrics:
            result_holder["usage"] = crew.usage_metrics.model_dump()
    except Exception as exc:
        result_holder["error"] = str(exc)
    finally:
        log_q.put("__DONE__")


def word_stream(text: str, delay: float = 0.03):
    """Yield the text word by word for st.write_stream()."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


# ----------------------------------------------------------------------
# Kick off a run
# ----------------------------------------------------------------------
if run_clicked and topic.strip():
    st.session_state.running = True
    st.session_state.result = None
    st.session_state.error = None
    st.session_state.logs = []
    st.session_state.log_queue = queue.Queue()
    st.session_state.result_holder = {}
    st.session_state.stream_done = False

    thread = threading.Thread(
        target=run_crew_worker,
        args=(
            topic.strip(),
            provider_choice,
            model_override.strip(),
            st.session_state.log_queue,
            st.session_state.result_holder,
        ),
        daemon=True,
    )
    st.session_state.worker_thread = thread
    thread.start()
    st.rerun()

# ----------------------------------------------------------------------
# While running: drain the queue and show live agent activity
# ----------------------------------------------------------------------
if st.session_state.running:
    st.subheader("🔍 Agent activity (live)")
    status_placeholder = st.status("Crew is working...", expanded=True)
    log_box = status_placeholder.container()

    for line in st.session_state.logs:
        if line.startswith("__PROVIDER__:"):
            _, prov, mod = line.split(":", 2)
            log_box.caption(f"Running on **{prov}** / `{mod}`")
        else:
            log_box.markdown(line)

    q = st.session_state.log_queue
    thread = st.session_state.worker_thread
    finished = False

    while True:
        try:
            item = q.get(timeout=0.2)
        except queue.Empty:
            if not thread.is_alive():
                finished = True
                break
            continue

        if item == "__DONE__":
            finished = True
            break

        st.session_state.logs.append(item)
        if item.startswith("__PROVIDER__:"):
            _, prov, mod = item.split(":", 2)
            log_box.caption(f"Running on **{prov}** / `{mod}`")
        else:
            log_box.markdown(item)

    if finished:
        rh = st.session_state.result_holder
        st.session_state.running = False
        if "error" in rh:
            st.session_state.error = rh["error"]
            status_placeholder.update(label="Crew failed ❌", state="error", expanded=True)
        else:
            st.session_state.result = rh.get("output", "")
            st.session_state.run_meta = {
                "provider": rh.get("provider"),
                "model": rh.get("model"),
                "usage": rh.get("usage"),
            }
            status_placeholder.update(label="Crew finished ✅", state="complete", expanded=False)
        st.rerun()

# ----------------------------------------------------------------------
# Show any error
# ----------------------------------------------------------------------
if st.session_state.error:
    st.error(f"Crew run failed: {st.session_state.error}")
    if "OPENAI_API_KEY" in st.session_state.error or "ANTHROPIC_API_KEY" in st.session_state.error:
        st.info("Add a key in the sidebar, or switch to **Ollama (free, local)** if you have it installed.")
    elif "Ollama" in st.session_state.error:
        st.info("Ollama isn't reachable — install it from https://ollama.com, run `ollama serve`, "
                "then `ollama pull llama3.1`, or switch to an OpenAI/Anthropic key in the sidebar.")

# ----------------------------------------------------------------------
# Final article, streamed word by word
# ----------------------------------------------------------------------
if st.session_state.result and not st.session_state.running:
    meta = st.session_state.get("run_meta", {})
    if meta.get("provider"):
        st.caption(f"Generated with **{meta['provider']}** / `{meta['model']}`")

    st.subheader("📝 Final Article")
    if not st.session_state.get("stream_done"):
        st.write_stream(word_stream(st.session_state.result))
        st.session_state.stream_done = True
    else:
        st.markdown(st.session_state.result)

    usage = meta.get("usage")
    if usage:
        with st.expander("📊 Token usage for this run"):
            cols = st.columns(4)
            cols[0].metric("Prompt tokens", usage.get("prompt_tokens", 0))
            cols[1].metric("Completion tokens", usage.get("completion_tokens", 0))
            cols[2].metric("Total tokens", usage.get("total_tokens", 0))
            cols[3].metric("LLM calls", usage.get("successful_requests", 0))

    st.download_button(
        "⬇️ Download article (.md)",
        data=st.session_state.result,
        file_name="article.md",
        mime="text/markdown",
    )
