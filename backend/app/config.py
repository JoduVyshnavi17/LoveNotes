
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LoveNotes"
    environment: str = "development"

    # AI configuration
    openai_api_key: str = ""
    ai_model: str = "gpt-4.1-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # OCR configuration
    ocr_provider: str = "gemini_vision"
    ocr_language: str = "eng"
    tesseract_cmd: str = ""

    # Authentication
    jwt_secret_key: str = "development-secret-change-before-launch"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Database
    database_url: str = "sqlite:///./notemind.db"

    # File storage
    upload_dir: str = "../storage/uploads"
    max_upload_mb: int = 20

    # Frontend
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
