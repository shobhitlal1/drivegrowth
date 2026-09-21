"""Validate structural, financial and intentionally simulated relationships."""
from __future__ import annotations
import json
from pathlib import Path
from src.config import ROOT, DB_PATH
from src.database import connect


def validate(db_path: Path = DB_PATH) -> dict:
    checks = {}
    with connect(db_path) as con:
        zero_queries = {
            "unique_customers": "SELECT count(*) - count(DISTINCT customer_id) FROM customers",
            "unique_customer_mart": "SELECT count(*) - count(DISTINCT customer_id) FROM customer_facts",
            "unique_policies": "SELECT count(*) - count(DISTINCT customer_id) FROM policies",
            "unique_monthly_value": "SELECT count(*) - count(DISTINCT (customer_id, month)) FROM monthly_customer_value",
            "policy_foreign_keys": "SELECT count(*) FROM policies p ANTI JOIN customers c USING(customer_id)",
            "event_foreign_keys": "SELECT count(*) FROM funnel_events e ANTI JOIN customers c USING(customer_id)",
            "quote_foreign_keys": "SELECT count(*) FROM quotes q ANTI JOIN customers c USING(customer_id)",
            "carrier_foreign_keys": "SELECT count(*) FROM quotes q ANTI JOIN carriers k USING(carrier_id)",
            "ledger_foreign_keys": "SELECT count(*) FROM monthly_customer_value v ANTI JOIN policies p USING(policy_id)",
            "event_censoring": "SELECT count(*) FROM funnel_events WHERE event_timestamp >= (SELECT as_of + 1 FROM metadata)",
            "event_chronology": "SELECT count(*) FROM (SELECT customer_id, min(CASE WHEN event_type='quote_started' THEN event_timestamp END) AS started, min(CASE WHEN event_type='quote_completed' THEN event_timestamp END) AS completed, min(CASE WHEN event_type='policy_purchased' THEN event_timestamp END) AS purchased FROM funnel_events GROUP BY 1) WHERE completed < started OR purchased < completed",
            "nested_funnel": "SELECT count(*) FROM customer_facts WHERE (policy_purchased AND NOT carrier_matched) OR (carrier_matched AND NOT quote_completed) OR (quote_completed AND NOT quote_started)",
            "nonnegative_spend": "SELECT count(*) FROM marketing_spend WHERE spend < 0 OR clicks > impressions",
            "complete_spend_allocation": "SELECT count(*) FROM customer_facts WHERE allocated_spend IS NULL",
            "ledger_margin_identity": "SELECT count(*) FROM monthly_customer_value WHERE abs(contribution_margin - (commission_revenue - service_cost - onboarding_cost)) > 0.00001",
            "renewals_are_mature": "SELECT count(*) FROM policies WHERE renewed AND (NOT renewal_eligible OR policy_start + INTERVAL 365 DAY > (SELECT as_of FROM metadata))",
            "cancellations_after_start": "SELECT count(*) FROM policies WHERE cancellation_date <= policy_start",
            "no_ledger_after_cancellation": "SELECT count(*) FROM monthly_customer_value v JOIN policies p USING(policy_id) WHERE v.month >= p.cancellation_date",
        }
        for name, query in zero_queries.items():
            failures = con.execute(query).fetchone()[0]
            checks[name] = {"passed": failures == 0, "violations": failures}
        delta = con.execute("SELECT (SELECT sum(spend) FROM marketing_spend) - (SELECT sum(allocated_spend) FROM customer_facts)").fetchone()[0]
        checks["spend_reconciles_to_source"] = {"passed": abs(delta) < .01, "difference": delta}
        policy_delta = con.execute("SELECT (SELECT count(*) FROM policies) - (SELECT sum(policy_purchased::INT) FROM customer_facts)").fetchone()[0]
        checks["policies_reconcile_to_source"] = {"passed": policy_delta == 0, "difference": policy_delta}
        desktop, mobile = con.execute("SELECT avg(quote_completed::INT) FILTER(WHERE device_type='Desktop' AND quote_started), avg(quote_completed::INT) FILTER(WHERE device_type='Mobile' AND quote_started) FROM customer_facts").fetchone()
        checks["simulated_mobile_friction"] = {"passed": desktop > mobile, "desktop": desktop, "mobile": mobile}
        referral, social = con.execute("SELECT avg(modeled_ltv_24m) FILTER(WHERE acquisition_channel='Referral'), avg(modeled_ltv_24m) FILTER(WHERE acquisition_channel='TikTok / Social') FROM customer_facts").fetchone()
        checks["simulated_retention_value"] = {"passed": referral > social, "referral_ltv": referral, "social_ltv": social}
        counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                  for t in ["customers", "quotes", "policies", "funnel_events", "monthly_customer_value"]}
    return {"all_passed": all(c["passed"] for c in checks.values()), "checks": checks, "row_counts": counts}


if __name__ == "__main__":
    report = validate()
    output = ROOT / "docs" / "validation_report.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{sum(c['passed'] for c in report['checks'].values())}/{len(report['checks'])} data checks passed.")
    if not report["all_passed"]:
        raise SystemExit(json.dumps(report, indent=2))
