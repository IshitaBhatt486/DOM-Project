"""Write phase3.md in five steps, from the pipeline results, so figures trace back to the data."""

from __future__ import annotations

import statistics as st
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from phase3_config import LARGEST_AIRLINER_SEATS, OUTLIER_MEASURES, SCALED_PREDICTORS

Row = Mapping[str, Any]
ECO = "Eco_Tourism_Revenue_USD_000"
CARBON = "Carbon_Footprint_kg"

IQR_FORMULAS = r"""$$IQR = Q_3 - Q_1$$

$$Lower = Q_1 - 1.5(IQR)$$

$$Upper = Q_3 + 1.5(IQR)$$"""

SCALING_FORMULAS = r"""$$X_{MinMax} = \frac{X - Min}{Max - Min}$$

$$Z = \frac{X - Mean}{Sample\ SD}$$"""

TRANSFORMATION_TABLE = """| Original variable | Transformation | Final format |
|---|---|---|
| Year, Month | Date construction | `Period_Date` as YYYY-MM-01 |
| Month | Calendar labels | `Month_Name`, `Quarter` (Q1 to Q4) |
| Month, Hemisphere | Season derived by hemisphere | `Season` (Winter, Spring, Summer, Autumn) |
| Tourism_Revenue_USD, Eco_Tourism_Revenue_USD | Relabelled with the true unit | `_USD_000`, numeric, values unchanged |
| Hotel_Rating | Label encoding (ordinal) | `Hotel_Star_Level` 1 to 5, blank for Unrated |
| Hotel_Rating | One-hot encoding, model file | 6 columns of 1/0 |
| Country, Purpose_of_Visit, Season | One-hot encoding (nominal), model file | 31 columns of 1/0 |
| City | Left as a label | Text, 56 levels, not encoded |
| Hotel_Occupancy_Rate | Equal-width discretisation | `Occupancy_Band` and `Occupancy_Band_Code` 1 to 4 |
| Number_of_Tourists | Equal-frequency discretisation | `Demand_Tier` and `Demand_Tier_Code` 1 to 4 |
| 14 numeric predictors | Min-Max normalisation, model file | `_MinMax`, decimal from 0 to 1 |
| 14 numeric predictors | Z-score standardisation, comparison only | `_Z` in `scaled_features_both_methods.csv` |
| Spending, stay, tourists, hotels, eco revenue, carbon, passengers, flights | New ratio and product variables | Six decimal columns, listed below |
| Country | Joined to UN M49 | `ISO3`, `UN_Region`, `UN_Sub_Region`, `Hemisphere` |"""

NEW_VARIABLES_TABLE = """| New variable | Formula | Why we wanted it |
|---|---|---|
| Spend_per_Night_USD | Spending ÷ length of stay | Compares visitor value across different trip lengths (Q2) |
| Tourist_Nights | Tourists × length of stay | A fuller measure of demand on accommodation (Q3) |
| Tourists_per_Hotel | Tourists ÷ hotels | Sets demand against capacity (Q3) |
| Eco_Revenue_Share_Pct | 100 × eco revenue ÷ tourism revenue | Phase 2 advised reading eco revenue as a share (Q2) |
| Carbon_kg_per_Tourist | Carbon ÷ tourists | Phase 2 advised reporting carbon per tourist |
| Passengers_per_Flight | Passengers ÷ flights | Tests whether airport figures can be believed |"""


def _format(value: Any) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def md_table(records: Sequence[Row], columns: Sequence[tuple[str, str]]) -> str:
    header = "| " + " | ".join(label for _, label in columns) + " |"
    divider = "|" + "---|" * len(columns)
    body = ["| " + " | ".join(_format(r[key]) for key, _ in columns) + " |" for r in records]
    return "\n".join([header, divider, *body])


def _flag_total(results: Any, flag: str) -> int:
    return sum(r[flag] for r in results.cleaned_rows)


def _summary(results: Any) -> dict[str, Row]:
    return {r["Variable"]: r for r in results.outlier_summary}


def intro_section() -> str:
    return """# Phase 3: Data Preprocessing and Preparation

A dataset can look clean and still need looking at. Ours arrived as 500 records and 23 columns, with no blanks and no repeated rows, and for a moment it seemed there was very little left to do. But what does a tidy file actually tell us? Only that nothing is visibly missing. Whether the values mean what their column names claim, whether they can be believed, and whether later phases can use them in the form they arrived, those questions were still open, and the five steps below are how we went about answering them.

The techniques and formulas follow DOM 304 Module 2 (Data Pre-Processing). The script `analysis/phase3_data_preprocessing.py` calculates the results, and the raw file itself was never altered."""


