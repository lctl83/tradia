"""Tests d'intégration pour DCIA."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


def _mock_translator(**methods):
    """Crée un mock d'OllamaTranslator asynchrone."""
    translator = AsyncMock()
    translator.__aenter__.return_value = translator
    translator.__aexit__.return_value = False
    for name, value in methods.items():
        getattr(translator, name).return_value = value
    return translator


def test_index_page(client):
    """La page d'accueil doit mentionner DCIA."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"DCIA" in response.content


def test_health_check(client):
    """Le healthcheck doit retourner l'état du service Ollama."""
    translator = _mock_translator(check_health=True)
    with patch("app.main.OllamaTranslator", return_value=translator):
        response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["ollama_available"] is True


def test_metrics_endpoint(client):
    """Les métriques doivent être initialisées à zéro."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "text_translations": 0,
        "corrections": 0,
        "reformulations": 0,
        "meeting_summaries": 0,
    }


def test_translate_text_success(client):
    """La traduction de texte retourne le texte traduit."""
    translator = _mock_translator(translate_text="Hello")
    with patch("app.main.OllamaTranslator", return_value=translator):
        response = client.post(
            "/translate-text",
            data={
                "text": "Bonjour",
                "source_lang": "fr",
                "target_lang": "en",
            },
        )

    assert response.status_code == 200
    assert response.json()["translated_text"] == "Hello"


def test_translate_text_invalid_language(client):
    """La traduction échoue si la langue cible est invalide."""
    response = client.post(
        "/translate-text",
        data={
            "text": "Bonjour",
            "source_lang": "fr",
            "target_lang": "de",
        },
    )

    assert response.status_code == 400


def test_translate_text_same_language(client):
    """La traduction échoue si la source et la cible sont identiques."""
    response = client.post(
        "/translate-text",
        data={
            "text": "Bonjour",
            "source_lang": "fr",
            "target_lang": "fr",
        },
    )

    assert response.status_code == 400


def test_correct_text_success(client):
    """La correction retourne le texte corrigé et des explications."""
    translator = _mock_translator(
        correct_text='{"corrected_text": "Texte corrigé", "explanations": ["Correction 1"]}'
    )
    with patch("app.main.OllamaTranslator", return_value=translator):
        response = client.post(
            "/correct-text",
            data={
                "text": "Texte a corriger",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["corrected_text"] == "Texte corrigé"
    assert data["explanations"] == ["Correction 1"]


def test_correct_text_invalid_payload(client):
    """Une réponse non JSON renvoie une erreur 502."""
    translator = _mock_translator(correct_text="Pas du JSON")
    with patch("app.main.OllamaTranslator", return_value=translator):
        response = client.post(
            "/correct-text",
            data={"text": "Texte"},
        )

    assert response.status_code == 502


def test_reformulation_success(client):
    """La reformulation retourne un texte et des explications."""
    translator = _mock_translator(
        reformulate_text='{"reformulated_text": "Texte reformulé", "highlights": ["Ajout de clarté"]}'
    )
    with patch("app.main.OllamaTranslator", return_value=translator):
        response = client.post(
            "/reformulate-text",
            data={"text": "Texte"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reformulated_text"] == "Texte reformulé"
    assert data["highlights"] == ["Ajout de clarté"]


def test_meeting_summary_success(client):
    """Le compte rendu retourne résumé, décisions et actions."""
    translator = _mock_translator(
        summarize_meeting='{"summary": "Résumé", "decisions": ["Décision"], "action_items": ["Action"]}'
    )
    with patch("app.main.OllamaTranslator", return_value=translator):
        response = client.post(
            "/meeting-summary",
            data={"text": "Notes"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Résumé"
    assert data["decisions"] == ["Décision"]
    assert data["action_items"] == ["Action"]


def test_models_endpoint(client):
    """La liste des modèles place le modèle par défaut en premier."""
    translator = _mock_translator(list_models=["model-b", "mistral-small3.2:latest"])
    with patch("app.main.OllamaTranslator", return_value=translator):
        response = client.get("/models")

    assert response.status_code == 200
    data = response.json()
    assert data["models"][0] == "mistral-small3.2:latest"


def test_models_endpoint_empty_ollama_list(client):
    """L'endpoint des modèles retourne une liste par défaut si Ollama ne retourne rien."""
    translator = _mock_translator(list_models=[])
    with patch("app.main.OllamaTranslator", return_value=translator):
        response = client.get("/models")

    assert response.status_code == 200
    data = response.json()
    assert data["models"] == ["mistral-small3.2:latest"]
