import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from database import get_all_transactions, update_transaction_category, get_categories, add_category
from utils import format_currency

st.set_page_config(
    page_title="Categorize Transactions",
    page_icon="🏷️",
    layout="wide"
)

st.title("🏷️ Categorize Transactions")
st.markdown("Review and categorize your imported transactions for better spending insights.")

# Sidebar filters
st.sidebar.header("Filters")

# Date range filter
date_range = st.sidebar.selectbox(
    "Date Range",
    options=["Last 30 days", "Last 90 days", "This Year", "Custom Range"],
    index=0
)

if date_range == "Last 30 days":
    start_date = datetime.now().date() - timedelta(days=30)
    end_date = datetime.now().date()
elif date_range == "Last 90 days":
    start_date = datetime.now().date() - timedelta(days=90)
    end_date = datetime.now().date()
elif date_range == "This Year":
    start_date = date(datetime.now().year, 1, 1)
    end_date = datetime.now().date()
else:  # Custom Range
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.sidebar.date_input(
            "Start Date",
            value=datetime.now().date() - timedelta(days=30)
        )
    with col2:
        end_date = st.sidebar.date_input(
            "End Date",
            value=datetime.now().date()
        )

# Category filter
all_categories = get_categories()
selected_categories = st.sidebar.multiselect(
    "Filter by Categories",
    options=all_categories,
    default=[]
)

# Amount filter
amount_filter = st.sidebar.selectbox(
    "Amount Filter",
    options=["All", "Expenses Only", "Income Only", "> $100", "> $50", "< $50"]
)

# Get transactions with filters
transactions = get_all_transactions(start_date, end_date)

if not transactions:
    st.info("No transactions found for the selected date range.")
    st.stop()

# Apply filters
df = pd.DataFrame(transactions)

# Category filter
if selected_categories:
    df = df[df['category'].isin(selected_categories)]

# Amount filter
if amount_filter == "Expenses Only":
    df = df[df['amount'] < 0]
elif amount_filter == "Income Only":
    df = df[df['amount'] > 0]
elif amount_filter == "> $100":
    df = df[abs(df['amount']) > 100]
elif amount_filter == "> $50":
    df = df[abs(df['amount']) > 50]
elif amount_filter == "< $50":
    df = df[abs(df['amount']) < 50]

if df.empty:
    st.warning("No transactions match your current filters.")
    st.stop()

# Summary statistics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_transactions = len(df)
    st.metric("Total Transactions", total_transactions)

with col2:
    uncategorized_count = len(df[df['category'] == 'Uncategorized'])
    st.metric("Uncategorized", uncategorized_count)

with col3:
    total_expenses = abs(df[df['amount'] < 0]['amount'].sum())
    st.metric("Total Expenses", format_currency(total_expenses))

with col4:
    unique_categories = df['category'].nunique()
    st.metric("Categories Used", unique_categories)

# Categorization interface
st.markdown("---")
st.subheader("Bulk Categorization")

# Option 1: Bulk update by description pattern
with st.expander("Bulk Categorize by Description Pattern", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        pattern_text = st.text_input(
            "Description contains",
            placeholder="e.g., AMAZON, STARBUCKS",
            help="Find transactions containing this text"
        )
        
        if pattern_text:
            matching_transactions = df[df['description'].str.contains(pattern_text, case=False, na=False)]
            st.write(f"Found {len(matching_transactions)} transactions matching '{pattern_text}'")
    
    with col2:
        new_category = st.selectbox(
            "New Category",
            options=all_categories,
            key="bulk_category"
        )
        
        # Option to add new category
        if st.checkbox("Add new category", key="bulk_new_cat"):
            new_cat_name = st.text_input("New Category Name", key="bulk_new_cat_name")
            if new_cat_name and st.button("Create Category", key="bulk_create_cat"):
                if add_category(new_cat_name, 'expense'):
                    st.success(f"Added new category: {new_cat_name}")
                    st.rerun()
                else:
                    st.error("Category already exists")
    
    if pattern_text and st.button("Apply Bulk Categorization"):
        matching_ids = matching_transactions['id'].tolist()
        success_count = 0
        
        for trans_id in matching_ids:
            if update_transaction_category(trans_id, new_category):
                success_count += 1
        
        st.success(f"Updated {success_count} transactions to category: {new_category}")
        st.rerun()

# Option 2: Individual transaction categorization
st.markdown("---")
st.subheader("Individual Transaction Review")

# Pagination
transactions_per_page = 20
total_pages = (len(df) - 1) // transactions_per_page + 1

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    current_page = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1,
        key="page_number"
    )

start_idx = (current_page - 1) * transactions_per_page
end_idx = min(start_idx + transactions_per_page, len(df))
page_transactions = df.iloc[start_idx:end_idx].copy()

