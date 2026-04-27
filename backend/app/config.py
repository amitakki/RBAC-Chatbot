from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    llm_provider: Literal["groq", "ollama"] = "groq"
    groq_api_key: str | None = None

    # Vector DB
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "finsolve_docs"

    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 8

    # Redis
    redis_url: str = "redis://localhost:6379"

    # LangSmith
    langsmith_api_key: str | None = None
    langsmith_project: str = "finsolve-chatbot"
    langchain_tracing_v2: bool = False

    # Embedding & Prompts
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dims: int = 384
    hf_token: str | None = None
    prompt_version: str = "v1"

    # Application
    environment: str = "local"
    cors_allow_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Rate limiting
    rate_limit_default_per_hour: int = 30
    rate_limit_default_per_day: int = 100
    rate_limit_finance_per_hour: int = 50
    rate_limit_engineering_per_hour: int = 50
    rate_limit_executive_per_hour: int = 100
    max_query_length_chars: int = 1000

    # Data
    data_dir: str = "../data"

    # RAG pipeline
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.0
    groq_timeout_seconds: int = 10
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str | None = None
    ollama_temperature: float = 0.0
    ollama_timeout_seconds: int = 10
    llm_retry_attempts: int = 2
    llm_retry_backoff_seconds: int = 2
    session_history_max_messages: int = 12
    langsmith_chunk_excerpt_max_chars: int = 200
    # Retrieval controls for Qdrant search.
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.55
    enable_query_rewrite: bool = False
    enable_multi_query: bool = False
    enable_step_back: bool = False
    multi_query_count: int = 3
    # Reranking (cross-encoder, optional)
    enable_reranking: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_top_n: int = 3
    # Hybrid search (BM25 + dense RRF fusion, optional)
    enable_hybrid_search: bool = False
    bm25_model: str = "Qdrant/bm25"
    hybrid_prefetch_limit_multiplier: int = 2

    # Guardrails
    injection_similarity_threshold: float = 0.85
    scope_similarity_threshold: float = 0.05

    # Health checks
    health_redis_timeout_seconds: int = 2

    # Cost monitoring (RC-143, RC-144)
    # Groq LLaMA 3.3-70B pricing as of 2026-Q1 (USD per 1 000 tokens)
    groq_cost_per_1k_input_tokens: float = 0.00059
    groq_cost_per_1k_output_tokens: float = 0.00079
    cloudwatch_metrics_enabled: bool = False   # set True in staging/production
    cloudwatch_namespace: str = "FinSolveAI/TokenUsage"
    aws_region: str = "us-east-1"

    @field_validator(
        "groq_api_key",
        "qdrant_api_key",
        "langsmith_api_key",
        "hf_token",
        "ollama_model",
        mode="before",
    )
    @classmethod
    def empty_strings_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.split("#", 1)[0].strip()
            return cleaned or None
        return value

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalize_llm_provider(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.split("#", 1)[0].strip()
            if not cleaned:
                return []
            return [origin.strip() for origin in cleaned.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_llm_settings(self) -> "Settings":
        if self.llm_provider == "groq" and not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        if self.llm_provider == "ollama" and not self.ollama_model:
            raise ValueError("OLLAMA_MODEL is required when LLM_PROVIDER=ollama")
        return self

    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
