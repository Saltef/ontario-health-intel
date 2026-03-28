"""
fetch/statcan.py
────────────────
Fetches Ontario population data from Statistics Canada WDS (Web Data Service).

Tables used:
  17-10-0142-01  Population estimates by health region of residence (annual)
                 → Ontario LHINs map to "health regions" in this table
  17-10-0057-01  Projected population by projection scenario
                 → Province-level; we apply age-share weights to get LHIN projections

Stats Can WDS docs: https://www.statcan.gc.ca/en/developers/wds
No API key required. Rate limit: ~20 req/s. All data is open licence (OGL 2.0).

Usage:
    python -m fetch.statcan            # fetch + save both tables
    from fetch.statcan import fetch_all
"""

import io
import json
import zipfile
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
RAW_DIR    = ROOT / "data" / "raw"
OUT_DIR    = ROOT / "data" / "processed"
META_FILE  = ROOT / "data" / "metadata.json"

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Stats Can WDS endpoints ─────────────────────────────────────────────────
WDS_BASE   = "https://www150.statcan.gc.ca/t1/tbl1/en"
TABLE_POP_HR    = "17100142"   # Pop by health region (annual estimates)
TABLE_PROJ      = "17100057"   # Projected population by scenario
TABLE_POP_AGE   = "17100005"   # Pop estimates quarterly (province, age, sex)

# ── LHIN → Stats Can health region code mapping ─────────────────────────────
# Source: Stats Can geographic concordance 2021
# Health region codes for Ontario (province code 35)
LHIN_HR_MAP = {
    "Erie St. Clair":                   "3540",
    "South West":                       "3530",
    "Waterloo Wellington":              "3520",
    "Hamilton Niagara Haldimand Brant": "3510",
    "Central West":                     "3560",
    "Mississauga Halton":               "3550",
    "Toronto Central":                  "3595",
    "Central":                          "3570",
    "Central East":                     "3580",
    "South East":                       "3500",
    "Champlain":                        "3615",
    "North Simcoe Muskoka":             "3575",
    "North East":                       "3590",
    "North West":                       "3610",
}

AGE_GROUPS = ["0–14", "15–24", "25–44", "45–64", "65–74", "75–84", "85+"]

# Age band labels used inside the Stats Can table → our age groups
STATCAN_AGE_MAP = {
    "0 to 4 years":   "0–14",
    "5 to 9 years":   "0–14",
    "10 to 14 years": "0–14",
    "15 to 19 years": "15–24",
    "20 to 24 years": "15–24",
    "25 to 29 years": "25–44",
    "30 to 34 years": "25–44",
    "35 to 39 years": "25–44",
    "40 to 44 years": "25–44",
    "45 to 49 years": "45–64",
    "50 to 54 years": "45–64",
    "55 to 59 years": "45–64",
    "60 to 64 years": "45–64",
    "65 to 69 years": "65–74",
    "70 to 74 years": "65–74",
    "75 to 79 years": "75–84",
    "80 to 84 years": "75–84",
    "85 years and over": "85+",
}

PROJECTION_SCENARIOS = {
    "M1": "Medium-growth (reference)",
    "LG": "Low-growth",
    "HG": "High-growth",
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _download_csv(table_id: str) -> pd.DataFrame:
    """Download a Stats Can table CSV via the WDS bulk download endpoint."""
    url = f"{WDS_BASE}/dtbl/downloadCSV/{table_id}"
    log.info(f"Downloading Stats Can table {table_id}…")
    r = requests.get(url, timeout=120)
    r.raise_for_status()

    # Response is a zip containing <tableid>.csv + <tableid>_MetaData.csv
    z = zipfile.ZipFile(io.BytesIO(r.content))
    csv_name = f"{table_id}.csv"
    if csv_name not in z.namelist():
        # Some tables use a hyphenated name
        csv_name = [n for n in z.namelist() if not n.endswith("_MetaData.csv")][0]

    raw_path = RAW_DIR / f"statcan_{table_id}.csv"
    with z.open(csv_name) as f:
        data = f.read()
    raw_path.write_bytes(data)
    log.info(f"  Saved raw → {raw_path}")

    return pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", low_memory=False)


def _update_meta(key: str, rows: int, source_table: str):
    meta = {}
    if META_FILE.exists():
        meta = json.loads(META_FILE.read_text())
    meta[key] = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "rows": rows,
        "source": f"Statistics Canada table {source_table}",
        "licence": "Open Government Licence – Canada",
        "url": f"https://www150.statcan.gc.ca/t1/tbl1/en/tbl/{source_table.replace('-','')[:-2]}-eng.htm",
    }
    META_FILE.write_text(json.dumps(meta, indent=2))


# ── Table 1: Population by health region ────────────────────────────────────

