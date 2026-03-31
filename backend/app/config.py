from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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

    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
