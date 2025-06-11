import streamlit as st
import pandas as pd
import numpy as np
import altair as alt # Still importing for general Altair.Axis.format string use, though not plotting directly
from bokeh.plotting import figure, show 
from bokeh.models import ColumnDataSource, NumeralTickFormatter, DatetimeTickFormatter, HoverTool
from bokeh.embed import json_item # Not directly used for st.bokeh_chart, but useful for debugging Bokeh plots
from bokeh.palettes import Category10, Category20 
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

# --- Configuration (UPDATE THESE BASED ON YOUR DATA) ---
CURRENT_DAY_SHEET_NAME = "DVaR_COB"
PREVIOUS_DAY_SHEET_NAME = "DVaR_Prev_COB"
SVAR_COB_SHEET_NAME = "SVaR_COB"
SVAR_PREV_COB_SHEET_NAME = "SVaR_Prev_COB"

FX_DVAR_NODE = 10
RATES_DVAR_NODE = 22194
EM_MACRO_DVAR_NODE = 137354

DVAR_PNL_VECTOR_START = 261
DVAR_PNL_VECTOR_END = 520 

SVAR_PNL_VECTOR_START = 1
SVAR_PNL_VECTOR_END = 260

# Define Barclays-specific color palette for Bokeh plots and AgGrid styling
BARCLAYS_COLOR_PALETTE = [
    '#0076B6',  # Primary Blue (used for trends, main elements)
    '#2188D7',  # Lighter Blue
    '#004B7F',  # Darker Blue
    '#6A6C6E',  # Medium Grey
    '#A0A3A6',  # Light Grey
    '#FF4B4B',  # Red for negative changes (index 5) - used in JS
    '#28a745',  # Green for positive changes (index 6) - used in JS
]

# --- Streamlit Application Setup ---
st.set_page_config(layout="wide", page_title="Market Risk DVaR Tail Analysis")

st.title("📊 Comprehensive Market Risk DVaR Tail Analysis")

st.write(
    """
    Upload your Excel workbook (`Tail_analysis_auto.xlsx`) to perform detailed DVaR and SVaR tail analysis
    for FX, Rates, and EM Macro.
    """
)

# --- Sidebar for File Uploader and Debug Toggle ---
with st.sidebar:
    st.header("Upload Data & Debug Options")
    uploaded_file = st.file_uploader("Choose your Excel file (Tail_analysis_auto.xlsx)", type="xlsx")
    DEBUG_MODE = st.checkbox("Show Debug Info (for troubleshooting)", value=False)


# --- Helper Functions (Core Logic) ---

@st.cache_data(show_spinner="Loading Excel data... This may take a moment for large files.")
def load_data(file_buffer, debug_mode):
    """
    Loads data from the specified sheets in the Excel workbook.
    Handles date extraction from the first row and sets proper headers.
    Ensures 'Node' column is numeric.
    Includes debug output (prints to console if debug_mode).
    """
    data_frames = {}
    date_mappings = {}

    sheets_to_load = [
        CURRENT_DAY_SHEET_NAME,
        PREVIOUS_DAY_SHEET_NAME,
        SVAR_COB_SHEET_NAME,
        SVAR_PREV_COB_SHEET_NAME
    ]

    for sheet_name in sheets_to_load:
        if debug_mode:
            print(f"DEBUG: Loading Sheet: {sheet_name}") # Use print for console output in Streamlit
        try:
            # Using pd.ExcelFile context manager for efficient multi-sheet reading
            with pd.ExcelFile(file_buffer) as xls:
                # Read the first two rows to get dates and column names
                df_temp = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=2)
                
                if df_temp.empty:
                    print(f"ERROR: Sheet '{sheet_name}' is empty or could not be read.")
                    return None, None # Indicate error
                if len(df_temp) < 2:
                    print(f"ERROR: Sheet '{sheet_name}' has fewer than 2 rows (expected dates in row 1, headers in row 2). Found {len(df_temp)} rows.")
                    return None, None # Indicate error

                dates_row = df_temp.iloc[0]
                column_names_row = df_temp.iloc[1]

                # Read the actual data, skipping the first two rows
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None, skiprows=2)
                df.columns = column_names_row # Assign the second row as column headers
                
                # Drop columns that are entirely NaN after header adjustments (e.g., empty columns in Excel)
                df = df.dropna(axis=1, how='all')

                if 'Node' in df.columns:
                    df['Node'] = pd.to_numeric(df['Node'], errors='coerce').astype('Int64')
                else:
                    if debug_mode:
                        print(f"DEBUG: 'Node' column not found in sheet '{sheet_name}'. This might cause issues downstream.")

                pnl_date_map = {}
                for col_idx, col_name in enumerate(column_names_row):
                    if pd.isna(col_name):
                        continue
                    if str(col_name).startswith('pnl_vector') or ('[T-2]' in str(col_name) and 'pnl_vector' in str(col_name)): 
                        if col_idx < len(dates_row):
                            date_val = dates_row.iloc[col_idx]
                            if isinstance(date_val, (int, float)):
                                try:
                                    pnl_date_map[str(col_name)] = pd.to_datetime(date_val, unit='D', origin='1899-12-30')
                                except:
                                    pnl_date_map[str(col_name)] = pd.NaT
                            else:
                                pnl_date_map[str(col_name)] = pd.to_datetime(date_val, errors='coerce')
                
                data_frames[sheet_name] = df
                date_mappings[sheet_name] = pnl_date_map

        except Exception as e:
            print(f"ERROR: Failed to process sheet '{sheet_name}': {e}. Check file format.")
            return None, None # Indicate error
    
    return data_frames, date_mappings


