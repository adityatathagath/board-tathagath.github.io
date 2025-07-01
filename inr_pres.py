import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Load data from Excel file ---
data_file = "currency_data.xlsx"

df_usd_inr_milestones = pd.read_excel(data_file, sheet_name='usd_inr_milestones')
df_usd_inr_milestones['Plot_Year'] = pd.to_numeric(df_usd_inr_milestones['Year'], errors='coerce')
df_usd_inr_milestones['Exchange Rate (INR per USD, Approximate)'] = pd.to_numeric(df_usd_inr_milestones['Exchange Rate (INR per USD, Approximate)'])

df_macro_2000_2008 = pd.read_excel(data_file, sheet_name='macro_2000_2008')
df_macro_2019_2026 = pd.read_excel(data_file, sheet_name='macro_2019_2026')
df_historical_inr_major_currencies = pd.read_excel(data_file, sheet_name='historical_inr_major_currencies')
df_fiscal_deficit = pd.read_excel(data_file, sheet_name='fiscal_deficit')
df_trade_balance = pd.read_excel(data_file, sheet_name='trade_balance')
df_simulated_fii = pd.read_excel(data_file, sheet_name='simulated_fii')


# --- Streamlit App Configuration ---
st.set_page_config(
    page_title="The Indian Rupee's Journey",
    page_icon="🇮🇳",
    layout="wide"
)

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
sections = [
    "Home",
    "Introduction to INR",
    "Historical Trajectory",
    "Key Influencing Factors",
    "Major Companies & Export Partners",
    "INR Rates & FX (Trader's Perspective)",
    "Data Tables",
    "Conclusion"
]
selected_section = st.sidebar.radio("Go to", sections)

# --- Helper Functions for Visualizations ---
def plot_usd_inr_milestones(df):
    fig = px.line(df.dropna(subset=['Plot_Year']), x="Plot_Year", y="Exchange Rate (INR per USD, Approximate)",
                  title="USD/INR Exchange Rate Milestones (1947-2025)",
                  labels={"Plot_Year": "Year", "Exchange Rate (INR per USD, Approximate)": "INR per USD"},
                  markers=True,
                  line_shape='linear') # Use 'linear' for straight lines between points
    fig.update_traces(marker=dict(size=8, line=dict(width=2, color='DarkSlateGrey')),
                      selector=dict(mode='markers+lines'))
    fig.update_layout(hovermode="x unified",
                      xaxis_title="Year",
                      yaxis_title="INR per USD",
                      template="plotly_white")
    return fig

def plot_macro_indicators(df, y_col, title, y_axis_title):
    fig = px.line(df, x="Fiscal Year", y=y_col,
                  title=title,
                  labels={"Fiscal Year": "Fiscal Year", y_col: y_axis_title},
                  markers=True,
                  line_shape='linear')
    fig.update_traces(marker=dict(size=8, line=dict(width=2, color='DarkSlateGrey')),
                      selector=dict(mode='markers+lines'))
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig

def plot_fiscal_deficit(df):
    fig = px.bar(df, x="Fiscal Year (FY)", y="Fiscal Deficit (% of GDP)",
                 title="India's Fiscal Deficit (% of GDP) Over Time",
                 labels={"Fiscal Year (FY)": "Fiscal Year", "Fiscal Deficit (% of GDP)": "Fiscal Deficit (% of GDP)"},
                 color="Fiscal Deficit (% of GDP)",
                 color_continuous_scale=px.colors.sequential.Plasma) # A nice color scale
    fig.update_layout(template="plotly_white")
    return fig

def plot_trade_components(df, component_name, title):
    df_filtered = df[df['Component'] == component_name].set_index('Component')
    df_plot = df_filtered.T.reset_index()
    df_plot.columns = ['Fiscal Year', component_name]
    fig = px.bar(df_plot, x='Fiscal Year', y=component_name,
                 title=title,
                 labels={'Fiscal Year': 'Fiscal Year', component_name: 'USD Billion'},
                 color=component_name,
                 color_continuous_scale=px.colors.sequential.Viridis)
    fig.update_layout(template="plotly_white")
    return fig

# --- NEW: Multi-Currency Exchange Rate Chart ---
def plot_multi_currency_inr(df):
    df_plot = df.melt(id_vars=['Year'], var_name='Currency Pair', value_name='Exchange Rate')
    df_plot = df_plot.dropna(subset=['Exchange Rate']) # Remove None values for plotting

    fig = px.line(df_plot, x='Year', y='Exchange Rate', color='Currency Pair',
                  title='INR Exchange Rates Against Major Currencies (Annual Average)',
                  labels={'Exchange Rate': 'INR per Unit of Foreign Currency'},
                  markers=True)
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig

# --- NEW: Twin Deficits Plot (Fiscal vs. Current Account) ---
def plot_twin_deficits(df_fiscal, df_macro_2019_2026):
    df_plot = df_macro_2019_2026[['Fiscal Year', 'Fiscal Deficit (General Govt, % GDP)', 'Current Account Balance (% GDP)']].copy()
    df_plot['Fiscal Deficit (General Govt, % GDP)'] = pd.to_numeric(df_plot['Fiscal Deficit (General Govt, % GDP)'])
    df_plot['Current Account Balance (% GDP)'] = pd.to_numeric(df_plot['Current Account Balance (% GDP)'])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['Fiscal Year'], y=df_plot['Fiscal Deficit (General Govt, % GDP)'],
                             mode='lines+markers', name='Fiscal Deficit (% GDP)',
                             line=dict(color='red', width=2)))
    fig.add_trace(go.Scatter(x=df_plot['Fiscal Year'], y=df_plot['Current Account Balance (% GDP)'],
                             mode='lines+markers', name='Current Account Balance (% GDP)',
                             line=dict(color='blue', width=2)))

    fig.update_layout(title='India\'s Twin Deficits: Fiscal vs. Current Account (% of GDP)',
                      xaxis_title='Fiscal Year',
                      yaxis_title='% of GDP',
                      hovermode="x unified",
                      template="plotly_white")
    return fig

