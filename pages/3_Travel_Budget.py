import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from database import add_travel_allocation, add_travel_expense, get_travel_budget_balance, get_travel_transactions
from utils import format_currency

st.set_page_config(
    page_title="Travel Budget",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Travel Budget Management")
st.markdown("Manage your travel fund with monthly allocations and expense tracking.")

# Current balance display
current_balance = get_travel_budget_balance()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        "Current Travel Balance",
        format_currency(current_balance),
        help="Total available travel funds"
    )

# Quick actions
st.markdown("---")
st.subheader("Quick Actions")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Add Monthly Allocation")
    with st.form("monthly_allocation"):
        allocation_amount = st.number_input(
            "Monthly Allocation Amount",
            value=500.00,
            min_value=0.01,
            step=1.00,
            format="%.2f"
        )
        
        allocation_date = st.date_input(
            "Allocation Date",
            value=datetime.now().date()
        )
        
        if st.form_submit_button("Add Allocation"):
            try:
                allocation_id = add_travel_allocation(allocation_amount, allocation_date)
                if allocation_id:
                    st.success(f"Added ${allocation_amount:.2f} to travel budget!")
                    st.rerun()
                else:
                    st.error("Failed to add allocation")
            except Exception as e:
                st.error(f"Error adding allocation: {str(e)}")

with col2:
    st.markdown("#### Record Travel Expense")
    with st.form("travel_expense"):
        expense_description = st.text_input(
            "Expense Description",
            placeholder="e.g., Flight to NYC, Hotel booking, Car rental"
        )
        
        expense_amount = st.number_input(
            "Expense Amount",
            min_value=0.01,
            step=1.00,
            format="%.2f"
        )
        
        expense_date = st.date_input(
            "Expense Date",
            value=datetime.now().date()
        )
        
        if st.form_submit_button("Record Expense"):
            if not expense_description:
                st.error("Please provide an expense description")
            elif expense_amount > current_balance:
                st.error(f"Insufficient travel funds! Available: {format_currency(current_balance)}")
            else:
                try:
                    expense_id = add_travel_expense(expense_description, expense_amount, expense_date)
                    if expense_id:
                        st.success(f"Recorded travel expense: {expense_description}")
                        st.rerun()
                    else:
                        st.error("Failed to record expense")
                except Exception as e:
                    st.error(f"Error recording expense: {str(e)}")

# Travel transaction history
st.markdown("---")
st.subheader("Travel Budget History")

# Date range filter
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "Start Date",
        value=date(datetime.now().year, 1, 1)
    )
with col2:
    end_date = st.date_input(
        "End Date",
        value=datetime.now().date()
    )

# Get transactions
travel_transactions = get_travel_transactions(start_date, end_date)

