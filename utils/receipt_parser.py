import re
from datetime import datetime
import logging
from utils.word_lists import get_words, load_wordlists

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
        'receipt_number': '',
        'currency': 'CZK' if language == 'cs' else 'EUR',
        'purpose': '',
        'specific_data': {}  # New field for specific data based on receipt type
    }

    # Normalize the text - fix common OCR errors
    text = text.replace('|', '1')
    
    # Determine receipt type first - this helps with specialized extraction
    receipt_type = determine_receipt_type(text, language)
    result['purpose'] = receipt_type
    
    # Extract merchant name
    result['merchant'] = extract_merchant(text, language)
    
    # Extract date
    date_result = extract_date(text, language)
    if date_result:
        result['date'] = date_result
    
    # Extract total amount
    total_result = extract_total_amount(text, language)
    if total_result:
        result['total'] = total_result
    
    # Detect currency
    result['currency'] = detect_currency(text, language)
    
    # Extract payment method
    result['payment_method'] = extract_payment_method(text, language)
    
    # Extract receipt number
    receipt_num = extract_receipt_number(text, language)
    if receipt_num:
        result['receipt_number'] = receipt_num
    
    # Extract specific data based on receipt type
    if receipt_type == 'Pohonné hmoty':
        result['specific_data'] = extract_fuel_data(text, language)
    elif receipt_type == 'Mýtné':
        result['specific_data'] = extract_toll_data(text, language)
    
    logger.info(f"Extracted receipt information: {result}")
    return result

def determine_receipt_type(text, language):
    """Determine the type of receipt based on text content"""
    # Check for fuel-related keywords
    fuel_words = get_words('fuel', language)
    for keyword in fuel_words:
        if keyword.lower() in text.lower():
            # Additional verification for fuel receipts
            if (re.search(r'(\d+[.,]\d+)\s*[lL]', text) or 
                re.search(r'[qQ]uantit[eé]', text) or 
                re.search(r'[vV]olume', text) or
                re.search(r'[lL]itre', text) or
                re.search(r'[gG]azole', text) or
                re.search(r'[dD]iesel', text)):
                return 'Pohonné hmoty'
    
    # Check for toll-related keywords
    toll_words = get_words('toll', language)
    for keyword in toll_words:
        if keyword.lower() in text.lower():
            # Additional verification for toll receipts
            if (re.search(r'[kK]m', text) or 
                re.search(r'[tT]rajet', text) or 
                re.search(r'[sS]ortie', text) or
                re.search(r'[eE]ntrée', text) or
                re.search(r'SANEF', text) or
                re.search(r'COFIROUTE', text) or
                re.search(r'VINCI', text) or
                re.search(r'AUTOROUTES', text)):
                return 'Mýtné'
    
    # Check for accommodation-related keywords
    accommodation_words = get_words('accommodation', language)
    for keyword in accommodation_words:
        if keyword.lower() in text.lower():
            return 'Bydlení'
    
    # Default to Other
    return 'Ostatní'
