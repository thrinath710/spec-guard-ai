import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.ai import llm_nodes
from backend.app.ai.heuristics import (
    analyze_consistency,
    analyze_quality,
    analyze_security,
    extract_requirements,
    generate_edge_cases,
    generate_tests,
    improve_requirement,
    retrieve_related,
    score_risk,
)
from backend.app.ai.llm import LLMError, build_llm_client
from backend.app.ai.rag import embed_and_store, retrieve_related as rag_retrieve_related
from backend.app.core.config import get_settings
from backend.app.models import (
    AnalysisResult,
    AnalysisScore,
    EdgeCase,
    ImprovedRequirement,
    QualityAnalysis,
    Requirement,
    RequirementConflict,
    SecurityFinding,
    TestCase,
)

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = build_llm_client()
    return _client


class WorkflowState(TypedDict, total=False):
    document_text: str
    chunks: list[str]
    document_id: str
    analysis_id: str
    repository: Any
    requirement_id_map: dict[str, str]
    related: dict[str, list[Requirement]]
    degraded_reasons: list[str]
    deadline: float
    tracker: Any
    requirements: list[Requirement]
    quality: list[QualityAnalysis]
    security_findings: list[SecurityFinding]
    conflicts: list[RequirementConflict]
    edge_cases: list[EdgeCase]
    test_cases: list[TestCase]
    improved_requirements: list[ImprovedRequirement]
    result: AnalysisResult


def build_workflow():
    graph = StateGraph(WorkflowState)
    graph.add_node("combined_analysis", _combined_analysis)
    graph.add_node("rag_retrieval", _rag_retrieval)
    graph.add_node("combined_improvement_and_tests", _combined_improvement_and_tests)
    graph.add_node("score_results", _score_results)
    graph.add_node("persist_results", _persist_results)

    graph.add_edge(START, "combined_analysis")
    graph.add_edge("combined_analysis", "rag_retrieval")
    graph.add_edge("rag_retrieval", "combined_improvement_and_tests")
    graph.add_edge("combined_improvement_and_tests", "score_results")
    graph.add_edge("score_results", "persist_results")
    graph.add_edge("persist_results", END)
    return graph.compile()


def run_analysis(
    document_text: str,
    chunks: list[str],
    *,
    document_id: str | None = None,
    analysis_id: str | None = None,
    repository: Any = None,
    tracker: Any = None,
) -> AnalysisResult:
    workflow = build_workflow()
    initial_state: WorkflowState = {
        "document_text": document_text,
        "chunks": chunks,
        "deadline": time.monotonic() + get_settings().analysis_deadline_seconds,
    }
    if document_id:
        initial_state["document_id"] = document_id
    if analysis_id:
        initial_state["analysis_id"] = analysis_id
    if repository is not None:
        initial_state["repository"] = repository
    if tracker is not None:
        initial_state["tracker"] = tracker
    state = workflow.invoke(initial_state)
    return state["result"]


