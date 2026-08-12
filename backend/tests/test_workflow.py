from backend.app.ai.workflow import run_analysis


def test_workflow_detects_requirement_issues() -> None:
    text = "Users can upload profile images. The system should respond quickly."
    result = run_analysis(text, [text])

    assert len(result.requirements) == 2
    assert result.score is not None
    assert result.score.overall_score > 0
    assert any(item.issues for item in result.quality)
    assert any(finding.category == "File security" for finding in result.security_findings)
