"""
Wordlist management for receipt parsing
This module handles user-defined wordlists for better receipt recognition
"""

import json
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Default wordlists for different languages and data fields
DEFAULT_WORDLISTS = {
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

def load_wordlists():
    """
    Load wordlists from a JSON file or return defaults if the file is not found.
    Returns:
        dict: Wordlists for different fields and languages.
    """
    wordlist_path = os.path.join(os.path.dirname(__file__), "wordlists.json")
    
    if os.path.exists(wordlist_path):
        try:
            with open(wordlist_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            print(f"Chyba při načítání slovníků: {e}")
            return DEFAULT_WORDLISTS
    else:
        return DEFAULT_WORDLISTS

def save_wordlists(wordlists):
        """
        Save wordlists to a JSON file.
        Args:
            wordlists: The wordlists dictionary to save.
        Returns:
            bool: Success or failure
        """
        wordlist_path = os.path.join(os.path.dirname(__file__), "wordlists.json")
        
        try:
            with open(wordlist_path, "w", encoding="utf-8") as file:
                json.dump(wordlists, file, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"Chyba při ukládání slovníků: {e}")
            return False

def add_word(field, language, word):
    """
    Add a word to a specific field and language wordlist
    Args:
        field: The field to add the word to (date, total, etc.)
        language: The language code (cs, fr, de)
        word: The word to add
    Returns:
        bool: Success or failure
    """
    wordlists = load_wordlists()
    
    # Ensure the field and language exist in the structure
    if field not in wordlists:
        wordlists[field] = {}
    if language not in wordlists[field]:
        wordlists[field][language] = []
    
    # Check if word already exists
    if word.lower() not in [w.lower() for w in wordlists[field][language]]:
        wordlists[field][language].append(word.lower())
        return save_wordlists(wordlists)
    return True  # Word already exists

def remove_word(field, language, word):
    """
    Remove a word from a specific field and language wordlist
    Args:
        field: The field to remove the word from
        language: The language code
        word: The word to remove
    Returns:
        bool: Success or failure
    """
    wordlists = load_wordlists()
    
    # Check if the field and language exist
    if field in wordlists and language in wordlists[field]:
        # Find the exact word (case insensitive)
        for existing_word in wordlists[field][language]:
            if existing_word.lower() == word.lower():
                wordlists[field][language].remove(existing_word)
                return save_wordlists(wordlists)
    return False  # Word not found

def reset_wordlist(field=None, language=None):
    """
    Reset wordlists to defaults
    Args:
        field: Optional field to reset (if None, resets all fields)
        language: Optional language to reset (if None, resets all languages for the field)
    Returns:
        bool: Success or failure
    """
    wordlists = load_wordlists()
    
    if field is None:
        # Reset all wordlists
        return save_wordlists(DEFAULT_WORDLISTS.copy())
    elif language is None:
        # Reset specific field for all languages
        if field in DEFAULT_WORDLISTS:
            wordlists[field] = DEFAULT_WORDLISTS[field].copy()
            return save_wordlists(wordlists)
    else:
        # Reset specific field and language
        if field in DEFAULT_WORDLISTS and language in DEFAULT_WORDLISTS[field]:
            if field not in wordlists:
                wordlists[field] = {}
            wordlists[field][language] = DEFAULT_WORDLISTS[field][language].copy()
            return save_wordlists(wordlists)
    
    return False  # Invalid field or language

def get_words(field, language):
    """
    Get words for a specific field and language
    Args:
        field: The field to get words for
        language: The language code
    Returns:
        list: List of words for the field and language
    """
    wordlists = load_wordlists()
    
    if field in wordlists and language in wordlists[field]:
        return wordlists[field][language]
    elif field in DEFAULT_WORDLISTS and language in DEFAULT_WORDLISTS[field]:
        # If not found in user wordlists, return defaults
        return DEFAULT_WORDLISTS[field][language]
    else:
        return []

def get_all_fields():
    """Get all available fields"""
    wordlists = load_wordlists()
    return list(wordlists.keys())

def get_all_languages():
    """Get all supported languages"""
    return ['cs', 'fr', 'de']

def add_field(field, words_dict=None):
    """
    Add a new field to the wordlists
    Args:
        field: The field name to add
        words_dict: Optional dictionary of words by language
    Returns:
        bool: Success or failure
    """
    if not words_dict:
        words_dict = {'cs': [], 'fr': [], 'de': []}
    
    wordlists = load_wordlists()
    
    if field not in wordlists:
        wordlists[field] = words_dict
        return save_wordlists(wordlists)
    
    return False  # Field already exists

def remove_field(field):
    """
    Remove a field from the wordlists
    Args:
        field: The field to remove
    Returns:
        bool: Success or failure
    """
    wordlists = load_wordlists()
    
    if field in wordlists:
        del wordlists[field]
        return save_wordlists(wordlists)
    
    return False  # Field doesn't exist
