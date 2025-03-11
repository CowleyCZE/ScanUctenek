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
    
    # Normalize the text - fix common OCR errors
    text = text.replace('|', '1').replace('O', '0').replace('o', '0')
    
    # Extract merchant name (usually first few lines)
    lines = text.strip().split('\n')
    if lines:
        # Skip empty or very short lines
        valid_lines = [line for line in lines[:5] if len(line.strip()) > 3 and not re.match(r'^\d+$', line.strip())]
        if valid_lines:
            # Most often first non-empty line that doesn't look like a date or number
            result['merchant'] = valid_lines[0].strip()
    
    # Extract date based on language with improved patterns
    date_patterns = {
        'cs': [
            r'(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})',  # DD.MM.YYYY or DD.MM.YY
            r'Datum:?\s*(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})',
            r'Dne:?\s*(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})',
            r'Date:?\s*(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})'
        ],
        'fr': [
            r'(\d{1,2})[/-\.](\d{1,2})[/-\.](\d{2,4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'Date:?\s*(\d{1,2})[/-\.](\d{1,2})[/-\.](\d{2,4})'
        ],
        'de': [
            r'(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})',  # DD.MM.YYYY
            r'Datum:?\s*(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})'
        ]
    }
    
    # Get patterns for the selected language or default to Czech
    patterns = date_patterns.get(language, date_patterns['cs'])
    
    # Try each pattern
    for pattern in patterns:
        date_matches = re.search(pattern, text, re.IGNORECASE)
        if date_matches:
            day, month, year = date_matches.groups()
            # Handle 2-digit years
            if len(year) == 2:
                year = '20' + year
            try:
                # Validate date values
                day_val = int(day)
                month_val = int(month)
                year_val = int(year)
                
                if 1 <= day_val <= 31 and 1 <= month_val <= 12 and 2000 <= year_val <= 2030:
                    result['date'] = datetime(year_val, month_val, day_val)
                    break
                else:
                    logger.warning(f"Found date with out-of-range values: {day}.{month}.{year}")
            except ValueError:
                logger.warning(f"Found invalid date: {day}.{month}.{year}")
                continue
    
    # Extract total amount based on language - enhanced patterns
    total_patterns = {
        'cs': [
            r'CELKEM\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            r'Celkem:?\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            r'Součet:?\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            r'SOUČET:?\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            r'Celková\s*částka:?\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            r'(?:CZK|Kč|KC)\s*(\d+[.,]\d{2})$',
            r'TOTAL\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            r'Celkem\s*(?:CZK|Kč|KC)?\.?\s*[^\d]?(\d+[.,]\d{2})',
            r'Celkem:?\s*[^\d]?(\d+[.,]\d{2})',
            r'ZAPLACENO:?\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            r'Zaplaceno:?\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            r'K ÚHRADĚ:?\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            r'K úhradě:?\s*(?:CZK|Kč|KC)?\.?\s*(\d+[.,]\d{2})',
            # Fallback pattern - look for numeric values that look like prices at the end of lines
            r'\s(\d+[.,]\d{2})(?:\s*(?:CZK|Kč|KC))?$'
        ],
        'fr': [
            r'TOTAL\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'Total:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'MONTANT\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'Montant:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'Total à payer:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'TOTAL TTC:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'Total TTC:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'NET A PAYER:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'(?:EUR|€)\s*(\d+[.,]\d{2})$',
            r'\s(\d+[.,]\d{2})(?:\s*(?:EUR|€))?$'
        ],
        'de': [
            r'GESAMT\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'Summe:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'SUMME:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'Gesamtbetrag:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'GESAMTBETRAG:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'ZU ZAHLEN:?\s*(?:EUR|€)?\.?\s*(\d+[.,]\d{2})',
            r'(?:EUR|€)\s*(\d+[.,]\d{2})$',
            r'\s(\d+[.,]\d{2})(?:\s*(?:EUR|€))?$'
        ]
    }
    
    # Get patterns for the selected language or default to Czech
    patterns = total_patterns.get(language, total_patterns['cs'])
    
    # Try each pattern
    for pattern in patterns:
        total_matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if total_matches:
            # Use the largest value found (often the final total)
            largest_total = 0.0
            for total_str in total_matches:
                try:
                    total_val = float(total_str.replace(',', '.'))
                    # Keep the largest value that's reasonably sized (to filter out possible line item prices)
                    if total_val > largest_total and total_val < 100000:  # Sanity check for reasonable amount
                        largest_total = total_val
                except ValueError:
                    logger.warning(f"Found invalid total amount: {total_str}")
                    continue
            
            if largest_total > 0:
                result['total'] = largest_total
                break
    
    # Extract payment method based on language - enhanced patterns
    payment_patterns = {
        'cs': {
            'cash': [r'HOTOVOST', r'Hotově', r'Hotovost', r'v hotovosti', r'HOTOVĚ'],
            'card': [r'KARTA', r'Platební karta', r'Kartou', r'Karta', r'KARTOU', r'PLATEBNÍ KARTA'],
            'other': [r'Jiné', r'Ostatní', r'Bankovní převod', r'PŘEVOD', r'POUKÁZKA', r'STRAVENKY']
        },
        'fr': {
            'cash': [r'ESPÈCES', r'ESPECES', r'Espèces', r'En espèces', r'CASH'],
            'card': [r'CARTE', r'Carte bancaire', r'Carte de crédit', r'CB', r'CARTE BANCAIRE'],
            'other': [r'Autre', r'Virement', r'Chèque', r'CHEQUE', r'VIREMENT']
        },
        'de': {
            'cash': [r'BARGELD', r'Bar', r'Barzahlung', r'BAR', r'BARZAHLUNG'],
            'card': [r'KARTE', r'EC-Karte', r'Kreditkarte', r'Kartenzahlung', r'EC KARTE', r'KARTENZAHLUNG'],
            'other': [r'Andere', r'Überweisung', r'Lastschrift', r'UEBERWEISUNG', r'RECHNUNG']
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
    
    # Extract receipt number based on language - enhanced patterns
    receipt_patterns = {
        'cs': [
            r'Č\.\s*(?:účtenky|dokladu):?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Doklad\s*(?:č\.):?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Účtenka\s*(?:č\.):?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Číslo\s*dokladu:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Číslo\s*účtenky:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'DOKLAD\s*(?:č\.)?:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Cislo\s*dokladu:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Číslo\s*prodejky:?\s*[:#]?\s*(\w+[-/]?\w+)'
        ],
        'fr': [
            r'N°\s*ticket:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Ticket\s*N°:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Facture\s*N°:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Numéro\s*de\s*reçu:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Reçu\s*N°:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'TICKET\s*[:#]?\s*(\w+[-/]?\w+)',
            r'N°\s*TICKET\s*[:#]?\s*(\w+[-/]?\w+)'
        ],
        'de': [
            r'Beleg\s*Nr\.:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Quittung\s*Nr\.:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Belegnummer:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Rechnungsnummer:?\s*[:#]?\s*(\w+[-/]?\w+)',
            r'BELEG\s*NR\.\s*[:#]?\s*(\w+[-/]?\w+)',
            r'BELEGNR\.\s*[:#]?\s*(\w+[-/]?\w+)',
            r'Kassabon\s*Nr\.:?\s*[:#]?\s*(\w+[-/]?\w+)'
        ]
    }
    
    # Get patterns for the selected language or default to Czech
    patterns = receipt_patterns.get(language, receipt_patterns['cs'])
    
    # Try each pattern
    for pattern in patterns:
        receipt_num_matches = re.search(pattern, text, re.IGNORECASE)
        if receipt_num_matches:
            result['receipt_number'] = receipt_num_matches.group(1).strip()
            break
    
    logger.info(f"Extracted receipt information: {result}")
    return result
