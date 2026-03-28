"""
pages/00_data_manager.py
────────────────────────
Streamlit Data Manager — central hub to fetch, upload, validate,
and monitor all data sources for the Ontario Health Intelligence platform.

Accessible at:  http://localhost:8501  (first page = default)
Or via sidebar: "Data Manager"
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fetch.cihi_loader import (load_providers, load_nurse_practitioners,
                                validate as validate_files)
from utils.data_store import get_metadata, load_population, load_providers as ds_providers

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Data Manager · Ontario Health Intelligence",
    page_icon="⚙️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono&display=swap');

html, body, [class*="css"]        { font-family: 'IBM Plex Sans', sans-serif; }
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stHeader"]           { background: #0d1117; }
.main                              { background: #0d1117; }
.block-container                   { padding: 1.5rem 2rem !important; }

h1,h2,h3 { color: #e6edf3 !important; }
p, li     { color: #c9d1d9; }
code      { font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem;
            background: #21262d; padding: 1px 5px; border-radius: 4px; }

.section-header {
    font-size: 0.68rem; font-weight: 600; color: #7d8590;
    text-transform: uppercase; letter-spacing: 0.1em; margin: 20px 0 6px;
}
.source-card {
    background: #161b22; border: 1px solid #21262d; border-radius: 10px;
    padding: 16px 18px; margin-bottom: 10px;
}
.source-title { font-size: 0.92rem; font-weight: 600; color: #e6edf3; }
.source-meta  { font-size: 0.75rem; color: #7d8590; margin-top: 2px; }
.badge {
    display: inline-block; padding: 2px 9px; border-radius: 20px;
    font-size: 0.68rem; font-weight: 600;
}
.badge-ok      { background: #1a3d20; color: #3fb950; border: 1px solid #238636; }
.badge-warn    { background: #3d2c00; color: #d29922; border: 1px solid #9e6a03; }
.badge-missing { background: #2d1517; color: #f85149; border: 1px solid #6e2020; }
.badge-synth   { background: #1b2a3d; color: #58a6ff; border: 1px solid #1f6feb; }

.step { background: #0d1f35; border-left: 3px solid #1f6feb;
        border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 6px 0; }
.step-num { color: #58a6ff; font-weight: 600; font-size: 0.8rem; }
.step-text { color: #c9d1d9; font-size: 0.82rem; margin-top: 2px; }

a { color: #58a6ff !important; }

div[data-testid="stMetric"] {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 10px; padding: 12px 16px;
}
div[data-testid="stMetric"] label { color: #7d8590 !important; font-size: 0.7rem !important; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #e6edf3 !important; }

[data-testid="stExpander"] { background: #161b22; border: 1px solid #21262d; border-radius: 10px; }
[data-testid="stExpander"] summary { color: #c9d1d9 !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("## ⚙️  Data Manager")
st.markdown(
    "Fetch, upload, and validate all data sources for the Ontario Health Intelligence platform. "
    "Until real data is loaded, all dashboard pages use **synthetic data** modelled after public sources."
)
st.divider()

meta = get_metadata()
validation = validate_files()

# ── Status overview ──────────────────────────────────────────────────────────
st.markdown('<p class="section-header">Data source status</p>', unsafe_allow_html=True)

SOURCES = [
    {
        "key":    "population_by_age_lhin",
        "title":  "Population by age × LHIN",
        "source": "Statistics Canada — table 17-10-0142-01",
        "method": "auto",
        "layer":  "L1",
    },
    {
        "key":    "population_projections",
        "title":  "Population projections",
        "source": "Statistics Canada — table 17-10-0057-01",
        "method": "auto",
        "layer":  "L3",
    },
    {
        "key":    "providers_by_lhin",
        "title":  "Physicians in Canada (GPs + specialists)",
        "source": "CIHI — Physicians in Canada annual report",
        "method": "manual",
        "layer":  "L1",
    },
    {
        "key":    "np_by_lhin",
        "title":  "Nurse Practitioners by LHIN",
        "source": "CIHI — Regulated Nurses in Canada",
        "method": "manual",
        "layer":  "L1",
    },
]

for src in SOURCES:
    v      = validation.get(src["key"], {})
    m      = meta.get(src["key"], {})
    ok     = v.get("ok", False)
    rows   = v.get("rows", 0)
    issues = v.get("issues", [])

    if ok:
        badge = '<span class="badge badge-ok">✓ loaded</span>'
        last  = m.get("last_updated","")
        if last:
            try:
                dt = datetime.fromisoformat(last.replace("Z","+00:00"))
                age_days = (datetime.now(timezone.utc) - dt).days
                freshness = f"Updated {age_days}d ago · {rows:,} rows"
            except:
                freshness = f"{rows:,} rows"
        else:
            freshness = f"{rows:,} rows"
    elif rows > 0:
        badge = '<span class="badge badge-warn">⚠ issues</span>'
        freshness = f"{rows:,} rows · {len(issues)} issue(s)"
    else:
        badge = '<span class="badge badge-missing">✗ not loaded</span>'
        freshness = "Using synthetic data"

    method_badge = (
        '<span class="badge" style="background:#0d2d1a;color:#56d364;border:1px solid #238636;margin-left:6px">API auto-fetch</span>'
        if src["method"] == "auto" else
        '<span class="badge" style="background:#21262d;color:#8b949e;border:1px solid #30363d;margin-left:6px">Manual download</span>'
    )
    layer_badge = f'<span class="badge" style="background:#1b2a3d;color:#58a6ff;border:1px solid #1f6feb;margin-left:6px">{src["layer"]}</span>'

    st.markdown(f"""
    <div class="source-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <span class="source-title">{src["title"]}</span>
                {method_badge}{layer_badge}
                <div class="source-meta">{src["source"]}</div>
            </div>
            <div style="text-align:right">
                {badge}
                <div class="source-meta">{freshness}</div>
            </div>
        </div>
        {"" if not issues else f'<div style="margin-top:8px;font-size:0.75rem;color:#d29922">⚠ ' + " · ".join(issues) + "</div>"}
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Auto-fetch: Stats Canada ─────────────────────────────────────────────────
col_auto, col_manual = st.columns([1, 1], gap="large")

