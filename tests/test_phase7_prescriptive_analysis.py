"""Verify economic decisions, sensitivity boundaries and prepared-data evidence."""

import copy
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
import phase7_prescriptive_analysis as p7


class PrescriptiveAnalysisTests(unittest.TestCase):
    def test_contribution_uses_room_nights_and_all_relevant_costs(self):
        # 3,000 available nights, 1,800 sold, USD 85 contribution, less fixed/campaign.
        self.assertEqual(p7.hotel_profit(3000, .6, 120, 35, 150000), 3000)
        self.assertEqual(p7.hotel_profit(3000, .6, 120, 35, 150000, 6000), -3000)

    def test_discount_break_even_preserves_baseline_profit(self):
        required = p7.required_occupancy(.6, 120, 108, 35, 3000, 1500)
        self.assertAlmostEqual(required, 51.5 / 73)
        self.assertAlmostEqual(p7.hotel_profit(3000, required, 108, 35, 150000, 1500),
                               p7.hotel_profit(3000, .6, 120, 35, 150000))

    def test_impossible_break_even_is_not_capped_or_presented_as_feasible(self):
        required = p7.required_occupancy(.95, 120, 60, 35, 3000, 1500)
        self.assertGreater(required, 1)

    def test_invalid_capacity_or_margin_rejected(self):
        with self.assertRaises(ValueError):
            p7.hotel_profit(3000, 1.01, 120, 35, 150000)
        with self.assertRaises(ValueError):
            p7.required_occupancy(.6, 120, 35, 35, 3000)
        with self.assertRaises(ValueError):
            p7.pricing_scenarios(.95)

    def test_campaign_profit_accounts_for_existing_guests_discount(self):
        baseline, cases = p7.pricing_scenarios(.648408)
        self.assertAlmostEqual(baseline, 15344.04)
        pilot = next(r for r in cases if r["Action"] == "Targeted pilot" and r["Scenario"] == "Central")
        discount = next(r for r in cases if r["Action"] == "Blanket discount" and r["Scenario"] == "Central")
        self.assertAlmostEqual(pilot["Incremental_Profit_USD"], 4200)
        self.assertAlmostEqual(discount["Incremental_Profit_USD"], -2942.688)

    def test_overflow_serves_only_unmet_demand_and_respects_partner_limit(self):
        a = copy.deepcopy(p7.ASSUMPTIONS)
        a["future_demand_room_nights"] = [1800, 3000, 4000]
        rows = p7.capacity_payoffs(a)
        partner = [r["Incremental_Monthly_Payoff_USD"] for r in rows if r["Action"] == "Contract overflow"]
        self.assertEqual(partner, [-2000, -2000, 20500])  # 450 partner nights, not 1,000.

    def test_emv_maximin_regret_and_value_of_information(self):
        result, evpi = p7.decision_summary(p7.capacity_payoffs())
        by_action = {r["Action"]: r for r in result}
        self.assertEqual(by_action["Contract overflow"]["Expected_Monetary_Value_USD"], 1000)
        self.assertEqual(by_action["Expand by 20 rooms"]["Expected_Monetary_Value_USD"], -14900)
        self.assertEqual(by_action["Keep capacity"]["Maximum_Regret_USD"], 13000)
        self.assertEqual(max(result, key=lambda r: r["Worst_Case_Payoff_USD"])["Action"], "Keep capacity")
        self.assertEqual(min(result, key=lambda r: r["Maximum_Regret_USD"])["Action"], "Contract overflow")
        self.assertEqual(evpi, 1600)

    def test_invalid_probabilities_rejected(self):
        for bad_probability in [.4, -.2, math.nan]:
            rows = p7.capacity_payoffs()
            for row in rows:
                if row["Demand_State"] == "Low":
                    row["Illustrative_Probability"] = bad_probability
            with self.assertRaises(ValueError):
                p7.decision_summary(rows)

    def test_integer_staffing_and_sample_evidence(self):
        hours, people = p7.staffing(.648408)
        self.assertAlmostEqual(hours, 32.4204)
        self.assertEqual(people, 6)
        self.assertEqual(p7.staffing(.8)[1], 7)
        metrics = p7.evidence(p7.load_rows())
        self.assertEqual(metrics["records"], 500)
        self.assertEqual(metrics["below_60_occupancy_records"], 207)
        self.assertEqual(metrics["repeated_key_records"], 61)
        self.assertEqual(metrics["room_spend_flag_records"], 83)
        self.assertAlmostEqual(metrics["weighted_spend_usd"], 2792.0091973)


if __name__ == "__main__":
    unittest.main()
