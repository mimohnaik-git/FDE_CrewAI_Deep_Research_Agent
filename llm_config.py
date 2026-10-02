"""Compatibility import for the prototype's provider module."""

from research.providers import (
    DEFAULT_MODELS,
    ProviderConfig,
    check_providers,
    get_llm,
    resolve_provider,
)

__all__ = ["DEFAULT_MODELS", "ProviderConfig", "check_providers", "get_llm", "resolve_provider"]
