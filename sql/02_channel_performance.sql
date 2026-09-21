WITH monthly AS (
    SELECT date_trunc('month', signup_date) AS cohort_month, acquisition_channel,
           count(*) AS customers, sum(policy_purchased::INT) AS policies,
           sum(allocated_spend) AS spend, avg(modeled_ltv_24m) AS ltv
    FROM customer_facts GROUP BY 1, 2
), economics AS (
    SELECT *, spend / nullif(policies, 0) AS cac FROM monthly
)
SELECT *, ltv / nullif(cac, 0) AS ltv_cac,
       lag(cac) OVER (PARTITION BY acquisition_channel ORDER BY cohort_month) AS previous_month_cac,
       avg(cac) OVER (PARTITION BY acquisition_channel ORDER BY cohort_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS three_month_mean_cac
FROM economics ORDER BY acquisition_channel, cohort_month;
