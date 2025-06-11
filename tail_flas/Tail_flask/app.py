# app.py
from flask import Flask, render_template, request, jsonify, flash, send_from_directory
import pandas as pd
import numpy as np
import io
import os # For path joining
from bokeh.embed import json_item
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, NumeralTickFormatter, DatetimeTickFormatter
from bokeh.palettes import Category10, Category20 # For Bokeh plot colors

app = Flask(__name__)
app.secret_key = 'your_strong_secret_key_here' # IMPORTANT: Replace with a strong secret key

# --- Configuration (UPDATE THESE BASED ON YOUR DATA) ---
EXCEL_FILE_PATH = os.path.join(app.root_path, 'data', 'Tail_analysis_auto.xlsx') # Path to your Excel file
# Create a 'data' directory in your Flask app's root and place the Excel file there.

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

# Define Barclays-specific color palette (example professional blue/grey tones)
BARCLAYS_COLOR_PALETTE = [
    '#0076B6',  # Primary Blue (Barclays blue)
    '#2188D7',  # Lighter Blue
    '#004B7F',  # Darker Blue
    '#6A6C6E',  # Medium Grey
    '#A0A3A6',  # Light Grey
    '#FF4B4B',  # Red for negative changes
    '#28a745',  # Green for positive changes
]

# --- Data Storage and Caching ---
processed_data_store = {} # Stores results of calculate_var_tails
processed_data_loaded_flag = False # Flag to indicate if data has been loaded and processed

# --- Helper Functions (Adapted from Streamlit app) ---

def load_data_backend(file_path):
    """
    Loads data from the specified sheets in the Excel workbook from a given file path.
    Handles date extraction from the first row and sets proper headers.
    Ensures 'Node' column is numeric.
    Returns (data_frames, date_mappings)
    """
    data_frames = {}
    date_mappings = {}

    sheets_to_load = [
        CURRENT_DAY_SHEET_NAME,
        PREVIOUS_DAY_SHEET_NAME,
        SVAR_COB_SHEET_NAME,
        SVAR_PREV_COB_SHEET_NAME
    ]
    
    # Ensure file exists before opening
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel file not found at: {file_path}")

    # Use a single file handle for all sheets to avoid re-opening
    # Using pd.ExcelFile context manager is more robust
    with pd.ExcelFile(file_path) as xls:
        for sheet_name in sheets_to_load:
            # Added more robust error handling for each sheet's header parsing
            try:
                # Read the first two rows to get dates and column names
                # It's better to read data directly via pd.read_excel if pd.ExcelFile causes issues
                # with header=None and nrows=2
                # Re-opening with pd.read_excel per sheet is safer if ExcelFile is buggy with headers
                df_temp = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=2)
                
                if df_temp.empty:
                    raise ValueError(f"Sheet '{sheet_name}' is empty or could not be read.")
                if len(df_temp) < 2:
                    raise ValueError(f"Sheet '{sheet_name}' has fewer than 2 rows (expected dates in row 1, headers in row 2). Found {len(df_temp)} rows.")

                dates_row = df_temp.iloc[0]
                column_names_row = df_temp.iloc[1]

                # Read the actual data, skipping the first two rows, using the same ExcelFile object
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None, skiprows=2)
                df.columns = column_names_row # Assign the second row as column headers
                
                df = df.dropna(axis=1, how='all')

                if 'Node' in df.columns:
                    df['Node'] = pd.to_numeric(df['Node'], errors='coerce')
                    df['Node'] = df['Node'].astype('Int64')

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
                raise Exception(f"Error processing sheet '{sheet_name}': {e}")
    
    return data_frames, date_mappings


