"""Configuration de l'application DCIA."""
import os
from typing import Optional


class Settings:
    """Paramètres de configuration de l'application."""
    
    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral-small:latest")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    OLLAMA_MAX_RETRIES: int = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
    
    # Upload
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
    MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024
    ALLOWED_MIME_TYPES: set = {"application/xml", "text/xml"}
    
    # Traduction
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    
    # Proxy
    HTTP_PROXY: Optional[str] = os.getenv("HTTP_PROXY")
    HTTPS_PROXY: Optional[str] = os.getenv("HTTPS_PROXY")
    NO_PROXY: Optional[str] = os.getenv("NO_PROXY")
    
    # App
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Langues supportées
    SUPPORTED_LANGUAGES: dict = {
        "fr": "Français",
        "en": "English",
        "ar": "العربية"
    }
    
    RTL_LANGUAGES: set = {"ar"}


settings = Settings()