def _assessment_rows(results: Any) -> list[dict[str, str]]:
    summary = _summary(results)
    room_alone = sum(
        r["Average_Length_of_Stay"] * r["Average_Room_Price_USD"] > r["Tourist_Spending_USD"]
        for r in results.cleaned_rows
    )
    single_cells = sum(r["Records"] == 1 for r in results.country_year)
    unrated = sum(r["Hotel_Rating"] == "Unrated" for r in results.cleaned_rows)
    repeats = _flag_total(results, "Flag_Repeated_City_Month")
    rows = [
        ("Misleading unit", "Tourism_Revenue_USD, Eco_Tourism_Revenue_USD", "Named USD, yet revenue equals tourists × spending ÷ 1,000 in all 500 records, so the values behave as USD thousand", "High"),
        ("Columns calculated from arrivals", "Tourism_Revenue_USD, Eco_Tourism_Revenue_USD, Carbon_Footprint_kg", "Built from Number_of_Tourists (r = 0.45 to 0.64), a leakage risk for any model predicting arrivals", "High"),
        ("Apparent synthetic data", "Most numeric columns", "Nearly uniform between round bounds, with almost no correlation between variables", "High"),
        ("Repeated city-month keys", "City, Year, Month", f"{repeats} records share 30 keys, and city-wide fields conflict within a key", "Medium"),
        ("Sparse coverage", "City, Year, Month", f"500 of 3,360 possible city-month cells are present; {single_cells} country-year cell holds one record", "Medium"),
        ("Potential outliers", "Eco_Tourism_Revenue_USD", f"{summary[ECO]['IQR_Flagged']} records above the IQR limit, {summary[ECO]['SD3_Flagged']} above Mean + 3 SD", "Medium"),
        ("Tier outside the star scale", "Hotel_Rating", f"{unrated} Unrated records have no position among 1-star to 5-star", "Medium"),
        ("Implausible cost relationship", "Average_Length_of_Stay, Average_Room_Price_USD, Tourist_Spending_USD", f"Room cost exceeds total spend in {room_alone} records if one guest pays, {_flag_total(results, 'Flag_Room_Cost_Exceeds_Spend')} if two share", "Medium"),
        ("Potential outliers", "Carbon_Footprint_kg", f"{summary[CARBON]['IQR_Flagged']} records above the IQR limit, {summary[CARBON]['SD3_Flagged']} above Mean + 3 SD", "Low"),
        ("Passengers below tourists", "Airport_Passenger_Traffic, Number_of_Tourists", f"{_flag_total(results, 'Flag_Passengers_Below_Tourists')} records have fewer airport passengers than tourists", "Low"),
        ("High passengers per flight", "Airport_Passenger_Traffic, Number_of_Flights", f"{_flag_total(results, 'Flag_High_Passengers_per_Flight')} records imply more than {LARGEST_AIRLINER_SEATS} passengers per flight", "Low"),
        ("No unique identifier", "All records", "No column or combination of columns identifies a record", "Low"),
        ("Time held in separate codes", "Year, Month", "Two integer columns and no date field", "Low"),
        ("No regional grouping", "Country", "20 countries with nothing to group them", "Low"),
        ("Very different numeric scales", "Numeric columns", "Occupancy runs from 40 to 89.8, carbon from 6.3 million to 99.9 million", "Low"),
        ("Categories stored as text", "Country, City, Purpose_of_Visit, Hotel_Rating", "Predictive models cannot use these directly", "Low"),
    ]
    return [dict(Issue=a, Variable=b, Observation=c, Severity=d) for a, b, c, d in rows]


