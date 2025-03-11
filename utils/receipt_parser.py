import re
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_receipt_info(text, language='cs'):
    """
    Extract relevant information from receipt text
    
    Args:
        text: OCR extracted text from receipt
        language: Language code ('cs', 'fr', 'de')
    
    Returns:
        Dictionary with extracted information
    """
    logger.info(f"Extracting receipt information from text in language: {language}")
    
    # Initialize result dictionary
    result = {
        'merchant': '',
        'date': datetime.now(),
        'total': 0.0,
        'payment_method': '',
        'receipt_number': ''
    }
    
    # Extract merchant name (usually first few lines)
    lines = text.strip().split('\n')
    if lines:
        # Try to find a line that looks like a company name
        # Often the first non-empty line
        for line in lines[:3]:
            if len(line.strip()) > 2 and not re.match(r'^\d+$', line.strip()):
                result['merchant'] = line.strip()
                break
    
    # Extract date based on language
    date_patterns = {
        'cs': [
            r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})',  # DD.MM.YYYY or DD.MM.YY
            r'Datum:?\s*(\d{1,2})\.(\d{1,2})\.(\d{2,4})',
            r'Dne:?\s*(\d{1,2})\.(\d{1,2})\.(\d{2,4})'
        ],
        'fr': [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'Date:?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})'
        ],
        'de': [
            r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})',  # DD.MM.YYYY
            r'Datum:?\s*(\d{1,2})\.(\d{1,2})\.(\d{2,4})'
        ]
    }
    
    # Get patterns for the selected language or default to Czech
    patterns = date_patterns.get(language, date_patterns['cs'])
    
    # Try each pattern
    for pattern in patterns:
        date_matches = re.search(pattern, text)
        if date_matches:
            day, month, year = date_matches.groups()
            # Handle 2-digit years
            if len(year) == 2:
                year = '20' + year
            try:
                result['date'] = datetime(int(year), int(month), int(day))
                break
            except ValueError:
                logger.warning(f"Found invalid date: {day}.{month}.{year}")
                continue
    
    # Extract total amount based on language
    total_patterns = {
        'cs': [
            r'CELKEM\s*(?:CZK|Kč)?\.?\s*(\d+[.,]\d{2})',
            r'Celkem:?\s*(?:CZK|Kč)?\.?\s*(\d+[.,]\d{2})',
            r'Součet:?\s*(?:CZK|Kč)?\.?\s*(\d+[.,]\d{2})',
            r'Celková\s*částka:?\s*(?:CZK|Kč)?\.?\s*(\d+[.,]\d{2})',
            r'(?:CZK|Kč)\s*(\d+[.,]\d{2})$',
            r'TOTAL\s*(?:CZK|Kč)?\.?\s*(\d+[.,]\d{2})',
            r'Celkem\s*(?:CZK|Kč)?\.?\s*[^\d]?(\d+[.,]\d{2})',
            r'Celkem:?\s*[^\d]?(\d+[.,]\d{2})',
        ],
        'fr': [
            r'TOTAL\s*(?:EUR)?\.?\s*(\d+[.,]\d{2})',
            r'Total:?\s*(?:EUR)?\.?\s*(\d+[.,]\d{2})',
            r'MONTANT\s*(?:EUR)?\.?\s*(\d+[.,]\d{2})',
            r'Total à payer:?\s*(?:EUR)?\.?\s*(\d+[.,]\d{2})',
            r'EUR\s*(\d+[.,]\d{2})$'
        ],
        'de': [
            r'GESAMT\s*(?:EUR)?\.?\s*(\d+[.,]\d{2})',
            r'Summe:?\s*(?:EUR)?\.?\s*(\d+[.,]\d{2})',
            r'Gesamtbetrag:?\s*(?:EUR)?\.?\s*(\d+[.,]\d{2})',
            r'EUR\s*(\d+[.,]\d{2})$'
        ]
    }
    
    # Get patterns for the selected language or default to Czech
    patterns = total_patterns.get(language, total_patterns['cs'])
    
    # Try each pattern
    for pattern in patterns:
        total_matches = re.search(pattern, text, re.IGNORECASE)
        if total_matches:
            total_str = total_matches.group(1).replace(',', '.')
            try:
                result['total'] = float(total_str)
                break
            except ValueError:
                logger.warning(f"Found invalid total amount: {total_str}")
                continue
    
    # Extract payment method based on language
    payment_patterns = {
        'cs': {
            'cash': [r'HOTOVOST', r'Hotově', r'Hotovost', r'v hotovosti'],
            'card': [r'KARTA', r'Platební karta', r'Kartou', r'Karta'],
            'other': [r'Jiné', r'Ostatní', r'Bankovní převod']
        },
        'fr': {
            'cash': [r'ESPÈCES', r'ESPECES', r'Espèces', r'En espèces'],
            'card': [r'CARTE', r'Carte bancaire', r'Carte de crédit', r'CB'],
            'other': [r'Autre', r'Virement', r'Chèque']
        },
        'de': {
            'cash': [r'BARGELD', r'Bar', r'Barzahlung'],
            'card': [r'KARTE', r'EC-Karte', r'Kreditkarte', r'Kartenzahlung'],
            'other': [r'Andere', r'Überweisung', r'Lastschrift']
        }
    }
    
    # Get patterns for the selected language or default to Czech
    patterns = payment_patterns.get(language, payment_patterns['cs'])
    
    # Try each pattern for each payment type
    payment_found = False
    for payment_type, pattern_list in patterns.items():
        if payment_found:
            break
        
        for pattern in pattern_list:
            if re.search(pattern, text, re.IGNORECASE):
                # Get appropriate translation for the payment method based on language
                if language == 'cs':
                    result['payment_method'] = 'Hotovost' if payment_type == 'cash' else 'Kartou' if payment_type == 'card' else 'Jiné'
                elif language == 'fr':
                    result['payment_method'] = 'Espèces' if payment_type == 'cash' else 'Carte' if payment_type == 'card' else 'Autre'
                elif language == 'de':
                    result['payment_method'] = 'Bargeld' if payment_type == 'cash' else 'Karte' if payment_type == 'card' else 'Andere'
                else:
                    result['payment_method'] = 'Cash' if payment_type == 'cash' else 'Card' if payment_type == 'card' else 'Other'
                
                payment_found = True
                break
    
    # Default payment method if none is found
    if not result['payment_method']:
        if language == 'cs':
            result['payment_method'] = 'Hotovost'
        elif language == 'fr':
            result['payment_method'] = 'Espèces'
        elif language == 'de':
            result['payment_method'] = 'Bargeld'
        else:
            result['payment_method'] = 'Cash'
    
    # Extract receipt number based on language
    receipt_patterns = {
        'cs': [
            r'Č\.\s*účtenky:?\s*(\w+)',
            r'Doklad\s*(?:č\.):?\s*(\w+)',
            r'Účtenka\s*(?:č\.):?\s*(\w+)',
            r'Číslo\s*dokladu:?\s*(\w+)',
            r'Číslo\s*účtenky:?\s*(\w+)'
        ],
        'fr': [
            r'N°\s*ticket:?\s*(\w+)',
            r'Ticket\s*N°:?\s*(\w+)',
            r'Facture\s*N°:?\s*(\w+)',
            r'Numéro\s*de\s*reçu:?\s*(\w+)'
        ],
        'de': [
            r'Beleg\s*Nr\.:?\s*(\w+)',
            r'Quittung\s*Nr\.:?\s*(\w+)',
            r'Belegnummer:?\s*(\w+)',
            r'Rechnungsnummer:?\s*(\w+)'
        ]
    }
    
    # Get patterns for the selected language or default to Czech
    patterns = receipt_patterns.get(language, receipt_patterns['cs'])
    
    # Try each pattern
    for pattern in patterns:
        receipt_num_matches = re.search(pattern, text, re.IGNORECASE)
        if receipt_num_matches:
            result['receipt_number'] = receipt_num_matches.group(1)
            break
    
    logger.info(f"Extracted receipt information: {result}")
    return result
