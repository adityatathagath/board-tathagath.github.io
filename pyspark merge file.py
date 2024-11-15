from pyspark.sql import SparkSession

def merge_and_filter_csv(path, nodes, column_name, output_file):
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("CSVProcessing") \
        .getOrCreate()

    # Read all CSV files that contain "delta" in their name
    file_pattern = f"{path}/*delta*.csv"
    print(f"Reading files matching pattern: {file_pattern}")
    
    # Load all matching CSV files into a Spark DataFrame
    df = spark.read.csv(file_pattern, header=True, inferSchema=True)

    # Filter rows based on the specified nodes
    filtered_df = df.filter(df[column_name].isin(nodes))

    # Save the filtered data to a single CSV file
    filtered_df.coalesce(1).write.csv(output_file, header=True, mode="overwrite")
    print(f"Filtered and merged data saved to: {output_file}")

# Example usage
if __name__ == "__main__":
    # Define the folder path where CSV files are located
    path = "path_to_your_folder"  # Update with the actual path

    # List of node numbers to search for
    nodes = [123, 456, 789]  # Replace with your specific node numbers

    # The column name to search for nodes in
    column_name = "node_num"  # Replace with your column name

    # Output folder for the merged file
    output_file = "output_folder"  # Spark writes to a folder; update with your desired location

    # Call the function to merge and filter the CSV files
    merge_and_filter_csv(path, nodes, column_name, output_file)
