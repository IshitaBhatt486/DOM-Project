"""Phase 3 checks. Formula tests use the worked examples from the DOM 304 Module 2 slides.

Run: python -m unittest discover -s tests -v
"""

import statistics as st
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

import phase3_audit as audit  # noqa: E402
import phase3_data_preprocessing as pipeline  # noqa: E402
import phase3_methods as methods  # noqa: E402

INCOME = [18000, 64500, 120000, 200000]
AGE = [18, 20, 36, 40]
DELIVERY_MINUTES = [
    65, 25, 110, 38, 18, 50, 85, 30, 140, 42,
    27, 70, 35, 60, 22, 100, 45, 32, 55, 40,
]
LEAKAGE_COLUMNS = {
    "Tourism_Revenue_USD_000", "Eco_Tourism_Revenue_USD_000", "Carbon_Footprint_kg",
    "Tourists_per_Hotel", "Tourist_Nights", "Carbon_kg_per_Tourist",
    "Eco_Revenue_Share_Pct", "Demand_Tier", "Demand_Tier_Code",
}


def bin_counts(assignments: list[int]) -> list[int]:
    return [assignments.count(b) for b in sorted(set(assignments))]


class SlideFormulaTests(unittest.TestCase):
    def test_min_max_matches_slide_29(self) -> None:
        self.assertEqual([round(x, 2) for x in methods.min_max(INCOME)], [0, 0.26, 0.56, 1])
        self.assertEqual([round(x, 2) for x in methods.min_max(AGE)], [0, 0.09, 0.82, 1])

    def test_z_score_uses_sample_sd_like_excel_stdev(self) -> None:
        self.assertEqual([round(x, 1) for x in methods.z_scores(INCOME)], [-1.1, -0.5, 0.2, 1.3])
        self.assertEqual([round(x, 1) for x in methods.z_scores(AGE)], [-0.9, -0.8, 0.7, 1.0])

    def test_scaling_a_constant_column_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            methods.min_max([5, 5, 5])
        with self.assertRaises(ValueError):
            methods.z_scores([5, 5, 5])

    def test_iqr_limits_use_1_5_times_iqr(self) -> None:
        limits = methods.iqr_limits([1, 2, 3, 4, 100])
        self.assertEqual((limits.lower, limits.upper), (-1.0, 7.0))
        self.assertTrue(limits.is_outside(100))
        self.assertFalse(limits.is_outside(7))

    def test_sd_limits_use_mean_plus_minus_three_sample_sd(self) -> None:
        values = [2, 4, 4, 4, 5, 5, 7, 9]
        sd = st.stdev(values)
        limits = methods.sd_limits(values)
        self.assertAlmostEqual(limits.lower, 5 - 3 * sd)
        self.assertAlmostEqual(limits.upper, 5 + 3 * sd)

    def test_equal_width_matches_slide_34(self) -> None:
        edges = methods.equal_width_edges(DELIVERY_MINUTES, 4)
        self.assertEqual(edges, [18, 48.5, 79, 109.5, 140])
        assigned = methods.assign_equal_width(DELIVERY_MINUTES, edges)
        self.assertEqual(bin_counts(assigned), [11, 5, 2, 2])

    def test_equal_width_upper_edge_is_inclusive(self) -> None:
        self.assertEqual(methods.assign_equal_width([48.5, 48.6], [18, 48.5, 79]), [1, 2])

    def test_equal_frequency_matches_slide_35(self) -> None:
        assigned = methods.assign_equal_frequency(DELIVERY_MINUTES, 4)
        self.assertEqual(bin_counts(assigned), [5, 5, 5, 5])
        widths = []
        for b in range(1, 5):
            members = [v for v, a in zip(DELIVERY_MINUTES, assigned) if a == b]
            widths.append(max(members) - min(members))
        self.assertEqual(widths, [12, 10, 20, 70])

    def test_one_hot_matches_slide_30(self) -> None:
        encoded = methods.one_hot(["Card", "UPI"], ["Card", "UPI", "Cash"], "Payment")
        self.assertEqual(encoded, {
            "Payment_Card": [1, 0], "Payment_UPI": [0, 1], "Payment_Cash": [0, 0],
        })

    def test_one_hot_rejects_unknown_level(self) -> None:
        with self.assertRaises(ValueError):
            methods.one_hot(["Crypto"], ["Card"], "Payment")

    def test_label_encoding_keeps_order_and_leaves_unmapped_blank(self) -> None:
        mapping = {"Low": 0, "Medium": 1, "High": 2}
        self.assertEqual(methods.label_encode(["High", "Low"], mapping), [2, 0])
        self.assertEqual(methods.label_encode(["Unrated"], mapping), [None])

    def test_season_depends_on_hemisphere(self) -> None:
        self.assertEqual(methods.season_for(1, "Northern"), "Winter")
        self.assertEqual(methods.season_for(1, "Southern"), "Summer")
        self.assertEqual(methods.season_for(10, "Southern"), "Spring")

    def test_quarter(self) -> None:
        self.assertEqual([methods.quarter_for(m) for m in (1, 3, 4, 12)],
                         ["Q1", "Q1", "Q2", "Q4"])


