"""Application FastAPI principale pour IA DCI."""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
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
    title="IA DCI",
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
    """Page d'accueil avec les outils IA DCI."""
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
    """Retourne les métriques d'utilisation de IA DCI."""
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


# ============================================================================
# STREAMING ENDPOINTS - Affichage progressif des réponses
# ============================================================================


async def _stream_generator(translator: OllamaTranslator, generator, feature_name: str):
    """Générateur SSE pour le streaming des tokens.
    
    Utilise le format Server-Sent Events avec flush forcé après chaque token.
    Ajoute du padding pour forcer les proxies à ne pas bufferiser.
    """
    import asyncio
    
    # Envoyer un commentaire SSE initial pour forcer l'ouverture du stream
    # Le ':' est un commentaire SSE qui n'est pas traité par le client
    yield ": stream opened\n\n"
    await asyncio.sleep(0)
    
    try:
        async for token in generator:
            # Format SSE: data: {"token": "..."}
            # On ajoute un peu de padding pour forcer le flush des proxies
            message = f"data: {json.dumps({'token': token})}\n\n"
            yield message
            # Force un flush du buffer en cédant le contrôle à l'event loop
            await asyncio.sleep(0)
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.log("ERROR", f"Streaming error for {feature_name}", error=str(e))
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        await translator.close()