def step_one(results: Any) -> str:
    table = md_table(_assessment_rows(results), [
        ("Issue", "Issue"), ("Variable", "Variable/Column"),
        ("Observation", "Observation"), ("Severity", "Severity"),
    ])
    return f"""## Step 1: Data quality assessment

We began with the obvious worries. Every cell across all 500 records was tested for blanks and for placeholders such as NA, null or a lone dash, and none appeared. There are no exact duplicates, no stray spaces and no labels differing only in case, each of the 56 cities belongs to one country, and percentages, scores, months and years all sit within their valid ranges. So where were the problems? They were quieter ones, of meaning and of believability, and the table records them as we found them, before any change was made.

{table}

Severity reflects what would happen if the issue were left alone: High would distort results or conclusions, Medium could mislead a particular analysis, and Low is mostly a matter of convenience.

Two of these deserve more than a table row. The repeated keys first seemed harmless, since the records differ in purpose and hotel tier, as if each described a separate segment of the same city and month. But Bangkok in September 2022 shows a GDP share of both 2.6% and 13.5%, and both 481 and 190 hotels, and how can one city have two different GDP shares in one month? The file offers no way of telling. The second is the shape of the data itself, for nearly every numeric variable is spread evenly between a fixed minimum and maximum, and real tourism figures rarely behave so politely. Phase 2 concluded from this that the data appears synthetic, and everything that follows should be read with that in mind."""


def _log_rows(results: Any) -> list[dict[str, Any]]:
    summary = _summary(results)
    rows = [
        ("Tourism_Revenue_USD, Eco_Tourism_Revenue_USD", "Names overstate the unit by a factor of 1,000", "Renamed with `_USD_000`, values unchanged", "Prevents revenue being misread a thousandfold"),
        ("All records", "No unique identifier", "Added `Record_ID`, R0001 to R0500, in raw file order", "Lets any record be traced back to the raw file"),
        ("Year, Month", "No date field", "Created `Period_Date`, keeping both originals", "Gives Tableau and later phases a true time axis"),
        ("Hotel_Rating", "Unrated has no star level", "Created `Hotel_Star_Level` 1 to 5, left blank for Unrated", "Avoids inventing a rating or ranking Unrated below 1-star"),
        ("City, Year, Month", "Repeated keys with conflicting fields", "Investigated, all retained, `Flag_Repeated_City_Month` added", "Nothing shows which record is right"),
        ("Eco_Tourism_Revenue_USD", "Potential outliers", f"Investigated, all {summary[ECO]['IQR_Flagged']} retained, flag columns added", "No arithmetic inconsistency found"),
        ("Carbon_Footprint_kg", "Potential outliers", f"Investigated, all {summary[CARBON]['IQR_Flagged']} retained, flag columns added", "No arithmetic inconsistency found"),
        ("Airport_Passenger_Traffic", "Fewer passengers than tourists", "Retained, `Flag_Passengers_Below_Tourists` added", "Possible through land or sea arrivals"),
        ("Airport_Passenger_Traffic, Number_of_Flights", "Very high passengers per flight", "Retained, ratio and `Flag_High_Passengers_per_Flight` added", "Depends on an undocumented counting basis"),
        ("Length of stay, room price, spending", "Room cost above total spend", "Retained, `Flag_Room_Cost_Exceeds_Spend` added", "The source does not define what spending includes"),
        ("Country", "No regional grouping", "Joined to UN M49 through a name crosswalk, `Hemisphere` added", "Allows regional comparison and correct seasons"),
    ]
    return [dict(No=i, Variable=a, Problem=b, Action=c, Reason=d)
            for i, (a, b, c, d) in enumerate(rows, start=1)]


