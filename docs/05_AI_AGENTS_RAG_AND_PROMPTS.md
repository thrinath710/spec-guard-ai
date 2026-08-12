# SpecGuard AI — AI Agents, RAG and Prompt Design

## 1. Purpose

This document defines the AI architecture used by SpecGuard AI.

The AI system is responsible for understanding software requirements, identifying quality and security problems, detecting relationships between requirements, generating test scenarios, and improving weak requirements.

The system uses:

- Ollama
- Qwen
- LangChain
- LangGraph
- Embeddings
- Supabase pgvector
- Structured JSON output
- Pydantic validation

The AI workflow is divided into specialized nodes rather than relying on one large prompt.

---

# 2. AI Architecture

The main AI workflow is:

Document

↓

Requirement Extraction

↓

Requirement Structuring

↓

Embedding Generation

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

Final Result

LangGraph is responsible for coordinating the workflow.

LangChain is used for LLM interaction, prompt management, retrieval, embeddings, and structured output where appropriate.

---

# 3. Why Multiple AI Nodes Are Used

A single large prompt could technically perform many of these tasks.

However, SpecGuard AI separates them because each task has a different responsibility.

For example:

Quality Analysis asks:

"Is this requirement clear and complete?"

Security Analysis asks:

"What security assumptions or controls are missing?"

Consistency Analysis asks:

"Does this requirement conflict with another requirement?"

Test Generation asks:

"What tests should verify this requirement?"

Requirement Improvement asks:

"How can this requirement be rewritten without changing its intended business behavior?"

Separating these responsibilities makes the system:

- Easier to debug
- Easier to test
- Easier to improve
- More explainable
- More modular
- Easier to extend

---

# 4. AI Nodes

The MVP contains the following major AI nodes:

1. Requirement Extractor
2. Quality Analyzer
3. Security Analyzer
4. Consistency Analyzer
5. Edge Case Analyzer
6. Test Generator
7. Requirement Improver

---

# 5. Requirement Extractor

## Purpose

The Requirement Extractor converts raw document text into structured software requirements.

## Input

Extracted document text.

Example:

"Users can create an account using their email address. Users must verify their email before accessing the dashboard."

## Output

The output should contain separate requirements.

Example:

{
  "requirements": [
    {
      "id": "REQ-001",
      "text": "Users can create an account using their email address.",
      "category": "Authentication"
    },
    {
      "id": "REQ-002",
      "text": "Users must verify their email before accessing the dashboard.",
      "category": "Authentication"
    }
  ]
}

## Responsibilities

The extractor should:

- Identify explicit requirements
- Separate independent requirements
- Preserve the original meaning
- Assign requirement IDs
- Assign a category where possible
- Preserve source information

## Restrictions

The extractor must not:

- Invent requirements
- Add business rules
- Rewrite requirements unnecessarily
- Assume missing behavior

---

# 6. Quality Analyzer

## Purpose

The Quality Analyzer evaluates the general quality of a requirement.

It checks:

- Clarity
- Completeness
- Ambiguity
- Testability
- Missing constraints
- Missing acceptance criteria
- Undefined terminology

## Input

The analyzer receives:

- Target requirement
- Relevant retrieved requirements
- Optional document context

## Output

Example:

{
  "requirement_id": "REQ-001",
  "clarity_score": 70,
  "completeness_score": 45,
  "testability_score": 40,
  "issues": [
    {
      "severity": "high",
      "type": "ambiguity",
      "title": "Maximum file size is not specified",
      "description": "The requirement does not define a maximum file size.",
      "evidence": "Users can upload profile images.",
      "recommendation": "Specify the maximum permitted file size."
    }
  ]
}

---

# 7. Quality Analysis Prompt

The following is the initial prompt for the Quality Analyzer.

System Prompt:

You are a software requirements quality analyst.

Analyze the target software requirement using the supplied project context.

Evaluate:

1. Clarity
2. Completeness
3. Testability
4. Ambiguity
5. Missing constraints
6. Missing acceptance criteria
7. Undefined terminology

Only report issues that are supported by the requirement or retrieved project context.

Do not invent business rules.

If information is unknown, identify it as missing or requiring clarification.

Return structured JSON only.

The response must contain:

- clarity_score
- completeness_score
- testability_score
- issues

Each issue must contain:

- severity
- type
- title
- description
- evidence
- recommendation

---

# 8. Security Analyzer

## Purpose

The Security Analyzer identifies security requirements that may be missing or insufficiently specified.

## Security Categories

