
import pandas as pd
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.utils import get_column_letter
from .cell_mapping import get_cell_range, find_next_empty_cell

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
        writer.close()
    except Exception as e:
        print(f"Error saving Excel file: {str(e)}")
    
    # Reset the file pointer to the beginning
    output.seek(0)
    
    return output

def format_main_sheet(writer, df):
    """Format the main receipts sheet"""
    try:
        worksheet = writer.sheets['Receipts']
        
        # Set column widths with better overflow handling
        for idx, column in enumerate(df.columns):
            # Get max width considering reasonable limits
            max_width = 0
            for val in df[column]:
                val_str = str(val)
                # Limit string length to avoid excessive column widths
                width = min(len(val_str), 50)
                max_width = max(max_width, width)
            
            # Apply width calculation with sensible boundaries
            column_width = min(max(max_width, len(column)) + 4, 60)
            
            # Convert to Excel column letter
            column_letter = get_column_letter(idx + 1)
            worksheet.column_dimensions[column_letter].width = column_width
        
        # Add formatting to header row
        for cell in worksheet[1]:
            # Create bold font for header
            from openpyxl.styles import Font, Alignment
            cell.font = Font(bold=True, size=12)
            cell.alignment = Alignment(horizontal='center')
    except Exception as e:
        print(f"Error formatting Excel worksheet: {str(e)}")

def create_mapped_sheet(writer, receipts):
    """Create a sheet with data mapped to specific cells"""
    try:
        # Create a new sheet for the mapped data
        workbook = writer.book
        mapped_sheet = workbook.create_sheet(title='Mapped Data')
        
        # Set up the basic structure
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
                    # Add a comment with additional details
                    comment_text = f"Datum: {date_str}\nObchodník: {receipt.get('merchant', '')}"
                    mapped_sheet[cell].comment = openpyxl.comments.Comment(comment_text, "Receipt Parser")
            except Exception as e:
                print(f"Error mapping receipt to cell: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error creating mapped sheet: {str(e)}")

# Add support for the os module
import os
