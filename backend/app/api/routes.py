from collections import Counter
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, status

from backend.app.ai.workflow import run_analysis
from backend.app.db.repository import repository
from backend.app.models import (
    AnalysisRecord,
    AnalysisStatus,
    ApiResponse,
    DocumentStatus,
    LogLevel,
    StartAnalysisRequest,
    utc_now,
)
from backend.app.services import progress as progress_service
from backend.app.services.document_processor import (
    DocumentProcessor,
    DocumentValidationError,
)
from backend.app.services.progress import AnalysisCancelled, ProgressTracker

router = APIRouter()
processor = DocumentProcessor()


def _not_found(kind: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": f"{kind.upper()}_NOT_FOUND", "message": f"The requested {kind} does not exist."},
    )


def _load_completed(analysis_id: str):
    analysis = repository.get_analysis(analysis_id)
    if not analysis:
        raise _not_found("analysis")
    if analysis.status != AnalysisStatus.completed or not analysis.result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ANALYSIS_NOT_READY", "message": "Analysis results are not ready yet."},
        )
    return analysis


@router.get("/health", response_model=ApiResponse)
def health() -> ApiResponse:
    return ApiResponse(success=True, data={"status": "ok"})


# ---- documents ----


@router.post("/documents/upload", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile) -> ApiResponse:
    try:
        document = await processor.save_upload(file)
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    document = repository.add_document(document)
    return ApiResponse(
        success=True,
        data={
            "document_id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "status": document.status,
        },
    )


# ---- analyses ----


@router.post("/analyses", response_model=ApiResponse, status_code=status.HTTP_202_ACCEPTED)
def start_analysis(payload: StartAnalysisRequest, background_tasks: BackgroundTasks) -> ApiResponse:
    document = repository.get_document(payload.document_id)
    if not document:
        raise _not_found("document")

    analysis = repository.add_analysis(AnalysisRecord(document_id=document.id))
    background_tasks.add_task(_execute_analysis, analysis.id)
    return ApiResponse(
        success=True,
        data={
            "analysis_id": analysis.id,
            "document_id": document.id,
            "filename": document.filename,
            "status": analysis.status,
        },
    )


@router.get("/analyses", response_model=ApiResponse)
def list_analyses(limit: int = Query(default=50, ge=1, le=200)) -> ApiResponse:
    return ApiResponse(success=True, data={"analyses": repository.list_analyses(limit=limit)})


@router.get("/analyses/{analysis_id}/status", response_model=ApiResponse)
def get_analysis_status(analysis_id: str) -> ApiResponse:
    analysis = repository.get_analysis(analysis_id, include_result=False)
    if not analysis:
        raise _not_found("analysis")

    data = {
        "analysis_id": analysis.id,
        "status": analysis.status,
        "progress": analysis.progress,
        "current_stage": analysis.current_stage,
        "error_message": analysis.error_message,
        "stages": [stage.model_dump(mode="json") for stage in analysis.stages],
        "events": [event.model_dump(mode="json") for event in analysis.events],
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at,
    }
    # While the analysis is still running, in-memory state is fresher than the last flush.
    live = progress_service.status_for(analysis_id, analysis.status)
    if live and analysis.status in (AnalysisStatus.queued, AnalysisStatus.processing):
        data.update(live)
        data["status"] = analysis.status
    return ApiResponse(success=True, data=data)


@router.get("/analyses/{analysis_id}/events", response_model=ApiResponse)
def get_analysis_events(analysis_id: str) -> ApiResponse:
    tracker = progress_service.get_tracker(analysis_id)
    if tracker:
        return ApiResponse(
            success=True,
            data={"events": [event.model_dump(mode="json") for event in tracker.events]},
        )
    analysis = repository.get_analysis(analysis_id, include_result=False)
    if not analysis:
        raise _not_found("analysis")
    return ApiResponse(
        success=True, data={"events": [event.model_dump(mode="json") for event in analysis.events]}
    )


@router.post("/analyses/{analysis_id}/cancel", response_model=ApiResponse)
def cancel_analysis(analysis_id: str) -> ApiResponse:
    analysis = repository.get_analysis(analysis_id, include_result=False)
    if not analysis:
        raise _not_found("analysis")
    if analysis.status in (AnalysisStatus.completed, AnalysisStatus.failed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ANALYSIS_FINISHED", "message": "This analysis has already finished."},
        )
    cancelled = progress_service.cancel_analysis(analysis_id)
    return ApiResponse(success=True, data={"analysis_id": analysis_id, "cancelling": cancelled})


@router.delete("/analyses/{analysis_id}", response_model=ApiResponse)
def delete_analysis(analysis_id: str) -> ApiResponse:
    analysis = repository.get_analysis(analysis_id, include_result=False)
    if not analysis:
        raise _not_found("analysis")
    if analysis.status in (AnalysisStatus.queued, AnalysisStatus.processing):
        # Stop the worker first so it cannot resurrect rows after the delete.
        progress_service.cancel_analysis(analysis_id)
    repository.delete_analysis(analysis_id)
    return ApiResponse(success=True, data={"analysis_id": analysis_id, "deleted": True})


