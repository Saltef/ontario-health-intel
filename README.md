# Ontario Health Intel

Ontario Health Intel is a Streamlit-based analytics prototype for showing Ontario healthcare burden and economics across four layers:

1. Population baseline
2. Current hospitalization burden
3. Predictive trajectory
4. Cost and avoidable-savings analysis

The current emphasis is on Layer 2 to Layer 4 condition-level modeling, with projection years available for 2024, 2029, and 2034.

## Tech Stack

- Python
- Streamlit
- Pandas / NumPy
- Plotly
- OpenPyXL (for CIHI/NPDB workbook ingestion)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Core Data Files

Primary dashboard inputs live in `inputData/`:

- `layer1_population_demographics.csv`
- `layer2_current_burden.csv`
- `layer3_predictive_trajectory.csv`
- `layer4_cost_analysis.csv`
- `layer4_metadata.csv`

`layer4_cost_analysis.csv` now includes year-specific cost views for 2024, 2029, and 2034, plus percent columns for share metrics (for easier demo readability).

`layer4_metadata.csv` stores formulas, column definitions, and plain-language finance summaries.

## Run Options

### Main launcher

```powershell
python streamlit.py
```

This launches `Home.py`.

### Direct Streamlit entrypoint

```powershell
streamlit run Home.py
```

### Standalone data manager page

```powershell
streamlit run 00_data_manager.py
```

## Data Refresh Commands

### StatsCan auto-fetch

```powershell
python -m fetch.statcan
```

Outputs to `data/processed/` (for population mapping workflows).

### CIHI loaders

```powershell
python -m fetch.cihi_loader
```

Parses supported CIHI files from `data/raw/` and writes normalized outputs to `data/processed/`.

## Repository Layout

```text
inputData/                 Layered dashboard inputs and metadata
fetch/                     Data ingestion scripts (StatsCan, CIHI)
utils/                     Shared loaders/helpers for projection logic
data/                      Auto-fetched and processed auxiliary datasets
app/, pages/, scripts/     Legacy/prototype app modules and utilities
```

## Future Roadmap

### Platform Stabilization

- Consolidate to one production Streamlit app path (`Home.py` + validated pages).
- Remove or archive legacy duplicate entrypoints (`app/*`, `map_dashboard.py`, `ontario_health_l1.py`).
- Standardize imports and module layout (single loader/util package structure).
- Add compatibility checks so dashboards fail gracefully when schema changes.

### Data Quality and Governance

- Add strict schema contracts for `layer1` to `layer4` with automated validation.
- Expand `layer4_metadata.csv` into a full data dictionary + assumptions registry.
- Add dataset freshness tracking (last refresh, source version, confidence by field).
- Create reproducible ETL scripts to regenerate dashboard inputs from raw sources.

### Economic Modeling Enhancements

- Add inflation-adjusted and nominal cost views for every projection year.
- Add scenario-based economics (Low/Reference/High) beyond current reference path.
- Introduce additional cost drivers:
  - Workforce pressure (overtime, locum, vacancy costs)
  - Readmission costs and avoidable revisit penalties
  - ALC/LOS bed-day opportunity costs
  - Community-care substitution costs
  - Drug and diagnostics inflation factors
- Add sensitivity analysis for key assumptions (avoidability %, growth rates, unit costs).

### Geographic Expansion

- Move from Ontario-level condition economics to city/LHIN-level financial projections.
- Add allocation models linking population growth and age mix to local cost burden.
- Add map layers for "cost growth hotspots" and "avoidable-cost opportunity zones."

### Product and Demo Features

- Add a "Demo mode" narrative flow with prebuilt story steps and key KPI callouts.
- Add downloadable executive summary exports (CSV/PDF) for selected scenario/year.
- Add intervention planner: expected impact and cost ranges by condition and region.
- Add side-by-side baseline vs intervention view for decision-making workshops.

### Engineering and Delivery

- Add automated tests for loaders, formulas, and cross-layer consistency.
- Add CI checks (lint, type checks, schema checks, smoke tests).
- Add environment bootstrap scripts for one-command local setup.
- Add release/versioning notes so model and data updates are traceable over time.

## Recommended Demo Flow

1. Run `python streamlit.py`.
2. Present Layer 2 burden context (volume, avoidability, wait times).
3. Present Layer 3 trajectory (2024 to 2034 growth by condition).
4. Present Layer 4 economics (total cost, avoidable cost, concentration, growth).
5. Use `layer4_metadata.csv` to explain formulas and assumptions clearly during Q&A.
