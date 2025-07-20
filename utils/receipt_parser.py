"""
Parser pro extrakci informací z účtenek
Extrahuje relevantní informace z OCR textu účtenky
"""

import re
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List, Tuple
from utils.word_lists import get_words
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurace pro regulární výrazy
PATTERNS = {
    'date': {
        'cs': r'(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})',
        'fr': r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',
        'de': r'(\d{1,2})[\.,](\d{1,2})[\.,](\d{2,4})'
    },
    'amount': {
        'cs': r'(?:CELKEM|TOTAL|TOTAAL|SUMA)[\s:]*[€]?\s*(\d+[.,]\d{2})',
        'fr': r'(?:TOTAL|TOTAAL|SOMME)[\s:]*[€]?\s*(\d+[.,]\d{2})',
        'de': r'(?:GESAMT|TOTAL|SUMME)[\s:]*[€]?\s*(\d+[.,]\d{2})'
    },
    'receipt_number': {
        'cs': r'(?:č\.|číslo|čís\.)\s*:?\s*(\d+)',
        'fr': r'(?:n°|no\.|num\.)\s*:?\s*(\d+)',
        'de': r'(?:nr\.|nummer)\s*:?\s*(\d+)'
    }
}

@lru_cache(maxsize=128)
def compile_pattern(pattern: str) -> re.Pattern:
    """
    Kompiluje a cachuje regulární výraz.
    
    Args:
        pattern: Vzorek regulárního výrazu
        
    Returns:
        Kompilovaný regulární výraz
    """
    return re.compile(pattern, re.IGNORECASE)

def detect_language(text: str) -> str:
    """
    Detekuje jazyk textu účtenky.
    
    Args:
        text: OCR extrahovaný text z účtenky
        
    Returns:
        Detekovaný jazykový kód ('cs', 'fr', 'de')
    """
    try:
        # Počítadlo skóre pro každý jazyk
        scores = {'cs': 0, 'fr': 0, 'de': 0}
        
        # Získání seznamů slov pro každé pole a jazyk
        fields = ['date', 'total', 'payment_method', 'merchant', 'currency']
        
        # Počítání shod pro každý jazyk
        for field in fields:
            for lang in scores.keys():
                words = get_words(field, lang)
                for word in words:
                    if word.lower() in text.lower():
                        scores[lang] += 1

        # Dodatečné jazykově specifické vzory
        patterns = {
            'cs': [
                (r'č\.|číslo|kč|částka|celkem|dph', 2),
                (r'[áčďéěíňóřšťúůýž]', 2)
            ],
            'fr': [
                (r'n°|tva|ttc|eur|montant|total|prix', 2),
                (r'[àâçèéêëîïôûùü]', 2)
            ],
            'de': [
                (r'nr\.|summe|gesamt|eur|preis|danke', 2),
                (r'[äöüß]', 2)
            ]
        }
        
        # Aplikace vzorů pro každý jazyk
        for lang, lang_patterns in patterns.items():
            for pattern, score in lang_patterns:
                if re.search(pattern, text.lower()):
                    scores[lang] += score

        # Získání jazyku s nejvyšším skóre
        max_score = max(scores.values())
        if max_score == 0:
            logger.warning("Nepodařilo se detekovat jazyk, používá se výchozí čeština")
            return 'cs'
        
        for lang, score in scores.items():
            if score == max_score:
                logger.info(f"Detekovaný jazyk: {lang}")
                return lang
                
    except Exception as e:
        logger.error(f"Chyba při detekci jazyka: {str(e)}")
        return 'cs'

