import os
import glob
import time
import logging
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from bokeh.plotting import figure
from bokeh.models import HoverTool
from st_aggrid import AgGrid, GridOptionsBuilder

# --- Optional ICE (xlwings) imports (only used when fetching or computing dates) ---
try:
    import xlwings as xw
except Exception:
    xw = None

# =====================
# Page Configuration
# =====================
st.set_page_config(
    page_title="Tail Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================
# CONFIG
# =====================
DATA_DIR = r"C:/Top tails daily run data"  # Excel files live here
BASE_DIR = r"C:/Users/x01489120/Downloads"  # ICE CSV output (history/latest)
XLL_PATH = r"C:/Program Files/Barclays Capital/ICE Excel ToolKit/Barclays.ICE.ExcelAddIn64.xll"

# Tail report IDs provided by Aditya
REPORT_IDS = {
    "DVaR": 20455915,
    "SVaR": 20455936,
}
# Lags: 1 = COB, 2 = Prev COB
LAG_COB = 1
LAG_PREV = 2

# =====================
# LOGGING
# =====================
LOG_FILE = os.path.join(BASE_DIR, "ice_report_fetch.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, mode="a"), logging.StreamHandler()],
)

# =====================
# UTILS
# =====================

def extract_date_from_filename(filename: str):
    """Extract date like 06_Jun_2025 from Tail_analysis_auto_06_Jun_2025.xlsx."""
    try:
        name = os.path.basename(filename).replace(".xlsx", "")
        parts = name.split("_")
        date_str = "_".join(parts[-3:])  # '06_Jun_2025'
        return datetime.strptime(date_str, "%d_%b_%Y")
    except Exception:
        return None


def get_latest_excel_file():
    if not os.path.isdir(DATA_DIR):
        return None
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".xlsx") and f.startswith("Tail_analysis_auto_")]
    if not files:
        return None
    files_with_dates = [(f, extract_date_from_filename(f)) for f in files]
    files_with_dates = [t for t in files_with_dates if t[1] is not None]
    if not files_with_dates:
        return None
    files_sorted = sorted(files_with_dates, key=lambda x: x[1], reverse=True)
    return os.path.join(DATA_DIR, files_sorted[0][0])


def previous_business_day(d: datetime, n: int = 1) -> datetime:
    # Simple Mon-Fri business day logic (no holidays). If you want London holidays, we can add a calendar.
    return np.busday_offset(d.date(), -n, roll='backward').astype('datetime64[D]').astype(datetime)


# =====================
# CORE AGG LOGIC (case‑sensitive columns)
# =====================
# Expected columns: 'Var Type', 'Node', 'Asset class', 'currency', 'sensitivity_type', 'load_code', 'pnl_vector<N>'

def aggregate_vectors(df: pd.DataFrame, max_vector: int) -> pd.DataFrame:
    df = df[df['Node'].isin([10, 22194, 1373254])].copy()
    df['Asset class'] = df['Node'].map({10: 'FX', 22194: 'Rates', 1373254: 'EM Macro'})

    rows = []
    for i in range(1, max_vector + 1):
        vcol = f"pnl_vector{i}"
        if vcol not in df.columns:
            continue
        fx_sum = df.loc[df['Asset class'] == 'FX', vcol].sum()
        rates_sum = df.loc[df['Asset class'] == 'Rates', vcol].sum()
        em_sum = df.loc[df['Asset class'] == 'EM Macro', vcol].sum()
        macro = fx_sum + rates_sum + em_sum
        rows.append([i, vcol, fx_sum, rates_sum, em_sum, macro])

    return pd.DataFrame(rows, columns=['rank', 'pnl_vector', 'FX', 'Rates', 'EM Macro', 'Macro'])


