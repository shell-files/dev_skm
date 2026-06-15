# S5-B8 ROLLUP_RESPONSE_CYCLE_PER_BATCH_SCHEMA_FIX — 적용 안내

## 배경
같은 자회사가 부모로부터 **목적이 다른 rollup 요청 2개**(예: `DMA_PRECHECK` batch19,
`REPORT_DISCLOSURE` batch20)를 받으면, `ESG_ONBOARDING_CYCLE`의 UNIQUE 제약
`uk_esg_cycle(company_id, reporting_year, cycle_type)` 때문에 `ROLLUP_RESPONSE`
cycle이 1개로 강제된다. 두 번째 batch workspace 생성 시 기존 cycle과 충돌하여
**409 (ROLLUP_RESPONSE_WORKSPACE_BATCH_CONFLICT)** 가 발생하고, 이후
`/onboarding ... cycleType=ROLLUP_RESPONSE` 가 "받은 요청함 지표 범위가
초기화되지 않았습니다" 409 로 데이터 목록을 못 띄운다.

## 변경 요약
- **DB**: `uk_esg_cycle` 를 `(company_id, reporting_year, cycle_type, rollup_batch_key)`
  로 재정의. `rollup_batch_key = COALESCE(parent_rollup_batch_id, 0)` PERSISTENT
  generated column. → `ROLLUP_RESPONSE` 는 batch별 분리, NULL batch(PRE_DMA_G0 등)는
  0으로 정규화되어 기존 단일성 유지.
- **코드**: `backend/src/utils/onboardingscoperepository.py`
  `ensureRollupResponseWorkspaceTx()` 가 cycle 을 `parent_rollup_batch_id` 기준으로
  조회/생성하도록 변경. **batch 재바인딩(parent_rollup_batch_id update) 및 409 충돌
  가드 제거** — batch19 cycle은 그대로 두고 batch20용 cycle을 별도 생성한다.

## ⚠️ 적용 순서 (중요)
코드는 새 UNIQUE 제약을 전제로 `INSERT` 한다. **마이그레이션을 코드 배포 전(또는
동시)에 적용**해야 한다. 미적용 상태에서 코드만 배포하면 batch20 cycle INSERT 가
`Duplicate entry ... for key 'uk_esg_cycle'` 로 실패한다.

## 실행 정책
- **SQL 직접 실행 / DB 직접 접속 / 자동 DDL 금지.** 본 산출물은 **수동 적용용**이다.
- 적용은 DBA 또는 권한자가 백업 후 수동으로 수행한다.

## 적용 절차
1. **백업**
   ```
   mysqldump -h 192.168.0.205 -u <user> -p skm ESG_ONBOARDING_CYCLE \
     > backup_ESG_ONBOARDING_CYCLE_$(date +%Y%m%d).sql
   ```
2. **PRE-CHECK** — `*.verify.sql` 의 `[PRE-CHECK]` 블록 실행.
   - (P2) 중복 쿼리 결과가 **빈 결과** 여야 한다. (행이 나오면 적용 중단)
   - (P3) `rollup_batch_key` 컬럼이 아직 없어야 한다.
3. **적용** — `20260615_S5B8_rollup_response_cycle_per_batch.up.sql` 실행.
4. **POST-CHECK** — `*.verify.sql` 의 `[POST-CHECK]` (Q1~Q3) 로 제약/컬럼 확인.
5. **코드 배포** (이미 배포됐다면 backend 재시작).
6. **기능 검증** — `/onb?mode=ROLLUP_RESPONSE&batchId=19` 와 `&batchId=20` 모두 정상
   진입 확인 후 (Q4)(Q5) 로 cycle 2건 분리 / batch20 scope seed 확인.

## 롤백
`20260615_S5B8_rollup_response_cycle_per_batch.down.sql` 사용.
- 단, 적용 후 batch20 cycle 이 이미 생성됐다면 기존 `(company, year, cycle_type)`
  단위 중복이 되어 복원이 실패한다. down.sql 상단 `[ROLLBACK PRE-CHECK]` 가
  **빈 결과** 인지 먼저 확인하고, 아니라면 분리 생성된 batch cycle 을 정리한 뒤
  롤백한다.

## 산출물
| 파일 | 용도 |
|---|---|
| `*.up.sql` | forward DDL |
| `*.down.sql` | rollback DDL |
| `*.verify.sql` | 적용 전(PRE)/후(POST) 검증 SELECT |
| `README_S5B8_apply.md` | 본 안내 |
