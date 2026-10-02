"""
crew_setup.py
--------------
Defines the 3-agent CrewAI pipeline used in the demo:

    Researcher  -> gathers raw facts on the topic
    Analyst     -> turns raw facts into structured insights
    Writer      -> turns insights into a polished article

`build_crew(topic, step_callback)` wires everything together and returns
a ready-to-run Crew. `step_callback` is called by CrewAI after every
agent "step" (thought / tool call / tool result), which is how the
Streamlit app displays live progress.

The LLM itself (OpenAI / Anthropic / local Ollama) is resolved by
`llm_config.get_llm()`, so this file doesn't need to know or care which
provider is actually running underneath.
"""

from crewai import Agent, Task, Crew, Process

from llm_config import get_llm


def build_crew(topic: str, step_callback=None, provider: str | None = None, model: str | None = None):
    """
    Build the crew for `topic`.

    Returns (crew, provider_name, model_name) — the last two are handed back
    so the UI can show exactly what backed this run.
    """
    llm, provider_name, model_name = get_llm(provider=provider, model=model)

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------
    researcher = Agent(
        role="Senior Research Analyst",
        goal=f"Uncover accurate, up-to-date information about '{topic}'",
        backstory=(
            "You work at a leading research think tank. You're excellent at "
            "digging up facts, statistics, key players, and recent developments "
            "on any subject, and you always double-check what you find."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        step_callback=step_callback,
    )

    analyst = Agent(
        role="Data & Insights Analyst",
        goal=f"Analyze the research on '{topic}' and extract the key insights",
        backstory=(
            "You are a meticulous analyst who takes raw research notes and turns "
            "them into structured insights, spotting trends, risks, and "
            "opportunities that a casual reader would miss."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        step_callback=step_callback,
    )

    writer = Agent(
        role="Content Writer",
        goal=f"Write an engaging, well-structured article about '{topic}'",
        backstory=(
            "You are a skilled content writer known for turning dense analysis "
            "into a clear, engaging article that a general audience will enjoy "
            "reading."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        step_callback=step_callback,
    )

    # ------------------------------------------------------------------
    # Tasks (sequential: research -> analysis -> writing)
    # ------------------------------------------------------------------
    research_task = Task(
        description=(
            f"Research the topic: '{topic}'.\n"
            "Gather the latest facts, statistics, key players, and developments. "
            "Prioritize accuracy and recency. Organize your findings as bullet points."
        ),
        expected_output="A detailed bullet-point summary of research findings (8-12 bullets).",
        agent=researcher,
    )

    analysis_task = Task(
        description=(
            f"Analyze the research findings on '{topic}' produced by the researcher.\n"
            "Identify 3-5 key insights, trends, or implications. Call out anything "
            "surprising, risky, or strategically important."
        ),
        expected_output=(
            "A structured analysis in Markdown with clear headings: "
            "'Key Insights', 'Trends', and 'Implications'."
        ),
        agent=analyst,
        context=[research_task],
    )

    writing_task = Task(
        description=(
            f"Using the research and analysis above, write a polished ~500-600 word "
            f"article about '{topic}'.\n"
            "Include an engaging title, a short intro, 2-3 sub-sections with headers, "
            "and a concise conclusion. Write in Markdown."
        ),
        expected_output="A complete, publish-ready article in Markdown format.",
        agent=writer,
        context=[research_task, analysis_task],
    )

    # ------------------------------------------------------------------
    # Crew
    # ------------------------------------------------------------------
    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew, provider_name, model_name
