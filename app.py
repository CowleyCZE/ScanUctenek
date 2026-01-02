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
from typing import Dict, List, Any, Optional, Tuple, Union
from utils.exceptions import OcrError
from utils.ocr_utils import perform_ocr, preprocess_image
from utils.ocr_utils import auto_ocr_optimize
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
    if 'tesseract_cmd' not in st.session_state:
        st.session_state.tesseract_cmd = os.environ.get('TESSERACT_CMD', r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        os.environ['TESSERACT_CMD'] = st.session_state.tesseract_cmd
    # Nové proměnné pro multi-image workflow
    if 'uploaded_images' not in st.session_state:
        st.session_state.uploaded_images = []  # Seznam nahraných obrázků (bytes)
    if 'image_rotations' not in st.session_state:
        st.session_state.image_rotations = {}  # Rotace pro každý index {index: stupně}
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0  # Aktuálně zobrazený obrázek
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}  # Výsledky analýzy {index: {'text': ..., 'info': ...}}

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
        os.environ['OCR_PROFILE'] = os.environ.get('OCR_PROFILE', 'default')
        processed_image = preprocess_image(image_np)
        
        if processed_image is None:
            raise OcrError("Předzpracování obrázku selhalo.")
            
        # Provedení OCR s nastaveným/override jazykem
        override = os.environ.get('OCR_LANG_OVERRIDE', 'auto')
        lang_map = {'cs': 'ces', 'fr': 'fra', 'de': 'deu'}
        initial_lang = lang_map.get(override, 'ces')
        if initial_lang == 'fra':
            os.environ['OCR_PROFILE'] = 'dotmatrix'
        extracted_text, structured_data = perform_ocr(processed_image, initial_lang)
        
        # Detekce jazyka z extrahovaného textu
        detected_language = detect_language(extracted_text)
        lang_code = APP_CONFIG['ocr_language_codes'].get(detected_language, 'ces')
        # Nastavení profilu pro francouzské účtenky (jehličkový/termo tisk)
        if lang_code == 'fra':
            os.environ['OCR_PROFILE'] = 'dotmatrix'
        
        # Pokud je override auto a byl detekován jiný jazyk, provedeme OCR znovu
        if override == 'auto' and lang_code != initial_lang:
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
            
            if image_source == 'camera':
                if not st.session_state.camera_enabled:
                    if st.button("Zapnout kameru"):
                        st.session_state.camera_enabled = True
                        st.rerun()
                else:
                    camera_image = st.camera_input("Pořídit snímek")
                    if camera_image is not None:
                        image_bytes = camera_image.read()
                        # Přidat jako nový obrázek
                        st.session_state.uploaded_images.append(image_bytes)
                        st.session_state.current_image_index = len(st.session_state.uploaded_images) - 1
                        st.rerun()
                    if st.button("Vypnout kameru"):
                        st.session_state.camera_enabled = False
                        st.rerun()
            else:
                uploaded_files = st.file_uploader(
                    "Nahrát obrázky",
                    type=['png', 'jpg', 'jpeg'],
                    accept_multiple_files=True,
                    key='file_uploader'
                )
                
                # Zpracování nahraných souborů
                if uploaded_files:
                    new_images = []
                    for f in uploaded_files:
                        img_bytes = f.read()
                        # Kontrola, zda obrázek již není nahrán (porovnání velikosti)
                        if img_bytes not in st.session_state.uploaded_images:
                            new_images.append(img_bytes)
                    
                    if new_images:
                        st.session_state.uploaded_images.extend(new_images)
                        st.session_state.current_image_index = len(st.session_state.uploaded_images) - len(new_images)
                        st.rerun()

            # Zobrazení náhledu a ovládání, pokud jsou nahrané obrázky
            if st.session_state.uploaded_images:
                total_images = len(st.session_state.uploaded_images)
                current_idx = st.session_state.current_image_index
                
                # Zajištění platného indexu
                if current_idx >= total_images:
                    current_idx = total_images - 1
                    st.session_state.current_image_index = current_idx
                if current_idx < 0:
                    current_idx = 0
                    st.session_state.current_image_index = current_idx
                
                st.markdown(f"**Účtenka {current_idx + 1} z {total_images}**")
                
                # Navigace mezi obrázky
                nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
                with nav_col1:
                    if st.button("◀ Předchozí", disabled=(current_idx == 0)):
                        st.session_state.current_image_index -= 1
                        st.rerun()
                with nav_col3:
                    if st.button("Další ▶", disabled=(current_idx >= total_images - 1)):
                        st.session_state.current_image_index += 1
                        st.rerun()
                
                # Rotace obrázku
                rot_col1, rot_col2 = st.columns([1, 1])
                with rot_col1:
                    if st.button("↻ Otočit o 90°"):
                        current_rotation = st.session_state.image_rotations.get(current_idx, 0)
                        st.session_state.image_rotations[current_idx] = (current_rotation + 90) % 360
                        # Smazat výsledky analýzy při rotaci
                        if current_idx in st.session_state.analysis_results:
                            del st.session_state.analysis_results[current_idx]
                        st.rerun()
                with rot_col2:
                    if st.button("🗑 Odebrat účtenku"):
                        st.session_state.uploaded_images.pop(current_idx)
                        # Aktualizovat rotace a výsledky
                        new_rotations = {}
                        new_results = {}
                        for idx in list(st.session_state.image_rotations.keys()):
                            if idx < current_idx:
                                new_rotations[idx] = st.session_state.image_rotations[idx]
                            elif idx > current_idx:
                                new_rotations[idx - 1] = st.session_state.image_rotations[idx]
                        for idx in list(st.session_state.analysis_results.keys()):
                            if idx < current_idx:
                                new_results[idx] = st.session_state.analysis_results[idx]
                            elif idx > current_idx:
                                new_results[idx - 1] = st.session_state.analysis_results[idx]
                        st.session_state.image_rotations = new_rotations
                        st.session_state.analysis_results = new_results
                        if st.session_state.current_image_index >= len(st.session_state.uploaded_images):
                            st.session_state.current_image_index = max(0, len(st.session_state.uploaded_images) - 1)
                        st.rerun()
                
                # Načtení a zobrazení aktuálního obrázku s rotací
                image_bytes = st.session_state.uploaded_images[current_idx]
                preview = Image.open(io.BytesIO(image_bytes))
                rotation = st.session_state.image_rotations.get(current_idx, 0)
                if rotation != 0:
                    preview = preview.rotate(-rotation, expand=True)  # Záporná hodnota pro clockwise
                st.image(preview, caption=f"Náhled účtenky {current_idx + 1}", use_container_width=True)

        with col2:
            # Tlačítko pro spuštění analýzy
            if st.session_state.uploaded_images:
                current_idx = st.session_state.current_image_index
                
                # Kontrola, zda již existuje výsledek analýzy
                if current_idx in st.session_state.analysis_results:
                    analysis = st.session_state.analysis_results[current_idx]
                    extracted_text = analysis['text']
                    receipt_info = analysis['info']
                else:
                    extracted_text = None
                    receipt_info = None
                
                # Tlačítko pro analýzu
                if st.button("🔍 Analyzovat vybranou účtenku", type="primary"):
                    with st.spinner('Zpracovávám obrázek...'):
                        # Načtení obrázku s rotací
                        image_bytes = st.session_state.uploaded_images[current_idx]
                        image = Image.open(io.BytesIO(image_bytes))
                        rotation = st.session_state.image_rotations.get(current_idx, 0)
                        if rotation != 0:
                            image = image.rotate(-rotation, expand=True)
                        
                        # OCR parametry
                        if 'ocr_params' in st.session_state:
                            used = st.session_state.ocr_params
                            os.environ['OCR_PSM'] = str(used.get('psm', os.environ.get('OCR_PSM','6')))
                            os.environ['OCR_SCALE'] = str(used.get('scale', os.environ.get('OCR_SCALE','1.0')))
                            lang_map_rev = {'ces': 'cs', 'fra': 'fr', 'deu': 'de'}
                            os.environ['OCR_LANG_OVERRIDE'] = lang_map_rev.get(used.get('lang','ces'), os.environ.get('OCR_LANG_OVERRIDE','auto'))
                        
                        extracted_text, _ = process_receipt_image(image)
                        
                        # Auto OCR optimalizace
                        auto_enabled = os.environ.get('OCR_MULTIPASS', '0') in ['1', 'true', 'yes']
                        if auto_enabled:
                            override = os.environ.get('OCR_LANG_OVERRIDE', 'auto')
                            lang_map = {'cs': 'ces', 'fr': 'fra', 'de': 'deu'}
                            init_lang = lang_map.get(override, 'ces')
                            try:
                                det_lang = detect_language(extracted_text)
                                init_lang = lang_map.get(det_lang, init_lang)
                            except Exception:
                                pass
                            if init_lang == 'fra':
                                os.environ['OCR_PROFILE'] = 'dotmatrix'
                            optimized_text, used = auto_ocr_optimize(preprocess_image(np.array(image)), init_lang)
                            if optimized_text.strip():
                                extracted_text = optimized_text
                                os.environ['OCR_PSM'] = str(used['psm'])
                                os.environ['OCR_SCALE'] = str(used['scale'])
                                st.session_state.ocr_params = used
                        
                        if extracted_text:
                            receipt_info = extract_receipt_info(extracted_text)
                            # Uložit výsledky analýzy
                            st.session_state.analysis_results[current_idx] = {
                                'text': extracted_text,
                                'info': receipt_info
                            }
                            st.rerun()
                        else:
                            st.warning("Nepodařilo se extrahovat žádný text. Zkuste účtenku otočit nebo použít jiný obrázek.")
                
                # Zobrazení výsledků analýzy
                if extracted_text and receipt_info:
                    st.subheader("Extrahované informace")
                    with st.expander("Zobrazení OCR textu"):
                        st.text(extracted_text)
                        used_lang = os.environ.get('OCR_LANG_OVERRIDE','auto')
                        if 'ocr_params' in st.session_state:
                            rev = {'ces':'cs','fra':'fr','deu':'de'}
                            used_lang = rev.get(st.session_state.ocr_params.get('lang', used_lang), used_lang)
                        st.caption(f"Použité OCR: PSM={os.environ.get('OCR_PSM','')}, scale={os.environ.get('OCR_SCALE','')}, lang={used_lang}")
                    
                    with st.form(f"receipt_form_{current_idx}"):
                        merchant = st.text_input("Obchodník", value=receipt_info.get('merchant', ''))
                        date = st.date_input("Datum", value=receipt_info.get('date', datetime.now()))
                        total = st.number_input("Celková částka", min_value=0.0, value=float(receipt_info.get('total', 0.0)))
                        currency = st.selectbox("Měna", options=APP_CONFIG['supported_currencies'],
                                                index=APP_CONFIG['supported_currencies'].index(receipt_info.get('currency', APP_CONFIG['default_currency'])))
                        payment_method = st.selectbox("Způsob platby", options=['Kartou', 'Hotovost', 'Neznámý'], index=0)
                        purpose = st.selectbox("Účel", options=['Pohonné hmoty', 'Mýtné', 'Ubytování', 'Stravování', 'Ostatní'], index=0)
                        
                        if st.form_submit_button("Uložit účtenku"):
                            receipt_data = {
                                'merchant': merchant, 'date': date, 'total': total, 'currency': currency,
                                'category': st.session_state.selected_category, 'payment_method': payment_method,
                                'purpose': purpose, 'timestamp': datetime.now()
                            }
                            if save_receipt(receipt_data):
                                st.success("Účtenka byla úspěšně uložena.")
                                # Smazat pouze výsledek analýzy, ne obrázek
                                if current_idx in st.session_state.analysis_results:
                                    del st.session_state.analysis_results[current_idx]
                                # Přejít na další obrázek, pokud existuje
                                if current_idx < len(st.session_state.uploaded_images) - 1:
                                    st.session_state.current_image_index += 1
                                st.rerun()
                            else:
                                st.error("Chyba při ukládání účtenky.")
                elif current_idx not in st.session_state.analysis_results:
                    st.info("Klikněte na tlačítko 'Analyzovat vybranou účtenku' pro spuštění OCR analýzy.")

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
        
        # Nastavení jazyka (UI)
        language = st.selectbox(
            "Jazyk",
            options=list(APP_CONFIG['supported_languages'].keys()),
            format_func=lambda x: APP_CONFIG['supported_languages'][x]
        )
        # OCR jazykový override
        lang_override = st.selectbox("OCR jazyk", options=['auto', 'cs', 'fr', 'de'], index=0)
        os.environ['OCR_LANG_OVERRIDE'] = lang_override
        
        # Nastavení OCR
        ocr_provider = st.radio(
            "OCR poskytovatel",
            ['tesseract', 'google'],
            horizontal=True
        )
        
        if ocr_provider != st.session_state.ocr_provider:
            st.session_state.ocr_provider = ocr_provider
            st.rerun()

        tesseract_cmd_input = st.text_input("Cesta k Tesseract OCR", value=st.session_state.tesseract_cmd)
        if tesseract_cmd_input != st.session_state.tesseract_cmd:
            st.session_state.tesseract_cmd = tesseract_cmd_input
            if tesseract_cmd_input:
                os.environ['TESSERACT_CMD'] = tesseract_cmd_input
            st.rerun()
        if st.session_state.tesseract_cmd:
            if os.path.exists(st.session_state.tesseract_cmd):
                st.success("Cesta k Tesseract je platná")
            else:
                st.error("Cesta k Tesseract není platná")

        st.subheader("OCR parametry")
        psm_value = st.selectbox("PSM (Page Segmentation Mode)", options=[6, 4, 11], index=0)
        conf_thr = st.slider("Confidence threshold", min_value=0, max_value=100, value=40)
        if os.environ.get('OCR_PSM') != str(psm_value) or os.environ.get('OCR_CONF_THRESH') != str(conf_thr):
            os.environ['OCR_PSM'] = str(psm_value)
            os.environ['OCR_CONF_THRESH'] = str(conf_thr)

        scale_value = st.select_slider("Zvětšení (scale)", options=[1.0, 1.5, 2.0], value=1.0)
        deskew_enable = st.checkbox("Odskevení (narovnání textu)", value=True)
        multipass_enable = st.checkbox("Multipass OCR (zkusit více jazyků/PSM)", value=True)
        os.environ['OCR_SCALE'] = str(scale_value)
        os.environ['OCR_DESKEW'] = '1' if deskew_enable else '0'
        os.environ['OCR_MULTIPASS'] = '1' if multipass_enable else '0'
        log_level = st.selectbox("Úroveň logování", options=['INFO', 'DEBUG', 'WARNING'], index=0)
        os.environ['LOG_LEVEL'] = log_level
        try:
            logger.setLevel(getattr(logging, log_level))
        except Exception:
            pass

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
