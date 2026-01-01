"""
Parser pro extrakci informací z účtenek
Extrahuje relevantní informace z OCR textu účtenky
"""

import re
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List, Tuple
from utils.word_lists import get_words, get_all_fields
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
        'cs': r'(?:č\.|číslo\s*účtenky|čís\.)\s*:?\s*([A-Za-z0-9]+)',
        'fr': r'(?:n°|no\.|num\.)\s*:?\s*([A-Za-z0-9]+)',
        'de': r'(?:nr\.|nummer)\s*:?\s*([A-Za-z0-9]+)'
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
                (r'n°|tva|ttc|eur|montant|prix|autoroutes|paiement|carte|sortie|entrée|entree|euros|€', 2),
                (r'carte\s+bancaire', 3),
                (r'montant\s+net', 2),
                (r'station\s+avia', 2),
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
                    # Return the first keyword, which is the localized name
                    return words[0].capitalize()
        
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
        
        # Rozšířený seznam známých obchodníků s více variacemi
        known_merchants = {
            # Pohonné hmoty
            'AVIA': r'AVIA\s*(?:SELF)*\s*(?:SERVICE)*',
            'GULF': r'GULF\s*(?:OIL)*\s*(?:STATION)*',
            'OMV': r'OMV\s*(?:TANK)*\s*(?:STATION)*',
            'TOTALENERGIES': r'TOTAL(?:\s*ENERGIES)*\s*(?:STATION|STANICE)*',
            'SHELL': r'SHELL\s*(?:STATION)*',
            'MOL': r'MOL\s*(?:STATION)*',
            'ORLEN': r'ORLEN\s*(?:BENZINA)*',
            'BENZINA': r'BENZINA\s*(?:PLUS)*',
            # Dálnice a mýtné
            'SANEF': r'SANEF\s*(?:PEAGE)*',
            'COFIROUTE': r'COFIROUTE\s*(?:AUTOROUTE)*',
            'VINCI': r'VINCI\s*(?:AUTOROUTES)*',
            'COFIROUTE': r'COFIROUTE',
            # Supermarkety
            'ALBERT': r'ALBERT\s*(?:SUPERMARKET|HYPERMARKET)*',
            'BILLA': r'BILLA',
            'LIDL': r'LIDL',
            'KAUFLAND': r'KAUFLAND',
            'TESCO': r'TESCO\s*(?:STORES|EXPRESS)*',
            'PENNY': r'PENNY\s*(?:MARKET)*',
            'HUBO': r'HUBO\s*(?:EUPEN)*'
        }
        
        for name, pattern in known_merchants.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        normalized = re.sub(r'[^A-Z]', '', text.upper())
        if 'AVIA' in normalized:
            return 'AVIA'

        try:
            import difflib
            top_lines = [l.strip() for l in lines[:8] if l.strip()]
            tokens = []
            for li, l in enumerate(top_lines):
                for t in re.findall(r'[A-Z]{3,12}', l.upper()):
                    tokens.append((t, li))
            brand_keys = list(known_merchants.keys())
            best = ('', -1.0, 99)
            for token, li in tokens:
                for bk in brand_keys:
                    r = difflib.SequenceMatcher(None, token, bk).ratio()
                    score = r - (li * 0.02)
                    if score > best[1]:
                        best = (bk, score, li)
            if best[0] and best[1] >= 0.7:
                return best[0]
            if re.search(r'a\s*v\s*i\s*a', '\n'.join(top_lines).lower()):
                return 'AVIA'
        except Exception:
            pass

        # Vylepšený generický přístup
        potential_merchants = []
        for line in lines[:5]:
            line = line.strip()
            if len(line) < 3 or len(line) > 50:
                continue
            if re.fullmatch(r'\d{3,}', line):
                continue

            # Kontrola, zda řádek neobsahuje typické údaje, které nejsou obchodník
            if any(keyword in line.lower() for keyword in [
                'ulice', 'street', 'tel', 'www', 'email', 'datum', 'čas', 'číslo',
                'pokladna', 'kasir', 'dph', 'ičo', 'dič'
            ]):
                continue

            # Kontrola, zda řádek neobsahuje formát data
            if re.search(r'\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4}', line):
                continue

            # Přidání váhy řádku na základě charakteristik
            score = 0
            # Větší váha pro řádky psané velkými písmeny (časté pro název firmy)
            if line.isupper() and ' ' in line:
                score += 3
            # Váha pro přítomnost právní formy
            if re.search(r'\b(s\.r\.o|a\.s|SE|v\.o\.s)\b', line, re.IGNORECASE):
                score += 5

            # Základní skóre za to, že je to kandidát
            score += 1
            potential_merchants.append((line, score))

        # Vrácení obchodníka s nejvyšším skóre
        if potential_merchants:
            best_merchant = max(potential_merchants, key=lambda item: item[1])
            return best_merchant[0]

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
            r'(\d{4})-(\d{2})-(\d{2})',  # yyyy-mm-dd (prioritní)
            r'(\d{1,2})[\.,/\-](\d{1,2})[\.,/\-](\d{2,4})'  # dd.mm.yyyy, dd/mm/yy, dd-mm-yy
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
        total_keywords = get_words('total', language)
        extra_keywords = [
            'ttc', 't.t.c', 'prix ttc', 'tarif ttc', 'tarif t.t.c',
            'payé', 'paye', 'montant reel', 'montant réel',
            'montant net', 'net a payer', 'net à payer', 'montant total', 'total'
        ]
        # Regex pro částky, který zvládá mezery jako oddělovače tisíců a různé desetinné oddělovače
        amount_pattern = r'((?:\d{1,3}(?:\s\d{3})*|\d+)[,.]\d{2})'
        
        lines = text.split('\n')
        eur_pat = r'(€|e\s*u\s*r|euros?)'
        potential_amounts = []

        # Preferenční zachycení finálních částek na typických FR řádcích
        for line in lines:
            m = re.search(r'(montant\s+net|net\s+a\s+payer|net\s+à\s+payer|montant\s+total|total)\s*[:\-]?\s*((?:\d{1,3}(?:\s\d{3})*|\d+)[,.]\d{2})\s*' + eur_pat + '?', line, re.IGNORECASE)
            if m:
                return float(m.group(2).replace(' ', '').replace(',', '.'))

        # Hledání řádků s klíčovými slovy a extrakce čísel
        for line in lines:
            line_lower = line.lower()
            if any(keyword.lower() in line_lower for keyword in total_keywords + extra_keywords):
                # Vyhnout se řádkům s procenty bez měny (např. 'TVA 20,00%')
                if '%' in line_lower and ('€' not in line_lower and 'eur' not in line_lower and 'kč' not in line_lower):
                    continue
                # Vyhnout se řádkům typickým pro položky paliva (množství v litrech, jednotková cena)
                if re.search(r'\b(?:l|litre|litres)\b', line_lower) or 'prix unit' in line_lower or 'price/l' in line_lower or 'cena/l' in line_lower:
                    continue
                numbers = re.findall(amount_pattern, line)
                if numbers:
                    # Pokud jsou na řádku nalezena čísla, vezmeme nejvyšší
                    line_amounts = [float(num.replace(' ', '').replace(',', '.')) for num in numbers]
                    if line_amounts:
                        potential_amounts.append(max(line_amounts))

        # Pokud byly nalezeny částky na řádcích s klíčovými slovy, vrátíme tu nejvyšší z nich
        if potential_amounts:
            return max(potential_amounts)

        # Vylepšený fallback: nejprve z posledních 8 řádků s měnou, pokud nic, tak z posledních 8 řádků obecně
        last_lines = lines[-8:]
        amounts_with_currency = []
        amounts_any = []
        eur_pat = r'(€|e\s*u\s*r|euros?)'
        czk_pat = r'(k\s*č|c\s*z\s*k|czk|korun[a-y]?)'
        for line in last_lines:
            # ignoruj čisté procentní řádky bez měny (např. 'TVA 20,00%')
            if '%' in line.lower() and not re.search(f'{eur_pat}|{czk_pat}', line, re.IGNORECASE):
                continue
            # ignoruj řádky typické pro položky paliva
            if re.search(r'\b(?:l|litre|litres)\b', line.lower()) or 'prix unit' in line.lower() or 'price/l' in line.lower() or 'cena/l' in line.lower():
                continue
            numbers = re.findall(amount_pattern, line)
            if numbers:
                parsed = [float(num.replace(' ', '').replace(',', '.')) for num in numbers]
                if re.search(f'{eur_pat}|{czk_pat}', line, re.IGNORECASE):
                    amounts_with_currency.extend(parsed)
                else:
                    amounts_any.extend(parsed)

        if amounts_with_currency:
            return max(amounts_with_currency)
        if amounts_any:
            return max(amounts_any)

        return None

    except Exception as e:
        logger.error(f"Chyba při extrakci částky: {str(e)}")
        return None