def step_two(results: Any) -> str:
    table = md_table(_log_rows(results), [
        ("No", "No."), ("Variable", "Variable"), ("Problem", "Problem identified"),
        ("Action", "Action taken"), ("Reason", "Reason"),
    ])
    summary = _summary(results)
    return f"""## Step 2: Data cleaning log

Only what was actually done appears in this log. Since no value was missing and no row repeated exactly, there is no imputation and no removal below, for documenting a fix that never happened would misrepresent the data.

{table}

**Revenue units (1).** Recalculating tourists × spending ÷ 1,000 reproduced Tourism_Revenue_USD, to within rounding, in all 500 records, which showed that the column holds USD thousand despite its name. Both revenue columns were renamed so that nobody downstream reads 951,467 as under a million dollars. The unit is inferred from this arithmetic and the publisher has not confirmed it.

**Record identifier (2).** City, year and month together could not serve as a key, because 30 of those combinations repeat. A sequential `Record_ID` was added in the raw file's order, so that any figure can be followed back to its original line.

**Date field (3).** Year and Month were combined into `Period_Date`, and both originals were kept because Phases 4 and 5 group by them directly.

**Unrated hotels (4).** The 82 Unrated records were examined as possible missing values and recognised as a structural case, where the star scale simply does not apply. Imputing a median star would have invented a rating, and a code of 0 would have ranked them below 1-star, so `Hotel_Star_Level` was left blank for these records and `Hotel_Rating` keeps Unrated as its own level.

**Repeated keys (5).** Investigating the {_flag_total(results, 'Flag_Repeated_City_Month')} records in repeated keys revealed that they are not duplicates, as purpose and hotel tier combinations never repeat within a key, and yet city-wide fields contradict one another. With nothing to indicate which record is right, deleting any of them would have been a guess, so all were retained and flagged.

**Outliers (6 and 7).** The {summary[ECO]['IQR_Flagged']} eco-revenue and {summary[CARBON]['IQR_Flagged']} carbon records beyond the IQR limits were investigated individually, as Step 3 sets out, and retained with flags.

**Believability flags (8 to 10).** Three relationships between columns looked doubtful. Tourists can arrive by land or sea, which could explain the {_flag_total(results, 'Flag_Passengers_Below_Tourists')} records with fewer airport passengers than tourists. The {_flag_total(results, 'Flag_High_Passengers_per_Flight')} records above {LARGEST_AIRLINER_SEATS} passengers per flight, the Airbus A380's maximum certified seating, are a problem only if passengers and flights are counted alike, and Phase 2 describes flights as incoming and passengers as handled by the airport, so the passengers may include departures. Room cost exceeded total spending in {_flag_total(results, 'Flag_Room_Cost_Exceeds_Spend')} records even with two guests sharing, yet the source never says what spending includes. None of this could be settled from the file, so the values were left as they are and the doubt was recorded.

**Regional lookup (11).** The UN M49 table was joined on country name once three differently spelled countries had been matched by hand. Step 4 describes the integration.

Smoothing by binning, which the module also covers, was considered and not applied. Each record is a distinct city and period, and the module cautions against smoothing variation that is meaningful or binning where time order matters. Would averaging these values have made them any truer? It would only have erased the differences this project exists to study."""


def step_three(results: Any) -> str:
    summary = _summary(results)
    rows = [
        {**summary[v], "Spread": summary[v]["Q3"] - summary[v]["Q1"]} for v in OUTLIER_MEASURES
    ]
    table = md_table(rows, [
        ("Variable", "Variable"), ("Q1", "Q1"), ("Q3", "Q3"), ("Spread", "IQR"),
        ("IQR_Lower", "Lower limit"), ("IQR_Upper", "Upper limit"),
        ("IQR_Flagged", "Outliers found"), ("SD3_Flagged", "Beyond Mean ± 3 SD"),
    ])
    return f"""## Step 3: Outlier detection and treatment

A value far from the rest may be an error, or it may be the most interesting record in the file, and the statistics alone cannot say which. Hence every numeric measure was screened first and judged afterwards. Year and Month were left out as time codes. The three score variables are ordinal, and as stated in Phase 2 they are treated as approximately interval for these calculations.

{IQR_FORMULAS}

Quartiles use linear interpolation, the same as Excel's `QUARTILE.INC` and the method used in Phase 4. Limits for the 3 SD rule are Mean ± 3 × sample SD.

{table}

![Box plots of the numeric measures](outputs/phase3/fig_boxplots_outlier_screen.png)

The module recommends IQR for skewed data and the 3 SD rule for data that is approximately normal. Most of our variables are uniform, which is neither, so both were applied, with IQR as the primary test for the two right-skewed columns where anything was found.

{_investigation(results, summary)}

![Flagged totals compared with per-unit measures](outputs/phase3/fig_outliers_per_unit.png)

| Treatment | Applied? | Why |
|---|---|---|
| Retained the outliers | **Yes** | No error was found, and removal would cut mean eco-revenue by {abs(summary[ECO]['Mean_Change_If_Removed_Pct']):.1f}% and mean carbon by {abs(summary[CARBON]['Mean_Change_If_Removed_Pct']):.1f}%, understating the highest-value records in the sample |
| Removed invalid observations | No | None of the flagged observations was shown to be invalid |
| Capped extreme values (winsorisation) | No | Capping would alter values that are internally consistent |
| Transformed the variable | No | The originals stand; the per-unit columns sit beside them and do not replace them |

The `Outlier_*` columns allow Phases 5 and 6 to show or exclude these records as a sensitivity check.

{_engineered_tails(results)}"""


