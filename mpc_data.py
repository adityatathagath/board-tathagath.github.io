import pandas as pd
import os
import re # Import the regular expression module
from pathlib import Path

def parse_risk_excel(file_path):
    """
    Parses a single risk data Excel file and extracts DV01 and Change DV01 data.
    It robustly handles filenames with extra text after the date.

    Args:
        file_path (Path): The path to the Excel file.

    Returns:
        list: A list of dictionaries, where each dictionary is a single time-series record.
              Returns an empty list if the file or sheet is invalid.
    """
    try:
        # --- Robust Date Extraction using Regular Expressions ---
        # Search for a pattern like YYYY.MM.DD in the filename.
        date_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', file_path.name)
        if not date_match:
            print(f"Warning: Could not find a date in the expected format (YYYY.MM.DD) in filename: {file_path.name}")
            return []
        
        date_str = date_match.group(1)
        cob_date = pd.to_datetime(date_str, format='%Y.%m.%d')

        # Read the specific sheet
        # Using openpyxl engine is recommended for .xlsx files
        xls = pd.ExcelFile(file_path, engine='openpyxl')
        if 'Trade_Desk_Data' not in xls.sheet_names:
            print(f"Warning: 'Trade_Desk_Data' sheet not found in {file_path.name}")
            return []

        df = pd.read_excel(xls, sheet_name='Trade_Desk_Data', header=None)

        # --- Data Extraction ---
        # Asset classes are in row 6 (index 5), from column D to N (index 3 to 13)
        asset_classes = df.iloc[5, 3:14].tolist()
        
        # Tenors are in column C (index 2)
        
        all_records = []

        # Function to process a single table (DV01 or Change DV01)
        def process_table(start_row, metric_name):
            records = []
            # Data is from start_row to start_row + 8 (9 rows total, excluding 'Total')
            table_data = df.iloc[start_row:start_row+8, 2:14]
            table_data.columns = ['Tenor'] + asset_classes
            
            for index, row in table_data.iterrows():
                tenor = row['Tenor']
                for asset in asset_classes:
                    record = {
                        'Date': cob_date,
                        'Tenor': tenor,
                        'Asset Class': asset,
                        'Metric': metric_name,
                        'Value': row[asset]
                    }
                    records.append(record)
            return records

        # Process "Today's Risk" (DV01) table from C7:N15 (starts at row index 6)
        all_records.extend(process_table(6, 'DV01'))
        
        # Process "Change in Risk" (Change DV01) table from C17:N25 (starts at row index 16)
        all_records.extend(process_table(16, 'Change DV01'))

        return all_records

    except Exception as e:
        print(f"Error processing file {file_path.name}: {e}")
        return []

def main():
    """
    Main function to find all risk files, process them, and save to a single Excel file.
    """
    # --- Configuration ---
    # Assumes the script is placed on the Desktop, next to the 'Risk_data' folder.
    # If not, change 'base_path' to the absolute path of your 'Risk_data' folder.
    desktop_path = Path.home() / 'Desktop'
    base_path = desktop_path / 'Risk_data'
    
    # Check if the base directory exists
    if not base_path.exists():
        print(f"Error: The directory '{base_path}' was not found.")
        print("Please make sure the 'Risk_data' folder is on your Desktop, or update the 'base_path' in the script.")
        return

    print(f"Starting data consolidation from: {base_path}")

    # Find all relevant excel files in the subdirectories (2023, 2024, 2025, etc.)
    all_files = list(base_path.glob('**/risk_data_In_*.xlsx'))
    
    if not all_files:
        print("No 'risk_data_In_*.xlsx' files were found. Please check the folder structure.")
        return

    print(f"Found {len(all_files)} files to process.")

    # Process all files and collect the data
    master_data_list = []
    for file in all_files:
        print(f"Processing: {file.name}...")
        master_data_list.extend(parse_risk_excel(file))

    if not master_data_list:
        print("No data was extracted. Aborting.")
        return
        
    # Convert the list of dictionaries to a pandas DataFrame
    final_df = pd.DataFrame(master_data_list)

    # --- Data Cleaning (Optional but Recommended) ---
    # Convert 'Value' to numeric, coercing errors to NaN (Not a Number)
    final_df['Value'] = pd.to_numeric(final_df['Value'], errors='coerce')
    # Remove rows where the value could not be parsed (e.g., if it was '-')
    final_df.dropna(subset=['Value'], inplace=True)
    
    # Sort the data for better readability
    final_df.sort_values(by=['Date', 'Metric', 'Tenor', 'Asset Class'], inplace=True)

    # --- Save to Excel ---
    output_filename = desktop_path / 'consolidated_risk_timeseries.xlsx'
    try:
        final_df.to_excel(output_filename, index=False, engine='openpyxl')
        print("-" * 50)
        print(f"Successfully created the consolidated time-series file!")
        print(f"File saved to: {output_filename}")
        print(f"Total records created: {len(final_df)}")
        print("-" * 50)
    except Exception as e:
        print(f"Error saving the final Excel file: {e}")


if __name__ == "__main__":

    main()
