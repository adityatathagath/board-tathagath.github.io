import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Macro Risk Manager Dashboard",
    page_icon="📈"
)

# --- Verified RBI MPC Data (User Provided) ---
MPC_DATA = pd.DataFrame([
    # 2023 — 6 Meetings
    {'Date': '2023-02-08', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '6.5% (FY23)', 'GDP Forecast': '7.2% (FY23)', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2023-04-06', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '5.7% (FY23)', 'GDP Forecast': '7.2% (FY23)', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2023-06-08', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '5.7% (FY23)', 'GDP Forecast': '7.2% (FY23)', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2023-08-10', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '—', 'GDP Forecast': '—', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2023-10-06', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '—', 'GDP Forecast': '—', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2023-12-08', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '—', 'GDP Forecast': '—', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},

    # 2024 — 6 Meetings
    {'Date': '2024-02-08', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '—', 'GDP Forecast': '—', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2024-04-05', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '—', 'GDP Forecast': '—', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2024-06-07', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '4.5% (FY25)', 'GDP Forecast': '7.2% (FY25)', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2024-08-08', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '4.5% (FY25)', 'GDP Forecast': '7.2% (FY25)', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2024-10-09', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '4.5% (FY25)', 'GDP Forecast': '7.2% (FY25)', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},
    {'Date': '2024-12-06', 'Repo Rate': '6.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Withdrawal of accommodation', 'CPI Forecast': '4.5% (FY25)', 'GDP Forecast': '7.0% (FY25)', 'MSF Rate': '6.75%', 'SDF Rate': '6.25%', 'Bank Rate': '6.75%'},

    # 2025 — 3 Meetings till June
    {'Date': '2025-02-07', 'Repo Rate': '6.25%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Neutral', 'CPI Forecast': '4.2% (FY26)', 'GDP Forecast': '6.7% (FY26)', 'MSF Rate': '6.50%', 'SDF Rate': '6.00%', 'Bank Rate': '6.50%'},
    {'Date': '2025-04-09', 'Repo Rate': '6.00%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Accommodative', 'CPI Forecast': '—', 'GDP Forecast': '6.5% (FY26)', 'MSF Rate': '6.25%', 'SDF Rate': '5.75%', 'Bank Rate': '6.25%'},
    {'Date': '2025-06-06', 'Repo Rate': '5.50%', 'Reverse Repo Rate': '3.35%', 'Stance': 'Neutral', 'CPI Forecast': '3.7% (FY26)', 'GDP Forecast': '6.5% (FY26)', 'MSF Rate': '5.75%', 'SDF Rate': '5.25%', 'Bank Rate': '5.75%'}
])
MPC_DATA['Date'] = pd.to_datetime(MPC_DATA['Date'])
MPC_DATA['Meeting'] = MPC_DATA['Date'].dt.strftime('%B %Y')


# --- Barclays Theming ---
BARCLAYS_DARK_BLUE = "#002A5D"
BARCLAYS_LIGHT_BLUE = "#00AEEF"
BACKGROUND_COLOR = "#0E1117"
TEXT_COLOR = "#FAFAFA"
st.markdown(f"""<style>
    .reportview-container, .main {{ background-color: {BACKGROUND_COLOR}; }}
    .sidebar .sidebar-content {{ background-color: {BARCLAYS_DARK_BLUE}; }}
    h1, h2, h3 {{ color: {BARCLAYS_LIGHT_BLUE}; }}
    .stMetric {{ background-color: #262730; border-radius: 0.5rem; padding: 1rem; }}
    .stMetric > label {{ color: {BARCLAYS_LIGHT_BLUE}; }}
</style>""", unsafe_allow_html=True)


# --- Helper Functions ---
@st.cache_data
def load_data(file):
    df = pd.read_excel(file, engine='openpyxl')
    df['Date'] = pd.to_datetime(df['Date'])
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0)
    return df

@st.cache_data
def get_data_with_totals(_df):
    total_df = _df.groupby(['Date', 'Metric', 'Asset Class'])['Value'].sum().reset_index()
    total_df['Tenor'] = 'Total'
    return pd.concat([_df, total_df], ignore_index=True)

def format_k(value):
    if pd.isna(value): return "N/A"
    return f"£{value:,.0f}k" if value >= 0 else f"-£{-value:,.0f}k"

