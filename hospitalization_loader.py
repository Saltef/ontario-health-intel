"""loaders/hospitalization_loader.py"""

import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

DATA_PATH = Path("inputData/layer2_current_burden.csv")

NUMERIC_COLS = [
    "ed_visits", "ed_visits_per_100k",
    "admissions", "admissions_per_100k",
    "avg_cost_per_admission", "total_cost",
    "avoidability_pct", "avoidable_admissions", "avoidable_cost",
    "effective_physician_capacity_fte", "num_specialties_involved",
    "care_gap_score",
    "specialist_wait_weeks_ontario", "specialist_wait_weeks_canada",
    "total_wait_weeks_canada", "wait_time_change_1993_2025_pct",
]


@st.cache_data(ttl=3600)
def load_burden() -> pd.DataFrame:
    if not DATA_PATH.exists():
        st.error(f"File not found: `{DATA_PATH}`")
        return pd.DataFrame()

    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalise confidence label
    if "wait_time_confidence" in df.columns:
        df["wait_time_confidence"] = (
            df["wait_time_confidence"]
            .fillna("None")
            .str.strip()
            .replace({"Not available in Fraser Institute 2025": "None"})
        )

    # avoidability_pct is stored as 0–1; derive a display version
    if "avoidability_pct" in df.columns:
        df["avoidability_pct_display"] = (df["avoidability_pct"] * 100).round(1)

    if {"total_cost", "avoidable_cost"}.issubset(df.columns):
        df["non_avoidable_cost"] = df["total_cost"] - df["avoidable_cost"]

    return df


def get_conditions(df: pd.DataFrame) -> list:
    return sorted(df["condition"].dropna().unique().tolist())


def get_years(df: pd.DataFrame) -> list:
    return sorted(df["year"].dropna().astype(int).unique().tolist(), reverse=True)


def filter_burden(df, conditions=None, year=None):
    out = df.copy()
    if conditions:
        out = out[out["condition"].isin(conditions)]
    if year is not None:
        out = out[out["year"] == year]
    return out


def get_wait_times(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition", "primary_specialty",
        "specialist_wait_weeks_ontario", "specialist_wait_weeks_canada",
        "total_wait_weeks_canada", "wait_time_change_1993_2025_pct",
        "wait_time_confidence", "wait_time_data_source",
    ]
    return (
        df[[c for c in cols if c in df.columns]]
        .drop_duplicates(subset=["condition"])
        .copy()
    )