@st.cache_data(show_spinner="Calculating DVaR/SVaR tails...")
def calculate_var_tails(df, pnl_date_map, sheet_type="current", var_type_filter="DVaR", 
                        dvar_pnl_vector_start=None, dvar_pnl_vector_end=None, 
                        svar_pnl_vector_start=None, svar_pnl_vector_end=None, debug_mode=False):
    """
    Calculates VaR tails (DVaR or SVaR) for FX, Rates, EM Macro, and Macro.
    Adds a 'Sheet_Type' column for differentiation.
    Includes debug output.
    """
    if debug_mode:
        print(f"DEBUG: Calculating VaR Tails for {sheet_type} ({var_type_filter})")
        print("DEBUG: Input DataFrame Head:")
        print(df.head())

    current_pnl_vector_start = None
    current_pnl_vector_end = None

    if var_type_filter == "DVaR":
        current_pnl_vector_start = dvar_pnl_vector_start
        current_pnl_vector_end = dvar_pnl_vector_end
    elif var_type_filter == "SVaR":
        current_pnl_vector_start = svar_pnl_vector_start
        current_pnl_vector_end = svar_pnl_vector_end
    
    if current_pnl_vector_start is None or current_pnl_vector_end is None:
        print(f"ERROR: PnL vector range not defined for {var_type_filter}.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    id_vars = ['Var Type', 'Node', 'Asset class', 'currency', 'sensitivity_type', 'load_code']
    pnl_vector_cols = [col for col in df.columns if str(col).startswith('pnl_vector') or ('[T-2]' in str(col) and 'pnl_vector' in str(col))]

    valid_pnl_cols = []
    for col in pnl_vector_cols:
        col_str = str(col)
        is_previous_cob_vector = '[T-2]' in col_str
        numeric_part_str = ''.join(filter(str.isdigit, col_str.split('[T-2]')[0]))
        
        if not numeric_part_str.isdigit():
            continue
        
        vector_number = int(numeric_part_str)

        if sheet_type == "current":
            if not is_previous_cob_vector and current_pnl_vector_start <= vector_number <= current_pnl_vector_end:
                valid_pnl_cols.append(col)
        elif sheet_type == "previous":
            if is_previous_cob_vector and current_pnl_vector_start <= vector_number <= current_pnl_vector_end:
                valid_pnl_cols.append(col)
    
    if debug_mode:
        print(f"DEBUG: Valid PnL Columns for current config ({sheet_type}, {var_type_filter}): {valid_pnl_cols}")


    id_vars_present = [col for col in id_vars if col in df.columns]
    
    if not valid_pnl_cols:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_melted = df.melt(id_vars=id_vars_present,
                         value_vars=valid_pnl_cols,
                         var_name='Pnl_Vector_Name',
                         value_name='Value')
    
    def extract_pnl_rank(pnl_vector_name):
        # Ensure pnl_vector_name is a string before attempting string operations
        pnl_vector_name_str = str(pnl_vector_name) 
        
        if debug_mode:
            print(f"DEBUG: extract_pnl_rank - Processing: '{pnl_vector_name_str}'")

        if '[T-2]' in pnl_vector_name_str:
            name_without_suffix = pnl_vector_name_str.split('[T-2]')[0]
        else:
            name_without_suffix = pnl_vector_name_str
        
        numeric_part = ''.join(filter(str.isdigit, name_without_suffix))
        
        if debug_mode:
            print(f"DEBUG: extract_pnl_rank - Numeric part: '{numeric_part}'")

        try:
            return int(numeric_part) if numeric_part else np.nan
        except ValueError:
            print(f"ERROR: Could not convert '{numeric_part}' to int for Pnl_Vector_Name '{pnl_vector_name_str}'")
            return np.nan
    
    df_melted['Pnl_Vector_Rank'] = df_melted['Pnl_Vector_Name'].apply(extract_pnl_rank)
    df_melted['Pnl_Vector_Rank'] = df_melted['Pnl_Vector_Rank'].astype('Int64')

    df_melted['Date'] = df_melted['Pnl_Vector_Name'].map(pnl_date_map)
    df_melted['Date'] = pd.to_datetime(df_melted['Date'], errors='coerce')
    df_melted = df_melted.dropna(subset=['Date'])

    df_filtered_var_type = df_melted[df_melted['Var Type'] == var_type_filter].copy()
    
    asset_classes = ['FX', 'Rates', 'EM Macro']
    asset_var_dfs = {}
    
    node_mapping = {
        'FX': FX_DVAR_NODE, 
        'Rates': RATES_DVAR_NODE, 
        'EM Macro': EM_MACRO_DVAR_NODE
    }

    for ac in asset_classes:
        node_val_for_filter = node_mapping.get(ac, FX_DVAR_NODE)
        filtered_df = df_filtered_var_type[
            (df_filtered_var_type['Asset class'] == ac) &
            (df_filtered_var_type['Node'] == node_val_for_filter)
        ]
        if not filtered_df.empty:
            asset_var_dfs[ac] = filtered_df.groupby(['Date', 'Pnl_Vector_Name', 'Pnl_Vector_Rank'])['Value'].sum().reset_index(name=f'{ac.replace(" ", "_")}_{var_type_filter}_Value')
            asset_var_dfs[ac]['Sheet_Type'] = sheet_type
        else:
            asset_var_dfs[ac] = pd.DataFrame(columns=['Date', 'Pnl_Vector_Name', 'Pnl_Vector_Rank', f'{ac.replace(" ", "_")}_{var_type_filter}_Value', 'Sheet_Type'])
            
    macro_var_df = pd.DataFrame(columns=['Date', 'Pnl_Vector_Name', 'Pnl_Vector_Rank', f'Macro_{var_type_filter}_Value', 'Sheet_Type'])
    
    if 'FX' in asset_var_dfs and not asset_var_dfs['FX'].empty:
        macro_var_df = asset_var_dfs['FX']
        for ac in ['Rates', 'EM Macro']:
            if ac in asset_var_dfs and not asset_var_dfs[ac].empty:
                macro_var_df = pd.merge(macro_var_df, asset_var_dfs[ac], on=['Date', 'Pnl_Vector_Name', 'Pnl_Vector_Rank', 'Sheet_Type'], how='outer')
        
        cols_for_sum = [f'{ac.replace(" ", "_")}_{var_type_filter}_Value' for ac in asset_classes]
        for col_sum in cols_for_sum:
            if col_sum not in macro_var_df.columns:
                macro_var_df[col_sum] = 0
        
        macro_var_df[f'Macro_{var_type_filter}_Value'] = macro_var_df[cols_for_sum].sum(axis=1)
        macro_var_df = macro_var_df.sort_values('Date').reset_index(drop=True)
        macro_var_df['Sheet_Type'] = sheet_type
    
    return asset_var_dfs.get('FX', pd.DataFrame()), \
           asset_var_dfs.get('Rates', pd.DataFrame()), \
           asset_var_dfs.get('EM Macro', pd.DataFrame()), \
           macro_var_df, \
           df_filtered_var_type

# --- Visualization Functions (Bokeh) ---

def create_bokeh_line_chart(df, title, y_column, legend_title="Type", colors=BARCLAYS_COLOR_PALETTE):
    """Generates a Bokeh line chart for DVaR trends or volatility."""
    if df.empty:
        st.info(f"No data to display for {title}.")
        return

    df['Date'] = pd.to_datetime(df['Date'])
    
    p = figure(
        height=350, 
        sizing_mode="stretch_width", 
        title=title,
        x_axis_type="datetime",
        tools="pan,wheel_zoom,box_zoom,reset,save,hover",
        active_drag="pan",
        active_scroll="wheel_zoom"
    )

    # Determine unique types for coloring (e.g., 'current', 'previous')
    unique_types = df[legend_title].unique()
    
    for i, chart_type in enumerate(unique_types):
        view = ColumnDataSource(df[df[legend_title] == chart_type])
        color_index = i % len(colors) # Cycle through colors if more types than defined colors
        p.line(
            x='Date', 
            y=y_column, 
            source=view, 
            legend_label=chart_type, 
            line_color=colors[color_index],
            line_width=2
        )
        p.circle(
            x='Date', 
            y=y_column, 
            source=view, 
            size=6, 
            color=colors[color_index], 
            alpha=0.6,
            legend_label=chart_type
        )

    p.xaxis.formatter = DatetimeTickFormatter(days="%d-%m-%Y", months="%d-%m-%Y", years="%d-%m-%Y")
    p.xaxis.axis_label = "Date"
    p.yaxis.formatter = NumeralTickFormatter(format="0,0.00")
    p.yaxis.axis_label = y_column
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"

    # Define hover tooltips based on available columns
    tooltips_list = [
        ("Date", "@Date{%d-%m-%Y}"),
        (y_column, f"@{y_column}{{0,0.00}}"),
        (legend_title, f"@{legend_title}")
    ]
    if 'Pnl_Vector_Rank' in df.columns:
        tooltips_list.append(("P&L Vector Rank", "@Pnl_Vector_Rank"))
    
    p.add_tools(HoverTool(tooltips=tooltips_list, formatters={"@Date": "datetime"}))

    st.bokeh_chart(p, use_container_width=True)

def create_bokeh_stacked_area_chart(df, title, colors=BARCLAYS_COLOR_PALETTE):
    """Generates a Bokeh stacked area chart for DVaR contributions."""
    if df.empty: 
        st.info(f"No data available for {title} chart.")
        return

    df_long = df.melt(id_vars=['Date', 'Pnl_Vector_Name', 'Macro_DVaR_Value', 'Sheet_Type'],
                      value_vars=[col for col in df.columns if '_DVaR_Value' in col and col != 'Macro_DVaR_Value'],
                      var_name='Asset_Class',
                      value_name='Contribution_Value')
    
    df_long['Contribution_Percentage'] = np.where(
        (df_long['Macro_DVaR_Value'] != 0),
        (df_long['Contribution_Value'] / df_long['Macro_DVaR_Value']) * 100,
        np.where(df_long['Contribution_Value'] == 0, 0, np.nan)
    )
    
    df_long = df_long.dropna(subset=['Contribution_Percentage'])

    if df_long.empty:
        st.info(f"No valid contribution data after filtering for {title}.")
        return

    df_long['Date_str'] = df_long['Date'].dt.strftime('%d-%m-%Y')
    
    # Map internal asset class names to display names if desired
    display_asset_names = {
        'FX_DVaR_Value': 'FX',
        'Rates_DVaR_Value': 'Rates',
        'EM_Macro_DVaR_Value': 'EM Macro'
    }
    df_long['Display_Asset_Class'] = df_long['Asset_Class'].map(display_asset_names).fillna(df_long['Asset_Class'])

    # --- FIX: Pivot data for Bokeh varea_stack ---
    df_wide = df_long.pivot_table(index='Date', columns='Display_Asset_Class', values='Contribution_Percentage', fill_value=0).reset_index()
    
    asset_class_cols_for_stack = df_wide.columns.drop('Date').tolist()
    source_wide = ColumnDataSource(df_wide)
    
    bokeh_colors = Category10[len(asset_class_cols_for_stack)] if len(asset_class_cols_for_stack) <= 10 else Category20[len(asset_class_cols_for_stack)]

    p_stacked = figure(
        height=350, 
        sizing_mode="stretch_width", 
        title=title,
        x_axis_type="datetime",
        tools="pan,wheel_zoom,box_zoom,reset,save,hover",
        active_drag="pan",
        active_scroll="wheel_zoom"
    )
    
    p_stacked.varea_stack(
        x='Date', 
        stackers=asset_class_cols_for_stack, # Correctly pass list of columns to stack
        source=source_wide, 
        legend_label=asset_class_cols_for_stack, 
        color=bokeh_colors
    )

    p_stacked.xaxis.formatter = DatetimeTickFormatter(days="%d-%m-%Y", months="%d-%m-%Y", years="%d-%m-%Y")
    p_stacked.xaxis.axis_label = "Date"
    p_stacked.yaxis.formatter = NumeralTickFormatter(format="0.00%")
    p_stacked.yaxis.axis_label = "Percentage Contribution (%)"
    p_stacked.legend.location = "top_left"
    p_stacked.legend.click_policy = "hide"

    hover_tool = HoverTool(tooltips=[
        ("Date", "@Date{%d-%m-%Y}"),
        ("Asset Class", "$name"), # $name refers to the column name used in stackers
        ("Contribution", "@$name{0.00}%") # Use $name for the stacked value
    ], formatters={"@Date": "datetime"})
    p_stacked.add_tools(hover_tool)

    st.bokeh_chart(p_stacked, use_container_width=True)


def display_correlations_bokeh(df):
    """Calculates and displays correlation matrix for DVaR asset classes using a heatmap."""
    if df.empty:
        st.info("No data available to calculate correlations.")
        return

    df_current_day = df[df['Sheet_Type'] == 'current']
    if df_current_day.empty:
        st.info("No 'Current Day' data available for correlation calculation.")
        return

    dvar_value_cols = [col for col in df_current_day.columns if '_DVaR_Value' in col and col != 'Macro_DVaR_Value']
    
    if not dvar_value_cols:
        st.info("No individual asset class DVaR values found for correlation calculation.")
        return

    correlation_df = df_current_day[dvar_value_cols].corr()
    
    # Rename columns for display in heatmap
    display_names = {
        'FX_DVaR_Value': 'FX',
        'Rates_DVaR_Value': 'Rates',
        'EM_Macro_DVaR_Value': 'EM Macro'
    }
    correlation_df = correlation_df.rename(columns=display_names, index=display_names)

    # Prepare data for Bokeh heatmap
    assets = correlation_df.columns.tolist()
    correlations = [(x, y, correlation_df.loc[x, y]) for x in assets for y in assets]
    
    source = ColumnDataSource(pd.DataFrame(correlations, columns=['asset1', 'asset2', 'correlation']))

    p = figure(
        height=350, 
        sizing_mode="stretch_width", 
        title="DVaR Asset Class Correlations (Current Day)",
        x_range=assets, y_range=list(reversed(assets)), # Reverse y-axis for proper matrix display
        x_axis_location="above", tools="hover", toolbar_location=None,
        tooltips=[("Assets", "@asset1 - @asset2"), ("Correlation", "@correlation{0.00}")]
    )

    # Using a divergent color scale (red for -1, white for 0, green for 1)
    color_mapper = alt.Scale(domain=[-1, 1], range=[BARCLAYS_COLOR_PALETTE[5], BARCLAYS_COLOR_PALETTE[4], BARCLAYS_COLOR_PALETTE[6]], type="linear").to_json()['range']

    p.rect(x="asset1", y="asset2", width=1, height=1,
           source=source,
           line_color=None, fill_color={'field': 'correlation', 'transform': {'expr': f'color_mapper.map(correlation)'}}) # Fill color based on correlation value
    
    p.axis.fixed_bounds = True
    p.grid.grid_line_color = None
    p.axis.axis_line_color = None
    p.axis.major_tick_line_color = None
    p.xaxis.major_label_text_font_size = "10pt"
    p.yaxis.major_label_text_font_size = "10pt"
    p.xaxis.major_label_orientation = np.pi/4 # Angle labels if needed

    st.bokeh_chart(p, use_container_width=True)


def create_bokeh_sensitivity_attribution_chart(df_raw_var_type, selected_asset_class, colors=BARCLAYS_COLOR_PALETTE):
    """
    Calculates and plots VaR contribution by sensitivity type for a selected asset class using Bokeh.
    """
    if df_raw_var_type.empty:
        st.info("Raw VaR data not available for sensitivity attribution.")
        return

    node_config_key = f"{selected_asset_class.replace(' ', '_').upper()}_DVAR_NODE"
    node_value_for_filter = globals().get(node_config_key)
    
    if node_value_for_filter is None:
        st.error(f"Configuration error: Node value for '{selected_asset_class}' is not defined.")
        return

    df_filtered = df_raw_var_type[
        (df_raw_var_type['Asset class'] == selected_asset_class) &
        (df_raw_var_type['Node'] == node_value_for_filter)
    ].copy()
    
    if df_filtered.empty:
        st.info(f"No DVaR data found for '{selected_asset_class}' with Node {str(node_value_for_filter)}.")
        return

    sensitivity_contributions = df_filtered.groupby(['Date', 'Pnl_Vector_Name', 'sensitivity_type'])['Value'].sum().reset_index()
    total_dvar_by_date = sensitivity_contributions.groupby(['Date', 'Pnl_Vector_Name'])['Value'].sum().reset_index(name='Total_DVaR')
    sensitivity_contributions = pd.merge(sensitivity_contributions, total_dvar_by_date, on=['Date', 'Pnl_Vector_Name'], how='left')
    
    sensitivity_contributions['Percentage_Contribution'] = np.where(
        (sensitivity_contributions['Total_DVaR'] != 0),
        (sensitivity_contributions['Value'] / sensitivity_contributions['Total_DVaR']) * 100,
        np.where(sensitivity_contributions['Value'] == 0, 0, np.nan)
    )
    
    sensitivity_contributions.replace([np.inf, -np.inf], np.nan, inplace=True)
    sensitivity_contributions.dropna(subset=['Percentage_Contribution'], inplace=True)

    if sensitivity_contributions.empty:
        st.info(f"No valid sensitivity contribution data after filtering for {selected_asset_class}.")
        return

    top_n = st.slider(f"Show Top N Sensitivities for {selected_asset_class}", 5, 20, 10, key=f"top_n_sens_{selected_asset_class}_bokeh")
    
    avg_sens_contrib = sensitivity_contributions.groupby('sensitivity_type')['Value'].mean().nlargest(top_n).index
    
    sensitivity_contributions['Display_Sensitivity'] = sensitivity_contributions['sensitivity_type'].apply(
        lambda x: x if x in avg_sens_contrib else 'Other'
    )
    
    df_display = sensitivity_contributions.groupby(['Date', 'Pnl_Vector_Name', 'Display_Sensitivity'])['Value'].sum().reset_index()
    total_dvar_recalculated = df_display.groupby(['Date', 'Pnl_Vector_Name'])['Value'].sum().reset_index(name='Total_DVaR')
    df_display = pd.merge(df_display, total_dvar_recalculated, on=['Date', 'Pnl_Vector_Name'], how='left')
    df_display['Percentage_Contribution'] = (df_display['Value'] / df_display['Total_DVaR']) * 100
    
    df_display.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_display.dropna(subset=['Percentage_Contribution'], inplace=True)

    if df_display.empty:
        st.info(f"No displayable sensitivity contribution data after grouping for {selected_asset_class}.")
        return

    df_display['Date'] = pd.to_datetime(df_display['Date'])
    
    # Pivot for Bokeh's varea_stack
    df_wide_sensitivity = df_display.pivot_table(index='Date', columns='Display_Sensitivity', values='Percentage_Contribution', fill_value=0).reset_index()
    
    sensitivity_stack_cols = df_wide_sensitivity.columns.drop('Date').tolist()
    source_sensitivity = ColumnDataSource(df_wide_sensitivity)
    
    bokeh_colors_sens = Category10[len(sensitivity_stack_cols)] if len(sensitivity_stack_cols) <= 10 else Category20[len(sensitivity_stack_cols)]

    p = figure(
        height=350, 
        sizing_mode="stretch_width", 
        title=f"DVaR Contribution by Sensitivity Type for {selected_asset_class}",
        x_axis_type="datetime",
        tools="pan,wheel_zoom,box_zoom,reset,save,hover",
        active_drag="pan",
        active_scroll="wheel_zoom"
    )
    
    p.varea_stack(
        x='Date', 
        stackers=sensitivity_stack_cols, # Correctly pass list of columns to stack
        source=source_sensitivity, 
        legend_label=sensitivity_stack_cols, 
        color=bokeh_colors_sens
    )

    p.xaxis.formatter = DatetimeTickFormatter(days="%d-%m-%Y", months="%d-%m-%Y", years="%d-%m-%Y")
    p.xaxis.axis_label = "Date"
    p.yaxis.formatter = NumeralTickFormatter(format="0.00%")
    p.yaxis.axis_label = "Percentage Contribution (%)"
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"

    hover_tool_sens = HoverTool(tooltips=[
        ("Date", "@Date{%d-%m-%Y}"),
        ("Sensitivity Type", "$name"),
        ("Contribution", "@$name{0.00}%")
    ], formatters={"@Date": "datetime"})
    p.add_tools(hover_tool_sens)

    st.bokeh_chart(p, use_container_width=True)


def create_bokeh_svar_dvar_comparison(dvar_df, svar_df, title, colors=BARCLAYS_COLOR_PALETTE):
    """Compares Macro DVaR and Macro SVaR using Bokeh."""
    if svar_df.empty or dvar_df.empty:
        st.info("SVaR or DVaR data not available for comparison.")
        return
    
    comparison_df = pd.merge(dvar_df[['Date', 'Pnl_Vector_Name', 'Macro_DVaR_Value', 'Sheet_Type']],
                             svar_df[['Date', 'Pnl_Vector_Name', 'Macro_SVaR_Value', 'Sheet_Type']],
                             on=['Date', 'Pnl_Vector_Name', 'Sheet_Type'], how='inner')
    
    if comparison_df.empty:
        st.info("No common dates/pnl vectors found between DVaR and SVaR data for comparison.")
        return

    df_melted = comparison_df.melt(id_vars=['Date', 'Pnl_Vector_Name', 'Sheet_Type'],
                                   value_vars=['Macro_DVaR_Value', 'Macro_SVaR_Value'],
                                   var_name='VaR_Type',
                                   value_name='Value')

    df_melted['Date'] = pd.to_datetime(df_melted['Date'])
    source = ColumnDataSource(df_melted)

    p = figure(
        height=350, 
        sizing_mode="stretch_width", 
        title=title,
        x_axis_type="datetime",
        tools="pan,wheel_zoom,box_zoom,reset,save,hover",
        active_drag="pan",
        active_scroll="wheel_zoom"
    )

    va_types = df_melted['VaR_Type'].unique()
    type_colors = {va_type: colors[i % len(colors)] for i, va_type in enumerate(va_types)}

    p.line(
        x='Date', 
        y='Value', 
        source=source, 
        legend_field='VaR_Type', 
        line_color=alt.Color('VaR_Type', scale=alt.Scale(range=list(type_colors.values()))).to_json()['range'], 
        line_width=2
    )
    p.circle(
        x='Date', 
        y='Value', 
        source=source, 
        size=6, 
        color=alt.Color('VaR_Type', scale=alt.Scale(range=list(type_colors.values()))).to_json()['range'], 
        alpha=0.6,
        legend_field='VaR_Type'
    )

    p.xaxis.formatter = DatetimeTickFormatter(days="%d-%m-%Y", months="%d-%m-%Y", years="%d-%m-%Y")
    p.xaxis.axis_label = "Date"
    p.yaxis.formatter = NumeralTickFormatter(format="0,0.00")
    p.yaxis.axis_label = "VaR Value"
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"

    p.hover.tooltips = [
        ("Date", "@Date{%d-%m-%Y}"),
        ("VaR Type", "@VaR_Type"),
        ("Value", "@Value{0,0.00}")
    ]
    p.hover.formatters = {"@Date": "datetime"}

    st.bokeh_chart(p, use_container_width=True)


def display_top_bottom_tails_table(macro_dvar_curr, macro_dvar_prev, fx_dvar_curr, fx_dvar_prev, rates_dvar_curr, rates_dvar_prev, em_macro_dvar_curr, em_macro_dvar_prev, debug_mode):
    """
    Generates and displays the top 20 positive and negative Macro DVaR tails table using AgGrid.
    """
    st.header("🏆 Top/Bottom DVaR Tails Analysis")
    st.markdown("Identify the top 20 positive and negative Macro DVaR tails and their corresponding asset class contributions, showing change from previous COB.")

    common_merge_keys_pnl_vector = ['Date', 'Pnl_Vector_Name', 'Pnl_Vector_Rank']
    common_merge_keys_date_only = ['Date'] # Key for merging daily aggregated data

    # --- Step 1: Identify Top/Bottom Tails from Current COB Macro DVaR ---
    if macro_dvar_curr.empty:
        st.info("No current Macro DVaR data to identify top/bottom tails.")
        return # Exit function if no data

    # Get top 20 positive and negative Macro DVaR values from current COB
    top_20_positive_curr = macro_dvar_curr.nlargest(min(20, len(macro_dvar_curr)), 'Macro_DVaR_Value', keep='all').copy()
    top_20_negative_curr = macro_dvar_curr.nsmallest(min(20, len(macro_dvar_curr)), 'Macro_DVaR_Value', keep='all').copy()

    # Combine these identified top/bottom tails into a single DataFrame for processing
    # This DataFrame will be the base for our final table, ensuring we only analyze these specific tails
    all_current_tails_base = pd.concat([top_20_positive_curr, top_20_negative_curr]).drop_duplicates(subset=common_merge_keys_pnl_vector).reset_index(drop=True)
    
    # Rename Macro_DVaR_Value to Macro_DVaR_Value_Current immediately
    all_current_tails_base.rename(columns={'Macro_DVaR_Value': 'Macro_DVaR_Value_Current'}, inplace=True)

    if debug_mode:
        print("DEBUG: Top/Bottom Tails - All Current Tails (Base for Merge):")
        print(all_current_tails_base.head())


    # --- Step 2: Prepare lookup DataFrames for all *current* asset class values (specific PnL vector level) ---
    # These will be merged onto all_current_tails_base
    current_asset_specific_lookups = [
        (fx_dvar_curr, 'FX_DVaR_Value', 'FX_DVaR_Value_Current'),
        (rates_dvar_curr, 'Rates_DVaR_Value', 'Rates_DVaR_Value_Current'),
        (em_macro_dvar_curr, 'EM_Macro_DVaR_Value', 'EM_Macro_DVaR_Value_Current')
    ]
    for df, original_val_col, new_val_col in current_asset_specific_lookups:
        if not df.empty and original_val_col in df.columns:
            temp_lookup_df = df[common_merge_keys_pnl_vector + [original_val_col]].copy()
            temp_lookup_df.rename(columns={original_val_col: new_val_col}, inplace=True)
            all_current_tails_base = pd.merge(all_current_tails_base, temp_lookup_df, on=common_merge_keys_pnl_vector, how='left')
        else:
            # Ensure the column exists even if lookup is empty
            all_current_tails_base[new_val_col] = np.nan
    
    if debug_mode:
        print("DEBUG: Top/Bottom Tails - all_current_tails_base after adding all current asset values (head):")
        print(all_current_tails_base.head())
        print("DEBUG: Top/Bottom Tails - all_current_tails_base columns after current asset values:", all_current_tails_base.columns.tolist())


    # --- Step 3: Prepare lookup DataFrames for all *previous* asset class values (aggregated by Date only) ---
    # These will be merged onto the main DataFrame based on 'Date' only
    
    # Macro Previous Daily Total
    prev_macro_daily_total = pd.DataFrame()
    if not macro_dvar_prev.empty and 'Macro_DVaR_Value' in macro_dvar_prev.columns:
        prev_macro_daily_total = macro_dvar_prev.groupby('Date')['Macro_DVaR_Value'].sum().reset_index().rename(columns={'Macro_DVaR_Value': 'Macro_DVaR_Value_Previous'})
    
    # FX Previous Daily Total
    prev_fx_daily_total = pd.DataFrame()
    if not fx_dvar_prev.empty and 'FX_DVaR_Value' in fx_dvar_prev.columns:
        prev_fx_daily_total = fx_dvar_prev.groupby('Date')['FX_DVaR_Value'].sum().reset_index().rename(columns={'FX_DVaR_Value': 'FX_DVaR_Value_Previous'})
    
    # Rates Previous Daily Total
    prev_rates_daily_total = pd.DataFrame()
    if not rates_dvar_prev.empty and 'Rates_DVaR_Value' in rates_dvar_prev.columns:
        prev_rates_daily_total = rates_dvar_prev.groupby('Date')['Rates_DVaR_Value'].sum().reset_index().rename(columns={'Rates_DVaR_Value': 'Rates_DVaR_Value_Previous'})
    
    # EM Macro Previous Daily Total
    prev_em_macro_daily_total = pd.DataFrame()
    if not em_macro_dvar_prev.empty and 'EM_Macro_DVaR_Value' in em_macro_dvar_prev.columns:
        prev_em_macro_daily_total = em_macro_dvar_prev.groupby('Date')['EM_Macro_DVaR_Value'].sum().reset_index().rename(columns={'EM_Macro_DVaR_Value': 'EM_Macro_DVaR_Value_Previous'})

    if debug_mode:
        print("DEBUG: Top/Bottom Tails - Aggregated Daily Totals (Previous Macro Head):")
        print(prev_macro_daily_total.head())
        print("DEBUG: Top/Bottom Tails - Aggregated Daily Totals (Previous FX Head):")
        print(prev_fx_daily_total.head())


    # --- Step 4: Perform the final merge of identified tails with aggregated previous values ---
    # Merge Macro Previous Daily Total
    final_display_df = pd.merge(all_current_tails_base, prev_macro_daily_total, on='Date', how='left', suffixes=('_Current', '_Previous'))
    
    # Merge other Previous Daily Totals
    final_display_df = pd.merge(final_display_df, prev_fx_daily_total, on='Date', how='left') # New col name: FX_DVaR_Value_Previous
    final_display_df = pd.merge(final_display_df, prev_rates_daily_total, on='Date', how='left') # New col name: Rates_DVaR_Value_Previous
    final_display_df = pd.merge(final_display_df, prev_em_macro_daily_total, on='Date', how='left') # New col name: EM_Macro_DVaR_Value_Previous

    if debug_mode:
        print("DEBUG: Top/Bottom Tails - Final Display DF after all merges (before fillna and change calculation):")
        print(final_display_df.head())
        print("DEBUG: Top/Bottom Tails - Final Display DF columns after all merges:", final_display_df.columns.tolist())


    # --- Step 5: Fill NaNs and Calculate Changes ---
    # Identify all 'Current' and 'Previous' DVaR value columns in the final_display_df
    value_cols_to_fill = [col for col in final_display_df.columns if '_DVaR_Value_Current' in col or '_DVaR_Value_Previous' in col]
    
    # Fill NaNs with 0 for all relevant value columns
    final_display_df[value_cols_to_fill] = final_display_df[value_cols_to_fill].fillna(0)

    # Calculate Change columns
    asset_prefixes = ['Macro', 'FX', 'Rates', 'EM_Macro']
    for prefix in asset_prefixes:
        current_col_name = f'{prefix}_DVaR_Value_Current'
        previous_col_name = f'{prefix}_DVaR_Value_Previous'
        change_col_name = f'{prefix}_DVaR_Change'
        
        # Calculate change; columns are guaranteed to exist and be filled with 0
        final_display_df[change_col_name] = final_display_df[current_col_name] - final_display_df[previous_col_name]

    # Final sort and drop duplicates in case the initial concat introduced any
    final_display_df.drop_duplicates(subset=common_merge_keys_pnl_vector, inplace=True)
    final_display_df.sort_values(by=['Date', 'Pnl_Vector_Rank'], inplace=True, ignore_index=True)

    if debug_mode:
        print("DEBUG: Top/Bottom Tails - Final Display DF ready for AgGrid (final columns):")
        print(final_display_df.head())
        print(final_display_df.columns.tolist())


    # --- Step 6: Prepare data for AgGrid display (re-select top/bottom from final_display_df) ---
    top_20_positive_aggrid = final_display_df.nlargest(min(20, len(final_display_df)), 'Macro_DVaR_Value_Current', keep='all').copy()
    top_20_negative_aggrid = final_display_df.nsmallest(min(20, len(final_display_df)), 'Macro_DVaR_Value_Current', keep='all').copy()


    columnDefs = [
        {"field": "Date", "headerName": "Date", "type": ["dateColumnFilter", "customDateTimeFormat"], "custom_format_string": 'dd-MM-yyyy'},
        {"field": "Pnl_Vector_Name", "headerName": "P&L Vector"},
    ]

    change_cell_style_jscode = JsCode(f"""
    function(params) {{
        if (typeof params.value === 'number') {{
            if (params.value < 0) {{
                return {{backgroundColor: '{BARCLAYS_COLOR_PALETTE[5]}', color: 'black'}};
            }} else if (params.value > 0) {{
                return {{backgroundColor: '{BARCLAYS_COLOR_PALETTE[6]}', color: 'black'}};
            }}
        }}
        return null;
    }}
    """)
    
    number_formatter_jscode = JsCode("""
    function(params) { 
        if (typeof params.value === 'number') { 
            return (params.value / 1000000).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) + 'M'; 
        } 
        return params.value; 
    }
    """)

    asset_prefixes = ['Macro', 'FX', 'Rates', 'EM_Macro']
    for prefix in asset_prefixes:
        # Use the correct column names for AgGrid display from final_display_df
        columnDefs.append({"field": f"{prefix}_DVaR_Value_Current", "headerName": f"{prefix} Current (M)", "type": ["numericColumn", "numberColumnFilter"], "valueFormatter": number_formatter_jscode, "cellStyle": change_cell_style_jscode})
        columnDefs.append({"field": f"{prefix}_DVaR_Value_Previous", "headerName": f"{prefix} Previous (M)", "type": ["numericColumn", "numberColumnFilter"], "valueFormatter": number_formatter_jscode, "cellStyle": change_cell_style_jscode})
        columnDefs.append({"field": f"{prefix}_DVaR_Change", "headerName": f"{prefix} Change (M)", "type": ["numericColumn", "numberColumnFilter"], "cellStyle": change_cell_style_jscode, "valueFormatter": number_formatter_jscode})

    gb = GridOptionsBuilder.from_dataframe(pd.DataFrame(columns=[col['field'] for col in columnDefs])) 
    gb.configure_columns(columnDefs)
    gb.configure_grid_options(domLayout='autoHeight', suppressColumnVirtualization=True) 
    gridOptions = gb.build()

    st.subheader("Top 20 Positive Macro DVaR Tails (Current COB)")
    if not top_20_positive_aggrid.empty:
        top_20_positive_aggrid_display = top_20_positive_aggrid.copy()
        top_20_positive_aggrid_display['Date'] = top_20_positive_aggrid_display['Date'].dt.strftime('%Y-%m-%d') 
        AgGrid(top_20_positive_aggrid_display, gridOptions=gridOptions, 
               data_return_mode='AS_INPUT', update_mode='MODEL_CHANGED', 
               fit_columns_on_grid_load=True, allow_unsafe_jscode=True, 
               enable_enterprise_modules=True, height=350, width='100%', reload_data=True, key='ag_pos_tails')
    else:
        st.info("No positive Macro DVaR tails found.")

    st.subheader("Top 20 Negative Macro DVaR Tails (Current COB)")
    if not top_20_negative_aggrid.empty:
        top_20_negative_aggrid_display = top_20_negative_aggrid.copy()
        top_20_negative_aggrid_display['Date'] = top_20_negative_aggrid_display['Date'].dt.strftime('%Y-%m-%d') 
        AgGrid(top_20_negative_aggrid_display, gridOptions=gridOptions, 
               data_return_mode='AS_INPUT', update_mode='MODEL_CHANGED', 
               fit_columns_on_grid_load=True, allow_unsafe_jscode=True, 
               enable_enterprise_modules=True, height=350, width='100%', reload_data=True, key='ag_neg_tails')
    else:
        st.info("No negative Macro DVaR tails found.")

