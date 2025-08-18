import re
from datetime import datetime
from dateutil import parser as dateparser
import pandas as pd
import numpy as np

def parse_date_from_text(text:str, patterns):
    for pat in patterns:
        for m in re.finditer(pat, text):
            groups = [g for g in m.groups() if g]
            if not groups:
                continue
            candidate = groups[-1]
            try:
                dt = dateparser.parse(candidate, dayfirst=False, fuzzy=True)
                return dt.date().isoformat()
            except Exception:
                continue
    return None

def try_date_from_filename(fname:str):
    pats = [
        r"([0-9]{4}[-_/][0-9]{2}[-_/][0-9]{2})",
        r"([0-9]{2}[-_/][0-9]{2}[-_/][0-9]{4})",
        r"([0-9]{8})",
        r"([0-9]{1,2}[A-Za-z]{3,9}[0-9]{2,4})"
    ]
    for p in pats:
        m = re.search(p, fname)
        if m:
            try:
                return dateparser.parse(m.group(1), dayfirst=True, fuzzy=True).date().isoformat()
            except Exception:
                pass
    return None

def coerce_numeric(x, regex_to_strip):
    if x is None:
        return np.nan
    if isinstance(x, (int, float, np.number)):
        return float(x)
    s = str(x)
    s = re.sub(regex_to_strip, "", s)
    s = s.replace(",", "")
    if s in ("", "+", "-"):
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan

def wide_to_long_guess(df, value_hints):
    cols = df.columns
    val_cols = [c for c in cols if any(h.lower() in str(c).lower() for h in value_hints)]
    if not val_cols:
        numeric_mask = df.apply(lambda s: pd.to_numeric(s, errors='coerce')).notna().sum()
        val_cols = list(numeric_mask.sort_values(ascending=False).head(3).index)
    id_cols = [c for c in cols if c not in val_cols]
    long = df.melt(id_vars=id_cols, value_vars=val_cols, var_name="measure", value_name="value")
    return long