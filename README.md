# Tourism Demand and Hospitality Resource Allocation

Business analytics course project using the Tourism & Hospitality Industry Analysis dataset.

| Phase | Report | Reproducible analysis |
|---|---|---|
| 1 — Business understanding | [phase1.md](phase1.md) | Business questions, stakeholders and objectives |
| 2 — Data understanding | [phase2.md](phase2.md) | `analysis/phase2_data_understanding.py` and `notebooks/02_Data_Understanding.ipynb` |
| 4 — Descriptive analytics | [phase4.md](phase4.md) | `analysis/phase4_descriptive_analytics.py` and `notebooks/04_Descriptive_Analytics.ipynb` |

Course requirements are recorded in [context.md](context.md). A Phase 3 prepared dataset is not yet present; Phase 4 uses the unchanged raw data and documents that dependency explicitly.

## Reproduce Phase 4

From the repository root, with Python 3.10+ (no additional packages):

```sh
python analysis/phase4_descriptive_analytics.py
python -m unittest discover -s tests -v
```

This regenerates `phase4.md` and seven files in `outputs/phase4/`. The notebook runs the same analysis and displays the report; opening it requires a normal Jupyter/IPython environment.

Phase 4 covers central tendency, dispersion, quartiles/percentiles, frequency distributions, skewness and kurtosis, plus business interpretations by destination, time period, visitor purpose and hospitality utilisation. CSV exports retain full calculation precision.

Revenue units are inferred as **thousand USD** from the dataset's arithmetic identity. Records have uneven geographic/time coverage and the dataset appears synthetic, as documented in Phase 2. Observed sums and rankings are descriptive sample results, requiring validation before real investment or marketing decisions.