# --- Main Application UI ---
st.title("Macro Risk Manager Dashboard")
st.markdown(f"##### A strategic overview of portfolio risk, themed for <span style='color:{BARCLAYS_LIGHT_BLUE};'>professional analysis</span>.", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload `consolidated_risk_timeseries.xlsx`", type="xlsx")

if uploaded_file is None:
    st.info("Awaiting data file to begin analysis...")
    st.stop()

df_base = load_data(uploaded_file)
df = get_data_with_totals(df_base)
latest_date = df['Date'].max()
latest_df = df[(df['Date'] == latest_date) & (df['Metric'] == 'DV01')]

# --- Risk Manager's Summary View ---
st.subheader(f"Key Exposures: {latest_date.strftime('%d-%b-%Y')}")
latest_positions = latest_df[latest_df['Tenor'] != 'Total']
gov_dv01 = latest_positions[latest_positions['Asset Class'] == 'GOV']['Value'].sum()
corp_dv01 = latest_positions[latest_positions['Asset Class'] == 'CORP']['Value'].sum()
ois_dv01 = latest_positions[latest_positions['Asset Class'] == 'OIS']['Value'].sum()
net_dv01 = latest_positions[latest_positions['Asset Class'] == 'NET']['Value'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Net DV01 (Portfolio)", format_k(net_dv01), help="Overall sensitivity. Positive = bet on rates falling.")
col2.metric("GOV DV01 (Rates Direction)", format_k(gov_dv01), help="Govt bond exposure. Negative = bet on yields rising.")
col3.metric("CORP DV01 (Credit View)", format_k(corp_dv01), help="Corporate bond exposure. Positive = bullish on credit.")
col4.metric("OIS DV01 (Policy Bet)", format_k(ois_dv01), help="Direct bet on the central bank's policy rate path.")

# --- Detailed Analysis Tabs ---
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Strategic Analysis", "🔎 Risk Position Details", "🏦 MPC Decisions", "🗃️ Raw Data Explorer"])

with tab1:
    st.header("Strategic Analysis Workbench")
    st.markdown("Use the filters to investigate key risk themes and validate trading theses against market events.")
    analysis_options = ["Track Conviction vs. Events (e.g., OIS - 2Y)", "Analyze Performance of Curve Trades (e.g., GOV - 10Y)", "Identify Changes in Strategy (e.g., NET DV01)", "Correlate Trading with MPC Commentary (e.g., CORP DV01)"]
    selected_analysis = st.selectbox("Select an Analysis Scenario:", analysis_options)
    
    st.sidebar.header("Analysis Filters")
    metrics = sorted(df['Metric'].unique())
    asset_classes = sorted(df['Asset Class'].unique())
    tenor_order = ['<=1Y', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y', '>=15Y', 'Total']
    tenors = sorted(df['Tenor'].unique(), key=lambda x: tenor_order.index(x) if x in tenor_order else len(tenor_order))

    if selected_analysis == analysis_options[0]: sel_metric, sel_assets, sel_tenor = 'DV01', ['OIS'], '2Y'
    elif selected_analysis == analysis_options[1]: sel_metric, sel_assets, sel_tenor = 'DV01', ['GOV'], '10Y'
    elif selected_analysis == analysis_options[2]: sel_metric, sel_assets, sel_tenor = 'DV01', ['NET'], 'Total'
    else: sel_metric, sel_assets, sel_tenor = 'DV01', ['CORP'], '5Y'

    selected_metric = st.sidebar.selectbox("Metric", metrics, index=metrics.index(sel_metric))
    selected_asset_classes = st.sidebar.multiselect("Asset Classes", asset_classes, default=sel_assets)
    selected_tenor = st.sidebar.selectbox("Tenor", tenors, index=tenors.index(sel_tenor))

    chart_df = df[(df['Metric'] == selected_metric) & (df['Asset Class'].isin(selected_asset_classes)) & (df['Tenor'] == selected_tenor)]

    if chart_df.empty:
        st.warning("No data available for the selected filter combination.")
    else:
        fig = go.Figure()
        for asset in selected_asset_classes:
            asset_df = chart_df[chart_df['Asset Class'] == asset]
            fig.add_trace(go.Scatter(x=asset_df['Date'], y=asset_df['Value'], mode='lines+markers', name=asset))

        y_pos = chart_df['Value'].max() * 1.05 if not chart_df.empty else 1
        fig.add_trace(go.Scatter(
            x=MPC_DATA['Date'], y=[y_pos] * len(MPC_DATA), mode='markers',
            marker=dict(symbol='diamond-tall', color=BARCLAYS_LIGHT_BLUE, size=10, line=dict(width=1, color=TEXT_COLOR)),
            name='MPC Meeting', hovertext=MPC_DATA['Meeting'], hoverinfo='text'
        ))

        fig.update_layout(
            title_text=f"{selected_metric}: {', '.join(selected_asset_classes)} ({selected_tenor})",
            template='plotly_dark', xaxis_title='Date', yaxis_title=f'{selected_metric} Value (£k)',
            legend_title_text='Asset Class', paper_bgcolor=BACKGROUND_COLOR, plot_bgcolor="#262730",
            font=dict(color=TEXT_COLOR)
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header(f"Risk Position Details: {latest_date.strftime('%d-%b-%Y')}")
    latest_pivot = latest_df[latest_df.Tenor != 'Total'].pivot_table(index='Tenor', columns='Asset Class', values='Value').reindex(tenor_order[:-1]).fillna(0)
    st.dataframe(latest_pivot.style.format("{:,.0f}").background_gradient(cmap='RdYlGn', axis=None))

with tab3:
    st.header("Verified RBI MPC Decisions")
    st.markdown("Official data from RBI press releases. Use this table to correlate trading activity with specific central bank commentary.")
    st.dataframe(MPC_DATA.set_index('Meeting'))

with tab4:
    st.header("Raw Data Explorer")
    st.dataframe(df)

st.sidebar.markdown("---")
st.sidebar.info("Dashboard developed for strategic risk analysis.")
