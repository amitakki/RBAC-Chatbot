# FinSolve Internal AI Assistant

Enterprise RAG chatbot for FinSolve Technologies with Role-Based Access Control (RBAC), guardrails, and full observability. Built on FastAPI + LangChain + Qdrant with configurable Groq or Ollama LLM backends.

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
#   LLM_PROVIDER=groq
#   GROQ_API_KEY=<your key from console.groq.com>
#   JWT_SECRET=<generate: python -c "import secrets; print(secrets.token_hex(32))">
#   HF_TOKEN=<optional; useful for Hugging Face model downloads/rate limits>
#
# Or for local Ollama:
#   LLM_PROVIDER=ollama
#   OLLAMA_MODEL=llama3.2
#   OLLAMA_BASE_URL=http://localhost:11434

# 3. Start infrastructure in Docker
just up

# 4. Run the backend locally
just dev-backend

# 5. Run the frontend locally
just dev-frontend

# 6. Ingest source documents into Qdrant (first time only)
just ingest-reset

# 7. Open the app
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

## Local Development

```bash
# Backend
cd backend
uv sync
# Uses ../.env from the repository root
# Expects Qdrant and Redis on localhost, typically via `just infra`
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

> Qdrant and Redis still run in Docker. Start them with:
> ```bash
> docker compose up qdrant redis -d
> ```

`HF_TOKEN` is optional for the default public embedding model, but recommended if
you hit Hugging Face download limits or switch to a gated/private model.

For Groq, set `LLM_PROVIDER=groq` and provide `GROQ_API_KEY`.
For Ollama, set `LLM_PROVIDER=ollama`, provide `OLLAMA_MODEL`, and ensure the
Ollama server is reachable at `OLLAMA_BASE_URL`.

If you want the full Docker stack instead, use:

```bash
just up-full
```

### Optional: Hybrid BM25 + Dense Search

By default, retrieval uses only dense vector search. For improved recall with terminology-heavy queries, you can enable hybrid search combining BM25 sparse keywords with dense vectors via Qdrant's Reciprocal Rank Fusion (RRF).

```bash
# 1. Enable hybrid search in .env
echo "ENABLE_HYBRID_SEARCH=true" >> .env

# 2. Reinstall and re-ingest
cd backend
uv sync
uv run python -m ingest.ingest --reset
```

This is optional and off by default — existing dense-only behavior is preserved until explicitly enabled.

---

## Common Commands

```bash
just init             # Copy .env.example → .env (first time)
just up               # Start Qdrant + Redis only
just up-full          # Start the full Docker stack
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
| LLM | Groq or Ollama via LangChain |
| Embeddings (Dense) | `all-MiniLM-L6-v2` (sentence-transformers) |
| Embeddings (Sparse BM25, optional) | `fastembed` + Qdrant native RRF (hybrid search) |
| RAG Framework | LangChain 0.3 |
| Vector DB | Qdrant Cloud (prod) / Docker (local) with optional hybrid RRF |
| Backend | FastAPI + Python 3.11 |
| Frontend | React 18 + TypeScript + Tailwind |
| Session / Rate Limit | Redis (ElastiCache in AWS) |
| PII Detection | Microsoft Presidio |
| Observability | LangSmith |
| Evaluation | Ragas |
| Cloud | AWS ECS + Fargate + Amplify |
| IaC | Terraform |
