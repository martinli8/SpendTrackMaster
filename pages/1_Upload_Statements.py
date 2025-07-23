import streamlit as st
import pandas as pd
from datetime import datetime
import io
from database import insert_transactions
from utils import parse_bank_csv, parse_bank_excel, validate_file_format

st.set_page_config(
    page_title="Upload Bank Statements",
    page_icon="📤",
    layout="wide"
)

st.title("📤 Upload Bank Statements")
st.markdown("Upload your CSV or Excel bank statements to import transactions into the tracker.")

# File uploader
uploaded_files = st.file_uploader(
    "Choose bank statement files",
    accept_multiple_files=True,
    type=['csv', 'xlsx', 'xls'],
    help="Upload CSV or Excel files from your bank exports"
)

if uploaded_files:
    st.markdown("---")
    st.subheader("File Processing Results")
    
    total_inserted = 0
    processing_results = []
    
    for uploaded_file in uploaded_files:
        with st.expander(f"Processing: {uploaded_file.name}", expanded=True):
            
            # Validate file format
            if not validate_file_format(uploaded_file.name):
                st.error(f"Unsupported file format: {uploaded_file.name}")
                processing_results.append({
                    'filename': uploaded_file.name,
                    'status': 'Failed',
                    'transactions': 0,
                    'error': 'Unsupported file format'
                })
                continue
            
            try:
                # Parse file based on extension
                if uploaded_file.name.lower().endswith('.csv'):
                    # Read CSV file
                    file_content = uploaded_file.read().decode('utf-8')
                    transactions = parse_bank_csv(file_content, uploaded_file.name)
                else:
                    # Read Excel file
                    file_content = uploaded_file.read()
                    transactions = parse_bank_excel(file_content, uploaded_file.name)
                
                if not transactions:
                    st.warning(f"No valid transactions found in {uploaded_file.name}")
                    processing_results.append({
                        'filename': uploaded_file.name,
                        'status': 'Warning',
                        'transactions': 0,
                        'error': 'No valid transactions found'
                    })
                    continue
                
                # Show preview of transactions
                st.write(f"Found {len(transactions)} transactions")
                
                # Display sample transactions
                if len(transactions) > 0:
                    df_preview = pd.DataFrame(transactions[:5])  # Show first 5 transactions
                    st.write("Preview of first 5 transactions:")
                    st.dataframe(df_preview[['transaction_date', 'description', 'category', 'type', 'amount']])
                
                # Insert transactions into database
                inserted_count = insert_transactions(transactions)
                total_inserted += inserted_count
                
                if inserted_count > 0:
                    st.success(f"Successfully imported {inserted_count} transactions from {uploaded_file.name}")
                    processing_results.append({
                        'filename': uploaded_file.name,
                        'status': 'Success',
                        'transactions': inserted_count,
                        'error': None
                    })
                else:
                    st.error(f"Failed to import transactions from {uploaded_file.name}")
                    processing_results.append({
                        'filename': uploaded_file.name,
                        'status': 'Failed',
                        'transactions': 0,
                        'error': 'Database insertion failed'
                    })
                
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                processing_results.append({
                    'filename': uploaded_file.name,
                    'status': 'Failed',
                    'transactions': 0,
                    'error': str(e)
                })
    
    # Summary of results
    if processing_results:
        st.markdown("---")
        st.subheader("Import Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            successful_files = len([r for r in processing_results if r['status'] == 'Success'])
            st.metric("Files Processed Successfully", successful_files)
        
        with col2:
            failed_files = len([r for r in processing_results if r['status'] == 'Failed'])
            st.metric("Files Failed", failed_files)
        
        with col3:
            st.metric("Total Transactions Imported", total_inserted)
        
        # Detailed results table
        if st.checkbox("Show detailed results"):
            df_results = pd.DataFrame(processing_results)
            st.dataframe(df_results, use_container_width=True)
        
        if total_inserted > 0:
            st.success(f"Successfully imported {total_inserted} transactions from {len(uploaded_files)} files!")
            st.info("You can now categorize these transactions in the 'Categorize Transactions' page.")

# Instructions and tips
st.markdown("---")
st.subheader("Upload Instructions")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Supported File Formats:**
    - CSV files (.csv)
    - Excel files (.xlsx, .xls)
    
    **Expected Columns:**
    - Transaction Date / Date
    - Description
    - Amount
    - Type (optional)
    - Category (optional)
    - Post Date (optional)
    - Memo (optional)
    """)

with col2:
    st.markdown("""
    **Tips for Best Results:**
    - Ensure your files have a header row
    - Date columns should be in a standard format
    - Amount columns should be numeric
    - Negative amounts typically represent expenses
    - The system will auto-categorize transactions based on descriptions
    """)

# Show example of expected format
st.markdown("---")
st.subheader("Example File Format")

example_data = {
    'Transaction Date': ['2025-01-15', '2025-01-16', '2025-01-17'],
    'Description': ['Amazon.com*Shopping', 'Whole Foods Market', 'Shell Gas Station'],
    'Category': ['Shopping', 'Groceries', 'Transportation'],
    'Type': ['Sale', 'Sale', 'Sale'],
    'Amount': [-45.67, -89.34, -35.20],
    'Memo': ['', '', '']
}

df_example = pd.DataFrame(example_data)
st.dataframe(df_example, use_container_width=True)

st.info("Your bank export files should have similar column structure. The system is flexible and will attempt to map columns automatically.")
