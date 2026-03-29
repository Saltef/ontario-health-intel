"""loaders/cost_loader.py"""

import pandas as pd
from pathlib import Path
import streamlit as st

DATA_PATH = Path("inputData/layer4_cost_analysis.csv")

NUMERIC_COLS = [
    "avg_cost_per_admission", "admissions_2024", "total_cost_2024",
    "avoidable_admissions_2024", "avoidable_cost_2024",
    "avoidable_admissions_2034", "avoidable_cost_2034",
    "managed_care_cost_alternative", "potential_savings_per_admission",
    "savings_5yr", "roi_5yr", "savings_10yr", "roi_10yr",
]


@st.cache_data(ttl=3600)
def load_costs() -> pd.DataFrame:
    if not DATA_PATH.exists():
        st.error(f"File not found: `{DATA_PATH}`")
        return pd.DataFrame()

    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derived: avoidable share of total cost
    if {"avoidable_cost_2024", "total_cost_2024"}.issubset(df.columns):
        df["avoidable_pct_2024"] = (
            df["avoidable_cost_2024"] / df["total_cost_2024"].replace(0, float("nan")) * 100
        ).round(1)

    # Derived: avoidable cost growth 2024→2034
    if {"avoidable_cost_2024", "avoidable_cost_2034"}.issubset(df.columns):
        df["avoidable_cost_growth_pct"] = (
            (df["avoidable_cost_2034"] - df["avoidable_cost_2024"])
            / df["avoidable_cost_2024"].replace(0, float("nan")) * 100
        ).round(1)

    return df


def get_top_by_cost(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return df.nlargest(n, "total_cost_2024").copy()