def extract_payment_method(text: str, language: str) -> str:
    """
    Extrahuje způsob platby z textu účtenky s vyšší přesností.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Způsob platby ('Kartou', 'Hotovost', nebo 'Neznámý')
    """
    try:
        # Prohledáváme jen posledních 10 řádků, kde se info o platbě obvykle nachází
        lines = text.lower().strip().split('\n')
        search_text = "\n".join(lines[-10:])

        # Rozšířený seznam klíčových slov pro platbu kartou
        card_keywords = [
            'karta', 'kartou', 'card', 'carte', 'karte', 'kreditkarte',
            'visa', 'mastercard', 'maestro', 'ec/mc', 'plat. kartou', 'cb'
        ]
        
        # Rozšířený seznam klíčových slov pro hotovostní platbu
        cash_keywords = [
            'hotovost', 'hotově', 'cash', 'espèces', 'bargeld', 'bar', 'zaplaceno hotově'
        ]

        # Kontrola klíčových slov
        if any(keyword in search_text for keyword in card_keywords):
            return 'Kartou'
            
        if any(keyword in search_text for keyword in cash_keywords):
            return 'Hotovost'
            
        # Pokud nic nenalezeno, vrátíme 'Neznámý'
        return 'Neznámý'
        
    except Exception as e:
        logger.error(f"Chyba při extrakci způsobu platby: {str(e)}")
        return 'Neznámý'

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
        pattern = PATTERNS['receipt_number'].get(language, PATTERNS['receipt_number']['cs'])
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1)
        alt_patterns = [
            r'no\.?\s*[:]?\s*([A-Za-z0-9]+)',
            r'n°\s*[:]?\s*([A-Za-z0-9]+)',
            r'num[eé]ro\s*[:]?\s*([A-Za-z0-9]+)',
            r'no\.\s*ticket\s*[:]?\s*([A-Za-z0-9]+)'
        ]
        for p in alt_patterns:
            mm = re.search(p, text, re.IGNORECASE)
            if mm:
                return mm.group(1)
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
                
        # Extrakce ceny za litr - vylepšená logika
        for line in text.split('\n'):
            # Hledání klíčových slov pro cenu za litr
            if any(keyword in line.lower() for keyword in ['cena/l', 'price/l', 'prix/l', 'prix unit']):
                price_match = re.search(r'(\d+[.,]\d+)', line)
                if price_match:
                    try:
                        result['price_per_liter'] = float(price_match.group(1).replace(',', '.'))
                        break  # Nalezeno, přerušit smyčku
                    except ValueError:
                        logger.warning("Nepodařilo se extrahovat cenu za litr z řádku: " + line)

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
            entry_text = text[entry_match.end():].split('\n')[0].strip().lstrip(':').strip()
            result['entry_point'] = entry_text
            
        # Hledání výstupního bodu
        exit_match = re.search(exit_patterns.get(language, exit_patterns['cs']), text, re.IGNORECASE)
        if exit_match:
            # Extrakce textu po výstupním bodě
            exit_text = text[exit_match.end():].split('\n')[0].strip().lstrip(':').strip()
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
    Detekuje měnu z textu účtenky s prioritou na řádcích s celkovou částkou.
    
    Args:
        text: Text účtenky
        language: Jazykový kód
        
    Returns:
        Detekovaná měna ('EUR', 'CZK')
    """
    try:
        # Nejvyšší priorita: měna na řádku s celkovou částkou
        lines = text.lower().strip().split('\n')
        total_keywords = get_words('total', language)
        extended_total_keywords = [
            'celkem', 'k úhradě', 'total', 'montant total', 'montant net',
            'net a payer', 'net à payer', 'tarif ttc', 'prix ttc', 'summe', 'gesamt'
        ]
        eur_pat = r'(€|e\s*u\s*r|euros?)'
        czk_pat = r'(k\s*č|c\s*z\s*k|czk|korun[a-y]?)'
        search_keys = set([w.lower() for w in total_keywords] + extended_total_keywords)
        for line in lines:
            if any(key in line for key in search_keys):
                if re.search(eur_pat, line, re.IGNORECASE):
                    return 'EUR'
                if re.search(czk_pat, line, re.IGNORECASE):
                    return 'CZK'

        # Fallback: globální hledání v celém textu
        if re.search(eur_pat, text, re.IGNORECASE):
            return 'EUR'
        if re.search(czk_pat, text, re.IGNORECASE):
            return 'CZK'

        # Výchozí hodnota podle jazyka
        return 'EUR' if language in ['fr', 'de'] else 'CZK'
        
    except Exception as e:
        logger.error(f"Chyba při detekci měny: {str(e)}")
        return 'CZK' if language != 'fr' and language != 'de' else 'EUR'