# --- NEW: Forex Reserves Growth ---
def plot_forex_reserves(df_macro_2000_2008, df_macro_2019_2026):
    df_combined = pd.concat([
        df_macro_2000_2008[['Fiscal Year', 'Forex Reserves (End-Period, USD Bn)']],
        df_macro_2019_2026[['Fiscal Year', 'Forex Reserves (End-Period, USD Bn)']]
    ])
    df_combined['Forex Reserves (End-Period, USD Bn)'] = pd.to_numeric(df_combined['Forex Reserves (End-Period, USD Bn)'])

    fig = px.area(df_combined, x='Fiscal Year', y='Forex Reserves (End-Period, USD Bn)',
                  title='India\'s Foreign Exchange Reserves Growth (USD Billion)',
                  labels={'Forex Reserves (End-Period, USD Bn)': 'Forex Reserves (USD Bn)'},
                  line_shape='spline',
                  color_discrete_sequence=px.colors.sequential.Greens)
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig

# --- NEW: Inflation Breakdown (CPI vs WPI) ---
def plot_inflation_breakdown(df_macro_2000_2008, df_macro_2019_2026):
    df_combined = pd.concat([
        df_macro_2000_2008[['Fiscal Year', 'WPI Inflation (Avg, %)', 'CPI-IW Inflation (Avg, %)']],
        df_macro_2019_2026[['Fiscal Year', 'CPI Inflation (Avg, %)']].rename(columns={'CPI Inflation (Avg, %)': 'CPI-IW Inflation (Avg, %)'}) # Align column names
    ])
    df_combined['WPI Inflation (Avg, %)'] = pd.to_numeric(df_combined['WPI Inflation (Avg, %)'])
    df_combined['CPI-IW Inflation (Avg, %)'] = pd.to_numeric(df_combined['CPI-IW Inflation (Avg, %)'])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_combined['Fiscal Year'], y=df_combined['WPI Inflation (Avg, %)'],
                             mode='lines+markers', name='WPI Inflation (Avg, %)',
                             line=dict(color='orange', width=2)))
    fig.add_trace(go.Scatter(x=df_combined['Fiscal Year'], y=df_combined['CPI-IW Inflation (Avg, %)'],
                             mode='lines+markers', name='CPI Inflation (Avg, %)',
                             line=dict(color='purple', width=2)))

    fig.update_layout(title='India\'s Inflation Trends: WPI vs. CPI (Average %)',
                      xaxis_title='Fiscal Year',
                      yaxis_title='Inflation (%)',
                      hovermode="x unified",
                      template="plotly_white")
    return fig

# --- NEW: FII/FPI Net Flows (Bar Chart with Positive/Negative) ---
def plot_fii_net_flows(df_macro_2000_2008, df_simulated_fii):
    # Combine historical and simulated recent data
    # df_historical_fii = df_macro_2000_2008[['Fiscal Year', 'Net FII Inflows (USD Bn)']].copy()
    # df_historical_fii.rename(columns={'Fiscal Year': 'Date', 'Net FII Inflows (USD Bn)': 'Net FII Flow (INR Cr)'}, inplace=True)
    # df_historical_fii['Net FII Flow (INR Cr)'] = df_historical_fii['Net FII Flow (INR Cr)'] * 100 # Convert USD Bn to INR Cr (approx)

    # df_combined_fii = pd.concat([df_historical_fii, df_simulated_fii], ignore_index=True)
    df_simulated_fii['Flow Type'] = df_simulated_fii['Net FII Flow ($m)'].apply(lambda x: 'Inflow' if x >= 0 else 'Outflow')
    df_simulated_fii['Net FII Flow ($m)'] = round(df_simulated_fii['Net FII Flow ($m)'].astype(int))
    # df_combined_fii['Date'] = pd.to_datetime(df_combined_fii['Date'])
    # df_combined_fii = df_combined_fii.sort_values(by='Date')

    fig = px.bar(df_simulated_fii, x='Date', y='Net FII Flow ($m)', color='Flow Type',
                 color_discrete_map={'Inflow': 'green', 'Outflow': 'red'},
                 title='Net FII Inflows/Outflows ($m) - Historical & Recent',
                 labels={'Net FII Flow ($m)': 'Net FII Flows ($m)'})
    fig.update_layout(template="plotly_white")
    return fig

# --- NEW: GDP Growth Comparison (Illustrative) ---
def plot_gdp_comparison(df_macro_2019_2026):
    df_plot = df_macro_2019_2026.copy()
    df_plot['Global Avg. GDP Growth (%)'] = [3.0, -3.5, 5.5, 3.2, 2.8, 3.0, 3.1] # Hypothetical global averages

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['Fiscal Year'], y=df_plot['Real GDP Growth (%)'],
                             mode='lines+markers', name='India Real GDP Growth (%)',
                             line=dict(color='darkblue', width=2)))
    fig.add_trace(go.Scatter(x=df_plot['Fiscal Year'], y=df_plot['Global Avg. GDP Growth (%)'],
                             mode='lines+markers', name='Global Avg. GDP Growth (%) (Illustrative)',
                             line=dict(color='grey', width=2, dash='dash')))

    fig.update_layout(title='India vs. Global Average Real GDP Growth (%) (2019-2026)',
                      xaxis_title='Fiscal Year',
                      yaxis_title='GDP Growth (%)',
                      hovermode="x unified",
                      template="plotly_white")
    return fig

# --- NEW: Hypothetical Yield Curve Plot ---
def plot_yield_curve():
    maturities = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30]  # Years
    yields =     [5.80, 5.90, 6.10, 6.30, 6.40, 6.50, 6.60, 6.36, 6.80, 6.88, 7.04]  # %

    fig = px.line(x=maturities, y=yields,
                  title='Indian Government Bond Yield Curve',
                  labels={'x': 'Maturity (Years)', 'y': 'Yield (%)'},
                  markers=True)
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig


