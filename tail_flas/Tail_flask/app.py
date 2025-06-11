# app.py
from flask import Flask, render_template, request, jsonify, flash, send_from_directory
import pandas as pd
import numpy as np
import io
import os # For path joining
import sqlite3 # For SQLite database operations
from bokeh.embed import json_item
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, NumeralTickFormatter, DatetimeTickFormatter
from bokeh.palettes import Category10, Category20 # For Bokeh plot colors
from sqlalchemy import create_engine # For pandas to_sql

app = Flask(__name__)
app.secret_key = 'your_strong_secret_key_here' # IMPORTANT: Replace with a strong secret key

# --- Configuration ---
EXCEL_FILE_PATH = os.path.join(app.root_path, 'data', 'Tail_analysis_auto.xlsx')
DB_FILE_PATH = os.path.join(app.root_path, 'data', 'data.db') # SQLite database file path

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

BARCLAYS_COLOR_PALETTE = [
    '#0076B6',  # Primary Blue
    '#2188D7',  # Lighter Blue
    '#004B7F',  # Darker Blue
    '#6A6C6E',  # Medium Grey
    '#A0A3A6',  # Light Grey
    '#FF4B4B',  # Red for negative changes (index 5)
    '#28a745',  # Green for positive changes (index 6)
]

# --- Database Helper ---
def get_db_engine():
    """Returns a SQLAlchemy engine for SQLite."""
    return create_engine(f'sqlite:///{DB_FILE_PATH}')

def get_db_connection():
    """Returns a direct SQLite connection."""
    conn = sqlite3.connect(DB_FILE_PATH)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

