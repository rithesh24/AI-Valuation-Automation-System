from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ".env" is the developer/dev-machine config. "data/local.env" is written
    # at runtime by settings_service.py (the in-app Settings screen, for a
    # packaged build where the client has no .env to hand-edit) and loads
    # second, so a client-entered API key overrides whatever (if anything)
    # ".env" provided.
    model_config = SettingsConfigDict(
        env_file=(".env", "data/local.env"), env_file_encoding="utf-8"
    )

    ENV: str = "development"
    DATABASE_PATH: str = "data/avas.db"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-5"
    ANTHROPIC_MAX_RETRIES: int = 2
    ANTHROPIC_RETRY_DELAY_SECONDS: float = 3.0
    # Placeholder Sonnet-class list pricing (USD per million tokens) — update once
    # real usage/billing is available (see docs/DECISIONS.md D18).
    ANTHROPIC_INPUT_PRICE_PER_MTOK: float = 3.0
    ANTHROPIC_OUTPUT_PRICE_PER_MTOK: float = 15.0
    CORS_ORIGINS: str = "http://localhost:3000"
    UPLOAD_DIR: str = "data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    REPORTS_DIR: str = "data/reports"
    TESSERACT_CMD: str = ""
    OCR_TRIGGER_CHAR_THRESHOLD: int = 20
    EASR_HEADLESS: bool = True
    EASR_TIMEOUT_MS: int = 30000
    EASR_MAX_RETRIES: int = 2
    EASR_RETRY_DELAY_SECONDS: float = 3.0
    EASR_MAX_RESULT_PAGES: int = 10

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