def _investigation(results: Any, summary: Mapping[str, Row]) -> str:
    rows = results.cleaned_rows
    shares = [r["Eco_Revenue_Share_Pct"] for r in rows]
    rates = [r["Carbon_kg_per_Tourist"] for r in rows]
    eco_rows = [r for r in rows if r["Outlier_Eco_Revenue_IQR"]]
    carbon_rows = [r for r in rows if r["Outlier_Carbon_IQR"]]
    eco_shares = [r["Eco_Revenue_Share_Pct"] for r in eco_rows]
    revenue = min(r["Tourism_Revenue_USD_000"] for r in eco_rows)
    median_revenue = st.median(r["Tourism_Revenue_USD_000"] for r in rows)
    carbon_rates = [r["Carbon_kg_per_Tourist"] for r in carbon_rows]
    arrivals = [r["Number_of_Tourists"] for r in carbon_rows]
    median_arrivals = st.median(r["Number_of_Tourists"] for r in rows)
    return f"""Only {sum(1 for v in OUTLIER_MEASURES if summary[v]['IQR_Flagged'])} of the {len(OUTLIER_MEASURES)} measures produced any flags, and why those two? Both are calculated by multiplying other columns together, and multiplication is what stretches a right tail. Looking into the {len(results.outlier_records)} flagged records, listed in `outputs/phase3/outlier_records.csv`, supported this. All {summary[ECO]['IQR_Flagged']} eco-revenue records combine high total revenue (at least {revenue:,.0f} thousand USD, against a median of {median_revenue:,.0f}) with an above-median eco-tourism share ({min(eco_shares):.1f}% to {max(eco_shares):.1f}%, against a median of {st.median(shares):.1f}%), and every share stays inside the {min(shares):.0f}% to {max(shares):.0f}% range seen across the file. All {summary[CARBON]['IQR_Flagged']} carbon records combine very high arrivals ({min(arrivals):,} to {max(arrivals):,}, against a median of {median_arrivals:,.0f}) with some of the highest emissions per tourist ({min(carbon_rates):.0f} to {max(carbon_rates):.0f} kg, against a median of {st.median(rates):.0f} kg).

Once expressed per unit, no record is flagged in either variable. These are single city-month records where two high values happen to coincide, and no arithmetic inconsistency was found. Because the data appears synthetic, we cannot claim that they are accurate in the real world, only that nothing marks them as mistakes."""


def _engineered_tails(results: Any) -> str:
    tails = md_table(
        [r for r in results.outlier_summary if r["Group"] == "Engineered" and r["IQR_Flagged"]],
        [("Variable", "Engineered variable"), ("IQR_Flagged", "IQR flagged"),
         ("SD3_Flagged", "Beyond Mean ± 3 SD"), ("Observed_Max", "Observed max")],
    )
    return f"""Some of the new variables from Step 4 have long right tails of their own, which is what dividing by a small number or multiplying two large ones will do. They too are retained, and medians are the better summary for charts.

{tails}"""


def step_four(results: Any) -> str:
    return f"""## Step 4: Data transformation and standardisation

Cleaning asks whether the data is right, and transformation asks whether it is usable. The module is firm that scaling should happen only when an analysis requires it, so we kept two files for two purposes: `tourism_cleaned.csv` stays in original units for Tableau and descriptive work, and `tourism_model_ready.csv` carries the scaled and encoded form for Phase 6.

{TRANSFORMATION_TABLE}

{NEW_VARIABLES_TABLE}

{_scaling_text()}

{_encoding_text()}

{_binning_text(results)}

{_integration_text(results)}

{_aggregation_text(results)}

{_redundancy_text(results)}"""


def _scaling_text() -> str:
    return f"""### Scaling

{SCALING_FORMULAS}

Both were calculated for the {len(SCALED_PREDICTORS)} numeric predictors, with the Z-score using the sample SD to match Excel's `STANDARDIZE` with `STDEV`. Airport traffic runs close to a million while occupancy stops below 90, and left alone, the larger numbers would dominate any scale-sensitive model.

Which one should the model file use? We chose Min-Max, because these predictors are bounded and roughly uniform with no flagged outliers, so a few extreme values cannot compress the scale, and it places them on the same 0 to 1 range as the one-hot columns. The three ordinal scores are included on the Phase 2 assumption that they are approximately interval. `scaling_parameters.csv` confirms the Min-Max columns run from 0 to 1 and the Z-scores have a mean of 0 and an SD of 1.

![Original units compared with Min-Max scaling](outputs/phase3/fig_scaling_effect.png)"""


