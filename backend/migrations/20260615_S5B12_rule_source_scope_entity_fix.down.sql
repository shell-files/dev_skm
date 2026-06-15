-- =====================================================================
-- S5-B12 ROLLUP_RULE_SCOPE source_scope metadata 보정 (ROLLBACK / DOWN)
-- Target table : ESG_CALCULATION_RULE_SOURCE
-- Engine       : MariaDB
--
-- 주의: UP 은 조건에 매칭되는 모든 row 를 ENTITY 로 바꾼다. 정확한 rollback 을 위해서는
--       UP 적용 "전"에 변경 대상 row 의 (id, source_scope) 를 백업해 두어야 한다.
--       (verify.sql [PRE-CHECK] (P1) 결과를 캡처)
--
--       아래는 백업이 없을 때 사용할 "최소 안전 롤백"으로, 본 작업에서 반드시 보정해야 하는
--       CR_AP_E_06_G0001 / AP-E-06__Q0001 만 명시적으로 되돌린다.
--       (그 외 광범위 보정분까지 되돌리려면 백업 기반 복원을 사용한다.)
-- =====================================================================

-- ---------------------------------------------------------------------
-- [A] 명시 대상만 롤백 (백업 없이 안전)
-- ---------------------------------------------------------------------
UPDATE ESG_CALCULATION_RULE_SOURCE
SET source_scope = 'CONSOLIDATED',
    updated_at = CURRENT_TIMESTAMP
WHERE delete_yn = 0
  AND calculation_rule_code COLLATE utf8mb4_unicode_ci = 'CR_AP_E_06_G0001' COLLATE utf8mb4_unicode_ci
  AND source_atomic_metric_id COLLATE utf8mb4_unicode_ci = 'AP-E-06__Q0001' COLLATE utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- [B] 백업 기반 전체 롤백 (UP 전에 (id, source_scope) 를 캡처한 경우)
--     캡처해 둔 id 들에 대해 원래 source_scope 로 되돌린다. 예:
-- UPDATE ESG_CALCULATION_RULE_SOURCE SET source_scope = 'CONSOLIDATED', updated_at = CURRENT_TIMESTAMP
-- WHERE id IN ( /* UP 으로 변경된 id 목록 */ );
-- ---------------------------------------------------------------------
