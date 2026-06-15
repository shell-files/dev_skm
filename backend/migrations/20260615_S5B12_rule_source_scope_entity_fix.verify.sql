-- =====================================================================
-- S5-B12 source_scope 보정 (VERIFY)
-- 실행 금지 정책 유지: 아래는 검증용 SELECT 모음이다. 수동으로 확인한다.
-- =====================================================================

-- =====================================================================
-- [PRE-CHECK]  up.sql 적용 "전"
-- =====================================================================

-- (P1) 보정 대상 목록 — 적용 전 반드시 캡처(rollback 백업용).
--      __Q 계열이거나 onboarding_input_yn=1 인데 source_scope=CONSOLIDATED 인 잘못된 row.
SELECT
  s.id,
  s.calculation_rule_code,
  r.metric_id,
  r.target_atomic_metric_id,
  r.formula_type,
  s.source_atomic_metric_id,
  s.source_scope,
  a.atomic_data_role,
  a.onboarding_input_yn
FROM ESG_CALCULATION_RULE_SOURCE s
JOIN ESG_CALCULATION_RULE r
  ON r.calculation_rule_code COLLATE utf8mb4_unicode_ci
   = s.calculation_rule_code COLLATE utf8mb4_unicode_ci
LEFT JOIN ESG_ATOMIC_METRIC_MASTER a
  ON a.atomic_metric_id COLLATE utf8mb4_unicode_ci
   = s.source_atomic_metric_id COLLATE utf8mb4_unicode_ci
WHERE s.delete_yn = 0
  AND r.delete_yn = 0
  AND UPPER(COALESCE(r.execution_scope, '')) = 'CONSOLIDATED'
  AND UPPER(COALESCE(s.source_scope, '')) = 'CONSOLIDATED'
  AND (
    s.source_atomic_metric_id LIKE '%__Q%'
    OR COALESCE(a.onboarding_input_yn, 0) = 1
  )
ORDER BY r.metric_id, s.calculation_rule_code, s.source_atomic_metric_id;


-- =====================================================================
-- [POST-CHECK]  up.sql 적용 "후"
-- =====================================================================

-- (Q1) CR_AP_E_06_G0001 / AP-E-06__Q0001 source_scope = ENTITY 확인 (검증 1)
SELECT
  r.calculation_rule_code,
  r.metric_id,
  r.target_atomic_metric_id,
  r.formula_type,
  s.source_atomic_metric_id,
  s.source_scope
FROM ESG_CALCULATION_RULE r
JOIN ESG_CALCULATION_RULE_SOURCE s
  ON s.calculation_rule_code COLLATE utf8mb4_unicode_ci
   = r.calculation_rule_code COLLATE utf8mb4_unicode_ci
WHERE r.calculation_rule_code = 'CR_AP_E_06_G0001'
  AND s.delete_yn = 0;
-- 기대: AP-E-06__Q0001 / source_scope = ENTITY

-- (Q2) (P1) 잔여 0건 확인 — 보정 후 잘못된 CONSOLIDATED 가 남지 않아야 함. 빈 결과여야 정상.
SELECT s.id, s.calculation_rule_code, s.source_atomic_metric_id, s.source_scope
FROM ESG_CALCULATION_RULE_SOURCE s
LEFT JOIN ESG_ATOMIC_METRIC_MASTER a
  ON a.atomic_metric_id COLLATE utf8mb4_unicode_ci
   = s.source_atomic_metric_id COLLATE utf8mb4_unicode_ci
WHERE s.delete_yn = 0
  AND UPPER(COALESCE(s.source_scope, '')) = 'CONSOLIDATED'
  AND (
    s.source_atomic_metric_id LIKE '%__Q%'
    OR COALESCE(a.onboarding_input_yn, 0) = 1
  );

-- (Q3) AP-E-06__Q0001 회사별 ENTITY fact 확인 (검증 2)
SELECT company_id, reporting_year, atomic_metric_id, company_scope_type,
       approval_status, value_numeric, value_text, unit, delete_yn
FROM ESG_KPI_FACT
WHERE company_id IN (6,7,8,9)
  AND reporting_year = 2026
  AND atomic_metric_id = 'AP-E-06__Q0001'
ORDER BY company_id;
-- 기대: 6,7,8,9 모두 ENTITY / approved / delete_yn=0

-- (Q4) E1-06__G0003 연결 baseline 존재 여부 (검증 3) — 2025 없으면 CR_E1_06_G0004 는 BASELINE_REQUIRED
SELECT esg_rollup_batch_id, reporting_year, parent_company_id, group_metric_id,
       group_atomic_metric_id, value_numeric, unit, rollup_status, delete_yn
FROM ESG_GROUP_ROLLUP_RESULT
WHERE parent_company_id = 6
  AND reporting_year IN (2025, 2026)
  AND group_atomic_metric_id = 'E1-06__G0003'
  AND delete_yn = 0
ORDER BY reporting_year, id DESC;
