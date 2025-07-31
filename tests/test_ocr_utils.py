import pytest
import numpy as np
from PIL import Image

from utils.ocr_utils import preprocess_image, perform_ocr

@pytest.fixture
def sample_color_image():
    """Vytvoří jednoduchý barevný obrázek (10x10) pro testování."""
    # Vytvoří 3-kanálový obrázek (RGB)
    return np.zeros((10, 10, 3), dtype=np.uint8)

def test_preprocess_image_converts_to_grayscale(sample_color_image):
    """Testuje, zda preprocess_image převede barevný obrázek na černobílý."""
    processed_image = preprocess_image(sample_color_image)

    # Ověření typu a rozměrů
    assert isinstance(processed_image, np.ndarray)
    assert len(processed_image.shape) == 2  # Očekáváme 2D pole (černobílý obrázek)
    assert processed_image.shape == (10, 10) # Rozměry by měly zůstat stejné

def test_preprocess_image_handles_grayscale_input(sample_color_image):
    """Testuje, že funkce správně zpracuje již černobílý obrázek."""
    # Převedeme testovací obrázek na černobílý
    grayscale_image = np.array(Image.fromarray(sample_color_image).convert('L'))

    processed_image = preprocess_image(grayscale_image)

    assert isinstance(processed_image, np.ndarray)
    assert len(processed_image.shape) == 2
    assert processed_image.shape == (10, 10)

def test_preprocess_image_handles_pil_image_input():
    """Testuje, že funkce správně zpracuje vstup typu PIL.Image."""
    pil_image = Image.new('RGB', (20, 20), color = 'red')
    processed_image = preprocess_image(pil_image)

    assert isinstance(processed_image, np.ndarray)
    assert len(processed_image.shape) == 2
    assert processed_image.shape == (20, 20)

def test_perform_ocr_handles_none_input():
    """Testuje, že perform_ocr nespadne při vstupu None."""
    # Očekáváme, že funkce vrátí prázdný text a slovník, ale hlavně že nevyvolá výjimku
    text, data = perform_ocr(None)
    assert text == ""
    assert data == {}

def test_perform_ocr_on_blank_image(sample_color_image):
    """
    Testuje perform_ocr na prázdném obrázku.
    Neočekáváme žádný text, ale funkce by měla proběhnout bez chyby.
    """
    # Mockování pytesseractu, abychom se vyhnuli skutečnému volání OCR
    try:
        from unittest.mock import patch
        with patch('pytesseract.image_to_string', return_value=""), \
             patch('pytesseract.image_to_data', return_value={'conf': [], 'text': []}):

            text, data = perform_ocr(sample_color_image)

            assert isinstance(text, str)
            assert isinstance(data, dict)
    except ImportError:
        # Pokud unittest.mock není k dispozici, spustíme test bez mockování
        # (v tomto případě by měl pytesseract vrátit prázdný řetězec)
        text, data = perform_ocr(sample_color_image)
        assert text == ""
