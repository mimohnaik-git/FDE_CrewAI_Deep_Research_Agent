---
name: ai-evaluation
description: Evaluate this research workflow with its locked offline fixture suite while distinguishing deterministic contract checks from live AI quality.
---

# AI evaluation

1. Read `docs/EVALUATION.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md` before changing evaluation logic or expectations.
2. Use the frozen scenarios in `research/fixtures.json` and `uv run --locked python -m research.evaluation --output data/evaluation.json` for offline evaluation.
3. Preserve expected outputs unless the task explicitly changes the baseline; show observed values separately from expectations.
4. Use `uv run --locked pytest -q` for regression coverage. Keep routine checks offline and credential-free; do not call paid model or search services without explicit scope.

## Interpretation

Report case counts, pass/fail output, and any metric changes from actual command output. Fixture results do not estimate live factual accuracy, semantic entailment, or resistance to all prompt injection.
