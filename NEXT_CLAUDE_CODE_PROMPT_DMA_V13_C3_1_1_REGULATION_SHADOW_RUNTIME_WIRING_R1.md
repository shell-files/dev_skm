# NEXT CLAUDE CODE PROMPT
# DMA v1.3 Phase C3.1.1 — media_external.regulation Shadow Runtime Wiring
# R1

## 0. 작업 목적

현재 `feature/DAM_score_ljb` 브랜치는 Regulation Pure Screening Foundation과 Contract Micro Patch까지 완료된 상태다.

현재 원격 기준:

```text
branch:
feature/DAM_score_ljb

HEAD:
b1dfc1b413e74e9ab63316372437d327d5610517
```

현재까지 완료된 Regulation 범위:

```text
Phase C3.1
→ RegulationApplicabilityInputV13 DTO
→ RegulationSubIssueMappingSeedV13 DTO
→ step2BuildRegulationScreeningPayloads()
→ 기존 step2CalcRegulation() 재사용
→ APPROVED-only
→ activeYn fail-closed
→ duplicate fail-fast
→ deterministic sort
→ media_external 내부 source type 유지

Phase C3.1.0.1
→ companyId strict positive int
→ numeric string 차단
→ regime / applicability JSON SSOT
→ mapping subIssueCode Universe Guard
→ direct-call static guard 확대
```

DB는 아래 2개 테이블이 이미 수동 생성되어 있다.

```text
ESG_DMA_REGULATION__INPUT
ESG_DMA_REGULATION_SUB_ISSUE_MAP
```

주의:

```text
ESG_DMA_REGULATION__INPUT
                       ^^
REGULATION과 INPUT 사이의 이중 언더스코어는 의도된 실제 테이블명이다.
Repository SQL에서도 정확히 동일하게 사용한다.
```

추가로 아래 보정도 이미 DB에 적용되어 있다.

```text
ESG_DMA_SIGNAL_DETAIL.source_step
VARCHAR(30)
→ VARCHAR(80)
```

이번 Phase C3.1.1 목표:

```text
ESG_DMA_REGULATION__INPUT
+
ESG_DMA_REGULATION_SUB_ISSUE_MAP
→ APPROVED-only Repository Reader
→ step2BuildRegulationScreeningPayloads()
→ Regulation Shadow Row Serializer
→ Replace-Active Transaction
→ media_external Service Hook
→ ESG_DMA_SIGNAL_DETAIL Shadow 적재
```

완료 후 멈춰라.

---

## 1. Mandatory Architecture Invariant

### 1.1 DMA 상위 Stage

상위 Stage는 아래 3개만 유지한다.

```text
benchmark
media_external
survey
```

Regulation을 독립 Stage로 승격하지 마라.

```text
금지:
regulation_impact_score 신규 Summary 컬럼
regulation_financial_score 신규 Summary 컬럼
ESG_DMA_SCORE_SUMMARY.regulation_*
독립 regulation Stage
```

Regulation은 아래 계층이다.

```text
media_external
└─ regulation
   ├─ CSRD
   ├─ CBAM
   └─ DPP
```

### 1.2 Shadow-only 유지

이번 단계는 Regulation Shadow Runtime Wiring까지만 수행한다.

```text
Regulation Payload
→ ESG_DMA_SIGNAL_DETAIL
→ source_step = media_external_regulation_v13_shadow
→ source_type = regulation
```

이번 단계에서 금지:

```text
ESG_DMA_SCORE_SUMMARY 반영
recalcStage()
upsertStage()
recalcFinal()
updateRanks()
externalMax
Top20
Survey
KCGS 계산
KIS 계산
API 변경
Frontend 변경
DDL 변경
```

### 1.3 Rule SSOT 유지

Regulation 점수표는 기존 JSON을 재사용한다.

```text
backend/src/resources/dma/v1_3_mvp/screening_policy.json
```

Calculator는 기존 함수를 재사용한다.

```python
step2CalcRegulation(regime, applicability, policy)
```

중복 Calculator를 만들지 마라.

---

## 2. Confirmed Live DB Schema

### 2.1 Company FK

```text
ESG_COMPANY_PROFILE.company_id
→ BIGINT(20)
→ UNIQUE
```

### 2.2 Sub-Issue FK

```text
ESG_SUB_ISSUE_MASTER.sub_issue_code
→ VARCHAR(120)
→ utf8mb4_unicode_ci
→ UNIQUE
```

