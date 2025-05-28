import xlwings as xw

def copy_range_with_format(src_range, dest_range):
    values = src_range.value
    dest_range.value = values  # Copy values first

    rows = src_range.rows.count
    cols = src_range.columns.count

    for i in range(rows):
        for j in range(cols):
            try:
                src_cell = src_range.cells[i * cols + j]
                dest_cell = dest_range.cells[i * cols + j]

                dest_cell.api.Interior.Color = src_cell.api.Interior.Color
                dest_cell.api.Font.Color = src_cell.api.Font.Color
                dest_cell.api.Font.Bold = src_cell.api.Font.Bold
                dest_cell.api.Font.Size = src_cell.api.Font.Size
                dest_cell.api.Font.Name = src_cell.api.Font.Name

                for b in range(7, 13):  # Border indices
                    dest_cell.api.Borders(b).LineStyle = src_cell.api.Borders(b).LineStyle
                    dest_cell.api.Borders(b).Weight = src_cell.api.Borders(b).Weight
                    dest_cell.api.Borders(b).Color = src_cell.api.Borders(b).Color

            except Exception as e:
                print(f"Formatting error at cell ({i},{j}): {e}")

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