# --- Data Ingestion Function ---
def ingest_excel_to_sqlite(excel_file_path):
    """
    Reads the Excel file and ingests all relevant data into a SQLite database.
    Stores processed data in a single 'pnl_data' table in long format.
    """
    print(f"Ingesting Excel data from {excel_file_path} into SQLite database {DB_FILE_PATH}...")
    engine = get_db_engine()

    sheets_to_process = {
        CURRENT_DAY_SHEET_NAME: {"type": "DVaR", "sheet_type": "current", "vector_start": DVAR_PNL_VECTOR_START, "vector_end": DVAR_PNL_VECTOR_END},
        PREVIOUS_DAY_SHEET_NAME: {"type": "DVaR", "sheet_type": "previous", "vector_start": DVAR_PNL_VECTOR_START, "vector_end": DVAR_PNL_VECTOR_END},
        SVAR_COB_SHEET_NAME: {"type": "SVaR", "sheet_type": "current", "vector_start": SVAR_PNL_VECTOR_START, "vector_end": SVAR_PNL_VECTOR_END},
        SVAR_PREV_COB_SHEET_NAME: {"type": "SVaR", "sheet_type": "previous", "vector_start": SVAR_PNL_VECTOR_START, "vector_end": SVAR_PNL_VECTOR_END},
    }

    all_melted_dfs = []

    with pd.ExcelFile(excel_file_path) as xls:
        for sheet_name, config in sheets_to_process.items():
            print(f"  Processing sheet: {sheet_name} (Type: {config['type']}, Period: {config['sheet_type']})")
            try:
                # Read header rows first to get dates and column names
                df_temp = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=2)
                if df_temp.empty or len(df_temp) < 2:
                    print(f"    WARNING: Sheet '{sheet_name}' is empty or has insufficient header rows. Skipping.")
                    continue

                dates_row = df_temp.iloc[0]
                column_names_row = df_temp.iloc[1]

                # Read actual data
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None, skiprows=2)
                df.columns = column_names_row
                df = df.dropna(axis=1, how='all') # Drop columns that are entirely NaN

                # Ensure 'Node' column is numeric
                if 'Node' in df.columns:
                    df['Node'] = pd.to_numeric(df['Node'], errors='coerce').astype('Int64')

                # Create PnL date map
                pnl_date_map = {}
                for col_idx, col_name in enumerate(column_names_row):
                    if pd.isna(col_name): continue
                    if str(col_name).startswith('pnl_vector') or ('[T-2]' in str(col_name) and 'pnl_vector' in str(col_name)):
                        if col_idx < len(dates_row):
                            date_val = dates_row.iloc[col_idx]
                            if isinstance(date_val, (int, float)):
                                try: pnl_date_map[str(col_name)] = pd.to_datetime(date_val, unit='D', origin='1899-12-30')
                                except: pnl_date_map[str(col_name)] = pd.NaT
                            else: pnl_date_map[str(col_name)] = pd.to_datetime(date_val, errors='coerce')

                # Identify valid PnL vector columns based on sheet type and range
                pnl_vector_cols = [col for col in df.columns if str(col).startswith('pnl_vector') or ('[T-2]' in str(col) and 'pnl_vector' in str(col))]
                valid_pnl_cols_for_sheet = []
                for col_name in pnl_vector_cols:
                    col_str = str(col_name)
                    is_previous_cob_vector = '[T-2]' in col_str
                    numeric_part_str = ''.join(filter(str.isdigit, col_str.split('[T-2]')[0]))

                    if not numeric_part_str.isdigit(): continue
                    vector_number = int(numeric_part_str)

                    if config["sheet_type"] == "current":
                        if not is_previous_cob_vector and config["vector_start"] <= vector_number <= config["vector_end"]:
                            valid_pnl_cols_for_sheet.append(col_name)
                    elif config["sheet_type"] == "previous":
                        if is_previous_cob_vector and config["vector_start"] <= vector_number <= config["vector_end"]:
                            valid_pnl_cols_for_sheet.append(col_name)

                if not valid_pnl_cols_for_sheet:
                    print(f"    WARNING: No valid PnL vector columns found for sheet '{sheet_name}'. Skipping.")
                    continue

                # Melt the DataFrame
                id_vars = ['Var Type', 'Node', 'Asset class', 'currency', 'sensitivity_type', 'load_code']
                id_vars_present = [col for col in id_vars if col in df.columns]
                df_melted = df.melt(id_vars=id_vars_present,
                                     value_vars=valid_pnl_cols_for_sheet,
                                     var_name='Pnl_Vector_Name',
                                     value_name='Value')
                
                # Add Pnl_Vector_Rank
                def extract_pnl_rank_ingest(pnl_vector_name):
                    name_without_suffix = pnl_vector_name.split('[T-2]')[0]
                    numeric_part = ''.join(filter(str.isdigit, name_without_suffix))
                    return int(numeric_part) if numeric_part else np.nan
                df_melted['Pnl_Vector_Rank'] = df_melted['Pnl_Vector_Name'].apply(extract_pnl_rank_ingest)
                df_melted['Pnl_Vector_Rank'] = df_melted['Pnl_Vector_Rank'].astype('Int64')

                # Add Date and Sheet_Type
                df_melted['Date'] = df_melted['Pnl_Vector_Name'].map(pnl_date_map)
                df_melted['Date'] = pd.to_datetime(df_melted['Date'], errors='coerce')
                df_melted = df_melted.dropna(subset=['Date'])
                df_melted['Sheet_Type'] = config["sheet_type"]
                df_melted['Var_Type_Original'] = config["type"] # Keep original Var Type for filtering in queries

                all_melted_dfs.append(df_melted)
                print(f"    Successfully processed sheet '{sheet_name}'. Rows: {len(df_melted)}")

            except Exception as e:
                print(f"    ERROR processing sheet '{sheet_name}': {e}")
                raise # Re-raise to stop ingestion if one sheet fails critically

    if not all_melted_dfs:
        print("No data processed from any sheet. Database will be empty.")
        return

    final_ingestion_df = pd.concat(all_melted_dfs, ignore_index=True)
    # Convert dates to string for SQLite storage to prevent issues with different drivers/versions
    final_ingestion_df['Date'] = final_ingestion_df['Date'].dt.strftime('%Y-%m-%d')
    
    print(f"Total rows to ingest: {len(final_ingestion_df)}")
    # Write to SQLite
    final_ingestion_df.to_sql('pnl_data', engine, if_exists='replace', index=False, dtype={
        'Date': 'TEXT',
        'Pnl_Vector_Name': 'TEXT',
        'Pnl_Vector_Rank': 'INTEGER',
        'Value': 'REAL',
        'Var Type': 'TEXT',
        'Node': 'INTEGER',
        'Asset class': 'TEXT',
        'currency': 'TEXT',
        'sensitivity_type': 'TEXT',
        'load_code': 'TEXT',
        'Sheet_Type': 'TEXT',
        'Var_Type_Original': 'TEXT'
    })
    print("Ingestion complete. Data stored in 'pnl_data' table.")


