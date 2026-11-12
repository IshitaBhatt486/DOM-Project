"""Phase 5 - Data Visualization.

Builds the eight report charts and the data behind each one from the Phase 3
cleaned dataset. Every chart answers one Phase 1 business question.

Inputs (never modified):
  data/processed/tourism_cleaned.csv   - 500 records, 51 columns (Phase 3)

Outputs, in outputs/phase5/:
  fig1_arrivals_by_country.png ... fig8_occupancy_band_by_rating.png
  chart_data_fig1.csv ... chart_data_fig8.csv  - the exact numbers plotted
  kpi_summary.csv                             - headline KPIs (check values for Tableau)

Uses only the standard library, numpy and matplotlib (no pandas), like the
Phase 2-4 scripts. Run from any directory:
    python analysis/phase5_visualizations.py
"""

from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data/processed/tourism_cleaned.csv"
OUT = ROOT / "outputs/phase5"

# Colours: same reference palette as the Phase 3 figures.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"          # single-series colour (categorical slot 1)
BLUE_LIGHT = "#cde2fb"    # band / quadrant wash
NEUTRAL_FILL = "#e1e0d9"  # low-sample cells
ORDINAL = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # validated 4-step ramp
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DPI = 200
SOURCE = ("Source: Phase 3 cleaned dataset (tourism_cleaned.csv), 500 records, "
          "20 countries, 2020-2024. Data appears synthetic (see Phase 2).")

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
RATING_ORDER = ["1-star", "2-star", "3-star", "4-star", "5-star", "Unrated"]
REGION_ORDER = ["Africa", "Americas", "Asia", "Europe", "Oceania"]
LOW_N = 5  # cells with fewer records are greyed out in the heatmap

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.parse_math": False,
})


# --------------------------------------------------------------------------- data
NUMERIC = {
    "Year", "Month", "Number_of_Tourists", "Tourist_Spending_USD",
    "Hotel_Occupancy_Rate", "Number_of_Hotels", "Tourism_Revenue_USD_000",
    "Spend_per_Night_USD", "Tourists_per_Hotel", "Average_Length_of_Stay",
    "Average_Room_Price_USD",
}


def load() -> list[dict]:
    with CLEAN.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in NUMERIC:
            r[k] = float(r[k])
    assert len(rows) == 500, f"expected 500 records, found {len(rows)}"
    return rows


def group(rows, *keys):
    g = defaultdict(list)
    for r in rows:
        g[tuple(r[k] for k in keys) if len(keys) > 1 else r[keys[0]]].append(r)
    return g


def weighted_spend(rs) -> float:
    """Tourist-weighted spend per tourist = sum(revenue) / sum(arrivals).

    Revenue = arrivals x spend / 1000 (Phase 2 identity), so this equals
    sum(arrivals x spend) / sum(arrivals): what the average tourist spent.
    """
    return sum(r["Tourism_Revenue_USD_000"] for r in rs) * 1000 / sum(
        r["Number_of_Tourists"] for r in rs)


def mean(rs, k):
    return st.mean(r[k] for r in rs)


def median(rs, k):
    return st.median(r[k] for r in rs)


def quantile(values, p):
    return float(np.percentile(values, p, method="linear"))


