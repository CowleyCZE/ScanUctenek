import os
from typing import Tuple, Optional, Dict, Union
from PIL import Image
import pytesseract
import logging
import cv2
import numpy as np
import re
from datetime import datetime
from gemini_ocr import GeminiOCR  # Change import to use GeminiOCR class
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def preprocess_image(image) -> Image:
    """
    Preprocess the image for better OCR results.
    
    Args:
        image: Input image (numpy array or PIL Image)
        
    Returns:
        Image: Preprocessed image
    """
    logging.info("Starting image preprocessing")
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Resize image to a standard size
    resized = cv2.resize(gray, (1024, 1024))
    
    # Apply contrast enhancement using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(resized)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    logging.info("Image preprocessing completed")
    return Image.fromarray(thresh)

def extract_structured_data(response: Dict) -> Dict:
    """
    Extract structured data from OCR response.
    
    Args:
        response: OCR response containing text and possibly other data
        
    Returns:
        Dict: Extracted structured data
    """
    text = response.get('text', '')
    structured_data = {
        'merchant': '',
        'date': None,
        'total': 0.0,
        'items': [],
        'metadata': {}
    }

    # Regex patterns for extracting data
    merchant_pattern = re.compile(r'Obchodník:\s*(.*)')
    date_pattern = re.compile(r'Datum:\s*(\d{2}\.\d{2}\.\d{4})')
    total_pattern = re.compile(r'Celkem:\s*([\d,]+\.?\d*)\s*Kč')
    item_pattern = re.compile(r'(\d+)\s*x\s*(.*)\s*([\d,]+\.?\d*)\s*Kč')

    # Extract merchant
    merchant_match = merchant_pattern.search(text)
    if merchant_match:
        structured_data['merchant'] = merchant_match.group(1).strip()

    # Extract date
    date_match = date_pattern.search(text)
    if date_match:
        structured_data['date'] = datetime.strptime(date_match.group(1), '%d.%m.%Y')

    # Extract total
    total_match = total_pattern.search(text)
    if total_match:
        structured_data['total'] = float(total_match.group(1).replace(',', ''))

    # Extract items
    for item_match in item_pattern.finditer(text):
        quantity = int(item_match.group(1))
        name = item_match.group(2).strip()
        price = float(item_match.group(3).replace(',', ''))
        structured_data['items'].append({
            'name': name,
            'quantity': quantity,
            'unit_price': price / quantity,
            'total_price': price
        })

    return structured_data

def perform_gemini_ocr(image) -> Union[str, Dict]:
    """
    Provede OCR pomocí Gemini API.
    
    Args:
        image: Vstupní obrázek (numpy array nebo PIL Image)
        
    Returns:
        Union[str, Dict]: Výsledek OCR jako text nebo strukturovaná data
    """
    api_key = os.getenv('GEMINI_API_KEY', '')

    if not api_key:
        raise ValueError("GEMINI_API_KEY není nastaven. Prosím zadejte platný API klíč v nastavení.")

    if len(api_key) < 30:  # Základní kontrola formátu klíče
        raise ValueError("Neplatný formát GEMINI_API_KEY")

    # Create GeminiOCR instance
    ocr = GeminiOCR(api_key)
    
    # Convert image to bytes
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        image.save(tmp.name)
        
        try:
            with open(tmp.name, "rb") as image_file:
                image_data = image_file.read()
                
            # Use GeminiOCR class for analysis
            result = ocr.analyze_image(image_data)
            if result:
                return result
            else:
                raise ValueError("Gemini API neposkytla žádná data")
                
        finally:
            os.unlink(tmp.name)

def perform_ocr(image, language: str = 'ces', ocr_provider: str = 'tesseract') -> Tuple[str, Optional[Dict]]:
    """
    Provede OCR pomocí zvoleného poskytovatele (Tesseract nebo Gemini)
    
    Args:
        image: Vstupní obrázek (numpy array nebo PIL Image)
        language: Kód jazyka pro OCR (výchozí 'ces' pro češtinu)
        ocr_provider: Poskytovatel OCR ('tesseract' nebo 'gemini')
        
    Returns:
        Tuple obsahující:
        - text (str): Extrahovaný text
        - structured_data (Optional[Dict]): Strukturovaná data nebo None
    """
    logging.info(f"Performing OCR with provider: {ocr_provider}")
    try:
        if ocr_provider == 'gemini':
            response = perform_gemini_ocr(image)
            structured_data = None
            
            if isinstance(response, dict):
                structured_data = extract_structured_data(response)
                text = response.get('text', '')
            else:
                text = str(response)
                
            return text, structured_data
                
        elif ocr_provider == 'tesseract':
            processed_image = preprocess_image(image)
            text = pytesseract.image_to_string(
                Image.fromarray(processed_image),  # Fix call to Image.fromarray
                config=f'--oem 1 --psm 6 -l {language}'
            )
            # Pokus o extrakci strukturovaných dat i z Tesseract výstupu
            structured_data = extract_structured_data({'text': text})
            return text, structured_data
            
        else:
            raise ValueError(f"Nepodporovaný OCR poskytovatel: {ocr_provider}")
            
    except Exception as e:
        logging.error(f"OCR chyba s poskytovatelem {ocr_provider}: {str(e)}")
        return f"OCR chyba: {str(e)}", None
