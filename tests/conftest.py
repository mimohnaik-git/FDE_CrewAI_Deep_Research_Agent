"""No network and no real keys in the default test suite."""

import inspect
import socket

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "SERPER_API_KEY",
        "LLM_MODEL",
        "LLM_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CREWAI_TELEMETRY_ENABLED", "false")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

    original_connect = socket.socket.connect

    def blocked(connection, address):
        # Windows asyncio builds an internal wake-up pipe with socketpair.
        # Permit only that standard-library call, never application traffic.
        if any(frame.function == "_fallback_socketpair" for frame in inspect.stack()):
            return original_connect(connection, address)
        raise AssertionError("Default tests may not access the network")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
