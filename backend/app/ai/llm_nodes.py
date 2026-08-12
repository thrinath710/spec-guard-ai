import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.app.ai.heuristics import _tokens
from backend.app.ai.llm import TieredLLMClient
from backend.app.core.config import get_settings
from backend.app.services import progress as progress_service
from backend.app.ai.prompts import (
    COMBINED_ANALYSIS_SYSTEM_PROMPT,
    COMBINED_IMPROVEMENT_TEST_SYSTEM_PROMPT,
)
from backend.app.models import (
    LogLevel,
    EdgeCase,
    ImprovedRequirement,
    QualityAnalysis,
    Requirement,
    RequirementConflict,
    RequirementIssue,
    SecurityFinding,
    Severity,
    TestCase,
)

logger = logging.getLogger(__name__)

GROUNDING_THRESHOLD = 0.6

# The wire schemas below use short keys and default every field. Two reasons:
#  - short keys + omitted "evidence" fields cut generated tokens, which is the dominant cost;
#  - defaults mean an unconstrained (fast) json-mode response still parses, so a small model
#    dropping a field degrades one value instead of failing validation and silently dropping
#    the whole analysis to heuristics.
# Evidence is reconstructed server-side from the source requirement text, which is both cheaper
# and better grounded than asking the model to echo it back.


def _drop_non_objects(value: Any) -> Any:
    """Discard list entries that are not JSON objects.

    Models sometimes slip commentary into an array as a bare string (observed on
    qwen2.5:7b: a "// no security issues here" pseudo-comment emitted as an element).
    Without this, one stray element invalidates the entire response and the whole
    analysis silently degrades to heuristics; with it, we lose only the junk entry.
    """
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return value


def _correct_conflict_ids(
    item: Any, index_to_id: dict[int, str], text_by_id: dict[str, str]
) -> tuple[str, str]:
    """Repair a conflict whose indexes disagree with the requirements its own reason quotes.

    Smaller models reliably identify *that* two requirements contradict each other but often
    mis-number them (observed on qwen2.5:3b: reason quoted "cancel at any time" vs "cannot be
    cancelled after payment" while pointing at REQ-001/REQ-005). The prompt asks the model to
    quote both requirements in "reason", so we re-derive the pair by word overlap and only
    override when the quoted evidence matches a different pair distinctly better. This fixes
    bookkeeping, not analysis - the contradiction judgement stays the model's.
    """
    stated = (index_to_id[item.r], index_to_id[item.r2])
    reason_tokens = _tokens(item.reason)
    if not reason_tokens:
        return stated

    scored = sorted(
        ((len(_tokens(text) & reason_tokens) / max(len(_tokens(text)), 1), req_id) for req_id, text in text_by_id.items()),
        reverse=True,
    )
    if len(scored) < 2:
        return stated
    (best_score, best_id), (second_score, second_id) = scored[0], scored[1]
    stated_score = min(
        next((s for s, rid in scored if rid == stated[0]), 0.0),
        next((s for s, rid in scored if rid == stated[1]), 0.0),
    )
    # Require the re-derived pair to be a clearly better match before overriding.
    if second_score >= 0.5 and second_score > stated_score + 0.2:
        return (best_id, second_id) if best_id != second_id else stated
    return stated


def _is_grounded(text: str, document_tokens: set[str]) -> bool:
    text_tokens = _tokens(text)
    if not text_tokens:
        return False
    return (len(text_tokens & document_tokens) / len(text_tokens)) >= GROUNDING_THRESHOLD


def _severity(raw: str) -> Severity:
    try:
        return Severity(raw.strip().lower())
    except (ValueError, AttributeError):
        return Severity.medium


# ---- Call 1: extraction + quality + security + consistency + edge cases ----


class _WireRequirement(BaseModel):
    text: str = ""
    category: str = "Other"


class _WireIssue(BaseModel):
    sev: str = "medium"
    type: str = "quality"
    title: str = ""
    desc: str = ""
    rec: str = ""


class _WireQuality(BaseModel):
    r: int = -1
    c: int = 0
    cm: int = 0
    t: int = 0
    issues: list[_WireIssue] = Field(default_factory=list)


class _WireSecurity(BaseModel):
    r: int = -1
    sev: str = "medium"
    cat: str = "security"
    desc: str = ""
    rec: str = ""


class _WireConflict(BaseModel):
    r: int = -1
    r2: int = -1
    sev: str = "medium"
    reason: str = ""


class _WireEdge(BaseModel):
    r: int = -1
    title: str = ""
    scenario: str = ""
    expected: str = ""
    priority: str = "medium"


class CombinedAnalysisResponse(BaseModel):
    requirements: list[_WireRequirement] = Field(default_factory=list)
    quality: list[_WireQuality] = Field(default_factory=list)
    conflicts: list[_WireConflict] = Field(default_factory=list)
    edges: list[_WireEdge] = Field(default_factory=list)

    _clean = field_validator("requirements", "quality", "conflicts", "edges", mode="before")(_drop_non_objects)


