"""Tests unitaires pour le traducteur Ollama."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.translator import OllamaTranslator, CircuitBreaker
import httpx


@pytest.fixture
def translator():
    """Fixture pour le traducteur."""
    return OllamaTranslator()


def test_circuit_breaker_initial_state():
    """Test de l'état initial du circuit breaker."""
    cb = CircuitBreaker()
    assert cb.state == "closed"
    assert cb.can_attempt() is True


def test_circuit_breaker_opens_after_failures():
    """Test que le circuit s'ouvre après plusieurs échecs."""
    cb = CircuitBreaker(failure_threshold=3)
    
    for _ in range(3):
        cb.call_failed()
    
    assert cb.state == "open"
    assert cb.can_attempt() is False


def test_circuit_breaker_resets_on_success():
    """Test que le circuit se réinitialise après un succès."""
    cb = CircuitBreaker()
    cb.call_failed()
    cb.call_failed()
    
    cb.call_succeeded()
    
    assert cb.failures == 0
    assert cb.state == "closed"


def test_translate_text_success(translator):
    """Test de traduction réussie."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "Translated text"
    }
    
    with patch.object(translator.client, 'post', return_value=mock_response):
        result = translator.translate_text(
            "Texte source",
            "fr",
            "en"
        )
    
    assert result == "Translated text"


def test_translate_text_empty_response(translator):
    """Test avec réponse vide d'Ollama."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": ""
    }
    
    with patch.object(translator.client, 'post', return_value=mock_response):
        result = translator.translate_text(
            "Texte source",
            "fr",
            "en"
        )
    
    assert result is None


def test_translate_text_http_error(translator):
    """Test avec erreur HTTP."""
    mock_response = Mock()
    mock_response.status_code = 500
    
    with patch.object(translator.client, 'post', return_value=mock_response):
        result = translator.translate_text(
            "Texte source",
            "fr",
            "en"
        )
    
    assert result is None


def test_translate_text_timeout(translator):
    """Test avec timeout."""
    with patch.object(translator.client, 'post', side_effect=httpx.TimeoutException("Timeout")):
        result = translator.translate_text(
            "Texte source",
            "fr",
            "en"
        )
    
    assert result is None


def test_translate_text_retries(translator):
    """Test des retries avec succès au 2ème essai."""
    translator.max_retries = 3
    
    mock_response_fail = Mock()
    mock_response_fail.status_code = 500
    
    mock_response_success = Mock()
    mock_response_success.status_code = 200
    mock_response_success.json.return_value = {
        "response": "Success on retry"
    }
    
    with patch.object(
        translator.client,
        'post',
        side_effect=[mock_response_fail, mock_response_success]
    ):
        with patch('time.sleep'):  # Skip les délais
            result = translator.translate_text(
                "Texte source",
                "fr",
                "en"
            )
    
    assert result == "Success on retry"


def test_translate_text_circuit_breaker_open(translator):
    """Test que le circuit breaker bloque les appels quand ouvert."""
    translator.circuit_breaker.state = "open"
    
    result = translator.translate_text(
        "Texte source",
        "fr",
        "en"
    )
    
    assert result is None


def test_translate_text_unsupported_language_pair(translator):
    """Test avec paire de langues non supportée."""
    result = translator.translate_text(
        "Text",
        "fr",
        "de"  # Allemand non supporté
    )
    
    assert result is None


def test_check_health_success(translator):
    """Test du healthcheck avec Ollama disponible."""
    mock_response = Mock()
    mock_response.status_code = 200
    
    with patch.object(translator.client, 'get', return_value=mock_response):
        assert translator.check_health() is True


def test_check_health_failure(translator):
    """Test du healthcheck avec Ollama indisponible."""
    with patch.object(translator.client, 'get', side_effect=httpx.ConnectError("Connection failed")):
        assert translator.check_health() is False


def test_translate_batch(translator):
    """Test de traduction par lot."""
    texts = ["Text 1", "Text 2", "Text 3"]
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "Translated"
    }
    
    with patch.object(translator.client, 'post', return_value=mock_response):
        results = translator.translate_batch(
            texts,
            "en",
            "fr",
            batch_size=2
        )
    
    assert len(results) == 3
    assert all(r == "Translated" for r in results)


def test_translate_batch_with_failures(translator):
    """Test de batch avec certains échecs."""
    texts = ["Text 1", "Text 2"]
    
    mock_success = Mock()
    mock_success.status_code = 200
    mock_success.json.return_value = {"response": "Success"}
    
    mock_fail = Mock()
    mock_fail.status_code = 500
    
    with patch.object(
        translator.client,
        'post',
        side_effect=[mock_success, mock_fail]
    ):
        results = translator.translate_batch(
            texts,
            "en",
            "fr"
        )
    
    assert results[0] == "Success"
    assert results[1] is None


def test_system_prompt_exists_for_all_pairs():
    """Test que tous les prompts système existent."""
    supported_langs = ["fr", "en", "ar"]
    
    for src in supported_langs:
        for tgt in supported_langs:
            if src != tgt:
                key = (src, tgt)
                assert key in OllamaTranslator.SYSTEM_PROMPTS, f"Missing prompt for {key}"


def test_close_client(translator):
    """Test de fermeture du client."""
    with patch.object(translator.client, 'close') as mock_close:
        translator.close()
        mock_close.assert_called_once()
