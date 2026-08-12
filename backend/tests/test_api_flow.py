from fastapi.testclient import TestClient

from backend.app.api import routes as routes_module
from backend.app.main import app
from backend.app.models import AnalysisRecord, DocumentRecord


class FakeRepository:
    """In-memory stand-in for SupabaseRepository, used to test the API/workflow wiring
    without depending on a live database or network access."""

    def __init__(self) -> None:
        self.documents: dict[str, DocumentRecord] = {}
        self.analyses: dict[str, AnalysisRecord] = {}
        self.results: dict[str, object] = {}

    def add_document(self, document: DocumentRecord) -> DocumentRecord:
        self.documents[document.id] = document
        return document

    def get_document(self, document_id: str) -> DocumentRecord | None:
        return self.documents.get(document_id)

    def update_document(self, document: DocumentRecord) -> DocumentRecord:
        self.documents[document.id] = document
        return document

    def add_analysis(self, analysis: AnalysisRecord) -> AnalysisRecord:
        self.analyses[analysis.id] = analysis
        return analysis

    def get_analysis(self, analysis_id: str, *, include_result: bool = True) -> AnalysisRecord | None:
        analysis = self.analyses.get(analysis_id)
        if analysis and include_result and analysis_id in self.results:
            return analysis.model_copy(update={"result": self.results[analysis_id]})
        return analysis

    def update_analysis(self, analysis: AnalysisRecord) -> AnalysisRecord:
        self.analyses[analysis.id] = analysis
        return analysis

    def persist_requirements(self, document_id, requirements):
        return {req.id: f"fake-uuid-{req.id}" for req in requirements}

    def persist_chunks(self, document_id, requirement_id_map, requirements, embeddings):
        return None

    def match_chunks(self, embedding, document_id, match_count=5):
        return []

    def persist_result(self, analysis_id, requirement_id_map, result):
        self.results[analysis_id] = result


def test_full_upload_analyze_results_flow(monkeypatch):
    fake_repo = FakeRepository()
    monkeypatch.setattr(routes_module, "repository", fake_repo)

    client = TestClient(app)
    spec_text = (
        "Users can cancel an order at any time. "
        "Orders cannot be cancelled after payment. "
        "The system should respond quickly to user requests.\n"
    )

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("spec.txt", spec_text.encode("utf-8"), "text/plain")},
    )
    assert upload_response.status_code == 201
    upload_data = upload_response.json()["data"]
    document_id = upload_data["document_id"]
    assert upload_data["status"] == "uploaded"

    start_response = client.post("/api/v1/analyses", json={"document_id": document_id})
    assert start_response.status_code == 202
    analysis_id = start_response.json()["data"]["analysis_id"]

    status_response = client.get(f"/api/v1/analyses/{analysis_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()["data"]
    assert status_data["status"] == "completed"
    assert status_data["progress"] == 100

    results_response = client.get(f"/api/v1/analyses/{analysis_id}/results")
    assert results_response.status_code == 200
    result_data = results_response.json()["data"]

    assert len(result_data["requirements"]) >= 3
    assert result_data["score"]["overall_score"] > 0
    assert any(item["issues"] for item in result_data["quality"])

    document = fake_repo.get_document(document_id)
    assert document is not None
    from pathlib import Path

    Path(document.storage_path).unlink(missing_ok=True)


def test_results_not_ready_before_completion(monkeypatch):
    fake_repo = FakeRepository()
    monkeypatch.setattr(routes_module, "repository", fake_repo)

    client = TestClient(app)
    fake_id = "does-not-exist"
    response = client.get(f"/api/v1/analyses/{fake_id}/results")
    assert response.status_code == 404
