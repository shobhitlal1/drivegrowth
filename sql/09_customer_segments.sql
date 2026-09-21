SELECT customer_segment, count(*) AS customers, sum(policy_purchased::INT) AS policies,
       avg(modeled_ltv_24m) AS ltv,
       sum(allocated_spend) / nullif(sum(policy_purchased::INT), 0) AS allocated_cac,
       sum(observed_contribution) AS observed_lifetime_contribution,
       CASE WHEN avg(modeled_ltv_24m) > (SELECT avg(modeled_ltv_24m) FROM customer_facts)
            THEN 'Above portfolio modeled value' ELSE 'Below portfolio modeled value' END AS value_context
FROM customer_facts GROUP BY 1 ORDER BY ltv DESC;
