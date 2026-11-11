"""Formulas from DOM 304 Module 2 (Data Pre-Processing), standard library only.

Each function mirrors a slide so the calculation can be checked by hand or in Excel:
    IQR limits             Slide 23   Q1 - 1.5 x IQR, Q3 + 1.5 x IQR
    Standard deviation     Slide 23   Mean +/- 3 x SD
    Min-max normalisation  Slide 28   (X - Min) / (Max - Min)
    Z-score                Slide 28   (X - Mean) / SD, with Excel's STDEV (sample SD)
    Label / one-hot        Slide 30
    Equal-width binning    Slide 34   upper edge inclusive, as in the slide's IF formula
    Equal-frequency        Slide 35   sort, then assign equal record counts
"""

from __future__ import annotations

import bisect
import math
import re
import statistics as st
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

SEASONS_NORTHERN = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
}
OPPOSITE_SEASON = {
    "Winter": "Summer", "Summer": "Winter", "Spring": "Autumn", "Autumn": "Spring",
}
IQR_MULTIPLIER = 1.5
SD_MULTIPLIER = 3.0
MONTHS_PER_QUARTER = 3
MISSING_PLACEHOLDERS = frozenset({"", "-", "?", "na", "n/a", "nan", "null", "none", "unknown"})


@dataclass(frozen=True)
class Limits:
    """Lower and upper bounds outside which a value is a potential outlier."""

    lower: float
    upper: float

    def is_outside(self, value: float) -> bool:
        return value < self.lower or value > self.upper


def is_missing(value: str) -> bool:
    """Blank, NULL or '-' count as missing (slide 13), as do other common placeholders."""
    return value.strip().casefold() in MISSING_PLACEHOLDERS


def percentile(values: Sequence[float], p: float) -> float:
    """Linear interpolation at (n-1)p, matching Excel PERCENTILE.INC and Phase 4."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * p / 100
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def iqr_limits(values: Sequence[float], multiplier: float = IQR_MULTIPLIER) -> Limits:
    q1, q3 = percentile(values, 25), percentile(values, 75)
    iqr = q3 - q1
    return Limits(q1 - multiplier * iqr, q3 + multiplier * iqr)


def sd_limits(values: Sequence[float], multiplier: float = SD_MULTIPLIER) -> Limits:
    mean, sd = st.mean(values), st.stdev(values)
    return Limits(mean - multiplier * sd, mean + multiplier * sd)


def min_max(values: Sequence[float]) -> list[float]:
    low, high = min(values), max(values)
    if high == low:
        raise ValueError("Cannot min-max scale a constant column.")
    return [(x - low) / (high - low) for x in values]


def z_scores(values: Sequence[float]) -> list[float]:
    mean, sd = st.mean(values), st.stdev(values)
    if sd == 0:
        raise ValueError("Cannot standardise a constant column.")
    return [(x - mean) / sd for x in values]


def equal_width_edges(values: Sequence[float], bins: int) -> list[float]:
    low, high = min(values), max(values)
    width = (high - low) / bins
    return [low + width * i for i in range(bins)] + [high]


def assign_equal_width(values: Sequence[float], edges: Sequence[float]) -> list[int]:
    """Return 1-based bin numbers; a value on an inner edge joins the lower bin."""
    inner_edges = list(edges[1:-1])
    return [bisect.bisect_left(inner_edges, v) + 1 for v in values]


def assign_equal_frequency(values: Sequence[float], bins: int) -> list[int]:
    """Return 1-based bin numbers holding equal record counts (ties broken by position)."""
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    assigned = [0] * len(values)
    for rank, index in enumerate(order):
        assigned[index] = rank * bins // len(values) + 1
    return assigned


def column_safe(label: str) -> str:
    """Turn a category label into a column-name fragment: 'Family Visit' -> 'Family_Visit'."""
    return re.sub(r"[^0-9A-Za-z]+", "_", label).strip("_")


def one_hot(values: Sequence[str], levels: Sequence[str], prefix: str) -> dict[str, list[int]]:
    unknown = set(values) - set(levels)
    if unknown:
        raise ValueError(f"Levels not in the {prefix} encoding: {sorted(unknown)}")
    return {
        f"{prefix}_{column_safe(level)}": [int(v == level) for v in values]
        for level in levels
    }


def label_encode(values: Sequence[str], mapping: Mapping[str, int]) -> list[int | None]:
    """Map ordered labels to integer codes; labels outside the order stay blank."""
    return [mapping.get(v) for v in values]


def quarter_for(month: int) -> str:
    return f"Q{(month - 1) // MONTHS_PER_QUARTER + 1}"


def season_for(month: int, hemisphere: str) -> str:
    northern = SEASONS_NORTHERN[month]
    return northern if hemisphere == "Northern" else OPPOSITE_SEASON[northern]


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    """Pearson correlation, the same calculation as Excel CORREL."""
    return st.correlation(x, y)
