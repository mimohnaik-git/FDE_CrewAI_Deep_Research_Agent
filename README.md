# CrewAI Demo — Research → Analyst → Writer (Streamlit UI)

- **Researcher** — gathers raw facts on your topic
- **Analyst** — turns raw facts into structured insights
- **Writer** — turns insights into a polished ~500-word article

The UI shows each agent's steps live as they run, then streams the final
article onto the page **word by word**.

Runs on **OpenAI, Anthropic, or a free local Ollama model** — pick whichever
you have in the sidebar, or leave it on **Auto** and it'll use the first one
that's actually available. This makes the demo work in front of a client
even if they don't want to hand over an API key: switch to Ollama and it
runs at zero cost, fully offline after the model is pulled.

```
crewai_research_writer/
├── app.py            # Streamlit front-end (topic input, live trace, provider picker)
├── crew_setup.py      # Agents, tasks, and the Crew
├── llm_config.py       # Picks OpenAI / Anthropic / Ollama and builds the LLM
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 1. Setup (in VS Code)

Open this folder in VS Code, then in the integrated terminal:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key (only one of these is required — see below)
cp .env.example .env
# then edit .env and paste your OPENAI_API_KEY or ANTHROPIC_API_KEY
```

## 2. Pick a model — pick whichever you have

You do **not** need all three. The app auto-detects what's usable:

| Provider | Cost | Setup |
|---|---|---|
| **OpenAI** | Paid | Set `OPENAI_API_KEY` (in `.env` or the sidebar). Default model: `gpt-4o-mini`. |
| **Anthropic** | Paid | Set `ANTHROPIC_API_KEY` (in `.env` or the sidebar). Default model: `claude-haiku-4-5`. |
| **Ollama** | Free, local | Install [Ollama](https://ollama.com), run `ollama serve`, then `ollama pull llama3.1`. No key needed. |

The sidebar shows a live ✅ / ⚠️ status for all three so you always know
what's about to run — useful when you're troubleshooting live in front of
someone. Set `LLM_PROVIDER=openai|anthropic|ollama` in `.env` to pin one
explicitly instead of auto-detecting, and `LLM_MODEL` to override the
default model for whichever provider is active.

## 3. Run the app

```bash
streamlit run app.py
```

This opens `http://localhost:8501` in your browser.

## 4. Demo it in class / to a client

1. Check the sidebar — confirm which provider is active (or add a key /
   switch to Ollama right there if it isn't).
2. Paste a topic into the text box, e.g.
   `"The impact of quantum computing on cybersecurity"`.
3. Click **🚀 Run Crew**.
4. Point out the **live "Agent activity" panel** — you can literally watch
   the Researcher, then the Analyst, then the Writer think and work,
   one step at a time. The panel also shows which model is running.
5. When the crew finishes, the **final article streams onto the page word
   by word**, like a typewriter — great visual payoff for a demo.
6. Expand **📊 Token usage for this run** to show exactly how many tokens
   and LLM calls the run cost — handy for a cost conversation with a client.
7. Use the **Download article (.md)** button to show the exportable output.

## How the live steps work

CrewAI lets you pass a `step_callback` to each `Agent`. Every time an agent
thinks, calls a tool, or gets a result, that callback fires. In
`crew_setup.py` all three agents share the same callback, which is wired
up in `app.py` to push a short description of each step into a
`queue.Queue`. The Crew itself runs in a background thread (so the UI
doesn't freeze), while the main Streamlit thread drains the queue and
renders each new line live inside a `st.status(...)` panel.

## How the word-by-word streaming works

Once `crew.kickoff()` returns the final article text, `app.py` uses a small
generator (`word_stream`) that `yield`s one word at a time with a short
`time.sleep()` between them, fed straight into Streamlit's built-in
`st.write_stream(...)`.

## How provider switching works

`llm_config.py` resolves a provider (openai / anthropic / ollama) and model,
then builds a single `crewai.LLM(...)` object which is passed as `llm=` to
every `Agent`. Since CrewAI routes all three providers through the same
LiteLLM interface, swapping providers is just a different `model=` string —
`"gpt-4o-mini"`, `"anthropic/claude-haiku-4-5-20251001"`, or
`"ollama/llama3.1"` — no other code changes needed.

## Extending the demo

- **Give the Researcher a real web-search tool**: install `crewai-tools`,
  add `SERPER_API_KEY` to `.env`, and pass
  `tools=[SerperDevTool()]` to the `researcher` Agent in `crew_setup.py`.
- **Swap in a different topic UI**: e.g. add a dropdown of sample topics
  for a faster live demo if you're worried about API latency.
- **Add more providers**: `llm_config.py` is intentionally small — add a
  branch to `get_llm()` and a default model entry in `DEFAULT_MODELS` for
  any other LiteLLM-supported provider (Azure, Bedrock, Gemini, etc.).
