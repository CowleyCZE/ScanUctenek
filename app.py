"""
Hlavní modul aplikace SkenÚčtenek
Tento modul obsahuje hlavní logiku Streamlit aplikace pro skenování a zpracování účtenek
"""

import streamlit as st
import base64
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
import os
import requests
from typing import Dict, List, Any, Optional, Tuple, Union
from utils.exceptions import OcrError
from utils.ocr_utils import perform_ocr, preprocess_image
from utils.receipt_parser import extract_receipt_info, detect_language
from utils.excel_export import export_to_excel
from localization.translations import get_text
from utils.word_lists import (
    add_field,
    get_all_fields,
    remove_field,
    load_user_categories,
    save_wordlists,
)
import io

# Konfigurace logování
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import APP_CONFIG


def initialize_session_state() -> None:
    """
    Inicializuje proměnné session state.
    """
    if 'ocr_provider' not in st.session_state:
        st.session_state.ocr_provider = 'tesseract'
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = 'other'
    if 'receipts' not in st.session_state:
        st.session_state.receipts = []
    if 'current_receipt' not in st.session_state:
        st.session_state.current_receipt = None
    if 'excel_file' not in st.session_state:
        st.session_state.excel_file = None
    if 'receipt_categories' not in st.session_state:
        # Načtení výchozích a uživatelských kategorií
        user_categories = load_user_categories()
        default_categories = {
            'fuel': get_text('category_fuel', 'cs'),
            'toll': get_text('category_toll', 'cs'),
            'accommodation': get_text('category_accommodation', 'cs'),
            'food': get_text('category_food', 'cs'),
            'other': get_text('category_other', 'cs')
        }
        # Sloučení kategorií
        st.session_state.receipt_categories = {**default_categories, **user_categories}

    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = 'fuel'
    if 'available_tags' not in st.session_state:
        st.session_state.available_tags = []
    if 'currencies' not in st.session_state:
        st.session_state.currencies = APP_CONFIG['supported_currencies']
    if 'camera_enabled' not in st.session_state:
        st.session_state.camera_enabled = False
    if 'image_source' not in st.session_state:
        st.session_state.image_source = 'upload'
    if 'preview_image' not in st.session_state:
        st.session_state.preview_image = None
    if 'image_bytes' not in st.session_state:
        st.session_state.image_bytes = None


def get_svg_content() -> str:
    """
    Získá obsah SVG loga.
    
    Returns:
        str: HTML obsah s logem
    """
    try:
        with open("assets/logo.svg", "r", encoding='utf-8') as f:
            svg_content = f.read()
            return f'<div class="logo-container">{svg_content}</div>'
    except Exception as e:
        logger.error(f"Chyba při načítání SVG: {str(e)}")
        return '<div style="color:#2196F3;font-weight:bold;font-size:24px;margin:10px;">SkenÚčtenek</div>'

def process_receipt_image(image: Image.Image) -> Tuple[str, Dict[str, Any]]:
    """
    Zpracuje obrázek účtenky pomocí OCR.
    
    Args:
        image: Obrázek účtenky (PIL Image)
        
    Returns:
        Tuple[str, Dict[str, Any]]: Extrahovaný text a strukturovaná data
    """
    try:
        # Kontrola, zda je obrázek validní PIL Image
        if not isinstance(image, Image.Image):
            raise OcrError("Vstupní obrázek není platný.")
            
        # Kontrola, zda má obrázek platné rozměry
        if image.size[0] == 0 or image.size[1] == 0:
            raise OcrError("Neplatný obrázek - nulová velikost.")
            
        # Převod na numpy array pro předzpracování
        image_np = np.array(image)
        
        # Převod RGB na BGR pokud je potřeba
        if len(image_np.shape) == 3 and image_np.shape[2] == 3:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            
        # Předzpracování obrázku
        processed_image = preprocess_image(image_np)
        
        if processed_image is None:
            raise OcrError("Předzpracování obrázku selhalo.")
            
        # Provedení OCR s výchozím jazykem
        extracted_text, structured_data = perform_ocr(processed_image, 'ces')
        
        # Detekce jazyka z extrahovaného textu
        detected_language = detect_language(extracted_text)
        lang_code = APP_CONFIG['ocr_language_codes'].get(detected_language, 'ces')
        
        # Pokud byl detekován jiný jazyk, provedeme OCR znovu
        if lang_code != 'ces':
            extracted_text, structured_data = perform_ocr(processed_image, lang_code)
        
        return extracted_text, structured_data
        
    except OcrError as e:
        logger.error(f"Chyba při zpracování obrázku: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Neočekávaná chyba při zpracování obrázku: {str(e)}")
        raise OcrError("Došlo k neočekávané chybě při zpracování obrázku.")

