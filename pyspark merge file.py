from pyspark.sql import SparkSession
import glob
import os

def merge_and_filter_csv(path, nodes, column_name, output_file):
    # Debugging: List matching files
    file_pattern = os.path.join(path, "*delta*.csv")
    matching_files = glob.glob(file_pattern)
    print(f"Matching files: {matching_files}")

    if not matching_files:
        print("No CSV files with 'delta' in the name found.")
        return

    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("CSVProcessing") \
        .getOrCreate()

    # Read files into Spark DataFrame
    print(f"Reading files from: {file_pattern}")
    df = spark.read.csv(file_pattern, header=True, inferSchema=True)

    # Debug: Print schema and count
    print(f"Schema: {df.printSchema()}")
    print(f"Number of rows: {df.count()}")

    # Filter rows based on specific node numbers
    filtered_df = df.filter(df[column_name].isin(nodes))

    # Save filtered data to output
    filtered_df.coalesce(1).write.csv(output_file, header=True, mode="overwrite")
    print(f"Filtered and merged data saved to: {output_file}")

# Example usage
if __name__ == "__main__":
    path = "/path/to/your/folder"
    nodes = [123, 456, 789]
    column_name = "node_num"
    output_file = "output_folder"
    merge_and_filter_csv(path, nodes, column_name, output_file)
