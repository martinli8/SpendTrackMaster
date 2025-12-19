import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from database import (
    get_all_transactions, 
    get_categories, 
    bulk_update_transactions,
    bulk_update_transaction_descriptions,
    bulk_adjust_amounts,
    bulk_adjust_dates,
    get_all_categories,
    delete_transactions_by_upload_date,
    delete_transactions_by_source_file,
    get_upload_dates,
    get_transactions_by_upload_date
)
from utils import format_currency

st.set_page_config(
    page_title="Mass Edit Transactions",
    page_icon="✏️",
    layout="wide"
)

st.title("✏️ Mass Edit Transactions")
st.markdown("Select and bulk edit multiple transactions at once. Filter, select, and apply changes to multiple transactions efficiently.")

# Initialize session state for selected transactions
if 'selected_transaction_ids' not in st.session_state:
    st.session_state.selected_transaction_ids = set()

st.markdown("---")

# Sidebar filters
st.sidebar.header("🔍 Filters")

# Date range filter
date_range = st.sidebar.selectbox(
    "Date Range",
    options=["Last 30 days", "Last 90 days", "Last 6 months", "This Year", "All Time", "Custom Range"],
    index=0
)

if date_range == "Last 30 days":
    start_date = datetime.now().date() - timedelta(days=30)
    end_date = datetime.now().date()
elif date_range == "Last 90 days":
    start_date = datetime.now().date() - timedelta(days=90)
    end_date = datetime.now().date()
elif date_range == "Last 6 months":
    start_date = datetime.now().date() - timedelta(days=180)
    end_date = datetime.now().date()
elif date_range == "This Year":
    start_date = date(datetime.now().year, 1, 1)
    end_date = datetime.now().date()
elif date_range == "All Time":
    start_date = None
    end_date = None
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
    options=["All", "Expenses Only", "Income Only", "> $100", "> $50", "< $50", "Custom Range"]
)

if amount_filter == "Custom Range":
    amount_min = st.sidebar.number_input("Min Amount", value=0.0, step=0.01)
    amount_max = st.sidebar.number_input("Max Amount", value=1000.0, step=0.01)
else:
    amount_min = None
    amount_max = None

# Description filter / Search
description_filter = st.sidebar.text_input(
    "🔍 Search / Description contains",
    placeholder="e.g., AMAZON, STARBUCKS",
    help="Search transactions by description text"
)

# Upload date filter
st.sidebar.markdown("---")
st.sidebar.markdown("**Upload Date Filter**")
filter_by_upload_date = st.sidebar.checkbox("Filter by upload date", key="filter_upload_date")

upload_start_date = None
upload_end_date = None

if filter_by_upload_date:
    upload_start_date = st.sidebar.date_input(
        "Upload Start Date",
        value=datetime.now().date() - timedelta(days=30),
        key="upload_start"
    )
    upload_end_date = st.sidebar.date_input(
        "Upload End Date",
        value=datetime.now().date(),
        key="upload_end"
    )

# Get transactions with filters
transactions = get_all_transactions(start_date, end_date)

if not transactions:
    st.info("No transactions found for the selected filters.")
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
elif amount_filter == "Custom Range" and amount_min is not None and amount_max is not None:
    df = df[(abs(df['amount']) >= amount_min) & (abs(df['amount']) <= amount_max)]

# Description filter
if description_filter:
    df = df[df['description'].str.contains(description_filter, case=False, na=False)]

# Upload date filter
if filter_by_upload_date and upload_start_date and upload_end_date:
    if 'created_at' in df.columns:
        # Convert created_at to datetime if it's a string
        df['created_at'] = pd.to_datetime(df['created_at'])
        # Filter by upload date range
        start_datetime = pd.Timestamp(datetime.combine(upload_start_date, datetime.min.time()))
        end_datetime = pd.Timestamp(datetime.combine(upload_end_date, datetime.max.time()))
        df = df[(df['created_at'] >= start_datetime) & (df['created_at'] <= end_datetime)]

if df.empty:
    st.warning("No transactions match your current filters.")
    st.stop()

# Summary statistics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_transactions = len(df)
    st.metric("Filtered Transactions", total_transactions)