# --- Streamlit App Content ---

if selected_section == "Home":
    st.title("🇮🇳 The Indian Rupee's Journey: An Economic Barometer 📈")
    st.write("""
    Welcome to the comprehensive analysis of the Indian Rupee (INR)!
    The INR is more than just a currency; it's a critical barometer of India's economic health,
    reflecting its fiscal prudence, trade dynamics, and attractiveness to global capital.

    This site delves into the fascinating history of the USD/INR exchange rate from 1947 to 2025,
    exploring the complex interplay of domestic policies, global events, and the pivotal role of the
    Reserve Bank of India (RBI).

    Navigate through the sections using the sidebar to gain a nuanced understanding of the INR's
    movements and its significance in the global financial landscape.
    """)
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Indian_Rupee_symbol.svg/1200px-Indian_Rupee_symbol.svg.png", width=150)
    st.subheader("What you'll find here:")
    st.markdown("""
    - **Historical Trajectory:** Key milestones and turning points in the INR's value. 🕰️
    - **Key Influencing Factors:** Deep dive into political, fiscal, trade, monetary, and investment dynamics. 📊
    - **RBI's Role:** Understanding the central bank's strategies in managing currency volatility. 🏦
    - **Trader's Perspective:** Insights into INR rates, FX, and market sentiment. 💹
    - **Comprehensive Data:** Access to key macroeconomic indicators and exchange rate data. 📈
    """)
    st.info("💡 **Tip:** Use the navigation on the left to explore different aspects of the Indian Rupee's journey!")

elif selected_section == "Introduction to INR":
    st.title("Introduction to the Indian Rupee (INR) 📚")
    st.header("Purpose and Scope")
    st.write("""
    This report provides a comprehensive analysis of the historical trajectory of the United States Dollar (USD)
    versus the Indian Rupee (INR) exchange rate, spanning the period from India's independence in 1947 to
    projections for 2025. The primary objective is to identify significant movements and turning points in the
    USD/INR exchange rate and to provide detailed explanations for these changes.
    """)
    st.subheader("Key Influencing Factors: A Snapshot 📸")
    st.markdown("""
    - **Political Environment:** Stability, policy direction, geopolitical events, and reforms. 🏛️
    - **Fiscal Situation:** Government spending, revenue, budget deficits, and public debt. 💰
    - **Trade Situation:** Balance of trade, current account balance, export competitiveness, and import dependence (especially oil). 🚢
    - **Monetary Conditions:** Inflation rates (WPI, CPI), money supply, and currency in circulation. 💲
    - **Economic Growth:** GDP growth rates, sectoral performance, and overall economic health. 📈
    - **Investment Flows:** The volume and volatility of FDI and FII inflows/outflows. 💸
    - **Central Bank Policies:** RBI's stance on interest rates, liquidity management, forex intervention, reserve management, and the overall monetary/exchange rate policy framework. 🏦
    """)

    st.header("Evolution of Exchange Rate Regimes 🔄")
    st.write("""
    India's exchange rate regime has undergone a significant transformation since 1947.
    """)
    st.markdown("""
    - **Initial Peg & Bretton Woods (1947-1970s):** Initially pegged to the Pound Sterling, then briefly to the USD. 🔗
    - **Basket Peg (1975):** Shifted to a basket of currencies of major trading partners to manage volatility. 🧺
    - **Post-1991 Reforms (1992-1993):** Transitioned through LERMS to a unified, market-determined managed float system. 🌊
    - **Inflation Targeting (2016):** Formal adoption of a flexible IT framework, making price stability the primary nominal anchor. 🎯
    """)
    st.info("The journey reflects India's adaptation to global economic shifts and its pursuit of macroeconomic stability.")

