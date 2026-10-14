from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "multimodal-support-bot"

    upload_dir: str = "./uploads"
    retention_seconds: int = 3600
    processing_timeout_seconds: int = 30
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./chatbot.db"

    max_file_size_mb: int = 15
    allowed_mime_types: tuple = (
        "image/png",
        "image/jpeg",
        "image/webp",
        "application/pdf",
    )
    ocr_min_confidence: float = 60.0
    ocr_min_dpi_width: int = 800

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()