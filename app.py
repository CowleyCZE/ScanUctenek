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
from utils.ocr_utils import perform_ocr, preprocess_image
from utils.receipt_parser import extract_receipt_info, detect_language
from utils.excel_export import export_to_excel
from localization.translations import get_text
import io

# Konfigurace logování
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurace aplikace
APP_CONFIG = {
    'supported_languages': {
        'cs': 'Čeština',
        'fr': 'Francouzština',
        'de': 'Němčina'
    },
    'ocr_language_codes': {
        'cs': 'ces',
        'fr': 'fra',
        'de': 'deu'
    },
    'default_currency': 'CZK',
    'supported_currencies': ['CZK', 'EUR'],
    'receipt_categories': {
        'fuel': 'Pohonné hmoty',
        'toll': 'Mýtné',
        'accommodation': 'Ubytování',
        'food': 'Stravování',
        'other': 'Ostatní'
    }
}

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
        st.session_state.receipt_categories = {
            'fuel': get_text('category_fuel', 'cs'),
            'toll': get_text('category_toll', 'cs'),
            'accommodation': get_text('category_accommodation', 'cs'),
            'food': get_text('category_food', 'cs'),
            'other': get_text('category_other', 'cs')
        }
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
            logger.error("Vstupní obrázek není PIL Image")
            return "", {}
            
        # Kontrola, zda má obrázek platné rozměry
        if image.size[0] == 0 or image.size[1] == 0:
            logger.error("Neplatný obrázek - nulová velikost")
            return "", {}
            
        # Převod na numpy array pro předzpracování
        image_np = np.array(image)
        
        # Převod RGB na BGR pokud je potřeba
        if len(image_np.shape) == 3 and image_np.shape[2] == 3:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            
        # Předzpracování obrázku
        processed_image = preprocess_image(image_np)
        
        if processed_image is None:
            logger.error("Předzpracování obrázku selhalo")
            return "", {}
            
        # Provedení OCR s výchozím jazykem
        extracted_text, structured_data = perform_ocr(processed_image, 'ces')
        
        # Detekce jazyka z extrahovaného textu
        detected_language = detect_language(extracted_text)
        lang_code = APP_CONFIG['ocr_language_codes'].get(detected_language, 'ces')
        
        # Pokud byl detekován jiný jazyk, provedeme OCR znovu
        if lang_code != 'ces':
            extracted_text, structured_data = perform_ocr(processed_image, lang_code)
        
        return extracted_text, structured_data
        
    except Exception as e:
        logger.error(f"Chyba při zpracování obrázku: {str(e)}")
        return "", {}

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

def process_scan_tab(tab: st.tabs) -> None:
    """
    Zpracuje záložku pro skenování účtenek.
    
    Args:
        tab: Streamlit tab element
    """
    with tab:
        st.subheader(get_text('scan_subheader', 'cs'))
        
        # Výběr zdroje obrázku
        col1, col2 = st.columns([1, 3])
        with col1:
            image_source = st.radio(
                get_text('image_source', 'cs'),
                ['upload', 'camera'],
                horizontal=True,
                key='image_source_radio'
            )
            
            if image_source != st.session_state.image_source:
                st.session_state.image_source = image_source
                st.session_state.preview_image = None
                st.rerun()
        
        # Zobrazení náhledu a ovládacích prvků
        col1, col2 = st.columns([2, 2])
        
        with col1:
            uploaded_file = None
            if st.session_state.image_source == 'camera':
                if not st.session_state.camera_enabled:
                    if st.button("Zapnout kameru"):
                        st.session_state.camera_enabled = True
                        st.rerun()
                else:
                    uploaded_file = st.camera_input(get_text('camera_input', 'cs'))
                    if st.button("Vypnout kameru"):
                        st.session_state.camera_enabled = False
                        st.rerun()
            else:
                uploaded_file = st.file_uploader(
                    get_text('file_uploader', 'cs'),
                    type=['png', 'jpg', 'jpeg']
                )
                
        with col2:
            # Zobrazení náhledu
            if uploaded_file is not None:
                try:
                    # Načtení obrázku pro náhled
                    preview = Image.open(uploaded_file)
                    st.session_state.preview_image = preview
                    
                    # Zobrazení náhledu
                    st.image(preview, caption="Náhled účtenky", use_container_width=True)
                    
                    # Reset pozice souboru pro další čtení
                    uploaded_file.seek(0)
                    
                except Exception as e:
                    logger.error(f"Chyba při zobrazení náhledu: {str(e)}")
            elif st.session_state.preview_image is not None:
                st.image(st.session_state.preview_image, caption="Náhled účtenky", use_container_width=True)
            
        if uploaded_file is not None:
            try:
                # Načtení obrázku pro zpracování
                image_bytes = uploaded_file.read()
                image = Image.open(io.BytesIO(image_bytes))
                
                # Zpracování obrázku
                extracted_text, structured_data = process_receipt_image(image)
                
                if extracted_text:
                    # Extrakce informací z textu
                    receipt_info = extract_receipt_info(extracted_text)
                    
                    # Zobrazení výsledků
                    st.subheader(get_text('extracted_info', 'cs'))
                    
                    # Formulář pro úpravu dat
                    with st.form("receipt_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            merchant = st.text_input(
                                get_text('merchant', 'cs'),
                                value=receipt_info.get('merchant', '')
                            )
                            date = st.date_input(
                                get_text('date', 'cs'),
                                value=receipt_info.get('date', datetime.now())
                            )
                            
                        with col2:
                            total = st.number_input(
                                get_text('total', 'cs'),
                                min_value=0.0,
                                value=float(receipt_info.get('total', 0.0))
                            )
                            currency = st.selectbox(
                                get_text('currency', 'cs'),
                                options=APP_CONFIG['supported_currencies'],
                                index=APP_CONFIG['supported_currencies'].index(
                                    receipt_info.get('currency', APP_CONFIG['default_currency'])
                                )
                            )
                            
                        # Uložení účtenky
                        if st.form_submit_button(get_text('save_receipt', 'cs')):
                            receipt_data = {
                                'merchant': merchant,
                                'date': date,
                                'total': total,
                                'currency': currency,
                                'category': st.session_state.selected_category,
                                'timestamp': datetime.now()
                            }
                            
                            if save_receipt(receipt_data):
                                st.success(get_text('receipt_saved', 'cs'))
                                # Vyčištění náhledu po uložení
                                st.session_state.preview_image = None
                                st.rerun()
                            else:
                                st.error(get_text('save_error', 'cs'))
                                
            except Exception as e:
                logger.error(f"Chyba při zpracování obrázku: {str(e)}")
                st.error(get_text('processing_error', 'cs'))

