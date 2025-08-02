
# ScanUctenek

ScanUctenek je open-source aplikace pro automatizované zpracování účtenek a extrakci dat z jejich fotografií pomocí OCR. Umožňuje uživatelům nahrávat účtenky, rozpoznávat položky, exportovat data do Excelu a spravovat vlastní slovníky i kategorie. Projekt je určen pro osobní správu výdajů, digitalizaci účtenek a analýzu nákupů.

---

## Hlavní funkce

- **OCR účtenek:** Automatické rozpoznání textu z obrázků účtenek (využívá Tesseract OCR).
- **Parsers & rozpoznávání položek:** Pokročilé parsování textu účtenky, včetně detekce položek, cen, DPH a obchodů.
- **Export do Excelu:** Možnost exportovat zpracovaná data do přehledné tabulky (XLSX).
- **Uživatelské slovníky:** Uživatel může definovat vlastní kategorie a slovníky pro přesnější rozpoznání položek.
- **Lokalizace:** Podpora vícejazyčného rozhraní (CZ/EN) – viz složka `localization/`.
- **Webové rozhraní:** (volitelně) Možnost rozšíření o jednoduché webové UI pro správu účtenek.

---

## Architektura a složky projektu

- `app.py` – Hlavní spouštěcí bod aplikace (webový server nebo CLI).
- `utils/` – Pomocné moduly:
  - `ocr.py`, `ocr_utils.py` – Funkce pro zpracování obrázků a OCR.
  - `receipt_parser.py`, `receipt_parser_extended.py` – Parsování textu účtenek.
  - `excel_export.py` – Export dat do Excelu.
  - `word_lists.py`, `cell_mapping.py` – Práce se slovníky a mapováním kategorií.
- `data/` – Uživatelská data (slovníky, kategorie, uložené účtenky).
- `localization/` – Překlady a jazykové mutace.
- `styles/` – CSS styly pro případné webové rozhraní.
- `templates/` – Šablony pro export (např. `user_template.xlsx`).
- `assets/`, `attached_assets/` – Obrázky, loga, screenshoty.
- `tests/` – Automatizované testy (pytest).

---

## Jak aplikace funguje

1. **Nahrání účtenky:** Uživatel nahraje fotografii účtenky (přes webové rozhraní nebo CLI).
2. **OCR a předzpracování:** Obrázek je zpracován pomocí Tesseract OCR (`utils/ocr.py`), text je očištěn a připraven k parsování.
3. **Parsování a extrakce dat:** Text je analyzován (`utils/receipt_parser.py`), detekují se položky, ceny, obchod, datum, DPH atd. Využívají se uživatelské slovníky a kategorie.
4. **Uložení a export:** Výsledná data lze uložit do JSON nebo exportovat do Excelu (`utils/excel_export.py`, šablona v `templates/`).
5. **Správa slovníků a kategorií:** Uživatel může upravovat slovníky a kategorie v souborech v `data/` nebo přes UI.

---

## Instalace a spuštění

1. **Klonujte repozitář:**
   ```bash
   git clone https://github.com/CowleyCZE/ScanUctenek.git
   cd ScanUctenek
   ```
2. **Nainstalujte závislosti:**
   ```bash
   pip3 install -r requirements.txt
   ```
3. **Spusťte aplikaci:**
   ```bash
   python3 app.py
   ```
   (nebo spusťte testy: `pytest`)

---

## Požadavky

- Python 3.8+
- Tesseract OCR (lze nainstalovat přes balíček `tesseract-ocr`)
- Knihovny viz `requirements.txt`

---

## Testování

Testy jsou ve složce `tests/` a lze je spustit příkazem:

```bash
pytest
```

---

## Přispívání

Příspěvky jsou vítány! Pro úpravy doporučujeme forknout repozitář, vytvořit větev a poslat pull request. Před odesláním změn spusťte testy.

---

## Licence

Projekt je dostupný pod licencí MIT.