def save_receipt(receipt_data: Dict[str, Any]) -> bool:
    """
    Uloží účtenku do session state.
    
    Args:
        receipt_data: Data účtenky k uložení
        
    Returns:
        bool: Úspěch nebo neúspěch operace
    """
    try:
        if not hasattr(st.session_state, 'receipts') or st.session_state.receipts is None:
            st.session_state.receipts = []
            
        st.session_state.receipts.append(receipt_data)
        return True
        
    except Exception as e:
        logger.error(f"Chyba při ukládání účtenky: {str(e)}")
        return False

def delete_receipt(index: int) -> bool:
    """
    Smaže účtenku z session state.
    
    Args:
        index: Index účtenky k smazání
        
    Returns:
        bool: Úspěch nebo neúspěch operace
    """
    try:
        if 0 <= index < len(st.session_state.receipts):
            st.session_state.receipts.pop(index)
            return True
        return False
        
    except Exception as e:
        logger.error(f"Chyba při mazání účtenky: {str(e)}")
        return False

def process_scan_tab(tab: "st.delta_generator.DeltaGenerator") -> None:
    """
    Zpracuje záložku pro skenování účtenek.
    
    Args:
        tab: Streamlit tab element
    """
    with tab:
        st.subheader("Skenování účtenky")
        
        col1, col2 = st.columns([2, 3])

        with col1:
            # Výběr zdroje obrázku
            image_source = st.radio(
                "Zdroj obrázku",
                ['upload', 'camera'],
                horizontal=True,
                key='image_source_radio'
            )
            
            uploaded_file = None
            if image_source == 'camera':
                if not st.session_state.camera_enabled:
                    if st.button("Zapnout kameru"):
                        st.session_state.camera_enabled = True
                        st.rerun()
                else:
                    uploaded_file = st.camera_input("Pořídit snímek")
                    if st.button("Vypnout kameru"):
                        st.session_state.camera_enabled = False
                        st.rerun()
            else:
                uploaded_file = st.file_uploader(
                    "Nahrát obrázek",
                    type=['png', 'jpg', 'jpeg']
                )

            # Zobrazení náhledu
            if uploaded_file is not None:
                image_bytes = uploaded_file.read()
                st.session_state.image_bytes = image_bytes
                preview = Image.open(io.BytesIO(image_bytes))
                st.session_state.preview_image = preview
                st.image(preview, caption="Náhled účtenky", use_container_width=True)

        with col2:
            # Zpracování obrázku a zobrazení formuláře
            if 'image_bytes' in st.session_state and st.session_state.image_bytes:
                try:
                    with st.spinner('Zpracovávám obrázek...'):
                        image = Image.open(io.BytesIO(st.session_state.image_bytes))
                        extracted_text, _ = process_receipt_image(image)
                    
                    if extracted_text:
                        receipt_info = extract_receipt_info(extracted_text)
                        
                        st.subheader("Extrahované informace")
                        with st.form("receipt_form"):
                            merchant = st.text_input("Obchodník", value=receipt_info.get('merchant', ''))
                            date = st.date_input("Datum", value=receipt_info.get('date', datetime.now()))
                            total = st.number_input("Celková částka", min_value=0.0, value=float(receipt_info.get('total', 0.0)))
                            currency = st.selectbox("Měna", options=APP_CONFIG['supported_currencies'],
                                                    index=APP_CONFIG['supported_currencies'].index(receipt_info.get('currency', APP_CONFIG['default_currency'])))
                            payment_method = st.selectbox("Způsob platby", options=['Kartou', 'Hotovost'], index=0)
                            purpose = st.selectbox("Účel", options=['Pohonné hmoty', 'Mýtné', 'Ubytování', 'Ostatní'], index=0)

                            if st.form_submit_button("Uložit účtenku"):
                                receipt_data = {
                                    'merchant': merchant, 'date': date, 'total': total, 'currency': currency,
                                    'category': st.session_state.selected_category, 'payment_method': payment_method,
                                    'purpose': purpose, 'timestamp': datetime.now()
                                }
                                if save_receipt(receipt_data):
                                    st.success("Účtenka byla úspěšně uložena.")
                                    st.session_state.preview_image = None
                                    st.session_state.image_bytes = None
                                    st.rerun()
                                else:
                                    st.error("Chyba při ukládání účtenky.")
                    else:
                        st.warning("Nepodařilo se extrahovat žádný text. Zkuste prosím jiný obrázek.")
                except OcrError as e:
                    st.error(f"Chyba při zpracování účtenky: {e}")