with col2:
    selected_count = len(st.session_state.selected_transaction_ids)
    st.metric("Selected", selected_count)

with col3:
    total_expenses = abs(df[df['amount'] < 0]['amount'].sum())
    st.metric("Total Expenses", format_currency(total_expenses))

with col4:
    total_income = df[df['amount'] > 0]['amount'].sum()
    st.metric("Total Income", format_currency(total_income))

st.markdown("---")

# Selection controls
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.subheader("Select Transactions")
    
with col2:
    if st.button("Select All", use_container_width=True):
        st.session_state.selected_transaction_ids = set(df['id'].tolist())
        st.rerun()
    
with col3:
    if st.button("Clear Selection", use_container_width=True):
        st.session_state.selected_transaction_ids = set()
        st.rerun()

# Display transactions with checkboxes
st.markdown("#### Transaction List")

# Create a dataframe for display with selection
df_display = df.copy()

# Convert transaction_date to date type if it's a string
if 'transaction_date' in df_display.columns:
    if df_display['transaction_date'].dtype == 'object':
        df_display['transaction_date'] = pd.to_datetime(df_display['transaction_date']).dt.date

# Convert created_at to datetime if it exists and create formatted upload date column
if 'created_at' in df_display.columns:
    if df_display['created_at'].dtype == 'object':
        df_display['created_at'] = pd.to_datetime(df_display['created_at'])
    # Create a formatted upload date column for display
    df_display['uploaded'] = df_display['created_at'].dt.strftime('%Y-%m-%d %H:%M')

df_display['Select'] = df_display['id'].apply(lambda x: x in st.session_state.selected_transaction_ids)

# Reorder columns for better display - include upload info if available
base_columns = ['Select', 'transaction_date', 'description', 'category', 'amount', 'type']
if 'uploaded' in df_display.columns:
    base_columns.insert(-1, 'uploaded')
if 'source_file' in df_display.columns:
    base_columns.insert(-1, 'source_file')
    
other_columns = [col for col in df_display.columns if col not in base_columns]
df_display = df_display[base_columns + other_columns]

# Build column config
column_config = {
    "Select": st.column_config.CheckboxColumn(
        "Select",
        help="Select transactions for bulk editing",
        default=False,
    ),
    "transaction_date": st.column_config.DateColumn(
        "Date",
        format="YYYY-MM-DD",
    ),
    "description": st.column_config.TextColumn(
        "Description",
        width="large",
    ),
    "category": st.column_config.SelectboxColumn(
        "Category",
        options=all_categories,
    ),
    "amount": st.column_config.NumberColumn(
        "Amount",
        format="$%.2f",
    ),
    "type": st.column_config.TextColumn(
        "Type",
    ),
}

# Add upload info columns if they exist
if 'uploaded' in df_display.columns:
    column_config["uploaded"] = st.column_config.TextColumn(
        "Uploaded",
        help="When this transaction was uploaded",
        width="medium"
    )
if 'source_file' in df_display.columns:
    column_config["source_file"] = st.column_config.TextColumn(
        "Source File",
        help="File from which this transaction was imported",
        width="medium"
    )

# Convert to editable dataframe
edited_df = st.data_editor(
    df_display,
    column_config=column_config,
    hide_index=True,
    use_container_width=True,
    num_rows="dynamic",
    key="transaction_editor"
)

# Update selected transactions based on checkbox changes
if edited_df is not None and 'Select' in edited_df.columns:
    selected_ids = set(edited_df[edited_df['Select'] == True]['id'].tolist())
    st.session_state.selected_transaction_ids = selected_ids

st.markdown("---")

# Bulk Edit Operations
st.subheader("🔧 Bulk Edit Operations")

if not st.session_state.selected_transaction_ids:
    st.info("👆 Select transactions above to enable bulk editing operations.")
