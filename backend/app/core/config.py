import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from pydantic import AnyHttpUrl, validator, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application settings
    PROJECT_NAME: str = "RAG System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "1"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").upper()
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # Frontend default
        "http://localhost:8000",  # Backend default
    ]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database settings
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "raguser")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "ragpassword")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "ragdb")
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @field_validator("DATABASE_URL", mode='before')
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            path=f"{values.get('POSTGRES_DB') or ''}",
        )
    
    # RAG settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.2")
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    
    # File upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf", "text/plain", 
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    
    # Security settings
    SECURE_COOKIES: bool = not DEBUG
    SESSION_COOKIE_NAME: str = "rag_session"
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "your-session-secret-key")
    
    # Email settings (for password reset, etc.)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    @validator("EMAILS_FROM_NAME")
    def get_project_name(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            return values["PROJECT_NAME"]
        return v
    
    # First superuser
    FIRST_SUPERUSER: str = os.getenv("FIRST_SUPERUSER", "admin@example.com")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "changethis")
    
    # HuggingFace
    HUGGINGFACEHUB_API_TOKEN: Optional[str] = os.getenv("HUGGINGFACEHUB_API_TOKEN", None)
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Model configuration
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

# Create settings instance
settings = Settings()

# Create upload directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
