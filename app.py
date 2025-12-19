import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, date, timedelta
import calendar
from database import init_database, get_all_transactions, get_recurring_expenses, get_travel_budget_balance, get_monthly_summary, update_transaction_category, get_categories, add_transaction, edit_transaction, delete_transaction
from utils import get_month_name, calculate_prorated_amount, format_currency

# Initialize the database
init_database()

st.set_page_config(
    page_title="Dashboard",
    page_icon="💰",
    layout="wide"
)

# Header with title and info button
col_title, col_info = st.columns([10, 1])
with col_title:
    st.title("💰 Dashboard")
with col_info:
    if st.button("ℹ️", help="Getting Started Guide"):
        st.session_state.show_info = not st.session_state.get('show_info', False)

if st.session_state.get('show_info', False):
    st.info("""
    **Welcome to your Spend Tracker!** To get started:
    
    1. **Upload Bank Statements**: Go to the "Upload Statements" page to import your CSV/Excel files
    2. **Add Recurring Expenses**: Visit "Recurring Expenses" to add fixed costs like rent, subscriptions, etc.
    3. **Set Up Travel Budget**: Use "Travel Budget" to manage your $500 monthly travel fund
    4. **Categorize Transactions**: Go to "Categorize Transactions" to organize your imported expenses
    
    Once you have data, this dashboard will show comprehensive insights into your spending patterns!
    """)

st.markdown("---")

# Sidebar for month/year selection
st.sidebar.header("Month Selection")
current_date = datetime.now()

# Year selection
available_years = list(range(2020, current_date.year + 2))
selected_year = st.sidebar.selectbox(
    "Year",
    options=available_years,
    index=available_years.index(current_date.year)
)

# Month selection
months = [
    (1, "January"), (2, "February"), (3, "March"), (4, "April"),
    (5, "May"), (6, "June"), (7, "July"), (8, "August"),
    (9, "September"), (10, "October"), (11, "November"), (12, "December")
]
month_names = [month[1] for month in months]
month_values = [month[0] for month in months]

selected_month = st.sidebar.selectbox(
    "Month",
    options=month_values,
    format_func=lambda x: month_names[month_values.index(x)],
    index=current_date.month - 1
)

# Calculate date range for selected month
month_start = date(selected_year, selected_month, 1)
month_end = date(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1])

# Calculate average monthly spend (last 6 months)
avg_monthly = 0
monthly_totals = []
for i in range(6):
    calc_date = date(current_date.year, current_date.month, 1)
    if calc_date.month - i <= 0:
        calc_year = calc_date.year - 1
        calc_month = 12 + (calc_date.month - i)
    else:
        calc_year = calc_date.year
        calc_month = calc_date.month - i
    
    summary = get_monthly_summary(calc_year, calc_month)
    total = summary['imported_expenses'] + summary['recurring_expenses'] + summary['travel_expenses']
    monthly_totals.append(total)

avg_monthly = sum(monthly_totals) / len(monthly_totals) if monthly_totals else 0

# Get current month summary
current_month_summary = get_monthly_summary(selected_year, selected_month)
current_month_total = (
    current_month_summary['imported_expenses'] + 
    current_month_summary['recurring_expenses'] + 
    current_month_summary['travel_expenses']
)

# Get travel budget balance
travel_balance = get_travel_budget_balance()

# Main metrics in requested order
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Average Monthly Spend (6mo)",
        value=format_currency(avg_monthly)
    )

with col2:
    st.metric(
        label=f"Current Month Total ({get_month_name(selected_month)})",
        value=format_currency(current_month_total)
    )

with col3:
    st.metric(
        label="Travel Budget Balance",
        value=format_currency(travel_balance)
    )

st.markdown("---")

# Spending Over Time Chart
st.subheader("💹 Spending Over Time")

chart_col1, chart_col2 = st.columns([3, 1])

with chart_col1:
    st.markdown("**Customize your chart**")
    
    chart_date_range = st.selectbox(
        "Time Frame",
        options=["Last 30 days", "Last 90 days", "Last 6 months", "This Year", "Custom Range"],
        key="chart_date_range"
    )
    
    if chart_date_range == "Last 30 days":
        chart_start = date.today() - timedelta(days=30)
        chart_end = date.today()
    elif chart_date_range == "Last 90 days":
        chart_start = date.today() - timedelta(days=90)
        chart_end = date.today()
    elif chart_date_range == "Last 6 months":
        chart_start = date.today() - timedelta(days=180)
        chart_end = date.today()
    elif chart_date_range == "This Year":
        chart_start = date(date.today().year, 1, 1)
        chart_end = date.today()
    else:  # Custom Range
        col_cs, col_ce = st.columns(2)
        with col_cs:
            chart_start = st.date_input("Start Date", value=date.today() - timedelta(days=30))
        with col_ce:
            chart_end = st.date_input("End Date", value=date.today())

