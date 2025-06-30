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

# --- Professional Theming & Colors ---
PRIMARY_BLUE = "#003B6D"
ACCENT_BLUE = "#00AEEF"
ACCENT_ORANGE = "#D4691E"
BACKGROUND_COLOR = "#FFFFFF"
CHART_BG_COLOR = "#F5F5F5"
TEXT_COLOR = "#1C1C1C"
GRID_COLOR = "#E0E0E0"

st.markdown(f"""
<style>
    .reportview-container, .main {{
        background-color: {BACKGROUND_COLOR};
        color: {TEXT_COLOR};
    }}
    .st-emotion-cache-16txtl3 {{
        padding-top: 2rem;
    }}
    h1, h2, h3 {{
        color: {PRIMARY_BLUE};
    }}
    .stMetric {{
        background-color: {CHART_BG_COLOR};
        border: 1px solid {GRID_COLOR};
        border-radius: 0.5rem;
        padding: 1rem;
    }}
    .stMetric > label {{
        color: {PRIMARY_BLUE};
        font-weight: bold;
    }}
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
@st.cache_data
def load_data(file):
    df = pd.read_excel(file, engine='openpyxl')
    df['Date'] = pd.to_datetime(df['Date'])
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce').fillna(0)
    return df

def create_timeseries_chart(df, title):
    """Creates a Plotly line chart for a given dataframe."""
    fig = go.Figure()
    tenors = sorted(df['Tenor'].unique(), key=lambda x: tenor_order.index(x) if x in tenor_order else len(tenor_order))
    for tenor in tenors:
        tenor_df = df[df['Tenor'] == tenor]
        fig.add_trace(go.Scatter(x=tenor_df['Date'], y=tenor_df['Value'], mode='lines', name=tenor))

    for _, row in MPC_DATA.iterrows():
        fig.add_vline(x=row['Date'], line_width=1, line_dash="dash", line_color=ACCENT_ORANGE)

    fig.update_layout(
        title_text=title, template='plotly_white',
        xaxis_title='Date', yaxis_title='DV01 Value (£k)',
        legend_title_text='Tenor', paper_bgcolor=CHART_BG_COLOR, plot_bgcolor=CHART_BG_COLOR,
        font=dict(color=TEXT_COLOR), xaxis=dict(gridcolor=GRID_COLOR), yaxis=dict(gridcolor=GRID_COLOR)
    )
    return fig

def create_comparison_barchart(df, title):
    """Creates a Plotly grouped bar chart for day-on-day comparison."""
    df['Date'] = df['Date'].dt.strftime('%d-%b-%Y')
    fig = px.bar(
        df, x='Tenor', y='Value', color='Date', barmode='group',
        title=title, labels={'Value': 'DV01 Value (£k)'},
        color_discrete_map={df['Date'].unique()[0]: PRIMARY_BLUE, df['Date'].unique()[1]: ACCENT_BLUE}
    )
    fig.update_layout(
        template='plotly_white', paper_bgcolor=CHART_BG_COLOR, plot_bgcolor=CHART_BG_COLOR,
        font=dict(color=TEXT_COLOR), xaxis=dict(gridcolor=GRID_COLOR), yaxis=dict(gridcolor=GRID_COLOR)
    )
    return fig

# --- Main Application UI ---
st.title("Macro Risk Manager Dashboard")

uploaded_file = st.file_uploader("Upload `consolidated_risk_timeseries.xlsx`", type="xlsx")

if uploaded_file is None:
    st.info("Awaiting data file to begin analysis...")
    st.stop()

df_full = load_data(uploaded_file)
df_dv01 = df_full[df_full['Metric'] == 'DV01'].copy()
tenor_order = ['<=1Y', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y', '>=15Y']

# --- Sidebar for View Control ---
st.sidebar.header("View Options")
comparison_mode = st.sidebar.toggle("Show Day-on-Day Comparison", value=False)

# --- Main Dashboard Layout ---
if not comparison_mode:
    st.header("Time Series Analysis: DV01 Risk Profile")
    
    # --- NET Risk Chart ---
    st.subheader("Portfolio Net Exposure (NET)")
    net_df = df_dv01[df_dv01['Asset Class'] == 'NET']
    if not net_df.empty:
        fig_net = create_timeseries_chart(net_df, "NET DV01 Across All Tenors")
        st.plotly_chart(fig_net, use_container_width=True)
    else:
        st.warning("No data found for Asset Class 'NET'.")

    # --- Other Asset Class Charts ---
    st.markdown("---")
    st.subheader("Asset Class Deep Dive")
    other_assets = sorted([a for a in df_dv01['Asset Class'].unique() if a != 'NET'])
    
    for asset in other_assets:
        asset_df = df_dv01[df_dv01['Asset Class'] == asset]
        if not asset_df.empty:
            fig_asset = create_timeseries_chart(asset_df, f"{asset} DV01 Across All Tenors")
            st.plotly_chart(fig_asset, use_container_width=True)

else: # Day-on-Day Comparison View
    unique_dates = sorted(df_dv01['Date'].unique(), reverse=True)
    if len(unique_dates) < 2:
        st.error("Cannot perform comparison. The dataset contains data for only one day.")
        st.stop()
    
    latest_date = unique_dates[0]
    previous_date = unique_dates[1]
    
    st.header(f"Day-on-Day Comparison: {previous_date.strftime('%d-%b-%Y')} vs {latest_date.strftime('%d-%b-%Y')}")
    
    comparison_df = df_dv01[df_dv01['Date'].isin([latest_date, previous_date])].copy()
    comparison_df = comparison_df[comparison_df['Tenor'] != 'Total']
    
    all_assets = sorted(comparison_df['Asset Class'].unique())
    
    for asset in all_assets:
        asset_comp_df = comparison_df[comparison_df['Asset Class'] == asset]
        asset_comp_df = asset_comp_df.sort_values(by='Tenor', key=lambda x: x.map({t: i for i, t in enumerate(tenor_order)}))
        if not asset_comp_df.empty:
            fig_comp = create_comparison_barchart(asset_comp_df, f"{asset} DV01 Comparison")
            st.plotly_chart(fig_comp, use_container_width=True)
