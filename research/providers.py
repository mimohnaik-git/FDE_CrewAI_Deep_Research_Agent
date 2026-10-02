"""Session-scoped provider configuration; no mutation of process credentials."""

import os
from dataclasses import dataclass
from typing import Literal, Mapping

import httpx
from pydantic import Field, SecretStr

from research.models import StrictModel
from research.search import local_ollama_url

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "anthropic/claude-haiku-4-5-20251001",
    "ollama": "ollama/llama3.1",
}


class ProviderConfig(StrictModel):
    provider: Literal["auto", "openai", "anthropic", "ollama"] = "auto"
    model: str | None = Field(default=None, min_length=1, max_length=200)
    openai_key: SecretStr = Field(default_factory=lambda: SecretStr(""), exclude=True)
    anthropic_key: SecretStr = Field(default_factory=lambda: SecretStr(""), exclude=True)
    ollama_url: str = "http://localhost:11434"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None):
        env = os.environ if environ is None else environ
        return cls(
            provider=env.get("LLM_PROVIDER", "auto"),
            model=env.get("LLM_MODEL") or None,
            openai_key=env.get("OPENAI_API_KEY", ""),
            anthropic_key=env.get("ANTHROPIC_API_KEY", ""),
            ollama_url=env.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        )


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    status: str
    detail: str


def ollama_reachable(url, client=None):
    endpoint = local_ollama_url(url)
    try:
        if client:
            return client.get(f"{endpoint}/api/tags").status_code == 200
        with httpx.Client(timeout=1.5, follow_redirects=False) as connection:
            return connection.get(f"{endpoint}/api/tags").status_code == 200
    except httpx.HTTPError:
        return False


def check_providers(config=None, probe_local=False):
    config = config or ProviderConfig.from_env()
    statuses = [
        ProviderStatus(
            p,
            "configured" if key.get_secret_value() else "unavailable",
            "Key configured; authentication not checked"
            if key.get_secret_value()
            else "No key configured",
        )
        for p, key in (("openai", config.openai_key), ("anthropic", config.anthropic_key))
    ]
    reachable = probe_local and ollama_reachable(config.ollama_url)
    statuses.append(
        ProviderStatus(
            "ollama",
            "locally reachable" if reachable else ("unavailable" if probe_local else "configured"),
            "Local endpoint reachable"
            if reachable
            else (
                "Local endpoint unavailable"
                if probe_local
                else "Endpoint configured; reachability not checked"
            ),
        )
    )
    return statuses


def resolve_provider(config: ProviderConfig):
    if config.provider != "auto":
        provider = config.provider
    elif config.openai_key.get_secret_value():
        provider = "openai"
    elif config.anthropic_key.get_secret_value():
        provider = "anthropic"
    elif ollama_reachable(config.ollama_url):
        provider = "ollama"
    else:
        raise RuntimeError("No model provider available")
    if (
        provider in ("openai", "anthropic")
        and not getattr(config, f"{provider}_key").get_secret_value()
    ):
        raise RuntimeError("Selected model provider has no configured key")
    if provider == "ollama" and not ollama_reachable(config.ollama_url):
        raise RuntimeError("Ollama is unavailable")
    return provider


def get_llm(config: ProviderConfig):
    from crewai import LLM

    provider = resolve_provider(config)
    model = config.model or DEFAULT_MODELS[provider]
    kwargs = {"model": model, "temperature": 0, "timeout": 60, "max_tokens": 4000}
    if provider == "ollama":
        kwargs["base_url"] = local_ollama_url(config.ollama_url)
    else:
        kwargs["api_key"] = getattr(config, f"{provider}_key").get_secret_value()
    return LLM(**kwargs), provider, model
