"""Evidence and explicitly hypothetical decision scenarios for Phase 7.

Python 3.10+, standard library only. Run from any working directory.
No model fitting, changes to prior phases, or external business actions.
"""

import csv
import hashlib
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/tourism_cleaned.csv"
OUT = ROOT / "outputs/phase7"
ASSUMPTIONS = {
    "hotel_rooms": 100,
    "days": 30,
    "adr_usd": 120,
    "variable_cost_per_room_night_usd": 35,
    "fixed_monthly_cost_usd": 150000,
    "targeted_pilot_cost_usd": 6000,
    "discount_campaign_cost_usd": 1500,
    "discount_fraction": 0.10,
    "pilot_occupancy_uplifts_pp": [1, 4, 7],
    "discount_occupancy_uplifts_pp": [5, 10, 15],
    "future_demand_room_nights": [1800, 2400, 3300],
    "illustrative_probabilities": [0.30, 0.50, 0.20],
    "partner_extra_capacity_room_nights": 450,
    "partner_net_contribution_usd": 50,
    "partner_monthly_retainer_usd": 2000,
    "expansion_extra_rooms": 20,
    "expansion_extra_fixed_and_capital_charge_usd": 20000,
    "housekeeping_minutes_per_occupied_room": 30,
    "housekeeping_productive_hours_per_shift": 6,
}


def load_rows():
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("Phase 3 prepared input is empty.")
    numeric = ["Number_of_Tourists", "Tourist_Spending_USD", "Hotel_Occupancy_Rate",
               "Tourism_Revenue_USD_000", "Number_of_Hotels", "Average_Length_of_Stay"]
    for row in rows:
        for c in numeric:
            row[c] = float(row[c])
            if not math.isfinite(row[c]):
                raise ValueError(f"Nonfinite {c} in prepared input.")
        if any(row[c] <= 0 for c in numeric if c != "Hotel_Occupancy_Rate"):
            raise ValueError("Positive ratio measures required.")
        if not 0 <= row["Hotel_Occupancy_Rate"] <= 100:
            raise ValueError("Occupancy outside 0–100%.")
        expected = row["Number_of_Tourists"] * row["Tourist_Spending_USD"] / 1000
        if abs(row["Tourism_Revenue_USD_000"] - expected) > 0.011:
            raise ValueError("Recheck revenue scale: identity changed.")
    if len({r["Record_ID"] for r in rows}) != len(rows):
        raise ValueError("Prepared Record_ID must be unique.")
    return rows


def group(rows, key):
    result = defaultdict(list)
    for row in rows:
        result[row[key]].append(row)
    return result


def weighted_spend(rows):
    return sum(r["Number_of_Tourists"] * r["Tourist_Spending_USD"] for r in rows) / sum(
        r["Number_of_Tourists"] for r in rows)


def evidence(rows):
    arrivals = [r["Number_of_Tourists"] for r in rows]
    spend = [r["Tourist_Spending_USD"] for r in rows]
    monthly = {month: st.mean(r["Number_of_Tourists"] for r in subset)
               for month, subset in group(rows, "Month").items()}
    result = {
        "records": len(rows), "countries": len(group(rows, "Country")),
        "cities": len(group(rows, "City")), "mean_arrivals": st.mean(arrivals),
        "arrival_cv_percent": 100 * st.stdev(arrivals) / st.mean(arrivals),
        "spend_cv_percent": 100 * st.stdev(spend) / st.mean(spend),
        "weighted_spend_usd": weighted_spend(rows),
        "mean_occupancy_percent": st.mean(r["Hotel_Occupancy_Rate"] for r in rows),
        "below_60_occupancy_records": sum(r["Hotel_Occupancy_Rate"] < 60 for r in rows),
        "repeated_key_records": sum(int(r["Flag_Repeated_City_Month"]) for r in rows),
        "room_spend_flag_records": sum(int(r["Flag_Room_Cost_Exceeds_Spend"]) for r in rows),
        "january_mean_arrivals": monthly["1"], "august_mean_arrivals": monthly["8"],
    }
    for purpose in ["Business", "Family Visit"]:
        subset = group(rows, "Purpose_of_Visit")[purpose]
        result[purpose + "_weighted_spend_usd"] = weighted_spend(subset)
        result[purpose + "_records"] = len(subset)
    result["business_vs_family_gap_percent"] = 100 * (
        result["Business_weighted_spend_usd"] / result["Family Visit_weighted_spend_usd"] - 1)
    for region in ["Americas", "Europe"]:
        subset = [r for r in rows if r["Purpose_of_Visit"] == "Business" and r["UN_Region"] == region]
        result[region + "_business_spend_usd"] = weighted_spend(subset)
        result[region + "_business_records"] = len(subset)
    result["country_record_min"] = min(map(len, group(rows, "Country").values()))
    result["country_record_max"] = max(map(len, group(rows, "Country").values()))
    return result