def run_combined_analysis(
    document_text: str, client: TieredLLMClient
) -> tuple[list[Requirement], list[QualityAnalysis], list[RequirementConflict], list[EdgeCase]]:
    response = client.call_structured(COMBINED_ANALYSIS_SYSTEM_PROMPT, document_text, CombinedAnalysisResponse)

    document_tokens = _tokens(document_text)
    requirements: list[Requirement] = []
    index_to_id: dict[int, str] = {}
    text_by_id: dict[str, str] = {}
    seen: set[str] = set()
    for raw_index, item in enumerate(response.requirements):
        text = item.text.strip()
        if not text or not _is_grounded(text, document_tokens):
            continue
        normalized = text.lower().rstrip(".")
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned = text.rstrip(".") + "."
        req_id = f"REQ-{len(requirements) + 1:03d}"
        index_to_id[raw_index] = req_id
        text_by_id[req_id] = cleaned
        requirements.append(
            Requirement(
                id=req_id,
                text=cleaned,
                category=item.category or "Other",
                source_text=cleaned,
                source_location=f"extracted item {len(requirements) + 1}",
            )
        )

    quality = [
        QualityAnalysis(
            requirement_id=index_to_id[item.r],
            clarity_score=item.c,
            completeness_score=item.cm,
            testability_score=item.t,
            issues=[
                RequirementIssue(
                    severity=_severity(issue.sev),
                    type=issue.type or "quality",
                    title=issue.title or "Requirement quality issue",
                    description=issue.desc,
                    evidence=text_by_id[index_to_id[item.r]],
                    recommendation=issue.rec,
                )
                for issue in item.issues
                if issue.desc or issue.title
            ],
        )
        for item in response.quality
        if item.r in index_to_id
    ]

    conflicts: list[RequirementConflict] = []
    seen_pairs: set[tuple[str, str]] = set()
    for item in response.conflicts:
        if item.r not in index_to_id or item.r2 not in index_to_id or item.r == item.r2:
            continue
        if not item.reason:
            continue
        left, right = _correct_conflict_ids(item, index_to_id, text_by_id)
        pair = tuple(sorted((left, right)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        conflicts.append(
            RequirementConflict(
                requirement_id=left,
                related_requirement_id=right,
                severity=_severity(item.sev),
                reason=item.reason,
                evidence=f"{text_by_id[left]} / {text_by_id[right]}",
            )
        )

    edge_cases = [
        EdgeCase(
            requirement_id=index_to_id[item.r],
            title=item.title or "Unspecified scenario",
            scenario=item.scenario,
            expected_behavior=item.expected,
            priority=item.priority or "medium",
        )
        for item in response.edges
        if item.r in index_to_id and (item.scenario or item.title)
    ]

    return requirements, quality, conflicts, edge_cases


# ---- Call 2: security + requirement improvement + test generation ----
# Security lives here rather than in call 1 because a single call asked to do extraction,
# quality, security, consistency AND edge cases reliably under-populates whole sections on
# local models (measured: qwen2.5:7b returned zero security findings for a spec containing an
# unvalidated file upload). Splitting the load keeps the pipeline at two calls while restoring
# security coverage.


class _WireImprovement(BaseModel):
    r: int = -1
    text: str = ""
    why: str = ""
    questions: list[str] = Field(default_factory=list)


class _WireTest(BaseModel):
    r: int = -1
    title: str = ""
    cat: str = "positive"
    priority: str = "medium"
    steps: list[str] = Field(default_factory=list)
    expected: str = ""


class CombinedImprovementTestResponse(BaseModel):
    security: list[_WireSecurity] = Field(default_factory=list)
    improvements: list[_WireImprovement] = Field(default_factory=list)
    tests: list[_WireTest] = Field(default_factory=list)

    _clean = field_validator("security", "improvements", "tests", mode="before")(_drop_non_objects)


def run_combined_improvement_and_tests(
    requirements: list[Requirement],
    quality: list[QualityAnalysis],
    edge_cases: list[EdgeCase],
    client: TieredLLMClient,
    related: dict[str, list[Requirement]] | None = None,
    deadline: float | None = None,
) -> tuple[list[SecurityFinding], list[ImprovedRequirement], list[TestCase]]:
    if not requirements:
        return [], [], []
    related = related or {}

    text_by_id = {req.id: req.text for req in requirements}
    quality_by_id = {item.requirement_id: item for item in quality}
    edges_by_id: dict[str, list[EdgeCase]] = {}
    for edge_case in edge_cases:
        edges_by_id.setdefault(edge_case.requirement_id, []).append(edge_case)

    # Process in batches. A single call covering every requirement overflows the completion
    # token cap on real documents, and the model then truncates mid-JSON - which silently
    # drops whole sections rather than failing loudly.
    settings = get_settings()
    # Provider-aware: Gemini answers for a whole document in one request, while Groq's
    # per-minute token budget needs the work split into much smaller batches.
    batch_size = max(1, getattr(client, "batch_size", settings.improvement_batch_size))
    batches = [requirements[i : i + batch_size] for i in range(0, len(requirements), batch_size)]

    def _run(batch: list[Requirement]):
        return _run_improvement_batch(
            batch, text_by_id, quality_by_id, edges_by_id, related, client
        )

    # Batches are independent, so issue them concurrently: a document large enough to need
    # several batches would otherwise pay the full latency of each one in sequence.
    batch_results = []
    if settings.llm_max_parallel > 1 and len(batches) > 1:
        with ThreadPoolExecutor(max_workers=min(settings.llm_max_parallel, len(batches))) as pool:
            batch_results = list(pool.map(_run, batches))
    else:
        for index, batch in enumerate(batches):
            # Stop issuing further batches once out of time. Requirements already processed keep
            # their AI output; the caller fills the remainder deterministically, so a slow or
            # rate-limited provider degrades coverage instead of hanging the request.
            if deadline is not None and index and time.monotonic() >= deadline:
                logger.warning(
                    "Deadline reached after %d/%d improvement batches", index, len(batches)
                )
                progress_service.report(
                    f"Time limit reached after {index} of {len(batches)} batches; "
                    "remaining requirements analyzed without AI.",
                    LogLevel.warning,
                )
                break
            # Progress is reported per batch: on a rate-limited free tier this stage can run
            # for minutes, and without this the bar would sit unchanged the whole time.
            progress_service.report_stage_progress(
                "security_tests",
                20 + int(70 * index / max(1, len(batches))),
                f"Generating security findings and tests — batch {index + 1} of {len(batches)}.",
            )
            batch_results.append(_run(batch))

    security_findings: list[SecurityFinding] = []
    improved: list[ImprovedRequirement] = []
    tests: list[TestCase] = []
    test_counters: dict[str, int] = {}

    # Merge sequentially so test numbering stays deterministic regardless of completion order.
    for batch_security, batch_improved, batch_tests in batch_results:
        security_findings.extend(batch_security)
        improved.extend(batch_improved)
        for requirement_id, title, steps, expected, priority, category in batch_tests:
            test_counters[requirement_id] = test_counters.get(requirement_id, 0) + 1
            tests.append(
                TestCase(
                    id=f"TC-{requirement_id.removeprefix('REQ-')}-{test_counters[requirement_id]:03d}",
                    requirement_id=requirement_id,
                    title=title,
                    preconditions=["The system is available."],
                    steps=steps or [f"Exercise the behavior described by {requirement_id}."],
                    expected_result=expected,
                    priority=priority or "medium",
                    category=category or "positive",
                )
            )

    return security_findings, improved, tests


def _run_improvement_batch(
    requirements: list[Requirement],
    text_by_id: dict[str, str],
    quality_by_id: dict[str, QualityAnalysis],
    edges_by_id: dict[str, list[EdgeCase]],
    related: dict[str, list[Requirement]],
    client: TieredLLMClient,
):
    id_by_index = {index: req.id for index, req in enumerate(requirements)}
    index_by_id = {req.id: index for index, req in enumerate(requirements)}
    payload = {
        "requirements": [
            {
                "r": index_by_id[req.id],
                "text": req.text,
                "category": req.category,
                "issues": [issue.title for issue in quality_by_id[req.id].issues]
                if req.id in quality_by_id
                else [],
                "edges": [edge.title for edge in edges_by_id.get(req.id, [])],
                # RAG: semantically nearest requirements, retrieved from pgvector.
                "related": [neighbour.text for neighbour in related.get(req.id, [])],
            }
            for req in requirements
        ]
    }
    response = client.call_structured(
        COMBINED_IMPROVEMENT_TEST_SYSTEM_PROMPT, json.dumps(payload), CombinedImprovementTestResponse
    )

    security = [
        SecurityFinding(
            requirement_id=id_by_index[item.r],
            severity=_severity(item.sev),
            category=item.cat or "security",
            description=item.desc,
            evidence=text_by_id[id_by_index[item.r]],
            recommendation=item.rec,
        )
        for item in response.security
        if item.r in id_by_index and item.desc
    ]

    improved = [
        ImprovedRequirement(
            requirement_id=id_by_index[item.r],
            original_text=text_by_id[id_by_index[item.r]],
            improved_text=item.text,
            rationale=item.why,
            remaining_questions=item.questions,
        )
        for item in response.improvements
        if item.r in id_by_index and item.text
    ]

    # Returned as tuples rather than TestCase objects so the caller can assign the sequential
    # test codes after all batches have come back.
    tests = [
        (id_by_index[item.r], item.title, item.steps, item.expected, item.priority, item.cat)
        for item in response.tests
        if item.r in id_by_index and item.title
    ]
    return security, improved, tests
