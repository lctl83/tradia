"""Processeur XML pour fichiers SCENARI avec préservation stricte."""
import logging
from typing import List, Tuple, Optional
from lxml import etree
from io import BytesIO

logger = logging.getLogger(__name__)


class XMLProcessor:
    """Gère le parsing et la manipulation de fichiers XML SCENARI."""
    
    # Namespaces SCENARI communs
    SCENARI_NAMESPACES = {
        'sc': 'http://www.utc.fr/ics/scenari/v3/core',
        'sp': 'http://www.utc.fr/ics/scenari/v3/primitive',
    }
    
    # XPaths pour les éléments textuels à traduire
    TEXT_ELEMENT_XPATHS = [
        ".//sc:para",
        ".//sc:title",
        ".//sc:item",
        ".//sc:caption",
        ".//sc:legend",
        ".//sc:label",
        ".//sc:question",
        ".//sc:answer",
        ".//sc:comment",
        ".//sc:description",
        ".//sp:txt",
    ]
    
    # Éléments à ignorer (code, math, références, etc.)
    IGNORE_ELEMENTS = {
        'code', 'math', 'equation', 'ref', 'link', 'url', 
        'img', 'image', 'video', 'audio', 'file'
    }
    
    def __init__(self):
        """Initialise le processeur XML."""
        self.tree: Optional[etree._ElementTree] = None
        self.root: Optional[etree._Element] = None
        self.original_encoding: str = 'utf-8'
        
    def parse(self, xml_content: bytes) -> bool:
        """
        Parse le contenu XML en préservant la structure.
        
        Args:
            xml_content: Contenu XML en bytes
            
        Returns:
            True si succès, False sinon
        """
        try:
            # Parser avec préservation maximale
            parser = etree.XMLParser(
                remove_blank_text=False,
                remove_comments=False,
                remove_pis=False,
                resolve_entities=False,
                strip_cdata=False,
                encoding='utf-8'
            )
            
            self.tree = etree.parse(BytesIO(xml_content), parser)
            self.root = self.tree.getroot()
            
            # Détecter l'encodage original
            if xml_content.startswith(b'<?xml'):
                encoding_start = xml_content.find(b'encoding="')
                if encoding_start != -1:
                    encoding_start += 10
                    encoding_end = xml_content.find(b'"', encoding_start)
                    self.original_encoding = xml_content[encoding_start:encoding_end].decode('ascii')
            
            logger.info("XML parsed successfully. Root: %s", self.root.tag)
            return True
            
        except etree.XMLSyntaxError as e:
            logger.error("XML syntax error: %s", e)
            return False
        except Exception as e:
            logger.error("Error parsing XML: %s", e)
            return False
    
    def extract_translatable_segments(self) -> List[Tuple[etree._Element, str, str]]:
        """
        Extrait les segments traduisibles du document.
        
        Returns:
            Liste de tuples (element, xpath, text)
        """
        segments = []
        
        if self.root is None:
            return segments
        
        # Enregistrer les namespaces
        for prefix, uri in self.SCENARI_NAMESPACES.items():
            etree.register_namespace(prefix, uri)
        
        # Parcourir tous les éléments textuels
        for xpath_expr in self.TEXT_ELEMENT_XPATHS:
            try:
                elements = self.root.xpath(xpath_expr, namespaces=self.SCENARI_NAMESPACES)
                
                for elem in elements:
                    # Ignorer les éléments sans texte ou vides
                    if elem.text is None or not elem.text.strip():
                        continue
                    
                    # Ignorer les éléments dans la liste d'exclusion
                    local_name = etree.QName(elem).localname
                    if local_name in self.IGNORE_ELEMENTS:
                        continue
                    
                    # Ignorer si parent est à exclure
                    parent = elem.getparent()
                    if parent is not None:
                        parent_name = etree.QName(parent).localname
                        if parent_name in self.IGNORE_ELEMENTS:
                            continue
                    
                    # Créer un xpath unique pour cet élément
                    xpath = self._get_element_xpath(elem)
                    text = elem.text.strip()
                    
                    if text:
                        segments.append((elem, xpath, text))
                        
            except etree.XPathEvalError as e:
                logger.warning("XPath error for %s: %s", xpath_expr, e)
                continue
        
        logger.info("Extracted %d translatable segments", len(segments))
        return segments
    
    def _get_element_xpath(self, element: etree._Element) -> str:
        """
        Génère un XPath unique pour un élément.
        
        Args:
            element: Élément XML
            
        Returns:
            XPath de l'élément
        """
        path_parts = []
        current = element
        
        while current is not None:
            parent = current.getparent()
            if parent is None:
                path_parts.insert(0, current.tag)
                break
            
            # Compter la position parmi les frères du même type
            siblings = [e for e in parent if e.tag == current.tag]
            if len(siblings) > 1:
                index = siblings.index(current) + 1
                path_parts.insert(0, f"{current.tag}[{index}]")
            else:
                path_parts.insert(0, current.tag)
            
            current = parent
        
        return "/" + "/".join(path_parts)
    
    def update_segment(self, element: etree._Element, translated_text: str) -> bool:
        """
        Met à jour un segment avec le texte traduit.
        
        Args:
            element: Élément à mettre à jour
            translated_text: Texte traduit
            
        Returns:
            True si succès
        """
        try:
            # Préserver les sous-éléments et attributs
            # Remplacer uniquement le texte
            element.text = translated_text
            return True
        except Exception as e:
            logger.error("Error updating segment: %s", e)
            return False
    
    def update_language(self, target_lang: str) -> None:
        """
        Met à jour l'attribut xml:lang du document.
        
        Args:
            target_lang: Code langue cible (fr, en, ar)
        """
        if self.root is None:
            return
        
        # Mettre à jour xml:lang sur la racine
        self.root.set("{http://www.w3.org/XML/1998/namespace}lang", target_lang)
        
        logger.info("Updated xml:lang to %s", target_lang)
    
    def to_bytes(self) -> bytes:
        """
        Génère le XML en bytes avec préservation de la structure.
        
        Returns:
            Contenu XML en bytes
        """
        if self.tree is None:
            return b""
        
        return etree.tostring(
            self.tree,
            encoding=self.original_encoding,
            xml_declaration=True,
            pretty_print=False,  # Préserver formatage original
            method='xml'
        )
