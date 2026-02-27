"""
Application Configuration
Loads and validates environment variables
"""
import os
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Enterprise Attendance System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # MongoDB
    MONGODB_URL: str = os.getenv("DB_URL")
    MONGODB_DB_NAME: str = "attendance_system"
    
    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 500

    # Groq API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_STT_MODEL: str = os.getenv("GROQ_STT_Model","whisper-large-v3-turbo")
    GROQ_TTS_MODEL: str = os.getenv("GROQ_TTS_Model","playai-tts")
    GROQ_TTS_VOICE: str = os.getenv("GROQ_TTS_Voice","Fritz-PlayAI")
    
    # Local LLM
    USE_LOCAL_LLM: bool = False
    LOCAL_LLM_MODEL: str = "llama2"
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = os.getenv("EMAIL_FROM")
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 5242880  # 5MB
    UPLOAD_DIR: str = "./uploads"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_ENABLED: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # Attendance
    AUTO_CHECKOUT_ENABLED: bool = True
    AUTO_CHECKOUT_TIME: str = "18:00"
    LATE_ARRIVAL_THRESHOLD_MINUTES: int = 15
    EARLY_DEPARTURE_THRESHOLD_MINUTES: int = 30
    
    # Leave
    MAX_CASUAL_LEAVE_DAYS: int = 12
    MAX_SICK_LEAVE_DAYS: int = 10
    MAX_ANNUAL_LEAVE_DAYS: int = 20
    
    # Geolocation
    GEOLOCATION_ENABLED: bool = False
    OFFICE_LATITUDE: float = 0.0
    OFFICE_LONGITUDE: float = 0.0
    GEOFENCE_RADIUS_METERS: int = 100
    
    # Fingerprint
    FINGERPRINT_ENABLED: bool = True
    FINGERPRINT_DEVICE_PORT: str = "COM3"
    FINGERPRINT_BAUD_RATE: int = 57600
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS origins string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
