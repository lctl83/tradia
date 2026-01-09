"""Module de traduction de fichiers XML SCENARI."""
from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, List, Optional, Tuple

from lxml import etree

from app.translator import OllamaTranslator

logger = logging.getLogger(__name__)

# Namespaces SCENARI
NAMESPACES = {
    'sc': 'http://www.utc.fr/ics/scenari/v3/core'
}

# Balise contenant le texte à traduire
TRANSLATABLE_TAG = '{http://www.utc.fr/ics/scenari/v3/core}para'


@dataclass
class TranslationProgress:
    """État de progression de la traduction."""
    filename: str
    current_element: int
    total_elements: int
    current_text: str
    status: str  # "translating", "done", "error"
    error_message: Optional[str] = None


@dataclass
class TranslationResult:
    """Résultat de la traduction d'un fichier."""
    original_filename: str
    translated_filename: str
    translated_content: bytes
    elements_translated: int
    total_words: int


class ScenariTranslator:
    """Traducteur de fichiers XML SCENARI."""

    def __init__(self, ollama_translator: OllamaTranslator):
        self.translator = ollama_translator
        # Enregistrer les namespaces pour la sérialisation
        for prefix, uri in NAMESPACES.items():
            etree.register_namespace(prefix, uri)

    def count_translatable_elements(self, xml_content: bytes) -> int:
        """Compte le nombre d'éléments traduisibles dans un fichier XML."""
        try:
            tree = etree.parse(io.BytesIO(xml_content))
            root = tree.getroot()
            elements = root.findall(f'.//{TRANSLATABLE_TAG}', NAMESPACES)
            # Filtrer les éléments avec du texte
            count = sum(1 for el in elements if self._get_element_text(el).strip())
            return count
        except etree.XMLSyntaxError as e:
            logger.error("XML parsing error: %s", e)
            return 0

    def _get_element_text(self, element: etree._Element) -> str:
        """Récupère le texte complet d'un élément (y compris les sous-éléments)."""
        return "".join(element.itertext())

    async def translate_file(
        self,
        xml_content: bytes,
        filename: str,
        source_lang: str,
        target_lang: str,
        model: Optional[str] = None,
    ) -> AsyncGenerator[Tuple[TranslationProgress, Optional[TranslationResult]], None]:
        """
        Traduit un fichier XML SCENARI avec progression.
        
        Yields:
            Tuple de (TranslationProgress, TranslationResult optionnel à la fin)
        """
        try:
            tree = etree.parse(io.BytesIO(xml_content))
            root = tree.getroot()
        except etree.XMLSyntaxError as e:
            yield TranslationProgress(
                filename=filename,
                current_element=0,
                total_elements=0,
                current_text="",
                status="error",
                error_message=f"Erreur de parsing XML: {e}"
            ), None
            return

        elements = root.findall(f'.//{TRANSLATABLE_TAG}', NAMESPACES)
        translatable = [(el, self._get_element_text(el).strip()) 
                        for el in elements if self._get_element_text(el).strip()]
        
        total_elements = len(translatable)
        total_words = 0
        translated_count = 0

        for idx, (element, original_text) in enumerate(translatable, 1):
            word_count = len(original_text.split())
            total_words += word_count

            # Émettre la progression
            yield TranslationProgress(
                filename=filename,
                current_element=idx,
                total_elements=total_elements,
                current_text=original_text[:50] + "..." if len(original_text) > 50 else original_text,
                status="translating"
            ), None

            # Traduire le texte avec la méthode stricte pour XML
            translated_text = await self.translator.translate_xml_text(
                text=original_text,
                source_lang=source_lang,
                target_lang=target_lang,
                model=model
            )

            if translated_text:
                # Supprimer les enfants et remplacer le texte
                for child in list(element):
                    element.remove(child)
                element.text = translated_text
                translated_count += 1
            else:
                logger.warning("Translation failed for element %d in %s", idx, filename)

        # Mettre à jour l'attribut de langue du document
        lang_attr = '{http://www.w3.org/XML/1998/namespace}lang'
        lang_map = {'en': 'en', 'fr': 'fr', 'ar': 'ar'}
        if target_lang in lang_map:
            root.set(lang_attr, lang_map[target_lang])

        # Sérialiser le résultat
        translated_content = etree.tostring(
            tree,
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True
        )

        # Générer le nom du fichier traduit
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            translated_filename = f"{name_parts[0]}_{target_lang}.{name_parts[1]}"
        else:
            translated_filename = f"{filename}_{target_lang}"

        # Émettre le résultat final
        yield TranslationProgress(
            filename=filename,
            current_element=total_elements,
            total_elements=total_elements,
            current_text="",
            status="done"
        ), TranslationResult(
            original_filename=filename,
            translated_filename=translated_filename,
            translated_content=translated_content,
            elements_translated=translated_count,
            total_words=total_words
        )


def create_zip_from_results(results: List[TranslationResult]) -> bytes:
    """Crée un ZIP contenant tous les fichiers traduits."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for result in results:
            zf.writestr(result.translated_filename, result.translated_content)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
