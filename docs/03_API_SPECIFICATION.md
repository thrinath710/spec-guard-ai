# SpecGuard AI — API Specification

## 1. Overview

The SpecGuard AI backend uses FastAPI to expose REST APIs for:

- Document upload
- Analysis creation
- Analysis status tracking
- Analysis results
- Requirement retrieval
- Security findings
- Requirement conflicts
- Generated test cases
- Requirement improvement

Base API path:

/api/v1

The API is responsible for communication between the frontend and the backend. AI processing, document processing, database operations, and scoring are handled internally by the backend.

---

# 2. API Design Principles

The API should follow these principles:

- REST-style endpoints
- JSON responses
- Clear HTTP status codes
- Pydantic request and response validation
- Consistent error responses
- No AI-generated raw output directly exposed to the frontend
- Structured responses only
- Long-running analysis should not block the upload request

---

# 3. Common Response Format

Successful responses should return structured JSON.

Example:

{
  "success": true,
  "data": {
    "document_id": "doc_123"
  }
}

Error responses should follow:

{
  "success": false,
  "error": {
    "code": "INVALID_DOCUMENT",
    "message": "The uploaded document format is not supported."
  }
}

---

# 4. Health Check

## GET /health

### Purpose

Check whether the backend is running correctly.

### Request

No request body.

### Response

{
  "success": true,
  "data": {
    "status": "ok"
  }
}

### HTTP Status

200 OK

---

# 5. Upload Document

## POST /documents/upload

### Purpose

Upload a software requirements document for analysis.

### Supported Formats

- PDF
- DOCX
- TXT
- MD

### Request

Content-Type:

multipart/form-data

Field:

file

Example:

POST /api/v1/documents/upload

### Processing

The backend should:

1. Validate the file.
2. Validate the file type.
3. Validate the file size.
4. Save the document.
5. Create a document record.
6. Return a unique document ID.

### Response

{
  "success": true,
  "data": {
    "document_id": "doc_123",
    "filename": "requirements.pdf",
    "file_type": "pdf",
    "status": "uploaded"
  }
}

### HTTP Status

201 Created

### Possible Errors

INVALID_DOCUMENT

UNSUPPORTED_FILE_TYPE

FILE_TOO_LARGE

DOCUMENT_STORAGE_ERROR

---

# 6. Start Analysis

## POST /analyses

### Purpose

Start an AI analysis for an uploaded document.

### Request

{
  "document_id": "doc_123"
}

### Processing

The backend should:

1. Verify that the document exists.
2. Create an analysis record.
3. Start the analysis workflow.
4. Return an analysis ID.

The complete AI workflow should not need to finish before returning the response.

### Response

{
  "success": true,
  "data": {
    "analysis_id": "analysis_123",
    "document_id": "doc_123",
    "status": "queued"
  }
}

### HTTP Status

202 Accepted

---

# 7. Get Analysis Status

## GET /analyses/{analysis_id}/status

### Purpose

Return the current processing state of an analysis.

### Path Parameter

analysis_id

Example:

GET /api/v1/analyses/analysis_123/status

### Response

{
  "success": true,
  "data": {
    "analysis_id": "analysis_123",
    "status": "processing",
    "progress": 65,
    "current_stage": "security_analysis"
  }
}

### Possible Status Values

queued

processing

completed

failed

### Possible Processing Stages

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

# 8. Get Complete Analysis

## GET /analyses/{analysis_id}

### Purpose

Return the complete analysis after processing is finished.

### Response

{
  "success": true,
  "data": {
    "analysis_id": "analysis_123",
    "status": "completed",
    "overall_score": 64,
    "quality_scores": {
      "completeness": 61,
      "testability": 48,
      "security": 72,
      "clarity": 67,
      "consistency": 84
    },
    "statistics": {
      "requirements": 38,
      "critical_issues": 7,
      "high_issues": 11,
      "medium_issues": 14,
      "low_issues": 8,
      "generated_tests": 91,
      "security_findings": 12,
      "conflicts": 3
    }
  }
}

