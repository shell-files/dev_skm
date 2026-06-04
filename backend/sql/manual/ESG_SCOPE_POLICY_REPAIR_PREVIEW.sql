/*
Manual preview only. Do not execute any UPDATE from this file.

Purpose:
- Compare current ESG_ONBOARDING_CYCLE_METRIC_SCOPE.approval_policy_code
  with the metadata-derived default policy.
- No Python metric_id or atomic_metric_id hardcoding.
*/

WITH quant_input AS (
    SELECT DISTINCT
        amm.metric_id,
        amm.atomic_metric_id
    FROM ESG_ATOMIC_METRIC_MASTER amm
    WHERE amm.onboarding_input_yn = 1
      AND amm.active_yn = 1
      AND amm.delete_yn = 0
      AND UPPER(COALESCE(amm.atomic_data_role, '')) = 'INPUT'
      AND (
          UPPER(COALESCE(amm.data_value_type, '')) IN ('QUANT', 'NUMBER', 'NUMERIC')
          OR amm.data_value_type = '정량'
      )
),
rollup_source AS (
    SELECT DISTINCT
        qi.metric_id
    FROM quant_input qi
    JOIN ESG_CALCULATION_RULE cr
      ON cr.source_atomic_metric_ids LIKE CONCAT('%', qi.atomic_metric_id, '%')
     AND UPPER(COALESCE(cr.execution_scope, '')) = 'CONSOLIDATED'
     AND cr.delete_yn = 0
),
expected_policy AS (
    SELECT
        s.id AS scope_id,
        s.esg_onboarding_cycle_id AS cycle_id,
        c.cycle_type,
        s.metric_id,
        s.approval_policy_code AS current_policy,
        CASE
            WHEN NOT EXISTS (
                SELECT 1
                FROM quant_input qi
                WHERE qi.metric_id = s.metric_id
            ) THEN 'INPUT_APPROVAL_ONLY'
            WHEN EXISTS (
                SELECT 1
                FROM rollup_source rs
                WHERE rs.metric_id = s.metric_id
            ) THEN 'PROMOTE_TO_KPI_FACT_AND_ROLLUP'
            ELSE 'PROMOTE_TO_KPI_FACT'
        END AS expected_policy
    FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE s
    JOIN ESG_ONBOARDING_CYCLE c
      ON c.id = s.esg_onboarding_cycle_id
     AND c.delete_yn = 0
    WHERE s.active_yn = 1
      AND s.delete_yn = 0
)
SELECT
    cycle_id,
    cycle_type,
    metric_id,
    current_policy,
    expected_policy,
    CASE
        WHEN COALESCE(current_policy, '') <> expected_policy THEN 1
        ELSE 0
    END AS policy_changed_yn
FROM expected_policy
ORDER BY cycle_id, metric_id;
