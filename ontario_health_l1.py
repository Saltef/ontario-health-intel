import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# ──────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────
st.set_page_config(
    page_title="Ontario Health Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for the "Dark Mode" Analytics look
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.main { background: #0d1117; }
.page-title { font-size: 1.4rem; font-weight: 600; color: #e6edf3; margin-bottom: 0; }
.page-sub { font-size: 0.78rem; color: #7d8590; margin-top: 2px; margin-bottom: 12px; }
.section-label { font-size: 0.68rem; font-weight: 600; color: #7d8590; text-transform: uppercase; letter-spacing: 0.09em; margin: 18px 0 8px; }
.provider-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #21262d; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# DATA & PROJECTION ENGINE
# ──────────────────────────────────────────
BENCHMARK_GP = 1.05  # Target physicians per 1,000 residents

# Baseline 2024 Data (Layer 1 + Layer 2 Capacity)
LHIN_BASE = {
    "Erie St. Clair":      {"lat": 42.32, "lon": -82.55, "pop_2024": 650_000,   "growth": 0.012, "gps": 572},
    "South West":          {"lat": 42.98, "lon": -81.25, "pop_2024": 1_000_000, "growth": 0.015, "gps": 920},
    "Waterloo Wellington": {"lat": 43.55, "lon": -80.50, "pop_2024": 850_000,   "growth": 0.021, "gps": 867},
    "Hamilton Niagara":    {"lat": 43.18, "lon": -79.90, "pop_2024": 1_500_000, "growth": 0.011, "gps": 1725},
    "Central West":        {"lat": 43.72, "lon": -79.90, "pop_2024": 950_000,   "growth": 0.025, "gps": 902},
    "Mississauga Halton":  {"lat": 43.60, "lon": -79.65, "pop_2024": 1_300_000, "growth": 0.018, "gps": 1430},
    "Toronto Central":     {"lat": 43.67, "lon": -79.39, "pop_2024": 1_250_000, "growth": 0.014, "gps": 1562},
    "Central":             {"lat": 43.83, "lon": -79.50, "pop_2024": 1_900_000, "growth": 0.022, "gps": 1995},
    "Central East":        {"lat": 44.15, "lon": -78.90, "pop_2024": 1_700_000, "growth": 0.019, "gps": 1666},
    "South East":          {"lat": 44.52, "lon": -76.55, "pop_2024": 520_000,   "growth": 0.008, "gps": 390},
    "Champlain":           {"lat": 45.30, "lon": -75.70, "pop_2024": 1_400_000, "growth": 0.016, "gps": 1652},
    "North Simcoe":        {"lat": 44.85, "lon": -79.60, "pop_2024": 500_000,   "growth": 0.020, "gps": 410},
    "North East":          {"lat": 46.80, "lon": -81.00, "pop_2024": 560_000,   "growth": 0.003, "gps": 364},
    "North West":          {"lat": 49.40, "lon": -86.60, "pop_2024": 240_000,   "growth": 0.001, "gps": 139},
}

@st.cache_data
def get_projected_df(year, scenario_mult):
    rows = []
    years_out = year - 2024
    for name, d in LHIN_BASE.items():
        # Calculate Projected Population (Layer 3)
        effective_growth = d['growth'] * scenario_mult
        proj_pop = int(d['pop_2024'] * ((1 + effective_growth) ** years_out))
        
        # Calculate Future Care Density (Physicians per 1k)
        # This simulates service erosion if headcount doesn't grow with population
        future_rate = (d['gps'] / proj_pop) * 1000
        
        rows.append({
            "LHIN": name, "lat": d['lat'], "lon": d['lon'],
            "Population": proj_pop,
            "Growth %": round(((proj_pop/d['pop_2024'])-1)*100, 1),
            "Physicians": d['gps'],
            "Physicians_per_1k": round(future_rate, 2)
        })
    return pd.DataFrame(rows)

# ──────────────────────────────────────────
# SIDEBAR: PROJECTION CONTROLS
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📈 Time Machine")
    target_year = st.slider("Target Year", 2024, 2043, 2030)
    scenario = st.radio("Growth Scenario", ["Low", "Reference", "High"], index=1)
    
    s_map = {"Low": 0.75, "Reference": 1.0, "High": 1.35}
    df = get_projected_df(target_year, s_map[scenario])
    
    st.divider()
    st.markdown("### 🔍 LHIN Focus")
    selected_name = st.selectbox("Select LHIN to Inspect", df["LHIN"].tolist())
    l_data = df[df["LHIN"] == selected_name].iloc[0]

# ──────────────────────────────────────────
# MAIN CONTENT
# ──────────────────────────────────────────
st.markdown('<div class="page-title">Ontario Health Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown(f'<div class="page-sub">Year: **{target_year}** | Scenario: **{scenario}** (L1 Baseline + L3 Projections)</div>', unsafe_allow_html=True)

col_map, col_detail = st.columns([2, 1], gap="medium")

with col_map:
    # Population Heatmap
    fig = px.scatter_mapbox(
        df, lat="lat", lon="lon", 
        size="Population", 
        color="Growth %",
        hover_name="LHIN",
        color_continuous_scale="Viridis",
        size_max=40, zoom=4.6, 
        mapbox_style="carto-darkmatter",
        height=650
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor="#0d1117")
    st.plotly_chart(fig, use_container_width=True)

with col_detail:
    st.markdown(f"## {selected_name}")
    
    # Population Stats
    st.markdown('<p class="section-label">Population Projection</p>', unsafe_allow_html=True)
    st.metric("Estimated Residents", f"{l_data['Population']:,}", f"+{l_data['Growth %']}%")
    
    # Hospital/Care Capacity (Layer 2 Simulation)
    st.markdown('<p class="section-label">Care Capacity (Layer 2)</p>', unsafe_allow_html=True)
    
    rate = l_data['Physicians_per_1k']
    ratio = rate / BENCHMARK_GP
    
    # Dynamic styling based on projected density
    status_color = "#3fb950" if ratio >= 1.0 else "#d29922" if ratio >= 0.8 else "#f85149"
    status_text = "Adequate" if ratio >= 1.0 else "Under Pressure" if ratio >= 0.8 else "Critical Gap"

    st.markdown(f"""
    <div class="provider-row">
        <div>
            <div style="font-size:0.85rem; color:#e6edf3;">Family Physicians</div>
            <div style="font-size:0.7rem; color:#7d8590;">Projected: {rate:.2f} per 1,000</div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:0.85rem; color:{status_color}; font-weight:600;">{status_text}</div>
            <div style="font-size:0.6rem; color:#7d8590;">{ratio:.1%} of benchmark</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Placeholder for remaining Layer 2 Data
    st.markdown('<p class="section-label">Hospital Performance</p>', unsafe_allow_html=True)
    st.info("Hospital metrics (ALC rates, ER wait times) will be enabled once Layer 2 Excel files are uploaded.")
    
    # Quick Comparison Table
    st.markdown('<p class="section-label">Top Growth LHINs</p>', unsafe_allow_html=True)
    st.dataframe(
        df[["LHIN", "Population", "Growth %"]].sort_values("Growth %", ascending=False).head(5),
        hide_index=True, use_container_width=True
    )

# ──────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────
st.divider()
st.caption("Data sources: StatsCan 2021 Census & 2043 Projections (Simulated). Care benchmarks modeled after CIHI 2022.")
