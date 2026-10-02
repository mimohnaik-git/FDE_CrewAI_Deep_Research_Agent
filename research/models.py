"""Strict contracts for every workflow boundary; credentials never enter state."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

Text = Annotated[str, Field(min_length=1, max_length=20000)]
SourceID = Annotated[str, Field(pattern=r"^S[1-9]\d*$")]
EvidenceID = Annotated[str, Field(pattern=r"^E[1-9]\d*$")]
ClaimID = Annotated[str, Field(pattern=r"^C[1-9]\d*$")]


def now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class ResearchRequest(StrictModel):
    topic: Annotated[str, Field(min_length=3, max_length=1000)]
    mode: Literal["offline", "web"] = "offline"
    max_queries: int = Field(default=3, ge=1, le=5)
    max_sources: int = Field(default=8, ge=1, le=20)


class ResearchQuestion(StrictModel):
    question_id: Annotated[str, Field(pattern=r"^Q[1-9]\d*$")]
    question: Text


class SearchQuery(StrictModel):
    question_id: Annotated[str, Field(pattern=r"^Q[1-9]\d*$")]
    text: Annotated[str, Field(min_length=3, max_length=1000)]


class ResearchPlan(StrictModel):
    questions: list[ResearchQuestion] = Field(min_length=1, max_length=5)
    queries: list[SearchQuery] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def linked_queries(self):
        ids = [q.question_id for q in self.questions]
        if len(ids) != len(set(ids)) or any(q.question_id not in ids for q in self.queries):
            raise ValueError("Question IDs must be unique and queries must reference them")
        return self


class SearchResult(StrictModel):
    url: HttpUrl
    title: Annotated[str, Field(min_length=1, max_length=500)]
    excerpt: Annotated[str, Field(min_length=1, max_length=20000)]
    query: Annotated[str, Field(min_length=3, max_length=1000)]
    retrieved_at: datetime = Field(default_factory=now)

    @field_validator("retrieved_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("Retrieval timestamps require a timezone")
        return value


class SourceRecord(SearchResult):
    source_id: SourceID
    domain: Annotated[str, Field(min_length=1, max_length=253)]
    fingerprint: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]

    @model_validator(mode="after")
    def domain_matches(self):
        if self.domain != self.url.host:
            raise ValueError("Domain does not match source URL")
        return self


class EvidenceRecord(StrictModel):
    evidence_id: EvidenceID
    source_id: SourceID
    quote: Text


class ClaimRecord(StrictModel):
    claim_id: ClaimID
    text: Text
    evidence_ids: list[EvidenceID] = Field(default_factory=list, max_length=40)
    contradicting_evidence_ids: list[EvidenceID] = Field(default_factory=list, max_length=40)
    important: bool = True

    @model_validator(mode="after")
    def unique_links(self):
        links = self.evidence_ids + self.contradicting_evidence_ids
        if len(links) != len(set(links)):
            raise ValueError("Evidence links must be unique and cannot support and contradict")
        return self


class VerificationStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partially supported"
    CONFLICTING = "conflicting"
    INSUFFICIENT = "insufficient evidence"


class VerifiedClaim(ClaimRecord):
    status: VerificationStatus
    source_ids: list[SourceID] = Field(default_factory=list)
    rationale: Text

    @model_validator(mode="after")
    def verified_has_evidence(self):
        if self.status == VerificationStatus.SUPPORTED and (
            not self.evidence_ids or not self.source_ids
        ):
            raise ValueError("Supported claims require evidence and sources")
        return self


class CitationRecord(StrictModel):
    source_id: SourceID
    url: HttpUrl
    title: Annotated[str, Field(min_length=1, max_length=500)]


class ReportSection(StrictModel):
    text: Text
    claim_ids: list[ClaimID] = Field(min_length=1, max_length=40)


class ReportDraft(StrictModel):
    title: Annotated[str, Field(min_length=1, max_length=500)]
    executive_summary: ReportSection
    major_findings: list[ReportSection] = Field(min_length=1, max_length=40)
    analysis: ReportSection
    limitations: Text
    conclusion: ReportSection


class ResearchReport(ReportDraft):
    citations: list[CitationRecord] = Field(min_length=1)
    markdown: Text
    citation_integrity: bool = False


class EvidenceBatch(StrictModel):
    evidence: list[EvidenceRecord] = Field(min_length=1, max_length=40)


class ClaimBatch(StrictModel):
    claims: list[ClaimRecord] = Field(min_length=1, max_length=40)


class RunMetrics(StrictModel):
    search_calls: int = Field(default=0, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    source_count: int = Field(default=0, ge=0)
    evidence_count: int = Field(default=0, ge=0)
    supported_claims: int = Field(default=0, ge=0)
    unverified_claims: int = Field(default=0, ge=0)
    duplicate_sources: int = Field(default=0, ge=0)
    invalid_citations: int = Field(default=0, ge=0)
    latency_seconds: float = Field(default=0, ge=0)


class WorkflowState(StrictModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    request: ResearchRequest | None = None
    plan: ResearchPlan | None = None
    sources: list[SourceRecord] = Field(default_factory=list)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    claims: list[VerifiedClaim] = Field(default_factory=list)
    report: ResearchReport | None = None
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    provider: str = Field(default="offline", min_length=1, max_length=50)
    model: str = Field(default="fixture-v1", min_length=1, max_length=200)
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: datetime = Field(default_factory=now)
    finished_at: datetime | None = None
    failure_reason: str | None = Field(default=None, max_length=500)