# --- Data Retrieval Functions (Querying SQLite) ---

def get_filtered_var_data_from_db(conn, sheet_type, var_type_original, debug_mode):
    """
    Fetches and calculates aggregated VAR data (Macro, FX, Rates, EM Macro) from DB.
    """
    asset_classes = ['FX', 'Rates', 'EM Macro']
    node_mapping = {
        'FX': FX_DVAR_NODE, 
        'Rates': RATES_DVAR_NODE, 
        'EM Macro': EM_MACRO_DVAR_NODE
    }
    
    # Base query for the specific sheet type and original VAR type (DVaR or SVaR)
    # The 'Var Type' column in the DB corresponds to DVaR or SVaR from the original sheet
    # We are filtering by 'Var_Type_Original' now, as 'Var Type' column is just 'DVaR' or 'SVaR'
    # depending on what was in the source Excel column.
    
    # Construct individual asset class queries first
    asset_dfs = {}
    for ac in asset_classes:
        query = f"""
            SELECT
                Date,
                Pnl_Vector_Name,
                Pnl_Vector_Rank,
                SUM(Value) AS "{ac.replace(" ", "_")}_{var_type_original}_Value"
            FROM pnl_data
            WHERE
                Sheet_Type = '{sheet_type}' AND
                "Var Type" = '{var_type_original}' AND  -- Use the 'Var Type' column which stores DVaR/SVaR for filtering
                "Asset class" = '{ac}' AND
                Node = {node_mapping[ac]}
            GROUP BY Date, Pnl_Vector_Name, Pnl_Vector_Rank
            ORDER BY Date, Pnl_Vector_Rank;
        """
        try:
            df = pd.read_sql_query(query, conn)
            # Ensure Pnl_Vector_Rank is Int64 for merging
            df['Pnl_Vector_Rank'] = df['Pnl_Vector_Rank'].astype('Int64')
            asset_dfs[ac] = df
            if debug_mode: print(f"  DB Query: {ac} {var_type_original} {sheet_type} rows: {len(df)}")
        except Exception as e:
            print(f"  ERROR DB Query for {ac} {var_type_original} {sheet_type}: {e}")
            asset_dfs[ac] = pd.DataFrame(columns=['Date', 'Pnl_Vector_Name', 'Pnl_Vector_Rank', f'{ac.replace(" ", "_")}_{var_type_original}_Value'])

    # Combine into macro_var_df
    macro_var_df = pd.DataFrame(columns=['Date', 'Pnl_Vector_Name', 'Pnl_Vector_Rank', f'Macro_{var_type_original}_Value'])

    # Start with FX, then outer join others
    if 'FX' in asset_dfs and not asset_dfs['FX'].empty:
        macro_var_df = asset_dfs['FX'].copy()
        for ac_other in [ac for ac in asset_classes if ac != 'FX']:
            if ac_other in asset_dfs and not asset_dfs[ac_other].empty:
                macro_var_df = pd.merge(macro_var_df, asset_dfs[ac_other], on=['Date', 'Pnl_Vector_Name', 'Pnl_Vector_Rank'], how='outer')
        
        # Calculate Macro Sum
        cols_for_sum = [f'{ac.replace(" ", "_")}_{var_type_original}_Value' for ac in asset_classes]
        # Fill NA for summing, as outer merge might introduce them
        for col_sum in cols_for_sum:
            if col_sum not in macro_var_df.columns:
                macro_var_df[col_sum] = 0.0 # Ensure float type for summing
            macro_var_df[col_sum] = macro_var_df[col_sum].fillna(0.0)

        macro_var_df[f'Macro_{var_type_original}_Value'] = macro_var_df[cols_for_sum].sum(axis=1)
        macro_var_df['Sheet_Type'] = sheet_type # Add Sheet_Type column
        macro_var_df = macro_var_df.sort_values(['Date', 'Pnl_Vector_Rank']).reset_index(drop=True)
    else:
        print(f"  WARNING: No FX data found for Macro {var_type_original} {sheet_type} calculation.")


    return asset_dfs.get('FX', pd.DataFrame()), \
           asset_dfs.get('Rates', pd.DataFrame()), \
           asset_dfs.get('EM Macro', pd.DataFrame()), \
           macro_var_df


