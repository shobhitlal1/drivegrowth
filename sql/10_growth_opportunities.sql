-- Transparent screening, not a causal recommendation or budget optimizer.
WITH channel_metrics AS (
    SELECT acquisition_channel, count(*) AS visitors, sum(policy_purchased::INT) AS policies,
           sum(allocated_spend) / nullif(sum(policy_purchased::INT), 0) AS cac,
           avg(modeled_ltv_24m) AS ltv
    FROM customer_facts GROUP BY 1
), ranked AS (
    SELECT *, ltv / nullif(cac, 0) AS value_ratio,
           percent_rank() OVER (ORDER BY ltv / nullif(cac, 0)) AS value_percentile
    FROM channel_metrics
)
SELECT *, CASE WHEN policies < 100 THEN 'Insufficient sample'
               WHEN value_ratio < 3 THEN 'Review acquisition costs and retention'
               WHEN value_percentile >= .75 THEN 'Test incremental channel capacity'
               ELSE 'Monitor marginal economics' END AS investigation
FROM ranked ORDER BY value_ratio DESC;