def write_csv(name, header, rows):
    with (OUT / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow([round(x, 4) if isinstance(x, float) else x for x in row])


# ------------------------------------------------------------------------ helpers
def thousands(x, _pos=0):
    return f"{x / 1000:,.0f}K" if abs(x) >= 1000 else f"{x:,.0f}"


def style_axes(ax, grid_axis="x"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if grid_axis == "x":
        ax.spines["left"].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def titles(fig, title, subtitle, question):
    fig.text(0.012, 0.975, title, fontsize=14, fontweight="bold", color=INK,
             va="top", ha="left")
    fig.text(0.012, 0.925, subtitle, fontsize=10, color=INK_2, va="top", ha="left")
    fig.text(0.988, 0.975, question, fontsize=9, color=MUTED, va="top", ha="right")
    fig.text(0.012, 0.015, SOURCE, fontsize=7.5, color=MUTED, ha="left", va="bottom")


def save(fig, name):
    fig.savefig(OUT / name, dpi=DPI)
    plt.close(fig)


def place_labels(ax, xs, ys, labels, fontsize=8, manual=None):
    """Greedy label placement: try several offsets per point, keep the least-overlapping.

    `manual` maps a label to an (dx, dy) offset in points; those labels get a thin
    leader line, for points that sit almost on top of each other.
    """
    manual = manual or {}
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    taken = []
    pts = [ax.transData.transform((x, y)) for x, y in zip(xs, ys)]
    for i, lab in enumerate(labels):
        if lab in manual:
            dx, dy = manual[lab]
            t = ax.annotate(lab, (xs[i], ys[i]), xytext=(dx, dy), textcoords="offset points",
                            fontsize=fontsize, color=INK_2, va="center",
                            ha="left" if dx > 0 else "right",
                            arrowprops=dict(arrowstyle="-", color=AXIS, lw=0.8,
                                            shrinkA=0, shrinkB=4))
            taken.append(t.get_window_extent(renderer).expanded(1.05, 1.15))
    offsets = [(6, 4), (6, -14), (-6, 4), (-6, -14), (0, 9), (0, -18), (9, -5), (-9, -5),
               (14, 10), (-14, 10), (14, -20), (-14, -20)]
    order = sorted((i for i in range(len(xs)) if labels[i] not in manual),
                   key=lambda i: -ys[i])
    for i in order:
        best, best_score = None, None
        for dx, dy in offsets:
            ha = "left" if dx > 0 else "right" if dx < 0 else "center"
            t = ax.annotate(labels[i], (xs[i], ys[i]), xytext=(dx, dy),
                            textcoords="offset points", fontsize=fontsize,
                            color=INK_2, ha=ha, va="bottom")
            bb = t.get_window_extent(renderer).expanded(1.05, 1.15)
            score = 2 * sum(bb.overlaps(o) for o in taken)
            near = bb.padded(7)
            score += 2 * sum(near.contains(px, py) for j, (px, py) in enumerate(pts) if j != i)
            axbb = ax.get_window_extent(renderer)
            if bb.x0 < axbb.x0 or bb.x1 > axbb.x1 or bb.y0 < axbb.y0 or bb.y1 > axbb.y1:
                score += 5
            if best_score is None or score < best_score:
                if best is not None:
                    best[0].remove()
                best, best_score = (t, bb), score
            else:
                t.remove()
            if best_score == 0:
                break
        taken.append(best[1])


# ------------------------------------------------------------------------- charts
def fig1_arrivals_by_country(rows, overall_mean):
    g = group(rows, "Country")
    data = sorted(((c, len(rs), mean(rs, "Number_of_Tourists"),
                    median(rs, "Number_of_Tourists")) for c, rs in g.items()),
                  key=lambda t: t[2])
    write_csv("chart_data_fig1.csv",
              ["Country", "Records", "Mean_Arrivals", "Median_Arrivals"], data)

    fig, ax = plt.subplots(figsize=(10, 7.2))
    fig.subplots_adjust(left=0.2, right=0.9, top=0.87, bottom=0.11)
    names = [d[0] for d in data]
    vals = [d[2] for d in data]
    y = np.arange(len(data))
    ax.barh(y, vals, height=0.62, color=BLUE)
    for yi, (c, n, m, _) in zip(y, data):
        ax.text(m + 1500, yi, f"{m / 1000:,.0f}K  (n={n})", va="center",
                fontsize=8, color=INK_2, zorder=4,
                bbox=dict(boxstyle="square,pad=0.15", fc=SURFACE, ec="none"))
    ax.axvline(overall_mean, color=INK_2, linewidth=1, zorder=3)
    ax.text(overall_mean, len(data) - 0.2, f"Overall mean {overall_mean / 1000:,.0f}K",
            ha="center", va="bottom", fontsize=8, color=INK_2)
    ax.set_yticks(y, names)
    ax.set_xlim(0, 165000)
    ax.set_ylim(-0.6, len(data) + 0.3)
    ax.xaxis.set_major_formatter(FuncFormatter(thousands))
    ax.set_xlabel("Mean tourist arrivals per record (persons)")
    style_axes(ax, "x")
    lo, hi = data[0], data[-1]
    titles(fig, "Average tourist arrivals by country",
           f"Most countries average 115K-140K arrivals per record. {hi[0]} is highest "
           f"({hi[2] / 1000:,.0f}K), {lo[0]} lowest ({lo[2] / 1000:,.0f}K, n={lo[1]}).",
           "Business question 1")
    save(fig, "fig1_arrivals_by_country.png")
    return data


def fig2_monthly_pattern(rows, overall_mean):
    g = group(rows, "Month")
    data = []
    for m in range(1, 13):
        rs = g[float(m)]
        vals = [r["Number_of_Tourists"] for r in rs]
        data.append((MONTHS[m - 1], len(rs), st.mean(vals), quantile(vals, 25),
                     quantile(vals, 75)))
    write_csv("chart_data_fig2.csv",
              ["Month", "Records", "Mean_Arrivals", "Q1_Arrivals", "Q3_Arrivals"], data)

    fig, ax = plt.subplots(figsize=(10, 5.8))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.82, bottom=0.17)
    x = np.arange(12)
    ax.fill_between(x, [d[3] for d in data], [d[4] for d in data], color=BLUE_LIGHT,
                    linewidth=0, label="Middle 50% of records (Q1-Q3)")
    ax.axhline(overall_mean, color=MUTED, linewidth=1)
    ax.text(11.35, overall_mean, "Overall\nmean", fontsize=8, color=INK_2, va="center")
    means = [d[2] for d in data]
    ax.plot(x, means, color=BLUE, linewidth=2, marker="o", markersize=6,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label="Mean arrivals")
    hi, lo = int(np.argmax(means)), int(np.argmin(means))
    for i, txt in ((hi, "Highest"), (lo, "Lowest")):
        ax.annotate(f"{txt}: {means[i] / 1000:,.0f}K", (i, means[i]),
                    xytext=(0, 10 if i == hi else -16), textcoords="offset points",
                    ha="center", fontsize=8, color=INK)
    ax.set_xticks(x, [f"{d[0]}\nn={d[1]}" for d in data])
    ax.set_xlim(-0.4, 11.9)
    ax.set_ylim(0, 200000)
    ax.yaxis.set_major_formatter(FuncFormatter(thousands))
    ax.set_ylabel("Tourist arrivals per record (persons)")
    style_axes(ax, "y")
    ax.legend(loc="lower left", frameon=False, fontsize=8, ncol=2)
    spread = (max(means) - min(means)) / overall_mean * 100
    titles(fig, "Tourist arrivals by month",
           f"Monthly means move within a {spread:.0f}% range; records inside each month vary "
           "far more (shaded band). No clear peak season.",
           "Business question 1")
    save(fig, "fig2_monthly_pattern.png")
    return data, spread


def fig3_year_by_region(rows):
    panels = [("All regions", rows)] + [
        (reg, [r for r in rows if r["UN_Region"] == reg]) for reg in REGION_ORDER]
    years = [2020, 2021, 2022, 2023, 2024]
    data = []
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.6), sharey=True)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.8, bottom=0.14, hspace=0.62,
                        wspace=0.08)
    for ax, (name, rs) in zip(axes.flat, panels):
        g = group(rs, "Year")
        ns = [len(g[float(y)]) for y in years]
        ms = [mean(g[float(y)], "Number_of_Tourists") for y in years]
        data += [(name, y, n, m) for y, n, m in zip(years, ns, ms)]
        ax.plot(range(5), ms, color=BLUE, linewidth=2, marker="o", markersize=5,
                markeredgecolor=SURFACE, markeredgewidth=1.2)
        ax.set_title(f"{name}  (n={len(rs)})", fontsize=10, loc="left", color=INK)
        ax.set_xticks(range(5), [f"{y}\n{n}" for y, n in zip(years, ns)], fontsize=7.5)
        ax.set_ylim(0, 180000)
        ax.yaxis.set_major_formatter(FuncFormatter(thousands))
        style_axes(ax, "y")
    for ax in axes[:, 0]:
        ax.set_ylabel("Mean arrivals per record")
    write_csv("chart_data_fig3.csv", ["Panel", "Year", "Records", "Mean_Arrivals"], data)
    titles(fig, "Mean tourist arrivals per record by year, by UN region",
           "Year-to-year movement is small overall. Regional lines move more, but they rest "
           "on few records (count under each year).", "Business question 1")
    fig.text(0.5, 0.05, "Year (number of records below)", ha="center", fontsize=9,
             color=INK_2)
    save(fig, "fig3_year_by_region.png")
    return data


