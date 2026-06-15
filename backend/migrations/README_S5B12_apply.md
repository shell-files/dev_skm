# S5-B12 ROLLUP_RULE_SCOPE_AND_YOY_BASELINE_POLICY_FIX — 적용 안내

## 구성
이 작업은 **DB 보정(파트 1)** 과 **코드 수정(파트 2)** 으로 나뉜다.

### 파트 1 — source_scope metadata 보정 (DB, 수동 적용)
`CR_AP_E_06_G0001` 의 source `AP-E-06__Q0001` 은 회사별 사용자 입력값(`__Q` 계열)인데
`source_scope=CONSOLIDATED` 로 잘못 설정되어 readiness/calculate 에서 연결 결과값처럼
처리되어 계산이 실패한다. 사용자 입력값(`__Q` 또는 `onboarding_input_yn=1`)을 `ENTITY` 로 보정한다.

| 파일 | 용도 |
|---|---|
| `20260615_S5B12_rule_source_scope_entity_fix.up.sql` | forward UPDATE |
| `...down.sql` | rollback (명시 대상 / 백업 기반) |
| `...verify.sql` | PRE/POST 검증 SELECT |

### 파트 2 — YoY prior baseline 정책 (코드, 적용 완료)
전년도 연결 baseline 부재 시 전체 batch 422 대신 해당 YoY rule 만 `BASELINE_REQUIRED`
(non-blocking)으로 분리한다. 코드 변경은 이미 반영됨:
- `backend/src/utils/rollupcalculator.py`
  - `STATUS_BASELINE_REQUIRED` / `NON_BLOCKING_STATUSES` 추가
  - `evaluateAtomicAtYear(..., sourceTiming)` — **PRIOR + CONSOLIDATED 는 producer 재계산보다
    persisted baseline(ESG_GROUP_ROLLUP_RESULT) 우선**
  - `resolveConsolidatedSourceAtYear` — 값 없으면 `BASELINE_REQUIRED` + `requiredReportingYear` trace
  - rule 루프 — `BASELINE_REQUIRED`/`NOT_APPLICABLE` 은 warning 만 남기고 batch 계속
- `backend/src/services/rollups/service.py` `calcBatch`
  - **CALCULATED 결과만** `upsertGroupRollupResultsTx` 로 저장 (baseline_required 는 미저장)
  - response 에 `warnings` 포함
- `backend/src/models/rollup.py`
  - `RollupResultDto.calculationStatus`, `RollupCalculateStatusDto.warnings` 추가

## 실행 정책
- **SQL 직접 실행 / DB 직접 접속 / 자동 실행 금지.** 파트 1 은 수동 적용용이다.
- 적용은 DBA 또는 권한자가 백업 후 수동 수행한다.

## 파트 1 적용 절차
1. **백업**
   ```
   mysqldump -h 192.168.0.205 -u <user> -p skm ESG_CALCULATION_RULE_SOURCE \
     > backup_ESG_CALCULATION_RULE_SOURCE_$(date +%Y%m%d).sql
   ```
2. **PRE-CHECK** — `verify.sql` `[PRE-CHECK]` (P1) 실행 후 결과(특히 `id`, `source_scope`)를
   **캡처**한다. (rollback 백업용)
3. **적용** — `...up.sql` 실행.
4. **POST-CHECK** — `verify.sql` `[POST-CHECK]`
   - (Q1) `AP-E-06__Q0001` `source_scope = ENTITY`
   - (Q2) 잔여 잘못된 CONSOLIDATED **0건**
   - (Q3) `AP-E-06__Q0001` 회사 6/7/8/9 ENTITY/approved fact 존재
   - (Q4) `E1-06__G0003` 2025 baseline 유무 확인
5. **기능 검증** — `POST /api/v1/rollups/batches/{batchId}/calculate`
   - `AP-E-06__G0001` 계산 성공 (회사별 `AP-E-06__Q0001` 합산)
   - `E1-06__G0004` 는 2025 baseline 없으면 `warnings` 에 `BASELINE_REQUIRED` (전체 422 아님)

## 롤백
`...down.sql`.
- 백업이 있으면 [B] 백업 기반(변경된 `id` 목록)으로 정확히 복원.
- 백업이 없으면 [A] `CR_AP_E_06_G0001` / `AP-E-06__Q0001` 만 안전 복원.

## 완료 기준 매핑
- 파트1: `CR_AP_E_06_G0001 / AP-E-06__Q0001 source_scope = ENTITY`, AP-E-06__G0001 회사별 합산 계산
- 파트2: 전년도 baseline 없을 때 CR_E1_06_G0004 가 batch 422 유발 안 함, 계산 가능 결과는 저장,
  YoY 만 `baselineRequired` warning(metric/atomic/year/sourceScope/missingConsolidatedSource 포함)