def extract_receipt_info(text: str, language: str = 'cs') -> Dict[str, Any]:
    """
    Extrahuje relevantní informace z textu účtenky.
    
    Args:
        text: OCR extrahovaný text z účtenky
        language: Jazykový kód ('cs', 'fr', 'de')
        
    Returns:
        Slovník s extrahovanými informacemi
    """
    try:
        # Detekce jazyka pokud není specifikován
        detected_language = detect_language(text)
        
        logger.info(f"Extrahuji informace z účtenky v jazyce: {detected_language}")

        # Inicializace výsledného slovníku s výchozími hodnotami
        result = {
            'merchant': '',
            'date': datetime.now(),
            'total': 0.0,
            'payment_method': '',
            'receipt_number': '',
            'currency': 'CZK' if detected_language == 'cs' else 'EUR',
            'purpose': '',
            'specific_data': {}
        }

        # Zpracování podle detekovaného jazyka
        receipt_type = determine_receipt_type(text, detected_language)
        result['purpose'] = receipt_type

        result['merchant'] = extract_merchant(text, detected_language)
        
        date_result = extract_date(text, detected_language)
        if date_result:
            result['date'] = date_result
            
        total_result = extract_total_amount(text, detected_language)
        if total_result:
            result['total'] = total_result
            
        result['currency'] = detect_currency(text, detected_language)
        result['payment_method'] = extract_payment_method(text, detected_language)
        
        receipt_num = extract_receipt_number(text, detected_language)
        if receipt_num:
            result['receipt_number'] = receipt_num

        if receipt_type == 'Pohonné hmoty':
            result['specific_data'] = extract_fuel_data(text, detected_language)
        elif receipt_type == 'Mýtné':
            result['specific_data'] = extract_toll_data(text, detected_language)

        return result
        
    except Exception as e:
        logger.error(f"Chyba při extrakci informací z účtenky: {str(e)}")
        return {
            'merchant': '',
            'date': datetime.now(),
            'total': 0.0,
            'payment_method': '',
            'receipt_number': '',
            'currency': 'CZK',
            'purpose': 'Ostatní',
            'specific_data': {}
        }

from utils.word_lists import get_words, get_all_fields

def determine_receipt_type(text: str, language: str) -> str:
    """
    Určuje typ účtenky na základě obsahu textu.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Typ účtenky ('Pohonné hmoty', 'Mýtné', 'Ubytování', 'Ostatní')
    """
    try:
        # Získání všech dostupných kategorií
        all_categories = get_all_fields()
        
        # Iterace přes všechny kategorie a hledání klíčových slov
        for category in all_categories:
            # Přeskočení obecných polí, které nejsou kategoriemi
            if category in ['date', 'total', 'currency', 'payment_method', 'merchant', 'purpose']:
                continue

            words = get_words(category, language)
            for keyword in words:
                if keyword.lower() in text.lower():
                    # Zde by mohla být dodatečná verifikace pro konkrétní kategorie
                    return category.replace('_', ' ').capitalize()
        
        return 'Ostatní'
        
    except Exception as e:
        logger.error(f"Chyba při určování typu účtenky: {str(e)}")
        return 'Ostatní'

def extract_merchant(text: str, language: str) -> str:
    """
    Extrahuje název obchodníka z textu účtenky.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Název obchodníka
    """
    try:
        lines = text.strip().split('\n')
        
        # Známí obchodníci s více variacemi
        known_merchants = {
            'AVIA': r'AVIA\s*(?:SELF)*\s*(?:SERVICE)*',
            'GULF': r'GULF\s*(?:OIL)*\s*(?:STATION)*',
            'OMV': r'OMV\s*(?:TANK)*\s*(?:STATION)*',
            'TOTALENERGIES': r'TOTAL(?:\s*ENERGIES)*',
            'SHELL': r'SHELL\s*(?:STATION)*',
            'MOL': r'MOL\s*(?:STATION)*',
            'ORLEN': r'ORLEN\s*(?:BENZINA)*',
            'BENZINA': r'BENZINA\s*(?:PLUS)*',
            'SANEF': r'SANEF\s*(?:PEAGE)*',
            'COFIROUTE': r'COFIROUTE\s*(?:AUTOROUTE)*',
            'VINCI': r'VINCI\s*(?:AUTOROUTES)*'
        }
        
        for name, pattern in known_merchants.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        # Generický přístup: hledání prvního řádku, který není adresa, datum nebo čas
        for line in lines[:5]:  # Omezení na prvních 5 řádků
            line = line.strip()
            if len(line) > 3 and not re.search(r'\d{2}[/\.]\d{2}[/\.]\d{4}', line):
                # Vyloučení řádků, které vypadají jako adresa nebo jiné nepodstatné informace
                if not any(keyword in line.lower() for keyword in ['ulice', 'street', 'tel', 'www', 'email']):
                    return line
        
        return ''
        
    except Exception as e:
        logger.error(f"Chyba při extrakci obchodníka: {str(e)}")
        return ''