def process_history_tab(tab: st.tabs) -> None:
    """
    Zpracuje záložku s historií účtenek.
    
    Args:
        tab: Streamlit tab element
    """
    with tab:
        st.subheader(get_text('history_subheader', 'cs'))
        
        if not st.session_state.receipts:
            st.info(get_text('no_receipts', 'cs'))
            return
            
        # Filtrování podle kategorie
        filtered_receipts = [
            r for r in st.session_state.receipts 
            if r.get('category') == st.session_state.selected_category
        ]
        
        if not filtered_receipts:
            st.info(get_text('no_receipts_category', 'cs'))
            return
            
        # Zobrazení účtenek
        for i, receipt in enumerate(filtered_receipts):
            with st.expander(
                f"{receipt.get('merchant', 'Neznámý obchod')} - "
                f"{receipt.get('date', 'Neznámé datum')}"
            ):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{get_text('merchant', 'cs')}:** {receipt.get('merchant', '')}")
                    st.write(f"**{get_text('date', 'cs')}:** {receipt.get('date', '')}")
                    
                with col2:
                    st.write(
                        f"**{get_text('total', 'cs')}:** "
                        f"{receipt.get('total', 0.0)} {receipt.get('currency', '')}"
                    )
                    
                with col3:
                    if st.button(get_text('delete', 'cs'), key=f"delete_{i}"):
                        if delete_receipt(i):
                            st.success(get_text('receipt_deleted', 'cs'))
                            st.rerun()
                        else:
                            st.error(get_text('delete_error', 'cs'))

def process_export_tab(tab: st.tabs) -> None:
    """
    Zpracuje záložku pro export účtenek.
    
    Args:
        tab: Streamlit tab element
    """
    with tab:
        st.subheader(get_text('export_subheader', 'cs'))
        
        if not st.session_state.receipts:
            st.info(get_text('no_receipts', 'cs'))
            return
            
        # Filtrování podle kategorie
        filtered_receipts = [
            r for r in st.session_state.receipts 
            if r.get('category') == st.session_state.selected_category
        ]
        
        if not filtered_receipts:
            st.info(get_text('no_receipts_category', 'cs'))
            return
            
        # Export do Excelu
        if st.button(get_text('export_excel', 'cs')):
            try:
                column_mapping = {
                    'date': 'Datum',
                    'merchant': 'Obchodník',
                    'total': 'Celková částka',
                    'payment_method': 'Způsob platby',
                    'receipt_number': 'Číslo účtenky',
                    'purpose': 'Účel',
                    'currency': 'Měna'
                }
                excel_file = export_to_excel(filtered_receipts, column_mapping)
                if excel_file:
                    st.session_state.excel_file = excel_file
                    st.success(get_text('export_success', 'cs'))
                else:
                    st.error(get_text('export_error', 'cs'))
            except Exception as e:
                logger.error(f"Chyba při exportu do Excelu: {str(e)}")
                st.error(get_text('export_error', 'cs'))
                
        # Stažení souboru
        if st.session_state.excel_file:
            st.download_button(
                label=get_text('download_excel', 'cs'),
                data=st.session_state.excel_file,
                file_name=f"receipts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def process_settings_tab(tab: st.tabs) -> None:
    """
    Zpracuje záložku s nastavením aplikace.
    
    Args:
        tab: Streamlit tab element
    """
    with tab:
        st.subheader(get_text('settings_subheader', 'cs'))
        
        # Nastavení jazyka
        language = st.selectbox(
            get_text('language', 'cs'),
            options=list(APP_CONFIG['supported_languages'].keys()),
            format_func=lambda x: APP_CONFIG['supported_languages'][x]
        )
        
        # Nastavení OCR
        ocr_provider = st.radio(
            get_text('ocr_provider', 'cs'),
            ['tesseract', 'google'],
            horizontal=True
        )
        
        if ocr_provider != st.session_state.ocr_provider:
            st.session_state.ocr_provider = ocr_provider
            st.rerun()

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
        category = st.radio(
            "Vyberte kategorii účtenky",
            options=list(APP_CONFIG['receipt_categories'].keys()),
            format_func=lambda x: st.session_state.receipt_categories[x],
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
