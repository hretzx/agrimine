"""
utils/charts.py
---------------
Plotly figures shared by Home and the For teachers pages. Every figure is built from the cached models in
utils/models.py and the helpers in utils/advice.py: nothing is typed in. Each function returns a figure;
show it with show_chart(style_fig(fig, height=...)).
"""
import pandas as pd
import plotly.graph_objects as go

from core.algorithms.hierarchical import dendrogram_layout
from core.advice import cluster_summary
from core.models import crop_linkage, crop_rules, get_data, id3_root_gains, train_kmeans, train_naive_bayes
from utils.i18n import crop_name
from core.preprocessing import TARGET
from core.features import AXIS
from utils.style import (ALGO, CROP_GROUPS, HEADING_STACK, INK, INK_2, INK_3, PALETTE, SURFACE, SURFACE_2,
                         crop_group, rgba)

PRETTY = AXIS


def label_positions(points: pd.DataFrame, x_range, y_range, width: float = 900, height: float = 400) -> dict:
    """
    Pick a text position for every bubble label so labels overlap each other and the
    bubbles as little as possible. Works in approximate screen pixels: each label is a
    box (about 6.8 px per character, 14 px high) tried above, below, beside and diagonally
    off its bubble; the spot with the least overlap wins.
    """
    def to_px(x, y):
        return ((x - x_range[0]) / (x_range[1] - x_range[0]) * width,
                (y - y_range[0]) / (y_range[1] - y_range[0]) * height)

    def overlap(a, b):   # boxes as (left, bottom, right, top)
        return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))

    def gap(box, cx, cy):   # distance from a point to a box (0 when inside)
        return (max(box[0] - cx, 0, cx - box[2]) ** 2 + max(box[1] - cy, 0, cy - box[3]) ** 2) ** 0.5

    centers = {key: to_px(r["temperature"], r["rainfall"]) for key, r in points.iterrows()}
    bubbles = {}
    for key, r in points.iterrows():
        px_, py_ = to_px(r["temperature"], r["rainfall"])
        rad = r["Diameter"] / 2 + 10      # keep a margin, so a label never sits beside another crop's bubble
        bubbles[key] = (px_ - rad, py_ - rad, px_ + rad, py_ + rad)

    placed, chosen = [], {}
    for key, r in points.sort_values("rainfall", ascending=False).iterrows():
        px_, py_ = to_px(r["temperature"], r["rainfall"])
        rad, w, h = r["Diameter"] / 2, 6.8 * len(r["Crop"]) + 6, 14
        options = {
            "top center": (px_ - w / 2, py_ + rad + 2, px_ + w / 2, py_ + rad + 2 + h),
            "bottom center": (px_ - w / 2, py_ - rad - 2 - h, px_ + w / 2, py_ - rad - 2),
            "middle right": (px_ + rad + 3, py_ - h / 2, px_ + rad + 3 + w, py_ + h / 2),
            "middle left": (px_ - rad - 3 - w, py_ - h / 2, px_ - rad - 3, py_ + h / 2),
            "top left": (px_ - rad * 0.7 - w, py_ + rad * 0.7, px_ - rad * 0.7, py_ + rad * 0.7 + h),
            "top right": (px_ + rad * 0.7, py_ + rad * 0.7, px_ + rad * 0.7 + w, py_ + rad * 0.7 + h),
            "bottom left": (px_ - rad * 0.7 - w, py_ - rad * 0.7 - h, px_ - rad * 0.7, py_ - rad * 0.7),
            "bottom right": (px_ + rad * 0.7, py_ - rad * 0.7 - h, px_ + rad * 0.7 + w, py_ - rad * 0.7),
        }
        best, best_cost = "top center", None
        for name, box in options.items():
            cost = sum(overlap(box, p) for p in placed)
            cost += 3 * sum(overlap(box, b) for k, b in bubbles.items() if k != key)
            cost += 2000 * (box[0] < 0 or box[2] > width or box[1] < 0 or box[3] > height)   # stay inside
            # never let a label sit closer to another crop's bubble than to its own
            own = gap(box, px_, py_)
            cost += 1500 * any(gap(box, *c) < own + 12 for k, c in centers.items() if k != key)
            if best_cost is None or cost < best_cost:
                best, best_cost = name, cost
        chosen[key] = best
        placed.append(options[best])
    return chosen


def accuracy_donut(name: str, accuracy: float) -> go.Figure:
    """Donut of the best model's held-out accuracy with the number in the middle."""
    color = ALGO["naive_bayes"] if name == "Naive Bayes" else ALGO["id3"]
    fig = go.Figure(go.Pie(values=[accuracy, 1 - accuracy], labels=["Correct", "Wrong"], hole=0.72, sort=False,
                           marker=dict(colors=[color, SURFACE_2], line=dict(color=SURFACE, width=2)),
                           textinfo="none", hovertemplate="%{label}: %{percent}<extra></extra>"))
    fig.update_layout(showlegend=False, annotations=[dict(
        text=f"<b>{accuracy:.1%}</b><br><span style='font-size:12px;color:{INK_2}'>{name}</span>",
        showarrow=False, font=dict(size=26, family=HEADING_STACK, color=INK))])
    return fig


