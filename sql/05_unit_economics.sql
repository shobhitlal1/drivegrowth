-- Calendar financials: active-book revenue / current spend is a blended ratio,
-- deliberately not labeled causal advertising ROAS.
WITH revenue AS (
    SELECT month, sum(revenue) AS revenue, sum(contribution_margin) AS contribution
    FROM monthly_operating_performance GROUP BY 1
), spend AS (
    SELECT date_trunc('month', date) AS month, sum(spend) AS acquisition_cost
    FROM marketing_spend GROUP BY 1
)
SELECT r.*, s.acquisition_cost, contribution - acquisition_cost AS contribution_after_acquisition,
       contribution / nullif(revenue, 0) AS contribution_rate,
       revenue / nullif(acquisition_cost, 0) AS blended_revenue_to_spend
FROM revenue r JOIN spend s USING (month) ORDER BY month;
