from typing import Dict, List, Any, Optional
from datetime import datetime

def extract_structured_data(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrahuje strukturovaná data z Gemini API odpovědi
    """
    structured_data = {
        'merchant': '',
        'date': None,
        'total': 0.0,
        'items': [],
        'metadata': {}
    }

    try:
        if 'receipt' in response_data:
            receipt = response_data['receipt']
            
            # Extrahovat základní údaje
            if 'merchant' in receipt:
                structured_data['merchant'] = receipt['merchant'].get('name', '')
            
            if 'date' in receipt:
                structured_data['date'] = datetime.strptime(receipt['date'], '%Y-%m-%d')
                
            if 'total' in receipt:
                structured_data['total'] = float(receipt['total'])
                
            # Zpracovat položky
            if 'items' in receipt:
                for item in receipt['items']:
                    structured_data['items'].append({
                        'name': item.get('name', ''),
                        'quantity': float(item.get('quantity', 1)),
                        'unit_price': float(item.get('unit_price', 0)),
                        'total_price': float(item.get('total_price', 0))
                    })
                    
            # Zpracovat metadata
            if 'metadata' in receipt:
                structured_data['metadata'] = receipt['metadata']

        return structured_data
        
    except Exception as e:
        return {
            'error': f"Chyba při zpracování dat: {str(e)}",
            'raw_data': response_data
        }
