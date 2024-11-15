import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

class FileProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Processor")
        self.root.geometry("800x600")
        self.root.configure(bg="#f7f7f7")
        
        # Variables
        self.file_paths = []
        self.selected_files = []
        self.column_name_var = tk.StringVar()
        self.search_values_var = tk.StringVar()
        
        # UI Components
        self.create_widgets()
    
    def create_widgets(self):
        # Heading
        tk.Label(self.root, text="CSV File Processor", font=("Arial", 22, "bold"), fg="#4CAF50", bg="#f7f7f7").grid(row=0, column=0, columnspan=4, pady=10)
        
        # Select Files or Folder Buttons
        ttk.Button(self.root, text="Select Files", command=self.select_files).grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        ttk.Button(self.root, text="Select Folder", command=self.select_folder).grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # File Listbox
        tk.Label(self.root, text="Selected Files:", font=("Arial", 12), bg="#f7f7f7").grid(row=2, column=0, columnspan=4, pady=5)
        self.file_listbox = tk.Listbox(self.root, selectmode=tk.MULTIPLE, width=100, height=5, bg="#e3f2fd", font=("Arial", 10))
        self.file_listbox.grid(row=3, column=0, columnspan=4, padx=10, pady=5)
        
        # Proceed Button
        self.proceed_button = ttk.Button(self.root, text="Proceed", command=self.show_column_selection, state=tk.DISABLED)
        self.proceed_button.grid(row=4, column=0, columnspan=4, pady=10)
        
        # Column Selection Dropdown
        self.column_frame = tk.Frame(self.root, bg="#f7f7f7")
        tk.Label(self.column_frame, text="Select Column:", font=("Arial", 12), bg="#f7f7f7").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.column_dropdown = ttk.Combobox(self.column_frame, state="readonly", width=40)
        self.column_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.column_frame.grid(row=5, column=0, columnspan=4, pady=5)
        self.column_frame.grid_remove()
        
        # Search Input Field
        tk.Label(self.root, text="Enter Search Values (comma-separated):", font=("Arial", 12), bg="#f7f7f7").grid(row=6, column=0, columnspan=4, pady=5)
        self.search_values_entry = tk.Entry(self.root, textvariable=self.search_values_var, width=50, bg="#e3f2fd", font=("Arial", 10))
        self.search_values_entry.grid(row=7, column=0, columnspan=4, pady=5)
        self.search_values_entry.grid_remove()
        
        # Process Button
        self.process_button = ttk.Button(self.root, text="Process Files", command=self.start_processing, state=tk.DISABLED)
        self.process_button.grid(row=8, column=0, columnspan=4, pady=10)
        self.process_button.grid_remove()
        
        # Reset Button
        self.reset_button = ttk.Button(self.root, text="Reset", command=self.reset_app, state=tk.DISABLED)
        self.reset_button.grid(row=9, column=0, columnspan=4, pady=10)
        
        # Footer
        tk.Label(self.root, text="Designed with ❤️ in Python", font=("Arial", 10), bg="#f7f7f7", fg="#888").grid(row=10, column=0, columnspan=4, pady=10)
    
    def select_files(self):
        self.file_paths = filedialog.askopenfilenames(filetypes=[("CSV Files", "*.csv")])
        self.populate_file_listbox()
    
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.csv')]
            self.file_paths = all_files
            self.populate_file_listbox()
    
    def populate_file_listbox(self):
        self.file_listbox.delete(0, tk.END)
        
        for file in self.file_paths:
            self.file_listbox.insert(tk.END, os.path.basename(file))
        
        if self.file_paths:
            self.proceed_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.NORMAL)
        else:
            messagebox.showwarning("No files selected", "Please select at least one CSV file.")
    
    def show_column_selection(self):
        try:
            selected_indices = self.file_listbox.curselection()
            self.selected_files = [self.file_paths[i] for i in selected_indices]
            
            if not self.selected_files:
                raise ValueError("Please select at least one file.")
            
            # Load columns from the first file
            sample_df = pd.read_csv(self.selected_files[0], nrows=1)  # Only load the first row for columns
            self.column_dropdown['values'] = sample_df.columns.tolist()
            self.column_dropdown.current(0)
            
            # Show column dropdown and search input
            self.column_frame.grid()
            self.search_values_entry.grid()
            self.process_button.grid()
            self.process_button.config(state=tk.NORMAL)
        except Exception as e:
            self.show_error(f"Error loading columns: {e}")
    
    def start_processing(self):
        # Disable process button during processing
        self.process_button.config(state=tk.DISABLED)
        
        # Show loading indicator
        loading_label = tk.Label(self.root, text="Processing... Please wait.", font=("Arial", 12, "italic"), fg="#ff5722", bg="#f7f7f7")
        loading_label.grid(row=8, column=0, columnspan=4)
        
        # Process files in a separate thread
        thread = threading.Thread(target=self.process_files, args=(loading_label,))
        thread.start()
    
    def process_files(self, loading_label):
        try:
            selected_column = self.column_dropdown.get()
            search_values = self.search_values_var.get().split(',')
            
            if not selected_column:
                raise ValueError("Please select a column.")
            if not search_values:
                raise ValueError("Please enter search values.")
            
            # Clean up search values
            search_values = [val.strip() for val in search_values]
            
            # Merge data based on search criteria
            merged_df = pd.DataFrame()
            output_file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            
            if not output_file:
                raise ValueError("No output file specified. Process aborted.")
            
            # Process large files in chunks
            self.process_large_files(self.selected_files, selected_column, search_values, output_file)
            
            # Success message
            messagebox.showinfo("Success", f"Merged file saved as {output_file}")
        except Exception as e:
            self.show_error(str(e))
        finally:
            # Remove loading indicator
            loading_label.destroy()
    
    def process_large_files(self, selected_files, selected_column, search_values, output_file_path):
        search_values_set = set(search_values)  # Convert to set for faster lookup
        header_written = False  # To ensure the header is only written once

        for file in selected_files:
            for chunk in pd.read_csv(file, chunksize=50000):  # Read in chunks of 50,000 rows
                if selected_column in chunk.columns:
                    filtered_chunk = chunk[chunk[selected_column].astype(str).isin(search_values_set)]

                    # Write the filtered rows to the output file
                    filtered_chunk.to_csv(output_file_path, mode='a', header=not header_written, index=False)
                    header_written = True  # Set to True after the first write to skip header in subsequent writes

    def reset_app(self):
        self.file_listbox.delete(0, tk.END)
        self.column_dropdown.set("")
        self.column_frame.grid_remove()
        self.search_values_entry.delete(0, tk.END)
        self.search_values_entry.grid_remove()
        self.process_button.grid_remove()
        self.process_button.config(state=tk.DISABLED)
        self.proceed_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.DISABLED)
        self.file_paths = []
        self.selected_files = []
        self.column_name_var.set("")
        self.search_values_var.set("")
    
    def show_error(self, message):
        messagebox.showerror("Error", message)


# Main
if __name__ == "__main__":
    root = tk.Tk()
    app = FileProcessorApp(root)
    root.mainloop()
