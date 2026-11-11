"""Phase 3: data cleaning, outlier detection, integration and transformation.

Run from any directory: python analysis/phase3_data_preprocessing.py

Needs Python 3.10+ and matplotlib (for the box plots). pandas is deliberately not
used because Windows Smart App Control blocks it on a team member's machine.
The raw file is never modified. See phase3.md for the decisions and their reasons.
"""

from __future__ import annotations

import calendar
import csv
import logging
import re
import statistics as st
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import phase3_audit as audit
import phase3_methods as methods
from phase3_config import (
    BIN_COUNT,
    COLUMN_RENAMES,
    COUNTRY_CROSSWALK,
    DEMAND_TIER_LABELS,
    DERIVED_DECIMALS,
    ENGINEERED_MEASURES,
    HOTEL_RATING_LEVELS,
    HOTEL_STAR_LEVELS,
    INTEGER_COLUMNS,
    LARGEST_AIRLINER_SEATS,
    OCCUPANCY_BAND_LABELS,
    ONE_HOT_SOURCES,
    OUTLIER_FLAGS,
    OUTLIER_MEASURES,
    PEOPLE_SHARING_A_ROOM,
    POSITIVE_COLUMNS,
    PURPOSE_LEVELS,
    REVENUE_IDENTITY_TOLERANCE,
    SCALED_DECIMALS,
    SCALED_PREDICTORS,
    SOUTHERN_HEMISPHERE_COUNTRIES,
    TEXT_COLUMNS,
    VALID_RANGES,
)

Row = dict[str, Any]

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/Tourism_Hospitality_Industry_Analysis.csv"
M49 = ROOT / "data/external/un_m49_regions.csv"
PROCESSED = ROOT / "data/processed"
OUT = ROOT / "outputs/phase3"
PHASE2_METADATA = ROOT / "outputs/phase2/metadata_table.csv"

@dataclass(frozen=True)
class Phase3Results:
    """Everything the pipeline produces; written to disk and reported separately."""

    cleaned_rows: list[Row]
    model_rows: list[Row]
    country_year: list[Row]
    year_month: list[Row]
    before_after: list[Row]
    data_type_changes: list[Row]
    quality_log: list[Row]
    outlier_summary: list[Row]
    outlier_records: list[Row]
    scaling_parameters: list[Row]
    scaled_both_methods: list[Row]
    encoding_map: list[Row]
    binning_summary: list[Row]
    integration_checks: list[Row]
    redundancy: list[Row]
    data_dictionary: list[Row]
    final_validation: list[Row]
    reference_by_country: dict[str, Row]


# ---------------------------------------------------------------- reading and cleaning


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def standardise_text(rows: Sequence[Mapping[str, str]]) -> tuple[list[dict[str, str]], int]:
    """Trim cells and collapse repeated spaces; return new rows and the cells changed."""
    tidy = [
        {key: re.sub(r"\s+", " ", value).strip() for key, value in row.items()} for row in rows
    ]
    changed = sum(a[k] != b[k] for a, b in zip(rows, tidy) for k in a)
    return tidy, changed


def remove_exact_duplicates(
    rows: Sequence[Mapping[str, str]],
) -> tuple[list[dict[str, str]], int]:
    unique = [dict(items) for items in dict.fromkeys(tuple(row.items()) for row in rows)]
    return unique, len(rows) - len(unique)


def require_complete(rows: Sequence[Mapping[str, str]]) -> None:
    """Stop rather than guess: the imputation method depends on the variable's scale."""
    for line, row in enumerate(rows, start=2):
        blanks = [key for key, value in row.items() if methods.is_missing(value)]
        if blanks:
            raise ValueError(f"Missing value on line {line}: {blanks}. Choose a treatment first.")


def coerce_types(rows: Sequence[Mapping[str, str]]) -> list[Row]:
    def convert(key: str, value: str) -> Any:
        if key in TEXT_COLUMNS:
            return value
        return int(value) if key in INTEGER_COLUMNS else float(value)

    return [{key: convert(key, value) for key, value in row.items()} for row in rows]


