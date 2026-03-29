"""pages/00_data_manager.py — upload and preview source files."""

import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Data Manager", layout="wide")
st.markdown("## ⚙️ Data Manager")
st.caption("Upload replacement source files or verify what's currently loaded.")

INPUT_DIR = Path("inputData")
INPUT_DIR.mkdir(exist_ok=True)

FILE_MAP = {
    "Layer 2 — Current Burden":         "layer2_current_burden.csv",
    "Layer 3 — Predictive Trajectory":  "layer3_predictive_trajectory.csv",
    "Layer 4 — Cost Analysis":          "layer4_cost_analysis.csv",
}

for label, filename in FILE_MAP.items():
    with st.expander(f"**{label}** — `{filename}`"):
        dest = INPUT_DIR / filename
        if dest.exists():
            df = pd.read_csv(dest)
            st.success(f"✅ {len(df):,} rows · {len(df.columns)} columns")
            st.dataframe(df.head(5), use_container_width=True)
        else:
            st.warning("⚠️ File not found in `inputData/`")

        uploaded = st.file_uploader(
            f"Upload new `{filename}`", type=["csv"], key=filename
        )
        if uploaded:
            dest.write_bytes(uploaded.read())
            st.success("Saved. Reload the page to preview.")

st.divider()
st.markdown("""
**Layer 1 — Population Demographics** is generated from Statistics Canada.
Run the fetcher from your terminal:
```bash
python -m fetch.statcan
```
This writes `inputData/layer1_population_demographics.csv` and will unlock the **L1 Population & Services** page.
""")
