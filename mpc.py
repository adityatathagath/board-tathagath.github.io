import streamlit as st
import pandas as pd
import plotly.express as px

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Macro Risk Manager Dashboard",
    page_icon="📈"
)

# --- Data & Helper Functions ---

# MPC data with more detail for correlation analysis
MPC_DATA = pd.DataFrame([
    {'Date': '2025-06-06', 'Meeting': 'June 2025', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '4.5% (26)', 'GDP Forecast (FY)': '7.2% (26)'},
    {'Date': '2025-04-04', 'Meeting': 'April 2025', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '4.5% (26)', 'GDP Forecast (FY)': '7.0% (26)'},
    {'Date': '2025-02-07', 'Meeting': 'February 2025', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '4.5% (25)', 'GDP Forecast (FY)': '7.0% (25)'},
    {'Date': '2024-12-06', 'Meeting': 'December 2024', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '4.5% (25)', 'GDP Forecast (FY)': '7.0% (25)'},
    {'Date': '2024-10-09', 'Meeting': 'October 2024', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '4.5% (25)', 'GDP Forecast (FY)': '7.0% (25)'},
    {'Date': '2024-08-08', 'Meeting': 'August 2024', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '4.5% (25)', 'GDP Forecast (FY)': '7.0% (25)'},
    {'Date': '2024-06-07', 'Meeting': 'June 2024', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '4.5% (25)', 'GDP Forecast (FY)': '7.2% (25)'},
    {'Date': '2024-04-05', 'Meeting': 'April 2024', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '4.5% (25)', 'GDP Forecast (FY)': '7.0% (25)'},
    {'Date': '2024-02-08', 'Meeting': 'February 2024', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '5.4% (24)', 'GDP Forecast (FY)': '7.3% (24)'},
    {'Date': '2023-12-08', 'Meeting': 'December 2023', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '5.4% (24)', 'GDP Forecast (FY)': '7.0% (24)'},
    {'Date': '2023-10-06', 'Meeting': 'October 2023', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '5.4% (24)', 'GDP Forecast (FY)': '6.5% (24)'},
    {'Date': '2023-08-10', 'Meeting': 'August 2023', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '5.4% (24)', 'GDP Forecast (FY)': '6.5% (24)'},
    {'Date': '2023-06-08', 'Meeting': 'June 2023', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '5.1% (24)', 'GDP Forecast (FY)': '6.5% (24)'},
    {'Date': '2023-04-06', 'Meeting': 'April 2023', 'Repo Rate': '6.50% (Unchanged)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '5.2% (24)', 'GDP Forecast (FY)': '6.5% (24)'},
    {'Date': '2023-02-08', 'Meeting': 'February 2023', 'Repo Rate': '6.50% (+25bps)', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast (FY)': '6.5% (23)', 'GDP Forecast (FY)': '7.0% (23)'},
])
MPC_DATA['Date'] = pd.to_datetime(MPC_DATA['Date'])


@st.cache_data
def load_data(file):
    """Loads and preprocesses the data from the uploaded Excel file."""
    df = pd.read_excel(file, engine='openpyxl')
    df['Date'] = pd.to_datetime(df['Date'])
    return df

def format_k(value):
    """Formats a number into a string like '£64k' or '-£22k'."""
    if pd.isna(value):
        return "N/A"
    if value >= 0:
        return f"£{value:,.0f}k"
    else:
        return f"-£{-value:,.0f}k"

# --- Main Application UI ---

st.title("🛡️ Macro Market Risk Dashboard")
st.markdown("A strategic overview of portfolio risk exposures, inspired by a Macro Risk Manager's perspective.")

uploaded_file = st.file_uploader(
    "Upload the `consolidated_risk_timeseries.xlsx` file",
    type="xlsx"
)

if uploaded_file is None:
    st.info("Awaiting data file to begin analysis...")
    st.stop()

# Load the data
df = load_data(uploaded_file)
latest_date = df['Date'].max()
latest_df = df[(df['Date'] == latest_date) & (df['Metric'] == 'DV01')]

# --- Risk Manager's Summary View ---
st.subheader(f"Risk Manager's View: Key Exposures for {latest_date.strftime('%d-%b-%Y')}")

# Calculate key metrics for the summary
net_dv01 = latest_df[latest_df['Asset Class'] == 'NET']['Value'].sum()
gov_dv01 = latest_df[latest_df['Asset Class'] == 'GOV']['Value'].sum()
corp_dv01 = latest_df[latest_df['Asset Class'] == 'CORP']['Value'].sum()
ois_dv01 = latest_df[latest_df['Asset Class'] == 'OIS']['Value'].sum()

# Display key metrics in columns
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Net DV01 (Portfolio)", format_k(net_dv01), help="Overall sensitivity. Positive = bet on rates falling.")
with col2:
    st.metric("GOV DV01 (Rates Direction)", format_k(gov_dv01), help="Govt bond exposure. Negative = bet on yields rising.")
with col3:
    st.metric("CORP DV01 (Credit View)", format_k(corp_dv01), help="Corporate bond exposure. Positive = bullish on credit.")
with col4:
    st.metric("OIS DV01 (Policy Bet)", format_k(ois_dv01), help="Direct bet on the central bank's policy rate path.")

# --- Detailed Analysis Tabs ---
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Strategic Analysis", 
    "🔎 Risk Position Details", 
    "🏦 MPC Decisions", 
    "🗃️ Raw Data Explorer"
])

