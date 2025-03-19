"""
Wordlist management for receipt parsing
This module handles user-defined wordlists for better receipt recognition
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default wordlists for different languages and data fields
DEFAULT_WORDLISTS: Dict[str, Dict[str, List[str]]] = {
    'date': {
        'cs': ['datum', 'dne', 'vystaveno', 'dat.', 'ze dne', 'dat'],
        'fr': ['date', 'émis le', 'date d\'émission', 'du', 'le', 'date de transaction'],
        'de': ['datum', 'ausgestellt am', 'tag', 'vom', 'dat.', 'dat']
    },
    'total': {
        'cs': ['celkem', 'celková částka', 'součet', 'k úhradě', 'zaplaceno', 'uhrazeno', 'suma', 'cena celkem'],
        'fr': ['total', 'montant', 'total à payer', 'à payer', 'net à payer', 'total ttc', 'somme', 'prix total', 
               'montant reel', 'tarif t.t.c.', 'montant total', 'total eur', 'total €'],
        'de': ['gesamt', 'summe', 'gesamtbetrag', 'zu zahlen', 'zahlbetrag', 'endsumme', 'gesamtsumme', 'total']
    },
    'currency': {
        'cs': ['kč', 'czk', 'korun', 'koruny', 'korun českých', 'koruny české', 'k', 'eur', '€'],
        'fr': ['€', 'eur', 'euro', 'euros', 'e'],
        'de': ['€', 'eur', 'euro']
    },
    'payment_method': {
        'cs': ['způsob platby', 'platba', 'placeno', 'hotovost', 'karta', 'platební karta', 'kartou', 'bankovní převod',
               'v hotovosti', 'hotově'],
        'fr': ['méthode de paiement', 'paiement', 'réglé par', 'payé par', 'espèces', 'carte', 'cb', 'carte bancaire',
               'virement', 'chèque', 'sans contact', 'contactless', 'mastercard', 'visa'],
        'de': ['zahlungsart', 'zahlung', 'bezahlt mit', 'bargeld', 'bar', 'karte', 'ec-karte', 'kreditkarte',
               'kartenzahlung', 'überweisung']
    },
    'merchant': {
        'cs': ['obchodník', 'prodejce', 'prodejna', 'firma', 'dodavatel', 'název', 'společnost'],
        'fr': ['commerçant', 'vendeur', 'magasin', 'entreprise', 'fournisseur', 'nom', 'société', 'siret'],
        'de': ['händler', 'verkäufer', 'geschäft', 'firma', 'lieferant', 'name', 'unternehmen', 'geschäftsname']
    },
    'purpose': {
        'cs': ['účel', 'zboží', 'produkt', 'služba', 'popis', 'položka', 'název zboží', 'název položky'],
        'fr': ['objet', 'marchandise', 'produit', 'service', 'description', 'article', 'désignation'],
        'de': ['zweck', 'ware', 'produkt', 'dienstleistung', 'beschreibung', 'artikel', 'bezeichnung']
    },
    'fuel': {
        'cs': ['pohonné hmoty', 'phm', 'palivo', 'natural', 'benzin', 'benzín', 'nafta', 'diesel', 'natankováno',
               'čerpací stanice', 'čerpací st.', 'tankování', 'tankovat', 'shell', 'mol', 'omv', 'benzina', 'orlen', 'lpg',
               'litr', 'l', 'cena/l', 'kč/l', 'množství'],
        'fr': ['carburant', 'essence', 'diesel', 'gazole', 'gazole+', 'station-service', 'station service', 'plein', 
               'super', 'sans plomb', 'avia', 'total', 'totalenergies', 'gulf', 'litre', 'litres', 'l', 'prix unit', 
               'quantité', 'volume', 'pompe', 'naturel', 'e5', 'e10', 'sp95', 'sp98'],
        'de': ['kraftstoff', 'benzin', 'diesel', 'tanken', 'tankstelle', 'zapfsäule', 'super', 'e10', 'autogas',
               'liter', 'l', 'preis/l', 'menge']
    },
    'toll': {
        'cs': ['mýtné', 'mýto', 'dálniční známka', 'dálniční poplatek', 'poplatek za dálnici', 'dálnice', 'poplatek',
               'emyto', 'e-myto', 'známka', 'elektronické mýto', 'km'],
        'fr': ['péage', 'autoroute', 'vignette', 'taxe routière', 'frais d\'autoroute', 'sanef', 'cofiroute', 
               'vinci', 'autoroutes', 'echangeur', 'barrier', 'km parcourus', 'trajet', 'sortie', 'entrée',
               'classe tarif', 'ticket a conserver', 'recu a conserver'],
        'de': ['maut', 'autobahngebühr', 'vignette', 'straßengebühr', 'autobahnmaut', 'e-vignette', 'strecke', 'km']
    },
    'accommodation': {
        'cs': ['ubytování', 'hotel', 'penzion', 'motel', 'nocleh', 'apartmán', 'pokoj', 'aparthotel', 'apartmány',
               'hostel', 'lůžko', 'nocování', 'noclehárna', 'bydlení'],
        'fr': ['hébergement', 'hôtel', 'pension', 'motel', 'chambre', 'appartement', 'gîte', 'auberge', 'logement'],
        'de': ['unterkunft', 'hotel', 'pension', 'motel', 'zimmer', 'appartement', 'ferienwohnung', 'gasthaus', 'übernachtung']
    }
}

def get_wordlist_path() -> Path:
    """
    Získá cestu k souboru se slovníky.
    
    Returns:
        Path: Cesta k souboru se slovníky
    """
    return Path(__file__).parent / "wordlists.json"

def load_wordlists() -> Dict[str, Dict[str, List[str]]]:
    """
    Načte slovníky z JSON souboru nebo vrátí výchozí hodnoty, pokud soubor neexistuje.
    
    Returns:
        Dict[str, Dict[str, List[str]]]: Slovníky pro různá pole a jazyky
    """
    wordlist_path = get_wordlist_path()
    
    if wordlist_path.exists():
        try:
            with open(wordlist_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Chyba při načítání slovníků: {e}")
            return DEFAULT_WORDLISTS.copy()
    else:
        return DEFAULT_WORDLISTS.copy()

def save_wordlists(wordlists: Dict[str, Dict[str, List[str]]]) -> bool:
    """
    Uloží slovníky do JSON souboru.
    
    Args:
        wordlists: Slovníky k uložení
        
    Returns:
        bool: Úspěch nebo neúspěch operace
    """
    wordlist_path = get_wordlist_path()
    
    try:
        with open(wordlist_path, "w", encoding="utf-8") as file:
            json.dump(wordlists, file, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Chyba při ukládání slovníků: {e}")
        return False

def add_word(field: str, language: str, word: str) -> bool:
    """
    Přidá slovo do slovníku pro konkrétní pole a jazyk.
    
    Args:
        field: Pole pro přidání slova (date, total, atd.)
        language: Jazykový kód (cs, fr, de)
        word: Slovo k přidání
        
    Returns:
        bool: Úspěch nebo neúspěch operace
    """
    try:
        wordlists = load_wordlists()
        
        # Zajistí existenci pole a jazyka ve struktuře
        if field not in wordlists:
            wordlists[field] = {}
        if language not in wordlists[field]:
            wordlists[field][language] = []
        
        # Kontrola, zda slovo již existuje
        word_lower = word.lower()
        if word_lower not in [w.lower() for w in wordlists[field][language]]:
            wordlists[field][language].append(word_lower)
            return save_wordlists(wordlists)
        return True  # Slovo již existuje
        
    except Exception as e:
        logger.error(f"Chyba při přidávání slova: {e}")
        return False

def remove_word(field: str, language: str, word: str) -> bool:
    """
    Odstraní slovo ze slovníku pro konkrétní pole a jazyk.
    
    Args:
        field: Pole pro odstranění slova
        language: Jazykový kód
        word: Slovo k odstranění
        
    Returns:
        bool: Úspěch nebo neúspěch operace
    """
    try:
        wordlists = load_wordlists()
        
        # Kontrola existence pole a jazyka
        if field in wordlists and language in wordlists[field]:
            # Hledání přesného slova (bez ohledu na velikost písmen)
            word_lower = word.lower()
            for existing_word in wordlists[field][language]:
                if existing_word.lower() == word_lower:
                    wordlists[field][language].remove(existing_word)
                    return save_wordlists(wordlists)
        return False  # Slovo nebylo nalezeno
        
    except Exception as e:
        logger.error(f"Chyba při odstraňování slova: {e}")
        return False

def reset_wordlist(field: Optional[str] = None, language: Optional[str] = None) -> bool:
    """
    Resetuje slovníky na výchozí hodnoty.
    
    Args:
        field: Volitelné pole k resetu (pokud None, resetuje všechna pole)
        language: Volitelný jazyk k resetu (pokud None, resetuje všechny jazyky pro pole)
        
    Returns:
        bool: Úspěch nebo neúspěch operace
    """
    try:
        wordlists = load_wordlists()
        
        if field is None:
            # Reset všech slovníků
            return save_wordlists(DEFAULT_WORDLISTS.copy())
        elif language is None:
            # Reset konkrétního pole pro všechny jazyky
            if field in DEFAULT_WORDLISTS:
                wordlists[field] = DEFAULT_WORDLISTS[field].copy()
                return save_wordlists(wordlists)
        else:
            # Reset konkrétního pole a jazyka
            if field in DEFAULT_WORDLISTS and language in DEFAULT_WORDLISTS[field]:
                if field not in wordlists:
                    wordlists[field] = {}
                wordlists[field][language] = DEFAULT_WORDLISTS[field][language].copy()
                return save_wordlists(wordlists)
        
        return False  # Neplatné pole nebo jazyk
        
    except Exception as e:
        logger.error(f"Chyba při resetování slovníku: {e}")
        return False

def get_words(field: str, language: str) -> List[str]:
    """
    Získá slova pro konkrétní pole a jazyk.
    
    Args:
        field: Pole pro získání slov
        language: Jazykový kód
        
    Returns:
        List[str]: Seznam slov pro pole a jazyk
    """
    try:
        wordlists = load_wordlists()
        
        if field in wordlists and language in wordlists[field]:
            return wordlists[field][language]
        elif field in DEFAULT_WORDLISTS and language in DEFAULT_WORDLISTS[field]:
            # Pokud nenalezeno v uživatelských slovnících, vrátí výchozí hodnoty
            return DEFAULT_WORDLISTS[field][language]
        else:
            return []
            
    except Exception as e:
        logger.error(f"Chyba při získávání slov: {e}")
        return []

def get_all_fields() -> List[str]:
    """
    Získá všechna dostupná pole.
    
    Returns:
        List[str]: Seznam všech dostupných polí
    """
    try:
        wordlists = load_wordlists()
        return list(wordlists.keys())
    except Exception as e:
        logger.error(f"Chyba při získávání polí: {e}")
        return list(DEFAULT_WORDLISTS.keys())

def get_all_languages() -> List[str]:
    """
    Získá všechny podporované jazyky.
    
    Returns:
        List[str]: Seznam podporovaných jazyků
    """
    return ['cs', 'fr', 'de']

def add_field(field: str, words_dict: Optional[Dict[str, List[str]]] = None) -> bool:
    """
    Přidá nové pole do slovníků.
    
    Args:
        field: Název pole k přidání
        words_dict: Volitelný slovník slov podle jazyka
        
    Returns:
        bool: Úspěch nebo neúspěch operace
    """
    try:
        if not words_dict:
            words_dict = {'cs': [], 'fr': [], 'de': []}
        
        wordlists = load_wordlists()
        
        if field not in wordlists:
            wordlists[field] = words_dict
            return save_wordlists(wordlists)
        
        return False  # Pole již existuje
        
    except Exception as e:
        logger.error(f"Chyba při přidávání pole: {e}")
        return False

def remove_field(field: str) -> bool:
    """
    Odstraní pole ze slovníků.
    
    Args:
        field: Pole k odstranění
        
    Returns:
        bool: Úspěch nebo neúspěch operace
    """
    try:
        wordlists = load_wordlists()
        
        if field in wordlists:
            del wordlists[field]
            return save_wordlists(wordlists)
        
        return False  # Pole neexistuje
        
    except Exception as e:
        logger.error(f"Chyba při odstraňování pole: {e}")
        return False
