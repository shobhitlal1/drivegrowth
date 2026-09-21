-- Event-grain source deduplicated to customer-grain milestones before aggregation.
WITH milestones AS (
    SELECT customer_id,
           bool_or(event_type = 'quote_started') AS started,
           bool_or(event_type = 'quote_completed') AS completed,
           bool_or(event_type = 'carrier_matched') AS matched,
           bool_or(event_type = 'policy_purchased') AS purchased
    FROM funnel_events GROUP BY 1
)
SELECT c.device_type, c.acquisition_channel, count(*) AS visitors,
       sum(started::INT) AS starts, sum(completed::INT) AS completions,
       sum(matched::INT) AS matches, sum(purchased::INT) AS policies,
       sum(completed::INT)::DOUBLE / nullif(sum(started::INT), 0) AS completion_rate,
       sum(purchased::INT)::DOUBLE / nullif(sum(matched::INT), 0) AS match_to_policy_rate
FROM customers c JOIN milestones m USING (customer_id)
GROUP BY 1, 2 ORDER BY visitors DESC;