@app.post("/translate-text-stream")
async def translate_text_stream_endpoint(
    text: str = Form(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    model: Optional[str] = Form(None),
) -> StreamingResponse:
    """Traduit un texte via Ollama avec streaming progressif."""
    if source_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported source language: {source_lang}")

    if target_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported target language: {target_lang}")

    if source_lang == target_lang:
        raise HTTPException(400, "Source and target languages must be different")

    if not text.strip():
        raise HTTPException(400, "Text to translate cannot be empty")

    translator = OllamaTranslator()
    generator = translator.translate_text_stream(text, source_lang, target_lang, model)

    metrics.text_translations += 1
    logger.log(
        "INFO",
        "Text translation stream started",
        source_lang=source_lang,
        target_lang=target_lang,
        model=model or settings.OLLAMA_MODEL,
    )

    return StreamingResponse(
        _stream_generator(translator, generator, "translation"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
            "Content-Encoding": "identity",
        },
    )


@app.post("/correct-text-stream")
async def correct_text_stream_endpoint(
    text: str = Form(...),
    model: Optional[str] = Form(None),
) -> StreamingResponse:
    """Corrige un texte avec streaming progressif."""
    if not text.strip():
        raise HTTPException(400, "Text to correct cannot be empty")

    translator = OllamaTranslator()
    generator = translator.correct_text_stream(text, model)

    metrics.corrections += 1
    logger.log("INFO", "Text correction stream started", model=model or settings.OLLAMA_MODEL)

    return StreamingResponse(
        _stream_generator(translator, generator, "correction"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
            "Content-Encoding": "identity",
        },
    )


@app.post("/reformulate-text-stream")
async def reformulate_text_stream_endpoint(
    text: str = Form(...),
    model: Optional[str] = Form(None),
) -> StreamingResponse:
    """Reformule un texte avec streaming progressif."""
    if not text.strip():
        raise HTTPException(400, "Text to reformulate cannot be empty")

    translator = OllamaTranslator()
    generator = translator.reformulate_text_stream(text, model)

    metrics.reformulations += 1
    logger.log("INFO", "Text reformulation stream started", model=model or settings.OLLAMA_MODEL)

    return StreamingResponse(
        _stream_generator(translator, generator, "reformulation"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
            "Content-Encoding": "identity",
        },
    )


@app.post("/meeting-summary-stream")
async def meeting_summary_stream_endpoint(
    text: str = Form(""),
    image_base64: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
) -> StreamingResponse:
    """Génère un compte rendu avec streaming progressif."""
    has_text = text.strip() if text else False
    has_image = image_base64 and len(image_base64) > 100

    if not has_text and not has_image:
        raise HTTPException(400, "Veuillez fournir des notes texte ou une image")

    translator = OllamaTranslator()
    generator = translator.summarize_meeting_stream(
        text=text if has_text else None,
        image_base64=image_base64 if has_image else None,
        model=model,
    )

    metrics.meeting_summaries += 1
    logger.log(
        "INFO",
        "Meeting summary stream started",
        model=model or settings.OLLAMA_MODEL,
        has_image=has_image,
    )

    return StreamingResponse(
        _stream_generator(translator, generator, "meeting_summary"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
            "Content-Encoding": "identity",
        },
    )


def _sanitize_json_string(text: str) -> str:
    """Nettoie une chaîne JSON en échappant les caractères de contrôle invalides.
    
    Les LLMs retournent parfois des sauts de ligne non échappés dans les valeurs JSON,
    ce qui provoque des erreurs de parsing.
    """
    result = []
    in_string = False
    escape_next = False
    
    for char in text:
        if escape_next:
            result.append(char)
            escape_next = False
            continue
            
        if char == '\\':
            result.append(char)
            escape_next = True
            continue
            
        if char == '"':
            in_string = not in_string
            result.append(char)
            continue
        
        # Si on est dans une chaîne, échapper les caractères de contrôle
        if in_string:
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif ord(char) < 32:  # Autres caractères de contrôle
                result.append(f'\\u{ord(char):04x}')
            else:
                result.append(char)
        else:
            result.append(char)
    
    return ''.join(result)


def _load_json_payload(raw_payload: str, context: str) -> dict:
    """Charge un payload JSON renvoyé par le modèle.
    
    Nettoie les éventuels blocs markdown (```json ... ```) 
    que certains LLMs ajoutent autour du JSON.
    Gère le cas où le modèle retourne plusieurs blocs JSON.
    Échappe les caractères de contrôle invalides dans les chaînes.
    """
    # Stratégie 1: Extraire tous les blocs markdown ```json ... ```
    json_blocks = re.findall(r'```json\s*(.*?)\s*```', raw_payload, re.DOTALL)
    
    # Essayer chaque bloc JSON en commençant par le dernier (souvent le plus propre)
    for block in reversed(json_blocks):
        try:
            sanitized = _sanitize_json_string(block.strip())
            return json.loads(sanitized)
        except json.JSONDecodeError:
            continue
    
    # Stratégie 2: Nettoyer le payload brut si pas de bloc markdown valide
    cleaned = raw_payload.strip()
    
    # Retirer ```json ou ``` au début
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    
    # Retirer ``` à la fin
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    
    cleaned = cleaned.strip()
    
    # Stratégie 3: Chercher le premier objet JSON valide dans le texte
    # Trouver toutes les occurrences potentielles de JSON ({...})
    brace_start = cleaned.find('{')
    while brace_start != -1:
        depth = 0
        in_string = False
        escape_next = False
        for i, char in enumerate(cleaned[brace_start:], brace_start):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
            elif not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[brace_start:i+1]
                        try:
                            sanitized = _sanitize_json_string(candidate)
                            return json.loads(sanitized)
                        except json.JSONDecodeError:
                            break
        brace_start = cleaned.find('{', brace_start + 1)
    
    # Stratégie 4: Essai direct avec le texte nettoyé et sanitisé
    try:
        sanitized = _sanitize_json_string(cleaned)
        return json.loads(sanitized)
    except json.JSONDecodeError as exc:
        logger.log(
            "ERROR",
            "Invalid JSON payload received",
            context=context,
            error=str(exc),
            payload=raw_payload[:500] + "..." if len(raw_payload) > 500 else raw_payload,
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
    text: str = Form(""),
    image_base64: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
) -> dict[str, object]:
    """Génère un compte rendu de réunion à partir de notes texte ou d'une image."""
    has_text = text.strip() if text else False
    has_image = image_base64 and len(image_base64) > 100
    
    if not has_text and not has_image:
        raise HTTPException(400, "Veuillez fournir des notes texte ou une image")

    async with OllamaTranslator() as translator:
        raw_response = await translator.summarize_meeting(
            text=text if has_text else None,
            image_base64=image_base64 if has_image else None,
            model=model
        )

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
    logger.log("INFO", "Meeting summary generated", model=model or settings.OLLAMA_MODEL, has_image=has_image)

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


# ============================================================================
# SCENARI XML TRANSLATION ENDPOINTS
# ============================================================================

from typing import List
from fastapi import UploadFile, File
import base64
import asyncio

from app.scenari import ScenariTranslator, create_zip_from_results, TranslationResult


@app.post("/scenari/preview")
async def scenari_preview_endpoint(
    files: List[UploadFile] = File(...),
) -> dict:
    """Prévisualise le nombre d'éléments à traduire dans les fichiers XML SCENARI."""
    results = []
    total_elements = 0
    
    async with OllamaTranslator() as translator:
        scenari = ScenariTranslator(translator)
        
        for file in files:
            if not file.filename or not file.filename.endswith('.xml'):
                continue
            
            content = await file.read()
            await file.seek(0)  # Reset pour potentielle lecture ultérieure
            
            count = scenari.count_translatable_elements(content)
            total_elements += count
            results.append({
                "filename": file.filename,
                "elements": count
            })
    
    return {
        "files": results,
        "total_elements": total_elements
    }


@app.post("/scenari/translate")
async def scenari_translate_endpoint(
    files: List[UploadFile] = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    model: Optional[str] = Form(None),
) -> StreamingResponse:
    """Traduit des fichiers XML SCENARI avec streaming de progression."""
    if source_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported source language: {source_lang}")

    if target_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported target language: {target_lang}")

    if source_lang == target_lang:
        raise HTTPException(400, "Source and target languages must be different")

    if not files:
        raise HTTPException(400, "No files provided")

    # Lire tous les fichiers en mémoire
    file_contents: List[tuple[str, bytes]] = []
    for file in files:
        if not file.filename or not file.filename.endswith('.xml'):
            continue
        content = await file.read()
        file_contents.append((file.filename, content))

    if not file_contents:
        raise HTTPException(400, "No valid XML files provided")

    async def generate_stream():
        translator = OllamaTranslator()
        scenari = ScenariTranslator(translator)
        results: List[TranslationResult] = []
        
        try:
            total_files = len(file_contents)
            
            for file_idx, (filename, content) in enumerate(file_contents, 1):
                async for progress, result in scenari.translate_file(
                    xml_content=content,
                    filename=filename,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    model=model,
                ):
                    # Émettre la progression
                    progress_data = {
                        "type": "progress",
                        "file_index": file_idx,
                        "total_files": total_files,
                        "filename": progress.filename,
                        "current_element": progress.current_element,
                        "total_elements": progress.total_elements,
                        "current_text": progress.current_text,
                        "status": progress.status,
                    }
                    if progress.error_message:
                        progress_data["error"] = progress.error_message
                    
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    await asyncio.sleep(0)
                    
                    if result:
                        results.append(result)
            
            # Générer le fichier résultat
            if len(results) == 1:
                # Un seul fichier : retourner directement le contenu
                result = results[0]
                content_b64 = base64.b64encode(result.translated_content).decode('utf-8')
                yield f"data: {json.dumps({'type': 'complete', 'filename': result.translated_filename, 'content_base64': content_b64, 'content_type': 'application/xml'})}\n\n"
            elif len(results) > 1:
                # Plusieurs fichiers : créer un ZIP
                zip_content = create_zip_from_results(results)
                content_b64 = base64.b64encode(zip_content).decode('utf-8')
                yield f"data: {json.dumps({'type': 'complete', 'filename': f'scenari_translated_{target_lang}.zip', 'content_base64': content_b64, 'content_type': 'application/zip'})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.log("ERROR", "SCENARI translation error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            await translator.close()

    logger.log(
        "INFO",
        "SCENARI translation started",
        source_lang=source_lang,
        target_lang=target_lang,
        file_count=len(file_contents),
        model=model or settings.OLLAMA_MODEL,
    )

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
            "Content-Encoding": "identity",
        },
    )


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

