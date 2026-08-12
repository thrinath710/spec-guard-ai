# SpecGuard AI — Architecture and System Flow

---

# 1. High-Level Architecture

The system follows a frontend-backend-AI architecture.

```text
                    USER
                     |
                     v
              Next.js Frontend
                     |
                     v
                 FastAPI
                     |
          +----------+----------+
          |                     |
          v                     v
   Document Processor      Analysis API
          |                     |
          v                     v
    Text Extraction        LangGraph
          |                     |
          v                     |
      Chunking                  |
          |                     |
          v                     |
      Embeddings                |
          |                     |
          v                     |
     Supabase pgvector          |
          |                     |
          +----------+----------+
                     |
                     v
               RAG Retriever
                     |
                     v
              AI Analysis Nodes
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
   Quality       Security      Consistency
   Analysis      Analysis       Analysis
       |             |             |
       +-------------+-------------+
                     |
                     v
                Edge Cases
                     |
                     v
                Test Cases
                     |
                     v
             Requirement Rewrite
                     |
                     v
               Risk Scoring
                     |
                     v
              Final Analysis
                     |
                     v
               Next.js UI


2. Main Components
Frontend
Technology:
Next.js
TypeScript
Tailwind CSS
Responsibilities:
Upload requirements
Display processing status
Display overall score
Display detected issues
Display security findings
Display contradictions
Display test cases
Display improved requirements
Allow users to view evidence
Backend
Technology:
FastAPI
Python
Responsibilities:
Receive uploaded documents
Manage analysis sessions
Process documents
Start LangGraph workflows
Return analysis results
Store analysis results
Document Processor
Responsibilities:
Validate uploaded file.
Extract text.
Detect document structure.
Split text into chunks.
Identify candidate requirements.
Generate embeddings.
Store chunks in Supabase.
Supported formats:
PDF
DOCX
TXT
Markdown
RAG Layer
The RAG system stores requirement chunks in a vector database.
Flow:
Document
   |
   v
Text
   |
   v
Chunks
   |
   v
Embeddings
   |
   v
Supabase pgvector
During analysis:
Requirement
     |
     v
Embedding
     |
     v
Vector Search
     |
     v
Related Requirements
     |
     v
LLM Analysis
The purpose of RAG is to provide related project-specific requirements to the AI when analyzing a requirement.
3. LangGraph Workflow
The main AI workflow is:
START
 |
 v
Extract Requirements
 |
 v
Retrieve Related Requirements
 |
 v
Quality Analysis
 |
 +----------+----------+
 |                     |
 v                     v
Security Analysis   Consistency Analysis
 |                     |
 +----------+----------+
            |
            v
       Edge Case Analysis
            |
            v
       Test Generation
            |
            v
    Requirement Improvement
            |
            v
        Score Results
            |
            v
           END
           
4. Node Responsibilities
Node 1: Requirement Extraction
Input:
Document text
Output:
Structured requirements.
Example:
{
  "id": "REQ-001",
  "text": "Users can upload profile images.",
  "category": "File Upload"
}
Node 2: Related Requirement Retrieval
Input:
Current requirement
Output:
Top related requirements.
Example:
REQ-001
REQ-014
REQ-019
REQ-023
These requirements are provided as context to subsequent analysis.
Node 3: Quality Analysis
Checks:
Ambiguity
Completeness
Clarity
Testability
Output:
{
  "clarity": 70,
  "completeness": 45,
  "testability": 40,
  "issues": []
}
Node 4: Security Analysis
Checks:
Authentication
Authorization
Input validation
Data protection
File security
Rate limiting
Session security
Output:
{
  "risk": "HIGH",
  "findings": []
}
Node 5: Consistency Analysis
Compares the current requirement against retrieved related requirements.
Output:
{
  "conflict": true,
  "related_requirement": "REQ-021",
  "reason": "Maximum upload size differs."
}
Node 6: Edge Case Analysis
Generates missing scenarios.
Example:
- Invalid file
- Oversized file
- Corrupted file
- Unauthorized upload
- Storage failure
Node 7: Test Generation
Generates structured test cases.
Each test contains:
Test ID
Requirement ID
Title
Preconditions
Steps
Expected result
Priority
Category
Node 8: Requirement Improvement
Produces an improved requirement.
The improved requirement must:
Be unambiguous
Be testable
Include important constraints
Include security considerations where appropriate
Preserve the original business intent
5. Scoring Engine
Scoring should be deterministic.
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
The LLM produces individual analysis scores.
The backend calculates the final score.
This prevents the LLM from arbitrarily deciding the final score.
6. Evidence System
Every important finding should contain evidence.
Example:
{
  "issue": "Authorization rule missing",
  "requirement_id": "REQ-017",
  "evidence": "Users can download documents.",
  "reason": "The requirement does not specify whether users can access documents belonging to other users."
}
Evidence should reference the original requirement whenever possible.
7. Final Response Flow
The final result returned to the frontend contains:
Project Score
Requirement Statistics
Quality Issues
Security Findings
Contradictions
Edge Cases
Test Cases
Improved Requirements
Evidence