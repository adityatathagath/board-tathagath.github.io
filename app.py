import os, io, json, yaml
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from parser import EMFlowsParser
from insights import prep_timeseries, compute_rolls, divergence_equity_vs_bond, generate_alerts
from digitizer import render_pdf_page, relative_crop, extract_bars_series, extract_line_series, load_template, save_template

st.set_page_config(page_title="EM Flows – Offline Deep Insights", layout="wide")

@st.cache_data(show_spinner=False)
def parse_many(pdf_bytes_list, names):
    parser = EMFlowsParser("config.yml")
    frames = []
    dates = []
    os.makedirs("data", exist_ok=True)
    for b, nm in zip(pdf_bytes_list, names):
        path = f"data/{nm}"
        with open(path, "wb") as f:
            f.write(b.read())
        as_of, df = parser.parse_pdf(path)
        dates.append(as_of)
        frames.append(df)
    if frames:
        out = pd.concat(frames, ignore_index=True)
    else:
        out = pd.DataFrame(columns=["as_of_date","level","region","country","asset_class","measure","value","unit","source_pdf"])
    return out

def plot_ts(ts, key_cols, title):
    d = ts.groupby(key_cols + ["as_of_date"], dropna=False)["flow_wow_usd_mn"].sum().reset_index()
    fig = px.line(d, x="as_of_date", y="flow_wow_usd_mn", color=key_cols[-1] if key_cols else None, markers=True, title=title)
    st.plotly_chart(fig, use_container_width=True)

def load_cfg():
    with open("config.yml","r") as f:
        return yaml.safe_load(f)

def save_cfg(cfg):
    with open("config.yml","w") as f:
        yaml.safe_dump(cfg, f)

st.title("EM Flows – Offline Deep Insights")
st.caption("All processing is local. No internet calls.")

with st.sidebar:
    st.header("PDF Ingest (tables/text)")
    files = st.file_uploader("Drop weekly EM Flows PDFs", type=["pdf"], accept_multiple_files=True)
    if st.button("Ingest & Parse", disabled=not files):
        df = parse_many(files, [f.name for f in files])
        if df.empty:
            st.error("No recognizable tables extracted. Use Digitizer tab for charts.")
        else:
            os.makedirs("data", exist_ok=True)
            df.to_parquet("data/flows_raw.parquet", index=False)
            st.success(f"Ingest complete. Rows: {len(df):,} saved to data/flows_raw.parquet")

    st.divider()
    st.header("Digitizer Templates")
    cfg = load_cfg()
    if st.button("Reset to defaults"):
        # reload from disk (noop here)
        st.warning("Defaults restored from config.yml (if you edited, re-run the app).")

tabs = st.tabs(["Overview (Parsed Tables)", "Digitizer (Charts → Data)", "Insights & Alerts", "Download Weekly Note"])

with tabs[0]:
    if not os.path.exists("data/flows_raw.parquet"):
        st.info("No parsed tables yet. Use **Ingest & Parse** on the left, or go to **Digitizer**.")
    else:
        df = pd.read_parquet("data/flows_raw.parquet")
        st.subheader("Normalized sample")
        st.dataframe(df.head(50), use_container_width=True)

        base = prep_timeseries(df)
        ts = compute_rolls(base)

        with st.expander("Filters", expanded=True):
            level = st.multiselect("Level", sorted(ts["level"].dropna().unique()))
            region = st.multiselect("Region", sorted(ts["region"].dropna().unique()))
            asset = st.multiselect("Asset Class", sorted(ts["asset_class"].dropna().unique()))
            country = st.multiselect("Country", sorted(ts["country"].dropna().unique()))

        mask = pd.Series(True, index=ts.index)
        if level: mask &= ts["level"].isin(level)
        if region: mask &= ts["region"].isin(region)
        if asset: mask &= ts["asset_class"].isin(asset)
        if country: mask &= ts["country"].isin(country)
        tsf = ts[mask].copy()
        if tsf.empty:
            st.warning("No data for current filter.")
        else:
            group_keys = []
            if country: group_keys = ["country","asset_class"]
            elif region: group_keys = ["region","asset_class"]
            else: group_keys = ["level","asset_class"]
            plot_ts(tsf, [k for k in group_keys if k in tsf.columns], "Weekly Net Flows (USD mn)")
            st.subheader("Rolling Sums (4W / 12W / 52W)")
            agg = tsf.groupby(group_keys + ["as_of_date"], dropna=False)[["flow_wow_usd_mn","roll_4w","roll_12w","roll_52w"]].sum().reset_index()
            st.dataframe(agg.tail(1000), use_container_width=True)

