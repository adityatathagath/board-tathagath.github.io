import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import re
from datetime import datetime, timedelta
from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource, NumeralTickFormatter
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# --- Page Configuration and Styling ---
st.set_page_config(
    page_title="Tail Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for AgGrid theming and alignment
st.markdown("""
<style>
    .stApp {
        background-color: #F0F2F6;
    }
    .ag-header-cell-label {
        justify-content: center;
    }
</style>
""", unsafe_allow_html=True)

# --- MOCK DATA GENERATION ---
def create_mock_excel_file(path, file_date):
    """Generates a mock Excel file with the specified structure."""
    if os.path.exists(path):
        return

    writer = pd.ExcelWriter(path, engine='openpyxl')
    nodes = {10: "FX", 22194: "Rates", 1373254: "EM Macro"}
    sensitivity_types = ["IR Delta SABR", "EQ Delta", "IR Delta Normal Backbone", "FX Vega"]
    currencies = ["USD", "EUR", "GBP", "AUD", "JPY"]
    
    dvar_vectors = range(261, 522)
    svar_vectors = range(1, 261)

    for sheet_name_base in ["DVaR_COB", "DVaR_Prev_COB"]:
        df_data = []
        for i in range(300): 
            node = np.random.choice(list(nodes.keys()))
            df_data.append({
                "Var Type": "DVaR", "Node": node, "Asset class": nodes[node], "currency": np.random.choice(currencies),
                "sensitivity_type": np.random.choice(sensitivity_types), "load_code": f"LC{np.random.randint(1000, 9999)}",
                **{f"pnl_vector{v}{'[T-2]' if 'Prev' in sheet_name_base else ''}": np.random.uniform(-5e5, 5e5) for v in dvar_vectors}
            })
        df = pd.DataFrame(df_data)
        date_header_row = [np.nan] * 6 + list(pd.to_datetime([file_date - timedelta(days=i*2) for i in range(len(dvar_vectors))]).strftime('%d-%m-%Y'))
        header_df = pd.DataFrame([date_header_row])
        header_df.to_excel(writer, sheet_name=sheet_name_base, index=False, header=False)
        df.to_excel(writer, sheet_name=sheet_name_base, index=False, startrow=1)

    for sheet_name_base in ["SVaR_COB", "SVaR_Prev_COB"]:
        df_data = []
        for i in range(300):
            node = np.random.choice(list(nodes.keys()))
            df_data.append({
                "Var Type": "SVaR", "Node": node, "Asset class": nodes[node], "currency": np.random.choice(currencies),
                "sensitivity_type": np.random.choice(sensitivity_types), "load_code": f"LC{np.random.randint(1000, 9999)}",
                **{f"pnl_vector{v}{'[T-2]' if 'Prev' in sheet_name_base else ''}": np.random.uniform(-1e6, 1e6) for v in svar_vectors}
            })
        df = pd.DataFrame(df_data)
        date_header_row = [np.nan] * 6 + list(pd.to_datetime([file_date - timedelta(days=i*3) for i in range(len(svar_vectors))]).strftime('%d-%m-%Y'))
        header_df = pd.DataFrame([date_header_row])
        header_df.to_excel(writer, sheet_name=sheet_name_base, index=False, header=False)
        df.to_excel(writer, sheet_name=sheet_name_base, index=False, startrow=1)

    writer.close()
    st.info(f"Created a mock data file: {os.path.basename(path)}")


# --- Data Loading and Processing ---
@st.cache_data
def process_data_file(file_path):
    """
    Main function to process the selected Excel file. Reads all sheets, performs
    aggregations, and creates all final dataframes exactly as specified.
    """
    def read_sheet(sheet_name):
        try:
            date_map_df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=1, header=None)
            raw_df = pd.read_excel(file_path, sheet_name=sheet_name, header=1)
            date_map = dict(zip(raw_df.columns, date_map_df.iloc[0]))
            pnl_cols = [col for col in raw_df.columns if 'pnl_vector' in str(col)]
            return raw_df, date_map, pnl_cols
        except Exception as e:
            st.error(f"Could not read sheet '{sheet_name}'. Error: {e}")
            return None, None, None

    def create_summary_df(sheet_name, node_map={10: "FX", 22194: "Rates", 1373254: "EM Macro"}):
        raw_df, date_map, pnl_vectors = read_sheet(sheet_name)
        if raw_df is None: return None
        
        long_df = pd.melt(raw_df, id_vars=["Node"], value_vars=pnl_vectors, var_name="Pnl_Vector", value_name="Value")
        long_df["Asset_Class"] = long_df["Node"].map(node_map)
        summary = long_df.groupby(["Pnl_Vector", "Asset_Class"])["Value"].sum().reset_index()
        pivot_df = summary.pivot_table(index="Pnl_Vector", columns="Asset_Class", values="Value").fillna(0)
        
        pivot_df["Macro"] = pivot_df.sum(axis=1)
        pivot_df["Date"] = pivot_df.index.map(date_map)
        pivot_df["P&L Vector No"] = pivot_df.index.str.extract(r'(\d+)').astype(int)
        
        # FIX: Add the requested internal rank column based on Macro value
        pivot_df['Macro Rank'] = pivot_df['Macro'].rank(method='first', ascending=True).astype(int)
        
        pivot_df.drop_duplicates(subset=['P&L Vector No'], keep='first', inplace=True)
        return pivot_df.reset_index()

    dvar_cob_df = create_summary_df("DVaR_COB")
    dvar_prev_cob_df = create_summary_df("DVaR_Prev_COB")
    svar_cob_df = create_summary_df("SVaR_COB")
    svar_prev_cob_df = create_summary_df("SVaR_Prev_COB")

    if any(df is None for df in [dvar_cob_df, dvar_prev_cob_df, svar_cob_df, svar_prev_cob_df]): return None

    def create_top_20_comparison_df(cob_df, prev_cob_df):
        top_20_neg = cob_df.sort_values("Macro", ascending=True).head(20).copy()
        top_20_pos = cob_df.sort_values("Macro", ascending=False).head(20).copy()
        
        top_20_neg['COB Rank'] = range(1, len(top_20_neg) + 1)
        top_20_pos['COB Rank'] = range(260, 260 - len(top_20_pos), -1)

        combined_top = pd.concat([top_20_neg, top_20_pos])
        comparison = pd.merge(combined_top, prev_cob_df, on="P&L Vector No", how="left", suffixes=('_COB', '_PrevCOB'))
        
        for col in ["Macro", "Rates", "FX", "EM Macro"]:
            if f'{col}_COB' in comparison.columns and f'{col}_PrevCOB' in comparison.columns:
                 comparison[f'Diff_{col}'] = comparison[f'{col}_COB'] - comparison[f'{col}_PrevCOB']
        
        final_df = pd.DataFrame()
        final_df["COB Rank"] = comparison["COB Rank"]
        final_df["COB P&L Vector No"] = comparison["P&L Vector No"]
        final_df["Date"] = comparison["Date_COB"]
        final_df["Macro"] = comparison.get("Macro_COB")
        final_df["Rates"] = comparison.get("Rates_COB")
        final_df["FX"] = comparison.get("FX_COB")
        final_df["EM Macro"] = comparison.get("EM Macro_COB")
        final_df["Prev Cob Rank"] = comparison.get("Macro Rank_PrevCOB")
        final_df["Prev COB P&L Vector No"] = comparison.get("P&L Vector No")
        final_df["Macro "] = comparison.get("Macro_PrevCOB")
        final_df["Rates "] = comparison.get("Rates_PrevCOB")
        final_df["FX "] = comparison.get("FX_PrevCOB")
        final_df["EM Macro "] = comparison.get("EM Macro_PrevCOB")
        final_df["Macro  "] = comparison.get("Diff_Macro")
        final_df["Rates  "] = comparison.get("Diff_Rates")
        final_df["FX  "] = comparison.get("Diff_FX")
        final_df["EM Macro  "] = comparison.get("Diff_EM Macro")

        return final_df.sort_values(by="COB Rank").reset_index(drop=True)

    def create_top_changes_df(cob_df, prev_cob_df):
        merged_df = pd.merge(cob_df, prev_cob_df, on="P&L Vector No", how="inner", suffixes=('_COB', '_PrevCOB'))
        if merged_df.empty: return pd.DataFrame() 
        
        merged_df['Diff'] = merged_df['Macro_COB'] - merged_df['Macro_PrevCOB']
        
        top_20_neg_changes = merged_df.sort_values("Diff", ascending=True).head(20)
        top_20_pos_changes = merged_df.sort_values("Diff", ascending=False).head(20)
        
        combined_changes = pd.concat([top_20_neg_changes, top_20_pos_changes])
        if combined_changes.empty: return pd.DataFrame()

        combined_changes['Final_Rank'] = list(range(1, len(top_20_neg_changes) + 1)) + list(range(1, len(top_20_pos_changes) + 1))
        
        final_df = pd.DataFrame()
        final_df["Rank"] = combined_changes["Final_Rank"]
        final_df["COB P&L Vector No"] = combined_changes["P&L Vector No"]
        final_df["Prev COB P&L Vector No"] = combined_changes["P&L Vector No"]
        final_df["Date"] = combined_changes["Date_COB"]
        final_df["Macro COB"] = combined_changes["Macro_COB"]
        final_df["Macro PrevCob"] = combined_changes["Macro_PrevCOB"]
        final_df["Diff"] = combined_changes["Diff"]
        final_df["Rates"] = combined_changes["Rates_COB"]
        final_df["FX"] = combined_changes["FX_COB"]
        final_df["EM Macro"] = combined_changes["EM Macro_COB"]
        
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
def display_aggrid(df):
    """Configures and displays a dataframe with Streamlit AgGrid."""
    if df is None or df.empty:
        st.warning("Data not available or no matching records found.")
        return

    gb = GridOptionsBuilder.from_dataframe(df)
    
    # Enable sorting, filtering, and resizable columns
    gb.configure_default_column(
        resizable=True,
        filterable=True,
        sortable=True,
        enableValue=True,
        enableRowGroup=False,
        enablePivot=False,
    )
    
    # Custom JS for cell styling (red for negative, green for positive)
    cells_renderer = JsCode("""
    class GreenRedCellRenderer {
        init(params) {
            this.eGui = document.createElement('div');
            if (params.value < 0) {
                this.eGui.innerHTML = `<span style="color: red; font-weight: bold;">${params.value.toLocaleString()}</span>`;
            } else if (params.value > 0) {
                this.eGui.innerHTML = `<span style="color: green; font-weight: bold;">${params.value.toLocaleString()}</span>`;
            } else {
                 this.eGui.innerHTML = params.value.toLocaleString();
            }
        }
        getGui() {
            return this.eGui;
        }
    }
    """)

    # Apply formatting and styling
    for col in df.columns:
        if "Diff" in col or col.strip() != col: # Identify difference columns
             gb.configure_column(col, cellRenderer=cells_renderer, type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=0)
        elif df[col].dtype == 'float64' or df[col].dtype == 'int64':
             if col not in ["COB Rank", "COB P&L Vector No", "Prev COB P&L Vector No", "Rank", "Prev Cob Rank", "Macro Rank"]:
                gb.configure_column(col, type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=0)

    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=40)
    gb.configure_grid_options(domLayout='normal')
    gridOptions = gb.build()

    AgGrid(
        df,
        gridOptions=gridOptions,
        height=600,
        width='100%',
        theme='streamlit',
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True
    )

