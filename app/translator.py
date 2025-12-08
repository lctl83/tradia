"""Client Ollama asynchrone pour IA DCI."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional

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
            "You are a French to English translator. "
            "Translate the user's French text into English. "
            "Output ONLY the English translation. No explanations, no original text, no extra words."
        ),
        ("fr", "ar"): (
            "أنت مترجم من الفرنسية إلى العربية. "
            "ترجم النص الفرنسي إلى العربية. "
            "أخرج الترجمة العربية فقط. لا تفسيرات، لا نص أصلي، لا كلمات إضافية."
        ),
        ("en", "fr"): (
            "Tu es un traducteur anglais vers français. "
            "Traduis le texte anglais de l'utilisateur en français. "
            "Retourne UNIQUEMENT la traduction française. Pas d'explications, pas de texte original, pas de mots supplémentaires."
        ),
        ("en", "ar"): (
            "أنت مترجم من الإنجليزية إلى العربية. "
            "ترجم النص الإنجليزي إلى العربية. "
            "أخرج الترجمة العربية فقط. لا تفسيرات، لا نص أصلي، لا كلمات إضافية."
        ),
        ("ar", "fr"): (
            "Tu es un traducteur arabe vers français. "
            "Traduis le texte arabe de l'utilisateur en français. "
            "Retourne UNIQUEMENT la traduction française. Pas d'explications, pas de texte original, pas de mots supplémentaires."
        ),
        ("ar", "en"): (
            "You are an Arabic to English translator. "
            "Translate the user's Arabic text into English. "
            "Output ONLY the English translation. No explanations, no original text, no extra words."
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
            "Corrige UNIQUEMENT l'orthographe et la grammaire du texte ci-dessous.\n\n"
            "INTERDICTIONS ABSOLUES (ne JAMAIS modifier ces éléments):\n"
            "- Les dates (2025, 5 décembre, etc.) - même si elles te semblent erronées\n"
            "- Les prix et montants (14,99 €, 9,99 €, etc.)\n"
            "- Les noms propres de personnes, entreprises, produits\n"
            "- Les chiffres et statistiques\n"
            "- Le formatage Markdown (pas de ** ou autres balises)\n\n"
            "Tu ne corriges QUE:\n"
            "- Les fautes d'orthographe (accords, conjugaisons)\n"
            "- Les erreurs de grammaire\n"
            "- La ponctuation\n\n"
            "Tu DOIS retourner UNIQUEMENT ce JSON (rien d'autre, pas de texte avant ou après):\n"
            '{"corrected_text": "LE TEXTE CORRIGÉ ICI", "explanations": ["explication 1", "explication 2"]}\n\n'
            "Exemple pour le texte 'Je suis alé au magazin le 5 décembre 2025':\n"
            '{"corrected_text": "Je suis allé au magasin le 5 décembre 2025", "explanations": ["alé → allé (accent aigu)", "magazin → magasin (orthographe)"]}\n\n'
            "RÈGLES:\n"
            "- Retourne SEULEMENT le JSON, pas de texte explicatif\n"
            "- Préserve les sauts de ligne avec \\n dans la valeur corrected_text\n"
            "- Maximum 5 explanations courtes\n"
            "- GARDE les dates, prix et noms EXACTEMENT comme dans l'original\n\n"
            f"Texte à corriger:\n{text}"
        )

        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "system": "Tu es un correcteur. Réponds UNIQUEMENT avec un objet JSON valide, rien d'autre.",
            "stream": False,
            "options": {
                "temperature": 0.0,
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

    async def summarize_meeting(
        self,
        text: Optional[str] = None,
        image_base64: Optional[str] = None,
        model: Optional[str] = None
    ) -> Optional[str]:
        """Produit un compte rendu structuré à partir de notes de réunion (texte ou image)."""
        if not self.circuit_breaker.can_attempt():
            logger.warning("Circuit breaker OPEN, skipping meeting summary")
            return None

        # Build prompt based on input type
        if image_base64 and text:
            prompt = (
                "Analyse l'image ET le texte fournis pour créer un compte rendu de réunion. "
                "L'image peut contenir des notes manuscrites, un tableau blanc, etc. "
                "Retourne uniquement un JSON respectant la structure :\n"
                "{\n"
                '  "summary": "...",\n'
                '  "decisions": ["..."],\n'
                '  "action_items": ["..."]\n'
                "}\n"
                "Le résumé doit être concis (moins de 150 mots). Les décisions et les actions doivent être formulées en phrases courtes.\n\n"
                f"Texte additionnel :\n{text}"
            )
        elif image_base64:
            prompt = (
                "Analyse cette image qui contient des notes de réunion (notes manuscrites, tableau blanc, capture d'écran, etc.). "
                "Extrait le contenu et crée un compte rendu structuré. "
                "Retourne uniquement un JSON respectant la structure :\n"
                "{\n"
                '  "summary": "...",\n'
                '  "decisions": ["..."],\n'
                '  "action_items": ["..."]\n'
                "}\n"
                "Le résumé doit être concis (moins de 150 mots). Les décisions et les actions doivent être formulées en phrases courtes."
            )
        else:
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

        # Add image for vision models
        if image_base64:
            payload["images"] = [image_base64]

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

    async def _generate_stream(
        self, payload: Dict[str, object]
    ) -> AsyncGenerator[str, None]:
        """Génère les tokens en streaming via Ollama."""
        if not self.circuit_breaker.can_attempt():
            logger.warning("Circuit breaker OPEN, skipping streaming request")
            return

        payload["stream"] = True

        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            ) as response:
                if response.status_code != 200:
                    logger.error("Ollama streaming returned status %s", response.status_code)
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done"):
                            self.circuit_breaker.call_succeeded()
                            break
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON in stream: %s", line[:100])
                        continue

        except httpx.TimeoutException:
            logger.warning("Timeout during streaming")
            self.circuit_breaker.call_failed()
        except Exception as exc:
            logger.error("Error during streaming: %s", exc)
            self.circuit_breaker.call_failed()

    async def translate_text_stream(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Traduit un texte via Ollama en streaming."""
        system_prompt = self.SYSTEM_PROMPTS.get((source_lang, target_lang))
        if not system_prompt:
            logger.error("No system prompt for %s -> %s", source_lang, target_lang)
            return

        payload = {
            "model": model or self.model,
            "prompt": text,
            "system": system_prompt,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }

        async for token in self._generate_stream(payload):
            yield token

    async def correct_text_stream(
        self, text: str, model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Corrige un texte en streaming."""
        prompt = (
            "Corrige UNIQUEMENT l'orthographe et la grammaire du texte ci-dessous.\n\n"
            "INTERDICTIONS ABSOLUES (ne JAMAIS modifier ces éléments):\n"
            "- Les dates (2025, 5 décembre, etc.) - même si elles te semblent erronées\n"
            "- Les prix et montants (14,99 €, 9,99 €, etc.)\n"
            "- Les noms propres de personnes, entreprises, produits\n"
            "- Les chiffres et statistiques\n"
            "- Le formatage Markdown (pas de ** ou autres balises)\n\n"
            "Tu ne corriges QUE:\n"
            "- Les fautes d'orthographe (accords, conjugaisons)\n"
            "- Les erreurs de grammaire\n"
            "- La ponctuation\n\n"
            "Tu DOIS retourner UNIQUEMENT ce JSON (rien d'autre, pas de texte avant ou après):\n"
            '{"corrected_text": "LE TEXTE CORRIGÉ ICI", "explanations": ["explication 1", "explication 2"]}\n\n'
            "Exemple pour le texte 'Je suis alé au magazin le 5 décembre 2025':\n"
            '{"corrected_text": "Je suis allé au magasin le 5 décembre 2025", "explanations": ["alé → allé (accent aigu)", "magazin → magasin (orthographe)"]}\n\n'
            "RÈGLES:\n"
            "- Retourne SEULEMENT le JSON, pas de texte explicatif\n"
            "- Préserve les sauts de ligne avec \\n dans la valeur corrected_text\n"
            "- Maximum 5 explanations courtes\n"
            "- GARDE les dates, prix et noms EXACTEMENT comme dans l'original\n\n"
            f"Texte à corriger:\n{text}"
        )

        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "system": "Tu es un correcteur. Réponds UNIQUEMENT avec un objet JSON valide, rien d'autre.",
            "options": {
                "temperature": 0.0,
                "top_p": 0.9,
            },
        }

        async for token in self._generate_stream(payload):
            yield token

    async def reformulate_text_stream(
        self, text: str, model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Reformule un texte en streaming."""
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
            "options": {
                "temperature": 0.4,
                "top_p": 0.9,
            },
        }

        async for token in self._generate_stream(payload):
            yield token

    async def summarize_meeting_stream(
        self,
        text: Optional[str] = None,
        image_base64: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Produit un compte rendu en streaming."""
        # Build prompt based on input type
        if image_base64 and text:
            prompt = (
                "Analyse l'image ET le texte fournis pour créer un compte rendu de réunion. "
                "L'image peut contenir des notes manuscrites, un tableau blanc, etc. "
                "Retourne uniquement un JSON respectant la structure :\n"
                "{\n"
                '  "summary": "...",\n'
                '  "decisions": ["..."],\n'
                '  "action_items": ["..."]\n'
                "}\n"
                "Le résumé doit être concis (moins de 150 mots). Les décisions et les actions doivent être formulées en phrases courtes.\n\n"
                f"Texte additionnel :\n{text}"
            )
        elif image_base64:
            prompt = (
                "Analyse cette image qui contient des notes de réunion (notes manuscrites, tableau blanc, capture d'écran, etc.). "
                "Extrait le contenu et crée un compte rendu structuré. "
                "Retourne uniquement un JSON respectant la structure :\n"
                "{\n"
                '  "summary": "...",\n'
                '  "decisions": ["..."],\n'
                '  "action_items": ["..."]\n'
                "}\n"
                "Le résumé doit être concis (moins de 150 mots). Les décisions et les actions doivent être formulées en phrases courtes."
            )
        else:
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
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }

        # Add image for vision models
        if image_base64:
            payload["images"] = [image_base64]

        async for token in self._generate_stream(payload):
            yield token
