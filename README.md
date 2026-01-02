
# ScanUctenek

ScanUctenek je open-source aplikace pro automatizované zpracování účtenek a extrakci dat z jejich fotografií pomocí OCR. Umožňuje uživatelům nahrávat účtenky, rozpoznávat položky, exportovat data do Excelu a spravovat vlastní slovníky i kategorie. Projekt je určen pro osobní správu výdajů, digitalizaci účtenek a analýzu nákupů.

---

## Hlavní funkce

- **OCR účtenek:** Automatické rozpoznání textu z obrázků účtenek (využívá Tesseract OCR).
- **Parsování a rozpoznávání položek:** Pokročilé parsování textu účtenky, včetně detekce položek, cen, DPH a obchodů.
- **Export do Excelu:** Možnost exportovat zpracovaná data do přehledné tabulky (XLSX).
- **Uživatelské slovníky:** Uživatel může definovat vlastní kategorie a slovníky pro přesnější rozpoznání položek.
- **Lokalizace:** Podpora vícejazyčného rozhraní (čeština, francouzština, němčina).
- **Webové rozhraní:** Streamlit webové UI pro snadnou správu účtenek.

---

## Podporované kategorie

- **Pohonné hmoty** – účtenky z čerpacích stanic
- **Mýtné** – dálniční poplatky a mýtné
- **Ubytování** – hotely, penziony, apartmány
- **Stravování** – restaurace, jídlo
- **Ostatní** – vše ostatní

---

## Architektura a složky projektu

- `app.py` – Hlavní Streamlit aplikace.
- `config.py` – Konfigurace aplikace (jazyky, měny, kategorie).
- `utils/` – Pomocné moduly:
  - `ocr.py`, `ocr_utils.py` – Funkce pro zpracování obrázků a OCR.
  - `receipt_parser.py` – Parsování textu účtenek.
  - `excel_export.py` – Export dat do Excelu.
  - `cell_mapping.py` – Mapování kategorií na buňky v Excelu.
  - `word_lists.py` – Práce se slovníky pro rozpoznávání.
  - `exceptions.py` – Vlastní výjimky.
  - `pdf_report.py` – Generování PDF reportů.
- `data/` – Uživatelská data (slovníky, kategorie).
- `localization/` – Překlady a jazykové mutace.
- `styles/` – CSS styly pro webové rozhraní.
- `templates/` – Šablony pro export.
- `assets/` – Obrázky a loga.
- `tests/` – Automatizované testy (pytest).

---

## Jak aplikace funguje

1. **Nahrání účtenky:** Uživatel nahraje fotografii účtenky přes webové rozhraní nebo pořídí snímek kamerou.
2. **OCR a předzpracování:** Obrázek je zpracován pomocí Tesseract OCR, text je očištěn a připraven k parsování.
3. **Parsování a extrakce dat:** Text je analyzován, detekují se položky, ceny, obchod, datum, DPH atd.
4. **Uložení a export:** Výsledná data lze uložit nebo exportovat do Excelu.
5. **Správa slovníků a kategorií:** Uživatel může upravovat slovníky a kategorie přes UI.

---

## Instalace a spuštění

1. **Klonujte repozitář:**
   ```bash
   git clone https://github.com/CowleyCZE/ScanUctenek.git
   cd ScanUctenek
   ```

2. **Nainstalujte závislosti:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Nainstalujte Tesseract OCR:**

   **Windows (PowerShell jako administrátor):**
   ```powershell
   # Instalace Tesseract
   winget install UB-Mannheim.TesseractOCR
   
   # Stažení jazykových balíčků (čeština, francouzština, němčina)
   $tessdata = "C:\Program Files\Tesseract-OCR\tessdata"
   @("ces", "fra", "deu") | ForEach-Object { Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/$_.traineddata" -OutFile "$tessdata\$_.traineddata" }
   ```

   **Linux:**
   ```bash
   sudo apt install tesseract-ocr tesseract-ocr-ces tesseract-ocr-fra tesseract-ocr-deu
   ```

   **macOS:**
   ```bash
   brew install tesseract tesseract-lang
   ```

4. **Spusťte aplikaci:**
   ```bash
   streamlit run app.py
   ```

---

## Požadavky

- Python 3.8+
- Tesseract OCR s jazykovými balíčky (ces, fra, deu)
- Knihovny viz `requirements.txt`

---

## Testování

Testy jsou ve složce `tests/` a lze je spustit příkazem:

```bash
pytest -v
```

---

## Přispívání

Příspěvky jsou vítány! Pro úpravy doporučujeme forknout repozitář, vytvořit větev a poslat pull request. Před odesláním změn spusťte testy.

---

## Licence

Projekt je dostupný pod licencí MIT.
