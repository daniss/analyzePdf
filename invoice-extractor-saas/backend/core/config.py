from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "ComptaFlow"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:password@localhost/invoiceai"
    )
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://invoiceai.com"
    ]
    
    # File upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf", "image/jpeg", "image/png"]
    
    # Storage (GDPR-compliant: no local file storage)
    STORAGE_BACKEND: str = "memory"  # Files processed in memory only
    # LOCAL_STORAGE_PATH removed - GDPR compliance (no unencrypted files on disk)
    AWS_BUCKET_NAME: str = os.getenv("AWS_BUCKET_NAME", "")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # AI Settings - Groq with Llama 3.1 8B
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    AI_MODEL: str = "llama-3.1-8b-instant"  # Groq Llama 3.1 8B
    MAX_TOKENS: int = 8192
    
    
    # PDF Processing
    PDF_DPI: int = 300  # DPI for PDF to image conversion
    MAX_PAGES: int = 10  # Maximum pages to process per invoice
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # INSEE API Configuration for French compliance
    INSEE_API_KEY: str = os.getenv("INSEE_API_KEY", "")
    INSEE_API_SECRET: str = os.getenv("INSEE_API_SECRET", "")
    
    # GDPR and Encryption
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "your-32-byte-encryption-key-change-this!")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()

def get_settings() -> Settings:
    """Get application settings instance"""
    return settings