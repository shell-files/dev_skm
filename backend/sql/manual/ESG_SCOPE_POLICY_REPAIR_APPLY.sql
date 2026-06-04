/*
Manual APPLY script. Do not execute in Codex.

Execute only after all conditions are satisfied:
1. ESG_SCOPE_POLICY_REPAIR_PREVIEW.sql reviewed and approved.
2. A DB backup or rollback plan exists.
3. Product owner explicitly approves scope policy repair.
4. Current cycle snapshots should receive metadata-derived default policy.

This script intentionally preserves rows with rollup_readonly_yn = 1.
*/

UPDATE ESG_ONBOARDING_CYCLE_METRIC_SCOPE s
JOIN ESG_ONBOARDING_CYCLE c
  ON c.id = s.esg_onboarding_cycle_id
 AND c.delete_yn = 0
LEFT JOIN (
    SELECT DISTINCT
        amm.metric_id
    FROM ESG_ATOMIC_METRIC_MASTER amm
    WHERE amm.onboarding_input_yn = 1
      AND amm.active_yn = 1
      AND amm.delete_yn = 0
      AND UPPER(COALESCE(amm.atomic_data_role, '')) = 'INPUT'
      AND (
          UPPER(COALESCE(amm.data_value_type, '')) IN ('QUANT', 'NUMBER', 'NUMERIC')
          OR amm.data_value_type = '정량'
      )
) qi
  ON qi.metric_id = s.metric_id
LEFT JOIN (
    SELECT DISTINCT
        amm.metric_id
    FROM ESG_ATOMIC_METRIC_MASTER amm
    JOIN ESG_CALCULATION_RULE cr
      ON UPPER(COALESCE(cr.execution_scope, '')) = 'CONSOLIDATED'
     AND cr.active_yn = 1
     AND cr.delete_yn = 0
    JOIN ESG_CALCULATION_RULE_SOURCE src
      ON src.calculation_rule_code = cr.calculation_rule_code
     AND src.source_atomic_metric_id = amm.atomic_metric_id
     AND src.delete_yn = 0
    WHERE amm.onboarding_input_yn = 1
      AND amm.active_yn = 1
      AND amm.delete_yn = 0
      AND UPPER(COALESCE(amm.atomic_data_role, '')) = 'INPUT'
      AND (
          UPPER(COALESCE(amm.data_value_type, '')) IN ('QUANT', 'NUMBER', 'NUMERIC')
          OR amm.data_value_type = '정량'
      )
) rs
  ON rs.metric_id = s.metric_id
SET s.approval_policy_code = CASE
        WHEN qi.metric_id IS NULL THEN 'INPUT_APPROVAL_ONLY'
        WHEN rs.metric_id IS NOT NULL THEN 'PROMOTE_TO_KPI_FACT_AND_ROLLUP'
        ELSE 'PROMOTE_TO_KPI_FACT'
    END,
    s.updated_at = CURRENT_TIMESTAMP
WHERE s.active_yn = 1
  AND s.delete_yn = 0
  AND COALESCE(s.rollup_readonly_yn, 0) = 0
  AND COALESCE(s.approval_policy_code, '') <> CASE
        WHEN qi.metric_id IS NULL THEN 'INPUT_APPROVAL_ONLY'
        WHEN rs.metric_id IS NOT NULL THEN 'PROMOTE_TO_KPI_FACT_AND_ROLLUP'
        ELSE 'PROMOTE_TO_KPI_FACT'
    END;
