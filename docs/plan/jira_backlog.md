# RBAC-Chatbot Jira Backlog — Project RC

> **Project:** RBAC-Chatbot (`RC`) · invoice-automation.atlassian.net  
> **Total Issues:** 149 (12 Epics · 40 Stories · 97 Subtasks)  
> **Generated:** 2026-03-31

---

## E1 · Project Foundation & DevEnv `RC-1`

### S1.1 · Repository Scaffold `RC-13`
| Key | Subtask |
|-----|---------|
| RC-53 | Create full directory tree with `__init__.py` files |
| RC-54 | Write `backend/pyproject.toml` with all Python dependencies |
| RC-55 | Write `frontend/package.json` with React 18, TS, Vite, Tailwind, Axios, React Query |
| RC-56 | Write `.env.example` with all 25+ required env vars |
| RC-57 | Update `README.md` with setup steps and role credentials table |

### S1.2 · Docker Compose Local Stack `RC-14`
| Key | Subtask |
|-----|---------|
| RC-58 | Write `backend/Dockerfile` (Python 3.11-slim, non-root user, health check) |
| RC-59 | Write `frontend/Dockerfile` (Node 20-alpine, multi-stage: build + nginx) |
| RC-60 | Write `docker-compose.yml` with 4 services, volumes, healthchecks, depends_on |
| RC-61 | Verify all 4 services start healthy with `docker compose ps` |

### S1.3 · Configuration Management `RC-15`
_(No subtasks — covered by RC-56 above)_

---

## E2 · Data Ingestion Pipeline `RC-2`

### S2.1 · Markdown Chunker `RC-16`
_(No subtasks — implementation covered in ingestion epic)_

### S2.2 · CSV Row Chunker `RC-17`
_(No subtasks — implementation covered in ingestion epic)_

### S2.3 · Chunk Metadata Schema & RBAC Access Matrix `RC-18`
_(No subtasks — covered by metadata schema tasks)_

### S2.4 · Embedding & Qdrant Upsert `RC-19`
| Key | Subtask |
|-----|---------|
| RC-62 | Implement `embedder.py` wrapping `sentence-transformers/all-MiniLM-L6-v2` (384-dim, batch=32) |
| RC-63 | Implement `qdrant_client.py`: create collection (cosine, 384 dims), batch upsert |
| RC-64 | Implement `ingest.py` CLI with `--dry-run` and `--reset` flags |
| RC-65 | Integration test: ingest `financial_summary.md` → assert 1 point in Qdrant with correct payload |

### S2.5 · Embedding Model Versioning `RC-20`
_(No subtasks — covered by embedder implementation)_

---

## E3 · Core RAG Backend (FastAPI) `RC-3`

### S3.1 · FastAPI App Skeleton `RC-21`
_(No subtasks — covered by scaffold tasks)_

### S3.2 · Qdrant Retriever with RBAC Filter `RC-22`
| Key | Subtask |
|-----|---------|
| RC-66 | Implement `rag/retriever.py`: embed query → search Qdrant with role filter → top-5 (score ≥ 0.60) |
| RC-67 | Apply RBAC filter as Qdrant `must` condition on `allowed_roles` field |
| RC-68 | Unit test: mock Qdrant, assert role filter is applied in every search request |

### S3.3 · LLM Generator (Groq + LangChain) `RC-23`
_(No subtasks — covered by pipeline tasks)_

### S3.4 · RAG Pipeline Orchestrator `RC-24`
| Key | Subtask |
|-----|---------|
| RC-69 | Implement `rag/pipeline.py`: `run_rag(query, user_context, session_history)` → `RagResult` |
| RC-70 | Implement optional `rag/rewriter.py` feature-flagged via `ENABLE_QUERY_REWRITE` env var |
| RC-71 | Integration test: FIN-001 query as finance role → answer contains "$9.4 billion" |

### S3.5 · Chat Router & Service `RC-25`
_(No subtasks)_

### S3.6 · Health & Readiness Endpoints `RC-26`
_(No subtasks)_

---

## E4 · RBAC & Authentication `RC-4`

### S4.1 · Mock Auth & JWT `RC-27`
| Key | Subtask |
|-----|---------|
| RC-72 | Implement `auth/service.py`: static user store (5 accounts), bcrypt-hashed passwords |
| RC-73 | Implement `create_jwt()` → HS256 JWT (8h expiry) and `verify_jwt()` → `UserContext` or 401 |
| RC-74 | Implement `POST /auth/login` → `{access_token, token_type, expires_in, role}` |
| RC-75 | Unit tests: valid login → token; invalid password → 401; expired token → 401 |

