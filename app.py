import streamlit as st
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(page_title="Personal Finance Dashboard", page_icon="💸", layout="wide")

def load_and_clean_data(uploaded_file):
    """Reads the uploaded file and formats the columns appropriately."""
    # Define the expected columns based on the user's sample data
    col_names = ["Account", "Date", "Description", "Expense", "Income", "Category"]
    
    # Read CSV without a header
    df = pd.read_csv(uploaded_file, header=None, names=col_names)
    
    # Clean up any trailing/leading whitespaces in string columns
    string_cols = ["Account", "Description", "Category"]
    for col in string_cols:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
            
    # Convert dates to datetime objects
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Ensure numerical columns are correctly typed
    df['Expense'] = pd.to_numeric(df['Expense'], errors='coerce').fillna(0)
    df['Income'] = pd.to_numeric(df['Income'], errors='coerce').fillna(0)
    
    # Sort chronologically
    df = df.sort_values('Date')
    
    return df

# Main Title
st.title("💸 Monthly Spending Dashboard")
st.markdown("Upload your text/csv file to visualize your spending habits, filter by categories, and track your finances.")

# Sidebar - File Upload and Filters
st.sidebar.header("1. Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload your spending data (.txt or .csv)", type=["txt", "csv"])

if uploaded_file is not None:
    try:
        # Load the data
        raw_df = load_and_clean_data(uploaded_file)
        
        # --- FILTERS ---
        st.sidebar.header("2. Filters")
        
        # Date Filter
        min_date = raw_df['Date'].min().date()
        max_date = raw_df['Date'].max().date()
        
        if min_date == max_date:
            st.sidebar.info(f"Data is only for one day: {min_date}")
            start_date, end_date = min_date, max_date
        else:
            date_range = st.sidebar.date_input("Select Date Range", (min_date, max_date), min_value=min_date, max_value=max_date)
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = min_date, max_date

        # Category Filter (Useful to exclude massive outliers like "Invest Transfer")
        all_categories = raw_df['Category'].unique().tolist()
        selected_categories = st.sidebar.multiselect(
            "Select Categories to Include",
            options=all_categories,
            default=all_categories
        )
        
        # Account Filter
        all_accounts = raw_df['Account'].unique().tolist()
        selected_accounts = st.sidebar.multiselect(
            "Select Accounts",
            options=all_accounts,
            default=all_accounts
        )

        # Apply Filters
        mask = (
            (raw_df['Date'].dt.date >= start_date) & 
            (raw_df['Date'].dt.date <= end_date) &
            (raw_df['Category'].isin(selected_categories)) &
            (raw_df['Account'].isin(selected_accounts))
        )
        filtered_df = raw_df[mask]

        # --- KPI METRICS ---
        st.subheader("At a Glance")
        kpi1, kpi2, kpi3 = st.columns(3)
        
        total_expense = filtered_df['Expense'].sum()
        total_income = filtered_df['Income'].sum()
        net_flow = total_income - total_expense
        
        kpi1.metric(label="Total Expenses 📉", value=f"${total_expense:,.2f}")
        kpi2.metric(label="Total Income 📈", value=f"${total_income:,.2f}")
        kpi3.metric(label="Net Flow ⚖️", value=f"${net_flow:,.2f}", delta=float(net_flow))

        st.divider()

        # --- CHARTS ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Expenses by Category")
            if total_expense > 0:
                # Group by category and sum expenses
                cat_expense = filtered_df[filtered_df['Expense'] > 0].groupby('Category')['Expense'].sum().reset_index()
                pastel_colors = ['#fca5a5', '#fdba74', '#fde047', '#86efac', '#93c5fd', '#c4b5fd', '#f9a8d4']
                fig_pie = px.pie(cat_expense, values='Expense', names='Category', hole=0.4, 
                                 color_discrete_sequence=pastel_colors)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No expenses found for the selected filters.")

        with col2:
            st.subheader("Daily Spending Trend")
            # Group by date
            daily_expense = filtered_df.groupby('Date')['Expense'].sum().reset_index()
            if not daily_expense.empty and daily_expense['Expense'].sum() > 0:
                fig_line = px.bar(daily_expense, x='Date', y='Expense', 
                                  labels={'Expense': 'Amount Spent ($)'},
                                  color_discrete_sequence=['#93c5fd'])
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("No expense trends available for the selected filters.")

        st.divider()

        col3, col4 = st.columns([1, 2])
        
        with col3:
            st.subheader("Spending by Account")
            acc_expense = filtered_df[filtered_df['Expense'] > 0].groupby('Account')['Expense'].sum().reset_index()
            if not acc_expense.empty:
                acc_colors = ['#c4b5fd', '#6ee7b7', '#fcd34d', '#fca5a5', '#93c5fd']
                fig_bar = px.bar(acc_expense, x='Account', y='Expense', color='Account',
                                 labels={'Expense': 'Total Spent ($)'},
                                 color_discrete_sequence=acc_colors)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No data to show.")

        with col4:
            st.subheader("Detailed Transactions")
            # Format dataframe for display
            display_df = filtered_df.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%d %b %Y')
            display_df['Expense'] = display_df['Expense'].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")
            display_df['Income'] = display_df['Income'].apply(lambda x: f"${x:,.2f}" if x > 0 else "-")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        st.info("Please ensure your uploaded file matches the expected comma-separated format: Account, Date, Description, Expense, Income, Category.")

else:
    st.info("👈 Please upload your spending data file in the sidebar to get started.")
    
    st.markdown("### Expected File Format (No Headers Required)")
    st.code("""
bank account,date, transaction detail, credit, debit ,spend category
    """, language="text")
