import sqlite3
import os
from datetime import datetime, date
import calendar
from typing import List, Dict, Optional, Tuple

DATABASE_FILE = "spend_tracker.db"

def get_db_connection():
    """Get database connection with proper configuration"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Transactions table for imported bank data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date DATE NOT NULL,
            post_date DATE,
            description TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Uncategorized',
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            memo TEXT,
            source_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Recurring expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recurring_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            frequency TEXT NOT NULL CHECK (frequency IN ('monthly', 'quarterly', 'semi-annually', 'annually')),
            start_date DATE NOT NULL,
            end_date DATE,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Travel budget table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS travel_budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date DATE NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('allocation', 'expense')),
            category TEXT DEFAULT 'Travel',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Income table for tracking income separately from transactions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            income_date DATE NOT NULL,
            description TEXT NOT NULL,
            source TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Categories table for custom categories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('expense', 'income', 'travel')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default categories
    default_categories = [
        ('Fixed', 'expense'),
        ('Utilities', 'expense'),
        ('Bills', 'expense'),
        ('Groceries', 'expense'),
        ('Eating out', 'expense'),
        ('Household Goods', 'expense'),
        ('Travel', 'travel'),
        ('Gas', 'expense'),
        ('Health', 'expense'),
        ('Fun / Misc', 'expense'),
        ('Business School', 'expense'),
        ('Gifts', 'expense'),
        ('Salary', 'income'),
        ('Payments', 'expense'),  # Payments category - excluded from spending totals
        ("Martin's Paycheck", 'income'),
        ("Rachel's Paycheck", 'income'),
        ('Misc Income', 'income'),
        ('Money from Mom', 'income'),
        ('Uncategorized', 'expense')
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)
    """, default_categories)
    
    conn.commit()
    conn.close()

def insert_transactions(transactions_data: List[Dict]) -> int:
    """Insert multiple transactions into the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    for transaction in transactions_data:
        try:
            cursor.execute("""
                INSERT INTO transactions 
                (transaction_date, post_date, description, category, type, amount, memo, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction['transaction_date'],
                transaction.get('post_date'),
                transaction['description'],
                transaction.get('category', 'Uncategorized'),
                transaction['type'],
                float(transaction['amount']),
                transaction.get('memo', ''),
                transaction.get('source_file', '')
            ))
            inserted_count += 1
        except Exception as e:
            print(f"Error inserting transaction: {e}")
            continue
    
    conn.commit()
    conn.close()
    return inserted_count

def get_all_transactions(start_date: date = None, end_date: date = None, limit: int = None) -> List[Dict]:
    """Get all transactions within date range"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM transactions"
    params = []
    
    if start_date or end_date:
        query += " WHERE"
        conditions = []
        
        if start_date:
            conditions.append(" transaction_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append(" transaction_date <= ?")
            params.append(end_date)
        
        query += " AND".join(conditions)
    
    query += " ORDER BY transaction_date DESC"
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query, params)
    transactions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return transactions

def update_transaction_category(transaction_id: int, category: str) -> bool:
    """Update transaction category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE transactions 
        SET category = ? 
        WHERE id = ?
    """, (category, transaction_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def insert_recurring_expense(name: str, category: str, amount: float, frequency: str, start_date: date, end_date: date = None) -> int:
    """Insert a recurring expense"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO recurring_expenses 
        (name, category, amount, frequency, start_date, end_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, category, amount, frequency, start_date, end_date))
    
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return expense_id

def get_recurring_expenses() -> List[Dict]:
    """Get all active recurring expenses"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM recurring_expenses 
        WHERE is_active = 1 
        ORDER BY name
    """)
    
    expenses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return expenses

