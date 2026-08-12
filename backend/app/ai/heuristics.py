import re
from collections import Counter

from backend.app.models import (
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

AMBIGUOUS_TERMS = {
    "quickly": "Define a measurable response time.",
    "fast": "Define a measurable performance target.",
    "secure": "Name the required security controls.",
    "user-friendly": "Define usability acceptance criteria.",
    "easy": "Define observable usability criteria.",
    "reasonable": "Define the exact threshold or policy.",
    "appropriate": "Define the exact standard or decision rule.",
    "large": "Specify a size limit.",
    "small": "Specify a size limit.",
    "many": "Specify a numeric limit.",
}

CATEGORY_KEYWORDS = {
    "Authentication": ["login", "register", "password", "verify", "session", "mfa"],
    "Authorization": ["permission", "role", "admin", "access", "owner"],
    "File Management": ["upload", "file", "document", "image", "attachment"],
    "Payment": ["payment", "refund", "invoice", "checkout"],
    "Order Management": ["order", "cart", "cancel", "shipping"],
    "Notifications": ["email", "sms", "notification", "alert"],
    "Performance": ["latency", "response", "load", "throughput", "performance"],
    "Security": ["encrypt", "security", "audit", "rate limit", "token"],
    "Administration": ["admin", "moderator", "manage"],
}

SECURITY_HINTS = {
    "upload": [
        ("File security", "Allowed file types, size limits, and malware scanning are not defined."),
        ("Authorization", "Ownership rules for uploaded files are not defined."),
    ],
    "password": [
        ("Authentication", "Password complexity, reset, and storage requirements are not defined."),
    ],
    "login": [
        ("Authentication", "Rate limiting and session behavior are not defined."),
    ],
    "payment": [
        ("Data protection", "Sensitive payment handling and audit requirements are not defined."),
    ],
    "admin": [
        ("Authorization", "Administrative role boundaries and audit logging are not defined."),
    ],
    "personal": [
        ("Data protection", "Sensitive data retention, encryption, and access controls are not defined."),
    ],
}


def extract_requirements(text: str) -> list[Requirement]:
    candidates: list[str] = []
    for line in text.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)]|REQ-\d+:?)\s*", "", line).strip()
        if cleaned.endswith(":"):
            continue
        if _looks_like_requirement(cleaned):
            sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
            if len(sentences) > 1:
                candidates.extend(sentence for sentence in sentences if _looks_like_requirement(sentence))
            else:
                candidates.append(cleaned)

    if not candidates:
        for sentence in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text.strip())):
            sentence = sentence.strip()
            if _looks_like_requirement(sentence):
                candidates.append(sentence)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.lower()
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(candidate.rstrip(".") + ".")

    return [
        Requirement(
            id=f"REQ-{index:03d}",
            text=requirement,
            category=categorize(requirement),
            source_text=requirement,
            source_location=f"extracted item {index}",
        )
        for index, requirement in enumerate(deduped[:80], start=1)
    ]


def _looks_like_requirement(text: str) -> bool:
    if len(text) < 12:
        return False
    lowered = text.lower()
    signals = [
        r"\bshall\b",
        r"\bshould\b",
        r"\bmust\b",
        r"\bcan\b",
        r"\bcannot\b",
        r"\bcan\s*not\b",
        r"\ballow\b",
        r"\ballows\b",
        r"\benable\b",
        r"\benables\b",
        r"\bprovide\b",
        r"\bsupport\b",
        r"\bdisplay\b",
        r"\bgenerate\b",
        r"\bvalidate\b",
        r"\bstore\b",
        r"\busers?\b",
        r"\bsystem\b",
        r"\bapplication\b",
    ]
    return any(re.search(signal, lowered) for signal in signals)


