"""Business interpretation and submission report for the Phase 7 calculations."""


def table(records, columns):
    def fmt(value):
        if isinstance(value, int):
            return f"{value:,}"
        if isinstance(value, float):
            return f"{value:,.2f}"
        return str(value)
    return "\n".join([
        "| " + " | ".join(label for _, label in columns) + " |",
        "|" + "---|" * len(columns),
        *["| " + " | ".join(fmt(r[key]) for key, _ in columns) + " |" for r in records],
    ])


def render_report(root, m, baseline, scenarios, payoffs, decisions, evpi, staffing):
    from phase7_prescriptive_analysis import ASSUMPTIONS as a, required_occupancy

    occ = m["mean_occupancy_percent"] / 100
    capacity = a["hotel_rooms"] * a["days"]
    margin = a["adr_usd"] - a["variable_cost_per_room_night_usd"]
    new_adr = a["adr_usd"] * (1 - a["discount_fraction"])
    discount_be = required_occupancy(occ, a["adr_usd"], new_adr,
                                     a["variable_cost_per_room_night_usd"], capacity,
                                     a["discount_campaign_cost_usd"])
    pilot_be_pp = 100 * a["targeted_pilot_cost_usd"] / (capacity * margin)
    high_overflow_nights = min(max(a["future_demand_room_nights"]) - capacity,
                              a["partner_extra_capacity_room_nights"])
    partner_probability_be = a["partner_monthly_retainer_usd"] / (
        high_overflow_nights * a["partner_net_contribution_usd"])
    wide_payoffs = []
    for decision in decisions:
        subset = [r for r in payoffs if r["Action"] == decision["Action"]]
        wide_payoffs.append(dict(Action=decision["Action"],
                                  **{r["Demand_State"]: r["Incremental_Monthly_Payoff_USD"] for r in subset}))
    report = f"""# Phase 7: Prescriptive Insights and Recommendations

**Project:** Optimising Tourism Demand and Hospitality Resource Allocation

**Decision-makers:** Tourism authorities, hotel managers and tourism investors

**Scope:** Convert the team's analytical findings into actionable decisions, using decision theory, operations management and essential data analysis.

## 1. Management recommendation

**Use the present capacity more effectively before committing to permanent expansion.** Test a small, locally targeted marketing offer; protect contribution margin when pricing; schedule staff against booked workload; and use flexible capacity when an independently validated demand outlook justifies it. Release further funds only when measured incremental contribution and service quality support the decision.

This is a proposed decision process, not an instruction to spend money now. The data appears synthetic and contains uneven coverage and unresolved capacity inconsistencies. The project can demonstrate how a manager should decide, but cannot establish that a real destination needs investment or guarantee an uplift.

## 2. Evidence base and connection to earlier phases

This phase uses `data/processed/tourism_cleaned.csv` from [Phase 3](phase3.md): **{m['records']} records, {m['countries']} countries, {m['cities']} cities, 2020–2024**. It extends the [Phase 4 statistics](phase4.md) and [Phase 5 dashboard](phase5.md). Phase 3 preserved the original observations; financial units follow its inferred `Tourism_Revenue_USD_000` convention.

**What Phase 6 currently supports:** The repository contains `notebooks/06_Logistic_Regression.ipynb`. It defines a binary **High_Satisfaction** target using the full-data median satisfaction score, rather than predicting tourist arrivals. It contains no saved evaluation outputs. Phase 7 therefore makes no claim about its accuracy, significant predictors, causal effects or ability to forecast room demand. The Phase 1 arrivals-prediction question remains unresolved by that notebook. If the team uses the classifier, establish the label threshold on training data or use a predeclared business threshold, fit preprocessing on training data, compare with a majority-class baseline, report held-out discrimination and calibration, and validate on new periods before using its probabilities. A satisfaction association would still not identify which intervention improves satisfaction.

### Key findings: evidence → decision implication

| ID | Finding from the prepared data | Interpretation for management |
|---|---|---|
| F1 | Equal-record mean occupancy is **{m['mean_occupancy_percent']:.2f}%**. **{m['below_60_occupancy_records']} of {m['records']} records ({100*m['below_60_occupancy_records']/m['records']:.1f}%)** are below 60%. The 60% boundary is an illustrative screening level. | Investigate utilisation before adding fixed capacity. This is not a room-weighted occupancy rate, and 60% is not an industry breakeven threshold. |
| F2 | Arrivals average **{m['mean_arrivals']:,.0f} per record**, with CV **{m['arrival_cv_percent']:.1f}%**. | There is substantial workload variation. Use flexible rosters and actual bookings; the pooled average cannot determine staffing at a particular hotel. |
| F3 | Spending has CV **{m['spend_cv_percent']:.1f}%**, above the arrivals CV. Tourist-weighted spend is **USD {m['weighted_spend_usd']:,.2f}**. | Assess value and contribution per visitor alongside volume. Tourism spending is not equivalent to hotel room revenue or profit. |
| F4 | Business visitors spend **USD {m['Business_weighted_spend_usd']:,.2f}** per tourist (n={m['Business_records']}); Family Visit visitors **USD {m['Family Visit_weighted_spend_usd']:,.2f}** (n={m['Family Visit_records']}). The observed gap is **{m['business_vs_family_gap_percent']:.1f}%**. | Business travel is a hypothesis for a marketing pilot, not proof of a superior acquisition return. Do not withdraw service from lower-spend groups without cost and lifetime-value evidence. |
| F5 | Within Business travel, weighted spend is **USD {m['Americas_business_spend_usd']:,.2f}** in the Americas (n={m['Americas_business_records']}) versus **USD {m['Europe_business_spend_usd']:,.2f}** in Europe (n={m['Europe_business_records']}). | Segment averages depend on location and sample mix. Test offers at a local segment level; avoid applying the global Business ranking everywhere. |
| F6 | January mean arrivals are **{m['january_mean_arrivals']:,.0f}** versus **{m['august_mean_arrivals']:,.0f}** in August, pooling different destinations and years. | These descriptive differences do not establish a stable peak season. Use a rolling forecast validated within each destination before seasonal commitments. |
| F7 | Phase 5's relative capacity matrix flags China, India, Spain and UAE as high load/high occupancy; Egypt, Germany, Thailand and US as low load/low occupancy. Singapore has high load but only **59.05%** mean occupancy. | Use the matrix as an investigation list, not an investment rule. Tourists per hotel cannot replace room-night capacity; hotel size, guest nights and repeated records can explain apparent contradictions. |
| F8 | **{m['repeated_key_records']} records** have repeated city-month keys; **{m['room_spend_flag_records']}** have the Phase 3 room-cost-versus-spend flag. Country coverage is **{m['country_record_min']}–{m['country_record_max']} records**. | Reconcile definitions and obtain property-level data before funding decisions. Do not sum repeated hotel counts or interpret sample totals as annual country totals. |
| F9 | The model notebook has a satisfaction target, not an evaluated arrivals forecast. | Do not automate demand allocation, staffing or expansion from unvalidated model outputs. Retain managerial review and a transparent booking-based baseline. |

F1–F6 and F8 are recalculated by `analysis/phase7_prescriptive_analysis.py`; F7 is traceable to `outputs/phase5/chart_data_fig7.csv`. F9 is a static inspection of the supplied notebook, recorded in `source_audit.json`. These are descriptive associations, not experimental treatment effects.

## 3. Five actionable recommendations

### R1. Prioritise utilisation and flexible capacity before construction

**Evidence:** F1 and F7. **Principles:** Capacity planning, capacity utilisation, fixed-versus-variable cost, opportunity cost and bottleneck analysis.

The hotel operations manager should first reconcile rooms, saleable room-nights, occupied room-nights and local booking pace. Investigate low occupancy using channel mix, cancellations, hotel size and stay duration. In a genuinely constrained location, compare an overflow partnership or temporary capacity with permanent expansion. In a location with validated spare capacity, test demand generation before increasing the fixed-cost base.

Use `occupied room-nights / available room-nights` for utilisation. A hotel count measures establishments, not production capacity. Establish the actual constraint—rooms, housekeeping, transport, reception or demand—before adding resources; more rooms do not improve throughput when demand is the constraint. High utilisation also leaves less room for demand variation and service recovery, so the objective is profitable service at an acceptable quality level, not 100% occupancy at any price.

**Owner and timing:** Hotel operations manager; data reconciliation in days 1–30, flexible-capacity assessment in days 31–60. **Expected impact:** Lower risk of idle fixed assets and lost peak bookings; the magnitude is unestimated. **Gate:** No expansion until local demand evidence, room-night economics and a downside-tested investment appraisal support it. Expansion NPV must include construction, working capital, maintenance, financing and residual value, which are not in this dataset.

### R2. Test local segment offers and allocate marketing by incremental contribution

**Evidence:** F3–F5. **Principles:** Market segmentation, scarce-budget allocation, opportunity cost and controlled experimentation.

The tourism marketing lead and participating hotel sales manager should select a locally plausible Business, Educational or Medical visitor offer, using Phase 5's purpose/region view to formulate the hypothesis. Confirm targetability and room availability from current data. Compare a capped treatment offer with business-as-usual in comparable eligible units, preferably randomising customers or booking cohorts. Avoid comparing different countries as if they were experimental controls. Account for spillovers, cancellations and bookings shifted from other channels.

Allocate the next budget increment by **incremental contribution after acquisition cost**, not by historical revenue, spend rank or record frequency. Include net room revenue, attributable ancillary margin, servicing cost, commissions and cannibalisation. Educational and Family Visit are the most common record labels; that does not mean they are the largest populations of tourists.

**Owner and timing:** Marketing lead with finance; design in days 1–30, pilot in days 31–60, review in days 61–90. **Expected impact:** Potential improvement in visitor value and use of spare capacity, with the causal uplift to be estimated by the pilot. **Gate:** Scale only if the conservative estimate of incremental contribution after campaign cost is positive, operational capacity is available, and the predeclared service-quality guardrail passes. Choose test size using business-relevant uplift, variability and power; the small regional cells do not establish sufficient evidence by themselves.

### R3. Protect contribution margin before using blanket discounts

**Evidence:** F1 and F3; the dataset does not contain price elasticity. **Principles:** Contribution analysis, cost–volume–profit, revenue management and sensitivity analysis.

The revenue manager should compare an occupancy-building offer with a value-added package at a protected room rate. Where spare rooms are validated, use limited eligible dates or channels and include displacement of full-rate guests in the economics. Never assume a 10% price cut automatically produces enough additional bookings.

**Owner and timing:** Revenue manager and finance; calculate break-even before any promotion, then review weekly during a pilot. **Expected impact:** Avoid filling more rooms while earning less contribution. **Gate:** Forecast and subsequently measure net room-night contribution above the relevant break-even threshold. Section 4 shows the calculation with explicitly assumed hotel economics; it does not estimate an optimal price.

### R4. Match staffing to booked workload and protect the service constraint

**Evidence:** F2 and F6; Phase 6 does not supply a validated room-demand forecast. **Principles:** Aggregate planning, flexible workforce, workload measurement, service buffers and the theory of constraints.

Use current reservations, expected arrivals/departures and task timings to create daily housekeeping and reception workloads. Cross-train staff and keep an agreed flexible shift pool for temporary peaks. Protect productive time for cleaning and check-in bottlenecks, and check safety, labour and service requirements before adjusting rosters. A pooled tourist-arrivals percentile is not a hotel's 90% service-level forecast.

For an illustrative **100-room property**, assume every occupied room needs 30 minutes of housekeeping per day and each attendant supplies 6 productive hours per shift:

`Required attendants = ceiling(rooms × occupancy × cleaning minutes / (60 × productive hours))`

{table(staffing, [('Scenario','Scenario'), ('Assumed_Occupancy_Percent','Assumed occupancy %'), ('Housekeeping_Hours_Per_Day','Cleaning hours/day'), ('Attendants_Per_Shift','Attendants/shift')])}

The sample mean occupancy is used only as a classroom reference; it is not a measured property occupancy. Productive hours, room count and task time are assumptions, not dataset observations. This excludes checkout complexity, public-area cleaning, leave coverage and supervisor work; measure them before using the roster. Match staff to the bottleneck and evaluate labour cost per occupied room-night together with room-ready time, overtime and complaints.

**Owner and timing:** Operations/HR; time study in days 1–30, roster pilot in days 31–60. **Expected impact:** Potential reduction in overtime and service delays; no cost saving is estimated from the present data. **Gate:** Maintain a predeclared room-ready-time and complaint-rate guardrail while meeting contractual staffing requirements.

### R5. Use a measured decision cycle and improve evidence before major allocation

**Evidence:** F6, F8 and F9. **Principles:** Decisions under uncertainty, value of information, forecasting validation and Plan–Do–Check–Act (PDCA).

The analytics lead should reconcile room and spending definitions, confirm the revenue scale, and build a destination/property-period panel with available room-nights, occupied room-nights, bookings, cancellations, prices and costs. Validate a simple booking-pace or seasonal-naive forecast before trying a more complex one. Use time-based validation, report MAE in operational units and forecast bias, and assess interval coverage when using forecast uncertainty. Prevent target leakage and fit preprocessing inside the training split. The satisfaction model addresses a separate service question.

**Owner and timing:** Analytics lead and finance sponsor; evidence checks start immediately and continue through day 90. **Expected impact:** More defensible allocation and fewer decisions driven by misleading rankings; financial impact is unestimated. **Gate:** A representative input, an appropriate baseline, decision-relevant validation and an accountable owner are required before model-assisted rollout.

## 4. Expected impact: contribution and pricing scenarios

### 4.1 Explicit assumptions and units

The following is a **hypothetical hotel-month**, separate from the country/segment records. All values are **USD**, not the dataset's thousand-USD revenue unit. The only empirical reference used is the **{m['mean_occupancy_percent']:.4f}% equal-record mean occupancy**; applying it to one hotel is an illustrative assumption.

| Input | Assumed value | Basis |
|---|---|---|
| Rooms and period | 100 rooms × 30 days = 3,000 available room-nights | Classroom assumption, not room inventory in the dataset |
| Average daily room rate (ADR) | USD 120 | Classroom assumption; not tourist spending |
| Variable cost per sold room-night | USD 35 | Classroom assumption; includes servicing cost for this example |
| Monthly fixed operating costs | USD 150,000 | Classroom assumption; held constant across the pricing options |
| Targeted campaign cost | USD 6,000/month | Assumption, separate from servicing cost |
| Blanket discount | 10%, taking ADR to USD 108; campaign cost USD 1,500/month | Assumptions, applied to all sold nights to capture lost margin on existing demand |
| Occupancy uplift | Targeted pilot: +1/+4/+7 percentage points; discount: +5/+10/+15 points | Deliberately assumed sensitivity cases; neither fitted nor estimated from past data |

The campaign and discount cases are **alternatives**, not cumulative benefits. No probability is attached to the three pricing cases. Cancellations, capacity spillover and changes in variable costs are assumed absent; replace these simplifications for a real investment case. There is no extrapolation to all observed tourists or national revenue.

### 4.2 Formula and break-even

`Monthly operating profit = available room-nights × occupancy × (ADR − variable cost) − fixed cost − campaign cost`

The assumed contribution is USD {margin:.0f} per sold night, and the reference monthly operating profit is **USD {baseline:,.2f}** before tax, financing and capital charges. This is calculated, not observed. At these costs the operating break-even occupancy without a campaign is **{100*a['fixed_monthly_cost_usd']/(capacity*margin):.2f}%**; the sample mean occupancy cannot establish an actual hotel's profitability.

For the targeted pilot, incremental profit is `3,000 × occupancy uplift × 85 − 6,000`. The campaign breaks even at **+{pilot_be_pp:.2f} percentage points** of incremental occupancy, equivalent to **{a['targeted_pilot_cost_usd']/margin:.2f} additional room-nights/month** in the continuous calculation (round bookings up for an operational target). The +4-point case adds 120 room-nights, giving **USD 4,200** incremental monthly profit, only if that uplift is attributable to the campaign and servicing capacity is sufficient.

For a discount applied to all sold nights:

`Required new occupancy = [old occupancy × (old ADR − variable cost) + campaign cost / available nights] / (new ADR − variable cost)`

A 10% discount requires **{100*discount_be:.2f}% occupancy**, an increase of **{100*(discount_be-occ):.2f} percentage points**, just to preserve baseline profit after the USD 1,500 campaign cost. Higher occupancy by itself is not success.

### 4.3 Sensitivity results

{table(scenarios, [('Action','Alternative'), ('Scenario','Assumed response'), ('Assumed_Uplift_PP','Uplift (points)'), ('Assumed_Occupancy_Percent','Occupancy %'), ('Monthly_Profit_USD','Monthly profit USD'), ('Incremental_Profit_USD','Change vs baseline USD')])}

**Decision implication:** The targeted pilot is loss-making in its conservative case; the discount is still loss-making at a +10-point uplift. These scenarios identify what must be learned, not which uplift will occur. Estimate the causal response and contribution with a small test before committing the full campaign budget. A larger return in an optimistic case is not evidence that the alternative is better.

## 5. Decision analysis: fixed expansion versus flexibility

### 5.1 Alternatives, demand states and assumed payoffs

Consider a separate future month at a 100-room hotel with 3,000 available nights. Compare three alternatives before demand is known:

1. **Keep current capacity:** Accept demand up to 3,000 nights; forego bookings above that. This is the zero incremental-payoff reference.
2. **Contract overflow:** A partner can serve at most 450 additional room-nights, earning the decision-maker USD 50 net contribution for each overflow night after partner and variable costs, with a USD 2,000 monthly retainer. These are assumptions, and availability is not guaranteed in the data.
3. **Expand by 20 rooms:** Add 600 room-nights/month at USD 85 room contribution and USD 20,000 in extra monthly fixed costs plus an assumed equivalent capital charge. This single-period simplification is not a full NPV appraisal.

Low/central/high demands are assumed to be **1,800 / 2,400 / 3,300 room-nights**. They are not forecasts from tourist arrivals. Within each state, the same demand applies to every alternative; expansion is assumed not to generate extra demand or change prices. Existing operating costs are common and cancel when calculating incremental payoffs. Under high demand, keep-capacity loses 300 bookings, overflow serves those 300, and expansion also serves only 300 extra nights despite adding 600 nights of capacity.

{table(wide_payoffs, [('Action','Alternative'), ('Low','Low demand USD'), ('Central','Central demand USD'), ('High','High demand USD')])}

These are incremental monthly monetary payoffs. Common fixed costs and baseline operating contribution are excluded from every option consistently. The expansion option is dominated by the overflow option across these assumed states; different persistent demand or partner terms could change that result.

### 5.2 Risk preference changes the decision rule

Under **certainty**, demand would be known and the best payoff in that column could be chosen. Under **risk**, probabilities can be used if justified. Here **0.30 / 0.50 / 0.20** are illustrative probabilities, not estimated frequencies, so the probability-weighted result is only a sensitivity example. Under **uncertainty**, probabilities are unavailable; a manager can explicitly choose a downside or regret criterion.

`Expected monetary value (EMV) = sum(probability of state × incremental payoff in that state)`

`Regret = best available payoff in a state − payoff of the chosen alternative`

{table(decisions, [('Action','Alternative'), ('Expected_Monetary_Value_USD','Illustrative EMV USD'), ('Worst_Case_Payoff_USD','Worst case USD'), ('Maximum_Regret_USD','Maximum regret USD')])}

- **EMV, assuming a risk-neutral manager and the illustrative probabilities:** Contract overflow has the highest EMV, **USD 1,000/month**. This does not demonstrate its real-world expected return.
- **Maximin, protecting the worst outcome without probabilities:** Keep capacity, since its worst incremental payoff is zero, whereas overflow can lose USD 2,000.
- **Minimax regret, limiting the largest missed opportunity:** Contract overflow, whose maximum regret is USD 2,000, compared with USD 13,000 for keeping capacity.

The analysis makes the trade-off visible: an authority or hotel manager must decide whether an uncertain upside justifies the USD 2,000 retainer exposure. The choice cannot be settled from the descriptive data alone.

### 5.3 Sensitivity and value of information

With only the high-demand state generating overflow bookings, expected incremental partner payoff is `15,000 × probability(high demand) − 2,000`. The agreement breaks even when the high-demand probability exceeds **{100*partner_probability_be:.2f}%**, under the other stated assumptions. Verify this probability from a relevant booking outlook and assess whether peak partner rooms will actually be available.

At the illustrative probabilities, the expected value with perfect demand information is USD 2,600/month; the best fixed decision yields USD 1,000. Therefore **expected value of perfect information (EVPI) = USD {evpi:,.0f}/month**. This is a theoretical upper bound on what perfect advance demand information could add for this decision and horizon. It is not an approved research budget: an imperfect forecast or pilot is worth less, and its delay and costs must also be considered. Do not transfer this bound to the marketing or staffing decisions.

## 6. Implementation, measurement and accountability

| Stage | Action and accountable owner | Evidence required to proceed |
|---|---|---|
| Days 1–30: Plan | Analytics lead reconciles definitions and local room-night data. Finance checks margins. Operations measures task times. Marketing specifies one pilot and its comparison group. | Approved definitions, feasible capacity and cost assumptions, pilot design, primary contribution metric and predeclared service guardrails. Timings are proposed, not historical facts. |
| Days 31–60: Do | Marketing runs a capped pilot; operations trials a flexible roster; revenue manager records prices, eligibility, cancellations and displaced full-rate demand. | Operational execution logs and a valid comparison; no claim of benefit from a simple before/after change alone. |
| Days 61–90: Check | Finance and analytics compare incremental contribution, uncertainty and service outcomes with the predeclared criteria; review scenario sensitivity. | Positive conservative incremental contribution after all relevant costs, no material service deterioration, and suitable staffing/capacity. Otherwise stop, redesign or collect more evidence. |
| After review: Act | Sponsor chooses scale, revise or stop; repeat the cycle. Permanent expansion requires a separate investment appraisal. | Recorded decision, accountable owner, budget limit and next review date. |

### KPI definitions for the existing Tableau dashboard and operational review

| Decision | Primary KPI and formula | Supporting measure / guardrail | Present data availability |
|---|---|---|---|
| Capacity | Room occupancy = occupied room-nights / available room-nights | Turned-away bookings; cancellations; service delay | Only record-level occupancy is present; numerator and denominator must be collected. |
| Marketing | Incremental contribution = contribution with treatment − estimated contribution without treatment − incremental campaign cost | Acquisition cost per incremental booking; cancellations; segment/customer experience | Costs and counterfactual are absent. Use an experiment; sample spending is only a hypothesis. |
| Pricing | Contribution per available room-night = (net room revenue − variable room costs − allocated campaign cost) / available room-nights | ADR = net room revenue / sold nights; RevPAR = net room revenue / available nights | No valid pooled room-night denominator or cost data. Do not multiply unrelated mean ADR and mean occupancy to report observed RevPAR. |
| Staffing | Labour cost / occupied room-night | Room-ready time; overtime; complaints; workload coverage | Labour hours, task times, cost and service events must be collected. |
| Forecast use | MAE in booked room-nights and signed forecast bias, out of time | Prediction interval coverage and cost of over/under capacity | No validated room-demand forecast is supplied. Satisfaction classification is a separate target. |

Use the Tableau destination, month and purpose filters for **screening and discussion**. Label small cells and show sample size; do not treat a minimum of five records as proof of statistical reliability. Keep the existing dashboard's empirical figures separate from the hypothetical financial scenario tables.

## 7. Limits, assumptions and final project conclusion

The recommendation is to fund learning and reversible operating improvements before irreversible capacity commitments. The project's evidence supports questions to investigate, while the operations and decision models show the economic conditions under which an action could be worthwhile.

The dataset appears synthetic; observations are sparse and uneven; repeated city-month fields conflict; revenue units are inferred; and costs, room inventories, causal demand response and future-demand probabilities are absent. There is no observed causal effect or verified profit forecast here. Recommendations about actual countries remain illustrative. Validate with representative local data, property records and a prospective pilot before real deployment.

All numerical impact examples are **conditional scenario results**. They are not added together, annualised or presented as achieved savings. The 90-day timeline and service guardrails are proposed management controls, not data-derived outcomes. The report uses standard decision and operations management principles; it does not claim to quote course material that was not provided.

## 8. Deliverables and reproduction

```sh
python analysis/phase7_prescriptive_analysis.py
python -m unittest discover -s tests -p "test_phase7*.py" -v
```

The analysis needs Python 3.10+ and no third-party packages. It reads the Phase 3 prepared input without modifying earlier phases. The notebook runs the same calculation and displays this report; Jupyter/IPython is needed only for notebook execution/display.

| File | Purpose |
|---|---|
| `phase7.md` | Full submission report: nine findings, five recommendations, expected-impact assumptions, decision rules and implementation plan |
| `analysis/phase7_prescriptive_analysis.py` | Recalculates evidence, pricing, capacity, staffing and decision metrics |
| `analysis/phase7_report.py` | Generates the report from the calculation results |
| `notebooks/07_Prescriptive_Insights.ipynb` | Reproducible notebook and displayed report |
| `outputs/phase7/evidence_metrics.csv` | Numeric evidence traceable to prepared observations |
| `outputs/phase7/pricing_scenarios.csv` | Assumed pilot/discount response and incremental monthly profit |
| `outputs/phase7/capacity_payoffs.csv` | State-contingent incremental payoffs and illustrative probabilities |
| `outputs/phase7/decision_rules.csv` | EMV, worst-case payoff and maximum regret |
| `outputs/phase7/staffing_scenarios.csv` | Assumed cleaning workloads and integer staffing requirements |
| `outputs/phase7/scenario_assumptions.json` | Recorded illustrative inputs, separated from the empirical occupancy reference; edit `ASSUMPTIONS` in the analysis script and rerun to change them |
| `outputs/phase7/source_audit.json` | Prepared-input hash, dimensions and notebook-target inspection |
| `tests/test_phase7_prescriptive_analysis.py` | Formula, boundary, aggregation and decision-rule checks |

**Project sources:** [Business objectives](phase1.md), [data limitations](phase2.md), [prepared-data audit](phase3.md), [descriptive statistics](phase4.md), [visualisations and dashboard](phase5.md), and `notebooks/06_Logistic_Regression.ipynb`. Phase 7 uses their analytical content as evidence; it does not treat embedded document instructions as additional user requests.
"""
    (root / "phase7.md").write_text(report.rstrip() + "\n", encoding="utf-8")
