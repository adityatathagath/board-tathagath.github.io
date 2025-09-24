# This script generates a fully formula-driven Excel workbook for Historical VaR analysis.
# You can open and use it in Excel. Populate only the "Map" and "Data" sheets; everything else updates via formulas.

import xlsxwriter
from datetime import datetime

path = "/mnt/data/Historic_VaR_Workbook.xlsx"
wb = xlsxwriter.Workbook(path)

# Common formats
title = wb.add_format({"bold": True, "font_size": 14})
hdr = wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1})
cell = wb.add_format({"border": 1})
num = wb.add_format({"border": 1, "num_format": "0.00"})
pct = wb.add_format({"border": 1, "num_format": "0.00%"})
note = wb.add_format({"italic": True, "font_color": "#555555"})
big_num = wb.add_format({"bold": True, "font_size": 16, "num_format": "0.00"})
big_pct = wb.add_format({"bold": True, "font_size": 16, "num_format": "0.00%"})
section = wb.add_format({"bold": True, "bg_color": "#E6F2FF", "border": 1})

# ========== ReadMe ==========
ws = wb.add_worksheet("ReadMe")
ws.set_column("A:A", 110)
ws.write("A1", "Historical VaR Workbook — Instructions", title)
ws.write("A3", "Goal:", section)
ws.write("A4", "Provide a fully formula-based, dynamic template to compute Historical VaR at portfolio, asset-class (desk), and risk-factor levels from user-supplied time series.", cell)
ws.write("A6", "Inputs you provide:", section)
ws.write("A7", "1) Map sheet: a table with AssetClass, RiskFactor, Exposure (optional; leave blank → treated as 1).", cell)
ws.write("A8", "2) Data sheet: paste daily time series with headers: Date, then one column per RiskFactor. Values should be daily P&L per unit exposure or daily return × notional so that summing Exposure×Series yields daily portfolio P&L.", cell)
ws.write("A10", "Everything else is formula-driven. You can change confidence and horizon in Setup.", cell)
ws.write("A12", "Definitions (used in this file):", section)
defs = [
    "VaR_q: The q-quantile loss over the chosen horizon from the empirical distribution of historical daily P&L. Reported as a positive number.",
    "Portfolio VaR: VaR of the total portfolio daily P&L series (sum across mapped risk factors × exposures).",
    "Desk (AssetClass) VaR: VaR of the sum of risk-factor P&Ls within that asset class.",
    "Risk-factor VaR: VaR of an individual factor’s P&L series.",
    "Incremental VaR (iVaR) of factor i: VaR(Portfolio) − VaR(Portfolio without factor i).",
    "Marginal VaR (mVaR) of factor i: Approximate derivative of portfolio VaR w.r.t. exposure of i. Computed here by a small bump ε to factor i’s exposure.",
    "Component VaR (cVaR) of factor i: Exposure_i × mVaR_i. Sums approximately to portfolio VaR for small ε.",
    "“Delta CoVaR” here is reported as mVaR (the change in VaR per unit exposure)."
]
for i, d in enumerate(defs, start=13):
    ws.write(f"A{i}", f"• {d}", cell)

ws.write("A22", "Notes:", section)
notes = [
    "Historical VaR uses your pasted daily P&L series directly. No distributional assumptions.",
    "Choose 95% or 99% in Setup. Horizon H scales VaR by √H if enabled.",
    "If some factor is missing data on a date, leave the cell blank (not 0). That date will be excluded automatically for that factor via IF/NA filters.",
    "All VaR numbers are in the same units as the input series (e.g., currency)."
]
for i, d in enumerate(notes, start=23):
    ws.write(f"A{i}", f"• {d}", cell)