def fetch_population_by_lhin() -> pd.DataFrame:
    """
    Fetch annual population estimates by Ontario health region from table 17-10-0142-01.
    Outputs: data/processed/population_by_age_lhin.csv

    Columns:
        LHIN, year, age_group, sex, population
    """
    df_raw = _download_csv(TABLE_POP_HR)

    # Standardise column names (Stats Can uses mixed case + spaces)
    df_raw.columns = [c.strip().lower().replace(" ", "_") for c in df_raw.columns]

    # Filter to Ontario health regions and most recent reference year
    # Typical columns: ref_date, geo, dguid, sex, age_group, value, ...
    # Keep only Ontario codes and "Both sexes"
    df = df_raw[
        df_raw["geo"].str.startswith("Ontario", na=False) |
        df_raw.get("dguid", pd.Series(dtype=str)).str.startswith("2016A000235", na=False)
    ].copy()

    if df.empty:
        # Fallback: filter by health region codes
        hr_codes = list(LHIN_HR_MAP.values())
        df = df_raw[df_raw.get("dguid", pd.Series(dtype=str)).str[-4:].isin(hr_codes)].copy()

    # Parse year
    df["year"] = pd.to_numeric(df["ref_date"].astype(str).str[:4], errors="coerce")

    # Map sex column
    sex_col = next((c for c in df.columns if "sex" in c.lower()), None)
    if sex_col:
        df = df[df[sex_col].str.lower().str.contains("both|total", na=False)]

    # Map age groups
    age_col = next((c for c in df.columns if "age" in c.lower()), None)
    if age_col:
        df["age_group"] = df[age_col].map(STATCAN_AGE_MAP)
        df = df[df["age_group"].notna()]

    # Value column
    val_col = next((c for c in df.columns if c in ("value", "val", "population")), "value")
    df["population"] = pd.to_numeric(df[val_col], errors="coerce")

    # Map DGUID to LHIN name
    inv_map = {v: k for k, v in LHIN_HR_MAP.items()}
    dguid_col = next((c for c in df.columns if "dguid" in c.lower()), None)
    if dguid_col:
        df["hr_code"] = df[dguid_col].astype(str).str[-4:]
        df["LHIN"] = df["hr_code"].map(inv_map)
    else:
        df["LHIN"] = df["geo"]

    # Aggregate to our age groups
    out = (
        df.groupby(["LHIN", "year", "age_group"], as_index=False)["population"]
        .sum()
        .dropna(subset=["LHIN", "population"])
    )

    out_path = OUT_DIR / "population_by_age_lhin.csv"
    out.to_csv(out_path, index=False)
    _update_meta("population_by_age_lhin", len(out), TABLE_POP_HR)
    log.info(f"  Wrote {len(out)} rows → {out_path}")
    return out


# ── Table 2: Population projections ─────────────────────────────────────────

def fetch_population_projections() -> pd.DataFrame:
    """
    Fetch projected population by age × scenario from table 17-10-0057-01.
    Province-level only (Ontario = "35"). LHIN-level projections are derived
    downstream by applying current LHIN age-share weights.

    Outputs: data/processed/population_projections.csv

    Columns:
        year, scenario, scenario_label, age_group, sex, province, population
    """
    df_raw = _download_csv(TABLE_PROJ)
    df_raw.columns = [c.strip().lower().replace(" ", "_") for c in df_raw.columns]

    # Filter Ontario
    df = df_raw[
        df_raw["geo"].str.lower().str.contains("ontario", na=False)
    ].copy()

    if df.empty:
        df = df_raw[df_raw.get("dguid", pd.Series(dtype=str)).str.contains("35", na=False)].copy()

    df["year"] = pd.to_numeric(df["ref_date"].astype(str).str[:4], errors="coerce")

    # Scenario column (Stats Can label: "Projection scenario")
    scen_col = next((c for c in df.columns if "scenario" in c.lower() or "projection" in c.lower()), None)
    if scen_col:
        # Map to readable labels
        df["scenario"] = df[scen_col].astype(str)
        df["scenario_label"] = df["scenario"].map(
            lambda s: next((v for k,v in PROJECTION_SCENARIOS.items() if k.lower() in s.lower()), s)
        )
    else:
        df["scenario"] = "M1"
        df["scenario_label"] = "Medium-growth (reference)"

    # Age
    age_col = next((c for c in df.columns if "age" in c.lower()), None)
    if age_col:
        df["age_group"] = df[age_col].map(STATCAN_AGE_MAP)
        df = df[df["age_group"].notna()]

    # Sex
    sex_col = next((c for c in df.columns if "sex" in c.lower()), None)
    if sex_col:
        df = df[df[sex_col].str.lower().str.contains("both|total", na=False)]

    val_col = next((c for c in df.columns if c in ("value","val","population")), "value")
    df["population"] = pd.to_numeric(df[val_col], errors="coerce")

    out = df[[
        "year","scenario","scenario_label","age_group","population"
    ]].dropna().copy()
    out = out.groupby(["year","scenario","scenario_label","age_group"], as_index=False)["population"].sum()

    out_path = OUT_DIR / "population_projections.csv"
    out.to_csv(out_path, index=False)
    _update_meta("population_projections", len(out), TABLE_PROJ)
    log.info(f"  Wrote {len(out)} rows → {out_path}")
    return out


# ── Main ────────────────────────────────────────────────────────────────────

def fetch_all(progress_cb=None) -> dict:
    """
    Run all Stats Can fetches. Returns dict of DataFrames.
    progress_cb(step: int, total: int, msg: str) — optional Streamlit progress hook.
    """
    results = {}
    steps = [
        ("population_by_age_lhin", fetch_population_by_lhin, "Population by health region (17-10-0142-01)"),
        ("population_projections",  fetch_population_projections, "Population projections (17-10-0057-01)"),
    ]
    for i, (key, fn, label) in enumerate(steps):
        if progress_cb:
            progress_cb(i, len(steps), label)
        try:
            results[key] = fn()
        except Exception as e:
            log.error(f"Failed to fetch {key}: {e}")
            results[key] = None
    if progress_cb:
        progress_cb(len(steps), len(steps), "Done")
    return results


if __name__ == "__main__":
    fetch_all()
