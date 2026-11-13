# Tourism Demand and Hospitality Resource Allocation

Business analytics course project using the Tourism & Hospitality Industry Analysis dataset.

| Phase | Report | Reproducible analysis |
|---|---|---|
| 1 — Business understanding | [phase1.md](phase1.md) | Business questions, stakeholders and objectives |
| 2 — Data understanding | [phase2.md](phase2.md) | `analysis/phase2_data_understanding.py` and `notebooks/02_Data_Understanding.ipynb` |
| 3 — Data preprocessing and preparation | [phase3.md](phase3.md) | `analysis/phase3_data_preprocessing.py` and `notebooks/03_Data_Preprocessing.ipynb` |
| 4 — Descriptive analytics | [phase4.md](phase4.md) | `analysis/phase4_descriptive_analytics.py` and `notebooks/04_Descriptive_Analytics.ipynb` |
| 5 — Data visualization and dashboard | [phase5.md](phase5.md) | `analysis/phase5_visualizations.py` and `Phase 5_DOM304_Tourism_Dashboard.twbx` |
| 6 — Satisfaction classification | `notebooks/06_Logistic_Regression.ipynb` | Logistic-regression code; targets high satisfaction, with no saved evaluation results |
| 7 — Prescriptive insights and recommendations | [phase7.md](phase7.md) | `analysis/phase7_prescriptive_analysis.py` and `notebooks/07_Prescriptive_Insights.ipynb` |

Course requirements are recorded in [context.md](context.md). Phase 3 writes the prepared datasets to `data/processed/`: `tourism_cleaned.csv` for descriptive work and Tableau, and `tourism_model_ready.csv` for Phase 6. Phase 4 was calculated on the raw data; its statistics still hold because Phase 3 changed no original values.

## Reproduce Phase 3

From the repository root, with Python 3.10+ and matplotlib:

```sh
python analysis/phase3_data_preprocessing.py
```

This regenerates `phase3.md`, the files in `data/processed/` and the tables and box plots in `outputs/phase3/`.

## Reproduce Phase 4

From the repository root, with Python 3.10+ (no additional packages):

```sh
python analysis/phase4_descriptive_analytics.py
python -m unittest discover -s tests -v
```

This regenerates `phase4.md` and seven files in `outputs/phase4/`. The notebook runs the same analysis and displays the report; opening it requires a normal Jupyter/IPython environment.

Phase 4 covers central tendency, dispersion, quartiles/percentiles, frequency distributions, skewness and kurtosis, plus business interpretations by destination, time period, visitor purpose and hospitality utilisation. CSV exports retain full calculation precision.

## Reproduce Phase 5

From the repository root, with Python 3.10+, numpy and matplotlib:

```sh
python analysis/phase5_visualizations.py
```

This regenerates the eight charts in `outputs/phase5/`, the data behind each chart and `kpi_summary.csv` (headline KPIs with their Tableau formulas). The Tableau dashboard, `Phase 5_DOM304_Tourism_Dashboard.twbx`, is built from `data/processed/tourism_cleaned.csv` and has the data packaged inside. Its Tableau Public link is in `Phase 5 DASHBOARD_Tableau Public Link.txt`.

## Reproduce Phase 7

From the repository root, with Python 3.10+ (no additional packages):

```sh
python analysis/phase7_prescriptive_analysis.py
python -m unittest discover -s tests -p "test_phase7*.py" -v
```

This regenerates the simplified `phase7.md` and five files in `outputs/phase7/`. It follows the supplied course modules: basic descriptive findings, discretisation, association rules, support, confidence and lift. Six findings lead to five practical marketing, capacity and service recommendations, with one simple hypothetical net-benefit example.

All 88 single-condition rules are exported, not just the most attractive examples. The project uses 5% minimum support for smaller tourism categories and the course example's 70% confidence threshold. There are 74 frequent pairs but no strong rules under these thresholds; lift is assessed separately, as taught in Module 4. The report treats the associations as ideas to test, not as proven effects or forecast uplifts. Each record is a destination-period observation, not an individual tourist.

Definitions and thresholds are recorded in `outputs/phase7/rule_definitions.json`. To change them, edit `OUTCOMES` or `FILTER` in the analysis script, rerun, and review the report narrative. Source PDFs are referenced by module and page in the report and are not uploaded to this public repository. The original detailed Phase 7 version remains in Git history.

Revenue units are inferred as **thousand USD** from the dataset's arithmetic identity. Records have uneven geographic/time coverage and the dataset appears synthetic, as documented in Phase 2. Observed sums and rankings are descriptive sample results, requiring validation before real investment or marketing decisions. Phase 7's illustrative net-benefit example uses **USD**, states its assumptions and does not extrapolate returns to the observed tourist totals.
