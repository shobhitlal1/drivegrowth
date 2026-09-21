WITH states AS (
    SELECT state, count(*) AS customers, sum(policy_purchased::INT) AS policies,
           sum(allocated_spend) AS allocated_spend,
           avg(premium) AS annual_premium, avg(modeled_ltv_24m) AS ltv
    FROM customer_facts GROUP BY 1
)
SELECT *, allocated_spend / nullif(policies, 0) AS allocated_cac,
       ltv * policies / nullif(allocated_spend, 0) AS ltv_cac,
       policies / sum(policies) OVER () AS policy_share
FROM states ORDER BY ltv_cac DESC;