def categorize(text: str) -> str:
    lowered = text.lower()
    scores = {
        category: sum(1 for keyword in keywords if keyword in lowered)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    category, score = max(scores.items(), key=lambda item: item[1])
    return category if score else "Other"


def retrieve_related(requirement: Requirement, requirements: list[Requirement], limit: int = 4) -> list[Requirement]:
    target_tokens = _tokens(requirement.text)
    scored: list[tuple[int, Requirement]] = []
    for candidate in requirements:
        if candidate.id == requirement.id:
            continue
        overlap = len(target_tokens & _tokens(candidate.text))
        if overlap:
            scored.append((overlap, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in scored[:limit]]


def analyze_quality(requirement: Requirement) -> QualityAnalysis:
    issues: list[RequirementIssue] = []
    lowered = requirement.text.lower()

    for term, recommendation in AMBIGUOUS_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            issues.append(
                RequirementIssue(
                    severity=Severity.medium,
                    type="ambiguity",
                    title=f"Ambiguous term: {term}",
                    description=f'"{term}" cannot be verified objectively without a measurable criterion.',
                    evidence=requirement.text,
                    recommendation=recommendation,
                )
            )

    if not re.search(r"\b(within|at least|no more than|maximum|minimum|\d+|when|if|unless)\b", lowered):
        issues.append(
            RequirementIssue(
                severity=Severity.medium,
                type="testability",
                title="Acceptance criteria are missing",
                description="The requirement does not define measurable constraints or observable completion criteria.",
                evidence=requirement.text,
                recommendation="Add conditions, limits, expected outcomes, and failure behavior.",
            )
        )

    if requirement.category == "File Management" and not re.search(r"\b(type|size|format|dimension|scan|virus|malware)\b", lowered):
        issues.append(
            RequirementIssue(
                severity=Severity.high,
                type="completeness",
                title="File constraints are missing",
                description="File-related requirements need allowed formats, size limits, validation, and failure behavior.",
                evidence=requirement.text,
                recommendation="Specify permitted file types, max size, validation rules, storage behavior, and errors.",
            )
        )

    penalty = len(issues) * 12
    clarity = max(30, 92 - penalty)
    completeness = max(25, 88 - penalty - (10 if "missing" in lowered else 0))
    testability = max(25, 90 - penalty - (12 if not re.search(r"\d+|when|if|within|maximum|minimum", lowered) else 0))
    return QualityAnalysis(
        requirement_id=requirement.id,
        clarity_score=clarity,
        completeness_score=completeness,
        testability_score=testability,
        issues=issues,
    )


def analyze_security(requirement: Requirement) -> list[SecurityFinding]:
    lowered = requirement.text.lower()
    findings: list[SecurityFinding] = []
    for keyword, checks in SECURITY_HINTS.items():
        if keyword in lowered:
            for category, description in checks:
                findings.append(
                    SecurityFinding(
                        requirement_id=requirement.id,
                        severity=Severity.high if keyword in {"upload", "payment", "admin"} else Severity.medium,
                        category=category,
                        description=description,
                        evidence=requirement.text,
                        recommendation="Add explicit security controls and acceptance criteria for this behavior.",
                    )
                )
    return findings


def analyze_consistency(requirement: Requirement, related: list[Requirement]) -> list[RequirementConflict]:
    conflicts: list[RequirementConflict] = []
    lowered = requirement.text.lower()
    for other in related:
        other_lowered = other.text.lower()
        if (" at any time" in lowered and "cannot" in other_lowered) or (
            "cannot" in lowered and " at any time" in other_lowered
        ):
            conflicts.append(
                RequirementConflict(
                    requirement_id=requirement.id,
                    related_requirement_id=other.id,
                    reason="One requirement permits the action broadly while a related requirement restricts it.",
                    evidence=f"{requirement.text} / {other.text}",
                    severity=Severity.high,
                )
            )

        numbers = re.findall(r"\b\d+\s*(?:mb|gb|seconds?|minutes?|hours?|days?)\b", lowered)
        other_numbers = re.findall(r"\b\d+\s*(?:mb|gb|seconds?|minutes?|hours?|days?)\b", other_lowered)
        if numbers and other_numbers and set(numbers).isdisjoint(other_numbers):
            conflicts.append(
                RequirementConflict(
                    requirement_id=requirement.id,
                    related_requirement_id=other.id,
                    reason="Related requirements appear to specify different numeric constraints.",
                    evidence=f"{', '.join(numbers)} vs {', '.join(other_numbers)}",
                )
            )
    return conflicts


def generate_edge_cases(requirement: Requirement) -> list[EdgeCase]:
    lowered = requirement.text.lower()
    cases = [
        EdgeCase(
            requirement_id=requirement.id,
            title="Unauthorized actor attempts the action",
            scenario="A user without the required permissions attempts to perform the requirement behavior.",
            expected_behavior="The system rejects the action and records an appropriate error.",
            priority="high",
        )
    ]
    if "upload" in lowered or "file" in lowered:
        cases.extend(
            [
                EdgeCase(
                    requirement_id=requirement.id,
                    title="Invalid file is submitted",
                    scenario="The user uploads an unsupported, corrupted, or spoofed file.",
                    expected_behavior="The system rejects the file with a clear validation error.",
                    priority="high",
                ),
                EdgeCase(
                    requirement_id=requirement.id,
                    title="Storage failure occurs",
                    scenario="File storage is unavailable during upload.",
                    expected_behavior="The system fails gracefully without losing traceability.",
                ),
            ]
        )
    if "payment" in lowered:
        cases.append(
            EdgeCase(
                requirement_id=requirement.id,
                title="Payment provider timeout",
                scenario="The payment provider does not respond before the timeout.",
                expected_behavior="The system marks the transaction as pending or failed according to policy.",
                priority="high",
            )
        )
    return cases[:4]


def generate_tests(requirement: Requirement, edge_cases: list[EdgeCase]) -> list[TestCase]:
    base = TestCase(
        id=f"TC-{requirement.id.removeprefix('REQ-')}-001",
        requirement_id=requirement.id,
        title=f"Verify {requirement.id} expected behavior",
        preconditions=["The system is available.", "A valid user context exists when authentication is required."],
        steps=["Perform the behavior described by the requirement.", "Observe the system response."],
        expected_result="The system completes the behavior and returns the documented result.",
        priority="medium",
        category="positive",
    )
    tests = [base]
    for index, edge_case in enumerate(edge_cases[:2], start=2):
        tests.append(
            TestCase(
                id=f"TC-{requirement.id.removeprefix('REQ-')}-{index:03d}",
                requirement_id=requirement.id,
                title=edge_case.title,
                preconditions=["The system is available."],
                steps=[edge_case.scenario],
                expected_result=edge_case.expected_behavior,
                priority=edge_case.priority,
                category="edge",
            )
        )
    return tests


def improve_requirement(requirement: Requirement, quality: QualityAnalysis, security: list[SecurityFinding]) -> ImprovedRequirement:
    additions: list[str] = []
    if quality.issues:
        additions.append("Define measurable acceptance criteria, validation rules, and expected failure behavior")
    if security:
        additions.append("include authentication, authorization, input validation, logging, and rate limiting where relevant")
    if not additions:
        additions.append("preserve the current behavior with explicit success and failure outcomes")

    improved = f"{requirement.text.rstrip('.')} The system shall {', and '.join(additions).removeprefix('Define').strip()}."
    return ImprovedRequirement(
        requirement_id=requirement.id,
        original_text=requirement.text,
        improved_text=improved,
        rationale="The rewrite keeps the original intent while adding testable and security-aware constraints.",
    )


def score_risk(severities: list[Severity]) -> str:
    counts = Counter(severities)
    if counts[Severity.critical] or counts[Severity.high] >= 3:
        return "high"
    if counts[Severity.high] or counts[Severity.medium] >= 3:
        return "medium"
    return "low"


def _stem(token: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "and", "or", "to", "of", "in", "for", "with", "can", "shall", "should", "must"}
    return {_stem(token) for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in stop}
