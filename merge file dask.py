import pandas as pd
from concurrent.futures import ProcessPoolExecutor
import os

# IDs to search for (as strings)
search_ids = {'2345', '12313', '343', '543'}

# Function to process a single file
def process_file(file_path):
    matched_rows = []
    chunksize = 10**5  # Adjust chunk size based on memory availability
    for chunk in pd.read_csv(file_path, chunksize=chunksize, dtype=str):
        # Filter rows where subjectid matches
        matched = chunk[chunk['subjectid'].isin(search_ids)]
        matched_rows.append(matched)
    if matched_rows:
        return pd.concat(matched_rows)
    return pd.DataFrame()  # Return empty dataframe if no match

# Main function to process all files
def process_files_in_parallel(file_paths, output_path):
    all_matches = []
    with ProcessPoolExecutor() as executor:
        results = executor.map(process_file, file_paths)
        for result in results:
            if not result.empty:
                all_matches.append(result)
    # Combine all matched rows and write to CSV
    if all_matches:
        pd.concat(all_matches).to_csv(output_path, index=False)

# File paths
input_folder = 'path_to_your_csv_files'
output_file = 'output.csv'
file_paths = [os.path.join(input_folder, file) for file in os.listdir(input_folder) if file.endswith('.csv')]

# Run the script
process_files_in_parallel(file_paths, output_file)
