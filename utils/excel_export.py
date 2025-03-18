import pandas as pd
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from .cell_mapping import get_cell_range, find_next_empty_cell
import os

def export_to_excel(receipts, column_mapping, template_path=None):
    """
    Export receipts to Excel file - only amounts with metadata as comments
    """
    import streamlit as st
    if template_path is None and 'excel_template_path' in st.session_state:
        template_path = st.session_state.excel_template_path

    # Create a BytesIO object to store the Excel file
    output = BytesIO()

    try:
        # Create or load workbook
        if template_path and os.path.exists(template_path):
            workbook = openpyxl.load_workbook(template_path)
        else:
            workbook = openpyxl.Workbook()
            
        # Use first sheet or create new one
        if 'List1' in workbook.sheetnames:
            sheet = workbook['List1']
        else:
            sheet = workbook.active
            sheet.title = 'List1'

        # Set up headers if new sheet
        if sheet['B11'].value is None:
            sheet['B11'] = 'EUR Karta'
            sheet['C11'] = 'EUR Hotově'
            sheet['D11'] = 'CZK Karta'
            sheet['E11'] = 'CZK Hotově'
            
            sheet['A12'] = 'Pohonné hmoty'
            sheet['A20'] = 'Mýtné'
            sheet['A27'] = 'Ubytování'
            sheet['A32'] = 'Ostatní'

        # Process each receipt
        for receipt in receipts:
            try:
                # Get receipt details for cell mapping
                purpose = receipt.get('purpose', 'Ostatní')
                currency = receipt.get('currency', 'CZK')
                payment_method = receipt.get('payment_method', 'Hotovost')
                amount = float(receipt.get('total', 0.0))

                # Get appropriate cell range
                cell_range = get_cell_range(purpose, currency, payment_method)
                if not cell_range:
                    continue

                # Find next empty cell
                cell = find_next_empty_cell(sheet, cell_range)
                if not cell:
                    continue

                # Write amount to cell
                sheet[cell] = amount

                # Add comment with receipt details
                comment_text = (
                    f"Datum: {receipt['date'].strftime('%d.%m.%Y') if isinstance(receipt['date'], datetime) else ''}\n"
                    f"Obchodník: {receipt.get('merchant', '')}\n"
                    f"Číslo účtenky: {receipt.get('receipt_number', '')}"
                )
                comment = Comment(comment_text, "Receipt Details")
                sheet[cell].comment = comment

            except Exception as e:
                print(f"Error processing receipt: {str(e)}")
                continue

        # Save workbook
        workbook.save(output)
        output.seek(0)
        return output

    except Exception as e:
        print(f"Error creating Excel file: {str(e)}")
        raise