def fig4_value_by_purpose(rows):
    g = group(rows, "Purpose_of_Visit")
    data = sorted(((p, len(rs), weighted_spend(rs), median(rs, "Spend_per_Night_USD"),
                    mean(rs, "Average_Length_of_Stay")) for p, rs in g.items()),
                  key=lambda t: t[2])
    write_csv("chart_data_fig4.csv",
              ["Purpose_of_Visit", "Records", "Tourist_Weighted_Spend_USD",
               "Median_Spend_per_Night_USD", "Mean_Length_of_Stay_Nights"], data)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5.6), sharey=True)
    fig.subplots_adjust(left=0.155, right=0.97, top=0.8, bottom=0.14, wspace=0.12)
    y = np.arange(len(data))
    for ax, idx, label, fmt, xmax in (
            (a1, 2, "Spend per tourist, tourist-weighted (USD)", "${:,.0f}", 3600),
            (a2, 3, "Median spend per night (USD)", "${:,.0f}", 410)):
        vals = [d[idx] for d in data]
        ax.barh(y, vals, height=0.62, color=BLUE)
        for yi, v in zip(y, vals):
            ax.text(v + xmax * 0.01, yi, fmt.format(v), va="center", fontsize=8,
                    color=INK_2)
        ax.set_xlim(0, xmax)
        ax.set_xlabel(label)
        style_axes(ax, "x")
    a1.set_yticks(y, [f"{d[0]} (n={d[1]})" for d in data])
    a1.set_title("Per trip", loc="left", fontsize=10)
    a2.set_title("Per night (adjusts for length of stay)", loc="left", fontsize=10)
    top, bottom = data[-1], data[0]
    gap = (top[2] / bottom[2] - 1) * 100
    titles(fig, "Visitor value by purpose of visit",
           f"{top[0]} travellers spend the most per trip (${top[2]:,.0f}), {gap:.0f}% more "
           f"than {bottom[0]} (${bottom[2]:,.0f}). Per night, Medical and Educational lead.",
           "Business question 2")
    save(fig, "fig4_value_by_purpose.png")
    return data


