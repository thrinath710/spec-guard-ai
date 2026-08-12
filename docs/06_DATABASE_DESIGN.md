# SpecGuard AI — Database Design

## 1. Purpose

This document defines the database structure for SpecGuard AI.

The database stores:

- Uploaded documents
- Extracted requirements
- Document chunks
- Vector embeddings
- Analysis records
- Quality findings
- Security findings
- Requirement conflicts
- Edge cases
- Generated test cases
- Improved requirements
- Analysis scores

The database uses PostgreSQL through Supabase.

Supabase pgvector is used for semantic similarity search required by the RAG pipeline.

---

# 2. Database Technology

Primary database:

PostgreSQL

Hosted through:

Supabase

Vector extension:

pgvector

The database should use UUIDs or generated identifiers for primary keys.

---

# 3. Entity Relationship Overview

The main relationships are:

Document

↓

Requirements

↓

Analysis

↓

Quality Findings
Security Findings
Conflicts
Edge Cases
Test Cases
Improved Requirements

Document

↓

Document Chunks

↓

Vector Embeddings

The general relationship can be represented as:

documents
    |
    +---- requirements
    |        |
    |        +---- quality_findings
    |        +---- security_findings
    |        +---- edge_cases
    |        +---- test_cases
    |        +---- improved_requirements
    |
    +---- document_chunks
             |
             +---- embeddings

analyses
    |
    +---- analysis_scores
    +---- quality_findings
    +---- security_findings
    +---- conflicts
    +---- edge_cases
    +---- test_cases
    +---- improved_requirements

---

# 4. Documents Table

## Table

documents

## Purpose

Stores information about uploaded software requirement documents.

## Columns

id

Type:

UUID

Primary Key:

Yes

Description:

Unique identifier for the document.

---

filename

Type:

TEXT

Description:

Original uploaded filename.

Example:

requirements.pdf

---

file_type

Type:

TEXT

Description:

Type of uploaded document.

Possible values:

pdf

docx

txt

md

---

file_size

Type:

INTEGER

Description:

Size of uploaded document in bytes.

---

storage_path

Type:

TEXT

Description:

Location of the stored document.

---

status

Type:

TEXT

Description:

Current document processing status.

Possible values:

uploaded

processing

processed

failed

---

created_at

Type:

TIMESTAMP

Description:

Time the document was uploaded.

---

updated_at

Type:

TIMESTAMP

Description:

Last update time.

---

# 5. Requirements Table

## Table

requirements

## Purpose

Stores individual requirements extracted from a document.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

document_id

Type:

UUID

Foreign Key:

documents.id

Description:

Document from which the requirement was extracted.

---

requirement_code

Type:

TEXT

Description:

Human-readable requirement identifier.

Example:

REQ-001

---

text

Type:

TEXT

Description:

Original requirement text.

---

category

Type:

TEXT

Description:

Requirement category.

Possible values:

authentication

authorization

user_management

file_management

payment

order_management

data_management

notification

performance

security

administration

other

---

source_location

Type:

TEXT

Description:

Page number, section, paragraph, or other source location where available.

---

created_at

Type:

TIMESTAMP

Description:

Time the requirement was created.

---

# 6. Document Chunks Table

## Table

document_chunks

## Purpose

Stores chunks of extracted document text used for RAG.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

document_id

Type:

UUID

Foreign Key:

documents.id

Description:

Document from which the chunk originated.

---

requirement_id

Type:

UUID

Foreign Key:

requirements.id

Nullable:

Yes

Description:

Requirement associated with the chunk when applicable.

---

content

Type:

TEXT

Description:

Text contained within the chunk.

---

chunk_index

Type:

INTEGER

Description:

Position of the chunk within the document.

---

metadata

Type:

JSONB

Description:

Additional information about the chunk.

Example:

{
  "page": 4,
  "section": "Authentication",
  "source": "requirements.pdf"
}

---

created_at

Type:

TIMESTAMP

Description:

Time the chunk was created.

---

# 7. Embeddings

The vector embedding should be stored in the document_chunks table or a dedicated vector table.

For the MVP, storing the embedding directly with document chunks is sufficient.

## Column

embedding

Type:

VECTOR

Description:

Vector representation of the chunk used for semantic search.

The vector dimension depends on the selected embedding model.

The dimension must match the embedding model used by the application.

---

# 8. Analyses Table

## Table

analyses

## Purpose

Stores each analysis execution performed on a document.

A document may have multiple analyses.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

document_id

Type:

UUID

Foreign Key:

documents.id

Description:

Document being analyzed.

---

status

Type:

TEXT

Description:

Current analysis state.

Possible values:

queued

processing

completed

failed

---

current_stage

Type:

TEXT

Description:

