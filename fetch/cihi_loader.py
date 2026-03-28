"""
fetch/cihi_loader.py
────────────────────
Standardises and validates manually downloaded CIHI data files.

CIHI data requires a free account at https://www.cihi.ca
After registering and downloading, drop files into data/raw/ and run:
    python -m fetch.cihi_loader

Supported files (all free to download from CIHI):
  providers_by_lhin    ← "Physicians in Canada" annual report data tables
                          URL: https://www.cihi.ca/en/physicians-in-canada
                          Download: Excel data tables → sheet "Table 3" or "PHY_Table3"
                          Expected filename pattern: physicians_in_canada_*.xlsx (or .csv)

  np_by_lhin           ← "Regulated Nurses in Canada" report
                          URL: https://www.cihi.ca/en/regulated-nurses-in-canada
                          Expected filename pattern: regulated_nurses_*.xlsx (or .csv)

Schema contracts — each loader outputs one standardised CSV to data/processed/:

  providers_by_lhin.csv
    columns: LHIN, province, year, gp_count, spec_count, np_count,
             total_physicians, gp_per_1000, spec_per_1000, np_per_1000, population

Notes:
  - CIHI Excel tables change column layouts between report years.
    Each loader auto-detects the layout and normalises to the contract above.
  - If a column can't be found, it's filled with NaN and flagged in metadata.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ROOT      = Path(__file__).parent.parent
RAW_DIR   = ROOT / "data" / "raw"
OUT_DIR   = ROOT / "data" / "processed"
META_FILE = ROOT / "data" / "metadata.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── LHIN name normalisation ──────────────────────────────────────────────────
# CIHI uses slightly different region names year to year. Map all variants → canonical.
LHIN_ALIASES = {
    "Erie St. Clair":                         "Erie St. Clair",
    "Erie St. Clair":                         "Erie St. Clair",
    "South West":                             "South West",
    "Waterloo Wellington":                    "Waterloo Wellington",
    "Hamilton Niagara Haldimand Brant":       "Hamilton Niagara Haldimand Brant",
    "HNHB":                                   "Hamilton Niagara Haldimand Brant",
    "Central West":                           "Central West",
    "Mississauga Halton":                     "Mississauga Halton",
    "Toronto Central":                        "Toronto Central",
    "Central":                                "Central",
    "Central East":                           "Central East",
    "South East":                             "South East",
    "Champlain":                              "Champlain",
    "North Simcoe Muskoka":                   "North Simcoe Muskoka",
    "NSM":                                    "North Simcoe Muskoka",
    "North East":                             "North East",
    "NE":                                     "North East",
    "North West":                             "North West",
    "NW":                                     "North West",
}

ALL_LHINS = list(dict.fromkeys(LHIN_ALIASES.values()))


def _norm_lhin(name: str) -> str | None:
    if not isinstance(name, str):
        return None
    name = name.strip()
    return LHIN_ALIASES.get(name) or next(
        (v for k,v in LHIN_ALIASES.items() if k.lower() in name.lower()), None
    )


def _update_meta(key: str, rows: int, source_file: str, issues: list[str]):
    meta = {}
    if META_FILE.exists():
        meta = json.loads(META_FILE.read_text())
    meta[key] = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "rows": rows,
        "source_file": source_file,
        "source": "CIHI — Canadian Institute for Health Information",
        "licence": "CIHI Data Sharing Agreement (free account required)",
        "url": "https://www.cihi.ca/en/access-data-and-reports",
        "issues": issues,
    }
    META_FILE.write_text(json.dumps(meta, indent=2))


# ── Providers loader ─────────────────────────────────────────────────────────

def load_providers(filepath: str | Path | None = None) -> pd.DataFrame | None:
    """
    Load CIHI "Physicians in Canada" data.

    Auto-detects file if filepath is None — looks for physicians_*.csv or
    physicians_*.xlsx in data/raw/.

    Returns normalised DataFrame or None if no file found.

    Output schema:
        LHIN, province, year, gp_count, spec_count, total_physicians,
        gp_per_1000, spec_per_1000, population
    """
    # Find file
    if filepath is None:
        candidates = list(RAW_DIR.glob("physicians_in_canada*.csv")) + \
                     list(RAW_DIR.glob("physicians_in_canada*.xlsx")) + \
                     list(RAW_DIR.glob("phy_*.csv")) + \
                     list(RAW_DIR.glob("phy_*.xlsx"))
        if not candidates:
            log.warning("No CIHI physicians file found in data/raw/")
            return None
        filepath = sorted(candidates)[-1]  # most recent by filename

    filepath = Path(filepath)
    log.info(f"Loading providers from {filepath.name}…")
    issues = []

    # Read
    if filepath.suffix == ".xlsx":
        # Try each sheet looking for the right one
        xls = pd.ExcelFile(filepath)
        target_sheets = [s for s in xls.sheet_names
                         if any(k in s.lower() for k in ["table 3","tbl3","lhin","region","ontario"])]
        sheet = target_sheets[0] if target_sheets else xls.sheet_names[0]
        df_raw = pd.read_excel(filepath, sheet_name=sheet, header=None)
    else:
        df_raw = pd.read_csv(filepath, encoding="utf-8-sig", header=None)

    # Auto-detect header row (first row that has "LHIN" or "region" or a physician count column)
    header_row = 0
    for i, row in df_raw.iterrows():
        row_str = " ".join(str(v).lower() for v in row.values)
        if any(k in row_str for k in ["lhin","health region","family","physician","gp","specialist"]):
            header_row = i
            break

    df = df_raw.iloc[header_row:].copy()
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Locate key columns by fuzzy match
    def find_col(keywords):
        for kw in keywords:
            for c in df.columns:
                if kw in c.lower():
                    return c
        return None

    region_col = find_col(["lhin","health region","region","geo","geography"])
    gp_col     = find_col(["family","general practitioner","gp","fp","family physician"])
    spec_col   = find_col(["specialist","specialist physician","spec"])
    total_col  = find_col(["total physician","all physician","total md"])
    pop_col    = find_col(["population","pop"])
    year_col   = find_col(["year","ref_date","fiscal"])

    if region_col is None:
        issues.append("Could not find a region/LHIN column — check file format")
        log.error(issues[-1])
        return None

    df["LHIN"] = df[region_col].apply(_norm_lhin)
    df = df[df["LHIN"].isin(ALL_LHINS)].copy()

    if df.empty:
        issues.append("No Ontario LHIN rows found after region matching")
        log.error(issues[-1])
        return None

    # Parse numeric columns
    def to_num(col):
        if col is None:
            return np.nan
        return pd.to_numeric(df[col].astype(str).str.replace(",",""), errors="coerce")

    df["gp_count"]          = to_num(gp_col)
    df["spec_count"]        = to_num(spec_col)
    df["total_physicians"]  = to_num(total_col)
    df["population"]        = to_num(pop_col)

    # Derive total if missing
    if df["total_physicians"].isna().all() and not df["gp_count"].isna().all():
        df["total_physicians"] = df["gp_count"].fillna(0) + df["spec_count"].fillna(0)

    # Derive rates if population available
    if not df["population"].isna().all():
        df["gp_per_1000"]   = (df["gp_count"]   / df["population"] * 1000).round(3)
        df["spec_per_1000"] = (df["spec_count"]  / df["population"] * 1000).round(3)
    else:
        df["gp_per_1000"]   = np.nan
        df["spec_per_1000"] = np.nan
        issues.append("Population column not found — per-1,000 rates could not be computed")

    # Year
    if year_col:
        df["year"] = pd.to_numeric(df[year_col].astype(str).str[:4], errors="coerce")
    else:
        # Try to extract year from filename
        yr_match = re.search(r"20\d{2}", filepath.stem)
        df["year"] = int(yr_match.group()) if yr_match else None
        if df["year"] is None:
            issues.append("Year could not be determined from file")

    df["province"] = "Ontario"

    out_cols = ["LHIN","province","year","gp_count","spec_count","total_physicians",
                "gp_per_1000","spec_per_1000","population"]
    out = df[out_cols].copy()

    out_path = OUT_DIR / "providers_by_lhin.csv"
    out.to_csv(out_path, index=False)
    _update_meta("providers_by_lhin", len(out), filepath.name, issues)
    log.info(f"  Wrote {len(out)} rows → {out_path}" + (f"  ⚠ {len(issues)} issue(s)" if issues else ""))
    return out


# ── NP loader ────────────────────────────────────────────────────────────────

def load_nurse_practitioners(filepath: str | Path | None = None) -> pd.DataFrame | None:
    """
    Load CIHI "Regulated Nurses in Canada" NP data.
    Looks for regulated_nurses_*.xlsx / *.csv in data/raw/.

    Output schema:
        LHIN, province, year, np_count, np_per_1000, population
    """
    if filepath is None:
        candidates = list(RAW_DIR.glob("regulated_nurses*.csv")) + \
                     list(RAW_DIR.glob("regulated_nurses*.xlsx")) + \
                     list(RAW_DIR.glob("rn_*.csv")) + \
                     list(RAW_DIR.glob("np_*.csv"))
        if not candidates:
            log.warning("No CIHI NP file found in data/raw/")
            return None
        filepath = sorted(candidates)[-1]

    filepath = Path(filepath)
    log.info(f"Loading NPs from {filepath.name}…")
    issues = []

    if filepath.suffix == ".xlsx":
        xls = pd.ExcelFile(filepath)
        target = [s for s in xls.sheet_names if any(k in s.lower() for k in ["np","nurse practitioner","ontario"])]
        sheet = target[0] if target else xls.sheet_names[0]
        df_raw = pd.read_excel(filepath, sheet_name=sheet, header=None)
    else:
        df_raw = pd.read_csv(filepath, encoding="utf-8-sig", header=None)

    header_row = 0
    for i, row in df_raw.iterrows():
        row_str = " ".join(str(v).lower() for v in row.values)
        if any(k in row_str for k in ["lhin","region","nurse","np","count"]):
            header_row = i
            break

    df = df_raw.iloc[header_row:]
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)
    df.columns = [str(c).strip().lower() for c in df.columns]

    def find_col(kws):
        for k in kws:
            for c in df.columns:
                if k in c.lower():
                    return c
        return None

    region_col = find_col(["lhin","health region","region","geo"])
    np_col     = find_col(["np","nurse practitioner","count"])
    pop_col    = find_col(["population","pop"])
    year_col   = find_col(["year","ref_date"])

    if region_col is None:
        issues.append("Could not find region column")
        return None

    df["LHIN"] = df[region_col].apply(_norm_lhin)
    df = df[df["LHIN"].isin(ALL_LHINS)].copy()

    def to_num(col):
        if col is None:
            return np.nan
        return pd.to_numeric(df[col].astype(str).str.replace(",",""), errors="coerce")

    df["np_count"]    = to_num(np_col)
    df["population"]  = to_num(pop_col)

    if not df["population"].isna().all():
        df["np_per_1000"] = (df["np_count"] / df["population"] * 1000).round(3)
    else:
        df["np_per_1000"] = np.nan

    if year_col:
        df["year"] = pd.to_numeric(df[year_col].astype(str).str[:4], errors="coerce")
    else:
        yr_match = re.search(r"20\d{2}", filepath.stem)
        df["year"] = int(yr_match.group()) if yr_match else None

    df["province"] = "Ontario"
    out = df[["LHIN","province","year","np_count","np_per_1000","population"]].copy()

    out_path = OUT_DIR / "np_by_lhin.csv"
    out.to_csv(out_path, index=False)
    _update_meta("np_by_lhin", len(out), filepath.name, issues)
    log.info(f"  Wrote {len(out)} rows → {out_path}")
    return out


# ── Validate all processed files ─────────────────────────────────────────────

def validate() -> dict[str, dict]:
    """
    Check that all expected processed files exist and pass basic sanity checks.
    Returns a dict: {dataset_name: {ok: bool, issues: [str]}}
    """
    expected = {
        "population_by_age_lhin": {
            "file": "population_by_age_lhin.csv",
            "required_cols": ["LHIN","year","age_group","population"],
            "min_rows": 50,
        },
        "population_projections": {
            "file": "population_projections.csv",
            "required_cols": ["year","scenario","age_group","population"],
            "min_rows": 20,
        },
        "providers_by_lhin": {
            "file": "providers_by_lhin.csv",
            "required_cols": ["LHIN","gp_count"],
            "min_rows": 14,
        },
        "np_by_lhin": {
            "file": "np_by_lhin.csv",
            "required_cols": ["LHIN","np_count"],
            "min_rows": 14,
        },
    }

    results = {}
    for name, spec in expected.items():
        path = OUT_DIR / spec["file"]
        issues = []
        if not path.exists():
            results[name] = {"ok": False, "issues": ["File not found"], "rows": 0}
            continue
        try:
            df = pd.read_csv(path)
            missing_cols = [c for c in spec["required_cols"] if c not in df.columns]
            if missing_cols:
                issues.append(f"Missing columns: {missing_cols}")
            if len(df) < spec["min_rows"]:
                issues.append(f"Only {len(df)} rows (expected ≥{spec['min_rows']})")
            results[name] = {"ok": len(issues)==0, "issues": issues, "rows": len(df)}
        except Exception as e:
            results[name] = {"ok": False, "issues": [str(e)], "rows": 0}

    return results


if __name__ == "__main__":
    load_providers()
    load_nurse_practitioners()
    print("\nValidation:")
    for k,v in validate().items():
        status = "✓" if v["ok"] else "✗"
        print(f"  {status} {k}: {v['rows']} rows  {v['issues'] or ''}")
