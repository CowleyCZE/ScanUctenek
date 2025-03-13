
"""
Cell mapping utility for receipt data
Maps combinations of purpose, currency, and payment method to specific Excel cells
"""

# Define cell ranges for different combinations
CELL_MAPPINGS = {
    # Format: (purpose, currency, payment_method): (start_cell, end_cell)
    ('Pohonné hmoty', 'EUR', 'Kartou'): ('B12', 'B19'),
    ('Pohonné hmoty', 'EUR', 'Hotovost'): ('C12', 'C19'),
    ('Pohonné hmoty', 'CZK', 'Kartou'): ('D12', 'D19'),
    ('Pohonné hmoty', 'CZK', 'Hotovost'): ('E12', 'E19'),
    
    ('Mýtné', 'EUR', 'Kartou'): ('B20', 'B26'),
    ('Mýtné', 'EUR', 'Hotovost'): ('C20', 'C26'),
    ('Mýtné', 'CZK', 'Kartou'): ('D20', 'D26'),
    ('Mýtné', 'CZK', 'Hotovost'): ('E20', 'E26'),
    
    ('Bydlení', 'EUR', 'Kartou'): ('B27', 'B31'),
    ('Bydlení', 'EUR', 'Hotovost'): ('C27', 'C31'),
    ('Bydlení', 'CZK', 'Kartou'): ('D27', 'D31'),
    ('Bydlení', 'CZK', 'Hotovost'): ('E27', 'E31'),
    
    ('Ostatní', 'EUR', 'Kartou'): ('B31', 'B39'),
    ('Ostatní', 'EUR', 'Hotovost'): ('C31', 'C39'),
    ('Ostatní', 'CZK', 'Kartou'): ('D31', 'D39'),
    ('Ostatní', 'CZK', 'Hotovost'): ('E31', 'E39'),
}

def get_cell_range(purpose, currency, payment_method):
    """
    Get the appropriate cell range based on purpose, currency, and payment method
    
    Args:
        purpose: The purpose category (e.g., 'Pohonné hmoty', 'Mýtné', etc.)
        currency: The currency (e.g., 'EUR', 'CZK')
        payment_method: The payment method (e.g., 'Kartou', 'Hotovost')
    
    Returns:
        tuple: (start_cell, end_cell) or None if no match
    """
    # Standardize inputs
    if purpose.lower() in ['pohonné hmoty', 'palivo', 'fuel', 'phm', 'benzin', 'nafta', 'diesel']:
        purpose = 'Pohonné hmoty'
    elif purpose.lower() in ['mýtné', 'mýto', 'toll', 'dálniční známka', 'poplatek']:
        purpose = 'Mýtné'
    elif purpose.lower() in ['bydlení', 'ubytování', 'hotel', 'accommodation', 'housing']:
        purpose = 'Bydlení'
    else:
        purpose = 'Ostatní'
    
    # Normalize payment method
    if payment_method.lower() in ['karta', 'kartou', 'card', 'kreditní karta', 'platební karta']:
        payment_method = 'Kartou'
    else:
        payment_method = 'Hotovost'
    
    # Normalize currency
    if currency not in ['EUR', 'CZK']:
        currency = 'CZK'  # Default to CZK if unrecognized
    
    # Look up the cell range
    return CELL_MAPPINGS.get((purpose, currency, payment_method))

def find_next_empty_cell(worksheet, cell_range):
    """
    Find the next empty cell in the given range
    
    Args:
        worksheet: The Excel worksheet object
        cell_range: Tuple of (start_cell, end_cell)
        
    Returns:
        str: Cell reference (e.g., 'B12') or None if all cells in range are filled
    """
    if not cell_range:
        return None
        
    start_cell, end_cell = cell_range
    
    # Extract column letter and row number from start and end cells
    start_col = start_cell[0]
    start_row = int(start_cell[1:])
    end_row = int(end_cell[1:])
    
    # Check each cell in the range
    for row in range(start_row, end_row + 1):
        cell = f"{start_col}{row}"
        if not worksheet[cell].value:
            return cell
    
    # All cells are filled
    return None
