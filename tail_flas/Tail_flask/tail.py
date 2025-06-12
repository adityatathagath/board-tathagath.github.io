import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import re
from datetime import datetime, timedelta
from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource, NumeralTickFormatter

# --- Page Configuration and Styling ---
st.set_page_config(
    page_title="Tail Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling the dataframes and improving the visual appeal
st.markdown("""
<style>
    /* Main app styling */
    .stApp {
        background-color: #F0F2F6;
    }
    /* Dataframe styling */
    .dataframe-container {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    .dataframe-container table {
        width: 100%;
        border-collapse: collapse;
    }
    .dataframe-container th {
        background-color: #0068C9;
        color: white;
        text-align: left;
        padding: 12px 15px;
        font-weight: bold;
    }
    .dataframe-container td {
        padding: 10px 15px;
        border-bottom: 1px solid #ddd;
    }
    .dataframe-container tbody tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .dataframe-container tbody tr:hover {
        background-color: #f1f1f1;
    }
    /* Cell styling for numbers */
    .positive-change {
        color: #28a745 !important;
        font-weight: bold;
    }
    .negative-change {
        color: #dc3545 !important;
        font-weight: bold;
    }
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
    }
    /* Metric cards styling */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-left: 5px solid #0068C9;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 2px 4px 0 rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- MOCK DATA GENERATION ---
# This function creates a realistic mock file if no real file is found.
def create_mock_excel_file(path, file_date):
    """Generates a mock Excel file with the specified structure."""
    if os.path.exists(path):
        return # Don't overwrite if it exists

    writer = pd.ExcelWriter(path, engine='openpyxl')
    nodes = {10: "FX", 22194: "Rates", 1373254: "EM Macro"}
    sensitivity_types = ["IR Delta SABR", "EQ Delta", "IR Delta Normal Backbone", "FX Vega"]
    currencies = ["USD", "EUR", "GBP", "AUD", "JPY"]
    
    dvar_vectors = range(261, 522)
    svar_vectors = range(1, 261)

    # --- Generate Data for DVaR sheets ---
    dvar_dates = pd.to_datetime([file_date - timedelta(days=i*2) for i in range(len(dvar_vectors))]).strftime('%d-%m-%Y')
    for sheet_name_base in ["DVaR_COB", "DVaR_Prev_COB"]:
        df_data = []
        for i in range(300): 
            node = np.random.choice(list(nodes.keys()))
            df_data.append({
                "Var Type": "DVaR",
                "Node": node,
                "Asset class": nodes[node],
                "currency": np.random.choice(currencies),
                "sensitivity_type": np.random.choice(sensitivity_types),
                "load_code": f"LC{np.random.randint(1000, 9999)}",
                **{f"pnl_vector{v}{'[T-2]' if 'Prev' in sheet_name_base else ''}": np.random.uniform(-5e5, 5e5) for v in dvar_vectors}
            })
        df = pd.DataFrame(df_data)
        # Create header with empty placeholders to mimic the real file structure
        date_header_row = [np.nan] * 6 + list(dvar_dates)
        header_df = pd.DataFrame([date_header_row])
        header_df.to_excel(writer, sheet_name=sheet_name_base, index=False, header=False)
        df.to_excel(writer, sheet_name=sheet_name_base, index=False, startrow=1)

    # --- Generate Data for SVaR sheets ---
    svar_dates = pd.to_datetime([file_date - timedelta(days=i*3) for i in range(len(svar_vectors))]).strftime('%d-%m-%Y')
    for sheet_name_base in ["SVaR_COB", "SVaR_Prev_COB"]:
        df_data = []
        for i in range(300):
            node = np.random.choice(list(nodes.keys()))
            df_data.append({
                "Var Type": "SVaR",
                "Node": node,
                "Asset class": nodes[node],
                "currency": np.random.choice(currencies),
                "sensitivity_type": np.random.choice(sensitivity_types),
                "load_code": f"LC{np.random.randint(1000, 9999)}",
                **{f"pnl_vector{v}{'[T-2]' if 'Prev' in sheet_name_base else ''}": np.random.uniform(-1e6, 1e6) for v in svar_vectors}
            })
        df = pd.DataFrame(df_data)
        # Create header with empty placeholders
        date_header_row = [np.nan] * 6 + list(svar_dates)
        header_df = pd.DataFrame([date_header_row])
        header_df.to_excel(writer, sheet_name=sheet_name_base, index=False, header=False)
        df.to_excel(writer, sheet_name=sheet_name_base, index=False, startrow=1)

    writer.close()
    st.info(f"Created a mock data file: {os.path.basename(path)}")


# --- Data Loading and Processing ---
@st.cache_data
def process_data_file(file_path):
    """
    Main function to process the selected Excel file.
    Reads all sheets, performs aggregations, and creates all final dataframes.
    """
    # Helper function to read a single sheet correctly
    def read_sheet(sheet_name):
        try:
            date_map_df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=1, header=None)
            raw_df = pd.read_excel(file_path, sheet_name=sheet_name, header=1)
            
            # FIX: Create a direct mapping from the final column names to the values in the first row (dates)
            # This correctly handles the offset empty cells by aligning the two series.
            date_map = dict(zip(raw_df.columns, date_map_df.iloc[0]))
            
            id_cols = ['Var Type', 'Node', 'Asset class', 'currency', 'sensitivity_type', 'load_code']
            pnl_cols = [col for col in raw_df.columns if 'pnl_vector' in str(col)]
            
            final_cols = id_cols + pnl_cols
            raw_df = raw_df[[col for col in final_cols if col in raw_df.columns]]

            return raw_df, date_map, id_cols, pnl_cols
        except Exception as e:
            st.error(f"Could not read sheet '{sheet_name}' in '{os.path.basename(file_path)}'. Error: {e}")
            return None, None, None, None

    # Helper function to create the summary dataframe for a sheet
    def create_summary_df(sheet_name, node_map={10: "FX", 22194: "Rates", 1373254: "EM Macro"}):
        raw_df, date_map, id_vars, pnl_vectors = read_sheet(sheet_name)
        if raw_df is None: return None
        
        long_df = pd.melt(raw_df, id_vars=["Node"], value_vars=pnl_vectors, var_name="Pnl_Vector", value_name="Value")
        
        long_df["Asset_Class"] = long_df["Node"].map(node_map)
        summary = long_df.groupby(["Pnl_Vector", "Asset_Class"])["Value"].sum().reset_index()
        pivot_df = summary.pivot_table(index="Pnl_Vector", columns="Asset_Class", values="Value").fillna(0)
        
        pivot_df["Macro"] = pivot_df.sum(axis=1)
        pivot_df["Date"] = pivot_df.index.map(date_map)
        pivot_df["Rank"] = pivot_df.index.str.extract(r'(\d+)').astype(int)
        
        pivot_df.drop_duplicates(subset=['Rank'], keep='first', inplace=True)
        return pivot_df.reset_index()

    dvar_cob_df = create_summary_df("DVaR_COB")
    dvar_prev_cob_df = create_summary_df("DVaR_Prev_COB")
    svar_cob_df = create_summary_df("SVaR_COB")
    svar_prev_cob_df = create_summary_df("SVaR_Prev_COB")

    if any(df is None for df in [dvar_cob_df, dvar_prev_cob_df, svar_cob_df, svar_prev_cob_df]): return None

    # Helper function to create the Top 20 Comparison dataframe
    def create_top_20_comparison_df(cob_df, prev_cob_df):
        top_20_neg = cob_df.sort_values("Macro", ascending=True).head(20).copy()
        top_20_pos = cob_df.sort_values("Macro", ascending=False).head(20).copy()
        
        top_20_neg['COB Rank'] = range(1, len(top_20_neg) + 1)
        top_20_pos['COB Rank'] = range(260, 260 - len(top_20_pos), -1)

        combined_top = pd.concat([top_20_neg, top_20_pos], ignore_index=True)
        comparison = pd.merge(combined_top, prev_cob_df, on="Rank", how="left", suffixes=('_COB', '_PrevCOB'))
        
        all_asset_classes = ["Macro", "Rates", "FX", "EM Macro"]
        for col in all_asset_classes:
            if f'{col}_COB' in comparison.columns and f'{col}_PrevCOB' in comparison.columns:
                 comparison[f'{col}_Diff'] = comparison[f'{col}_COB'] - comparison[f'{col}_PrevCOB']
        
        final_cols_map = {
            "COB Rank": 'COB Rank', "COB P&L Vector No": 'Rank', "Date": 'Date_COB',
            "Macro": 'Macro_COB', "Rates": 'Rates_COB', "FX": 'FX_COB', "EM Macro": 'EM Macro_COB',
            "Prev COB P&L Vector No": 'Rank', 
            "Prev Macro": 'Macro_PrevCOB', "Prev Rates": 'Rates_PrevCOB', "Prev FX": 'FX_PrevCOB', "Prev EM Macro": 'EM Macro_PrevCOB',
            "Diff Macro": 'Macro_Diff', "Diff Rates": 'Rates_Diff', "Diff FX": 'FX_Diff', "Diff EM Macro": 'EM Macro_Diff'
        }
        final_df = pd.DataFrame()
        for new_col, old_col in final_cols_map.items():
            if old_col in comparison: final_df[new_col] = comparison[old_col]
            else: final_df[new_col] = np.nan
        return final_df.sort_values(by="COB Rank").reset_index(drop=True)

    # Helper function to create the Top Changes dataframe
    def create_top_changes_df(cob_df, prev_cob_df):
        merged_df = pd.merge(cob_df, prev_cob_df, on="Rank", how="inner", suffixes=('_COB', '_PrevCOB'))
        if merged_df.empty: return pd.DataFrame() 
        
        merged_df['Diff'] = merged_df['Macro_COB'] - merged_df['Macro_PrevCOB']
        
        top_20_neg_changes = merged_df.sort_values("Diff", ascending=True).head(20)
        top_20_pos_changes = merged_df.sort_values("Diff", ascending=False).head(20)
        
        combined_changes = pd.concat([top_20_neg_changes, top_20_pos_changes])
        if combined_changes.empty: return pd.DataFrame()

        combined_changes['Rank_Final'] = list(range(1, len(top_20_neg_changes) + 1)) + list(range(1, len(top_20_pos_changes) + 1))
        
        final_cols_map = {
            "Rank": 'Rank_Final', "COB P&L Vector No": 'Rank', "Prev COB P&L Vector No": 'Rank', 
            "Date": 'Date_COB', "Macro COB": 'Macro_COB', "Macro PrevCob": 'Macro_PrevCOB', "Diff": 'Diff',
            "Rates": 'Rates_COB', "FX": 'FX_COB', "EM Macro": 'EM Macro_COB'
        }
        final_df = pd.DataFrame()
        for new_col, old_col in final_cols_map.items():
             if old_col in combined_changes: final_df[new_col] = combined_changes[old_col]
             else: final_df[new_col] = np.nan
        return final_df

    data_dict = {
        "dvar_cob": dvar_cob_df, "svar_cob": svar_cob_df,
        "dvar_prev_cob": dvar_prev_cob_df, "svar_prev_cob": svar_prev_cob_df
    }
    data_dict["dvar_comparison"] = create_top_20_comparison_df(dvar_cob_df, dvar_prev_cob_df)
    data_dict["svar_comparison"] = create_top_20_comparison_df(svar_cob_df, svar_prev_cob_df)
    data_dict["dvar_changes"] = create_top_changes_df(dvar_cob_df, dvar_prev_cob_df)
    data_dict["svar_changes"] = create_top_changes_df(svar_cob_df, svar_prev_cob_df)

    return data_dict

# --- UI Rendering Functions ---
def format_df_for_display(df):
    if df is None or df.empty: return "<p>Data not available or no matching records found.</p>"
    formatted_df = df.copy().fillna('N/A')
    for col in formatted_df.columns:
        is_diff_col = 'Diff' in col
        if any(isinstance(x, (int, float)) for x in formatted_df[col] if pd.notna(x) and x != 'N/A') and col not in ["COB Rank", "COB P&L Vector No", "Prev COB P&L Vector No", "Rank"]:
            formatted_df[col] = formatted_df[col].apply(
                lambda x: f'<span class="positive-change">{x:,.0f}</span>' if is_diff_col and isinstance(x, (int, float)) and x > 0 else (f'<span class="negative-change">{x:,.0f}</span>' if is_diff_col and isinstance(x, (int, float)) and x < 0 else (f'{x:,.0f}' if isinstance(x, (int, float)) else x))
            )
    return f"<div class='dataframe-container'>{formatted_df.to_html(escape=False, index=False)}</div>"

def create_bokeh_chart(cob_df, prev_cob_df, title):
    if cob_df.empty or prev_cob_df.empty:
        p = figure(height=400, title=f"{title} - No Data Available", sizing_mode="stretch_width")
        return p
    source_df = pd.merge(cob_df, prev_cob_df, on='Rank', how="inner", suffixes=('_COB', '_PrevCOB'))
    if source_df.empty:
        p = figure(height=400, title=f"{title} - No Matching P&L Vectors", sizing_mode="stretch_width")
        return p
    source_df['Date_COB_dt'] = pd.to_datetime(source_df['Date_COB'], errors='coerce')
    source = ColumnDataSource(source_df)
    p = figure(height=400, x_axis_label="P&L Vector No", y_axis_label="Value", title=title, sizing_mode="stretch_width", tools="pan,wheel_zoom,box_zoom,reset,save")
    p.yaxis.formatter = NumeralTickFormatter(format="0,0.00a")
    p.line(x='Rank', y='Macro_COB', source=source, legend_label="Macro COB", color="dodgerblue", width=2.5, alpha=0.8)
    p.circle(x='Rank', y='Macro_COB', source=source, legend_label="Macro COB", color="dodgerblue", size=5)
    p.line(x='Rank', y='Macro_PrevCOB', source=source, legend_label="Macro PrevCOB", color="gray", width=2, line_dash="dashed")
    hover = HoverTool(tooltips=[("P&L Vector", "@Rank"), ("Date", "@Date_COB_dt{%F}"), ("Macro COB", "@Macro_COB{0,0}"), ("Macro PrevCOB", "@Macro_PrevCOB{0,0}")], formatters={'@Date_COB_dt': 'datetime'})
    p.add_tools(hover)
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"
    return p

# --- MAIN APP ---
def main():
    st.title("📊 Tail Analysis Dashboard")
    st.write("An interactive web application to analyze daily DVaR and SVaR tail events.")
    DATA_FOLDER_PATH = r"C:\Top tails daily run data"
    
    st.sidebar.title("Controls")
    st.sidebar.markdown("---")
    debug_mode = st.sidebar.checkbox("Show Debug Info")
    
    if not os.path.exists(DATA_FOLDER_PATH):
        st.warning(f"Folder not found: '{DATA_FOLDER_PATH}'. Creating it now.")
        os.makedirs(DATA_FOLDER_PATH)
        
    files = glob.glob(os.path.join(DATA_FOLDER_PATH, "Tail_analysis_auto_*.xlsx"))
    if not files:
        st.sidebar.warning("No data files found. A mock file will be created for demonstration.")
        today = datetime.now()
        mock_file_name = f"mock_Tail_analysis_auto_{today.strftime('%d_%b_%Y')}.xlsx"
        mock_file_path = os.path.join(DATA_FOLDER_PATH, mock_file_name)
        create_mock_excel_file(mock_file_path, today)
        files = glob.glob(os.path.join(DATA_FOLDER_PATH, "Tail_analysis_auto_*.xlsx"))
        
    file_map = {os.path.basename(f): f for f in files}
    selected_file_name = st.sidebar.selectbox("Select a Report File", sorted(file_map.keys(), reverse=True))

    if selected_file_name:
        selected_file_path = file_map[selected_file_name]
        st.sidebar.success(f"Loaded: **{selected_file_name}**")
        data = process_data_file(selected_file_path)

        if data:
            if debug_mode:
                st.subheader("🐛 Debug Information")
                for name, df in data.items():
                    if df is not None:
                        st.markdown(f"**DataFrame: `{name}`** (Shape: {df.shape})")
                        st.dataframe(df.head())
                    else:
                        st.markdown(f"**DataFrame: `{name}`** (is None)")
                st.markdown("---")

            dvar_tab, svar_tab = st.tabs(["DVaR Analysis", "SVaR Analysis"])
            with dvar_tab:
                st.header("DVaR Analysis")
                chart_tab, comparison_tab, changes_tab = st.tabs(["📈 Time Series Chart", "🏆 Top 20 Comparison", "🔄 Top Changes"])
                with chart_tab: st.bokeh_chart(create_bokeh_chart(data["dvar_cob"], data["dvar_prev_cob"], "DVaR: Macro COB vs. Macro PrevCOB"), use_container_width=True)
                with comparison_tab: st.subheader("Top 20 Positive & Negative DVaR Macro Values"); st.markdown(format_df_for_display(data['dvar_comparison']), unsafe_allow_html=True)
                with changes_tab: st.subheader("Top 20 Largest DVaR Macro Changes (COB vs PrevCOB)"); st.markdown(format_df_for_display(data['dvar_changes']), unsafe_allow_html=True)
            with svar_tab:
                st.header("SVaR Analysis")
                chart_tab, comparison_tab, changes_tab = st.tabs(["📈 Time Series Chart", "🏆 Top 20 Comparison", "🔄 Top Changes"])
                with chart_tab: st.bokeh_chart(create_bokeh_chart(data["svar_cob"], data["svar_prev_cob"], "SVaR: Macro COB vs. Macro PrevCOB"), use_container_width=True)
                with comparison_tab: st.subheader("Top 20 Positive & Negative SVaR Macro Values"); st.markdown(format_df_for_display(data['svar_comparison']), unsafe_allow_html=True)
                with changes_tab: st.subheader("Top 20 Largest SVaR Macro Changes (COB vs PrevCOB)"); st.markdown(format_df_for_display(data['svar_changes']), unsafe_allow_html=True)
    else: st.error("No data files could be found or created. Please check the folder path.")

if __name__ == "__main__":
    main()
