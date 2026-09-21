# Architecture

```text
Seeded numpy generator → 7 Parquet source tables → DuckDB transaction
                                                   ↓
                                Customer facts + LTV assumptions + monthly view
                                                   ↓
                             Parameterized SQL → Python metric contract
                                                   ↓
                               Streamlit + Plotly / CSV / checkpoint memo
```

`src/generate_data.py` creates vectorized, linked source records. `src/database.py` builds in a staging file and atomically replaces the existing database only after success. `sql/build_marts.sql` aggregates ledger facts before joining, preventing duplicate customer counts and inflated revenue. The ten numbered SQL files are executable analytical case studies.

`src/analytics.py` binds filters as query parameters and opens independent read-only connections. Streamlit caches by filter selection and database modification time. No server credentials, container, paid API or cloud account is needed.

`src/metrics.py` defines analytical primitives; `src/executive_insights.py` evaluates calculated metrics with sample thresholds. `src/charts.py` and `assets/style.css` own presentation. The interface scales from an app panel to a wide browser using responsive layouts. No nonfunctional navigation to future modules is shown.

`src/validate_data.py` produces a machine-readable validation report. Pytest builds its own small seeded dataset, validates financial and relational invariants, compares SQL/Python LTV, exercises filter semantics, and uses Streamlit AppTest for render and empty-state checks. When the full database exists, application tests run against it.

Checkpoint 02 adds `views/experiments.py` alongside the preserved `views/overview.py`. `app.py` owns routing, while `src/ui.py` preserves shared typography, number formatting and visual helpers.

`src/experiment_designs.py` specifies designs before outcomes. `src/generate_experiments.py` builds independent trial cohorts using pre-test historical profiles and valuation assumptions. Their source fingerprints are checked during the transactional DuckDB build. `sql/experiment_marts.sql` and `sql/11_experiment_analysis.sql` preserve intention-to-treat denominators and expose an auditable financial bridge.

`src/experimentation.py` contains statistical primitives, bootstrap intervals, guardrail noninferiority, sample planning, heterogeneity and the experiment-agnostic decision policy. `src/experiment_analysis.py` binds the database registry to those calculations, quality checks and downloadable decision records. `src/experiment_report.py` produces the executive experiment memo. The sidebar never applies historical operating-book filters to the randomized comparison; segment analysis is explicitly exploratory.

Optimization, carrier strategy, predictive modeling and forecasting remain unimplemented. The next work begins only after experiment review.
