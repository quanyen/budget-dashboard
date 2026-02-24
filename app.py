import streamlit as st
import pandas as pd
import plotly.express as px
from io import StringIO
import datetime

# Page Config
st.set_page_config(page_title="Budget Insight", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: white; padding: 20px; border-radius: 15px; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True) # Fixed the parameter name here

# --- Utilities ---
def format_sgd(val):
    return f"S${val:,.2f}"

# --- CSV Processing Logic ---
def process_csv_data(uploaded_file):
    # Read text and handle CSV format
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    
    # We use pandas for more robust parsing compared to manual splitting
    # Based on the original logic: bank account, date, detail, credit, debit, category
    try:
        df = pd.read_csv(stringio, names=['Account', 'Date', 'Detail', 'Credit', 'Debit', 'Category'], header=0)
    except:
        st.error("Format error. Please ensure: Account, Date, Detail, Credit, Debit, Category")
        return None

    # Date Parsing (D-MMM-YY or similar)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    # Normalize Category
    df['Category'] = df['Category'].str.strip().str.title()
    
    # Handle Numeric Columns (Income/Expense)
    df['Income'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
    df['Expense'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
    
    # Sort and create helper columns
    df = df.sort_values('Date')
    df['MonthYear'] = df['Date'].dt.strftime('%b %Y')
    df['SortKey'] = df['Date'].dt.strftime('%Y-%m')
    
    return df

# --- Main UI ---
st.title("📊 Budget Insight")

uploaded_file = st.file_uploader("Upload your transaction CSV", type=['csv', 'txt'])

if uploaded_file:
    df = process_csv_data(uploaded_file)
    
    if df is not None:
        # --- Sidebar Filters ---
        st.sidebar.header("Filters")
        
        # Month Filter
        month_options = sorted(df['SortKey'].unique())
        selected_month_key = st.sidebar.selectbox("Select Month", ["All"] + month_options)
        
        # Account Filter
        account_options = sorted(df['Account'].unique())
        selected_account = st.sidebar.selectbox("Select Account", ["All"] + account_options)
        
        # Category Filter (Applying the "Exclusion" logic from your React code)
        unique_cats = sorted(df['Category'].unique())
        excluded_cats = ['Bank Transfer', 'Invest Transfer', 'Cc Payment', 'Cash Withdrawal']
        default_cats = [c for c in unique_cats if c not in excluded_cats]
        
        selected_categories = st.sidebar.multiselect("Select Categories", unique_cats, default=default_cats)

        # --- Data Filtering ---
        mask = df['Category'].isin(selected_categories)
        if selected_month_key != "All":
            mask &= (df['SortKey'] == selected_month_key)
        if selected_account != "All":
            mask &= (df['Account'] == selected_account)
            
        filtered_df = df[mask]

        # --- KPI Cards ---
        total_exp = filtered_df['Expense'].sum()
        total_inc = filtered_df['Income'].sum()
        net_flow = total_inc - total_exp

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Spending", format_sgd(total_exp), delta_color="inverse")
        col2.metric("Total Income", format_sgd(total_inc))
        col3.metric("Net Flow", format_sgd(net_flow), delta=net_flow)

        st.divider()

        # --- Charts ---
        # 1. Month-to-Month Trend (Always shows trend regardless of month filter)
        trend_df = df[df['Category'].isin(selected_categories)].groupby('MonthYear').agg({
            'Income': 'sum',
            'Expense': 'sum',
            'SortKey': 'first'
        }).sort_values('SortKey').reset_index()

        st.subheader("📅 Month-to-Month Trend")
        fig_trend = px.bar(trend_df, x='MonthYear', y=['Income', 'Expense'], 
                          barmode='group', 
                          color_discrete_map={'Income': '#34d399', 'Expense': '#f87171'})
        fig_trend.update_layout(xaxis_title="", yaxis_title="Amount", plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_trend, use_container_width=True)

        # 2. Category Breakdown
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("💳 Spend by Category")
            # Net spend calculation from your code: Expense - Income
            spend_df = filtered_df.groupby('Category').apply(lambda x: (x['Expense'] - x['Income']).sum()).reset_index(name='NetSpend')
            spend_df = spend_df[spend_df['NetSpend'] > 0].sort_values('NetSpend', ascending=True)
            
            if not spend_df.empty:
                fig_spend = px.bar(spend_df, x='NetSpend', y='Category', orientation='h',
                                  color_discrete_sequence=['#60a5fa'])
                st.plotly_chart(fig_spend, use_container_width=True)
            else:
                st.info("No spend data available")

        with chart_col2:
            st.subheader("📈 Income by Category")
            income_df = filtered_df.groupby('Category').apply(lambda x: (x['Income'] - x['Expense']).sum()).reset_index(name='NetInc')
            income_df = income_df[income_df['NetInc'] > 0].sort_values('NetInc', ascending=True)
            
            if not income_df.empty:
                fig_inc = px.bar(income_df, x='NetInc', y='Category', orientation='h',
                                color_discrete_sequence=['#34d399'])
                st.plotly_chart(fig_inc, use_container_width=True)
            else:
                st.info("No income data available")

        # --- Transactions Table ---
        st.subheader("📄 Recent Transactions")
        display_df = filtered_df[['Date', 'Account', 'Category', 'Detail', 'Income', 'Expense']].copy()
        display_df['Date'] = display_df['Date'].dt.strftime('%d-%b-%y')
        
        # Styling the table amounts
        st.dataframe(
            display_df.sort_values('Date', ascending=False),
            column_config={
                "Income": st.column_config.NumberColumn(format="S$%.2f"),
                "Expense": st.column_config.NumberColumn(format="S$%.2f"),
            },
            use_container_width=True,
            hide_index=True
        )

else:
    # Empty State
    st.info("Waiting for CSV upload. Expected format: Account, Date, Detail, Credit, Debit, Category")