### S4.2 · RBAC Enforcement (Dual-Layer) `RC-28`
| Key | Subtask |
|-----|---------|
| RC-76 | Implement `auth/rbac.py`: `ROLE_DOCUMENT_ACCESS` dict, `get_allowed_docs()`, `can_access()` |
| RC-77 | Unit test: finance cannot access marketing docs; executive can access all 10 docs |
| RC-78 | Integration test: marketing content query as finance role → 0 chunks retrieved |

---

## E5 · Guardrails & Safety `RC-5`

### S5.1 · Input Guard: Prompt Injection Detection `RC-29`
| Key | Subtask |
|-----|---------|
| RC-87 | Implement `injection.py`: keyword list check (ignore previous instructions, jailbreak, etc.) |
| RC-88 | Add embedding similarity check vs known injection templates (cosine > 0.85 → block) |
| RC-89 | Unit test: GUARD-006 query → blocked; normal "what is Q4 revenue" → not blocked |

### S5.2 · Input Guard: Out-of-Scope Detection `RC-30`
| Key | Subtask |
|-----|---------|
| RC-90 | Implement `scope.py`: keyword check for off-topic domains (politics, sports, AI trends, etc.) |
| RC-91 | Add embedding similarity check vs "FinSolve internal company data" anchor (sim < 0.35 → block) |
| RC-92 | Unit test: GUARD-005 "AI trends" → blocked; "What is the notice period?" → not blocked |

### S5.3 · Input Guard: PII Bulk Extraction Detection `RC-31`
| Key | Subtask |
|-----|---------|
| RC-93 | Implement `pii.py`: Presidio `AnalyzerEngine` for PII detection in query text |
| RC-94 | Add heuristic: plural PII request + aggregation terms (all, list, every) → block GUARD-002 |

### S5.4 · Output Guard: PII Redaction `RC-32`
| Key | Subtask |
|-----|---------|
| RC-95 | Implement `output_guard.py`: run Presidio `AnonymizerEngine` on LLM response text |
| RC-96 | Configure redaction rules: `SALARY→[REDACTED-SALARY]`, `DATE_OF_BIRTH→[REDACTED-DOB]`, PHONE, EMAIL |
| RC-97 | Unit test: response containing "salary: 800,000" → output has `[REDACTED-SALARY]` |

### S5.5 · Output Guard: Source Boundary Enforcement `RC-33`
| Key | Subtask |
|-----|---------|
| RC-98 | In `output_guard.py`: iterate citations, drop any with `source_file` not in `allowed_docs(role)` |
| RC-99 | If all citations stripped, append fallback: "I could not find relevant information in your accessible documents." |

### S5.6 · Input Guard Orchestrator `RC-34`
| Key | Subtask |
|-----|---------|
| RC-79 | Implement `guardrails/input_guard.py`: `check_input(query, role)` → `GuardResult` (injection → scope → PII) |
| RC-80 | Integration test: run all 8 GUARD-* golden dataset scenarios → assert `expected_behaviour` |

---

## E6 · Conversation Memory & Rate Limiting `RC-6`

### S6.1 · Redis Session Memory `RC-35`
| Key | Subtask |
|-----|---------|
| RC-100 | Implement `memory/session.py`: `save_turn()` and `get_history()` with Redis LTRIM to 12 entries |
| RC-101 | Set Redis session key TTL = 8 hours (matching JWT expiry) |
| RC-102 | Integrate session into `chat/service.py`: load history before RAG, save turn after generation |
| RC-103 | Unit test: save 7 turns → `get_history` returns only last 6 pairs (12 entries trimmed) |

### S6.2 · Redis Rate Limiter `RC-36`
| Key | Subtask |
|-----|---------|
| RC-104 | Implement `rate_limit/limiter.py`: sliding window counter `check_and_increment(user_id, window, limit)` |
| RC-105 | Implement per-role hourly limits: 30 (default), 50 (finance/engineering), 100 (executive) from env vars |
| RC-106 | Return 429 with `Retry-After` header when rate limit exceeded |
| RC-107 | Unit test: 30 requests succeed; 31st returns False; counter resets after 3600s |

---

## E7 · React Frontend `RC-7`

### S7.1 · Auth & Login UI `RC-37`
| Key | Subtask |
|-----|---------|
| RC-108 | Implement `LoginForm.tsx`: username/password form, POST `/auth/login`, store JWT in memory |
| RC-109 | Implement `useAuth.ts` hook: login, logout, token refresh, 8h expiry timer |
| RC-110 | Implement `RoleBadge.tsx`: colour-coded badge per role (finance/hr/marketing/engineering/executive) |

