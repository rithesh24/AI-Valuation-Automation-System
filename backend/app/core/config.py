from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENV: str = "development"
    ANTHROPIC_API_KEY: str = ""
    CORS_ORIGINS: str = "http://localhost:3000"
    UPLOAD_DIR: str = "data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
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
