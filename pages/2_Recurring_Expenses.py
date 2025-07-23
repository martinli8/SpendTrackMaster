import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from database import insert_recurring_expense, get_recurring_expenses, delete_recurring_expense, get_categories, add_category
from utils import calculate_prorated_amount, format_currency

st.set_page_config(
    page_title="Recurring Expenses",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 Recurring Expenses Management")
st.markdown("Manage your fixed costs and recurring expenses that don't appear in bank statements.")

# Tabs for different sections
tab1, tab2 = st.tabs(["Add New Expense", "Manage Existing"])

with tab1:
    st.subheader("Add New Recurring Expense")
    
    with st.form("add_recurring_expense"):
        col1, col2 = st.columns(2)
        
        with col1:
            expense_name = st.text_input(
                "Expense Name *",
                placeholder="e.g., Rent, Gym Membership, Netflix"
            )
            
            # Get existing categories
            expense_categories = get_categories('expense')
            
            category = st.selectbox(
                "Category *",
                options=expense_categories,
                index=expense_categories.index('Uncategorized') if 'Uncategorized' in expense_categories else 0
            )
            
            # Option to add new category
            if st.checkbox("Add new category"):
                new_category = st.text_input("New Category Name")
                if new_category:
                    if add_category(new_category, 'expense'):
                        st.success(f"Added new category: {new_category}")
                        st.rerun()
                    else:
                        st.error("Category already exists")
        
        with col2:
            amount = st.number_input(
                "Amount *",
                min_value=0.01,
                step=0.01,
                format="%.2f"
            )
            
            frequency = st.selectbox(
                "Frequency *",
                options=['monthly', 'quarterly', 'semi-annually', 'annually'],
                help="How often this expense occurs"
            )
        
        col3, col4 = st.columns(2)
        
        with col3:
            start_date = st.date_input(
                "Start Date *",
                value=datetime.now().date(),
                help="When this expense starts/started"
            )
        
        with col4:
            has_end_date = st.checkbox("Has End Date")
            end_date = None
            if has_end_date:
                end_date = st.date_input(
                    "End Date",
                    value=datetime.now().date() + timedelta(days=365),
                    help="When this expense ends (leave unchecked for ongoing)"
                )
        
        # Show monthly equivalent
        if amount > 0:
            monthly_amount = calculate_prorated_amount(amount, frequency)
            st.info(f"Monthly equivalent: {format_currency(monthly_amount)}")
        
        submitted = st.form_submit_button("Add Recurring Expense")
        
        if submitted:
            if not expense_name or not category or amount <= 0:
                st.error("Please fill in all required fields marked with *")
            else:
                try:
                    expense_id = insert_recurring_expense(
                        name=expense_name,
                        category=category,
                        amount=amount,
                        frequency=frequency,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if expense_id:
                        st.success(f"Successfully added recurring expense: {expense_name}")
                        st.rerun()
                    else:
                        st.error("Failed to add recurring expense")
                        
                except Exception as e:
                    st.error(f"Error adding recurring expense: {str(e)}")

with tab2:
    st.subheader("Existing Recurring Expenses")
    
    # Get all recurring expenses
    recurring_expenses = get_recurring_expenses()
    
    if not recurring_expenses:
        st.info("No recurring expenses found. Add some using the form above.")
    else:
        # Create DataFrame for display
        display_data = []
        total_monthly = 0
        
        for expense in recurring_expenses:
            monthly_amount = calculate_prorated_amount(expense['amount'], expense['frequency'])
            total_monthly += monthly_amount
            
            display_data.append({
                'ID': expense['id'],
                'Name': expense['name'],
                'Category': expense['category'],
                'Amount': format_currency(expense['amount']),
                'Frequency': expense['frequency'].title(),
                'Monthly Equivalent': format_currency(monthly_amount),
                'Start Date': expense['start_date'],
                'End Date': expense['end_date'] if expense['end_date'] else 'Ongoing',
                'Status': 'Active' if expense['is_active'] else 'Inactive'
            })
        
        df_expenses = pd.DataFrame(display_data)
        
        # Show summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Recurring Expenses", len(recurring_expenses))
        with col2:
            st.metric("Total Monthly Amount", format_currency(total_monthly))
        with col3:
            active_count = len([e for e in recurring_expenses if e['is_active']])
            st.metric("Active Expenses", active_count)
        
        # Display table
        st.dataframe(
            df_expenses.drop('ID', axis=1),  # Hide ID column
            use_container_width=True
        )
        
        # Delete functionality
        st.markdown("---")
        st.subheader("Delete Recurring Expense")
        
        expense_options = {f"{e['name']} ({e['category']})": e['id'] for e in recurring_expenses}
        
        if expense_options:
            selected_expense = st.selectbox(
                "Select expense to delete",
                options=list(expense_options.keys()),
                key="delete_expense_select"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("Delete Selected", type="secondary"):
                    expense_id = expense_options[selected_expense]
                    if delete_recurring_expense(expense_id):
                        st.success(f"Deleted expense: {selected_expense}")
                        st.rerun()
                    else:
                        st.error("Failed to delete expense")
            
            with col2:
                st.warning("⚠️ Deleting an expense will mark it as inactive but preserve historical data.")

# Category breakdown
if recurring_expenses:
    st.markdown("---")
    st.subheader("Monthly Spending by Category")
    
    # Calculate monthly totals by category
    category_totals = {}
    for expense in recurring_expenses:
        if expense['is_active']:
            category = expense['category']
            monthly_amount = calculate_prorated_amount(expense['amount'], expense['frequency'])
            category_totals[category] = category_totals.get(category, 0) + monthly_amount
    
    if category_totals:
        # Create visualization
        import plotly.express as px
        
        df_categories = pd.DataFrame([
            {'Category': cat, 'Monthly Amount': amount}
            for cat, amount in category_totals.items()
        ])
        
        fig = px.pie(
            df_categories,
            values='Monthly Amount',
            names='Category',
            title='Monthly Recurring Expenses by Category'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show category breakdown table
        df_categories['Monthly Amount'] = df_categories['Monthly Amount'].apply(format_currency)
        st.dataframe(df_categories, use_container_width=True)

# Help section
st.markdown("---")
st.subheader("Help & Tips")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Frequency Options:**
    - **Monthly**: Occurs every month (rent, subscriptions)
    - **Quarterly**: Occurs every 3 months (some insurance payments)
    - **Semi-annually**: Occurs every 6 months (some subscriptions)
    - **Annually**: Occurs once per year (annual memberships, insurance)
    """)

with col2:
    st.markdown("""
    **Monthly Equivalent Calculation:**
    - The system automatically calculates how much each expense costs per month
    - This helps with budgeting and comparing expenses
    - All frequencies are prorated to monthly amounts for consistent tracking
    """)

st.info("💡 **Tip**: Add all your fixed costs here (rent, insurance, subscriptions) to get a complete picture of your monthly obligations alongside your imported bank transactions.")
