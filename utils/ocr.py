import cv2
import pytesseract
import logging

logger = logging.getLogger(__name__)

def perform_ocr(image):
    """
    Perform OCR on image
    Args:
        image: numpy array image
    Returns:
        Extracted text as string
    """
    try:
        text = pytesseract.image_to_string(image, lang='ces')
        return text
    except Exception as e:
        logger.error(f"OCR error: {str(e)}")
        return ""
