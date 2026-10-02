"""Provenance and linkage checks independent of model output."""

import hashlib
import re
from urllib.parse import urlsplit

from research.models import EvidenceRecord, SourceRecord, VerificationStatus, VerifiedClaim
from research.search import normalize_url


def normalize_sources(results, limit):
    sources, urls, fingerprints = [], set(), set()
    duplicates = 0
    for result in results:
        url = normalize_url(str(result.url))
        excerpt = re.sub(r"\s+", " ", result.excerpt).strip()
        fingerprint = hashlib.sha256(excerpt.encode()).hexdigest()
        if url in urls or fingerprint in fingerprints:
            duplicates += 1
            continue
        if len(sources) >= limit:
            continue
        source = SourceRecord(
            **{**result.model_dump(), "url": url, "excerpt": excerpt},
            source_id=f"S{len(sources) + 1}",
            domain=urlsplit(url).hostname,
            fingerprint=fingerprint,
        )
        sources.append(source)
        urls.add(url)
        fingerprints.add(fingerprint)
    return sources, duplicates


def validate_evidence(evidence: list[EvidenceRecord], sources: list[SourceRecord]):
    lookup = {s.source_id: s for s in sources}
    ids = set()
    for item in evidence:
        if item.evidence_id in ids or item.source_id not in lookup:
            raise ValueError("Invalid or duplicate evidence linkage")
        if item.quote not in lookup[item.source_id].excerpt:
            raise ValueError("Evidence quote must be an exact substring of retrieved text")
        ids.add(item.evidence_id)


def verify_claims(claims, evidence, sources):
    lookup = {e.evidence_id: e for e in evidence}
    source_lookup = {s.source_id: s for s in sources}
    ids, verified = set(), []
    for claim in claims:
        if claim.claim_id in ids:
            raise ValueError("Duplicate claim ID")
        ids.add(claim.claim_id)
        links = claim.evidence_ids + claim.contradicting_evidence_ids
        if any(e not in lookup for e in links):
            raise ValueError("Claim references nonexistent evidence")
        supporting_sources = {lookup[e].source_id for e in claim.evidence_ids}
        domains = {source_lookup[s].domain.removeprefix("www.") for s in supporting_sources}
        if claim.contradicting_evidence_ids:
            status, reason = (
                VerificationStatus.CONFLICTING,
                "Retrieved evidence contains a contradiction.",
            )
        elif not claim.evidence_ids:
            status, reason = VerificationStatus.INSUFFICIENT, "No retrieved support."
        elif claim.important and len(domains) < 2:
            status, reason = (
                VerificationStatus.PARTIAL,
                "Only one source domain supports this important claim.",
            )
        else:
            status, reason = (
                VerificationStatus.SUPPORTED,
                "Linked evidence meets the source corroboration threshold.",
            )
        source_ids = sorted({lookup[e].source_id for e in links}, key=lambda s: int(s[1:]))
        verified.append(
            VerifiedClaim(
                **claim.model_dump(), status=status, source_ids=source_ids, rationale=reason
            )
        )
    return verified
