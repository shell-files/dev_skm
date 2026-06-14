# NEXT CLAUDE CODE PROMPT

# DMA S1 — Google Sheets Survey Response Import Runtime

# R1

## 0. 목적

C4.0에서 생성된 Google Survey MasterSheet의 응답 데이터를 Backend로 가져와 `ESG_DMA_SURVEY_RESPONSE`에 Long Format으로 저장한다.

이번 단계는 **응답 Import + DB UPSERT까지만** 수행한다.

이번 단계에서 하지 말 것:

```text
Survey Score 계산
ESG_DMA_SCORE_SUMMARY 갱신
Final Score 재계산
rank_no 재계산
Survey.jsx 결과 화면 연결
Fake Timer 제거
KPI 실시간 집계 연결
Apps Script Code.gs 수정
```

점수 계산은 다음 단계 `S2 Survey Rule-Based Scoring`에서 진행한다.

---

## 1. 작업 브랜치

현재 작업 브랜치는 GitHub Issue 연결 규칙상 아래 브랜치를 사용한다.

```text
feature/bench_api_ljb
```

작업 시작 전 반드시 실행:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git diff --name-only
```

조건:

```text
현재 브랜치가 feature/bench_api_ljb가 아니면 작업 중단
status가 clean이 아니면 작업 중단
```

금지:

```text
git add
git commit
git push
git reset
git restore
git stash
```

완료 후 diff와 테스트 결과만 보고하고 멈춘다.

---

## 2. 현재 전제

Apps Script `Code.gs`는 이미 교체 및 재배포 완료됐다.

Backend `.env`의 `APPS_SCRIPT_URL`도 신규 Web App URL로 교체 완료됐다.

C4.0 Backend는 이미 다음을 완료했다.

```text
Top20 Snapshot Freeze
ESG_DMA_SURVEY_FORM 저장
Apps Script URL 자동 생성
employee_form_url / management_form_url / external_form_url 저장
SURVEY_FORM Workflow Progress
Survey.jsx URL 생성 버튼 제거
Survey.jsx URL 조회형 UI 전환
```

이번 S1은 C4.0에서 저장된 `ESG_DMA_SURVEY_FORM.master_sheet_id`를 기준으로 Google Sheets 응답을 읽는다.

---

## 3. Apps Script MasterSheet 계약

S1 Import는 Apps Script가 생성한 MasterSheet 내부의 아래 메타 시트를 사용한다.

```text
_FORM_REGISTRY
_SELECTOR_MAP
_QUESTION_MAP
_ISSUE_MAP
_META
```

### 3.1 _FORM_REGISTRY

컬럼:

```text
respondent_group
form_id
form_url
form_name
response_sheet_name
```

용도:

```text
응답 시트명 → respondent_group 매핑
```

`respondent_group` 값:

```text
employee
management
external
```

### 3.2 _SELECTOR_MAP

컬럼:

```text
respondent_group
selector_title
selector_value
selector_label
route
```

용도:

```text
응답 시트의 selector label
→ selector_value / route 변환
```

예:

```text
employee | 현재 소속된 부서 유형을 선택해 주십시오. | finance | 재무·회계 | finance
external | 이해관계자 유형을 선택해 주십시오. | investor | 투자자·금융기관 | finance
```

경영진은 selector가 없으므로 `_SELECTOR_MAP`에 없어도 된다.

### 3.3 _QUESTION_MAP

컬럼:

```text
respondent_group
route
question_code
mapped_axis
question_type
question_title
sheet_header_title
```

용도:

```text
응답 시트 컬럼명
→ question_code / mapped_axis / question_type / route 복원
```

`mapped_axis` 값:

```text
impact
financial
ranking
common
```

### 3.4 _ISSUE_MAP

컬럼:

```text
sub_issue_code
sub_issue_name
rank_no
```

용도:

```text
Google Forms Grid row label 또는 Top5 option label
→ sub_issue_code 복원
```

### 3.5 응답 시트

Apps Script는 응답 시트명을 다음과 같이 저장해야 한다.

```text
RESP_employee
RESP_management
RESP_external
```

실제 시트명이 다를 수 있으므로 `_FORM_REGISTRY.response_sheet_name`을 SSOT로 사용한다.

---

## 4. DB 계약

기존 테이블을 사용한다.

```text
ESG_DMA_SURVEY_FORM
ESG_DMA_SURVEY_RESPONSE
```

이번 작업에서 신규 테이블 생성 금지.

### 4.1 ESG_DMA_SURVEY_RESPONSE 현재 주요 컬럼

```text
id
esg_materiality_run_id
survey_form_id
question_code
mapped_axis
respondent_group
source_response_key
respondent_user_id
department_code
sub_issue_code
answer_numeric
answer_text
normalized_score
created_at
updated_at
delete_yn
```

### 4.2 S1 시작 전 DDL 보완 필요

현재 Unique Key가 `sub_issue_code` nullable 컬럼을 직접 사용하고 있다.

MariaDB/MySQL 계열에서 UNIQUE KEY는 NULL을 중복으로 보지 않을 수 있으므로, `sub_issue_code IS NULL`인 selector/common/ranking 응답이 중복 적재될 수 있다.

따라서 S1 작업 시작 시 DB 보완 SQL 파일을 새로 만들지 말고, 작업 결과 문서에 아래 수동 SQL 적용 필요성을 기록한다.

단, 사용자가 이미 수동 반영한 경우에는 코드만 그 구조를 지원한다.

권장 DDL:

```sql
ALTER TABLE `ESG_DMA_SURVEY_RESPONSE`
  DROP INDEX `uk_dma_survey_response_source`;

