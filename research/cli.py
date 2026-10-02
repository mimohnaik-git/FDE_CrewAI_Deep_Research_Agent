"""CLI for the same offline workflow used by Streamlit and evaluation."""

import argparse

from research.models import ResearchRequest
from research.persistence import RunStore
from research.reasoning import OfflineReasoner
from research.search import FixtureSearch
from research.workflow import ResearchFlow


def offline_run(case="corroboration", db="data/research.sqlite3", event=None):
    search = FixtureSearch(case=case)
    request = ResearchRequest(topic=search.case["topic"])
    return ResearchFlow(
        request, search, OfflineReasoner(search.case), RunStore(db), event=event
    ).run()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="corroboration")
    parser.add_argument("--db", default="data/research.sqlite3")
    args = parser.parse_args()
    state = offline_run(args.case, args.db, print)
    if state.status != "completed":
        raise SystemExit(state.failure_reason)
    print(state.report.markdown)
    print(state.metrics.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
