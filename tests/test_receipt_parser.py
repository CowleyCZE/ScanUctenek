from utils.receipt_parser import extract_receipt_info, determine_receipt_type
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
