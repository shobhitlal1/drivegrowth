-- Demonstrates SQL intention-to-treat aggregation and financial decomposition.
-- Inference runs in src/experimentation.py, not on rounded dashboard values.
WITH arms AS (
    SELECT e.experiment_id, e.variant, count(*) AS assigned_units,
           avg(CASE WHEN r.primary = 'quote_completed' THEN e.quote_completed ELSE e.policy_purchased END) AS primary_rate,
           avg(e.policy_purchased) AS policy_rate,
           avg(e.modeled_policy_value_12m) AS gross_value,
           avg(e.incentive_cost + e.variable_cost) AS variable_cost,
           avg(e.net_value_12m) AS net_value
    FROM experiments e JOIN experiment_registry r USING(experiment_id)
    WHERE outcome_observed GROUP BY 1, 2
), paired AS (
    SELECT c.experiment_id, c.assigned_units AS control_n, t.assigned_units AS treatment_n,
           c.primary_rate AS control_rate, t.primary_rate AS treatment_rate,
           t.primary_rate - c.primary_rate AS absolute_lift,
           (t.primary_rate - c.primary_rate) / nullif(c.primary_rate, 0) AS relative_lift,
           t.policy_rate - c.policy_rate AS policy_lift,
           t.gross_value - c.gross_value AS gross_value_delta,
           t.variable_cost - c.variable_cost AS cost_delta,
           t.net_value - c.net_value AS net_value_delta
    FROM arms c JOIN arms t USING(experiment_id)
    WHERE c.variant = 'Control' AND t.variant = 'Treatment'
)
SELECT * FROM paired ORDER BY experiment_id;