with tabs[1]:
    st.subheader("Digitizer (Charts → Data) – template-based, works offline")
    st.write("**Step 1.** Upload one PDF. **Step 2.** Pick Figure (1–9), adjust crop and Y-axis range, tune colors, then click **Extract**.")
    up = st.file_uploader("Upload a single PDF to digitize", type=["pdf"], accept_multiple_files=False, key="digpdf")
    if up:
        # Save temp pdf
        os.makedirs("data", exist_ok=True)
        pdf_path = f"data/_digitize.pdf"
        with open(pdf_path, "wb") as f:
            f.write(up.read())

        cfg = load_cfg()
        dcfg = cfg.get("digitizer", {})
        dpi = int(dcfg.get("dpi", 220))
        page_index = st.number_input("Page index (0-based)", min_value=0, value=int(dcfg.get("crops", {}).get("FIGURE 1", {}).get("page", 2)), step=1)
        img = render_pdf_page(pdf_path, page_index, dpi=dpi)
        st.image(img, caption=f"Page {page_index}", use_column_width=True)

        figure = st.selectbox("Which figure?", ["FIGURE 1","FIGURE 2","FIGURE 3","FIGURE 4","FIGURE 5","FIGURE 6","FIGURE 7","FIGURE 8","FIGURE 9"])
        crop_defaults = dcfg.get("crops", {}).get(figure, {"left":0.06,"top":0.10,"right":0.95,"bottom":0.58,"page":page_index})
        left = st.slider("Crop left", 0.0, 0.99, float(crop_defaults.get("left",0.06)), 0.001)
        top = st.slider("Crop top", 0.0, 0.99, float(crop_defaults.get("top",0.10)), 0.001)
        right = st.slider("Crop right", 0.01, 1.0, float(crop_defaults.get("right",0.95)), 0.001)
        bottom = st.slider("Crop bottom", 0.01, 1.0, float(crop_defaults.get("bottom",0.58)), 0.001)

        plot_img, box = relative_crop(img, left, top, right, bottom)
        st.image(plot_img, caption=f"{figure} – Cropped plot area", use_column_width=True)

        yr_defaults = dcfg.get("y_ranges", {}).get(figure, {"y_min":-10.0,"y_max":46.0,"units":"$bn"})
        y_min = st.number_input("Y min (units on y-axis, negative allowed)", value=float(yr_defaults.get("y_min",-10.0)))
        y_max = st.number_input("Y max", value=float(yr_defaults.get("y_max",46.0)))

        hsv_cfg = dcfg.get("hsv_thresholds", {})
        series_count = st.number_input("Number of series to extract (1 for line; 1-3 for bars)", min_value=1, max_value=3, value=2)
        series_names, series_thresholds = [], []

        def hsv_ui(label, defaults):
            h1 = st.slider(f"{label} H min", 0, 179, int(defaults.get("h_min",0)))
            h2 = st.slider(f"{label} H max", 0, 179, int(defaults.get("h_max",179)))
            s1 = st.slider(f"{label} S min", 0, 255, int(defaults.get("s_min",0)))
            s2 = st.slider(f"{label} S max", 0, 255, int(defaults.get("s_max",255)))
            v1 = st.slider(f"{label} V min", 0, 255, int(defaults.get("v_min",0)))
            v2 = st.slider(f"{label} V max", 0, 255, int(defaults.get("v_max",255)))
            return {"h_min":h1,"h_max":h2,"s_min":s1,"s_max":s2,"v_min":v1,"v_max":v2}

        presets = list(hsv_cfg.keys())
        for i in range(series_count):
            st.markdown(f"**Series {i+1}**")
            preset = st.selectbox(f"HSV preset for series {i+1}", presets, index=min(i,len(presets)-1) if presets else 0)
            th = hsv_ui(preset, hsv_cfg.get(preset, {"h_min":0,"h_max":179,"s_min":0,"s_max":255,"v_min":0,"v_max":255}))
            nm = st.text_input(f"Series {i+1} name", value=preset)
            series_names.append(nm)
            series_thresholds.append(th)

        mode = st.selectbox("Extraction mode", ["Bars (weekly columns)","Line (time series)"])

        if st.button("Extract"):
            all_series = {}
            for nm, th in zip(series_names, series_thresholds):
                if mode.startswith("Bars"):
                    vals, baseline, mask = extract_bars_series(plot_img, th, y_min, y_max)
                else:
                    vals, baseline, mask = extract_line_series(plot_img, th, y_min, y_max)
                st.image(mask, caption=f"Mask preview – {nm}", use_column_width=True, clamp=True)
                all_series[nm] = vals

            # Align lengths (pad with NaN to max length)
            max_len = max(len(v) for v in all_series.values())
            for k in all_series.keys():
                if len(all_series[k]) < max_len:
                    all_series[k] = all_series[k] + [np.nan]*(max_len-len(all_series[k]))

            out = pd.DataFrame(all_series)
            # Add week index as proxy for date; user can attach actual 'as_of_date' on merge with parsed date or manual input.
            out["week_index"] = np.arange(len(out))
            st.dataframe(out.head(200), use_container_width=True)

            # Save to parquet so Insights tab can pick it (keyed by figure)
            os.makedirs("data/digitized", exist_ok=True)
            out.to_parquet(f"data/digitized/{figure.replace(' ','_')}.parquet", index=False)
            st.success(f"Saved to data/digitized/{figure.replace(' ','_')}.parquet")

        if st.button("Save as Template"):
            # Persist crop + y-range back into config.yml
            cfg = load_cfg()
            dcfg = cfg.get("digitizer", {})
            crops = dcfg.get("crops", {})
            crops[figure] = {"page": int(page_index), "left": float(left), "top": float(top), "right": float(right), "bottom": float(bottom)}
            dcfg["crops"] = crops
            yr = dcfg.get("y_ranges", {})
            yr[figure] = {"y_min": float(y_min), "y_max": float(y_max), "units": "$bn"}
            dcfg["y_ranges"] = yr
            cfg["digitizer"] = dcfg
            save_cfg(cfg)
            st.success("Template saved into config.yml")