def fig5_volume_vs_value(rows):
    g = group(rows, "Country")
    data = sorted(((c, len(rs), mean(rs, "Number_of_Tourists"), weighted_spend(rs),
                    mean(rs, "Tourism_Revenue_USD_000")) for c, rs in g.items()),
                  key=lambda t: -t[4])
    write_csv("chart_data_fig5.csv",
              ["Country", "Records", "Mean_Arrivals", "Tourist_Weighted_Spend_USD",
               "Mean_Revenue_per_Record_USD_000"], data)

    xs = [d[2] for d in data]
    ys = [d[3] for d in data]
    mx, my = st.median(xs), st.median(ys)
    fig, ax = plt.subplots(figsize=(10.5, 7))
    fig.subplots_adjust(left=0.1, right=0.97, top=0.84, bottom=0.12)
    xlim, ylim = (100000, 145000), (1600, 3450)
    # iso-revenue curves: mean revenue per record = mean arrivals x weighted spend / 1000
    xx = np.linspace(*xlim, 200)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    for rev in (200000, 300000, 400000):
        yy = rev * 1000 / xx
        ax.plot(xx, yy, color=GRID, linewidth=1.2, zorder=1)
        # label where the curve enters the plot area (top or left edge)
        xi = max(xlim[0] + 800, rev * 1000 / (ylim[1] - 60)) + 600
        yi = rev * 1000 / xi
        p1 = ax.transData.transform((xi, yi))
        p2 = ax.transData.transform((xi + 2000, rev * 1000 / (xi + 2000)))
        angle = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
        ax.text(xi, yi + 18, f"USD {rev / 1000:,.0f}M revenue per record", fontsize=7.5,
                color=MUTED, rotation=angle, rotation_mode="anchor", ha="left",
                va="bottom")
    ax.axvline(mx, color=AXIS, linewidth=1, zorder=1)
    ax.axhline(my, color=AXIS, linewidth=1, zorder=1)
    q = dict(fontsize=8.5, color=MUTED, fontweight="bold")
    ax.text(xlim[1] - 400, ylim[1] - 40, "HIGH VOLUME, HIGH VALUE", ha="right", va="top", **q)
    ax.text(xlim[0] + 400, ylim[1] - 40, "VALUE-LED", ha="left", va="top", **q)
    ax.text(xlim[1] - 400, ylim[0] + 40, "VOLUME-LED", ha="right", va="bottom", **q)
    ax.text(xlim[0] + 400, ylim[0] + 40, "LOW VOLUME, LOW VALUE", ha="left", va="bottom", **q)
    ax.scatter(xs, ys, s=64, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.xaxis.set_major_formatter(FuncFormatter(thousands))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"${v:,.0f}"))
    ax.set_xlabel("Mean tourist arrivals per record (volume)")
    ax.set_ylabel("Spend per tourist, tourist-weighted (value)")
    style_axes(ax, "both")
    ax.spines["left"].set_visible(True)
    place_labels(ax, xs, ys, [d[0] for d in data],
                 manual={"Canada": (-10, 12), "United Kingdom": (10, 14), "India": (12, 0),
                         "Mexico": (-10, 0), "Italy": (-10, -4), "Brazil": (-10, -6),
                         "Japan": (16, 18), "Turkey": (-16, -22), "Germany": (18, -16),
                         "Greece": (12, -14)})
    top = data[0]
    titles(fig, "Where revenue comes from: visitor volume vs visitor value, by country",
           f"Revenue = volume x value. {top[0]} leads on both (USD {top[4] / 1000:,.0f}M "
           "per record). France is low on both. Lines cross at the median country.",
           "Business question 2")
    save(fig, "fig5_volume_vs_value.png")
    return data, mx, my