def info_gain_chart() -> go.Figure:
    """Horizontal bars of the ID3 information gain per feature; the root split is the brightest."""
    gains = id3_root_gains()
    colors = [ALGO["id3"] if i == len(gains) - 1 else rgba(ALGO["id3"], 0.45) for i in range(len(gains))]
    fig = go.Figure(go.Bar(x=gains["Gain"], y=[PRETTY[f] for f in gains["Feature"]], orientation="h",
                           marker_color=colors, hovertemplate="%{y}: %{x:.3f} bits<extra></extra>"))
    fig.update_layout(xaxis_title="Information gain (bits)", yaxis_title=None, bargap=0.3)
    return fig


def posterior_chart(row: dict, top: int = 6) -> go.Figure:
    """Naive Bayes posterior probability of the most likely crops for one record."""
    post = train_naive_bayes()["model"].posterior(row).head(top).iloc[::-1]
    colors = [ALGO["naive_bayes"] if i == len(post) - 1 else rgba(ALGO["naive_bayes"], 0.45) for i in range(len(post))]
    fig = go.Figure(go.Bar(x=post.values, y=[crop_name(c) for c in post.index], orientation="h",
                           marker_color=colors, hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Posterior probability", tickformat=".0%", range=[0, 1.05]), yaxis_title=None)
    return fig


def dendrogram_chart(k: int = 4) -> go.Figure:
    """Horizontal dendrogram of the 22 crops (Ward linkage), merges coloured by cluster."""
    info = crop_linkage("ward")
    layout = dendrogram_layout(info["Z"], k)
    fig = go.Figure()
    for seg in layout["segments"]:
        color = PALETTE[seg["cluster"] % len(PALETTE)] if seg["cluster"] is not None else INK_3
        fig.add_trace(go.Scatter(x=seg["y"], y=seg["x"], mode="lines", line=dict(color=color, width=1.8),
                                 hoverinfo="skip", showlegend=False))
    fig.update_layout(
        xaxis=dict(title="Merge height (Ward)", autorange="reversed", showgrid=False),
        yaxis=dict(tickmode="array", tickvals=layout["leaf_x"], showgrid=False, side="right",
                   ticktext=[crop_name(info["crops"][i]) for i in layout["order"]],
                   tickfont=dict(size=9, color=INK_2)))
    return fig


def rules_bubbles() -> go.Figure:
    """Apriori rules: support (x) against confidence (y); bubble size and colour = lift."""
    rules = crop_rules()
    fig = go.Figure(go.Scatter(
        x=rules["Support"], y=rules["Confidence"], mode="markers",
        marker=dict(size=rules["Lift"], sizemode="area", sizeref=2 * rules["Lift"].max() / (12 ** 2), sizemin=3,
                    color=rules["Lift"], colorscale=[[0, rgba(ALGO["apriori"], 0.35)], [1, ALGO["apriori"]]],
                    line=dict(width=0.5, color=SURFACE), opacity=0.55),
        customdata=rules[["Antecedent", "Consequent", "Lift"]],
        hovertemplate="%{customdata[0]} → %{customdata[1]}<br>support %{x:.1%} · confidence %{y:.0%} · "
                      "lift %{customdata[2]:.1f}<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Support", tickformat=".0%"), yaxis=dict(title="Confidence", tickformat=".0%", range=[0.58, 1.03]))
    return fig


def benchmark_chart(bench: pd.DataFrame) -> go.Figure:
    """Measured run time of the three miners (milliseconds)."""
    colors = {"Apriori": ALGO["apriori"], "FP-Growth": ALGO["fpgrowth"], "Eclat": "#E879F9"}
    fig = go.Figure(go.Bar(x=bench["Algorithm"], y=bench["Seconds"] * 1000,
                           marker_color=[colors[a] for a in bench["Algorithm"]],
                           text=[f"{s * 1000:.0f} ms" for s in bench["Seconds"]], textposition="outside",
                           textfont=dict(color=INK_2, size=12), cliponaxis=False,
                           hovertemplate="%{x}: %{y:.1f} ms<extra></extra>"))
    fig.update_layout(yaxis=dict(title="Run time (ms)", rangemode="tozero"), xaxis_title=None, bargap=0.4)
    return fig


# Colours of the farm groups on Home (green, blue, yellow first, like the reference design).
CLUSTER_COLORS = ["#2E9E6A", "#3D86C6", "#E3A92B", "#8467D0", "#E0649A", "#E8793A", "#1F9C8F", "#6A78D6"]
X_COLOR = "#D64533"


def farm_cluster_chart(k: int, current: dict | None) -> go.Figure:
    """
    Every record as a dot at its rainfall (x) and temperature (y), coloured by its K-Means group.
    The groups are found from all seven measurements, so they overlap a little on two axes.
    Your own field is the red X, placed at its real rainfall and temperature.
    """
    df, _ = get_data()
    labels = train_kmeans(k).labels_
    fig = go.Figure()
    for c in range(k):
        part = df[labels == c]
        fig.add_trace(go.Scatter(
            x=part["rainfall"], y=part["temperature"], mode="markers", name=f"Cluster {c + 1}", showlegend=False,
            marker=dict(size=5, color=CLUSTER_COLORS[c % len(CLUSTER_COLORS)], opacity=0.7, line=dict(width=0)),
            hovertemplate=f"Cluster {c + 1}<br>%{{x:.0f}} mm · %{{y:.1f}} °C<extra></extra>"))
    if current is not None:
        fig.add_trace(go.Scatter(
            x=[current["rainfall"]], y=[current["temperature"]], mode="markers", name="Your field", showlegend=False,
            marker=dict(symbol="x", size=13, color=X_COLOR, line=dict(width=3, color=X_COLOR)),
            hovertemplate="Your field<br>%{x:.0f} mm · %{y:.1f} °C<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Rainfall (mm)", title_standoff=2), yaxis=dict(title="Temperature (°C)", title_standoff=2))
    return fig


def cluster_legend(k: int, current: dict | None, your_field: str, most_often: str) -> str:
    """HTML legend for farm_cluster_chart: colour dot, 'Cluster n' and the crop most records in it grow."""
    summary = cluster_summary(k)
    rows = []
    for _, r in summary.iterrows():
        color = CLUSTER_COLORS[int(r["Cluster"]) % len(CLUSTER_COLORS)]
        rows.append(f'<div class="legend-row"><i style="background:{color}"></i><div><b>Cluster {int(r["Cluster"]) + 1} · {int(r["Records"]):,}</b>'
                    f'<span>{most_often} {crop_name(r["Top crop"])} ({r["Share"]:.0%})</span></div></div>')
    if current is not None:
        rows.append(f'<div class="legend-row"><i style="background:{X_COLOR};border-radius:2px"></i><div><b>{your_field}</b></div></div>')
    return "".join(rows)


def climate_bubbles(compact: bool = True, current: dict | None = None) -> go.Figure:
    """
    Average temperature (x) and rainfall (y) of every crop. Colour = crop family, bubble size = average humidity.
    compact=True shrinks the bubbles and labels for a small Home card.
    """
    df, _ = get_data()
    climate = df.groupby(TARGET)[["temperature", "rainfall", "humidity"]].mean()
    climate["Crop"] = [crop_name(c) for c in climate.index]
    climate["Group"] = [crop_group(c) for c in climate.index]
    x_range = [climate["temperature"].min() - 1.4, climate["temperature"].max() + 1.4]
    y_range = [0, climate["rainfall"].max() * (1.2 if compact else 1.12)]
    size_max = 12 if compact else 22
    climate["Diameter"] = size_max * (climate["humidity"] / climate["humidity"].max()) ** 0.5
    positions = label_positions(climate, x_range, y_range, width=430 if compact else 900, height=215 if compact else 400)
    fig = go.Figure()
    for color, group in zip(PALETTE, CROP_GROUPS):
        part = climate[climate["Group"] == group]
        fig.add_trace(go.Scatter(
            x=part["temperature"], y=part["rainfall"], mode="markers+text", name=group,
            text=part["Crop"], textposition=[positions[c] for c in part.index],
            textfont=dict(size=9 if compact else 11, color=INK_2), customdata=part[["humidity"]],
            marker=dict(size=part["Diameter"], color=color, opacity=0.85, line=dict(width=1, color=SURFACE)),
            hovertemplate="<b>%{text}</b><br>%{x:.1f} °C · %{y:.0f} mm<br>Humidity %{customdata[0]:.0f}%<extra></extra>"))
    if current is not None:
        fig.add_trace(go.Scatter(x=[current["temperature"]], y=[current["rainfall"]], mode="markers", name="Your field",
                                 marker=dict(symbol="x", size=11, color=X_COLOR, line=dict(width=3, color=X_COLOR)),
                                 hovertemplate="Your field<br>%{x:.1f} °C · %{y:.0f} mm<extra></extra>"))
    fig.update_layout(xaxis=dict(title="Temperature (°C)", range=x_range, title_standoff=2),
                      yaxis=dict(title="Rainfall (mm)", range=y_range, title_standoff=2),
                      showlegend=not compact)
    return fig


def climate_chips(your_field: str | None) -> str:
    """Small HTML legend under the compact climate chart: one dot per crop family (and your field)."""
    chips = [f'<span><i style="background:{c}"></i>{g}</span>' for c, g in zip(PALETTE, CROP_GROUPS)]
    if your_field:
        chips.append(f'<span><i style="background:{X_COLOR};border-radius:2px"></i>{your_field}</span>')
    return f'<div class="chips">{"".join(chips)}</div>'


def tiny(fig: go.Figure, size: int = 9) -> go.Figure:
    """Shrink fonts and margins so a chart fits a small Home card."""
    fig.update_layout(font=dict(size=size), margin=dict(l=2, r=6, t=2, b=2))
    fig.update_xaxes(title_font=dict(size=size), tickfont=dict(size=size), title_standoff=1)
    fig.update_yaxes(title_font=dict(size=size), tickfont=dict(size=size), title_standoff=1)
    return fig
