import pandas as pd
import os

# Input Excel file path
input_file = "C:/path/to/your/input_file.xlsx"  # Replace with your file path

# Output directory where individual files will be saved
output_directory = "C:/path/to/output/directory"  # Replace with your output directory path

# Specify the column that contains the unique names
name_column = "Name"  # Replace with your column name

# Create output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)

# Read the Excel file
try:
    df = pd.read_excel(input_file)
except Exception as e:
    print(f"Error reading the Excel file: {e}")
    exit()

# Check if the specified column exists
if name_column not in df.columns:
    print(f"Column '{name_column}' not found in the Excel file.")
    exit()

# Get the unique names in the specified column
unique_names = df[name_column].dropna().unique()

# Split the data and save each subset to a separate Excel file
for name in unique_names:
    filtered_df = df[df[name_column] == name]
    output_file = os.path.join(output_directory, f"{name}.xlsx")
    
    try:
        filtered_df.to_excel(output_file, index=False)
        print(f"Saved file: {output_file}")
    except Exception as e:
        print(f"Error saving file for '{name}': {e}")

print("All files have been created successfully.")
