# SpecGuard AI — Functional and Non-Functional Requirements

## 1. Purpose

This document defines the functional and non-functional requirements of SpecGuard AI.

Functional requirements describe what the system must do.

Non-functional requirements describe how the system should behave in terms of performance, reliability, security, maintainability, and usability.

---

# 2. Functional Requirements

## FR-001 — Document Upload

The system shall allow users to upload software requirement documents for analysis.

Supported document formats:

- PDF
- DOCX
- TXT
- Markdown

The system shall generate a unique document ID for every successfully uploaded document.

---

## FR-002 — Document Validation

The system shall validate every uploaded document before processing.

The validation shall check:

- File extension
- MIME type
- File size
- File readability
- Supported document format

The system shall reject unsupported, corrupted, or invalid documents.

---

## FR-003 — Document Text Extraction

The system shall extract readable text from uploaded documents.

The extraction process shall support:

- PDF documents
- DOCX documents
- TXT documents
- Markdown documents

The extracted text shall be passed to the requirement extraction pipeline.

---

## FR-004 — Requirement Extraction

The system shall identify individual software requirements from the extracted document.

Each extracted requirement shall contain:

- Unique requirement ID
- Requirement text
- Category
- Source text
- Source location where available

Example:

REQ-001

"Users can upload profile images."

---

## FR-005 — Requirement Categorization

The system shall classify extracted requirements into relevant categories where possible.

Possible categories include:

- Authentication
- Authorization
- User Management
- File Management
- Payment
- Order Management
- Data Management
- Notifications
- Performance
- Security
- Administration
- Other

The system shall allow a requirement to be classified as "Other" when no suitable category is identified.

---

## FR-006 — Document Chunking

The system shall divide extracted document content into smaller chunks before generating embeddings.

The chunking process should attempt to preserve meaningful requirement boundaries.

The system should avoid unnecessarily splitting a single requirement across multiple unrelated chunks.

---

## FR-007 — Embedding Generation

The system shall generate vector embeddings for document chunks or extracted requirements.

These embeddings shall be used for semantic similarity search.

---

## FR-008 — Vector Storage

The system shall store generated embeddings in a vector-enabled PostgreSQL database using Supabase pgvector.

Each stored vector should maintain a reference to:

- Document
- Requirement where applicable
- Original text
- Metadata

---

## FR-009 — Related Requirement Retrieval

The system shall retrieve semantically related requirements when analyzing a requirement.

The retrieval process shall provide relevant project-specific context to the AI analysis nodes.

The system should not send the entire document to every AI analysis request when relevant context can be retrieved using RAG.

---

## FR-010 — Ambiguity Detection

The system shall identify ambiguous or subjective language in requirements.

Examples include:

- Quickly
- Easily
- Fast
- Secure
- Reasonable
- Appropriate
- User-friendly
- Many
- Large
- Small

The system shall explain why the identified language is ambiguous.

Example:

Requirement:

"The system should respond quickly."

Finding:

"Quickly" does not define an objectively measurable response time.

---

## FR-011 — Completeness Analysis

The system shall identify important information missing from a requirement.

For example, for:

"Users can upload documents."

The system may identify missing information such as:

- Allowed file types
- Maximum file size
- Authentication requirements
- Authorization rules
- Storage behavior
- Failure behavior

The system shall distinguish between genuinely missing information and information that is not relevant to the requirement.

---

## FR-012 — Clarity Analysis

The system shall evaluate whether a requirement clearly communicates the intended behavior.

The system shall identify:

- Unclear statements
- Vague terminology
- Confusing wording
- Undefined actors
- Undefined actions
- Undefined outcomes

---

## FR-013 — Testability Analysis

The system shall determine whether a requirement can be objectively tested.

A requirement should ideally define observable behavior and measurable outcomes.

Example of a weak requirement:

"The application should load quickly."

Example of a more testable requirement:

"The application shall display the dashboard within 2 seconds under normal operating conditions."

---

## FR-014 — Security Analysis

The system shall analyze requirements for relevant security considerations.

The analysis may consider:

