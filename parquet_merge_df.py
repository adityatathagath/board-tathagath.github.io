import pandas as pd
import os
import pyarrow.parquet as pq
import pyarrow as pa

# List of subjectids to search for (ensure they are strings)
search_ids = {'2345', '12313', '343', '543'}

# Function to convert CSV or XLSX to Parquet
def convert_to_parquet(input_file, output_file):
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file, dtype=str)  # Read as string to avoid data type issues
    elif input_file.endswith('.xlsx'):
        df = pd.read_excel(input_file, dtype=str)  # Read as string for XLSX
    else:
        raise ValueError(f"Unsupported file format: {input_file}")
    
    # Save to Parquet
    df.to_parquet(output_file, engine='pyarrow', compression='snappy')

# Function to search for matching subjectid in Parquet file
def search_in_parquet(parquet_file, search_ids):
    df = pd.read_parquet(parquet_file, dtype=str)  # Read as string
    matched_rows = df[df['subjectid'].isin(search_ids)]
    return matched_rows

# Function to process all files, convert to Parquet, search, and merge
def process_files(input_folder, search_ids, output_file):
    all_matches = []
    
    # Step 1: Convert CSV/XLSX to Parquet
    parquet_files = []
    for file in os.listdir(input_folder):
        if file.endswith('.csv') or file.endswith('.xlsx'):
            input_file = os.path.join(input_folder, file)
            parquet_file = os.path.join(input_folder, file.replace('.csv', '.parquet').replace('.xlsx', '.parquet'))
            convert_to_parquet(input_file, parquet_file)
            parquet_files.append(parquet_file)

    # Step 2: Search for matching subjectid in Parquet files
    for parquet_file in parquet_files:
        matched_rows = search_in_parquet(parquet_file, search_ids)
        if not matched_rows.empty:
            all_matches.append(matched_rows)
    
    # Step 3: Merge all matched rows and save as CSV
    if all_matches:
        final_df = pd.concat(all_matches)
        final_df.to_csv(output_file, index=False)
        print(f"Data has been saved to {output_file}")
    else:
        print("No matching data found.")

# Example usage:
input_folder = 'path_to_your_files'  # Folder where CSV/XLSX files are located
output_file = 'output.csv'  # Final output CSV file
process_files(input_folder, search_ids, output_file)

