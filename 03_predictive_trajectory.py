"""pages/03_predictive_trajectory.py"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from loaders.trajectory_loader import (
    load_trajectory, get_scenarios, get_conditions, filter_trajectory
)
from utils.helpers import (
    dark_layout, fmt_currency, fmt_number,
    SCENARIO_COLORS, DARK_BG, CARD_BG, RED, YELLOW, BLUE, GREEN
)

st.set_page_config(page_title="L3 · Predictive Trajectory", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; background: #0d1117; color: #e6edf3; }
</style>
""", unsafe_allow_html=True)

st.markdown("## Layer 3 — Predictive Care Trajectory")
st.caption("Projected ED visits, admissions, and avoidable burden by condition and scenario · Source: CIHI / Data-driven V2 model")

df = load_trajectory()
if df.empty:
    st.stop()

# ── Sidebar
with st.sidebar:
    st.markdown("### Scenario")
    available_scenarios = get_scenarios(df)
    # Always show Historical + user-selected projection
    projection_scenarios = [s for s in available_scenarios if s != "Historical"]
    selected_projection = st.radio(
        "Projection scenario", projection_scenarios,
        index=projection_scenarios.index("Reference") if "Reference" in projection_scenarios else 0
    )
    show_historical = st.checkbox("Show historical baseline", value=True)

    st.markdown("### Conditions")
    all_conditions = get_conditions(df)
    selected_conditions = st.multiselect(
        "Select conditions", all_conditions, default=all_conditions
    )

active_scenarios = [selected_projection]
if show_historical:
    active_scenarios.append("Historical")

filt = filter_trajectory(df, scenarios=active_scenarios, conditions=selected_conditions)

if filt.empty:
    st.warning("No data for selected filters.")
    st.stop()

# ── KPI: change from 2024 baseline to 2034 projection (Reference)
ref_df = filter_trajectory(df, scenarios=["Historical", selected_projection], conditions=selected_conditions)
base_2024 = ref_df[ref_df["year"] == 2024]
proj_2034 = ref_df[ref_df["year"] == 2034]

if not base_2024.empty and not proj_2034.empty:
    st.markdown("### 2024 → 2034 Summary")
    k1, k2, k3, k4 = st.columns(4)

    ed_2024   = base_2024["ed_visits"].sum()
    ed_2034   = proj_2034["ed_visits"].sum()
    adm_2024  = base_2024["admissions"].sum()
    adm_2034  = proj_2034["admissions"].sum()
    av_c_2024 = base_2024["avoidable_cost"].sum()
    av_c_2034 = proj_2034["avoidable_cost"].sum()
    av_a_2024 = base_2024["avoidable_admissions"].sum()
    av_a_2034 = proj_2034["avoidable_admissions"].sum()

    def pct_delta(a, b):
        return f"{((b-a)/a*100):+.1f}%" if a else "N/A"

    k1.metric("ED Visits 2034",          fmt_number(ed_2034),    pct_delta(ed_2024, ed_2034))
    k2.metric("Admissions 2034",         fmt_number(adm_2034),   pct_delta(adm_2024, adm_2034))
    k3.metric("Avoidable Admissions 2034", fmt_number(av_a_2034), pct_delta(av_a_2024, av_a_2034))
    k4.metric("Avoidable Cost 2034",     fmt_currency(av_c_2034), pct_delta(av_c_2024, av_c_2034))

    st.divider()

# ── Chart 1: ED Visit trajectory
st.markdown("### ED Visit Projections by Condition")
fig_ed = px.line(
    filt, x="year", y="ed_visits", color="condition",
    line_dash="scenario",
    line_dash_map={"Historical": "dot", selected_projection: "solid"},
    markers=True,
    labels={"ed_visits": "ED Visits", "year": "Year"},
)
dark_layout(fig_ed, height=400)
st.plotly_chart(fig_ed, use_container_width=True)

# ── Chart 2: Admissions trajectory
st.markdown("### Admissions Projections by Condition")
fig_adm = px.line(
    filt, x="year", y="admissions", color="condition",
    line_dash="scenario",
    line_dash_map={"Historical": "dot", selected_projection: "solid"},
    markers=True,
    labels={"admissions": "Admissions", "year": "Year"},
)
dark_layout(fig_adm, height=400)
st.plotly_chart(fig_adm, use_container_width=True)

st.divider()

# ── Chart 3: Avoidable cost growth (area)
st.markdown("### Avoidable Cost Trajectory")

proj_only = filter_trajectory(
    df, scenarios=active_scenarios, conditions=selected_conditions
)
fig_av = px.area(
    proj_only.sort_values(["condition", "year"]),
    x="year", y="avoidable_cost", color="condition",
    labels={"avoidable_cost": "Avoidable Cost ($)", "year": "Year"},
)
fig_av.update_layout(yaxis_tickformat="$,.0f")
dark_layout(fig_av, height=400)
st.plotly_chart(fig_av, use_container_width=True)

# ── Chart 4: Scenario comparison for a single condition
st.divider()
st.markdown("### Scenario Band — Single Condition")

all_proj_scenarios = [s for s in get_scenarios(df) if s != "Historical"]
comparison_condition = st.selectbox("Condition", all_conditions)
metric_choice = st.radio(
    "Metric", ["ed_visits", "admissions", "avoidable_admissions", "avoidable_cost"],
    horizontal=True
)

band_df = filter_trajectory(
    df, scenarios=all_proj_scenarios + ["Historical"],
    conditions=[comparison_condition]
)

if not band_df.empty:
    fig_band = go.Figure()
    for scenario in ["Historical"] + all_proj_scenarios:
        sub = band_df[band_df["scenario"] == scenario].sort_values("year")
        if sub.empty:
            continue
        fig_band.add_trace(go.Scatter(
            x=sub["year"], y=sub[metric_choice],
            mode="lines+markers",
            name=scenario,
            line=dict(
                color=SCENARIO_COLORS.get(scenario, "#7d8590"),
                dash="dot" if scenario == "Historical" else "solid",
                width=2,
            ),
        ))
    fig_band.update_layout(
        yaxis_tickformat="$,.0f" if "cost" in metric_choice else ",",
    )
    dark_layout(fig_band, title=f"{comparison_condition} — {metric_choice} by Scenario", height=380)
    st.plotly_chart(fig_band, use_container_width=True)

# ── Raw table
with st.expander("📋 Full projection data"):
    st.dataframe(filt.sort_values(["condition", "year"]), hide_index=True, use_container_width=True)