def fig6_spend_heatmap(rows):
    purposes = sorted({r["Purpose_of_Visit"] for r in rows})
    g = group(rows, "Purpose_of_Visit", "UN_Region")
    mat = np.full((len(purposes), len(REGION_ORDER)), np.nan)
    ns = np.zeros_like(mat)
    data = []
    for i, p in enumerate(purposes):
        for j, reg in enumerate(REGION_ORDER):
            rs = g.get((p, reg), [])
            ns[i, j] = len(rs)
            if rs:
                mat[i, j] = weighted_spend(rs)
            data.append((p, reg, len(rs), mat[i, j] if rs else ""))
    write_csv("chart_data_fig6.csv",
              ["Purpose_of_Visit", "UN_Region", "Records", "Tourist_Weighted_Spend_USD"],
              data)

    fig, ax = plt.subplots(figsize=(10, 6.4))
    fig.subplots_adjust(left=0.14, right=0.88, top=0.8, bottom=0.12)
    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ)
    shown = np.where(ns >= LOW_N, mat, np.nan)
    vmin, vmax = 1500, 4000
    im = ax.imshow(shown, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    for i in range(len(purposes)):
        for j in range(len(REGION_ORDER)):
            low = ns[i, j] < LOW_N
            if low:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, color=NEUTRAL_FILL))
            v = mat[i, j]
            dark_bg = (not low) and (v - vmin) / (vmax - vmin) > 0.55
            colour = "#ffffff" if dark_bg else (MUTED if low else INK)
            ax.text(j, i - 0.1, f"${v:,.0f}", ha="center", va="center", fontsize=9.5,
                    color=colour, fontweight="bold" if not low else "normal")
            ax.text(j, i + 0.22, f"n={int(ns[i, j])}", ha="center", va="center",
                    fontsize=7.5, color=colour)
    for k in range(len(REGION_ORDER) + 1):
        ax.axvline(k - 0.5, color=SURFACE, linewidth=2)
    for k in range(len(purposes) + 1):
        ax.axhline(k - 0.5, color=SURFACE, linewidth=2)
    ax.set_xticks(range(len(REGION_ORDER)), REGION_ORDER)
    ax.set_yticks(range(len(purposes)), purposes)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.xaxis.tick_top()
    cax = fig.add_axes([0.9, 0.2, 0.018, 0.5])
    cb = fig.colorbar(im, cax=cax)
    cb.outline.set_visible(False)
    cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"${v:,.0f}"))
    cb.ax.tick_params(length=0, labelsize=8)
    cb.set_label("Spend per tourist (USD)", fontsize=8, color=INK_2)
    fig.text(0.14, 0.075, f"Grey cells have fewer than {LOW_N} records: shown for "
             "completeness, too few to compare.", fontsize=8, color=INK_2)
    ok = [(mat[i, j], purposes[i], REGION_ORDER[j], int(ns[i, j]))
          for i in range(len(purposes)) for j in range(len(REGION_ORDER))
          if ns[i, j] >= LOW_N]
    best, worst = max(ok), min(ok)
    titles(fig, "Spend per tourist by purpose of visit and region",
           f"Among cells with {LOW_N}+ records, {best[1]} in {best[2]} spends most "
           f"(${best[0]:,.0f}, n={best[3]}); {worst[1]} in {worst[2]} least "
           f"(${worst[0]:,.0f}, n={worst[3]}).", "Business question 2")
    save(fig, "fig6_spend_heatmap.png")
    return data, best, worst


