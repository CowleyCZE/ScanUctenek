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

# Cesty k souborům se slovníky
DEFAULT_WORDLIST_PATH = Path(__file__).parent.parent / "data" / "user_wordlists.json"
USER_CATEGORIES_PATH = Path(__file__).parent.parent / "data" / "user_categories.json"

def load_default_wordlists() -> Dict[str, Any]:
    """
    Načte výchozí slovníky.
    """
    if not DEFAULT_WORDLIST_PATH.exists():
        return {}
    with open(DEFAULT_WORDLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_user_categories() -> Dict[str, Any]:
    """
    Načte uživatelsky definované kategorie.
    """
    if not USER_CATEGORIES_PATH.exists():
        return {}
    with open(USER_CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

DEFAULT_WORDLISTS = load_default_wordlists()
USER_CATEGORIES = load_user_categories()

def get_wordlist_path() -> Path:
    """
    Získá cestu k souboru se slovníky.
    
    Returns:
        Path: Cesta k souboru se slovníky
    """
    return USER_CATEGORIES_PATH

def load_wordlists() -> Dict[str, Dict[str, List[str]]]:
    """
    Načte a sloučí výchozí a uživatelské slovníky.
    """
    wordlists = DEFAULT_WORDLISTS.copy()
    user_wordlists = load_user_categories()
    
    # Sloučení slovníků, přičemž uživatelské mají přednost
    for field, languages in user_wordlists.items():
        if field not in wordlists:
            wordlists[field] = {}
        for lang, words in languages.items():
            if lang not in wordlists[field]:
                wordlists[field][lang] = []

            # Přidání unikátních slov
            existing_words = set(wordlists[field][lang])
            wordlists[field][lang].extend([w for w in words if w not in existing_words])

    return wordlists

def save_wordlists(wordlists: Dict[str, Dict[str, List[str]]]) -> bool:
    """
    Uloží uživatelsky definované slovníky.
    """
    user_wordlists = {}
    
    # Uložení pouze uživatelsky definovaných polí
    for field, languages in wordlists.items():
        if field not in DEFAULT_WORDLISTS:
            user_wordlists[field] = languages

    try:
        with open(USER_CATEGORIES_PATH, "w", encoding="utf-8") as file:
            json.dump(user_wordlists, file, ensure_ascii=False, indent=4)
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
