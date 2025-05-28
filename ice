import xlwings as xw

def copy_range_with_format(src_range, dest_range):
    # Copy values
    dest_range.value = src_range.value

    # Copy formatting cell-by-cell
    for i in range(src_range.rows.count):
        for j in range(src_range.columns.count):
            src_cell = src_range[i, j]
            dest_cell = dest_range[i, j]
            dest_cell.api.Interior.Color = src_cell.api.Interior.Color  # background color
            dest_cell.api.Font.Color = src_cell.api.Font.Color  # font color
            dest_cell.api.Font.Bold = src_cell.api.Font.Bold
            dest_cell.api.Font.Size = src_cell.api.Font.Size
            dest_cell.api.Font.Name = src_cell.api.Font.Name
            # Borders (optional)
            for b in range(7, 13):  # Excel border indices 7–12
                dest_cell.api.Borders(b).LineStyle = src_cell.api.Borders(b).LineStyle
                dest_cell.api.Borders(b).Weight = src_cell.api.Borders(b).Weight
                dest_cell.api.Borders(b).Color = src_cell.api.Borders(b).Color

# Load source .xlsb file
source_path = r"C:\path\to\ice_vectors.xlsb"
wb = xw.Book(source_path)

# Refresh data sheets
wb.sheets['ice'].calculate()
wb.sheets['ice_prev_cob'].calculate()
summary = wb.sheets['summary']
summary.calculate()

# Set 'Var' to 'DVaR'
summary.range('C3').value = "DVaR"

# Create output workbook
output_wb = xw.Book()
output_wb.sheets[0].name = 'DVaR'

for rank in range(1, 4):
    summary.range('C2').value = rank  # Set P&L Rank
    summary.calculate()

    # For rank = 1, copy AA14:BB54 to sheet 'DVaR'
    if rank == 1:
        src_range1 = summary.range('AA14:BB54')
        dest_range1 = output_wb.sheets['DVaR'].range('A1')
        copy_range_with_format(src_range1, dest_range1)

    # Copy B13:Y140 to new sheet DVaR PLx
    sheet_name = f"DVaR PL{rank}"
    output_wb.sheets.add(name=sheet_name)
    src_range2 = summary.range('B13:Y140')
    dest_range2 = output_wb.sheets[sheet_name].range('A1')
    copy_range_with_format(src_range2, dest_range2)

# Save and close everything
output_path = r"C:\path\to\output\DVaR.xlsx"
output_wb.save(output_path)
output_wb.close()
wb.close()