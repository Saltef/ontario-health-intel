"""pages/04_cost_and_savings.py"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from loaders.cost_loader import load_costs, get_top_by_cost
from utils.helpers import (
    dark_layout, fmt_currency, fmt_number,
    DARK_BG, CARD_BG, GREEN, YELLOW, RED, BLUE, PURPLE
)

st.set_page_config(page_title="L4 · Cost & Savings", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; background: #0d1117; color: #e6edf3; }
</style>
""", unsafe_allow_html=True)

st.markdown("## Layer 4 — Cost Breakdown & Avoidable Savings")
st.caption("Top conditions by cost · Avoidable burden 2024 → 2034 · ROI of primary care investment · Source: CIHI Patient Cost Estimator (DAD)")

df = load_costs()
if df.empty:
    st.stop()

top10 = get_top_by_cost(df, 10)

# ── KPI row
st.markdown("### System-Wide Summary")
k1, k2, k3, k4 = st.columns(4)

total_cost    = top10["total_cost_2024"].sum()
total_av_2024 = top10["avoidable_cost_2024"].sum()
total_av_2034 = top10["avoidable_cost_2034"].sum()
total_sav_10  = top10["savings_10yr"].sum()

k1.metric("Total Cost (Top 10)",          fmt_currency(total_cost))
k2.metric("Avoidable Cost 2024",           fmt_currency(total_av_2024))
k3.metric("Avoidable Cost 2034 (projected)", fmt_currency(total_av_2034),
          f"{((total_av_2034 - total_av_2024)/total_av_2024*100):+.1f}%")
k4.metric("Potential Savings over 10 yr", fmt_currency(total_sav_10))

st.divider()

# ── Chart 1: Total cost vs avoidable portion (horizontal bar)
st.markdown("### Total Cost vs. Avoidable Portion by Condition")

cost_long = top10[["condition", "avoidable_cost_2024"]].copy()
cost_long["necessary_cost"] = top10["total_cost_2024"] - top10["avoidable_cost_2024"]
cost_long = cost_long.sort_values("total_cost_2024", ascending=True) if "total_cost_2024" in top10.columns else cost_long

plot_df = top10.sort_values("total_cost_2024", ascending=True).copy()
plot_df["necessary_cost"] = plot_df["total_cost_2024"] - plot_df["avoidable_cost_2024"]

fig1 = go.Figure()
fig1.add_trace(go.Bar(
    y=plot_df["condition"], x=plot_df["necessary_cost"],
    name="Necessary Cost", orientation="h",
    marker_color=BLUE,
))
fig1.add_trace(go.Bar(
    y=plot_df["condition"], x=plot_df["avoidable_cost_2024"],
    name="Avoidable Cost", orientation="h",
    marker_color=RED,
))
fig1.update_layout(barmode="stack", xaxis_tickformat="$,.0f")
dark_layout(fig1, title="2024 Cost Breakdown (Top 10 Conditions)", height=420)
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ── Chart 2: Avoidable cost growth 2024 → 2034
st.markdown("### Avoidable Cost Growth: 2024 → 2034")

col_a, col_b = st.columns(2)

with col_a:
    av_compare = top10[["condition", "avoidable_cost_2024", "avoidable_cost_2034"]].melt(
        id_vars="condition", var_name="Period", value_name="Avoidable Cost"
    )
    av_compare["Period"] = av_compare["Period"].map({
        "avoidable_cost_2024": "2024", "avoidable_cost_2034": "2034 (projected)"
    })
    fig2 = px.bar(
        av_compare, x="condition", y="Avoidable Cost", color="Period", barmode="group",
        color_discrete_map={"2024": YELLOW, "2034 (projected)": RED},
    )
    fig2.update_layout(yaxis_tickformat="$,.0f")
    dark_layout(fig2, title="Avoidable Cost: 2024 vs 2034", height=380)
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    # Growth % as horizontal bar
    growth_df = top10.dropna(subset=["avoidable_cost_growth_pct"]).sort_values("avoidable_cost_growth_pct")
    fig3 = px.bar(
        growth_df, x="avoidable_cost_growth_pct", y="condition", orientation="h",
        color="avoidable_cost_growth_pct",
        color_continuous_scale=[[0, GREEN], [0.5, YELLOW], [1, RED]],
        labels={"avoidable_cost_growth_pct": "Growth (%)"},
    )
    dark_layout(fig3, title="Avoidable Cost Growth % (2024→2034)", height=380)
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Chart 3: Savings & ROI
st.markdown("### ROI of Primary Care Investment")

col_c, col_d = st.columns(2)

with col_c:
    savings_df = top10[["condition", "savings_5yr", "savings_10yr"]].melt(
        id_vars="condition", var_name="Horizon", value_name="Savings"
    )
    savings_df["Horizon"] = savings_df["Horizon"].map({
        "savings_5yr": "5-Year Savings", "savings_10yr": "10-Year Savings"
    })
    fig4 = px.bar(
        savings_df, x="condition", y="Savings", color="Horizon", barmode="group",
        color_discrete_map={"5-Year Savings": BLUE, "10-Year Savings": GREEN},
    )
    fig4.update_layout(yaxis_tickformat="$,.0f")
    dark_layout(fig4, title="Projected Savings by Investment Horizon", height=380)
    st.plotly_chart(fig4, use_container_width=True)

with col_d:
    roi_df = top10.dropna(subset=["roi_5yr", "roi_10yr"])
    fig5 = px.scatter(
        roi_df, x="roi_5yr", y="roi_10yr",
        size="savings_10yr", hover_name="condition",
        color="savings_10yr",
        color_continuous_scale=[[0, BLUE], [1, GREEN]],
        labels={"roi_5yr": "5-Year ROI (×)", "roi_10yr": "10-Year ROI (×)"},
    )
    # Reference line: ROI = 1 (break even)
    fig5.add_hline(y=1, line_dash="dash", line_color="#7d8590",
                   annotation_text="Break-even", annotation_position="right")
    fig5.add_vline(x=1, line_dash="dash", line_color="#7d8590")
    dark_layout(fig5, title="ROI: 5-Year vs 10-Year (bubble = 10yr savings)", height=380)
    st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ── Chart 4: Savings per avoided admission vs cost of managed care
st.markdown("### Cost per Avoided Admission vs. Managed Care Alternative")

fig6 = go.Figure()
fig6.add_trace(go.Bar(
    x=top10["condition"], y=top10["avg_cost_per_admission"],
    name="Hospital Admission Cost", marker_color=RED,
))
fig6.add_trace(go.Bar(
    x=top10["condition"], y=top10["managed_care_cost_alternative"],
    name="Managed Care Alternative", marker_color=GREEN,
))
fig6.update_layout(barmode="group", yaxis_tickformat="$,.0f")
dark_layout(fig6, title="Hospital Admission Cost vs. Managed Care Alternative (per case)", height=380)
st.plotly_chart(fig6, use_container_width=True)

st.divider()

# ── Raw table
with st.expander("📋 Full cost analysis table"):
    display_cols = [
        "condition", "admissions_2024", "avg_cost_per_admission", "total_cost_2024",
        "avoidable_admissions_2024", "avoidable_cost_2024", "avoidable_pct_2024",
        "avoidable_cost_2034", "avoidable_cost_growth_pct",
        "potential_savings_per_admission", "savings_5yr", "roi_5yr",
        "savings_10yr", "roi_10yr",
    ]
    st.dataframe(
        top10[[c for c in display_cols if c in top10.columns]],
        hide_index=True, use_container_width=True
    )
