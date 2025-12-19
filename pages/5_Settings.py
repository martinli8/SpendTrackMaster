import streamlit as st
import pandas as pd
from database import get_all_categories, add_category, delete_category

st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ Settings")
st.markdown("Manage your application settings and categories.")

st.markdown("---")

# Category Management Section
st.subheader("📂 Category Management")

col1, col2 = st.columns(2)

# Left column: Add new category
with col1:
    st.write("**Add New Category**")
    with st.form("add_category_form"):
        cat_name = st.text_input("Category Name", placeholder="e.g., Subscriptions, Shopping")
        cat_type = st.selectbox("Category Type", options=["expense", "income", "travel"])
        
        if st.form_submit_button("Add Category", use_container_width=True):
            if cat_name.strip():
                if add_category(cat_name, cat_type):
                    st.success(f"✅ Added category: {cat_name}")
                    st.rerun()
                else:
                    st.error("❌ Category already exists or invalid")
            else:
                st.error("Please enter a category name")

# Right column: View and delete categories
with col2:
    st.write("**Existing Categories**")
    
    all_categories = get_all_categories()
    
    if all_categories:
        # Group by type
        df_cats = pd.DataFrame(all_categories)
        
        # Display by type
        for cat_type in ["expense", "income", "travel"]:
            type_cats = df_cats[df_cats['type'] == cat_type]['name'].tolist()
            
            if type_cats:
                st.write(f"*{cat_type.title()}:*")
                
                # Create columns for each category with delete button
                for cat_name in type_cats:
                    col_name, col_delete = st.columns([4, 1])
                    
                    with col_name:
                        st.write(f"• {cat_name}")
                    
                    with col_delete:
                        if st.button("🗑️", key=f"del_{cat_name}", help=f"Delete {cat_name}"):
                            if delete_category(cat_name):
                                st.success(f"Deleted {cat_name}")
                                st.rerun()
                            else:
                                st.error("Failed to delete")
                
                st.write("")  # Spacing
    else:
        st.info("No categories found")

st.markdown("---")

# Info box
st.info("""
💡 **Tips:**
- Expense categories are used for regular spending (groceries, utilities, etc.)
- Income categories track money coming in
- Travel categories are specifically for travel budget management
- Categories appear in dropdowns across the app
- Deleting a category won't affect existing transactions using that category
""")