def validate_rows(rows: Sequence[Mapping[str, Any]]) -> None:
    """Enforce the accuracy rules; a failure means the source changed and needs review."""
    for number, row in enumerate(rows, start=1):
        for column, (low, high) in VALID_RANGES.items():
            if not low <= row[column] <= high:
                raise ValueError(f"Record {number}: {column}={row[column]} outside {low}-{high}.")
        for column in POSITIVE_COLUMNS:
            if row[column] <= 0:
                raise ValueError(f"Record {number}: {column} must be positive.")
        if row["Hotel_Rating"] not in HOTEL_RATING_LEVELS:
            raise ValueError(f"Record {number}: unknown Hotel_Rating {row['Hotel_Rating']}.")
        if row["Purpose_of_Visit"] not in PURPOSE_LEVELS:
            raise ValueError(f"Record {number}: unknown Purpose {row['Purpose_of_Visit']}.")
        expected = row["Number_of_Tourists"] * row["Tourist_Spending_USD"] / 1000
        if abs(row["Tourism_Revenue_USD"] - expected) > REVENUE_IDENTITY_TOLERANCE:
            raise ValueError(f"Record {number}: revenue identity no longer holds.")


def rename_and_identify(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    return [
        {
            "Record_ID": f"R{number:04d}",
            **{COLUMN_RENAMES.get(key, key): value for key, value in row.items()},
        }
        for number, row in enumerate(rows, start=1)
    ]


# ---------------------------------------------------------------- integration


def load_country_reference(path: Path, countries: Iterable[str]) -> dict[str, Row]:
    """Join key = the Kaggle country name, resolved to the UN name through the crosswalk."""
    by_un_name = {row["Country_or_Area"]: row for row in read_csv_rows(path)}
    reference: dict[str, Row] = {}
    for country in sorted(set(countries)):
        un_row = by_un_name.get(COUNTRY_CROSSWALK.get(country, country))
        if un_row is None:
            continue
        reference[country] = {
            "ISO3": un_row["ISO_Alpha3"],
            "UN_Region": un_row["Region_Name"],
            "UN_Sub_Region": un_row["Sub_Region_Name"],
            "Hemisphere": "Southern" if country in SOUTHERN_HEMISPHERE_COUNTRIES else "Northern",
        }
    return reference


def count_duplicate_lookup_names(path: Path) -> int:
    names = [row["Country_or_Area"] for row in read_csv_rows(path)]
    return len(names) - len(set(names))


def integrate_country_reference(
    rows: Sequence[Mapping[str, Any]], reference: Mapping[str, Row]
) -> list[Row]:
    unmatched = sorted({row["Country"] for row in rows} - set(reference))
    if unmatched:
        raise ValueError(f"No UN M49 match for: {unmatched}")
    return [{**row, **reference[row["Country"]]} for row in rows]


def integration_checks(
    before: Sequence[Mapping[str, Any]],
    after: Sequence[Mapping[str, Any]],
    reference: Mapping[str, Row],
    lookup_duplicates: int,
) -> list[Row]:
    added = ["ISO3", "UN_Region", "UN_Sub_Region", "Hemisphere"]
    blanks = sum(1 for row in after for column in added if not row[column])
    rows = [
        ("Record count before join", len(before), "Left table"),
        ("Record count after join", len(after), "Must equal the left table"),
        ("Distinct countries in left table", len({r["Country"] for r in before}), ""),
        ("Countries matched in UN M49", len(reference), "Must equal distinct countries"),
        ("Country names needing the crosswalk", len(COUNTRY_CROSSWALK), ", ".join(COUNTRY_CROSSWALK)),
        ("Blank cells in joined columns", blanks, "Must be 0"),
        ("Duplicate Record_IDs after join", len(after) - len({r["Record_ID"] for r in after}), "Must be 0"),
        ("Duplicate country names in UN table", lookup_duplicates, "Must be 0, or a join can multiply rows"),
    ]
    return [dict(Check=check, Result=result, Note=note) for check, result, note in rows]


# ---------------------------------------------------------------- feature creation


def add_time_features(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    return [
        {
            **row,
            "Period_Date": f"{row['Year']}-{row['Month']:02d}-01",
            "Quarter": methods.quarter_for(row["Month"]),
            "Month_Name": calendar.month_name[row["Month"]],
            "Season": methods.season_for(row["Month"], row["Hemisphere"]),
        }
        for row in rows
    ]


def add_ratio_features(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    def ratios(row: Mapping[str, Any]) -> Row:
        tourists = row["Number_of_Tourists"]
        return {
            "Spend_per_Night_USD": round(
                row["Tourist_Spending_USD"] / row["Average_Length_of_Stay"], DERIVED_DECIMALS),
            "Tourist_Nights": round(tourists * row["Average_Length_of_Stay"], 1),
            "Tourists_per_Hotel": round(tourists / row["Number_of_Hotels"], DERIVED_DECIMALS),
            "Eco_Revenue_Share_Pct": round(
                100 * row["Eco_Tourism_Revenue_USD_000"] / row["Tourism_Revenue_USD_000"],
                DERIVED_DECIMALS),
            "Carbon_kg_per_Tourist": round(row["Carbon_Footprint_kg"] / tourists, DERIVED_DECIMALS),
            "Passengers_per_Flight": round(
                row["Airport_Passenger_Traffic"] / row["Number_of_Flights"], DERIVED_DECIMALS),
        }

    return [{**row, **ratios(row)} for row in rows]


def add_encoded_rating(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    codes = methods.label_encode([r["Hotel_Rating"] for r in rows], HOTEL_STAR_LEVELS)
    return [{**row, "Hotel_Star_Level": code} for row, code in zip(rows, codes)]


def band_name(label: str, low: float, high: float, unit: str) -> str:
    return f"{label} ({low:.2f}-{high:.2f}{unit})"


def add_bins(rows: Sequence[Mapping[str, Any]]) -> tuple[list[Row], list[Row]]:
    """Occupancy gets equal-width bands, arrivals get equal-frequency tiers (slides 34-35)."""
    occupancy = [r["Hotel_Occupancy_Rate"] for r in rows]
    edges = methods.equal_width_edges(occupancy, BIN_COUNT)
    occupancy_codes = methods.assign_equal_width(occupancy, edges)
    occupancy_names = {
        code: band_name(OCCUPANCY_BAND_LABELS[code - 1], edges[code - 1], edges[code], "%")
        for code in range(1, BIN_COUNT + 1)
    }
    tourists = [r["Number_of_Tourists"] for r in rows]
    tier_codes = methods.assign_equal_frequency(tourists, BIN_COUNT)
    binned = [
        {
            **row,
            "Occupancy_Band": occupancy_names[occ],
            "Occupancy_Band_Code": occ,
            "Demand_Tier": DEMAND_TIER_LABELS[tier - 1],
            "Demand_Tier_Code": tier,
        }
        for row, occ, tier in zip(rows, occupancy_codes, tier_codes)
    ]
    summary = _bin_summary("Hotel_Occupancy_Rate", "Equal-width", occupancy, occupancy_codes,
                           OCCUPANCY_BAND_LABELS, edges)
    summary += _bin_summary("Number_of_Tourists", "Equal-frequency", tourists, tier_codes,
                            DEMAND_TIER_LABELS)
    return binned, summary


def _bin_summary(
    variable: str, method: str, values: Sequence[float], codes: Sequence[int],
    labels: Sequence[str], edges: Sequence[float] | None = None,
) -> list[Row]:
    """Bounds are the bin edges for equal-width, the observed span for equal-frequency."""
    summary = []
    for code in range(1, BIN_COUNT + 1):
        members = [v for v, c in zip(values, codes) if c == code]
        lower, upper = (edges[code - 1], edges[code]) if edges else (min(members), max(members))
        summary.append(dict(
            Variable=variable, Method=method, Code=code, Label=labels[code - 1],
            Lower_Bound=round(lower, DERIVED_DECIMALS), Upper_Bound=round(upper, DERIVED_DECIMALS),
            Records=len(members), Bin_Width=round(upper - lower, DERIVED_DECIMALS),
        ))
    return summary


def add_believability_flags(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    key_counts = Counter((r["City"], r["Year"], r["Month"]) for r in rows)

    def flags(row: Mapping[str, Any]) -> Row:
        room_cost = row["Average_Length_of_Stay"] * row["Average_Room_Price_USD"]
        return {
            "Flag_Repeated_City_Month": int(key_counts[(row["City"], row["Year"], row["Month"])] > 1),
            "Flag_Passengers_Below_Tourists": int(
                row["Airport_Passenger_Traffic"] < row["Number_of_Tourists"]),
            "Flag_High_Passengers_per_Flight": int(
                row["Passengers_per_Flight"] > LARGEST_AIRLINER_SEATS),
            "Flag_Room_Cost_Exceeds_Spend": int(
                room_cost / PEOPLE_SHARING_A_ROOM > row["Tourist_Spending_USD"]),
        }

    return [{**row, **flags(row)} for row in rows]


# ---------------------------------------------------------------- outlier analysis


def summarise_outliers(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    summary = []
    for variable in (*OUTLIER_MEASURES, *ENGINEERED_MEASURES):
        values = [r[variable] for r in rows]
        iqr, sd3 = methods.iqr_limits(values), methods.sd_limits(values)
        kept = [v for v in values if not iqr.is_outside(v)]
        mean_all = st.mean(values)
        mean_kept = st.mean(kept)
        summary.append(dict(
            Variable=variable,
            Group="Original" if variable in OUTLIER_MEASURES else "Engineered",
            Q1=methods.percentile(values, 25), Q3=methods.percentile(values, 75),
            IQR_Lower=iqr.lower, IQR_Upper=iqr.upper,
            IQR_Flagged=sum(iqr.is_outside(v) for v in values),
            Mean=mean_all, Sample_SD=st.stdev(values),
            SD3_Lower=sd3.lower, SD3_Upper=sd3.upper,
            SD3_Flagged=sum(sd3.is_outside(v) for v in values),
            Max_Abs_Z=max(abs(z) for z in methods.z_scores(values)),
            Observed_Min=min(values), Observed_Max=max(values),
            Mean_Without_IQR_Flagged=mean_kept,
            Mean_Change_If_Removed_Pct=100 * (mean_kept - mean_all) / mean_all,
            Treatment=_outlier_treatment(variable, sum(iqr.is_outside(v) for v in values)),
        ))
    return summary


def _outlier_treatment(variable: str, flagged: int) -> str:
    if flagged == 0:
        return "None flagged"
    if variable in OUTLIER_FLAGS:
        return "Retained and flagged: no arithmetic inconsistency found"
    return "Retained: tail follows from the formula; use medians in charts"


def add_outlier_flags(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    def limits_for(column: str) -> tuple[methods.Limits, methods.Limits]:
        values = [r[column] for r in rows]
        return methods.iqr_limits(values), methods.sd_limits(values)

    limits = {column: limits_for(column) for column in OUTLIER_FLAGS}

    def flags(row: Mapping[str, Any]) -> Row:
        result: Row = {}
        for column, (iqr_name, sd_name) in OUTLIER_FLAGS.items():
            iqr, sd3 = limits[column]
            result[iqr_name] = int(iqr.is_outside(row[column]))
            result[sd_name] = int(sd3.is_outside(row[column]))
        return result

    return [{**row, **flags(row)} for row in rows]


def list_outlier_records(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    """Show each flagged record beside the drivers used to judge whether it is an error."""
    flagged = [
        row for row in rows
        if row["Outlier_Eco_Revenue_IQR"] or row["Outlier_Carbon_IQR"]
    ]
    columns = (
        "Record_ID", "Country", "City", "Year", "Month", "Number_of_Tourists",
        "Tourist_Spending_USD", "Tourism_Revenue_USD_000", "Eco_Tourism_Revenue_USD_000",
        "Eco_Revenue_Share_Pct", "Carbon_Footprint_kg", "Carbon_kg_per_Tourist",
        "Outlier_Eco_Revenue_IQR", "Outlier_Eco_Revenue_3SD",
        "Outlier_Carbon_IQR", "Outlier_Carbon_3SD",
    )
    return [{column: row[column] for column in columns} for row in flagged]


# ---------------------------------------------------------------- scaling and encoding


def scale_predictors(rows: Sequence[Mapping[str, Any]]) -> tuple[list[Row], list[Row]]:
    """Calculate both slide 28 methods; only min-max goes into the model-ready file."""
    parameters, columns = [], {}
    for variable in SCALED_PREDICTORS:
        values = [r[variable] for r in rows]
        scaled_mm = [round(x, SCALED_DECIMALS) for x in methods.min_max(values)]
        scaled_z = [round(x, SCALED_DECIMALS) for x in methods.z_scores(values)]
        columns[f"{variable}_MinMax"], columns[f"{variable}_Z"] = scaled_mm, scaled_z
        parameters.append(dict(
            Variable=variable, Original_Min=min(values), Original_Max=max(values),
            Original_Mean=st.mean(values), Original_Sample_SD=st.stdev(values),
            MinMax_Min=min(scaled_mm), MinMax_Max=max(scaled_mm),
            Z_Mean=st.mean(scaled_z), Z_Sample_SD=st.stdev(scaled_z),
        ))
    both = [
        {"Record_ID": row["Record_ID"], **{name: col[i] for name, col in columns.items()}}
        for i, row in enumerate(rows)
    ]
    return both, parameters


def category_levels(rows: Sequence[Mapping[str, Any]], source: str) -> list[str]:
    fixed: dict[str, Sequence[str]] = {
        "Hotel_Rating": HOTEL_RATING_LEVELS,
        "Purpose_of_Visit": PURPOSE_LEVELS,
        "Season": ("Winter", "Spring", "Summer", "Autumn"),
    }
    return list(fixed.get(source, sorted({r[source] for r in rows})))


def build_model_rows(
    rows: Sequence[Mapping[str, Any]], scaled: Sequence[Mapping[str, Any]]
) -> list[Row]:
    encoded: dict[str, list[int]] = {}
    for source, prefix in ONE_HOT_SOURCES.items():
        encoded |= methods.one_hot(
            [r[source] for r in rows], category_levels(rows, source), prefix)
    model_rows = []
    for i, (row, scaled_row) in enumerate(zip(rows, scaled)):
        predictors = {f"{v}_MinMax": scaled_row[f"{v}_MinMax"] for v in SCALED_PREDICTORS}
        model_rows.append({
            "Record_ID": row["Record_ID"],
            "Number_of_Tourists": row["Number_of_Tourists"],
            **predictors,
            **{column: values[i] for column, values in encoded.items()},
        })
    return model_rows


def build_encoding_map(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    entries: list[Row] = [
        dict(Variable="Hotel_Rating", Method="Label (ordinal)", Level=label,
             Encoded_As="Hotel_Star_Level", Code=code)
        for label, code in HOTEL_STAR_LEVELS.items()
    ]
    entries.append(dict(Variable="Hotel_Rating", Method="Label (ordinal)", Level="Unrated",
                        Encoded_As="Hotel_Star_Level", Code="blank (not on the star scale)"))
    for source, prefix in ONE_HOT_SOURCES.items():
        entries += [
            dict(Variable=source, Method="One-hot (nominal)", Level=level,
                 Encoded_As=f"{prefix}_{methods.column_safe(level)}", Code="1 if match, else 0")
            for level in category_levels(rows, source)
        ]
    return entries


# ---------------------------------------------------------------- aggregation


def summarise_group(rows: Sequence[Mapping[str, Any]]) -> Row:
    """Flows are summed; rates, prices and hotel stocks are averaged, never summed."""
    arrivals = sum(r["Number_of_Tourists"] for r in rows)
    return dict(
        Records=len(rows),
        Observed_Arrivals_Sum=arrivals,
        Observed_Revenue_Sum_USD_000=round(sum(r["Tourism_Revenue_USD_000"] for r in rows), 2),
        Tourist_Weighted_Spending_USD=sum(
            r["Number_of_Tourists"] * r["Tourist_Spending_USD"] for r in rows) / arrivals,
        Mean_Occupancy_Percent=st.mean(r["Hotel_Occupancy_Rate"] for r in rows),
        Mean_Hotels_Per_Record=st.mean(r["Number_of_Hotels"] for r in rows),
        Mean_Room_Price_USD=st.mean(r["Average_Room_Price_USD"] for r in rows),
    )


def aggregate(
    rows: Sequence[Mapping[str, Any]], key: Callable[[Mapping[str, Any]], Row]
) -> list[Row]:
    groups: dict[tuple, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(key(row).items())].append(row)
    return [{**dict(group_key), **summarise_group(members)}
            for group_key, members in sorted(groups.items())]


def rounded_summary(table: Sequence[Mapping[str, Any]]) -> list[Row]:
    return [
        {k: round(v, DERIVED_DECIMALS) if isinstance(v, float) else v for k, v in row.items()}
        for row in table
    ]


# ---------------------------------------------------------------- orchestration


def order_cleaned_columns(rows: Sequence[Mapping[str, Any]]) -> list[Row]:
    leading = (
        "Record_ID", "Period_Date", "Year", "Quarter", "Month", "Month_Name", "Season",
        "Country", "ISO3", "UN_Region", "UN_Sub_Region", "Hemisphere", "City",
        "Purpose_of_Visit", "Hotel_Rating", "Hotel_Star_Level",
    )
    rest = [column for column in rows[0] if column not in leading]
    return [{column: row[column] for column in (*leading, *rest)} for row in rows]


def clean_records(raw: Sequence[Mapping[str, str]]) -> tuple[list[Row], int, int]:
    tidy, text_changed = standardise_text(raw)
    require_complete(tidy)
    unique, removed = remove_exact_duplicates(tidy)
    typed = coerce_types(unique)
    validate_rows(typed)
    return rename_and_identify(typed), removed, text_changed


def engineer_features(rows: Sequence[Mapping[str, Any]]) -> tuple[list[Row], list[Row]]:
    enriched = add_encoded_rating(add_ratio_features(add_time_features(rows)))
    binned, binning_summary = add_bins(enriched)
    return add_outlier_flags(add_believability_flags(binned)), binning_summary


def build_phase3(raw_path: Path, m49_path: Path) -> Phase3Results:
    raw = read_csv_rows(raw_path)
    identified, removed, text_changed = clean_records(raw)
    reference = load_country_reference(m49_path, (r["Country"] for r in identified))
    integrated = integrate_country_reference(identified, reference)
    featured, binning_summary = engineer_features(integrated)
    cleaned = order_cleaned_columns(featured)
    both_scaled, scaling_parameters = scale_predictors(cleaned)
    model_rows = build_model_rows(cleaned, both_scaled)
    country_year = rounded_summary(aggregate(
        cleaned, lambda r: {"Country": r["Country"], "UN_Region": r["UN_Region"], "Year": r["Year"]}))
    year_month = rounded_summary(aggregate(
        cleaned, lambda r: {"Period_Date": r["Period_Date"], "Year": r["Year"], "Month": r["Month"]}))
    return Phase3Results(
        cleaned_rows=cleaned,
        model_rows=model_rows,
        country_year=country_year,
        year_month=year_month,
        final_validation=audit.build_final_validation(raw, cleaned, country_year, year_month),
        before_after=audit.build_before_after(raw, cleaned, model_rows, text_changed),
        data_type_changes=audit.build_data_type_changes(raw),
        quality_log=audit.build_quality_log(cleaned, removed, text_changed),
        outlier_summary=summarise_outliers(cleaned),
        outlier_records=list_outlier_records(cleaned),
        scaling_parameters=scaling_parameters,
        scaled_both_methods=both_scaled,
        encoding_map=build_encoding_map(cleaned),
        binning_summary=binning_summary,
        integration_checks=integration_checks(
            identified, integrated, reference, count_duplicate_lookup_names(m49_path)),
        redundancy=audit.find_redundant_pairs(cleaned),
        data_dictionary=audit.build_data_dictionary(
            cleaned, read_csv_rows(PHASE2_METADATA), model_rows),
        reference_by_country=reference,
    )


def write_table(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(results: Phase3Results) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    datasets = {
        "tourism_cleaned.csv": results.cleaned_rows,
        "tourism_model_ready.csv": results.model_rows,
        "tourism_country_year_summary.csv": results.country_year,
        "tourism_year_month_summary.csv": results.year_month,
    }
    tables = {
        "before_after_comparison.csv": results.before_after,
        "data_type_changes.csv": results.data_type_changes,
        "data_quality_log.csv": results.quality_log,
        "outlier_summary.csv": results.outlier_summary,
        "outlier_records.csv": results.outlier_records,
        "scaling_parameters.csv": results.scaling_parameters,
        "scaled_features_both_methods.csv": results.scaled_both_methods,
        "encoding_map.csv": results.encoding_map,
        "binning_summary.csv": results.binning_summary,
        "integration_checks.csv": results.integration_checks,
        "redundancy_check.csv": results.redundancy,
        "data_dictionary.csv": results.data_dictionary,
        "final_validation.csv": results.final_validation,
    }
    for name, rows in datasets.items():
        write_table(PROCESSED / name, rows)
    for name, rows in tables.items():
        write_table(OUT / name, rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Imported here so the data pipeline and its tests do not depend on matplotlib or the report.
    import phase3_figures
    import phase3_report

    results = build_phase3(RAW, M49)
    write_outputs(results)
    phase3_figures.draw_all(results, OUT)
    phase3_report.write_report(results, ROOT / "phase3.md")
    logging.getLogger(__name__).info(
        "Phase 3 complete: %d records, %d cleaned columns, %d model-ready columns.",
        len(results.cleaned_rows), len(results.cleaned_rows[0]), len(results.model_rows[0]),
    )


if __name__ == "__main__":
    main()