- Authentication
- Authorization
- Access control
- Input validation
- Output validation
- File validation
- Data protection
- Sensitive information
- Rate limiting
- Session management
- Security logging
- Resource access
- Ownership verification

The system shall only report security findings that are relevant to the analyzed requirement.

---

## FR-015 — Security Risk Classification

The system shall classify security findings using the following severity levels:

- Low
- Medium
- High
- Critical

Each security finding shall contain:

- Severity
- Security category
- Description
- Evidence
- Recommendation
- Related requirement

---

## FR-016 — Consistency Analysis

The system shall compare a requirement against relevant retrieved requirements.

The system shall identify:

- Direct contradictions
- Conflicting constraints
- Conflicting permissions
- Conflicting business rules
- Conflicting limits
- Potential semantic inconsistencies

Example:

REQ-007:

"Users can cancel an order at any time."

REQ-015:

"Orders cannot be cancelled after payment."

The system shall identify this as a potential conflict.

---

## FR-017 — Conflict Evidence

Every detected conflict shall reference the requirements involved.

A conflict result shall contain:

- Requirement A
- Requirement B
- Conflict description
- Evidence
- Severity
- Resolution status

---

## FR-018 — Edge Case Generation

The system shall identify relevant edge cases that are not explicitly addressed by a requirement.

The system may consider:

- Empty input
- Invalid input
- Boundary values
- Duplicate operations
- Missing data
- Unauthorized actions
- Failed operations
- Network failures
- External service failures
- Concurrent operations
- Security abuse cases

The system shall avoid generating irrelevant edge cases.

---

## FR-019 — Test Case Generation

The system shall generate structured test cases from requirements and detected issues.

Test cases shall include:

- Test ID
- Requirement ID
- Title
- Category
- Priority
- Preconditions
- Steps
- Expected result

---

## FR-020 — Test Case Categories

Generated test cases shall be categorized as:

- Positive
- Negative
- Edge
- Security

Example:

Requirement:

"Users can upload profile images."

Generated tests may include:

Positive:

Upload a valid JPEG image.

Negative:

Upload an unsupported file format.

Edge:

Upload an image exactly at the maximum file size.

Security:

Attempt to access another user's uploaded image.

---

## FR-021 — Test Case Priority

Test cases shall have a priority:

- Low
- Medium
- High
- Critical

Security-related failures and major business-rule violations should receive higher priority where appropriate.

---

## FR-022 — Requirement Improvement

The system shall generate an improved version of weak requirements.

The improved requirement should:

- Preserve the original business intent
- Remove ambiguity
- Add important missing constraints
- Improve testability
- Include relevant security considerations
- Clearly define expected behavior

The system shall not invent unsupported business rules.

---

## FR-023 — Clarification Questions

When important information is genuinely unknown, the system should generate clarification questions instead of inventing an answer.

Example:

Requirement:

"Users can cancel orders."

Clarification:

"Should users be allowed to cancel an order after payment has been completed?"

---

## FR-024 — Evidence Generation

Every important issue should contain evidence from the original requirement or related requirements.

Example:

Issue:

Authorization rule missing.

Evidence:

"Users can download documents."

Explanation:

"The requirement does not specify whether users may download documents belonging to other users."

---

## FR-025 — Requirement-Level Scoring

The system shall calculate scores for individual requirements.

The scores shall include:

- Clarity
- Completeness
- Testability
- Security
- Consistency

Each score shall use a 0-100 scale.

---

## FR-026 — Overall Specification Score

The system shall calculate an overall specification score using predefined weights.

The score shall be calculated by backend logic.

The LLM shall not directly determine the final score.

Formula:

Overall Score =
(Completeness × 0.30)
+
(Testability × 0.25)
+
(Security × 0.20)
+
(Clarity × 0.15)
+
(Consistency × 0.10)

---

## FR-027 — Score Classification

The system shall classify the overall score as:

90-100:

Excellent

75-89:

Good

60-74:

Needs Improvement

40-59:

High Risk

0-39:

Critical

---

## FR-028 — Analysis Workflow

The system shall execute the analysis workflow in the following general sequence:

Document

↓

Text Extraction

↓

Requirement Extraction

↓

Chunking

↓

Embedding

↓

Vector Storage

↓

Related Requirement Retrieval

↓

Quality Analysis

↓

Security Analysis

↓

Consistency Analysis

↓

Edge Case Analysis

↓

Test Generation

↓

Requirement Improvement

↓

Scoring

↓

Final Results

---

## FR-029 — Analysis Status

The system shall provide the current status of an analysis.

Possible states:

- Queued
- Processing
- Completed
- Failed

The system should provide the current processing stage where possible.

---

## FR-030 — Analysis Results

The system shall provide a structured analysis result containing:

- Overall score
- Category scores
- Requirement statistics
- Quality issues
- Security findings
- Conflicts
- Edge cases
- Generated test cases
- Improved requirements

---

## FR-031 — Dashboard

The frontend shall display an analysis dashboard.

The dashboard should display:

- Overall score
- Quality category scores
- Issue counts
- Security risk
- Number of requirements
- Number of test cases
- Number of conflicts
- Number of edge cases

---

## FR-032 — Requirement Explorer

The frontend shall allow users to inspect individual requirements.

The requirement view should display:

- Requirement text
- Requirement category
- Score
- Quality issues
- Security findings
- Evidence
- Edge cases
- Related requirements
- Improved requirement
- Generated test cases

---

## FR-033 — Issue Filtering

The frontend should allow users to filter issues by:

- Severity
- Category
- Requirement
- Issue type

Possible severity filters:

- Critical
- High
- Medium
- Low

---

## FR-034 — Test Case Explorer

The frontend shall display generated test cases.

Users should be able to filter test cases by:

- Positive
- Negative
- Edge
- Security

Users should also be able to filter by priority.

---

## FR-035 — Error Handling

The system shall handle errors during:

- File upload
- File extraction
- Embedding generation
- Vector search
- AI processing
- Database operations
- Analysis workflow execution

Errors should be returned using the standard API error format.

---

# 3. Non-Functional Requirements

## NFR-001 — Performance

The frontend shall remain responsive while a document is being analyzed.

Long-running AI analysis should be handled as an asynchronous or background process where possible.

The upload request should not wait for the complete analysis to finish.

---

## NFR-002 — Reliability

The system should handle temporary AI or database failures gracefully.

Transient AI failures may be retried where appropriate.

The system should avoid losing completed analysis stages unnecessarily.

---

## NFR-003 — Error Recovery

If a non-critical AI node fails, the system should attempt recovery where possible.

If the complete analysis cannot be completed, the analysis status shall be marked as:

failed

The system should provide a meaningful error message.

---

## NFR-004 — Maintainability

The backend shall separate major responsibilities.

Recommended separation:

API Routes

→ Services

→ AI Workflow

→ AI Nodes

→ Document Processing

→ Database Layer

→ Scoring

This prevents business logic from being placed directly inside API route handlers.

---

## NFR-005 — Modularity

Each major AI analysis component should be independently replaceable.

For example:

Security Analyzer

Quality Analyzer

Consistency Analyzer

Test Generator

Requirement Improver

Each should have a clearly defined input and output structure.

---

## NFR-006 — Structured AI Output

AI nodes shall return structured JSON rather than unrestricted natural-language responses.

The backend shall validate AI responses using Pydantic models.

Invalid responses should be rejected, repaired, or retried.

---

## NFR-007 — Explainability

Important findings shall include evidence and an explanation.

The system should make it possible for a user to understand why a requirement was flagged.

---

## NFR-008 — Hallucination Control

The system shall minimize unsupported AI-generated claims.

The AI should:

- Use retrieved project context
- Reference source requirements
- Distinguish evidence from inference
- Avoid inventing business rules
- Ask for clarification when required information is unknown
- Avoid reporting irrelevant security concerns

---

## NFR-009 — Deterministic Scoring

The final specification score shall be calculated using backend logic and predefined weights.

The LLM may provide component-level assessments, but the final score shall be calculated programmatically.

---

## NFR-010 — Security