# Display transactions for categorization
for idx, (_, transaction) in enumerate(page_transactions.iterrows()):
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([2, 3, 1, 1.5, 1])
        
        with col1:
            st.write(f"**{transaction['transaction_date']}**")
        
        with col2:
            st.write(f"{transaction['description'][:50]}...")
        
        with col3:
            amount_color = "red" if transaction['amount'] < 0 else "green"
            st.markdown(f"<span style='color:{amount_color}'>{format_currency(transaction['amount'])}</span>", unsafe_allow_html=True)
        
        with col4:
            current_category = transaction['category']
            new_category = st.selectbox(
                "Category",
                options=all_categories,
                index=all_categories.index(current_category) if current_category in all_categories else 0,
                key=f"cat_{transaction['id']}",
                label_visibility="collapsed"
            )
        
        with col5:
            if new_category != current_category:
                if st.button("Update", key=f"update_{transaction['id']}"):
                    if update_transaction_category(transaction['id'], new_category):
                        st.success("Updated!")
                        st.rerun()
                    else:
                        st.error("Failed to update")

# Show page info
st.markdown(f"Showing transactions {start_idx + 1}-{end_idx} of {len(df)}")

# Quick categorization suggestions
st.markdown("---")
st.subheader("Smart Categorization Suggestions")

# Find uncategorized transactions and suggest categories
uncategorized = df[df['category'] == 'Uncategorized']

if not uncategorized.empty:
    st.write("**Uncategorized transactions that might be easy to categorize:**")
    
    # Common patterns
    patterns = {
        'Amazon': 'Shopping',
        'Whole Foods': 'Groceries',
        'Starbucks': 'Dining',
        'Shell': 'Transportation',
        'McDonald': 'Dining',
        'Netflix': 'Entertainment',
        'Spotify': 'Entertainment'
    }
    
    suggestions = []
    for pattern, suggested_category in patterns.items():
        matches = uncategorized[uncategorized['description'].str.contains(pattern, case=False, na=False)]
        if not matches.empty:
            suggestions.append({
                'Pattern': f"Contains '{pattern}'",
                'Count': len(matches),
                'Suggested Category': suggested_category,
                'Action': pattern
            })
    
    if suggestions:
        df_suggestions = pd.DataFrame(suggestions)
        
        for idx, suggestion in df_suggestions.iterrows():
            col1, col2, col3, col4 = st.columns([3, 1, 2, 2])
            
            with col1:
                st.write(suggestion['Pattern'])
            
            with col2:
                st.write(f"{suggestion['Count']} transactions")
            
            with col3:
                st.write(f"→ {suggestion['Suggested Category']}")
            
            with col4:
                if st.button(f"Apply All", key=f"suggest_{idx}"):
                    pattern = suggestion['Action']
                    category = suggestion['Suggested Category']
                    
                    matching_trans = uncategorized[uncategorized['description'].str.contains(pattern, case=False, na=False)]
                    success_count = 0
                    
                    for _, trans in matching_trans.iterrows():
                        if update_transaction_category(trans['id'], category):
                            success_count += 1
                    
                    st.success(f"Updated {success_count} transactions!")
                    st.rerun()

# Category management
st.markdown("---")
st.subheader("Category Management")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Add New Category**")
    with st.form("add_category_form"):
        new_category_name = st.text_input("Category Name")
        category_type = st.selectbox("Type", options=['expense', 'income'])
        
        if st.form_submit_button("Add Category"):
            if new_category_name:
                if add_category(new_category_name, category_type):
                    st.success(f"Added category: {new_category_name}")
                    st.rerun()
                else:
                    st.error("Category already exists or invalid")

with col2:
    st.markdown("**Current Categories**")
    categories_by_type = {}
    for cat_type in ['expense', 'income', 'travel']:
        type_categories = get_categories(cat_type)
        if type_categories:
            categories_by_type[cat_type] = type_categories
    
    for cat_type, cats in categories_by_type.items():
        st.write(f"**{cat_type.title()}**: {', '.join(cats)}")

# Export functionality
st.markdown("---")
if st.button("Export Categorized Transactions"):
    export_df = df.copy()
    export_df['amount_formatted'] = export_df['amount'].apply(format_currency)
    
    csv = export_df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"categorized_transactions_{start_date}_to_{end_date}.csv",
        mime="text/csv"
    )

# Help section
st.markdown("---")
st.subheader("Categorization Tips")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Quick Tips:**
    - Use bulk categorization for recurring merchants
    - Start with uncategorized transactions
    - Create specific categories for better insights
    - Review and update categories regularly
    """)

with col2:
    st.markdown("""
    **Common Categories:**
    - Groceries, Dining, Shopping
    - Transportation, Utilities
    - Entertainment, Healthcare
    - Travel, Subscriptions
    """)
