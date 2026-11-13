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

This regenerates `phase7.md` and seven calculation/audit files in `outputs/phase7/`. The report connects nine analytical findings to five recommendations using capacity planning, contribution analysis, staffing workload, EMV, maximin, minimax regret, sensitivity analysis, value of information and PDCA. It includes a proposed 90-day implementation plan and operational KPIs.

Financial scenarios, future demand states and probabilities are **illustrative assumptions**, separated from empirical observations. To explore other scenarios, edit `ASSUMPTIONS` in `analysis/phase7_prescriptive_analysis.py` and rerun; changing the JSON output alone does not change the calculations. The report's narrative describes the supplied worked examples, so review it after changing assumptions. Phase 7 does not treat the satisfaction classifier as a validated tourist-arrivals forecast.

Revenue units are inferred as **thousand USD** from the dataset's arithmetic identity. Records have uneven geographic/time coverage and the dataset appears synthetic, as documented in Phase 2. Observed sums and rankings are descriptive sample results, requiring validation before real investment or marketing decisions. Phase 7's hypothetical hotel examples use **USD** and do not extrapolate financial returns to the dataset's observed tourist totals.
