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

def get_monthly_summary(year: int, month: int) -> Dict:
    """Get summary of all expenses for a given month"""
    from utils import calculate_prorated_amount
    
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    
    # Get imported transactions
    imported_transactions = get_all_transactions(month_start, month_end)
    imported_expenses = sum(abs(t['amount']) for t in imported_transactions if t['amount'] < 0)
    
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
    
    return {
        'imported_expenses': imported_expenses,
        'recurring_expenses': recurring_total,
        'travel_expenses': travel_expenses
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