def extract_fuel_data(text, language):
    """
    Extract fuel-specific data from receipt
    Args:
        text: OCR text from receipt
        language: Language code
    Returns:
        Dictionary with fuel-specific data
    """
    fuel_data = {
        'volume': None,
        'unit_price': None,
        'fuel_type': None,
        'station': None
    }
    
    # Extract volume (liters)
    volume_patterns = [
        # Czech patterns
        r'(\d+[.,]\d+)\s*[lL](?![a-zA-Z])',
        r'[mM]nožství:?\s*(\d+[.,]\d+)',
        # French patterns
        r'[vV]olume\s*[=:]\s*(\d+[.,]\d+)',
        r'[vV]olume\s*(\d+[.,]\d+)',
        r'[qQ]uantit[eé]\s*[=:]*\s*\(?(\d+[.,]\d+)',
        r'(\d+[.,]\d+)\s*[lL]i?t?r?e?s?\s*pompe'
    ]
    
    for pattern in volume_patterns:
        volume_match = re.search(pattern, text)
        if volume_match:
            try:
                fuel_data['volume'] = float(volume_match.group(1).replace(',', '.'))
                break
            except ValueError:
                continue
    
    # Extract unit price
    price_patterns = [
        # Czech patterns
        r'[cC]ena\s*\/\s*[lL].*?(\d+[.,]\d+)',
        r'[jJ]ednotková\s*cena.*?(\d+[.,]\d+)',
        # French patterns
        r'[pP]rix\s*unit[.,]\s*[=:]*\s*\(?(\d+[.,]\d+)',
        r'[pP]ri[xjs]\s*[=:]*\s*[\€\$]*\s*\(?(\d+[.,]\d+)\s*\/\s*[lL]',
        r'(\d+[.,]\d+)\s*\€\s*\/\s*[lL]'
    ]
    
    for pattern in price_patterns:
        price_match = re.search(pattern, text)
        if price_match:
            try:
                fuel_data['unit_price'] = float(price_match.group(1).replace(',', '.'))
                break
            except ValueError:
                continue
    
    # Extract fuel type
    if re.search(r'\b(diesel|gazo[l]?e|nafta)\b', text, re.IGNORECASE):
        fuel_data['fuel_type'] = 'DIESEL'
    elif re.search(r'\b(natural\s*95|natural|sp95|sp\s*95|e5)\b', text, re.IGNORECASE):
        fuel_data['fuel_type'] = 'NATURAL95'
    elif re.search(r'\b(super|sp98|e10)\b', text, re.IGNORECASE):
        fuel_data['fuel_type'] = 'SUPER'
    elif re.search(r'\b(lpg|autogas)\b', text, re.IGNORECASE):
        fuel_data['fuel_type'] = 'LPG'
    
    # Extract station name
    station_patterns = [
        r'(AVIA\s+[A-Za-z\s]+)',
        r'(GULF\s+[A-Za-z\s]+)',
        r'(OMV\s+[A-Za-z\s]+)',
        r'(TOTAL\s*ENERGIES)',
        r'(SHELL\s+[A-Za-z\s]+)',
        r'(MOL\s+[A-Za-z\s]+)',
        r'(ORLEN\s+[A-Za-z\s]+)',
        r'(BENZINA\s+[A-Za-z\s]+)'
    ]
    
    for pattern in station_patterns:
        station_match = re.search(pattern, text, re.IGNORECASE)
        if station_match:
            fuel_data['station'] = station_match.group(1).strip()
            break
    
    # Calculate unit price if we have volume and total but no unit price
    if fuel_data['volume'] and not fuel_data['unit_price']:
        total = extract_total_amount(text, language)
        if total and fuel_data['volume'] > 0:
            fuel_data['unit_price'] = total / fuel_data['volume']
    
    return fuel_data

def extract_toll_data(text, language):
    """
    Extract toll-specific data from receipt
    Args:
        text: OCR text from receipt
        language: Language code
    Returns:
        Dictionary with toll-specific data
    """
    toll_data = {
        'company': None,
        'route': None,
        'distance': None,
        'entry_point': None,
        'exit_point': None,
        'vehicle_class': None
    }
    
    # Extract toll company
    if re.search(r'SANEF', text, re.IGNORECASE):
        toll_data['company'] = 'SANEF'
    elif re.search(r'COFIROUTE', text, re.IGNORECASE):
        toll_data['company'] = 'COFIROUTE'
    elif re.search(r'VINCI', text, re.IGNORECASE):
        toll_data['company'] = 'VINCI'
    
    # Extract route
    route_match = re.search(r'[tT]rajet\s*:?\s*([^,\n]+)', text)
    if route_match:
        toll_data['route'] = route_match.group(1).strip()
    
    # Extract entry and exit points
    entry_match = re.search(r'[eE]ntrée\s*:?\s*([^,\n]+)', text)
    if entry_match:
        toll_data['entry_point'] = entry_match.group(1).strip()
    
    exit_match = re.search(r'[sS]ortie\s*:?\s*([^,\n]+)', text)
    if exit_match:
        toll_data['exit_point'] = exit_match.group(1).strip()
    
    # If we have entry and exit but no route, construct it
    if not toll_data['route'] and toll_data['entry_point'] and toll_data['exit_point']:
        toll_data['route'] = f"{toll_data['entry_point']} - {toll_data['exit_point']}"
    
    # Extract distance
    distance_match = re.search(r'[kK]m\s*parcourus\s*:?\s*(\d+[.,]\d+)', text) or re.search(r'[kK]m\s*:?\s*(\d+)', text)
    if distance_match:
        try:
            toll_data['distance'] = float(distance_match.group(1).replace(',', '.'))
        except ValueError:
            pass
    
    # Extract vehicle class
    class_match = re.search(r'[cC]lasse\s*:?\s*(\d+)', text) or re.search(r'[cC]lasse\s*tarif\s*:?\s*(\d+)', text)
    if class_match:
        try:
            toll_data['vehicle_class'] = int(class_match.group(1))
        except ValueError:
            pass
    
    return toll_data