def extract_date(text: str, language: str) -> Optional[datetime]:
    """
    Extrahuje datum z textu účtenky.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Datum nebo None pokud není nalezeno
    """
    try:
        # Rozšířené vzory pro různé formáty data
        date_patterns = [
            r'(\d{1,2})[\.,/](\d{1,2})[\.,/](\d{2,4})',  # dd.mm.yyyy, dd/mm/yy
            r'(\d{4})-(\d{2})-(\d{2})'  # yyyy-mm-dd
        ]
        
        for pattern in date_patterns:
            date_matches = re.search(pattern, text, re.IGNORECASE)
            if date_matches:
                parts = date_matches.groups()
                
                # Sjednocení formátu na (den, měsíc, rok)
                if pattern == r'(\d{4})-(\d{2})-(\d{2})':
                    year, month, day = parts
                else:
                    day, month, year = parts

                # Zpracování dvouciferného roku
                if len(year) == 2:
                    year = '20' + year

                try:
                    # Validace hodnot data
                    day_val, month_val, year_val = int(day), int(month), int(year)

                    if 1 <= day_val <= 31 and 1 <= month_val <= 12 and 2000 <= year_val <= 2030:
                        return datetime(year_val, month_val, day_val)
                except ValueError:
                    continue  # Pokračujeme k dalšímu vzoru

        return None
        
    except Exception as e:
        logger.error(f"Chyba při extrakci data: {str(e)}")
        return None

def extract_total_amount(text: str, language: str) -> Optional[float]:
    """
    Extrahuje celkovou částku z textu účtenky.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Celková částka nebo None pokud není nalezena
    """
    try:
        # Vylepšené regulární výrazy pro hledání klíčových slov a částek
        total_keywords = get_words('total', language)
        amount_pattern = r'(\d+[.,]\d{2})'
        
        lines = text.split('\n')
        potential_amounts = []

        # Hledání řádků s klíčovými slovy a extrakce čísel
        for line in lines:
            # Převod na malá písmena pro porovnání bez rozlišení velikosti
            line_lower = line.lower()

            # Kontrola, zda řádek obsahuje klíčové slovo
            if any(keyword.lower() in line_lower for keyword in total_keywords):
                # Extrakce všech čísel z řádku
                numbers = re.findall(amount_pattern, line)
                if numbers:
                    # Přidání poslední nalezené částky (obvykle celková)
                    potential_amounts.append(float(numbers[-1].replace(',', '.')))

        # Pokud byly nalezeny potenciální částky, vrátíme nejvyšší
        if potential_amounts:
            return max(potential_amounts)

        # Fallback: pokud nebyla nalezena klíčová slova, hledáme největší částku v celém textu
        all_numbers = re.findall(amount_pattern, text)
        if all_numbers:
            # Převedeme všechny nalezené řetězce na čísla
            all_amounts = [float(num.replace(',', '.')) for num in all_numbers]
            # Vrátíme nejvyšší hodnotu, která je pravděpodobně celkovou částkou
            return max(all_amounts)

        return None

    except Exception as e:
        logger.error(f"Chyba při extrakci částky: {str(e)}")
        return None

def extract_payment_method(text: str, language: str) -> str:
    """
    Extrahuje způsob platby z textu účtenky.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Způsob platby ('Kartou' nebo 'Hotovost')
    """
    try:
        payment_words = get_words('payment_method', language)
        
        # Kontrola klíčových slov pro platbu kartou
        card_words = ['karta', 'kartou', 'card', 'carte', 'karte']
        if any(word.lower() in text.lower() for word in card_words):
            return 'Kartou'
            
        # Kontrola klíčových slov pro hotovostní platbu
        cash_words = ['hotovost', 'cash', 'espèces', 'bargeld']
        if any(word.lower() in text.lower() for word in cash_words):
            return 'Hotovost'
            
        # Výchozí hodnota
        return 'Hotovost'
        
    except Exception as e:
        logger.error(f"Chyba při extrakci způsobu platby: {str(e)}")
        return 'Hotovost'

def extract_receipt_number(text: str, language: str) -> Optional[str]:
    """
    Extrahuje číslo účtenky z textu.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Číslo účtenky nebo None pokud není nalezeno
    """
    try:
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if "číslo účtenky" in line.lower():
                # Extract the text after the colon
                parts = line.split(':')
                if len(parts) > 1:
                    return parts[1].strip()
        return None
        
    except Exception as e:
        logger.error(f"Chyba při extrakci čísla účtenky: {str(e)}")
        return None