def fig7_capacity_matrix(rows):
    g = group(rows, "Country")
    data = sorted(((c, len(rs), median(rs, "Tourists_per_Hotel"),
                    mean(rs, "Hotel_Occupancy_Rate"), mean(rs, "Number_of_Hotels"))
                   for c, rs in g.items()), key=lambda t: t[0])
    xs = [d[2] for d in data]
    ys = [d[3] for d in data]
    mx, my = st.median(xs), st.median(ys)

    def zone(x, y):
        if x >= mx and y >= my:
            return "High load, high occupancy"
        if x < mx and y < my:
            return "Low load, low occupancy"
        if x >= mx:
            return "High load, low occupancy"
        return "Low load, high occupancy"

    out = [d + (zone(d[2], d[3]),) for d in data]
    write_csv("chart_data_fig7.csv",
              ["Country", "Records", "Median_Tourists_per_Hotel", "Mean_Occupancy_Pct",
               "Mean_Hotels_per_Record", "Capacity_Zone"], out)

    fig, ax = plt.subplots(figsize=(10.5, 7))
    fig.subplots_adjust(left=0.1, right=0.97, top=0.84, bottom=0.12)
    xlim, ylim = (260, 700), (57, 72.5)
    ax.add_patch(plt.Rectangle((mx, my), xlim[1] - mx, ylim[1] - my, color=BLUE_LIGHT,
                               alpha=0.55, linewidth=0, zorder=0))
    ax.add_patch(plt.Rectangle((xlim[0], ylim[0]), mx - xlim[0], my - ylim[0],
                               color=NEUTRAL_FILL, alpha=0.6, linewidth=0, zorder=0))
    ax.axvline(mx, color=AXIS, linewidth=1, zorder=1)
    ax.axhline(my, color=AXIS, linewidth=1, zorder=1)
    q = dict(fontsize=8.5, color=INK_2, fontweight="bold")
    ax.text(xlim[1] - 6, ylim[1] - 0.2, "HIGH LOAD, HIGH OCCUPANCY\nwatch for capacity pressure",
            ha="right", va="top", **q)
    ax.text(xlim[0] + 6, ylim[0] + 0.2, "LOW LOAD, LOW OCCUPANCY\npossible spare capacity",
            ha="left", va="bottom", **q)
    ax.text(xlim[0] + 6, ylim[1] - 0.2, "LOW LOAD, HIGH OCCUPANCY", ha="left", va="top",
            fontsize=8.5, color=MUTED, fontweight="bold")
    ax.text(xlim[1] - 6, ylim[0] + 0.2, "HIGH LOAD, LOW OCCUPANCY", ha="right",
            va="bottom", fontsize=8.5, color=MUTED, fontweight="bold")
    ax.scatter(xs, ys, s=64, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    ax.set_xlabel("Median tourists per hotel (demand load on each hotel)")
    ax.set_ylabel("Mean hotel occupancy rate")
    style_axes(ax, "both")
    ax.spines["left"].set_visible(True)
    place_labels(ax, xs, ys, [d[0] for d in data],
                 manual={"United States": (26, 4), "Thailand": (26, -10),
                         "Egypt": (-22, 8)})
    hh = [d[0] for d in out if d[5] == "High load, high occupancy"]
    ll = [d[0] for d in out if d[5] == "Low load, low occupancy"]
    titles(fig, "Is hotel capacity matched to demand? Load vs occupancy, by country",
           f"{len(hh)} countries sit in the high-load, high-occupancy zone and {len(ll)} in the "
           "low-low zone. Lines are the median country.", "Business question 3")
    save(fig, "fig7_capacity_matrix.png")
    return out, mx, my


def fig8_occupancy_band_by_rating(rows):
    bands = sorted({(int(r["Occupancy_Band_Code"]), r["Occupancy_Band"]) for r in rows})
    g = group(rows, "Hotel_Rating")
    data, shares = [], []
    for rating in RATING_ORDER:
        rs = g[rating]
        row = []
        for code, label in bands:
            k = sum(1 for r in rs if int(r["Occupancy_Band_Code"]) == code)
            row.append(k / len(rs) * 100)
            data.append((rating, len(rs), label, k, k / len(rs) * 100))
        shares.append(row)
    write_csv("chart_data_fig8.csv",
              ["Hotel_Rating", "Records", "Occupancy_Band", "Band_Records", "Share_Pct"], data)

    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    fig.subplots_adjust(left=0.14, right=0.97, top=0.74, bottom=0.12)
    y = np.arange(len(RATING_ORDER))[::-1]
    left = np.zeros(len(RATING_ORDER))
    shares = np.array(shares)
    for b, (code, label) in enumerate(bands):
        w = shares[:, b]
        ax.barh(y, w, left=left, height=0.64, color=ORDINAL[b], edgecolor=SURFACE,
                linewidth=2, label=label)
        for yi, l, v in zip(y, left, w):
            ax.text(l + v / 2, yi, f"{v:.0f}%", ha="center", va="center", fontsize=8.5,
                    color=INK if b == 0 else "#ffffff")
        left += w
    ax.set_yticks(y, [f"{r} (n={len(g[r])})" for r in RATING_ORDER])
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:.0f}%"))
    ax.set_xlabel("Share of records in each occupancy band")
    style_axes(ax, "x")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4, frameon=False,
              fontsize=8, handlelength=1.2)
    vh = {r: shares[i, 3] for i, r in enumerate(RATING_ORDER)}
    top = max(vh, key=vh.get)
    low = min(vh, key=vh.get)
    titles(fig, "Hotel occupancy bands by hotel rating",
           f"Higher star ratings do not fill more reliably: 'Very High' occupancy ranges from "
           f"{vh[low]:.0f}% of {low} records to {vh[top]:.0f}% of {top} records, with no star trend.",
           "Business question 3")
    save(fig, "fig8_occupancy_band_by_rating.png")
    return data, vh


