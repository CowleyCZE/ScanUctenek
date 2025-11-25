import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.pdf_report import create_pdf_report

def main():
    title = "Ověření výsledků zpracování účtenky (AVIA)"
    acceptance = (
        "Byl přijat screenshot s výsledkem testu a obrázek testovací účtenky."
        " Oba jsou dle vizuální kontroly kompletní a čitelné (vysoké rozlišení,"
        " mírné odlesky bez zásadního vlivu)."
    )
    comparison = [
        ("Obchodník", "(prázdné)", "AVIA"),
        ("Datum", "2025/11/24", "09.11.2023"),
        ("Celková částka", "82,38", "150,00"),
        ("Měna", "CZK", "EUR"),
        ("Způsob platby", "Kartou", "Kartou (Debit Mastercard)"),
        ("Účel", "Pohonné hmoty", "Pohonné hmoty"),
        ("Množství", "—", "82,38 L"),
        ("Cena/litr", "—", "1,821 EUR/L"),
    ]
    issues = [
        "Obchodník nerozpoznán (má být AVIA).",
        "Datum převzato jako systémové místo 'LE 09-11-23'.",
        "Celková částka vzata z množství paliva (82,38 L).",
        "Měna detekována jako CZK; na účtence je EUR.",
    ]
    recommendations = [
        "Použít PSM=4 pro tabulkově formátované účtenky, threshold 40–50.",
        "Preferovat řádky 'MONTANT NET' / 'NET À PAYER' pro total (implementováno).",
        "Normalizovat text obchodníka (implementováno: detekce 'AVIA' i s mezerami).",
        "Upřednostnit měnu přímo na řádku s celkovou částkou (implementováno).",
        "Znovu nahrát obrázek po úpravách a ověřit výsledky v aplikaci.",
    ]
    out_path = os.path.join("output", "verification_report_AVIA.pdf")
    create_pdf_report(title, acceptance, comparison, issues, recommendations, out_path)
    print(out_path)

if __name__ == "__main__":
    main()
