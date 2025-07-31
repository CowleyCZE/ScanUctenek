import pytest
import json
from unittest.mock import patch, mock_open
import copy

# Import funkcí z modulu, který testujeme
from utils import word_lists

# Ukázková data pro mockování
MOCK_DEFAULT_WORDLISTS = {
    "total": {
        "cs": ["celkem", "suma"],
        "en": ["total", "sum"]
    },
    "date": {
        "cs": ["datum"],
        "en": ["date"]
    }
}

MOCK_USER_CATEGORIES = {
    "custom_category": {
        "cs": ["moje kategorie"],
        "en": ["my category"]
    }
}

@pytest.fixture(autouse=True)
def setup_mocks():
    """
    Patchuje globální proměnné a souborové operace.
    """
    # Používáme hluboké kopie, aby se zabránilo vzájemnému ovlivňování testů
    default_wordlists_copy = copy.deepcopy(MOCK_DEFAULT_WORDLISTS)
    user_categories_copy = copy.deepcopy(MOCK_USER_CATEGORIES)

    # Patchování globálních proměnných, které se načítají při importu
    with patch('utils.word_lists.DEFAULT_WORDLISTS', new=default_wordlists_copy), \
         patch('utils.word_lists.USER_CATEGORIES', new=user_categories_copy), \
         patch('utils.word_lists.load_user_categories', return_value=user_categories_copy):
        yield

def test_load_wordlists():
    """Testuje, zda se správně sloučí výchozí a uživatelské slovníky."""
    loaded_wordlists = word_lists.load_wordlists()

    assert "total" in loaded_wordlists
    assert "custom_category" in loaded_wordlists
    assert len(loaded_wordlists) == 3

@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_save_wordlists(mock_json_dump, mock_file_open):
    """Testuje, že save_wordlists správně filtruje a ukládá jen uživatelské kategorie."""
    wordlists_to_save = {
        "total": {"cs": ["celkem"]}, # výchozí
        "custom_category": {"cs": ["moje"]}, # uživatelská
        "new_user_category": {"cs": ["nová"]} # nová uživatelská
    }

    word_lists.save_wordlists(wordlists_to_save)

    # Ověříme, že se volal open pro správný soubor
    mock_file_open.assert_called_once_with(word_lists.USER_CATEGORIES_PATH, "w", encoding="utf-8")

    # Ověříme, že json.dump byl volán s odfiltrovanými daty
    mock_json_dump.assert_called_once()
    saved_data = mock_json_dump.call_args[0][0]

    assert "new_user_category" in saved_data
    assert "custom_category" in saved_data
    assert "total" not in saved_data # Ověření, že výchozí pole bylo odfiltrováno

@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_add_field(mock_json_dump, mock_file_open):
    """Testuje přidání nového pole a jeho uložení."""
    new_field = "another_category"
    new_words = {"cs": ["další kategorie"]}

    result = word_lists.add_field(new_field, new_words)

    assert result is True
    mock_json_dump.assert_called_once()
    saved_data = mock_json_dump.call_args[0][0]

    assert new_field in saved_data
    assert "custom_category" in saved_data # Původní uživatelská tam stále je

@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_remove_field(mock_json_dump, mock_file_open):
    """Testuje odstranění pole a jeho uložení."""
    field_to_remove = "custom_category"

    result = word_lists.remove_field(field_to_remove)

    assert result is True
    mock_json_dump.assert_called_once()
    saved_data = mock_json_dump.call_args[0][0]

    assert field_to_remove not in saved_data
    assert "total" not in saved_data # Ujistíme se, že se neukládají výchozí

def test_get_words():
    """Testuje získávání slov pro konkrétní pole a jazyk."""
    words = word_lists.get_words("total", "cs")
    assert words == ["celkem", "suma"]

    user_words = word_lists.get_words("custom_category", "cs")
    assert user_words == ["moje kategorie"]

def test_get_all_fields():
    """Testuje, zda vrací všechna pole (výchozí i uživatelská)."""
    fields = word_lists.get_all_fields()
    assert "total" in fields
    assert "date" in fields
    assert "custom_category" in fields
    assert len(fields) == 3

@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_add_word(mock_json_dump, mock_file_open):
    """Testuje přidání nového slova do existujícího pole."""
    result = word_lists.add_word("total", "cs", "nové slovo")
    assert result is True

    mock_json_dump.assert_called_once()
    saved_data = mock_json_dump.call_args[0][0]

    # save_wordlists by neměla ukládat výchozí pole, takže by saved_data měla být prázdná
    assert saved_data == {"custom_category": {"cs": ["moje kategorie"], "en": ["my category"]}}

@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_remove_word(mock_json_dump, mock_file_open):
    """Testuje odstranění slova."""
    result = word_lists.remove_word("total", "cs", "celkem")
    assert result is True

    mock_json_dump.assert_called_once()
    saved_data = mock_json_dump.call_args[0][0]

    # Zkontrolujeme, že se nic nezměnilo v uživatelských datech k uložení
    assert saved_data == {"custom_category": {"cs": ["moje kategorie"], "en": ["my category"]}}
