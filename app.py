import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, date
import calendar
from database import init_database, get_all_transactions, get_recurring_expenses, get_travel_budget_balance, get_monthly_summary
from utils import get_month_name, calculate_prorated_amount

# Initialize the database
init_database()

st.set_page_config(
    page_title="Spend Tracker Dashboard",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Comprehensive Spend Tracker")
st.markdown("---")

# Sidebar for date range selection
st.sidebar.header("Date Range Selection")
current_date = datetime.now()
start_date = st.sidebar.date_input(
    "Start Date",
    value=date(current_date.year, 1, 1)
)
end_date = st.sidebar.date_input(
    "End Date",
    value=current_date.date()
)

# Main dashboard content
col1, col2, col3 = st.columns(3)

# Get travel budget balance
travel_balance = get_travel_budget_balance()

with col1:
    st.metric(
        label="Travel Budget Balance",
        value=f"${travel_balance:,.2f}"
    )

with col2:
    # Calculate current month expenses
    current_month_summary = get_monthly_summary(
        current_date.year, 
        current_date.month
    )
    current_month_total = (
        current_month_summary['imported_expenses'] + 
        current_month_summary['recurring_expenses'] + 
        current_month_summary['travel_expenses']
    )
    st.metric(
        label="Current Month Total Spend",
        value=f"${current_month_total:,.2f}"
    )

with col3:
    # Calculate average monthly spend
    monthly_summaries = []
    for year in range(start_date.year, end_date.year + 1):
        start_month = start_date.month if year == start_date.year else 1
        end_month = end_date.month if year == end_date.year else 12
        
        for month in range(start_month, end_month + 1):
            summary = get_monthly_summary(year, month)
            total = summary['imported_expenses'] + summary['recurring_expenses'] + summary['travel_expenses']
            monthly_summaries.append(total)
    
    avg_monthly = sum(monthly_summaries) / len(monthly_summaries) if monthly_summaries else 0
    st.metric(
        label="Average Monthly Spend",
        value=f"${avg_monthly:,.2f}"
    )

st.markdown("---")

# Monthly spend breakdown chart
st.subheader("Monthly Spend Breakdown")

# Prepare data for monthly chart
monthly_data = []
for year in range(start_date.year, end_date.year + 1):
    start_month = start_date.month if year == start_date.year else 1
    end_month = end_date.month if year == end_date.year else 12
    
    for month in range(start_month, end_month + 1):
        summary = get_monthly_summary(year, month)
        monthly_data.append({
            'Month': f"{get_month_name(month)} {year}",
            'Year': year,
            'MonthNum': month,
            'Imported Expenses': summary['imported_expenses'],
            'Recurring Expenses': summary['recurring_expenses'],
            'Travel Expenses': summary['travel_expenses'],
            'Total': summary['imported_expenses'] + summary['recurring_expenses'] + summary['travel_expenses']
        })

if monthly_data:
    df_monthly = pd.DataFrame(monthly_data)
    
    # Create stacked bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Imported Expenses',
        x=df_monthly['Month'],
        y=df_monthly['Imported Expenses'],
        marker_color='lightblue'
    ))
    
    fig.add_trace(go.Bar(
        name='Recurring Expenses',
        x=df_monthly['Month'],
        y=df_monthly['Recurring Expenses'],
        marker_color='lightgreen'
    ))
    
    fig.add_trace(go.Bar(
        name='Travel Expenses',
        x=df_monthly['Month'],
        y=df_monthly['Travel Expenses'],
        marker_color='lightcoral'
    ))
    
    fig.update_layout(
        barmode='stack',
        title='Monthly Spend Breakdown',
        xaxis_title='Month',
        yaxis_title='Amount ($)',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data available for the selected date range. Please upload statements and add recurring expenses.")

# Category breakdown
st.markdown("---")
st.subheader("Spend by Category")

col1, col2 = st.columns(2)

with col1:
    # Get all transactions for category analysis
    transactions = get_all_transactions(start_date, end_date)
    
    if transactions:
        df_transactions = pd.DataFrame(transactions)
        category_totals = df_transactions.groupby('category')['amount'].sum().abs()
        
        fig_pie = px.pie(
            values=category_totals.values,
            names=category_totals.index,
            title='Imported Transactions by Category'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No imported transactions found for the selected date range.")

with col2:
    # Recurring expenses by category
    recurring_expenses = get_recurring_expenses()
    
    if recurring_expenses:
        df_recurring = pd.DataFrame(recurring_expenses)
        
        # Calculate monthly amounts for each recurring expense
        monthly_amounts = []
        for _, expense in df_recurring.iterrows():
            monthly_amount = calculate_prorated_amount(expense['amount'], expense['frequency'])
            monthly_amounts.append({
                'category': expense['category'],
                'monthly_amount': monthly_amount
            })
        
        df_recurring_monthly = pd.DataFrame(monthly_amounts)
        recurring_category_totals = df_recurring_monthly.groupby('category')['monthly_amount'].sum()
        
        fig_pie_recurring = px.pie(
            values=recurring_category_totals.values,
            names=recurring_category_totals.index,
            title='Recurring Expenses by Category (Monthly)'
        )
        st.plotly_chart(fig_pie_recurring, use_container_width=True)
    else:
        st.info("No recurring expenses defined.")

# Recent transactions
st.markdown("---")
st.subheader("Recent Transactions")

recent_transactions = get_all_transactions(start_date, end_date, limit=20)
if recent_transactions:
    df_recent = pd.DataFrame(recent_transactions)
    df_recent['amount'] = df_recent['amount'].round(2)
    df_recent = df_recent.sort_values('transaction_date', ascending=False)
    
    st.dataframe(
        df_recent[['transaction_date', 'description', 'category', 'amount', 'type']],
        use_container_width=True
    )
else:
    st.info("No recent transactions found.")

# Summary statistics
st.markdown("---")
st.subheader("Summary Statistics")

if monthly_data:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_imported = sum([d['Imported Expenses'] for d in monthly_data])
        st.metric("Total Imported Expenses", f"${total_imported:,.2f}")
    
    with col2:
        total_recurring = sum([d['Recurring Expenses'] for d in monthly_data])
        st.metric("Total Recurring Expenses", f"${total_recurring:,.2f}")
    
    with col3:
        total_travel = sum([d['Travel Expenses'] for d in monthly_data])
        st.metric("Total Travel Expenses", f"${total_travel:,.2f}")
    
    with col4:
        grand_total = total_imported + total_recurring + total_travel
        st.metric("Grand Total", f"${grand_total:,.2f}")

# Instructions for new users
if not monthly_data:
    st.markdown("---")
    st.subheader("Getting Started")
    st.markdown("""
    Welcome to your Spend Tracker! To get started:
    
    1. **Upload Bank Statements**: Go to the "Upload Statements" page to import your CSV/Excel files
    2. **Add Recurring Expenses**: Visit "Recurring Expenses" to add fixed costs like rent, subscriptions, etc.
    3. **Set Up Travel Budget**: Use "Travel Budget" to manage your $500 monthly travel fund
    4. **Categorize Transactions**: Go to "Categorize Transactions" to organize your imported expenses
    
    Once you have data, this dashboard will show comprehensive insights into your spending patterns!
    """)