elif selected_section == "Historical Trajectory":
    st.title("Historical Trajectory of the INR 🕰️")

    st.header("USD/INR Exchange Rate Milestones: A Visual Journey 📊")
    st.write("Observe the long-term depreciation trend of the Indian Rupee against the US Dollar.")
    st.plotly_chart(plot_usd_inr_milestones(df_usd_inr_milestones), use_container_width=True)
    st.dataframe(df_usd_inr_milestones) # Keep table for detailed view
    st.download_button("Download USD/INR Milestones Data", df_usd_inr_milestones.to_csv(index=False), "usd_inr_milestones.csv", "text/csv")

    st.markdown("---") # Separator

    st.header("INR Against Major Currencies: A Broader Perspective 🌍")
    st.write("The Indian Rupee's value against other major global currencies reveals its sensitivity to diverse international economic forces.")
    st.plotly_chart(plot_multi_currency_inr(df_historical_inr_major_currencies), use_container_width=True)
    st.caption("Source: Compiled from RBI, BookMyForex, Investing.com. Note: Data availability varies by currency pair.")
    st.download_button("Download INR Major Currencies Data", df_historical_inr_major_currencies.to_csv(index=False), "inr_major_currencies.csv", "text/csv")

    st.markdown("---") # Separator

    st.header("Key Historical Periods & Their Impact on INR 📉📈")

    with st.expander("The Early Years (1947 - 1966): Post-Independence Stability and the First Major Devaluation"):
        st.subheader("Initial Peg & Bretton Woods Context (1947 - 1949) 🔗")
        st.write(f"""
        Upon independence, INR was pegged to the British Pound at £1 = ₹13.33. This set the initial USD/INR at approximately **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == 1947, 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f}**.
        """)
        st.subheader("The 1949 Devaluation 📉")
        st.write(f"""
        Triggered by Pound Sterling's devaluation, INR followed suit, establishing a new stable peg of **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == 1949, 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f} per USD**.
        """)
        st.subheader("Period of Stability (1950 - 1965): Growing Pressures ⏳")
        st.write("""
        A fixed rate masked underlying issues: growing fiscal deficits, persistent trade deficits (due to Import Substitution Industrialization), and nascent inflation. The Rupee became increasingly overvalued.
        """)
        st.subheader("The 1966 Devaluation: A Breaking Point 💥")
        st.write(f"""
        Severe BoP crisis (wars, drought, aid cut-off) forced a **57.5% devaluation** to **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == 1966, 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f} per USD**.
        """)

    with st.expander("Navigating Global Shifts (1966 - 1991): Basket Peg and Rising Vulnerabilities"):
        st.subheader("Post-Devaluation Adjustments & Bretton Woods Collapse (1966 - 1975) 🌍")
        st.write(f"""
        INR settled at ₹7.50, then shifted to a basket peg in 1975. Rate moved towards **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == 1975, 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f} by 1975**.
        """)
        st.subheader("The Basket Peg Era (1975 - 1990): Managed Depreciation & Growing Debt 💸")
        st.write(f"""
        Managed depreciation to **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == 1990, 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f} by 1990**, against a backdrop of deteriorating fiscal discipline and widening CAD. External debt nearly doubled.
        """)
        st.subheader("The 1991 BoP Crisis: A Wake-Up Call 🚨")
        st.write(f"""
        Triggered by the Gulf War and critically low reserves, the INR was devalued by **18-19%** to over **₹22.74 This led to major economic reforms.
        """)

    with st.expander("Liberalization Era (1991 - 2000): Reforms, Recovery, and Resilience"):
        st.subheader("The 1991 Reforms and Exchange Rate Management 🚀")
        st.write("""
        Shift to a market-determined managed float system in 1993, coupled with trade and investment liberalization.
        """)
        st.subheader("Economic Performance (1992 - 1997): Recovery and Growth 📈")
        st.write("""
        GDP growth averaged over 7%. Forex reserves began a steady climb, providing a crucial buffer.
        """)
        st.subheader("Navigating the Asian Financial Crisis (AFC) (1997 - 1998): Relative Insulation 🛡️")
        st.write("""
        India weathered the AFC well due to cautious capital account liberalization and a flexible exchange rate. The Rupee depreciated orderly by **18-19%**.
        """)
        st.subheader("Late 1990s (1998 - 2000): Pokhran Sanctions and Continued Reforms ⚛️")
        st.write(f"""
        Economic impact of sanctions was modest, bolstered by **$4.2 billion** from Resurgent India Bonds. USD/INR moved towards **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == 2000, 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f}**.
        """)

    with st.expander("The Growth Phase (2000 - 2008): IT Boom, Capital Inflows, and RBI's Balancing Act"):
        st.subheader("High Growth Era (2003 - 2008) 🚀")
        st.write(f"""
        Unprecedented GDP growth, averaging nearly **9%** per year, driven by the IT sector.
        """)
        st.subheader("Capital Inflows and INR Appreciation Pressure 💰")
        st.write(f"""
        Massive FII inflows created immense appreciation pressure, with INR briefly breaching **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == '2008 (Peak)', 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f}**.
        """)
        st.subheader("RBI Policy Response: Intervention and Sterilization 🏦")
        st.write(f"""
        RBI intervened heavily, accumulating forex reserves up to **${df_macro_2000_2008.loc[df_macro_2000_2008['Fiscal Year'] == '2007/08', 'Forex Reserves (End-Period, USD Bn)'].iloc[0]:.1f} billion**. Massive sterilization operations were undertaken.
        """)
        st.subheader("Macroeconomic Snapshot (2000-2008) 📊")
        st.plotly_chart(plot_macro_indicators(df_macro_2000_2008, "Real GDP Growth (%)", "Real GDP Growth (2000-2008)", "GDP Growth (%)"), use_container_width=True)
        st.plotly_chart(plot_fii_net_flows(df_macro_2000_2008, df_simulated_fii), use_container_width=True) # NEW FII plot
        st.caption("Source: RBI, NSDL.")
        st.info("This period highlighted the 'Impossible Trilemma' for India, balancing exchange rate stability, independent monetary policy, and capital account openness.")

    with st.expander("Global Shocks and Domestic Challenges (2008 - 2013): GFC, Inflation, and the Taper Tantrum"):
        st.subheader("Impact of the 2008 Global Financial Crisis (GFC) 📉")
        st.write(f"""
        GFC led to capital outflows and sharp INR depreciation, crossing **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == '2008 (Avg)', 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f}**. GDP growth slowed to **6.7%**.
        """)
        st.subheader("Post-GFC Recovery and Emerging Problems (2009 - 2012) ⚠️")
        st.write(f"""
        Recovery sowed seeds for future problems: persistent high inflation and a widening CAD, reaching a record **4.2% of GDP** in 2011-12.
        """)
        st.subheader("The 2013 Taper Tantrum: 'Fragile Five' Moment 🌪️")
        st.write(f"""
        Fears of US Fed tapering triggered massive capital outflows. INR depreciated sharply to an all-time low of nearly **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == '2013 (Low)', 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f}**.
        """)
        st.subheader("India's Twin Deficits: A Vulnerability Highlighted 📊")
        st.plotly_chart(plot_twin_deficits(df_fiscal_deficit, df_macro_2019_2026), use_container_width=True) # NEW Twin Deficits plot
        st.caption("Source: RBI, Economic Surveys. Note: Fiscal deficit data aligned for common years.")


    with st.expander("Navigating New Normals (2014 - 2019): Policy Shifts and Domestic Events"):
        st.subheader("New Government and Policy Framework (2014 onwards) 🏛️")
        st.write("""
        The BJP-led NDA government emphasized economic reforms and fiscal consolidation.
        A key development was the formal adoption of a flexible Inflation Targeting (IT) framework in 2016, with a CPI inflation target of **4% (+/- 2%)**.
        """)
        st.subheader("Economic Performance and USD/INR (2014 - 2019) 📊")
        st.write(f"""
        Relative macroeconomic stability, with inflation largely contained. USD/INR depreciated gradually from **₹60-63/$ to ₹70-72/$**.
        """)
        st.subheader("Major Domestic Events: Structural Shifts & Shocks 🔄")
        st.markdown("""
        - **Demonetization (Nov 2016):** Withdrawal of ₹500 and ₹1000 banknotes, causing short-term disruption. 💸
        - **Goods and Services Tax (GST) (July 2017):** Significant indirect tax reform for a unified national market. 🧾
        - **IL&FS Crisis (2018):** Defaults by a large NBFC, triggering a liquidity crisis. 🏦
        """)

    with st.expander("Recent Years and Outlook (2020 - 2025): Pandemic, Recovery, and Future Path"):
        st.subheader("Impact of COVID-19 Pandemic (2020 - 2022) 😷")
        st.write(f"""
        Severe GDP contraction (**-5.8% in FY21**), followed by recovery. Forex reserves reached an all-time high of over **${df_macro_2019_2026.loc[df_macro_2019_2026['Fiscal Year'] == '2023/24', 'Forex Reserves (End-Period, USD Bn)'].iloc[0]:.1f} billion** in late 2021.
        """)
        st.subheader("Post-Pandemic Recovery and Global Headwinds (2022 - 2024) 🌪️")
        st.write(f"""
        Global commodity price surges and monetary tightening put pressure on INR, depreciating past **₹80/$**. RBI actively intervened.
        """)
        st.subheader("Current Situation and Outlook (2024 - 2025) 🔮")
        st.write(f"""
        Strong growth momentum (IMF projects **6.2% in 2025**). Inflation expected to converge towards **4%**.
        USD/INR outlook suggests relative stability around **₹{df_usd_inr_milestones.loc[df_usd_inr_milestones['Year'] == '2025 (May)', 'Exchange Rate (INR per USD, Approximate)'].iloc[0]:.2f}**.
        """)
        st.subheader("Macroeconomic Snapshot (2019-2026) 📊")
        st.plotly_chart(plot_macro_indicators(df_macro_2019_2026, "Real GDP Growth (%)", "Real GDP Growth (2019-2026)", "GDP Growth (%)"), use_container_width=True)
        st.plotly_chart(plot_inflation_breakdown(df_macro_2000_2008, df_macro_2019_2026), use_container_width=True) # Re-using the new inflation breakdown plot
        st.plotly_chart(plot_forex_reserves(df_macro_2000_2008, df_macro_2019_2026), use_container_width=True) # NEW Forex Reserves
        st.plotly_chart(plot_gdp_comparison(df_macro_2019_2026), use_container_width=True) # NEW GDP Comparison