def create_top_20_comparison(COB_df: pd.DataFrame, Prev_df: pd.DataFrame) -> pd.DataFrame:
    neg = COB_df.nsmallest(20, 'Macro')
    pos = COB_df.nlargest(20, 'Macro')
    combined = pd.concat([neg, pos], ignore_index=True)
    combined['COB Rank'] = list(range(1, 21)) + list(range(260, 240, -1))

    prev_map = Prev_df.set_index('pnl_vector')
    combined['Prev COB Macro'] = combined['pnl_vector'].map(prev_map['Macro'])
    combined['Prev COB FX'] = combined['pnl_vector'].map(prev_map['FX'])
    combined['Prev COB Rates'] = combined['pnl_vector'].map(prev_map['Rates'])
    combined['Prev COB EM Macro'] = combined['pnl_vector'].map(prev_map['EM Macro'])
    combined['Prev COB P&L Vector No'] = combined['pnl_vector'].map(prev_map['rank'])

    combined['Diff Macro'] = combined['Macro'] - combined['Prev COB Macro']
    combined['Diff FX'] = combined['FX'] - combined['Prev COB FX']
    combined['Diff Rates'] = combined['Rates'] - combined['Prev COB Rates']
    combined['Diff EM Macro'] = combined['EM Macro'] - combined['Prev COB EM Macro']
    return combined


def create_top_changes(COB_df: pd.DataFrame, Prev_df: pd.DataFrame) -> pd.DataFrame:
    merged = COB_df.merge(Prev_df, on='pnl_vector', suffixes=('_cob', '_prev'))
    merged['Diff'] = merged['Macro_cob'] - merged['Macro_prev']
    top_neg = merged.nsmallest(20, 'Diff')
    top_pos = merged.nlargest(20, 'Diff')
    final = pd.concat([top_neg, top_pos], ignore_index=True)
    final = final.rename(columns={
        'rank_cob': 'COB Rank', 'rank_prev': 'Prev COB Rank',
        'Macro_cob': 'COB Macro', 'Macro_prev': 'Prev COB Macro',
        'FX_cob': 'COB FX', 'Rates_cob': 'COB Rates', 'EM Macro_cob': 'COB EM Macro',
        'FX_prev': 'Prev FX', 'Rates_prev': 'Prev Rates', 'EM Macro_prev': 'Prev EM Macro'
    })
    return final


# =====================
# DATA LOADERS
# =====================
@st.cache_data(show_spinner=False)
def load_from_excel(filepath: str):
    xls = pd.ExcelFile(filepath)
    DVaR_COB_raw = xls.parse('DVaR_COB')
    DVaR_Prev_raw = xls.parse('DVaR_Prev_COB')
    SVaR_COB_raw = xls.parse('SVaR_COB')
    SVaR_Prev_raw = xls.parse('SVaR_Prev_COB')

    DVaR_COB_df = aggregate_vectors(DVaR_COB_raw, 521)
    DVaR_Prev_COB_df = aggregate_vectors(DVaR_Prev_raw, 521)
    SVaR_COB_df = aggregate_vectors(SVaR_COB_raw, 260)
    SVaR_Prev_COB_df = aggregate_vectors(SVaR_Prev_raw, 260)

    return build_outputs(DVaR_COB_df, DVaR_Prev_COB_df, SVaR_COB_df, SVaR_Prev_COB_df)


@st.cache_data(show_spinner=False)
def load_from_ice_latest():
    latest_dir = os.path.join(BASE_DIR, "latest")
    paths = {
        'DVaR_COB': os.path.join(latest_dir, 'DVaR_COB.csv'),
        'DVaR_Prev_COB': os.path.join(latest_dir, 'DVaR_PrevCOB.csv'),
        'SVaR_COB': os.path.join(latest_dir, 'SVaR_COB.csv'),
        'SVaR_Prev_COB': os.path.join(latest_dir, 'SVaR_PrevCOB.csv'),
    }
    for key, p in paths.items():
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing ICE latest output: {p}")

    DVaR_COB_raw = pd.read_csv(paths['DVaR_COB'])
    DVaR_Prev_raw = pd.read_csv(paths['DVaR_Prev_COB'])
    SVaR_COB_raw = pd.read_csv(paths['SVaR_COB'])
    SVaR_Prev_raw = pd.read_csv(paths['SVaR_Prev_COB'])

    DVaR_COB_df = aggregate_vectors(DVaR_COB_raw, 521)
    DVaR_Prev_COB_df = aggregate_vectors(DVaR_Prev_raw, 521)
    SVaR_COB_df = aggregate_vectors(SVaR_COB_raw, 260)
    SVaR_Prev_COB_df = aggregate_vectors(SVaR_Prev_raw, 260)

    return build_outputs(DVaR_COB_df, DVaR_Prev_COB_df, SVaR_COB_df, SVaR_Prev_COB_df)


