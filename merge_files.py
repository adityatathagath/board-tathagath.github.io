import os
import glob
import pandas as pd

def merge_and_filter_csv(path, nodes, column_name, output_file):
    # Get all CSV files in the folder with "delta" in their name
    file_pattern = os.path.join(path, "*delta*.csv")
    csv_files = glob.glob(file_pattern)

    # Check if no matching files were found
    if not csv_files:
        print("No CSV files with 'delta' in the name found.")
        return

    # List to store the filtered data from all files
    filtered_data = []

    # Loop through each CSV file and filter data
    for file in csv_files:
        print(f"Processing file: {file}")

        # Read the CSV in chunks to avoid memory issues with large files
        chunk_iter = pd.read_csv(file, chunksize=1000000)  # Adjust chunk size as needed

        for chunk in chunk_iter:
            # Filter rows based on the specific node numbers in the given column
            filtered_chunk = chunk[chunk[column_name].isin(nodes)]
            filtered_data.append(filtered_chunk)

    # Concatenate all filtered chunks into one DataFrame
    if filtered_data:
        merged_data = pd.concat(filtered_data, ignore_index=True)

        # Write the merged and filtered data to a new CSV file
        merged_data.to_csv(output_file, index=False)
        print(f"Filtered and merged data saved to: {output_file}")
    else:
        print("No matching rows found in any of the files.")

# Example usage
if __name__ == "__main__":
    # Define the folder path where CSV files are located
    path = "path_to_your_folder"  # Update with the actual path

    # List of node numbers to search for
    nodes = [123, 456, 789]  # Replace with your specific node numbers

    # The column name to search for nodes in
    column_name = "node_num"  # Replace with your column name

    # Output file name
    output_file = "merged_filtered_data.csv"

    # Call the function to merge and filter the CSV files
    merge_and_filter_csv(path, nodes, column_name, output_file)