elif selected_section == "Key Influencing Factors":
    st.title("Key Influencing Factors on the INR 📊")

    st.header("Understanding the Forces that Shape the Rupee's Value")

    with st.expander("Political Environment 🏛️"):
        st.subheader("Stability & Elections")
        st.write("""
        Political stability fosters a predictable economic environment, crucial for attracting foreign investment.
        Historically, the rupee tends to see a modest appreciation (avg. **1.85%** in first week) post-election due to reduced uncertainty.
        """)
        st.info("A strong majority for the ruling party could lead to INR appreciation towards **82.50 levels**, while a hung parliament might result in depreciation towards **84-84.50 levels**.")
        st.subheader("Geopolitical Tensions")
        st.write("""
        External geopolitical and trade policy shifts (e.g., Israel-Iran conflict, US reciprocal tariffs) trigger "risk-off" sentiment, leading to capital flight from emerging markets like India.
        """)
        st.warning("Continuous monitoring of the global geopolitical landscape is essential for FX traders.")

    with st.expander("Fiscal Health: Budget Balance and Deficit 💰"):
        st.subheader("Fiscal Deficit Trends")
        st.write("""
        A manageable fiscal deficit is essential for macroeconomic stability and investor confidence.
        Historically, India has grappled with high fiscal deficits, peaking at **12.7% of GDP in 1990-91**.
        """)
        st.plotly_chart(plot_fiscal_deficit(df_fiscal_deficit), use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="FY25 Fiscal Deficit Target", value="4.8% of GDP", delta="-0.1% from initial target")
        with col2:
            st.metric(label="FY26 Fiscal Deficit Target", value="4.4% of GDP")
        st.write("""
        The successful achievement of the FY25 fiscal deficit target and the commitment to a downward glide path are crucial for reinforcing investor confidence.
        """)
        st.subheader("The 'Oil Factor' in Fiscal Health ⛽")
        st.write("""
        Elevated oil prices directly contribute to widening India's fiscal deficit. When oil prices rise, India's import bill increases, straining government finances.
        """)
        st.error("This forms a negative feedback loop where external shocks can exacerbate domestic fiscal challenges, ultimately putting downward pressure on the INR.")

    with st.expander("Trade Dynamics: Import/Export Shocks and Trade Balance 🚢"):
        st.subheader("Persistent Trade Deficits")
        st.write("""
        India's trade balance consistently shows deficits due to its heavy reliance on imports of crude oil, gold, and machinery.
        """)
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Merchandise Trade Deficit FY2023-24", value="$240.17 Billion", delta="-9.33% from FY2022-23")
        with col2:
            st.metric(label="Recent Trade Deficit (narrowed to)", value="$15.6 Billion")

        # Visualizing Merchandise Trade Deficit
        merch_deficit_data = df_trade_balance[df_trade_balance['Component'] == 'Merchandise Trade Deficit'].iloc[0]
        merch_deficit_years = ['FY2022-23 (USD Billion)', 'FY2023-24 (USD Billion)', 'FY2025 (Projected/Actual) (USD Billion)']
        merch_deficit_values = [merch_deficit_data[col] for col in merch_deficit_years]
        merch_deficit_df = pd.DataFrame({
            'Fiscal Year': ['FY2022-23', 'FY2023-24', 'FY2025 (Proj)'],
            'Merchandise Trade Deficit (USD Bn)': merch_deficit_values
        })
        fig_merch_deficit = px.bar(merch_deficit_df, x='Fiscal Year', y='Merchandise Trade Deficit (USD Bn)',
                                   title='Merchandise Trade Deficit (USD Billion)',
                                   labels={'Merchandise Trade Deficit (USD Bn)': 'USD Billion'},
                                   color='Merchandise Trade Deficit (USD Bn)',
                                   color_continuous_scale=px.colors.sequential.Reds)
        st.plotly_chart(fig_merch_deficit, use_container_width=True)

        st.subheader("The Dual Impact of Rupee Depreciation")
        st.write("""
        A weaker rupee can make imports more expensive, exacerbating the trade deficit, but it can also boost exports by making Indian goods more competitive globally.
        However, a stronger rupee can positively impact real exports by reducing the cost of imported inputs for export-oriented industries.
        """)
        st.info("Optimal exchange rate depends on the import content of India's export basket.")

        st.subheader("Strategic Trade Initiatives 🤝")
        st.write("""
        India has **13 active Free Trade Agreements (FTAs)** and is negotiating more (e.g., UK-India trade deal expected to increase bilateral trade by **£25.5 billion**).
        Over **18 countries** have agreed to use INR for international trade settlements, reducing reliance on the US Dollar.
        """)
        st.success("These initiatives aim to enhance the INR's global standing and reduce its vulnerability to dollar strength.")

    with st.expander("Inflation Regimes and Their Impact 💲"):
        st.subheader("Inflation's Erosion of Purchasing Power")
        st.write("""
        When India's inflation rate is higher than its trading partners, the rupee's purchasing power diminishes, leading to natural depreciation to maintain purchasing power parity.
        """)
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Projected CPI Inflation FY2025-26", value="4.8%")
        with col2:
            st.metric(label="CPI Inflation Feb 2024", value="5.09%")
        st.plotly_chart(plot_inflation_breakdown(df_macro_2000_2008, df_macro_2019_2026), use_container_width=True) # Re-using the new inflation breakdown plot

        st.subheader("RBI's Balancing Act ⚖️")
        st.write("""
        The RBI raises interest rates to combat inflation, which can attract foreign capital and support the rupee. However, this also increases domestic borrowing costs, potentially dampening economic growth.
        """)
        st.warning("Anticipating the RBI's reaction function to inflation data is paramount for traders, as its policy decisions significantly influence currency movements and bond yields.")

    with st.expander("Investment Flows: FDI, FII/FPI Inflows and Outflows 💸"):
        st.subheader("FII/FPI Impact on INR")
        st.write("""
        Foreign Institutional Investors (FIIs) and Foreign Portfolio Investors (FPIs) significantly influence the INR.
        **Inflows** (foreign currency converted to INR) strengthen the rupee.
        **Outflows** (INR converted back to foreign currency) put downward pressure on the rupee.
        """)
        st.plotly_chart(plot_fii_net_flows(df_macro_2000_2008, df_simulated_fii), use_container_width=True) # Re-using the new FII plot
        st.caption("Source: RBI, NSDL.")
        st.write("""
        FIIs pulled out over **₹1 lakh crore** from Indian equities by mid-February 2025 due to pricey valuations and strong dollar.
        However, they turned net buyers in April 2025, pumping in over **₹4,200 crore**, helping the rupee rebound.
        """)
        st.subheader("Drivers of Flows")
        st.markdown("""
        - **Outflows:** Global economic conditions, political instability, currency fluctuations, high inflation.
        - **Inflows:** Economic growth prospects, strong market performance, stable political environment.
        """)
        st.info("The growing resilience of India's domestic capital markets (DIIs) helps mitigate the impact of FII outflows.")

    with st.expander("Central Bank Policies: RBI's Role in Exchange Rate Management 🏦"):
        st.subheader("Managed Float Regime")
        st.write("""
        India operates under a "managed float" system, where the INR's value is largely market-determined, but the RBI intervenes to maintain orderly conditions and curb excessive volatility.
        """)
        st.subheader("RBI's Intervention Strategy")
        st.write("""
        The RBI "leans against the wind" by buying or selling foreign currency (mainly USD) in spot or forward markets.
        """)
        st.metric(label="Rupee-Dollar Volatility (2023-2024)", value="1.8%", help="Lowest in over two decades, attributed to active RBI interventions.")
        st.write("""
        The RBI's net sales reached **$34.5 billion in FY25**, the highest since the 2008-09 global financial crisis, to stabilize the rupee.
        """)
        st.subheader("Monetary Policy Tools")
        st.markdown("""
        - **Setting Interest Rates (Repo Rate):** Influences borrowing costs and attracts foreign capital.
        - **Open Market Operations (OMOs):** Manages money supply and liquidity.
        - **Reserve Requirements (CRR):** Dictates banks' lending capacity.
        - **Forex Swaps:** Manages volatility and infuses liquidity.
        """)
        st.success("The RBI's sophisticated and proactive role is crucial in maintaining macroeconomic equilibrium amidst global uncertainties.")


