"""Application FastAPI principale pour SCENARI Translator."""
import logging
import json
import hashlib
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import Response, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import TranslationReport, SegmentInfo, HealthResponse
from app.xml_processor import XMLProcessor
from app.translator import OllamaTranslator

# Configuration du logging structuré
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(message)s'
)

class StructuredLogger:
    """Logger avec sortie JSON structurée."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log(self, level: str, message: str, **kwargs):
        """Log un message avec métadonnées."""
        log_entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logger.log(getattr(logging, level), json.dumps(log_entry))


logger = StructuredLogger(__name__)

# Initialisation FastAPI
app = FastAPI(
    title="SCENARI Translator",
    description="Traduction de fichiers XML SCENARI via Ollama",
    version="1.0.0"
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


# Métriques simples
class Metrics:
    """Métriques de l'application."""
    
    def __init__(self):
        self.total_translations = 0
        self.total_segments_translated = 0
        self.total_segments_failed = 0
        self.total_duration = 0.0
    
    def record_translation(self, report: TranslationReport):
        """Enregistre une traduction."""
        self.total_translations += 1
        self.total_segments_translated += report.translated
        self.total_segments_failed += report.failed
        self.total_duration += report.duration_seconds


metrics = Metrics()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Page d'accueil avec formulaire de traduction."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "languages": settings.SUPPORTED_LANGUAGES,
            "rtl_languages": list(settings.RTL_LANGUAGES),
            "default_model": settings.OLLAMA_MODEL,
            "max_upload_mb": settings.MAX_UPLOAD_MB,
        }
    )


@app.get("/healthz")
async def health_check():
    """Endpoint de healthcheck."""
    translator = OllamaTranslator()
    ollama_available = translator.check_health()
    translator.close()
    
    return HealthResponse(
        status="healthy" if ollama_available else "degraded",
        ollama_available=ollama_available,
        ollama_url=settings.OLLAMA_BASE_URL
    )


@app.get("/metrics")
async def get_metrics():
    """Métriques de l'application."""
    return {
        "total_translations": metrics.total_translations,
        "total_segments_translated": metrics.total_segments_translated,
        "total_segments_failed": metrics.total_segments_failed,
        "average_duration": (
            metrics.total_duration / metrics.total_translations
            if metrics.total_translations > 0
            else 0
        ),
    }


@app.post("/translate")
async def translate_file(
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    model: Optional[str] = Form(None),
):
    """
    Traduit un fichier XML SCENARI.
    
    Args:
        file: Fichier XML à traduire
        source_lang: Langue source (fr, en, ar)
        target_lang: Langue cible (fr, en, ar)
        model: Modèle Ollama à utiliser
    
    Returns:
        Fichier XML traduit
    """
    start_time = time.time()
    request_id = hashlib.md5(f"{time.time()}".encode()).hexdigest()[:8]
    
    logger.log(
        "INFO",
        "Translation request received",
        request_id=request_id,
        filename=file.filename,
        source_lang=source_lang,
        target_lang=target_lang,
        model=model or settings.OLLAMA_MODEL,
    )
    
    # Validation
    if source_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported source language: {source_lang}")
    
    if target_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported target language: {target_lang}")
    
    if source_lang == target_lang:
        raise HTTPException(400, "Source and target languages must be different")
    
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            400,
            f"Invalid file type. Expected XML, got {file.content_type}"
        )
    
    # Lire le fichier
    try:
        content = await file.read()

        if len(content) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                413,
                f"File too large. Max size: {settings.MAX_UPLOAD_MB}MB"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.log("ERROR", "Error reading file", request_id=request_id, error=str(e))
        raise HTTPException(500, f"Error reading file: {e}")
    
    # Parser le XML
    processor = XMLProcessor()
    if not processor.parse(content):
        raise HTTPException(400, "Invalid XML file")
    
    # Extraire les segments traduisibles
    segments = processor.extract_translatable_segments()
    
    if not segments:
        raise HTTPException(400, "No translatable segments found in XML")
    
    logger.log(
        "INFO",
        "Segments extracted",
        request_id=request_id,
        count=len(segments),
    )
    
    # Traduire les segments
    translator = OllamaTranslator()
    report_segments = []
    translated_count = 0
    failed_count = 0
    
    try:
        for i, (element, xpath, text) in enumerate(segments):
            logger.log(
                "DEBUG",
                "Translating segment",
                request_id=request_id,
                segment_num=i + 1,
                total=len(segments),
                xpath=xpath,
            )
            
            translated_text = translator.translate_text(
                text,
                source_lang,
                target_lang,
                model
            )
            
            if translated_text:
                success = processor.update_segment(element, translated_text)
                if success:
                    translated_count += 1
                    report_segments.append(
                        SegmentInfo(
                            xpath=xpath,
                            original=text[:100],  # Limiter pour le rapport
                            translated=translated_text[:100],
                            success=True,
                        )
                    )
                else:
                    failed_count += 1
                    report_segments.append(
                        SegmentInfo(
                            xpath=xpath,
                            original=text[:100],
                            translated="",
                            success=False,
                            error="Failed to update XML",
                        )
                    )
            else:
                failed_count += 1
                report_segments.append(
                    SegmentInfo(
                        xpath=xpath,
                        original=text[:100],
                        translated="",
                        success=False,
                        error="Translation failed",
                    )
                )
        
        # Mettre à jour xml:lang
        processor.update_language(target_lang)
        
        # Générer le XML traduit
        output_xml = processor.to_bytes()
        
    finally:
        translator.close()
    
    # Créer le rapport
    duration = time.time() - start_time
    report = TranslationReport(
        total_segments=len(segments),
        translated=translated_count,
        failed=failed_count,
        ignored=0,
        duration_seconds=duration,
        segments=report_segments,
    )
    
    metrics.record_translation(report)
    
    logger.log(
        "INFO",
        "Translation completed",
        request_id=request_id,
        translated=translated_count,
        failed=failed_count,
        duration=duration,
    )
    
    # Générer le nom de fichier de sortie
    original_filename = Path(file.filename).stem
    file_hash = hashlib.md5(content).hexdigest()[:8]
    output_filename = f"{original_filename}.{source_lang}-{target_lang}.{file_hash}.xml"
    
    # Ajouter le rapport dans les headers
    headers = {
        "X-Translation-Report": json.dumps(report.model_dump()),
        "Content-Disposition": f'attachment; filename="{output_filename}"',
    }
    
    return Response(
        content=output_xml,
        media_type="application/xml",
        headers=headers,
    )


@app.post("/translate-text")
async def translate_text_endpoint(
    text: str = Form(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    model: Optional[str] = Form(None),
):
    """Traduit un texte brut via Ollama."""

    if source_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported source language: {source_lang}")

    if target_lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Unsupported target language: {target_lang}")

    if source_lang == target_lang:
        raise HTTPException(400, "Source and target languages must be different")

    if not text.strip():
        raise HTTPException(400, "Text to translate cannot be empty")

    translator = OllamaTranslator()

    try:
        translated_text = translator.translate_text(
            text,
            source_lang,
            target_lang,
            model,
        )
    finally:
        translator.close()

    if translated_text is None:
        raise HTTPException(502, "Failed to translate text with Ollama")

    return {"translated_text": translated_text}


@app.get("/models", response_class=JSONResponse)
async def list_models():
    """Retourne la liste des modèles disponibles côté Ollama."""
    translator = OllamaTranslator()
    try:
        models = translator.list_models()
    finally:
        translator.close()

    # Toujours faire apparaître le modèle par défaut en premier
    unique_models = []
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

    return {"models": unique_models, "default_model": default_model}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
