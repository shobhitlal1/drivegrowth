-- One row per channel/risk cell; current-snapshot descriptive LTV assumptions.
-- Includes cancellations and nonrenewals. Exposure is right-censored at snapshot.
CREATE OR REPLACE TABLE ltv_assumptions AS
WITH survival AS (
    SELECT c.acquisition_channel, c.risk_segment,
           count(*) AS policy_count,
           count(p.cancellation_date) AS exits,
           sum(date_diff('day', p.policy_start,
               coalesce(p.cancellation_date, CAST((SELECT as_of FROM metadata) AS DATE) + 1))) / 30.4375 AS exposure_months
    FROM policies p JOIN customers c USING (customer_id)
    GROUP BY 1, 2
), economics AS (
    SELECT c.acquisition_channel, c.risk_segment,
           sum(v.commission_revenue - v.service_cost) / nullif(sum(v.active_month_fraction), 0) AS monthly_margin
    FROM monthly_customer_value v JOIN customers c USING (customer_id)
    GROUP BY 1, 2
), assumptions AS (
    SELECT *, exp(-exits / nullif(exposure_months, 0)) AS monthly_survival
    FROM survival JOIN economics USING (acquisition_channel, risk_segment)
)
SELECT *, monthly_margin *
    (1 - power(monthly_survival / power(1.08, 1.0 / 12), 24)) /
    nullif(1 - monthly_survival / power(1.08, 1.0 / 12), 0) - 7.5 AS modeled_ltv_24m
FROM assumptions;

-- Avoid fan-out: aggregate the ledger before joining to the customer dimension.
CREATE OR REPLACE TABLE customer_facts AS
WITH observed_value AS (
    SELECT customer_id, sum(contribution_margin) AS observed_contribution,
           sum(commission_revenue) AS observed_revenue
    FROM monthly_customer_value GROUP BY 1
)
SELECT c.*, q.quote_id, q.carrier_id AS quoted_carrier_id,
       coalesce(k.carrier_name, 'Not yet quoted') AS carrier_name,
       q.quote_id IS NOT NULL AS quote_started,
       q.quote_completion_date IS NOT NULL AS quote_completed,
       coalesce(q.carrier_matched, false) AS carrier_matched,
       p.policy_id IS NOT NULL AS policy_purchased,
       p.policy_id, p.policy_start, p.premium, p.commission_rate,
       p.expected_claim_cost, p.cancellation_date,
       coalesce(p.renewal_eligible, false) AS renewal_eligible,
       coalesce(p.renewed, false) AS renewed,
       m.spend / nullif(m.clicks, 0) AS allocated_spend,
       coalesce(v.observed_contribution, 0) AS observed_contribution,
       coalesce(v.observed_revenue, 0) AS observed_revenue,
       CASE WHEN p.policy_id IS NOT NULL THEN l.modeled_ltv_24m END AS modeled_ltv_24m
FROM customers c
LEFT JOIN quotes q USING (customer_id)
LEFT JOIN policies p USING (customer_id)
LEFT JOIN carriers k ON q.carrier_id = k.carrier_id
LEFT JOIN observed_value v USING (customer_id)
LEFT JOIN ltv_assumptions l USING (acquisition_channel, risk_segment)
LEFT JOIN marketing_spend m
    ON c.signup_date = m.date AND c.acquisition_channel = m.channel;

CREATE OR REPLACE VIEW monthly_operating_performance AS
SELECT v.month, c.state, c.acquisition_channel, c.carrier_name, c.customer_segment,
       sum(v.commission_revenue) AS revenue,
       sum(v.contribution_margin) AS contribution_margin,
       sum(v.premium_volume) AS premium_volume,
       count(*) AS active_policies
FROM monthly_customer_value v JOIN customer_facts c USING (customer_id)
GROUP BY 1, 2, 3, 4, 5;
