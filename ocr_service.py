import os
import google.generativeai as genai

def perform_gemini_ocr(image):
    """
    Performs OCR using Google Gemini API
    """
    api_key = os.getenv('GEMINI_API_KEY', '')

    if not api_key:
        raise ValueError("GEMINI_API_KEY není nastaven. Prosím zadejte platný API klíč v nastavení.")

    if len(api_key) < 30:  # Základní kontrola formátu klíče
        raise ValueError("Neplatný formát GEMINI_API_KEY")
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Create model instance - using Gemini Pro Vision
        model = genai.GenerativeModel('gemini-pro-vision')
        
        # Generate content from image
        response = model.generate_content(
            ["Extrahuj veškerý text z tohoto účtenky.", image],
            generation_config={
                "temperature": 0.1,  # Lower temperature for more focused results
                "top_p": 1,
                "top_k": 32,
            }
        )
        
        # Get the text from response
        if response.text:
            return response.text.strip()
        else:
            return "Nebyl nalezen žádný text."

    except Exception as e:
        raise Exception(f"Chyba při zpracování OCR: {str(e)}")
