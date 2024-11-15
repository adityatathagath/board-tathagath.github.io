import dask.dataframe as dd

def merge_and_filter_csv(path, nodes, column_name, output_file):
    # Step 1: Read all files and treat all columns as strings
    df = dd.read_csv(
        f"{path}/*delta*.csv",
        dtype=str,  # Treat all columns as strings
        na_values=["", "NA", "null"],  # Handle missing values
    )
    
    # Step 2: Filter rows where the specified column matches any of the nodes
    # Convert nodes to strings for comparison
    nodes_str = list(map(str, nodes))
    filtered_df = df[df[column_name].isin(nodes_str)]

    # Step 3: Write the merged and filtered data to a single CSV
    filtered_df.compute().to_csv(output_file, index=False)

# Example usage
if __name__ == "__main__":
    path = "/path/to/your/folder"  # Path to CSV files
    nodes = [123, 456, 789]  # Node numbers to search for
    column_name = "node_num"  # Column to search in
    output_file = "output.csv"
    merge_and_filter_csv(path, nodes, column_name, output_file)