elif selected_section == "Major Companies & Export Partners":
    st.title("Major Companies and Export Partners Affecting India's Fiscal Health 🏭🌍")

    st.header("India's Corporate Giants: Pillars of the Economy 🏢")
    st.write("""
    India's largest companies contribute significantly to national revenue, foreign exchange earnings, and overall economic stability.
    """)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Revenue Earners 💰")
        st.markdown("""
        - **Reliance Industries:** $110.94 Billion
        - **Life Insurance of India:** $102.15 Billion
        - **Indian Oil:** $87.18 Billion
        - **Oil and Natural Gas:** $76.11 Billion
        - **Bharat Petroleum:** $50.94 Billion
        """)
    with col2:
        st.subheader("Most Profitable (2024) 📈")
        st.markdown("""
        - **Reliance Industries:** $8,412.50 Million
        - **Life Insurance Corp. of India (LIC):** $103,547.60 Million revenue, $4,944 Million profits.
        - HDFC Bank made its debut among the world's largest corporations by revenue in 2025.
        """)
    st.info("Export-oriented companies like TCS and Sun Pharma, earning substantial foreign currency, benefit from rupee depreciation, boosting national income.")

    st.header("India's Export Powerhouses & Global Reach 🌐")
    st.write("""
    Strong demand from India's export partners, particularly for high-value-added products and services, directly supports the INR's value.
    """)
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Top Export Destinations 🗺️")
        st.markdown("""
        - **United States:** 17.73% of total exports ($77.52 Billion)
        - **United Arab Emirates**
        - **Netherlands**
        - **China**
        - **Singapore**
        """)
    with col4:
        st.subheader("Key Indian Exports 📦")
        st.markdown("""
        - Refined Petroleum ⛽
        - Diamonds 💎
        - Packaged Medicaments 💊
        - Jewelry 💍
        - Rice 🍚
        - Engineering Goods ⚙️
        - Electronics 🔌
        - Pharmaceuticals 🧪
        """)
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total Exports (Goods & Services) 2024-25", value="$825 Billion")
    with col2:
        st.metric(label="Services Exports Growth (2013-14 to 2024-25)", value=">2x", help="From $158 Billion to $387 Billion")
    st.success("Strategic Free Trade Agreements (FTAs) and rupee-based trade settlements are enhancing India's global competitiveness and reducing reliance on the US Dollar.")