### 2.3 Regulation Input Table

```sql
ESG_DMA_REGULATION__INPUT
```

핵심 컬럼:

```text
id BIGINT PK
company_id BIGINT FK
reporting_year INT
regime VARCHAR(30)
applicability VARCHAR(40)
input_method VARCHAR(30)
source_document_ref VARCHAR(500)
review_status VARCHAR(20)
reviewer_comment TEXT
created_by_user_id BIGINT NULL
reviewed_by_user_id BIGINT NULL
reviewed_at DATETIME NULL
created_at DATETIME
updated_at DATETIME
delete_yn TINYINT
```

Unique Key:

```text
company_id
+
reporting_year
+
regime
```

FK:

```text
company_id
→ ESG_COMPANY_PROFILE.company_id
→ RESTRICT / RESTRICT
```

### 2.4 Regulation Mapping Table

```sql
ESG_DMA_REGULATION_SUB_ISSUE_MAP
```

핵심 컬럼:

```text
id BIGINT PK
regime VARCHAR(30)
sub_issue_code VARCHAR(120)
mapping_reason VARCHAR(1000)
source_document_ref VARCHAR(500)
active_yn TINYINT DEFAULT 0
review_status VARCHAR(20) DEFAULT DRAFT
created_by_user_id BIGINT NULL
reviewed_by_user_id BIGINT NULL
reviewed_at DATETIME NULL
created_at DATETIME
updated_at DATETIME
delete_yn TINYINT
```

Unique Key:

```text
regime
+
sub_issue_code
```

FK:

```text
sub_issue_code
→ ESG_SUB_ISSUE_MASTER.sub_issue_code
→ CASCADE / RESTRICT
```

### 2.5 Initial State

현재 두 테이블은 빈 상태다.

```text
ESG_DMA_REGULATION__INPUT
→ 0 rows

ESG_DMA_REGULATION_SUB_ISSUE_MAP
→ 0 rows
```

이번 작업에서 Seed를 넣지 마라.

---

## 3. Runtime Contract

### 3.1 Runtime Read

회사·연도별 승인 입력:

```text
ESG_DMA_REGULATION__INPUT
WHERE company_id = ?
  AND reporting_year = ?
  AND review_status = 'APPROVED'
  AND delete_yn = 0
```

활성 승인 Mapping:

```text
ESG_DMA_REGULATION_SUB_ISSUE_MAP
WHERE review_status = 'APPROVED'
  AND active_yn = 1
  AND delete_yn = 0
```

### 3.2 Runtime Build

```text
Approved Input Rows
+
Approved Active Mapping Rows
→ step2BuildRegulationScreeningPayloads()
```

### 3.3 Runtime Persist

```text
Regulation Screening Payloads
→ step4ReplaceRegulationShadowTracesTx()
→ ESG_DMA_SIGNAL_DETAIL
```

Namespace:

```text
media_external_regulation_v13_shadow
```

### 3.4 Empty State

승인 입력 또는 활성 Mapping이 없으면:

```text
payloads = []
→ Replace-Active TX 실행
→ 기존 활성 Regulation Shadow Row soft-delete
→ 신규 INSERT 없음
→ COMMIT
```

즉 빈 입력은 정상 Clear다.

### 3.5 Failure State

Reader 실패, Builder 실패, Serializer 실패, TX 실패 시:

```text
기존 활성 Regulation Shadow Set 유지
Legacy News 응답 유지
API 응답 구조 변경 없음
Warning만 출력
```

---

## 4. Preflight

Repo Root에서 실행:

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short

python -m compileall backend/src -q
python -m pytest backend/tests -q
```

Expected:

```text
branch:
feature/DAM_score_ljb

HEAD:
b1dfc1b413e74e9ab63316372437d327d5610517