Current AI processing stage.

Possible values:

document_processing

requirement_extraction

embedding

retrieval

quality_analysis

security_analysis

consistency_analysis

edge_case_analysis

test_generation

requirement_improvement

scoring

completed

---

progress

Type:

INTEGER

Description:

Approximate analysis progress from 0 to 100.

---

error_message

Type:

TEXT

Nullable:

Yes

Description:

Error message if analysis fails.

---

created_at

Type:

TIMESTAMP

Description:

Time the analysis started.

---

completed_at

Type:

TIMESTAMP

Nullable:

Yes

Description:

Time the analysis completed.

---

# 9. Requirement Analysis Scores

## Table

requirement_scores

## Purpose

Stores quality scores for individual requirements.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

analysis_id

Type:

UUID

Foreign Key:

analyses.id

---

requirement_id

Type:

UUID

Foreign Key:

requirements.id

---

clarity_score

Type:

INTEGER

Description:

Clarity score from 0 to 100.

---

completeness_score

Type:

INTEGER

Description:

Completeness score from 0 to 100.

---

testability_score

Type:

INTEGER

Description:

Testability score from 0 to 100.

---

security_score

Type:

INTEGER

Description:

Security score from 0 to 100.

---

consistency_score

Type:

INTEGER

Description:

Consistency score from 0 to 100.

---

overall_score

Type:

INTEGER

Description:

Overall requirement score from 0 to 100.

---

created_at

Type:

TIMESTAMP

Description:

Time the score was generated.

---

# 10. Quality Findings Table

## Table

quality_findings

## Purpose

Stores issues related to requirement quality.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

analysis_id

Type:

UUID

Foreign Key:

analyses.id

---

requirement_id

Type:

UUID

Foreign Key:

requirements.id

---

severity

Type:

TEXT

Description:

Issue severity.

Possible values:

low

medium

high

critical

---

type

Type:

TEXT

Description:

Quality issue category.

Examples:

ambiguity

completeness

clarity

testability

missing_constraint

missing_acceptance_criteria

---

title

Type:

TEXT

Description:

Short issue title.

---

description

Type:

TEXT

Description:

Detailed explanation.

---

evidence

Type:

TEXT

Description:

Relevant evidence from the requirement or retrieved context.

---

recommendation

Type:

TEXT

Description:

Suggested improvement.

---

created_at

Type:

TIMESTAMP

Description:

Time the finding was generated.

---

# 11. Security Findings Table

## Table

security_findings

## Purpose

Stores security-related findings.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

analysis_id

Type:

UUID

Foreign Key:

analyses.id

---

requirement_id

Type:

UUID

Foreign Key:

requirements.id

---

severity

Type:

TEXT

Description:

Security severity.

Possible values:

low

medium

high

critical

---

category

Type:

TEXT

Description:

Security category.

Examples:

authentication

authorization

access_control

input_validation

file_security

data_protection

rate_limiting

session_management

ownership

logging

---

title

Type:

TEXT

Description:

Security issue title.

---

description

Type:

TEXT

Description:

Detailed explanation.

---

evidence

Type:

TEXT

Description:

Evidence supporting the finding.

---

recommendation

Type:

TEXT

Description:

Suggested security improvement.

---

created_at

Type:

TIMESTAMP

Description:

Time the finding was generated.

---

# 12. Conflicts Table

## Table

requirement_conflicts

## Purpose

Stores contradictions or potential conflicts between requirements.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

analysis_id

Type:

UUID

Foreign Key:

analyses.id

---

requirement_a_id

Type:

UUID

Foreign Key:

requirements.id

---

requirement_b_id

Type:

UUID

Foreign Key:

requirements.id

---

severity

Type:

TEXT

Possible values:

low

medium

high

critical

---

description

Type:

TEXT

Description:

Explanation of the conflict.

---

evidence

Type:

JSONB

Description:

Evidence from both requirements.

Example:

{
  "requirement_a": "Users can cancel orders at any time.",
  "requirement_b": "Orders cannot be cancelled after payment."
}

---

resolution_status

Type:

TEXT

Possible values:

unresolved

resolved

ignored

---

created_at

Type:

TIMESTAMP

Description:

Time the conflict was detected.

---

# 13. Edge Cases Table

## Table

edge_cases

## Purpose

Stores edge cases generated by the AI.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

analysis_id

Type:

UUID

Foreign Key:

analyses.id

---

requirement_id

Type:

UUID

Foreign Key:

requirements.id

---

title

Type:

TEXT

Description:

Name of the edge case.

---

description

Type:

TEXT

Description:

Detailed description of the scenario.

---

category

Type:

TEXT

Examples:

invalid_input

boundary

failure

authorization

concurrency

recovery

security

