-- =====================================================================
-- S5-B12 ROLLUP_RULE_SCOPE source_scope metadata 보정 (FORWARD / UP)
-- Target table : ESG_CALCULATION_RULE_SOURCE
-- Engine       : MariaDB
--
-- 문제:
--   CR_AP_E_06_G0001 의 source AP-E-06__Q0001 은 회사별 사용자 입력값(__Q 계열)인데
--   source_scope 가 CONSOLIDATED 로 잘못 설정되어, 입력 UI/readiness/calculate 에서
--   연결 결과값처럼 처리되어 계산이 실패한다.
--
-- 정책:
--   - source atomic 이 사용자 입력값이면 ENTITY.
--   - __Q 계열이거나 ESG_ATOMIC_METRIC_MASTER.onboarding_input_yn = 1 이면 ENTITY.
--   - DERIVED / ROLLUP_READONLY 이고 연결 결과를 참조하는 source 만 CONSOLIDATED 로 유지.
--
-- !! 실행 금지 정책 유지: 이 파일은 수동 적용용이다. (DB 직접 접속/자동 실행 금지)
-- !! 적용 전 반드시 백업 + verify.sql 의 [PRE-CHECK] 로 변경 대상(id 목록) 확보.
-- !! 코드(rollupcalculator/source readiness)는 이미 source_scope 기반으로 동작하므로
--    이 보정만으로 AP-E-06__Q0001 이 ENTITY 입력값으로 readiness/calculate 에 포함된다.
-- =====================================================================

UPDATE ESG_CALCULATION_RULE_SOURCE s
JOIN ESG_ATOMIC_METRIC_MASTER a
  ON a.atomic_metric_id COLLATE utf8mb4_unicode_ci
   = s.source_atomic_metric_id COLLATE utf8mb4_unicode_ci
SET s.source_scope = 'ENTITY',
    s.updated_at = CURRENT_TIMESTAMP
WHERE s.delete_yn = 0
  AND UPPER(COALESCE(s.source_scope, '')) = 'CONSOLIDATED'
  AND (
    s.source_atomic_metric_id LIKE '%__Q%'
    OR COALESCE(a.onboarding_input_yn, 0) = 1
  );