# --- Bokeh Plotting Functions ---

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
    global processed_data_loaded_flag 
    global processed_data_store 

    # Only process if data is not already loaded
    if not processed_data_loaded_flag:
        try:
            # Establish DB connection
            conn = get_db_connection()
            cursor = conn.cursor()

            # --- Check if 'pnl_data' table exists and is populated ---
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pnl_data';")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                # Table doesn't exist, or is empty: ingest from Excel
                conn.close() # Close connection before ingestion (ingestion will open its own)
                ingest_excel_to_sqlite(EXCEL_FILE_PATH)
                # Re-establish connection after ingestion
                conn = get_db_connection()
                cursor = conn.cursor()
            else:
                # Check if table has data
                cursor.execute("SELECT COUNT(*) FROM pnl_data;")
                if cursor.fetchone()[0] == 0:
                    print("WARNING: 'pnl_data' table is empty. Ingesting from Excel...")
                    conn.close()
                    ingest_excel_to_sqlite(EXCEL_FILE_PATH)
                    conn = get_db_connection()
                    cursor = conn.cursor()
            
            # Now that we are sure data is in DB, retrieve it via queries
            # For this simplified Flask structure, we'll fetch all necessary data here
            # that is needed by subsequent GET requests and store in 'processed_data_store'

            # DVaR Current COB
            fx_dvar_curr, rates_dvar_curr, em_macro_dvar_curr, macro_dvar_curr = \
                get_filtered_var_data_from_db(conn, "current", "DVaR", request.json.get('debug_mode', False))
            
            # DVaR Previous COB
            fx_dvar_prev, rates_dvar_prev, em_macro_dvar_prev, macro_dvar_prev = \
                get_filtered_var_data_from_db(conn, "previous", "DVaR", request.json.get('debug_mode', False))
            
            # SVaR Current COB
            fx_svar_curr, rates_svar_curr, em_macro_svar_curr, macro_svar_curr = \
                get_filtered_var_data_from_db(conn, "current", "SVaR", request.json.get('debug_mode', False))

            # SVaR Previous COB
            fx_svar_prev, rates_svar_prev, em_macro_svar_prev, macro_svar_prev = \
                get_filtered_var_data_from_db(conn, "previous", "SVaR", request.json.get('debug_mode', False))
            
            conn.close() # Close connection after all queries

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

        except Exception as e:
            # Ensure connection is closed on error
            if 'conn' in locals() and conn:
                conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # If successful or data already loaded, return metrics
    key_metrics = get_key_metrics_from_store()
    return jsonify({'success': True, 'message': 'Data processed successfully', 'key_metrics': key_metrics}), 200

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
    
    # Run Flask app
    app.run(debug=True)