def create_bokeh_chart(cob_df, prev_cob_df, title):
    if cob_df is None or prev_cob_df is None or cob_df.empty or prev_cob_df.empty:
        p = figure(height=400, title=f"{title} - No Data Available", sizing_mode="stretch_width")
        return p
    source_df = pd.merge(cob_df, prev_cob_df, on='P&L Vector No', how="inner", suffixes=('_COB', '_PrevCOB'))
    if source_df.empty:
        p = figure(height=400, title=f"{title} - No Matching P&L Vectors to Compare", sizing_mode="stretch_width")
        return p
    source_df['Date_COB_dt'] = pd.to_datetime(source_df['Date_COB'], errors='coerce')
    source = ColumnDataSource(source_df)
    p = figure(height=400, x_axis_label="P&L Vector No", y_axis_label="Value", title=title, sizing_mode="stretch_width", tools="pan,wheel_zoom,box_zoom,reset,save")
    p.yaxis.formatter = NumeralTickFormatter(format="0,0.00a")
    p.line(x='P&L Vector No', y='Macro_COB', source=source, legend_label="Macro COB", color="dodgerblue", width=2.5, alpha=0.8)
    p.circle(x='P&L Vector No', y='Macro_COB', source=source, legend_label="Macro COB", color="dodgerblue", size=5)
    p.line(x='P&L Vector No', y='Macro_PrevCOB', source=source, legend_label="Macro PrevCOB", color="gray", width=2, line_dash="dashed")
    hover = HoverTool(tooltips=[("P&L Vector", "@{P&L Vector No}"), ("Date", "@Date_COB_dt{%F}"), ("Macro COB", "@Macro_COB{0,0}"), ("Macro PrevCOB", "@Macro_PrevCOB{0,0}")], formatters={'@Date_COB_dt': 'datetime'})
    p.add_tools(hover)
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"
    return p

