# FinSolve AI Assistant — Developer Commands
# Install just: https://github.com/casey/just
# Usage: just <recipe>

set dotenv-load := true

# Show available commands
default:
    @just --list

# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------

# Start all services (detached)
up:
    docker compose up -d

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
    docker compose up -d --build

# ---------------------------------------------------------------------------
# Data Ingestion
# ---------------------------------------------------------------------------

# Ingest all documents (incremental upsert)
ingest:
    docker compose exec backend uv run python -m ingest.ingest

# Drop Qdrant collection and re-ingest from scratch
ingest-reset:
    docker compose exec backend uv run python -m ingest.ingest --reset

# Dry-run: show chunk counts without writing to Qdrant
ingest-dry:
    docker compose exec backend uv run python -m ingest.ingest --dry-run

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

# Install Python dependencies locally (for IDE support)
install:
    cd backend && uv sync

# Run backend locally (outside Docker)
dev-backend:
    cd backend && uv run uvicorn app.main:app --reload --port 8000

# Open an interactive shell in the running backend container
shell:
    docker compose exec backend bash

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

# Install Node dependencies
install-frontend:
    cd frontend && npm install

# Run frontend dev server locally (outside Docker)
dev-frontend:
    cd frontend && npm run dev

# Build frontend for production
build-frontend:
    cd frontend && npm run build

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

# Run all unit tests
test:
    cd backend && uv run pytest tests/unit -v

# Run integration tests (requires running Qdrant + Redis)
test-integration:
    cd backend && uv run pytest tests/integration -v

# Run all tests with coverage report
test-cov:
    cd backend && uv run pytest tests/ --cov=app --cov-report=term-missing

# ---------------------------------------------------------------------------
# Linting & Formatting
# ---------------------------------------------------------------------------

# Lint Python code
lint:
    cd backend && uv run ruff check .

# Format Python code
fmt:
    cd backend && uv run ruff format .

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

# Run Ragas evaluation suite against staging endpoint
eval:
    cd backend && uv run python -m evals.run_ragas

# Run RBAC boundary tests
test-rbac:
    cd backend && uv run pytest evals/rbac_boundary_tests.py -v

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

# Copy .env.example to .env (first-time setup)
init:
    cp -n .env.example .env && echo ".env created — fill in GROQ_API_KEY and JWT_SECRET"

# Generate a random JWT secret
gen-secret:
    python -c "import secrets; print(secrets.token_hex(32))"
