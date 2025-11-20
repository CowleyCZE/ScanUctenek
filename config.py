# -*- coding: utf-8 -*-
"""
Konfigurační soubor pro aplikaci SkenÚčtenek.
"""

# Konfigurace aplikace
APP_CONFIG = {
    'supported_languages': {
        'cs': 'Čeština',
        'fr': 'Francouzština',
        'de': 'Němčina'
    },
    'ocr_language_codes': {
        'cs': 'ces',
        'fr': 'fra',
        'de': 'deu'
    },
    'default_currency': 'CZK',
    'supported_currencies': ['CZK', 'EUR'],
    'receipt_categories': {
        'fuel': 'Pohonné hmoty',
        'toll': 'Mýtné',
        'accommodation': 'Ubytování',
        'food': 'Stravování',
        'other': 'Ostatní'
    }
}
