# FinSolve Internal AI Assistant

Enterprise RAG chatbot for FinSolve Technologies with Role-Based Access Control (RBAC), guardrails, and full observability. Built on FastAPI + LangChain + Qdrant + Groq (LLaMA 3.1 70B).

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker + Docker Compose | 24+ |
| Python | 3.11+ (for local dev without Docker) |
| Node.js | 20+ (for frontend dev) |
| uv | Latest (`pip install uv`) |

---

## Quick Start

```bash
# 1. Clone
git clone <repo-url>
cd RBAC-Chatbot

# 2. Set up environment
cp .env.example .env
# Edit .env — minimum required:
#   GROQ_API_KEY=<your key from console.groq.com>
#   JWT_SECRET=<generate: python -c "import secrets; print(secrets.token_hex(32))">

# 3. Start all services (Qdrant + Redis + Backend + Frontend)
just up

# 4. Ingest source documents into Qdrant (first time only)
just ingest-reset

# 5. Open the app
open http://localhost:3000
```

---

## Mock User Credentials

The login form accepts any username. Select a role from the dropdown to authenticate as that role.

| Role | Access |
|------|--------|
| `finance` | Financial summaries, quarterly reports, market reports (Q4) |
| `hr` | Employee handbook, HR data (PII) |
| `marketing` | All marketing reports (annual + Q1–Q4) |
| `engineering` | Engineering master document |
| `executive` | Full access to all documents |

---

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/` | Health ping | None |
| `GET` | `/health` | Liveness check | None |
| `GET` | `/ready` | Readiness check (Qdrant + Redis) | None |
| `POST` | `/auth/login` | Get JWT token | None |
| `POST` | `/chat` | Send a message | Bearer JWT |
| `GET` | `/chat/history` | Retrieve session history | Bearer JWT |

Full API docs available at `http://localhost:8000/docs` in local/staging.

---

## Local Development (without Docker)

```bash
# Backend
cd backend
uv sync
cp ../.env.example .env   # fill required vars
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

> Qdrant and Redis still need to be running. Start them via Docker:
> ```bash
> docker compose up qdrant redis -d
> ```

---

## Common Commands

```bash
just init             # Copy .env.example → .env (first time)
just up               # Start all services
just ingest-reset     # Drop collection + re-ingest all docs
just ingest           # Incremental ingest (upsert only)
just test             # Unit tests
just test-integration # Integration tests (needs running services)
just test-cov         # Tests with coverage report
just lint             # Ruff linter
just fmt              # Ruff formatter
just logs             # Stream all service logs
just down             # Stop all services
```

Run `just` with no arguments to see all available commands.

---

## Project Structure

```
RBAC-Chatbot/
├── backend/          FastAPI application + ingestion pipeline
├── frontend/         React 18 + TypeScript chat UI
├── infra/            Terraform modules (AWS ECS, Redis, Secrets)
├── evals/            Ragas evaluation suite + RBAC boundary tests
├── data/             Source documents (10 files, gitignored in prod)
├── scripts/          Helper scripts (ingestion, reset)
├── docs/             Requirements & implementation plan
├── docker-compose.yml
└── .env.example
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | LLaMA 3.1 70B via Groq |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers) |
| RAG Framework | LangChain 0.3 |
| Vector DB | Qdrant Cloud (prod) / Docker (local) |
| Backend | FastAPI + Python 3.11 |
| Frontend | React 18 + TypeScript + Tailwind |
| Session / Rate Limit | Redis (ElastiCache in AWS) |
| PII Detection | Microsoft Presidio |
| Observability | LangSmith |
| Evaluation | Ragas |
| Cloud | AWS ECS + Fargate + Amplify |
| IaC | Terraform |