if travel_transactions:
    # Process transactions for display
    display_data = []
    running_balance = 0
    
    # Sort by date (oldest first) to calculate running balance
    sorted_transactions = sorted(travel_transactions, key=lambda x: x['transaction_date'])
    
    for transaction in sorted_transactions:
        running_balance += transaction['amount']
        display_data.append({
            'Date': transaction['transaction_date'],
            'Description': transaction['description'],
            'Type': transaction['type'].title(),
            'Amount': format_currency(abs(transaction['amount'])),
            'Balance After': format_currency(running_balance),
            'ID': transaction['id']
        })
    
    # Reverse for display (newest first)
    display_data.reverse()
    
    df_transactions = pd.DataFrame(display_data)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    allocations = [t for t in travel_transactions if t['type'] == 'allocation']
    expenses = [t for t in travel_transactions if t['type'] == 'expense']
    
    with col1:
        total_allocations = sum(t['amount'] for t in allocations)
        st.metric("Total Allocations", format_currency(total_allocations))
    
    with col2:
        total_expenses = sum(abs(t['amount']) for t in expenses)
        st.metric("Total Expenses", format_currency(total_expenses))
    
    with col3:
        st.metric("Net Savings", format_currency(total_allocations - total_expenses))
    
    with col4:
        st.metric("Number of Transactions", len(travel_transactions))
    
    # Display transactions table
    st.dataframe(
        df_transactions.drop('ID', axis=1),
        use_container_width=True
    )
    
    # Monthly allocation vs expenses chart
    if len(travel_transactions) > 1:
        st.markdown("---")
        st.subheader("Monthly Travel Budget Trend")
        
        # Group by month
        df_for_chart = pd.DataFrame(travel_transactions)
        df_for_chart['transaction_date'] = pd.to_datetime(df_for_chart['transaction_date'])
        df_for_chart['month'] = df_for_chart['transaction_date'].dt.to_period('M')
        
        monthly_summary = []
        for month in df_for_chart['month'].unique():
            month_data = df_for_chart[df_for_chart['month'] == month]
            allocations_amount = sum(row['amount'] for _, row in month_data.iterrows() if row['type'] == 'allocation')
            expenses_amount = sum(abs(row['amount']) for _, row in month_data.iterrows() if row['type'] == 'expense')
            
            monthly_summary.append({
                'Month': str(month),
                'Allocations': allocations_amount,
                'Expenses': expenses_amount,
                'Net': allocations_amount - expenses_amount
            })
        
        df_monthly = pd.DataFrame(monthly_summary)
        
        if not df_monthly.empty:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='Allocations',
                x=df_monthly['Month'],
                y=df_monthly['Allocations'],
                marker_color='lightgreen'
            ))
            
            fig.add_trace(go.Bar(
                name='Expenses',
                x=df_monthly['Month'],
                y=df_monthly['Expenses'],
                marker_color='lightcoral'
            ))
            
            fig.update_layout(
                title='Monthly Travel Budget: Allocations vs Expenses',
                xaxis_title='Month',
                yaxis_title='Amount ($)',
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Travel balance over time
        st.subheader("Travel Balance Over Time")
        
        # Calculate cumulative balance
        df_balance = pd.DataFrame(sorted_transactions)
        df_balance['transaction_date'] = pd.to_datetime(df_balance['transaction_date'])
        df_balance = df_balance.sort_values('transaction_date')
        df_balance['cumulative_balance'] = df_balance['amount'].cumsum()
        
        fig_line = px.line(
            df_balance,
            x='transaction_date',
            y='cumulative_balance',
            title='Travel Budget Balance Over Time',
            markers=True
        )
        
        fig_line.update_layout(
            xaxis_title='Date',
            yaxis_title='Balance ($)',
            height=400
        )
        
        st.plotly_chart(fig_line, use_container_width=True)

else:
    st.info("No travel transactions found for the selected date range.")

# Automated monthly allocation setup
st.markdown("---")
st.subheader("Automated Monthly Allocation")

st.info("""
💡 **Quick Setup**: You can manually add your $500 monthly allocation using the form above.
For automated monthly allocations, you would typically set up a recurring calendar reminder
or integrate with your bank's automatic transfer system.
""")

# Tips and help
st.markdown("---")
st.subheader("Travel Budget Tips")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **How It Works:**
    - Add $500 (or any amount) monthly to build your travel fund
    - Record expenses to deduct from your available balance
    - Track your savings progress over time
    - Plan trips based on available funds
    """)

with col2:
    st.markdown("""
    **Best Practices:**
    - Set up automatic monthly transfers
    - Record expenses promptly for accurate tracking
    - Use descriptive names for expenses
    - Review monthly to stay on budget
    """)

# Travel fund projections
st.markdown("---")
st.subheader("Travel Fund Projections")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### If you save $500/month:")
    months_6 = 6 * 500 + current_balance
    months_12 = 12 * 500 + current_balance
    
    st.write(f"• In 6 months: {format_currency(months_6)}")
    st.write(f"• In 12 months: {format_currency(months_12)}")

with col2:
    st.markdown("#### Custom Projection:")
    monthly_save = st.number_input("Monthly savings amount", value=500.0, step=50.0)
    months_ahead = st.slider("Months ahead", 1, 24, 12)
    
    projected_balance = months_ahead * monthly_save + current_balance
    st.write(f"Projected balance: {format_currency(projected_balance)}")
