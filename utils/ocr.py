"""
OCR modul pro rozpoznávání textu z obrázků
Tento modul poskytuje funkce pro OCR zpracování obrázků pomocí Tesseract
"""

import cv2
import pytesseract
import logging
from PIL import Image
from typing import Tuple, Dict, Any, Union
import numpy as np

# Konfigurace logování
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurace OCR
OCR_CONFIG = {
    'language': 'ces',  # Výchozí jazyk - čeština
    'psm': 6,  # Page Segmentation Mode - předpokládá uniformní blok textu
    'oem': 3,  # OCR Engine Mode - používá LSTM OCR Engine
    'config': '--oem 3 --psm 6'  # Výchozí konfigurace Tesseract
}

def perform_ocr(
    image: Union[np.ndarray, Image.Image],
    language: str = OCR_CONFIG['language'],
    config: str = OCR_CONFIG['config']
) -> Tuple[str, Dict[str, Any]]:
    """
    Provede OCR na obrázku pomocí Tesseract.
    
    Args:
        image: Obrázek ve formátu numpy array nebo PIL Image
        language: Jazykový kód pro OCR (výchozí 'ces' pro češtinu)
        config: Konfigurační řetězec pro Tesseract
        
    Returns:
        Tuple[str, Dict[str, Any]]: Rozpoznaný text a strukturovaná data
    """
    try:
        # Převod numpy array na PIL Image pokud je potřeba
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
            
        # Kontrola, zda je obrázek validní
        if not isinstance(image, Image.Image) or image.size[0] == 0 or image.size[1] == 0:
            logger.error("Neplatný obrázek pro OCR")
            return "", {}
            
        # Provedení OCR
        text = pytesseract.image_to_string(
            image,
            lang=language,
            config=config
        )
        
        # Získání strukturovaných dat
        data = pytesseract.image_to_data(
            image,
            lang=language,
            config=config,
            output_type=pytesseract.Output.DICT
        )
        
        # Filtrování dat s nízkou důvěryhodností
        confidence_threshold = 60
        filtered_data = {
            key: [val for i, val in enumerate(data[key]) 
                  if data['conf'][i] > confidence_threshold]
            for key in data.keys()
        }
        
        return text.strip(), filtered_data
        
    except Exception as e:
        logger.error(f"Chyba při OCR zpracování: {str(e)}")
        return "", {}

def preprocess_image(
    image: Union[np.ndarray, Image.Image]
) -> Union[np.ndarray, Image.Image]:
    """
    Předzpracuje obrázek pro lepší OCR výsledky.
    
    Args:
        image: Obrázek ve formátu numpy array nebo PIL Image
        
    Returns:
        Union[np.ndarray, Image.Image]: Předzpracovaný obrázek
    """
    try:
        # Převod na numpy array pokud je potřeba
        if isinstance(image, Image.Image):
            image = np.array(image)
            
        # Převod na šedotónový obrázek
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
        # Aplikace adaptivního prahování
        image = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        # Odstranění šumu
        image = cv2.fastNlMeansDenoising(image)
        
        return image
        
    except Exception as e:
        logger.error(f"Chyba při předzpracování obrázku: {str(e)}")
        return image