def delete_recurring_expense(expense_id: int) -> bool:
    """Delete a recurring expense"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE recurring_expenses 
        SET is_active = 0 
        WHERE id = ?
    """, (expense_id,))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def add_travel_allocation(amount: float, date: date = None) -> int:
    """Add monthly travel allocation"""
    if date is None:
        date = datetime.now().date()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO travel_budget 
        (transaction_date, description, amount, type)
        VALUES (?, ?, ?, ?)
    """, (date, "Monthly Travel Allocation", amount, "allocation"))
    
    allocation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return allocation_id

def add_travel_expense(description: str, amount: float, date: date = None) -> int:
    """Add travel expense"""
    if date is None:
        date = datetime.now().date()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO travel_budget 
        (transaction_date, description, amount, type)
        VALUES (?, ?, ?, ?)
    """, (date, description, -abs(amount), "expense"))
    
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return expense_id

def get_travel_budget_balance() -> float:
    """Get current travel budget balance"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) as balance
        FROM travel_budget
    """)
    
    balance = cursor.fetchone()['balance']
    conn.close()
    return balance

def get_travel_transactions(start_date: date = None, end_date: date = None) -> List[Dict]:
    """Get travel budget transactions"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM travel_budget"
    params = []
    
    if start_date or end_date:
        query += " WHERE"
        conditions = []
        
        if start_date:
            conditions.append(" transaction_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append(" transaction_date <= ?")
            params.append(end_date)
        
        query += " AND".join(conditions)
    
    query += " ORDER BY transaction_date DESC"
    
    cursor.execute(query, params)
    transactions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return transactions

def get_categories(category_type: str = None) -> List[str]:
    """Get all categories, optionally filtered by type"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if category_type:
        cursor.execute("SELECT name FROM categories WHERE type = ? ORDER BY name", (category_type,))
    else:
        cursor.execute("SELECT name FROM categories ORDER BY name")
    
    categories = [row['name'] for row in cursor.fetchall()]
    conn.close()
    return categories

def add_category(name: str, category_type: str) -> bool:
    """Add a new category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO categories (name, type) 
            VALUES (?, ?)
        """, (name, category_type))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    
    conn.close()
    return success

def delete_category(category_name: str) -> bool:
    """Delete a category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM categories WHERE name = ?", (category_name,))
        conn.commit()
        success = cursor.rowcount > 0
    except Exception:
        success = False
    
    conn.close()
    return success

def get_all_categories() -> List[Dict]:
    """Get all categories with their types"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, type FROM categories ORDER BY type, name")
    
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return categories

def get_monthly_summary(year: int, month: int) -> Dict:
    """Get summary of all expenses for a given month"""
    from utils import calculate_prorated_amount
    
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    
    # Get imported transactions
    imported_transactions = get_all_transactions(month_start, month_end)
    # Exclude "Payments" category from spending calculations
    imported_expenses = sum(abs(t['amount']) for t in imported_transactions if t['amount'] < 0 and t.get('category', '') != 'Payments')
    
    # Get recurring expenses (prorated for the month)
    recurring_expenses = get_recurring_expenses()
    recurring_total = 0
    for expense in recurring_expenses:
        start_date = datetime.strptime(expense['start_date'], '%Y-%m-%d').date()
        end_date = None
        if expense['end_date']:
            end_date = datetime.strptime(expense['end_date'], '%Y-%m-%d').date()
        
        # Check if the expense is active for this month
        if start_date <= month_end and (end_date is None or end_date >= month_start):
            monthly_amount = calculate_prorated_amount(expense['amount'], expense['frequency'])
            recurring_total += monthly_amount
    
    # Get travel expenses for the month
    travel_transactions = get_travel_transactions(month_start, month_end)
    travel_expenses = sum(abs(t['amount']) for t in travel_transactions if t['type'] == 'expense')
    
    # Get income for the month (from dedicated income table, not transactions)
    month_income = get_monthly_income_total(year, month)
    
    return {
        'imported_expenses': imported_expenses,
        'recurring_expenses': recurring_total,
        'travel_expenses': travel_expenses,
        'income': month_income
    }