# =====================
# OUTPUT BUILDER
# =====================

def build_outputs(DVaR_COB_df, DVaR_Prev_COB_df, SVaR_COB_df, SVaR_Prev_COB_df):
    return {
        'DVaR_COB_df': DVaR_COB_df,
        'DVaR_Prev_COB_df': DVaR_Prev_COB_df,
        'SVaR_COB_df': SVaR_COB_df,
        'SVaR_Prev_COB_df': SVaR_Prev_COB_df,
        'DVaR_top_20_comparison_df': create_top_20_comparison(DVaR_COB_df, DVaR_Prev_COB_df),
        'SVaR_top_20_comparison_df': create_top_20_comparison(SVaR_COB_df, SVaR_Prev_COB_df),
        'DVaR_top_changes_df': create_top_changes(DVaR_COB_df, DVaR_Prev_COB_df),
        'SVaR_top_changes_df': create_top_changes(SVaR_COB_df, SVaR_Prev_COB_df)
    }


# =====================
# ICE FETCH & DATES
# =====================

def _ensure_ice_dirs():
    latest_dir = os.path.join(BASE_DIR, "latest")
    hist_dir = os.path.join(BASE_DIR, "history", datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(latest_dir, exist_ok=True)
    os.makedirs(hist_dir, exist_ok=True)
    return latest_dir, hist_dir


def fetch_tail_report(var_type: str, lag: int):
    if xw is None:
        raise RuntimeError("xlwings not available in this environment.")
    report_id = REPORT_IDS.get(var_type)
    if not report_id:
        raise ValueError(f"Missing report_id for {var_type}")

    latest_dir, hist_dir = _ensure_ice_dirs()
    app = xw.App(visible=False, add_book=False)
    try:
        app.api.RegisterXLL(XLL_PATH)
        arr = app.api.Run("Ice_Report_Legacy", report_id, "*", lag)
        data = [list(row) for row in arr]
        headers, *rows = data
        df = pd.DataFrame(rows, columns=headers)

        tag = 'COB' if lag == LAG_COB else 'PrevCOB'
        out_name = f"{var_type}_{tag}.csv"
        latest_csv = os.path.join(latest_dir, out_name)
        hist_csv = os.path.join(hist_dir, out_name)
        df.to_csv(latest_csv, index=False)
        df.to_csv(hist_csv, index=False)
        logging.info(f"Saved {var_type} lag={lag} → {latest_csv}")
        return latest_csv
    finally:
        try:
            app.kill()
        except Exception:
            pass


def fetch_all_via_ice():
    paths = {}
    for var in ("DVaR", "SVaR"):
        for lag in (LAG_COB, LAG_PREV):
            try:
                paths[(var, lag)] = fetch_tail_report(var, lag)
                time.sleep(0.1)
            except Exception as e:
                logging.error(f"Failed {var} lag={lag}: {e}")
    return paths


def get_cob_dates(use_ice: bool, source_excel_path: str | None) -> tuple[datetime | None, datetime | None]:
    """Return (COB_date, PrevCOB_date).
    - In ICE mode: evaluate Excel formula =FODate_AddBusDays(TODAY(),-1,"Ldn") and -2 for Prev.
    - In Excel mode: parse from filename and compute previous business day.
    """
    if use_ice and xw is not None:
        app = xw.App(visible=False, add_book=True)
        try:
            # Try both the correct and (historically seen) misspelled function names
            sheet = app.books.add().sheets[0]
            tried = ["FODate_AddBusDays", "FODate_AddBusDasy"]
            cob_dt = None
            prev_dt = None
            for fname in tried:
                try:
                    sheet.range("A1").formula = f"={fname}(TODAY(),-1,\"Ldn\")"
                    sheet.range("A2").formula = f"={fname}(TODAY(),-2,\"Ldn\")"
                    cob_dt = sheet.range("A1").value
                    prev_dt = sheet.range("A2").value
                    if cob_dt and prev_dt:
                        break
                except Exception:
                    continue
            # Normalize to datetime
            cob_dt = pd.to_datetime(cob_dt).to_pydatetime() if cob_dt else None
            prev_dt = pd.to_datetime(prev_dt).to_pydatetime() if prev_dt else None
            return cob_dt, prev_dt
        finally:
            try:
                app.kill()
            except Exception:
                pass
    # Excel file path mode
    if source_excel_path:
        cob = extract_date_from_filename(os.path.basename(source_excel_path))
        if cob is not None:
            prev = previous_business_day(cob, 1)
            return cob, prev
    return None, None


# =====================
# UI
# =====================

st.title("📈 Tail Risk Dashboard")

st.sidebar.header("Data Source")
use_ice = st.sidebar.toggle("Use ICE latest CSVs (xlwings)", value=False)
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("Fetch latest via ICE"):
        try:
            out_paths = fetch_all_via_ice()
            st.success("Fetched via ICE. Latest CSVs updated.")
            if out_paths:
                st.caption("\n".join(f"✓ {k}: {v}" for k, v in out_paths.items()))
        except Exception as e:
            st.error(f"ICE fetch failed: {e}")
with col2:
    debug_mode = st.checkbox("Debug mode")

# Load data
if use_ice:
    try:
        data = load_from_ice_latest()
        source_label = "ICE latest CSVs"
        cob_date, prev_date = get_cob_dates(True, None)
    except Exception as e:
        st.error(f"Failed to load ICE latest CSVs: {e}")
        st.stop()
else:
    file_path = get_latest_excel_file()
    if not file_path:
        st.error("No valid Excel files found in directory.")
        st.stop()
    st.success(f"Loaded Excel file: {os.path.basename(file_path)}")
    data = load_from_excel(file_path)
    source_label = "Excel file"
    cob_date, prev_date = get_cob_dates(False, file_path)

st.caption(f"Source: {source_label}")
if cob_date:
    st.info(f"COB Date: **{cob_date.strftime('%d %b %Y')}** | Prev COB: **{(prev_date or previous_business_day(cob_date,1)).strftime('%d %b %Y')}** (London)")

st.sidebar.header("View Options")
tab_choice = st.sidebar.radio("Choose View", [
    "DVaR Comparison", "SVaR Comparison",
    "DVaR Changes", "SVaR Changes",
    "Time Series"
])


def show_aggrid(df: pd.DataFrame):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(filterable=True, sortable=True, resizable=True)
    grid_options = gb.build()
    AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=False, fit_columns_on_grid_load=True)


