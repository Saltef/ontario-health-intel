"""
fetch/statcan.py
────────────────
Updated 2026 version using PID-based ZIP downloads.
Fetches Ontario population data from Statistics Canada WDS (Web Data Service).
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

# ── Stats Can PID Endpoints (2026 Standard) ─────────────────────────────────
# Note: URLs now point directly to the English ZIP bundles
WDS_BULK_URL   = "https://www150.statcan.gc.ca/n1/en/tbl/csv"
TABLE_POP_HR    = "17100142"   # Pop by health region (annual estimates)
TABLE_PROJ      = "17100057"   # Projected population by scenario

# ── LHIN → Stats Can health region code mapping ─────────────────────────────
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

STATCAN_AGE_MAP = {
    "0 to 4 years":   "0–14", "5 to 9 years":   "0–14", "10 to 14 years": "0–14",
    "15 to 19 years": "15–24", "20 to 24 years": "15–24",
    "25 to 29 years": "25–44", "30 to 34 years": "25–44", "35 to 39 years": "25–44", "40 to 44 years": "25–44",
    "45 to 49 years": "45–64", "50 to 54 years": "45–64", "55 to 59 years": "45–64", "60 to 64 years": "45–64",
    "65 to 69 years": "65–74", "70 to 74 years": "65–74",
    "75 to 79 years": "75–84", "80 to 84 years": "75–84",
    "85 years and over": "85+",
}

PROJECTION_SCENARIOS = {
    "M1": "Medium-growth (reference)",
    "LG": "Low-growth",
    "HG": "High-growth",
}

# ── Helpers ─────────────────────────────────────────────────────────────────

def _download_csv(table_id: str) -> pd.DataFrame:
    """Download and extract a Stats Can table ZIP via the 2026 PID endpoint."""
    url = f"{WDS_BULK_URL}/{table_id}-eng.zip"
    log.info(f"Attempting download for PID {table_id}...")
    
    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            # Find the main data CSV (excludes metadata files)
            csv_candidates = [n for n in z.namelist() if n.endswith(".csv") and "MetaData" not in n]
            if not csv_candidates:
                raise FileNotFoundError(f"No data CSV found in ZIP for {table_id}")
            
            csv_name = csv_candidates[0]
            with z.open(csv_name) as f:
                data = f.read()
                
            raw_path = RAW_DIR / f"statcan_{table_id}.csv"
            raw_path.write_bytes(data)
            log.info(f"  Successfully extracted → {raw_path}")
            
            return pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", low_memory=False)
            
    except requests.exceptions.HTTPError as e:
        log.error(f"HTTP Error for {table_id}: {e}")
        raise

def _update_meta(key: str, rows: int, source_table: str):
    meta = {}
    if META_FILE.exists():
        try:
            meta = json.loads(META_FILE.read_text())
        except json.JSONDecodeError:
            meta = {}
            
    meta[key] = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": rows,
        "source": f"Statistics Canada table {source_table}",
        "licence": "Open Government Licence – Canada",
        "url": f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={source_table}01",
    }
    META_FILE.write_text(json.dumps(meta, indent=2))

# ── Table Fetches ───────────────────────────────────────────────────────────

def fetch_population_by_lhin() -> pd.DataFrame:
    df_raw = _download_csv(TABLE_POP_HR)
    df_raw.columns = [c.strip().lower().replace(" ", "_") for c in df_raw.columns]

    # Filter for Ontario
    df = df_raw[df_raw["geo"].str.contains("Ontario", na=False)].copy()
    
    # Filter for 'Both sexes'
    sex_col = next((c for c in df.columns if "sex" in c), "sex")
    df = df[df[sex_col].str.lower().str.contains("both|total", na=False)]

    # Map age groups
    age_col = next((c for c in df.columns if "age" in c), "age_group")
    df["mapped_age"] = df[age_col].map(STATCAN_AGE_MAP)
    df = df[df["mapped_age"].notna()]

    # Extract Year and LHIN
    df["year"] = pd.to_numeric(df["ref_date"].astype(str).str[:4], errors="coerce")
    
    inv_map = {v: k for k, v in LHIN_HR_MAP.items()}
    dguid_col = next((c for c in df.columns if "dguid" in c), "dguid")
    df["hr_code"] = df[dguid_col].astype(str).str[-4:]
    df["LHIN"] = df["hr_code"].map(inv_map)

    # Aggregate
    val_col = next((c for c in df.columns if c in ["value", "val", "population"]), "value")
    out = df.groupby(["LHIN", "year", "mapped_age"], as_index=False)[val_col].sum()
    out.columns = ["LHIN", "year", "age_group", "population"]

    out_path = OUT_DIR / "population_by_age_lhin.csv"
    out.to_csv(out_path, index=False)
    _update_meta("population_by_age_lhin", len(out), TABLE_POP_HR)
    return out

def fetch_population_projections() -> pd.DataFrame:
    df_raw = _download_csv(TABLE_PROJ)
    df_raw.columns = [c.strip().lower().replace(" ", "_") for c in df_raw.columns]

    df = df_raw[df_raw["geo"].str.lower().str.contains("ontario", na=False)].copy()
    df["year"] = pd.to_numeric(df["ref_date"].astype(str).str[:4], errors="coerce")

    # Scenario handling
    scen_col = next((c for c in df.columns if "scenario" in c or "projection" in c), "scenario")
    df["scenario_label"] = df[scen_col].map(
        lambda s: next((v for k,v in PROJECTION_SCENARIOS.items() if k.lower() in str(s).lower()), s)
    )

    age_col = next((c for c in df.columns if "age" in c), "age_group")
    df["mapped_age"] = df[age_col].map(STATCAN_AGE_MAP)
    df = df[df["mapped_age"].notna()]

    val_col = next((c for c in df.columns if c in ["value", "val", "population"]), "value")
    out = df.groupby(["year", "scenario_label", "mapped_age"], as_index=False)[val_col].sum()
    out.columns = ["year", "scenario_label", "age_group", "population"]

    out_path = OUT_DIR / "population_projections.csv"
    out.to_csv(out_path, index=False)
    _update_meta("population_projections", len(out), TABLE_PROJ)
    return out

def fetch_all(progress_cb=None) -> dict:
    results = {}
    steps = [
        ("population_by_age_lhin", fetch_population_by_lhin, "Population by LHIN (17-10-0142)"),
        ("population_projections", fetch_population_projections, "Projections (17-10-0057)"),
    ]
    for i, (key, fn, label) in enumerate(steps):
        if progress_cb: progress_cb(i, len(steps), label)
        try:
            results[key] = fn()
        except Exception as e:
            log.error(f"Failed {key}: {e}")
            results[key] = None
    if progress_cb: progress_cb(len(steps), len(steps), "Completed")
    return results

if __name__ == "__main__":
    fetch_all()
