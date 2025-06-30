import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

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

def create_timeseries_chart(df, title, selected_tenors):
    """Creates a Plotly line chart using the robust marker method for MPC dates."""
    fig = go.Figure()
    
    plot_df = df[df['Tenor'].isin(selected_tenors)]
    
    for tenor in selected_tenors:
        tenor_df = plot_df[plot_df['Tenor'] == tenor]
        fig.add_trace(go.Scatter(x=tenor_df['Date'], y=tenor_df['Value'], mode='lines', name=tenor))

    y_pos = plot_df['Value'].max() * 1.05 if not plot_df.empty else 1
    fig.add_trace(go.Scatter(
        x=MPC_DATA['Date'], y=[y_pos] * len(MPC_DATA), mode='markers',
        marker=dict(symbol='diamond-tall', color=ACCENT_ORANGE, size=10),
        name='MPC Meeting', hovertext=MPC_DATA['Meeting'], hoverinfo='text'
    ))

    fig.update_layout(
        title_text=title, template='plotly_white',
        xaxis_title='Date', yaxis_title='DV01 Value (£k)',
        legend_title_text='Tenor', paper_bgcolor=CHART_BG_COLOR, plot_bgcolor=CHART_BG_COLOR,
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
available_tenors = [t for t in tenor_order if t in df_dv01['Tenor'].unique()]

# --- Sidebar and Main Page Filters ---
st.sidebar.header("View Options")
comparison_mode = st.sidebar.toggle("Show Day-on-Day Comparison", value=False)

# --- Main Dashboard Layout ---
if not comparison_mode:
    st.header("Time Series Analysis: DV01 Risk Profile")
    
    selected_tenors = st.multiselect(
        "Select Tenors to Display:",
        options=available_tenors,
        default=available_tenors[:3]
    )

    if not selected_tenors:
        st.warning("Please select at least one tenor to display the charts.")
        st.stop()

    st.subheader("Portfolio Net Exposure (NET)")
    net_df = df_dv01[df_dv01['Asset Class'] == 'NET']
    if not net_df.empty:
        fig_net = create_timeseries_chart(net_df, "NET DV01 Across Selected Tenors", selected_tenors)
        st.plotly_chart(fig_net, use_container_width=True)
    else:
        st.warning("No data found for Asset Class 'NET'.")

    st.markdown("---")
    st.subheader("Asset Class Deep Dive")
    other_assets = sorted([a for a in df_dv01['Asset Class'].unique() if a != 'NET'])
    
    for asset in other_assets:
        asset_df = df_dv01[df_dv01['Asset Class'] == asset]
        if not asset_df.empty:
            fig_asset = create_timeseries_chart(asset_df, f"{asset} DV01 Across Selected Tenors", selected_tenors)
            st.plotly_chart(fig_asset, use_container_width=True)

else: # Day-on-Day Comparison View
    unique_dates = sorted(df_dv01['Date'].unique(), reverse=True)
    if len(unique_dates) < 2:
        st.error("Cannot perform comparison. The dataset contains data for only one day.")
        st.stop()
    
    with st.expander("Show MPC Meeting Dates for Reference"):
        st.dataframe(MPC_DATA[['Date', 'Meeting']].rename(columns={'Date': 'MPC Date'}).set_index('Meeting'))

    col1, col2 = st.columns(2)
    with col1:
        date_1 = st.selectbox("Select First Date:", options=unique_dates, format_func=lambda d: pd.to_datetime(d).strftime('%d-%b-%Y'), index=1)
    with col2:
        date_2 = st.selectbox("Select Second Date:", options=unique_dates, format_func=lambda d: pd.to_datetime(d).strftime('%d-%b-%Y'), index=0)
    
    if date_1 == date_2:
        st.warning("Please select two different dates for a meaningful comparison.")
        st.stop()
        
    st.header(f"Day-on-Day Comparison: {pd.to_datetime(date_1).strftime('%d-%b-%Y')} vs {pd.to_datetime(date_2).strftime('%d-%b-%Y')}")
    
    comparison_df = df_dv01[df_dv01['Date'].isin([date_1, date_2])].copy()
    comparison_df = comparison_df[comparison_df['Tenor'] != 'Total']
    
    all_assets = sorted(comparison_df['Asset Class'].unique())
    
    for asset in all_assets:
        st.subheader(f"{asset} DV01 Comparison")
        asset_comp_df = comparison_df[comparison_df['Asset Class'] == asset]
        
        if not asset_comp_df.empty:
            pivot_df = asset_comp_df.pivot_table(index='Tenor', columns='Date', values='Value').reset_index()
            date1_col_name = f"Value on {pd.to_datetime(date_1).strftime('%d-%b')}"
            date2_col_name = f"Value on {pd.to_datetime(date_2).strftime('%d-%b')}"
            pivot_df = pivot_df.rename(columns={pd.to_datetime(date_1): date1_col_name, pd.to_datetime(date_2): date2_col_name})
            pivot_df = pivot_df.fillna(0)

            pivot_df['Change'] = pivot_df[date2_col_name] - pivot_df[date1_col_name]

            pivot_df['Tenor'] = pd.Categorical(pivot_df['Tenor'], categories=tenor_order, ordered=True)
            pivot_df = pivot_df.sort_values('Tenor')

            # Bar chart of the absolute change
            fig_change = px.bar(
                pivot_df, x='Tenor', y='Change', title=f"Change in DV01 for {asset}",
                labels={'Change': 'Change in DV01 (£k)'}, color='Change', color_continuous_scale='RdBu'
            )
            fig_change.update_layout(
                template='plotly_white', paper_bgcolor=CHART_BG_COLOR, plot_bgcolor=CHART_BG_COLOR,
                font=dict(color=TEXT_COLOR)
            )
            st.plotly_chart(fig_change, use_container_width=True)

            # --- Simplified and Safe Dataframe Display ---
            with st.expander("Show/Hide Detailed Data"):
                display_df = pivot_df.rename(columns={
                    date1_col_name: f"Value on {pd.to_datetime(date_1).strftime('%d-%b')}",
                    date2_col_name: f"Value on {pd.to_datetime(date_2).strftime('%d-%b')}",
                    'Change': "Change (£k)"
                })
                
                # Use a simple st.dataframe without complex styling to avoid recursion
                st.dataframe(
                    display_df.set_index('Tenor'),
                    use_container_width=True
                )
            st.markdown("---")