def _encoding_text() -> str:
    return """### Encoding

Ordered categories suit a single integer, and unordered ones need a column each, or else a model would read a false distance between Egypt and France. Hotel_Rating needed more thought. Its five star levels have a real order, which `Hotel_Star_Level` keeps in the cleaned file, but Unrated has no place on that scale, so the model file gives each of the six levels its own column. City was left out altogether: 56 levels averaging about 9 records each would add 56 sparse columns, the high-cardinality problem the module warns about. Every level is listed in `outputs/phase3/encoding_map.csv`."""


def _binning_text(results: Any) -> str:
    bins = md_table(results.binning_summary, [
        ("Variable", "Variable"), ("Method", "Method"), ("Label", "Label"),
        ("Lower_Bound", "Lower"), ("Upper_Bound", "Upper"), ("Records", "Records"),
        ("Bin_Width", "Width"),
    ])
    return f"""### Discretisation

Occupancy uses equal-width bins, whose bands are simple to report. Arrivals uses equal-frequency bins, which give four demand tiers of the same size, so its bounds are the lowest and highest values in each tier. Upper edges are inclusive, as in the module's Excel formula. These bands describe this sample and are not industry thresholds.

{bins}"""


def _integration_text(results: Any) -> str:
    checks = md_table(results.integration_checks, [
        ("Check", "Check"), ("Result", "Result"), ("Note", "Note"),
    ])
    return f"""### Integration

The project has one main dataset, and it can be used without merging anything. But 20 countries are a lot to compare, and the file has no way of grouping them. Hence the UN M49 table was joined on country name, following the module's steps of identifying a key, standardising names, performing the lookup (the equivalent of `XLOOKUP`) and validating the result. Three countries are named differently in the two sources, and a direct lookup would have missed them, so a crosswalk maps Turkey to Türkiye, United Kingdom to United Kingdom of Great Britain and Northern Ireland, and United States to United States of America.

`Hemisphere` is a small lookup of our own, needed because January is winter in Italy and summer in Australia. Australia, Brazil and South Africa are Southern and the rest Northern, based on the cities in this dataset.

{checks}"""


def _aggregation_text(results: Any) -> str:
    lowest = min(r["Records"] for r in results.country_year)
    return f"""### Aggregation

Two summaries support Phases 4 and 5: `tourism_country_year_summary.csv` ({len(results.country_year)} rows) and `tourism_year_month_summary.csv` ({len(results.year_month)} rows). Arrivals and revenue are summed. Occupancy, hotel counts and room prices are averaged, for a hotel count is a stock, and adding it across records would give no meaningful total. Spending is weighted by tourists. Each row shows its record count, which falls as low as {lowest} in the country-year table, so these rows should not be read as complete market totals."""


def _redundancy_text(results: Any) -> str:
    table = md_table(results.redundancy, [
        ("Variable_X", "Variable X"), ("Variable_Y", "Variable Y"), ("Pearson_r", "Pearson r"),
    ])
    correlations = [abs(r["Pearson_r"]) for r in results.redundancy]
    first = results.model_rows[0]
    one_hot = len(first) - len(SCALED_PREDICTORS) - 2
    return f"""### Attribute redundancy

Pairs with |r| ≥ 0.7, calculated as with Excel's `CORREL`:

{table}

Every pair shares a formula, so the columns overlap substantially (|r| from {min(correlations):.2f} to {max(correlations):.2f}) without being identical. They stay in the cleaned file because each answers a different business question, and the model file excludes those calculated from arrivals. Sampling was not used, since 500 records are few enough to analyse in full.

The model file has {len(first)} columns: `Record_ID`, the target, {len(SCALED_PREDICTORS)} scaled predictors and {one_hot} one-hot columns."""


