"""
OCR utility for receipt processing
Handles image preprocessing and OCR operations
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import re
import tempfile
import requests
import logging
from typing import Tuple, Dict, List, Optional, Any
from functools import lru_cache

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OCR configuration
OCR_CONFIG = {
    'language': 'ces',
    'psm': 6,
    'oem': 1,
    'confidence_threshold': 40
}

@lru_cache(maxsize=128)
def compile_pattern(pattern: str) -> re.Pattern:
    """
    Kompiluje a cachuje regulární výraz.
    
    Args:
        pattern: Vzorek regulárního výrazu
        
    Returns:
        Kompilovaný regulární výraz
    """
    return re.compile(pattern)

def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Předzpracuje obrázek pro lepší výsledky OCR.
    
    Args:
        image: Vstupní obrázek (numpy array)
        
    Returns:
        Předzpracovaný obrázek (numpy array)
    """
    try:
        # Kontrola typu vstupu
        if not isinstance(image, np.ndarray):
            logger.error("Vstupní obrázek není numpy array")
            return image
            
        # Převod na uint8 pokud není
        if image.dtype != np.uint8:
            image = image.astype(np.uint8)
            
        # Převod na stupně šedi pokud není
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
            
        # Kontrola, že obrázek je ve stupních šedi
        if len(gray.shape) != 2:
            logger.error("Nepodařilo se převést obrázek na stupně šedi")
            return image
            
        # Aplikace bilaterálního filtru pro zachování hran při odstranění šumu
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Vylepšení kontrastu pomocí CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(filtered)
        
        # Adaptivní prahování s optimalizovanými parametry
        thresh = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 9
        )
        
        # Odstranění šumu pomocí morfologických operací
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Dilatace pro zvýraznění textu
        kernel2 = np.ones((1, 1), np.uint8)
        dilated = cv2.dilate(opening, kernel2, iterations=1)
        
        return dilated
        
    except Exception as e:
        logger.error(f"Chyba při předzpracování obrázku: {str(e)}")
        return image

def perform_ocr(image: np.ndarray, language: str = 'ces', ocr_provider: str = 'tesseract') -> Tuple[str, Dict[str, Any]]:
    """
    Provede OCR na zadaném obrázku pomocí Tesseractu.
    
    Args:
        image: Vstupní obrázek (numpy array)
        language: Jazyk pro OCR
        ocr_provider: OCR engine (pouze tesseract je podporován)
        
    Returns:
        Tuple obsahující (extrahovaný_text, strukturovaná_data)
    """
    try:
        if image is None:
            raise ValueError("Vstupní obrázek je prázdný")
            
        processed_image = preprocess_image(image)
        if processed_image is None:
            raise ValueError("Předzpracování obrázku selhalo")
            
        pil_image = Image.fromarray(processed_image)
        custom_config = f'--oem {OCR_CONFIG["oem"]} --psm {OCR_CONFIG["psm"]} -l {language}'
        
        # Získání textu z obrázku s lepším ošetřením chyb
        try:
            text = pytesseract.image_to_string(pil_image, config=custom_config)
            if not text.strip():
                logger.warning("OCR nedetekoval žádný text")
        except pytesseract.TesseractError as te:
            logger.error(f"Tesseract chyba: {str(te)}")
            return "", {}
            
        # Vytvoření základních strukturovaných dat
        structured_data = {
            'merchant': '',
            'date': None,
            'total': 0.0,
            'items': [],
            'metadata': {
                'language': language,
                'confidence': None,
                'processing_time': None
            }
        }
        
        return text, structured_data
        
    except Exception as e:
        logger.error(f"OCR chyba: {str(e)}")
        return "", {}

def extract_text_blocks(image: np.ndarray, language: str = 'ces') -> List[Dict[str, Any]]:
    """
    Extrahuje textové bloky s informacemi o pozicích.
    
    Args:
        image: Vstupní obrázek (numpy array)
        language: Jazyk pro OCR
        
    Returns:
        Seznam slovníků s textem a informacemi o pozicích
    """
    # Mapování jazykových kódů
    lang_map = {
        'ces': 'ces',
        'fra': 'fra',
        'deu': 'deu',
        'cs': 'ces',
        'fr': 'fra',
        'de': 'deu'
    }
    
    # Získání správného jazykového kódu
    lang_code = lang_map.get(language, 'ces')
    
    try:
        # Předzpracování obrázku
        processed_image = preprocess_image(image)
        
        # Převod NumPy array na PIL Image
        pil_image = Image.fromarray(processed_image)
        
        # Extrakce textu s daty o pozicích
        custom_config = f'--oem {OCR_CONFIG["oem"]} --psm {OCR_CONFIG["psm"]} -l {lang_code}'
        data = pytesseract.image_to_data(pil_image, config=custom_config, output_type=pytesseract.Output.DICT)
        
        blocks = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > OCR_CONFIG['confidence_threshold'] and data['text'][i].strip():
                block = {
                    'text': data['text'][i].strip(),
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'conf': data['conf'][i]
                }
                
                blocks.append(block)
                
        return blocks
        
    except Exception as e:
        logger.error(f"Chyba při extrakci textových bloků: {str(e)}")
        
        # Fallback na metodu založenou na souborech
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_filename = tmp.name
            try:
                cv2.imwrite(tmp_filename, processed_image)
                
                # Extrakce textu s daty o pozicích
                custom_config = f'--oem {OCR_CONFIG["oem"]} --psm {OCR_CONFIG["psm"]} -l {lang_code}'
                data = pytesseract.image_to_data(Image.open(tmp_filename), config=custom_config, output_type=pytesseract.Output.DICT)
                
                blocks = []
                for i in range(len(data['text'])):
                    if int(data['conf'][i]) > OCR_CONFIG['confidence_threshold'] and data['text'][i].strip():
                        block = {
                            'text': data['text'][i].strip(),
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'conf': data['conf'][i]
                        }
                        
                        blocks.append(block)
                        
                return blocks
                
            finally:
                if os.path.exists(tmp_filename):
                    os.unlink(tmp_filename)
                    
        return []
