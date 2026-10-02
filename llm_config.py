"""
llm_config.py
-------------
Picks which LLM provider/model the crew runs on, so this demo works whether
the person in front of it has a paid OpenAI key, a paid Anthropic key, or
nothing but a free local Ollama install.

Resolution order (first one that's usable wins), unless LLM_PROVIDER is set
explicitly in the environment:

    1. OPENAI_API_KEY present      -> OpenAI (gpt-4o-mini by default)
    2. ANTHROPIC_API_KEY present   -> Anthropic (claude-haiku-4-5 by default)
    3. A local Ollama server is reachable -> Ollama (llama3.1 by default, $0 cost)

Override the model for whichever provider is chosen with LLM_MODEL.
Force a specific provider with LLM_PROVIDER=openai|anthropic|ollama.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from crewai import LLM

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "anthropic/claude-haiku-4-5-20251001",
    "ollama": "ollama/llama3.1",
}
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@dataclass
class ProviderStatus:
    provider: str
    available: bool
    detail: str


def _ollama_reachable(timeout: float = 1.5) -> bool:
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def check_providers() -> list[ProviderStatus]:
    """Status of every provider, for display in the sidebar."""
    return [
        ProviderStatus(
            "openai",
            bool(os.getenv("OPENAI_API_KEY")),
            "OPENAI_API_KEY set" if os.getenv("OPENAI_API_KEY") else "OPENAI_API_KEY not set",
        ),
        ProviderStatus(
            "anthropic",
            bool(os.getenv("ANTHROPIC_API_KEY")),
            "ANTHROPIC_API_KEY set" if os.getenv("ANTHROPIC_API_KEY") else "ANTHROPIC_API_KEY not set",
        ),
        ProviderStatus(
            "ollama",
            _ollama_reachable(),
            f"reachable at {OLLAMA_BASE_URL}" if _ollama_reachable() else f"not reachable at {OLLAMA_BASE_URL}",
        ),
    ]


def resolve_provider(preferred: str | None = None) -> str:
    """Work out which provider to actually use."""
    preferred = preferred or os.getenv("LLM_PROVIDER", "auto")
    if preferred != "auto":
        return preferred

    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if _ollama_reachable():
        return "ollama"
    return "openai"  # nothing usable found; fall through so the error message is clear


def get_llm(provider: str | None = None, model: str | None = None) -> tuple[LLM, str, str]:
    """
    Build a crewai LLM for the resolved provider.

    Returns (llm, provider_name, model_name) so the caller can show the user
    exactly what's about to run.
    """
    provider = resolve_provider(provider)
    model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS[provider]

    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or switch providers.")
        llm = LLM(model=model, api_key=os.environ["OPENAI_API_KEY"])
    elif provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to .env or switch providers.")
        llm = LLM(model=model, api_key=os.environ["ANTHROPIC_API_KEY"])
    elif provider == "ollama":
        if not _ollama_reachable():
            raise RuntimeError(
                f"No Ollama server found at {OLLAMA_BASE_URL}. Install Ollama, run "
                f"`ollama pull {model.split('/')[-1]}`, and make sure `ollama serve` is running "
                "(or set OLLAMA_BASE_URL if it's hosted elsewhere)."
            )
        llm = LLM(model=model, base_url=OLLAMA_BASE_URL)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use openai, anthropic, ollama, or auto.")

    return llm, provider, model
