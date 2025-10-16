"""Tests unitaires pour le processeur XML."""
import pytest
from lxml import etree
from app.xml_processor import XMLProcessor


@pytest.fixture
def sample_xml():
    """Exemple de XML SCENARI."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<sc:item xmlns:sc="http://www.utc.fr/ics/scenari/v3/core" xml:lang="fr">
    <sc:title>Titre du document</sc:title>
    <sc:para>Ceci est un paragraphe de test.</sc:para>
    <sc:para>Un autre paragraphe.</sc:para>
    <sc:code>print("Ne pas traduire")</sc:code>
</sc:item>
"""


@pytest.fixture
def complex_xml():
    """XML avec structure complexe."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<sc:document xmlns:sc="http://www.utc.fr/ics/scenari/v3/core" xml:lang="fr">
    <sc:section>
        <sc:title>Introduction</sc:title>
        <sc:para>Premier paragraphe.</sc:para>
        <sc:item>
            <sc:label>Item 1</sc:label>
            <sc:description>Description de l'item.</sc:description>
        </sc:item>
    </sc:section>
</sc:document>
"""


def test_parse_valid_xml(sample_xml):
    """Test du parsing d'un XML valide."""
    processor = XMLProcessor()
    assert processor.parse(sample_xml) is True
    assert processor.root is not None
    assert processor.tree is not None


def test_parse_invalid_xml():
    """Test du parsing d'un XML invalide."""
    processor = XMLProcessor()
    invalid_xml = b"<invalid>Not closed"
    assert processor.parse(invalid_xml) is False


def test_extract_segments(sample_xml):
    """Test de l'extraction des segments traduisibles."""
    processor = XMLProcessor()
    processor.parse(sample_xml)
    
    segments = processor.extract_translatable_segments()
    
    # Devrait trouver title et 2 para (pas le code)
    assert len(segments) >= 3
    
    texts = [seg[2] for seg in segments]
    assert "Titre du document" in texts
    assert "Ceci est un paragraphe de test." in texts
    assert "Un autre paragraphe." in texts
    assert "print" not in " ".join(texts)  # Code ignoré


def test_extract_segments_complex(complex_xml):
    """Test de l'extraction sur XML complexe."""
    processor = XMLProcessor()
    processor.parse(complex_xml)
    
    segments = processor.extract_translatable_segments()
    
    assert len(segments) >= 4
    texts = [seg[2] for seg in segments]
    assert "Introduction" in texts
    assert "Premier paragraphe." in texts


def test_update_segment(sample_xml):
    """Test de la mise à jour d'un segment."""
    processor = XMLProcessor()
    processor.parse(sample_xml)
    
    segments = processor.extract_translatable_segments()
    first_element, xpath, original_text = segments[0]
    
    new_text = "Translated title"
    success = processor.update_segment(first_element, new_text)
    
    assert success is True
    assert first_element.text == new_text


def test_update_language(sample_xml):
    """Test de la mise à jour de xml:lang."""
    processor = XMLProcessor()
    processor.parse(sample_xml)
    
    processor.update_language("en")
    
    lang = processor.root.get("{http://www.w3.org/XML/1998/namespace}lang")
    assert lang == "en"


def test_to_bytes_preserves_structure(sample_xml):
    """Test que to_bytes préserve la structure."""
    processor = XMLProcessor()
    processor.parse(sample_xml)
    
    output = processor.to_bytes()
    
    # Vérifier que c'est du XML valide
    assert b"<?xml" in output
    assert b"sc:item" in output
    assert b"sc:title" in output


def test_namespace_preservation(sample_xml):
    """Test de la préservation des namespaces."""
    processor = XMLProcessor()
    processor.parse(sample_xml)
    
    output = processor.to_bytes()
    
    # Le namespace doit être préservé
    assert b'xmlns:sc="http://www.utc.fr/ics/scenari/v3/core"' in output


def test_empty_elements_ignored(sample_xml):
    """Test que les éléments vides sont ignorés."""
    xml_with_empty = b"""<?xml version="1.0" encoding="UTF-8"?>
<sc:item xmlns:sc="http://www.utc.fr/ics/scenari/v3/core">
    <sc:para></sc:para>
    <sc:para>   </sc:para>
    <sc:para>Texte valide</sc:para>
</sc:item>
"""
    processor = XMLProcessor()
    processor.parse(xml_with_empty)
    
    segments = processor.extract_translatable_segments()
    
    # Seul le paragraphe avec du texte doit être extrait
    assert len(segments) == 1
    assert segments[0][2] == "Texte valide"


def test_get_element_xpath():
    """Test de la génération de XPath."""
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <item>
        <para>First</para>
        <para>Second</para>
    </item>
</root>
"""
    processor = XMLProcessor()
    processor.parse(xml)
    
    paras = processor.root.findall(".//para")
    xpath1 = processor._get_element_xpath(paras[0])
    xpath2 = processor._get_element_xpath(paras[1])
    
    # Les XPaths doivent être différents
    assert xpath1 != xpath2
    assert "[1]" in xpath1
    assert "[2]" in xpath2
