"""Client Ollama pour traduction avec retries et circuit breaker."""
import logging
import time
import httpx
from typing import List, Optional, Dict
from app.config import settings

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker léger pour éviter les appels répétés en cas d'échec."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
    
    def call_failed(self):
        """Enregistre un échec."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker OPEN after {self.failures} failures")
    
    def call_succeeded(self):
        """Enregistre un succès."""
        self.failures = 0
        self.state = "closed"
    
    def can_attempt(self) -> bool:
        """Vérifie si on peut tenter un appel."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Vérifier si le timeout est écoulé
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                logger.info("Circuit breaker moving to HALF-OPEN")
                return True
            return False
        
        # half-open: autoriser une tentative
        return True


class OllamaTranslator:
    """Client pour traduire du texte via Ollama."""
    
    SYSTEM_PROMPTS = {
        ("fr", "en"): "You are a translator. Translate the following French text to English. Return ONLY the translated text, without any explanation, formatting, or additional content. Preserve punctuation and tone.",
        ("fr", "ar"): "أنت مترجم. ترجم النص الفرنسي التالي إلى العربية. أعد النص المترجم فقط، دون أي تفسير أو تنسيق أو محتوى إضافي. احتفظ بعلامات الترقيم والنبرة.",
        ("en", "fr"): "Tu es un traducteur. Traduis le texte anglais suivant en français. Retourne UNIQUEMENT le texte traduit, sans explication, formatage ou contenu additionnel. Préserve la ponctuation et le ton.",
        ("en", "ar"): "أنت مترجم. ترجم النص الإنجليزي التالي إلى العربية. أعد النص المترجم فقط، دون أي تفسير أو تنسيق أو محتوى إضافي. احتفظ بعلامات الترقيم والنبرة.",
        ("ar", "fr"): "Tu es un traducteur. Traduis le texte arabe suivant en français. Retourne UNIQUEMENT le texte traduit, sans explication, formatage ou contenu additionnel. Préserve la ponctuation et le ton.",
        ("ar", "en"): "You are a translator. Translate the following Arabic text to English. Return ONLY the translated text, without any explanation, formatting, or additional content. Preserve punctuation and tone.",
    }
    
    def __init__(self):
        """Initialise le client Ollama."""
        self.base_url = settings.OLLAMA_BASE_URL.rstrip('/')
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.max_retries = settings.OLLAMA_MAX_RETRIES
        self.circuit_breaker = CircuitBreaker()
        
        # Configuration du client HTTP
        proxies = {}
        if settings.HTTP_PROXY:
            proxies['http://'] = settings.HTTP_PROXY
        if settings.HTTPS_PROXY:
            proxies['https://'] = settings.HTTPS_PROXY
        
        self.client = httpx.Client(
            timeout=self.timeout,
            proxies=proxies if proxies else None,
            follow_redirects=True
        )
    
    def check_health(self) -> bool:
        """
        Vérifie que Ollama est disponible.

        Returns:
            True si Ollama répond
        """
        try:
            response = self.client.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def list_models(self) -> List[str]:
        """Récupère la liste des modèles Ollama disponibles."""
        try:
            response = self.client.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code != 200:
                logger.error(
                    "Failed to list Ollama models: status %s", response.status_code
                )
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
        except Exception as exc:
            logger.error(f"Error while listing Ollama models: {exc}")
            return []
    
    def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        model: Optional[str] = None
    ) -> Optional[str]:
        """
        Traduit un texte via Ollama.
        
        Args:
            text: Texte à traduire
            source_lang: Langue source (fr, en, ar)
            target_lang: Langue cible (fr, en, ar)
            model: Modèle Ollama à utiliser (optionnel)
            
        Returns:
            Texte traduit ou None en cas d'échec
        """
        if not self.circuit_breaker.can_attempt():
            logger.warning("Circuit breaker OPEN, skipping translation")
            return None
        
        model_to_use = model or self.model
        system_prompt = self.SYSTEM_PROMPTS.get((source_lang, target_lang))
        
        if not system_prompt:
            logger.error(f"No system prompt for {source_lang} -> {target_lang}")
            return None
        
        payload = {
            "model": model_to_use,
            "prompt": text,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Basse température pour traduction fidèle
                "top_p": 0.9,
            }
        }
        
        # Retries avec backoff exponentiel
        for attempt in range(self.max_retries):
            try:
                response = self.client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    translated = result.get("response", "").strip()
                    
                    if translated:
                        self.circuit_breaker.call_succeeded()
                        return translated
                    else:
                        logger.warning("Empty response from Ollama")
                        
                else:
                    logger.error(f"Ollama returned status {response.status_code}")
                    
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}")
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}/{self.max_retries}: {e}")
            
            # Backoff exponentiel
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time}s before retry")
                time.sleep(wait_time)
        
        # Tous les essais ont échoué
        self.circuit_breaker.call_failed()
        return None
    
    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        model: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> List[Optional[str]]:
        """
        Traduit un lot de textes.
        
        Args:
            texts: Liste de textes à traduire
            source_lang: Langue source
            target_lang: Langue cible
            model: Modèle Ollama
            batch_size: Taille des lots (utilise settings.BATCH_SIZE par défaut)
            
        Returns:
            Liste de textes traduits (None pour les échecs)
        """
        batch_size = batch_size or settings.BATCH_SIZE
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Translating batch {i//batch_size + 1} ({len(batch)} texts)")
            
            for text in batch:
                translated = self.translate_text(text, source_lang, target_lang, model)
                results.append(translated)
        
        return results
    
    def close(self):
        """Ferme le client HTTP."""
        self.client.close()