else:
    st.success(f"✅ {len(st.session_state.selected_transaction_ids)} transaction(s) selected")
    
    # Create tabs for different bulk operations
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Update Category",
        "✏️ Update Description",
        "💰 Adjust Amount",
        "📅 Adjust Date",
        "🔄 Multiple Changes"
    ])
    
    selected_ids_list = list(st.session_state.selected_transaction_ids)
    
    with tab1:
        st.markdown("### Update Category for Selected Transactions")
        new_category = st.selectbox(
            "New Category",
            options=all_categories,
            key="bulk_category"
        )
        
        if st.button("Apply Category Update", type="primary", key="apply_category"):
            updated_count = bulk_update_transactions(
                selected_ids_list,
                category=new_category
            )
            st.success(f"✅ Updated category for {updated_count} transaction(s) to '{new_category}'")
            st.session_state.selected_transaction_ids = set()
            st.rerun()
    
    with tab2:
        st.markdown("### Update Description for Selected Transactions")
        
        desc_option = st.radio(
            "Update Method",
            options=["Find and Replace", "Set New Description"],
            key="desc_method"
        )
        
        if desc_option == "Find and Replace":
            col1, col2 = st.columns(2)
            with col1:
                find_text = st.text_input("Find text", placeholder="e.g., AMAZON.COM")
            with col2:
                replace_text = st.text_input("Replace with", placeholder="e.g., Amazon")
            
            if st.button("Apply Find & Replace", type="primary", key="apply_find_replace"):
                if find_text:
                    updated_count = bulk_update_transaction_descriptions(
                        selected_ids_list,
                        find_text,
                        replace_text
                    )
                    st.success(f"✅ Updated descriptions for {updated_count} transaction(s)")
                    st.session_state.selected_transaction_ids = set()
                    st.rerun()
                else:
                    st.error("Please enter text to find")
        else:
            new_description = st.text_input("New Description", placeholder="Enter new description for all selected")
            
            if st.button("Apply New Description", type="primary", key="apply_new_desc"):
                if new_description:
                    updated_count = bulk_update_transactions(
                        selected_ids_list,
                        description=new_description
                    )
                    st.success(f"✅ Updated description for {updated_count} transaction(s)")
                    st.session_state.selected_transaction_ids = set()
                    st.rerun()
                else:
                    st.error("Please enter a description")
    
    with tab3:
        st.markdown("### Adjust Amount for Selected Transactions")
        
        operation = st.selectbox(
            "Operation",
            options=["Multiply by", "Add", "Subtract", "Set to"],
            key="amount_operation"
        )
        
        if operation == "Multiply by":
            value = st.number_input("Multiplier", value=1.0, step=0.01, key="amount_value")
            st.info(f"This will multiply all selected amounts by {value}")
        elif operation == "Add":
            value = st.number_input("Amount to add", value=0.0, step=0.01, key="amount_value")
            st.info(f"This will add ${value:,.2f} to all selected amounts")
        elif operation == "Subtract":
            value = st.number_input("Amount to subtract", value=0.0, step=0.01, key="amount_value")
            st.info(f"This will subtract ${value:,.2f} from all selected amounts")
        else:  # Set to
            value = st.number_input("New amount", value=0.0, step=0.01, key="amount_value")
            st.info(f"This will set all selected amounts to ${value:,.2f}")
        
        operation_map = {
            "Multiply by": "multiply",
            "Add": "add",
            "Subtract": "subtract",
            "Set to": "set"
        }
        
        if st.button("Apply Amount Adjustment", type="primary", key="apply_amount"):
            updated_count = bulk_adjust_amounts(
                selected_ids_list,
                operation_map[operation],
                value
            )
            st.success(f"✅ Updated amounts for {updated_count} transaction(s)")
            st.session_state.selected_transaction_ids = set()
            st.rerun()
    
    with tab4:
        st.markdown("### Adjust Date for Selected Transactions")
        
        days_to_add = st.number_input(
            "Days to add/subtract",
            value=0,
            step=1,
            help="Positive number to add days, negative to subtract"
        )
        
        if days_to_add != 0:
            if days_to_add > 0:
                st.info(f"This will add {days_to_add} day(s) to all selected transaction dates")
            else:
                st.info(f"This will subtract {abs(days_to_add)} day(s) from all selected transaction dates")
        
        if st.button("Apply Date Adjustment", type="primary", key="apply_date"):
            if days_to_add != 0:
                updated_count = bulk_adjust_dates(selected_ids_list, days_to_add)
                st.success(f"✅ Updated dates for {updated_count} transaction(s)")
                st.session_state.selected_transaction_ids = set()
                st.rerun()
            else:
                st.warning("Please enter a non-zero number of days")
    
    with tab5:
        st.markdown("### Apply Multiple Changes at Once")
        st.info("Apply multiple changes to selected transactions simultaneously")
        
        col1, col2 = st.columns(2)
        
        with col1:
            update_category = st.checkbox("Update Category", key="multi_cat")
            if update_category:
                multi_category = st.selectbox("New Category", options=all_categories, key="multi_category_select")
            
            update_description = st.checkbox("Update Description", key="multi_desc")
            if update_description:
                multi_description = st.text_input("New Description", key="multi_description_input")
        
        with col2:
            update_amount = st.checkbox("Update Amount", key="multi_amt")
            if update_amount:
                multi_amount = st.number_input("New Amount", value=0.0, step=0.01, key="multi_amount_input")
            
            update_date = st.checkbox("Update Date", key="multi_date")
            if update_date:
                multi_date = st.date_input("New Date", value=date.today(), key="multi_date_input")
        
        if st.button("Apply All Selected Changes", type="primary", key="apply_multi"):
            changes_made = []
            
            category = multi_category if update_category else None
            description = multi_description if update_description else None
            amount = multi_amount if update_amount else None
            transaction_date = multi_date if update_date else None
            
            if category or description or amount is not None or transaction_date:
                updated_count = bulk_update_transactions(
                    selected_ids_list,
                    transaction_date=transaction_date,
                    description=description,
                    category=category,
                    amount=amount
                )
                
                if updated_count > 0:
                    if category:
                        changes_made.append(f"Category → {category}")
                    if description:
                        changes_made.append(f"Description → {description[:30]}...")
                    if amount is not None:
                        changes_made.append(f"Amount → ${amount:,.2f}")
                    if transaction_date:
                        changes_made.append(f"Date → {transaction_date}")
                    
                    st.success(f"✅ Updated {updated_count} transaction(s) with: {', '.join(changes_made)}")
                    st.session_state.selected_transaction_ids = set()
                    st.rerun()
                else:
                    st.error("Failed to update transactions")
            else:
                st.warning("Please select at least one field to update")

