import os
import google.generativeai as genai
from google.api_core import retry

# ...existing code...

def process_with_gemini(image_path):
    try:
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        model = genai.GenerativeModel('gemini-pro-vision')
        
        with open(image_path, 'rb') as f:
            image_data = f.read()
            
        response = retry.Retry()(model.generate_content)(image_data)
        return response.text
        
    except Exception as e:
        logger.error(f"Error processing image with Gemini: {str(e)}")
        return None

# ...existing code...
