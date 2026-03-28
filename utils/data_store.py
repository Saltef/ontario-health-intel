"""
utils/data_store.py
───────────────────
Central data access layer for all Streamlit pages.
Loads from data/processed/ with graceful fallback to synthetic data
when real data hasn't been fetched yet.

Usage:
    from utils.data_store import load_population, load_providers,
                                  load_projections, get_metadata
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

ROOT      = Path(__file__).parent.parent
OUT_DIR   = ROOT / "data" / "processed"
META_FILE = ROOT / "data" / "metadata.json"

AGE_GROUPS = ["0–14", "15–24", "25–44", "45–64", "65–74", "75–84", "85+"]

LHIN_COORDS = {
    "Erie St. Clair":                   (42.32, -82.55),
    "South West":                       (42.98, -81.25),
    "Waterloo Wellington":              (43.55, -80.50),
    "Hamilton Niagara Haldimand Brant": (43.18, -79.90),
    "Central West":                     (43.72, -79.90),
    "Mississauga Halton":               (43.60, -79.65),
    "Toronto Central":                  (43.67, -79.39),
    "Central":                          (43.83, -79.50),
    "Central East":                     (44.15, -78.90),
    "South East":                       (44.52, -76.55),
    "Champlain":                        (45.30, -75.70),
    "North Simcoe Muskoka":             (44.85, -79.60),
    "North East":                       (46.80, -81.00),
    "North West":                       (49.40, -86.60),
}

LHIN_TYPES = {
    "Erie St. Clair": "mixed",     "South West": "rural",
    "Waterloo Wellington": "suburban", "Hamilton Niagara Haldimand Brant": "urban",
    "Central West": "suburban",    "Mississauga Halton": "urban",
    "Toronto Central": "urban",    "Central": "urban",
    "Central East": "suburban",    "South East": "rural",
    "Champlain": "urban",          "North Simcoe Muskoka": "rural",
    "North East": "northern",      "North West": "northern",
}

PHU_MAP = {
    "Erie St. Clair":   ["Windsor-Essex", "Chatham-Kent", "Lambton"],
    "South West":       ["Elgin-St. Thomas", "Middlesex-London", "Huron Perth", "Oxford"],
    "Waterloo Wellington": ["Waterloo Region", "Wellington-Dufferin-Guelph"],
    "Hamilton Niagara Haldimand Brant": ["Hamilton", "Niagara", "Haldimand-Norfolk", "Brant"],
    "Central West":     ["Peel (north)", "Halton Hills"],
    "Mississauga Halton": ["Halton", "Mississauga"],
    "Toronto Central":  ["Toronto"],
    "Central":          ["York Region", "South Simcoe"],
    "Central East":     ["Durham", "Peterborough", "Haliburton Kawartha"],
    "South East":       ["Kingston Frontenac Lennox", "Leeds Grenville", "Hastings Prince Edward"],
    "Champlain":        ["Ottawa", "Eastern Ontario", "Renfrew"],
    "North Simcoe Muskoka": ["North Bay Parry Sound", "Simcoe Muskoka"],
    "North East":       ["Sudbury", "Porcupine", "Algoma", "Timiskaming"],
    "North West":       ["Thunder Bay", "Northwestern"],
}

# Benchmarks (CIHI Canada 2022)
BENCHMARK = dict(gp_per_1000=1.05, spec_per_1000=1.10, np_per_1000=0.30)


# ── Synthetic fallback ───────────────────────────────────────────────────────

def _synthetic_population() -> pd.DataFrame:
    """Generates synthetic population data modelled after Stats Can 2021 Census."""
    rng = np.random.default_rng(42)
    AGE_W = {
        "urban":    [0.155,0.120,0.290,0.240,0.100,0.065,0.030],
        "suburban": [0.175,0.115,0.275,0.240,0.105,0.065,0.025],
        "mixed":    [0.168,0.118,0.268,0.248,0.108,0.065,0.025],
        "rural":    [0.155,0.110,0.245,0.270,0.125,0.070,0.025],
        "northern": [0.160,0.118,0.260,0.278,0.110,0.055,0.019],
    }
    BASE_POP = {
        "Erie St. Clair":542000,"South West":503000,"Waterloo Wellington":634000,
        "Hamilton Niagara Haldimand Brant":1497000,"Central West":882000,
        "Mississauga Halton":1218000,"Toronto Central":1214000,"Central":1812000,
        "Central East":1403000,"South East":491000,"Champlain":1298000,
        "North Simcoe Muskoka":471000,"North East":563000,"North West":242000,
    }
    rows = []
    for lhin, pop in BASE_POP.items():
        t = LHIN_TYPES[lhin]
        w = np.array(AGE_W[t]) * rng.uniform(0.97,1.03,7)
        w /= w.sum()
        for i, ag in enumerate(AGE_GROUPS):
            rows.append({"LHIN":lhin,"year":2021,"age_group":ag,
                         "population":int(w[i]*pop)})
    return pd.DataFrame(rows)


def _synthetic_providers() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    GP_D   = {"urban":1.18,"suburban":0.98,"mixed":0.88,"rural":0.72,"northern":0.58}
    SPEC_D = {"urban":1.55,"suburban":0.92,"mixed":0.75,"rural":0.45,"northern":0.38}
    NP_D   = {"urban":0.35,"suburban":0.28,"mixed":0.25,"rural":0.22,"northern":0.30}
    BASE_POP = {
        "Erie St. Clair":542000,"South West":503000,"Waterloo Wellington":634000,
        "Hamilton Niagara Haldimand Brant":1497000,"Central West":882000,
        "Mississauga Halton":1218000,"Toronto Central":1214000,"Central":1812000,
        "Central East":1403000,"South East":491000,"Champlain":1298000,
        "North Simcoe Muskoka":471000,"North East":563000,"North West":242000,
    }
    rows = []
    for lhin, pop in BASE_POP.items():
        t = LHIN_TYPES[lhin]
        gp_r   = GP_D[t]   * rng.uniform(0.92,1.08)
        spec_r = SPEC_D[t] * rng.uniform(0.92,1.08)
        np_r   = NP_D[t]   * rng.uniform(0.92,1.08)
        rows.append({
            "LHIN":lhin,"province":"Ontario","year":2022,
            "gp_count":int(gp_r*pop/1000), "spec_count":int(spec_r*pop/1000),
            "np_count":int(np_r*pop/1000),
            "total_physicians":int((gp_r+spec_r)*pop/1000),
            "gp_per_1000":round(gp_r,3), "spec_per_1000":round(spec_r,3),
            "np_per_1000":round(np_r,3), "population":pop,
        })
    return pd.DataFrame(rows)


def _synthetic_projections() -> pd.DataFrame:
    rng = np.random.default_rng(99)
    base = _synthetic_population()
    base_agg = base.groupby("age_group")["population"].sum().reset_index()
    rows = []
    growth = {"M1":0.0085,"LG":0.0040,"HG":0.0140}
    age_mult = {"0–14":0.90,"15–24":0.95,"25–44":1.00,"45–64":1.00,
                "65–74":1.20,"75–84":1.35,"85+":1.50}
    for scen, rate in growth.items():
        for year in range(2023, 2046):
            yrs = year - 2021
            for _, r in base_agg.iterrows():
                pop = int(r["population"] * (1+rate)**yrs * age_mult.get(r["age_group"],1))
                rows.append({
                    "year":year,"scenario":scen,
                    "scenario_label":{"M1":"Medium-growth","LG":"Low-growth","HG":"High-growth"}[scen],
                    "age_group":r["age_group"],
                    "population":int(pop * rng.uniform(0.99,1.01)),
                })
    return pd.DataFrame(rows)


# ── Public loaders ───────────────────────────────────────────────────────────

def load_population(year: int | None = None) -> tuple[pd.DataFrame, bool]:
    """
    Returns (df, is_real) where is_real=True means data came from Stats Can.
    df columns: LHIN, year, age_group, population
    """
    path = OUT_DIR / "population_by_age_lhin.csv"
    if path.exists():
        df = pd.read_csv(path)
        if year:
            df = df[df["year"] == year]
        return df, True
    return _synthetic_population(), False


def load_providers() -> tuple[pd.DataFrame, bool]:
    """
    Returns (df, is_real).
    Merges physicians + NP files if both exist.
    df columns: LHIN, province, year, gp_count, spec_count, np_count,
                gp_per_1000, spec_per_1000, np_per_1000, population
    """
    phy_path = OUT_DIR / "providers_by_lhin.csv"
    np_path  = OUT_DIR / "np_by_lhin.csv"

    if phy_path.exists():
        df = pd.read_csv(phy_path)
        if np_path.exists():
            np_df = pd.read_csv(np_path)[["LHIN","np_count","np_per_1000"]]
            df = df.merge(np_df, on="LHIN", how="left")
        else:
            df["np_count"]    = np.nan
            df["np_per_1000"] = np.nan
        return df, True

    return _synthetic_providers(), False


def load_projections() -> tuple[pd.DataFrame, bool]:
    """
    Returns (df, is_real).
    df columns: year, scenario, scenario_label, age_group, population
    """
    path = OUT_DIR / "population_projections.csv"
    if path.exists():
        return pd.read_csv(path), True
    return _synthetic_projections(), False


def build_lhin_summary() -> tuple[pd.DataFrame, bool]:
    """
    Build the main LHIN-level summary DataFrame used by the map.
    Merges population + providers + coordinates.
    Returns (df, any_real_data).
    """
    pop_df, pop_real   = load_population(year=None)
    prov_df, prov_real = load_providers()

    # Use most recent year from population data
    if "year" in pop_df.columns:
        latest_year = pop_df["year"].max()
        pop_df = pop_df[pop_df["year"] == latest_year]

    # Pivot age groups wide
    pop_wide = pop_df.pivot_table(
        index="LHIN", columns="age_group", values="population", aggfunc="sum"
    ).reset_index()
    pop_wide.columns.name = None

    # Ensure all age groups present
    for ag in AGE_GROUPS:
        if ag not in pop_wide.columns:
            pop_wide[ag] = 0

    pop_wide["population"]  = pop_wide[[ag for ag in AGE_GROUPS if ag in pop_wide.columns]].sum(axis=1)
    pop_wide["pct_65plus"]  = (
        (pop_wide.get("65–74",0) + pop_wide.get("75–84",0) + pop_wide.get("85+",0))
        / pop_wide["population"] * 100
    ).round(1)

    # Rename age cols to safe names
    pop_wide = pop_wide.rename(columns={ag: f"pop_{ag}" for ag in AGE_GROUPS})

    # Merge providers
    merge_cols = ["LHIN","gp_per_1000","spec_per_1000","np_per_1000",
                  "gp_count","spec_count","np_count"]
    avail = [c for c in merge_cols if c in prov_df.columns]
    df = pop_wide.merge(prov_df[avail], on="LHIN", how="left")

    # Fill any missing provider rates with 0 (flagged in UI)
    for col in ["gp_per_1000","spec_per_1000","np_per_1000"]:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = df[col].fillna(0.0)

    # Demand / supply / gap scores
    w = [0.5, 0.6, 0.8, 1.0, 1.5, 2.0, 2.5]
    age_fracs = []
    for ag in AGE_GROUPS:
        col = f"pop_{ag}"
        frac = (df[col] if col in df.columns else pd.Series(0, index=df.index)) / df["population"]
        age_fracs.append(frac)
    df["demand_score"] = sum(frac * wi for frac, wi in zip(age_fracs, w)).round(3)
    df["supply_score"] = (
        (df["gp_per_1000"] / BENCHMARK["gp_per_1000"])   * 0.55 +
        (df["spec_per_1000"] / BENCHMARK["spec_per_1000"]) * 0.35 +
        (df["np_per_1000"]  / BENCHMARK["np_per_1000"])   * 0.10
    ).round(3)
    df["gap_score"] = (df["demand_score"] / df["supply_score"].replace(0, np.nan)).round(3)

    # Attach coords and type
    df["lat"] = df["LHIN"].map(lambda l: LHIN_COORDS.get(l, (0,0))[0])
    df["lon"] = df["LHIN"].map(lambda l: LHIN_COORDS.get(l, (0,0))[1])
    df["type"] = df["LHIN"].map(LHIN_TYPES)

    any_real = pop_real or prov_real
    return df, any_real


def get_metadata() -> dict:
    if META_FILE.exists():
        return json.loads(META_FILE.read_text())
    return {}