def extract_fuel_data(text: str, language: str) -> Dict[str, Any]:
    """
    Extrahuje specifická data z účtenky za pohonné hmoty.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Slovník s extrahovanými daty
    """
    try:
        result = {
            'fuel_type': '',
            'quantity': 0.0,
            'price_per_liter': 0.0,
            'location': ''
        }
        
        # Extrakce typu paliva
        fuel_types = {
            'cs': ['benzín', 'diesel', 'nafta', 'lpg'],
            'fr': ['essence', 'diesel', 'gazole', 'gpl'],
            'de': ['benzin', 'diesel', 'kraftstoff', 'lpg']
        }
        
        for fuel_type in fuel_types.get(language, fuel_types['cs']):
            if fuel_type.lower() in text.lower():
                result['fuel_type'] = fuel_type
                break
                
        # Extrakce množství
        quantity_pattern = r'(\d+[.,]\d+)\s*[lL]'
        quantity_match = re.search(quantity_pattern, text, re.IGNORECASE)
        if quantity_match:
            try:
                result['quantity'] = float(quantity_match.group(1).replace(',', '.'))
            except ValueError:
                logger.warning("Nepodařilo se extrahovat množství paliva")
                
        # Extrakce ceny za litr
        price_pattern = r'(\d+[.,]\d+)\s*(?:Kč|CZK|€|EUR)\s*/\s*[lL]'
        price_match = re.search(price_pattern, text, re.IGNORECASE)
        if price_match:
            try:
                result['price_per_liter'] = float(price_match.group(1).replace(',', '.'))
            except ValueError:
                logger.warning("Nepodařilo se extrahovat cenu za litr")
                
        return result
        
    except Exception as e:
        logger.error(f"Chyba při extrakci dat o pohonných hmotách: {str(e)}")
        return {
            'fuel_type': '',
            'quantity': 0.0,
            'price_per_liter': 0.0,
            'location': ''
        }

def extract_toll_data(text: str, language: str) -> Dict[str, Any]:
    """
    Extrahuje specifická data z mýtné účtenky.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Slovník s extrahovanými daty
    """
    try:
        result = {
            'entry_point': '',
            'exit_point': '',
            'distance': 0.0,
            'vehicle_type': ''
        }
        
        # Extrakce vstupního a výstupního bodu
        entry_patterns = {
            'cs': r'vstup|nástup',
            'fr': r'entrée|entree',
            'de': r'einfahrt|eingang'
        }
        
        exit_patterns = {
            'cs': r'výstup|sjezd',
            'fr': r'sortie|sortie',
            'de': r'ausfahrt|ausgang'
        }
        
        # Hledání vstupního bodu
        entry_match = re.search(entry_patterns.get(language, entry_patterns['cs']), text, re.IGNORECASE)
        if entry_match:
            # Extrakce textu po vstupním bodě
            entry_text = text[entry_match.end():].split('\n')[0].strip()
            result['entry_point'] = entry_text
            
        # Hledání výstupního bodu
        exit_match = re.search(exit_patterns.get(language, exit_patterns['cs']), text, re.IGNORECASE)
        if exit_match:
            # Extrakce textu po výstupním bodě
            exit_text = text[exit_match.end():].split('\n')[0].strip()
            result['exit_point'] = exit_text
            
        # Extrakce vzdálenosti
        distance_pattern = r'(\d+[.,]?\d*)\s*(?:km|kilomètres|kilometer)'
        distance_match = re.search(distance_pattern, text, re.IGNORECASE)
        if distance_match:
            try:
                result['distance'] = float(distance_match.group(1).replace(',', '.'))
            except ValueError:
                logger.warning("Nepodařilo se extrahovat vzdálenost")
                
        return result
        
    except Exception as e:
        logger.error(f"Chyba při extrakci dat o mýtném: {str(e)}")
        return {
            'entry_point': '',
            'exit_point': '',
            'distance': 0.0,
            'vehicle_type': ''
        }

def detect_currency(text: str, language: str) -> str:
    """
    Detekuje měnu z textu účtenky.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Detekovaná měna ('EUR' nebo 'CZK')
    """
    try:
        # Kontrola EUR
        if re.search(r'€|EUR|euro', text, re.IGNORECASE):
            return 'EUR'
            
        # Kontrola CZK
        if re.search(r'Kč|CZK|koruna', text, re.IGNORECASE):
            return 'CZK'
            
        # Výchozí hodnota podle jazyka
        return 'EUR' if language in ['fr', 'de'] else 'CZK'
        
    except Exception as e:
        logger.error(f"Chyba při detekci měny: {str(e)}")
        return 'CZK'
