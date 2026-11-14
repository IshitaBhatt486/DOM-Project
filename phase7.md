# Phase 7: Prescriptive Insights and Recommendations

**Project:** Tourism Demand and Hospitality Resource Allocation

We use simple descriptive findings and **association rules—support, confidence and lift—to suggest marketing, capacity and service decisions**. The approach follows the supplied Contemporary Business Analytics course material.

## 1. Data and course concepts

We use the **500 prepared records** from [Phase 3](phase3.md), supported by [Phase 4](phase4.md) and [Phase 5](phase5.md). Each row is a destination-period record with a visit-purpose and hotel-tier label. It is **not an individual tourist or purchase transaction**, so percentages below describe records.

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

There are **71 Business records**, **235 high-spending records overall**, and **39 records with both**.

- Support = 39 / 500 = **7.8%**.
- Confidence = 39 / 71 = **54.9%**.
- Overall high-spending proportion = 235 / 500 = **47.0%**.
- Lift = 0.5493 / 0.47 = **1.17**.

**Interpretation:** High spending occurs about **16.9% more often in Business records relative to its overall frequency**. This suggests a segment to examine. It does not mean a campaign would raise spending by that amount.

### Frequent patterns versus strong rules

Module 4 distinguishes a **frequent itemset** (enough support) from a **strong rule** (enough support and confidence). Lift is then used to assess association against the outcome's baseline.

The slides' supermarket example uses 40% minimum support and 70% minimum confidence. We keep **70% minimum confidence**, but use **5% minimum support (25 of 500 records)** for this tourism exercise because the data has many smaller categories. This is a project choice; the supermarket example's 40% is not a universal requirement.

Business + High spending is frequent at 7.8% support, but Business → High spending is **not strong** because its confidence is only 54.9%. A positive lift alone does not make it strong. We count single-condition pairs directly; this is not a claim to have run full Apriori or FP-Growth.

## 3. Results and key findings

| Rule: A → B | A records | A and B records | Support | Confidence | Baseline P(B) | Lift |
|---|---|---|---|---|---|---|
| Business → High spending | 71 | 39 | 7.8% | 54.9% | 47.0% | 1.17 |
| Spring → High spending | 114 | 66 | 13.2% | 57.9% | 47.0% | 1.23 |
| Family Visit → High spending | 80 | 30 | 6.0% | 37.5% | 47.0% | 0.80 |
| Family Visit → High occupancy | 80 | 39 | 7.8% | 48.8% | 40.8% | 1.19 |
| 4-star → High satisfaction | 87 | 44 | 8.8% | 50.6% | 37.8% | 1.34 |
| 5-star → High satisfaction | 91 | 37 | 7.4% | 40.7% | 37.8% | 1.08 |

These are six explanatory examples. The complete output includes **all 88 candidate rules**, including rules with lift below 1. This avoids presenting only attractive examples.

1. **Capacity use needs attention.** Mean record occupancy is **64.84%**. **207 of 500 records (41.4%)** are below 60%. This is a screening observation, not proof of hotel losses or a room-weighted market occupancy rate.
2. **Business travel has a modest spending association.** Confidence is **54.9%** and lift **1.17**. Business packages are an idea to test, not a guaranteed source of profit.
3. **Spring spending should be checked locally.** High-spending confidence is **57.9%**, versus **47.0%** overall; lift is **1.23**. Pooling destinations and years does not establish a reliable peak season.
4. **Family visitors can also support occupancy.** High-occupancy confidence is **48.8%**, versus **40.8%** overall; lift is **1.19**. Lower spending in the earlier analysis does not mean the segment should be ignored.
5. **More stars do not automatically mean higher satisfaction.** The 4-star satisfaction rule has lift **1.34**, compared with **1.08** for 5-star. This does not prove that changing a hotel's rating improves service.
6. **There are no strong rules at the chosen thresholds.** Of **88 rules**, **74 pairs** meet 5% support, but **0 rules** also meet 70% confidence. The displayed examples are exploratory associations, not strong rules. The responsible decision is to test ideas rather than commit a large budget.

## 4. Five practical recommendations

| Finding | Recommendation | Simple business principle | Expected benefit and how to check it |
|---|---|---|---|
| Business → High spending: lift 1.17 | Test a small Business-travel package in a suitable local market. | Segmentation: tailor the offer to a group. | Potentially attract higher-value bookings. Compare additional revenue minus service and campaign costs with a comparable group receiving no new offer. |
| Spring → High spending: lift 1.23 | Verify local booking patterns before testing a seasonal offer. | Match marketing to the period and available capacity. | Potentially improve visitor value. Track spending and bookings with a suitable comparison; do not apply the pooled pattern everywhere. |
| Family Visit → High occupancy: lift 1.19 | Include family packages in local marketing and availability planning. | Balance visitor value with utilisation. | Potentially fill available rooms. Track occupied room-nights, package cost and cancellations. |
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
