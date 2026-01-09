"""Tests pour le module de traduction SCENARI XML."""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.scenari import ScenariTranslator, create_zip_from_results, TranslationResult


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


@pytest.fixture
def sample_scenari_xml():
    """Exemple de fichier XML SCENARI."""
    return b'''<?xml version="1.0" encoding="UTF-8"?>
<sc:item xmlns:sc="http://www.utc.fr/ics/scenari/v3/core" xml:lang="fr">
    <sc:content>
        <sc:para>Premier paragraphe en français.</sc:para>
        <sc:para>Deuxième paragraphe à traduire.</sc:para>
        <sc:para></sc:para>
    </sc:content>
</sc:item>'''


@pytest.fixture
def mock_translator():
    """Mock du traducteur Ollama."""
    translator = AsyncMock()
    translator.translate_text.return_value = "Translated text"
    return translator


class TestScenariTranslator:
    """Tests pour la classe ScenariTranslator."""

    def test_count_translatable_elements(self, sample_scenari_xml, mock_translator):
        """Compte correctement les éléments traduisibles."""
        scenari = ScenariTranslator(mock_translator)
        count = scenari.count_translatable_elements(sample_scenari_xml)
        # 2 paragraphes avec du texte (le 3ème est vide)
        assert count == 2

    def test_count_translatable_elements_invalid_xml(self, mock_translator):
        """Retourne 0 pour un XML invalide."""
        scenari = ScenariTranslator(mock_translator)
        count = scenari.count_translatable_elements(b"<invalid>")
        assert count == 0

    def test_count_translatable_elements_no_para(self, mock_translator):
        """Retourne 0 si aucun élément sc:para."""
        xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns:sc="http://www.utc.fr/ics/scenari/v3/core">
    <other>Texte</other>
</root>'''
        scenari = ScenariTranslator(mock_translator)
        count = scenari.count_translatable_elements(xml)
        assert count == 0

    @pytest.mark.asyncio
    async def test_translate_file(self, sample_scenari_xml, mock_translator):
        """Traduit correctement un fichier XML."""
        scenari = ScenariTranslator(mock_translator)
        
        results = []
        async for progress, result in scenari.translate_file(
            xml_content=sample_scenari_xml,
            filename="test.xml",
            source_lang="fr",
            target_lang="en"
        ):
            results.append((progress, result))
        
        # Vérifie les progressions
        assert len(results) == 3  # 2 progressions + 1 final
        
        # Dernière entrée contient le résultat
        final_progress, final_result = results[-1]
        assert final_progress.status == "done"
        assert final_result is not None
        assert final_result.translated_filename == "test_en.xml"
        assert final_result.elements_translated == 2
        
        # Le traducteur a été appelé 2 fois
        assert mock_translator.translate_text.call_count == 2

    @pytest.mark.asyncio
    async def test_translate_file_invalid_xml(self, mock_translator):
        """Gère correctement un XML invalide."""
        scenari = ScenariTranslator(mock_translator)
        
        results = []
        async for progress, result in scenari.translate_file(
            xml_content=b"<invalid>",
            filename="invalid.xml",
            source_lang="fr",
            target_lang="en"
        ):
            results.append((progress, result))
        
        assert len(results) == 1
        progress, result = results[0]
        assert progress.status == "error"
        assert "XML" in progress.error_message
        assert result is None


class TestCreateZipFromResults:
    """Tests pour la création de ZIP."""

    def test_create_zip_single_file(self):
        """Crée un ZIP avec un seul fichier."""
        results = [
            TranslationResult(
                original_filename="test.xml",
                translated_filename="test_en.xml",
                translated_content=b"<content>Translated</content>",
                elements_translated=1,
                total_words=10
            )
        ]
        
        zip_content = create_zip_from_results(results)
        assert isinstance(zip_content, bytes)
        assert len(zip_content) > 0

    def test_create_zip_multiple_files(self):
        """Crée un ZIP avec plusieurs fichiers."""
        results = [
            TranslationResult(
                original_filename="file1.xml",
                translated_filename="file1_en.xml",
                translated_content=b"<content>File 1</content>",
                elements_translated=1,
                total_words=5
            ),
            TranslationResult(
                original_filename="file2.xml",
                translated_filename="file2_en.xml",
                translated_content=b"<content>File 2</content>",
                elements_translated=2,
                total_words=10
            )
        ]
        
        zip_content = create_zip_from_results(results)
        assert isinstance(zip_content, bytes)
        
        # Vérifie que le ZIP contient les deux fichiers
        import zipfile
        with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zf:
            names = zf.namelist()
            assert "file1_en.xml" in names
            assert "file2_en.xml" in names


class TestScenariEndpoints:
    """Tests pour les endpoints SCENARI."""

    def test_scenari_preview_endpoint(self, client, sample_scenari_xml):
        """Le preview retourne le compte d'éléments."""
        files = [
            ("files", ("test.xml", io.BytesIO(sample_scenari_xml), "application/xml"))
        ]
        
        response = client.post("/scenari/preview", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_elements"] == 2
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "test.xml"
        assert data["files"][0]["elements"] == 2

    def test_scenari_preview_no_xml_extension(self, client):
        """Le preview ignore les fichiers non-XML."""
        files = [
            ("files", ("test.txt", io.BytesIO(b"Hello"), "text/plain"))
        ]
        
        response = client.post("/scenari/preview", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_elements"] == 0
        assert len(data["files"]) == 0

    def test_scenari_translate_invalid_language(self, client, sample_scenari_xml):
        """La traduction échoue avec une langue invalide."""
        files = [
            ("files", ("test.xml", io.BytesIO(sample_scenari_xml), "application/xml"))
        ]
        
        response = client.post(
            "/scenari/translate",
            files=files,
            data={
                "source_lang": "fr",
                "target_lang": "de"  # Non supporté
            }
        )
        
        assert response.status_code == 400

    def test_scenari_translate_same_language(self, client, sample_scenari_xml):
        """La traduction échoue si source == cible."""
        files = [
            ("files", ("test.xml", io.BytesIO(sample_scenari_xml), "application/xml"))
        ]
        
        response = client.post(
            "/scenari/translate",
            files=files,
            data={
                "source_lang": "fr",
                "target_lang": "fr"
            }
        )
        
        assert response.status_code == 400
