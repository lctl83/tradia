"""Client Ollama asynchrone pour DCIA."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker léger pour éviter les appels répétés en cas d'échec."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "closed"  # closed, open, half-open

    def call_failed(self) -> None:
        """Enregistre un échec."""
        self.failures += 1
        self.last_failure_time = time.time()

        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning("Circuit breaker OPEN after %s failures", self.failures)

    def call_succeeded(self) -> None:
        """Réinitialise l'état après un succès."""
        self.failures = 0
        self.state = "closed"

    def can_attempt(self) -> bool:
        """Indique si un appel peut être tenté."""
        if self.state == "closed":
            return True

        if self.state == "open":
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.timeout:
                self.state = "half-open"
                logger.info("Circuit breaker moving to HALF-OPEN")
                return True
            return False

        # half-open: autoriser une tentative
        return True


class OllamaTranslator:
    """Client asynchrone pour interagir avec Ollama."""

    SYSTEM_PROMPTS: Dict[tuple[str, str], str] = {
        ("fr", "en"): (
            "You are a translator. Translate the following French text to English. "
            "Return ONLY the translated text, without any explanation, formatting, or additional content. "
            "Preserve punctuation and tone."
        ),
        ("fr", "ar"): (
            "أنت مترجم. ترجم النص الفرنسي التالي إلى العربية. أعد النص المترجم فقط، دون أي تفسير أو تنسيق أو محتوى إضافي. "
            "احتفظ بعلامات الترقيم والنبرة."
        ),
        ("en", "fr"): (
            "Tu es un traducteur. Traduis le texte anglais suivant en français. Retourne UNIQUEMENT le texte traduit, "
            "sans explication, formatage ou contenu additionnel. Préserve la ponctuation et le ton."
        ),
        ("en", "ar"): (
            "أنت مترجم. ترجم النص الإنجليزي التالي إلى العربية. أعد النص المترجم فقط، دون أي تفسير أو تنسيق أو محتوى إضافي. "
            "احتفظ بعلامات الترقيم والنبرة."
        ),
        ("ar", "fr"): (
            "Tu es un traducteur. Traduis le texte arabe suivant en français. Retourne UNIQUEMENT le texte traduit, sans explication, "
            "formatage ou contenu additionnel. Préserve la ponctuation et le ton."
        ),
        ("ar", "en"): (
            "You are a translator. Translate the following Arabic text to English. Return ONLY the translated text, "
            "without any explanation, formatting, or additional content. Preserve punctuation and tone."
        ),
    }

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.max_retries = settings.OLLAMA_MAX_RETRIES
        self.circuit_breaker = CircuitBreaker()

        proxies: Dict[str, str] = {}
        if settings.HTTP_PROXY:
            proxies["http://"] = settings.HTTP_PROXY
        if settings.HTTPS_PROXY:
            proxies["https://"] = settings.HTTPS_PROXY

        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            proxies=proxies or None,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )

    async def __aenter__(self) -> "OllamaTranslator":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        """Ferme le client HTTP."""
        await self.client.aclose()

    async def check_health(self) -> bool:
        """Vérifie que Ollama est disponible."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as exc:  # pragma: no cover - logging path
            logger.error("Ollama health check failed: %s", exc)
            return False

    async def list_models(self) -> List[str]:
        """Récupère la liste des modèles Ollama disponibles."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code != 200:
                logger.error("Failed to list Ollama models: status %s", response.status_code)
                return []

            data = response.json()
            models = data.get("models", [])

            unique_models: List[str] = []
            seen = set()
            for model in models:
                name = (model.get("name") or "").strip()
                if name and name not in seen:
                    seen.add(name)
                    unique_models.append(name)

            return unique_models
        except Exception as exc:  # pragma: no cover - logging path
            logger.error("Error while listing Ollama models: %s", exc)
            return []

    async def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Traduit un texte via Ollama."""
        if not self.circuit_breaker.can_attempt():
            logger.warning("Circuit breaker OPEN, skipping translation")
            return None

        system_prompt = self.SYSTEM_PROMPTS.get((source_lang, target_lang))
        if not system_prompt:
            logger.error("No system prompt for %s -> %s", source_lang, target_lang)
            return None

        payload = {
            "model": model or self.model,
            "prompt": text,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }

        return await self._generate(payload)

    async def correct_text(self, text: str, model: Optional[str] = None) -> Optional[str]:
        """Corrige un texte et fournit des explications au format JSON."""
        if not self.circuit_breaker.can_attempt():
            logger.warning("Circuit breaker OPEN, skipping correction")
            return None

        prompt = (
            "Tu es un correcteur professionnel. Corrige le texte suivant en respectant la langue d'origine et le ton employé. "
            "Retourne exclusivement un objet JSON respectant exactement cette structure :\n"
            "{\n"
            '  "corrected_text": "...",\n'
            '  "explanations": ["..."]\n'
            "}\n"
            "La clé 'corrected_text' doit contenir le texte intégralement corrigé. "
            "La clé 'explanations' doit être une liste décrivant brièvement chaque correction importante. "
            "Indique qu'aucune correction n'a été nécessaire si le texte est déjà correct.\n\n"
            f"Texte à corriger :\n{text}"
        )

        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "system": "Tu es un correcteur orthographique et grammatical interne à DCI. Retourne uniquement du JSON valide.",
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
            },
        }

        return await self._generate(payload)

    async def reformulate_text(self, text: str, model: Optional[str] = None) -> Optional[str]:
        """Reformule un texte en conservant le sens original."""
        if not self.circuit_breaker.can_attempt():
            logger.warning("Circuit breaker OPEN, skipping reformulation")
            return None

        prompt = (
            "Tu es chargé de reformuler le texte suivant pour l'améliorer (fluidité, clarté, ton professionnel) tout en conservant le sens. "
            "Retourne exclusivement un objet JSON avec la structure :\n"
            "{\n"
            '  "reformulated_text": "...",\n'
            '  "highlights": ["..."]\n'
            "}\n"
            "La liste 'highlights' doit contenir quelques explications sur les changements importants.\n\n"
            f"Texte à reformuler :\n{text}"
        )

        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "system": "Tu es un assistant de rédaction interne à DCI. Fournis uniquement du JSON valide.",
            "stream": False,
            "options": {
                "temperature": 0.4,
                "top_p": 0.9,
            },
        }

        return await self._generate(payload)

    async def summarize_meeting(self, text: str, model: Optional[str] = None) -> Optional[str]:
        """Produit un compte rendu structuré à partir de notes de réunion."""
        if not self.circuit_breaker.can_attempt():
            logger.warning("Circuit breaker OPEN, skipping meeting summary")
            return None

        prompt = (
            "À partir des notes de réunion suivantes, crée un compte rendu clair. "
            "Retourne uniquement un JSON respectant la structure :\n"
            "{\n"
            '  "summary": "...",\n'
            '  "decisions": ["..."],\n'
            '  "action_items": ["..."]\n'
            "}\n"
            "Le résumé doit être concis (moins de 150 mots). Les décisions et les actions doivent être formulées en phrases courtes.\n\n"
            f"Notes de réunion :\n{text}"
        )

        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "system": "Tu es l'assistant de compte rendu interne à DCI. Réponds uniquement avec du JSON valide.",
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }

        return await self._generate(payload)

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        model: Optional[str] = None,
        batch_size: Optional[int] = None,
    ) -> List[Optional[str]]:
        """Traduit un lot de textes."""
        batch_size = batch_size or settings.BATCH_SIZE
        results: List[Optional[str]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            logger.info("Translating batch %s (%s texts)", i // batch_size + 1, len(batch))
            for text in batch:
                translated = await self.translate_text(text, source_lang, target_lang, model)
                results.append(translated)

        return results

    async def _generate(self, payload: Dict[str, object]) -> Optional[str]:
        """Effectue l'appel HTTP avec retries et backoff exponentiel."""
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    generated = (data.get("response") or "").strip()
                    if generated:
                        self.circuit_breaker.call_succeeded()
                        return generated
                    logger.warning("Empty response from Ollama")
                else:
                    logger.error("Ollama returned status %s", response.status_code)
            except httpx.TimeoutException:
                logger.warning("Timeout on attempt %s/%s", attempt + 1, self.max_retries)
            except Exception as exc:  # pragma: no cover - logging path
                logger.error("Error on attempt %s/%s: %s", attempt + 1, self.max_retries, exc)

            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                logger.info("Waiting %ss before retry", wait_time)
                await asyncio.sleep(wait_time)

        self.circuit_breaker.call_failed()
        return None
