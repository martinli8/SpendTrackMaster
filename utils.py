import pandas as pd
import numpy as np
from datetime import datetime, date
import calendar
from typing import Dict, List, Any, Optional, Tuple

def get_month_name(month_num: int) -> str:
    """Get month name from month number"""
    return calendar.month_name[month_num]

def calculate_prorated_amount(amount: float, frequency: str) -> float:
    """Calculate monthly prorated amount based on frequency"""
    frequency_multipliers = {
        'monthly': 1.0,
        'quarterly': 1.0 / 3.0,
        'semi-annually': 1.0 / 6.0,
        'annually': 1.0 / 12.0
    }
    
    return amount * frequency_multipliers.get(frequency, 1.0)

def parse_bank_csv(file_content: str, filename: str) -> List[Dict]:
    """Parse bank CSV file and return list of transaction dictionaries"""
    try:
        # Read CSV content
        from io import StringIO
        df = pd.read_csv(StringIO(file_content))
        
        # Standardize column names (remove spaces and make lowercase)
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        transactions = []
        for _, row in df.iterrows():
            # Skip empty rows
            if pd.isna(row.get('description', '')) or row.get('description', '').strip() == '':
                continue
            
            # Parse transaction date
            try:
                if 'transaction_date' in df.columns:
                    trans_date = pd.to_datetime(row['transaction_date']).date()
                elif 'date' in df.columns:
                    trans_date = pd.to_datetime(row['date']).date()
                else:
                    # Use first date column found
                    date_cols = [col for col in df.columns if 'date' in col]
                    if date_cols:
                        trans_date = pd.to_datetime(row[date_cols[0]]).date()
                    else:
                        trans_date = datetime.now().date()
            except:
                trans_date = datetime.now().date()
            
            # Parse post date if available
            post_date = None
            if 'post_date' in df.columns and not pd.isna(row['post_date']):
                try:
                    post_date = pd.to_datetime(row['post_date']).date()
                except:
                    post_date = None
            
            # Parse amount
            try:
                amount = float(row.get('amount', 0))
            except:
                amount = 0.0
            
            # Determine transaction type
            transaction_type = row.get('type', '').strip()
            if not transaction_type:
                # Infer type from amount
                if amount > 0:
                    transaction_type = 'Credit'
                else:
                    transaction_type = 'Debit'
            
            # Categorize based on description
            description = str(row.get('description', '')).strip()
            category = categorize_transaction(description)
            
            transaction = {
                'transaction_date': trans_date,
                'post_date': post_date,
                'description': description,
                'category': category,
                'type': transaction_type,
                'amount': amount,
                'memo': str(row.get('memo', '')).strip(),
                'source_file': filename
            }
            
            transactions.append(transaction)
        
        return transactions
    
    except Exception as e:
        raise ValueError(f"Error parsing CSV file: {str(e)}")

def parse_bank_excel(file_content: bytes, filename: str) -> List[Dict]:
    """Parse bank Excel file and return list of transaction dictionaries"""
    try:
        # Read Excel content
        from io import BytesIO
        df = pd.read_excel(BytesIO(file_content), engine='openpyxl')
        
        # Standardize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        transactions = []
        for _, row in df.iterrows():
            # Skip empty rows
            if pd.isna(row.get('description', '')) or row.get('description', '').strip() == '':
                continue
            
            # Parse transaction date
            try:
                if 'transaction_date' in df.columns:
                    trans_date = pd.to_datetime(row['transaction_date']).date()
                elif 'date' in df.columns:
                    trans_date = pd.to_datetime(row['date']).date()
                else:
                    # Use first date column found
                    date_cols = [col for col in df.columns if 'date' in col]
                    if date_cols:
                        trans_date = pd.to_datetime(row[date_cols[0]]).date()
                    else:
                        trans_date = datetime.now().date()
            except:
                trans_date = datetime.now().date()
            
            # Parse post date if available
            post_date = None
            if 'post_date' in df.columns and not pd.isna(row['post_date']):
                try:
                    post_date = pd.to_datetime(row['post_date']).date()
                except:
                    post_date = None
            
            # Parse amount
            try:
                amount = float(row.get('amount', 0))
            except:
                amount = 0.0
            
            # Determine transaction type
            transaction_type = row.get('type', '').strip()
            if not transaction_type:
                if amount > 0:
                    transaction_type = 'Credit'
                else:
                    transaction_type = 'Debit'
            
            # Categorize based on description
            description = str(row.get('description', '')).strip()
            category = categorize_transaction(description)
            
            transaction = {
                'transaction_date': trans_date,
                'post_date': post_date,
                'description': description,
                'category': category,
                'type': transaction_type,
                'amount': amount,
                'memo': str(row.get('memo', '')).strip(),
                'source_file': filename
            }
            
            transactions.append(transaction)
        
        return transactions
    
    except Exception as e:
        raise ValueError(f"Error parsing Excel file: {str(e)}")