elif selected_section == "INR Rates & FX (Trader's Perspective)":
    st.title("INR Rates & FX: A Trader's Deep Dive 💹")
    st.write("For financial professionals, understanding the nuances of INR trading, interest rate dynamics, and advanced instruments is crucial.")

    st.header("1. Understanding Rate Curves: The Price of Time ⏳")
    st.write("""
    The **Yield Curve** is a graphical representation of the yields on bonds of different maturities, but with the same credit quality. For traders, it's a powerful indicator of market expectations for future interest rates and economic growth.
    """)
    st.plotly_chart(plot_yield_curve(), use_container_width=True)
    st.caption("Source: Hypothetical data for illustrative purposes. Real data from CCIL, RBI, Bloomberg.")

    st.subheader("What the Yield Curve Tells Traders:")
    st.markdown("""
    - **Normal Curve (Upward Sloping):** Long-term yields > Short-term yields. Signals economic expansion and higher inflation expectations.
    - **Inverted Curve (Downward Sloping):** Short-term yields > Long-term yields. Often signals an impending economic slowdown or recession.
    - **Flat Curve:** Little difference between short and long-term yields. Suggests a transition period.
    """)
    st.info("Traders use yield curve shifts to anticipate RBI's monetary policy moves and position their bond portfolios (e.g., Barbell Strategy, Laddered Maturity).")

    st.header("2. FX Trading: Spot, Forwards, and NDFs 🌐")
    st.write("Foreign Exchange (FX) trading involves exchanging one currency for another. For the INR, traders engage in various types of transactions:")

    st.subheader("A. Spot Trading: Immediate Exchange ⚡")
    st.markdown("""
    - **Definition:** Exchange of currencies for immediate delivery (typically T+2 business days).
    - **Use Case:** Most common for tourism, international trade payments, and short-term speculative positions.
    - **INR Context:** The USD/INR spot rate is what you see quoted most frequently.
    """)

    st.subheader("B. Forward Contracts: Locking in Future Rates 🔒")
    st.markdown("""
    - **Definition:** An agreement to exchange a specified amount of one currency for another at a pre-determined rate on a future date.
    - **Use Case:** Primarily used by businesses to hedge against future currency risk (e.g., an Indian exporter expecting USD payment in 3 months can lock in the INR conversion rate today).
    - **INR Context:** Indian companies use onshore forward contracts to manage their forex exposure.
    """)

    st.subheader("C. Non-Deliverable Forwards (NDFs): Offshore INR Trading 🌊")
    st.markdown("""
    - **Definition:** A cash-settled, short-term forward contract on a thinly traded or non-convertible currency (like the INR in offshore markets). No physical exchange of currencies occurs at maturity.
    - **How it Works:** At maturity, the difference between the agreed-upon NDF rate and the prevailing spot rate is settled in a freely convertible currency (usually USD).
    - **Why NDFs for INR?**
        - **Capital Controls:** India has capital account restrictions, making the INR not fully convertible for all purposes. NDFs allow foreign investors and institutions to gain exposure to INR movements without physically bringing rupees onshore.
        - **Liquidity:** The offshore NDF market for INR is highly liquid, often more so than the onshore forward market for certain tenors.
        - **Price Discovery:** NDF rates can influence onshore rates and vice-versa, providing a key channel for price discovery.
    - **Use Case:** Speculation on INR movements, hedging by foreign entities with INR exposure, and arbitrage opportunities between onshore and offshore markets.
    """)
    st.info("NDFs are a critical component of the global INR ecosystem, reflecting international sentiment and demand for INR exposure.")

    st.header("3. Arbitrage: Exploiting Price Discrepancies 💰🔄")
    st.write("""
    Arbitrage is the simultaneous purchase and sale of an asset in different markets to profit from a difference in its price. In FX and rates, this often involves exploiting discrepancies between exchange rates and interest rates.
    """)

    st.subheader("A. Covered Interest Parity (CIP): The Foundation of FX Arbitrage 🤝")
    st.markdown("""
    - **Concept:** CIP states that the interest rate differential between two countries should be equal to the differential between the forward exchange rate and the spot exchange rate.
    - **Formula (Simplified):** `Forward Rate / Spot Rate ≈ (1 + Domestic Interest Rate) / (1 + Foreign Interest Rate)`
    - **Arbitrage Opportunity:** If this parity does not hold, a trader can borrow in one currency, convert it to another, invest at the higher interest rate, and simultaneously lock in a forward rate to convert back, guaranteeing a risk-free profit.
    - **INR Example:** If the interest rate in India is higher than in the US, the INR forward rate should trade at a discount to the spot rate (meaning you get fewer rupees per dollar in the future) to offset the higher interest earned in India. If this discount is not enough, an arbitrage opportunity exists.
    """)
    st.success("Arbitrageurs play a crucial role in ensuring market efficiency by quickly closing these price gaps, which helps keep exchange rates aligned with interest rate differentials.")

    st.subheader("B. Onshore-Offshore Arbitrage (NDF vs. Onshore Forward) 🌉")
    st.markdown("""
    - **Concept:** Exploiting price differences between the INR NDF market (offshore) and the onshore INR forward market.
    - **How it Works:** If the NDF rate for a specific tenor is significantly different from the onshore forward rate for the same tenor, traders with access to both markets can execute simultaneous buy/sell trades to profit.
    - **Impact:** This arbitrage helps to keep the onshore and offshore INR markets broadly aligned, despite capital controls.
    """)
    st.warning("While theoretically risk-free, real-world arbitrage involves transaction costs, liquidity constraints, and execution risk.")

    st.header("4. Market Sentiment & Technical Analysis for Traders 📈📉")
    st.write("Beyond fundamentals, traders rely on sentiment and technical indicators:")

    st.subheader("Market Sentiment Indicators 🧠")
    st.markdown("""
    - **Economic Data Releases:** Immediate reaction to GDP, inflation, trade balance, and FII flow data.
    - **Equity Market Performance:** Strong domestic equity markets often correlate with a stronger INR.
    - **Global Risk Appetite:** "Risk-on" environments favor emerging market currencies like INR; "Risk-off" leads to capital flight to safe havens (USD).
    - **Commitment of Traders (COT) Reports:** For major currencies, these show institutional positioning, offering clues about future moves.
    """)

    st.subheader("Technical Analysis 📐")
    st.markdown("""
    - **Chart Patterns:** Identifying trends, support/resistance levels, and reversal patterns.
    - **Moving Averages:** Used to confirm trends and identify potential entry/exit points.
    - **Relative Strength Index (RSI):** Momentum oscillator to identify overbought or oversold conditions.
    - **Bollinger Bands:** Measure volatility and identify potential price reversals.
    """)
    st.info("A comprehensive trading strategy combines fundamental analysis (macro factors), technical analysis (chart patterns), and an understanding of market sentiment.")


