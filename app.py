import streamlit as st
import pandas as pd
import os
import tempfile
import base64
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
from io import BytesIO

from utils.ocr_utils import perform_ocr
from utils.receipt_parser import extract_receipt_info
from utils.excel_export import export_to_excel
from localization.translations import get_text, LANGUAGES, LANGUAGE_NAMES

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
if 'language' not in st.session_state:
    st.session_state.language = 'cs'  # Default to Czech
if 'receipts' not in st.session_state:
    st.session_state.receipts = []
if 'current_receipt' not in st.session_state:
    st.session_state.current_receipt = None
if 'excel_file' not in st.session_state:
    st.session_state.excel_file = None
if 'column_mapping' not in st.session_state:
    st.session_state.column_mapping = {
        'date': 'Datum',
        'total': 'Celková částka',
        'payment_method': 'Způsob platby',
        'merchant': 'Obchodník',
        'receipt_number': 'Číslo účtenky'
    }

def get_svg_content():
    try:
        with open("assets/logo.svg", "r") as f:
            svg_content = f.read()
            # Ensure we're returning properly escaped content
            return svg_content
    except Exception as e:
        # Fallback if the SVG can't be loaded
        print(f"Error loading SVG: {str(e)}")
        return '<div style="color:#2196F3;font-weight:bold;font-size:24px;margin:10px;">SkenÚčtenek</div>'

# Language selector in sidebar
with st.sidebar:
    try:
        st.markdown(get_svg_content(), unsafe_allow_html=True)
    except Exception as e:
        # Fallback if the markdown fails
        print(f"Error displaying SVG: {str(e)}")
        st.write("SkenÚčtenek")
    st.title(get_text('app_name', st.session_state.language))
    
    selected_language = st.selectbox(
        get_text('select_language', st.session_state.language),
        options=LANGUAGES,
        format_func=lambda x: LANGUAGE_NAMES[x],
        index=LANGUAGES.index(st.session_state.language)
    )
    
    if selected_language != st.session_state.language:
        st.session_state.language = selected_language
        st.rerun()

# Main app
st.title(get_text('app_name', st.session_state.language))

# Navigation
tabs = st.tabs([
    get_text('scan_tab', st.session_state.language),
    get_text('history_tab', st.session_state.language),
    get_text('export_tab', st.session_state.language),
    get_text('settings_tab', st.session_state.language)
])