### HTTP Status

200 OK

---

# 9. Get Extracted Requirements

## GET /analyses/{analysis_id}/requirements

### Purpose

Return all requirements extracted from the analyzed document.

### Response

{
  "success": true,
  "data": {
    "requirements": [
      {
        "id": "REQ-001",
        "text": "Users can upload profile images.",
        "category": "File Management",
        "score": 48
      },
      {
        "id": "REQ-002",
        "text": "Users can view their uploaded images.",
        "category": "File Management",
        "score": 82
      }
    ]
  }
}

---

# 10. Get Requirement Details

## GET /analyses/{analysis_id}/requirements/{requirement_id}

### Purpose

Return complete analysis information for one requirement.

### Response

{
  "success": true,
  "data": {
    "id": "REQ-001",
    "text": "Users can upload profile images.",
    "category": "File Management",
    "score": 48,
    "quality": {
      "clarity": 70,
      "completeness": 45,
      "testability": 40
    },
    "issues": [
      {
        "severity": "high",
        "type": "completeness",
        "title": "Maximum file size not specified",
        "description": "The requirement does not define the maximum allowed file size.",
        "evidence": "Users can upload profile images."
      }
    ],
    "security_findings": [
      {
        "severity": "critical",
        "category": "authorization",
        "title": "Access control not specified",
        "description": "The requirement does not specify who can access uploaded images."
      }
    ],
    "edge_cases": [
      "Unsupported file type",
      "Oversized file",
      "Corrupted image",
      "Unauthorized upload",
      "Storage failure"
    ],
    "improved_requirement": "Authenticated users shall be able to upload JPEG, PNG or WebP images up to 5 MB."
  }
}

---

# 11. Get Security Findings

## GET /analyses/{analysis_id}/security

### Purpose

Return all security findings identified during analysis.

### Response

{
  "success": true,
  "data": {
    "risk": "HIGH",
    "findings": [
      {
        "id": "SEC-001",
        "requirement_id": "REQ-001",
        "severity": "critical",
        "category": "authorization",
        "title": "Authorization rule missing",
        "description": "The requirement does not define who is allowed to access uploaded files.",
        "evidence": "Users can upload profile images.",
        "recommendation": "Define ownership and access-control rules for uploaded files."
      }
    ]
  }
}

---

# 12. Get Requirement Conflicts

## GET /analyses/{analysis_id}/conflicts

### Purpose

Return contradictory or potentially conflicting requirements.

### Response

{
  "success": true,
  "data": {
    "conflicts": [
      {
        "id": "CON-001",
        "requirement_a": "REQ-007",
        "requirement_b": "REQ-015",
        "severity": "high",
        "description": "REQ-007 allows cancellation at any time while REQ-015 prevents cancellation after payment.",
        "resolution_status": "unresolved"
      }
    ]
  }
}

---

# 13. Get Generated Test Cases

## GET /analyses/{analysis_id}/tests

### Purpose

Return all generated test cases.

### Optional Query Parameters

category

Possible values:

positive

negative

edge

security

priority

Possible values:

low

medium

high

critical

### Example

GET /api/v1/analyses/analysis_123/tests?category=security

### Response

{
  "success": true,
  "data": {
    "tests": [
      {
        "id": "TC-001",
        "requirement_id": "REQ-001",
        "title": "Reject unsupported file type",
        "category": "security",
        "priority": "high",
        "preconditions": [
          "User is authenticated"
        ],
        "steps": [
          "Attempt to upload an executable file"
        ],
        "expected_result": "The upload is rejected."
      }
    ]
  }
}

---

# 14. Improve Requirement

## POST /requirements/{requirement_id}/improve

### Purpose

Generate an improved version of a requirement.

### Request

{
  "analysis_id": "analysis_123"
}

### Response

