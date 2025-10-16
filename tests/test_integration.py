"""Tests d'intégration pour l'application complète."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


@pytest.fixture
def sample_xml_file():
    """Fichier XML de test."""
    content = b"""<?xml version="1.0" encoding="UTF-8"?>
<sc:item xmlns:sc="http://www.utc.fr/ics/scenari/v3/core" xml:lang="fr">
    <sc:title>Test Document</sc:title>
    <sc:para>Ceci est un test.</sc:para>
</sc:item>
"""
    return ("test.xml", content, "application/xml")


def test_index_page(client):
    """Test de la page d'accueil."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"SCENARI Translator" in response.content


def test_health_check(client):
    """Test du endpoint healthcheck."""
    with patch('app.main.OllamaTranslator') as mock_translator_class:
        mock_translator = Mock()
        mock_translator.check_health.return_value = True
        mock_translator_class.return_value = mock_translator
        
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "ollama_available" in data


def test_metrics_endpoint(client):
    """Test du endpoint métriques."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_translations" in data
    assert "total_segments_translated" in data


def test_translate_endpoint_success(client, sample_xml_file):
    """Test de traduction réussie."""
    with patch('app.main.OllamaTranslator') as mock_translator_class:
        mock_translator = Mock()
        mock_translator.translate_text.return_value = "This is a test."
        mock_translator_class.return_value = mock_translator
        
        response = client.post(
            "/translate",
            data={
                "source_lang": "fr",
                "target_lang": "en",
                "model": "llama3.2:latest"
            },
            files={"file": sample_xml_file}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        assert "X-Translation-Report" in response.headers


def test_translate_invalid_language(client, sample_xml_file):
    """Test avec langue invalide."""
    response = client.post(
        "/translate",
        data={
            "source_lang": "fr",
            "target_lang": "de",  # Non supporté
            "model": "llama3.2:latest"
        },
        files={"file": sample_xml_file}
    )
    
    assert response.status_code == 400


def test_translate_same_languages(client, sample_xml_file):
    """Test avec langues identiques."""
    response = client.post(
        "/translate",
        data={
            "source_lang": "fr",
            "target_lang": "fr",  # Identique
            "model": "llama3.2:latest"
        },
        files={"file": sample_xml_file}
    )
    
    assert response.status_code == 400


def test_translate_invalid_file_type(client):
    """Test avec type de fichier invalide."""
    response = client.post(
        "/translate",
        data={
            "source_lang": "fr",
            "target_lang": "en",
            "model": "llama3.2:latest"
        },
        files={"file": ("test.txt", b"Not XML", "text/plain")}
    )
    
    assert response.status_code == 400


def test_translate_invalid_xml(client):
    """Test avec XML invalide."""
    response = client.post(
        "/translate",
        data={
            "source_lang": "fr",
            "target_lang": "en",
            "model": "llama3.2:latest"
        },
        files={"file": ("test.xml", b"<invalid>Not closed", "application/xml")}
    )
    
    assert response.status_code == 400


def test_translate_no_translatable_segments(client):
    """Test avec XML sans segments traduisibles."""
    xml_no_text = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <empty></empty>
</root>
"""
    response = client.post(
        "/translate",
        data={
            "source_lang": "fr",
            "target_lang": "en",
            "model": "llama3.2:latest"
        },
        files={"file": ("test.xml", xml_no_text, "application/xml")}
    )
    
    assert response.status_code == 400
    assert b"No translatable segments" in response.content


def test_translate_with_translation_failures(client, sample_xml_file):
    """Test avec échecs de traduction."""
    with patch('app.main.OllamaTranslator') as mock_translator_class:
        mock_translator = Mock()
        # Premier appel réussit, second échoue
        mock_translator.translate_text.side_effect = ["Translated", None]
        mock_translator_class.return_value = mock_translator
        
        response = client.post(
            "/translate",
            data={
                "source_lang": "fr",
                "target_lang": "en",
                "model": "llama3.2:latest"
            },
            files={"file": sample_xml_file}
        )
        
        assert response.status_code == 200
        report_header = response.headers.get("X-Translation-Report")
        assert report_header is not None


def test_output_filename_format(client, sample_xml_file):
    """Test du format du nom de fichier de sortie."""
    with patch('app.main.OllamaTranslator') as mock_translator_class:
        mock_translator = Mock()
        mock_translator.translate_text.return_value = "Translated"
        mock_translator_class.return_value = mock_translator
        
        response = client.post(
            "/translate",
            data={
                "source_lang": "fr",
                "target_lang": "en",
                "model": "llama3.2:latest"
            },
            files={"file": sample_xml_file}
        )
        
        content_disposition = response.headers.get("Content-Disposition")
        assert "test.fr-en." in content_disposition
        assert ".xml" in content_disposition


def test_translation_preserves_xml_structure(client, sample_xml_file):
    """Test que la traduction préserve la structure XML."""
    with patch('app.main.OllamaTranslator') as mock_translator_class:
        mock_translator = Mock()
        mock_translator.translate_text.return_value = "Translated text"
        mock_translator_class.return_value = mock_translator
        
        response = client.post(
            "/translate",
            data={
                "source_lang": "fr",
                "target_lang": "en",
                "model": "llama3.2:latest"
            },
            files={"file": sample_xml_file}
        )
        
        output_xml = response.content
        
        # Vérifications de structure
        assert b"<?xml" in output_xml
        assert b"sc:item" in output_xml
        assert b"sc:title" in output_xml
        assert b'xml:lang="en"' in output_xml


def test_translation_updates_xml_lang(client):
    """Test que xml:lang est mis à jour."""
    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<sc:item xmlns:sc="http://www.utc.fr/ics/scenari/v3/core" xml:lang="fr">
    <sc:para>Texte</sc:para>
</sc:item>
"""
    
    with patch('app.main.OllamaTranslator') as mock_translator_class:
        mock_translator = Mock()
        mock_translator.translate_text.return_value = "Text"
        mock_translator_class.return_value = mock_translator
        
        response = client.post(
            "/translate",
            data={
                "source_lang": "fr",
                "target_lang": "ar",
                "model": "llama3.2:latest"
            },
            files={"file": ("test.xml", xml_content, "application/xml")}
        )
        
        output_xml = response.content
        assert b'xml:lang="ar"' in output_xml


def test_file_size_limit(client):
    """Test de la limite de taille de fichier."""
    # Créer un fichier trop gros (simulé)
    large_content = b"<root>" + b"x" * (51 * 1024 * 1024) + b"</root>"
    
    response = client.post(
        "/translate",
        data={
            "source_lang": "fr",
            "target_lang": "en",
            "model": "llama3.2:latest"
        },
        files={"file": ("large.xml", large_content, "application/xml")}
    )
    
    assert response.status_code == 413