def get_filtered_receipts(category: str) -> List[Dict[str, Any]]:
    """
    Filtruje účtenky podle kategorie.
    
    Args:
        category: Kategorie pro filtrování
        
    Returns:
        Seznam filtrovaných účtenek
    """
    if not st.session_state.receipts:
        return []
    return [
        r for r in st.session_state.receipts 
        if r.get('category') == category
    ]

def process_history_tab(tab: "st.delta_generator.DeltaGenerator") -> None:
    """
    Zpracuje záložku s historií účtenek.
    
    Args:
        tab: Streamlit tab element
    """
    with tab:
        st.subheader("Historie účtenek")
        
        filtered_receipts = get_filtered_receipts(st.session_state.selected_category)
        
        if not filtered_receipts:
            st.info("V této kategorii nejsou žádné účtenky.")
            return
            
        # Zobrazení účtenek
        for i, receipt in enumerate(filtered_receipts):
            with st.expander(
                f"{receipt.get('merchant', 'Neznámý obchod')} - "
                f"{receipt.get('date', 'Neznámé datum')}"
            ):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Obchodník:** {receipt.get('merchant', '')}")
                    st.write(f"**Datum:** {receipt.get('date', '')}")
                    st.write(f"**Způsob platby:** {receipt.get('payment_method', '')}")
                    st.write(f"**Účel:** {receipt.get('purpose', '')}")
                    
                with col2:
                    st.write(
                        f"**Celková částka:** "
                        f"{receipt.get('total', 0.0)} {receipt.get('currency', '')}"
                    )
                    
                with col3:
                    if st.button("Smazat", key=f"delete_{i}"):
                        st.session_state.receipt_to_delete = i
                        st.rerun()

        if 'receipt_to_delete' in st.session_state:
            receipt_index = st.session_state.receipt_to_delete
            st.warning(f"Opravdu chcete smazat účtenku? Tato akce je nevratná.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Ano, smazat"):
                    if delete_receipt(receipt_index):
                        st.success("Účtenka byla smazána")
                        del st.session_state.receipt_to_delete
                        st.rerun()
                    else:
                        st.error("Chyba při mazání účtenky")
            with col2:
                if st.button("Zrušit"):
                    del st.session_state.receipt_to_delete
                    st.rerun()


