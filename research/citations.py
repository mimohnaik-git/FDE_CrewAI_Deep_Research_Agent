"""Deterministic report rendering and citation/linkage integrity."""

import re

from research.models import CitationRecord, ResearchReport, VerificationStatus
from research.provenance import validate_evidence


def sections(report):
    return [report.executive_summary, *report.major_findings, report.analysis, report.conclusion]


def render_report(draft, claims, sources, mode):
    lookup = {c.claim_id: c for c in claims}

    def paragraph(section):
        if any(c not in lookup for c in section.claim_ids):
            raise ValueError("Writer referenced a nonexistent claim")
        details = []
        for cid in section.claim_ids:
            claim = lookup[cid]
            refs = " ".join(f"[{s}]" for s in claim.source_ids)
            details.append(f"- {claim.text} {refs} — **{claim.status.value}**")
        return section.text + "\n\n" + "\n".join(details)

    citations = [CitationRecord(source_id=s.source_id, url=s.url, title=s.title) for s in sources]
    markdown = f"# {draft.title}\n\nMode: {mode} ({'frozen fixture demo; no web retrieval' if mode == 'offline' else 'retrieved search excerpts'})\n\n"
    markdown += "## Executive summary\n\n" + paragraph(draft.executive_summary)
    markdown += "\n\n## Major findings\n\n" + "\n\n".join(
        paragraph(s) for s in draft.major_findings
    )
    markdown += "\n\n## Analysis\n\n" + paragraph(draft.analysis)
    markdown += "\n\n## Limitations / uncertainty\n\n" + draft.limitations
    markdown += "\n\n## Conclusion\n\n" + paragraph(draft.conclusion)
    markdown += "\n\n## Sources\n\n" + "\n".join(
        f"- [{s.source_id}] {s.title}: {s.url}" for s in sources
    )
    return ResearchReport(**draft.model_dump(), citations=citations, markdown=markdown)


def citation_errors(report, sources, evidence, claims):
    errors = []
    source_ids = [s.source_id for s in sources]
    if len(source_ids) != len(set(source_ids)):
        errors.append("duplicate source IDs")
    lookup = {s.source_id: s for s in sources}
    for source in sources:
        if not source.url:
            errors.append(f"missing URL: {source.source_id}")
    # Match citation-like tokens, including missing brackets and malformed IDs.
    tokens = re.findall(r"\[[sS][^\]\n]*\]?", report.markdown)
    tokens.extend(re.findall(r"(?<![\w\[])[sS]\d+\]", report.markdown))
    for token in tokens:
        if not re.fullmatch(r"\[S[1-9]\d*\]", token):
            errors.append(f"malformed citation: {token}")
        elif token[1:-1] not in lookup:
            errors.append(f"nonexistent citation: {token}")
    citation_ids = [c.source_id for c in report.citations]
    if len(citation_ids) != len(set(citation_ids)):
        errors.append("duplicate citation records")
    if set(citation_ids) != set(source_ids):
        errors.append("source list does not match provenance")
    for citation in report.citations:
        source = lookup.get(citation.source_id)
        if (
            source is None
            or not citation.url
            or citation.url != source.url
            or citation.title != source.title
        ):
            errors.append(f"citation metadata mismatch: {citation.source_id}")
    try:
        validate_evidence(evidence, sources)
    except ValueError:
        errors.append("invalid evidence linkage")
    ev = {e.evidence_id: e for e in evidence}
    claim_lookup = {c.claim_id: c for c in claims}
    if len(claim_lookup) != len(claims):
        errors.append("duplicate claim IDs")
    for claim in claims:
        links = claim.evidence_ids + claim.contradicting_evidence_ids
        linked_sources = {ev[e].source_id for e in links if e in ev}
        if any(e not in ev for e in links) or set(claim.source_ids) != linked_sources:
            errors.append(f"invalid claim linkage: {claim.claim_id}")
        if claim.status == VerificationStatus.SUPPORTED and (
            not claim.evidence_ids or not claim.source_ids
        ):
            errors.append(f"verified claim without evidence: {claim.claim_id}")
    for section in sections(report):
        for cid in section.claim_ids:
            if cid not in claim_lookup:
                errors.append(f"nonexistent report claim: {cid}")
        inline = set(re.findall(r"\[S[1-9]\d*\]", section.text))
        allowed = {
            f"[{s}]"
            for cid in section.claim_ids
            if cid in claim_lookup
            for s in claim_lookup[cid].source_ids
        }
        if inline - allowed:
            errors.append("section citation is not linked to its claims")
    return errors