def categorize_transaction(description: str) -> str:
    """Auto-categorize transaction based on description"""
    description_lower = description.lower()
    
    # Grocery stores
    grocery_keywords = [
        'whole foods', 'trader joe', 'safeway', 'kroger', 'walmart', 'target',
        'costco', 'sam\'s club', 'grocery', 'market', 'fresh', 'organic'
    ]
    
    # Shopping
    shopping_keywords = [
        'amazon', 'ebay', 'best buy', 'home depot', 'lowes', 'macy\'s',
        'nordstrom', 'gap', 'old navy', 'h&m', 'zara', 'shopping'
    ]
    
    # Dining
    dining_keywords = [
        'restaurant', 'cafe', 'coffee', 'starbucks', 'mcdonald\'s',
        'burger', 'pizza', 'taco', 'dining', 'food', 'kitchen'
    ]
    
    # Transportation
    transport_keywords = [
        'uber', 'lyft', 'taxi', 'gas', 'shell', 'chevron', 'bp',
        'parking', 'metro', 'bus', 'train', 'airline', 'flight'
    ]
    
    # Utilities
    utility_keywords = [
        'electric', 'gas company', 'water', 'internet', 'phone',
        'cable', 'utility', 'power', 'energy'
    ]
    
    # Entertainment
    entertainment_keywords = [
        'netflix', 'hulu', 'spotify', 'apple music', 'cinema',
        'theater', 'movie', 'concert', 'game', 'entertainment'
    ]
    
    # Check each category
    for keyword in grocery_keywords:
        if keyword in description_lower:
            return 'Groceries'
    
    for keyword in shopping_keywords:
        if keyword in description_lower:
            return 'Shopping'
    
    for keyword in dining_keywords:
        if keyword in description_lower:
            return 'Dining'
    
    for keyword in transport_keywords:
        if keyword in description_lower:
            return 'Transportation'
    
    for keyword in utility_keywords:
        if keyword in description_lower:
            return 'Utilities'
    
    for keyword in entertainment_keywords:
        if keyword in description_lower:
            return 'Entertainment'
    
    # Default category
    return 'Uncategorized'

def validate_file_format(filename: str) -> bool:
    """Validate if file format is supported"""
    supported_extensions = ['.csv', '.xlsx', '.xls']
    return any(filename.lower().endswith(ext) for ext in supported_extensions)

def format_currency(amount: float) -> str:
    """Format amount as currency string"""
    return f"${abs(amount):,.2f}"

def calculate_month_difference(start_date: date, end_date: date) -> int:
    """Calculate number of months between two dates"""
    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

def get_date_range_months(start_date: date, end_date: date) -> List[Tuple[int, int]]:
    """Get list of (year, month) tuples for date range"""
    months = []
    current_date = start_date.replace(day=1)
    
    while current_date <= end_date:
        months.append((current_date.year, current_date.month))
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    return months

def clean_amount_string(amount_str: str) -> float:
    """Clean amount string and convert to float"""
    if pd.isna(amount_str):
        return 0.0
    
    # Remove currency symbols and commas
    cleaned = str(amount_str).replace('$', '').replace(',', '').strip()
    
    # Handle parentheses for negative amounts
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
