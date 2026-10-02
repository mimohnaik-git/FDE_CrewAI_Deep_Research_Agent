"""Research package runtime defaults: local storage, no tracing/telemetry."""

import os
from pathlib import Path

# CrewAI imports initialize storage. Keep it in the application's local data directory.
# These are fixed runtime policy settings, never session credentials.
os.environ["CREWAI_STORAGE_DIR"] = str(Path("data/crewai").resolve())
os.environ["CREWAI_TELEMETRY_ENABLED"] = "false"
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"
