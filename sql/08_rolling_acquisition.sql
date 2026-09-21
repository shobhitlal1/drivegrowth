-- Densify missing calendar days before using a seven-row rolling window.
WITH dates AS (
    SELECT unnest(generate_series(min(signup_date), max(signup_date), INTERVAL 1 DAY)) AS day
    FROM customers
), daily AS (
    SELECT signup_date AS day, count(*) AS customers,
           sum(policy_purchased::INT) AS policies, sum(allocated_spend) AS spend
    FROM customer_facts GROUP BY 1
), rollup AS (
    SELECT d.day, coalesce(customers, 0) AS customers, coalesce(policies, 0) AS policies,
           sum(coalesce(policies, 0)) OVER w AS seven_day_policies,
           sum(coalesce(spend, 0)) OVER w AS seven_day_spend
    FROM dates d LEFT JOIN daily USING (day)
    WINDOW w AS (ORDER BY d.day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
)
SELECT *, seven_day_spend / nullif(seven_day_policies, 0) AS seven_day_cac
FROM rollup ORDER BY day;
