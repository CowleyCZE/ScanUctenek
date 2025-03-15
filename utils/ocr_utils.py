import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import re
import tempfile
import requests

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
    
    # Apply bilateral filter to preserve edges while removing noise
    filtered = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Apply contrast enhancement using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(filtered)
    
    # Apply adaptive thresholding with optimized parameters
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 9
    )
    
    # Noise removal with morphological operations
    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    # Dilation to make text more prominent
    kernel2 = np.ones((1, 1), np.uint8)
    dilated = cv2.dilate(opening, kernel2, iterations=1)
    
    return dilated

def perform_gemini_ocr(image):
    """
    Performs OCR using Google Cloud Vision API
    Args:
        image: Input image
    Returns:
        Extracted text as string
    """
    api_url = "https://gemini.googleapis.com/v1/receipts:analyze"
    api_key = os.getenv('GEMINI_API_KEY', '')

    if not api_key:
        raise Exception("GEMINI_API_KEY not set")

    # Save image to temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        cv2.imwrite(tmp.name, image)
        
        try:
            with open(tmp.name, "rb") as image_file:
                image_data = image_file.read()

            headers = {
                "Content-Type": "application/octet-stream",
                "Authorization": f"Bearer {api_key}"
            }

            response = requests.post(api_url, headers=headers, data=image_data)
            
            if response.status_code == 200:
                # Extract text from Gemini response
                data = response.json()
                text = ""
                if "text" in data:
                    text = data["text"]
                return text
            else:
                response.raise_for_status()
        finally:
            os.unlink(tmp.name)

def perform_ocr(image, language='ces', ocr_provider='tesseract'):
    """
    Performs OCR on the provided image using selected provider
    Args:
        image: Input image (numpy array)
        language: Language for OCR
        ocr_provider: 'tesseract' or 'gemini'
    Returns:
        Extracted text as string
    """
    try:
        if ocr_provider == 'gemini':
            return perform_gemini_ocr(image)
        else:
            # Use existing Tesseract OCR code
            processed_image = preprocess_image(image)
            pil_image = Image.fromarray(processed_image)
            custom_config = f'--oem 1 --psm 6 -l {language}'
            return pytesseract.image_to_string(pil_image, config=custom_config)
    except Exception as e:
        print(f"OCR error with {ocr_provider}: {str(e)}")
        return f"OCR error: {str(e)}"

def extract_text_blocks(image, language='ces'):
    """
    Extract text blocks with positioning information
    Args:
        image: Input image (numpy array)
        language: Language to use for OCR
    Returns:
        List of dictionaries with text and position information
    """
    # Map language codes
    lang_map = {
        'ces': 'ces',
        'fra': 'fra',
        'deu': 'deu',
        'cs': 'ces',
        'fr': 'fra',
        'de': 'deu'
    }
    
    # Get the correct language code
    lang_code = lang_map.get(language, 'ces')
    
    # Preprocess the image
    processed_image = preprocess_image(image)
    
    try:
        # Convert NumPy array to PIL Image
        pil_image = Image.fromarray(processed_image)
        
        # Extract text with positioning data
        custom_config = f'--oem 1 --psm 6 -l {lang_code}'
        data = pytesseract.image_to_data(pil_image, config=custom_config, output_type=pytesseract.Output.DICT)
        
        blocks = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 40 and data['text'][i].strip():
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
        print(f"Block extraction error: {str(e)}")
        
        # Fallback to file-based method if direct method fails
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_filename = tmp.name
            cv2.imwrite(tmp_filename, processed_image)
            
            try:
                # Extract text with positioning data
                custom_config = f'--oem 1 --psm 6 -l {lang_code}'
                data = pytesseract.image_to_data(Image.open(tmp_filename), config=custom_config, output_type=pytesseract.Output.DICT)
                
                blocks = []
                for i in range(len(data['text'])):
                    if int(data['conf'][i]) > 40 and data['text'][i].strip():
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