with col_auto:
    st.markdown("### 📡 Auto-fetch  —  Statistics Canada")
    st.markdown(
        "Pulls directly from the Stats Can Web Data Service (WDS). "
        "No account required. Licence: **Open Government Licence – Canada**."
    )

    st.markdown('<p class="section-header">What gets fetched</p>', unsafe_allow_html=True)
    st.markdown("""
- **17-10-0142-01** — Population estimates by Ontario health region, sex, and age group (annual)
- **17-10-0057-01** — Projected population to 2043 × 3 growth scenarios (province-level)
""")

    fetch_clicked = st.button("🔄  Fetch from Stats Canada", type="primary", use_container_width=True)

    if fetch_clicked:
        try:
            from fetch.statcan import fetch_all
        except ImportError as e:
            st.error(f"Import error: {e}")
            st.stop()

        progress_bar = st.progress(0)
        status_text  = st.empty()

        def progress_cb(step, total, msg):
            progress_bar.progress(step / max(total, 1))
            status_text.markdown(f"*{msg}*")

        with st.spinner("Connecting to Statistics Canada…"):
            try:
                results = fetch_all(progress_cb=progress_cb)
                progress_bar.progress(1.0)
                status_text.empty()

                ok_count = sum(1 for v in results.values() if v is not None)
                if ok_count == len(results):
                    st.success(f"✓ All {ok_count} tables fetched successfully. Reload the page to see updated status.")
                else:
                    failed = [k for k,v in results.items() if v is None]
                    st.warning(f"Fetched {ok_count}/{len(results)} tables. Failed: {failed}")
                    st.info("Stats Can tables sometimes return 503 during high traffic. Try again in a few minutes.")
                st.rerun()
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Fetch failed: {e}")
                st.info("Check your internet connection. Stats Can WDS requires outbound HTTPS on port 443.")

    # Show preview if data exists
    if (ROOT / "data" / "processed" / "population_by_age_lhin.csv").exists():
        with st.expander("Preview — Population by age × LHIN"):
            df_prev = pd.read_csv(ROOT / "data" / "processed" / "population_by_age_lhin.csv")
            st.dataframe(df_prev.head(30), use_container_width=True, hide_index=True)
            st.caption(f"{len(df_prev):,} rows total")