elif selected_section == "Data Tables":
    st.title("Comprehensive Data Tables 📊")
    st.write("Here you can find the raw data used in the analysis.")

    st.subheader("Table 1: USD/INR Exchange Rate Milestones (Selected Years, 1947 - 2025)")
    st.dataframe(df_usd_inr_milestones)
    st.download_button("Download Table 1 Data", df_usd_inr_milestones.to_csv(index=False), "usd_inr_milestones.csv", "text/csv")

    st.subheader("Table 2: Key Macroeconomic Indicators Summary (2000/01 - 2007/08)")
    st.dataframe(df_macro_2000_2008)
    st.download_button("Download Table 2 Data", df_macro_2000_2008.to_csv(index=False), "macro_2000_2008.csv", "text/csv")

    st.subheader("Table 3: Key Macroeconomic Indicators Summary (2019/20 - 2025/26 Est/Proj)")
    st.dataframe(df_macro_2019_2026)
    st.download_button("Download Table 3 Data", df_macro_2019_2026.to_csv(index=False), "macro_2019_2026.csv", "text/csv")

    st.subheader("Table 4: Historical INR Exchange Rate Against Major Currencies (Annual Average)")
    st.dataframe(df_historical_inr_major_currencies)
    st.download_button("Download Table 4 Data", df_historical_inr_major_currencies.to_csv(index=False), "historical_inr_major_currencies.csv", "text/csv")

    st.subheader("Table 5: India's Fiscal Deficit as % of GDP (FY2013-FY2026 Projections)")
    st.dataframe(df_fiscal_deficit)
    st.download_button("Download Table 5 Data", df_fiscal_deficit.to_csv(index=False), "fiscal_deficit.csv", "text/csv")

    st.subheader("Table 6: India's Trade Balance and Key Components (FY2022-23 to FY2025 Projections)")
    st.dataframe(df_trade_balance)
    st.download_button("Download Table 6 Data", df_trade_balance.to_csv(index=False), "trade_balance.csv", "text/csv")

    st.subheader("Recent FII Data ")
    st.dataframe(df_simulated_fii)
    # st.caption("Note: This data is simulated for demonstration purposes. For genuine, real-time FII data, refer to official sources like NSDL (National Securities Depository Limited) or SEBI (Securities and Exchange Board of India) websites, or subscribe to financial data providers.")
    # st.download_button("Download Simulated FII Data", df_simulated_fii.to_csv(index=False), "simulated_fii.csv", "text/csv")


elif selected_section == "Conclusion":
    st.title("Conclusion ✅")

    st.header("Summary of Key Drivers 🔑")
    st.write("""
    The trajectory of the USD/INR exchange rate has been shaped by India's evolving economic structure, domestic policy choices, and global economic forces.
    From fixed pegs to a managed float and inflation targeting, India's framework has matured.
    Global crises and domestic events have consistently tested India's resilience, with the RBI playing a crucial role in managing volatility and accumulating reserves.
    """)

    st.header("Evolution of India's External Sector 🌐")
    st.write("""
    India's external sector transformed from a closed, aid-dependent economy to one with significant FDI and FII inflows.
    The massive accumulation of foreign exchange reserves, particularly since the early 2000s, has been critical in enhancing resilience to external shocks.
    """)

    st.header("Concluding Thoughts 💡")
    st.write("""
    The long-term trend of INR depreciation reflects historical inflation differentials and productivity gaps.
    Policymakers face a complex balancing act between high growth, price stability, and exchange rate management.
    Looking ahead, India's robust growth outlook, moderating inflation, and manageable CAD suggest relative INR stability.
    Continued focus on prudent fiscal management, effective inflation control, attracting stable long-term capital, and structural reforms will be crucial.
    """)
    st.markdown("---")
    st.subheader("Thank You")
