"""Checks against Module 4 worked examples and the actual tourism record counts."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
import phase7_prescriptive_analysis as p7


class AssociationRuleTests(unittest.TestCase):
    def test_bread_eggs_matches_module4_pages_21_and_24(self):
        # Ten transactions: Bread in 8, Eggs in 7, both in 6.
        result = p7.rule_measures(10, 8, 7, 6)
        self.assertEqual(result["Support"], .6)
        self.assertEqual(result["Confidence"], .75)
        self.assertAlmostEqual(result["Lift"], 1.0714285714)
        self.assertTrue(p7.is_strong(result, minimum_support=.40, minimum_confidence=.70))

    def test_confidence_is_directional_but_support_and_lift_are_symmetric(self):
        forward = p7.rule_measures(10, 8, 7, 6)
        reverse = p7.rule_measures(10, 7, 8, 6)
        self.assertNotEqual(forward["Confidence"], reverse["Confidence"])
        self.assertEqual(forward["Support"], reverse["Support"])
        self.assertAlmostEqual(forward["Lift"], reverse["Lift"])

    def test_high_confidence_can_have_lift_below_one(self):
        # Module 4 p. 25: Bread => Milk is strong, yet has negative association.
        result = p7.rule_measures(10, 8, 8, 6)
        self.assertTrue(p7.is_strong(result, .40, .70))
        self.assertEqual(result["Confidence"], .75)
        self.assertAlmostEqual(result["Lift"], .9375)

    def test_independent_and_absent_outcomes(self):
        self.assertEqual(p7.rule_measures(100, 20, 50, 10)["Lift"], 1)
        self.assertIsNone(p7.rule_measures(100, 0, 50, 0)["Confidence"])
        self.assertIsNone(p7.rule_measures(100, 20, 0, 0)["Lift"])

    def test_impossible_count_tables_are_rejected(self):
        for values in [(0, 0, 0, 0), (10, 8, 8, 2), (10, 2, 4, 3),
                       (10, -1, 4, 0), (10, 11, 4, 4), (10, 2.5, 4, 1)]:
            with self.assertRaises(ValueError):
                p7.rule_measures(*values)

    def test_weak_confidence_does_not_make_a_strong_rule(self):
        business = p7.rule_measures(500, 71, 235, 39)
        self.assertGreater(business["Lift"], 1)
        self.assertGreaterEqual(business["Support"], .05)
        self.assertFalse(p7.is_strong(business))

    def test_outcome_cutoffs_include_boundary_values(self):
        row = dict(Purpose_of_Visit="Business", UN_Region="Asia", Hotel_Rating="4-star",
                   Season="Spring", Tourist_Spending_USD=3000, Hotel_Occupancy_Rate=70,
                   Tourist_Satisfaction_Score=8, Number_of_Tourists=150000)
        rules = p7.calculate_rules([row])
        self.assertEqual(len(rules), 16)
        self.assertTrue(all(r["Joint_Count"] == 1 for r in rules))

    def test_all_rules_and_counts_reconcile_on_prepared_input(self):
        rows = p7.load_rows()
        rules = p7.calculate_rules(rows)
        m = p7.evidence(rows, rules)
        self.assertEqual(m["records"], 500)
        self.assertEqual(m["rules_checked"], 88)
        self.assertEqual(m["frequent_pairs"], 74)
        self.assertEqual(m["strong_rules"], 0)
        self.assertEqual(m["below_60_occupancy_records"], 207)
        business = next(r for r in rules if r["Antecedent_Level"] == "Business"
                        and r["Outcome"] == "High spending")
        self.assertEqual(business["Joint_Count"], 39)
        self.assertEqual(business["Outcome_Count"], 235)
        self.assertAlmostEqual(business["Lift"], 1.1687144141)
        self.assertTrue(any(r["Lift"] < 1 for r in rules))


if __name__ == "__main__":
    unittest.main()
