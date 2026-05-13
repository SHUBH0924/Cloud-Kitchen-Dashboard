"""
data_prep.py — Load and prepare the Kitchen P&L dataset.

The same function is used by both the Streamlit app and the analysis notebook.

Here, I derived the margin % columns (GM %, CM %, EBITDA %) from the absolute amounts in the input file,
and also created the required buckets for revenue and variance % as per the requirements of Dashboard 2. 

Formulas used:
- GM = Net Revenue - IDEAL FOOD COST
- GM % = (Gross Margin / Net Revenue) * 100
- CM (Contribution Margin) = GM - Variance
- CM (Contribution Margin) % = (CM / Net Revenue) * 100
- EBITDA % = (Kitchen EBITDA / Net Revenue) * 100
- Variance % = (Variance / Net Revenue) * 100
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path


# Revenue buckets, If revenue is in between the given range, it falls in the corresponding bucket.
# The labels are as per the requirements of Dashboard 2.
REVENUE_BUCKETS = [
    ("(a) Below INR 15 lacs", 0,          15_00_000),
    ("(b) INR 15 to 25 lacs", 15_00_000,  25_00_000),
    ("(c) INR 25 to 35 lacs", 25_00_000,  35_00_000),
    ("(d) INR 35 to 45 lacs", 35_00_000,  45_00_000),
    ("(e) Above INR 45 lacs", 45_00_000,  float("inf")),
]

# Variance % buckets, If variance % is in between the given range, it falls in the corresponding bucket.
# The labels are as per the requirements of Dashboard 2.
VARIANCE_BUCKETS = [
    ("(a) Var < 2%",      -float("inf"), 0.02),
    ("(b) Var 2% to 3%",   0.02,         0.03),
    ("(c) Var 3% to 5%",   0.03,         0.05),
    ("(d) Var > 5%",       0.05,         float("inf")),
]


# Helper functions to assign buckets based on the defined ranges. If a value is missing or doesn't fit any bucket, it returns "Unknown".
def _revenue_bucket(rev: float) -> str:
    for label, lo, hi in REVENUE_BUCKETS:
        if lo <= rev < hi:
            return label
    return "Unknown"


# Helper function to assign variance % buckets. If a value is missing or doesn't fit any bucket, it returns "Unknown".
def _variance_bucket(var_pct: float) -> str:
    if pd.isna(var_pct):
        return "Unknown"
    for label, lo, hi in VARIANCE_BUCKETS:
        if lo <= var_pct < hi:
            return label
    return "Unknown"


# Main function to load the Excel file and prepare the DataFrame with derived columns and buckets.
def load_and_prepare(path: str | Path) -> pd.DataFrame:
    """Load the raw Excel file and add derived columns used across the app."""
    df = pd.read_excel(path, sheet_name="Sheet 1 - stores", header=1)

    # Strip whitespace from text columns defensively
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip()

    # Real datetime column for sorting / range filters
    df["MONTH_DT"] = pd.to_datetime(df["MONTH"], format="%b-%Y", errors="coerce")
    df = df.sort_values(["MONTH_DT", "STORE"]).reset_index(drop=True)

    # Derived margin columns (the input file gives absolute amounts, not %)
    # Here, I use np.where for safe division to avoid #DIV/0! style errors
    nr = df["NET REVENUE"].replace(0, np.nan)
    df["GM %"]     = df["GROSS MARGIN"]   / nr
    df["CM"]       = df["GROSS MARGIN"] - df["VARIANCE"]   # CM = GM - food wastage
    df["CM %"]     = df["CM"]             / nr
    df["EBITDA %"] = df["KITCHEN EBITDA"] / nr
    df["VARIANCE %"] = df["VARIANCE"]     / nr

    # Required buckets for Dashboard 2
    df["REVENUE BUCKET"]  = df["NET REVENUE"].apply(_revenue_bucket)
    df["VARIANCE BUCKET"] = df["VARIANCE %"].apply(_variance_bucket)

    # Friendly label for the month column in display tables.
    df["MONTH LABEL"] = df["MONTH_DT"].dt.strftime("%b %Y")

    return df


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "Kittchen_PNL_Data.xlsx"
    d = load_and_prepare(p)
    print(d.shape)
    print(d.dtypes)
    print(d.head())