# Preview selected transactions
if st.session_state.selected_transaction_ids:
    st.markdown("---")
    st.subheader("📋 Preview Selected Transactions")
    
    selected_df = df[df['id'].isin(st.session_state.selected_transaction_ids)].copy()
    selected_df['amount_formatted'] = selected_df['amount'].apply(format_currency)
    
    preview_columns = ['transaction_date', 'description', 'category', 'amount_formatted', 'type']
    st.dataframe(
        selected_df[preview_columns],
        use_container_width=True,
        hide_index=True
    )
    
    col1, col2 = st.columns(2)
    with col1:
        selected_expenses = abs(selected_df[selected_df['amount'] < 0]['amount'].sum())
        st.metric("Selected Expenses", format_currency(selected_expenses))
    with col2:
        selected_income = selected_df[selected_df['amount'] > 0]['amount'].sum()
        st.metric("Selected Income", format_currency(selected_income))

# Delete by Upload Date Section
st.markdown("---")
st.subheader("🗑️ Delete Transactions by Upload Date")

st.warning("⚠️ **Warning**: This is a destructive operation. Deleted transactions cannot be recovered.")

# Get upload history
upload_history = get_upload_dates()

if upload_history:
    st.markdown("#### Upload History")
    df_uploads = pd.DataFrame(upload_history)
    
    # Convert dates for display
    if 'upload_date' in df_uploads.columns:
        df_uploads['upload_date'] = pd.to_datetime(df_uploads['upload_date']).dt.date
    
    st.dataframe(
        df_uploads[['upload_date', 'source_file', 'transaction_count', 'first_upload']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "upload_date": st.column_config.DateColumn("Upload Date", format="YYYY-MM-DD"),
            "source_file": st.column_config.TextColumn("Source File", width="large"),
            "transaction_count": st.column_config.NumberColumn("Transactions", format="%d"),
            "first_upload": st.column_config.DatetimeColumn("First Upload", format="YYYY-MM-DD HH:mm")
        }
    )

# Delete by upload date range
st.markdown("#### Delete by Upload Date Range")

col1, col2 = st.columns(2)

