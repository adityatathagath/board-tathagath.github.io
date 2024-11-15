import dask.dataframe as dd
import glob
import os

def merge_and_filter_csv(path, nodes, column_name, output_file):
    # Get all CSV files in the folder with "delta" in their name
    file_pattern = os.path.join(path, "*delta*.csv")
    csv_files = glob.glob(file_pattern)

    # Check if no matching files were found
    if not csv_files:
        print("No CSV files with 'delta' in the name found.")
        return

    # Read all CSV files into a Dask DataFrame
    df = dd.read_csv(csv_files)

    # Filter rows based on specific node numbers in the given column
    filtered_df = df[df[column_name].isin(nodes)]

    # Write the merged and filtered data to a new CSV file
    filtered_df.to_csv(output_file, index=False, single_file=True)
    print(f"Filtered and merged data saved to: {output_file}")

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