def hotel_profit(capacity, occupancy, adr, variable_cost, fixed_cost, action_cost=0):
    """Monthly operating contribution after stated fixed/action costs; before tax."""
    if capacity <= 0 or not 0 <= occupancy <= 1:
        raise ValueError("Positive capacity and occupancy between 0 and 1 required.")
    if min(adr, variable_cost, fixed_cost, action_cost) < 0:
        raise ValueError("Financial inputs cannot be negative.")
    return capacity * occupancy * (adr - variable_cost) - fixed_cost - action_cost


def required_occupancy(base_occupancy, old_adr, new_adr, variable_cost, capacity, action_cost=0):
    """Occupancy needed to retain baseline profit; may exceed feasible 100%."""
    if not 0 <= base_occupancy <= 1 or capacity <= 0 or action_cost < 0:
        raise ValueError("Invalid base occupancy, capacity or action cost.")
    if old_adr < variable_cost or new_adr <= variable_cost:
        raise ValueError("A positive new room contribution is required.")
    return (base_occupancy * (old_adr - variable_cost) + action_cost / capacity) / (new_adr - variable_cost)


def pricing_scenarios(base_occupancy, a=ASSUMPTIONS):
    cap = a["hotel_rooms"] * a["days"]
    baseline = hotel_profit(cap, base_occupancy, a["adr_usd"],
                            a["variable_cost_per_room_night_usd"], a["fixed_monthly_cost_usd"])
    result = []
    for action, uplifts, price, cost in [
        ("Targeted pilot", a["pilot_occupancy_uplifts_pp"], a["adr_usd"], a["targeted_pilot_cost_usd"]),
        ("Blanket discount", a["discount_occupancy_uplifts_pp"],
         a["adr_usd"] * (1 - a["discount_fraction"]), a["discount_campaign_cost_usd"]),
    ]:
        for state, uplift in zip(["Conservative", "Central", "Optimistic"], uplifts):
            occupancy = base_occupancy + uplift / 100
            if occupancy > 1:
                raise ValueError("Scenario exceeds room capacity; revise the assumed uplift.")
            profit = hotel_profit(cap, occupancy, price, a["variable_cost_per_room_night_usd"],
                                  a["fixed_monthly_cost_usd"], cost)
            result.append(dict(Action=action, Scenario=state, Assumed_Uplift_PP=uplift,
                               Assumed_Occupancy_Percent=100 * occupancy, Assumed_ADR_USD=price,
                               Action_Cost_USD=cost, Monthly_Profit_USD=profit,
                               Incremental_Profit_USD=profit - baseline))
    return baseline, result


def capacity_payoffs(a=ASSUMPTIONS):
    """Incremental payoff vs keeping 100 rooms, across assumed demand states."""
    cap = a["hotel_rooms"] * a["days"]
    margin = a["adr_usd"] - a["variable_cost_per_room_night_usd"]
    result = []
    for action in ["Keep capacity", "Contract overflow", "Expand by 20 rooms"]:
        for state, demand, probability in zip(["Low", "Central", "High"],
                a["future_demand_room_nights"], a["illustrative_probabilities"]):
            excess = max(0, demand - cap)
            payoff = 0
            if action == "Contract overflow":
                payoff = min(excess, a["partner_extra_capacity_room_nights"]) * a[
                    "partner_net_contribution_usd"] - a["partner_monthly_retainer_usd"]
            elif action == "Expand by 20 rooms":
                payoff = min(excess, a["expansion_extra_rooms"] * a["days"]) * margin - a[
                    "expansion_extra_fixed_and_capital_charge_usd"]
            result.append(dict(Action=action, Demand_State=state,
                               Assumed_Demand_Room_Nights=demand, Illustrative_Probability=probability,
                               Incremental_Monthly_Payoff_USD=payoff))
    return result