with col1:
    delete_start_date = st.date_input(
        "Upload Start Date",
        value=datetime.now().date() - timedelta(days=30),
        help="Delete transactions uploaded on or after this date"
    )

with col2:
    delete_end_date = st.date_input(
        "Upload End Date",
        value=datetime.now().date(),
        help="Delete transactions uploaded on or before this date"
    )

# Preview what will be deleted
if st.button("Preview Transactions to Delete", key="preview_delete"):
    preview_transactions = get_transactions_by_upload_date(
        start_date=datetime.combine(delete_start_date, datetime.min.time()),
        end_date=datetime.combine(delete_end_date, datetime.max.time())
    )
    
    if preview_transactions:
        preview_df = pd.DataFrame(preview_transactions)
        preview_df['amount_formatted'] = preview_df['amount'].apply(format_currency)
        
        st.write(f"**{len(preview_df)} transaction(s) will be deleted:**")
        st.dataframe(
            preview_df[['transaction_date', 'description', 'category', 'amount_formatted', 'source_file', 'created_at']].head(20),
            use_container_width=True,
            hide_index=True
        )
        
        if len(preview_df) > 20:
            st.info(f"... and {len(preview_df) - 20} more transactions")
        
        total_preview_expenses = abs(preview_df[preview_df['amount'] < 0]['amount'].sum())
        total_preview_income = preview_df[preview_df['amount'] > 0]['amount'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Expenses", format_currency(total_preview_expenses))
        with col2:
            st.metric("Total Income", format_currency(total_preview_income))
        
        st.session_state.preview_delete_count = len(preview_df)
    else:
        st.info("No transactions found for the selected upload date range.")

# Confirm and delete
if st.button("🗑️ Delete Transactions by Upload Date", type="primary", key="delete_by_date"):
    if delete_start_date <= delete_end_date:
        deleted_count = delete_transactions_by_upload_date(
            start_date=datetime.combine(delete_start_date, datetime.min.time()),
            end_date=datetime.combine(delete_end_date, datetime.max.time())
        )
        st.success(f"✅ Deleted {deleted_count} transaction(s) uploaded between {delete_start_date} and {delete_end_date}")
        st.rerun()
    else:
        st.error("Start date must be before or equal to end date")

# Delete by source file
st.markdown("---")
st.markdown("#### Delete by Source File")

if upload_history:
    source_files = [upload['source_file'] for upload in upload_history]
    unique_files = sorted(list(set(source_files)))
    
    selected_file = st.selectbox(
        "Select Source File",
        options=unique_files,
        help="Delete all transactions from a specific uploaded file"
    )
    
    if selected_file:
        # Get count for this file
        file_transactions = get_transactions_by_upload_date(source_file=selected_file)
        file_count = len(file_transactions)
        
        if file_count > 0:
            st.info(f"⚠️ This will delete {file_count} transaction(s) from '{selected_file}'")
            
            # Show preview
            if st.checkbox("Show preview", key="preview_file_delete"):
                file_df = pd.DataFrame(file_transactions)
                file_df['amount_formatted'] = file_df['amount'].apply(format_currency)
                st.dataframe(
                    file_df[['transaction_date', 'description', 'category', 'amount_formatted']].head(20),
                    use_container_width=True,
                    hide_index=True
                )
            
            if st.button(f"🗑️ Delete All Transactions from '{selected_file}'", type="primary", key="delete_by_file"):
                deleted_count = delete_transactions_by_source_file(selected_file)
                st.success(f"✅ Deleted {deleted_count} transaction(s) from '{selected_file}'")
                st.rerun()
        else:
            st.info("No transactions found for this source file")
else:
    st.info("No upload history available")

# Help section
st.markdown("---")
st.subheader("💡 Tips for Mass Editing")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Selection Tips:**
    - Use filters to narrow down transactions
    - Click "Select All" to select all filtered transactions
    - Use checkboxes in the table to select specific transactions
    - Selected transactions persist across filter changes
    """)

with col2:
    st.markdown("""
    **Bulk Operations:**
    - Update category for multiple transactions at once
    - Find and replace text in descriptions
    - Adjust amounts with mathematical operations
    - Shift dates forward or backward
    - Apply multiple changes simultaneously
    """)

