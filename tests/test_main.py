import unittest
from datetime import datetime
import numpy as np
from PIL import Image

# Import funkcí z aplikace
from utils.ocr_utils import perform_ocr
from utils.receipt_parser import extract_receipt_info
from utils.excel_export import export_to_excel

class TestSkenUctenek(unittest.TestCase):
    def setUp(self):
        """Inicializace dat pro testy."""
        self.test_image = np.zeros((100, 100, 3), dtype=np.uint8)  # Dummy obrázek (černý)
        self.test_text = """
        Obchodník: Testovací Obchod
        Datum: 13.03.2025
        Celkem: 1234.56 Kč
        Způsob platby: Kartou
        Číslo účtenky: ABC123
        """
        self.receipt_data = {
            "merchant": "Testovací Obchod",
            "date": datetime(2025, 3, 13),
            "total": 1234.56,
            "payment_method": "Kartou",
            "receipt_number": "ABC123",
            "currency": "CZK",
            "purpose": ""
        }

    def test_perform_ocr(self):
        """Test OCR zpracování obrázku."""
        extracted_text = perform_ocr(self.test_image)
        self.assertIsInstance(extracted_text, str, "OCR výstup by měl být typu string.")

    def test_extract_receipt_info(self):
        """Test extrakce informací z textu účtenky."""
        extracted_info = extract_receipt_info(self.test_text)
        self.assertEqual(extracted_info["merchant"], self.receipt_data["merchant"], "Obchodník by měl být správně rozpoznán.")
        self.assertEqual(extracted_info["total"], self.receipt_data["total"], "Celková částka by měla být správně rozpoznána.")
        self.assertEqual(extracted_info["payment_method"], self.receipt_data["payment_method"], "Způsob platby by měl být správně rozpoznán.")
        self.assertEqual(extracted_info["receipt_number"], self.receipt_data["receipt_number"], "Číslo účtenky by mělo být správně rozpoznáno.")

    def test_export_to_excel(self):
        """Test exportu dat do Excelu."""
        excel_file = export_to_excel([self.receipt_data], column_mapping={
            'date': 'Datum',
            'merchant': 'Obchodník',
            'total': 'Celková částka',
            'payment_method': 'Způsob platby',
            'receipt_number': 'Číslo účtenky',
            'purpose': 'Účel',
            'currency': 'Měna'
        })
        self.assertIsNotNone(excel_file, "Excel soubor by měl být vytvořen.")
        self.assertGreater(len(excel_file.getvalue()), 0, "Excel soubor by měl obsahovat data.")

if __name__ == '__main__':
    unittest.main()
