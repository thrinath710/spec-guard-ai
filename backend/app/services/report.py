"""Markdown report generation.

Markdown rather than a rendered PDF: it needs no rendering engine or extra dependency, is
readable in any editor, pastes into issue trackers, and the browser's own print-to-PDF covers
the cases where a PDF is genuinely wanted.
"""

from collections import Counter, defaultdict

from backend.app.models import AnalysisResult

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _by_severity(items, key=lambda item: item.severity.value):
    return sorted(items, key=lambda item: SEVERITY_ORDER.get(key(item), 9))


def build_markdown_report(
    result: AnalysisResult, filename: str, generated_at: str | None = None
) -> str:
    score = result.score
    issues = [issue for item in result.quality for issue in item.issues]
    lines: list[str] = []

    lines.append(f"# SpecGuard AI — Analysis Report")
    lines.append("")
    lines.append(f"**Document:** {filename}")
    if generated_at:
        lines.append(f"**Generated:** {generated_at}")
    lines.append("")

    if result.degraded:
        lines.append(
            f"> **Partial AI analysis.** {result.degraded_reason or ''} "
            "Sections produced by the rule-based fallback are less specific than a full run."
        )
        lines.append("")

    # ---- summary ----
    lines.append("## Summary")
    lines.append("")
    if score:
        lines.append(f"| Metric | Score |")
        lines.append("| --- | --- |")
        lines.append(f"| Overall | **{score.overall_score}/100** |")
        lines.append(f"| Quality | {score.quality_score}/100 |")
        lines.append(f"| Security | {score.security_score}/100 |")
        lines.append(f"| Testability | {score.testability_score}/100 |")
        lines.append(f"| Risk level | **{score.risk_level.upper()}** |")
        lines.append("")

    lines.append(f"- Requirements analyzed: **{len(result.requirements)}**")
    lines.append(f"- Quality issues: **{len(issues)}**")
    lines.append(f"- Security findings: **{len(result.security_findings)}**")
    lines.append(f"- Contradictions: **{len(result.conflicts)}**")
    lines.append(f"- Edge cases: **{len(result.edge_cases)}**")
    lines.append(f"- Test cases generated: **{len(result.test_cases)}**")
    lines.append("")

    # ---- contradictions first: they block development ----
    if result.conflicts:
        lines.append("## Contradictions")
        lines.append("")
        for conflict in _by_severity(result.conflicts):
            lines.append(
                f"### {conflict.requirement_id} ↔ {conflict.related_requirement_id} "
                f"({conflict.severity.value})"
            )
            lines.append("")
            lines.append(conflict.reason)
            if conflict.evidence:
                lines.append("")
                lines.append(f"> {conflict.evidence}")
            lines.append("")

    # ---- security ----
    if result.security_findings:
        lines.append("## Security Findings")
        lines.append("")
        counts = Counter(f.severity.value for f in result.security_findings)
        lines.append(
            " · ".join(
                f"**{level}**: {counts[level]}"
                for level in ("critical", "high", "medium", "low")
                if counts.get(level)
            )
        )
        lines.append("")
        for finding in _by_severity(result.security_findings):
            lines.append(
                f"### [{finding.severity.value.upper()}] {finding.category} — {finding.requirement_id}"
            )
            lines.append("")
            lines.append(finding.description)
            if finding.evidence:
                lines.append("")
                lines.append(f"> {finding.evidence}")
            if finding.recommendation:
                lines.append("")
                lines.append(f"**Recommendation:** {finding.recommendation}")
            lines.append("")

    # ---- requirements, each with everything traced to it ----
    lines.append("## Requirements")
    lines.append("")
    quality_by_id = {item.requirement_id: item for item in result.quality}
    improved_by_id = {item.requirement_id: item for item in result.improved_requirements}
    edges_by_id: dict[str, list] = defaultdict(list)
    for edge in result.edge_cases:
        edges_by_id[edge.requirement_id].append(edge)
    tests_by_id: dict[str, list] = defaultdict(list)
    for test in result.test_cases:
        tests_by_id[test.requirement_id].append(test)

    for requirement in result.requirements:
        lines.append(f"### {requirement.id} — {requirement.category}")
        lines.append("")
        lines.append(f"> {requirement.text}")
        lines.append("")

        quality = quality_by_id.get(requirement.id)
        if quality:
            lines.append(
                f"Clarity {quality.clarity_score} · "
                f"Completeness {quality.completeness_score} · "
                f"Testability {quality.testability_score}"
            )
            lines.append("")
            for issue in _by_severity(quality.issues):
                lines.append(f"- **[{issue.severity.value}] {issue.title}** — {issue.description}")
                if issue.recommendation:
                    lines.append(f"  - *Fix:* {issue.recommendation}")
            if quality.issues:
                lines.append("")

        for edge in edges_by_id.get(requirement.id, []):
            lines.append(f"- *Edge case:* **{edge.title}** — {edge.scenario} "
                         f"Expected: {edge.expected_behavior}")
        if edges_by_id.get(requirement.id):
            lines.append("")

        improved = improved_by_id.get(requirement.id)
        if improved:
            lines.append("**Improved requirement**")
            lines.append("")
            lines.append(f"> {improved.improved_text}")
            if improved.remaining_questions:
                lines.append("")
                lines.append("Open questions:")
                for question in improved.remaining_questions:
                    lines.append(f"- {question}")
            lines.append("")

    # ---- tests ----
    if result.test_cases:
        lines.append("## Generated Test Cases")
        lines.append("")
        for test in result.test_cases:
            lines.append(f"### {test.id} — {test.title}")
            lines.append("")
            lines.append(
                f"`{test.requirement_id}` · {test.category} · priority {test.priority}"
            )
            lines.append("")
            if test.preconditions:
                lines.append(f"**Given:** {'; '.join(test.preconditions)}")
                lines.append("")
            if test.steps:
                for index, step in enumerate(test.steps, start=1):
                    lines.append(f"{index}. {step}")
                lines.append("")
            lines.append(f"**Expected:** {test.expected_result}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by SpecGuard AI.*")
    return "\n".join(lines)