with tab1:
    st.header("Strategic Analysis Workbench")
    st.markdown("Use the filters to investigate key risk themes and validate trading theses against market events.")

    analysis_options = [
        "Track Conviction vs. Events (e.g., OIS - 2Y)",
        "Analyze Performance of Curve Trades (e.g., GOV - 10Y)",
        "Identify Changes in Strategy (e.g., NET DV01)",
        "Correlate Trading with MPC Commentary (e.g., CORP DV01)"
    ]
    selected_analysis = st.selectbox("Select an Analysis Scenario:", analysis_options)
    
    # Sidebar for deep dive filters
    st.sidebar.header("Analysis Filters")
    metrics = sorted(df['Metric'].unique())
    asset_classes = sorted(df['Asset Class'].unique())
    tenor_order = ['<=1Y', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y', '>=15Y']
    tenors = sorted(df['Tenor'].unique(), key=lambda x: tenor_order.index(x) if x in tenor_order else len(tenor_order))

    # Pre-configure filters based on selected analysis
    if selected_analysis == analysis_options[0]:
        st.sidebar.info("This view tracks the desk's conviction on a core policy bet (OIS 2Y) around MPC meetings.")
        sel_metric, sel_assets, sel_tenor = 'DV01', ['OIS'], '2Y'
    elif selected_analysis == analysis_options[1]:
        st.sidebar.info("This view isolates the long-end of a yield curve steepener trade to check its performance.")
        sel_metric, sel_assets, sel_tenor = 'DV01', ['GOV'], '10Y'
    elif selected_analysis == analysis_options[2]:
        st.sidebar.info("This view shows the overall portfolio direction. Look for major shifts in the trend.")
        sel_metric, sel_assets, sel_tenor = 'DV01', ['NET'], 'Total' # Assuming 'Total' tenor exists
        if 'Total' not in tenors:
             # Fallback if 'Total' is not a tenor, though it should be calculated
             total_df = df.groupby(['Date', 'Metric', 'Asset Class'])['Value'].sum().reset_index()
             total_df['Tenor'] = 'Total'
             df = pd.concat([df, total_df], ignore_index=True)
             tenors.append('Total')
    else: # Correlate Trading
        st.sidebar.info("Look for jumps in credit risk (CORP) and see if they align with positive GDP forecasts from the MPC.")
        sel_metric, sel_assets, sel_tenor = 'DV01', ['CORP'], '5Y'


    selected_metric = st.sidebar.selectbox("Metric", metrics, index=metrics.index(sel_metric))
    selected_asset_classes = st.sidebar.multiselect("Asset Classes", asset_classes, default=sel_assets)
    selected_tenor = st.sidebar.selectbox("Tenor", tenors, index=tenors.index(sel_tenor))

    # Filter data for the chart
    chart_df = df[
        (df['Metric'] == selected_metric) &
        (df['Asset Class'].isin(selected_asset_classes)) &
        (df['Tenor'] == selected_tenor)
    ]

    if chart_df.empty:
        st.warning("No data available for the selected filter combination.")
    else:
        fig = px.line(
            chart_df, x='Date', y='Value', color='Asset Class',
            title=f"{selected_metric}: {', '.join(selected_asset_classes)} ({selected_tenor})",
            labels={'Value': f'{selected_metric} Value (£k)', 'Date': 'Date'},
            template='plotly_dark'
        )
        for _, row in MPC_DATA.iterrows():
            fig.add_vline(x=row['Date'], line_width=1, line_dash="dash", line_color="orange", annotation_text=row['Meeting'], annotation_position="top left")
        
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header(f"Risk Position Details for {latest_date.strftime('%d-%b-%Y')}")
    
    latest_pivot = latest_df.pivot_table(
        index='Tenor', columns='Asset Class', values='Value'
    ).reindex(tenor_order).fillna(0)
    
    st.dataframe(latest_pivot.style.format("{:,.0f}").background_gradient(cmap='RdYlGn', axis=None))
    
    with st.expander("How to Interpret This Table"):
        st.markdown("""
        This table shows the **DV01** for the latest day, broken down by asset class and maturity.
        - **Positive (Green):** Profits if interest rates fall.
        - **Negative (Red):** Profits if interest rates rise.
        - **GOV Column:** A mix of positive and negative values suggests a **yield curve trade**.
        """)

with tab3:
    st.header("Key RBI MPC Decisions")
    st.markdown("Use this table to correlate trading activity with specific central bank commentary.")
    st.dataframe(MPC_DATA.set_index('Meeting'))

with tab4:
    st.header("Raw Data Explorer")
    st.markdown("The complete, consolidated time-series dataset.")
    st.dataframe(df)

# Sidebar footer
st.sidebar.markdown("---")
st.sidebar.info("Dashboard developed for strategic risk analysis.")