@router.get("/analyses/{analysis_id}", response_model=ApiResponse)
def get_analysis(analysis_id: str) -> ApiResponse:
    analysis = _load_completed(analysis_id)
    document = repository.get_document(analysis.document_id)
    return ApiResponse(
        success=True,
        data={
            "analysis_id": analysis.id,
            "document_id": analysis.document_id,
            "filename": document.filename if document else None,
            "status": analysis.status,
            "created_at": analysis.created_at,
            "completed_at": analysis.completed_at,
            "stages": [stage.model_dump(mode="json") for stage in analysis.stages],
            **analysis.result.model_dump(mode="json"),
        },
    )


@router.get("/analyses/{analysis_id}/results", response_model=ApiResponse)
def get_analysis_results(analysis_id: str) -> ApiResponse:
    analysis = _load_completed(analysis_id)
    return ApiResponse(success=True, data=analysis.result.model_dump(mode="json"))


@router.get("/analyses/{analysis_id}/requirements", response_model=ApiResponse)
def get_requirements(analysis_id: str) -> ApiResponse:
    result = _load_completed(analysis_id).result
    quality_by_id = {item.requirement_id: item for item in result.quality}
    improved_by_id = {item.requirement_id: item for item in result.improved_requirements}
    security_counts = Counter(finding.requirement_id for finding in result.security_findings)
    test_counts = Counter(test.requirement_id for test in result.test_cases)
    edge_counts = Counter(edge.requirement_id for edge in result.edge_cases)

    items = []
    for requirement in result.requirements:
        quality = quality_by_id.get(requirement.id)
        improved = improved_by_id.get(requirement.id)
        items.append(
            {
                **requirement.model_dump(mode="json"),
                "clarity_score": quality.clarity_score if quality else None,
                "completeness_score": quality.completeness_score if quality else None,
                "testability_score": quality.testability_score if quality else None,
                "issues": [issue.model_dump(mode="json") for issue in quality.issues] if quality else [],
                "improved": improved.model_dump(mode="json") if improved else None,
                "security_count": security_counts.get(requirement.id, 0),
                "test_count": test_counts.get(requirement.id, 0),
                "edge_case_count": edge_counts.get(requirement.id, 0),
            }
        )
    return ApiResponse(success=True, data={"requirements": items, "total": len(items)})


@router.get("/analyses/{analysis_id}/requirements/{requirement_code}", response_model=ApiResponse)
def get_requirement_detail(analysis_id: str, requirement_code: str) -> ApiResponse:
    result = _load_completed(analysis_id).result
    requirement = next((r for r in result.requirements if r.id == requirement_code), None)
    if not requirement:
        raise _not_found("requirement")
    quality = next((q for q in result.quality if q.requirement_id == requirement_code), None)
    improved = next(
        (i for i in result.improved_requirements if i.requirement_id == requirement_code), None
    )
    return ApiResponse(
        success=True,
        data={
            "requirement": requirement.model_dump(mode="json"),
            "quality": quality.model_dump(mode="json") if quality else None,
            "security_findings": [
                f.model_dump(mode="json") for f in result.security_findings if f.requirement_id == requirement_code
            ],
            "conflicts": [
                c.model_dump(mode="json")
                for c in result.conflicts
                if requirement_code in (c.requirement_id, c.related_requirement_id)
            ],
            "edge_cases": [
                e.model_dump(mode="json") for e in result.edge_cases if e.requirement_id == requirement_code
            ],
            "test_cases": [
                t.model_dump(mode="json") for t in result.test_cases if t.requirement_id == requirement_code
            ],
            "improved": improved.model_dump(mode="json") if improved else None,
        },
    )


@router.get("/analyses/{analysis_id}/security", response_model=ApiResponse)
def get_security_findings(analysis_id: str, severity: str | None = None) -> ApiResponse:
    findings = _load_completed(analysis_id).result.security_findings
    if severity:
        findings = [f for f in findings if f.severity.value == severity.lower()]
    return ApiResponse(
        success=True,
        data={
            "findings": [f.model_dump(mode="json") for f in findings],
            "total": len(findings),
            "by_severity": dict(Counter(f.severity.value for f in findings)),
            "by_category": dict(Counter(f.category for f in findings)),
        },
    )


@router.get("/analyses/{analysis_id}/conflicts", response_model=ApiResponse)
def get_conflicts(analysis_id: str) -> ApiResponse:
    conflicts = _load_completed(analysis_id).result.conflicts
    return ApiResponse(
        success=True,
        data={"conflicts": [c.model_dump(mode="json") for c in conflicts], "total": len(conflicts)},
    )


@router.get("/analyses/{analysis_id}/edge-cases", response_model=ApiResponse)
def get_edge_cases(analysis_id: str) -> ApiResponse:
    edge_cases = _load_completed(analysis_id).result.edge_cases
    return ApiResponse(
        success=True,
        data={"edge_cases": [e.model_dump(mode="json") for e in edge_cases], "total": len(edge_cases)},
    )