if tab_choice == "DVaR Comparison":
    st.header("📊 DVaR Top 20 Comparison")
    show_aggrid(data['DVaR_top_20_comparison_df'])

elif tab_choice == "SVaR Comparison":
    st.header("📊 SVaR Top 20 Comparison")
    show_aggrid(data['SVaR_top_20_comparison_df'])

elif tab_choice == "DVaR Changes":
    st.header("🔺 DVaR Top Changes")
    show_aggrid(data['DVaR_top_changes_df'])

elif tab_choice == "SVaR Changes":
    st.header("🔺 SVaR Top Changes")
    show_aggrid(data['SVaR_top_changes_df'])

elif tab_choice == "Time Series":
    st.header("📉 Macro Time Series Comparison")
    var_choice = st.selectbox("Select Type", ["DVaR", "SVaR"])
    cob_df = data[f"{var_choice}_COB_df"]
    prev_df = data[f"{var_choice}_Prev_COB_df"]

    p = figure(title=f"{var_choice} Macro: COB vs Prev COB", x_axis_label='Vector Rank', y_axis_label='Macro Value', width=1000, height=420)
    p.line(cob_df['rank'], cob_df['Macro'], legend_label='COB', line_width=2)
    p.line(prev_df['rank'], prev_df['Macro'], legend_label='Prev COB', line_width=2)
    p.legend.location = 'top_left'
    p.add_tools(HoverTool(tooltips=[("Rank", "@x"), ("Value", "@y")]))
    st.bokeh_chart(p, use_container_width=True)

if debug_mode:
    st.subheader("🔧 Debug")
    if not use_ice:
        st.write("Excel directory:", DATA_DIR)
        st.write("Detected Excel files:", [f for f in os.listdir(DATA_DIR) if f.endswith('.xlsx')])
    else:
        latest = os.path.join(BASE_DIR, 'latest')
        st.write("ICE latest dir:", latest)
        st.write("Present files:", os.listdir(latest) if os.path.isdir(latest) else "<missing>")
    for k, v in data.items():
        st.write(f"### {k}")
        st.dataframe(v.head())