---

reason

Type:

TEXT

Description:

Why the scenario is important.

---

created_at

Type:

TIMESTAMP

Description:

Time the edge case was generated.

---

# 14. Test Cases Table

## Table

test_cases

## Purpose

Stores AI-generated test cases.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

analysis_id

Type:

UUID

Foreign Key:

analyses.id

---

requirement_id

Type:

UUID

Foreign Key:

requirements.id

---

test_code

Type:

TEXT

Description:

Human-readable test identifier.

Example:

TC-001

---

title

Type:

TEXT

Description:

Test case title.

---

category

Type:

TEXT

Possible values:

positive

negative

edge

security

---

priority

Type:

TEXT

Possible values:

low

medium

high

critical

---

preconditions

Type:

JSONB

Description:

Conditions that must exist before executing the test.

Example:

[
  "User is authenticated",
  "User has access to the profile page"
]

---

steps

Type:

JSONB

Description:

Ordered test steps.

Example:

[
  "Open profile settings",
  "Select a valid JPEG",
  "Click upload"
]

---

expected_result

Type:

TEXT

Description:

Expected system behavior.

---

created_at

Type:

TIMESTAMP

Description:

Time the test was generated.

---

# 15. Improved Requirements Table

## Table

improved_requirements

## Purpose

Stores AI-generated improved versions of requirements.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

analysis_id

Type:

UUID

Foreign Key:

analyses.id

---

requirement_id

Type:

UUID

Foreign Key:

requirements.id

---

original_text

Type:

TEXT

Description:

Original requirement.

---

improved_text

Type:

TEXT

Description:

Improved requirement generated by the AI.

---

changes

Type:

JSONB

Description:

Changes made to the original requirement.

Example:

[
  "Added supported file types",
  "Added maximum file size",
  "Added validation requirement"
]

---

remaining_questions

Type:

JSONB

Description:

Questions that cannot be safely answered without additional business information.

Example:

[
  "Should users be allowed to replace an existing profile image?"
]

---

created_at

Type:

TIMESTAMP

Description:

Time the improved requirement was generated.

---

# 16. Analysis Scores Table

## Table

analysis_scores

## Purpose

Stores the final specification-level scores.

## Columns

id

Type:

UUID

Primary Key:

Yes

---

analysis_id

Type:

UUID

Foreign Key:

analyses.id

Unique:

Yes

---

completeness_score

Type:

INTEGER

Range:

0-100

---

testability_score

Type:

INTEGER

Range:

0-100

---

security_score

Type:

INTEGER

Range:

0-100

---

clarity_score

Type:

INTEGER

Range:

0-100

---

consistency_score

Type:

INTEGER

Range:

0-100

---

overall_score

Type:

INTEGER

Range:

0-100

---

risk_level

Type:

TEXT

Possible values:

low

medium

high

critical

---

created_at

Type:

TIMESTAMP

Description:

Time the final score was calculated.

---

# 17. Score Calculation

The final score must be calculated by backend code.

The formula is:

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

Example:

Completeness = 70

Testability = 60

Security = 80

Clarity = 75

Consistency = 90

Calculation:

(70 × 0.30)
+
(60 × 0.25)
+
(80 × 0.20)
+
(75 × 0.15)
+
(90 × 0.10)

= 21
+ 15
+ 16
+ 11.25
+ 9

= 72.25

Final score:

72

Classification:

Needs Improvement

---

# 18. Relationships

## Documents → Requirements

One document can contain many requirements.

Relationship:

documents.id

↓

requirements.document_id

Cardinality:

1 : N

---

## Documents → Chunks

One document can contain many chunks.

Relationship:

documents.id

↓

document_chunks.document_id

Cardinality:

1 : N

---

## Requirements → Chunks

A requirement may correspond to one or more chunks.

Relationship:

requirements.id

↓

document_chunks.requirement_id

Cardinality:

1 : N

---

## Documents → Analyses

A document can be analyzed multiple times.

Relationship:

documents.id

↓

analyses.document_id

Cardinality:

1 : N

---

## Analyses → Scores

An analysis has one final score.

Relationship:

analyses.id

↓

analysis_scores.analysis_id

Cardinality:

1 : 1

---

## Analyses → Findings

One analysis can generate many findings.

Relationship:

analyses.id

↓

quality_findings.analysis_id

analyses.id

↓

security_findings.analysis_id

Cardinality:

1 : N

---

## Requirements → Findings

A requirement can have multiple findings.

Relationship:

requirements.id

↓

quality_findings.requirement_id

requirements.id

↓

security_findings.requirement_id

Cardinality:

1 : N

---

## Requirements → Conflicts

A requirement can participate in multiple conflicts.

Each conflict contains two requirement references:

