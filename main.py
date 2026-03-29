"""app/main.py — Streamlit entry point."""

import streamlit as st

st.set_page_config(
    page_title="Ontario Health Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background: #0d1117;
    color: #e6edf3;
}
</style>
""", unsafe_allow_html=True)

st.title("🏥 Ontario Health Intelligence Platform")

st.markdown("""
Use the sidebar to navigate between layers.

| Layer | Focus | Status |
|-------|-------|--------|
| **L2 — Hospitalization Burden** | ED vs admissions, avoidable care, wait times | ✅ Live |
| **L3 — Predictive Trajectory** | Future burden by condition & scenario | ✅ Live |
| **L4 — Cost & Savings** | Top procedures, avoidable cost, ROI | ✅ Live |
| **L1 — Population & Services** | Who lives where, are they served? | 🔜 Pending StatsCan data |
""")