def calculate_var_tails_backend(df, pnl_date_map, sheet_type="current", var_type_filter="DVaR", 
                                dvar_pnl_vector_start=None, dvar_pnl_vector_end=None, 
                                svar_pnl_vector_start=None, svar_pnl_vector_end=None):
    """
    Calculates VaR tails (DVaR or SVaR) for FX, Rates, EM Macro, and Macro.
    Returns (fx_df, rates_df, em_macro_df, macro_df, raw_filtered_df)
    """
    current_pnl_vector_start = None
    current_pnl_vector_end = None

    if var_type_filter == "DVaR":
        current_pnl_vector_start = dvar_pnl_vector_start
        current_pnl_vector_end = dvar_pnl_vector_end
    elif var_type_filter == "SVaR":
        current_pnl_vector_start = svar_pnl_vector_start
        current_pnl_vector_end = svar_pnl_vector_end
    
    if current_pnl_vector_start is None or current_pnl_vector_end is None:
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
    
    if not valid_pnl_cols:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    id_vars_present = [col for col in id_vars if col in df.columns]
    
    df_melted = df.melt(id_vars=id_vars_present,
                         value_vars=valid_pnl_cols,
                         var_name='Pnl_Vector_Name',
                         value_name='Value')
    
    def extract_pnl_rank(pnl_vector_name):
        name_without_suffix = pnl_vector_name.split('[T-2]')[0]
        numeric_part = ''.join(filter(str.isdigit, name_without_suffix))
        return int(numeric_part) if numeric_part else np.nan
    
    df_melted['Pnl_Vector_Rank'] = df_melted['Pnl_Vector_Name'].apply(extract_pnl_rank)
    df_melted['Pnl_Vector_Rank'] = df_melted['Pnl_Vector_Rank'].astype('Int64')

    df_melted['Date'] = df_melted['Pnl_Vector_Name'].map(pnl_date_map)
    df_melted['Date'] = pd.to_datetime(df_melted['Date'], errors='coerce')
    df_melted = df_melted.dropna(subset=['Date'])

    df_filtered_var_type = df_melted[df_melted['Var Type'] == var_type_filter].copy()

    asset_classes = ['FX', 'Rates', 'EM Macro'] # Corrected casing
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

# --- Bokeh Plotting Functions (remain the same as they operate on DataFrames) ---

def create_dvar_trends_bokeh_plot(df, title, y_column, legend_title="Type"):
    """Generates a Bokeh line chart for DVaR trends."""
    if df.empty:
        return None

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

    sheet_types = df['Sheet_Type'].unique()
    
    # Use BARCLAYS_COLOR_PALETTE directly
    colors = BARCLAYS_COLOR_PALETTE 

    for i, sheet_type in enumerate(sheet_types):
        view = ColumnDataSource(df[df['Sheet_Type'] == sheet_type])
        # Ensure that the index is within the bounds of BARCLAYS_COLOR_PALETTE
        color_index = i % len(colors)
        p.line(
            x='Date', 
            y=y_column, 
            source=view, 
            legend_label=sheet_type, 
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
            legend_label=sheet_type
        )

    p.xaxis.formatter = DatetimeTickFormatter(days="%d-%m-%Y", months="%d-%m-%Y", years="%d-%m-%Y")
    p.xaxis.axis_label = "Date"
    p.yaxis.formatter = NumeralTickFormatter(format="0,0.00")
    p.yaxis.axis_label = "DVaR Value"
    p.legend.location = "top_left"
    p.legend.click_policy = "hide"

    p.hover.tooltips = [
        ("Date", "@Date{%d-%m-%Y}"),
        (y_column, f"@{y_column}{{0,0.00}}"),
        (legend_title, "@Sheet_Type"),
        ("P&L Vector Rank", "@Pnl_Vector_Rank")
    ]
    p.hover.formatters = {"@Date": "datetime"}

    return p

