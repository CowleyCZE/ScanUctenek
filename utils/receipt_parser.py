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
        'purpose': ''
    }
    
    # Normalize the text - fix common OCR errors
    text = text.replace('|', '1').replace('O', '0').replace('o', '0')
    
    # Get user-defined wordlists
    merchant_words = get_words('merchant', language)
    purpose_words = get_words('purpose', language)
    
    # Extract merchant name (looking for merchant-related keywords or using the first few lines)
    lines = text.strip().split('\n')
    
    # Try to find merchant by keywords first
    merchant_found = False
    for i, line in enumerate(lines):
        if i >= 10:  # Only check first 10 lines
            break
            
        # Check if any merchant keyword is in this line
        if any(word.lower() in line.lower() for word in merchant_words):
            # Extract the text after the keyword
            for word in merchant_words:
                if word.lower() in line.lower():
                    # Get text after the keyword
                    merchant_text = line[line.lower().find(word.lower()) + len(word):].strip()
                    if merchant_text and len(merchant_text) > 3:
                        result['merchant'] = merchant_text.strip('.: ')
                        merchant_found = True
                        break
            
            if merchant_found:
                break
                
    # If no merchant found by keywords, use the first line approach
    if not merchant_found and lines:
        # Skip empty or very short lines and avoid using total-related terms as merchant name
        total_terms = ['celkem', 'total', 'suma', 'součet', 'gesamt', 'summe', 'montant', 'somme']
        valid_lines = [line for line in lines[:5] if len(line.strip()) > 3 
                       and not re.match(r'^\d+$', line.strip())
                       and not any(term in line.strip().lower() for term in total_terms)]
        if valid_lines:
            # Most often first non-empty line that doesn't look like a date or number
            result['merchant'] = valid_lines[0].strip()
    
    # Get date keywords from user wordlist
    date_words = get_words('date', language)
    
    # Create dynamic date patterns based on user wordlist
    date_patterns = {
        'cs': [r'(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})'],  # Default pattern for Czech: DD.MM.YYYY or DD.MM.YY
        'fr': [r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})'],  # Default pattern for French: DD/MM/YYYY or DD-MM-YYYY 
        'de': [r'(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})']   # Default pattern for German: DD.MM.YYYY
    }
    
    # Add patterns based on user wordlist keywords
    for lang in ['cs', 'fr', 'de']:
        for word in get_words('date', lang):
            if lang == 'fr':
                date_patterns[lang].append(f"{word}:?\\s*(\\d{{1,2}})[/\\-\\.](\\d{{1,2}})[/\\-\\.](\\d{{2,4}})")
            else:
                date_patterns[lang].append(f"{word}:?\\s*(\\d{{1,2}})[\\.](\\d{{1,2}})[\\.](\\d{{2,4}})")
    
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
    
    # Get total and currency keywords from user wordlist
    total_words = get_words('total', language)
    currency_words = get_words('currency', language)
    
    # Create dynamic total patterns based on user wordlist
    total_patterns = {
        'cs': [],
        'fr': [],
        'de': []
    }
    
    # Create currency detection patterns
    currency_patterns = {
        'cs': [r'(?:CZK|Kč|KC|Kc)'],
        'fr': [r'(?:EUR|€)'],
        'de': [r'(?:EUR|€)']
    }
    
    # Add user-defined currency words to patterns
    for lang, words in zip(['cs', 'fr', 'de'], [get_words('currency', 'cs'), get_words('currency', 'fr'), get_words('currency', 'de')]):
        for word in words:
            # Escape special characters in the word
            escaped_word = re.escape(word)
            if not any(escaped_word in pattern for pattern in currency_patterns[lang]):
                currency_patterns[lang].append(escaped_word)
    
    # Join currency patterns with OR operator for each language
    cs_currency = '|'.join(currency_patterns['cs'])
    fr_currency = '|'.join(currency_patterns['fr'])
    de_currency = '|'.join(currency_patterns['de'])
    
    # Add dynamic patterns based on total keywords
    for lang, curr_pattern in zip(['cs', 'fr', 'de'], [cs_currency, fr_currency, de_currency]):
        # Add default pattern for finding totals
        total_patterns[lang].append(r'\s(\d+[.,]\d{2})(?:\s*(?:' + curr_pattern + r'))?$')
        
        # Add patterns based on user-defined keywords
        for word in get_words('total', lang):
            # Clean and escape the keyword for regex
            word_clean = re.escape(word.strip())
            total_patterns[lang].append(
                f"{word_clean}:?\\s*(?:{curr_pattern})?\.?\\s*(\\d+[.,]\\d{{2}})"
            )
            total_patterns[lang].append(
                f"{word_clean}:?\\s*[^\\d]?(\\d+[.,]\\d{{2}})(?:\\s*(?:{curr_pattern}))?"
            )
    
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
                
    # Detect currency - check for currency keywords in text
    if language == 'cs':
        # Default for Czech is CZK
        result['currency'] = 'CZK'
        # Look for EUR symbols in Czech receipts to detect possible EUR currency
        if re.search(r'(?:EUR|€)', text, re.IGNORECASE):
            result['currency'] = 'EUR'
    else:
        # Default for other languages is EUR
        result['currency'] = 'EUR'
        # Look for CZK symbols in non-Czech receipts to detect possible CZK currency
        if re.search(r'(?:CZK|Kč|KC|Kc)', text, re.IGNORECASE):
            result['currency'] = 'CZK'
    
    # Get payment method keywords from wordlist
    payment_words = get_words('payment_method', language)
    
    # Default payment patterns
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
    
    # Add payment method keywords from wordlist
    # Categorize payment methods by keyword analysis
    for word in payment_words:
        word_lower = word.lower()
        # Try to categorize the payment keyword
        if any(cash_word in word_lower for cash_word in ['hotov', 'cash', 'espèce', 'espece', 'bar', 'bargeld']):
            payment_patterns[language]['cash'].append(re.escape(word))
        elif any(card_word in word_lower for card_word in ['kart', 'card', 'carte', 'bank', 'credit', 'debit', 'karte']):
            payment_patterns[language]['card'].append(re.escape(word))
        else:
            payment_patterns[language]['other'].append(re.escape(word))
    
    # Get patterns for the selected language or default to Czech
    patterns = payment_patterns.get(language, payment_patterns['cs'])
    
    # Try each pattern for each payment type
    payment_found = False
    for payment_type, pattern_list in patterns.items():
        if payment_found:
            break
        
        for pattern in pattern_list:
            if re.search(pattern, text, re.IGNORECASE):
                # Always use standardized payment method names for consistent cell mapping
                result['payment_method'] = 'Hotovost' if payment_type == 'cash' else 'Kartou' if payment_type == 'card' else 'Jiné'
                
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
            
    # Try to detect purpose (what the receipt is for) using the purpose wordlist
    purpose_words = get_words('purpose', language)
    purpose_found = False
    
    # Check for special purpose categories (fuel, toll, accommodation)
    fuel_words = get_words('fuel', language)
    toll_words = get_words('toll', language)
    accommodation_words = get_words('accommodation', language)
    
    # Check for fuel-related keywords
    for keyword in fuel_words:
        if keyword.lower() in text.lower():
            result['purpose'] = 'Pohonné hmoty'
            purpose_found = True
            break
    
    # Check for toll-related keywords if no fuel match
    if not purpose_found:
        for keyword in toll_words:
            if keyword.lower() in text.lower():
                result['purpose'] = 'Mýtné'
                purpose_found = True
                break
    
    # Check for accommodation-related keywords if no fuel or toll match
    if not purpose_found:
        for keyword in accommodation_words:
            if keyword.lower() in text.lower():
                result['purpose'] = 'Bydlení'
                purpose_found = True
                break
    
    # If not found yet, try with user wordlist
    if not purpose_found:
        for word in purpose_words:
            if word.lower() in text.lower():
                # Find the line containing this word
                lines = text.lower().split('\n')
                for line in lines:
                    if word.lower() in line:
                        # Extract the text around the keyword
                        start_idx = line.find(word.lower())
                        # Get text after the keyword, limiting to 30 chars
                        purpose_text = line[start_idx:].strip()
                        if len(purpose_text) > 5:  # If we found something meaningful
                            result['purpose'] = purpose_text.capitalize()
                            purpose_found = True
                            break
                if purpose_found:
                    break
    
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
