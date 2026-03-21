"""Visualization functions — radar chart, property distributions, comparisons."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


SCORE_COLS = [
    "activity_score",
    "stability_score",
    "synthesizability_score",
]
SCORE_LABELS = {
    "activity_score": "Activity",
    "hemolytic_score": "Safety (hemolytic)",
    "phytotoxicity_score": "Safety (phyto)",
    "stability_score": "Stability",
    "synthesizability_score": "Synthesizability",
}
RADAR_COLS = list(SCORE_LABELS.keys())

# ── Design system palette ───────────────────────────────────────────────────
PRIMARY = "#012d1d"
TRACE_COLORS = ["#012d1d", "#1b4332", "#2d6a4f", "#40916c", "#52b788"]
TRACE_FILLS = [
    "rgba(1, 45, 29, 0.15)",
    "rgba(27, 67, 50, 0.12)",
    "rgba(45, 106, 79, 0.10)",
    "rgba(64, 145, 108, 0.08)",
    "rgba(82, 183, 136, 0.06)",
]
FONT = "Inter, sans-serif"
HEADING = "Manrope, sans-serif"


def radar_chart(df: pd.DataFrame, top_n: int = 5) -> go.Figure:
    top = df.head(top_n)
    fig = go.Figure()

    for idx, (_, row) in enumerate(top.iterrows()):
        values = []
        for col in RADAR_COLS:
            v = row[col]
            if col in ("hemolytic_score", "phytotoxicity_score"):
                v = 1 - v
            values.append(v)
        values.append(values[0])

        labels = [SCORE_LABELS[c] for c in RADAR_COLS] + [SCORE_LABELS[RADAR_COLS[0]]]
        ci = min(idx, len(TRACE_COLORS) - 1)
        fig.add_trace(go.Scatterpolar(
            r=values, theta=labels, fill="toself",
            fillcolor=TRACE_FILLS[ci], name=row["id"], opacity=0.9,
            line=dict(color=TRACE_COLORS[ci], width=2),
            marker=dict(size=4, color=TRACE_COLORS[ci]),
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1],
                            tickfont=dict(size=9, color="#94a3b8")),
            angularaxis=dict(tickfont=dict(size=10, family=FONT, color="#64748b")),
            bgcolor="rgba(0,0,0,0)",
        ),
        title=dict(text="Multivariate Candidate Scoring",
                   font=dict(family=HEADING, size=18, color=PRIMARY)),
        template="plotly_white", height=500, font=dict(family=FONT),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(size=11, color="#64748b"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=60, b=40),
    )
    return fig


def property_distributions(df: pd.DataFrame) -> go.Figure:
    props = ["length", "charge"]
    available = [p for p in props if p in df.columns]
    if not available:
        return go.Figure()

    fig = px.histogram(
        df.melt(value_vars=available, var_name="Property", value_name="Value"),
        x="Value", color="Property", facet_col="Property", nbins=20,
        template="plotly_white", title="Property Distributions",
        color_discrete_sequence=["#012d1d", "#40916c"],
    )
    fig.update_layout(
        showlegend=False, height=350, font=dict(family=FONT),
        title=dict(font=dict(family=HEADING, size=16, color=PRIMARY)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, b=40),
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return fig


def score_bar_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    top = df.head(top_n).copy()
    top = top.sort_values("combined_score", ascending=True)

    fig = go.Figure(go.Bar(
        x=top["combined_score"], y=top["id"], orientation="h",
        marker_color=_color_scale(top["combined_score"]),
        text=top["combined_score"].round(3), textposition="outside",
        textfont=dict(size=10, color="#64748b", family=FONT),
    ))
    fig.update_layout(
        title=dict(text=f"Top {top_n} Combined Scores",
                   font=dict(family=HEADING, size=16, color=PRIMARY)),
        xaxis_title="Combined Score", yaxis_title="",
        template="plotly_white", height=max(300, top_n * 35),
        xaxis=dict(range=[0, 1.05], tickfont=dict(size=10, color="#94a3b8")),
        yaxis=dict(tickfont=dict(size=10, color=PRIMARY, family="monospace")),
        font=dict(family=FONT),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, b=40, l=80),
    )
    return fig


def score_heatmap(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    top = df.head(top_n).copy()
    display_cols = RADAR_COLS + ["combined_score"]
    labels = [SCORE_LABELS.get(c, c.replace("_", " ").title()) for c in display_cols]

    z = top[display_cols].values
    fig = go.Figure(go.Heatmap(
        z=z, x=labels, y=top["id"].tolist(),
        colorscale=[[0, "#f2f4f6"], [0.25, "#d1fae5"], [0.5, "#a5d0b9"],
                     [0.75, "#3f6653"], [1, "#012d1d"]],
        zmin=0, zmax=1,
        text=np.round(z, 2), texttemplate="%{text}",
        textfont=dict(size=10, color="white"),
        hovertemplate="Candidate: %{y}<br>Score: %{x}<br>Value: %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Score Matrix (All Dimensions)",
                   font=dict(family=HEADING, size=16, color=PRIMARY)),
        template="plotly_white", height=max(300, top_n * 40),
        yaxis=dict(autorange="reversed",
                   tickfont=dict(size=10, color=PRIMARY, family="monospace")),
        xaxis=dict(tickfont=dict(size=9, color="#64748b")),
        font=dict(family=FONT),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, b=40),
    )
    return fig


def _color_scale(values: pd.Series) -> list[str]:
    colors = []
    for v in values:
        if v >= 0.7:
            colors.append("#012d1d")
        elif v >= 0.5:
            colors.append("#2d6a4f")
        else:
            colors.append("#94a3b8")
    return colors