def _combined_analysis(state: WorkflowState) -> WorkflowState:
    """Requirement extraction + quality + consistency + edge cases in one LLM call."""
    document_text = state["document_text"]
    degraded = None
    tracker = _tracker(state)
    if tracker:
        tracker.raise_if_cancelled()
        tracker.start(
            "analysis",
            f"Sending specification to {getattr(_get_client(), 'active_name', 'the language model')}.",
        )
        tracker.update("analysis", 35)
    if get_settings().use_llm and not _past_deadline(state):
        try:
            requirements, quality, conflicts, edge_cases = llm_nodes.run_combined_analysis(
                document_text, _get_client()
            )
            if requirements:
                if tracker:
                    tracker.update(
                        "analysis",
                        90,
                        f"Extracted {len(requirements)} requirements, {sum(len(q.issues) for q in quality)} "
                        f"quality issues, {len(conflicts)} contradictions, {len(edge_cases)} edge cases.",
                    )
                    tracker.complete("analysis")
                return {
                    "requirements": requirements,
                    "quality": quality,
                    "conflicts": conflicts,
                    "edge_cases": edge_cases,
                }
            logger.warning("Combined analysis call returned no grounded requirements, falling back to heuristics")
            degraded = "analysis: model returned no usable requirements"
        except LLMError as exc:
            logger.warning("Combined analysis LLM call failed, falling back to heuristics: %s", exc)
            degraded = f"analysis: {_short_reason(exc)}"
            if tracker:
                tracker.warn(f"AI analysis unavailable ({_short_reason(exc)}); using rule-based checks.", "analysis")

    requirements = extract_requirements(document_text)
    related = {requirement.id: retrieve_related(requirement, requirements) for requirement in requirements}
    quality = [analyze_quality(requirement) for requirement in requirements]
    security_findings: list[SecurityFinding] = []
    for requirement in requirements:
        security_findings.extend(analyze_security(requirement))
    # Each requirement is compared against its neighbours, so the same pair surfaces twice
    # (A vs B and B vs A). Keep one entry per pair.
    conflicts: list[RequirementConflict] = []
    seen_pairs: set[tuple[str, str]] = set()
    for requirement in requirements:
        for conflict in analyze_consistency(requirement, related.get(requirement.id, [])):
            pair = tuple(sorted((conflict.requirement_id, conflict.related_requirement_id)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            conflicts.append(conflict)
    edge_cases: list[EdgeCase] = []
    for requirement in requirements:
        edge_cases.extend(generate_edge_cases(requirement))
    if tracker:
        tracker.complete("analysis", f"Analyzed {len(requirements)} requirements without AI.")
    return {
        "requirements": requirements,
        "quality": quality,
        "security_findings": security_findings,
        "conflicts": conflicts,
        "edge_cases": edge_cases,
        "degraded_reasons": [degraded] if degraded else [],
    }


def _rag_retrieval(state: WorkflowState) -> WorkflowState:
    """Embed requirements, store them in Supabase pgvector, then semantically retrieve each
    requirement's nearest neighbours. The retrieved context is fed into the second LLM call.
    Uses the embedding model only - no chat-completion call happens here."""
    requirements = state.get("requirements", [])
    document_id = state.get("document_id")
    repository = state.get("repository")
    tracker = _tracker(state)
    if not (get_settings().use_llm and document_id and repository and requirements):
        if tracker:
            tracker.start("rag")
            tracker.complete("rag", "Vector storage not configured; skipping retrieval.")
        return {}
    if tracker:
        tracker.raise_if_cancelled()
        tracker.start("rag", f"Generating embeddings for {len(requirements)} requirements.")
        tracker.update("rag", 40)
    try:
        requirement_id_map, embeddings = embed_and_store(requirements, document_id, repository)
        if tracker:
            tracker.update("rag", 70, "Vectors stored in Supabase pgvector.")
        related = rag_retrieve_related(requirements, embeddings, requirement_id_map, document_id, repository)
        if tracker:
            total = sum(len(v) for v in related.values())
            tracker.complete("rag", f"Retrieved {total} related requirements via similarity search.")
        return {"requirement_id_map": requirement_id_map, "related": related}
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG retrieval failed (analysis continues without it): %s", exc)
        if tracker:
            tracker.warn(f"Retrieval unavailable: {exc}", "rag")
            tracker.complete("rag", "Continuing without retrieved context.")
        return {}


def _combined_improvement_and_tests(state: WorkflowState) -> WorkflowState:
    """Security analysis + requirement improvement + test case generation in one LLM call."""
    degraded = None
    requirements = state.get("requirements", [])
    quality = state.get("quality", [])
    security_findings = state.get("security_findings", [])
    edge_cases = state.get("edge_cases", [])
    tracker = _tracker(state)
    if tracker:
        tracker.raise_if_cancelled()
        tracker.start("security_tests", "Analyzing security gaps and generating test cases.")
        tracker.update("security_tests", 30)

    if get_settings().use_llm and requirements and not _past_deadline(state):
        try:
            security, improved, tests = llm_nodes.run_combined_improvement_and_tests(
                requirements, quality, edge_cases, _get_client(),
                related=state.get("related", {}), deadline=state.get("deadline")
            )
            # A deadline can cut the batch loop short, leaving later requirements with no
            # improvement or tests. Fill only those gaps rather than discarding the AI output.
            covered = {item.requirement_id for item in improved}
            missing = [req for req in requirements if req.id not in covered]
            if missing:
                quality_by_id = {item.requirement_id: item for item in quality}
                security_by_id: dict[str, list[SecurityFinding]] = {}
                for finding in security:
                    security_by_id.setdefault(finding.requirement_id, []).append(finding)
                edges_by_id: dict[str, list[EdgeCase]] = {}
                for edge_case in edge_cases:
                    edges_by_id.setdefault(edge_case.requirement_id, []).append(edge_case)
                for requirement in missing:
                    improved.append(
                        improve_requirement(
                            requirement,
                            quality_by_id.get(requirement.id)
                            or QualityAnalysis(
                                requirement_id=requirement.id,
                                clarity_score=0,
                                completeness_score=0,
                                testability_score=0,
                            ),
                            security_by_id.get(requirement.id, []),
                        )
                    )
                    tests.extend(generate_tests(requirement, edges_by_id.get(requirement.id, [])))
                degraded = f"improvement/tests: time limit reached, {len(missing)} requirement(s) analyzed without AI"

            if tracker:
                tracker.complete(
                    "security_tests",
                    f"Produced {len(security)} security findings, {len(tests)} test cases, "
                    f"{len(improved)} improved requirements.",
                )
            return {
                "security_findings": security,
                "improved_requirements": improved,
                "test_cases": tests,
                "degraded_reasons": [*state.get("degraded_reasons", []), *([degraded] if degraded else [])],
            }
        except LLMError as exc:
            logger.warning("Combined improvement/test LLM call failed, falling back to heuristics: %s", exc)
            degraded = f"improvement/tests: {_short_reason(exc)}"
            if tracker:
                tracker.warn(
                    f"AI generation unavailable ({_short_reason(exc)}); using rule-based checks.",
                    "security_tests",
                )

    # Security now comes from this call, so on fallback it has to be derived here too -
    # otherwise a failed call 2 would silently report zero security findings.
    if not security_findings:
        security_findings = []
        for requirement in requirements:
            security_findings.extend(analyze_security(requirement))

    quality_by_id = {item.requirement_id: item for item in quality}
    security_by_id: dict[str, list[SecurityFinding]] = {}
    for finding in security_findings:
        security_by_id.setdefault(finding.requirement_id, []).append(finding)
    cases_by_requirement: dict[str, list[EdgeCase]] = {}
    for edge_case in edge_cases:
        cases_by_requirement.setdefault(edge_case.requirement_id, []).append(edge_case)

    # Every requirement gets a rewrite, not only those the model happened to score: a
    # requirement missing from the quality list would otherwise vanish from the results.
    improved = [
        improve_requirement(
            requirement,
            quality_by_id.get(requirement.id)
            or QualityAnalysis(
                requirement_id=requirement.id,
                clarity_score=0,
                completeness_score=0,
                testability_score=0,
            ),
            security_by_id.get(requirement.id, []),
        )
        for requirement in requirements
    ]
    tests: list[TestCase] = []
    for requirement in requirements:
        tests.extend(generate_tests(requirement, cases_by_requirement.get(requirement.id, [])))
    if tracker:
        tracker.complete(
            "security_tests",
            f"Produced {len(security_findings)} security findings and {len(tests)} test cases without AI.",
        )
    return {
        # Returned explicitly: these were derived above and would otherwise be dropped,
        # leaving the report claiming zero security findings.
        "security_findings": security_findings,
        "improved_requirements": improved,
        "test_cases": tests,
        "degraded_reasons": [*state.get("degraded_reasons", []), *([degraded] if degraded else [])],
    }


def _score_results(state: WorkflowState) -> WorkflowState:
    tracker = _tracker(state)
    if tracker:
        tracker.start("scoring")
    quality = state.get("quality", [])
    security = state.get("security_findings", [])
    quality_score = _average(
        [(item.clarity_score + item.completeness_score + item.testability_score) // 3 for item in quality]
    )
    testability_score = _average([item.testability_score for item in quality])
    security_penalty = sum(18 if item.severity.value == "high" else 10 for item in security)
    security_score = max(10, 100 - security_penalty)
    overall = round((quality_score * 0.45) + (security_score * 0.35) + (testability_score * 0.20))
    result = AnalysisResult(
        requirements=state.get("requirements", []),
        quality=quality,
        security_findings=security,
        conflicts=state.get("conflicts", []),
        edge_cases=state.get("edge_cases", []),
        test_cases=state.get("test_cases", []),
        improved_requirements=state.get("improved_requirements", []),
        score=AnalysisScore(
            quality_score=quality_score,
            security_score=security_score,
            testability_score=testability_score,
            overall_score=overall,
            risk_level=score_risk([finding.severity for finding in security]),
        ),
        degraded=bool(state.get("degraded_reasons")),
        degraded_reason="; ".join(state.get("degraded_reasons", [])) or None,
    )
    if tracker:
        tracker.complete("scoring", f"Overall specification score: {overall}/100 ({result.score.risk_level} risk).")
    return {"result": result}


def _persist_results(state: WorkflowState) -> WorkflowState:
    tracker = _tracker(state)
    if tracker:
        tracker.start("persistence")
    repository = state.get("repository")
    analysis_id = state.get("analysis_id")
    document_id = state.get("document_id")
    result = state.get("result")
    if not (repository and analysis_id and document_id and result):
        if tracker:
            tracker.complete("persistence", "Report ready.")
        return {}
    try:
        requirement_id_map = state.get("requirement_id_map")
        if not requirement_id_map:
            requirement_id_map = repository.persist_requirements(document_id, state.get("requirements", []))
        repository.persist_result(analysis_id, requirement_id_map, result)
        if tracker:
            tracker.complete("persistence", "Results stored and report ready.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist analysis result to database: %s", exc)
        if tracker:
            tracker.warn(f"Could not store results: {exc}", "persistence")
            tracker.complete("persistence", "Report ready (not persisted).")
    return {}


def _tracker(state: WorkflowState):
    """Progress reporting is optional: the workflow runs identically without a tracker."""
    return state.get("tracker")


def _past_deadline(state: WorkflowState) -> bool:
    deadline = state.get("deadline")
    if deadline and time.monotonic() >= deadline:
        logger.warning("Analysis deadline exceeded; completing with deterministic analyzers")
        return True
    return False


def _short_reason(exc: Exception) -> str:
    text = str(exc)
    if "All AI providers failed" in text:
        return "every AI provider was unavailable"
    if "No AI provider is configured" in text:
        return "no AI provider configured"
    if "rate_limit" in text or "429" in text:
        return "provider rate limit reached"
    if "timeout" in text.lower():
        return "provider timed out"
    return text[:120]


def _average(values: list[int]) -> int:
    if not values:
        return 0
    return round(sum(values) / len(values))
