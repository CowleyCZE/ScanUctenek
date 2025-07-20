from utils.receipt_parser import extract_receipt_info, determine_receipt_type, extract_total_amount, extract_merchant, extract_date
from datetime import datetime

def test_extract_receipt_info_empty():
    """Test extrakce informací z prázdného vstupu."""
    result = extract_receipt_info("")
    assert isinstance(result, dict)
    assert result['merchant'] == ''
    assert isinstance(result['date'], datetime)
    assert result['total'] == 0.0
    assert result['currency'] == 'CZK'
    assert result['purpose'] == 'Ostatní'

def test_determine_receipt_type():
    """Test určení typu účtenky."""
    # Test fuel receipt
    fuel_text = "SHELL\nNatural 95\n25.5 L\n45.90 Kč/L"
    assert determine_receipt_type(fuel_text, 'cs') == 'Pohonné hmoty'

    # Test default type
    normal_text = "Potraviny\nRohlík 3ks"
    assert determine_receipt_type(normal_text, 'cs') == 'Ostatní'

def test_extract_total_amount():
    """Test extrakce celkové částky."""
    # Různé formáty a jazyky
    text_cs = "CELKEM: 123,45 Kč"
    text_en = "Total: 123.45 EUR"
    text_de = "Summe: 123,45 €"
    text_fr = "Montant Total 123.45"
    text_no_keyword = "Účtenka\nProdukt A 100.00\nProdukt B 23.45"

    assert extract_total_amount(text_cs, 'cs') == 123.45
    assert extract_total_amount(text_en, 'en') == 123.45
    assert extract_total_amount(text_de, 'de') == 123.45
    assert extract_total_amount(text_fr, 'fr') == 123.45
    assert extract_total_amount(text_no_keyword, 'cs') == 100.00 # Vrátí nejvyšší částku

def test_extract_merchant():
    """Test extrakce obchodníka."""
    text = "AVIA\n123 Main Street\nTel: 123-456-789"
    assert extract_merchant(text, 'cs') == 'AVIA'

    text_generic = "Můj Obchod\nDatum: 01.01.2023"
    assert extract_merchant(text_generic, 'cs') == 'Můj Obchod'

def test_extract_date():
    """Test extrakce data."""
    text_dmy = "Datum: 01.02.2023"
    text_ymd = "Date: 2023-02-01"
    text_dmy_slash = "01/02/2023"

    expected_date = datetime(2023, 2, 1)

    assert extract_date(text_dmy, 'cs') == expected_date
    assert extract_date(text_ymd, 'en') == expected_date
    assert extract_date(text_dmy_slash, 'cs') == expected_date