def detect_currency(text, language):
    """Detect currency from receipt text"""
    # Default currency based on language
    default_currency = 'CZK' if language == 'cs' else 'EUR'
    
    # Check for EUR symbols in text
    if re.search(r'(?:EUR|€)', text, re.IGNORECASE):
        return 'EUR'
    
    # Check for CZK symbols in text
    if re.search(r'(?:CZK|Kč|KC|Kc)', text, re.IGNORECASE):
        return 'CZK'
    
    # Check for French-specific indicators (likely to be EUR)
    if re.search(r'(?:TVA|SIRET|COFIROUTE|SANEF|VINCI|AUTOROUTES)', text, re.IGNORECASE):
        return 'EUR'
    
    return default_currency

def extract_receipt_number(text, language):
    """Extract receipt number from receipt text"""
    # Enhanced patterns for receipt numbers
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
            return receipt_num_matches.group(1).strip()
    
    # If no specific receipt number pattern matches, try generic patterns
    generic_patterns = [
        r'#\s*(\d+\w*)',
        r'No\.\s*(\d+\w*)',
        r'N°\s*(\d+\w*)',
        r'Nr\.\s*(\d+\w*)',
        r'Ref\.\s*(\d+\w*)',
        r'ID\s*:\s*(\d+\w*)'
    ]
    
    for pattern in generic_patterns:
        generic_match = re.search(pattern, text, re.IGNORECASE)
        if generic_match:
            return generic_match.group(1).strip()
    
    return ''
    # If no specific receipt number pattern matches, try generic patterns
    generic_patterns = [
        r'#\s*(\d+\w*)',
        r'No\.\s*(\d+\w*)',
        r'N°\s*(\d+\w*)',
        r'Nr\.\s*(\d+\w*)',
        r'Ref\.\s*(\d+\w*)',
        r'ID\s*:\s*(\d+\w*)'
    ]
    
    for pattern in generic_patterns:
        generic_match = re.search(pattern, text, re.IGNORECASE)
        if generic_match:
            result['receipt_number'] = generic_match.group(1).strip()
            break

    # If purpose is still not found, set a default
    if not result['purpose']:
        result['purpose'] = 'Ostatní'

    return result

def extract_fuel_data(text, language):
    """
    Extract fuel-specific data from receipt
    Args:
        text: OCR text from receipt
        language: Language code
    Returns:
        Dictionary with fuel-specific data
    """
    fuel_data = {
        'volume': None,
        'unit_price': None,
        'fuel_type': None,
        'station': None
    }
    
    # Extract volume (liters)
    volume_patterns = [
        r'(\d+[.,]\d+)\s*[lL](?![a-zA-Z])',
        r'[mM]nožství:?\s*(\d+[.,]\d+)',
        r'[vV]olume\s*[=:]\s*(\d+[.,]\d+)',
        r'[vV]olume\s*(\d+[.,]\d+)',
        r'[qQ]uantit[eé]\s*[=:]*\s*\(?(\d+[.,]\d+)',
        r'(\d+[.,]\d+)\s*[lL]i?t?r?e?s?\s*pompe'
    ]
    
    for pattern in volume_patterns:
        volume_match = re.search(pattern, text)
        if volume_match:
            try:
                fuel_data['volume'] = float(volume_match.group(1).replace(',', '.'))
                break
            except ValueError:
                continue
    
    # Extract unit price
    price_patterns = [
        r'[cC]ena\s*\/\s*[lL].*?(\d+[.,]\d+)',
        r'[jJ]ednotková\s*cena.*?(\d+[.,]\d+)',
        r'[pP]rix\s*unit[.,]\s*[=:]*\s*\(?(\d+[.,]\d+)',
        r'[pP]ri[xjs]\s*[=:]*\s*[\€\$]*\s*\(?(\d+[.,]\d+)\s*\/\s*[lL]',
        r'(\d+[.,]\d+)\s*\€\s*\/\s*[lL]'
    ]
    
    for pattern in price_patterns:
        price_match = re.search(pattern, text)
        if price_match:
            try:
                fuel_data['unit_price'] = float(price_match.group(1).replace(',', '.'))
                break
            except ValueError:
                continue
    
    # Extract fuel type
    if re.search(r'\b(diesel|gazo[l]?e|nafta)\b', text, re.IGNORECASE):
        fuel_data['fuel_type'] = 'DIESEL'
    elif re.search(r'\b(natural\s*95|natural|sp95|sp\s*95|e5)\b', text, re.IGNORECASE):
        fuel_data['fuel_type'] = 'NATURAL95'
    elif re.search(r'\b(super|sp98|e10)\b', text, re.IGNORECASE):
        fuel_data['fuel_type'] = 'SUPER'
    elif re.search(r'\b(lpg|autogas)\b', text, re.IGNORECASE):
        fuel_data['fuel_type'] = 'LPG'
    
    # Extract station name
    station_patterns = [
        r'(AVIA\s+[A-Za-z\s]+)',
        r'(GULF\s+[A-Za-z\s]+)',
        r'(OMV\s+[A-Za-z\s]+)',
        r'(TOTAL\s*ENERGIES)',
        r'(SHELL\s+[A-Za-z\s]+)',
        r'(MOL\s+[A-Za-z\s]+)',
        r'(ORLEN\s+[A-Za-z\s]+)',
        r'(BENZINA\s+[A-Za-z\s]+)'
    ]
    
    for pattern in station_patterns:
        station_match = re.search(pattern, text, re.IGNORECASE)
        if station_match:
            fuel_data['station'] = station_match.group(1).strip()
            break
    
    # Calculate unit price if we have volume and total but no unit price
    if fuel_data['volume'] and not fuel_data['unit_price']:
        total = extract_total_amount(text, language)
        if total and fuel_data['volume'] > 0:
            fuel_data['unit_price'] = total / fuel_data['volume']
    
    return fuel_data