with tabs[2]:
    st.subheader("Insights & Alerts")
    # Merge any parsed tables + digitized series we understand
    frames = []
    if os.path.exists("data/flows_raw.parquet"):
        frames.append(pd.read_parquet("data/flows_raw.parquet"))
    # Example mapping: FIGURE 2 bars to Bond sub-classes (user-renamable)
    fig2_path = "data/digitized/FIGURE_2.parquet"
    if os.path.exists(fig2_path):
        df2 = pd.read_parquet(fig2_path)
        # Assume Series names correspond to: Blended, Hard, Local, Total (as configured by user)
        long = df2.reset_index().melt(id_vars=["week_index"], var_name="asset_class", value_name="value")
        long["level"] = "EM"; long["region"] = None; long["country"] = None
        long["measure"] = "WOW"; long["unit"] = "USD mn"; long["source_pdf"] = "digitized"
        # Convert $bn → USD mn (×1000)
        long["value"] = long["value"] * 1000.0
        # Assign pseudo as_of_date using a reference (user can map week_index to dates later)
        long["as_of_date"] = pd.Timestamp.today().normalize()
        frames.append(long[["as_of_date","level","region","country","asset_class","measure","value","unit","source_pdf"]])

    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        base = prep_timeseries(all_df)
        ts = compute_rolls(base)
        st.write("Latest week in combined data:", ts["as_of_date"].max())
        plot_ts(ts, ["level","asset_class"], "Weekly Net Flows (USD mn)")
        div = divergence_equity_vs_bond(ts)
        st.write("Equity vs Bond divergences (latest week, opposite signs):")
        if not div.empty:
            latest_d = div[div["as_of_date"]==div["as_of_date"].max()]
            st.dataframe(latest_d[latest_d["divergence"]==-1], use_container_width=True)
        alerts = generate_alerts(ts)
        st.write("Automated Alerts")
        st.dataframe(pd.DataFrame(alerts), use_container_width=True)
    else:
        st.info("No data yet. Parse tables or digitize charts to populate insights.")