### S7.2 · Chat Interface `RC-38`
| Key | Subtask |
|-----|---------|
| RC-111 | Implement `ChatWindow.tsx`: message list + input box + send button; Enter submits |
| RC-112 | Implement `CitationPanel.tsx`: collapsible panel showing source file, excerpt (200 chars), score |
| RC-113 | Implement `ErrorBanner.tsx`: display 429 rate-limit, 403 RBAC denied, 400 guardrail blocked errors |
| RC-114 | Implement `api/chat.ts`: `sendMessage(question, session_id, token)` → `ChatResponse` using Axios |

### S7.3 · UI Polish & Accessibility `RC-39`
| Key | Subtask |
|-----|---------|
| RC-115 | Apply Tailwind CSS: dark sidebar with role info, white chat area, clean typography |
| RC-116 | Add keyboard shortcuts: Enter sends, Shift+Enter adds newline; character counter (max 1000) |
| RC-117 | Add "New Conversation" button that generates new `session_id` and clears message history |

---

## E8 · Evaluation Suite (Ragas) `RC-8`

### S8.1 · Answer Generation Script `RC-40`
| Key | Subtask |
|-----|---------|
| RC-118 | Implement `generate_answers.py`: read `golden_dataset.json`, login per role, call `/chat` for each pair |
| RC-119 | Store question, ground_truth, answer, contexts per result; output to `evals/report/answers_<timestamp>.json` |

### S8.2 · Ragas Evaluation Runner `RC-41`
| Key | Subtask |
|-----|---------|
| RC-81 | Implement `run_ragas.py` with 5 metrics and threshold enforcement (exit code 1 on fail) |
| RC-82 | Output full eval report to `evals/report/ragas_<timestamp>.json` |

### S8.3 · Guardrail & RBAC Boundary Tests `RC-42`
| Key | Subtask |
|-----|---------|
| RC-120 | Implement `guardrail_tests.py`: iterate 8 GUARD-* pairs, assert `expected_behaviour` with helpers |
| RC-121 | Implement `rbac_boundary_tests.py`: 25 cross-role tests (5 roles × 5 doc sets); exit 1 on any failure |

---

## E9 · Observability & LangSmith `RC-9`

### S9.1 · LangSmith Tracing Integration `RC-43`
| Key | Subtask |
|-----|---------|
| RC-122 | Configure LangSmith SDK with `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT` env vars |
| RC-123 | Decorate `run_rag()` with `langsmith.trace()`; add `user_role`, `prompt_version`, `num_chunks`, `top_score` metadata |
| RC-124 | Log chunk excerpts (max 200 chars, Presidio-anonymized) in trace; add `run_id` to `ChatResponse` |

### S9.2 · Structured CloudWatch Logging `RC-44`
| Key | Subtask |
|-----|---------|
| RC-125 | Configure `python-json-logger` for structured JSON log output |
| RC-126 | Log every chat request: `request_id`, `user_id`, `role`, `guardrail_outcome`, `num_chunks`, `latency_ms`, `tokens_used` |
| RC-127 | Configure ECS task `awslogs` driver to ship logs to CloudWatch log group `/finsolve/backend` |

---

## E10 · AWS Deployment & IaC `RC-10`

### S10.1 · Terraform Infrastructure Modules `RC-45`
| Key | Subtask |
|-----|---------|
| RC-83 | Write `modules/networking/`: VPC, subnets, IGW, NAT gateway, security groups |
| RC-84 | Write `modules/ecs/`: cluster, task def (1vCPU/2GB), ALB, auto-scaling (70% CPU, min 1 / max 4) |
| RC-85 | Write `modules/redis/` (cache.t3.micro), `modules/secrets/`, `modules/monitoring/` |
| RC-86 | Run `terraform plan` → validate 0 errors against staging account |

### S10.2 · Frontend AWS Amplify Deployment `RC-46`
| Key | Subtask |
|-----|---------|
| RC-128 | Create AWS Amplify app connected to GitHub repo; configure build spec (`npm ci && npm run build`) |
| RC-129 | Set `VITE_API_BASE_URL` env var in Amplify; verify HTTPS and CORS from Amplify domain |

### S10.3 · Secrets & Runtime Config Management `RC-47`
| Key | Subtask |
|-----|---------|
| RC-130 | ECS task definition: reference `GROQ_API_KEY`, `QDRANT_API_KEY`, `JWT_SECRET`, `LANGSMITH_API_KEY` from Secrets Manager ARNs |

---

## E11 · CI/CD Pipeline & Evaluation Gates `RC-11`

