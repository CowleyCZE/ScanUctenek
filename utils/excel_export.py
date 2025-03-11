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
        try:
            # Format date as string to avoid timezone issues
            date_str = receipt['date'].strftime('%d.%m.%Y') if isinstance(receipt['date'], datetime) else str(receipt['date'])
            
            receipt_row = {
                column_mapping['date']: date_str,
                column_mapping['merchant']: str(receipt['merchant']),
                column_mapping['total']: float(receipt['total']),
                column_mapping['payment_method']: str(receipt['payment_method']),
                column_mapping['receipt_number']: str(receipt['receipt_number'])
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
        # Create Excel writer with improved error handling
        with pd.ExcelWriter(output, engine='openpyxl', mode='w') as writer:
            # Export to Excel sheet
            df.to_excel(writer, index=False, sheet_name='Receipts')
            
            # Get the worksheet
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
                    column_letter = chr(65 + idx) if idx < 26 else chr(64 + idx // 26) + chr(65 + idx % 26)
                    worksheet.column_dimensions[column_letter].width = column_width
                
                # Add formatting to header row
                for cell in worksheet[1]:
                    cell.font = writer.book.styles['Heading 1'].font
                    cell.alignment = cell.alignment.copy(horizontal='center')
            except Exception as e:
                print(f"Error formatting Excel worksheet: {str(e)}")
    except Exception as e:
        print(f"Error creating Excel file: {str(e)}")
        # Create a simple Excel file as a fallback
        df.to_excel(output, index=False, sheet_name='Receipts')
    
    # Reset the file pointer to the beginning
    output.seek(0)
    
    return output
