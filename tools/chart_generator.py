"""
Chart Generator — matplotlib-based chart/graph generation tool.
Generates PNG charts from structured data, returns base64 for frontend display.
"""

from __future__ import annotations

import base64
import io
import os
import uuid
from datetime import datetime
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

CHART_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "charts")
os.makedirs(CHART_DIR, exist_ok=True)

# Dark theme matching the system UI
DARK_STYLE = {
    "figure.facecolor": "#0a0a0a",
    "axes.facecolor": "#111111",
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#e0e0e0",
    "text.color": "#e0e0e0",
    "xtick.color": "#aaaaaa",
    "ytick.color": "#aaaaaa",
    "grid.color": "#222222",
    "grid.alpha": 0.5,
    "legend.facecolor": "#1a1a1a",
    "legend.edgecolor": "#333333",
}

COLORS = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
    "#ec4899", "#06b6d4", "#f97316", "#84cc16", "#a78bfa",
]


def _apply_dark_theme():
    plt.rcParams.update(DARK_STYLE)


def generate_chart(
    chart_type: str,
    data: dict[str, Any],
    title: str = "Chart",
    width: int = 800,
    height: int = 450,
) -> dict[str, Any]:
    """Generate a chart and return base64 PNG + metadata."""
    _apply_dark_theme()

    fig_w = width / 100
    fig_h = height / 100
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=100)

    chart_type = chart_type.lower().strip()

    try:
        if chart_type == "bar":
            _draw_bar(ax, data)
        elif chart_type == "line":
            _draw_line(ax, data)
        elif chart_type == "pie":
            _draw_pie(fig, data)
            ax.remove()
        elif chart_type == "scatter":
            _draw_scatter(ax, data)
        elif chart_type == "histogram":
            _draw_histogram(ax, data)
        elif chart_type == "area":
            _draw_area(ax, data)
        elif chart_type == "heatmap":
            _draw_heatmap(fig, ax, data)
        else:
            _draw_bar(ax, data)

        if chart_type != "pie":
            ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
            if data.get("xlabel"):
                ax.set_xlabel(data["xlabel"], fontsize=11)
            if data.get("ylabel"):
                ax.set_ylabel(data["ylabel"], fontsize=11)
            ax.grid(True, alpha=0.3)

        fig.tight_layout()

        # Save to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")

        # Save to file
        chart_id = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        file_path = os.path.join(CHART_DIR, f"{chart_id}.png")
        buf.seek(0)
        with open(file_path, "wb") as f:
            f.write(buf.read())

        plt.close(fig)

        return {
            "chart_id": chart_id,
            "chart_type": chart_type,
            "title": title,
            "image_base64": image_base64,
            "file_path": file_path,
            "width": width,
            "height": height,
        }

    except Exception as e:
        plt.close(fig)
        return {"error": str(e), "chart_type": chart_type, "title": title}


def _draw_bar(ax, data: dict):
    labels = data.get("labels", [])
    datasets = data.get("datasets")
    if datasets and isinstance(datasets, list):
        x = np.arange(len(labels))
        n = len(datasets)
        w = 0.8 / n
        for i, ds in enumerate(datasets):
            vals = ds.get("values", [])
            label = ds.get("label", f"Seri {i+1}")
            ax.bar(x + i * w - (n-1)*w/2, vals, w, label=label, color=COLORS[i % len(COLORS)], alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.legend()
    else:
        values = data.get("values", [])
        colors = [COLORS[i % len(COLORS)] for i in range(len(labels))]
        ax.bar(labels, values, color=colors, alpha=0.85)
        ax.set_xticklabels(labels, rotation=45, ha="right")


def _draw_line(ax, data: dict):
    labels = data.get("labels", [])
    datasets = data.get("datasets")
    if datasets and isinstance(datasets, list):
        for i, ds in enumerate(datasets):
            vals = ds.get("values", [])
            label = ds.get("label", f"Seri {i+1}")
            ax.plot(labels, vals, marker="o", markersize=4, label=label,
                    color=COLORS[i % len(COLORS)], linewidth=2)
        ax.legend()
    else:
        values = data.get("values", [])
        ax.plot(labels, values, marker="o", markersize=4, color=COLORS[0], linewidth=2)
    if len(labels) > 8:
        ax.set_xticklabels(labels, rotation=45, ha="right")


def _draw_pie(fig, data: dict):
    labels = data.get("labels", [])
    values = data.get("values", [])
    title = data.get("title", "")
    colors = [COLORS[i % len(COLORS)] for i in range(len(labels))]
    ax = fig.add_subplot(111)
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=90, textprops={"color": "#e0e0e0", "fontsize": 10},
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_color("#ffffff")
    if title:
        ax.set_title(title, fontsize=14, fontweight="bold", pad=12, color="#e0e0e0")


def _draw_scatter(ax, data: dict):
    x = data.get("x", [])
    y = data.get("y", [])
    sizes = data.get("sizes", [50] * len(x))
    ax.scatter(x, y, s=sizes, color=COLORS[0], alpha=0.7, edgecolors="#ffffff", linewidth=0.5)


def _draw_histogram(ax, data: dict):
    values = data.get("values", [])
    bins = data.get("bins", 20)
    ax.hist(values, bins=bins, color=COLORS[0], alpha=0.75, edgecolor="#333333")


def _draw_area(ax, data: dict):
    labels = data.get("labels", [])
    datasets = data.get("datasets")
    if datasets and isinstance(datasets, list):
        for i, ds in enumerate(datasets):
            vals = ds.get("values", [])
            label = ds.get("label", f"Seri {i+1}")
            ax.fill_between(range(len(vals)), vals, alpha=0.3, color=COLORS[i % len(COLORS)], label=label)
            ax.plot(range(len(vals)), vals, color=COLORS[i % len(COLORS)], linewidth=1.5)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.legend()
    else:
        values = data.get("values", [])
        ax.fill_between(range(len(values)), values, alpha=0.3, color=COLORS[0])
        ax.plot(range(len(values)), values, color=COLORS[0], linewidth=1.5)
        if labels:
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right")


def _draw_heatmap(fig, ax, data: dict):
    matrix = np.array(data.get("matrix", [[]]))
    xlabels = data.get("xlabels", [])
    ylabels = data.get("ylabels", [])
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
    fig.colorbar(im, ax=ax, shrink=0.8)
    if xlabels:
        ax.set_xticks(range(len(xlabels)))
        ax.set_xticklabels(xlabels, rotation=45, ha="right")
    if ylabels:
        ax.set_yticks(range(len(ylabels)))
        ax.set_yticklabels(ylabels)


def list_charts(limit: int = 20) -> list[dict[str, Any]]:
    """List generated chart files."""
    charts = []
    if not os.path.exists(CHART_DIR):
        return charts
    files = sorted(os.listdir(CHART_DIR), reverse=True)
    for f in files[:limit]:
        if f.endswith(".png"):
            path = os.path.join(CHART_DIR, f)
            charts.append({
                "chart_id": f.replace(".png", ""),
                "file_path": path,
                "created_at": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
                "size_bytes": os.path.getsize(path),
            })
    return charts


def get_chart_base64(chart_id: str) -> str | None:
    """Get a chart's base64 by ID."""
    path = os.path.join(CHART_DIR, f"{chart_id}.png")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
