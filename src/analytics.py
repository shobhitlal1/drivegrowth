"""Parameterized SQL powers every dashboard KPI and chart."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from src.config import DB_PATH
from src.database import connect


@dataclass(frozen=True)
class Filters:
    start: date
    end: date
    state: str = "All states"
    channel: str = "All channels"
    carrier: str = "All carriers"
    segment: str = "All segments"

    def where(self) -> tuple[str, list]:
        clauses, params = [], []
        for col, value, default in [
            ("state", self.state, "All states"),
            ("acquisition_channel", self.channel, "All channels"),
            ("carrier_name", self.carrier, "All carriers"),
            ("customer_segment", self.segment, "All segments"),
        ]:
            if value != default:
                clauses.append(f"{col} = ?")
                params.append(value)
        return " AND ".join(clauses) or "TRUE", params

    def previous(self) -> "Filters":
        """Previous equal number of full calendar months."""
        months = (self.end.year - self.start.year) * 12 + self.end.month - self.start.month + 1
        end = pd.Timestamp(self.start) - pd.Timedelta(days=1)
        start = pd.Timestamp(self.start) - pd.DateOffset(months=months)
        return Filters(start.date(), end.date(), self.state, self.channel, self.carrier, self.segment)


def overview(f: Filters, db_path: Path = DB_PATH) -> dict:
    where, dims = f.where()
    with connect(db_path) as con:
        kpi = con.execute(f"""
            SELECT count(*) AS customers, sum(quote_started::INT) AS quote_starts,
                   sum(quote_completed::INT) AS quote_completions,
                   sum(carrier_matched::INT) AS carrier_matches,
                   sum(policy_purchased::INT) AS policies,
                   sum(allocated_spend) AS spend, avg(modeled_ltv_24m) AS ltv,
                   avg(premium) AS average_premium
            FROM customer_facts WHERE signup_date BETWEEN ? AND ? AND {where}
        """, [f.start, f.end, *dims]).fetchdf().iloc[0].to_dict()
        kpi = {key: None if pd.isna(value) else value for key, value in kpi.items()}
        for key in ["customers", "quote_starts", "quote_completions", "carrier_matches", "policies", "spend"]:
            kpi[key] = kpi[key] or 0
        financial = con.execute(f"""
            SELECT coalesce(sum(revenue), 0) AS revenue,
                   coalesce(sum(contribution_margin), 0) AS contribution_margin
            FROM monthly_operating_performance
            WHERE month BETWEEN ? AND ? AND {where}
        """, [f.start, f.end, *dims]).fetchdf().iloc[0].to_dict()
        renewal = con.execute(f"""
            SELECT count(*) AS eligible, sum(renewed::INT) AS renewed
            FROM customer_facts
            WHERE policy_start + INTERVAL 365 DAY BETWEEN ? AND ?
              AND renewal_eligible AND {where}
        """, [f.start, f.end, *dims]).fetchone()
        kpi.update(financial)
        kpi["cac"] = kpi["spend"] / kpi["policies"] if kpi["policies"] else None
        kpi["conversion"] = kpi["policies"] / kpi["quote_starts"] if kpi["quote_starts"] else None
        kpi["ltv_cac"] = kpi["ltv"] / kpi["cac"] if kpi["cac"] and kpi["ltv"] is not None else None
        kpi["renewal_rate"] = renewal[1] / renewal[0] if renewal[0] else None
        kpi["renewal_eligible"] = renewal[0]
        kpi["margin_rate"] = kpi["contribution_margin"] / kpi["revenue"] if kpi["revenue"] else None
    return kpi


def dashboard_data(f: Filters, db_path: Path = DB_PATH) -> dict:
    where, dims = f.where()
    with connect(db_path) as con:
        channels = con.execute(f"""
            SELECT acquisition_channel AS channel, count(*) AS customers,
                   sum(policy_purchased::INT) AS policies,
                   sum(allocated_spend) AS spend,
                   sum(allocated_spend) / nullif(sum(policy_purchased::INT), 0) AS cac,
                   avg(modeled_ltv_24m) AS ltv,
                   avg(modeled_ltv_24m) * sum(policy_purchased::INT) / nullif(sum(allocated_spend), 0) AS ltv_cac,
                   sum(policy_purchased::INT)::DOUBLE / nullif(sum(quote_started::INT), 0) AS conversion
            FROM customer_facts WHERE signup_date BETWEEN ? AND ? AND {where}
            GROUP BY 1 ORDER BY policies DESC
        """, [f.start, f.end, *dims]).fetchdf()
        series = con.execute(f"""
            SELECT month, sum(revenue) AS revenue, sum(contribution_margin) AS contribution_margin
            FROM monthly_operating_performance WHERE month BETWEEN ? AND ? AND {where}
            GROUP BY 1 ORDER BY 1
        """, [(pd.Timestamp(f.end).replace(day=1) - pd.DateOffset(months=11)).date(), f.end, *dims]).fetchdf()
        devices = con.execute(f"""
            SELECT device_type, sum(quote_started::INT) AS starts,
                   sum(quote_completed::INT)::DOUBLE / nullif(sum(quote_started::INT), 0) AS completion
            FROM customer_facts WHERE signup_date BETWEEN ? AND ? AND {where}
            GROUP BY 1
        """, [f.start, f.end, *dims]).fetchdf()
        integrity = con.execute("""
            SELECT (SELECT count(*) FROM customers) AS customers,
                   (SELECT count(*) FROM funnel_events) AS events,
                   (SELECT count(*) FROM monthly_customer_value) AS ledger_rows,
                   (SELECT as_of FROM metadata) AS as_of
        """).fetchdf().iloc[0].to_dict()
    return {"current": overview(f, db_path), "previous": overview(f.previous(), db_path),
            "channels": channels, "series": series, "devices": devices, "integrity": integrity}
