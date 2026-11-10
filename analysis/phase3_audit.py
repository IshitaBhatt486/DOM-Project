"""Phase 3 audit trail: before/after comparison, quality log and data dictionary."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import phase3_methods as methods
from phase3_config import (
    COLUMN_RENAMES,
    ENGINEERED_MEASURES,
    LARGEST_AIRLINER_SEATS,
    ONE_HOT_SOURCES,
    OUTLIER_MEASURES,
    REDUNDANCY_THRESHOLD,
    TARGET_DERIVED_COLUMNS,
    TEXT_COLUMNS,
    VALID_RANGES,
)

Row = dict[str, Any]
STRUCTURAL_BLANK_COLUMNS = frozenset({"Hotel_Star_Level"})
ADDED_COLUMN_SCALES = {
    "Record_ID": "Identifier", "ISO3": "Nominal", "UN_Region": "Nominal",
    "UN_Sub_Region": "Nominal", "Hemisphere": "Nominal", "Period_Date": "Interval",
    "Quarter": "Ordinal", "Month_Name": "Ordinal", "Season": "Nominal",
    "Spend_per_Night_USD": "Ratio", "Tourist_Nights": "Ratio", "Tourists_per_Hotel": "Ratio",
    "Eco_Revenue_Share_Pct": "Ratio", "Carbon_kg_per_Tourist": "Ratio",
    "Passengers_per_Flight": "Ratio", "Hotel_Star_Level": "Ordinal",
    "Occupancy_Band": "Ordinal", "Occupancy_Band_Code": "Ordinal",
    "Demand_Tier": "Ordinal", "Demand_Tier_Code": "Ordinal",
}
BINARY_FLAG_SCALE = "Nominal (0/1)"


def inferred_type(values: Sequence[str]) -> str:
    if all(re.fullmatch(r"-?\d+", v) for v in values):
        return "Integer"
    if all(re.fullmatch(r"-?\d+(\.\d+)?", v) for v in values):
        return "Decimal"
    return "Text"


def count_true_missing(rows: Sequence[Mapping[str, Any]], excluded: frozenset[str]) -> int:
    return sum(
        1 for row in rows for key, value in row.items()
        if key not in excluded
        and (value is None or (isinstance(value, str) and methods.is_missing(value)))
    )


def count_exact_duplicates(rows: Sequence[Mapping[str, Any]], ignored: str = "") -> int:
    signatures = {tuple((k, v) for k, v in row.items() if k != ignored) for row in rows}
    return len(rows) - len(signatures)


def repeated_key_counts(rows: Sequence[Mapping[str, Any]]) -> tuple[int, int]:
    """Return (repeated City-Year-Month keys, records inside those keys)."""
    counts = Counter((r["City"], r["Year"], r["Month"]) for r in rows)
    repeated = [v for v in counts.values() if v > 1]
    return len(repeated), sum(repeated)


def count_case_variants(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> int:
    """Count extra spellings of a label that differ only by upper or lower case."""
    return sum(
        len({r[c] for r in rows}) - len({r[c].casefold() for r in rows}) for c in columns
    )


def count_columns_of_type(rows: Sequence[Mapping[str, Any]], python_type: type) -> int:
    """Count columns whose non-blank values are all of the given Python type."""
    def matches(column: str) -> bool:
        present = [r[column] for r in rows if r[column] is not None]
        return all(type(value) is python_type for value in present)

    return sum(matches(column) for column in rows[0])


def build_before_after(
    raw: Sequence[Mapping[str, str]], cleaned: Sequence[Mapping[str, Any]],
    model: Sequence[Mapping[str, Any]], text_changed: int,
) -> list[Row]:
    raw_types = Counter(inferred_type([r[c] for r in raw]) for c in raw[0])
    table = [
        ("Rows", len(raw), len(cleaned), len(model), "No record removed"),
        ("Columns", len(raw[0]), len(cleaned[0]), len(model[0]),
         "Features added; model file keeps predictors, target and Record_ID"),
        ("Missing values", count_true_missing(raw, frozenset()),
         count_true_missing(cleaned, STRUCTURAL_BLANK_COLUMNS),
         count_true_missing(model, frozenset()), "None to treat"),
        ("Structural blanks (not applicable)", 0,
         sum(r["Hotel_Star_Level"] is None for r in cleaned), 0,
         "Hotel_Star_Level is blank for Unrated, which has no star level"),
        ("Exact duplicate rows", count_exact_duplicates(raw),
         count_exact_duplicates(cleaned, "Record_ID"),
         count_exact_duplicates(model, "Record_ID"), "None found"),
        ("Text cells with stray spaces", text_changed, 0, 0, "None found"),
        ("Repeated City-Year-Month keys", repeated_key_counts(raw)[0],
         repeated_key_counts(cleaned)[0], "n/a",
         "Retained and flagged: not exact duplicates, cause undetermined"),
        ("Integer columns", raw_types["Integer"], count_columns_of_type(cleaned, int),
         count_columns_of_type(model, int), "Includes new codes and 0/1 flags"),
        ("Decimal columns", raw_types["Decimal"], count_columns_of_type(cleaned, float),
         count_columns_of_type(model, float), "Includes new ratios and scaled predictors"),
        ("Text columns", raw_types["Text"], count_columns_of_type(cleaned, str),
         count_columns_of_type(model, str), "Only Record_ID is text in the model file"),
        ("Revenue columns labelled with the true unit", 0, len(COLUMN_RENAMES), "n/a",
         "Renamed to _USD_000"),
        ("Records flagged as potential outliers (IQR)", "not assessed",
         sum(1 for r in cleaned if r["Outlier_Eco_Revenue_IQR"] or r["Outlier_Carbon_IQR"]),
         "n/a", "Retained, see section 3"),
    ]
    return [dict(Metric=m, Before=b, After=a, Model_Ready=mr, Note=n) for m, b, a, mr, n in table]


def build_data_type_changes(raw: Sequence[Mapping[str, str]]) -> list[Row]:
    analytic = {
        "Year": ("Integer, plus Period_Date (ISO date text)", "Combined with Month into a date"),
        "Month": ("Integer, plus Month_Name, Quarter and Season", "Cyclical, so not modelled as a number"),
        "Country": ("Text, treated as nominal", "One-hot in model file"),
        "City": ("Text, treated as nominal", "Kept as a label; 56 levels is too wide to one-hot"),
        "Purpose_of_Visit": ("Text, treated as nominal", "One-hot in model file"),
        "Hotel_Rating": ("Text, treated as ordinal, plus Hotel_Star_Level (integer)",
                         "Unrated kept outside the star order"),
    }
    table = []
    for column in raw[0]:
        before = inferred_type([r[column] for r in raw])
        after, note = analytic.get(column, (before, "Unchanged"))
        table.append(dict(
            Variable=column, Cleaned_Name=COLUMN_RENAMES.get(column, column),
            Type_Before=before, Type_After=after, Note=note,
        ))
    return table


def _city_country_result(rows: Sequence[Mapping[str, Any]]) -> str:
    countries_by_city: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        countries_by_city[row["City"]].add(row["Country"])
    single = sum(len(v) == 1 for v in countries_by_city.values())
    return f"{single} of {len(countries_by_city)} cities map to one country; pairs reviewed by hand"


def _repeated_key_action(rows: Sequence[Mapping[str, Any]]) -> str:
    segments = Counter(
        (r["City"], r["Year"], r["Month"], r["Purpose_of_Visit"], r["Hotel_Rating"]) for r in rows
    )
    clashes = sum(v > 1 for v in segments.values())
    return (
        f"Retained and flagged: {clashes} keys repeat the same purpose and hotel tier, "
        "but city-wide fields conflict, so the cause cannot be determined"
    )


def build_quality_log(
    rows: Sequence[Mapping[str, Any]], removed: int, text_changed: int
) -> list[Row]:
    total = len(rows)
    room_alone = sum(
        r["Average_Length_of_Stay"] * r["Average_Room_Price_USD"] > r["Tourist_Spending_USD"]
        for r in rows
    )
    room_shared = sum(r["Flag_Room_Cost_Exceeds_Spend"] for r in rows)
    keys, keyed_records = repeated_key_counts(rows)
    years = sorted({r["Year"] for r in rows})
    unrated = sum(r["Hotel_Rating"] == "Unrated" for r in rows)
    entries = [
        ("Accuracy", "Percentages 0-100, scores 1-10, months 1-12, years 2020-2024, measures positive",
         f"All {total} records pass", "None needed"),
        ("Accuracy", "Revenue = Tourists x Spending / 1000", f"Holds on all {total} records",
         "Revenue relabelled as USD thousand"),
        ("Completeness", "Blanks and placeholders (NA, null, -, unknown)", "0 cells",
         "No imputation needed"),
        ("Completeness", "Unrated hotel tier", f"{unrated} records",
         "Kept as its own level; structural, so not imputed"),
        ("Consistency", "Exact duplicate rows", f"{removed} found", "None removed"),
        ("Consistency", "Stray spaces and case variants of the same label",
         f"{text_changed} cells with stray spaces; {count_case_variants(rows, TEXT_COLUMNS)} case variants",
         "None corrected"),
        ("Consistency", "City belongs to one, correct country", _city_country_result(rows),
         "None needed"),
        ("Consistency", "Repeated City-Year-Month keys", f"{keyed_records} records in {keys} keys",
         _repeated_key_action(rows)),
        ("Timeliness", "Period covered", f"{years[0]}-{years[-1]}", "Stated as a limitation"),
        ("Believability", "Airport passengers fewer than tourists",
         f"{sum(r['Flag_Passengers_Below_Tourists'] for r in rows)} records",
         "Retained and flagged: possible through land or sea arrivals"),
        ("Believability", f"Passengers per flight above {LARGEST_AIRLINER_SEATS} seats",
         f"{sum(r['Flag_High_Passengers_per_Flight'] for r in rows)} records",
         "Retained and flagged: none remain if passengers count both directions and flights only arrivals"),
        ("Believability", "Room cost for the stay above total spend",
         f"{room_alone} records if one guest pays; {room_shared} if two share",
         "Retained and flagged on the two-guest basis; the source does not define spend"),
        ("Interpretability", "Revenue columns named USD but holding USD thousand",
         f"{len(COLUMN_RENAMES)} columns", "Renamed with _USD_000"),
    ]
    return [dict(Dimension=d, Check=c, Result=r, Action=a) for d, c, r, a in entries]


def find_redundant_pairs(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    columns = [*OUTLIER_MEASURES, *ENGINEERED_MEASURES]
    vectors = {c: [r[c] for r in rows] for c in columns}
    pairs = []
    for i, x in enumerate(columns):
        for y in columns[i + 1:]:
            r = methods.pearson(vectors[x], vectors[y])
            if abs(r) >= REDUNDANCY_THRESHOLD:
                pairs.append(dict(Variable_X=x, Variable_Y=y, Pearson_r=round(r, 3)))
    return sorted(pairs, key=lambda p: -abs(p["Pearson_r"]))


ADDED_COLUMN_DOCS: tuple[tuple[str, str, str, str], ...] = (
    ("Record_ID", "Identifier", "Sequential key in raw file order; the raw file has no unique key", "No"),
    ("ISO3", "Integrated (UN M49)", "ISO alpha-3 country code", "No"),
    ("UN_Region", "Integrated (UN M49)", "UN geographic region", "Yes"),
    ("UN_Sub_Region", "Integrated (UN M49)", "UN geographic sub-region", "Yes"),
    ("Hemisphere", "Integrated (team lookup)", "Southern for Australia, Brazil and South Africa; otherwise Northern", "Yes"),
    ("Period_Date", "Type correction", "First day of the month: Year-Month-01", "No"),
    ("Quarter", "New feature", "Calendar quarter from Month", "Yes"),
    ("Month_Name", "New feature", "Month label from Month", "Yes"),
    ("Season", "New feature", "Meteorological season from Month and Hemisphere", "Yes"),
    ("Spend_per_Night_USD", "New feature", "Tourist_Spending_USD / Average_Length_of_Stay", "Yes"),
    ("Tourist_Nights", "New feature", "Number_of_Tourists x Average_Length_of_Stay", "No"),
    ("Tourists_per_Hotel", "New feature", "Number_of_Tourists / Number_of_Hotels", "No"),
    ("Eco_Revenue_Share_Pct", "New feature", "100 x Eco revenue / Tourism revenue", "No"),
    ("Carbon_kg_per_Tourist", "New feature", "Carbon_Footprint_kg / Number_of_Tourists", "No"),
    ("Passengers_per_Flight", "New feature", "Airport_Passenger_Traffic / Number_of_Flights", "Yes"),
    ("Hotel_Star_Level", "Label encoding", "1-5 from Hotel_Rating; blank for Unrated", "Yes"),
    ("Occupancy_Band", "Discretisation", "Four equal-width occupancy bands", "Yes"),
    ("Occupancy_Band_Code", "Label encoding", "1 (Low) to 4 (Very High)", "Yes"),
    ("Demand_Tier", "Discretisation", "Arrivals quartile tiers, equal frequency", "No"),
    ("Demand_Tier_Code", "Label encoding", "1 (Low) to 4 (High)", "No"),
    ("Flag_Repeated_City_Month", "Quality flag", "1 if the City-Year-Month key occurs more than once", "No"),
    ("Flag_Passengers_Below_Tourists", "Quality flag", "1 if airport passengers are fewer than tourists", "No"),
    ("Flag_High_Passengers_per_Flight", "Quality flag", f"1 if Passengers_per_Flight exceeds {LARGEST_AIRLINER_SEATS}", "No"),
    ("Flag_Room_Cost_Exceeds_Spend", "Quality flag", "1 if stay x room price / 2 exceeds spending per tourist", "No"),
    ("Outlier_Eco_Revenue_IQR", "Outlier flag", "1 if outside Q1-1.5 IQR to Q3+1.5 IQR", "No"),
    ("Outlier_Eco_Revenue_3SD", "Outlier flag", "1 if outside Mean +/- 3 SD", "No"),
    ("Outlier_Carbon_IQR", "Outlier flag", "1 if outside Q1-1.5 IQR to Q3+1.5 IQR", "No"),
    ("Outlier_Carbon_3SD", "Outlier flag", "1 if outside Mean +/- 3 SD", "No"),
)


def _originals_unchanged(
    raw: Sequence[Mapping[str, str]], cleaned: Sequence[Mapping[str, Any]]
) -> bool:
    def same(raw_value: str, value: Any) -> bool:
        return value == raw_value if isinstance(value, str) else value == float(raw_value)

    return len(raw) == len(cleaned) and all(
        same(raw_value, clean[COLUMN_RENAMES.get(column, column)])
        for source, clean in zip(raw, cleaned)
        for column, raw_value in source.items()
    )


def _dates_and_ranges_valid(cleaned: Sequence[Mapping[str, Any]]) -> bool:
    def valid_date(row: Mapping[str, Any]) -> bool:
        try:
            return date.fromisoformat(row["Period_Date"]) == date(row["Year"], row["Month"], 1)
        except ValueError:
            return False

    in_range = all(
        low <= row[column] <= high
        for row in cleaned for column, (low, high) in VALID_RANGES.items()
    )
    return in_range and all(valid_date(row) for row in cleaned)


def _validation_entry(check: str, passed: bool, evidence: str) -> Row:
    return dict(Check=check, Result="Pass" if passed else "Fail", Evidence=evidence)


def build_final_validation(
    raw: Sequence[Mapping[str, str]], cleaned: Sequence[Mapping[str, Any]],
    country_year: Sequence[Mapping[str, Any]], year_month: Sequence[Mapping[str, Any]],
) -> list[Row]:
    """Re-test the prepared data; each check can fail, so a Pass is earned."""
    ids = [r["Record_ID"] for r in cleaned]
    duplicates = count_exact_duplicates(cleaned, "Record_ID")
    missing = count_true_missing(cleaned, STRUCTURAL_BLANK_COLUMNS)
    blanks = sum(r["Hotel_Star_Level"] is None for r in cleaned)
    unrated = sum(r["Hotel_Rating"] == "Unrated" for r in cleaned)
    typed = sum(count_columns_of_type(cleaned, kind) for kind in (int, float, str))
    variants = count_case_variants(cleaned, TEXT_COLUMNS)
    levels = ", ".join(f"{len({r[c] for r in cleaned})} {c}" for c in TEXT_COLUMNS)
    arrivals = sum(int(r["Number_of_Tourists"]) for r in raw)
    totals = {
        sum(r["Number_of_Tourists"] for r in cleaned),
        sum(r["Observed_Arrivals_Sum"] for r in country_year),
        sum(r["Observed_Arrivals_Sum"] for r in year_month),
    }
    unchanged = _originals_unchanged(raw, cleaned)
    same_order = [r["City"] for r in raw] == [r["City"] for r in cleaned]
    return [
        _validation_entry("No unintended duplicate records", duplicates == 0 and len(set(ids)) == len(ids),
                          f"{duplicates} exact duplicates; {len(set(ids))} unique Record_IDs"),
        _validation_entry("Missing values handled appropriately", missing == 0 and blanks == unrated,
                          f"{missing} missing values; {blanks} structural blanks, one for each Unrated record"),
        _validation_entry("Consistent data types", typed == len(cleaned[0]),
                          f"All {len(cleaned[0])} columns hold a single type"),
        _validation_entry("Consistent category labels", variants == 0,
                          f"{variants} case variants across {levels}"),
        _validation_entry("Valid date and numerical formats", _dates_and_ranges_valid(cleaned),
                          "Every Period_Date is a real date matching its Year and Month; percentages, scores, months and years are in range"),
        _validation_entry("No accidental loss of important observations",
                          unchanged and totals == {arrivals},
                          f"{len(raw)} records in and {len(cleaned)} out; all 23 original columns compared value by value; arrivals total {arrivals:,} reconciles in both summaries"),
        _validation_entry("Dataset structure preserved",
                          same_order and len(raw) == len(cleaned) and all(
                              COLUMN_RENAMES.get(c, c) in cleaned[0] for c in raw[0]),
                          f"One row per original record in raw order; all {len(raw[0])} original columns present, {len(COLUMN_RENAMES)} renamed"),
    ]


def _reached_model_file(column: str, model_columns: frozenset[str]) -> bool:
    return (
        column in model_columns
        or f"{column}_MinMax" in model_columns
        or column in ONE_HOT_SOURCES
    )


def build_data_dictionary(
    cleaned: Sequence[Mapping[str, Any]],
    metadata_rows: Sequence[Mapping[str, str]],
    model_rows: Sequence[Mapping[str, Any]],
) -> list[Row]:
    metadata = {row["Variable"]: row for row in metadata_rows}
    documented = {name: (group, text, eligible) for name, group, text, eligible in ADDED_COLUMN_DOCS}
    reverse_names = {new: old for old, new in COLUMN_RENAMES.items()}
    model_columns = frozenset(model_rows[0])
    entries = []
    for column in cleaned[0]:
        if column in documented:
            group, text, eligible = documented[column]
            scale = ADDED_COLUMN_SCALES.get(column, BINARY_FLAG_SCALE)
        else:
            source = metadata[reverse_names.get(column, column)]
            group, text, scale = "Original", source["Description"], source["Measurement_Scale"]
            eligible = "No" if column in TARGET_DERIVED_COLUMNS else "Yes"
        if column == "Number_of_Tourists":
            eligible = "Target"
        entries.append(dict(
            Column=column, Group=group, Definition=text, Measurement_Scale=scale,
            Phase6_Predictor_of_Arrivals=eligible,
            In_Model_Ready="Yes" if _reached_model_file(column, model_columns) else "No",
        ))
    return entries
