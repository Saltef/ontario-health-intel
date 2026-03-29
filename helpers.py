"""utils/helpers.py — shared formatting and Plotly theme."""

import plotly.graph_objects as go

# ── Colour palette (GitHub dark)
DARK_BG    = "#0d1117"
CARD_BG    = "#161b22"
BORDER     = "#21262d"
TEXT       = "#e6edf3"
MUTED      = "#7d8590"
GREEN      = "#3fb950"
YELLOW     = "#d29922"
RED        = "#f85149"
BLUE       = "#58a6ff"
PURPLE     = "#bc8cff"

STATUS_COLORS = {
    "Adequate":       GREEN,
    "Under Pressure": YELLOW,
    "Critical Gap":   RED,
    "Unknown":        MUTED,
}

SCENARIO_COLORS = {
    "Historical": BLUE,
    "Low":        GREEN,
    "Reference":  YELLOW,
    "High":       RED,
}

CONDITION_PALETTE = [
    "#58a6ff", "#3fb950", "#d29922", "#f85149",
    "#bc8cff", "#79c0ff", "#56d364", "#e3b341",
    "#ffa198", "#d2a8ff",
]


def dark_layout(fig: go.Figure, title: str = "", height: int = 420) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=TEXT)),
        paper_bgcolor=DARK_BG,
        plot_bgcolor=CARD_BG,
        font=dict(family="IBM Plex Sans, sans-serif", color=TEXT, size=12),
        margin=dict(l=24, r=24, t=44, b=24),
        height=height,
        legend=dict(bgcolor=CARD_BG, bordercolor=BORDER, borderwidth=1),
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER),
    )
    return fig


def fmt_currency(v: float) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "N/A"
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    return f"${v:,.0f}"


def fmt_number(v: float) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "N/A"
    if v >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{int(v):,}"
