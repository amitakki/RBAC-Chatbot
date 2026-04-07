import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router  # Epic 4 ✓
from app.chat.router import router as chat_router  # Epic 3 ✓
from app.config import settings
from app.health.router import router as health_router  # Epic 3 ✓
from app.observability.logging_config import configure_logging

# RC-125: structured JSON logging — must run before the first request is handled
configure_logging()

# RC-122: ensure LangSmith env vars are propagated from settings so @traceable
# picks them up (LangChain reads LANGCHAIN_TRACING_V2 at import time on some
# versions, so setdefault is safe — it won't overwrite values already set in env)
if settings.langchain_tracing_v2 and settings.langsmith_api_key:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)

app = FastAPI(
    title="FinSolve AI Assistant",
    description="Enterprise RAG Chatbot with RBAC, Guardrails & Monitoring",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins if settings.is_local else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)                       # /health, /ready
app.include_router(auth_router, prefix="/auth")         # /auth/login
app.include_router(chat_router, prefix="/chat")         # /chat/


@app.get("/", tags=["root"])
def root() -> dict:
    return {"status": "ok", "environment": settings.environment}