def extract_toll_data(text, language):
    """
    Extract toll-specific data from receipt
    Args:
        text: OCR text from receipt
        language: Language code
    Returns:
        Dictionary with toll-specific data
    """
    toll_data = {
        'company': None,
        'route': None,
        'distance': None,
        'entry_point': None,
        'exit_point': None,
        'vehicle_class': None
    }
    
    # Extract toll company
    if re.search(r'SANEF', text, re.IGNORECASE):
        toll_data['company'] = 'SANEF'
    elif re.search(r'COFIROUTE', text, re.IGNORECASE):
        toll_data['company'] = 'COFIROUTE'
    elif re.search(r'VINCI', text, re.IGNORECASE):
        toll_data['company'] = 'VINCI'
    
    # Extract route
    route_match = re.search(r'[tT]rajet\s*:?\s*([^,\n]+)', text)
    if route_match:
        toll_data['route'] = route_match.group(1).strip()
    
    # Extract entry and exit points
    entry_match = re.search(r'[eE]ntrée\s*:?\s*([^,\n]+)', text)
    if entry_match:
        toll_data['entry_point'] = entry_match.group(1).strip()
    
    exit_match = re.search(r'[sS]ortie\s*:?\s*([^,\n]+)', text)
    if exit_match:
        toll_data['exit_point'] = exit_match.group(1).strip()
    
    # If we have entry and exit but no route, construct it
    if not toll_data['route'] and toll_data['entry_point'] and toll_data['exit_point']:
        toll_data['route'] = f"{toll_data['entry_point']} - {toll_data['exit_point']}"
    
    # Extract distance
    distance_match = re.search(r'[kK]m\s*parcourus\s*:?\s*(\d+[.,]\d+)', text) or re.search(r'[kK]m\s*:?\s*(\d+)', text)
    if distance_match:
        try:
            toll_data['distance'] = float(distance_match.group(1).replace(',', '.'))
        except ValueError:
            pass
    
    # Extract vehicle class
    class_match = re.search(r'[cC]lasse\s*:?\s*(\d+)', text) or re.search(r'[cC]lasse\s*tarif\s*:?\s*(\d+)', text)
    if class_match:
        try:
            toll_data['vehicle_class'] = int(class_match.group(1))
        except ValueError:
            pass
    
    return toll_data

def extract_total_amount(text, language):
    """Extract total amount from receipt text"""
    # Get total keywords from user wordlist
    total_words = get_words('total', language)
    
    # Create dynamic total patterns based on user wordlist
    total_patterns = []
    
    # Add patterns based on user-defined keywords
    for word in total_words:
        # Clean and escape the keyword for regex
        word_clean = re.escape(word.strip())
        total_patterns.append(
            f"{word_clean}:?\\s*[^\\d]?(\\d+[.,]\\d{{2}})(?:\\s*(?:EUR|€|CZK|Kč))?"
        )
    
    # Add default pattern for finding totals
    total_patterns.append(r'\s(\d+[.,]\d{2})(?:\s*(?:EUR|€|CZK|Kč))?$')
    
    # Try each pattern
    for pattern in total_patterns:
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
                return largest_total
    
    return 0.0
