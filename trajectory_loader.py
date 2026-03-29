"""loaders/trajectory_loader.py"""

import pandas as pd
from pathlib import Path
import streamlit as st

DATA_PATH = Path("inputData/layer3_predictive_trajectory.csv")

SCENARIO_ORDER = ["Historical", "Low", "Reference", "High"]

NUMERIC_COLS = [
    "growth_rate_pct", "confidence",
    "ed_visits", "admissions",
    "avoidable_admissions", "avoidable_cost",
]


@st.cache_data(ttl=3600)
def load_trajectory() -> pd.DataFrame:
    if not DATA_PATH.exists():
        st.error(f"File not found: `{DATA_PATH}`")
        return pd.DataFrame()

    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "year" in df.columns:
        df["year"] = df["year"].astype(int)

    if "scenario" in df.columns:
        df["scenario"] = df["scenario"].str.strip().str.title()

    return df


def get_scenarios(df: pd.DataFrame) -> list:
    present = df["scenario"].unique().tolist()
    return [s for s in SCENARIO_ORDER if s in present]


def get_conditions(df: pd.DataFrame) -> list:
    return sorted(df["condition"].dropna().unique().tolist())


def filter_trajectory(df, scenarios=None, conditions=None, exclude_historical=False):
    out = df.copy()
    if scenarios:
        out = out[out["scenario"].isin(scenarios)]
    if conditions:
        out = out[out["condition"].isin(conditions)]
    if exclude_historical:
        out = out[out["scenario"] != "Historical"]
    return out