The backend shall validate uploaded documents before processing.

The system should:

- Restrict supported file types
- Restrict file size
- Avoid exposing internal storage paths
- Validate API input
- Validate AI output
- Avoid returning sensitive internal errors
- Prevent unauthorized document access when authentication is implemented

---

## NFR-011 — Data Integrity

The system shall maintain relationships between:

- Documents
- Requirements
- Chunks
- Analyses
- Security findings
- Conflicts
- Test cases

A generated finding should remain traceable to its related requirement and analysis.

---

## NFR-012 — Traceability

The system should maintain traceability between:

Document

→ Requirement

→ Analysis

→ Finding

→ Test Case

→ Improved Requirement

This allows users to understand where each result originated.

---

## NFR-013 — Usability

The interface should present complex AI analysis in a simple and understandable manner.

Users should be able to quickly identify:

- What is wrong
- How serious it is
- Why it is wrong
- Which requirement is affected
- How it can be improved
- Which tests should be created

---

## NFR-014 — Scalability

The architecture should allow additional AI analysis nodes to be added later without redesigning the entire application.

Potential future nodes may include:

- Performance analysis
- Accessibility analysis
- Privacy analysis
- Compliance analysis
- API contract analysis

These are not required for the MVP.

---

## NFR-015 — Technology Independence

The application should keep AI-related functionality isolated from the API layer.

This should allow the underlying LLM to be replaced without rewriting the complete backend.

For example:

Ollama + Qwen

could later be replaced with another model provider without changing the frontend API contract.

---

## NFR-016 — Local Development

The MVP should be capable of running locally using:

- Python
- FastAPI
- Next.js
- Ollama
- Supabase

The AI model should preferably run locally through Ollama to avoid requiring a paid AI API for the MVP.

---

## NFR-017 — Cost

The MVP should avoid mandatory paid AI APIs.

Preferred development setup:

- FastAPI — Free
- Python — Free
- Next.js — Free
- LangChain — Free
- LangGraph — Free
- Ollama — Free
- Qwen — Local/open-weight model
- Supabase — Free tier where sufficient
- PostgreSQL/pgvector — Open source

External paid APIs or services should not be required for the basic MVP.

---

# 4. MVP Acceptance Criteria

The MVP shall be considered functional when a user can:

1. Upload a supported software requirements document.
2. Start an analysis.
3. See the analysis processing status.
4. Extract individual requirements.
5. Retrieve related requirements using RAG.
6. Detect ambiguous requirements.
7. Detect incomplete requirements.
8. Detect relevant security gaps.
9. Detect contradictions between requirements.
10. Generate relevant edge cases.
11. Generate structured test cases.
12. Generate improved requirements.
13. View evidence for detected issues.
14. View an overall specification score.
15. View requirement-level scores.
16. View the final results through the frontend.

---

# 5. MVP Priority

## Must Have

- Document upload
- Text extraction
- Requirement extraction
- Embedding generation
- Vector storage
- RAG retrieval
- Quality analysis
- Security analysis
- Test generation
- Overall scoring
- Basic dashboard

## Should Have

- Contradiction detection
- Edge-case generation
- Requirement improvement
- Evidence display
- Requirement explorer
- Test explorer

## Nice to Have

- PDF report export
- Analysis history
- User authentication
- Advanced filtering
- Dark mode
- Additional document formats
- Advanced security categories
- Performance analysis
- Accessibility analysis

---

# 6. MVP Definition of Done

The project is considered complete when the following end-to-end workflow works successfully:

User

↓

Uploads requirements document

↓

System extracts text

↓

System extracts requirements

↓

System generates embeddings

↓

System stores embeddings

↓

RAG retrieves related requirements

↓

AI analyzes requirements

↓

Security analysis runs

↓

Consistency analysis runs

↓

Edge cases are generated

↓

Test cases are generated

↓

Improved requirements are generated

↓

Scores are calculated

↓

Results are stored

↓

Frontend displays the complete analysis

The system should successfully demonstrate this workflow using a sample software specification containing intentionally ambiguous, incomplete, and contradictory requirements.