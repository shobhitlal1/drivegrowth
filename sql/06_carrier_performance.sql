SELECT carrier_name, state, risk_segment, count(quote_id) AS quotes,
       sum(policy_purchased::INT) AS policies,
       sum(policy_purchased::INT)::DOUBLE / nullif(count(quote_id), 0) AS quote_conversion,
       avg(premium) AS annual_premium, avg(modeled_ltv_24m) AS modeled_ltv,
       avg(expected_claim_cost / nullif(premium, 0)) AS carrier_expected_loss_ratio,
       rank() OVER (PARTITION BY state, risk_segment ORDER BY avg(modeled_ltv_24m) DESC) AS state_risk_value_rank
FROM customer_facts WHERE quote_started GROUP BY 1, 2, 3
HAVING count(quote_id) >= 100 ORDER BY state, risk_segment, state_risk_value_rank;
