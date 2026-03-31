# FinSolve Internal AI Assistant — Implementation Plan

**Project:** Enterprise RAG Chatbot with RBAC, Guardrails & Monitoring  
**Version:** 1.0  
**Date:** 2026-03-31  
**Based on Requirements:** docs/requirements.md v2.1

---

## Table of Contents

1. [Project File Structure](#1-project-file-structure)
2. [Epic Overview](#2-epic-overview)
3. [Epic 1 — Project Foundation & DevEnv](#epic-1--project-foundation--devenv)
4. [Epic 2 — Data Ingestion Pipeline](#epic-2--data-ingestion-pipeline)
5. [Epic 3 — Core RAG Backend (FastAPI)](#epic-3--core-rag-backend-fastapi)
6. [Epic 4 — RBAC & Authentication](#epic-4--rbac--authentication)
7. [Epic 5 — Guardrails & Safety](#epic-5--guardrails--safety)
8. [Epic 6 — Conversation Memory & Rate Limiting](#epic-6--conversation-memory--rate-limiting)
9. [Epic 7 — React Frontend](#epic-7--react-frontend)
10. [Epic 8 — Evaluation Suite (Ragas)](#epic-8--evaluation-suite-ragas)
11. [Epic 9 — Observability & LangSmith](#epic-9--observability--langsmith)
12. [Epic 10 — AWS Deployment & IaC](#epic-10--aws-deployment--iac)
13. [Epic 11 — CI/CD Pipeline & Evaluation Gates](#epic-11--cicd-pipeline--evaluation-gates)
14. [Epic 12 — Cost Monitoring & Alerting](#epic-12--cost-monitoring--alerting)
15. [Dependency Map](#15-dependency-map)
16. [Acceptance Criteria Summary](#16-acceptance-criteria-summary)

---

## 1. Project File Structure

```
RBAC-Chatbot/
│
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # App entrypoint, router registration
│   │   ├── config.py                 # Settings via pydantic-settings (.env loader)
│   │   ├── dependencies.py           # Shared FastAPI Depends() (DB, Redis, auth)
│   │   │
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # POST /auth/login, POST /auth/refresh
│   │   │   ├── service.py            # JWT create/verify, user store
│   │   │   ├── models.py             # LoginRequest, TokenResponse, UserContext
│   │   │   └── rbac.py               # Role-to-allowed-docs access matrix
│   │   │
│   │   ├── chat/
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # POST /chat, GET /chat/history
│   │   │   ├── service.py            # Orchestrates guardrails → RAG → response
│   │   │   └── models.py             # ChatRequest, ChatResponse, Citation
│   │   │
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── retriever.py          # Qdrant retrieval with RBAC filter
│   │   │   ├── generator.py          # Groq LLM call via LangChain
│   │   │   ├── pipeline.py           # Full RAG chain: rewrite → retrieve → generate
│   │   │   ├── rewriter.py           # Optional query rewriting / HyDE
│   │   │   └── prompts/
│   │   │       ├── __init__.py
│   │   │       ├── system_prompt_v1.txt
│   │   │       └── prompt_loader.py  # Version-aware prompt loader
│   │   │
│   │   ├── guardrails/
│   │   │   ├── __init__.py
│   │   │   ├── input_guard.py        # PII detect, injection detect, scope check
│   │   │   ├── output_guard.py       # PII redact, source boundary, hallucination
│   │   │   ├── pii.py                # Presidio analyzer + anonymizer wrappers
│   │   │   ├── injection.py          # Prompt injection keyword + embedding check
│   │   │   └── scope.py              # Out-of-scope classifier (keyword + embedding)
│   │   │
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── session.py            # Redis-backed session store (sliding window)
│   │   │   └── models.py             # ConversationTurn, SessionWindow
│   │   │
│   │   ├── rate_limit/
│   │   │   ├── __init__.py
│   │   │   └── limiter.py            # Redis sliding window rate limiter
│   │   │
│   │   └── health/
│   │       ├── __init__.py
│   │       └── router.py             # GET /health, GET /ready
│   │
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── ingest.py                 # CLI entrypoint: python -m ingest.ingest
│   │   ├── chunkers/
│   │   │   ├── __init__.py
│   │   │   ├── markdown_chunker.py   # Recursive text splitter for .md files
│   │   │   └── csv_chunker.py        # Row-per-chunk with header prepend for .csv
│   │   ├── embedder.py               # sentence-transformers embedding wrapper
│   │   ├── qdrant_client.py          # Qdrant collection management & upsert
│   │   └── metadata.py               # Metadata schema builder per chunk
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py               # Shared fixtures (test client, mock Redis, etc.)
│   │   ├── unit/
│   │   │   ├── test_auth.py
│   │   │   ├── test_rbac.py
│   │   │   ├── test_guardrails_input.py
│   │   │   ├── test_guardrails_output.py
│   │   │   ├── test_rate_limiter.py
│   │   │   ├── test_chunkers.py
│   │   │   └── test_session.py
│   │   └── integration/
│   │       ├── test_chat_pipeline.py  # Full RAG flow (local Qdrant + Groq)
│   │       └── test_rbac_boundaries.py
│   │
│   ├── Dockerfile
│   ├── pyproject.toml                # uv / pip-tools managed deps
│   └── requirements.txt              # Pinned lockfile
│
├── frontend/                         # React 18 + TypeScript
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   ├── auth.ts               # login(), refreshToken()
│   │   │   └── chat.ts               # sendMessage(), getHistory()
│   │   ├── components/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── CitationPanel.tsx
│   │   │   ├── RoleBadge.tsx
│   │   │   └── ErrorBanner.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   └── useChat.ts
│   │   ├── store/
│   │   │   └── authStore.ts          # Zustand or React Context for auth state
│   │   ├── types/
│   │   │   └── index.ts              # Shared TS interfaces
│   │   └── styles/
│   │       └── globals.css           # Tailwind base imports
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── vite.config.ts
│
├── evals/
│   ├── __init__.py
│   ├── run_ragas.py                  # Ragas evaluation runner (CI gate)
│   ├── rbac_boundary_tests.py        # 25 RBAC boundary assertions
│   ├── guardrail_tests.py            # 8 guardrail test assertions
│   ├── generate_answers.py           # Hits live API, collects answers for eval
│   └── report/                       # Auto-generated eval reports (gitignored)
│
├── infra/                            # Terraform IaC
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   └── modules/
│       ├── networking/               # VPC, subnets, security groups
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── ecs/                      # ECS cluster, task def, service, ALB
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── redis/                    # ElastiCache (cache.t3.micro)
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── secrets/                  # Secrets Manager entries
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       └── monitoring/               # CloudWatch dashboards, alarms, log groups
│           ├── main.tf
│           ├── variables.tf
│           └── outputs.tf
│
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Lint, test, build on PR
│       ├── eval-gate.yml             # Ragas + RBAC eval on staging
│       └── deploy.yml                # ECS deploy after eval gate passes
│
├── data/                             # Source documents (already present)
│   ├── engineering/
│   ├── eval/
│   │   └── golden_dataset.json
│   ├── finance/
│   ├── general/
│   ├── hr/
│   └── marketing/
│
├── docs/
│   ├── requirements.md               # Source of truth (v2.1)
│   ├── implementation_plan.md        # This file
│   ├── architecture.md               # Architecture decision records
│   └── api_reference.md              # Auto-generated from FastAPI /docs
│
├── scripts/
│   ├── ingest_all.sh                 # One-shot ingestion script
│   ├── reset_qdrant.sh               # Drop & recreate Qdrant collection
│   └── seed_users.py                 # Seed mock user store for local dev
│
├── docker-compose.yml                # backend + frontend + qdrant + redis
├── .env.example                      # All required env vars (no secrets)
├── .gitignore
└── README.md
```

---

## 2. Epic Overview

| # | Epic | Phase | Priority | Depends On |
|---|------|-------|----------|------------|
| E1 | Project Foundation & DevEnv | Week 1 | Critical | — |
| E2 | Data Ingestion Pipeline | Week 1–2 | Critical | E1 |
| E3 | Core RAG Backend (FastAPI) | Week 2–3 | Critical | E1, E2 |
| E4 | RBAC & Authentication | Week 3 | Critical | E3 |
| E5 | Guardrails & Safety | Week 4–5 | High | E3, E4 |
| E6 | Conversation Memory & Rate Limiting | Week 4 | High | E3 |
| E7 | React Frontend | Week 5–6 | High | E3, E4 |
| E8 | Evaluation Suite (Ragas) | Week 6 | High | E3, E4, E5 |
| E9 | Observability & LangSmith | Week 5–6 | Medium | E3 |
| E10 | AWS Deployment & IaC | Week 7 | High | E3, E4, E6 |
| E11 | CI/CD Pipeline & Evaluation Gates | Week 7–8 | High | E8, E10 |
| E12 | Cost Monitoring & Alerting | Week 8 | Medium | E10 |

---

## Epic 1 — Project Foundation & DevEnv

**Goal:** Runnable local environment with all services wired up, one-command start.

### Story 1.1 — Repository Scaffold

**As a** developer, **I want** the repo structure created with all placeholder files so I can navigate and contribute without confusion.

| # | Task | Output |
|---|------|--------|
| 1.1.1 | Create full directory tree per §1 of this plan | All dirs + `__init__.py` files |
| 1.1.2 | Write `pyproject.toml` with all Python deps (FastAPI, LangChain, Qdrant, Groq, Presidio, Redis, Ragas, sentence-transformers, pytest) | `backend/pyproject.toml` |
| 1.1.3 | Pin `requirements.txt` via `uv pip compile` | `backend/requirements.txt` |
| 1.1.4 | Write `package.json` with React 18, TypeScript, Vite, Tailwind, Axios, React Query | `frontend/package.json` |
| 1.1.5 | Write `tsconfig.json` and `tailwind.config.ts` | Frontend config files |
| 1.1.6 | Write `.env.example` with all 25+ env vars (no secrets) | `.env.example` |
| 1.1.7 | Update `README.md` with project overview, local setup steps, and role credentials table | `README.md` |

**Acceptance:** `git clone` + `cp .env.example .env` + fill secrets → services start.

---

### Story 1.2 — Docker Compose Local Stack

**As a** developer, **I want** `docker compose up -d` to start all four services (backend, frontend, Qdrant, Redis) so I can develop offline.

| # | Task | Output |
|---|------|--------|
| 1.2.1 | Write `backend/Dockerfile` (Python 3.11-slim, non-root user, health check) | `backend/Dockerfile` |
| 1.2.2 | Write `frontend/Dockerfile` (Node 20-alpine, multi-stage: build + nginx) | `frontend/Dockerfile` |
| 1.2.3 | Write `docker-compose.yml` with 4 services, volumes, env_file, healthchecks, depends_on | `docker-compose.yml` |
| 1.2.4 | Verify all services start healthy: `docker compose ps` shows all "healthy" | Passing health checks |
| 1.2.5 | Write `scripts/ingest_all.sh` that runs ingestion after compose up | `scripts/ingest_all.sh` |

**Acceptance:** `docker compose up -d && docker compose ps` → all 4 services healthy within 60 s.

---

### Story 1.3 — Configuration Management

**As a** developer, **I want** all config loaded from environment variables via a single `Settings` class so there are no hardcoded values.

| # | Task | Output |
|---|------|--------|
| 1.3.1 | Write `backend/app/config.py` using `pydantic-settings` with all env vars typed and validated | `config.py` |
| 1.3.2 | Add `ENVIRONMENT` var (`local` / `staging` / `production`) to gate certain behaviours | Config field |
| 1.3.3 | Write test `test_config.py` asserting required fields raise `ValidationError` when absent | Unit test |

---

## Epic 2 — Data Ingestion Pipeline

**Goal:** All 10 source documents chunked, embedded, and stored in Qdrant with correct metadata and RBAC tags.

### Story 2.1 — Markdown Chunker

**As a** data engineer, **I want** `.md` files split into semantic chunks with metadata so they can be retrieved accurately.

| # | Task | Output |
|---|------|--------|
| 2.1.1 | Implement `markdown_chunker.py` using `RecursiveCharacterTextSplitter` (512 tokens, 64 overlap, split on headings first) | Chunker class |
| 2.1.2 | Preserve heading hierarchy in chunk metadata (`section_h1`, `section_h2`) | Metadata fields |
| 2.1.3 | Unit test: chunk `financial_summary.md` → assert chunk count, token size ≤ 512, metadata present | `test_chunkers.py` |

---

### Story 2.2 — CSV Row Chunker

**As a** data engineer, **I want** `hr_data.csv` chunked row-by-row with header prepended so each employee record is a self-contained retrievable chunk.

| # | Task | Output |
|---|------|--------|
| 2.2.1 | Implement `csv_chunker.py`: read CSV, prepend header row to each data row, yield one chunk per employee | Chunker class |
| 2.2.2 | Add row-level metadata: `row_index`, `employee_id` extracted from each row | Metadata |
| 2.2.3 | Unit test: assert 100 chunks from `hr_data.csv`, each starts with header, `employee_id` in metadata | `test_chunkers.py` |

---

### Story 2.3 — Metadata Schema

**As a** data engineer, **I want** every chunk to carry consistent metadata so RBAC filters and citations work correctly.

| # | Task | Output |
|---|------|--------|
| 2.3.1 | Define metadata schema in `metadata.py`: `doc_id`, `source_file`, `allowed_roles` (list), `chunk_index`, `sensitivity` (`public`/`internal`/`confidential`), `section_h1`, `section_h2` | Schema |
| 2.3.2 | Implement `build_metadata(file_path, chunk_index, roles, sensitivity)` function | Function |
| 2.3.3 | Define the role-to-document access matrix in `auth/rbac.py` (mirrors requirements.md §4.2) | Access matrix |
| 2.3.4 | Unit test: assert metadata for each source file has correct `allowed_roles` list | Test |

**Role-to-Document Access Matrix:**

| Document | finance | hr | marketing | engineering | executive |
|----------|---------|-----|-----------|-------------|-----------|
| quarterly_financial_report.md | ✓ | | | | ✓ |
| financial_summary.md | ✓ | | | | ✓ |
| employee_handbook.md | | ✓ | | | ✓ |
| hr_data.csv | | ✓ | | | ✓ |
| engineering_master_doc.md | | | | ✓ | ✓ |
| marketing_report_*.md (all 5) | | | ✓ | | ✓ |

---

### Story 2.4 — Embedding & Qdrant Upsert

**As a** data engineer, **I want** chunks embedded and upserted into Qdrant with metadata so they can be semantically searched.

| # | Task | Output |
|---|------|--------|
| 2.4.1 | Implement `embedder.py` wrapping `sentence-transformers/all-MiniLM-L6-v2` (384-dim, batch=32) | Embedder class |
| 2.4.2 | Implement `qdrant_client.py`: create collection (`cosine` distance, 384 dims), batch upsert points with payload | Client class |
| 2.4.3 | Implement `ingest.py` CLI: iterate all source docs → chunk → embed → upsert; log progress per file | CLI entrypoint |
| 2.4.4 | Add `--dry-run` flag to `ingest.py` that logs chunk count without upserting | CLI flag |
| 2.4.5 | Add `--reset` flag to `ingest.py` that drops and recreates the collection before ingesting | CLI flag |
| 2.4.6 | Log: total documents, total chunks, total vectors, time taken after run | Completion log |
| 2.4.7 | Integration test: run ingestion on `financial_summary.md` → assert ≥ 1 point in Qdrant with correct payload | Integration test |

---

### Story 2.5 — Embedding Model Versioning

**As a** data engineer, **I want** the embedding model version stored in collection metadata so I can detect when re-ingestion is needed.

| # | Task | Output |
|---|------|--------|
| 2.5.1 | Store `embedding_model` and `embedding_version` in Qdrant collection metadata on creation | Collection meta |
| 2.5.2 | On startup, compare stored model version against env var `EMBEDDING_MODEL`; warn if mismatch | Startup check |
| 2.5.3 | Document blue-green re-ingestion strategy in `docs/architecture.md` | ADR entry |

---

## Epic 3 — Core RAG Backend (FastAPI)

**Goal:** A working `/chat` endpoint that accepts a user query + JWT, retrieves relevant chunks, and generates a grounded response.

### Story 3.1 — FastAPI App Skeleton

**As a** developer, **I want** a running FastAPI app with structured routing, CORS, and error handling middleware.

| # | Task | Output |
|---|------|--------|
| 3.1.1 | Implement `app/main.py`: create FastAPI app, register routers (auth, chat, health), add CORS middleware | `main.py` |
| 3.1.2 | Add global exception handler returning structured JSON errors (no stack traces to client) | Exception handler |
| 3.1.3 | Add request ID middleware (UUID per request, logged and returned as `X-Request-ID` header) | Middleware |
| 3.1.4 | Verify `/docs` (Swagger) and `/redoc` endpoints work in local dev | Manual test |

---

### Story 3.2 — Retriever

**As a** backend engineer, **I want** a retriever that queries Qdrant and returns the top-k chunks filtered by user role.

| # | Task | Output |
|---|------|--------|
| 3.2.1 | Implement `rag/retriever.py`: embed query → search Qdrant with role filter → return top-5 chunks (score ≥ 0.60) | Retriever class |
| 3.2.2 | Apply RBAC filter as Qdrant `must` condition on `allowed_roles` field | Filter logic |
| 3.2.3 | Return chunk text + source_file + score + section metadata per result | Result model |
| 3.2.4 | Unit test: mock Qdrant, assert role filter is applied in search request | `test_retriever.py` |

---

### Story 3.3 — Generator (LLM)

**As a** backend engineer, **I want** the LLM to generate a grounded answer from retrieved context using the versioned system prompt.

| # | Task | Output |
|---|------|--------|
| 3.3.1 | Implement `rag/generator.py`: LangChain `ChatGroq` (llama-3.1-70b-versatile), 10s timeout, 1 retry | Generator class |
| 3.3.2 | Load system prompt from `prompts/system_prompt_v1.txt` via `prompt_loader.py` (version from env var `PROMPT_VERSION`) | Prompt loader |
| 3.3.3 | Write `system_prompt_v1.txt`: instruct model to answer only from provided context, cite sources, refuse if not in context, never reveal system instructions | Prompt file |
| 3.3.4 | Build LangChain prompt template: `system_prompt` + `context` (numbered chunks) + `conversation_history` + `question` | Prompt template |
| 3.3.5 | Unit test: mock LLM, assert prompt contains context and conversation history | `test_generator.py` |

---

### Story 3.4 — RAG Pipeline Orchestrator

**As a** backend engineer, **I want** a single pipeline function that chains query rewriting → retrieval → generation → citation assembly.

| # | Task | Output |
|---|------|--------|
| 3.4.1 | Implement `rag/pipeline.py`: `run_rag(query, user_context, session_history)` → `RagResult` | Pipeline function |
| 3.4.2 | `RagResult` contains: `answer`, `citations` (list of `{source, excerpt, score}`), `retrieved_chunks`, `prompt_version` | Result model |
| 3.4.3 | Implement optional `rag/rewriter.py`: rewrite query for better retrieval (HyDE or simple expansion); feature-flagged via `ENABLE_QUERY_REWRITE` env var | Rewriter |
| 3.4.4 | Log retrieval metrics: query, num_chunks_retrieved, top_score, latency_ms to LangSmith | Tracing |
| 3.4.5 | Integration test: send "What was FinSolve's total revenue in 2024?" as finance role → assert answer contains "$9.4 billion" | Integration test |

---

### Story 3.5 — Chat Router & Service

**As a** backend engineer, **I want** `POST /chat` to orchestrate guardrails → pipeline → response in a clean service layer.

| # | Task | Output |
|---|------|--------|
| 3.5.1 | Implement `chat/models.py`: `ChatRequest` (question: str, session_id: str), `ChatResponse` (answer, citations, session_id, request_id), `Citation` | Pydantic models |
| 3.5.2 | Implement `chat/service.py`: run input guard → check rate limit → load session → run RAG → run output guard → save session → return response | Service |
| 3.5.3 | Implement `chat/router.py`: `POST /chat` (requires JWT), `GET /chat/history/{session_id}` | Router |
| 3.5.4 | Validate `question` max length = 1000 chars at Pydantic level | Validation |
| 3.5.5 | Return `403` with structured message when RBAC blocks access; `400` for guardrail blocks | Error codes |

---

### Story 3.6 — Health Endpoints

**As an** ops engineer, **I want** `/health` and `/ready` endpoints so ECS can perform liveness and readiness checks.

| # | Task | Output |
|---|------|--------|
| 3.6.1 | Implement `GET /health` → `{"status": "ok", "timestamp": ...}` (always 200, no deps checked) | Liveness endpoint |
| 3.6.2 | Implement `GET /ready` → check Qdrant reachability + Redis reachability → `{"status": "ready"}` or `503` | Readiness endpoint |
| 3.6.3 | Unit test both endpoints | Tests |

---

## Epic 4 — RBAC & Authentication

**Goal:** JWT-based login with role assignment; every request validates role and enforces document access.

### Story 4.1 — Mock Auth & JWT

**As a** developer, **I want** a login endpoint that issues JWTs for the 5 predefined role accounts so I can test role-specific behaviour.

| # | Task | Output |
|---|------|--------|
| 4.1.1 | Implement `auth/service.py`: static user store (5 accounts, one per role), `bcrypt`-hashed passwords from env | User store |
| 4.1.2 | Implement `create_jwt(user_id, role)` → signed JWT (HS256, 8h expiry) with `sub`, `role`, `iat`, `exp` claims | JWT creator |
| 4.1.3 | Implement `verify_jwt(token)` → `UserContext(user_id, role)` or raises `401` | JWT verifier |
| 4.1.4 | Implement `POST /auth/login` (username + password → `{access_token, token_type, expires_in, role}`) | Login endpoint |
| 4.1.5 | Write `auth/models.py`: `LoginRequest`, `TokenResponse`, `UserContext` | Models |
| 4.1.6 | Unit test: valid login → token; invalid password → 401; expired token → 401 | `test_auth.py` |
| 4.1.7 | Write `scripts/seed_users.py` to print credentials table for local dev | Helper script |

---

### Story 4.2 — RBAC Enforcement

**As a** security engineer, **I want** RBAC enforced at both the retrieval filter and response validation layers so roles can never access out-of-scope data.

| # | Task | Output |
|---|------|--------|
| 4.2.1 | Implement `auth/rbac.py`: `ROLE_DOCUMENT_ACCESS` dict mapping each role to its allowed `source_file` list | Access matrix |
| 4.2.2 | Implement `get_allowed_docs(role: str) -> list[str]` and `can_access(role, source_file) -> bool` | RBAC helpers |
| 4.2.3 | In retriever: apply `allowed_roles contains role` Qdrant filter on every query | Retrieval guard |
| 4.2.4 | In output guard: strip any citation whose `source_file` is not in `allowed_docs` for the role (double-check) | Output guard |
| 4.2.5 | Unit test `rbac.py`: assert finance cannot access marketing docs; executive can access all | `test_rbac.py` |
| 4.2.6 | Integration test: query marketing content as finance role → assert 0 chunks retrieved | Integration test |

---

## Epic 5 — Guardrails & Safety

**Goal:** Input and output guardrails block PII extraction, prompt injection, out-of-scope queries, and prevent PII leakage in responses.

### Story 5.1 — Input Guardrail: Prompt Injection Detection

**As a** security engineer, **I want** prompt injection attempts detected and blocked before any retrieval occurs.

| # | Task | Output |
|---|------|--------|
| 5.1.1 | Implement `guardrails/injection.py`: keyword list check (e.g., "ignore previous instructions", "disregard", "jailbreak", "pretend you are") | Keyword detector |
| 5.1.2 | Add embedding-based similarity check against a list of known injection templates (cosine sim > 0.85 → block) | Embedding detector |
| 5.1.3 | Return `GuardResult(blocked=True, reason="prompt_injection", code="GUARD-006")` on detection | Guard result |
| 5.1.4 | Unit test: GUARD-006 query → blocked; normal query → not blocked | `test_guardrails_input.py` |

---

### Story 5.2 — Input Guardrail: Out-of-Scope Detection

**As a** security engineer, **I want** general knowledge questions not answerable from FinSolve documents rejected before retrieval.

| # | Task | Output |
|---|------|--------|
| 5.2.1 | Implement `guardrails/scope.py`: keyword-based check for off-topic domains (AI trends, politics, sports, etc.) | Keyword classifier |
| 5.2.2 | Add embedding similarity check: embed query, compare to "FinSolve internal company data" anchor; if similarity < 0.35 → out-of-scope | Embedding classifier |
| 5.2.3 | Return `GuardResult(blocked=True, reason="out_of_scope", code="GUARD-005")` | Guard result |
| 5.2.4 | Unit test: GUARD-005 query ("AI trends") → blocked; "What is the notice period?" → not blocked | Tests |

---

### Story 5.3 — Input Guardrail: PII Detection (Bulk Extraction)

**As a** security engineer, **I want** bulk PII extraction queries (e.g., "list all DOBs") blocked at input before retrieval.

| # | Task | Output |
|---|------|--------|
| 5.3.1 | Implement `guardrails/pii.py`: Presidio `AnalyzerEngine` for PII entity detection in query text | Presidio analyzer |
| 5.3.2 | Add heuristic for bulk extraction intent: query contains plural PII request + aggregation terms ("all", "list", "every") → block | Heuristic |
| 5.3.3 | Return `GuardResult(blocked=True, reason="pii_bulk_extraction", code="GUARD-002")` | Guard result |
| 5.3.4 | Unit test: GUARD-002 query → blocked; single employee ID query → not blocked | Tests |

---

### Story 5.4 — Output Guardrail: PII Redaction

**As a** security engineer, **I want** salary, DOB, and other sensitive fields redacted from LLM responses even when present in retrieved context.

| # | Task | Output |
|---|------|--------|
| 5.4.1 | Implement `guardrails/output_guard.py`: run Presidio `AnonymizerEngine` on LLM response text | Redaction |
| 5.4.2 | Configure redact rules: SALARY → `[REDACTED-SALARY]`, DATE_OF_BIRTH → `[REDACTED-DOB]`, PHONE_NUMBER, EMAIL | Redact config |
| 5.4.3 | For GUARD-001 (salary query): redact salary value but allow name, department, role to pass through | Selective redact |
| 5.4.4 | Unit test: response containing "salary: ₹800,000" → redacted to "[REDACTED-SALARY]" | `test_guardrails_output.py` |

---

### Story 5.5 — Output Guardrail: Source Boundary Enforcement

**As a** security engineer, **I want** citations limited to documents the user's role is allowed to access.

| # | Task | Output |
|---|------|--------|
| 5.5.1 | In `output_guard.py`: after generation, iterate `citations`, drop any with `source_file` not in `allowed_docs(role)` | Citation filter |
| 5.5.2 | If all citations are stripped, append standard disclaimer: "I could not find relevant information in your accessible documents." | Fallback message |
| 5.5.3 | Unit test: mock response with cross-role citation → citation stripped | Test |

---

### Story 5.6 — Input Guardrail Orchestrator

**As a** backend engineer, **I want** all input checks run in sequence before any retrieval, short-circuiting on first block.

| # | Task | Output |
|---|------|--------|
| 5.6.1 | Implement `guardrails/input_guard.py`: `check_input(query, role) -> GuardResult` running checks in order: injection → scope → PII | Orchestrator |
| 5.6.2 | Add timing: log each guard's latency to LangSmith | Metrics |
| 5.6.3 | Integration test: run all 8 GUARD-* scenarios from golden dataset against live guard → assert expected_behaviour | Integration test |

---

## Epic 6 — Conversation Memory & Rate Limiting

**Goal:** Multi-turn conversations with Redis-backed session memory; sliding-window rate limiting per user.

### Story 6.1 — Redis Session Memory

**As a** user, **I want** my conversation history preserved within a session so the AI understands follow-up questions.

| # | Task | Output |
|---|------|--------|
| 6.1.1 | Implement `memory/session.py`: `save_turn(session_id, human, ai)` and `get_history(session_id) -> list[ConversationTurn]` using Redis list with `LTRIM` to keep last 12 entries (6 pairs) | Session store |
| 6.1.2 | Set Redis key TTL = 8 hours (matching JWT expiry) | TTL |
| 6.1.3 | Implement `memory/models.py`: `ConversationTurn(role: "human" | "ai", content: str, timestamp: str)` | Model |
| 6.1.4 | In `chat/service.py`: load session history before RAG, save turn after generation | Integration |
| 6.1.5 | Unit test: save 7 turns → `get_history` returns only last 6 pairs (12 entries) | `test_session.py` |
| 6.1.6 | Unit test: session expires after TTL (mock Redis with TTL check) | Test |

---

### Story 6.2 — Rate Limiter

**As an** ops engineer, **I want** per-user rate limits enforced via Redis to prevent abuse.

| # | Task | Output |
|---|------|--------|
| 6.2.1 | Implement `rate_limit/limiter.py`: sliding window counter in Redis; `check_and_increment(user_id, window_seconds, limit) -> bool` | Limiter |
| 6.2.2 | Hourly limit: 30 queries/hour (default), 50 for finance/engineering, 100 for executive (from `RATE_LIMIT_<ROLE>_HOURLY` env vars) | Per-role limits |
| 6.2.3 | Daily limit: 100 queries/day for all roles | Daily limit |
| 6.2.4 | Max concurrent sessions: 2 per user (Redis set of active session IDs) | Concurrency guard |
| 6.2.5 | Return `429` with `Retry-After` header when limit exceeded | Error response |
| 6.2.6 | Unit test: 30 requests → 31st returns `False`; window reset after 3600s | `test_rate_limiter.py` |

---

## Epic 7 — React Frontend

**Goal:** A functional chat UI with login, role badge, conversation history, and source citations panel.

### Story 7.1 — Auth & Login

**As a** user, **I want** to log in with my credentials and see my role so I know what data I can access.

| # | Task | Output |
|---|------|--------|
| 7.1.1 | Implement `LoginForm.tsx`: username/password form, POST to `/auth/login`, store JWT in memory (not localStorage) | Login component |
| 7.1.2 | Implement `useAuth.ts` hook: login, logout, token refresh, expiry timer | Auth hook |
| 7.1.3 | Implement `authStore.ts`: in-memory auth state (user_id, role, token, expires_at) | Auth store |
| 7.1.4 | Implement `RoleBadge.tsx`: colour-coded badge showing user's role | Role badge |
| 7.1.5 | Redirect to login if JWT is expired or absent | Route guard |

---

### Story 7.2 — Chat Interface

**As a** user, **I want** a chat window where I can type questions and receive AI answers with source citations.

| # | Task | Output |
|---|------|--------|
| 7.2.1 | Implement `ChatWindow.tsx`: message list + input box + send button; Enter key submits | Chat window |
| 7.2.2 | Implement `MessageBubble.tsx`: user and AI message bubbles with timestamps | Message bubble |
| 7.2.3 | Implement `CitationPanel.tsx`: collapsible side panel listing citations (source file, excerpt, relevance score) | Citation panel |
| 7.2.4 | Implement `useChat.ts` hook: React Query mutation for `POST /chat`, append message to history | Chat hook |
| 7.2.5 | Show loading spinner while awaiting response; disable input during request | Loading state |
| 7.2.6 | Implement `ErrorBanner.tsx`: display API error messages (rate limit, RBAC denied, guardrail blocked) | Error banner |
| 7.2.7 | Implement `api/chat.ts`: `sendMessage(question, session_id, token) -> ChatResponse` using Axios | API client |

---

### Story 7.3 — UI Polish & Accessibility

**As a** user, **I want** a clean, accessible UI that works on desktop browsers.

| # | Task | Output |
|---|------|--------|
| 7.3.1 | Apply Tailwind CSS: dark sidebar with role info, white chat area, clean typography | Styling |
| 7.3.2 | Add keyboard shortcut: Enter sends message, Shift+Enter adds newline | Keyboard UX |
| 7.3.3 | Add character counter on input (max 1000 chars) | Input validation |
| 7.3.4 | Add "New Conversation" button that resets session_id | Session reset |
| 7.3.5 | ARIA labels on interactive elements; focus management after send | Accessibility |

---

## Epic 8 — Evaluation Suite (Ragas)

**Goal:** Automated evaluation using the 38-pair golden dataset, producing a report with pass/fail per metric.

### Story 8.1 — Answer Generation

**As a** QA engineer, **I want** a script that queries the live API for all 30 RAG pairs and collects answers.

| # | Task | Output |
|---|------|--------|
| 8.1.1 | Implement `evals/generate_answers.py`: read `golden_dataset.json`, iterate reference_required pairs, call `/chat` as the correct role, store `question`, `ground_truth`, `answer`, `contexts`, `session_id` | Answer collector |
| 8.1.2 | Output results to `evals/report/answers_<timestamp>.json` | Output file |
| 8.1.3 | Add role → JWT mapping (login before each role group) | Auth handling |
| 8.1.4 | Add `--subset` flag to run only a specific role's pairs | CLI flag |

---

### Story 8.2 — Ragas Evaluation Runner

**As a** QA engineer, **I want** Ragas metrics computed and compared to thresholds so I know if the system meets quality gates.

| # | Task | Output |
|---|------|--------|
| 8.2.1 | Implement `evals/run_ragas.py`: load answers file, run `ragas.evaluate()` with 5 metrics (faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness) | Eval runner |
| 8.2.2 | Define thresholds: faithfulness ≥ 0.80, answer_relevancy ≥ 0.75, context_precision ≥ 0.70, context_recall ≥ 0.70, answer_correctness ≥ 0.75 | Thresholds |
| 8.2.3 | Print per-metric score and PASS/FAIL status; exit with code 1 if any metric fails (for CI gate) | CI gate |
| 8.2.4 | Output full report to `evals/report/ragas_<timestamp>.json` | Report |

---

### Story 8.3 — Guardrail & RBAC Tests

**As a** QA engineer, **I want** automated tests for all 8 GUARD-* scenarios verifying expected behaviour.

| # | Task | Output |
|---|------|--------|
| 8.3.1 | Implement `evals/guardrail_tests.py`: iterate 8 reference_free pairs from golden dataset, call API, assert `expected_behaviour` matches response pattern | Guard eval |
| 8.3.2 | Implement assertion helpers: `assert_rbac_denied(response)`, `assert_pii_redacted(response)`, `assert_prompt_injection_blocked(response)`, `assert_out_of_scope_rejected(response)` | Helpers |
| 8.3.3 | Implement `evals/rbac_boundary_tests.py`: 25 cross-role access tests (each of 5 roles attempting each other role's documents) | RBAC test matrix |
| 8.3.4 | Exit with code 1 if any guardrail or RBAC test fails | CI gate |

---

## Epic 9 — Observability & LangSmith

**Goal:** Full tracing of every RAG call in LangSmith with chunk explainability and anonymized log retention.

### Story 9.1 — LangSmith Integration

**As an** engineer, **I want** every RAG pipeline run traced in LangSmith so I can debug retrieval and generation quality.

| # | Task | Output |
|---|------|--------|
| 9.1.1 | Configure LangSmith SDK: `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` env vars; enable tracing via `langsmith.trace()` decorator on `run_rag()` | Tracing setup |
| 9.1.2 | Add custom metadata to each trace: `user_role`, `prompt_version`, `num_chunks`, `top_score`, `latency_ms` | Trace metadata |
| 9.1.3 | Log chunk excerpts (max 200 chars, anonymized via Presidio before logging) in trace | Chunk excerpt |
| 9.1.4 | Add `run_id` to `ChatResponse` for traceability | Trace ID |
| 9.1.5 | Verify traces appear in LangSmith UI with correct metadata | Manual test |

---

### Story 9.2 — CloudWatch Logging

**As an** ops engineer, **I want** structured JSON logs shipped to CloudWatch so I can search and alert on them.

| # | Task | Output |
|---|------|--------|
| 9.2.1 | Configure Python `logging` to output structured JSON (using `python-json-logger`) | Log config |
| 9.2.2 | Log every chat request: `request_id`, `user_id`, `role`, `guardrail_outcome`, `num_chunks`, `latency_ms`, `tokens_used` | Request log |
| 9.2.3 | Log guardrail blocks with `guard_type` and `guard_code` (no raw query text) | Guard log |
| 9.2.4 | ECS task logs ship to CloudWatch log group `/finsolve/backend` via `awslogs` driver | Log group |

---

## Epic 10 — AWS Deployment & IaC

**Goal:** Production-grade AWS deployment via Terraform with ECS, ElastiCache, Secrets Manager, and Amplify.

### Story 10.1 — Terraform Modules

**As a** DevOps engineer, **I want** all AWS infrastructure defined in Terraform modules so it is reproducible and reviewable.

| # | Task | Output |
|---|------|--------|
| 10.1.1 | Write `infra/modules/networking/`: VPC (10.0.0.0/16), 2 public + 2 private subnets, IGW, NAT gateway, route tables, security groups (ALB 443, ECS 8000 from ALB only, Redis 6379 from ECS only) | Networking module |
| 10.1.2 | Write `infra/modules/ecs/`: ECS cluster, task definition (1 vCPU, 2GB RAM, port 8000), ECS service, ALB + target group, auto-scaling policy (70% CPU, min 1, max 4 tasks), ECR repo | ECS module |
| 10.1.3 | Write `infra/modules/redis/`: ElastiCache cluster (`cache.t3.micro`, Redis 7.2, single-node, 15-min RDB snapshots, encryption at rest) | Redis module |
| 10.1.4 | Write `infra/modules/secrets/`: Secrets Manager entries for `GROQ_API_KEY`, `QDRANT_API_KEY`, `JWT_SECRET`, `LANGSMITH_API_KEY` | Secrets module |
| 10.1.5 | Write `infra/modules/monitoring/`: CloudWatch log group (30-day retention), dashboard (request rate, latency, error rate, token usage), cost alarm ($5/day), query alarm (200/hour) | Monitoring module |
| 10.1.6 | Write `infra/main.tf`: wire all modules, pass outputs between them | Root module |
| 10.1.7 | Write `infra/variables.tf` and `terraform.tfvars.example` | Variables |
| 10.1.8 | Run `terraform plan` against staging account → 0 errors | Plan validation |

---

### Story 10.2 — Frontend AWS Amplify

**As a** DevOps engineer, **I want** the React frontend deployed to AWS Amplify with automatic builds on main branch push.

| # | Task | Output |
|---|------|--------|
| 10.2.1 | Create Amplify app via Terraform (or AWS console) pointing to GitHub repo | Amplify app |
| 10.2.2 | Configure build spec: `npm ci && npm run build` → publish `dist/` | Build spec |
| 10.2.3 | Set env var `VITE_API_BASE_URL` to ECS ALB URL in Amplify | Env var |
| 10.2.4 | Verify HTTPS, custom domain (if applicable), and CORS allow from Amplify domain | DNS/CORS |

---

### Story 10.3 — Secrets & Config Management

**As a** DevOps engineer, **I want** all secrets injected from AWS Secrets Manager into ECS tasks at runtime so no secrets are baked into images.

| # | Task | Output |
|---|------|--------|
| 10.3.1 | ECS task definition references `secrets` from Secrets Manager ARNs (not hardcoded env vars) | Task def config |
| 10.3.2 | ECS task IAM role has `secretsmanager:GetSecretValue` permission for specific secret ARNs only | IAM policy |
| 10.3.3 | Qdrant Cloud connection uses `QDRANT_URL` + `QDRANT_API_KEY` from Secrets Manager | Qdrant config |

---

## Epic 11 — CI/CD Pipeline & Evaluation Gates

**Goal:** GitHub Actions pipelines that block merges unless tests pass and block staging-to-production promotion unless Ragas thresholds pass.

### Story 11.1 — PR CI Pipeline

**As a** developer, **I want** every PR automatically linted, tested, and type-checked before it can merge.

| # | Task | Output |
|---|------|--------|
| 11.1.1 | Write `.github/workflows/ci.yml`: trigger on `pull_request` to `main` | CI workflow |
| 11.1.2 | Steps: checkout → setup Python → install deps → `ruff` lint → `mypy` type check → `pytest tests/unit/` with coverage → fail if coverage < 85% | CI steps |
| 11.1.3 | Steps (frontend): setup Node → `npm ci` → `npm run type-check` → `npm run build` | Frontend CI |
| 11.1.4 | Publish coverage report to PR as comment | Coverage report |

---

### Story 11.2 — Eval Gate Pipeline (Staging)

**As a** QA engineer, **I want** Ragas and guardrail evaluations run automatically on staging before production deployment.

| # | Task | Output |
|---|------|--------|
| 11.2.1 | Write `.github/workflows/eval-gate.yml`: trigger after staging ECS deploy succeeds | Eval gate workflow |
| 11.2.2 | Steps: run `generate_answers.py` → run `run_ragas.py` → run `guardrail_tests.py` → run `rbac_boundary_tests.py` | Eval steps |
| 11.2.3 | Upload eval reports as GitHub Actions artifacts | Artifacts |
| 11.2.4 | Fail workflow (exit 1) if any threshold not met; block production deploy | Gate enforcement |

---

### Story 11.3 — Production Deploy Pipeline

**As a** DevOps engineer, **I want** production ECS deployment gated behind eval pass and manual approval.

| # | Task | Output |
|---|------|--------|
| 11.3.1 | Write `.github/workflows/deploy.yml`: trigger on push to `main` (after eval gate succeeds) | Deploy workflow |
| 11.3.2 | Steps: `docker build` → `docker push` to ECR → `aws ecs update-service --force-new-deployment` | Deploy steps |
| 11.3.3 | Add `environment: production` with required reviewer for manual approval gate | Approval gate |
| 11.3.4 | Post deployment: run smoke test (call `/health` and `/ready` endpoints) | Smoke test |

---

## Epic 12 — Cost Monitoring & Alerting

**Goal:** Token cost and query volume tracked in CloudWatch with automated alerts at defined thresholds.

### Story 12.1 — Token Usage Tracking

**As an** ops engineer, **I want** token usage per request logged as a CloudWatch custom metric.

| # | Task | Output |
|---|------|--------|
| 12.1.1 | In `generator.py`: extract `usage.total_tokens` from Groq response and log to CloudWatch as `TokensUsed` metric with dimension `Role` | Metric emission |
| 12.1.2 | Log prompt token count and completion token count separately | Breakdown |
| 12.1.3 | Add `GROQ_COST_PER_1K_TOKENS` env var; compute estimated cost per request and emit `EstimatedCostUSD` metric | Cost metric |

---

### Story 12.2 — CloudWatch Alarms

**As an** ops engineer, **I want** alarms that page on unusual cost or query spikes.

| # | Task | Output |
|---|------|--------|
| 12.2.1 | Alarm: `HighDailyCost` → `EstimatedCostUSD` sum > $5 in 24h → SNS notification | Cost alarm |
| 12.2.2 | Alarm: `HighHourlyQueries` → query count > 200 in 1h → SNS notification | Query alarm |
| 12.2.3 | Alarm: `AbnormalTokenUsage` → single request > 4000 tokens → SNS notification | Token alarm |
| 12.2.4 | Terraform: define all alarms in `monitoring` module with `aws_cloudwatch_metric_alarm` | IaC |
| 12.2.5 | CloudWatch dashboard: panels for requests/min, p95 latency, error rate, daily cost, token usage by role | Dashboard |

---

## 15. Dependency Map

```
E1 (Foundation)
 ├── E2 (Ingestion)
 │    └── E3 (RAG Backend)
 │         ├── E4 (RBAC) ──────────────────────┐
 │         ├── E5 (Guardrails) ←── E4           │
 │         ├── E6 (Memory + Rate Limit)          │
 │         ├── E9 (LangSmith)                   │
 │         └── E7 (Frontend) ←── E4             │
 │              └── E8 (Evaluation) ←── E5 ─────┘
 │                   └── E11 (CI/CD) ←── E10
 │                        └── E12 (Cost Mon.) ←── E10
 └── E10 (AWS IaC)
```

---

## 16. Acceptance Criteria Summary

| Epic | Key Acceptance Criteria |
|------|------------------------|
| E1 | `docker compose up -d` → all 4 services healthy within 60s |
| E2 | All 10 docs ingested → Qdrant has correct chunk count + role metadata |
| E3 | FIN-001 query as finance → answer contains "$9.4 billion" |
| E4 | Finance role cannot retrieve any marketing chunks (0 results) |
| E5 | All 8 GUARD-* scenarios pass with expected_behaviour |
| E6 | 7th message in session → only last 6 pairs in context; 31st query → 429 |
| E7 | Login as all 5 roles → correct RoleBadge; citations panel shows source docs |
| E8 | Ragas scores ≥ thresholds on all 5 metrics; RBAC boundary tests 25/25 pass |
| E9 | Every `/chat` call creates a LangSmith trace with role + chunk metadata |
| E10 | `terraform apply` creates all AWS resources; ECS service healthy |
| E11 | PR with failing unit test → CI blocks merge; Ragas fail → deploy blocked |
| E12 | CloudWatch dashboard live; $5 cost alarm fires in staging load test |

---

*Plan last updated: 2026-03-31*
