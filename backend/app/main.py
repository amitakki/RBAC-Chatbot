from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title="FinSolve AI Assistant",
    description="Enterprise RAG Chatbot with RBAC, Guardrails & Monitoring",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.is_local else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers are registered here as each epic is completed:
# from app.health.router import router as health_router   # Epic 3
# from app.auth.router import router as auth_router       # Epic 4
# from app.chat.router import router as chat_router       # Epic 3
# app.include_router(health_router)
# app.include_router(auth_router, prefix="/auth")
# app.include_router(chat_router, prefix="/chat")


@app.get("/", tags=["root"])
def root() -> dict:
    return {"status": "ok", "environment": settings.environment}