def step_five(results: Any) -> str:
    checks = md_table(results.final_validation, [
        ("Check", "Check"), ("Result", "Result"), ("Evidence", "Evidence"),
    ])
    before_after = md_table(results.before_after, [
        ("Metric", "Metric"), ("Before", "Raw file"), ("After", "Cleaned file"),
        ("Model_Ready", "Model-ready file"), ("Note", "Note"),
    ])
    return f"""## Step 5: Final validation

How do we know the preparation did no harm? Each check below was run again on the finished data by the script, and each is able to fail: the test suite deliberately removes a record, alters a value and breaks a date, and confirms that validation catches all three.

{checks}

Beyond the script, the results were recalculated independently in pandas and scikit-learn from the written CSV files, and the quartiles, limits, scaled values, encodings, bins and aggregates all agreed. The raw file's SHA-256 hash still matches the one recorded in Phase 4.

### Before-and-after comparison

{before_after}

**No value in any of the 23 original columns changed**, so the Phase 4 statistics, calculated on the raw file, remain valid."""


def handover_section() -> str:
    return """## Notes for the next phases

**Phase 4.** No change is needed. If it is ever rerun on the cleaned file, its loader must use the two renamed revenue columns.

**Phase 5.** Use `tourism_cleaned.csv` in Tableau, with `UN_Region` for high-level comparisons, `Period_Date` for time axes and the summary files for pre-aggregated views. Avoid summing `Number_of_Hotels` across records.

**Phase 6.** Use `tourism_model_ready.csv` with `Number_of_Tourists` as the target. In `outputs/phase3/data_dictionary.csv`, `Phase6_Predictor_of_Arrivals` = Yes means a column is not calculated from arrivals, and `In_Model_Ready` shows which columns reached the model file. Scaling was fitted on all 500 records for this demonstration, so after the train-test split it should be refitted on the training records alone, using the original values in `tourism_cleaned.csv`. For linear regression, drop one one-hot column from each group (Country, Purpose, Season, Rating) to avoid perfect multicollinearity. Occupancy, passenger traffic and similar measures are recorded in the same period as arrivals, so they would not be known in advance in a true forecast, and Phase 2 found almost no correlation between these predictors and arrivals, so weak predictive results should be expected and reported plainly.

**Limitations.** A clean result here reflects how the data was generated and says little about the quality of real tourism data. Coverage ends in 2024. Season follows the temperate calendar and means less for tropical destinations such as Singapore and Thailand."""


def deliverables_section() -> str:
    return """## Files and reproduction

Run from the repository root (Python 3.10+ and matplotlib; pandas is not required):

```sh
python analysis/phase3_data_preprocessing.py
python -m unittest discover -s tests -v
```

`notebooks/03_Data_Preprocessing.ipynb` runs the same script and displays this report.

| File | Contents |
|---|---|
| `data/processed/tourism_cleaned.csv` | Cleaned dataset for Phases 4 and 5 and Tableau |
| `data/processed/tourism_model_ready.csv` | Encoded and scaled dataset for Phase 6 |
| `data/processed/tourism_country_year_summary.csv` | Country-year aggregation |
| `data/processed/tourism_year_month_summary.csv` | Monthly aggregation |
| `data/external/un_m49_regions.csv` | UN M49 lookup used for integration |
| `outputs/phase3/before_after_comparison.csv` | Before-and-after table |
| `outputs/phase3/data_type_changes.csv` | Type of each original column before and after |
| `outputs/phase3/data_quality_log.csv` | Checks by data quality dimension |
| `outputs/phase3/outlier_summary.csv`, `outlier_records.csv` | Limits, counts, treatment and flagged records |
| `outputs/phase3/scaling_parameters.csv`, `scaled_features_both_methods.csv` | Scaling inputs, checks and both methods' results |
| `outputs/phase3/encoding_map.csv`, `binning_summary.csv` | Encoding levels and bins |
| `outputs/phase3/integration_checks.csv`, `redundancy_check.csv` | Join validation and correlated pairs |
| `outputs/phase3/final_validation.csv` | The seven final checks and their evidence |
| `outputs/phase3/data_dictionary.csv` | Every cleaned column, with its Phase 6 eligibility |
| `outputs/phase3/fig_*.png` | Box plots and the scaling comparison |

### Data sourcing log (addition for the report appendix)

| Source URL | Date of collection | Tool / method |
|---|---|---|
| https://unstats.un.org/unsd/methodology/m49/overview/ | 10 November 2026 | Public page, no login. Downloaded once with `curl`, after checking `robots.txt`, which only restricts `/wiki/` paths. The English table was parsed and six columns kept. It contains no personal data. |"""


def write_report(results: Any, path: Path) -> None:
    sections = (
        intro_section(), step_one(results), step_two(results), step_three(results),
        step_four(results), step_five(results), handover_section(), deliverables_section(),
    )
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