requirement_a_id

requirement_b_id

---

## Requirements → Tests

One requirement can produce many test cases.

Relationship:

requirements.id

↓

test_cases.requirement_id

Cardinality:

1 : N

---

## Requirements → Improvements

A requirement may have one or more generated improvement versions.

Relationship:

requirements.id

↓

improved_requirements.requirement_id

---

# 19. Recommended Indexes

The following fields should have indexes where appropriate:

documents.id

documents.status

requirements.document_id

requirements.requirement_code

requirements.category

document_chunks.document_id

document_chunks.requirement_id

analyses.document_id

analyses.status

quality_findings.analysis_id

quality_findings.requirement_id

security_findings.analysis_id

security_findings.requirement_id

requirement_conflicts.analysis_id

test_cases.analysis_id

test_cases.requirement_id

improved_requirements.requirement_id

---

# 20. Vector Search Index

The embedding column should have an appropriate pgvector index once the dataset becomes large enough.

The index type can be selected based on the embedding model and retrieval requirements.

For the MVP, exact or small-scale similarity search may be sufficient.

As the dataset grows, an approximate vector index such as HNSW can be considered.

---

# 21. Data Retention

For the MVP, analysis results should remain stored so users can inspect previous analyses.

Future versions may introduce:

- Analysis deletion
- Document deletion
- Data retention policies
- User-specific data ownership
- Automatic cleanup

---

# 22. Database Security

Supabase Row Level Security should be considered when user authentication is introduced.

The MVP may initially operate in a controlled development environment.

Production deployment should not expose unrestricted database credentials to the frontend.

The frontend should communicate with the backend API rather than directly performing privileged database operations.

---

# 23. Environment Variables

Database configuration should be stored using environment variables.

Example:

SUPABASE_URL

SUPABASE_ANON_KEY

SUPABASE_SERVICE_ROLE_KEY

The service role key must only be used on the backend.

It must never be exposed to the frontend.

---

# 24. Database Access Architecture

The backend should use a database service layer.

Recommended structure:

API Route

↓

Service Layer

↓

Repository / Database Layer

↓

Supabase PostgreSQL

This keeps database queries separate from API route logic.

---

# 25. Example Data Flow

User uploads:

requirements.pdf

↓

documents

Document record created.

↓

Text extracted.

↓

requirements

REQ-001

REQ-002

REQ-003

...

↓

document_chunks

Chunks generated.

↓

Embeddings generated.

↓

Vector embeddings stored.

↓

Analysis created.

↓

analyses

↓

AI workflow executes.

↓

Results stored in:

quality_findings

security_findings

requirement_conflicts

edge_cases

test_cases

improved_requirements

↓

Final score stored in:

analysis_scores

↓

Frontend retrieves analysis through FastAPI.

---

# 26. Example Database Records

## Document

{
  "id": "doc_123",
  "filename": "requirements.pdf",
  "file_type": "pdf",
  "status": "processed"
}

## Requirement

{
  "id": "req_uuid_001",
  "document_id": "doc_123",
  "requirement_code": "REQ-001",
  "text": "Users can upload profile images.",
  "category": "file_management"
}

## Security Finding

{
  "id": "sec_uuid_001",
  "analysis_id": "analysis_123",
  "requirement_id": "req_uuid_001",
  "severity": "high",
  "category": "file_security",
  "title": "File validation not specified",
  "description": "The requirement does not specify allowed file types or validation behavior."
}

## Test Case

{
  "id": "test_uuid_001",
  "analysis_id": "analysis_123",
  "requirement_id": "req_uuid_001",
  "test_code": "TC-001",
  "title": "Reject unsupported file type",
  "category": "security",
  "priority": "high",
  "expected_result": "The system rejects the unsupported file."
}

---

# 27. MVP Database Tables

## Must Have

- documents
- requirements
- document_chunks
- analyses
- requirement_scores
- quality_findings
- security_findings
- requirement_conflicts
- edge_cases
- test_cases
- improved_requirements
- analysis_scores

---

# 28. Simplification for the 3-Day MVP

The database should not become unnecessarily complex.

If development time is limited, the following tables are sufficient for the first working version:

documents

requirements

document_chunks

analyses

security_findings

quality_findings

test_cases

analysis_scores

The following can initially be stored as JSON fields or added later:

- Edge cases
- Conflicts
- Improved requirements

However, separate tables are preferred once the system becomes more mature.

---

# 29. Database Design Principle

The database should preserve traceability.

Every AI-generated result should be traceable back to:

Document

→ Requirement

→ Analysis

→ Finding / Test / Improvement

This is one of the most important design principles of SpecGuard AI.

The system should never produce an important AI finding that cannot be associated with the requirement or project context that caused it.