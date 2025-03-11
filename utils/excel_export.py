import pandas as pd
from io import BytesIO

def export_to_excel(receipts, column_mapping):
    """
    Export receipts to Excel file
    
    Args:
        receipts: List of receipt dictionaries to export
        column_mapping: Dictionary mapping receipt fields to Excel column names
    
    Returns:
        BytesIO object containing the Excel file
    """
    # Create a pandas DataFrame from the receipts
    receipts_data = []
    for receipt in receipts:
        receipt_row = {
            column_mapping['date']: receipt['date'],
            column_mapping['merchant']: receipt['merchant'],
            column_mapping['total']: receipt['total'],
            column_mapping['payment_method']: receipt['payment_method'],
            column_mapping['receipt_number']: receipt['receipt_number']
        }
        receipts_data.append(receipt_row)
    
    df = pd.DataFrame(receipts_data)
    
    # Create a BytesIO object to store the Excel file
    output = BytesIO()
    
    # Create Excel writer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Receipts')
        
        # Get the worksheet
        worksheet = writer.sheets['Receipts']
        
        # Set column widths
        for idx, column in enumerate(df.columns):
            column_width = max(len(str(col)) for col in df[column])
            column_width = max(column_width, len(column)) + 4
            # Convert to Excel column letter
            column_letter = chr(65 + idx)  # A, B, C, ...
            worksheet.column_dimensions[column_letter].width = column_width
        
        # Add formatting
        for cell in worksheet[1]:
            cell.font = writer.book.styles['Heading 1'].font
            cell.alignment = cell.alignment.copy(horizontal='center')
    
    # Reset the file pointer to the beginning
    output.seek(0)
    
    return output
