# Project Requirements: Enterprise RAG Chatbot with RBAC, Guardrails & Monitoring

**Project Name:** FinSolve Internal AI Assistant  
**Version:** 2.1  
**Date:** March 31, 2026  
**Audience:** Engineering Team  

| Version | Change Summary |
|---------|---------------|
| 1.0 | Initial requirements |
| 2.0 | Added conversation memory, rate limiting, error handling, CSV chunking, embedding versioning, prompt versioning, chunk explainability, log retention, golden dataset governance, health/readiness endpoints, local dev setup |
| 2.1 | Replaced self-hosted Qdrant on EC2 with Qdrant Cloud managed free tier; updated architecture diagram, env vars, Terraform modules, docker-compose, local dev setup, and `.env.example` template accordingly |

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Data & Document Inventory](#3-data--document-inventory)
   - 3.4 Table-Aware Chunking for Structured Data
   - 3.5 Embedding Model Versioning & Re-ingestion Strategy
4. [Role-Based Access Control (RBAC)](#4-role-based-access-control-rbac)
5. [RAG Pipeline Requirements](#5-rag-pipeline-requirements)
   - 5.3 System Prompt Template + Prompt Versioning
   - 5.5 Conversation Memory & Multi-turn Context
   - 5.6 Error Handling & Fallback Behaviour
6. [Guardrails & Safety Requirements](#6-guardrails--safety-requirements)
7. [Frontend Requirements](#7-frontend-requirements)
8. [Monitoring & Evaluation Requirements](#8-monitoring--evaluation-requirements)
   - 8.1 LangSmith Tracing + Chunk Explainability + Log Retention
   - 8.2 Ragas Evaluation Suite + Golden Dataset Maintenance
9. [AWS Deployment Requirements](#9-aws-deployment-requirements)
   - 9.3 Health & Readiness Endpoints
   - 9.4 Redis (ElastiCache)
   - 9.6 API Rate Limiting & Abuse Prevention
10. [Cost Monitoring Requirements](#10-cost-monitoring-requirements)
11. [CI/CD & Evaluation Gates](#11-cicd--evaluation-gates)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Tech Stack Summary](#13-tech-stack-summary)
14. [Milestones & Delivery Phases](#14-milestones--delivery-phases)
15. [Local Development Setup](#15-local-development-setup)

---

## 1. Project Overview

### 1.1 Purpose

Build a production-grade internal AI chatbot for **FinSolve Technologies** that allows employees to query private company documents using Retrieval-Augmented Generation (RAG). Access to sensitive data is governed by Role-Based Access Control (RBAC), and the system is protected by guardrails that prevent PII leakage and out-of-scope queries. The system is deployed on AWS with full observability via LangSmith and evaluated continuously via Ragas.

### 1.2 Business Goals

- Reduce time employees spend searching internal documents
- Enforce information security policies programmatically — not by trust alone
- Provide C-level executives with a unified view across all company data
- Create a reusable, observable AI infrastructure pattern for future internal tools

### 1.3 Users & Roles

| Role | Description | Example Users |
|------|-------------|---------------|
| `finance` | Access to financial reports and marketing spend data | CFO, Finance Analysts |
| `hr` | Access to employee data, payroll, handbook | HR Managers, HR Business Partners |
| `marketing` | Access to marketing reports and campaign data | CMO, Marketing Managers |
| `engineering` | Access to engineering documentation | Tech Leads, Engineers |
| `executive` | Full access to all company data | CEO, CTO, Board Members |

### 1.4 Scope

**In scope:**
- RAG pipeline over FinSolve's internal documents
- RBAC enforcement at query and retrieval time
- PII detection and redaction guardrail
- Out-of-scope query detection and rejection
- React web frontend with role-based login
- AWS deployment (ECS + managed services)
- LangSmith tracing and Ragas evaluation suite
- Token cost tracking and alerting

**Out of scope:**
- Real SSO / identity provider integration (mocked for this project)
- Multi-tenancy across different companies
- Document upload UI (ingestion is a CLI/pipeline step)

---

## 2. System Architecture

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        User (Browser)                           │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS
┌───────────────────────────────▼─────────────────────────────────┐
│                   React Frontend (AWS Amplify)                   │
│          Login → Role Assignment → Chat UI → Citations          │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST API
┌───────────────────────────────▼─────────────────────────────────┐
│              FastAPI Backend (AWS ECS / Fargate)                 │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Auth/RBAC   │  │ Guardrails   │  │   RAG Chain            │  │
│  │ Middleware  │  │ Layer        │  │   (LangChain)          │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────┐  ┌─────────────────────────────┐  │
│  │  Rate Limiter Middleware  │  │  LangSmith Tracing (all)    │  │
│  └──────────────────────────┘  └─────────────────────────────┘  │
└────────┬───────────────────────────┬──────────────┬─────────────┘
         │                           │              │
┌────────────────────┐  ┌────────────▼────────┐  ┌─▼──────────────────┐
│   Qdrant Cloud     │  │   Groq API           │  │  Redis             │
│   (Managed, Free)  │  │   LLaMA 3.1 70B      │  │  (ElastiCache)     │
│   Vector Store     │  └─────────────────────-┘  │  Session Memory    │
│   + RBAC filter    │                             │  Rate Limit State  │
└────────┬───────────┘                             └────────────────────┘
         │
┌────────▼──────────────────────────────────────────────────────────────┐
│            AWS S3 — Raw document storage + ingestion logs              │
└───────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Frontend | React + TypeScript | Chat UI, login, role display, citation rendering |
| API Server | FastAPI (Python) | Auth, RBAC filtering, request orchestration |
| RAG Chain | LangChain | Retrieval, prompt construction, LLM call |
| Vector DB | Qdrant Cloud (managed, free tier) | Document chunk storage with role-tagged metadata |
| LLM | LLaMA 3.1 70B via Groq | Answer generation |
| Session Memory | Redis (ElastiCache) | Per-session chat history, rate limit counters |
| Observability | LangSmith | Full trace capture per query |
| Evaluation | Ragas | Automated RAG quality scoring |
| Document Storage | AWS S3 | Source documents, ingestion artifacts |
| Container Runtime | AWS ECS + Fargate | Backend deployment |
| Cost Tracking | AWS CloudWatch + custom | Token usage metrics and alerts |

---

## 3. Data & Document Inventory

### 3.1 Source Documents (from project knowledge)

| File | Department Tag | Sensitivity |
|------|---------------|-------------|
| `financial_summary.md` | `finance` | High |
| `quarterly_financial_report.md` | `finance` | High |
| `market_report_q4_2024.md` | `marketing`, `finance` | Medium |
| `marketing_report_2024.md` | `marketing` | Medium |
| `marketing_report_q1_2024.md` | `marketing` | Medium |
| `marketing_report_q2_2024.md` | `marketing` | Medium |
| `marketing_report_q3_2024.md` | `marketing` | Medium |
| `employee_handbook.md` | `hr` | Medium |
| `hr_data.csv` | `hr` | High — contains PII (salary, DOB, performance) |
| `engineering_master_doc.md` | `engineering` | Low |

### 3.2 Document Metadata Schema

Each chunk stored in Qdrant must carry this metadata payload:

```json
{
  "doc_id": "financial_summary_chunk_003",
  "source_file": "financial_summary.md",
  "allowed_roles": ["finance", "executive"],
  "department": "finance",
  "sensitivity": "high",
  "chunk_index": 3,
  "total_chunks": 12,
  "ingested_at": "2026-03-31T10:00:00Z"
}
```

### 3.3 Ingestion Pipeline

```
S3 Bucket (raw docs)
      │
      ▼
Docling / LangChain Document Loaders
      │  (PDF, Markdown, CSV parsers)
      ▼
Text Chunking (RecursiveCharacterTextSplitter)
  - chunk_size: 512 tokens
  - chunk_overlap: 64 tokens
      │
      ▼
Embedding (sentence-transformers/all-MiniLM-L6-v2 or
           nomic-embed-text via Groq/Ollama)
      │
      ▼
Qdrant Upsert with metadata payload
  - Collection per sensitivity tier OR
  - Single collection + metadata filtering (recommended)
```

**Ingestion is a standalone CLI script**, not triggered by the API server. It runs as a one-time or scheduled batch job.

### 3.4 Table-Aware Chunking for Structured Data

`RecursiveCharacterTextSplitter` is designed for prose and produces malformed chunks from CSV/tabular data. The `hr_data.csv` file and any future tabular documents require a dedicated chunking strategy.

#### Strategy: Row-per-Chunk with Header Prepending

Each CSV row becomes one chunk. The column headers are prepended to every row chunk so the LLM always has field context, even without surrounding rows.

```python
import csv

def chunk_csv(filepath: str, metadata: dict) -> list[dict]:
    chunks = []
    with open(filepath) as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for i, row in enumerate(reader):
            # Format: "employee_id: FINEMP1001 | full_name: Isha Chowdhury | role: Credit Officer ..."
            row_text = " | ".join(f"{k}: {v}" for k, v in row.items())
            chunks.append({
                "text": f"Columns: {', '.join(headers)}\nRow {i}: {row_text}",
                "metadata": {**metadata, "chunk_index": i, "row_id": row.get("employee_id", str(i))}
            })
    return chunks
```

#### PII Sensitivity Flag on CSV Chunks

Because `hr_data.csv` contains salary, date of birth, and performance ratings, each chunk from this file must carry an additional metadata flag:

```json
{
  "contains_pii": true,
  "pii_fields": ["salary", "date_of_birth", "performance_rating"]
}
```

The output guardrail checks this flag and applies stricter Presidio redaction rules before any HR data chunk content reaches the LLM response.

#### Chunking Strategy by Document Type

| Document Type | Chunking Method | Tool |
|--------------|----------------|------|
| Markdown (`.md`) | `RecursiveCharacterTextSplitter` by heading then paragraph | LangChain |
| CSV (`.csv`) | Row-per-chunk with header prepend | Custom (above) |
| PDF | Page-aware split, then paragraph | Docling |
| Future: Excel | Sheet-per-section, row-per-chunk | Docling + custom |

### 3.5 Embedding Model Versioning & Re-ingestion Strategy

If the embedding model is changed, all existing vectors become semantically misaligned with new query embeddings. This must be managed explicitly.

#### Versioning Approach

- The embedding model name and version are stored as a collection-level metadata field in Qdrant:

```json
{
  "collection_name": "finsolve_docs",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_model_version": "1.0.0",
  "ingested_at": "2026-03-31T10:00:00Z"
}
```

- At query time, the API server reads this metadata and asserts it matches the configured embedding model. If there is a mismatch, the query is rejected with a `503 MODEL_VERSION_MISMATCH` error and a CloudWatch alarm `EmbeddingModelMismatch` is triggered.

#### Re-ingestion Trigger Conditions

A full re-ingestion run is required when any of the following occur:

| Trigger | Action |
|---------|--------|
| Embedding model upgraded | Full re-ingestion into a new collection; swap collection name after validation |
| Source document updated or replaced | Partial re-ingestion: delete old chunks by `source_file`, re-ingest updated file |
| New document added | Incremental ingestion: append new chunks only |
| Chunk size / overlap parameters changed | Full re-ingestion required |

#### Blue-Green Collection Strategy for Model Upgrades

To avoid downtime during a full re-ingestion on Qdrant Cloud:

```
1. Ingest all documents into new collection: finsolve_docs_v2
   (Qdrant Cloud supports multiple collections on the free tier)
2. Run Ragas evaluation pointing QDRANT_COLLECTION=finsolve_docs_v2
3. If eval passes → update QDRANT_COLLECTION secret to finsolve_docs_v2
                  → redeploy ECS service (picks up new secret)
4. Keep finsolve_docs_v1 for 7 days (rollback: revert the secret)
5. Delete finsolve_docs_v1 via Qdrant Cloud console or API
```

---

## 4. Role-Based Access Control (RBAC)

### 4.1 Access Matrix

| Data Source | `finance` | `hr` | `marketing` | `engineering` | `executive` |
|-------------|-----------|------|-------------|---------------|-------------|
| Financial Summary | ✅ | ❌ | ❌ | ❌ | ✅ |
| Quarterly Financial Report | ✅ | ❌ | ❌ | ❌ | ✅ |
| Marketing Reports (all quarters) | ❌ | ❌ | ✅ | ❌ | ✅ |
| Employee Handbook | ❌ | ✅ | ❌ | ❌ | ✅ |
| HR Data (PII CSV) | ❌ | ✅ | ❌ | ❌ | ✅ |
| Engineering Master Doc | ❌ | ❌ | ❌ | ✅ | ✅ |

> **Note:** `finance` role can access marketing reports that contain marketing spend figures, since those are embedded in financial summaries.

### 4.2 RBAC Enforcement Layers

RBAC must be enforced at **two independent layers** — failing either blocks the query:

**Layer 1 — Retrieval Filter (Qdrant metadata filter)**

Before sending retrieved chunks to the LLM, filter by `allowed_roles` field:

```python
from qdrant_client.models import Filter, FieldCondition, MatchAny

def build_role_filter(user_role: str) -> Filter:
    return Filter(
        must=[
            FieldCondition(
                key="allowed_roles",
                match=MatchAny(any=[user_role])
            )
        ]
    )
```

**Layer 2 — Response Validation (Post-generation check)**

After the LLM generates a response, a validation step checks that the answer does not reference document sources outside the user's allowed set. If the LLM hallucinates a reference to a forbidden document, the response is blocked and replaced with an access-denied message.

### 4.3 Authentication (Mocked for this project)

- Login form accepts `username` + `role` (dropdown)
- Backend issues a signed JWT containing `{ user_id, role, exp }`
- JWT secret stored in AWS Secrets Manager
- All API endpoints require `Authorization: Bearer <token>` header
- Token expiry: 8 hours

```python
# JWT payload structure
{
  "sub": "user_123",
  "role": "finance",        # single role per user for this project
  "iat": 1743410000,
  "exp": 1743438800
}
```

### 4.4 Access Denial Behavior

When a user asks a question about data outside their role:

- Return a clear, non-leaking denial message: `"You don't have access to information in that area. Please contact your administrator if you need access."`
- Do NOT reveal what documents exist or what data they contain
- Log the denied access attempt to LangSmith with tag `rbac_denied`

---

## 5. RAG Pipeline Requirements

### 5.1 Pipeline Steps

```
User Query
    │
    ▼
[1] Input Guardrail Check
    │  - PII detection
    │  - Out-of-scope detection
    │  - Prompt injection detection
    ▼
[2] Query Rewriting (optional)
    │  - HyDE (Hypothetical Document Embeddings) or simple rewrite
    ▼
[3] Embedding of (rewritten) query
    │  - Same model as ingestion
    ▼
[4] Qdrant Retrieval with RBAC metadata filter
    │  - top_k: 5 chunks
    │  - similarity threshold: 0.6
    ▼
[5] Context Assembly
    │  - Deduplication of chunks
    │  - Source attribution tagging
    ▼
[6] Prompt Construction (see 5.3)
    ▼
[7] LLM Call (Groq / LLaMA 3.1 70B)
    ▼
[8] Output Guardrail Check
    │  - PII in response
    │  - Forbidden source reference check
    ▼
[9] Response + Citations returned to frontend
```

### 5.2 Retrieval Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `top_k` | 5 | Balance between context richness and token budget |
| `similarity_threshold` | 0.60 | Reject low-confidence chunks (dense-only mode) |
| `chunk_size` | 512 tokens | Fits within context without losing coherence |
| `chunk_overlap` | 64 tokens | Preserve sentence boundary context |
| `embedding_model` | `all-MiniLM-L6-v2` | Fast, free, good quality for English enterprise docs |
| `reranker` | `cross-encoder/ms-marco-MiniLM-L-6-v2` (optional) | Improve chunk relevance ordering |
| `hybrid_search` | Optional BM25 + Dense RRF (off by default) | See Section 5.2a |

#### 5.2a Hybrid Search (Optional Feature)

Dense vector search alone can miss relevant chunks when query terminology diverges from document text. BM25 sparse keyword search complements dense search by excelling at exact keyword matching.

**Feature Flag:** `ENABLE_HYBRID_SEARCH=false` (default) — no impact on existing dense-only retrieval.

**When to Enable:**
- If dense-only retrieval produces consistently incomplete results for keyword-heavy queries
- If the evaluation suite (Ragas) shows low `context_recall` due to terminological mismatches
- Enabling requires full re-ingestion: `uv run python -m ingest.ingest --reset`

**Architecture:**
- Uses Qdrant's native **Reciprocal Rank Fusion (RRF)** to fuse dense and sparse results
- BM25 sparse vectors computed via `fastembed` library (`Qdrant/bm25` ONNX model)
- RBAC filter applied inside each Prefetch arm (role isolation preserved)
- No `score_threshold` in hybrid mode (incompatible with Fusion; RRF produces rank-based scores)
- Prefetch multiplier: `hybrid_prefetch_limit_multiplier=2` (each arm pre-fetches `top_k × 2`)

**Configuration:**
```ini
ENABLE_HYBRID_SEARCH=false
BM25_MODEL=Qdrant/bm25
HYBRID_PREFETCH_LIMIT_MULTIPLIER=2
```

**Collateral Changes:**
- Qdrant collection schema bumped from v1 → v2 when hybrid enabled (stored in metadata sentinel)
- Old collections must be reset to support sparse vector field
- Integration tests remain green (RBAC, answer quality, source validation all preserved)

### 5.3 System Prompt Template

```
You are FinSolve's internal AI assistant. You answer questions strictly
based on the provided company documents. You do not use outside knowledge.

Rules:
1. Only use information from the CONTEXT below.
2. If the context does not contain the answer, say: "I don't have enough
   information in the available documents to answer that."
3. Never reveal salary, personal identification numbers, dates of birth,
   or other PII in your response, even if present in context.
4. Always cite the source document for each claim using [Source: <filename>].
5. Be concise and professional.

User Role: {role}
User Question: {question}

CONTEXT:
{context}
```

#### Prompt Versioning

Prompts are a first-class artifact — changes to prompts can silently degrade quality without a code change. All prompt versions must be tracked and evaluated.

- **Storage:** Prompts are version-controlled in the git repo at `/backend/prompts/system_prompt_v{N}.txt`
- **Active version:** The active prompt version is set via environment variable `PROMPT_VERSION=v3` (stored in Secrets Manager); no code change required to roll back
- **LangSmith Prompt Hub:** Optionally push prompts to LangSmith Prompt Hub for collaborative editing and A/B comparison
- **Change policy:** Any change to the system prompt must:
  1. Increment the version number
  2. Be committed to git with a description of what changed and why
  3. Automatically trigger a full Ragas evaluation run on staging before merging
  4. Include a comparison of Ragas scores (new vs. previous version) in the PR description
- **LangSmith trace attribution:** Every trace includes `prompt_version: "v3"` so degradations can be correlated to specific prompt changes

```python
# Prompt loading at runtime
import os

PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")
prompt_path = f"prompts/system_prompt_{PROMPT_VERSION}.txt"
with open(prompt_path) as f:
    system_prompt = f.read()
```

### 5.4 LangChain Chain Design

```python
chain = (
    RunnablePassthrough.assign(
        context=retriever_with_rbac_filter | format_docs
    )
    | prompt_template
    | groq_llm
    | output_guardrail
    | StrOutputParser()
)
```

All steps must be wrapped with LangSmith tracing callbacks.

### 5.5 Conversation Memory & Multi-turn Context

The chatbot must support multi-turn conversations within a session. Each follow-up question must be answerable in the context of prior exchanges (e.g., "What about Q3?" after asking about Q4).

#### Memory Strategy

Use a **sliding window buffer** of the last 6 message pairs (user + assistant), passed as `chat_history` in the prompt. If the conversation exceeds 6 pairs, drop the oldest pair. This keeps token usage bounded while preserving enough context for natural follow-up.

```python
# LangChain memory setup
from langchain.memory import ConversationBufferWindowMemory

memory = ConversationBufferWindowMemory(
    k=6,                          # retain last 6 exchanges
    memory_key="chat_history",
    return_messages=True,
    output_key="answer"
)
```

#### Updated Prompt Template (with history)

```
You are FinSolve's internal AI assistant.

CHAT HISTORY:
{chat_history}

CONTEXT (retrieved documents):
{context}

User Role: {role}
Current Question: {question}

Answer using only the CONTEXT. If the answer is not in the context,
say so. Cite sources using [Source: <filename>].
```

#### Memory Isolation Rules

- Memory is stored **server-side per session ID**, keyed as `session:{session_id}:history`
- Session IDs are generated at login and bound to the JWT (`session_id` claim)
- Memory is stored in **Redis** (AWS ElastiCache) with a TTL of 8 hours (matching JWT expiry)
- On logout or JWT expiry, the session memory is flushed
- Memory from one user's session is never accessible to another user, regardless of role
- The `executive` role does not inherit or see history from other roles' sessions

#### Memory Schema (Redis entry)

```json
{
  "session_id": "sess_abc123",
  "user_role": "finance",
  "history": [
    {"role": "user", "content": "What was Q4 net income?"},
    {"role": "assistant", "content": "Q4 net income was $325M... [Source: quarterly_financial_report.md]"}
  ],
  "created_at": "2026-03-31T09:00:00Z",
  "last_active": "2026-03-31T09:15:00Z"
}
```

#### LangSmith Tracing for Memory

Each trace must include:
- `session_id` — to group turns of the same conversation
- `turn_index` — which turn within the session (0-indexed)
- `history_length` — number of prior pairs included in this call

### 5.6 Error Handling & Fallback Behaviour

All failure modes must be handled gracefully — no raw stack traces or internal error details should ever reach the frontend.

#### LLM Failures (Groq API)

| Failure Type | Behaviour |
|-------------|-----------|
| Groq API timeout (> 10s) | Retry once with 2s backoff; if still failing, return user-friendly error |
| Groq rate limit (429) | Return: `"The assistant is temporarily busy. Please try again in a moment."` + log to CloudWatch |
| Groq API down (5xx) | Return same user message + trigger `GroqAPIDown` CloudWatch alarm |
| No fallback LLM | For this project scope, no secondary LLM; queue retries not required |

#### Vector DB Failures (Qdrant)

| Failure Type | Behaviour |
|-------------|-----------|
| Qdrant unreachable | Return: `"Document search is temporarily unavailable."` + trigger `QdrantDown` alarm |
| Query timeout (> 3s) | Retry once; if still timing out, return error message |
| Empty result (no chunks above threshold) | Return: `"I couldn't find relevant information to answer that."` — **not** an error, handled in Section 6.2.3 |

#### General API Errors

- All unhandled exceptions must be caught at the FastAPI middleware level
- Log full traceback to CloudWatch Logs; return only a generic `500` message to the client
- Error response schema:

```json
{
  "error": true,
  "code": "UPSTREAM_UNAVAILABLE",
  "message": "The assistant is temporarily unavailable. Please try again shortly.",
  "request_id": "req_xyz789"
}
```

- `request_id` is a UUID generated per request, included in all logs and LangSmith traces for correlation

#### Retry Policy

```python
# Applied to Groq LLM calls and Qdrant queries
MAX_RETRIES = 1
RETRY_BACKOFF_SECONDS = 2
TIMEOUT_SECONDS = 10   # LLM
QDRANT_TIMEOUT_SECONDS = 3
```

---

## 6. Guardrails & Safety Requirements

### 6.1 Input Guardrails

#### 6.1.1 PII Detection on User Input

Detect and block queries that attempt to extract PII in bulk:

- **Tool:** `presidio-analyzer` (Microsoft) or `spacy` NER
- **Detected entities:** PERSON, EMAIL, PHONE, AADHAAR, PAN, SALARY, DATE_OF_BIRTH
- **Action on detection:** Warn user, do not block unless the query is clearly a bulk extraction attempt (e.g., "list all employee salaries")

#### 6.1.2 Out-of-Scope Detection

Classify queries as in-scope or out-of-scope before retrieval:

- **Method:** LLM-based classifier (lightweight prompt) or keyword/embedding similarity to a curated list of scope examples
- **In-scope topics:** Financial performance, marketing metrics, HR policies, employee records (for HR), engineering architecture
- **Out-of-scope examples:** General knowledge questions, coding help, competitor research, personal advice
- **Action:** Return: `"This assistant is designed for FinSolve internal documents only. I'm not able to help with that query."`

#### 6.1.3 Prompt Injection Detection

Detect attempts to override system instructions:

- Pattern-match for phrases like: `"ignore previous instructions"`, `"you are now"`, `"disregard your rules"`, `"pretend you are"`
- If detected: block the query, log with tag `prompt_injection_attempt`

### 6.2 Output Guardrails

#### 6.2.1 PII Redaction in Response

Before returning any LLM response to the frontend:

- Run `presidio-anonymizer` over the response text
- Redact or mask: salary figures tied to names, Aadhaar/PAN numbers, personal phone numbers, dates of birth
- Exception: aggregate figures (e.g., "average salary of the department") are allowed

#### 6.2.2 Source Boundary Enforcement

- Parse the response for any source citations `[Source: ...]`
- Cross-check every cited source against the user's `allowed_roles`
- If a forbidden source is cited → block the response, return generic denial

#### 6.2.3 Hallucination Containment

- If no chunks pass the `similarity_threshold`, do not call the LLM
- Return: `"I couldn't find relevant information in the documents to answer your question."`

### 6.3 Guardrail Decision Flow

```
Input Query
    ├── Prompt injection? → BLOCK
    ├── Out-of-scope? → REJECT with message
    └── Proceed to retrieval
              │
              ▼
         Retrieved Chunks
              ├── No chunks above threshold? → REJECT with "no info" message
              └── Proceed to LLM
                        │
                        ▼
                   LLM Response
                        ├── PII in response? → REDACT then return
                        ├── Forbidden source cited? → BLOCK
                        └── Return response to user
```

---

## 7. Frontend Requirements

### 7.1 Pages & Components

#### Login Page
- Username field (text input)
- Role selector (dropdown: Finance, HR, Marketing, Engineering, Executive)
- "Sign In" button
- On success: stores JWT in memory (not localStorage), redirects to chat
- Display role badge in the header throughout the session

#### Chat Interface
- Message thread (user messages right-aligned, assistant left-aligned)
- Markdown rendering for assistant responses
- Citation panel: collapsible sidebar showing source documents and relevant chunks
- Role indicator badge (e.g., "Logged in as: Finance Analyst")
- Clear chat button
- Loading state with streaming response support (SSE or WebSocket)

#### Access Denied State
- Inline denial message with soft styling
- No modal interruption — denial appears in the chat thread naturally

### 7.2 UX Rules

- The frontend must never show raw chunk text or internal metadata to the user
- Citations should show: filename, section title (if available), and a short excerpt
- Users should see their role clearly at all times so they understand why access is denied
- Response time indicator (e.g., "Answered in 2.3s")

### 7.3 Tech Stack

- React 18 + TypeScript
- Tailwind CSS for styling
- Axios for API calls
- React Query for data fetching / caching
- Deployed on AWS Amplify or served via S3 + CloudFront

---

## 8. Monitoring & Evaluation Requirements

### 8.1 LangSmith Tracing

Every query must be traced end-to-end in LangSmith. Required trace attributes:

| Attribute | Description |
|-----------|-------------|
| `user_role` | Role of the authenticated user |
| `query` | The original user query |
| `retrieved_chunks` | List of chunk IDs and similarity scores |
| `guardrail_triggered` | Which guardrail fired (if any) |
| `rbac_denied` | Boolean — whether RBAC blocked retrieval |
| `llm_model` | Model name and version used |
| `input_tokens` | Tokens in the prompt |
| `output_tokens` | Tokens in the response |
| `latency_ms` | Total pipeline latency |
| `ragas_scores` | Evaluation scores (async, attached post-evaluation) |

All traces must be tagged with `environment: production | staging | dev`.

#### Chunk Retrieval Explainability

Every trace must include per-chunk retrieval metadata to support debugging and Ragas evaluation:

```json
"retrieved_chunks": [
  {
    "chunk_id": "financial_summary_chunk_003",
    "source_file": "financial_summary.md",
    "similarity_score": 0.87,
    "rank": 1,
    "passed_threshold": true,
    "allowed_role_match": true,
    "excerpt": "Net income grew to $1.15 billion, up 14% YoY..."
  },
  {
    "chunk_id": "quarterly_financial_report_chunk_011",
    "source_file": "quarterly_financial_report.md",
    "similarity_score": 0.54,
    "rank": 2,
    "passed_threshold": false,
    "allowed_role_match": true,
    "excerpt": "..."
  }
]
```

- Chunks that **fail** the similarity threshold must still be logged (with `passed_threshold: false`) so retrieval gaps are visible
- Chunks that fail the RBAC filter must be logged with `allowed_role_match: false` — this is the audit trail for access enforcement
- These scores feed directly into the Ragas `context_precision` and `context_recall` calculations
- **PII rule:** chunk `excerpt` fields in LangSmith traces must be truncated to 200 characters and run through the Presidio anonymizer before logging

#### Compliance Log Retention & Access Control

| Log Type | Retention Period | Storage | Who Can Access |
|----------|-----------------|---------|----------------|
| LangSmith traces (all queries) | 90 days | LangSmith cloud | Engineering Lead only |
| CloudWatch application logs | 30 days hot, 1 year cold (S3) | AWS CloudWatch + S3 | Engineering + Security team |
| RBAC denial logs | 1 year | CloudWatch + S3 | Security team + HR (for their domain) |
| Guardrail trigger logs | 1 year | CloudWatch + S3 | Security team |
| Cost/token logs | 2 years | CloudWatch + S3 | Engineering + Finance |

- All logs in S3 must be encrypted at rest (AES-256, AWS KMS)
- LangSmith traces must **never** contain raw PII — anonymize before trace export (see PII rule above)
- Access to CloudWatch log groups is restricted via IAM roles — developers cannot query production logs without elevated access
- A quarterly log audit is required to verify no PII leakage into traces

### 8.2 Ragas Evaluation Suite

Ragas evaluations run automatically on every deployment against a **golden dataset** of 30 curated QA pairs (10 per role: finance, hr, marketing).

#### Metrics to Track

| Metric | Target Threshold | Description |
|--------|-----------------|-------------|
| `faithfulness` | ≥ 0.80 | Answer is grounded in retrieved context |
| `answer_relevancy` | ≥ 0.75 | Answer addresses the question asked |
| `context_precision` | ≥ 0.70 | Retrieved chunks are relevant to the query |
| `context_recall` | ≥ 0.70 | All relevant chunks were retrieved |
| `answer_correctness` | ≥ 0.75 | Answer matches the ground truth |

#### Golden Dataset Format (per QA pair)

```json
{
  "question": "What was FinSolve's net income in Q4 2024?",
  "ground_truth": "$325 million, up 18% YoY",
  "required_role": "finance",
  "source_doc": "quarterly_financial_report.md"
}
```

#### Evaluation Pipeline

```
New deployment triggered
        │
        ▼
Run Ragas eval script against staging endpoint
        │
        ├── All metrics ≥ thresholds? → Pass → Promote to production
        │
        └── Any metric below threshold? → Fail → Block deployment
                                              → Notify via CloudWatch alarm
                                              → Post failure summary to LangSmith
```

#### Golden Dataset Ownership & Maintenance

- **Storage:** Versioned in the git repo at `/evals/golden_dataset.json` — treated as code, not a config file
- **Owner:** Engineering Lead is accountable; each department (Finance, HR, Marketing) nominates a reviewer to validate their domain's QA pairs for accuracy
- **Update triggers:** The dataset must be reviewed and updated whenever:
  - A source document is modified or replaced
  - A new document is added to the ingestion pipeline
  - A Ragas metric drops below threshold (investigate whether ground truth is stale)
- **Versioning:** Each dataset version is tagged with a semver string (e.g., `dataset_v1.2.0`) stored in the JSON header; LangSmith evaluation runs reference this version tag for traceability
- **Minimum coverage:** At least 3 QA pairs per source document; at least 2 pairs that specifically test cross-document reasoning (e.g., a question whose answer requires combining two chunks)
- **Reference-free vs. reference-required split:** 20 pairs include `ground_truth` (for `answer_correctness`); 10 pairs are reference-free (for `faithfulness` + `answer_relevancy` only)

```json
{
  "dataset_version": "1.2.0",
  "last_updated": "2026-03-31",
  "updated_by": "engineering-lead",
  "pairs": [...]
}
```



Separate from Ragas, a set of **role boundary tests** run on every deployment:

- For each role, send 5 queries about data they should NOT have access to
- Assert that all 5 return denial messages, not actual data
- If any test returns forbidden data → deployment is blocked immediately

---

## 9. AWS Deployment Requirements

### 9.1 Infrastructure Overview

```
AWS Account
├── VPC
│   ├── Public Subnet  → ALB (Application Load Balancer)
│   └── Private Subnet → ECS Fargate (FastAPI backend)
│                      → Redis (ElastiCache)
│
├── AWS Amplify        → React Frontend
├── AWS S3             → Raw document storage + ingestion logs
├── AWS Secrets Manager→ JWT secret, Groq API key, LangSmith API key,
│                        Qdrant API key + cluster URL
├── AWS CloudWatch     → Logs, Metrics, Alarms
└── AWS ECR            → Container registry for backend image

External Managed Services (outside VPC):
├── Qdrant Cloud       → Vector database (free tier, ~1GB)
├── Groq API           → LLM inference (LLaMA 3.1 70B)
└── LangSmith          → Tracing and evaluation
```

> **Note on Qdrant Cloud networking:** Because Qdrant Cloud is external to the VPC, all traffic between the ECS backend and Qdrant travels over HTTPS (TLS 1.3) using an API key. The Qdrant cluster URL and API key are stored in AWS Secrets Manager and injected at runtime. No inbound security group rules need to be opened — all connections are outbound from ECS.

### 9.2 Environment Variables (stored in Secrets Manager)

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | LLM API key (Groq) |
| `LANGSMITH_API_KEY` | Tracing API key |
| `LANGSMITH_PROJECT` | Project name in LangSmith |
| `JWT_SECRET` | HS256 signing secret |
| `QDRANT_URL` | Qdrant Cloud cluster URL (e.g. `https://xyz.eu-central.aws.cloud.qdrant.io`) |
| `QDRANT_API_KEY` | Qdrant Cloud API key (generated in Qdrant Cloud console) |
| `QDRANT_COLLECTION` | Name of the vector collection (`finsolve_docs`) |
| `EMBEDDING_MODEL` | Model name for embeddings |
| `REDIS_URL` | ElastiCache Redis endpoint |
| `PROMPT_VERSION` | Active prompt version (e.g. `v1`) |

### 9.3 ECS Task Definition (Backend)

- **CPU:** 1 vCPU  
- **Memory:** 2 GB  
- **Port:** 8000 (FastAPI)  
- **Health check:** `GET /health` → 200 OK  
- **Auto-scaling:** Scale out at 70% CPU, min 1 task, max 4 tasks  

#### Health & Readiness Endpoints

Two separate endpoints are required — the ALB uses `/health` for liveness, ECS uses `/ready` before routing traffic to a new task:

| Endpoint | Purpose | Checks |
|----------|---------|--------|
| `GET /health` | Liveness — is the process alive? | Returns `200 OK` immediately; no downstream checks |
| `GET /ready` | Readiness — is the service ready to serve traffic? | Checks Qdrant Cloud reachability (HTTPS ping) + Redis reachability + embedding model loaded |

```json
// GET /ready — healthy response
{
  "status": "ready",
  "checks": {
    "qdrant": "ok",
    "redis": "ok",
    "embedding_model": "ok"
  },
  "timestamp": "2026-03-31T10:00:00Z"
}

// GET /ready — degraded response (HTTP 503)
{
  "status": "not_ready",
  "checks": {
    "qdrant": "unreachable",
    "redis": "ok",
    "embedding_model": "ok"
  }
}
```

- ECS will not route traffic to a new task until `/ready` returns `200`
- If `/ready` returns `503` on an already-live task for > 60 seconds, ECS replaces the task

### 9.4 Redis (AWS ElastiCache)

Redis is required for two features added in this version: conversation memory (Section 5.5) and rate limiting (Section 9.6).

- **Instance type:** `cache.t3.micro` (sufficient for < 50 concurrent users)
- **Deployment:** Single-node in the private subnet (no replication needed for this project scope)
- **Persistence:** RDB snapshot every 15 minutes to S3 (so session memory survives a Redis restart)
- **TTL policy:** All keys set with TTL — session memory: 8 hours, rate limit counters: 1 hour / 24 hours
- **Security:** Not publicly accessible; only the ECS security group has inbound access on port 6379

### 9.5 Qdrant Cloud Setup (Managed Free Tier)

Qdrant Cloud replaces the self-hosted EC2 deployment. No EC2 instance, EBS volume, or security group inbound rules are needed for Qdrant.

#### Account & Cluster Setup

1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a **Free tier cluster** — choose the AWS region closest to your ECS deployment (e.g. `us-east-1`) to minimise latency
3. Note the **Cluster URL** (e.g. `https://xyz.us-east-1-0.aws.cloud.qdrant.io:6333`)
4. Generate an **API key** from the Qdrant Cloud console
5. Store both in AWS Secrets Manager as `QDRANT_URL` and `QDRANT_API_KEY`

#### Free Tier Constraints

| Limit | Value | Impact on this project |
|-------|-------|----------------------|
| Storage | 1 GB | ~100K chunks at 1536 dims; sufficient for 10 docs |
| Collections | Unlimited | No constraint |
| RAM | 256 MB | Adequate for HNSW index on this dataset size |
| Nodes | 1 (no HA) | Acceptable for a learning project |
| Uptime SLA | None (best effort) | Use retries + fallback message in production |

> **Data volume estimate:** 10 source documents → ~800 chunks × 384-dimensional vectors (`all-MiniLM-L6-v2`) × 4 bytes = ~1.2 MB of vector data. Well within the 1 GB free limit.

#### Python Client Connection

```python
from qdrant_client import QdrantClient
import os

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
```

#### Collection Configuration

```python
from qdrant_client.models import VectorParams, Distance

client.recreate_collection(
    collection_name="finsolve_docs",
    vectors_config=VectorParams(
        size=384,              # all-MiniLM-L6-v2 output dimension
        distance=Distance.COSINE,
    ),
)
```

#### Backup Strategy

Since there is no EBS snapshot, backups are handled via Qdrant Cloud's built-in snapshot API:

```python
# Trigger a snapshot (store reference for restore if needed)
client.create_snapshot(collection_name="finsolve_docs")
```

- Run snapshot after every ingestion run
- Snapshot URLs are accessible from the Qdrant Cloud console
- For this project, manual snapshots before major changes are sufficient

#### Local Dev vs. Cloud Qdrant

| Environment | Qdrant Endpoint | Auth |
|-------------|----------------|------|
| Local (docker-compose) | `http://localhost:6333` | None (no API key needed) |
| Staging / Production | Qdrant Cloud URL | `QDRANT_API_KEY` required |

The `QDRANT_API_KEY` env var is left empty in the local `.env` file — the Python client omits the header when the key is `None`, which is correct for the local Docker instance.

```python
# Handles both local (no key) and cloud (with key) transparently
client = QdrantClient(
    url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    api_key=os.getenv("QDRANT_API_KEY") or None,  # None → no auth header sent
)
```

### 9.6 API Rate Limiting & Abuse Prevention

Rate limiting is enforced at the **ALB + FastAPI middleware** level to protect Groq quota and control costs.

#### Per-User Limits

| Limit | Value | Window | Action on Breach |
|-------|-------|--------|-----------------|
| Queries per user | 30 | Per hour | HTTP 429 + `Retry-After` header |
| Queries per user | 100 | Per day | HTTP 429 + email notification to admin |
| Max input length | 1000 characters | Per query | HTTP 400 with message: `"Query too long."` |
| Max concurrent sessions per user | 2 | Active at once | Reject new login, prompt to log out existing |

#### Per-Role Limits

| Role | Max Queries/Hour | Rationale |
|------|-----------------|-----------|
| `finance` | 50 | Higher volume expected |
| `hr` | 30 | Moderate usage |
| `marketing` | 30 | Moderate usage |
| `engineering` | 30 | Moderate usage |
| `executive` | 100 | Unrestricted for C-level |

#### Implementation

- Rate limit state stored in **Redis** (same ElastiCache instance as memory)
- Key structure: `ratelimit:{user_id}:hourly` and `ratelimit:{user_id}:daily`
- Use sliding window counter (not fixed window) to avoid burst at window boundaries

```python
# Rate limit response
HTTP 429 Too Many Requests
{
  "error": true,
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "You have exceeded the query limit. Please wait before trying again.",
  "retry_after_seconds": 120
}
```

- All rate limit breaches logged to CloudWatch with metric `RateLimitBreaches`
- If a single user triggers > 5 rate limit events in an hour, flag for manual review in LangSmith with tag `abuse_suspected`

### 9.7 Infrastructure as Code

All AWS infrastructure defined in **Terraform** modules:

- `modules/networking` — VPC, subnets, security groups
- `modules/ecs` — Task definition, service, ALB
- `modules/redis` — ElastiCache subnet group, replication group, security group
- `modules/secrets` — Secrets Manager entries (including Qdrant Cloud URL + API key)
- `modules/monitoring` — CloudWatch dashboards, alarms, SNS topics

> **Note:** Qdrant Cloud is provisioned manually via the web console (not Terraform), since the free tier does not expose a Terraform provider for cluster creation. The cluster URL and API key are stored in Secrets Manager and referenced by the `modules/secrets` module.

---

## 10. Cost Monitoring Requirements

### 10.1 Token Usage Tracking

Every LLM call must log to CloudWatch custom metrics:

```
Namespace: FinSolveAI/TokenUsage
Metrics:
  - InputTokens (count, per query)
  - OutputTokens (count, per query)
  - TotalTokensCost (USD, computed: tokens × model rate)
  - QueriesPerHour (count)
```

### 10.2 Cost Estimation Formula

```python
# Groq LLaMA 3.1 70B pricing (approximate, check current rates)
INPUT_COST_PER_1K  = 0.00059   # USD per 1K input tokens
OUTPUT_COST_PER_1K = 0.00079   # USD per 1K output tokens

query_cost = (
    (input_tokens / 1000 * INPUT_COST_PER_1K) +
    (output_tokens / 1000 * OUTPUT_COST_PER_1K)
)
```

### 10.3 CloudWatch Alarms

| Alarm | Condition | Action |
|-------|-----------|--------|
| `HighDailyCost` | Daily spend > $5 USD | SNS email alert to admin |
| `HighHourlyQueries` | > 200 queries/hour | SNS email + auto-throttle |
| `AbnormalTokenUsage` | Single query > 4000 tokens | Log to LangSmith, flag for review |
| `ECSHighCPU` | ECS CPU > 85% for 5 min | Scale out + alert |
| `QdrantCloudUnreachable` | `/ready` returns Qdrant check failed for > 60s | SNS alert + page on-call |
| `EmbeddingModelMismatch` | Collection metadata model ≠ configured model | SNS alert + block queries |

### 10.4 Cost Dashboard

A CloudWatch dashboard named `FinSolveAI-Costs` with:
- Daily token spend (line chart)
- Queries per hour (bar chart)
- Spend by role segment (breakdown)
- Month-to-date total cost

---

## 11. CI/CD & Evaluation Gates

### 11.1 Pipeline (GitHub Actions)

```yaml
Trigger: Push to main or PR merge

Jobs:
  1. lint-and-test
     - Ruff / Black (Python linting)
     - Pytest (unit tests for RBAC logic, guardrails, chain)
     - Coverage threshold: 80%

  2. build-and-push
     - Docker build of FastAPI backend
     - Push to AWS ECR

  3. deploy-staging
     - Terraform apply (staging workspace)
     - ECS service update (new task revision)

  4. run-evaluations
     - Ragas eval against staging endpoint
     - RBAC boundary tests
     - Assert all thresholds pass

  5. promote-to-production (manual approval gate)
     - Terraform apply (prod workspace)
     - ECS service update
     - Post deployment summary to LangSmith
```

### 11.2 Evaluation Failure Behavior

- If `run-evaluations` fails → pipeline stops, production is NOT updated
- Failure report is posted as a GitHub Actions summary
- LangSmith run is tagged `eval_failed` with the specific metric that failed
- On-call engineer is notified via SNS

---

## 12. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Latency** | p95 end-to-end response time < 5 seconds |
| **Availability** | 99.5% uptime (ECS health checks + ALB) |
| **Security** | JWT auth on all endpoints; Qdrant Cloud access restricted to API key (stored in Secrets Manager, never in code); secrets never in env files in production |
| **Scalability** | Handle 50 concurrent users without degradation |
| **Data Privacy** | No raw PII logged to LangSmith (hash or redact before tracing) |
| **Auditability** | All access denials and guardrail triggers logged with timestamp and user ID |
| **Portability** | All services containerized; can be migrated to GCP/Azure with config change only |

---

## 13. Tech Stack Summary

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| LLM | LLaMA 3.1 70B via Groq | Latest | Free tier for dev/test |
| Embeddings (Dense) | `all-MiniLM-L6-v2` | `sentence-transformers` | Self-hosted, no API cost |
| Embeddings (Sparse BM25, optional) | `Qdrant/bm25` | `fastembed>=0.4` | ONNX-based, CPU-only, optional hybrid search |
| RAG Framework | LangChain | 0.3.x | Core chain + retrievers |
| Document Parsing | Docling + LangChain loaders | Latest | Markdown, CSV, PDF support |
| Vector Database | Qdrant Cloud (managed) | Free tier + Hybrid RRF | HTTPS + API key auth; local Docker for dev; supports named sparse vectors |
| Backend | FastAPI | 0.111.x | Async, Pydantic v2 |
| Frontend | React 18 + TypeScript | 18.x | Tailwind, React Query |
| PII Detection | Microsoft Presidio | 2.x | Analyzer + Anonymizer |
| Tracing | LangSmith | SDK 0.1.x | All chain steps traced |
| Evaluation | Ragas | 0.1.x | Golden dataset evaluation |
| Session Memory & Rate Limiting | Redis (AWS ElastiCache) | 7.2.x | Per-session history + sliding window counters |
| Cloud | AWS | — | ECS, S3, CloudWatch, Amplify, ElastiCache |
| IaC | Terraform | 1.7.x | All infra as code |
| CI/CD | GitHub Actions | — | Full pipeline with eval gates |

---

## 14. Milestones & Delivery Phases

### Phase 1 — Foundation (Week 1–2)
- [ ] Set up project repo structure (monorepo: `/backend`, `/frontend`, `/infra`, `/evals`)
- [ ] `docker-compose.yml` local dev environment working (backend + Qdrant + Redis + frontend)
- [ ] Implement document ingestion pipeline (Docling → Qdrant) with table-aware CSV chunking
- [ ] Define and ingest all 10 source documents with role metadata and embedding model version tag
- [ ] Basic FastAPI server with `/chat`, `/health`, and `/ready` endpoints
- [ ] Qdrant and Redis running locally via Docker Compose

### Phase 2 — RAG + RBAC (Week 3–4)
- [ ] LangChain RAG chain connected to Qdrant with RBAC metadata filter
- [ ] JWT auth middleware (mock login)
- [ ] Layer 1 (retrieval filter) and Layer 2 (response validation) RBAC
- [ ] All 5 roles tested with correct access boundaries
- [ ] LangSmith tracing wired to all chain steps
- [ ] Chunk similarity scores logged per trace

### Phase 3 — Guardrails (Week 5)
- [ ] Presidio PII detection on input and output
- [ ] Out-of-scope query classifier
- [ ] Prompt injection detection
- [ ] Guardrail decision flow unit tested (all branches)
- [ ] Error handling and fallback responses implemented and tested

### Phase 4 — Frontend (Week 6)
- [ ] React chat UI with login, role badge, markdown rendering
- [ ] Citation panel with source documents
- [ ] Access denial handling in UI
- [ ] Connected to backend API
- [ ] Session memory working across multi-turn conversations

### Phase 5 — Evaluation Suite (Week 7)
- [ ] Golden dataset of 30 QA pairs created and reviewed by department owners
- [ ] Ragas metrics configured and baseline scores established
- [ ] RBAC boundary test suite (25 tests across 5 roles)
- [ ] Evaluation script runnable from CI
- [ ] Prompt versioning system in place

### Phase 6 — AWS Deployment (Week 8)
- [ ] Terraform modules written and tested (including Redis/ElastiCache)
- [ ] ECR + ECS deployment working
- [ ] Qdrant Cloud cluster provisioned, collection created, ingestion verified
- [ ] Redis on ElastiCache in private subnet
- [ ] Frontend on Amplify
- [ ] Secrets in Secrets Manager
- [ ] GitHub Actions pipeline with eval gates live
- [ ] Rate limiting active and tested

### Phase 7 — Cost Monitoring & Polish (Week 9)
- [ ] CloudWatch custom metrics for token usage
- [ ] Cost alarms configured
- [ ] CloudWatch dashboard created
- [ ] End-to-end smoke test across all roles
- [ ] Documentation finalized

---

## 15. Local Development Setup

Every developer must be able to run the complete stack locally without an AWS account, using Docker Compose.

### 15.1 Repository Structure

```
finsolve-ai/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py
│   │   ├── auth/             # JWT middleware
│   │   ├── rag/              # LangChain chain, retriever
│   │   ├── guardrails/       # Presidio, injection detection
│   │   ├── memory/           # Redis session memory
│   │   └── prompts/          # system_prompt_v1.txt, v2.txt ...
│   ├── ingest/               # CLI ingestion pipeline
│   │   ├── ingest.py
│   │   └── chunkers/         # text_chunker.py, csv_chunker.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React application
│   ├── src/
│   └── Dockerfile
├── infra/                    # Terraform modules
│   └── modules/
├── evals/                    # Ragas + RBAC test suite
│   ├── golden_dataset.json
│   ├── run_ragas.py
│   └── rbac_tests.py
├── data/                     # Source documents (gitignored in prod)
│   ├── finance/
│   ├── hr/
│   ├── marketing/
│   └── engineering/
├── docker-compose.yml
├── docker-compose.override.yml   # Local dev overrides
└── .env.example
```

### 15.2 docker-compose.yml

Local development uses a **local Qdrant Docker container** so developers can work fully offline without consuming the Qdrant Cloud free tier quota or needing internet access. The cloud cluster is used for staging and production only.

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
      - LANGSMITH_PROJECT=${LANGSMITH_PROJECT}
      - JWT_SECRET=${JWT_SECRET}
      - QDRANT_URL=http://qdrant:6333       # local Docker instance
      - QDRANT_API_KEY=                     # empty = no auth for local
      - QDRANT_COLLECTION=finsolve_docs
      - REDIS_URL=redis://redis:6379
      - EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
      - PROMPT_VERSION=v1
      - ENVIRONMENT=dev
    depends_on:
      - qdrant
      - redis
    volumes:
      - ./data:/app/data        # Mount source docs for ingestion
      - ./backend:/app          # Hot reload in dev

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    depends_on:
      - backend

  qdrant:
    image: qdrant/qdrant:v1.9.0
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --save 60 1   # Persist every 60s if 1 key changed

volumes:
  qdrant_data:
  redis_data:
```

### 15.3 First-Time Setup

#### .env.example Template

Every developer copies this file to `.env` and fills in their own credentials. The `.env` file is gitignored — never committed.

```bash
# ── LLM ──────────────────────────────────────────────────
GROQ_API_KEY=gsk_...

# ── Observability ─────────────────────────────────────────
LANGSMITH_API_KEY=ls__...
LANGSMITH_PROJECT=finsolve-ai-dev

# ── Auth ──────────────────────────────────────────────────
JWT_SECRET=change-me-to-a-long-random-string

# ── Vector DB ─────────────────────────────────────────────
# Local dev: leave QDRANT_URL as-is, leave QDRANT_API_KEY blank
# Staging/Prod: set both to your Qdrant Cloud cluster values
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=

QDRANT_COLLECTION=finsolve_docs

# ── Redis ─────────────────────────────────────────────────
# Local dev: leave as-is
# Staging/Prod: set to your ElastiCache endpoint
REDIS_URL=redis://redis:6379

# ── Embedding & Prompt ────────────────────────────────────
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
PROMPT_VERSION=v1

# ── Environment ───────────────────────────────────────────
ENVIRONMENT=dev   # dev | staging | production
```

#### Setup Commands

```bash
# 1. Clone repo and copy env file
git clone https://github.com/org/finsolve-ai
cp .env.example .env
# Fill in: GROQ_API_KEY, LANGSMITH_API_KEY, JWT_SECRET
# Leave QDRANT_API_KEY empty for local dev (uses Docker Qdrant)

# 2. Start all services
docker compose up -d

# 3. Run ingestion into local Qdrant (one-time)
docker compose exec backend python ingest/ingest.py --data-dir /app/data

# 4. Verify ingestion
docker compose exec backend python ingest/ingest.py --verify

# 5. Open frontend
open http://localhost:3000
```

#### Ingesting into Qdrant Cloud (staging/prod)

```bash
# Set cloud credentials in environment
export QDRANT_URL=https://xyz.us-east-1-0.aws.cloud.qdrant.io:6333
export QDRANT_API_KEY=your-qdrant-cloud-api-key
export QDRANT_COLLECTION=finsolve_docs

# Run ingestion pointing at cloud (can run locally against cloud cluster)
python backend/ingest/ingest.py --data-dir ./data
```

### 15.4 Local vs. AWS Configuration

| Config | Local (docker-compose) | AWS Staging / Production |
|--------|----------------------|--------------------------|
| Qdrant URL | `http://qdrant:6333` (Docker) | Qdrant Cloud cluster URL |
| Qdrant API Key | _(empty — no auth)_ | Secret from Secrets Manager |
| Redis URL | `redis://redis:6379` | ElastiCache endpoint |
| Secrets | `.env` file | AWS Secrets Manager |
| LLM | Groq (same) | Groq (same) |
| Frontend | `localhost:3000` | AWS Amplify URL |
| Log destination | stdout / local file | CloudWatch Logs |

---

*This document is the authoritative requirements specification for the FinSolve Internal AI Assistant. All implementation decisions should trace back to a requirement here. Update this document as scope evolves.*

