"""SQLite stores validated state and redacted failure categories, never config."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from research.models import WorkflowState


class RunStore:
    def __init__(self, path="data/research.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, topic TEXT NOT NULL, status TEXT NOT NULL,
                started_at TEXT NOT NULL, finished_at TEXT, provider TEXT NOT NULL,
                model TEXT NOT NULL, source_count INTEGER NOT NULL,
                evidence_count INTEGER NOT NULL, supported_claims INTEGER NOT NULL,
                unverified_claims INTEGER NOT NULL, prompt_tokens INTEGER,
                completion_tokens INTEGER, latency REAL NOT NULL,
                failure_reason TEXT, report_content TEXT, state_json TEXT NOT NULL)""")

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def save(self, state: WorkflowState):
        m = state.metrics
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    state.id,
                    state.request.topic if state.request else "",
                    state.status,
                    state.started_at.isoformat(),
                    state.finished_at.isoformat() if state.finished_at else None,
                    state.provider,
                    state.model,
                    m.source_count,
                    m.evidence_count,
                    m.supported_claims,
                    m.unverified_claims,
                    m.prompt_tokens,
                    m.completion_tokens,
                    m.latency_seconds,
                    state.failure_reason,
                    state.report.markdown
                    if state.report and state.report.citation_integrity
                    else None,
                    state.model_dump_json(),
                ),
            )

    def load(self, run_id):
        with self.connect() as conn:
            row = conn.execute("SELECT state_json FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return WorkflowState.model_validate_json(row[0]) if row else None

    def recent(self, limit=20):
        with self.connect() as conn:
            return conn.execute(
                "SELECT run_id, topic, status, provider, model, source_count, latency FROM runs ORDER BY started_at DESC LIMIT ?",
                (min(max(limit, 1), 100),),
            ).fetchall()
