-- =====================================================================
-- S5-B8 ROLLUP_RESPONSE_CYCLE_PER_BATCH_SCHEMA_FIX  (VERIFY)
-- 실행 금지 정책 유지: 아래는 검증용 SELECT 모음이다. 수동으로 확인한다.
-- =====================================================================

-- =====================================================================
-- [PRE-CHECK]  up.sql 적용 "전" 에 실행 — 모두 통과해야 적용 가능
-- =====================================================================

-- (P1) 현재 UNIQUE 제약이 (company_id, reporting_year, cycle_type) 인지 확인
SHOW INDEX FROM ESG_ONBOARDING_CYCLE WHERE Key_name = 'uk_esg_cycle';

-- (P2) 새 키(company, year, cycle_type, COALESCE(batch,0)) 기준 중복이 없어야 함.
--      => 반드시 "빈 결과" 여야 새 UNIQUE 생성이 성공한다.
SELECT
    company_id,
    reporting_year,
    cycle_type,
    COALESCE(parent_rollup_batch_id, 0) AS rollup_batch_key,
    COUNT(*) AS cnt
FROM ESG_ONBOARDING_CYCLE
GROUP BY company_id, reporting_year, cycle_type, COALESCE(parent_rollup_batch_id, 0)
HAVING COUNT(*) > 1;

-- (P3) rollup_batch_key 컬럼이 아직 없어야 함 (재적용 방지). 빈 결과여야 정상.
SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'ESG_ONBOARDING_CYCLE'
  AND COLUMN_NAME = 'rollup_batch_key';

-- (P4) 문제 사례 현황 확인 (회사 8 / 부모 6 batch19,20)
SELECT id, company_id, reporting_year, cycle_type, parent_rollup_batch_id, cycle_status, delete_yn
FROM ESG_ONBOARDING_CYCLE
WHERE company_id = 8 AND reporting_year = 2026
ORDER BY id DESC;


-- =====================================================================
-- [POST-CHECK]  up.sql 적용 "후" 에 실행
-- =====================================================================

-- (Q1) 새 UNIQUE 제약이 batch_key 를 포함하는지 확인 (4개 컬럼)
SHOW INDEX FROM ESG_ONBOARDING_CYCLE WHERE Key_name = 'uk_esg_cycle';

-- (Q2) generated column 정의 확인
SELECT COLUMN_NAME, COLUMN_TYPE, GENERATION_EXPRESSION, EXTRA
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'ESG_ONBOARDING_CYCLE'
  AND COLUMN_NAME = 'rollup_batch_key';

-- (Q3) 기존 NULL batch cycle(PRE_DMA_G0 등)은 rollup_batch_key = 0 으로 정규화됐는지
SELECT id, cycle_type, parent_rollup_batch_id, rollup_batch_key
FROM ESG_ONBOARDING_CYCLE
WHERE company_id = 8 AND reporting_year = 2026
ORDER BY id DESC;

-- (Q4) [기능 검증] 코드 배포 후 /onb?mode=ROLLUP_RESPONSE&batchId=20 진입 1회 후 실행.
--      회사 8에 batch19 / batch20 대응 ROLLUP_RESPONSE cycle 이 2건으로 분리됐는지.
--      => parent_rollup_batch_id 가 19, 20 으로 서로 달라야 한다.
SELECT id, company_id, reporting_year, cycle_type, parent_rollup_batch_id, rollup_batch_key, cycle_status
FROM ESG_ONBOARDING_CYCLE
WHERE company_id = 8
  AND reporting_year = 2026
  AND cycle_type = 'ROLLUP_RESPONSE'
ORDER BY parent_rollup_batch_id;

-- (Q5) batch20 cycle 의 metric scope 가 seed 됐는지 (active_yn = 1 행 존재)
SELECT s.esg_onboarding_cycle_id, COUNT(*) AS active_scope_cnt
FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE s
JOIN ESG_ONBOARDING_CYCLE c ON c.id = s.esg_onboarding_cycle_id
WHERE c.company_id = 8
  AND c.reporting_year = 2026
  AND c.cycle_type = 'ROLLUP_RESPONSE'
  AND c.parent_rollup_batch_id = 20
  AND s.active_yn = 1
  AND s.delete_yn = 0
GROUP BY s.esg_onboarding_cycle_id;
