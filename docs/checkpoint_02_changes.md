# Experiment implementation notes

The existing visual language is preserved. The experiment decision workflow complements the project's acquisition economics analysis.

## Application and shared presentation

- `app.py`: workspace routing and shared sidebar.
- `views/__init__.py`, `views/overview.py`: existing overview moved behind the shared shell; website-visit and pre-acquisition contribution terminology clarified.
- `views/experiments.py`: portfolio, detail, financial bridge, scenarios, segment analysis, evidence and exports.
- `src/ui.py`: shared presentation helpers.
- `assets/style.css`: experiment components using the existing palette, typography and spacing.
- `src/charts.py`: clearer pre-acquisition contribution label.

## Experiment data, analysis and SQL

- `src/experiment_designs.py`: hypotheses, populations, metrics, guardrails, practical effects and sample plans.
- `src/generate_experiments.py`: reproducible randomized trial data and pre-test valuation inputs.
- `src/experimentation.py`: inference, financial impact, decision rules and segment interactions.
- `src/experiment_analysis.py`: database-backed analysis, quality checks, scenario calculations and audit records.
- `src/experiment_charts.py`: treatment comparisons, segment intervals and cumulative results.
- `src/experiment_report.py`: generated decision memo and JSON export.
- `src/database.py`: experiment loading, source-fingerprint validation and marts.
- `sql/experiment_marts.sql`, `sql/11_experiment_analysis.sql`: intention-to-treat denominators, window calculations and financial reconciliation.
- `src/checkpoint_report.py`: executive memo updated for the working experiment section.
- `requirements.txt`: analytical dependencies.

## Tests and documentation

- `tests/test_experimentation.py`: statistical calculations, impact accounting and decision gates.
- `tests/test_experiment_pipeline.py`: reproducibility, source timing, quality checks, computed insights, SQL reconciliation and exports.
- `tests/test_experiment_app.py`: portfolio/detail navigation, segment controls, financial scenarios and overview compatibility.
- `README.md`, `docs/experimentation.md`, `docs/methodology.md`, `docs/data_dictionary.md`, `docs/architecture.md`: product, methodology and implementation documentation.
- `docs/experiment_review.md`, `docs/experiment_results.json`, `docs/executive_memo.md`, `docs/validation_report.json`, `docs/test_results.txt`: current generated results and validation.
- `docs/screenshots/04-experiment-portfolio.png` through `08-referral-tradeoff.png`: screenshots captured from the running application.

Generated local artifacts include the three experiment Parquet tables, generation manifest and rebuilt DuckDB database. Historical source outcomes were not overwritten to incorporate the separate trials.

## Review limits

The trials and outcomes are synthetic. Annualized contribution values twelve acquisition cohorts over twelve policy months per cohort, rather than realized revenue or first-calendar-year contribution. Financial confidence intervals cover randomized-unit sampling only; value, traffic and cost assumptions remain uncertain. Segment differences are exploratory, and the referral model assumes no network spillovers.
