"""Build a local DuckDB from versioned Parquet inputs; no external services."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from src.config import DB_PATH, RAW_DIR, ROOT

TABLES = ["customers", "carriers", "quotes", "policies", "funnel_events",
          "marketing_spend", "monthly_customer_value"]


def build_database(raw_dir: Path = RAW_DIR, db_path: Path = DB_PATH) -> dict[str, int]:
    """Build in a staging file and replace only after a successful transaction."""
    manifest = json.loads((raw_dir / "manifest.json").read_text())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    staging = db_path.with_suffix(".tmp")
    # A prior failed build can safely be rebuilt; this file never contains source data.
    staging.unlink(missing_ok=True)
    with duckdb.connect(str(staging)) as con:
        con.execute("BEGIN TRANSACTION")
        for table in TABLES:
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet(?)",
                        [str(raw_dir / f"{table}.parquet")])
        con.execute("CREATE TABLE metadata (as_of DATE, seed BIGINT, synthetic BOOLEAN)")
        con.execute("INSERT INTO metadata VALUES (?, ?, true)", [manifest["as_of"], manifest["seed"]])
        con.execute((ROOT / "sql" / "build_marts.sql").read_text())
        experiment_tables = ["experiments", "experiment_registry", "experiment_value_assumptions"]
        present = [(raw_dir / f"{table}.parquet").exists() for table in experiment_tables]
        if any(present) and not all(present):
            raise ValueError("Incomplete experiment source files; regenerate the experiment dataset.")
        if all(present):
            from src.generate_experiments import source_fingerprints
            experiment_manifest = json.loads((raw_dir / "experiment_manifest.json").read_text())
            if experiment_manifest["source_fingerprints"] != source_fingerprints(raw_dir):
                raise ValueError("Experiment inputs are stale. Run python -m src.generate_experiments after changing the core data.")
            for table in experiment_tables:
                con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet(?)", [str(raw_dir / f"{table}.parquet")])
            con.execute((ROOT / "sql" / "experiment_marts.sql").read_text())
        con.execute("COMMIT")
        con.execute("CHECKPOINT")
        counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in TABLES}
    staging.replace(db_path)
    print(f"Database ready: {db_path.name} ({db_path.stat().st_size / 1e6:.1f} MB)")
    return counts


def connect(db_path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Use per-query read-only connections to avoid cross-session cursor sharing."""
    return duckdb.connect(str(db_path), read_only=True)


if __name__ == "__main__":
    build_database()
