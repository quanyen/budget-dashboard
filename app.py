import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION & MINIMALIST PASTEL CSS
# ==========================================
st.set_page_config(page_title="My Budget", page_icon="🌸", layout="centered")

st.markdown("""
    <style>
    /* Hide default Streamlit elements for a cleaner mobile app feel */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Top padding adjustment for mobile */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* Pastel Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #FAFAFA;
        border: 1px solid #F0F0F0;
        padding: 15px;
        border-radius: 16px;
        box-shadow: 0px 2px 10px rgba(0,0,0,0.02);
    }
    
    /* Global Font Tweak for Minimalism */
    * {
        font-family: 'Helvetica Neue', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# Pastel color palette for charts
PASTEL_COLORS = ['#FFB3BA', '#BAE1FF', '#BAFFC9', '#FFDFBA', '#E2CBF7', '#FFFFBA', '#FADADD', '#D4F0F0', '#FFC4C4']


# ==========================================
# DATA PROCESSING FUNCTION
# ==========================================
@st.cache_data
def parse_budget_file(file):
    """
    Robustly parses the text file, handling extra commas in the detail section.
    Format expected: bank, date, [details...], credit, debit, category
    """
    lines = file.getvalue().decode("utf-8").splitlines()
    data = []
    
    for line in lines:
        if not line.strip(): continue
        parts = line.split(',')
        
        # Ensure we have at least the 6 basic columns
        if len(parts) >= 6:
            bank = parts[0].strip()
            date_str = parts[1].strip()
            category = parts[-1].strip()
            
            try:
                # The last two items before category are debit and credit
                debit = float(parts[-2].strip() or 0)
                credit = float(parts[-3].strip() or 0)
            except ValueError:
                continue # Skip invalid numerical rows
                
            # Rejoin anything in the middle as the transaction detail
            detail = ', '.join(parts[2:-3]).strip()
            # Clean up empty commas from the sample format (e.g., ",buy toto")
            if detail.startswith(','): detail = detail[1:].strip()
                
            data.append([bank, date_str, detail, credit, debit, category])
            
    df = pd.DataFrame(data, columns=['Account', 'Date', 'Detail', 'Spend (Credit)', 'Income (Debit)', 'Category'])
    
    # Parse dates
    df['Date'] = pd.to_datetime(df['Date'], format='%d %b %Y', errors='coerce')
    df = df.dropna(subset=['Date'])
    df['Month_Year'] = df['Date'].dt.strftime('%b %Y')
    df['Month_Order'] = df['Date'].dt.to_period('M') # For sorting
    
    return df


# ==========================================
# APP UI & DASHBOARD
# ==========================================
st.title("🌸 Monthly Budget")
st.write("Upload your transaction text file to view your spending.")

uploaded_file = st.file_uploader("Choose a text file (.txt or .csv)", type=["txt", "csv"])

if uploaded_file is not None:
    # Load Data
    df = parse_budget_file(uploaded_file)
    
    if df.empty:
        st.error("No valid data found. Please check your file format.")
    else:
        # --- FILTERS ---
        # Sort months chronologically
        months = sorted(df['Month_Order'].unique())
        month_labels = [m.strftime('%b %Y') for m in months]
        month_labels.insert(0, "All Time")
        
        selected_month = st.selectbox("Select Month", month_labels)
        
        # Filter dataframe
        if selected_month != "All Time":
            filtered_df = df[df['Month_Year'] == selected_month]
        else:
            filtered_df = df
            
        # --- METRICS ---
        total_spend = filtered_df['Spend (Credit)'].sum()
        total_income = filtered_df['Income (Debit)'].sum()
        net_spend = total_spend - total_income
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Spend", f"${total_spend:,.2f}")
        with col2:
            st.metric("Income/Refunds", f"${total_income:,.2f}")
        with col3:
            st.metric("Net Spend", f"${net_spend:,.2f}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- CHARTS ---
        # 1. Donut Chart: Spending by Category
        st.subheader("Spending by Category")
        spend_by_cat = filtered_df[filtered_df['Spend (Credit)'] > 0].groupby('Category')['Spend (Credit)'].sum().reset_index()
        
        if not spend_by_cat.empty:
            fig_pie = px.pie(
                spend_by_cat, 
                values='Spend (Credit)', 
                names='Category', 
                hole=0.5,
                color_discrete_sequence=PASTEL_COLORS
            )
            fig_pie.update_traces(textinfo='percent+label', textposition='inside', showlegend=False)
            fig_pie.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No spending data to display for this period.")

        # 2. Bar Chart: Daily Spending Trend
        st.subheader("Daily Spend Trend")
        daily_spend = filtered_df.groupby('Date')['Spend (Credit)'].sum().reset_index()
        
        if not daily_spend.empty:
            fig_bar = px.bar(
                daily_spend, 
                x='Date', 
                y='Spend (Credit)',
                color_discrete_sequence=['#BAE1FF']
            )
            fig_bar.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                xaxis_title="",
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#F0F0F0")
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        # --- TRANSACTIONS TABLE ---
        st.subheader("Recent Transactions")
        display_cols = ['Date', 'Account', 'Detail', 'Spend (Credit)', 'Income (Debit)', 'Category']
        display_df = filtered_df[display_cols].sort_values(by='Date', ascending=False)
        
        # Format dates back to string for clean display
        display_df['Date'] = display_df['Date'].dt.strftime('%d %b %Y')
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
