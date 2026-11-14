"""Generate a short Phase 7 report aligned with the supplied course modules."""


def render_report(root, m, selected):
    def find(level, outcome):
        return next(r for r in selected if r["Antecedent_Level"] == level and r["Outcome"] == outcome)

    b = find("Business", "High spending")
    spring = find("Spring", "High spending")
    family = find("Family Visit", "High occupancy")
    four = find("4-star", "High satisfaction")
    five = find("5-star", "High satisfaction")
    rule_table = "\n".join([
        "| Rule: A → B | A records | A and B records | Support | Confidence | Baseline P(B) | Lift |",
        "|---|---|---|---|---|---|---|",
        *[f"| {r['Antecedent_Level']} → {r['Outcome']} | {r['Antecedent_Count']} | {r['Joint_Count']} | "
          f"{100*r['Support']:.1f}% | {100*r['Confidence']:.1f}% | {100*r['Outcome_Baseline']:.1f}% | {r['Lift']:.2f} |"
          for r in selected],
    ])
    report = f"""# Phase 7: Prescriptive Insights and Recommendations

**Project:** Tourism Demand and Hospitality Resource Allocation

We use simple descriptive findings and **association rules—support, confidence and lift—to suggest marketing, capacity and service decisions**. The approach follows the supplied Contemporary Business Analytics course material.

## 1. Data and course concepts

We use the **{m['records']} prepared records** from [Phase 3](phase3.md), supported by [Phase 4](phase4.md) and [Phase 5](phase5.md). Each row is a destination-period record with a visit-purpose and hotel-tier label. It is **not an individual tourist or purchase transaction**, so percentages below describe records.

Following the idea of discretisation in Module 2, we create four simple labels:

| Label | Project definition |
|---|---|
| High spending | Tourist spending ≥ USD 3,000 per tourist |
| High occupancy | Hotel occupancy ≥ 70% |
| High satisfaction | Satisfaction score ≥ 8 |
| High arrivals | Number of tourists ≥ 150,000 per record |

These are illustrative round cutoffs, not industry standards or values prescribed in the slides. Purpose, region, hotel tier and season are the possible conditions. Season uses the hemisphere-aware labels from Phase 3. Basic averages follow Modules 1 and 3; rule calculations follow Module 4.

## 2. Support, confidence and lift

For a rule **A → B**, A is a condition and B is an outcome associated with it. The arrow does not mean A causes B.

| Measure | Formula | Simple meaning |
|---|---|---|
| Support | Records with both A and B ÷ all records | How common is this combination? |
| Confidence | Records with both A and B ÷ records with A | Within group A, how often does B occur? |
| Lift | Confidence ÷ overall proportion with B | Is B more common with A than overall? |

**Lift > 1:** positive association. **Lift = 1:** no association. **Lift < 1:** negative association. A lift close to 1 suggests a weak relationship. Confidence is a conditional frequency, not a statistical confidence level or model accuracy. Confidence may change when the direction of a rule is reversed.

### Worked example: Business travel → High spending

There are **{b['Antecedent_Count']} Business records**, **{b['Outcome_Count']} high-spending records overall**, and **{b['Joint_Count']} records with both**.

- Support = {b['Joint_Count']} / {m['records']} = **{100*b['Support']:.1f}%**.
- Confidence = {b['Joint_Count']} / {b['Antecedent_Count']} = **{100*b['Confidence']:.1f}%**.
- Overall high-spending proportion = {b['Outcome_Count']} / {m['records']} = **{100*b['Outcome_Baseline']:.1f}%**.
- Lift = {b['Confidence']:.4f} / {b['Outcome_Baseline']:.2f} = **{b['Lift']:.2f}**.

**Interpretation:** High spending occurs about **{100*(b['Lift']-1):.1f}% more often in Business records relative to its overall frequency**. This suggests a segment to examine. It does not mean a campaign would raise spending by that amount.

### Frequent patterns versus strong rules

Module 4 distinguishes a **frequent itemset** (enough support) from a **strong rule** (enough support and confidence). Lift is then used to assess association against the outcome's baseline.

The slides' supermarket example uses 40% minimum support and 70% minimum confidence. We keep **70% minimum confidence**, but use **5% minimum support (25 of 500 records)** for this tourism exercise because the data has many smaller categories. This is a project choice; the supermarket example's 40% is not a universal requirement.

Business + High spending is frequent at 7.8% support, but Business → High spending is **not strong** because its confidence is only 54.9%. A positive lift alone does not make it strong. We count single-condition pairs directly; this is not a claim to have run full Apriori or FP-Growth.

## 3. Results and key findings

{rule_table}

These are six explanatory examples. The complete output includes **all {m['rules_checked']} candidate rules**, including rules with lift below 1. This avoids presenting only attractive examples.

1. **Capacity use needs attention.** Mean record occupancy is **{m['mean_occupancy_percent']:.2f}%**. **{m['below_60_occupancy_records']} of {m['records']} records ({100*m['below_60_occupancy_records']/m['records']:.1f}%)** are below 60%. This is a screening observation, not proof of hotel losses or a room-weighted market occupancy rate.
2. **Business travel has a modest spending association.** Confidence is **{100*b['Confidence']:.1f}%** and lift **{b['Lift']:.2f}**. Business packages are an idea to test, not a guaranteed source of profit.
3. **Spring spending should be checked locally.** High-spending confidence is **{100*spring['Confidence']:.1f}%**, versus **{100*spring['Outcome_Baseline']:.1f}%** overall; lift is **{spring['Lift']:.2f}**. Pooling destinations and years does not establish a reliable peak season.
4. **Family visitors can also support occupancy.** High-occupancy confidence is **{100*family['Confidence']:.1f}%**, versus **{100*family['Outcome_Baseline']:.1f}%** overall; lift is **{family['Lift']:.2f}**. Lower spending in the earlier analysis does not mean the segment should be ignored.
5. **More stars do not automatically mean higher satisfaction.** The 4-star satisfaction rule has lift **{four['Lift']:.2f}**, compared with **{five['Lift']:.2f}** for 5-star. This does not prove that changing a hotel's rating improves service.
6. **There are no strong rules at the chosen thresholds.** Of **{m['rules_checked']} rules**, **{m['frequent_pairs']} pairs** meet 5% support, but **{m['strong_rules']} rules** also meet 70% confidence. The displayed examples are exploratory associations, not strong rules. The responsible decision is to test ideas rather than commit a large budget.

## 4. Five practical recommendations

| Finding | Recommendation | Simple business principle | Expected benefit and how to check it |
|---|---|---|---|
| Business → High spending: lift {b['Lift']:.2f} | Test a small Business-travel package in a suitable local market. | Segmentation: tailor the offer to a group. | Potentially attract higher-value bookings. Compare additional revenue minus service and campaign costs with a comparable group receiving no new offer. |
| Spring → High spending: lift {spring['Lift']:.2f} | Verify local booking patterns before testing a seasonal offer. | Match marketing to the period and available capacity. | Potentially improve visitor value. Track spending and bookings with a suitable comparison; do not apply the pooled pattern everywhere. |
| Family Visit → High occupancy: lift {family['Lift']:.2f} | Include family packages in local marketing and availability planning. | Balance visitor value with utilisation. | Potentially fill available rooms. Track occupied room-nights, package cost and cancellations. |
| Occupancy varies across records | Use actual bookings to plan staff and improve existing capacity before adding hotels. | Capacity planning: match resources to workload. | Potentially reduce idle resources and staffing mismatches. Track property occupancy, overtime and room-ready time. |
| Satisfaction associations are modest; no rule is strong | Review guest feedback and test small service improvements before expanding them. | Continuous improvement: observe, try, measure and review. | Potentially improve satisfaction. Track complaints, service costs and satisfaction; do not assume a star upgrade will work. |

These are **proposals to test**, not proven effects. The data does not contain campaign costs, property room inventories or causal responses to offers, so it cannot establish a reliable profit increase or national marketing allocation.

### One simple expected-impact example

`Net benefit = additional booking revenue − additional service costs − campaign cost`

**Assume** a pilot adds 20 bookings, earns USD 100 per booking, costs USD 40 to serve each booking and has a USD 500 campaign cost:

`Net benefit = (20 × 100) − (20 × 40) − 500 = USD 700`

This is a classroom example, **not a dataset result**. It assumes all 20 bookings are additional and no existing full-price bookings are lost. The pilot must check this. Association-rule lift is not a forecast of extra bookings.

## 5. Simple implementation plan

1. **Check:** The analytics team checks the local bookings, rule counts and customer group.
2. **Try:** Marketing or hotel management tests one small offer or service change within available capacity.
3. **Measure:** Finance and operations compare net benefit, occupancy, cancellations and guest feedback with a suitable comparison group.
4. **Decide:** Keep or expand the idea only if the measured benefit is positive and service quality is maintained. Otherwise change or stop it.

## 6. Limitations and conclusion

The dataset appears synthetic and has uneven coverage and repeated city-month records. Rules are explored on the same 500 records, without validation on new data or a claim of statistical significance. Searching many rules can produce chance patterns. Association does not establish causation. The supplied Phase 6 notebook concerns satisfaction, not a validated arrivals forecast.

**Conclusion:** Support shows how common a combination is, confidence shows how often the outcome occurs within a group, and lift compares that frequency with the baseline. Here the patterns are modest. Use them to select small marketing and service tests and improve existing operations before large investments.

## 7. Reproduction and course references

```sh
python analysis/phase7_prescriptive_analysis.py
python -m unittest discover -s tests -p "test_phase7*.py" -v
```

Python 3.10+ is sufficient; no extra packages are needed. `notebooks/07_Prescriptive_Insights.ipynb` runs the same analysis and displays this report. Five files in `outputs/phase7/` contain all rules, the six displayed examples, summary findings, definitions and a source audit. CSV measures are fractions; this report shows percentages.

**Supplied course material used** (PDF page numbers):

- Module 1, *Foundations of Business Analytics and Data Preparation*, pp. 9, 12 and 29: decision support, the KDD process and mean.
- Module 2, *Data Preprocessing*, p. 32: discretisation into readable categories.
- Module 3, *Descriptive Analytics and Data Visualization*, pp. 3 and 6: basic summaries and tabular presentation.
- Module 4, *Pattern Mining*, pp. 10–11, 20 and 23–25: support, directional confidence, strong-rule thresholds and lift.

The course PDFs are reference material supplied by the student; they are not copied into the public repository. The project uses their methods, while the tourism cutoffs and recommendations are our application.
"""
    (root / "phase7.md").write_text(report.rstrip() + "\n", encoding="utf-8")
