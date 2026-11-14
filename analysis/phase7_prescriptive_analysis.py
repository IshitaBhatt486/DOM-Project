"""Simple Phase 7 using the course's support, confidence and lift definitions.

Run: python analysis/phase7_prescriptive_analysis.py
Python 3.10+; standard library only. One prepared record is one observation.
"""

import csv
import hashlib
import json
import math
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/tourism_cleaned.csv"
OUT = ROOT / "outputs/phase7"
ANTECEDENTS = ["Purpose_of_Visit", "UN_Region", "Hotel_Rating", "Season"]
# Simple project definitions, not publisher labels or industry standards.
OUTCOMES = {
    "High spending": ("Tourist_Spending_USD", 3000, "USD per tourist"),
    "High occupancy": ("Hotel_Occupancy_Rate", 70, "percent"),
    "High satisfaction": ("Tourist_Satisfaction_Score", 8, "score"),
    "High arrivals": ("Number_of_Tourists", 150000, "arrivals per record"),
}
# The course's worked example uses support 40%, confidence 70%.
# Support is adjusted to 5% for these smaller tourism subgroups; confidence stays 70%.
FILTER = {"minimum_support": .05, "minimum_confidence": .70}
DISPLAY_RULES = [
    ("Purpose_of_Visit", "Business", "High spending"),
    ("Season", "Spring", "High spending"),
    ("Purpose_of_Visit", "Family Visit", "High spending"),
    ("Purpose_of_Visit", "Family Visit", "High occupancy"),
    ("Hotel_Rating", "4-star", "High satisfaction"),
    ("Hotel_Rating", "5-star", "High satisfaction"),
]


def load_rows():
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("Prepared dataset is empty.")
    for row in rows:
        if any(not row.get(c) for c in ANTECEDENTS + ["Record_ID"]):
            raise ValueError("A rule category or Record_ID is missing.")
        for col in {spec[0] for spec in OUTCOMES.values()}:
            row[col] = float(row[col])
            if not math.isfinite(row[col]) or row[col] < 0:
                raise ValueError(f"Invalid {col}.")
        if not 0 <= row["Hotel_Occupancy_Rate"] <= 100:
            raise ValueError("Occupancy outside 0–100%.")
        if not 1 <= row["Tourist_Satisfaction_Score"] <= 10:
            raise ValueError("Satisfaction score outside 1–10.")
    if len({r["Record_ID"] for r in rows}) != len(rows):
        raise ValueError("Prepared Record_ID must be unique.")
    return rows


def rule_measures(n, antecedent_count, outcome_count, joint_count):
    """Support=P(A and B); confidence=P(B|A); lift=P(B|A)/P(B)."""
    if not (isinstance(n, int) and n > 0 and all(isinstance(v, int) for v in
            [antecedent_count, outcome_count, joint_count]) and
            0 <= joint_count <= min(antecedent_count, outcome_count) and
            max(antecedent_count, outcome_count) <= n and
            antecedent_count + outcome_count - joint_count <= n):
        raise ValueError("Counts do not describe a valid contingency table.")
    confidence = joint_count / antecedent_count if antecedent_count else None
    baseline = outcome_count / n
    return dict(Support=joint_count / n, Confidence=confidence, Outcome_Baseline=baseline,
                Lift=confidence / baseline if confidence is not None and baseline else None)


def is_strong(measures, minimum_support=.05, minimum_confidence=.70):
    """As taught: strong means clearing support AND confidence; assess lift separately."""
    return (measures["Confidence"] is not None and measures["Support"] >= minimum_support
            and measures["Confidence"] >= minimum_confidence)


def calculate_rules(rows):
    """Count all single-category => single-outcome rules, without claiming full Apriori."""
    rules = []
    for column in ANTECEDENTS:
        for level in sorted({r[column] for r in rows}):
            subset = [r for r in rows if r[column] == level]
            for outcome, (numeric_col, cutoff, _) in OUTCOMES.items():
                n_b = sum(r[numeric_col] >= cutoff for r in rows)
                n_ab = sum(r[numeric_col] >= cutoff for r in subset)
                measures = rule_measures(len(rows), len(subset), n_b, n_ab)
                rules.append(dict(Antecedent_Column=column, Antecedent_Level=level,
                                  Outcome=outcome, Total_Records=len(rows),
                                  Antecedent_Count=len(subset), Outcome_Count=n_b,
                                  Joint_Count=n_ab, **measures,
                                  Frequent_Pair="Yes" if measures["Support"] >= FILTER["minimum_support"] else "No",
                                  Strong_Rule="Yes" if is_strong(measures, **FILTER) else "No"))
    return rules


def evidence(rows, rules):
    return dict(records=len(rows),
                mean_arrivals=st.mean(r["Number_of_Tourists"] for r in rows),
                mean_spending_usd=st.mean(r["Tourist_Spending_USD"] for r in rows),
                mean_occupancy_percent=st.mean(r["Hotel_Occupancy_Rate"] for r in rows),
                below_60_occupancy_records=sum(r["Hotel_Occupancy_Rate"] < 60 for r in rows),
                rules_checked=len(rules),
                frequent_pairs=sum(r["Frequent_Pair"] == "Yes" for r in rules),
                strong_rules=sum(r["Strong_Rule"] == "Yes" for r in rules))


def write_csv(name, records):
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    rows = load_rows()
    rules = calculate_rules(rows)
    metrics = evidence(rows, rules)
    by_key = {(r["Antecedent_Column"], r["Antecedent_Level"], r["Outcome"]): r for r in rules}
    selected = [by_key[key] for key in DISPLAY_RULES]
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv("association_rules.csv", rules)
    write_csv("displayed_rules.csv", selected)
    write_csv("evidence_metrics.csv", [dict(Metric=k, Value=v) for k, v in metrics.items()])
    definitions = dict(
        unit_of_analysis="One prepared destination-period record, not one individual tourist",
        outcomes={name: dict(column=col, operator=">=", cutoff=cutoff, unit=unit)
                  for name, (col, cutoff, unit) in OUTCOMES.items()},
        antecedent_columns=ANTECEDENTS, project_thresholds=FILTER,
        course_example_thresholds=dict(minimum_support=.40, minimum_confidence=.70),
        threshold_basis="Project support 5% for small subgroups; confidence 70% follows Module 4 worked example",
        strength_definition="Support and confidence thresholds; lift assessed separately",
        search_scope="All single-category to single-outcome combinations; direct pair counting, not full Apriori",
    )
    (OUT / "rule_definitions.json").write_text(json.dumps(definitions, indent=2) + "\n", encoding="utf-8")
    audit = dict(source=SOURCE.relative_to(ROOT).as_posix(),
                 source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                 rows=len(rows), rules_checked=len(rules), strong_rules=metrics["strong_rules"],
                 validation="Exploratory in-sample associations; no statistical significance or out-of-sample claim")
    (OUT / "source_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    from phase7_report import render_report
    render_report(ROOT, metrics, selected)
    print(f"Phase 7: {len(rows)} records, {len(rules)} rules checked, {metrics['strong_rules']} strong rules.")


if __name__ == "__main__":
    main()
