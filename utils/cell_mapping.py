"""
Cell mapping utility for receipt data
Maps combinations of purpose, currency, and payment method to specific Excel cells
"""

from typing import Dict, Tuple, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Define cell ranges for different combinations
CELL_MAPPINGS: Dict[Tuple[str, str, str], Tuple[str, str]] = {
    ('Pohonné hmoty', 'EUR', 'Kartou'): ('B12', 'B19'),
    ('Pohonné hmoty', 'EUR', 'Hotovost'): ('C12', 'C19'),
    ('Pohonné hmoty', 'CZK', 'Kartou'): ('D12', 'D19'),
    ('Pohonné hmoty', 'CZK', 'Hotovost'): ('E12', 'E19'),
    
    ('Mýtné', 'EUR', 'Kartou'): ('B20', 'B26'),
    ('Mýtné', 'EUR', 'Hotovost'): ('C20', 'C26'),
    ('Mýtné', 'CZK', 'Kartou'): ('D20', 'D26'),
    ('Mýtné', 'CZK', 'Hotovost'): ('E20', 'E26'),
    
    # OPRAVA: Změněno z "Bydlení" na "Ubytování"
    ('Ubytování', 'EUR', 'Kartou'): ('B27', 'B31'),
    ('Ubytování', 'EUR', 'Hotovost'): ('C27', 'C31'),
    ('Ubytování', 'CZK', 'Kartou'): ('D27', 'D31'),
    ('Ubytování', 'CZK', 'Hotovost'): ('E27', 'E31'),
    
    ('Ostatní', 'EUR', 'Kartou'): ('B32', 'B39'),
    ('Ostatní', 'EUR', 'Hotovost'): ('C32', 'C39'),
    ('Ostatní', 'CZK', 'Kartou'): ('D32', 'D39'),
    ('Ostatní', 'CZK', 'Hotovost'): ('E32', 'E39'),
}

def standardize_purpose(purpose: str) -> str:
    """
    Standardizuje účel výdaje.
    
    Args:
        purpose: Původní účel výdaje
        
    Returns:
        Standardizovaný účel výdaje
    """
    if not purpose:
        return 'Ostatní'
    
    purpose_lower = purpose.lower().strip()
    
    # Mapování variant na standardní názvy
    if purpose_lower in ['pohonné hmoty', 'palivo', 'fuel', 'phm', 'benzin', 'nafta', 'diesel']:
        return 'Pohonné hmoty'
    elif purpose_lower in ['mýtné', 'mýto', 'toll', 'péage', 'maut']:
        return 'Mýtné'
    elif purpose_lower in ['ubytování', 'accommodation', 'hotel', 'hébergement', 'unterkunft', 'bydlení']:
        return 'Ubytování'
    elif purpose_lower in ['stravování', 'food', 'restauration', 'verpflegung']:
        return 'Stravování'
    
    return 'Ostatní'

def standardize_payment_method(payment_method: str) -> str:
    """
    Standardizuje způsob platby.
    
    Args:
        payment_method: Původní způsob platby
        
    Returns:
        Standardizovaný způsob platby
    """
    if not payment_method:
        return 'Hotovost'
    
    payment_method_lower = payment_method.lower().strip()
    
    if payment_method_lower in ['karta', 'kartou', 'card', 'carte', 'karte', 'visa', 'mastercard']:
        return 'Kartou'
    elif payment_method_lower in ['hotovost', 'hotově', 'cash', 'espèces', 'bargeld', 'bar']:
        return 'Hotovost'
    
    # Default na Hotovost pokud není rozpoznáno
    return 'Hotovost'

def standardize_currency(currency: str) -> str:
    """
    Standardizuje měnu.
    
    Args:
        currency: Původní měna
        
    Returns:
        Standardizovaná měna
    """
    if not currency:
        return 'CZK'
    
    currency_upper = currency.upper().strip()
    return 'EUR' if currency_upper in ['EUR', 'EURO', '€'] else 'CZK'

def get_cell_range(purpose: str, currency: str, payment_method: str) -> Optional[Tuple[str, str]]:
    """
    Získá odpovídající rozsah buněk na základě účelu, měny a způsobu platby.
    
    Args:
        purpose: Účel výdaje
        currency: Měna
        payment_method: Způsob platby
    
    Returns:
        Tuple obsahující (počáteční_buňka, koncová_buňka) nebo None pokud není nalezena shoda
    """
    try:
        # Standardizace vstupů
        std_purpose = standardize_purpose(purpose)
        std_currency = standardize_currency(currency)
        std_payment = standardize_payment_method(payment_method)
        
        logger.info(f"Standardizováno: účel='{std_purpose}', měna='{std_currency}', platba='{std_payment}'")
        
        # Získání rozsahu buněk
        cell_range = CELL_MAPPINGS.get((std_purpose, std_currency, std_payment))
        
        if cell_range is None:
            logger.warning(f"Nenalezen rozsah buněk pro kombinaci: {std_purpose}, {std_currency}, {std_payment}")
            return None
            
        return cell_range
        
    except Exception as e:
        logger.error(f"Chyba při získávání rozsahu buněk: {str(e)}")
        return None

def find_next_empty_cell(worksheet, cell_range: Optional[Tuple[str, str]]) -> Optional[str]:
    """
    Najde další prázdnou buňku v daném rozsahu.
    
    Args:
        worksheet: Excel worksheet objekt
        cell_range: Tuple obsahující (počáteční_buňka, koncová_buňka)
    
    Returns:
        Reference na buňku (např. 'B12') nebo None pokud jsou všechny buňky zaplněny
    """
    if not cell_range:
        logger.warning("Nebyl poskytnut žádný rozsah buněk")
        return None
    
    try:
        start_cell, end_cell = cell_range
        
        # Extrakce sloupce a řádku z počáteční a koncové buňky
        start_col = start_cell[0]
        start_row = int(start_cell[1:])
        end_row = int(end_cell[1:])
        
        # Validace rozsahu
        if start_row > end_row:
            logger.warning(f"Neplatný rozsah buněk {start_cell}:{end_cell}, počáteční řádek > koncový řádek")
            return None
        
        # Kontrola každé buňky v rozsahu
        for row in range(start_row, end_row + 1):
            cell = f"{start_col}{row}"
            try:
                if worksheet[cell].value is None:
                    logger.info(f"Nalezena prázdná buňka: {cell}")
                    return cell
            except Exception as e:
                logger.error(f"Chyba při kontrole buňky {cell}: {str(e)}")
                continue
        
        # Všechny buňky jsou zaplněny
        logger.warning(f"Všechny buňky v rozsahu {start_cell}:{end_cell} jsou zaplněny")
        return None
        
    except Exception as e:
        logger.error(f"Chyba při hledání prázdné buňky: {str(e)}")
        return None
