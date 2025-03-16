import requests
from typing import Optional

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1"

class GeminiOCR:
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def analyze_image(self, image_data: bytes) -> Optional[dict]:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Use the correct Gemini API endpoint for vision tasks
            url = f"{GEMINI_API_BASE}/models/gemini-pro-vision:generateContent"
            
            response = requests.post(url, 
                                  headers=headers,
                                  json={"contents": [{"parts": [{"image_bytes": image_data}]}]})
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"OCR Error: {str(e)}")
            return None