def decision_summary(payoffs):
    states = group(payoffs, "Demand_State")
    probabilities = {key: subset[0]["Illustrative_Probability"] for key, subset in states.items()}
    if any(not math.isfinite(p) or p < 0 for p in probabilities.values()) or not math.isclose(
            sum(probabilities.values()), 1, abs_tol=1e-12):
        raise ValueError("Decision probabilities must be nonnegative and sum to 1.")
    best = {key: max(r["Incremental_Monthly_Payoff_USD"] for r in subset)
            for key, subset in states.items()}
    result = []
    for action, subset in group(payoffs, "Action").items():
        result.append(dict(Action=action,
            Expected_Monetary_Value_USD=sum(r["Incremental_Monthly_Payoff_USD"] *
                                           probabilities[r["Demand_State"]] for r in subset),
            Worst_Case_Payoff_USD=min(r["Incremental_Monthly_Payoff_USD"] for r in subset),
            Maximum_Regret_USD=max(best[r["Demand_State"]] - r["Incremental_Monthly_Payoff_USD"]
                                  for r in subset)))
    ev_perfect = sum(probabilities[s] * best[s] for s in states)
    evpi = ev_perfect - max(r["Expected_Monetary_Value_USD"] for r in result)
    return result, evpi


def staffing(occupancy, rooms=100, minutes=30, productive_hours=6):
    if not 0 <= occupancy <= 1 or min(rooms, minutes, productive_hours) <= 0:
        raise ValueError("Invalid staffing inputs.")
    hours = rooms * occupancy * minutes / 60
    return hours, math.ceil(hours / productive_hours)


def model_review():
    nb = json.loads((ROOT / "notebooks/06_Logistic_Regression.ipynb").read_text(encoding="utf-8"))
    cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    code = "\n".join("".join(c["source"]) for c in cells)
    return dict(notebook="notebooks/06_Logistic_Regression.ipynb",
                target="High_Satisfaction (score above full-data median)" if "High_Satisfaction" in code else "Review required",
                code_cells=len(cells), cells_with_saved_outputs=sum(bool(c.get("outputs")) for c in cells),
                performance_verified_by_phase7=False,
                decision_use="Do not use as an arrivals forecast or causal treatment rule")


def write_csv(name, records):
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    rows = load_rows()
    metrics = evidence(rows)
    base_occ = metrics["mean_occupancy_percent"] / 100
    baseline, scenarios = pricing_scenarios(base_occ)
    payoffs = capacity_payoffs()
    decisions, evpi = decision_summary(payoffs)
    review = model_review()
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv("evidence_metrics.csv", [dict(Metric=k, Value=v) for k, v in metrics.items()])
    write_csv("pricing_scenarios.csv", scenarios)
    write_csv("capacity_payoffs.csv", payoffs)
    write_csv("decision_rules.csv", decisions)
    staffing_rows = []
    for label, occupancy in [("Illustrative low", 0.5), ("Sample-mean reference", base_occ),
                              ("Illustrative high", 0.8)]:
        hours, people = staffing(
            occupancy, rooms=ASSUMPTIONS["hotel_rooms"],
            minutes=ASSUMPTIONS["housekeeping_minutes_per_occupied_room"],
            productive_hours=ASSUMPTIONS["housekeeping_productive_hours_per_shift"])
        staffing_rows.append(dict(Scenario=label, Assumed_Occupancy_Percent=occupancy * 100,
                                  Housekeeping_Hours_Per_Day=hours, Attendants_Per_Shift=people))
    write_csv("staffing_scenarios.csv", staffing_rows)
    inputs = dict(assumptions=ASSUMPTIONS,
                  empirical_reference_only={"mean_record_occupancy_percent": metrics["mean_occupancy_percent"]},
                  scenario_status="Illustrative assumptions; no fitted uplift, estimated probabilities or financial forecast")
    (OUT / "scenario_assumptions.json").write_text(json.dumps(inputs, indent=2) + "\n", encoding="utf-8")
    audit = dict(source=str(SOURCE.relative_to(ROOT).as_posix()),
                 source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                 rows=len(rows), columns=len(rows[0]), model_review=review)
    (OUT / "source_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    # Keep report generation separate from the decision calculations.
    from phase7_report import render_report
    render_report(ROOT, metrics, baseline, scenarios, payoffs, decisions, evpi, staffing_rows)
    print(f"Phase 7 complete: {len(rows)} prepared records; report and seven calculation/audit files written.")


if __name__ == "__main__":
    main()