The analyzer should consider:

- Authentication
- Authorization
- Access Control
- Input Validation
- Output Validation
- File Security
- Data Protection
- Sensitive Data
- Rate Limiting
- Session Management
- Ownership Verification
- Security Logging

## Important Rule

The Security Analyzer should only report security concerns relevant to the requirement.

It should not flag every requirement with generic security warnings.

For example:

Requirement:

"The system displays the current date."

The analyzer should not generate unrelated warnings about password security.

---

# 9. Security Analyzer Input

The Security Analyzer receives:

- Target requirement
- Related requirements
- Requirement category
- Retrieved RAG context

---

# 10. Security Analyzer Output

Example:

{
  "requirement_id": "REQ-009",
  "risk": "HIGH",
  "findings": [
    {
      "severity": "critical",
      "category": "authorization",
      "title": "Access control is not specified",
      "description": "The requirement does not define which users can access uploaded files.",
      "evidence": "Users can upload profile images.",
      "recommendation": "Define ownership and access-control rules."
    }
  ]
}

---

# 11. Security Analyzer Prompt

System Prompt:

You are a software security requirements analyst.

Analyze the target requirement and relevant project context.

Identify security considerations that are missing, unclear, or insufficiently specified.

Consider only security categories relevant to the requirement:

- Authentication
- Authorization
- Access control
- Input validation
- Output validation
- File security
- Data protection
- Sensitive data
- Rate limiting
- Session management
- Ownership verification
- Security logging

Do not invent business requirements.

Do not report generic security concerns that are unrelated to the requirement.

For each finding provide:

- severity
- category
- title
- description
- evidence
- recommendation

Return valid structured JSON only.

---

# 12. Consistency Analyzer

## Purpose

The Consistency Analyzer detects contradictions between related requirements.

It uses RAG to retrieve potentially related requirements.

## Example

Target requirement:

REQ-007:

"Users can cancel an order at any time."

Retrieved requirement:

REQ-015:

"Orders cannot be cancelled after payment."

The analyzer should identify a conflict.

## Output

{
  "conflicts": [
    {
      "requirement_a": "REQ-007",
      "requirement_b": "REQ-015",
      "severity": "high",
      "description": "The requirements define conflicting cancellation behavior.",
      "evidence": [
        "Users can cancel an order at any time.",
        "Orders cannot be cancelled after payment."
      ]
    }
  ]
}

---

# 13. Consistency Analyzer Prompt

System Prompt:

You are a software requirements consistency analyst.

Compare the target requirement against the retrieved related requirements.

Identify direct or semantic contradictions.

A conflict may involve:

- Different limits
- Different permissions
- Different states
- Different business rules
- Conflicting timing requirements
- Conflicting behavior
- Conflicting conditions

Do not consider two requirements contradictory merely because they describe different features.

Only report a conflict when the requirements cannot both reasonably be true or when their interaction creates a meaningful ambiguity.

Return:

- requirement_a
- requirement_b
- severity
- description
- evidence

Return valid JSON only.

---

# 14. Edge Case Analyzer

## Purpose

The Edge Case Analyzer identifies important scenarios that are not explicitly addressed by the requirement.

## Categories

Potential categories include:

- Invalid input
- Empty input
- Boundary values
- Duplicate operations
- Missing data
- Unauthorized actions
- Failed operations
- Network failure
- External service failure
- Concurrency
- Recovery
- Security abuse

The analyzer should only generate relevant scenarios.

---

# 15. Edge Case Example

Requirement:

"Users can reset their password using email."

Generated edge cases:

1. Reset link expires.
2. Reset link is reused.
3. Reset token is invalid.
4. Multiple reset requests are made.
5. Email address does not exist.
6. Email delivery fails.
7. Too many reset attempts are made.

---

# 16. Edge Case Analyzer Prompt

System Prompt:

You are a senior software test and edge-case analyst.

Analyze the target requirement and identify important scenarios that are not explicitly specified.

Consider relevant:

- Invalid inputs
- Empty inputs
- Boundary values
- Duplicate operations
- Missing data
- Unauthorized actions
- System failures
- Network failures
- External service failures
- Concurrency
- Recovery scenarios
- Security abuse cases

Only generate relevant edge cases.

Do not invent unrelated functionality.

For each edge case provide:

- title
- description
- category
- reason

Return valid JSON only.

---

# 17. Test Generator

## Purpose

The Test Generator converts requirements, detected issues, and edge cases into structured test cases.

## Test Categories