with chart_col2:
    chart_category_filter = st.multiselect(
        "Filter by Categories",
        options=get_categories(),
        key="chart_category_filter"
    )

# Get transactions for chart
chart_transactions = get_all_transactions(chart_start, chart_end)

if chart_transactions:
    df_chart = pd.DataFrame(chart_transactions)
    df_chart['transaction_date'] = pd.to_datetime(df_chart['transaction_date'])
    
    # Filter by categories if selected
    if chart_category_filter:
        df_chart = df_chart[df_chart['category'].isin(chart_category_filter)]
    
    # Separate expenses and income
    expenses = df_chart[df_chart['amount'] < 0].copy()
    expenses['amount'] = abs(expenses['amount'])
    
    # Group by date and sum
    daily_totals = expenses.groupby(expenses['transaction_date'].dt.date)['amount'].sum().reset_index()
    daily_totals.columns = ['date', 'amount']
    daily_totals = daily_totals.sort_values('date')
    
    if not daily_totals.empty:
        fig = px.line(
            daily_totals,
            x='date',
            y='amount',
            title="Daily Spending Trend" + (f" - {', '.join(chart_category_filter)}" if chart_category_filter else ""),
            labels={'date': 'Date', 'amount': 'Amount ($)'},
            markers=True
        )
        fig.update_layout(hovermode='x unified', height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary stats for chart period
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Spent", format_currency(daily_totals['amount'].sum()))
        with col2:
            st.metric("Average Daily", format_currency(daily_totals['amount'].mean()))
        with col3:
            st.metric("Highest Day", format_currency(daily_totals['amount'].max()))
    else:
        st.info("No transactions found for the selected filters.")
else:
    st.info("No transactions in this time period.")

st.markdown("---")

# Monthly Spend Breakdown in Tabular Format
st.subheader(f"Monthly Spend Breakdown - {get_month_name(selected_month)} {selected_year}")

# Get transactions for the selected month
month_transactions = get_all_transactions(month_start, month_end)
recurring_expenses = get_recurring_expenses()

# Calculate category totals
category_totals = {}
total_spend = 0

# Process imported transactions by category
if month_transactions:
    df_transactions = pd.DataFrame(month_transactions)
    expense_transactions = df_transactions[df_transactions['amount'] < 0]
    
    for category in expense_transactions['category'].unique():
        cat_total = abs(expense_transactions[expense_transactions['category'] == category]['amount'].sum())
        category_totals[category] = category_totals.get(category, 0) + cat_total
        total_spend += cat_total

# Add recurring expenses (prorated to monthly)
for expense in recurring_expenses:
    if expense['is_active']:
        # Check if expense is active for this month
        start_date_exp = datetime.strptime(expense['start_date'], '%Y-%m-%d').date()
        end_date_exp = None
        if expense['end_date']:
            end_date_exp = datetime.strptime(expense['end_date'], '%Y-%m-%d').date()
        
        if start_date_exp <= month_end and (end_date_exp is None or end_date_exp >= month_start):
            monthly_amount = calculate_prorated_amount(expense['amount'], expense['frequency'])
            category = expense['category']
            category_totals[category] = category_totals.get(category, 0) + monthly_amount
            total_spend += monthly_amount

# Create category breakdown table
if category_totals:
    category_data = []
    for category, amount in category_totals.items():
        percentage = (amount / total_spend * 100) if total_spend > 0 else 0
        category_data.append({
            'Category': category,
            'Amount': amount,
            'Percentage': f"{percentage:.1f}%"
        })
    
    # Sort by amount descending
    category_data.sort(key=lambda x: x['Amount'], reverse=True)
    
    # Display table with clickable categories
    for item in category_data:
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        
        with col1:
            if st.button(f"📊 {item['Category']}", key=f"cat_{item['Category']}", help="Click to view transactions"):
                st.session_state.selected_category = item['Category']
                st.session_state.show_category_detail = True
        
        with col2:
            st.write(format_currency(item['Amount']))
        
        with col3:
            st.write(item['Percentage'])
        
        with col4:
            st.write("")
    
    # Add total row
    st.markdown(f"**Total Monthly Spend: {format_currency(total_spend)}**")
else:
    st.info("No spending data available for the selected month.")

# Show category detail if selected
if 'show_category_detail' in st.session_state and st.session_state.show_category_detail:
    st.markdown("---")
    selected_cat = st.session_state.selected_category
    st.subheader(f"Transactions in '{selected_cat}' - {get_month_name(selected_month)} {selected_year}")
    
    # Get transactions for this category
    cat_transactions = []
    if month_transactions:
        df_month = pd.DataFrame(month_transactions)
        cat_trans = df_month[df_month['category'] == selected_cat]
        cat_transactions = cat_trans.to_dict('records')
    
    # Add recurring expenses for this category
    for expense in recurring_expenses:
        if expense['category'] == selected_cat and expense['is_active']:
            start_date_exp = datetime.strptime(expense['start_date'], '%Y-%m-%d').date()
            end_date_exp = None
            if expense['end_date']:
                end_date_exp = datetime.strptime(expense['end_date'], '%Y-%m-%d').date()
            
            if start_date_exp <= month_end and (end_date_exp is None or end_date_exp >= month_start):
                monthly_amount = calculate_prorated_amount(expense['amount'], expense['frequency'])
                cat_transactions.append({
                    'transaction_date': month_start,
                    'description': f"{expense['name']} (Recurring)",
                    'amount': -monthly_amount,
                    'type': 'Recurring',
                    'category': selected_cat
                })
    
    if cat_transactions:
        df_cat = pd.DataFrame(cat_transactions)
        df_cat = df_cat.sort_values('transaction_date', ascending=False)
        st.dataframe(df_cat[['transaction_date', 'description', 'amount', 'type']], use_container_width=True)
        
        total_cat_amount = abs(df_cat['amount'].sum())
        st.write(f"**Total for {selected_cat}: {format_currency(total_cat_amount)}**")
    else:
        st.info(f"No transactions found for {selected_cat}")
    
    if st.button("← Back to Overview"):
        st.session_state.show_category_detail = False
        st.rerun()

# Fixed Spend Table
if 'show_category_detail' not in st.session_state or not st.session_state.show_category_detail:
    st.markdown("---")
    st.subheader("Fixed/Recurring Expenses")
    
    if recurring_expenses:
        fixed_data = []
        for expense in recurring_expenses:
            if expense['is_active']:
                monthly_amount = calculate_prorated_amount(expense['amount'], expense['frequency'])
                fixed_data.append({
                    'Name': expense['name'],
                    'Category': expense['category'],
                    'Original Amount': format_currency(expense['amount']),
                    'Frequency': expense['frequency'].title(),
                    'Monthly Amount': format_currency(monthly_amount)
                })
        
        if fixed_data:
            df_fixed = pd.DataFrame(fixed_data)
            st.dataframe(df_fixed, use_container_width=True)
        else:
            st.info("No active recurring expenses")
    else:
        st.info("No recurring expenses defined")

    # Complete Transaction View for the Month
    st.markdown("---")
    st.subheader(f"All Transactions - {get_month_name(selected_month)} {selected_year}")
    
    if month_transactions:
        # Create a comprehensive transaction list including recurring expenses
        all_month_transactions = []
        
        # Add imported transactions
        for trans in month_transactions:
            all_month_transactions.append({
                'Date': trans['transaction_date'],
                'Description': trans['description'],
                'Category': trans['category'],
                'Amount': trans['amount'],
                'Type': trans['type'],
                'Source': 'Imported',
                'ID': trans['id']
            })
        
        # Add recurring expenses for this month
        for expense in recurring_expenses:
            if expense['is_active']:
                start_date_exp = datetime.strptime(expense['start_date'], '%Y-%m-%d').date()
                end_date_exp = None
                if expense['end_date']:
                    end_date_exp = datetime.strptime(expense['end_date'], '%Y-%m-%d').date()
                
                if start_date_exp <= month_end and (end_date_exp is None or end_date_exp >= month_start):
                    monthly_amount = calculate_prorated_amount(expense['amount'], expense['frequency'])
                    all_month_transactions.append({
                        'Date': month_start,
                        'Description': f"{expense['name']} (Recurring)",
                        'Category': expense['category'],
                        'Amount': -monthly_amount,
                        'Type': 'Recurring',
                        'Source': 'Fixed',
                        'ID': None
                    })
        
        # Sort by date descending
        all_month_transactions.sort(key=lambda x: x['Date'], reverse=True)
        
        # Quick categorization section
        st.markdown("#### Quick Categorize Recent Transactions")
        
        # Get uncategorized transactions
        uncategorized_trans = [t for t in all_month_transactions if t['Category'] == 'Uncategorized' and t['ID'] is not None]
        
        if uncategorized_trans:
            st.write(f"Found {len(uncategorized_trans)} uncategorized transactions:")
            
            # Get available categories
            available_categories = get_categories()
            
            # Show first 5 uncategorized for quick categorization
            for i, trans in enumerate(uncategorized_trans[:5]):
                col1, col2, col3, col4, col5 = st.columns([2, 3, 1, 2, 1])
                
                with col1:
                    st.write(trans['Date'])
                
                with col2:
                    st.write(trans['Description'][:40] + "..." if len(trans['Description']) > 40 else trans['Description'])
                
                with col3:
                    st.write(format_currency(trans['Amount']))
                
                with col4:
                    new_category = st.selectbox(
                        "Category",
                        options=available_categories,
                        key=f"quick_cat_{trans['ID']}",
                        label_visibility="collapsed"
                    )
                
                with col5:
                    if st.button("Update", key=f"quick_update_{trans['ID']}"):
                        if update_transaction_category(trans['ID'], new_category):
                            st.success("Updated!")
                            st.rerun()
            
            if len(uncategorized_trans) > 5:
                st.info(f"+ {len(uncategorized_trans) - 5} more uncategorized transactions. Visit 'Categorize Transactions' page for bulk operations.")
        else:
            st.success("✅ All transactions are categorized!")
        
        # Display all transactions table with management options
        st.markdown("#### Complete Transaction List")
        
        # Add transaction management expander
        with st.expander("✏️ Add, Edit, or Delete Transactions", expanded=False):
            mgmt_tab1, mgmt_tab2, mgmt_tab3 = st.tabs(["Add Transaction", "Edit Transaction", "Delete Transaction"])
            
            with mgmt_tab1:
                st.write("**Add a new manual transaction**")
                with st.form("add_trans_form_home"):
                    col1, col2 = st.columns(2)
                    with col1:
                        add_date = st.date_input("Date", value=date.today())
                        add_desc = st.text_input("Description")
                    with col2:
                        add_category = st.selectbox("Category", options=get_categories())
                        add_amount = st.number_input("Amount", value=0.0, step=0.01)
                    
                    add_type = st.selectbox("Type", options=["Debit", "Credit"], key="add_type_home")
                    
                    if st.form_submit_button("Add Transaction"):
                        if add_desc:
                            add_transaction(add_date, add_desc, add_category, -add_amount if add_type == "Debit" else add_amount, add_type)
                            st.success("Transaction added!")
                            st.rerun()
            
            with mgmt_tab2:
                st.write("**Edit an existing transaction**")
                edit_trans_list = [f"{t['ID']} - {t['Date']} - {t['Description'][:40]}" for t in all_month_transactions if t['ID'] is not None]
                
                if edit_trans_list:
                    selected_trans = st.selectbox("Select transaction", options=edit_trans_list, key="edit_select_home")
                    selected_trans_id = int(selected_trans.split(' - ')[0])
                    selected_trans_obj = next((t for t in all_month_transactions if t['ID'] == selected_trans_id), None)
                    
                    if selected_trans_obj:
                        with st.form("edit_trans_form_home"):
                            col1, col2 = st.columns(2)
                            with col1:
                                edit_date = st.date_input("Date", value=selected_trans_obj['Date'])
                                edit_desc = st.text_input("Description", value=selected_trans_obj['Description'])
                            with col2:
                                edit_category = st.selectbox("Category", options=get_categories(), 
                                                             index=get_categories().index(selected_trans_obj['Category']) if selected_trans_obj['Category'] in get_categories() else 0)
                                edit_amount = st.number_input("Amount", value=selected_trans_obj['Amount'], step=0.01)
                            
                            if st.form_submit_button("Update Transaction"):
                                edit_transaction(selected_trans_id, edit_date, edit_desc, edit_category, edit_amount)
                                st.success("Transaction updated!")
                                st.rerun()
                else:
                    st.info("No transactions to edit")
            
            with mgmt_tab3:
                st.write("**Delete a transaction**")
                del_trans_list = [f"{t['ID']} - {t['Date']} - {t['Description'][:40]}" for t in all_month_transactions if t['ID'] is not None]
                
                if del_trans_list:
                    selected_del = st.selectbox("Select transaction to delete", options=del_trans_list, key="del_select_home")
                    selected_del_id = int(selected_del.split(' - ')[0])
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.warning(f"Are you sure you want to delete: {selected_del}?")
                    with col2:
                        if st.button("Delete", key="delete_btn_home", type="secondary"):
                            delete_transaction(selected_del_id)
                            st.success("Transaction deleted!")
                            st.rerun()
                else:
                    st.info("No transactions to delete")
        
        df_all = pd.DataFrame(all_month_transactions)
        
        # Format amounts for display
        df_display = df_all.copy()
        df_display['Amount'] = df_display['Amount'].apply(lambda x: format_currency(x))
        
        st.dataframe(
            df_display[['Date', 'Description', 'Category', 'Amount', 'Type', 'Source']],
            use_container_width=True
        )
        
        # Summary for the month
        total_expenses = sum([abs(t['Amount']) for t in all_month_transactions if t['Amount'] < 0])
        total_income = sum([t['Amount'] for t in all_month_transactions if t['Amount'] > 0])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Expenses", format_currency(total_expenses))
        with col2:
            st.metric("Total Income", format_currency(total_income))
        with col3:
            st.metric("Net", format_currency(total_income - total_expenses))
    
    else:
        st.info("No transactions found for this month. Upload bank statements to get started!")

# Export transactions section
st.markdown("---")
st.subheader("📥 Export Transactions")

with st.expander("Export to CSV or Excel", expanded=False):
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        st.write("**Select Date Range**")
        export_date_range = st.selectbox(
            "Time Frame",
            options=["Current Month", "Last 30 days", "Last 90 days", "Last 6 months", "This Year", "Custom Range"],
            key="export_date_range"
        )
        
        if export_date_range == "Current Month":
            export_start = month_start
            export_end = month_end
        elif export_date_range == "Last 30 days":
            export_start = date.today() - timedelta(days=30)
            export_end = date.today()
        elif export_date_range == "Last 90 days":
            export_start = date.today() - timedelta(days=90)
            export_end = date.today()
        elif export_date_range == "Last 6 months":
            export_start = date.today() - timedelta(days=180)
            export_end = date.today()
        elif export_date_range == "This Year":
            export_start = date(date.today().year, 1, 1)
            export_end = date.today()
        else:  # Custom Range
            col_s, col_e = st.columns(2)
            with col_s:
                export_start = st.date_input("Start Date", value=date.today() - timedelta(days=30), key="export_start")
            with col_e:
                export_end = st.date_input("End Date", value=date.today(), key="export_end")
    
    with export_col2:
        st.write("**Select Format**")
        export_format = st.radio("File Format", options=["CSV", "Excel"], horizontal=True)
    
    # Get transactions for export
    export_transactions = get_all_transactions(export_start, export_end)
    
    if export_transactions:
        df_export = pd.DataFrame(export_transactions)
        df_export['amount_formatted'] = df_export['amount'].apply(format_currency)
        
        # Create export dataframe with nice columns
        df_export_display = df_export[['transaction_date', 'description', 'category', 'amount', 'type', 'amount_formatted']].copy()
        df_export_display.columns = ['Date', 'Description', 'Category', 'Amount', 'Type', 'Amount (Formatted)']
        
        col_preview, col_button = st.columns([2, 1])
        
        with col_preview:
            st.write(f"**Preview** ({len(df_export)} transactions)")
            st.dataframe(df_export_display.head(10), use_container_width=True)
        
        with col_button:
            st.write("")
            st.write("")
            if export_format == "CSV":
                csv = df_export_display.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"transactions_{export_start}_to_{export_end}.csv",
                    mime="text/csv"
                )
            else:  # Excel
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_export_display.to_excel(writer, index=False, sheet_name='Transactions')
                output.seek(0)
                st.download_button(
                    label="📥 Download Excel",
                    data=output.getvalue(),
                    file_name=f"transactions_{export_start}_to_{export_end}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("No transactions found for the selected date range.")