# --------------------------------------------------------------------------- KPIs
def kpis(rows):
    arrivals = [r["Number_of_Tourists"] for r in rows]
    revenue = sum(r["Tourism_Revenue_USD_000"] for r in rows)
    k = [
        ("Records", len(rows), "count", "COUNT([Record_ID])"),
        ("Countries", len({r['Country'] for r in rows}), "count", "COUNTD([Country])"),
        ("Total observed arrivals", sum(arrivals), "persons", "SUM([Number_of_Tourists])"),
        ("Mean arrivals per record", st.mean(arrivals), "persons",
         "AVG([Number_of_Tourists])"),
        ("Spend per tourist (tourist-weighted)", weighted_spend(rows), "USD",
         "SUM([Tourism_Revenue_USD_000])*1000/SUM([Number_of_Tourists])"),
        ("Total observed revenue", revenue / 1000, "USD million",
         "SUM([Tourism_Revenue_USD_000])/1000"),
        ("Mean hotel occupancy", mean(rows, "Hotel_Occupancy_Rate"), "%",
         "AVG([Hotel_Occupancy_Rate])"),
        ("Median tourists per hotel", median(rows, "Tourists_per_Hotel"), "persons",
         "MEDIAN([Tourists_per_Hotel])"),
        ("Mean length of stay", mean(rows, "Average_Length_of_Stay"), "nights",
         "AVG([Average_Length_of_Stay])"),
    ]
    write_csv("kpi_summary.csv", ["KPI", "Value", "Unit", "Tableau_formula"], k)
    return k


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load()
    overall = mean(rows, "Number_of_Tourists")
    results = {
        "kpis": kpis(rows),
        "fig1": fig1_arrivals_by_country(rows, overall),
        "fig2": fig2_monthly_pattern(rows, overall),
        "fig3": fig3_year_by_region(rows),
        "fig4": fig4_value_by_purpose(rows),
        "fig5": fig5_volume_vs_value(rows),
        "fig6": fig6_spend_heatmap(rows),
        "fig7": fig7_capacity_matrix(rows),
        "fig8": fig8_occupancy_band_by_rating(rows),
    }
    print(f"Phase 5: 8 figures, 8 chart-data files and kpi_summary.csv written to {OUT}")
    return results


if __name__ == "__main__":
    main()