def add_transaction(transaction_date: date, description: str, category: str, amount: float, transaction_type: str = 'Debit', memo: str = '') -> int:
    """Add a manual transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO transactions 
        (transaction_date, description, category, type, amount, memo, source_file)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (transaction_date, description, category, transaction_type, amount, memo, 'Manual Entry'))
    
    transaction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return transaction_id

def edit_transaction(transaction_id: int, transaction_date: date = None, description: str = None, category: str = None, amount: float = None) -> bool:
    """Edit a transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if transaction_date is not None:
        updates.append("transaction_date = ?")
        params.append(transaction_date)
    
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    
    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)
    
    if not updates:
        return False
    
    params.append(transaction_id)
    query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, params)
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def get_months_with_data() -> List[Tuple[int, int]]:
    """Get all months that have transaction data, ordered by year/month descending"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT 
            CAST(strftime('%Y', transaction_date) AS INTEGER) as year,
            CAST(strftime('%m', transaction_date) AS INTEGER) as month
        FROM transactions
        ORDER BY year DESC, month DESC
    """)
    
    months = [(row['year'], row['month']) for row in cursor.fetchall()]
    conn.close()
    return months

def delete_transaction(transaction_id: int) -> bool:
    """Delete a transaction"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def bulk_update_transactions(transaction_ids: List[int], transaction_date: date = None, description: str = None, category: str = None, amount: float = None) -> int:
    """Bulk update multiple transactions with the same changes"""
    if not transaction_ids:
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if transaction_date is not None:
        updates.append("transaction_date = ?")
        params.append(transaction_date)
    
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    
    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)
    
    if not updates:
        conn.close()
        return 0
    
    # Create placeholders for IN clause
    placeholders = ','.join('?' * len(transaction_ids))
    params.extend(transaction_ids)
    
    query = f"UPDATE transactions SET {', '.join(updates)} WHERE id IN ({placeholders})"
    
    cursor.execute(query, params)
    updated_count = cursor.rowcount
    conn.commit()
    conn.close()
    return updated_count

def bulk_update_transaction_descriptions(transaction_ids: List[int], find_text: str, replace_text: str) -> int:
    """Bulk update transaction descriptions by finding and replacing text"""
    if not transaction_ids:
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current descriptions
    placeholders = ','.join('?' * len(transaction_ids))
    cursor.execute(f"SELECT id, description FROM transactions WHERE id IN ({placeholders})", transaction_ids)
    transactions = cursor.fetchall()
    
    updated_count = 0
    for row in transactions:
        old_desc = row['description']
        new_desc = old_desc.replace(find_text, replace_text)
        
        if old_desc != new_desc:
            cursor.execute("UPDATE transactions SET description = ? WHERE id = ?", (new_desc, row['id']))
            updated_count += 1
    
    conn.commit()
    conn.close()
    return updated_count

def bulk_adjust_amounts(transaction_ids: List[int], operation: str, value: float) -> int:
    """Bulk adjust transaction amounts (multiply, add, subtract, set)"""
    if not transaction_ids:
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(transaction_ids))
    
    if operation == 'multiply':
        query = f"UPDATE transactions SET amount = amount * ? WHERE id IN ({placeholders})"
        params = [value] + transaction_ids
    elif operation == 'add':
        query = f"UPDATE transactions SET amount = amount + ? WHERE id IN ({placeholders})"
        params = [value] + transaction_ids
    elif operation == 'subtract':
        query = f"UPDATE transactions SET amount = amount - ? WHERE id IN ({placeholders})"
        params = [value] + transaction_ids
    elif operation == 'set':
        query = f"UPDATE transactions SET amount = ? WHERE id IN ({placeholders})"
        params = [value] + transaction_ids
    else:
        conn.close()
        return 0
    
    cursor.execute(query, params)
    updated_count = cursor.rowcount
    conn.commit()
    conn.close()
    return updated_count

def bulk_adjust_dates(transaction_ids: List[int], days: int) -> int:
    """Bulk adjust transaction dates by adding/subtracting days"""
    if not transaction_ids or days == 0:
        return 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(transaction_ids))
    
    if days > 0:
        query = f"UPDATE transactions SET transaction_date = date(transaction_date, '+{days} days') WHERE id IN ({placeholders})"
    else:
        query = f"UPDATE transactions SET transaction_date = date(transaction_date, '{days} days') WHERE id IN ({placeholders})"
    
    cursor.execute(query, transaction_ids)
    updated_count = cursor.rowcount
    conn.commit()
    conn.close()
    return updated_count

def delete_transactions_by_upload_date(start_date: datetime = None, end_date: datetime = None) -> int:
    """Delete transactions based on when they were uploaded (created_at)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "DELETE FROM transactions WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)
    
    cursor.execute(query, params)
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def delete_transactions_by_source_file(source_file: str) -> int:
    """Delete all transactions from a specific source file"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM transactions WHERE source_file = ?", (source_file,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def get_upload_dates() -> List[Dict]:
    """Get list of unique upload dates and source files with transaction counts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            DATE(created_at) as upload_date,
            source_file,
            COUNT(*) as transaction_count,
            MIN(created_at) as first_upload,
            MAX(created_at) as last_upload
        FROM transactions
        WHERE source_file IS NOT NULL AND source_file != ''
        GROUP BY DATE(created_at), source_file
        ORDER BY first_upload DESC
    """)
    
    uploads = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return uploads

def get_transactions_by_upload_date(start_date: datetime = None, end_date: datetime = None, source_file: str = None) -> List[Dict]:
    """Get transactions filtered by upload date and/or source file"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date)
    
    if source_file:
        query += " AND source_file = ?"
        params.append(source_file)
    
    query += " ORDER BY transaction_date DESC"
    
    cursor.execute(query, params)
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return transactions

