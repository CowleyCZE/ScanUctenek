import streamlit as st
import base64
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
import os
import requests

from utils.ocr_utils import perform_ocr
from utils.receipt_parser import extract_receipt_info
from utils.excel_export import export_to_excel
from localization.translations import get_text

# Set page config
st.set_page_config(
    page_title="SkenÚčtenek",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Load and apply custom CSS
with open("styles/main.css") as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Session state initialization
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
    st.session_state.currencies = ['CZK', 'EUR']

def get_svg_content():
    try:
        with open("assets/logo.svg", "r") as f:
            svg_content = f.read()
            # Wrap SVG content in a div for proper rendering
            return f'<div class="logo-container">{svg_content}</div>'
    except Exception as e:
        # Fallback if the SVG can't be loaded
        print(f"Error loading SVG: {str(e)}")
        return '<div style="color:#2196F3;font-weight:bold;font-size:24px;margin:10px;">SkenÚčtenek</div>'

def extract_receipt_data(image_path):
    api_url = "https://gemini.googleapis.com/v1/receipts:analyze"
    api_key = "AIzaSyBvfpvviIHxJgOxkQeVyZCT2rnhyzI7bMo"  # Zde vložte svůj API klíč

    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

    headers = {
        "Content-Type": "application/octet-stream",
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.post(api_url, headers=headers, data=image_data)

    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

# Sidebar with categories
with st.sidebar:
    try:
        st.markdown(get_svg_content(), unsafe_allow_html=True)
    except Exception as e:
        # Fallback if the markdown fails
        print(f"Error displaying SVG: {str(e)}")
        st.write("SkenÚčtenek")
    st.title("SkenÚčtenek")

    st.subheader("Kategorie účtenek")
    category = st.radio(
        "Vyberte kategorii účtenky",
        options=list(st.session_state.receipt_categories.keys()),
        format_func=lambda x: st.session_state.receipt_categories[x]
    )

    if category != st.session_state.selected_category:
        st.session_state.selected_category = category
        st.experimental_rerun()

# Main app
st.title(get_text('app_name', 'cs'))

# Navigation
tabs = st.tabs([
    get_text('scan_tab', 'cs'),
    get_text('receipts_tab', 'cs'),
    get_text('history_tab', 'cs'),
    get_text('export_tab', 'cs'),
    get_text('settings_tab', 'cs')
])

# SCAN TAB
with tabs[0]:
    st.header(get_text('scan_receipt', 'cs'))

    # Camera input for capturing receipt
    camera_image = st.camera_input(get_text('take_photo', 'cs'), key="camera_input")
    if camera_image is not None:
        st.session_state.camera_image = camera_image

    # Alternatively, allow file upload
    uploaded_file = st.file_uploader(get_text('upload_receipt', 'cs'), 
                                     type=["jpg", "jpeg", "png"], key="file_uploader")
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file

    # Process the image (from camera or upload)
    receipt_image = None
    if 'camera_image' in st.session_state and st.session_state.camera_image is not None:
        receipt_image = st.session_state.camera_image
    elif 'uploaded_file' in st.session_state and st.session_state.uploaded_file is not None:
        receipt_image = st.session_state.uploaded_file

    if receipt_image is not None:
        # Display spinner during processing
        with st.spinner(get_text('processing_receipt', 'cs')):
            # Convert to OpenCV format
            image = Image.open(receipt_image)
            image_np = np.array(image)

            # Convert RGB to BGR (if needed)
            if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

            # Preprocess the image for better OCR results
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

            # Try OCR with all supported languages to find the best match
            languages = ['ces', 'fra', 'deu']
            best_text = ""
            detected_language = 'cs'  # Default to Czech

            # Create progress bar for language detection
            lang_progress = st.progress(0)

            for i, lang_code in enumerate(languages):
                lang_name = "češtiny" if lang_code == 'ces' else ("francouzštiny" if lang_code == 'fra' else "němčiny")
                st.write(f"Zkouším rozpoznat text pomocí {lang_name}...")
                lang_progress.progress((i+1)/len(languages))

                # Try OCR with this language
                text = perform_ocr(thresh, lang_code)

                # If text is recognized, remember it and the language
                if text and len(text) > len(best_text):
                    best_text = text
                    detected_language = 'cs' if lang_code == 'ces' else ('fr' if lang_code == 'fra' else 'de')

            # Use the best detected language for further processing
            extracted_text = best_text

            # Extract receipt information with the detected language
            receipt_info = extract_receipt_info(extracted_text, detected_language)

            # Show detected language
            st.success(f"Detekován jazyk účtenky: {detected_language == 'cs' and 'Čeština' or (detected_language == 'fr' and 'Francouzština' or 'Němčina')}")

            # Store current receipt in session state
            st.session_state.current_receipt = receipt_info

        # Display results and allow editing
        st.subheader(get_text('extracted_info', 'cs'))

        # Form for editing extracted information
        with st.form(key='receipt_form'):
            col1, col2 = st.columns(2)

            with col1:
                merchant = st.text_input(get_text('merchant', 'cs'), 
                                      value=receipt_info.get('merchant', ''))
                date = st.date_input(get_text('date', 'cs'), 
                                   value=receipt_info.get('date', datetime.now()))
                receipt_number = st.text_input(get_text('receipt_number', 'cs'), 
                                             value=receipt_info.get('receipt_number', ''))

                # Kategorie účtenky
                category_options = list(st.session_state.receipt_categories.keys())
                category_display = [st.session_state.receipt_categories[k] for k in category_options]
                category_index = 0  # Default to first category

                if 'category' in receipt_info and receipt_info['category'] in category_options:
                    category_index = category_options.index(receipt_info['category'])

                category = st.selectbox(
                    get_text('category', 'cs'),
                    options=category_options,
                    index=category_index,
                    format_func=lambda x: st.session_state.receipt_categories[x]
                )

            with col2:
                total = st.number_input(get_text('total', 'cs'), 
                                     value=float(receipt_info.get('total', 0.0)),
                                     min_value=0.0,
                                     step=0.01,
                                     format="%.2f")

                # Měna
                currency = st.selectbox(
                    get_text('currency', 'cs'),
                    options=st.session_state.currencies,
                    index=0 if receipt_info.get('currency', 'CZK') == 'CZK' else 1
                )

                payment_options = [
                    get_text('cash', 'cs'),
                    get_text('card', 'cs'),
                    get_text('other', 'cs')
                ]
                payment_method = st.selectbox(
                    get_text('payment_method', 'cs'),
                    options=payment_options,
                    index=payment_options.index(receipt_info.get('payment_method', payment_options[0])) 
                    if receipt_info.get('payment_method') in payment_options else 0
                )

            # Značky
            st.subheader(get_text('tags', 'cs'))

            # Existující značky
            existing_tags = receipt_info.get('tags', [])

            # Text input pro novou značku
            new_tag = st.text_input(get_text('add_tag', 'cs'))

            # Zobrazení existujících značek jako chips s možností odstranění
            tag_cols = st.columns(4)  # Až 4 značky na řádek
            updated_tags = []

            for i, tag in enumerate(existing_tags):
                col_idx = i % 4
                with tag_cols[col_idx]:
                    if st.checkbox(f"❌ {tag}", key=f"tag_{i}", value=True):
                        updated_tags.append(tag)

            # Přidání nové značky, pokud byla zadána
            if new_tag and new_tag not in updated_tags:
                updated_tags.append(new_tag)

            # Raw OCR text for reference
            with st.expander(get_text('show_ocr_text', 'cs')):
                st.text_area("OCR Text", extracted_text, height=200)

            # Save button
            submitted = st.form_submit_button(get_text('save_receipt', 'cs'))

            if submitted:
                try:
                    # Update receipt information with error handling
                    updated_receipt = {
                        'merchant': str(merchant) if merchant else '',
                        'date': date if date else datetime.now(),
                        'receipt_number': str(receipt_number) if receipt_number else '',
                        'total': float(total) if total is not None else 0.0,
                        'currency': str(currency) if currency else 'CZK',
                        'payment_method': str(payment_method) if payment_method else '',
                        'category': str(category) if category else 'other',
                        'tags': updated_tags,
                        'ocr_text': str(extracted_text) if extracted_text else '',
                        'timestamp': datetime.now()
                    }

                    # Add to receipts list - ensure we're adding a valid object
                    if not hasattr(st.session_state, 'receipts') or st.session_state.receipts is None:
                        st.session_state.receipts = []

                    # Safely append the receipt
                    st.session_state.receipts.append(updated_receipt)
                    st.success(get_text('receipt_saved', 'cs'))

                    # Clear current receipt
                    st.session_state.current_receipt = None
                    
                    # Reset the scan tab state completely
                    if 'camera_image' in st.session_state:
                        del st.session_state.camera_image
                    if 'uploaded_file' in st.session_state:
                        del st.session_state.uploaded_file
                    
                    # Show success message and clean up
                    st.balloons()
                except Exception as e:
                    # Show error if something goes wrong
                    st.error(f"Chyba při ukládání účtenky: {str(e)}")
                    print(f"Error saving receipt: {str(e)}")
                finally:
                    # Always rerun to refresh the form/page
                    st.experimental_rerun()

# RECEIPTS TAB
with tabs[1]:
    st.header(get_text('receipts', 'cs'))

    # Upload receipt image
    uploaded_receipt = st.file_uploader("Nahrajte účtenku", type=["jpg", "jpeg", "png"])

    if uploaded_receipt is not None:
        # Save uploaded image
        receipt_image_path = f"uploads/{uploaded_receipt.name}"
        with open(receipt_image_path, "wb") as f:
            f.write(uploaded_receipt.getbuffer())

        # Extract data using Gemini API
        try:
            receipt_data = extract_receipt_data(receipt_image_path)
            st.success("Data z účtenky byla úspěšně extrahována.")
            st.json(receipt_data)  # Zobrazte extrahovaná data

            # Zpracujte extrahovaná data a uložte je do session_state
            # Příklad: st.session_state.receipts.append(receipt_data)
        except Exception as e:
            st.error(f"Nepodařilo se extrahovat data z účtenky: {e}")

# HISTORY TAB
with tabs[2]:
    st.header(get_text('receipt_history', 'cs'))

    if not st.session_state.receipts:
        st.info(get_text('no_receipts', 'cs'))
    else:
        try:
            # Display receipts in reverse chronological order
            for idx, receipt in enumerate(reversed(st.session_state.receipts)):
                try:
                    # Safely format the receipt title with error handling
                    merchant = receipt.get('merchant', 'Neznámý obchodník')
                    try:
                        date_str = receipt['date'].strftime('%d.%m.%Y') if isinstance(receipt['date'], datetime) else str(receipt.get('date', 'N/A'))
                    except Exception:
                        date_str = 'N/A'

                    try:
                        total_str = f"{float(receipt.get('total', 0.0)):.2f}"
                    except Exception:
                        total_str = '0.00'

                    # Získat název kategorie pro zobrazení
                    category_key = receipt.get('category', 'other')
                    category_display = st.session_state.receipt_categories.get(category_key, get_text('category_other', 'cs'))

                    # Formátování měny
                    currency = receipt.get('currency', 'CZK')
                    currency_symbol = '€' if currency == 'EUR' else 'Kč' 

                    # Create the expander with safe formatting including category
                    with st.expander(f"{merchant} - {date_str} - {total_str} {currency_symbol} - {category_display}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**{get_text('merchant', 'cs')}:** {merchant}")
                            st.write(f"**{get_text('date', 'cs')}:** {date_str}")
                            st.write(f"**{get_text('receipt_number', 'cs')}:** {receipt.get('receipt_number', 'N/A')}")
                            st.write(f"**{get_text('category', 'cs')}:** {category_display}")

                        with col2:
                            st.write(f"**{get_text('total', 'cs')}:** {total_str} {currency_symbol}")
                            st.write(f"**{get_text('payment_method', 'cs')}:** {receipt.get('payment_method', 'N/A')}")
                            st.write(f"**{get_text('currency', 'cs')}:** {currency}")

                        # Zobrazení značek jako "chips"
                        if receipt.get('tags'):
                            st.write(f"**{get_text('tags', 'cs')}:**")
                            tags_html = ""
                            for tag in receipt.get('tags', []):
                                tags_html += f'<span style="display: inline-block; background-color: #e0e0e0; padding: 2px 10px; margin: 2px; border-radius: 10px;">{tag}</span>'
                            st.markdown(tags_html, unsafe_allow_html=True)

                        # Delete receipt button with error handling
                        if st.button(get_text('delete', 'cs'), key=f"delete_{idx}"):
                            try:
                                original_idx = len(st.session_state.receipts) - idx - 1
                                if 0 <= original_idx < len(st.session_state.receipts):
                                    st.session_state.receipts.pop(original_idx)
                                    st.success(get_text('receipt_deleted', 'cs'))
                                    st.experimental_rerun()
                                else:
                                    st.error("Chyba při mazání účtenky - neplatný index")
                            except Exception as e:
                                st.error(f"Chyba při mazání účtenky: {str(e)}")
                except Exception as e:
                    # If a specific receipt has issues, just skip it
                    st.warning(f"Chyba při zobrazení účtenky: {str(e)}")
                    continue
        except Exception as e:
            # If the whole history fails, show an error
            st.error(f"Chyba při načítání historie účtenek: {str(e)}")
            print(f"Error in receipt history: {str(e)}")
            # Offer a reset button if things are really broken
            if st.button("Resetovat historii účtenek"):
                st.session_state.receipts = []
                st.experimental_rerun()

# EXPORT TAB
with tabs[3]:
    st.header(get_text('export_to_excel', 'cs'))

    if not st.session_state.receipts:
        st.info(get_text('no_receipts_to_export', 'cs'))
    else:
        try:
            # File name for export with validation
            filename = st.text_input(
                get_text('excel_filename', 'cs'),
                value="receipts.xlsx"
            )

            # Ensure filename has proper extension
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'

            # Column mapping
            st.subheader(get_text('column_mapping', 'cs'))

            col_mapping = {}
            col1, col2 = st.columns(2)

            # Make sure default mapping exists
            if not hasattr(st.session_state, 'column_mapping') or not st.session_state.column_mapping:
                st.session_state.column_mapping = {
                    'date': 'Datum',
                    'total': 'Celková částka',
                    'currency': 'Měna',
                    'payment_method': 'Způsob platby',
                    'merchant': 'Obchodník',
                    'receipt_number': 'Číslo účtenky',
                    'category': 'Kategorie',
                    'tags': 'Značky'
                }

            with col1:
                col_mapping['date'] = st.text_input(
                    get_text('date_column', 'cs'),
                    value=st.session_state.column_mapping.get('date', 'Datum')
                )
                col_mapping['total'] = st.text_input(
                    get_text('total_column', 'cs'),
                    value=st.session_state.column_mapping.get('total', 'Celková částka')
                )
                col_mapping['currency'] = st.text_input(
                    get_text('currency', 'cs'),
                    value=st.session_state.column_mapping.get('currency', 'Měna')
                )
                col_mapping['payment_method'] = st.text_input(
                    get_text('payment_method_column', 'cs'),
                    value=st.session_state.column_mapping.get('payment_method', 'Způsob platby')
                )

            with col2:
                col_mapping['merchant'] = st.text_input(
                    get_text('merchant_column', 'cs'),
                    value=st.session_state.column_mapping.get('merchant', 'Obchodník')
                )
                col_mapping['receipt_number'] = st.text_input(
                    get_text('receipt_number_column', 'cs'),
                    value=st.session_state.column_mapping.get('receipt_number', 'Číslo účtenky')
                )
                col_mapping['category'] = st.text_input(
                    get_text('category', 'cs'),
                    value=st.session_state.column_mapping.get('category', 'Kategorie')
                )
                col_mapping['tags'] = st.text_input(
                    get_text('tags', 'cs'),
                    value=st.session_state.column_mapping.get('tags', 'Značky')
                )

            # Update column mapping in session state
            st.session_state.column_mapping = col_mapping

            # Export button
            if st.button(get_text('export', 'cs')):
                try:
                    with st.spinner(get_text('exporting', 'cs')):
                        # Convert receipts to DataFrame and export
                        excel_buffer = export_to_excel(st.session_state.receipts, st.session_state.column_mapping)

                        # Create download link
                        b64 = base64.b64encode(excel_buffer.getvalue()).decode()
                        download_button_style = "display:inline-block; padding:10px 20px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:4px; margin:10px 0;"
                        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" style="{download_button_style}">{get_text("download_excel", "cs")}</a>'
                        st.markdown(href, unsafe_allow_html=True)

                        st.success(get_text('export_success', 'cs'))
                except Exception as e:
                    st.error(f"Chyba při exportu: {str(e)}")
                    print(f"Export error: {str(e)}")
        except Exception as e:
            st.error(f"Chyba při nastavení exportu: {str(e)}")
            print(f"Export setup error: {str(e)}")

# SETTINGS TAB
with tabs[4]:
    st.header(get_text('settings', 'cs'))

    # Create sub-tabs for settings
    settings_tabs = st.tabs([
        "Základní nastavení", 
        "Správa wordlistů", 
        "O aplikaci"
    ])

    # Basic settings tab
    with settings_tabs[0]:
        st.subheader("Nastavení Excel šablony")
        
        # Initialize template path in session state if not exists
        if 'excel_template_path' not in st.session_state:
            st.session_state.excel_template_path = "templates/user_template.xlsx"
        
        # Show current template status
        if st.session_state.excel_template_path:
            st.info(f"Aktuálně používaná šablona: {os.path.basename(st.session_state.excel_template_path)}")
        else:
            st.info("Žádná šablona není nastavena. Při exportu bude vytvořen nový Excel soubor.")
        
        # Reset data option
        st.subheader(get_text('reset_data', 'cs'))

        if st.button(get_text('clear_all_receipts', 'cs'), type="primary"):
            if st.session_state.receipts:
                # Confirmation
                confirm = st.checkbox(get_text('confirm_delete', 'cs'))
                if confirm:
                    st.session_state.receipts = []
                    st.session_state.current_receipt = None
                    st.success(get_text('all_receipts_deleted', 'cs'))
                    st.experimental_rerun()
            else:
                st.info(get_text('no_receipts_to_delete', 'cs'))

    # Wordlist management tab
    with settings_tabs[1]:
        from utils.word_lists import get_all_fields, get_all_languages, get_words, add_word, remove_word, reset_wordlist

        st.subheader("Správa slovníků pro rozpoznávání účtenek")
        st.write("Zde můžete spravovat slovníky klíčových slov, která aplikace využívá pro lepší rozpoznávání údajů v účtenkách.")

        # Dropdown to select field and language
        wordlist_col1, wordlist_col2 = st.columns(2)

        with wordlist_col1:
            selected_field = st.selectbox(
                "Vyberte datové pole:",
                options=get_all_fields(),
                format_func=lambda x: {
                    'date': 'Datum',
                    'total': 'Celková částka',
                    'currency': 'Měna',
                    'payment_method': 'Způsob platby',
                    'merchant': 'Obchodník',
                    'purpose': 'Účel'
                }.get(x, x)
            )

        with wordlist_col2:
            selected_language = st.selectbox(
                "Vyberte jazyk:",
                options=get_all_languages(),
                format_func=lambda x: {
                    'cs': 'Čeština',
                    'fr': 'Francouzština',
                    'de': 'Němčina'
                }.get(x, x)
            )

        # Show current wordlist
        st.subheader(f"Aktuální slova pro pole '{selected_field}' v jazyce '{selected_language}':")
        words = get_words(selected_field, selected_language)

        # Display current words as "chips" with remove option
        if words:
            word_cols = st.columns(3)
            for i, word in enumerate(words):
                col_idx = i % 3
                with word_cols[col_idx]:
                    if st.button(f"❌ {word}", key=f"remove_{selected_field}_{selected_language}_{i}"):
                        if remove_word(selected_field, selected_language, word):
                            st.success(f"Slovo '{word}' bylo odstraněno.")
                            st.rerun()
                        else:
                            st.error(f"Nepodařilo se odstranit slovo '{word}'.")

        else:
            st.info("Pro toto pole a jazyk zatím nejsou definována žádná slova.")

        # Add new word
        st.subheader("Přidat nové slovo:")
        new_word = st.text_input("Zadejte nové slovo", key=f"new_word_{selected_field}_{selected_language}")

        if st.button("Přidat", key=f"add_{selected_field}_{selected_language}"):
            if new_word:
                if add_word(selected_field, selected_language, new_word):
                    st.success(f"Slovo '{new_word}' bylo přidáno.")
                    st.rerun()
                else:
                    st.error(f"Nepodařilo se přidat slovo '{new_word}'.")
            else:
                st.warning("Zadejte slovo, které chcete přidat.")

        # Reset wordlist option
        st.subheader("Resetovat slovník")
        reset_cols = st.columns(3)

        with reset_cols[0]:
            if st.button(f"Resetovat pole '{selected_field}' pro jazyk '{selected_language}'"):
                if reset_wordlist(selected_field, selected_language):
                    st.success(f"Slovník pro pole '{selected_field}' v jazyce '{selected_language}' byl obnoven na výchozí hodnoty.")
                    st.experimental_rerun()
                else:
                    st.error("Nepodařilo se obnovit slovník.")

        with reset_cols[1]:
            if st.button(f"Resetovat celé pole '{selected_field}'"):
                if reset_wordlist(selected_field):
                    st.success(f"Slovník pro pole '{selected_field}' byl obnoven na výchozí hodnoty pro všechny jazyky.")
                    st.rerun()
                else:
                    st.error("Nepodařilo se obnovit slovník.")

        with reset_cols[2]:
            if st.button("Resetovat všechny slovníky"):
                if reset_wordlist():
                    st.success("Všechny slovníky byly obnoveny na výchozí hodnoty.")
                    st.experimental_rerun()
                else:
                    st.error("Nepodařilo se obnovit slovníky.")

    # About tab
    with settings_tabs[2]:
        st.subheader(get_text('about_app', 'cs'))
        st.write(get_text('app_description', 'cs'))

        st.markdown("""
        ## Více informací

        SkenÚčtenek je aplikace pro digitalizaci účtenek a zjednodušení správy výdajů.

        ### Podporované jazyky pro rozpoznávání účtenek:
        - Čeština
        - Francouzština
        - Němčina

        ### Funkce aplikace:
        - Automatické rozpoznání jazyka účtenek
        - Extrakce klíčových údajů (datum, částka, měna, obchodník)
        - Kategorizace výdajů a značkování
        - Export do Excel
        - Správa vlastních slovníků pro lepší rozpoznávání
        """)

        st.info("Pro nejlepší výsledky rozpoznávání doporučujeme používat jasné a kvalitní fotografie účtenek.")

# Footer
st.markdown("---")
st.markdown(f"<p style='text-align: center; color: gray;'>SkenÚčtenek © {datetime.now().year}</p>", unsafe_allow_html=True)
