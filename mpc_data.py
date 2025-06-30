import pandas as pd
import re
import os
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
        date_match = re.search(r'(\d{4}\.\d{2}\.\d{2})', file_path.name)
        if not date_match:
            print(f"Warning: Could not find a date in the expected format (YYYY.MM.DD) in filename: {file_path.name}")
            return []
        
        date_str = date_match.group(1)
        cob_date = pd.to_datetime(date_str, format='%Y.%m.%d')

        # Read the specific sheet using openpyxl engine
        xls = pd.ExcelFile(file_path, engine='openpyxl')
        if 'Trade_Desk_Data' not in xls.sheet_names:
            print(f"Warning: 'Trade_Desk_Data' sheet not found in {file_path.name}")
            return []

        df = pd.read_excel(xls, sheet_name='Trade_Desk_Data', header=None)

        # --- Data Extraction ---
        asset_classes = df.iloc[5, 3:14].tolist()
        all_records = []

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

        # Process "Today's Risk" (DV01) and "Change in Risk" tables
        all_records.extend(process_table(6, 'DV01'))
        all_records.extend(process_table(16, 'Change DV01'))

        return all_records

    except Exception as e:
        print(f"Error processing file {file_path.name}: {e}")
        return []

def main():
    """
    Main function to prompt for a path, find all risk files directly in that folder, 
    process them, and save the consolidated data to a single Excel file on the Desktop.
    """
    # --- Configuration ---
    # Prompt the user for the path to the directory containing the risk files.
    input_path_str = input("Please enter the full path to the 'risk_data' folder: ").strip()
    
    # Convert the user's input string to a Path object
    base_path = Path(input_path_str)
    
    # Check if the provided path exists and is a directory
    if not base_path.is_dir():
        print(f"\nError: The path you provided is not a valid directory.")
        print(f"Path provided: '{base_path}'")
        return

    print(f"\nStarting data consolidation from: {base_path}")

    # --- Find all relevant Excel files directly in the provided folder ---
    # The .glob() method will find all matching files in this directory.
    all_files = list(base_path.glob('risk_data_In_*.xlsx'))
    
    if not all_files:
        print(f"No 'risk_data_In_*.xlsx' files were found directly in '{base_path}'.")
        print("Please check the path and ensure the files are inside it.")
        return

    print(f"Found {len(all_files)} files to process.")

    # Process all files and collect the data
    master_data_list = []
    for file in all_files:
        print(f"Processing: {file.name}...")
        master_data_list.extend(parse_risk_excel(file))

    if not master_data_list:
        print("\nNo data was successfully extracted. Aborting.")
        return
        
    # Convert the list of dictionaries to a pandas DataFrame
    final_df = pd.DataFrame(master_data_list)

    # --- Data Cleaning ---
    final_df['Value'] = pd.to_numeric(final_df['Value'], errors='coerce')
    final_df.dropna(subset=['Value'], inplace=True)
    final_df.sort_values(by=['Date', 'Metric', 'Tenor', 'Asset Class'], inplace=True)

    # --- Save to Excel ---
    # The output file will be saved to the user's Desktop for easy access.
    desktop_path = Path.home() / 'Desktop'
    output_filename = desktop_path / 'consolidated_risk_timeseries.xlsx'
    try:
        final_df.to_excel(output_filename, index=False, engine='openpyxl')
        print("-" * 50)
        print(f"Successfully created the consolidated time-series file!")
        print(f"File saved to: {output_filename}")
        print(f"Total records created: {len(final_df)}")
        print("-" * 50)
    except Exception as e:
        print(f"\nError saving the final Excel file: {e}")


if __name__ == "__main__":
    # --- Instructions for Use ---
    # 1. Make sure you have Python installed on your system.
    # 2. Install the required libraries by running these commands in your terminal:
    #    pip install pandas
    #    pip install openpyxl
    # 3. Save this script as a Python file (e.g., `consolidate_data.py`).
    # 4. Run the script from your terminal: python consolidate_data.py
    # 5. When prompted, paste the full path to the folder that contains all your risk excel files.
    main()
