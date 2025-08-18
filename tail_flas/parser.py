import os, re, yaml
from typing import List, Dict, Any, Tuple
import pandas as pd
import pdfplumber
from rapidfuzz import fuzz
from utils import parse_date_from_text, try_date_from_filename, coerce_numeric, wide_to_long_guess

DEFAULT_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "explicit_vertical_lines": [],
    "explicit_horizontal_lines": [],
}

class EMFlowsParser:
    def __init__(self, config_path="config.yml"):
        with open(config_path, "r") as f:
            self.cfg = yaml.safe_load(f)
        self.table_settings = self.cfg.get("parsing", {}).get("table_settings", DEFAULT_TABLE_SETTINGS)
        self.value_hints = self.cfg.get("value_column_hints", [])
        self.num_regex = self.cfg.get("parsing", {}).get("numeric_clean_regex", r"[^0-9+\\-.,]")

    def _extract_text_all(self, pdf_path:str, max_pages:int) -> str:
        text_chunks = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages: break
                try:
                    t = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                    text_chunks.append(t)
                except Exception:
                    continue
        return "\\n".join(text_chunks)

    def _extract_tables(self, pdf_path:str, max_pages:int) -> List[pd.DataFrame]:
        dfs = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages: break
                try:
                    tables = page.extract_tables(table_settings=self.table_settings)
                    for t in tables:
                        df = pd.DataFrame(t).dropna(axis=0, how="all").dropna(axis=1, how="all")
                        if df.shape[0] >= 2 and df.shape[1] >= 2:
                            df = df.rename(columns={c: str(c) for c in df.columns})
                            if df.shape[0] >= 2:
                                header = df.iloc[0].astype(str).tolist()
                                if len(set(header)) == len(header):
                                    df.columns = header
                                    df = df.iloc[1:].reset_index(drop=True)
                            dfs.append(df)
                except Exception:
                    continue
        return dfs

    def _score_match(self, title:str, keywords:List[str]) -> int:
        title = title.lower()
        best = 0
        for kw in keywords:
            best = max(best, fuzz.partial_ratio(title, kw.lower()))
        return best

    def _guess_title_for_df(self, df:pd.DataFrame) -> str:
        cols = " | ".join([str(c) for c in df.columns[:6]])
        first_vals = " ".join([str(v) for v in df.head(2).to_numpy().flatten()[:12]])
        return f"{cols} :: {first_vals}"

    def _unit_hint(self, df:pd.DataFrame) -> str:
        import re
        joined = " ".join([str(c) for c in df.columns]) + " " + " ".join([str(x) for x in df.head(3).to_numpy().flatten()])
        if re.search(r"(?i)(usd|us\\$)", joined) and re.search(r"(?i)(mn|million)", joined):
            return "USD mn"
        if re.search(r"(?i)(usd|us\\$)", joined):
            return "USD"
        return None

    def _normalize_topdown_table(self, df:pd.DataFrame, pattern_block:Dict[str,Any], as_of:str, pdf_name:str) -> pd.DataFrame:
        long = wide_to_long_guess(df, self.value_hints)
        if 'Country' in long.columns: name_col = 'Country'
        elif 'country' in long.columns: name_col = 'country'
        elif 'Market' in long.columns: name_col = 'Market'
        else: name_col = long.columns[0]

        long = long.rename(columns={name_col: "label"})
        long["value"] = long["value"].apply(lambda x: coerce_numeric(x, self.num_regex))
        long = long.dropna(subset=["value"])
        long["as_of_date"] = as_of
        long["level"] = pattern_block.get("level")
        long["region"] = pattern_block.get("region")
        long["country"] = None
        long["asset_class"] = pattern_block.get("asset_class")
        long["unit"] = self._unit_hint(df) or pattern_block.get("unit_hint", [None])[0]
        long["source_pdf"] = pdf_name

        if pattern_block.get("region") or "country" in " ".join(df.columns).lower():
            long["country"] = long["label"]
            long["level"] = "Country"

        long["measure"] = long["measure"].astype(str).strip().upper().replace({"W/W":"WOW", "1W":"WOW", "4W":"4W"})
        long["measure"] = long["measure"].str.replace(r"[^A-Z0-9]", "", regex=True)

        return long[["as_of_date","level","region","country","asset_class","measure","value","unit","source_pdf"]]

    def parse_pdf(self, pdf_path:str):
        max_pages = int(self.cfg.get("parsing", {}).get("max_pages", 40))
        raw_text = self._extract_text_all(pdf_path, max_pages)
        as_of = parse_date_from_text(raw_text, self.cfg.get("date_patterns", [])) or \
                try_date_from_filename(os.path.basename(pdf_path)) or "1970-01-01"
        tables = self._extract_tables(pdf_path, max_pages)

        blocks = []
        for df in tables:
            pseudo_title = self._guess_title_for_df(df)
            best_score, best_block = 0, None
            for patt in self.cfg.get("table_patterns", {}).values():
                score = self._score_match(pseudo_title, patt.get("keywords", []))
                if score > best_score:
                    best_score, best_block = score, patt
            for patt in self.cfg.get("country_table_patterns", {}).values():
                score = self._score_match(pseudo_title, patt.get("keywords", []))
                if score > best_score:
                    best_score, best_block = score, patt
            if best_block and best_score >= 60:
                try:
                    norm = self._normalize_topdown_table(df, best_block, as_of, os.path.basename(pdf_path))
                    blocks.append(norm)
                except Exception:
                    continue

        if blocks:
            out = pd.concat(blocks, ignore_index=True)
        else:
            out = pd.DataFrame(columns=["as_of_date","level","region","country","asset_class","measure","value","unit","source_pdf"])

        return as_of, out