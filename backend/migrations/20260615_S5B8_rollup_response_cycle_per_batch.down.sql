-- =====================================================================
-- S5-B8 ROLLUP_RESPONSE_CYCLE_PER_BATCH_SCHEMA_FIX  (ROLLBACK / DOWN)
-- Target table : ESG_ONBOARDING_CYCLE
-- Engine       : MariaDB
--
-- 주의: 마이그레이션 적용 이후 batch별로 분리 생성된 ROLLUP_RESPONSE cycle이
--       이미 존재한다면, 기존 UNIQUE(company_id, reporting_year, cycle_type)는
--       해당 행들 때문에 중복이 되어 복원에 실패한다.
--       (uk_esg_cycle은 delete_yn을 포함하지 않으므로 soft-delete 행도 충돌한다)
--
--       반드시 아래 [ROLLBACK PRE-CHECK]가 빈 결과여야 복원 가능하다.
--       빈 결과가 아니라면, 분리 생성된 batch cycle을 먼저 정리(물리 삭제 또는
--       parent_rollup_batch_id 정규화)한 뒤 본 롤백을 수행한다.
-- =====================================================================

-- ---------------------------------------------------------------------
-- [ROLLBACK PRE-CHECK] (반드시 빈 결과여야 함)
-- 기존 (company, year, cycle_type) 단위로 2건 이상이면 복원 불가.
-- ---------------------------------------------------------------------
-- SELECT company_id, reporting_year, cycle_type, COUNT(*) AS cnt
-- FROM ESG_ONBOARDING_CYCLE
-- GROUP BY company_id, reporting_year, cycle_type
-- HAVING COUNT(*) > 1;

-- 1) batch별 UNIQUE 제약 제거
ALTER TABLE ESG_ONBOARDING_CYCLE
    DROP INDEX uk_esg_cycle;

-- 2) 기존 UNIQUE 제약 복원
ALTER TABLE ESG_ONBOARDING_CYCLE
    ADD CONSTRAINT uk_esg_cycle
        UNIQUE (company_id, reporting_year, cycle_type);

-- 3) generated column 제거
ALTER TABLE ESG_ONBOARDING_CYCLE
    DROP COLUMN rollup_batch_key;