def ensure_income_table():
    """Ensure the income table exists (for databases created before income table was added)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            income_date DATE NOT NULL,
            description TEXT NOT NULL,
            source TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def add_income_entry(income_date: date, description: str, source: str, amount: float) -> int:
    """Add an income entry to the income table"""
    ensure_income_table()  # Ensure table exists
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO income (income_date, description, source, amount)
        VALUES (?, ?, ?, ?)
    """, (income_date, description, source, amount))
    
    income_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return income_id

def get_income_entries(start_date: date = None, end_date: date = None) -> List[Dict]:
    """Get income entries within date range"""
    ensure_income_table()  # Ensure table exists
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM income WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND income_date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND income_date <= ?"
        params.append(end_date)
    
    query += " ORDER BY income_date DESC"
    
    cursor.execute(query, params)
    income_entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return income_entries

def get_monthly_income_total(year: int, month: int) -> float:
    """Get total income for a given month"""
    ensure_income_table()  # Ensure table exists
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    
    income_entries = get_income_entries(month_start, month_end)
    return sum(entry['amount'] for entry in income_entries)

def get_monthly_income_by_category(year: int, month: int) -> Dict[str, float]:
    """Get monthly income broken down by source"""
    ensure_income_table()  # Ensure table exists
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    
    income_entries = get_income_entries(month_start, month_end)
    income_by_source = {}
    
    for entry in income_entries:
        source = entry.get('source', 'Uncategorized')
        income_by_source[source] = income_by_source.get(source, 0) + entry['amount']
    
    return income_by_source

def edit_income_entry(income_id: int, income_date: date = None, description: str = None, source: str = None, amount: float = None) -> bool:
    """Edit an income entry"""
    ensure_income_table()  # Ensure table exists
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if income_date is not None:
        updates.append("income_date = ?")
        params.append(income_date)
    
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    
    if source is not None:
        updates.append("source = ?")
        params.append(source)
    
    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)
    
    if not updates:
        conn.close()
        return False
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(income_id)
    
    query = f"UPDATE income SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, params)
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def delete_income_entry(income_id: int) -> bool:
    """Delete an income entry"""
    ensure_income_table()  # Ensure table exists
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM income WHERE id = ?", (income_id,))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def get_income_categories() -> List[str]:
    """Get list of income sources"""
    return ["Martin's Paycheck", "Rachel's Paycheck", "Misc Income", "Money from Mom"]
