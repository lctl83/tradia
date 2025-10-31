"""Tests unitaires pour le traducteur Ollama."""
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import pytest_asyncio

from app.translator import CircuitBreaker, OllamaTranslator


@pytest_asyncio.fixture
async def translator():
    """Fixture asynchrone pour le traducteur."""
    instance = OllamaTranslator()
    yield instance
    await instance.close()


def test_circuit_breaker_initial_state():
    cb = CircuitBreaker()
    assert cb.state == "closed"
    assert cb.can_attempt() is True


def test_circuit_breaker_opens_after_failures():
    cb = CircuitBreaker(failure_threshold=2)
    cb.call_failed()
    cb.call_failed()
    assert cb.state == "open"
    assert cb.can_attempt() is False


def test_circuit_breaker_resets_on_success():
    cb = CircuitBreaker()
    cb.call_failed()
    cb.call_succeeded()
    assert cb.failures == 0
    assert cb.state == "closed"


@pytest.mark.asyncio
async def test_translate_text_success(translator):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Translated text"}

    translator.client.post = AsyncMock(return_value=mock_response)

    result = await translator.translate_text("Texte", "fr", "en")
    assert result == "Translated text"


@pytest.mark.asyncio
async def test_translate_text_empty_response(translator):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": ""}

    translator.client.post = AsyncMock(return_value=mock_response)

    result = await translator.translate_text("Texte", "fr", "en")
    assert result is None


@pytest.mark.asyncio
async def test_translate_text_http_error(translator):
    mock_response = Mock()
    mock_response.status_code = 500

    translator.client.post = AsyncMock(return_value=mock_response)

    result = await translator.translate_text("Texte", "fr", "en")
    assert result is None


@pytest.mark.asyncio
async def test_translate_text_timeout(translator):
    translator.client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

    result = await translator.translate_text("Texte", "fr", "en")
    assert result is None


@pytest.mark.asyncio
async def test_translate_text_retries(translator):
    translator.max_retries = 2

    mock_fail = Mock()
    mock_fail.status_code = 500

    mock_success = Mock()
    mock_success.status_code = 200
    mock_success.json.return_value = {"response": "Success"}

    translator.client.post = AsyncMock(side_effect=[mock_fail, mock_success])

    with patch("asyncio.sleep", new=AsyncMock()):
        result = await translator.translate_text("Texte", "fr", "en")

    assert result == "Success"


@pytest.mark.asyncio
async def test_translate_text_circuit_breaker_open(translator):
    translator.circuit_breaker.state = "open"
    result = await translator.translate_text("Texte", "fr", "en")
    assert result is None


@pytest.mark.asyncio
async def test_translate_text_unsupported_language_pair(translator):
    result = await translator.translate_text("Texte", "fr", "de")
    assert result is None


@pytest.mark.asyncio
async def test_translate_batch(translator):
    responses = [
        Mock(status_code=200, json=Mock(return_value={"response": "A"})),
        Mock(status_code=200, json=Mock(return_value={"response": "B"})),
    ]
    translator.client.post = AsyncMock(side_effect=responses)

    results = await translator.translate_batch(["Texte 1", "Texte 2"], "fr", "en", batch_size=1)
    assert results == ["A", "B"]


@pytest.mark.asyncio
async def test_list_models(translator):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": "mistral-small3.2:latest"},
            {"name": "llama3.1"},
            {"name": "mistral-small3.2:latest"},
        ]
    }

    translator.client.get = AsyncMock(return_value=mock_response)

    models = await translator.list_models()
    assert models == ["mistral-small3.2:latest", "llama3.1"]


@pytest.mark.asyncio
async def test_check_health_success(translator):
    mock_response = Mock(status_code=200)
    translator.client.get = AsyncMock(return_value=mock_response)

    result = await translator.check_health()
    assert result is True


@pytest.mark.asyncio
async def test_check_health_failure(translator):
    translator.client.get = AsyncMock(side_effect=httpx.ConnectError("error"))
    result = await translator.check_health()
    assert result is False