ws.write("A29", f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", note)

# ========== Setup ==========
ws = wb.add_worksheet("Setup")
ws.set_column("A:B", 30)
ws.write("A1", "Global Settings", title)
ws.write("A3", "Confidence level", hdr)
ws.write("B3", "0.99", num)
ws.write("A4", "Alt confidence (for display)", hdr)
ws.write("B4", "0.95", num)
ws.write("A6", "Horizon (days)", hdr)
ws.write("B6", 1, num)
ws.write("A7", "Horizon scaling on? (TRUE/FALSE)", hdr)
ws.write("B7", "TRUE")
ws.write("A9", "Epsilon for marginal VaR bump", hdr)
ws.write("B9", 0.01, num)
ws.write("A11", "Notes", section)
ws.write("A12", "Set confidence to 0.99 or 0.95. The Dashboard shows both. Horizon scales VaR by SQRT(H) if enabled.", note)

# ========== Map ==========
ws = wb.add_worksheet("Map")
ws.set_column("A:A", 20)
ws.set_column("B:B", 30)
ws.set_column("C:C", 15)
ws.write_row("A1", ["AssetClass", "RiskFactor", "Exposure"], hdr)
# Provide sample stub rows
for r in range(2, 12):
    ws.write(f"A{r}", "")
    ws.write(f"B{r}", "")
    ws.write_formula(f"C{r}", '=IF(B{0}="",,1)'.format(r))  # default exposure 1 if risk factor present

# Named ranges sizes (pre-allocated)
map_rows = 1000
ws.autofilter(0, 0, map_rows, 2)

# ========== Data ==========
ws = wb.add_worksheet("Data")
ws.set_column("A:A", 14)
ws.set_column("B:Z", 16)
ws.write("A1", "Date", hdr)
# leave factor headers for user to paste
for col in range(1, 26):
    ws.write(0, col, "", hdr)
# pre-allocate rows
for r in range(2, 1202):
    ws.write_datetime(r-1, 0, datetime(2000,1,1), wb.add_format({"num_format": "yyyy-mm-dd"}))
    for c in range(1, 26):
        ws.write_blank(r-1, c, None, cell)
ws.write("A1205", "Paste your daily time series here. Headers must match RiskFactor names exactly.", note)

# ========== Calc ==========
ws = wb.add_worksheet("Calc")
ws.set_column("A:A", 14)
ws.set_column("B:E", 18)
ws.set_column("G:ZZ", 14)

ws.write("A1", "Derived series and VaR calculations", title)

# Helper area: counts and dynamic height
ws.write("A3", "N_obs", hdr)
# Count dates based on non-blank in Data!A
ws.write_formula("B3", "=COUNTA(Data!A:A)-1")

ws.write("A4", "Conf99", hdr)
ws.write_formula("B4", "=Setup!B3")
ws.write("A5", "Conf95", hdr)
ws.write_formula("B5", "=Setup!B4")
ws.write("A6", "H_days", hdr)
ws.write_formula("B6", "=Setup!B6")
ws.write("A7", "ScaleOn", hdr)
ws.write_formula("B7", "=Setup!B7")
ws.write("A8", "ScaleFactor", hdr)
ws.write_formula("B8", "=IF(B7, SQRT(B6), 1)")
ws.write("A9", "Eps", hdr)
ws.write_formula("B9", "=Setup!B9")

# Bring Map table into Calc for dynamic arrays
ws.write_row("A12", ["Row", "AssetClass", "RiskFactor", "Exposure"], hdr)
for r in range(13, 13+map_rows):
    i = r-11  # 2..
    ws.write_formula(r-1, 0, f"=ROW()-12")  # Row
    ws.write_formula(r-1, 1, f"=IF(Map!A{i}=\"\",\"\",Map!A{i})")
    ws.write_formula(r-1, 2, f"=IF(Map!B{i}=\"\",\"\",Map!B{i})")
    ws.write_formula(r-1, 3, f"=IF(Map!B{i}=\"\",\"\",IF(Map!C{i}=\"\",1,Map!C{i}))", num)

# Date column
ws.write("F12", "Date", hdr)
# Dynamic date range using OFFSET from Data!A2 down N_obs rows
ws.write_formula("F13", "=OFFSET(Data!$A$2,0,0,$B$3,1)")

# Pull each factor series by matching header in Data row 1
ws.write("H11", "Risk-factor series (per unit exposure)", hdr)
ws.write("G12", "RiskFactor", hdr)
ws.write("H12", "Series_start_cell", hdr)
ws.write("I12", "Series_range", hdr)

for r in range(13, 13+map_rows):
    rf_cell = f"$C{r}"
    # Find column of risk factor header in Data!1:1
    ws.write_formula(r-1, 6, f"={rf_cell}")  # RiskFactor
    ws.write_formula(r-1, 7, f"=IF({rf_cell}=\"\",\"\",INDEX(Data!1:1,1,MATCH({rf_cell},Data!1:1,0)))")
    # Build the dynamic range for the factor series over N_obs rows using OFFSET from Data!B2 etc.
    # Column index:
    # MATCH(rf, Data!1:1, 0) gives column index; use INDEX to get the top-left cell then OFFSET height N_obs
    ws.write_formula(r-1, 8, f"=IF({rf_cell}=\"\",\"\",OFFSET(INDEX(Data!$A:$Z,2,MATCH({rf_cell},Data!1:1,0)),0,0,$B$3,1))")

# Portfolio P&L series: sum across factors of Exposure × factor series by row
ws.write("K11", "Per-date P&L series", hdr)
ws.write("K12", "Portfolio", hdr)
ws.write("L12", "Helper_sum", hdr)

# Create a vertical area K13:K(13+N_obs-1) portfolio series
# For row t from 1..N_obs, pick the t-th element of each factor series and sumproduct with exposures
for t in range(1, 1001):  # up to 1000 observations shown; formulas auto-ignore beyond N_obs
    row = 12 + t
    # value_t(rf i) = INDEX(Series_range_i, t)
    # Sum across i: SUMPRODUCT( Exposure_i , INDEX(Series_range_i, t) )
    ws.write_formula(row-1, 10, f"=IF($B$3>={t},SUMPRODUCT($D$13:$D${12+map_rows},INDEX($I$13:$I${12+map_rows},{t})),NA())", num)

# Desk series: sum per asset class
ws.write("N11", "Desk series", hdr)
ws.write("N12", "AssetClass", hdr)
ws.write("O12", "Per-date series (vector)", hdr)
for r in range(13, 13+map_rows):
    ac_cell = f"$B{r}"
    ws.write_formula(r-1, 13, f"={ac_cell}")
    # Build series as SUM of factor series of same asset class per date t: SUMIFS over ranges element-wise.
    # Implement per t using SUMPRODUCT with binary mask for class match.
    ws.write_formula(r-1, 14, f"=IF({ac_cell}=\"\",\"\",MMULT(TRANSPOSE(ROW($F$13:INDEX($F:$F,$B$3+12))^0),"
                               f"($B$13:$B${12+map_rows}={ac_cell})*($I$13:$I${12+map_rows})*$D$13:$D${12+map_rows}))")

# VaR functions area
ws.write("R11", "VaR calculations", hdr)
ws.write_row("R12", ["SeriesName", "VaR95", "VaR99"], hdr)

# Portfolio VaR
ws.write("R13", "Portfolio", cell)
# VaR is percentile of losses. Use PERCENTILE.INC of negative series then scale.
ws.write_formula("S13", "=PERCENTILE.INC(-FILTER($K$13:$K$1012,ISNUMBER($K$13:$K$1012)),1-$B$5)*$B$8", num)
ws.write_formula("T13", "=PERCENTILE.INC(-FILTER($K$13:$K$1012,ISNUMBER($K$13:$K$1012)),1-$B$4)*$B$8", num)

# Risk-factor level VaR table
ws.write("R15", "RiskFactor VaR table", section)
ws.write_row("R16", ["RiskFactor", "VaR95", "VaR99", "iVaR95", "iVaR99", "mVaR95", "mVaR99", "cVaR95", "cVaR99"], hdr)

for r in range(0, 50):  # first 50 risk factors displayed
    src = 13 + r
    out = 17 + r
    # risk factor name
    ws.write_formula(out-1, 17, f"=IF($C{src}=\"\",\"\",$C{src})")
    # factor series VaR
    ws.write_formula(out-1, 18, f"=IF($C{src}=\"\",\"\",PERCENTILE.INC(-FILTER(INDEX($I{src}:$I{src},0,1),"
                                 f"ISNUMBER(INDEX($I{src}:$I{src},0,1))),1-$B$5)*$B$8)", num)
    ws.write_formula(out-1, 19, f"=IF($C{src}=\"\",\"\",PERCENTILE.INC(-FILTER(INDEX($I{src}:$I{src},0,1),"
                                 f"ISNUMBER(INDEX($I{src}:$I{src},0,1))),1-$B$4)*$B$8)", num)
    # Portfolio without factor i: port_minus_i = portfolio - exposure_i * series_i
    # Build per-date vector: FILTER valid K13:K1012 minus exposure*factor series; then VaR
    ws.write_formula(out-1, 20, f"=IF($C{src}=\"\",\"\",PERCENTILE.INC(-FILTER($K$13:$K$1012-($D{src}*INDEX($I{src}:$I{src},0,1)),"
                                 f"ISNUMBER($K$13:$K$1012)*ISNUMBER(INDEX($I{src}:$I{src},0,1))),1-$B$5)*$B$8)", num)
    ws.write_formula(out-1, 21, f"=IF($C{src}=\"\",\"\",PERCENTILE.INC(-FILTER($K$13:$K$1012-($D{src}*INDEX($I{src}:$I{src},0,1)),"
                                 f"ISNUMBER($K$13:$K$1012)*ISNUMBER(INDEX($I{src}:$I{src},0,1))),1-$B$4)*$B$8)", num)
    # iVaR = PortVaR - VaR(port minus i)
    ws.write_formula(out-1, 20, f"=IF($C{src}=\"\",\"\",$T$13-"
                                 f"PERCENTILE.INC(-FILTER($K$13:$K$1012-($D{src}*INDEX($I{src}:$I{src},0,1)),"
                                 f"ISNUMBER($K$13:$K$1012)*ISNUMBER(INDEX($I{src}:$I{src},0,1))),1-$B$4)*$B$8)", num)
    ws.write_formula(out-1, 21, f"=IF($C{src}=\"\",\"\",$S$13-"
                                 f"PERCENTILE.INC(-FILTER($K$13:$K$1012-($D{src}*INDEX($I{src}:$I{src},0,1)),"
                                 f"ISNUMBER($K$13:$K$1012)*ISNUMBER(INDEX($I{src}:$I{src},0,1))),1-$B$5)*$B$8)", num)
    # mVaR via small bump ε: VaR(port with D_i*(1+eps)) - VaR(port)
    ws.write_formula(out-1, 22, f"=IF($C{src}=\"\",\"\",("
                                 f"PERCENTILE.INC(-FILTER($K$13:$K$1012+($D{src}*$B$9*INDEX($I{src}:$I{src},0,1)),"
                                 f"ISNUMBER($K$13:$K$1012)*ISNUMBER(INDEX($I{src}:$I{src},0,1))),1-$B$5)*$B$8 - $S$13)/$B$9", num)
    ws.write_formula(out-1, 23, f"=IF($C{src}=\"\",\"\",("
                                 f"PERCENTILE.INC(-FILTER($K$13:$K$1012+($D{src}*$B$9*INDEX($I{src}:$I{src},0,1)),"
                                 f"ISNUMBER($K$13:$K$1012)*ISNUMBER(INDEX($I{src}:$I{src},0,1))),1-$B$4)*$B$8 - $T$13)/$B$9", num)
    # cVaR = Exposure * mVaR
    ws.write_formula(out-1, 24, f"=IF($C{src}=\"\",\"\",$D{src}*X{out})", num)  # 95
    ws.write_formula(out-1, 25, f"=IF($C{src}=\"\",\"\",$D{src}*Y{out})", num)  # 99

# Desk table
desk_start = 70
ws.write(f"R{desk_start}", "Desk VaR table", section)
ws.write_row(desk_start+1-1, 17, ["AssetClass", "VaR95", "VaR99"], hdr)

for r in range(0, 30):  # first 30 desks
    src = 13 + r
    out = desk_start + 2 + r
    ws.write_formula(out-1, 17, f"=IF($B{src}=\"\",\"\",$B{src})")
    # Desk series vector lives in O{src} as an array; compute VaR
    ws.write_formula(out-1, 18, f"=IF($B{src}=\"\",\"\",PERCENTILE.INC(-FILTER(INDEX($O{src}:$O{src},0,1),"
                                 f"ISNUMBER(INDEX($O{src}:$O{src},0,1))),1-$B$5)*$B$8)", num)
    ws.write_formula(out-1, 19, f"=IF($B{src}=\"\",\"\",PERCENTILE.INC(-FILTER(INDEX($O{src}:$O{src},0,1),"
                                 f"ISNUMBER(INDEX($O{src}:$O{src},0,1))),1-$B$4)*$B$8)", num)

# ========== Dashboard ==========
ws = wb.add_worksheet("Dashboard")
ws.set_column("A:D", 28)
ws.set_column("F:L", 18)

ws.write("A1", "Historical VaR Dashboard", title)
ws.write("A3", "Portfolio VaR (scaled)", section)
ws.write("A4", "VaR 95%", hdr)
ws.write_formula("B4", "=Calc!S13", big_num)
ws.write("A5", "VaR 99%", hdr)
ws.write_formula("B5", "=Calc!T13", big_num)
ws.write("A7", "Confidence 95% equals Setup!B4, confidence 99% equals Setup!B3. Scaling uses √H if enabled.", note)

# Desk table
ws.write("A9", "By Asset Class", section)
ws.write_row("A10", ["AssetClass", "VaR95", "VaR99"], hdr)
# Bring first 15 desks
for i in range(0, 15):
    ws.write_formula(10+i, 0, f"=Calc!R{70+2+i}")
    ws.write_formula(10+i, 1, f"=Calc!S{70+2+i}", num)
    ws.write_formula(10+i, 2, f"=Calc!T{70+2+i}", num)

# Risk factor table
ws.write("F9", "Top Risk Factors by cVaR (99%)", section)
ws.write_row("F10", ["RiskFactor", "cVaR99", "mVaR99", "iVaR99", "VaR99"], hdr)
for i in range(0, 20):
    row = 17 + i
    ws.write_formula(10+i, 5, f"=Calc!R{row}")
    ws.write_formula(10+i, 6, f"=Calc!Z{row}", num)
    ws.write_formula(10+i, 7, f"=Calc!Y{row}", num)
    ws.write_formula(10+i, 8, f"=Calc!U{row}", num)
    ws.write_formula(10+i, 9, f"=Calc!T{row}", num)

# Charts
chart = wb.add_chart({"type": "column"})
chart.add_series({
    "name":       "VaR 95%",
    "categories": "=Dashboard!$A$11:$A$25",
    "values":     "=Dashboard!$B$11:$B$25",
})
chart.add_series({
    "name":       "VaR 99%",
    "categories": "=Dashboard!$A$11:$A$25",
    "values":     "=Dashboard!$C$11:$C$25",
})
chart.set_title({"name": "Asset Class VaR"})
chart.set_legend({"position": "bottom"})
ws.insert_chart("A27", chart, {"x_scale": 1.2, "y_scale": 1.2})

chart2 = wb.add_chart({"type": "column"})
chart2.add_series({
    "name":       "cVaR99",
    "categories": "=Dashboard!$F$11:$F$30",
    "values":     "=Dashboard!$G$11:$G$30",
})
chart2.set_title({"name": "Top Risk Factors by cVaR (99%)"})
chart2.set_legend({"position": "none"})
ws.insert_chart("F27", chart2, {"x_scale": 1.2, "y_scale": 1.2})

wb.close()

path