# SCAN TAB
with tabs[0]:
    st.header(get_text('scan_receipt', st.session_state.language))
    
    # Camera input for capturing receipt
    camera_image = st.camera_input(get_text('take_photo', st.session_state.language))
    
    # Alternatively, allow file upload
    uploaded_file = st.file_uploader(get_text('upload_receipt', st.session_state.language), 
                                     type=["jpg", "jpeg", "png"])
    
    # Process the image (from camera or upload)
    receipt_image = None
    if camera_image is not None:
        receipt_image = camera_image
    elif uploaded_file is not None:
        receipt_image = uploaded_file
    
    if receipt_image is not None:
        # Display spinner during processing
        with st.spinner(get_text('processing_receipt', st.session_state.language)):
            # Convert to OpenCV format
            image = Image.open(receipt_image)
            image_np = np.array(image)
            
            # Convert RGB to BGR (if needed)
            if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            
            # Preprocess the image for better OCR results
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            
            # Perform OCR based on the selected language
            ocr_lang = 'ces' if st.session_state.language == 'cs' else ('fra' if st.session_state.language == 'fr' else 'deu')
            extracted_text = perform_ocr(thresh, ocr_lang)
            
            # Extract receipt information
            receipt_info = extract_receipt_info(extracted_text, st.session_state.language)
            
            # Store current receipt in session state
            st.session_state.current_receipt = receipt_info
        
        # Display results and allow editing
        st.subheader(get_text('extracted_info', st.session_state.language))
        
        # Form for editing extracted information
        with st.form(key='receipt_form'):
            col1, col2 = st.columns(2)
            
            with col1:
                merchant = st.text_input(get_text('merchant', st.session_state.language), 
                                      value=receipt_info.get('merchant', ''))
                date = st.date_input(get_text('date', st.session_state.language), 
                                   value=receipt_info.get('date', datetime.now()))
                receipt_number = st.text_input(get_text('receipt_number', st.session_state.language), 
                                             value=receipt_info.get('receipt_number', ''))
            
            with col2:
                total = st.number_input(get_text('total', st.session_state.language), 
                                     value=float(receipt_info.get('total', 0.0)),
                                     min_value=0.0,
                                     step=0.01,
                                     format="%.2f")
                
                payment_options = [
                    get_text('cash', st.session_state.language),
                    get_text('card', st.session_state.language),
                    get_text('other', st.session_state.language)
                ]
                payment_method = st.selectbox(
                    get_text('payment_method', st.session_state.language),
                    options=payment_options,
                    index=payment_options.index(receipt_info.get('payment_method', payment_options[0])) 
                    if receipt_info.get('payment_method') in payment_options else 0
                )
            
            # Raw OCR text for reference
            with st.expander(get_text('show_ocr_text', st.session_state.language)):
                st.text_area("OCR Text", extracted_text, height=200)
            
            # Save button
            submitted = st.form_submit_button(get_text('save_receipt', st.session_state.language))
            
            if submitted:
                try:
                    # Update receipt information with error handling
                    updated_receipt = {
                        'merchant': str(merchant) if merchant else '',
                        'date': date if date else datetime.now(),
                        'receipt_number': str(receipt_number) if receipt_number else '',
                        'total': float(total) if total is not None else 0.0,
                        'payment_method': str(payment_method) if payment_method else '',
                        'ocr_text': str(extracted_text) if extracted_text else '',
                        'timestamp': datetime.now()
                    }
                    
                    # Add to receipts list - ensure we're adding a valid object
                    if not hasattr(st.session_state, 'receipts') or st.session_state.receipts is None:
                        st.session_state.receipts = []
                    
                    # Safely append the receipt
                    st.session_state.receipts.append(updated_receipt)
                    st.success(get_text('receipt_saved', st.session_state.language))
                    
                    # Clear current receipt
                    st.session_state.current_receipt = None
                    
                    # Show success message and clean up
                    st.balloons()
                except Exception as e:
                    # Show error if something goes wrong
                    st.error(f"Chyba při ukládání účtenky: {str(e)}")
                    print(f"Error saving receipt: {str(e)}")
                finally:
                    # Always rerun to refresh the form/page
                    st.rerun()

# HISTORY TAB
with tabs[1]:
    st.header(get_text('receipt_history', st.session_state.language))
    
    if not st.session_state.receipts:
        st.info(get_text('no_receipts', st.session_state.language))
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
                    
                    # Create the expander with safe formatting
                    with st.expander(f"{merchant} - {date_str} - {total_str}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**{get_text('merchant', st.session_state.language)}:** {merchant}")
                            st.write(f"**{get_text('date', st.session_state.language)}:** {date_str}")
                            st.write(f"**{get_text('receipt_number', st.session_state.language)}:** {receipt.get('receipt_number', 'N/A')}")
                        
                        with col2:
                            st.write(f"**{get_text('total', st.session_state.language)}:** {total_str}")
                            st.write(f"**{get_text('payment_method', st.session_state.language)}:** {receipt.get('payment_method', 'N/A')}")
                        
                        # Delete receipt button with error handling
                        if st.button(get_text('delete', st.session_state.language), key=f"delete_{idx}"):
                            try:
                                original_idx = len(st.session_state.receipts) - idx - 1
                                if 0 <= original_idx < len(st.session_state.receipts):
                                    st.session_state.receipts.pop(original_idx)
                                    st.success(get_text('receipt_deleted', st.session_state.language))
                                    st.rerun()
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
                st.rerun()