- Positive
- Negative
- Edge
- Security

## Test Priorities

- Low
- Medium
- High
- Critical

---

# 18. Test Case Structure

Each generated test case should contain:

{
  "id": "TC-001",
  "requirement_id": "REQ-001",
  "title": "Upload valid JPEG",
  "category": "positive",
  "priority": "medium",
  "preconditions": [
    "User is authenticated"
  ],
  "steps": [
    "Open profile settings",
    "Select a valid JPEG image",
    "Submit the upload"
  ],
  "expected_result": "The image is uploaded successfully."
}

---

# 19. Test Generator Prompt

System Prompt:

You are a senior QA engineer.

Generate structured test cases for the target software requirement.

Use the requirement, detected issues, security findings, and relevant edge cases.

Generate relevant:

- Positive tests
- Negative tests
- Boundary tests
- Edge-case tests
- Security tests

Do not generate duplicate tests.

Do not test functionality that is unrelated to the requirement.

Each test case must contain:

- id
- requirement_id
- title
- category
- priority
- preconditions
- steps
- expected_result

Return valid JSON only.

---

# 20. Requirement Improver

## Purpose

The Requirement Improver rewrites weak requirements into clearer and more testable requirements.

## Example

Original:

"Users can upload profile images."

Improved:

"Authenticated users shall be able to upload JPEG, PNG or WebP profile images up to 5 MB. The server shall validate the actual file type and reject unsupported or malformed files."

---

# 21. Requirement Improvement Rules

The improved requirement should:

- Preserve the original business intent
- Remove ambiguity
- Improve specificity
- Improve testability
- Include important constraints
- Include relevant security requirements
- Clearly define expected behavior

The system must not invent unsupported business decisions.

If a required value is unknown, the system should generate a clarification question instead.

---

# 22. Requirement Improver Prompt

System Prompt:

You are a senior software requirements engineer.

Rewrite the target requirement so that it becomes:

- Clear
- Specific
- Complete
- Testable
- Security-aware when applicable

Preserve the original business intent.

Do not invent unsupported business rules.

If important information is unknown, do not guess.

Instead, identify it as a clarification question.

Return:

- improved_requirement
- changes_made
- remaining_questions

Return valid JSON only.

---

# 23. RAG Architecture

## Purpose

RAG allows SpecGuard AI to analyze requirements using project-specific context.

Without RAG, the AI may analyze each requirement independently.

With RAG, the system can retrieve related requirements before analysis.

Example:

Target:

REQ-007:
"Users can cancel orders at any time."

RAG retrieves:

REQ-015:
"Orders cannot be cancelled after payment."

The retrieved requirement provides evidence for the consistency analyzer.

---

# 24. RAG Pipeline

Document

↓

Text Extraction

↓

Chunking

↓

Embedding Generation

↓

Supabase pgvector

↓

Stored Vectors

↓

Target Requirement

↓

Query Embedding

↓

Similarity Search

↓

Top-K Related Requirements

↓

AI Analysis

---

# 25. Embedding Strategy

Each document chunk or requirement should be converted into a vector embedding.

The vector should be stored together with metadata.

Example metadata:

{
  "document_id": "doc_123",
  "requirement_id": "REQ-007",
  "category": "Order Management",
  "source": "requirements.pdf"
}

---

# 26. Retrieval Strategy

For each requirement:

1. Generate an embedding for the target requirement.
2. Search the vector database.
3. Retrieve the most semantically similar requirements.
4. Remove the target requirement itself.
5. Limit the number of retrieved results.
6. Pass relevant results to the appropriate AI node.

The initial MVP should use a small Top-K value such as 3-5 related requirements.

This reduces unnecessary context and keeps prompts manageable.

---

# 27. Why RAG Is Needed

RAG is primarily used for cross-requirement reasoning.

Important use cases include:

### Contradiction Detection

Finding requirements that define conflicting behavior.

### Dependency Detection

Finding requirements that depend on or affect another requirement.

### Security Context

Understanding whether another requirement already defines an authentication or authorization rule.

### Test Generation

Providing related requirements when generating tests.

RAG should not be used simply to make the project appear more complex.

It should provide information that improves analysis.

---

# 28. LangGraph Workflow

The LangGraph workflow should approximately follow:

START

↓

Extract Requirements

↓

Create/Retrieve Requirement Context

↓

Retrieve Related Requirements

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

Score Results

↓

END

---

# 29. LangGraph State

The workflow should maintain a shared state.

Example:

{
  "analysis_id": "analysis_123",
  "document_id": "doc_123",
  "requirements": [],
  "current_requirement": {},
  "related_requirements": [],
  "quality_results": [],
  "security_results": [],
  "conflicts": [],
  "edge_cases": [],
  "test_cases": [],
  "improved_requirements": [],
  "scores": {}
}

Each LangGraph node reads the information it needs and adds its results to the state.

---

# 30. Node Dependencies

Requirement Extraction:

Input:
Document text

Output:
Requirements

RAG Retrieval:

Input:
Requirement

Output:
Related requirements

Quality Analyzer:

Input:
Requirement + related context

Output:
Quality findings

Security Analyzer:

Input:
Requirement + related context

Output:
Security findings

Consistency Analyzer:

Input:
Requirement + retrieved requirements

Output:
Conflicts

Edge Case Analyzer:

Input:
Requirement + findings

Output:
Edge cases

Test Generator:

Input:
Requirement + findings + edge cases

Output:
Test cases

Requirement Improver:

Input:
Requirement + findings

Output:
Improved requirement

Scoring:

Input:
All analysis results

Output:
Final scores

---

# 31. Structured Output Validation

All AI nodes should return structured JSON.

The backend should define Pydantic models for expected outputs.

Example:

class SecurityFinding:

- severity
- category
- title
- description
- evidence
- recommendation

If the LLM returns invalid JSON or missing required fields:

1. Attempt structured output parsing.
2. Retry the request if appropriate.
3. Use a repair prompt if necessary.
4. Mark the node as failed if valid output cannot be produced.

---

# 32. Hallucination Prevention

SpecGuard AI should minimize hallucination by following these rules:

1. Use source requirements as evidence.
2. Use RAG for project-specific context.
3. Do not invent business rules.
4. Do not assume unspecified numeric limits.
5. Clearly identify unknown information.
6. Generate clarification questions when necessary.
7. Avoid unrelated security findings.
8. Validate all AI output.
9. Keep final scoring deterministic.
10. Maintain requirement-level traceability.

---

# 33. AI Model Configuration

The MVP should use a local LLM through Ollama.

Recommended model:

Qwen

The exact model size may depend on the available hardware.

The model should be configured through environment variables rather than hardcoded throughout the application.

Example:

OLLAMA_BASE_URL

OLLAMA_MODEL

EMBEDDING_MODEL

This allows the model to be changed without modifying the application logic.

---

# 34. Temperature and Determinism

For analysis tasks, the system should prefer relatively deterministic model settings.

Lower temperature should be used where supported because:

- Requirement analysis should be consistent.
- Security analysis should be reproducible.
- Structured output should be stable.
- Test generation should avoid unnecessary variation.

Creative generation is not a primary goal of SpecGuard AI.

---

# 35. AI Failure Handling

If an AI request fails:

1. Log the failure.
2. Retry where appropriate.
3. Avoid crashing the entire application if possible.
4. Mark the affected analysis stage.
5. Return a meaningful status to the frontend.

Example:

{
  "status": "failed",
  "current_stage": "security_analysis",
  "error": "AI service unavailable"
}

---

# 36. AI Design Principle

The AI should be treated as an analysis component rather than the source of truth.

The system of record remains:

- Original requirements
- Retrieved project context
- Structured analysis results
- Backend scoring logic

AI suggestions should be traceable, validated, and presented as recommendations rather than unquestionable facts.

---

# 37. Future AI Extensions

The architecture should allow future analysis nodes such as:

- Performance Requirement Analyzer
- Accessibility Analyzer
- Privacy Analyzer
- API Contract Analyzer
- Compliance Analyzer
- Database Requirement Analyzer
- Dependency Analyzer

These are outside the MVP scope.

---

# 38. Final AI Workflow Example

Input:

"Users can upload profile images."

RAG retrieves:

REQ-014:
"Only authenticated users can modify their profile."

REQ-021:
"Profile data is private to each user."

Quality Analyzer:

Detects missing file format and size constraints.

Security Analyzer:

Detects missing file validation and potential access-control ambiguity.

Consistency Analyzer:

Checks related profile requirements.

Edge Case Analyzer:

Generates:

- Unsupported format
- Oversized file
- Corrupted file
- Unauthorized upload
- Malicious file
- Storage failure

Test Generator:

Creates positive, negative, edge, and security tests.

Requirement Improver:

Produces a more precise requirement.

Scoring:

Calculates the final requirement and specification scores.

Final output:

A traceable, structured analysis of the original requirement.