전체 Backend:
502 passed
1 skipped
```

주의:

```text
- Working Tree가 깨끗하지 않으면 기존 Diff를 먼저 보고하고 멈춘다.
- reset 금지
- checkout 금지
- rebase 금지
- git add / commit / push 금지
- 실제 DB / Redis / Kafka / Docker / 외부 API 접근 금지
```

---

## 5. 반드시 읽을 파일

### 5.1 Pure Foundation

```text
backend/src/models/dmaengine.py
backend/src/services/materialities/orchestrator.py
backend/src/utils/dmascoring.py
backend/src/resources/dma/v1_3_mvp/screening_policy.json
backend/src/resources/dma/v1_3_mvp/manifest.json
```

### 5.2 Existing Shadow Runtime Pattern

```text
backend/src/utils/dmarepository.py
backend/src/services/medias/service.py
backend/src/services/benchmarks/service.py
```

특히 아래 기존 함수를 읽고 패턴을 재사용한다.

```text
_SHADOW_INSERT_SQL
step4WriteTrace()
step4ReplaceMediaNewsShadowBundleTx()
step4ReplaceBenchmarkShadowTracesTx()
runMediaCrawlAndAnalyze()
```

### 5.3 Existing Test

```text
backend/tests/test_dma_v1_3_phase_c3_1_regulation_screening_foundation.py
backend/tests/test_dma_v1_3_phase_c2_4_media_news_canonical_shadow_runtime.py
backend/tests/test_dma_v1_3_phase_c2_4_1_media_news_runtime_safety.py
```

---

## 6. 수정 허용 범위

### 6.1 Production 수정 허용

```text
backend/src/utils/dmarepository.py
backend/src/services/medias/service.py
```

필요 시 Test Surface 갱신 허용:

```text
backend/tests/test_dma_v1_3_phase_b_adapter_orchestrator.py
```

### 6.2 신규 Test 파일

```text
backend/tests/test_dma_v1_3_phase_c3_1_1_regulation_shadow_runtime.py
```

### 6.3 로컬 결과 문서

```text
docs/dma/v1_3_mvp/21_PHASE_C3_1_1_REGULATION_SHADOW_RUNTIME_RESULT.md
```

문서는 로컬 Ignore 정책에 따라 Git Status에 없어도 된다.

### 6.4 수정 금지

```text
backend/src/models/dmaengine.py
backend/src/services/materialities/orchestrator.py
backend/src/utils/dmascoring.py
backend/src/utils/dmaaggregator.py
backend/src/resources/dma/v1_3_mvp/*.json
backend/src/apis/**
frontend/**
*.sql
```

이번 단계에서는 이미 생성된 DB Table을 코드에서 읽고 쓰기만 한다.

DDL을 새로 만들거나 수정하지 마라.

---

## 7. Repository Namespace SSOT

수정:

```text
backend/src/utils/dmarepository.py
```

신규 상수:

```python
MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP = (
    "media_external_regulation_v13_shadow"
)
```

규칙:

```text
Namespace Literal은 dmarepository.py 상수 선언 1곳만 존재
service.py Literal 금지
orchestrator.py Literal 금지
test는 상수를 import하여 사용
```

---

## 8. Repository Reader

수정:

```text
backend/src/utils/dmarepository.py
```

신규 Public Reader 3개:

```python
def findRegulationRunContext(runId: int) -> dict:
    ...

def listApprovedRegulationInputs(
    companyId: int,
    reportingYear: int,
) -> list[dict]:
    ...

def listApprovedActiveRegulationMappings() -> list[dict]:
    ...
```

### 8.1 Run Context Reader

SQL:

```sql
SELECT
    id AS runId,
    company_id AS companyId,
    reporting_year AS reportingYear
FROM ESG_MATERIALITY_RUN
WHERE id = ?
  AND delete_yn = 0
```

규칙:

```text
Row 없음
→ RuntimeError
```

### 8.2 Applicability Reader

SQL:

```sql
SELECT
    company_id AS companyId,
    reporting_year AS reportingYear,
    regime,
    applicability,
    input_method AS inputMethod,
    source_document_ref AS sourceDocumentRef,
    review_status AS reviewStatus,
    reviewer_comment AS reviewerComment
FROM ESG_DMA_REGULATION__INPUT
WHERE company_id = ?
  AND reporting_year = ?
  AND review_status = 'APPROVED'
  AND delete_yn = 0
ORDER BY regime
```

규칙:

```text
- 실제 테이블명 이중 언더스코어 유지
- DTO camelCase alias로 반환
- DRAFT / REVIEWED / delete_yn=1 제외
```

### 8.3 Mapping Reader

SQL:

```sql
SELECT
    regime,
    sub_issue_code AS subIssueCode,
    mapping_reason AS mappingReason,
    active_yn AS activeYn,
    review_status AS reviewStatus
FROM ESG_DMA_REGULATION_SUB_ISSUE_MAP
WHERE review_status = 'APPROVED'
  AND active_yn = 1
  AND delete_yn = 0
ORDER BY regime, sub_issue_code
```

규칙:

```text
- source_document_ref는 현재 DTO 필드가 아니므로 Builder 입력에 넣지 않는다.
- activeYn, reviewStatus는 Builder의 fail-closed 재검증을 위해 유지한다.
```

### 8.4 Reader 원칙

```text
Repository Reader
→ 1차 APPROVED-only 필터

Pure Builder
→ 2차 Fail-Fast / Fail-Closed 검증
```

중복 검증을 제거하지 마라.

---

## 9. Regulation Shadow Serializer

수정:

```text
backend/src/utils/dmarepository.py
```

신규 Private 함수:

```python
def _buildRegulationShadowRows(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> list[tuple]:
    ...
```

책임:

```text
Regulation Screening Payload 검증
→ _SHADOW_INSERT_SQL Tuple 생성
→ DB 접근 없음
```

### 9.1 필수 검증

Top-level:

```text
payload.scorePurpose == "PRESURVEY_SCREENING"
payload.sourceChannel == "media_external"
payload.subIssueCode 존재
```

Screening Trace:

```text
screeningTrace
→ list
→ 정확히 1건

screeningTrace[0].channel
→ "regulation_" prefix

screeningTrace[0].rawInputs.sourceStep
→ "media_external"

screeningTrace[0].rawInputs.sourceType
→ "regulation"

screeningTrace[0].rawInputs.companyId
→ positive int

screeningTrace[0].rawInputs.reportingYear
→ int

screeningTrace[0].rawInputs.regime
→ 존재

screeningTrace[0].rawInputs.applicability
→ 존재
```

### 9.2 DB Row Mapping

```text
esg_materiality_run_id
= runId

evidence_id
= None

raw_issue_label
= rawInputs.regime

sub_issue_code
= payload.subIssueCode

source_step
= MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP

source_type
= "regulation"

impact_score
= screeningTrace[0].impactSignal

financial_score
= screeningTrace[0].financialSignal

confidence_score
= None

scoring_payload_json
= top-level ScoringPayloadV13 JSON
```

### 9.3 UNKNOWN / NOT_APPLICABLE

```text
UNKNOWN
→ impact_score = None
→ financial_score = None

NOT_APPLICABLE
→ impact_score = 0.0
→ financial_score = 0.0
```

`None`과 `0.0`을 혼동하지 마라.

---

## 10. Regulation Replace-Active Transaction

수정:

```text
backend/src/utils/dmarepository.py
```

신규 Public Writer 1개:

```python
def step4ReplaceRegulationShadowTracesTx(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> int:
    ...
```

### 10.1 Pre-DB Serialization

DB 연결 전에 모든 Row를 직렬화한다.

```python
rows = _buildRegulationShadowRows(runId, payloads)
```

Serializer 실패 시:

```text
getConn()
→ 호출 금지
```

### 10.2 TX 순서

```text
1. conn = getConn()
2. conn.autocommit = False
3. ESG_MATERIALITY_RUN WHERE id = ? FOR UPDATE
4. 기존 활성 Regulation Shadow Row soft-delete
5. 신규 Regulation Shadow Row INSERT
6. 활성 Row COUNT(*) 검증
7. COMMIT
8. close
```

Soft-delete SQL:

```sql
UPDATE ESG_DMA_SIGNAL_DETAIL
SET delete_yn = 1
WHERE esg_materiality_run_id = ?
  AND source_step = ?
  AND delete_yn = 0
```

Count Verify SQL:

```sql
SELECT COUNT(*) AS row_count
FROM ESG_DMA_SIGNAL_DETAIL
WHERE esg_materiality_run_id = ?
  AND source_step = ?
  AND delete_yn = 0
```

주의:

```text
COUNT(DISTINCT sub_issue_code)
→ 금지
```

이유:

```text
하나의 Sub-Issue가 CSRD와 CBAM 양쪽 Mapping에 포함될 수 있다.
Regulation Shadow는 Regime Trace를 보존해야 한다.
```

검증:

```text
row_count == len(rows)
```

### 10.3 Empty Clear

```text
payloads = []
→ 정상 TX 실행
→ 기존 활성 Row soft-delete
→ 신규 INSERT 없음
→ COUNT(*) == 0
→ COMMIT
```

### 10.4 Rollback

오류 발생:

```text
rollback
→ close
→ 기존 활성 Regulation Shadow Set 유지
```

---

## 11. Service Runtime Wiring

수정:

```text
backend/src/services/medias/service.py
```

신규 Public 함수 1개:

```python
def refreshRegulationShadowForRun(runId: int) -> int:
    ...
```

책임:

```text
1. findRegulationRunContext(runId)
2. listApprovedRegulationInputs(companyId, reportingYear)
3. listApprovedActiveRegulationMappings()
4. step2BuildRegulationScreeningPayloads(inputs, mappings)
5. step4ReplaceRegulationShadowTracesTx(runId, payloads)
6. 저장 Row 수 반환
```

Import:

```python
from src.services.materialities.orchestrator import (
    ...
    step2BuildRegulationScreeningPayloads,
)

from src.utils.dmarepository import (
    ...
    findRegulationRunContext,
    listApprovedRegulationInputs,
    listApprovedActiveRegulationMappings,
    step4ReplaceRegulationShadowTracesTx,
)
```

### 11.1 Hook 위치

`runMediaCrawlAndAnalyze()` 안에서 News 처리 블록 이후, 응답 조립 이전에 Regulation Shadow Refresh를 정확히 1회 호출한다.

권장 위치:

```python
    try:
        refreshRegulationShadowForRun(request.runId)
    except Exception as shadowError:
        print(f"Warning: media_external.regulation v1.3 shadow replace failed: {shadowError}")
```

규칙:

```text
- News Crawl 성공 여부와 독립적으로 호출
- Regulation은 News Crawl 실패 때문에 Skip되지 않음
- Regulation Shadow 실패가 News Legacy 응답을 깨뜨리지 않음
- runMediaAnalysis() 내부에서는 호출하지 않음
- 중복 호출 금지
```

### 11.2 향후 API 재사용

향후 Regulation 입력 저장·승인 API가 추가되면 아래 Public Service를 재사용한다.

```python
refreshRegulationShadowForRun(runId)
```

이번 단계에서는 API를 추가하지 마라.

---

## 12. `__all__` / Public Surface

Repository에 `__all__` 또는 Public Export 목록이 존재하면 아래를 추가한다.

```text
MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP
findRegulationRunContext
listApprovedRegulationInputs
listApprovedActiveRegulationMappings
step4ReplaceRegulationShadowTracesTx
```

Service Public 함수:

```text
refreshRegulationShadowForRun
```

과도한 신규 Helper를 추가하지 마라.

허용 신규 Production 함수 수:

```text
Repository Public Reader 3개
Repository Private Serializer 1개
Repository Public Writer 1개
Service Public Orchestrator 1개

총 6개
```

별도 Production 파일은 추가하지 마라.

---

## 13. 테스트

신규 파일:

```text
backend/tests/test_dma_v1_3_phase_c3_1_1_regulation_shadow_runtime.py
```

Fake Connection / Mock 기반 Pure Test만 작성한다.

금지:

```text
실제 DB
Docker
Redis
Kafka
외부 API
```

최소 38개 Test를 작성한다.

### 13.1 Namespace / Schema Guard

```text
#01 Regulation Namespace Literal SSOT
#02 실제 테이블명 ESG_DMA_REGULATION__INPUT 이중 언더스코어 사용
#03 잘못된 ESG_DMA_REGULATION_INPUT 문자열 0건
#04 source_step VARCHAR(80) DDL은 코드에 신규 추가하지 않음
```

### 13.2 Reader

```text
#05 Run Context alias: runId / companyId / reportingYear
#06 Run Context Row 없음 → RuntimeError
#07 Input Reader APPROVED-only SQL
#08 Input Reader delete_yn=0 SQL
#09 Input Reader DTO camelCase alias
#10 Mapping Reader APPROVED-only SQL
#11 Mapping Reader active_yn=1 SQL
#12 Mapping Reader delete_yn=0 SQL
#13 Mapping Reader deterministic ORDER BY
```

### 13.3 Serializer

```text
#14 Valid DIRECT_MANDATORY payload → row 1건
#15 raw_issue_label = regime
#16 source_step = Regulation Namespace
#17 source_type = regulation
#18 impact / financial signal 저장
#19 UNKNOWN → None / None
#20 NOT_APPLICABLE → 0.0 / 0.0
#21 scorePurpose mismatch → ValueError
#22 sourceChannel mismatch → ValueError
#23 subIssueCode 누락 → ValueError
#24 screeningTrace 누락 → ValueError
#25 screeningTrace 복수 Row → ValueError
#26 rawInputs.sourceType mismatch → ValueError
#27 rawInputs.companyId <= 0 → ValueError
```

### 13.4 Replace TX

```text
#28 pre-DB serialization 실패 → getConn 미호출
#29 getConn None → RuntimeError
#30 conn.autocommit = False
#31 ESG_MATERIALITY_RUN FOR UPDATE
#32 Regulation Namespace만 soft-delete
#33 INSERT rows
#34 COUNT(*) 검증
#35 COUNT(DISTINCT ...) 사용 금지
#36 Empty Clear → INSERT 0회 + commit
#37 Count mismatch → rollback + close
#38 Run Row 없음 → rollback + close
#39 Happy Path → commit + close
```

### 13.5 Service Hook

```text
#40 refreshRegulationShadowForRun Reader → Builder → Writer 순서
#41 Empty Approved Input → Writer([])
#42 Empty Mapping → Writer([])
#43 Reader 실패 → Writer 미호출
#44 Builder 실패 → Writer 미호출
#45 runMediaCrawlAndAnalyze() → Regulation Refresh 정확히 1회
#46 News Crawl FAILED 상태에서도 Regulation Refresh 시도
#47 Regulation Refresh 실패 → 기존 Media 응답 유지
#48 runMediaAnalysis() 내부 Regulation Refresh 호출 없음
```

### 13.6 Static Guard

```text
#49 Summary / Rank 함수 신규 호출 없음
#50 externalMax 호출 없음
#51 KCGS / KIS 변경 없음
#52 API / Frontend Diff 없음
#53 SQL / DDL Diff 없음
#54 eval / exec 없음
```

---

## 14. 정적 검증

Repo Root에서 실행:

```bash
python -m compileall backend/src -q

python -m pytest \
  backend/tests/test_dma_v1_3_phase_c3_1_regulation_screening_foundation.py \
  backend/tests/test_dma_v1_3_phase_c3_1_1_regulation_shadow_runtime.py \
  backend/tests/test_dma_v1_3_phase_c2_4_media_news_canonical_shadow_runtime.py \
  backend/tests/test_dma_v1_3_phase_c2_4_1_media_news_runtime_safety.py \
  -q

python -m pytest backend/tests -q

git diff --check
git diff --stat
git diff --name-only
git status --short
```

### 14.1 Namespace SSOT

```bash
rg -n "media_external_regulation_v13_shadow" backend/src
```

Expected:

```text
backend/src/utils/dmarepository.py
→ 상수 선언 1곳만
```

### 14.2 Table Name

```bash
rg -n "ESG_DMA_REGULATION__INPUT|ESG_DMA_REGULATION_INPUT" backend/src
```

Expected:

```text
ESG_DMA_REGULATION__INPUT
→ dmarepository.py Reader SQL 1곳 이상

ESG_DMA_REGULATION_INPUT
→ 0건
```

### 14.3 Summary / Rank 비침투

```bash
rg -n "recalcStage\(|upsertStage\(|recalcFinal\(|updateRanks\(|externalMax" \
  backend/src/services/medias/service.py \
  backend/src/utils/dmarepository.py
```

Expected:

```text
신규 Regulation 경로
→ 0건
```

기존 Legacy 함수 정의는 존재할 수 있다.
Diff 기준으로 신규 호출이 없는지 확인한다.

### 14.4 API / Frontend / SQL 비침투

```bash
git diff --name-only -- \
  backend/src/apis \
  frontend \
  "*.sql"
```

Expected:

```text
출력 없음
```

### 14.5 eval / exec

```bash
rg -n "eval\(|exec\(" backend/src
```

Expected:

```text
0건
```

---

## 15. 결과 문서

작성:

```text
docs/dma/v1_3_mvp/21_PHASE_C3_1_1_REGULATION_SHADOW_RUNTIME_RESULT.md
```

필수 내용:

```text
1. Branch
2. Baseline HEAD
3. 작업 전 git status
4. Baseline Test
5. 수정 파일 목록
6. 신규 Production 파일 수
7. 신규 Public 함수 목록
8. 신규 Private Helper 목록
9. DB Table Name
10. Double Underscore Contract
11. Regulation Namespace
12. Namespace Literal SSOT
13. Reader SQL
14. APPROVED-only Input Reader
15. APPROVED + active Mapping Reader
16. Run Context Reader
17. Serializer 검증
18. UNKNOWN None 처리
19. NOT_APPLICABLE 0.0 처리
20. Replace TX 순서
21. Empty Clear
22. Rollback
23. COUNT(*) 사용
24. COUNT(DISTINCT) 미사용
25. Service Hook 위치
26. News Crawl 독립성
27. Legacy 응답 보호
28. Summary / Rank 비침투
29. externalMax 미구현
30. KCGS / KIS 미접촉
31. API / Frontend 미수정
32. SQL / DDL 미수정
33. compileall
34. 지정 테스트
35. 전체 Backend 테스트
36. git diff --check
37. eval / exec
38. 실제 DB / Redis / Kafka / Docker / 외부 API 미접근
39. git add / commit / push 미수행
40. 다음 단계 후보
```

---

## 16. 완료 보고 형식

```text
Phase C3.1.1 완료 보고

Baseline
- branch:
- HEAD:
- 기존 전체 테스트:

Diff
- 수정 파일:
- 신규 Production 파일:
- 신규 Public 함수:
- 신규 Private Helper:

DB Contract
- Input Table:
- Mapping Table:
- Double Underscore:
- source_step VARCHAR(80):
- Seed:

Namespace
- Regulation Shadow:
- Literal SSOT:

Reader
- Run Context:
- Approved Input:
- Approved Active Mapping:
- camelCase Alias:

Serializer
- sourceChannel:
- sourceType:
- UNKNOWN:
- NOT_APPLICABLE:

Transaction
- Writer:
- Pre-DB Serialization:
- Row Lock:
- Soft Delete:
- COUNT(*):
- Empty Clear:
- Rollback:

Service Hook
- Function:
- Hook Location:
- News Crawl 독립성:
- Failure Isolation:

Guard
- Summary / Rank:
- externalMax:
- KCGS / KIS:
- API / Frontend:
- SQL / DDL:
- eval / exec:

Tests
- compileall:
- C3.1.1 신규:
- 지정 Suite:
- 전체 Backend:
- git diff --check:

Git
- status:
- add / commit / push:

다음 단계
- Phase C3.1.2 Regulation Runtime Safety Review
```

완료 후 멈춰라.

---

## 17. PASS 기준

아래를 모두 충족해야 PASS다.

```text
- Branch = feature/DAM_score_ljb
- Baseline HEAD = b1dfc1b413e74e9ab63316372437d327d5610517
- 신규 Production 파일 0
- ESG_DMA_REGULATION__INPUT 이중 언더스코어 정확히 사용
- 잘못된 ESG_DMA_REGULATION_INPUT 문자열 0건
- Regulation Namespace Literal Repository 상수 1곳
- Approved-only Input Reader
- Approved + active Mapping Reader
- Run Context Reader
- Pure Builder 재사용
- 신규 Regulation Calculator 없음
- Serializer pre-DB 검증
- UNKNOWN → None / None
- NOT_APPLICABLE → 0.0 / 0.0
- Replace-Active TX
- ESG_MATERIALITY_RUN Row Lock
- Regulation Namespace만 soft-delete
- COUNT(*) 검증
- COUNT(DISTINCT) 사용 금지
- Empty Clear 정상
- TX 실패 Rollback
- Service Hook 정확히 1회
- News Crawl 실패와 Regulation Refresh 독립
- Regulation 실패 시 기존 Media 응답 유지
- Summary 미수정
- Rank 미수정
- externalMax 미구현
- KCGS / KIS 미접촉
- API / Frontend 미수정
- SQL / DDL 미수정
- eval / exec 0건
- compileall PASS
- 전체 Backend Regression 0
- 실제 DB / Redis / Kafka / Docker / 외부 API 미접근
- git add / commit / push 미수행
```

---

## 18. 다음 단계

C3.1.1 PASS 후 바로 C3.2로 넘어가지 마라.

다음 후보:

```text
Phase C3.1.2
→ Regulation Shadow Runtime Safety Review
→ Reader Fail-Closed
→ Empty Clear
→ Duplicate Regime / Sub-Issue Trace
→ Partial Failure
→ TX Rollback
→ Service Hook 독립성
→ Shadow Read Inventory
```

C3.1.2 검토 후:

```text
Phase C3.2
→ KCGS 3개년 등급 입력
→ Pillar Signal
→ bounded boost-only Shadow
```

완료 후 멈춰라.
