import pandas as pd
import numpy as np

def prep_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["as_of_date"] = pd.to_datetime(df["as_of_date"])
    df = df.dropna(subset=["value"])
    wow_alias = {"WOW","W1","WEEK","FLOW","NETFLOW","USD","FLOWUSD","NET"}
    df["measure"] = df["measure"].str.upper()
    df["is_wow_like"] = df["measure"].isin(wow_alias) | df["measure"].str.contains("WOW|FLOW|USD")
    return df

def compute_rolls(df: pd.DataFrame, keys=("level","region","country","asset_class")) -> pd.DataFrame:
    d = df.copy()
    d = d[d["is_wow_like"]]
    d = d.groupby(list(keys) + ["as_of_date"], dropna=False)["value"].sum().reset_index(name="flow_wow_usd_mn")

    d = d.sort_values("as_of_date")
    d["roll_4w"]  = d.groupby(list(keys), dropna=False)["flow_wow_usd_mn"].transform(lambda s: s.rolling(4, min_periods=2).sum())
    d["roll_12w"] = d.groupby(list(keys), dropna=False)["flow_wow_usd_mn"].transform(lambda s: s.rolling(12, min_periods=3).sum())
    d["roll_52w"] = d.groupby(list(keys), dropna=False)["flow_wow_usd_mn"].transform(lambda s: s.rolling(52, min_periods=8).sum())

    def rolling_z(s, w=52):
        mu = s.rolling(w, min_periods=8).mean()
        sd = s.rolling(w, min_periods=8).std(ddof=0)
        return (s - mu) / sd.replace(0, np.nan)
    d["z_52w"] = d.groupby(list(keys), dropna=False)["flow_wow_usd_mn"].transform(rolling_z)

    def streak(arr):
        out = []
        cur = 0
        last_sign = 0
        for v in arr:
            sign = 1 if v>0 else (-1 if v<0 else 0)
            if sign == 0:
                cur = 0
            elif sign == last_sign:
                cur += 1
            else:
                cur = 1
            last_sign = sign
            out.append(cur*sign)
        return out

    d["streak"] = d.groupby(list(keys), dropna=False)["flow_wow_usd_mn"].transform(lambda s: streak(s.values))
    return d

def divergence_equity_vs_bond(ts: pd.DataFrame) -> pd.DataFrame:
    e = ts[ts["asset_class"].str.contains("Equity", case=False, na=False)]
    b = ts[ts["asset_class"].str.contains("Bond", case=False, na=False)]
    on = ["level","region","country","as_of_date"]
    m = pd.merge(
        e[on+["flow_wow_usd_mn"]].rename(columns={"flow_wow_usd_mn":"eq"}),
        b[on+["flow_wow_usd_mn"]].rename(columns={"flow_wow_usd_mn":"bd"}),
        on=on, how="inner"
    )
    m["divergence"] = np.sign(m["eq"]) * np.sign(m["bd"])
    return m

def generate_alerts(ts: pd.DataFrame, top_n=10):
    alerts = []
    if ts.empty:
        return alerts
    latest_date = ts["as_of_date"].max()
    latest = ts[ts["as_of_date"]==latest_date]
    extremes = latest.dropna(subset=["z_52w"]).sort_values("z_52w")
    lows = extremes.head(top_n).to_dict("records")
    highs = extremes.tail(top_n).to_dict("records")

    for r in highs:
        alerts.append({
            "type":"Extreme Inflow",
            "as_of_date": str(latest_date.date() if hasattr(latest_date,'date') else latest_date),
            "where": f'{r["country"] or r["level"]} / {r["asset_class"]}',
            "detail": f'z={r["z_52w"]:.2f}, WoW={r["flow_wow_usd_mn"]:.0f} USD mn, 4W={r["roll_4w"]:.0f}'
        })
    for r in lows:
        alerts.append({
            "type":"Extreme Outflow",
            "as_of_date": str(latest_date.date() if hasattr(latest_date,'date') else latest_date),
            "where": f'{r["country"] or r["level"]} / {r["asset_class"]}',
            "detail": f'z={r["z_52w"]:.2f}, WoW={r["flow_wow_usd_mn"]:.0f} USD mn, 4W={r["roll_4w"]:.0f}'
        })

    latest_streaks = ts.groupby(["level","region","country","asset_class"], dropna=False).tail(1)
    longest = latest_streaks.iloc[(-latest_streaks["streak"].abs()).argsort()[:top_n]]
    for _, r in longest.iterrows():
        direction = "inflows" if r["streak"]>0 else "outflows"
        alerts.append({
            "type":"Streak",
            "as_of_date": str(latest_date.date() if hasattr(latest_date,'date') else latest_date),
            "where": f'{r["country"] or r["level"]} / {r["asset_class"]}',
            "detail": f'{abs(int(r["streak"]))} weeks of {direction}; last WoW={r["flow_wow_usd_mn"]:.0f} USD mn'
        })
    return alerts