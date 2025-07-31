# SkenÚčtenek

SkenÚčtenek je webová aplikace postavená na frameworku Streamlit, která slouží k jednoduchému skenování, zpracování a archivaci účtenek. Aplikace využívá technologii optického rozpoznávání znaků (OCR) k automatické extrakci klíčových informací z nahraných obrázků účtenek.

## Klíčové funkce

- **Skenování účtenek**: Umožňuje nahrát obrázek účtenky z počítače nebo pořídit snímek pomocí kamery.
- **Automatická extrakce dat (OCR)**: Využívá Tesseract OCR k rozpoznání textu na účtence a extrakci údajů jako jsou:
  - Obchodník
  - Datum
  - Celková částka
  - Měna (CZK/EUR)
  - Způsob platby
- **Kategorizace**: Možnost zařadit účtenky do předdefinovaných kategorií (např. Pohonné hmoty, Mýtné, Ubytování) nebo si vytvořit vlastní.
- **Historie a správa**: Ukládání zpracovaných účtenek do historie pro pozdější použití a správu.
- **Export do Excelu**: Možnost exportovat data o účtenkách do souboru `.xlsx` pro další zpracování nebo archivaci.
- **Podpora více jazyků**: Aplikace podporuje češtinu, francouzštinu a němčinu, a to jak v uživatelském rozhraní, tak při zpracování účtenek.
- **Responzivní design**: Díky Streamlitu je aplikace použitelná na různých zařízeních.

## Použité technologie

Aplikace je postavena na následujících technologiích a knihovnách:

- **Frontend**:
  - [Streamlit](https://streamlit.io/): Hlavní framework pro vytvoření interaktivního webového uživatelského rozhraní.

- **Backend & Zpracování dat**:
  - [Python](https://www.python.org/): Programovací jazyk, ve kterém je napsána celá aplikace.
  - [Pandas](https://pandas.pydata.org/): Knihovna pro manipulaci a analýzu dat, použitá pro práci s tabulkovými daty.
  - [NumPy](https://numpy.org/): Knihovna pro numerické operace, využívaná především při zpracování obrázků.

- **Zpracování obrázků a OCR**:
  - [OpenCV (opencv-python-headless)](https://opencv.org/): Knihovna pro počítačové vidění, použitá pro předzpracování obrázků (např. ořez, filtrace šumu).
  - [Pillow (PIL)](https://python-pillow.org/): Knihovna pro práci s obrázky.
  - [Pytesseract](https://github.com/madmaze/pytesseract): Wrapper pro OCR engine Tesseract, který umožňuje extrakci textu z obrázků.

- **Export dat**:
  - [openpyxl](https://openpyxl.readthedocs.io/en/stable/): Knihovna pro čtení a zápis souborů Excel (`.xlsx`).

- **Testování a vývojové nástroje**:
  - [Pytest](https://docs.pytest.org/): Framework pro psaní a spouštění testů.
  - [Black](https://github.com/psf/black): Formátovač kódu pro udržení konzistentního stylu.
  - [Flake8](https://flake8.pycqa.org/en/latest/): Nástroj pro kontrolu kvality kódu a dodržování konvencí.

## Instalace a spuštění

Pro spuštění aplikace na lokálním počítači postupujte podle následujících kroků:

**1. Předpoklady**

- Nainstalovaný [Python](https://www.python.org/downloads/) verze 3.8 nebo vyšší.
- Nainstalovaný [Git](https://git-scm.com/downloads) pro klonování repozitáře.
- Nainstalovaný **Tesseract OCR engine**. Pytesseract je pouze wrapper, takže Tesseract musí být nainstalován v systému.
  - Instalační instrukce naleznete v [dokumentaci Tesseractu](https://tesseract-ocr.github.io/tessdoc/Installation.html).
  - Ujistěte se, že máte nainstalované i jazykové balíčky pro jazyky, které chcete používat (čeština, francouzština, němčina).

**2. Klonování repozitáře**

```bash
git clone https://github.com/vas-projekt/SkenUctenek.git
cd SkenUctenek
```
*(Poznámka: URL adresa repozitáře je zde jako příklad, nahraďte ji skutečnou adresou.)*

**3. Vytvoření a aktivace virtuálního prostředí**

Je doporučeno používat virtuální prostředí, aby se předešlo konfliktům mezi balíčky.

- **Windows**:
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
- **macOS / Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

**4. Instalace závislostí**

Nainstalujte všechny potřebné knihovny pomocí souboru `requirements.txt`.

```bash
pip install -r requirements.txt
```

**5. Spuštění aplikace**

Po úspěšné instalaci závislostí můžete spustit aplikaci.

```bash
streamlit run app.py
```

Aplikace by se měla otevřít ve vašem webovém prohlížeči na adrese `http://localhost:8501`.

## Jak používat aplikaci

Aplikace je rozdělena do několika záložek pro snadnou orientaci.

1.  **Výběr kategorie (v postranním panelu)**
    - V levém postranním panelu si nejprve zvolte kategorii, do které chcete účtenku zařadit (např. `Pohonné hmoty`).

2.  **Skenování účtenky (záložka "Skenování")**
    - Vyberte zdroj obrázku: `Nahrát obrázek` nebo `Použít kameru`.
    - Po nahrání/vyfocení se zobrazí náhled a aplikace automaticky zpracuje obrázek.
    - Zobrazí se formulář s extrahovanými údaji. Zkontrolujte je a případně upravte.
    - Klikněte na tlačítko `Uložit účtenku`.

3.  **Historie účtenek (záložka "Historie")**
    - Zde naleznete seznam všech uložených účtenek pro vybranou kategorii.
    - Účtenky můžete rozkliknout pro zobrazení detailů nebo je smazat.

4.  **Export do Excelu (záložka "Export")**
    - Na této záložce můžete exportovat všechny účtenky z vybrané kategorie do souboru Excel.
    - Klikněte na `Exportovat do Excelu` a následně na `Stáhnout Excel soubor`.

5.  **Nastavení (záložka "Nastavení")**
    - **Změna jazyka**: Změňte jazyk uživatelského rozhraní.
    - **Správa kategorií**:
        - Přidejte si vlastní kategorie pro lepší organizaci. Zadejte název a klíčová slova, která pomohou aplikaci kategorii rozpoznat.
        - Můžete mazat uživatelsky definované kategorie.

## Struktura projektu

Projekt má následující adresářovou strukturu:

```
.
├── app.py                  # Hlavní soubor Streamlit aplikace
├── assets/                 # Statické soubory (logo, obrázky)
├── data/                   # Datové soubory (uživatelské kategorie, slovníky)
├── localization/           # Moduly pro překlady a lokalizaci
├── styles/                 # CSS styly pro úpravu vzhledu
├── templates/              # Šablony (např. pro export do Excelu)
├── tests/                  # Automatizované testy
├── utils/                  # Pomocné moduly pro specifické úkoly:
│   ├── ocr.py              # Logika pro OCR
│   ├── receipt_parser.py   # Extrakce dat z textu účtenky
│   ├── excel_export.py     # Funkce pro export do Excelu
│   └── ...                 # a další...
├── requirements.txt        # Seznam Python závislostí
└── README.md               # Tento soubor
```

## Možnosti přispění

Příspěvky do projektu jsou vítány! Pokud máte nápad na vylepšení nebo jste objevili chybu, neváhejte vytvořit "Issue" nebo "Pull Request" v tomto repozitáři.

## Licence

Tento projekt je distribuován pod licencí MIT. Více informací naleznete v souboru `LICENSE`. (Poznámka: soubor LICENSE není součástí tohoto repozitáře, je třeba ho přidat).
