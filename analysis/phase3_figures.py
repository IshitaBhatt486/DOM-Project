"""Phase 3 box plots: outlier screening and the effect of scaling."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from phase3_config import OUTLIER_MEASURES  # noqa: E402

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
BOX_COLOUR = "#2a78d6"
BOX_FILL = "#cde2fb"
OUTLIER_COLOUR = "#eb6834"
DPI = 150
GRID_COLUMNS = 3
SCALING_VARIABLES = (
    "Airport_Passenger_Traffic", "Tourist_Spending_USD", "Number_of_Hotels",
    "Hotel_Occupancy_Rate",
)


def _compact(value: float, _position: int = 0) -> str:
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:g}M"
    if magnitude >= 1_000:
        return f"{value / 1_000:g}K"
    return f"{value:g}"


def _label(column: str) -> str:
    return column.replace("_USD_000", " (USD '000)").replace("_", " ")


def _column(rows: Sequence[Mapping[str, Any]], name: str) -> list[float]:
    return [row[name] for row in rows]


def _style_axis(ax: Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=8, length=0)


def _draw_box(ax: Axes, data: Sequence[Sequence[float]], labels: Sequence[str]) -> None:
    ax.boxplot(
        data, orientation="horizontal", tick_labels=labels, widths=0.55, patch_artist=True,
        whis=1.5,
        boxprops={"facecolor": BOX_FILL, "edgecolor": BOX_COLOUR, "linewidth": 1.5},
        medianprops={"color": BOX_COLOUR, "linewidth": 2},
        whiskerprops={"color": BOX_COLOUR, "linewidth": 1.5},
        capprops={"color": BOX_COLOUR, "linewidth": 1.5},
        flierprops={
            "marker": "D", "markersize": 6, "markerfacecolor": OUTLIER_COLOUR,
            "markeredgecolor": SURFACE, "markeredgewidth": 0.8,
        },
    )


def _outlier_legend(figure: plt.Figure, y: float) -> None:
    handle = Line2D(
        [], [], marker="D", linestyle="", markersize=7, markerfacecolor=OUTLIER_COLOUR,
        markeredgecolor=SURFACE, label="Potential outlier (outside Q1 - 1.5 IQR to Q3 + 1.5 IQR)",
    )
    figure.legend(handles=[handle], loc="upper left", bbox_to_anchor=(0.012, y), frameon=False,
                  fontsize=10, labelcolor=TEXT_SECONDARY)


def _new_figure(
    rows: int, columns: int, size: tuple[float, float], title: str
) -> tuple[plt.Figure, Any]:
    figure, axes = plt.subplots(rows, columns, figsize=size, facecolor=SURFACE)
    figure.text(0.02, 0.985, title, fontsize=15, fontweight="bold", color=TEXT_PRIMARY, va="top")
    return figure, axes


def _single_box_panel(ax: Axes, values: Sequence[float], title: str) -> None:
    _style_axis(ax)
    _draw_box(ax, [values], [""])
    ax.set_title(title, fontsize=10, color=TEXT_PRIMARY, loc="left")
    ax.set_yticks([])
    ax.xaxis.set_major_formatter(FuncFormatter(_compact))


def draw_outlier_screen(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    count = len(OUTLIER_MEASURES)
    grid_rows = (count + GRID_COLUMNS - 1) // GRID_COLUMNS
    figure, axes = _new_figure(
        grid_rows, GRID_COLUMNS, (13, 1.65 * grid_rows + 1.2),
        "Only eco-revenue and carbon footprint show potential outliers",
    )
    panels = list(axes.flat)
    for ax, column in zip(panels, OUTLIER_MEASURES):
        _single_box_panel(ax, _column(rows, column), _label(column))
    for ax in panels[count:]:
        ax.axis("off")
    _outlier_legend(figure, 0.962)
    figure.tight_layout(rect=(0, 0, 1, 0.925))
    figure.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(figure)


def draw_outliers_per_unit(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    figure, axes = _new_figure(
        2, 2, (12, 5.4), "The flagged totals disappear once expressed per unit",
    )
    panels = (
        ("Eco_Tourism_Revenue_USD_000", "Eco-tourism revenue, total (USD '000)"),
        ("Eco_Revenue_Share_Pct", "Eco-tourism share of tourism revenue (%)"),
        ("Carbon_Footprint_kg", "Carbon footprint, total (kg)"),
        ("Carbon_kg_per_Tourist", "Carbon footprint per tourist (kg)"),
    )
    for ax, (column, title) in zip(axes.flat, panels):
        _single_box_panel(ax, _column(rows, column), title)
    _outlier_legend(figure, 0.925)
    figure.tight_layout(rect=(0, 0, 1, 0.86))
    figure.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(figure)


def draw_scaling_effect(
    rows: Sequence[Mapping[str, Any]], scaled: Sequence[Mapping[str, Any]], path: Path
) -> None:
    figure, axes = _new_figure(
        1, 2, (13, 4.4), "Min-max scaling puts predictors with very different units side by side",
    )
    labels = [_label(c) for c in SCALING_VARIABLES][::-1]
    raw_data = [_column(rows, c) for c in SCALING_VARIABLES][::-1]
    scaled_data = [_column(scaled, f"{c}_MinMax") for c in SCALING_VARIABLES][::-1]
    for ax, data, title in (
        (axes[0], raw_data, "Original units: passenger traffic dominates the axis"),
        (axes[1], scaled_data, "After min-max scaling: every predictor spans 0 to 1"),
    ):
        _style_axis(ax)
        _draw_box(ax, data, labels)
        ax.set_title(title, fontsize=11, color=TEXT_PRIMARY, loc="left")
        ax.xaxis.set_major_formatter(FuncFormatter(_compact))
        ax.tick_params(axis="y", labelcolor=TEXT_PRIMARY, labelsize=9)
    figure.tight_layout(rect=(0, 0, 1, 0.92))
    figure.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(figure)


def draw_all(results: Any, out_dir: Path) -> None:
    draw_outlier_screen(results.cleaned_rows, out_dir / "fig_boxplots_outlier_screen.png")
    draw_outliers_per_unit(results.cleaned_rows, out_dir / "fig_outliers_per_unit.png")
    draw_scaling_effect(
        results.cleaned_rows, results.scaled_both_methods, out_dir / "fig_scaling_effect.png"
    )
