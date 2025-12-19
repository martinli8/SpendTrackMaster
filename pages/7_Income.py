import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from database import (
    add_income_entry,
    get_income_entries,
    edit_income_entry,
    delete_income_entry,
    get_monthly_income_by_category,
    get_monthly_income_total,
    get_income_categories,
    get_monthly_summary
)
from utils import format_currency, get_month_name

st.set_page_config(
    page_title="Income Tracking",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Income Tracking")
st.markdown("Track your income month by month and by source. Add manual income entries to keep accurate records.")

# Income categories
income_categories = ["Martin's Paycheck", "Rachel's Paycheck", "Misc Income", "Money from Mom"]

st.markdown("---")

# Add Income Section
st.subheader("➕ Add Income Entry")

with st.form("add_income_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        income_date = st.date_input("Date", value=date.today())
        income_category = st.selectbox(
            "Income Source",
            options=income_categories,
            help="Select the source of this income"
        )
    
    with col2:
        income_description = st.text_input("Description", placeholder="e.g., Bi-weekly paycheck, Bonus, etc.")
        income_amount = st.number_input("Amount", value=0.01, step=0.01, min_value=0.01, format="%.2f")
    
    submitted = st.form_submit_button("Add Income", type="primary")
    
    if submitted:
        if income_description and income_amount > 0:
            # Add to dedicated income table
            income_id = add_income_entry(
                income_date,
                income_description,
                income_category,
                income_amount
            )
            st.success(f"✅ Added {format_currency(income_amount)} from {income_category}")
            st.rerun()
        else:
            st.error("Please fill in all fields and ensure amount is greater than 0")

st.markdown("---")

# Month Selection
st.subheader("📅 View Income by Month")

col1, col2 = st.columns(2)
with col1:
    selected_year = st.selectbox(
        "Year",
        options=list(range(2020, datetime.now().year + 2)),
        index=datetime.now().year - 2020
    )

with col2:
    months = list(range(1, 13))
    month_names = [calendar.month_name[m] for m in months]
    selected_month = st.selectbox(
        "Month",
        options=months,
        format_func=lambda x: month_names[x - 1],
        index=datetime.now().month - 1
    )

month_start = date(selected_year, selected_month, 1)
month_end = date(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1])

# Get income for selected month (from dedicated income table)
income_transactions = get_income_entries(month_start, month_end)

# Summary metrics
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

total_income = sum(entry['amount'] for entry in income_transactions)
with col1:
    st.metric("Total Income", format_currency(total_income))

income_by_category = get_monthly_income_by_category(selected_year, selected_month)
with col2:
    martin_paycheck = income_by_category.get("Martin's Paycheck", 0)
    st.metric("Martin's Paycheck", format_currency(martin_paycheck))

with col3:
    rachel_paycheck = income_by_category.get("Rachel's Paycheck", 0)
    st.metric("Rachel's Paycheck", format_currency(rachel_paycheck))

with col4:
    other_income = total_income - martin_paycheck - rachel_paycheck
    st.metric("Other Income", format_currency(other_income))

# Income breakdown by category
st.markdown("---")
st.subheader("📊 Income Breakdown by Source")

if income_by_category:
    category_data = []
    for category, amount in income_by_category.items():
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        category_data.append({
            'Source': category,
            'Amount': amount,
            'Percentage': f"{percentage:.1f}%"
        })
    
    category_data.sort(key=lambda x: x['Amount'], reverse=True)
    
    for item in category_data:
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.write(f"**{item['Source']}**")
        with col2:
            st.write(format_currency(item['Amount']))
        with col3:
            st.write(item['Percentage'])
    
    # Create pie chart
    if len(category_data) > 1:
        import plotly.express as px
        df_pie = pd.DataFrame(category_data)
        fig = px.pie(
            df_pie,
            values='Amount',
            names='Source',
            title=f"Income Breakdown - {get_month_name(selected_month)} {selected_year}"
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No income recorded for this month.")

# Income transactions list
st.markdown("---")
st.subheader(f"📋 Income Transactions - {get_month_name(selected_month)} {selected_year}")

if income_transactions:
    # Search functionality
    search_term = st.text_input("🔍 Search income transactions", placeholder="Search by description...", key="income_search")
    
    filtered_transactions = income_transactions
    if search_term:
        filtered_transactions = [
            t for t in income_transactions
            if search_term.lower() in t['description'].lower() or search_term.lower() in t.get('source', '').lower()
        ]
    
    if filtered_transactions:
        # Display transactions with edit/delete options
        for idx, transaction in enumerate(filtered_transactions):
            edit_key = f"edit_income_{transaction['id']}"
            delete_key = f"delete_income_{transaction['id']}"
            
            col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 1, 1])
            
            with col1:
                st.write(str(transaction['income_date']))
            
            with col2:
                st.write(transaction['description'])
            
            with col3:
                st.write(f"**{transaction.get('source', 'Uncategorized')}**")
            
            with col4:
                st.write(format_currency(transaction['amount']))
            
            with col5:
                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button("✏️", key=edit_key, help="Edit"):
                        st.session_state[f"edit_income_{transaction['id']}"] = True
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=delete_key, help="Delete"):
                        if delete_income_entry(transaction['id']):
                            st.success("Income entry deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete")
            
            # Edit form
            if f"edit_income_{transaction['id']}" in st.session_state and st.session_state[f"edit_income_{transaction['id']}"]:
                with st.expander(f"Edit Income Entry {transaction['id']}", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        date_value = transaction['income_date']
                        if isinstance(date_value, str):
                            date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
                        elif not isinstance(date_value, date):
                            date_value = date.today()
                        
                        edit_date = st.date_input("Date", value=date_value, key=f"income_edit_date_{transaction['id']}")
                        edit_desc = st.text_input("Description", value=transaction['description'], key=f"income_edit_desc_{transaction['id']}")
                    
                    with col2:
                        edit_source = st.selectbox(
                            "Source",
                            options=income_categories,
                            index=income_categories.index(transaction['source']) if transaction['source'] in income_categories else 0,
                            key=f"income_edit_source_{transaction['id']}"
                        )
                        edit_amount = st.number_input("Amount", value=float(transaction['amount']), step=0.01, min_value=0.01, key=f"income_edit_amt_{transaction['id']}")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("💾 Save", key=f"income_save_{transaction['id']}", type="primary", use_container_width=True):
                            if edit_income_entry(transaction['id'], edit_date, edit_desc, edit_source, edit_amount):
                                st.success("Income entry updated!")
                                st.session_state[f"edit_income_{transaction['id']}"] = False
                                st.rerun()
                            else:
                                st.error("Failed to update")
                    
                    with col2:
                        if st.button("❌ Cancel", key=f"income_cancel_{transaction['id']}", use_container_width=True):
                            st.session_state[f"edit_income_{transaction['id']}"] = False
                            st.rerun()
        
        st.markdown(f"*Showing {len(filtered_transactions)} of {len(income_transactions)} income transaction(s)*")
    else:
        st.info("No income transactions match your search.")
else:
    st.info("No income recorded for this month. Add income entries above to get started.")

# Monthly comparison
st.markdown("---")
st.subheader("📈 Monthly Income Comparison")

# Get last 12 months of income
comparison_data = []
for i in range(12):
    calc_date = date.today()
    if calc_date.month - i <= 0:
        calc_year = calc_date.year - 1
        calc_month = 12 + (calc_date.month - i)
    else:
        calc_year = calc_date.year
        calc_month = calc_date.month - i
    
    month_income = get_monthly_income_total(calc_year, calc_month)
    
    comparison_data.append({
        'Month': f"{get_month_name(calc_month)} {calc_year}",
        'Income': month_income
    })

comparison_data.reverse()  # Show oldest first

if comparison_data:
    df_comparison = pd.DataFrame(comparison_data)
    
    import plotly.express as px
    fig = px.bar(
        df_comparison,
        x='Month',
        y='Income',
        title="Monthly Income Trend (Last 12 Months)",
        labels={'Income': 'Income ($)', 'Month': 'Month'}
    )
    fig.update_xaxes(tickangle=45)
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary table
    st.dataframe(df_comparison, use_container_width=True, hide_index=True)

# Help section
st.markdown("---")
st.subheader("💡 Tips")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Income Categories:**
    - **Martin's Paycheck**: Regular paychecks from Martin's job
    - **Rachel's Paycheck**: Regular paychecks from Rachel's job
    - **Misc Income**: Other income sources (bonuses, freelance, etc.)
    - **Money from Mom**: Financial assistance from Mom
    """)

with col2:
    st.markdown("""
    **Best Practices:**
    - Add income entries as soon as you receive them
    - Use descriptive descriptions (e.g., "Bi-weekly paycheck", "Q1 Bonus")
    - Review monthly to ensure accuracy
    - Compare month-over-month to track income trends
    """)

