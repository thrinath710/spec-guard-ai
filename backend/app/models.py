from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def new_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class DocumentStatus(StrEnum):
    uploaded = "uploaded"
    processing = "processing"
    processed = "processed"
    failed = "failed"


class AnalysisStatus(StrEnum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Severity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ApiError(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: ApiError | None = None


class DocumentRecord(BaseModel):
    id: str = Field(default_factory=new_uuid)
    filename: str
    file_type: str
    file_size: int
    storage_path: str
    status: DocumentStatus = DocumentStatus.uploaded
    extracted_text: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Requirement(BaseModel):
    id: str
    text: str
    category: str = "Other"
    source_text: str | None = None
    source_location: str | None = None


class RequirementIssue(BaseModel):
    severity: Severity
    type: str
    title: str
    description: str
    evidence: str
    recommendation: str


class QualityAnalysis(BaseModel):
    requirement_id: str
    clarity_score: int
    completeness_score: int
    testability_score: int
    issues: list[RequirementIssue] = Field(default_factory=list)


class SecurityFinding(BaseModel):
    requirement_id: str
    severity: Severity
    category: str
    description: str
    evidence: str
    recommendation: str


class RequirementConflict(BaseModel):
    requirement_id: str
    related_requirement_id: str
    reason: str
    evidence: str
    severity: Severity = Severity.medium


class EdgeCase(BaseModel):
    requirement_id: str
    title: str
    scenario: str
    expected_behavior: str
    priority: str = "medium"


class TestCase(BaseModel):
    id: str
    requirement_id: str
    title: str
    preconditions: list[str]
    steps: list[str]
    expected_result: str
    priority: str
    category: str


class ImprovedRequirement(BaseModel):
    requirement_id: str
    original_text: str
    improved_text: str
    rationale: str
    remaining_questions: list[str] = Field(default_factory=list)


class AnalysisScore(BaseModel):
    quality_score: int
    security_score: int
    testability_score: int
    overall_score: int
    risk_level: str


class AnalysisResult(BaseModel):
    requirements: list[Requirement] = Field(default_factory=list)
    quality: list[QualityAnalysis] = Field(default_factory=list)
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    conflicts: list[RequirementConflict] = Field(default_factory=list)
    edge_cases: list[EdgeCase] = Field(default_factory=list)
    test_cases: list[TestCase] = Field(default_factory=list)
    improved_requirements: list[ImprovedRequirement] = Field(default_factory=list)
    score: AnalysisScore | None = None
    # Set when one or more AI stages fell back to the deterministic heuristics (for example
    # because the LLM provider rate-limited the request). Without this a degraded run is
    # indistinguishable from a real AI analysis in the response.
    degraded: bool = False
    degraded_reason: str | None = None


class StageStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class LogLevel(StrEnum):
    info = "info"
    success = "success"
    warning = "warning"
    error = "error"


class StageInfo(BaseModel):
    """One node of the analysis pipeline, as rendered in the live progress view."""

    key: str
    label: str
    description: str = ""
    status: StageStatus = StageStatus.pending
    progress: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class LogEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    level: LogLevel = LogLevel.info
    stage: str | None = None
    message: str


class AnalysisRecord(BaseModel):
    id: str = Field(default_factory=new_uuid)
    document_id: str
    status: AnalysisStatus = AnalysisStatus.queued
    progress: int = 0
    current_stage: str = "queued"
    result: AnalysisResult | None = None
    error_message: str | None = None
    stages: list[StageInfo] = Field(default_factory=list)
    events: list[LogEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class StartAnalysisRequest(BaseModel):
    """Replaces the previously untyped dict payload so the field is validated and documented."""

    document_id: str = Field(min_length=1)
