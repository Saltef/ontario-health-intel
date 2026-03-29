"""pages/02_hospitalization_burden.py"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from loaders.hospitalization_loader import (
    load_burden, get_conditions, get_years, filter_burden, get_wait_times
)
from utils.helpers import (
    dark_layout, fmt_currency, fmt_number,
    DARK_BG, CARD_BG, GREEN, YELLOW, RED, BLUE, PURPLE, CONDITION_PALETTE
)

st.set_page_config(page_title="L2 · Hospitalization Burden", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; background: #0d1117; color: #e6edf3; }
.metric-card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px 20px; }
</style>
""", unsafe_allow_html=True)

st.markdown("## Layer 2 — Hospitalization Burden")
st.caption("ED visits vs. admissions · Avoidable care · Specialist wait times · Source: CIHI / Fraser Institute 2025")

df = load_burden()
if df.empty:
    st.stop()

# ── Sidebar filters
with st.sidebar:
    st.markdown("### Filters")
    all_conditions = get_conditions(df)
    selected_conditions = st.multiselect(
        "Conditions", all_conditions, default=all_conditions
    )
    all_years = get_years(df)
    selected_year = st.selectbox("Year", all_years)

filt = filter_burden(df, conditions=selected_conditions, year=selected_year)

if filt.empty:
    st.warning("No data for selected filters.")
    st.stop()

# ── KPI row
st.markdown("### At a Glance")
k1, k2, k3, k4, k5 = st.columns(5)

total_ed        = filt["ed_visits"].sum()
total_admissions= filt["admissions"].sum()
total_avoidable = filt["avoidable_admissions"].sum()
total_av_cost   = filt["avoidable_cost"].sum()
avg_gap         = filt["care_gap_score"].mean()

k1.metric("ED Visits",          fmt_number(total_ed))
k2.metric("Admissions",         fmt_number(total_admissions))
k3.metric("Avoidable Admissions", fmt_number(total_avoidable))
k4.metric("Avoidable Cost",     fmt_currency(total_av_cost))
k5.metric("Avg Care Gap Score", f"{avg_gap:.1f}" if pd.notna(avg_gap) else "N/A")

st.divider()

# ── Section 1: ED vs Admissions
st.markdown("### ED Visits vs. Admissions by Condition")

ed_long = filt[["condition", "ed_visits", "admissions"]].melt(
    id_vars="condition", var_name="Type", value_name="Count"
)
ed_long["Type"] = ed_long["Type"].map({
    "ed_visits": "ED Visits", "admissions": "Admissions"
})

fig_ed = px.bar(
    ed_long, x="condition", y="Count", color="Type", barmode="group",
    color_discrete_map={"ED Visits": BLUE, "Admissions": YELLOW},
)
dark_layout(fig_ed, height=380)
st.plotly_chart(fig_ed, use_container_width=True)

st.divider()

# ── Section 2: Avoidable admissions
st.markdown("### Avoidable vs. Necessary Admissions")

col_a, col_b = st.columns(2)

with col_a:
    fig_av = px.bar(
        filt.sort_values("avoidable_admissions", ascending=True),
        x="avoidable_admissions", y="condition", orientation="h",
        color="avoidability_pct_display",
        color_continuous_scale=[[0, GREEN], [0.5, YELLOW], [1, RED]],
        labels={
            "avoidable_admissions": "Avoidable Admissions",
            "avoidability_pct_display": "Avoidability %",
        },
    )
    dark_layout(fig_av, title="Avoidable Admissions (count)", height=380)
    st.plotly_chart(fig_av, use_container_width=True)

with col_b:
    # Stacked: avoidable vs non-avoidable cost
    cost_long = filt[["condition", "avoidable_cost", "non_avoidable_cost"]].melt(
        id_vars="condition", var_name="Type", value_name="Cost"
    )
    cost_long["Type"] = cost_long["Type"].map({
        "avoidable_cost": "Avoidable", "non_avoidable_cost": "Necessary"
    })
    fig_cost = px.bar(
        cost_long, x="condition", y="Cost", color="Type", barmode="stack",
        color_discrete_map={"Avoidable": RED, "Necessary": BLUE},
        labels={"Cost": "Cost ($)", "condition": "Condition"},
    )
    fig_cost.update_layout(yaxis_tickformat="$,.0f")
    dark_layout(fig_cost, title="Avoidable vs. Necessary Cost", height=380)
    st.plotly_chart(fig_cost, use_container_width=True)

st.divider()

# ── Section 3: Wait times
st.markdown("### Specialist Wait Times")
wt = get_wait_times(df)
wt_filtered = wt[wt["condition"].isin(selected_conditions)]

# Split: conditions with data vs without
has_wait  = wt_filtered[wt_filtered["specialist_wait_weeks_ontario"].notna()].copy()
no_wait   = wt_filtered[wt_filtered["specialist_wait_weeks_ontario"].isna()]["condition"].tolist()

if not has_wait.empty:
    wt_long = has_wait[
        ["condition", "specialist_wait_weeks_ontario", "specialist_wait_weeks_canada"]
    ].melt(id_vars="condition", var_name="Region", value_name="Wait (weeks)")
    wt_long["Region"] = wt_long["Region"].map({
        "specialist_wait_weeks_ontario": "Ontario",
        "specialist_wait_weeks_canada":  "Canada (avg)",
    })

    fig_wt = px.bar(
        wt_long, x="condition", y="Wait (weeks)", color="Region", barmode="group",
        color_discrete_map={"Ontario": BLUE, "Canada (avg)": YELLOW},
    )
    dark_layout(fig_wt, title="Specialist Wait Weeks: Ontario vs Canada", height=360)
    st.plotly_chart(fig_wt, use_container_width=True)

    # Wait time change since 1993
    trend_df = has_wait.dropna(subset=["wait_time_change_1993_2025_pct"])
    if not trend_df.empty:
        fig_trend = px.bar(
            trend_df.sort_values("wait_time_change_1993_2025_pct"),
            x="wait_time_change_1993_2025_pct", y="condition", orientation="h",
            color="wait_time_change_1993_2025_pct",
            color_continuous_scale=[[0, GREEN], [0.5, YELLOW], [1, RED]],
            labels={"wait_time_change_1993_2025_pct": "Change vs 1993 (%)"},
        )
        dark_layout(fig_trend, title="Wait Time Change: 1993 → 2025 (%)", height=300)
        st.plotly_chart(fig_trend, use_container_width=True)

if no_wait:
    st.info(
        f"No wait-time data available for: **{', '.join(no_wait)}** "
        "(not tracked in Fraser Institute 2025 report)"
    )

st.divider()

# ── Section 4: Raw table
with st.expander("📋 Full data table"):
    display_cols = [
        "condition", "ed_visits", "admissions",
        "avoidable_admissions", "avoidability_pct_display",
        "avoidable_cost", "care_gap_score",
        "specialist_wait_weeks_ontario", "specialist_wait_weeks_canada",
    ]
    st.dataframe(
        filt[[c for c in display_cols if c in filt.columns]],
        hide_index=True, use_container_width=True
    )
