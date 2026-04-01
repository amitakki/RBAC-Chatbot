from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    groq_api_key: str

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
    prompt_version: str = "v1"

    # Application
    environment: str = "local"

    # Rate limiting
    rate_limit_default_per_hour: int = 30
    rate_limit_default_per_day: int = 100
    max_query_length_chars: int = 1000

    # Data
    data_dir: str = "../data"

    # RAG pipeline
    groq_model: str = "llama-3.3-70b-versatile"
    groq_timeout_seconds: int = 10
    retrieval_top_k: int = 5
    retrieval_score_threshold: float = 0.55
    enable_query_rewrite: bool = False

    # Guardrails
    injection_similarity_threshold: float = 0.85
    scope_similarity_threshold: float = 0.05

    @field_validator("qdrant_api_key", "langsmith_api_key", mode="before")
    @classmethod
    def empty_strings_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.split("#", 1)[0].strip()
            return cleaned or None
        return value

    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
