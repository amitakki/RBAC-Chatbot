# FinSolve AI Assistant - Developer Commands
# Install just: https://github.com/casey/just
# Usage: just <recipe>

set dotenv-load := true
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# Show available commands
default:
    @just --list

# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------

# Start infrastructure only (Qdrant + Redis) in Docker
up:
    docker compose up -d qdrant redis

# Start the full Docker stack, including backend and frontend containers
up-full:
    docker compose --profile app up -d

# Start only infrastructure (Qdrant + Redis), no app containers
infra:
    docker compose up -d qdrant redis

# Stop all services
down:
    docker compose down

# Stop and remove volumes (full reset)
down-volumes:
    docker compose down -v

# Show service status and health
ps:
    docker compose ps

# Stream logs from all services
logs:
    docker compose logs -f

# Stream logs from a specific service: just log backend
log service:
    docker compose logs -f {{service}}

# Rebuild and restart all containers
rebuild:
    docker compose --profile app up -d --build

# ---------------------------------------------------------------------------
# Data Ingestion
# ---------------------------------------------------------------------------

# Ingest all documents (incremental upsert)
ingest:
    cd backend; uv run python -m ingest.ingest

# Drop Qdrant collection and re-ingest from scratch
ingest-reset:
    cd backend; uv run python -m ingest.ingest --reset

# Dry-run: show chunk counts without writing to Qdrant
ingest-dry:
    cd backend; uv run python -m ingest.ingest --dry-run

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

# Install Python dependencies locally (for IDE support)
install:
    cd backend; uv sync

# Run backend locally (outside Docker)
dev-backend:
    cd backend; uv run uvicorn app.main:app --reload --port 8000

# Open an interactive shell in the running backend container
shell:
    docker compose --profile app exec backend bash

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

# Install Node dependencies
install-frontend:
    cd frontend; npm install

# Run frontend dev server locally (outside Docker)
dev-frontend:
    cd frontend; npm run dev

# Build frontend for production
build-frontend:
    cd frontend; npm run build

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

# Run all unit tests
test:
    cd backend; uv run pytest tests/unit -v

# Run integration tests (requires running Qdrant + Redis)
test-integration:
    cd backend; uv run pytest tests/integration -v

# Run all tests with coverage report
test-cov:
    cd backend; uv run pytest tests/ --cov=app --cov-report=term-missing

# ---------------------------------------------------------------------------
# Linting & Formatting
# ---------------------------------------------------------------------------

# Lint Python code
lint:
    cd backend; uv run ruff check .

# Format Python code
fmt:
    cd backend; uv run ruff format .

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

# Run Ragas evaluation suite against staging endpoint
eval:
    cd backend; uv run --extra evals python ../evals/run_ragas.py

# Run RBAC boundary tests
test-rbac:
    cd backend; uv run pytest ../evals/rbac_boundary_tests.py -v

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

# Copy .env.example to .env (first-time setup)
init:
    if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Output ".env created - fill in GROQ_API_KEY and JWT_SECRET" } else { Write-Output ".env already exists" }

# Generate a random JWT secret
gen-secret:
    python -c "import secrets; print(secrets.token_hex(32))"
