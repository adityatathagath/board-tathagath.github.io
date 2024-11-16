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

























import pandas as pd
import os

# Directory containing the CSV files
folder_path = '/path/to/your/csv_files/'

# Get a list of all CSV files in the folder
csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]

# Dictionary to store dataframes dynamically
dfs = {}

# Read each CSV file and store it in the dictionary with its filename (without extension) as the key
for csv_file in csv_files:
    file_path = os.path.join(folder_path, csv_file)
    # Create a key from the filename (remove extension and use it as the variable name)
    df_name = os.path.splitext(csv_file)[0]
    # Read the CSV into a DataFrame and store it in the dictionary
    dfs[df_name] = pd.read_csv(file_path)

# Example: Access a specific DataFrame by the file name (without extension)
print(dfs['file_name'])  # Replace 'file_name' with the actual file name without the '.csv' extension


