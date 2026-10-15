from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://docguard:docguard_dev@localhost:5432/docguard"
    GEMINI_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "mistral-medium-latest"
    MISTRAL_VISION_MODEL: str = "pixtral-12b-2409"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
