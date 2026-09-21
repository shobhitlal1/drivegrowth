-- Assignment is the denominator. Never filter on a post-treatment conversion.
CREATE OR REPLACE VIEW experiment_arm_summary AS
SELECT experiment_id, variant, count(*) AS assigned,
       count(*) FILTER (WHERE outcome_observed) AS mature,
       sum(quote_completed) FILTER (WHERE outcome_observed) AS quote_completions,
       sum(policy_purchased) FILTER (WHERE outcome_observed) AS policies,
       sum(referral_sent) FILTER (WHERE outcome_observed) AS referrals_sent,
       avg(modeled_policy_value_12m) FILTER (WHERE outcome_observed) AS gross_value_per_unit,
       avg(incentive_cost) FILTER (WHERE outcome_observed) AS incentive_per_unit,
       avg(net_value_12m) FILTER (WHERE outcome_observed) AS net_value_per_unit,
       stddev_samp(net_value_12m) FILTER (WHERE outcome_observed) AS net_value_std
FROM experiments GROUP BY 1, 2;

CREATE OR REPLACE VIEW experiment_daily_results AS
WITH daily AS (
    SELECT e.experiment_id, assigned_date, variant, count(*) AS assigned,
           count(*) FILTER (WHERE outcome_observed) AS mature,
           sum(CASE WHEN r.primary = 'quote_completed' THEN e.quote_completed ELSE e.policy_purchased END)
               FILTER (WHERE outcome_observed) AS primary_successes
    FROM experiments e JOIN experiment_registry r USING(experiment_id)
    GROUP BY 1, 2, 3
)
SELECT *, sum(mature) OVER w AS cumulative_mature,
       sum(primary_successes) OVER w AS cumulative_successes,
       sum(primary_successes) OVER w / nullif(sum(mature) OVER w, 0) AS cumulative_rate
FROM daily WINDOW w AS (PARTITION BY experiment_id, variant ORDER BY assigned_date ROWS UNBOUNDED PRECEDING);