def process_export_tab(tab: "st.delta_generator.DeltaGenerator") -> None:
    """
    Zpracuje záložku pro export účtenek.
    
    Args:
        tab: Streamlit tab element
    """
    with tab:
        st.subheader("Export účtenek")
        
        filtered_receipts = get_filtered_receipts(st.session_state.selected_category)
        
        if not filtered_receipts:
            st.info("V této kategorii nejsou žádné účtenky.")
            return
            
        # Export do Excelu
        if st.button("Exportovat do Excelu"):
            try:
                column_mapping = {
                    'date': 'Datum',
                    'merchant': 'Obchodník',
                    'total': 'Celková částka',
                    'payment_method': 'Způsob platby',
                    'purpose': 'Účel',
                    'currency': 'Měna'
                }
                excel_file = export_to_excel(filtered_receipts, column_mapping)
                if excel_file:
                    st.session_state.excel_file = excel_file
                    st.success("Export byl úspěšně dokončen")
                else:
                    st.error("Chyba při exportu do Excelu")
            except Exception as e:
                logger.error(f"Chyba při exportu do Excelu: {str(e)}")
                st.error("Chyba při exportu do Excelu")
                
        # Stažení souboru
        if st.session_state.excel_file:
            st.download_button(
                label="Stáhnout Excel soubor",
                data=st.session_state.excel_file,
                file_name=f"receipts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


def process_settings_tab(tab: "st.delta_generator.DeltaGenerator") -> None:
    """
    Zpracuje záložku s nastavením aplikace.
    
    Args:
        tab: Streamlit tab element
    """
    with tab:
        st.subheader("Nastavení")
        
        # Nastavení jazyka
        language = st.selectbox(
            "Jazyk",
            options=list(APP_CONFIG['supported_languages'].keys()),
            format_func=lambda x: APP_CONFIG['supported_languages'][x]
        )
        
        # Nastavení OCR
        ocr_provider = st.radio(
            "OCR poskytovatel",
            ['tesseract', 'google'],
            horizontal=True
        )
        
        if ocr_provider != st.session_state.ocr_provider:
            st.session_state.ocr_provider = ocr_provider
            st.rerun()

        # Správa kategorií
        st.subheader("Správa kategorií")

        user_categories = load_user_categories()

        # Formulář pro přidání nové kategorie
        with st.form("new_category_form"):
            new_category_name = st.text_input("Název nové kategorie")
            new_category_keywords = st.text_area("Klíčová slova (oddělená čárkou)")

            if st.form_submit_button("Přidat kategorii"):
                if new_category_name and new_category_keywords:
                    keywords = [k.strip() for k in new_category_keywords.split(',')]
                    # Přidání kategorie pro všechny podporované jazyky
                    words_dict = {lang: keywords for lang in APP_CONFIG['supported_languages']}
                    if add_field(new_category_name.lower(), words_dict):
                        st.success(f"Kategorie '{new_category_name}' byla přidána.")
                        st.rerun()
                    else:
                        st.error(f"Kategorie '{new_category_name}' již existuje.")
                else:
                    st.warning("Název kategorie a klíčová slova jsou povinná.")

        # Zobrazení a správa uživatelských kategorií
        st.write("Uživatelské kategorie:")
        for category_name in user_categories.keys():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(category_name)
            with col2:
                if st.button(f"Smazat {category_name}", key=f"delete_{category_name}"):
                    if remove_field(category_name):
                        st.success(f"Kategorie '{category_name}' byla smazána.")
                        st.rerun()
                    else:
                        st.error(f"Chyba při mazání kategorie '{category_name}'.")


def main():
    """
    Hlavní funkce aplikace.
    """
    # Inicializace session state
    initialize_session_state()
    
    # Nastavení stránky
    st.set_page_config(
        page_title="SkenÚčtenek",
        page_icon="📝",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    
    # Načtení CSS
    try:
        with open("styles/main.css", "r", encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Chyba při načítání CSS: {str(e)}")
    
    # Sidebar
    with st.sidebar:
        try:
            st.markdown(get_svg_content(), unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Chyba při zobrazování SVG: {str(e)}")
            st.write("SkenÚčtenek")
        st.title("SkenÚčtenek")
        
        # Kategorie účtenek
        st.subheader("Kategorie účtenek")

        # Načtení všech kategorií
        all_categories = list(st.session_state.receipt_categories.keys())

        category = st.radio(
            "Vyberte kategorii účtenky",
            options=all_categories,
            format_func=lambda x: st.session_state.receipt_categories.get(x, x),
            key='category_radio'
        )
        
        if category != st.session_state.selected_category:
            st.session_state.selected_category = category
            st.rerun()
    
    # Hlavní nadpis
    st.title(get_text('app_name', 'cs'))
    
    # Navigace
    tabs = st.tabs([
        get_text('scan_tab', 'cs'),
        get_text('history_tab', 'cs'),
        get_text('export_tab', 'cs'),
        get_text('settings_tab', 'cs')
    ])
    
    # Zpracování jednotlivých záložek
    process_scan_tab(tabs[0])
    process_history_tab(tabs[1])
    process_export_tab(tabs[2])
    process_settings_tab(tabs[3])
    
    # Patička
    st.markdown("---")
    st.markdown(f"<p style='text-align: center; color: gray;'>SkenÚčtenek © {datetime.now().year}</p>", 
                unsafe_allow_html=True)

if __name__ == "__main__":
    main()
