# -*- coding: utf-8 -*-
from utils.receipt_parser import (
    detect_language,
    extract_payment_method,
    extract_receipt_number,
    detect_currency,
    extract_fuel_data,
    extract_toll_data,
    extract_total_amount,
    extract_merchant,
    extract_date
)
from datetime import datetime

# --- Testy pro detekci jazyka ---
def test_detect_language_cs():
    text = "Účtenka číslo 123. Celkem k úhradě: 500 Kč. Děkujeme za nákup."
    assert detect_language(text) == 'cs'

def test_detect_language_de():
    text = "Rechnung Nr. 456. Gesamtbetrag: 50 EUR. Vielen Dank für Ihren Einkauf."
    assert detect_language(text) == 'de'

def test_detect_language_fr():
    text = "Facture n° 789. Montant total: 75 EUR. Merci pour votre achat."
    assert detect_language(text) == 'fr'

def test_detect_language_fallback():
    text = "Receipt number 123. Total amount: 50 USD."
    assert detect_language(text) == 'cs' # Fallback na češtinu

# --- Testy pro extrakci platební metody ---
def test_extract_payment_method_card():
    text_cs = "Platba provedena kartou."
    text_en = "Payment by card."
    text_de = "Zahlung per Karte."
    assert extract_payment_method(text_cs, 'cs') == 'Kartou'
    assert extract_payment_method(text_en, 'en') == 'Kartou'
    assert extract_payment_method(text_de, 'de') == 'Kartou'

def test_extract_payment_method_cash():
    text_cs = "Placeno v hotovosti."
    text_de = "Bar bezahlt."
    text_fr = "Payé en espèces."
    assert extract_payment_method(text_cs, 'cs') == 'Hotovost'
    assert extract_payment_method(text_de, 'de') == 'Hotovost'
    assert extract_payment_method(text_fr, 'fr') == 'Hotovost'

def test_extract_payment_method_default():
    text = "Děkujeme za nákup."
    assert extract_payment_method(text, 'cs') == 'Neznámý' # Výchozí hodnota by měla být Neznámý

# --- Testy pro extrakci čísla účtenky ---
def test_extract_receipt_number_cs():
    text = "Číslo účtenky: 54321"
    assert extract_receipt_number(text, 'cs') == "54321"

def test_extract_receipt_number_none():
    text = "Žádné číslo zde není."
    assert extract_receipt_number(text, 'cs') is None

# --- Testy pro detekci měny ---
def test_detect_currency_czk():
    text = "Celkem: 100 Kč"
    assert detect_currency(text, 'cs') == 'CZK'

def test_detect_currency_eur():
    text = "Total: 50 €"
    assert detect_currency(text, 'de') == 'EUR'

def test_detect_currency_eur_symbol():
    text = "Montant: 25 EUR"
    assert detect_currency(text, 'fr') == 'EUR'

def test_detect_currency_fallback():
    text_cs = "Celkem: 100.00"
    text_fr = "Total: 50.00"
    assert detect_currency(text_cs, 'cs') == 'CZK'
    assert detect_currency(text_fr, 'fr') == 'EUR'

# --- Testy pro specifická data ---
def test_extract_fuel_data():
    text = """
    SHELL V-POWER
    Množství: 50.5 L
    Cena/L: 45.90 Kč
    """
    data = extract_fuel_data(text, 'cs')
    assert data['quantity'] == 50.5
    assert data['price_per_liter'] == 45.9

def test_extract_toll_data():
    text = """
    SANEF PEAGE
    Entrée: Paris
    Sortie: Lyon
    Distance: 450.5 km
    """
    data = extract_toll_data(text, 'fr')
    assert data['entry_point'] == 'Paris'
    assert data['exit_point'] == 'Lyon'
    assert data['distance'] == 450.5

# --- Rozšířené testy pro existující funkce ---
def test_extract_total_amount_extended():
    text1 = "Zaplaceno celkem 1 234,56 Kč" # s mezerou
    text2 = "TOTAAL: 123.45" # bez měny
    text3 = "Nejvyšší položka 500.00\nNižší položka 100.00" # fallback na nejvyšší
    assert extract_total_amount(text1, 'cs') == 1234.56
    assert extract_total_amount(text2, 'fr') == 123.45
    assert extract_total_amount(text3, 'cs') == 500.00
    assert extract_total_amount("žádná částka", 'cs') is None

