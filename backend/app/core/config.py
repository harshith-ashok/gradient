from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+psycopg://gradient:gradient@localhost:5433/gradient"
    redis_url: str = "redis://localhost:6380/0"

    jwt_secret: str = "dev-only-secret-change-me-dev-only-secret"
    jwt_algorithm: str = "HS256"
    access_ttl_minutes: int = 15
    refresh_ttl_days: int = 7
    cookie_secure: bool = False
    cookie_domain: str | None = None

    cors_origins: str = "http://localhost:3000"
    demo_mode: bool = True
    # Plan days roll over at midnight in this timezone.
    app_timezone: str = "UTC"

    # --- AI pipeline ---
    # "ollama" talks to the local Ollama server; "fake" is a deterministic stand-in for tests/CI.
    llm_provider: str = "ollama"
    ollama_url: str = "http://100.74.98.40:11434"
    # Text model for topics, sub-topics, study material and questions. Keep this on a model that runs
    # on your own server: a "-cloud" model would send syllabus text to a third party.
    llm_model: str = "gpt-oss:20b"
    # Vision model, used to read scanned or handwritten syllabi.
    vision_model: str = "gemma4:e4b"
    # Embedding model for retrieval. If it is not installed, generation still works from the
    # syllabus text without retrieval.
    embed_model: str = "nomic-embed-text"
    llm_timeout_seconds: int = 600
    llm_num_ctx: int = 16384
    llm_retries: int = 2
    chroma_url: str | None = None  # e.g. http://chromadb:8000; unset uses an in-process store
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 20
    ai_planning: bool = True  # have the model personalise each plan (the rules still guarantee coverage)
    verify_questions: bool = True  # have the model answer each question blind and drop mismatches
    job_stale_minutes: int = 15

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.llm_model.endswith("-cloud") or s.vision_model.endswith("-cloud"):
        raise RuntimeError("Cloud models are not allowed: syllabus text must stay on your own server")
    if s.env != "dev" and s.jwt_secret.startswith("dev-only"):
        raise RuntimeError("JWT_SECRET must be set outside dev")
    return s
