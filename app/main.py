"""Application FastAPI principale pour DCIA."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.models import HealthResponse
from app.translator import OllamaTranslator

# Configuration du logging structuré
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(message)s",
)


class StructuredLogger:
    """Logger avec sortie JSON structurée."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log(self, level: str, message: str, **kwargs) -> None:
        """Log un message avec métadonnées."""
        log_entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **kwargs,
        }
        self.logger.log(getattr(logging, level), json.dumps(log_entry))


logger = StructuredLogger(__name__)

# Initialisation FastAPI
app = FastAPI(
    title="DCIA",
    description=(
        "Suite d'assistants linguistiques internes DCI permettant la traduction, la correction et la génération de comptes rendus."
    ),
    version="2.0.0",
)

# CORS minimal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Templates et fichiers statiques
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent.parent / "static"

templates = Jinja2Templates(directory=str(templates_dir))

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class Metrics:
    """Métriques simples pour suivre l'utilisation."""

    def __init__(self) -> None:
        self.text_translations = 0
        self.corrections = 0
        self.reformulations = 0
        self.meeting_summaries = 0

    def snapshot(self) -> dict[str, int]:
        """Retourne un instantané des métriques."""
        return {
            "text_translations": self.text_translations,
            "corrections": self.corrections,
            "reformulations": self.reformulations,
            "meeting_summaries": self.meeting_summaries,
        }


metrics = Metrics()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Page d'accueil avec les outils DCIA."""
    context = {
        "request": request,
        "languages": settings.SUPPORTED_LANGUAGES,
        "rtl_languages": list(settings.RTL_LANGUAGES),
        "default_model": settings.OLLAMA_MODEL,
    }
    return templates.TemplateResponse(request, "index.html", context)


@app.get("/healthz")
async def health_check() -> HealthResponse:
    """Endpoint de healthcheck."""
    async with OllamaTranslator() as translator:
        ollama_available = await translator.check_health()

    status = "healthy" if ollama_available else "degraded"
    return HealthResponse(
        status=status,
        ollama_available=ollama_available,
        ollama_url=settings.OLLAMA_BASE_URL,
    )


@app.get("/metrics")
async def get_metrics() -> dict[str, int]:
    """Retourne les métriques d'utilisation de DCIA."""
    return metrics.snapshot()


@app.post("/translate-text")
async def translate_text_endpoint(
    text: str = Form(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    model: Optional[str] = Form(None),
) -> dict[str, str]:
    """Traduit un texte brut via Ollama."""
    if source_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported source language: {source_lang}")

    if target_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported target language: {target_lang}")

    if source_lang == target_lang:
        raise HTTPException(400, "Source and target languages must be different")

    if not text.strip():
        raise HTTPException(400, "Text to translate cannot be empty")

    async with OllamaTranslator() as translator:
        translated_text = await translator.translate_text(
            text,
            source_lang,
            target_lang,
            model,
        )

    if translated_text is None:
        raise HTTPException(502, "Failed to translate text with Ollama")

    metrics.text_translations += 1
    logger.log(
        "INFO",
        "Text translated",
        source_lang=source_lang,
        target_lang=target_lang,
        model=model or settings.OLLAMA_MODEL,
    )

    return {"translated_text": translated_text}


def _load_json_payload(raw_payload: str, context: str) -> dict:
    """Charge un payload JSON renvoyé par le modèle."""
    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - log path
        logger.log(
            "ERROR",
            "Invalid JSON payload received",
            context=context,
            error=str(exc),
            payload=raw_payload,
        )
        raise HTTPException(502, "Réponse du modèle invalide") from exc


@app.post("/correct-text")
async def correct_text_endpoint(
    text: str = Form(...),
    model: Optional[str] = Form(None),
) -> dict[str, object]:
    """Corrige un texte et fournit des explications."""
    if not text.strip():
        raise HTTPException(400, "Text to correct cannot be empty")

    async with OllamaTranslator() as translator:
        raw_response = await translator.correct_text(text, model)

    if raw_response is None:
        raise HTTPException(502, "Failed to correct text with Ollama")

    data = _load_json_payload(raw_response, "correction")
    corrected_text = str(data.get("corrected_text", "")).strip()
    explanations = data.get("explanations") or []

    if not isinstance(explanations, list):
        explanations = [str(explanations)]

    metrics.corrections += 1
    logger.log("INFO", "Text corrected", model=model or settings.OLLAMA_MODEL)

    return {
        "corrected_text": corrected_text,
        "explanations": explanations,
    }


@app.post("/reformulate-text")
async def reformulate_text_endpoint(
    text: str = Form(...),
    model: Optional[str] = Form(None),
) -> dict[str, object]:
    """Reformule un texte en conservant le sens."""
    if not text.strip():
        raise HTTPException(400, "Text to reformulate cannot be empty")

    async with OllamaTranslator() as translator:
        raw_response = await translator.reformulate_text(text, model)

    if raw_response is None:
        raise HTTPException(502, "Failed to reformulate text with Ollama")

    data = _load_json_payload(raw_response, "reformulation")
    reformulated_text = str(data.get("reformulated_text", "")).strip()
    highlights = data.get("highlights") or []

    if not isinstance(highlights, list):
        highlights = [str(highlights)]

    metrics.reformulations += 1
    logger.log("INFO", "Text reformulated", model=model or settings.OLLAMA_MODEL)

    return {
        "reformulated_text": reformulated_text,
        "highlights": highlights,
    }


@app.post("/meeting-summary")
async def meeting_summary_endpoint(
    text: str = Form(...),
    model: Optional[str] = Form(None),
) -> dict[str, object]:
    """Génère un compte rendu de réunion à partir de notes."""
    if not text.strip():
        raise HTTPException(400, "Notes to summarise cannot be empty")

    async with OllamaTranslator() as translator:
        raw_response = await translator.summarize_meeting(text, model)

    if raw_response is None:
        raise HTTPException(502, "Failed to summarise meeting notes with Ollama")

    data = _load_json_payload(raw_response, "meeting_summary")
    summary = str(data.get("summary", "")).strip()
    decisions = data.get("decisions") or []
    action_items = data.get("action_items") or []

    if not isinstance(decisions, list):
        decisions = [str(decisions)] if decisions else []
    if not isinstance(action_items, list):
        action_items = [str(action_items)] if action_items else []

    metrics.meeting_summaries += 1
    logger.log("INFO", "Meeting summary generated", model=model or settings.OLLAMA_MODEL)

    return {
        "summary": summary,
        "decisions": decisions,
        "action_items": action_items,
    }


@app.get("/models", response_class=JSONResponse)
async def list_models() -> JSONResponse:
    """Retourne la liste des modèles disponibles côté Ollama."""
    async with OllamaTranslator() as translator:
        models = await translator.list_models()

    unique_models: list[str] = []
    seen = set()
    for name in models:
        if name and name not in seen:
            seen.add(name)
            unique_models.append(name)

    default_model = settings.OLLAMA_MODEL
    if default_model:
        if default_model in seen:
            unique_models = [default_model] + [m for m in unique_models if m != default_model]
        else:
            unique_models.insert(0, default_model)
    elif not unique_models:
        unique_models = []

    if not unique_models and default_model:
        unique_models = [default_model]

    if not unique_models:
        unique_models = ["default_model"]

    return JSONResponse({"models": unique_models, "default_model": default_model})


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