class CleaningRuleTests(unittest.TestCase):
    def test_text_standardising_returns_new_rows_and_counts_changes(self) -> None:
        original = [{"Country": " Italy ", "City": "New  York"}]
        cleaned, changed = pipeline.standardise_text(original)
        self.assertEqual(cleaned, [{"Country": "Italy", "City": "New York"}])
        self.assertEqual(changed, 2)
        self.assertEqual(original[0]["Country"], " Italy ")

    def test_exact_duplicates_keep_first_occurrence(self) -> None:
        rows = [{"a": "1"}, {"a": "2"}, {"a": "1"}]
        unique, removed = pipeline.remove_exact_duplicates(rows)
        self.assertEqual(unique, [{"a": "1"}, {"a": "2"}])
        self.assertEqual(removed, 1)

    def test_blank_cell_stops_the_pipeline(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing"):
            pipeline.require_complete([{"Country": ""}])

    def test_placeholder_counts_as_missing(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing"):
            pipeline.require_complete([{"Country": "N/A"}])

    def test_out_of_range_month_is_rejected(self) -> None:
        row = {**pipeline.coerce_types(RAW_ROWS[:1])[0], "Month": 13}
        with self.assertRaisesRegex(ValueError, "Month"):
            pipeline.validate_rows([row])

    def test_occupancy_above_100_is_rejected(self) -> None:
        row = {**pipeline.coerce_types(RAW_ROWS[:1])[0], "Hotel_Occupancy_Rate": 101.0}
        with self.assertRaisesRegex(ValueError, "Hotel_Occupancy_Rate"):
            pipeline.validate_rows([row])

    def test_unmatched_country_stops_integration(self) -> None:
        row = {"Country": "Atlantis", "City": "X", "Month": 1}
        with self.assertRaisesRegex(ValueError, "Atlantis"):
            pipeline.integrate_country_reference([row], RESULTS.reference_by_country)


class PreparedDatasetTests(unittest.TestCase):
    def test_no_records_are_lost(self) -> None:
        self.assertEqual(len(RESULTS.cleaned_rows), 500)
        ids = [r["Record_ID"] for r in RESULTS.cleaned_rows]
        self.assertEqual(len(set(ids)), 500)

    def test_every_original_value_survives(self) -> None:
        for raw, clean in zip(RAW_ROWS, RESULTS.cleaned_rows):
            for raw_name, raw_value in raw.items():
                value = clean[pipeline.COLUMN_RENAMES.get(raw_name, raw_name)]
                if isinstance(value, str):
                    self.assertEqual(value, raw_value)
                else:
                    self.assertEqual(value, float(raw_value))

    def test_revenue_columns_carry_their_unit(self) -> None:
        columns = set(RESULTS.cleaned_rows[0])
        self.assertIn("Tourism_Revenue_USD_000", columns)
        self.assertNotIn("Tourism_Revenue_USD", columns)
        self.assertIn("Eco_Tourism_Revenue_USD_000", columns)

    def test_integration_matches_all_rows_with_name_crosswalk(self) -> None:
        rows = RESULTS.cleaned_rows
        self.assertTrue(all(r["UN_Region"] and r["ISO3"] for r in rows))
        self.assertEqual({r["ISO3"] for r in rows if r["Country"] == "Turkey"}, {"TUR"})
        self.assertEqual({r["Hemisphere"] for r in rows if r["Country"] == "Brazil"}, {"Southern"})

    def test_outlier_counts_and_retention(self) -> None:
        summary = {r["Variable"]: r for r in RESULTS.outlier_summary}
        eco = summary["Eco_Tourism_Revenue_USD_000"]
        carbon = summary["Carbon_Footprint_kg"]
        self.assertEqual((eco["IQR_Flagged"], eco["SD3_Flagged"]), (21, 8))
        self.assertEqual((carbon["IQR_Flagged"], carbon["SD3_Flagged"]), (3, 1))
        self.assertEqual(summary["Number_of_Tourists"]["IQR_Flagged"], 0)
        self.assertEqual(sum(r["Outlier_Eco_Revenue_IQR"] for r in RESULTS.cleaned_rows), 21)

    def test_flagged_values_vanish_once_expressed_per_unit(self) -> None:
        summary = {r["Variable"]: r for r in RESULTS.outlier_summary}
        self.assertEqual(summary["Eco_Revenue_Share_Pct"]["IQR_Flagged"], 0)
        self.assertEqual(summary["Carbon_kg_per_Tourist"]["IQR_Flagged"], 0)

    def test_unrated_is_not_given_a_star_level(self) -> None:
        unrated = [r for r in RESULTS.cleaned_rows if r["Hotel_Rating"] == "Unrated"]
        self.assertEqual(len(unrated), 82)
        self.assertTrue(all(r["Hotel_Star_Level"] is None for r in unrated))
        five = [r for r in RESULTS.cleaned_rows if r["Hotel_Rating"] == "5-star"]
        self.assertTrue(all(r["Hotel_Star_Level"] == 5 for r in five))

    def test_demand_tiers_hold_equal_record_counts(self) -> None:
        codes = [r["Demand_Tier_Code"] for r in RESULTS.cleaned_rows]
        self.assertEqual(bin_counts(codes), [125, 125, 125, 125])

    def test_season_uses_the_integrated_hemisphere(self) -> None:
        for row in RESULTS.cleaned_rows:
            self.assertEqual(row["Season"], methods.season_for(row["Month"], row["Hemisphere"]))

    def test_derived_ratios(self) -> None:
        row = RESULTS.cleaned_rows[0]
        self.assertAlmostEqual(row["Spend_per_Night_USD"], 1325.46 / 12.4, places=3)
        self.assertAlmostEqual(row["Tourists_per_Hotel"], 171958 / 70, places=3)


class ModelReadyTests(unittest.TestCase):
    def test_columns_derived_from_the_target_are_excluded(self) -> None:
        self.assertFalse(set(RESULTS.model_rows[0]) & LEAKAGE_COLUMNS)

    def test_no_blank_values(self) -> None:
        self.assertFalse([k for r in RESULTS.model_rows for k, v in r.items() if v in ("", None)])

    def test_target_is_left_unscaled(self) -> None:
        self.assertEqual(RESULTS.model_rows[0]["Number_of_Tourists"], 171958)

    def test_scaled_predictors_span_zero_to_one(self) -> None:
        for column in pipeline.SCALED_PREDICTORS:
            values = [r[f"{column}_MinMax"] for r in RESULTS.model_rows]
            self.assertEqual((min(values), max(values)), (0, 1), column)

    def test_each_one_hot_group_has_exactly_one_active_column(self) -> None:
        first = RESULTS.model_rows[0]
        for prefix in pipeline.ONE_HOT_SOURCES.values():
            group = [c for c in first if c.startswith(f"{prefix}_")]
            self.assertGreater(len(group), 1, prefix)
            self.assertTrue(all(sum(r[c] for c in group) == 1 for r in RESULTS.model_rows), prefix)

    def test_city_is_not_one_hot_encoded(self) -> None:
        self.assertFalse([c for c in RESULTS.model_rows[0] if c.startswith("City_")])

    def test_both_scaling_methods_are_reported_with_expected_properties(self) -> None:
        for row in RESULTS.scaling_parameters:
            self.assertEqual((row["MinMax_Min"], row["MinMax_Max"]), (0, 1))
            self.assertAlmostEqual(row["Z_Mean"], 0, places=5)
            self.assertAlmostEqual(row["Z_Sample_SD"], 1, places=5)


class AggregationTests(unittest.TestCase):
    def test_summaries_reconcile_to_record_totals(self) -> None:
        for table in (RESULTS.country_year, RESULTS.year_month):
            self.assertEqual(sum(r["Records"] for r in table), 500)
            self.assertEqual(sum(r["Observed_Arrivals_Sum"] for r in table), 62631942)

    def test_grain_of_each_summary(self) -> None:
        self.assertEqual(len(RESULTS.country_year), 100)
        self.assertEqual(len(RESULTS.year_month), 60)

    def test_weighted_spending_weights_by_tourists(self) -> None:
        rows = [
            {"Number_of_Tourists": 10, "Tourist_Spending_USD": 100.0,
             "Tourism_Revenue_USD_000": 1.0, "Hotel_Occupancy_Rate": 50.0,
             "Number_of_Hotels": 10, "Average_Room_Price_USD": 100.0},
            {"Number_of_Tourists": 90, "Tourist_Spending_USD": 200.0,
             "Tourism_Revenue_USD_000": 18.0, "Hotel_Occupancy_Rate": 70.0,
             "Number_of_Hotels": 30, "Average_Room_Price_USD": 200.0},
        ]
        result = pipeline.summarise_group(rows)
        self.assertEqual(result["Tourist_Weighted_Spending_USD"], 190)
        self.assertEqual(result["Mean_Occupancy_Percent"], 60)
        self.assertEqual(result["Mean_Hotels_Per_Record"], 20)


class FinalValidationTests(unittest.TestCase):
    def test_all_seven_checks_pass_on_the_prepared_data(self) -> None:
        self.assertEqual(len(RESULTS.final_validation), 7)
        self.assertEqual({r["Result"] for r in RESULTS.final_validation}, {"Pass"})

    def test_a_lost_record_fails_validation(self) -> None:
        results = audit.build_final_validation(
            RAW_ROWS, RESULTS.cleaned_rows[:-1], RESULTS.country_year, RESULTS.year_month)
        by_check = {r["Check"]: r["Result"] for r in results}
        self.assertEqual(by_check["No accidental loss of important observations"], "Fail")

    def test_a_changed_value_fails_validation(self) -> None:
        altered = [{**RESULTS.cleaned_rows[0], "Number_of_Hotels": 1}, *RESULTS.cleaned_rows[1:]]
        results = audit.build_final_validation(
            RAW_ROWS, altered, RESULTS.country_year, RESULTS.year_month)
        by_check = {r["Check"]: r["Result"] for r in results}
        self.assertEqual(by_check["No accidental loss of important observations"], "Fail")

    def test_a_mismatched_date_fails_validation(self) -> None:
        altered = [{**RESULTS.cleaned_rows[0], "Period_Date": "2021-02-01"},
                   *RESULTS.cleaned_rows[1:]]
        results = audit.build_final_validation(
            RAW_ROWS, altered, RESULTS.country_year, RESULTS.year_month)
        by_check = {r["Check"]: r["Result"] for r in results}
        self.assertEqual(by_check["Valid date and numerical formats"], "Fail")


class ReportingTests(unittest.TestCase):
    def test_before_after_table_shows_row_and_duplicate_counts(self) -> None:
        table = {r["Metric"]: r for r in RESULTS.before_after}
        self.assertEqual((table["Rows"]["Before"], table["Rows"]["After"]), (500, 500))
        self.assertEqual(table["Exact duplicate rows"]["After"], 0)
        self.assertEqual(table["Columns"]["Before"], 23)

    def test_every_cleaned_column_is_documented(self) -> None:
        documented = {r["Column"] for r in RESULTS.data_dictionary}
        self.assertEqual(set(RESULTS.cleaned_rows[0]) - documented, set())

    def test_dictionary_shows_what_reached_the_model_file(self) -> None:
        by_column = {r["Column"]: r for r in RESULTS.data_dictionary}
        self.assertEqual(by_column["City"]["In_Model_Ready"], "No")
        self.assertEqual(by_column["Country"]["In_Model_Ready"], "Yes")
        self.assertEqual(by_column["Number_of_Hotels"]["In_Model_Ready"], "Yes")
        self.assertEqual(by_column["Number_of_Tourists"]["In_Model_Ready"], "Yes")

    def test_added_columns_state_a_measurement_scale(self) -> None:
        by_column = {r["Column"]: r for r in RESULTS.data_dictionary}
        self.assertEqual(by_column["Hotel_Star_Level"]["Measurement_Scale"], "Ordinal")
        self.assertEqual(by_column["Tourists_per_Hotel"]["Measurement_Scale"], "Ratio")

    def test_equal_width_summary_reports_true_edges_and_width(self) -> None:
        occupancy = [r for r in RESULTS.binning_summary if r["Method"] == "Equal-width"]
        self.assertEqual({r["Bin_Width"] for r in occupancy}, {12.45})
        self.assertEqual(occupancy[0]["Upper_Bound"], 52.45)

    def test_equal_frequency_width_is_the_span_of_each_bin(self) -> None:
        tiers = [r for r in RESULTS.binning_summary if r["Method"] == "Equal-frequency"]
        self.assertEqual(tiers[0]["Bin_Width"], tiers[0]["Upper_Bound"] - tiers[0]["Lower_Bound"])

    def test_case_variants_are_counted(self) -> None:
        rows = [{"Country": "Italy"}, {"Country": "ITALY"}, {"Country": "Spain"}]
        self.assertEqual(audit.count_case_variants(rows, ("Country",)), 1)

    def test_leakage_columns_are_marked_ineligible(self) -> None:
        by_column = {r["Column"]: r for r in RESULTS.data_dictionary}
        for column in LEAKAGE_COLUMNS:
            self.assertEqual(by_column[column]["Phase6_Predictor_of_Arrivals"], "No", column)


RAW_ROWS = pipeline.read_csv_rows(pipeline.RAW)
RESULTS = pipeline.build_phase3(pipeline.RAW, pipeline.M49)


if __name__ == "__main__":
    unittest.main()
