-- Include only policyholders old enough to be evaluated at each horizon.
-- Recent/censored policies are not failures; early cancellations remain failures.
WITH horizons AS (SELECT unnest([30, 60, 90, 180, 365]) AS days), eligible AS (
    SELECT date_trunc('month', p.policy_start) AS cohort, h.days,
           p.cancellation_date IS NULL OR p.cancellation_date > p.policy_start + h.days * INTERVAL 1 DAY AS retained
    FROM policies p CROSS JOIN horizons h CROSS JOIN metadata m
    WHERE p.policy_start + h.days * INTERVAL 1 DAY <= m.as_of
)
SELECT cohort, days, count(*) AS eligible_policies, sum(retained::INT) AS retained_policies,
       avg(retained::INT) AS retention_rate
FROM eligible GROUP BY 1, 2 ORDER BY 1, 2;