def test_extract_merchant_extended():
    text1 = "Vítejte v obchodě Můj Obchod s.r.o."
    text2 = "TOTALENERGIES STANICE"
    text3 = "ORLEN BENZINA"
    assert extract_merchant(text1, 'cs') == "Vítejte v obchodě Můj Obchod s.r.o."
    assert extract_merchant(text2, 'fr') == "TOTALENERGIES STANICE"
    assert extract_merchant(text3, 'cs') == "ORLEN BENZINA"

def test_extract_date_extended():
    text1 = "Datum nákupu: 2024-03-13" # YYYY-MM-DD
    text2 = "Vystaveno dne 13/03/24" # DD/MM/YY
    text3 = "Date of issue: 03-13-2024" # MM-DD-YYYY - nepodporovaný formát, měl by selhat
    assert extract_date(text1, 'cs') == datetime(2024, 3, 13)
    assert extract_date(text2, 'cs') == datetime(2024, 3, 13)
    assert extract_date(text3, 'en') is None # Očekáváme, že nenajde platné datum

# --- Testy pro nově přidanou a vylepšenou logiku ---

def test_extract_merchant_improved():
    """Testuje vylepšenou logiku extrakce obchodníka."""
    # Test na velká písmena
    text_upper = "MŮJ SUPER OBCHOD\nulice 123\n123 45 Město"
    assert extract_merchant(text_upper, 'cs') == "MŮJ SUPER OBCHOD"

    # Test na právní formu s.r.o.
    text_sro = "Skvělé Potraviny s.r.o.\nTel: 111 222 333"
    assert extract_merchant(text_sro, 'cs') == "Skvělé Potraviny s.r.o."

    # Test, kde je název níže
    text_lower_pos = "Účtenka\n\nSUPER MARKET ABC\nDatum: 01.01.2025"
    assert extract_merchant(text_lower_pos, 'cs') == "SUPER MARKET ABC"

def test_extract_total_amount_improved_fallback():
    """Testuje vylepšenou fallback logiku pro celkovou částku."""
    text = "Položka 1: 100.00\nPoložka 2: 999.99\n\nSoučet: 1099.99\nDaň: 100.00\nCelkem k úhradě: 1199.99"
    # Tento test by měl projít díky klíčovým slovům
    assert extract_total_amount(text, 'cs') == 1199.99

    # Test fallback logiky - žádné klíčové slovo, celková částka je v posledních řádcích
    text_fallback = "Položka 1: 50.00\nPoložka 2: 70.00\n\n120,00"
    assert extract_total_amount(text_fallback, 'cs') == 120.00

def test_extract_payment_method_improved():
    """Testuje vylepšenou logiku pro detekci platební metody."""
    # Test nových klíčových slov
    text_visa = "Platba byla provedena kartou VISA."
    text_mastercard = "Zaplaceno přes MasterCard, částka 500 Kč."
    assert extract_payment_method(text_visa, 'cs') == 'Kartou'
    assert extract_payment_method(text_mastercard, 'cs') == 'Kartou'

    # Test výchozí hodnoty "Neznámý"
    text_unknown = "Děkujeme za Váš nákup."
    assert extract_payment_method(text_unknown, 'cs') == 'Neznámý'

    # Test, kdy je informace na konci
    text_end = "Položka 1\nPoložka 2\n\nPlaceno hotově."
    assert extract_payment_method(text_end, 'cs') == 'Hotovost'

def test_detect_currency_improved():
    """Testuje vylepšenou, kontextovou detekci měny."""
    # Měna je na stejném řádku jako klíčové slovo "celkem"
    text_context = "Mezisoučet: 100.00\nCelkem k úhradě: 121.00 EUR"
    assert detect_currency(text_context, 'cs') == 'EUR'

    # Měna je jinde, ale na řádku s "celkem" není, fallback na globální hledání
    text_fallback_global = "Měna transakce: EUR\nCelkem k úhradě: 121.00"
    assert detect_currency(text_fallback_global, 'cs') == 'EUR'

    # Na řádku s "celkem" je CZK, i když jinde v textu je EUR
    text_priority = "Info: Ceny jsou v EUR\n\nCelkem: 599.00 Kč"
    assert detect_currency(text_priority, 'cs') == 'CZK'
