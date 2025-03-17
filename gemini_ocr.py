import requests
import json
import base64
from typing import Optional, Dict, Any

class GeminiOCR:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.vision_api_url = "https://vision.googleapis.com/v1/images:annotate"
        
    def analyze_image(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        try:
            # Convert image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare Vision API request
            request_json = {
                "requests": [
                    {
                        "image": {
                            "content": image_b64
                        },
                        "features": [
                            {
                                "type": "DOCUMENT_TEXT_DETECTION"
                            }
                        ]
                    }
                ]
            }
            
            # Make request to Vision API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.post(
                f"{self.vision_api_url}?key={self.api_key}",
                headers=headers,
                json=request_json
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract text from response
                if 'responses' in result and len(result['responses']) > 0:
                    text_annotation = result['responses'][0].get('fullTextAnnotation', {})
                    extracted_text = text_annotation.get('text', '')
                    
                    # Return structured response
                    return {
                        'text': extracted_text,
                        'status': 'success',
                        'raw_response': result
                    }
            else:
                print(f"API Error: {response.status_code} - {response.text}")
            
            return None
                
        except Exception as e:
            print(f"OCR Error: {str(e)}")
            return None