ALTER TABLE `ESG_DMA_SURVEY_RESPONSE`
  ADD COLUMN `sub_issue_code_key` varchar(120)
      GENERATED ALWAYS AS (
          IFNULL(`sub_issue_code`, '')
      ) STORED
      AFTER `sub_issue_code`;

ALTER TABLE `ESG_DMA_SURVEY_RESPONSE`
  ADD UNIQUE KEY `uk_dma_survey_response_source` (
      `survey_form_id`,
      `respondent_group`,
      `source_response_key`,
      `question_code`,
      `sub_issue_code_key`
  );
```

이번 코드 구현은 아래 둘 다 지원해야 한다.

```text
sub_issue_code_key 있음
→ DB Unique Key가 강제

sub_issue_code_key 없음
→ Repository UPSERT 전에 SELECT/DELETE/UPDATE로 idempotency 보완
```

가능하면 `sub_issue_code_key` 없는 환경도 테스트에서 통과하게 한다.

---

## 5. 구현 파일 범위

신규 허용:

```text
backend/src/models/dmasurveyresponseimport.py
backend/src/utils/dmasurveyresponserepository.py
backend/src/services/surveys/importservice.py
backend/tests/test_dma_s1_survey_response_import.py
docs/dma/v1_3_mvp/30_PHASE_S1_SURVEY_RESPONSE_IMPORT_RESULT.md
```

수정 허용:

```text
backend/src/apis/survey.py
backend/src/services/surveys/service.py
```

수정 금지:

```text
frontend/**
backend/src/utils/dmasurveyformrepository.py
backend/src/services/surveys/formservice.py
backend/src/utils/dmarepository.py
backend/src/utils/dmaworkflowrepository.py
backend/src/services/materialities/orchestrator.py
backend/src/services/medias/service.py
*.sql
secrets/**
```

---

## 6. API 계약

### 6.1 Import 실행 API

추가:

```python
POST /survey/form/{runId}/responses/import
```

역할:

```text
ESG_DMA_SURVEY_FORM 조회
master_sheet_id 확인
Google Sheets 읽기
응답 Long Format 변환
ESG_DMA_SURVEY_RESPONSE UPSERT
Import 결과 반환
```

Response DTO 예:

```json
{
  "runId": 48,
  "surveyFormId": 12,
  "masterSheetId": "xxxxx",
  "importedRowCount": 420,
  "insertedCount": 350,
  "updatedCount": 70,
  "skippedCount": 0,
  "respondentCounts": {
    "employee": 100,
    "management": 20,
    "external": 45
  },
  "status": "success"
}
```

### 6.2 Import Preview API

추가:

```python
GET /survey/form/{runId}/responses/preview
```

역할:

```text
DB 저장 없이 Google Sheets를 읽어 파싱 결과 일부만 반환
```

용도:

```text
Apps Script 메타 시트 계약 검증
S1 개발 중 수동 검증
```

Response DTO 예:

```json
{
  "runId": 48,
  "surveyFormId": 12,
  "masterSheetId": "xxxxx",
  "metaSheets": {
    "formRegistry": true,
    "selectorMap": true,
    "questionMap": true,
    "issueMap": true
  },
  "responseSheets": ["RESP_employee", "RESP_management", "RESP_external"],
  "previewRows": [
    {
      "respondentGroup": "employee",
      "departmentCode": "finance",
      "questionCode": "ESG_FINANCE_RATING",
      "mappedAxis": "financial",
      "subIssueCode": "E_CLIMATE__GHG_SCOPE12_EMISSIONS",
      "answerNumeric": 5,
      "normalizedScore": 5
    }
  ]
}
```

Route 순서 주의:

```text
/survey/raw
/survey/form/{runId}
/survey/form/{runId}/retry
/survey/form/{runId}/responses/preview
/survey/form/{runId}/responses/import
/survey/{sheet_id}
```

catch-all `/{sheet_id}`보다 신규 form routes가 반드시 먼저 선언되어야 한다.

---

## 7. Google Sheets 읽기

기존 `backend/src/services/surveys/service.py`에는 `_getSheetsService()` lazy helper가 있다.

이를 재사용하거나 `importservice.py` 내부에 안전한 helper를 둔다.

요구사항:

```text
import time에 Google 인증 파일을 읽지 말 것
실제 API 호출 시점에만 build()
GOOGLE_APPLICATION_CREDENTIALS 사용
spreadsheets().values().get() 사용
```

읽어야 하는 범위:

```text
_FORM_REGISTRY!A:ZZ
_SELECTOR_MAP!A:ZZ
_QUESTION_MAP!A:ZZ
_ISSUE_MAP!A:ZZ
각 response_sheet_name!A:ZZ
```

빈 시트 / 누락 시트는 fail-fast.

---

## 8. 파싱 규칙

### 8.1 Sheet table parser

공통 함수:

```python
def _sheetValuesToDictRows(values: list[list[str]]) -> list[dict]:
    ...
```

규칙:

```text
첫 행 = header
이후 행 = data
짧은 row는 빈 문자열로 padding
중복 header 금지
blank header 금지
```

### 8.2 source_response_key

응답 Row마다 stable key를 만든다.

권장:

```text
{masterSheetId}:{responseSheetName}:{rowIndex}:{timestamp}:{email}
```

필드:

```text
timestamp
→ Google Forms 기본 타임스탬프 컬럼

email
→ 이메일 주소 컬럼 또는 Email Address 컬럼
```

timestamp/email이 없으면:

```text
{masterSheetId}:{responseSheetName}:{rowIndex}
```

단 rowIndex는 1-based physical row number를 사용한다.

### 8.3 respondent_group

`_FORM_REGISTRY.response_sheet_name`으로 response sheet를 찾고 `respondent_group`을 얻는다.

허용값:

```text
employee
management
external
```

이외 값은 reject.

### 8.4 selector / department_code

selector가 있는 그룹:

```text
employee
external
```

응답 시트에서 `_SELECTOR_MAP.selector_title`과 일치하는 컬럼을 찾는다.

응답값은 selector label이다.

`_SELECTOR_MAP`으로 변환:

```text
selector_label
→ selector_value
→ route
```

DB 저장:

```text
department_code = selector_value
```

예:

```text
재무·회계
→ finance

환경·안전
→ envSafety

투자자·금융기관
→ investor
```

management는 selector 없음:

```text
department_code = NULL
route = all
```

### 8.5 question_code / mapped_axis

응답 시트 컬럼명을 `_QUESTION_MAP.sheet_header_title`과 매칭한다.

각 질문 컬럼에서 다음을 얻는다.

```text
question_code
mapped_axis
question_type
route
```

중요:

```text
질문 title 문자열 직접 추론 금지
_QUESTION_MAP 기준으로만 매핑
```

### 8.6 Grid 응답 파싱

Google Forms Grid 응답은 환경에 따라 응답 시트 형태가 다를 수 있다.

S1은 아래 2개 형태를 모두 지원한다.

#### Case A: 컬럼 하나에 여러 row 응답이 문자열로 들어오는 경우

예:

```text
온실가스 배출량 관리: 5, 공급망 ESG 관리: 3
```

또는 줄바꿈:

```text
온실가스 배출량 관리: 5
공급망 ESG 관리: 3
```

Parser는 `issue label + score` 쌍을 분해한다.

#### Case B: Grid row별로 별도 컬럼이 생기는 경우

예:

```text
질문 제목 [온실가스 배출량 관리]
질문 제목 [공급망 ESG 관리]
```

또는 header 안에 issue label이 포함되는 경우.

Parser는 `_ISSUE_MAP.sub_issue_name`을 header에서 찾고 score를 파싱한다.

### 8.7 score 파싱

Grid score:

```text
"1" ~ "5"
1 ~ 5
```

저장:

```text
answer_numeric = decimal score
normalized_score = same score
```

범위 외:

```text
reject or skipped with reason
```

권장: fail-fast보다 row-level skip + skipped reason 수집.

단 question_code/mapped_axis/sub_issue_code 복원이 안 되는 구조적 오류는 fail-fast.

### 8.8 Top5 응답 파싱

`question_type = top5` 또는 `question_code = RANKING_TOP5`.

응답값은 복수 선택 문자열이다.

예:

```text
온실가스 배출량 관리, 공급망 ESG 관리
```

각 선택 항목을 `_ISSUE_MAP`으로 `sub_issue_code`로 변환한다.

저장:

```text
question_code = RANKING_TOP5
mapped_axis = ranking
sub_issue_code = 선택한 sub_issue_code
answer_numeric = NULL
answer_text = 원문 또는 선택 label
normalized_score = NULL
```

Top5는 S2 점수 산식에는 직접 반영하지 않는다. 보조 분석용으로만 저장한다.

---

## 9. Repository 구현

신규:

```text
backend/src/utils/dmasurveyresponserepository.py
```

공통 wrapper 금지:

```text
findOne
findAll
save
```

직접 사용:

```text
getConn()
cursor(dictionary=True)
execute()
executemany()
commit()
rollback()
close()
```

### 9.1 함수

```python
def getReadySurveyFormForRun(runId: int) -> dict:
    ...
```

조건:

```sql
SELECT ...
FROM ESG_DMA_SURVEY_FORM
WHERE esg_materiality_run_id = ?
  AND survey_status = 'READY'
  AND delete_yn = 0
```

없으면 RuntimeError.

```python
def replaceSurveyResponsesForFormTx(
    *,
    runId: int,
    surveyFormId: int,
    rows: list[dict],
) -> dict:
    ...
```

권장 정책:

```text
해당 survey_form_id의 기존 active response delete_yn = 1 처리
새 rows bulk insert
commit
```

이 방식은 단순하고, sub_issue_code NULL unique 문제를 회피한다.

단, source_response_key는 계속 저장한다.

TX 순서:

```text
1. validate runId/formId
2. validate rows
3. getConn autocommit false
4. UPDATE ESG_DMA_SURVEY_RESPONSE SET delete_yn = 1 WHERE survey_form_id = ? AND delete_yn = 0
5. INSERT new rows
6. COMMIT
```

이 방식이면 이번 S1에서는 generated column DDL이 없어도 동작한다.

주의:

```text
과거 응답 이력 보존 필요 시 delete_yn=1로 soft replace
중복 방지는 replace 방식으로 단순화
```

### 9.2 INSERT 컬럼

```sql
INSERT INTO ESG_DMA_SURVEY_RESPONSE (
    esg_materiality_run_id,
    survey_form_id,
    question_code,
    mapped_axis,
    respondent_group,
    source_response_key,
    respondent_user_id,
    department_code,
    sub_issue_code,
    answer_numeric,
    answer_text,
    normalized_score,
    delete_yn
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
```

### 9.3 Row validation

각 row 필수:

```text
runId
surveyFormId
respondentGroup
sourceResponseKey
questionCode
mappedAxis
```

Grid row 필수:

```text
subIssueCode
answerNumeric
normalizedScore
```

Top5 row 허용:

```text
answerNumeric NULL
normalizedScore NULL
answerText non-blank
```

---

## 10. Import Service 구현

신규:

```text
backend/src/services/surveys/importservice.py
```

주요 함수:

```python
def previewSurveyResponses(runId: int) -> dict:
    ...
```

```python
def importSurveyResponsesForRun(runId: int) -> dict:
    ...
```

내부 함수:

```python
def _loadWorkbookValues(masterSheetId: str) -> dict[str, list[list]]:
    ...
```

```python
def _parseMetaSheets(workbook: dict) -> dict:
    ...
```

```python
def _parseResponseSheets(
    *,
    runId: int,
    surveyFormId: int,
    masterSheetId: str,
    workbook: dict,
    meta: dict,
) -> list[dict]:
    ...
```

```python
def _parseGridAnswer(...):
    ...
```

```python
def _parseTop5Answer(...):
    ...
```

Preview는 DB 저장 금지.

Import는 `replaceSurveyResponsesForFormTx()` 호출.

---

## 11. Workflow Status

이번 S1은 별도 workflow_type을 추가하지 않는다.

이유:

```text
ESG_DMA_WORKFLOW_STATUS.workflow_type 허용값에 SURVEY_RESPONSE 없음
DB CHECK 변경 필요
이번 S1 범위에서 DDL 금지
```

Import API는 동기 실행으로 처리한다.

Post-MVP에서 필요하면 별도 workflow_type 또는 history table을 설계한다.

---

## 12. 테스트 요구사항

신규 테스트:

```text
backend/tests/test_dma_s1_survey_response_import.py
```

최소 80개.

### 12.1 Metadata parsing

```text
_FORM_REGISTRY required
_SELECTOR_MAP optional but required for selector groups
_QUESTION_MAP required
_ISSUE_MAP required
blank header reject
duplicate header reject
missing response_sheet_name reject
unknown respondent_group reject
```

### 12.2 Selector parsing

```text
employee selector label -> department_code
external selector label -> department_code
management no selector -> department_code None
unknown selector label reject
route from _SELECTOR_MAP
```

### 12.3 Question mapping

```text
sheet_header_title -> question_code
mapped_axis extracted
question_type extracted
unknown question column skipped or rejected by policy
grid question recognized
top5 question recognized
```

### 12.4 Grid parsing

```text
"이슈명: 5" parse
newline separated parse
comma separated parse
header contains issue label parse
score 1~5 valid
score 0 reject/skip
score 6 reject/skip
blank answer skipped
unknown issue label reject
```

### 12.5 Top5 parsing

```text
comma separated labels
newline separated labels
selected issue -> sub_issue_code
mapped_axis ranking
answer_numeric NULL
normalized_score NULL
answer_text set
unknown label reject
```

### 12.6 Repository

```text
getReadySurveyFormForRun validates runId
READY only
missing form RuntimeError
replace tx soft deletes old rows
bulk inserts new rows
rollback on insert failure
close always
getConn None RuntimeError
```

### 12.7 API

```text
POST /survey/form/{runId}/responses/import exists
GET /survey/form/{runId}/responses/preview exists
routes before /{sheet_id}
invalid runId -> 400
missing READY form -> 500 or 404 by policy
preview no DB write
import writes DB
```

### 12.8 Guards

```text
frontend diff 0
*.sql diff 0
dmasurveyformrepository.py diff 0
formservice.py diff 0
medias/service.py diff 0
dmarepository.py diff 0
orchestrator.py diff 0
Apps Script code not added to repo
eval/exec 없음
```

---

## 13. 검증 명령

```bash
python -m compileall backend/src -q
python -m compileall backend/tests -q

python -m pytest \
  backend/tests/test_dma_s1_survey_response_import.py \
  -q

python -m pytest \
  backend/tests/test_dma_c4_0_survey_form_auto_generation.py \
  -q
```

Static:

```bash
git diff --check
git diff --name-only

git diff -- frontend
git diff -- "*.sql"
git diff -- backend/src/utils/dmasurveyformrepository.py
git diff -- backend/src/services/surveys/formservice.py
git diff -- backend/src/services/medias/service.py
git diff -- backend/src/utils/dmarepository.py
git diff -- backend/src/services/materialities/orchestrator.py

rg -n "eval\\(|exec\\(" backend/src
rg -n "Code\\.gs|Apps Script" backend/src
```

---

## 14. 결과 문서

작성:

```text
docs/dma/v1_3_mvp/30_PHASE_S1_SURVEY_RESPONSE_IMPORT_RESULT.md
```

필수 내용:

```text
1. Branch
2. Baseline HEAD
3. Apps Script external contract
4. DB table contract
5. DDL 변경 없음
6. API 추가
7. Import service
8. Metadata sheet parser
9. Selector parser
10. Question mapper
11. Issue mapper
12. Grid parser
13. Top5 parser
14. Repository TX
15. Replace-active policy
16. Preview API
17. Import API
18. Tests
19. Guard result
20. Known limitations
21. Next phase S2
```

Known limitations:

```text
- Google Forms Grid 응답 시트 포맷은 실제 생성 결과로 추가 검증 필요
- S1은 점수 계산을 수행하지 않음
- Top5는 저장만 하고 scoring에는 미반영
- Workflow Status는 S1에서 추가하지 않음
```

---

## 15. 완료 보고 형식

```text
S1 Survey Response Import 완료 보고

Branch
- branch:
- baseline HEAD:

구현
- DTO:
- repository:
- import service:
- preview API:
- import API:

Parser
- _FORM_REGISTRY:
- _SELECTOR_MAP:
- _QUESTION_MAP:
- _ISSUE_MAP:
- grid:
- top5:

DB
- DDL diff:
- replace-active:
- inserted columns:
- delete_yn policy:

Tests
- compileall src:
- compileall tests:
- S1 tests:
- C4.0 regression:

Guards
- frontend:
- SQL:
- protected backend files:
- eval/exec:
- Apps Script code in repo:

Result
- git status:
- commit/push:
- known limitations:
- next:
```

완료 후 git add / commit / push 하지 말고 멈춘다.

---

## 16. PASS 기준

```text
Google Sheets metadata sheets parse 가능
READY survey form만 import 가능
Preview는 DB write 없음
Import는 ESG_DMA_SURVEY_RESPONSE replace-active 저장
Grid 응답 Long Format 변환
Top5 응답 Long Format 변환
selector label -> department_code 저장
question_code / mapped_axis 저장
sub_issue_code 복원
source_response_key 저장
frontend diff 0
SQL diff 0
protected backend file diff 0
compileall pass
S1 tests pass
C4.0 tests pass
git diff --check pass
git add/commit/push 없음
```
