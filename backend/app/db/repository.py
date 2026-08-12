from backend.app.core.config import Settings, get_settings
from backend.app.db.client import get_supabase_client
from backend.app.models import (
    AnalysisRecord,
    LogEvent,
    StageInfo,
    AnalysisResult,
    AnalysisScore,
    AnalysisStatus,
    DocumentRecord,
    DocumentStatus,
    EdgeCase,
    ImprovedRequirement,
    QualityAnalysis,
    Requirement,
    RequirementConflict,
    RequirementIssue,
    SecurityFinding,
    Severity,
    TestCase,
    utc_now,
)


def _document_to_row(document: DocumentRecord) -> dict:
    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "storage_path": document.storage_path,
        "status": document.status.value,
        "extracted_text": document.extracted_text or None,
    }


def _row_to_document(row: dict) -> DocumentRecord:
    return DocumentRecord(
        id=row["id"],
        filename=row["filename"],
        file_type=row["file_type"],
        file_size=row["file_size"],
        storage_path=row["storage_path"],
        status=DocumentStatus(row["status"]),
        extracted_text=row.get("extracted_text") or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class SupabaseRepository:
    # Set to False the first time the database rejects the pipeline-progress columns, so an
    # un-migrated database degrades to basic status tracking instead of failing every write.
    _progress_columns_available = True
    # Set to False if the documents table predates the extracted-text column.
    _document_text_available = True

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def client(self):
        # Resolved per call rather than cached on the instance: this repository is a module
        # level singleton shared between request handlers and background analysis threads,
        # and each thread needs its own Supabase connection.
        return get_supabase_client()

    # ---- documents ----

    def add_document(self, document: DocumentRecord) -> DocumentRecord:
        row = _document_to_row(document)
        if not type(self)._document_text_available:
            row.pop("extracted_text", None)
        try:
            self.client.table("documents").insert(row).execute()
        except Exception as exc:  # noqa: BLE001
            if not self._is_missing_column(exc):
                raise
            type(self)._document_text_available = False
            row.pop("extracted_text", None)
            self.client.table("documents").insert(row).execute()
        return document

    def get_document(self, document_id: str) -> DocumentRecord | None:
        resp = self.client.table("documents").select("*").eq("id", document_id).limit(1).execute()
        if not resp.data:
            return None
        return _row_to_document(resp.data[0])

    def update_document(self, document: DocumentRecord) -> DocumentRecord:
        document.updated_at = utc_now()
        row = _document_to_row(document)
        row.pop("id")
        if not type(self)._document_text_available:
            row.pop("extracted_text", None)
        self.client.table("documents").update(row).eq("id", document.id).execute()
        return document

    # ---- analyses ----

    def add_analysis(self, analysis: AnalysisRecord) -> AnalysisRecord:
        row = {
            "id": analysis.id,
            "document_id": analysis.document_id,
            "status": analysis.status.value,
            "progress": analysis.progress,
            "current_stage": analysis.current_stage,
            "error_message": analysis.error_message,
        }
        self.client.table("analyses").insert(row).execute()
        return analysis

    def get_analysis(self, analysis_id: str, *, include_result: bool = True) -> AnalysisRecord | None:
        """Set include_result=False for status polling. Reassembling the full result costs
        several seconds of round trips and the status endpoint never reads it."""
        resp = self.client.table("analyses").select("*").eq("id", analysis_id).limit(1).execute()
        if not resp.data:
            return None
        row = resp.data[0]
        result = None
        if include_result and row["status"] == AnalysisStatus.completed.value:
            result = self.load_result(analysis_id)
            note = row.get("error_message") or ""
            if result and note.startswith("Partial AI analysis"):
                result.degraded = True
                result.degraded_reason = note.removeprefix("Partial AI analysis - ")
        return AnalysisRecord(
            id=row["id"],
            document_id=row["document_id"],
            status=AnalysisStatus(row["status"]),
            progress=row["progress"],
            current_stage=row["current_stage"],
            error_message=row.get("error_message"),
            result=result,
            stages=[StageInfo.model_validate(item) for item in (row.get("stages") or [])],
            events=[LogEvent.model_validate(item) for item in (row.get("events") or [])],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row.get("completed_at"),
        )

    def update_analysis(self, analysis: AnalysisRecord) -> AnalysisRecord:
        analysis.updated_at = utc_now()
        row = {
            "status": analysis.status.value,
            "progress": analysis.progress,
            "current_stage": analysis.current_stage,
            "error_message": analysis.error_message,
        }
        if type(self)._progress_columns_available:
            row["stages"] = [stage.model_dump(mode="json") for stage in analysis.stages]
            row["events"] = [event.model_dump(mode="json") for event in analysis.events]
            if analysis.completed_at:
                row["completed_at"] = analysis.completed_at.isoformat()
        try:
            self.client.table("analyses").update(row).eq("id", analysis.id).execute()
        except Exception as exc:  # noqa: BLE001
            if not self._is_missing_column(exc):
                raise
            type(self)._progress_columns_available = False
            for key in ("stages", "events", "completed_at"):
                row.pop(key, None)
            self.client.table("analyses").update(row).eq("id", analysis.id).execute()
        return analysis

    @staticmethod
    def _is_missing_column(exc: Exception) -> bool:
        text = str(exc)
        return "PGRST204" in text or "does not exist" in text or "schema cache" in text

    def update_progress(
        self, analysis_id: str, progress: int, current_stage: str, stages: list, events: list
    ) -> None:
        """Lightweight write used by the live progress tracker at stage boundaries."""
        row: dict = {"progress": progress, "current_stage": current_stage}
        if type(self)._progress_columns_available:
            row["stages"] = stages
            row["events"] = events
        try:
            self.client.table("analyses").update(row).eq("id", analysis_id).execute()
        except Exception as exc:  # noqa: BLE001
            if not self._is_missing_column(exc):
                raise
            type(self)._progress_columns_available = False
            self.client.table("analyses").update(
                {"progress": progress, "current_stage": current_stage}
            ).eq("id", analysis_id).execute()

    def list_analyses(self, limit: int = 50) -> list[dict]:
        """History rows joined with their document filename, for the Analyses view."""
        resp = (
            self.client.table("analyses")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        rows = [
            {k: row.get(k) for k in
             ("id", "document_id", "status", "progress", "current_stage", "created_at",
              "completed_at", "error_message")}
            for row in (resp.data or [])
        ]
        if not rows:
            return []
        doc_ids = list({row["document_id"] for row in rows})
        docs = (
            self.client.table("documents").select("id, filename, file_type").in_("id", doc_ids).execute().data or []
        )
        by_id = {d["id"]: d for d in docs}
        scores = (
            self.client.table("analysis_scores")
            .select("analysis_id, overall_score, risk_level")
            .in_("analysis_id", [r["id"] for r in rows])
            .execute()
            .data
            or []
        )
        score_by_analysis = {s["analysis_id"]: s for s in scores}
        for row in rows:
            doc = by_id.get(row["document_id"], {})
            row["filename"] = doc.get("filename", "Unknown document")
            row["file_type"] = doc.get("file_type", "")
            score = score_by_analysis.get(row["id"])
            row["overall_score"] = score["overall_score"] if score else None
            row["risk_level"] = score["risk_level"] if score else None
        return rows

    def delete_analysis(self, analysis_id: str) -> None:
        """Findings, tests, scores and conflicts are removed by the schema's ON DELETE CASCADE.
        The source document is intentionally kept so it can be re-analyzed."""
        self.client.table("analyses").delete().eq("id", analysis_id).execute()

    # ---- requirements + embeddings ----

    def persist_requirements(self, document_id: str, requirements: list[Requirement]) -> dict[str, str]:
        if not requirements:
            return {}
        rows = [
            {
                "document_id": document_id,
                "requirement_code": req.id,
                "text": req.text,
                "category": req.category,
                "source_text": req.source_text,
                "source_location": req.source_location,
            }
            for req in requirements
        ]
        resp = self.client.table("requirements").insert(rows).execute()
        return {row["requirement_code"]: row["id"] for row in resp.data}

    def persist_requirement_scores(self, requirement_id_map: dict[str, str], quality: list[QualityAnalysis]) -> None:
        for item in quality:
            db_id = requirement_id_map.get(item.requirement_id)
            if not db_id:
                continue
            self.client.table("requirements").update(
                {
                    "clarity_score": item.clarity_score,
                    "completeness_score": item.completeness_score,
                    "testability_score": item.testability_score,
                }
            ).eq("id", db_id).execute()

    def persist_chunks(
        self,
        document_id: str,
        requirement_id_map: dict[str, str],
        requirements: list[Requirement],
        embeddings: list[list[float]],
    ) -> None:
        if not requirements:
            return
        rows = [
            {
                "document_id": document_id,
                "requirement_id": requirement_id_map.get(req.id),
                "chunk_index": index,
                "content": req.text,
                "metadata": {"requirement_code": req.id, "category": req.category},
                "embedding": embedding,
            }
            for index, (req, embedding) in enumerate(zip(requirements, embeddings, strict=True))
        ]
        self.client.table("document_chunks").insert(rows).execute()

    def match_chunks(self, embedding: list[float], document_id: str, match_count: int = 5) -> list[dict]:
        resp = self.client.rpc(
            "match_document_chunks",
            {"query_embedding": embedding, "match_count": match_count, "filter_document_id": document_id},
        ).execute()
        return resp.data or []

    # ---- result persistence ----

    def persist_result(self, analysis_id: str, requirement_id_map: dict[str, str], result: AnalysisResult) -> None:
        self.persist_requirement_scores(requirement_id_map, result.quality)

        quality_rows = [
            {
                "analysis_id": analysis_id,
                "requirement_id": requirement_id_map[item.requirement_id],
                "severity": issue.severity.value,
                "finding_type": issue.type,
                "title": issue.title,
                "description": issue.description,
                "evidence": issue.evidence,
                "recommendation": issue.recommendation,
            }
            for item in result.quality
            for issue in item.issues
            if item.requirement_id in requirement_id_map
        ]
        if quality_rows:
            self.client.table("quality_findings").insert(quality_rows).execute()

        security_rows = [
            {
                "analysis_id": analysis_id,
                "requirement_id": requirement_id_map[finding.requirement_id],
                "severity": finding.severity.value,
                "category": finding.category,
                "description": finding.description,
                "evidence": finding.evidence,
                "recommendation": finding.recommendation,
            }
            for finding in result.security_findings
            if finding.requirement_id in requirement_id_map
        ]
        if security_rows:
            self.client.table("security_findings").insert(security_rows).execute()

        conflict_rows = [
            {
                "analysis_id": analysis_id,
                "requirement_id": requirement_id_map[conflict.requirement_id],
                "related_requirement_id": requirement_id_map[conflict.related_requirement_id],
                "severity": conflict.severity.value,
                "reason": conflict.reason,
                "evidence": conflict.evidence,
            }
            for conflict in result.conflicts
            if conflict.requirement_id in requirement_id_map and conflict.related_requirement_id in requirement_id_map
        ]
        if conflict_rows:
            self.client.table("requirement_conflicts").insert(conflict_rows).execute()

        edge_case_rows = [
            {
                "analysis_id": analysis_id,
                "requirement_id": requirement_id_map[edge_case.requirement_id],
                "title": edge_case.title,
                "scenario": edge_case.scenario,
                "expected_behavior": edge_case.expected_behavior,
                "priority": edge_case.priority,
            }
            for edge_case in result.edge_cases
            if edge_case.requirement_id in requirement_id_map
        ]
        if edge_case_rows:
            self.client.table("edge_cases").insert(edge_case_rows).execute()

        test_rows = [
            {
                "analysis_id": analysis_id,
                "requirement_id": requirement_id_map[test.requirement_id],
                "test_code": test.id,
                "title": test.title,
                "preconditions": test.preconditions,
                "steps": test.steps,
                "expected_result": test.expected_result,
                "priority": test.priority,
                "category": test.category,
            }
            for test in result.test_cases
            if test.requirement_id in requirement_id_map
        ]
        if test_rows:
            self.client.table("test_cases").insert(test_rows).execute()

        improved_rows = [
            {
                "analysis_id": analysis_id,
                "requirement_id": requirement_id_map[improved.requirement_id],
                "original_text": improved.original_text,
                "improved_text": improved.improved_text,
                "rationale": improved.rationale,
                "remaining_questions": improved.remaining_questions,
            }
            for improved in result.improved_requirements
            if improved.requirement_id in requirement_id_map
        ]
        if improved_rows:
            self.client.table("improved_requirements").insert(improved_rows).execute()

        if result.score:
            self.client.table("analysis_scores").insert(
                {
                    "analysis_id": analysis_id,
                    "quality_score": result.score.quality_score,
                    "security_score": result.score.security_score,
                    "testability_score": result.score.testability_score,
                    "overall_score": result.score.overall_score,
                    "risk_level": result.score.risk_level,
                }
            ).execute()

    def load_result(self, analysis_id: str) -> AnalysisResult | None:
        score_resp = (
            self.client.table("analysis_scores").select("*").eq("analysis_id", analysis_id).limit(1).execute()
        )
        if not score_resp.data:
            return None
        score_row = score_resp.data[0]

        # Fetch this analysis's requirements via its parent document in one query. Fanning out
        # across every findings table to collect requirement ids instead costs seven round trips
        # and misses requirements that produced no findings at all.
        analysis_resp = (
            self.client.table("analyses").select("document_id").eq("id", analysis_id).limit(1).execute()
        )
        if not analysis_resp.data:
            return None
        req_resp = (
            self.client.table("requirements")
            .select("*")
            .eq("document_id", analysis_resp.data[0]["document_id"])
            .execute()
        )
        req_by_db_id = {row["id"]: row for row in req_resp.data}
        code_by_db_id = {db_id: row["requirement_code"] for db_id, row in req_by_db_id.items()}

        requirements = [
            Requirement(
                id=row["requirement_code"],
                text=row["text"],
                category=row["category"],
                source_text=row.get("source_text"),
                source_location=row.get("source_location"),
            )
            for row in req_by_db_id.values()
        ]

        quality = self._load_quality(analysis_id, req_by_db_id, code_by_db_id)
        security_findings = self._load_security(analysis_id, code_by_db_id)
        conflicts = self._load_conflicts(analysis_id, code_by_db_id)
        edge_cases = self._load_edge_cases(analysis_id, code_by_db_id)
        test_cases = self._load_test_cases(analysis_id, code_by_db_id)
        improved_requirements = self._load_improved(analysis_id, code_by_db_id)

        return AnalysisResult(
            requirements=requirements,
            quality=quality,
            security_findings=security_findings,
            conflicts=conflicts,
            edge_cases=edge_cases,
            test_cases=test_cases,
            improved_requirements=improved_requirements,
            score=AnalysisScore(
                quality_score=score_row["quality_score"],
                security_score=score_row["security_score"],
                testability_score=score_row["testability_score"],
                overall_score=score_row["overall_score"],
                risk_level=score_row["risk_level"],
            ),
        )


    def _load_quality(
        self, analysis_id: str, req_by_db_id: dict[str, dict], code_by_db_id: dict[str, str]
    ) -> list[QualityAnalysis]:
        resp = self.client.table("quality_findings").select("*").eq("analysis_id", analysis_id).execute()
        issues_by_requirement: dict[str, list[RequirementIssue]] = {}
        for row in resp.data:
            code = code_by_db_id.get(row["requirement_id"])
            if not code:
                continue
            issues_by_requirement.setdefault(code, []).append(
                RequirementIssue(
                    severity=Severity(row["severity"]),
                    type=row["finding_type"],
                    title=row["title"],
                    description=row["description"],
                    evidence=row["evidence"],
                    recommendation=row["recommendation"],
                )
            )
        return [
            QualityAnalysis(
                requirement_id=code,
                clarity_score=row.get("clarity_score") or 0,
                completeness_score=row.get("completeness_score") or 0,
                testability_score=row.get("testability_score") or 0,
                issues=issues_by_requirement.get(code, []),
            )
            for db_id, row in req_by_db_id.items()
            for code in [code_by_db_id[db_id]]
        ]

    def _load_security(self, analysis_id: str, code_by_db_id: dict[str, str]) -> list[SecurityFinding]:
        resp = self.client.table("security_findings").select("*").eq("analysis_id", analysis_id).execute()
        return [
            SecurityFinding(
                requirement_id=code_by_db_id[row["requirement_id"]],
                severity=Severity(row["severity"]),
                category=row["category"],
                description=row["description"],
                evidence=row["evidence"],
                recommendation=row["recommendation"],
            )
            for row in resp.data
            if row["requirement_id"] in code_by_db_id
        ]

    def _load_conflicts(self, analysis_id: str, code_by_db_id: dict[str, str]) -> list[RequirementConflict]:
        resp = self.client.table("requirement_conflicts").select("*").eq("analysis_id", analysis_id).execute()
        return [
            RequirementConflict(
                requirement_id=code_by_db_id[row["requirement_id"]],
                related_requirement_id=code_by_db_id[row["related_requirement_id"]],
                reason=row["reason"],
                evidence=row["evidence"],
                severity=Severity(row["severity"]),
            )
            for row in resp.data
            if row["requirement_id"] in code_by_db_id and row["related_requirement_id"] in code_by_db_id
        ]

    def _load_edge_cases(self, analysis_id: str, code_by_db_id: dict[str, str]) -> list[EdgeCase]:
        resp = self.client.table("edge_cases").select("*").eq("analysis_id", analysis_id).execute()
        return [
            EdgeCase(
                requirement_id=code_by_db_id[row["requirement_id"]],
                title=row["title"],
                scenario=row["scenario"],
                expected_behavior=row["expected_behavior"],
                priority=row["priority"],
            )
            for row in resp.data
            if row["requirement_id"] in code_by_db_id
        ]

    def _load_test_cases(self, analysis_id: str, code_by_db_id: dict[str, str]) -> list[TestCase]:
        resp = self.client.table("test_cases").select("*").eq("analysis_id", analysis_id).execute()
        return [
            TestCase(
                id=row["test_code"],
                requirement_id=code_by_db_id[row["requirement_id"]],
                title=row["title"],
                preconditions=row["preconditions"],
                steps=row["steps"],
                expected_result=row["expected_result"],
                priority=row["priority"],
                category=row["category"],
            )
            for row in resp.data
            if row["requirement_id"] in code_by_db_id
        ]

    def _load_improved(self, analysis_id: str, code_by_db_id: dict[str, str]) -> list[ImprovedRequirement]:
        resp = self.client.table("improved_requirements").select("*").eq("analysis_id", analysis_id).execute()
        return [
            ImprovedRequirement(
                requirement_id=code_by_db_id[row["requirement_id"]],
                original_text=row["original_text"],
                improved_text=row["improved_text"],
                rationale=row["rationale"],
                remaining_questions=row.get("remaining_questions") or [],
            )
            for row in resp.data
            if row["requirement_id"] in code_by_db_id
        ]


repository = SupabaseRepository()