### S11.1 · PR CI Pipeline `RC-48`
| Key | Subtask |
|-----|---------|
| RC-131 | Write `ci.yml`: trigger on `pull_request` to main, define backend and frontend jobs |
| RC-132 | Backend CI steps: ruff lint → mypy type-check → pytest unit tests → fail if coverage < 85% |
| RC-133 | Frontend CI steps: `npm ci` → tsc type-check → vite build → fail on type errors |
| RC-134 | Publish pytest coverage report as PR comment via coverage-comment action |

### S11.2 · Staging Eval Gate Pipeline `RC-49`
| Key | Subtask |
|-----|---------|
| RC-135 | Write `eval-gate.yml`: trigger on push to main, deploy to staging ECS task |
| RC-136 | Run `generate_answers.py` against staging, execute `run_ragas.py`, assert all 5 metric thresholds pass |
| RC-137 | Run `rbac_boundary_tests.py` and `guardrail_tests.py`; fail pipeline if any assertion fails |
| RC-138 | Upload Ragas report JSON as GitHub Actions artifact for audit trail |

### S11.3 · Production Deploy Pipeline `RC-50`
| Key | Subtask |
|-----|---------|
| RC-139 | Write `deploy.yml`: trigger manually (`workflow_dispatch`) with environment input (staging/prod) |
| RC-140 | Add GitHub Environment protection rule: require 1 manual approver before prod deploy job runs |
| RC-141 | Deploy step: build & push Docker image to ECR, update ECS service with new task definition revision |
| RC-142 | Post-deploy smoke test: `curl /health` endpoint, assert 200 within 2 minutes of ECS service stabilization |

---

## E12 · Cost Monitoring & Alerting `RC-12`

### S12.1 · Token Usage Tracking `RC-51`
| Key | Subtask |
|-----|---------|
| RC-143 | Instrument RAG pipeline to emit `TokensUsed` CloudWatch metric per request with role dimension |
| RC-144 | Calculate `EstimatedCostUSD` from token count using Groq pricing; emit as second CloudWatch metric |
| RC-145 | Aggregate daily cost totals per role in CloudWatch; verify metric data appears in console within 5 min |

### S12.2 · CloudWatch Alarms & Dashboard `RC-52`
| Key | Subtask |
|-----|---------|
| RC-146 | Create CloudWatch alarm: `EstimatedCostUSD` > $5/day → SNS alert to ops email |
| RC-147 | Create CloudWatch alarm: `RequestCount` > 200/hr → SNS alert; alarm: `TokensUsed` > 4000/request |
| RC-148 | Build CloudWatch Dashboard: widgets for `TokensUsed` by role, `EstimatedCostUSD` trend, request rate |
| RC-149 | Define all alarms and dashboard in Terraform monitoring module; validate with `terraform plan` |

---

## Quick Reference

### Issue Count by Type
| Type | Count |
|------|-------|
| Epic | 12 |
| Story | 40 |
| Subtask | 97 |
| **Total** | **149** |

### Issue Count by Epic
| Epic | Stories | Subtasks |
|------|---------|----------|
| E1 — Project Foundation & DevEnv | 3 | 9 |
| E2 — Data Ingestion Pipeline | 5 | 4 |
| E3 — Core RAG Backend (FastAPI) | 6 | 8 |
| E4 — RBAC & Authentication | 2 | 7 |
| E5 — Guardrails & Safety | 6 | 14 |
| E6 — Conversation Memory & Rate Limiting | 2 | 8 |
| E7 — React Frontend | 3 | 10 |
| E8 — Evaluation Suite (Ragas) | 3 | 6 |
| E9 — Observability & LangSmith | 2 | 6 |
| E10 — AWS Deployment & IaC | 3 | 7 |
| E11 — CI/CD Pipeline & Evaluation Gates | 3 | 8 |
| E12 — Cost Monitoring & Alerting | 2 | 7 |

### Jira Issue Range by Epic
| Epic | Key Range |
|------|-----------|
| E1 | RC-13 to RC-15, RC-53 to RC-61 |
| E2 | RC-16 to RC-20, RC-62 to RC-65 |
| E3 | RC-21 to RC-26, RC-66 to RC-71 |
| E4 | RC-27 to RC-28, RC-72 to RC-78 |
| E5 | RC-29 to RC-34, RC-79 to RC-99 |
| E6 | RC-35 to RC-36, RC-100 to RC-107 |
| E7 | RC-37 to RC-39, RC-108 to RC-117 |
| E8 | RC-40 to RC-42, RC-81 to RC-82, RC-118 to RC-121 |
| E9 | RC-43 to RC-44, RC-122 to RC-127 |
| E10 | RC-45 to RC-47, RC-83 to RC-86, RC-128 to RC-130 |
| E11 | RC-48 to RC-50, RC-131 to RC-138 |
| E12 | RC-51 to RC-52, RC-139 to RC-149 |