with tabs[3]:
    st.subheader("Download Weekly Note (auto-written)")
    if not os.path.exists("data/flows_raw.parquet") and not os.path.exists("data/digitized/FIGURE_2.parquet"):
        st.info("Need some data first (parse or digitize).")
    else:
        frames = []
        if os.path.exists("data/flows_raw.parquet"):
            frames.append(pd.read_parquet("data/flows_raw.parquet"))
        if os.path.exists("data/digitized/FIGURE_2.parquet"):
            df2 = pd.read_parquet("data/digitized/FIGURE_2.parquet")
            long = df2.reset_index().melt(id_vars=["week_index"], var_name="asset_class", value_name="value")
            long["level"] = "EM"; long["region"] = None; long["country"] = None
            long["measure"] = "WOW"; long["unit"] = "USD mn"; long["source_pdf"] = "digitized"
            long["value"] = long["value"] * 1000.0
            long["as_of_date"] = pd.Timestamp.today().normalize()
            frames.append(long[["as_of_date","level","region","country","asset_class","measure","value","unit","source_pdf"]])
        all_df = pd.concat(frames, ignore_index=True)
        base = prep_timeseries(all_df); ts = compute_rolls(base)

        latest = ts["as_of_date"].max()
        latest_rows = ts[ts["as_of_date"]==latest].sort_values("z_52w")
        top_in = latest_rows.dropna(subset=["z_52w"]).tail(5)
        top_out = latest_rows.dropna(subset=["z_52w"]).head(5)

        import io as _io
        note = _io.StringIO()
        note.write(f"# EM Flows Weekly – {latest.date() if hasattr(latest,'date') else str(latest)}\\n\\n")
        note.write("## Highlights\\n")
        if len(top_in):
            note.write("**Strongest Inflows (z-score):**\\n")
            for _, r in top_in.iterrows():
                lab = r["country"] or r["level"]
                note.write(f"- {lab} / {r['asset_class']}: z={r['z_52w']:.2f}, WoW={r['flow_wow_usd_mn']:.0f}mn, 4W={r['roll_4w']:.0f}mn\\n")
        if len(top_out):
            note.write("\\n**Strongest Outflows (z-score):**\\n")
            for _, r in top_out.iterrows():
                lab = r["country"] or r["level"]
                note.write(f"- {lab} / {r['asset_class']}: z={r['z_52w']:.2f}, WoW={r['flow_wow_usd_mn']:.0f}mn, 4W={r['roll_4w']:.0f}mn\\n")

        st.code(note.getvalue(), language="markdown")
        st.download_button("Download Weekly Note (Markdown)", note.getvalue().encode("utf-8"),
                           file_name="em_flows_weekly_note.md")