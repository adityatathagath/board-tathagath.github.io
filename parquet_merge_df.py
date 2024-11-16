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


















import os
from pyspark.sql import SparkSession
from pathlib import Path

# Manually set paths for Spark and Java if needed
os.environ["JAVA_HOME"] = "C:/Program Files/Java/jdk1.8.0_291"  # Replace with your Java path
os.environ["SPARK_HOME"] = "C:/path/to/spark"  # Replace with your Spark path
os.environ["HADOOP_HOME"] = os.environ["SPARK_HOME"]

# Step 1: Initialize PySpark session
spark = SparkSession.builder \
    .appName("Merge CSV Files with All Columns as Strings") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()

print("Spark session created successfully!")

# Step 2: Configuration variables
input_directory = "C:/path/to/your/csv/files"  # Replace with the directory containing your CSV files
output_file = "C:/path/to/output/merged_file.csv"  # Replace with your desired output file path
filter_column = "node_num"  # Column to filter on
filter_values = ["101", "202", "303"]  # Replace with your list of values to filter as strings

# Step 3: Identify CSV files with "delta" in their filenames
csv_files = [str(file) for file in Path(input_directory).rglob("*delta*.csv")]

if not csv_files:
    print("No CSV files with 'delta' in the name found in the specified directory.")
    spark.stop()
    exit()

print(f"Found {len(csv_files)} files to process.")

# Step 4: Read, filter, and collect DataFrames
all_dfs = []

for file in csv_files:
    print(f"Reading file: {file}")
    
    # Read the CSV file with all columns as strings
    df = spark.read.csv(file, header=True, inferSchema=False)
    
    # Check if the filter column exists in the DataFrame
    if filter_column not in df.columns:
        print(f"Column '{filter_column}' not found in {file}. Skipping this file.")
        continue

    # Filter rows where the filter_column contains values in filter_values
    filtered_df = df.filter(df[filter_column].isin(filter_values))
    
    # Append the filtered DataFrame to the list
    all_dfs.append(filtered_df)

# Step 5: Merge all DataFrames
if all_dfs:
    merged_df = all_dfs[0]
    for df in all_dfs[1:]:
        merged_df = merged_df.union(df)

    print("All relevant files merged successfully!")

    # Step 6: Write the merged DataFrame to a CSV
    merged_df.write.csv(output_file, header=True, mode="overwrite")
    print(f"Merged data saved to {output_file}")
else:
    print("No data matched the specified filters.")

# Stop the Spark session
spark.stop()
print("Spark session stopped.")


