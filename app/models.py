"""Modèles Pydantic pour validation des données."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


class TranslationRequest(BaseModel):
    """Requête de traduction."""
    source_lang: str = Field(..., pattern="^(fr|en|ar)$")
    target_lang: str = Field(..., pattern="^(fr|en|ar)$")
    model: str = Field(default="llama3.2:latest")
    
    @field_validator('target_lang')
    @classmethod
    def check_languages_different(cls, v, info):
        """Vérifie que source et cible sont différentes."""
        if 'source_lang' in info.data and v == info.data['source_lang']:
            raise ValueError("Source and target languages must be different")
        return v


class SegmentInfo(BaseModel):
    """Information sur un segment traduit."""
    xpath: str
    original: str
    translated: str
    success: bool
    error: Optional[str] = None


class TranslationReport(BaseModel):
    """Rapport de traduction."""
    total_segments: int
    translated: int
    failed: int
    ignored: int
    duration_seconds: float
    segments: List[SegmentInfo] = Field(default_factory=list)
    
    
class HealthResponse(BaseModel):
    """Réponse du healthcheck."""
    status: str
    ollama_available: bool
    ollama_url: str