with col_manual:
    st.markdown("### 📥 Manual download  —  CIHI")
    st.markdown(
        "CIHI data requires a **free account** at [cihi.ca](https://www.cihi.ca). "
        "Registration takes ~2 minutes. Data is free under the CIHI Data Sharing Agreement."
    )

    # ── Physicians ────────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">1 — Physicians in Canada (GPs + specialists)</p>', unsafe_allow_html=True)
    st.markdown("""
<div class="step"><div class="step-num">Step 1</div><div class="step-text">Go to <a href="https://www.cihi.ca/en/physicians-in-canada" target="_blank">cihi.ca/en/physicians-in-canada</a></div></div>
<div class="step"><div class="step-num">Step 2</div><div class="step-text">Click <strong>Access data</strong> → Download the most recent <strong>Data tables (Excel)</strong></div></div>
<div class="step"><div class="step-num">Step 3</div><div class="step-text">Rename the file to <code>physicians_in_canada_2023.xlsx</code> and upload below</div></div>
""", unsafe_allow_html=True)

    phy_file = st.file_uploader(
        "Upload physicians Excel file",
        type=["xlsx","csv"],
        key="phy_upload",
        label_visibility="collapsed",
    )
    if phy_file:
        save_path = ROOT / "data" / "raw" / phy_file.name
        save_path.write_bytes(phy_file.getbuffer())
        with st.spinner("Processing…"):
            result = load_providers(save_path)
        if result is not None:
            st.success(f"✓ Loaded {len(result)} LHIN rows.")
            st.dataframe(result.head(14), use_container_width=True, hide_index=True)
        else:
            st.error("Could not parse file. See the format guide below.")

    with st.expander("Expected format"):
        st.markdown("""
The loader auto-detects column layouts. It looks for columns containing:
- A region name matching Ontario LHINs (e.g. "Toronto Central", "Champlain")
- A family physician / GP count column
- A specialist count column
- Optionally: population, year

If your file has a different structure, rename the relevant columns to:
`LHIN`, `gp_count`, `spec_count`, `population`, `year`
""")

    st.divider()

    # ── Nurse Practitioners ───────────────────────────────────────────────────
    st.markdown('<p class="section-header">2 — Regulated Nurses in Canada (NPs)</p>', unsafe_allow_html=True)
    st.markdown("""
<div class="step"><div class="step-num">Step 1</div><div class="step-text">Go to <a href="https://www.cihi.ca/en/regulated-nurses-in-canada" target="_blank">cihi.ca/en/regulated-nurses-in-canada</a></div></div>
<div class="step"><div class="step-num">Step 2</div><div class="step-text">Download <strong>Data tables → Nurse Practitioners by province/region</strong></div></div>
<div class="step"><div class="step-num">Step 3</div><div class="step-text">Rename to <code>regulated_nurses_2023.xlsx</code> and upload below</div></div>
""", unsafe_allow_html=True)

    np_file = st.file_uploader(
        "Upload NP Excel file",
        type=["xlsx","csv"],
        key="np_upload",
        label_visibility="collapsed",
    )
    if np_file:
        save_path = ROOT / "data" / "raw" / np_file.name
        save_path.write_bytes(np_file.getbuffer())
        with st.spinner("Processing…"):
            result = load_nurse_practitioners(save_path)
        if result is not None:
            st.success(f"✓ Loaded {len(result)} LHIN rows.")
            st.dataframe(result.head(14), use_container_width=True, hide_index=True)
        else:
            st.error("Could not parse file. See the format guide below.")

st.divider()

# ── Validation detail ─────────────────────────────────────────────────────────
st.markdown("### 🔬 Validation detail")

vcols = st.columns(len(SOURCES))
for i, src in enumerate(SOURCES):
    v = validation.get(src["key"], {})
    m = meta.get(src["key"], {})
    with vcols[i]:
        st.markdown(f"**{src['title'].split('(')[0].strip()}**")
        status = "✓ OK" if v.get("ok") else ("⚠ issues" if v.get("rows",0)>0 else "✗ missing")
        color = "#3fb950" if v.get("ok") else ("#d29922" if v.get("rows",0)>0 else "#f85149")
        st.markdown(f"<span style='color:{color};font-weight:600'>{status}</span>", unsafe_allow_html=True)
        st.caption(f"{v.get('rows',0):,} rows")
        for issue in v.get("issues",[]):
            st.caption(f"⚠ {issue}")
        if m.get("source_file"):
            st.caption(f"File: `{m['source_file']}`")

st.divider()

# ── Git instructions ──────────────────────────────────────────────────────────
st.markdown("### 🗂  Git workflow")

st.markdown("""
**What gets committed vs ignored:**

| Path | Git status | Why |
|---|---|---|
| `data/processed/*.csv` | ✅ **Committed** | Small cleaned files, version-controlled |
| `data/raw/` | 🚫 **Gitignored** | Large/binary downloads — never commit |
| `data/metadata.json` | ✅ **Committed** | Tracks data freshness per source |

**After fetching or uploading new data:**
```bash
git add data/processed/ data/metadata.json
git commit -m "data: refresh population + providers $(date +%Y-%m-%d)"
git push
```

**On a fresh clone:**
```bash
pip install -r requirements.txt
streamlit run pages/00_data_manager.py  # fetch Stats Can data first
streamlit run ontario_health_l1.py      # then launch the dashboard
```
""")