# EXPORT TAB
with tabs[2]:
    st.header(get_text('export_to_excel', st.session_state.language))
    
    if not st.session_state.receipts:
        st.info(get_text('no_receipts_to_export', st.session_state.language))
    else:
        try:
            # File name for export with validation
            filename = st.text_input(
                get_text('excel_filename', st.session_state.language),
                value="receipts.xlsx"
            )
            
            # Ensure filename has proper extension
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
            
            # Column mapping
            st.subheader(get_text('column_mapping', st.session_state.language))
            
            col_mapping = {}
            col1, col2 = st.columns(2)
            
            # Make sure default mapping exists
            if not hasattr(st.session_state, 'column_mapping') or not st.session_state.column_mapping:
                st.session_state.column_mapping = {
                    'date': 'Datum',
                    'total': 'Celková částka',
                    'payment_method': 'Způsob platby',
                    'merchant': 'Obchodník',
                    'receipt_number': 'Číslo účtenky'
                }
            
            with col1:
                col_mapping['date'] = st.text_input(
                    get_text('date_column', st.session_state.language),
                    value=st.session_state.column_mapping.get('date', 'Datum')
                )
                col_mapping['total'] = st.text_input(
                    get_text('total_column', st.session_state.language),
                    value=st.session_state.column_mapping.get('total', 'Celková částka')
                )
                col_mapping['payment_method'] = st.text_input(
                    get_text('payment_method_column', st.session_state.language),
                    value=st.session_state.column_mapping.get('payment_method', 'Způsob platby')
                )
            
            with col2:
                col_mapping['merchant'] = st.text_input(
                    get_text('merchant_column', st.session_state.language),
                    value=st.session_state.column_mapping.get('merchant', 'Obchodník')
                )
                col_mapping['receipt_number'] = st.text_input(
                    get_text('receipt_number_column', st.session_state.language),
                    value=st.session_state.column_mapping.get('receipt_number', 'Číslo účtenky')
                )
            
            # Update column mapping in session state
            st.session_state.column_mapping = col_mapping
            
            # Export button
            if st.button(get_text('export', st.session_state.language)):
                try:
                    with st.spinner(get_text('exporting', st.session_state.language)):
                        # Convert receipts to DataFrame and export
                        excel_buffer = export_to_excel(st.session_state.receipts, st.session_state.column_mapping)
                        
                        # Create download link
                        b64 = base64.b64encode(excel_buffer.getvalue()).decode()
                        download_button_style = "display:inline-block; padding:10px 20px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:4px; margin:10px 0;"
                        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" style="{download_button_style}">{get_text("download_excel", st.session_state.language)}</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
                        st.success(get_text('export_success', st.session_state.language))
                except Exception as e:
                    st.error(f"Chyba při exportu: {str(e)}")
                    print(f"Export error: {str(e)}")
        except Exception as e:
            st.error(f"Chyba při nastavení exportu: {str(e)}")
            print(f"Export setup error: {str(e)}")

# SETTINGS TAB
with tabs[3]:
    st.header(get_text('settings', st.session_state.language))
    
    # App information
    st.subheader(get_text('about_app', st.session_state.language))
    st.write(get_text('app_description', st.session_state.language))
    
    # Reset data option
    st.subheader(get_text('reset_data', st.session_state.language))
    
    if st.button(get_text('clear_all_receipts', st.session_state.language), type="primary"):
        if st.session_state.receipts:
            # Confirmation
            confirm = st.checkbox(get_text('confirm_delete', st.session_state.language))
            
            if confirm:
                st.session_state.receipts = []
                st.session_state.current_receipt = None
                st.success(get_text('all_receipts_deleted', st.session_state.language))
                st.rerun()
        else:
            st.info(get_text('no_receipts_to_delete', st.session_state.language))

# Footer
st.markdown("---")
st.markdown(f"<p style='text-align: center; color: gray;'>SkenÚčtenek © {datetime.now().year}</p>", unsafe_allow_html=True)