{
  "success": true,
  "data": {
    "requirement_id": "REQ-001",
    "original": "Users can upload profile images.",
    "improved": "Authenticated users shall be able to upload JPEG, PNG or WebP profile images up to 5 MB. The server shall validate the actual file type and reject unsupported or malformed files.",
    "changes": [
      "Specified supported file formats",
      "Added maximum file size",
      "Added file validation",
      "Added authentication requirement"
    ],
    "remaining_questions": [
      "Should users be allowed to replace an existing profile image?"
    ]
  }
}

---

# 15. Generate Tests for Requirement

## POST /requirements/{requirement_id}/tests/generate

### Purpose

Generate or regenerate test cases for a specific requirement.

### Request

{
  "analysis_id": "analysis_123"
}

### Response

{
  "success": true,
  "data": {
    "requirement_id": "REQ-001",
    "tests_generated": 8
  }
}

---

# 16. Get Analysis Statistics

## GET /analyses/{analysis_id}/statistics

### Purpose

Return summary statistics for the analysis dashboard.

### Response

{
  "success": true,
  "data": {
    "total_requirements": 38,
    "critical_issues": 7,
    "high_issues": 11,
    "medium_issues": 14,
    "low_issues": 8,
    "security_findings": 12,
    "conflicts": 3,
    "edge_cases": 42,
    "test_cases": 91
  }
}

---

# 17. Error Handling

All API errors should use a consistent structure.

Example:

{
  "success": false,
  "error": {
    "code": "ANALYSIS_NOT_FOUND",
    "message": "The requested analysis does not exist."
  }
}

Common error codes:

INVALID_DOCUMENT

UNSUPPORTED_FILE_TYPE

FILE_TOO_LARGE

DOCUMENT_NOT_FOUND

ANALYSIS_NOT_FOUND

ANALYSIS_FAILED

INVALID_REQUIREMENT

AI_SERVICE_ERROR

AI_OUTPUT_INVALID

VECTOR_STORE_ERROR

DATABASE_ERROR

DOCUMENT_PROCESSING_ERROR

---

# 18. HTTP Status Codes

200 OK

Used for successful GET requests.

201 Created

Used when a new resource is successfully created.

202 Accepted

Used when a long-running analysis has been queued.

400 Bad Request

Used when request data is invalid.

404 Not Found

Used when the requested document, analysis, or requirement does not exist.

413 Payload Too Large

Used when an uploaded document exceeds the allowed size.

422 Unprocessable Entity

Used when request validation fails.

500 Internal Server Error

Used for unexpected backend errors.

503 Service Unavailable

Used when an external or internal service required for processing is unavailable.

---

# 19. API Security

The MVP may initially run without user authentication to reduce development time.

However, the backend should be structured so authentication can be added later.

The API should:

- Validate uploaded files
- Restrict file size
- Avoid exposing internal file paths
- Validate request bodies
- Validate AI responses
- Avoid returning sensitive system information in errors
- Prevent unauthorized access when authentication is introduced

---

# 20. API Processing Flow

Document upload:

POST /documents/upload

↓

Document stored

↓

document_id returned

↓

POST /analyses

↓

analysis_id returned

↓

GET /analyses/{analysis_id}/status

↓

Processing

↓

GET /analyses/{analysis_id}

↓

Final analysis returned

↓

Frontend displays:

- Score
- Issues
- Security findings
- Conflicts
- Edge cases
- Tests
- Improved requirements

---

# 21. MVP API Priority

Must Have:

- GET /health
- POST /documents/upload
- POST /analyses
- GET /analyses/{analysis_id}/status
- GET /analyses/{analysis_id}
- GET /analyses/{analysis_id}/requirements
- GET /analyses/{analysis_id}/security
- GET /analyses/{analysis_id}/tests

Should Have:

- GET /analyses/{analysis_id}/conflicts
- GET /analyses/{analysis_id}/statistics
- GET /analyses/{analysis_id}/requirements/{requirement_id}

Nice to Have:

- POST /requirements/{requirement_id}/improve
- POST /requirements/{requirement_id}/tests/generate