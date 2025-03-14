import pandas as pd
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from .cell_mapping import get_cell_range, find_next_empty_cell
import os  # Přidaný chybějící import

def export_to_excel(receipts, column_mapping, template_path=None):
    """
    Export receipts to Excel file

    Args:
        receipts: List of receipt dictionaries to export
        column_mapping: Dictionary mapping receipt fields to Excel column names
        template_path: Optional path to Excel template file

    Returns:
        BytesIO object containing the Excel file
    """

    # Check for template in session state if not provided explicitly
    import streamlit as st
    if template_path is None and 'excel_template_path' in st.session_state and st.session_state.excel_template_path:
        template_path = st.session_state.excel_template_path

    # Create a pandas DataFrame from the receipts for the general sheet
    receipts_data = []
    for receipt in receipts:
        try:
            # Format date as string to avoid timezone issues
            date_str = receipt['date'].strftime('%d.%m.%Y') if isinstance(receipt['date'], datetime) else str(receipt['date'])
            
            receipt_row = {
                column_mapping['date']: date_str,
                column_mapping['merchant']: str(receipt['merchant']),
                column_mapping['total']: float(receipt['total']),
                column_mapping['payment_method']: str(receipt['payment_method']),
                column_mapping['receipt_number']: str(receipt['receipt_number']),
                column_mapping.get('purpose', 'Účel'): str(receipt.get('purpose', '')),
                column_mapping.get('currency', 'Měna'): str(receipt.get('currency', 'CZK'))
            }
            receipts_data.append(receipt_row)
        except Exception as e:
            print(f"Error processing receipt for Excel: {str(e)}")
            continue

    # Create DataFrame with proper data types
    df = pd.DataFrame(receipts_data)

    # Create a BytesIO object to store the Excel file
    output = BytesIO()

    try:
        # Check if we're using a template
        if template_path and os.path.exists(template_path):
            # Load the existing template
            workbook = openpyxl.load_workbook(template_path)
            writer = pd.ExcelWriter(output, engine='openpyxl')
            writer.book = workbook
            writer.sheets = {ws.title: ws for ws in workbook.worksheets}  # Přidaná řádka pro správnou práci s existujícími listy
            
            # Create the main receipts sheet if it doesn't exist
            if 'Receipts' not in writer.sheets:
                df.to_excel(writer, index=False, sheet_name='Receipts')
                # Format the main sheet
                format_main_sheet(writer, df)
            
            # Create and format the mapped sheet
            create_mapped_sheet(writer, receipts)
        else:
            # Create a new workbook
            writer = pd.ExcelWriter(output, engine='openpyxl', mode='w')
            
            # Create the main receipts sheet
            df.to_excel(writer, index=False, sheet_name='Receipts')
            
            # Format the main sheet
            format_main_sheet(writer, df)
            
            # Create and format the mapped sheet
            create_mapped_sheet(writer, receipts)
    except Exception as e:
        print(f"Error creating Excel file: {str(e)}")
        # Create a simple Excel file as a fallback
        df.to_excel(output, index=False, sheet_name='Receipts')

    # Save the workbook
    try:
        writer.close()  # Používáme close místo save, protože to automaticky zavolá save() a pak uklidí zdroje
    except Exception as e:
        print(f"Error saving Excel file: {str(e)}")

    # Reset the file pointer to the beginning
    output.seek(0)

    return output


def format_main_sheet(writer, df):
    """Format the main receipts sheet"""
    try:
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Receipts']
        
        # Add headers formatting
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Write the column headers with the header format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # Auto-fit columns
        for column in df:
            column_width = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            worksheet.set_column(col_idx, col_idx, column_width)
    except Exception as e:
        print(f"Error formatting main sheet: {str(e)}")


def create_mapped_sheet(writer, receipts):
    """Create a sheet with data mapped to specific cells"""
    try:
        # Create a new sheet for the mapped data if it doesn't exist
        workbook = writer.book
        
        if 'Mapped Data' in workbook.sheetnames:
            mapped_sheet = workbook['Mapped Data']
        else:
            mapped_sheet = workbook.create_sheet(title='Mapped Data')
        
        # Set up the basic structure if it's a new sheet
        if 'B11' not in mapped_sheet or mapped_sheet['B11'].value is None:
            # Headers for columns
            mapped_sheet['B11'] = 'EUR Karta'
            mapped_sheet['C11'] = 'EUR Hotově'
            mapped_sheet['D11'] = 'CZK Karta'
            mapped_sheet['E11'] = 'CZK Hotově'
            
            # Category labels
            mapped_sheet['A12'] = 'Pohonné hmoty'
            mapped_sheet['A20'] = 'Mýtné'
            mapped_sheet['A27'] = 'Bydlení'
            mapped_sheet['A31'] = 'Ostatní'
        
        # Process each receipt and place it in the appropriate cell
        for receipt in receipts:
            try:
                # Get the receipt details
                purpose = receipt.get('purpose', 'Ostatní')
                currency = receipt.get('currency', 'CZK')
                payment_method = receipt.get('payment_method', 'Hotovost')
                amount = receipt.get('total', 0.0)
                date_str = receipt['date'].strftime('%d.%m.%Y') if isinstance(receipt['date'], datetime) else ""
                
                # Get the cell range for this combination
                cell_range = get_cell_range(purpose, currency, payment_method)
                
                # Find the next empty cell in the range
                cell = find_next_empty_cell(mapped_sheet, cell_range)
                
                # If a cell was found, write the data
                if cell:
                    mapped_sheet[cell] = amount
                    
                    # Add a comment with additional details - upravená část pro správné vytváření komentářů
                    from openpyxl.comments import Comment
                    comment_text = f"Datum: {date_str}\nObchodník: {receipt.get('merchant', '')}"
                    comment = Comment(comment_text, "Receipt Parser")
                    mapped_sheet[cell].comment = comment
            except Exception as e:
                print(f"Error mapping receipt to cell: {str(e)}")
                continue
    except Exception as e:
        print(f"Error creating mapped sheet: {str(e)}")
