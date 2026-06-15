-- =====================================================================
-- S5-B8 ROLLUP_RESPONSE_CYCLE_PER_BATCH_SCHEMA_FIX  (FORWARD / UP)
-- Target table : ESG_ONBOARDING_CYCLE
-- Engine       : MariaDB
-- Purpose      :
--   ROLLUP_RESPONSE onboarding cycle은 batch별 workspace이다.
--   기존 UNIQUE 제약 uk_esg_cycle(company_id, reporting_year, cycle_type)
--   때문에 같은 자회사/연도가 DMA_PRECHECK(batch19)와 REPORT_DISCLOSURE(batch20)
--   두 목적의 rollup 요청을 받으면 ROLLUP_RESPONSE cycle이 1개로 강제되어
--   두 번째 batch workspace 생성 시 409가 발생한다.
--
--   parent_rollup_batch_id를 유일 식별자에 포함시켜 batch별 cycle 공존을 허용한다.
--   단, PRE_DMA_G0 / POST_DMA_DISCLOSURE 등 parent_rollup_batch_id IS NULL 인
--   cycle_type은 MariaDB UNIQUE가 NULL을 중복 허용하므로 단일성이 깨질 수 있다.
--   이를 막기 위해 COALESCE(parent_rollup_batch_id, 0) 기반 PERSISTENT
--   generated column(rollup_batch_key)을 키에 사용한다.
--   => NULL batch는 0으로 정규화되어 cycle_type별 단일성이 그대로 유지되고,
--      ROLLUP_RESPONSE만 batch 값으로 분리된다.
--
-- !! 실행 금지 정책 유지: 이 파일은 수동 적용용이다. (DB 직접 접속/자동 DDL 금지)
-- !! 적용 전 반드시 백업 + verify.sql 의 [PRE-CHECK] 통과 확인.
-- !! 백엔드 코드(ensureRollupResponseWorkspaceTx)는 이 제약을 전제로 INSERT 하므로
--    이 마이그레이션을 코드 배포 전(또는 동시)에 적용해야 한다.
-- =====================================================================

-- 1) batch 정규화 키 컬럼 추가 (NULL -> 0)
ALTER TABLE ESG_ONBOARDING_CYCLE
    ADD COLUMN rollup_batch_key BIGINT
        AS (COALESCE(parent_rollup_batch_id, 0)) PERSISTENT
        AFTER parent_rollup_batch_id;

-- 2) 기존 UNIQUE 제약 제거
ALTER TABLE ESG_ONBOARDING_CYCLE
    DROP INDEX uk_esg_cycle;

-- 3) batch별 분리를 허용하는 새 UNIQUE 제약 생성
ALTER TABLE ESG_ONBOARDING_CYCLE
    ADD CONSTRAINT uk_esg_cycle
        UNIQUE (company_id, reporting_year, cycle_type, rollup_batch_key);
