import xlwings as xw

# Open the source workbook
source_path = r"C:\path\to\ice_vectors.xlsx"
wb = xw.Book(source_path)

# Refresh sheets
wb.sheets['ice'].calculate()
wb.sheets['ice_prev_cob'].calculate()
summary = wb.sheets['summary']
summary.calculate()

# Set up the new workbook
new_wb = xw.Book()
new_wb.sheets[0].name = "DVaR"

# Input values for Var = DVaR and P&L Rank = 1, 2, 3
summary.range('C3').value = "DVaR"

for rank in range(1, 4):
    summary.range('C2').value = rank
    summary.calculate()

    # For first iteration, copy AA14:BB54 into DVaR
    if rank == 1:
        data1 = summary.range('AA14:BB54').options(ndim=2).value
        new_wb.sheets['DVaR'].range('A1').value = data1
        # Formatting (optional, advanced): retain colors, borders, etc.

    # Copy B13:Y140 to respective DVaR PL sheet
    data2 = summary.range('B13:Y140').options(ndim=2).value
    new_sheet = new_wb.sheets.add(name=f'DVaR PL{rank}')
    new_sheet.range('A1').value = data2
    # Formatting can also be applied here if needed

# Save the output workbook
new_wb.save(r"C:\path\to\output\DVaR.xlsx")
new_wb.close()
wb.close()