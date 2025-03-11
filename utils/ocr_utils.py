import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import re
import tempfile

def preprocess_image(image):
    """
    Preprocess the image to improve OCR results
    
    Args:
        image: Input image (numpy array)
        
    Returns:
        Preprocessed image (numpy array)
    """
    # Convert to grayscale if not already
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Apply noise removal
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    return opening

def perform_ocr(image, language='ces'):
    """
    Performs OCR on the provided image
    
    Args:
        image: Input image (numpy array)
        language: Language to use for OCR (default: ces for Czech)
                  Other options: 'fra' (French), 'deu' (German)
    
    Returns:
        Extracted text as string
    """
    # Map language codes to Tesseract language codes
    lang_map = {
        'ces': 'ces',  # Czech
        'fra': 'fra',  # French
        'deu': 'deu',  # German
        'cs': 'ces',
        'fr': 'fra',
        'de': 'deu'
    }
    
    # Get the correct language code
    lang_code = lang_map.get(language, 'ces')
    
    # Preprocess the image
    processed_image = preprocess_image(image)
    
    # Save the processed image to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_filename = tmp.name
        cv2.imwrite(tmp_filename, processed_image)
    
    try:
        # Perform OCR
        custom_config = f'--oem 3 --psm 6 -l {lang_code}'
        text = pytesseract.image_to_string(Image.open(tmp_filename), config=custom_config)
        
        # Clean up the text
        text = text.strip()
        
        # Remove empty lines and common OCR artifacts
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r'[^\x00-\x7F\u00C0-\u02AF\u0370-\u03FF\u0400-\u04FF]+', '', text)
        
        return text
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_filename):
            os.unlink(tmp_filename)

def extract_text_blocks(image, language='ces'):
    """
    Extracts text blocks from the image with positions
    
    Args:
        image: Input image (numpy array)
        language: Language to use for OCR
    
    Returns:
        List of dictionaries with text and position information
    """
    # Map language codes to Tesseract language codes
    lang_map = {
        'ces': 'ces',  # Czech
        'fra': 'fra',  # French
        'deu': 'deu',  # German
        'cs': 'ces',
        'fr': 'fra',
        'de': 'deu'
    }
    
    # Get the correct language code
    lang_code = lang_map.get(language, 'ces')
    
    # Preprocess the image
    processed_image = preprocess_image(image)
    
    # Save the processed image to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_filename = tmp.name
        cv2.imwrite(tmp_filename, processed_image)
    
    try:
        # Extract text with positioning data
        custom_config = f'--oem 3 --psm 6 -l {lang_code}'
        data = pytesseract.image_to_data(Image.open(tmp_filename), config=custom_config, output_type=pytesseract.Output.DICT)
        
        blocks = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 60 and data['text'][i].strip():  # Filter out low confidence items
                block = {
                    'text': data['text'][i],
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'conf': data['conf'][i]
                }
                blocks.append(block)
        
        return blocks
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_filename):
            os.unlink(tmp_filename)
