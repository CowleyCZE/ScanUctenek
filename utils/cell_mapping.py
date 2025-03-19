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
    
    ('Bydlení', 'EUR', 'Kartou'): ('B27', 'B31'),
    ('Bydlení', 'EUR', 'Hotovost'): ('C27', 'C31'),
    ('Bydlení', 'CZK', 'Kartou'): ('D27', 'D31'),
    ('Bydlení', 'CZK', 'Hotovost'): ('E27', 'E31'),
    
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
    purpose = purpose.lower()
    if purpose in ['pohonné hmoty', 'palivo', 'fuel', 'phm']:
        return 'Pohonné hmoty'
    elif purpose in ['mýtné', 'mýto', 'toll']:
        return 'Mýtné'
    elif purpose in ['ubytování', 'accommodation', 'hotel']:
        return 'Ubytování'
    return 'Ostatní'

def standardize_payment_method(payment_method: str) -> str:
    """
    Standardizuje způsob platby.
    
    Args:
        payment_method: Původní způsob platby
        
    Returns:
        Standardizovaný způsob platby
    """
    payment_method = payment_method.lower()
    if payment_method in ['karta', 'kartou', 'card']:
        return 'Kartou'
    return 'Hotovost'

def standardize_currency(currency: str) -> str:
    """
    Standardizuje měnu.
    
    Args:
        currency: Původní měna
        
    Returns:
        Standardizovaná měna
    """
    currency = currency.upper()
    return 'EUR' if currency == 'EUR' else 'CZK'

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
                    return cell
            except Exception as e:
                logger.error(f"Chyba při kontrole buňky {cell}: {str(e)}")
                continue
        
        # Všechny buňky jsou zaplněny
        return None
        
    except Exception as e:
        logger.error(f"Chyba při hledání prázdné buňky: {str(e)}")
        return None