@router.get("/analyses/{analysis_id}/tests", response_model=ApiResponse)
def get_tests(analysis_id: str, category: str | None = None, priority: str | None = None) -> ApiResponse:
    tests = _load_completed(analysis_id).result.test_cases
    if category:
        tests = [t for t in tests if t.category.lower() == category.lower()]
    if priority:
        tests = [t for t in tests if t.priority.lower() == priority.lower()]
    return ApiResponse(
        success=True,
        data={
            "test_cases": [t.model_dump(mode="json") for t in tests],
            "total": len(tests),
            "by_category": dict(Counter(t.category for t in tests)),
            "by_priority": dict(Counter(t.priority for t in tests)),
        },
    )


@router.get("/analyses/{analysis_id}/statistics", response_model=ApiResponse)
def get_statistics(analysis_id: str) -> ApiResponse:
    result = _load_completed(analysis_id).result
    issues = [issue for item in result.quality for issue in item.issues]
    return ApiResponse(
        success=True,
        data={
            "totals": {
                "requirements": len(result.requirements),
                "quality_issues": len(issues),
                "security_findings": len(result.security_findings),
                "conflicts": len(result.conflicts),
                "edge_cases": len(result.edge_cases),
                "test_cases": len(result.test_cases),
                "improved_requirements": len(result.improved_requirements),
            },
            "score": result.score.model_dump(mode="json") if result.score else None,
            "quality_by_severity": dict(Counter(i.severity.value for i in issues)),
            "security_by_severity": dict(Counter(f.severity.value for f in result.security_findings)),
            "security_by_category": dict(Counter(f.category for f in result.security_findings)),
            "tests_by_category": dict(Counter(t.category for t in result.test_cases)),
            "requirements_by_category": dict(Counter(r.category for r in result.requirements)),
            "degraded": result.degraded,
            "degraded_reason": result.degraded_reason,
        },
    )


# ---- background execution ----


def _execute_analysis(analysis_id: str) -> None:
    analysis = repository.get_analysis(analysis_id, include_result=False)
    if not analysis:
        return
    document = repository.get_document(analysis.document_id)
    if not document:
        analysis.status = AnalysisStatus.failed
        analysis.error_message = "Document disappeared before analysis could begin."
        repository.update_analysis(analysis)
        return

    def _flush(tracker: ProgressTracker) -> None:
        repository.update_progress(
            analysis_id,
            tracker.overall_progress,
            tracker.current_stage,
            [stage.model_dump(mode="json") for stage in tracker.stages],
            [event.model_dump(mode="json") for event in tracker.events],
        )

    tracker = ProgressTracker(analysis_id, on_flush=_flush)
    progress_service.register(tracker)
    # Bind for this thread so deep call sites (the LLM client waiting out a rate-limit
    # window, the batch loop) can report progress without being passed the tracker.
    token = progress_service.current_tracker.set(tracker)

    try:
        document.status = DocumentStatus.processing
        repository.update_document(document)
        analysis.status = AnalysisStatus.processing
        repository.update_analysis(analysis)

        tracker.start("initialization", f"Loading {document.filename}.")
        extracted_text = processor.extract_text(Path(document.storage_path), document.file_type)
        chunks = processor.chunk_text(extracted_text)
        tracker.complete(
            "initialization",
            f"Extracted {len(extracted_text):,} characters across {len(chunks)} sections.",
        )

        result = run_analysis(
            extracted_text,
            chunks,
            document_id=document.id,
            analysis_id=analysis.id,
            repository=repository,
            tracker=tracker,
        )

        analysis.result = result
        # Surface a partial-AI run rather than reporting a clean success: without this a
        # rate-limited analysis is indistinguishable from a full one in the API.
        if result.degraded:
            analysis.error_message = f"Partial AI analysis - {result.degraded_reason}"
        analysis.status = AnalysisStatus.completed
        analysis.progress = 100
        analysis.current_stage = "completed"
        analysis.stages = tracker.stages
        analysis.events = tracker.events
        analysis.completed_at = utc_now()
        document.status = DocumentStatus.processed
        repository.update_document(document)
        repository.update_analysis(analysis)
    except AnalysisCancelled:
        tracker.skip_remaining("Analysis cancelled by user.")
        analysis.status = AnalysisStatus.failed
        analysis.progress = tracker.overall_progress
        analysis.current_stage = "cancelled"
        analysis.error_message = "Analysis was cancelled."
        analysis.stages = tracker.stages
        analysis.events = tracker.events
        analysis.completed_at = utc_now()
        document.status = DocumentStatus.uploaded
        repository.update_document(document)
        repository.update_analysis(analysis)
    except Exception as exc:  # noqa: BLE001
        tracker.log(f"Analysis failed: {exc}", LogLevel.error)
        analysis.status = AnalysisStatus.failed
        analysis.progress = 100
        analysis.current_stage = "failed"
        analysis.error_message = str(exc)
        analysis.stages = tracker.stages
        analysis.events = tracker.events
        analysis.completed_at = utc_now()
        document.status = DocumentStatus.failed
        repository.update_document(document)
        repository.update_analysis(analysis)
    finally:
        progress_service.current_tracker.reset(token)
        progress_service.unregister(analysis_id)
