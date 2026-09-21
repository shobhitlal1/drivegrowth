-- Observed value is age-dependent; keep it separate from the fixed-horizon model.
SELECT acquisition_channel, risk_segment, policy_count, exits, exposure_months,
       monthly_margin, monthly_survival, modeled_ltv_24m,
       dense_rank() OVER (ORDER BY modeled_ltv_24m DESC) AS value_rank
FROM ltv_assumptions ORDER BY value_rank;