# --- Flask Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_data', methods=['POST'])
def process_data():
    global processed_data_loaded_flag # Declare global to modify it
    global processed_data_store # Declare global to modify it

    if processed_data_loaded_flag:
        # Data already loaded and cached, return success
        return jsonify({'success': True, 'message': 'Data already processed from cache.', 'key_metrics': get_key_metrics_from_store()}), 200

    try:
        # Directly load from pre-defined path
        data_sheets, date_mappings = load_data_backend(EXCEL_FILE_PATH)

        current_day_df = data_sheets.get(CURRENT_DAY_SHEET_NAME)
        previous_day_df = data_sheets.get(PREVIOUS_DAY_SHEET_NAME)
        svar_cob_df = data_sheets.get(SVAR_COB_SHEET_NAME)
        svar_prev_cob_df = data_sheets.get(SVAR_PREV_COB_SHEET_NAME)

        current_day_date_map = date_mappings.get(CURRENT_DAY_SHEET_NAME)
        previous_day_date_map = date_mappings.get(PREVIOUS_DAY_SHEET_NAME)
        svar_cob_date_map = date_mappings.get(SVAR_COB_SHEET_NAME)
        svar_prev_cob_date_map = date_mappings.get(SVAR_PREV_COB_SHEET_NAME)

        if not all([df is not None for df in [current_day_df, previous_day_df, svar_cob_df, svar_prev_cob_df]]):
            raise Exception("One or more required sheets could not be loaded or are empty.")
        if not all([m is not None for m in [current_day_date_map, previous_day_date_map, svar_cob_date_map, svar_prev_cob_date_map]]):
            raise Exception("Date mappings could not be extracted for one or more sheets.")

        # Calculate DVaR for Current COB
        fx_dvar_curr, rates_dvar_curr, em_macro_dvar_curr, macro_dvar_curr, raw_dvar_curr = \
            calculate_var_tails_backend(current_day_df, current_day_date_map, "current", "DVaR", 
                                        DVAR_PNL_VECTOR_START, DVAR_PNL_VECTOR_END, 
                                        SVAR_PNL_VECTOR_START, SVAR_PNL_VECTOR_END)
        
        # Calculate DVaR for Previous COB
        fx_dvar_prev, rates_dvar_prev, em_macro_dvar_prev, macro_dvar_prev, raw_dvar_prev = \
            calculate_var_tails_backend(previous_day_df, previous_day_date_map, "previous", "DVaR", 
                                        DVAR_PNL_VECTOR_START, DVAR_PNL_VECTOR_END, 
                                        SVAR_PNL_VECTOR_START, SVAR_PNL_VECTOR_END)
        
        # Calculate SVaR for Current COB
        fx_svar_curr, rates_svar_curr, em_macro_svar_curr, macro_svar_curr, raw_svar_curr = \
            calculate_var_tails_backend(svar_cob_df, svar_cob_date_map, "current", "SVaR", 
                                        DVAR_PNL_VECTOR_START, DVAR_PNL_VECTOR_END, 
                                        SVAR_PNL_VECTOR_START, SVAR_PNL_VECTOR_END)

        # Calculate SVaR for Previous COB
        fx_svar_prev, rates_svar_prev, em_macro_svar_prev, macro_svar_prev, raw_svar_prev = \
            calculate_var_tails_backend(svar_prev_cob_df, svar_prev_cob_date_map, "previous", "SVaR", 
                                        DVAR_PNL_VECTOR_START, DVAR_PNL_VECTOR_END, 
                                        SVAR_PNL_VECTOR_START, SVAR_PNL_VECTOR_END)

        # Store processed data in the global dictionary
        processed_data_store['macro_dvar_curr'] = macro_dvar_curr
        processed_data_store['macro_dvar_prev'] = macro_dvar_prev
        processed_data_store['fx_dvar_curr'] = fx_dvar_curr
        processed_data_store['fx_dvar_prev'] = fx_dvar_prev
        processed_data_store['rates_dvar_curr'] = rates_dvar_curr
        processed_data_store['rates_dvar_prev'] = rates_dvar_prev
        processed_data_store['em_macro_dvar_curr'] = em_macro_dvar_curr
        processed_data_store['em_macro_dvar_prev'] = em_macro_dvar_prev
        processed_data_store['macro_svar_curr'] = macro_svar_curr
        processed_data_store['macro_svar_prev'] = macro_svar_prev
        
        processed_data_loaded_flag = True # Set flag to true as data is now processed

        # Prepare data for "Lowest Metrics" cards
        key_metrics = get_key_metrics_from_store()

        return jsonify({'success': True, 'message': 'Data processed successfully', 'key_metrics': key_metrics}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_key_metrics_from_store():
    """Helper to extract lowest metrics from the processed_data_store."""
    macro_dvar_curr = processed_data_store.get('macro_dvar_curr', pd.DataFrame())
    macro_svar_curr = processed_data_store.get('macro_svar_curr', pd.DataFrame())

    lowest_dvar_row = macro_dvar_curr.nsmallest(1, 'Macro_DVaR_Value').iloc[0] if not macro_dvar_curr.empty else None
    lowest_svar_row = macro_svar_curr.nsmallest(1, 'Macro_SVaR_Value').iloc[0] if not macro_svar_curr.empty else None

    return {
        'lowest_dvar': {
            'value': f"{lowest_dvar_row['Macro_DVaR_Value']:,.2f}",
            'date': lowest_dvar_row['Date'].strftime('%d-%m-%Y'),
            'pnl_vector': lowest_dvar_row['Pnl_Vector_Name']
        } if lowest_dvar_row is not None and 'Macro_DVaR_Value' in lowest_dvar_row else None,
        'lowest_svar': {
            'value': f"{lowest_svar_row['Macro_SVaR_Value']:,.2f}",
            'date': lowest_svar_row['Date'].strftime('%d-%m-%Y'),
            'pnl_vector': lowest_svar_row['Pnl_Vector_Name']
        } if lowest_svar_row is not None and 'Macro_SVaR_Value' in lowest_svar_row else None,
    }


@app.route('/get_top_bottom_tails', methods=['GET'])
def get_top_bottom_tails():
    # Retrieve from cache
    macro_dvar_curr = processed_data_store.get('macro_dvar_curr', pd.DataFrame())
    macro_dvar_prev = processed_data_store.get('macro_dvar_prev', pd.DataFrame())
    fx_dvar_curr = processed_data_store.get('fx_dvar_curr', pd.DataFrame())
    fx_dvar_prev = processed_data_store.get('fx_dvar_prev', pd.DataFrame())
    rates_dvar_curr = processed_data_store.get('rates_dvar_curr', pd.DataFrame())
    rates_dvar_prev = processed_data_store.get('rates_dvar_prev', pd.DataFrame())
    em_macro_dvar_curr = processed_data_store.get('em_macro_dvar_curr', pd.DataFrame())
    em_macro_dvar_prev = processed_data_store.get('em_macro_dvar_prev', pd.DataFrame())

    if macro_dvar_curr.empty:
        return jsonify({'error': 'No DVaR data available. Please process the file first.'}), 400

    common_merge_keys = ['Date', 'Pnl_Vector_Name', 'Pnl_Vector_Rank']

    top_20_positive_curr = macro_dvar_curr.nlargest(min(20, len(macro_dvar_curr)), 'Macro_DVaR_Value', keep='all').copy()
    top_20_negative_curr = macro_dvar_curr.nsmallest(min(20, len(macro_dvar_curr)), 'Macro_DVaR_Value', keep='all').copy()

    all_current_tails_base = pd.concat([top_20_positive_curr, top_20_negative_curr]).drop_duplicates(subset=common_merge_keys).reset_index(drop=True)
    all_current_tails_base.rename(columns={'Macro_DVaR_Value': 'Macro_DVaR_Value_Current'}, inplace=True)

    prev_lookup_configs = [
        (macro_dvar_prev, 'Macro_DVaR_Value', 'Macro_DVaR_Value_Previous'),
        (fx_dvar_prev, 'FX_DVaR_Value', 'FX_DVaR_Value_Previous'),
        (rates_dvar_prev, 'Rates_DVaR_Value', 'Rates_DVaR_Value_Previous'),
        (em_macro_dvar_prev, 'EM_Macro_DVaR_Value', 'EM_Macro_DVaR_Value_Previous')
    ]

    final_display_df = all_current_tails_base.copy()

    for prev_df, original_val_col, new_val_col in prev_lookup_configs:
        if not prev_df.empty and original_val_col in prev_df.columns:
            temp_prev_lookup_df = prev_df[common_merge_keys + [original_val_col]].copy()
            temp_prev_lookup_df.rename(columns={original_val_col: new_val_col}, inplace=True)
            final_display_df = pd.merge(final_display_df, temp_prev_lookup_df, on=common_merge_keys, how='left')
        
    current_asset_lookup_configs = [
        (fx_dvar_curr, 'FX_DVaR_Value', 'FX_DVaR_Value_Current'),
        (rates_dvar_curr, 'Rates_DVaR_Value', 'Rates_DVaR_Value_Current'),
        (em_macro_dvar_curr, 'EM_Macro_DVaR_Value', 'EM_Macro_DVaR_Value_Current')
    ]
    for curr_df, original_val_col, new_val_col in current_asset_lookup_configs:
        if new_val_col not in final_display_df.columns and not curr_df.empty and original_val_col in curr_df.columns:
            temp_curr_lookup_df = curr_df[common_merge_keys + [original_val_col]].copy()
            temp_curr_lookup_df.rename(columns={original_val_col: new_val_col}, inplace=True)
            final_display_df = pd.merge(final_display_df, temp_curr_lookup_df, on=common_merge_keys, how='left')

    value_cols_to_fill = [col for col in final_display_df.columns if '_DVaR_Value_Current' in col or '_DVaR_Value_Previous' in col]
    final_display_df[value_cols_to_fill] = final_display_df[value_cols_to_fill].fillna(0)

    for prefix in ['Macro', 'FX', 'Rates', 'EM_Macro']:
        current_col_name = f'{prefix}_DVaR_Value_Current'
        previous_col_name = f'{prefix}_DVaR_Value_Previous'
        change_col_name = f'{prefix}_DVaR_Change'
        
        if current_col_name in final_display_df.columns and previous_col_name in final_display_df.columns:
            final_display_df[change_col_name] = final_display_df[current_col_name] - final_display_df[previous_col_name]
        else:
            final_display_df[change_col_name] = 0

    final_display_df.dropna(subset=['Macro_DVaR_Value_Current'], inplace=True)
    final_display_df = final_display_df.sort_values(by=['Date', 'Pnl_Vector_Rank']).reset_index(drop=True)

    top_20_positive_aggrid = final_display_df.nlargest(min(20, len(final_display_df)), 'Macro_DVaR_Value_Current', keep='all')
    top_20_negative_aggrid = final_display_df.nsmallest(min(20, len(final_display_df)), 'Macro_DVaR_Value_Current', keep='all')

    top_20_positive_aggrid['Date'] = top_20_positive_aggrid['Date'].dt.strftime('%Y-%m-%d')
    top_20_negative_aggrid['Date'] = top_20_negative_aggrid['Date'].dt.strftime('%Y-%m-%d')

    return jsonify({
        'positive_tails': top_20_positive_aggrid.to_dict(orient='records'),
        'negative_tails': top_20_negative_aggrid.to_dict(orient='records')
    })


@app.route('/get_dvar_trends_plot', methods=['GET'])
def get_dvar_trends_plot():
    macro_dvar_curr = processed_data_store.get('macro_dvar_curr', pd.DataFrame())
    macro_dvar_prev = processed_data_store.get('macro_dvar_prev', pd.DataFrame())

    if macro_dvar_curr.empty and macro_dvar_prev.empty:
        return jsonify({'error': 'No DVaR data available for trends plot.'}), 400

    all_macro_dvar = pd.concat([macro_dvar_curr, macro_dvar_prev], ignore_index=True)
    if all_macro_dvar.empty:
         return jsonify({'error': 'No combined DVaR data for trends plot.'}), 400

    all_macro_dvar['Date'] = pd.to_datetime(all_macro_dvar['Date'])

    plot = create_dvar_trends_bokeh_plot(all_macro_dvar, "Macro DVaR Trend (Current vs. Previous Day)", 'Macro_DVaR_Value')
    
    if plot:
        return jsonify(json_item(plot, "dvar_trends_plot_div")), 200
    else:
        return jsonify({'error': 'Failed to create Bokeh plot.'}), 500

# Route to serve static files from the 'static' folder
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Initial data processing on Flask startup/first request
@app.before_first_request
def initialize_data():
    global processed_data_loaded_flag
    if not processed_data_loaded_flag:
        try:
            # Simulate a POST request to /process_data to trigger loading
            with app.test_request_context('/process_data', method='POST'):
                response = app.full_dispatch_request()
                if response.status_code != 200:
                    print(f"Error during initial data load: {response.get_data(as_text=True)}")
                    # Optionally, log this error more persistently
        except Exception as e:
            print(f"Unhandled exception during initial data load: {e}")

if __name__ == '__main__':
    # Create the 'data' directory if it doesn't exist
    data_dir = os.path.join(app.root_path, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Check if the Excel file exists, provide guidance if not
    if not os.path.exists(EXCEL_FILE_PATH):
        print(f"ERROR: Excel file not found at {EXCEL_FILE_PATH}")
        print("Please create a 'data' folder in the same directory as app.py and place 'Tail_analysis_auto.xlsx' inside it.")
        print("Exiting...")
        exit() # Exit if file is not found
        
    app.run(debug=True)