# --- MAIN APP ---
def main():
    st.title("📊 Tail Analysis Dashboard")
    st.write("""
    An interactive web application to analyze daily DVaR and SVaR tail events.
    **Installation Note:** This app requires `streamlit-aggrid`. Please install it using: `pip install streamlit-aggrid`
    """)
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
                with comparison_tab: st.subheader("Top 20 Positive & Negative DVaR Macro Values"); display_aggrid(data['dvar_comparison'])
                with changes_tab: st.subheader("Top 20 Largest DVaR Macro Changes (COB vs PrevCOB)"); display_aggrid(data['dvar_changes'])
            with svar_tab:
                st.header("SVaR Analysis")
                chart_tab, comparison_tab, changes_tab = st.tabs(["📈 Time Series Chart", "🏆 Top 20 Comparison", "🔄 Top Changes"])
                with chart_tab: st.bokeh_chart(create_bokeh_chart(data["svar_cob"], data["svar_prev_cob"], "SVaR: Macro COB vs. Macro PrevCOB"), use_container_width=True)
                with comparison_tab: st.subheader("Top 20 Positive & Negative SVaR Macro Values"); display_aggrid(data['svar_comparison'])
                with changes_tab: st.subheader("Top 20 Largest SVaR Macro Changes (COB vs PrevCOB)"); display_aggrid(data['svar_changes'])
    else: st.error("No data files could be found or created. Please check the folder path.")

if __name__ == "__main__":
    main()
