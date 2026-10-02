"""Frozen fixture evaluation; measures observed behavior and fails on regressions."""

import argparse
import json
import re
import tempfile
from pathlib import Path

from research.citations import citation_errors
from research.cli import offline_run
from research.models import WorkflowState


def evaluate(db):
    dataset = json.loads(Path(__file__).with_name("fixtures.json").read_text(encoding="utf-8"))
    rows = []
    for case, expected in dataset.items():
        state = offline_run(case, db)
        completed = state.status == "completed"
        errors = (
            citation_errors(state.report, state.sources, state.evidence, state.claims)
            if completed
            else []
        )
        claim_count = len(state.claims)
        source_count = len(state.sources)
        cited = (
            set(re.findall(r"\[(S[1-9]\d*)\]", state.report.markdown.split("## Sources")[0]))
            if completed
            else set()
        )
        linked = sum(bool(c.evidence_ids or c.contradicting_evidence_ids) for c in state.claims)
        statuses = [c.status.value for c in state.claims]
        expected_status = "failed" if expected.get("failure") else "completed"
        row = {
            "case": case,
            "schema_valid": WorkflowState.model_validate_json(state.model_dump_json()) == state,
            "workflow_status": state.status,
            "expected_status": expected_status,
            "citation_integrity": state.report.citation_integrity if completed else None,
            "invalid_citation_count": len(errors),
            "source_count": source_count,
            "source_coverage": len(cited & {s.source_id for s in state.sources}) / source_count
            if source_count
            else None,
            "evidence_linkage": linked / claim_count if claim_count else None,
            "supported_claim_rate": state.metrics.supported_claims / claim_count
            if claim_count
            else None,
            "unsupported_claim_rate": state.metrics.unverified_claims / claim_count
            if claim_count
            else None,
            "duplicate_sources_removed": state.metrics.duplicate_sources,
            "claim_statuses": statuses,
            "search_calls": state.metrics.search_calls,
            "llm_calls": state.metrics.llm_calls,
        }
        row["passed"] = (
            state.status == expected_status
            and statuses == expected["expected_statuses"]
            and source_count == expected["expected_sources"]
            and state.metrics.duplicate_sources == expected["expected_duplicates"]
            and row["schema_valid"]
            and not errors
            and (not completed or row["citation_integrity"])
        )
        rows.append(row)
    result = {"cases": rows, "passed": sum(r["passed"] for r in rows), "total": len(rows)}
    result["all_passed"] = result["passed"] == result["total"]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        result = evaluate(Path(directory) / "evaluation.sqlite3")
    payload = json.dumps(result, indent=2)
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if not result["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
