import cv2
import pytesseract
import logging
from PIL import Image

logger = logging.getLogger(__name__)

def perform_ocr(image, language='ces'):
    """
    Perform OCR on image using Tesseract
    Args:
        image: numpy array image
        language: OCR language code (default 'ces' for Czech)
    Returns:
        Extracted text as string
    """
    try:
        # Convert numpy array to PIL Image if needed
        if not isinstance(image, Image.Image):
            image = Image.fromarray(image)
            
        text = pytesseract.image_to_string(image, lang=language)
        return text, {}  # Return empty dict as structured data for compatibility
    except Exception as e:
        logger.error(f"OCR error: {str(e)}")
        return "", {}
