# FRONT_BACK_CONTRACT_G0_ONBOARDING_DMA_v2

작성일: 2026-05-28
상태: 병렬 개발 전 front/back 계약 기준

## 1. 목적

이 문서는 G0 company profile 입력, DMA final aggregation, Company Context Modifier, selected subIssue 확정, 일반 온보딩 연결 순서를 frontend/backend가 동일하게 이해하기 위한 계약 문서다.

핵심 원칙은 다음과 같다.

- G0는 DMA 전 company profile 입력이다.
- G0는 일반 온보딩이 아니다.
- 일반 온보딩은 selected subIssue 확정 후 필요한 metrics/atomic metrics를 입력하는 단계다.
- AI는 CompanyContextProfile만 생성한다.
- Rule Engine이 modifier를 산정한다.
- DMA score/final/rank/selected issue 확정은 deterministic pipeline을 유지한다.

## 2. 사용자 흐름

```text
G0 입력
  -> DMA stage 분석 실행
  -> final aggregation
  -> Company Context Modifier 적용
  -> selected subIssue 확정
  -> selected subIssue 기반 일반 온보딩
  -> 보고서 생성
```

세부 기준:

| 단계 | 시점 | 설명 |
|---|---|---|
| G0 입력 | DMA 전 | 사업모델, 가치사슬, 보고범위, 연결범위, 규모, 제품/서비스 등 company context 입력 |
| G0 읽기 | DMA final aggregation 시점 | Company Context Profile 생성에 사용 |
| G0 활용 | selected subIssue 확정 전 | final score에만 additive modifier 반영 |
| 일반 온보딩 | selected subIssue 확정 후 | selected issue에 매핑된 `metrics_id`, `atomic_metrics_id` 입력 |

## 3. Backend Source

G0 fact 조회 source:

- `ESG_ONBOARDING_INPUT_VALUE`
- `ESG_KPI_FACT`
- `ESG_GROUP_ROLLUP_RESULT`

Context modifier source/target:

- source: `ESG_DMA_SCORE_SUMMARY` stage score columns
- source: G0 facts
- target: `ESG_DMA_CONTEXT_PROFILE.context_json`
- target: `ESG_DMA_CONTEXT_PROFILE.modifier_json`
- target: `ESG_DMA_SCORE_SUMMARY.context_impact_modifier`
- target: `ESG_DMA_SCORE_SUMMARY.context_financial_modifier`
- target: `ESG_DMA_SCORE_SUMMARY.final_*`
- target: `ESG_DMA_SCORE_SUMMARY.rank_no`

## 4. API Contract

외부 문서상 경로는 `/api/v1/...`로 표기한다. backend 내부 router는 `fastset.py` 자동 prefix 구조를 유지하므로 `APIRouter(prefix=...)`를 중복 선언하지 않는다.

### 4.1 Apply Company Context Modifier

```text
POST /api/v1/materiality/context/{runId}/apply
```

Backend internal route:

```text
POST /materiality/context/{runId}/apply
```

역할:

- G0 facts 조회
- LangGraph profiler optional 실행
- 실패/비활성/미설치 시 deterministic fallback
- CompanyContextProfile 저장
- Rule Engine으로 modifier 산정
- guard 적용
- final score/rank 재계산

Response root fields:

- runId
- contextProfileId
- companyId
- reportingYear
- implementationStatus
- profile
- modifiers
- updatedModifierCount
- recalculatedFinalCount
- modifierRange
- systemModifierRange
- stageScoreChangedYn
- messages
- rawPayload

### 4.2 Materiality Results

```text
GET /api/v1/materiality/results/{runId}
```

현재 역할:

- context modifier 적용 후 재계산된 final score/rank를 반환한다.
- UI-04~UI-07 공통 결과 데이터를 제공한다.

현재 gap:

- `rawRank`, `adjustedRank`, `guardReason`, `profileSource`, `profileConfidence`는 result API의 `items/topIssues`에는 아직 직접 포함되지 않는다.
- 해당 transparency 정보는 현재 `POST /materiality/context/{runId}/apply` response와 `ESG_DMA_CONTEXT_PROFILE.modifier_json`에 존재한다.

후속 contract 후보:

```text
GET /api/v1/materiality/context/{runId}
```

또는 `GET /api/v1/materiality/results/{runId}`에 아래 section 추가:

```json
{
  "contextModifierSummary": {
    "contextProfileId": 1,
    "profileSource": "DETERMINISTIC_FALLBACK",
    "profileConfidence": 0.88,
    "guardAppliedCount": 3,
    "modifiers": []
  }
}
```

## 5. DTO Contract

### 5.1 CompanyContextProfileDto

필드:

- runId
- companyId
- reportingYear
- profileSource: `LANGGRAPH_LLM | DETERMINISTIC_FALLBACK | HYBRID`
- confidence
- industryProfile
- businessModel
- industryExposure
- valueChainExposure
- globalCustomerExposure
- euRegulationExposure
- transitionExposure
- supplyChainDependency
- productSafetyExposure
- businessScaleExposure
- evidenceMetricIds
- evidenceAtomicMetricIds
- evidenceText
- profileSummary

AI/LangGraph는 위 profile만 생성한다. score, modifier, rank, selected issue는 생성하지 않는다.

### 5.2 SubIssueContextModifierDto

필수 transparency fields:

- subIssueCode
- profileSource
- profileConfidence
- impactModifier
- financialModifier
- contextModifier
- rawFinalImpactScore
- finalImpactScoreAfterModifier
- rawFinalFinancialScore
- finalFinancialScoreAfterModifier
- rawFinalScore
- finalScoreAfterModifier
- adjustedFinalScore
- rawRank
- adjustedRank
- rankChangedYn
- rankDelta
- guardAppliedYn
- guardReason
- appliedRules

## 6. Guard Contract

Modifier range:

```text
MVP candidate clamp: -0.3 ~ +0.3
System absolute clamp: -0.5 ~ +0.5
```

Guard reasons:

| guardReason | 조건 | 처리 |
|---|---|---|
| `NO_STAGE_OBSERVATION` | benchmark/media/survey stage score가 모두 NULL | modifier 0.0000 |
| `LOW_CONTEXT_CONFIDENCE` | profile confidence < 0.5 | modifier 0.0000 |
| `TOP5_RAW_RANK_LIMIT` | rawRank 9위 이하가 modifier만으로 Top 5 진입 | modifier 0.0000 |
| `RANK_MOVEMENT_LIMIT` | rank 이동 폭이 2단계 초과 | modifier 0.0000 |
| `RANK_MOVEMENT_LIMIT_GLOBAL` | 개별 guard 후에도 global rank 이동 폭이 2단계 초과 | 남은 active modifier 0.0000 |

MVP에서는 rank 안정성을 우선하여 modifier partial shrink가 아니라 modifier 0 처리 방식을 사용한다. UI 설명 문구는 “보정 후보가 있었지만 순위 안정성 guard로 미적용”으로 표현할 수 있다.

## 7. LangGraph Contract

LangGraph node:

```text
loadG0Facts
  -> normalizeG0Context
  -> analyzeCompanyProfileByLLM
  -> validateProfileSchema
  -> verifyProfileAgainstEvidence
  -> fallbackIfLowConfidence
  -> returnCompanyContextProfile
```

환경변수:

```text
COMPANY_CONTEXT_LLM_PROVIDER=ollama
COMPANY_CONTEXT_LLM_MODEL=qwen2.5
COMPANY_CONTEXT_LLM_TIMEOUT_SEC=60
COMPANY_CONTEXT_LLM_ENABLED=true
```

Fallback 조건:

- LLM disabled
- provider/model missing
- dependency import failure
- timeout
- invalid JSON
- schema validation failure
- weak evidence
- confidence < 0.5

Fallback은 API 실패가 아니다. deterministic builder로 profile을 생성하고 `profileSource = "DETERMINISTIC_FALLBACK"`을 반환한다.

## 8. Frontend 표시 기준

G0 입력 화면:

- DMA 전 입력 단계로 분리한다.
- “일반 온보딩” 또는 “selected issue metric input”과 섞지 않는다.

DMA 결과 화면:

- 기본 표시 점수는 context modifier 적용 후 final score/rank를 사용한다.
- context modifier 설명 패널이 필요하면 `modifier_json` 기반 fields를 표시한다.
- guard 적용 시 `guardReason`과 “미적용 사유”를 함께 표시한다.

일반 온보딩 화면:

- selected subIssue 확정 후 진입한다.
- selected issue에 연결된 metric/atomic metric만 입력 대상으로 보여준다.

## 9. Smoke Result

2026-05-28 실DB smoke:

| runId | 목적 | 결과 |
|---|---|---|
| 6 | high confidence + normal/no-stage/top5 guard | 통과 |
| 7 | low confidence guard | 통과 |
| 8 | rank movement guard | 통과 |

확인 결과:

- `ESG_DMA_CONTEXT_PROFILE` row 생성
- `context_json.graphTrace` 저장
- `modifier_json.rawRank/adjustedRank/guardReason` 저장
- `ESG_DMA_SCORE_SUMMARY.context_*_modifier` 업데이트
- `final_score/rank_no` 재계산
- benchmark/media/survey stage score 불변

추가 안정화 결과:

- 전체 FastAPI app boot smoke는 통과했다. route count는 32개다.
- `logoutModel`, `pwdCheckModel`, `userUpdateModel`, `userDeleteModel` legacy DTO import 문제를 해결했다.
- Kafka/mail optional dependency import 실패는 app boot 실패가 아니라 기능 호출 시 graceful unavailable로 처리한다.
- `company_profile.py` 내부 module prefix는 `fastset.py`에서 underscore를 hyphen으로 변환하여 외부 path `/company-profile`로 노출한다.
- materiality result API는 재계산된 final score/rank는 반환하지만 context guard transparency fields는 아직 직접 반환하지 않는다.

## 10. Open Questions

1. 결과 API에 context transparency section을 추가할지, 현재처럼 별도 `GET /materiality/context/{runId}`를 사용할지 최종 UI 선택 필요.
2. branch `feature/onborading_renewal`의 오타를 `feature/onboarding_renewal`로 정리할지 결정 필요.
3. LangGraph dependency를 `pyproject.toml`에 명시할 시점 결정 필요.

## 11. Phase1 Frontend API Samples

아래 sample의 외부 호출 경로는 `/api/v1/...`로 표기한다. backend 내부 등록 경로는 gateway/baseURL prefix를 제외한 path다.

### 11.1 GET /company-profile/g0/{companyId}

Request:

```http
GET /api/v1/company-profile/g0/6?reportingYear=2024
```

Success response:

```json
{
  "companyId": 6,
  "reportingYear": 2024,
  "g0ProfileStatus": "COMPLETED",
  "items": [
    {
      "metricId": "G0-01",
      "atomicMetricId": "G0-01__QL0001",
      "metricName": "회사 개요",
      "atomicName": "회사 개요",
      "valueText": "A_GROUP은 자동차 부품과 전동화 부품 사업을 운영한다.",
      "valueNumeric": null,
      "unit": null,
      "requiredYn": true,
      "updatedAt": "2026-05-28 20:00:00"
    }
  ],
  "missingRequiredItems": [],
  "message": "OK",
  "implementationStatus": "READY"
}
```

Empty/no data response:

```json
{
  "companyId": 6,
  "reportingYear": 2026,
  "g0ProfileStatus": "NOT_STARTED",
  "items": [],
  "missingRequiredItems": [],
  "message": "OK",
  "implementationStatus": "READY"
}
```

Error response:

```json
{ "detail": "server error message" }
```

Field 설명: `items`는 G0 master 기준 입력 항목이다. `requiredYn=true`인 항목이 모두 채워지면 `COMPLETED`다.

### 11.2 GET /company-profile/g0/{companyId}/status

Request:

```http
GET /api/v1/company-profile/g0/6/status?reportingYear=2024
```

Success response:

```json
{
  "companyId": 6,
  "reportingYear": 2024,
  "g0ProfileStatus": "COMPLETED",
  "requiredItemCount": 15,
  "completedRequiredItemCount": 15,
  "missingRequiredItemCount": 0,
  "message": "OK",
  "implementationStatus": "READY"
}
```

Empty/no data response:

```json
{
  "companyId": 6,
  "reportingYear": 2026,
  "g0ProfileStatus": "NOT_STARTED",
  "requiredItemCount": 15,
  "completedRequiredItemCount": 0,
  "missingRequiredItemCount": 15,
  "message": "OK",
  "implementationStatus": "READY"
}
```

Error response:

```json
{ "detail": "server error message" }
```

Field 설명: MVP 상태 enum은 `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `STALE`이며 `STALE`은 아직 본구현하지 않는다.

### 11.3 POST /materiality/context/{runId}/apply

Request:

```http
POST /api/v1/materiality/context/6/apply
```

Success response:

```json
{
  "runId": 6,
  "contextProfileId": 3,
  "companyId": 6,
  "reportingYear": 2024,
  "implementationStatus": "APPLIED",
  "profile": {
    "profileSource": "DETERMINISTIC_FALLBACK",
    "confidence": 0.88,
    "industryExposure": "automotive_parts_high"
  },
  "modifiers": [
    {
      "subIssueCode": "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY",
      "profileSource": "DETERMINISTIC_FALLBACK",
      "profileConfidence": 0.88,
      "impactModifier": 0.1,
      "financialModifier": 0.1,
      "rawRank": 1,
      "adjustedRank": 1,
      "guardAppliedYn": false,
      "guardReason": null
    }
  ],
  "modifierRange": { "min": -0.3, "max": 0.3 },
  "systemModifierRange": { "min": -0.5, "max": 0.5 },
  "stageScoreChangedYn": false,
  "messages": ["Context modifiers were applied only to final aggregation."]
}
```

Empty/no data response:

```json
{
  "runId": 9999,
  "implementationStatus": "NO_RUN",
  "messages": ["No ESG_MATERIALITY_RUN row found for runId."]
}
```

Error response:

```json
{ "detail": "server error message" }
```

Field 설명: `stageScoreChangedYn`은 항상 false여야 한다. context modifier는 final score/rank에만 반영된다.

### 11.4 GET /materiality/context/{runId}

Request:

```http
GET /api/v1/materiality/context/6
```

Success response:

```json
{
  "runId": 6,
  "contextProfileId": 3,
  "companyId": 6,
  "reportingYear": 2024,
  "profileSource": "DETERMINISTIC_FALLBACK",
  "profileConfidence": 0.88,
  "modifierRange": { "min": -0.3, "max": 0.3 },
  "systemModifierRange": { "min": -0.5, "max": 0.5 },
  "graphTrace": [
    {
      "node": "fallbackIfLowConfidence",
      "status": "SKIPPED",
      "message": "COMPANY_CONTEXT_LLM_ENABLED is not true."
    }
  ],
  "modifiers": [
    {
      "subIssueCode": "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP",
      "rawRank": 10,
      "adjustedRank": 10,
      "guardAppliedYn": true,
      "guardReason": "TOP5_RAW_RANK_LIMIT"
    }
  ],
  "messages": ["OK"],
  "implementationStatus": "READY"
}
```

Empty/no data response:

```json
{
  "runId": 1,
  "contextProfileId": null,
  "profile": null,
  "modifiers": [],
  "messages": ["No ESG_DMA_CONTEXT_PROFILE row found for runId."],
  "implementationStatus": "NO_CONTEXT_PROFILE"
}
```

Error response:

```json
{ "detail": "server error message" }
```

Field 설명: 프론트는 context 설명 패널/guard 안내를 이 endpoint에서 읽는다.

### 11.5 GET /materiality/results/{runId}

Request:

```http
GET /api/v1/materiality/results/6
```

Success response:

```json
{
  "runId": 6,
  "summaryRowCount": 11,
  "scoredSubIssueCount": 10,
  "selectedSubIssueCount": 5,
  "selectionSource": "RANK_FALLBACK",
  "fallbackYn": true,
  "items": [],
  "matrixItems": [],
  "topIssues": [],
  "selectionReasons": [],
  "coverageSummary": {
    "fullCount": 0,
    "partialCount": 0,
    "limitedCount": 10,
    "noDataCount": 1
  }
}
```

Empty/no data response:

```json
{
  "runId": 9999,
  "summaryRowCount": 0,
  "scoredSubIssueCount": 0,
  "selectedSubIssueCount": 0,
  "items": [],
  "matrixItems": [],
  "topIssues": []
}
```

Error response:

```json
{ "detail": "server error message" }
```

Field 설명: 이 API는 context 적용 후 final score/rank를 보여주지만 guard transparency는 직접 포함하지 않는다.

### 11.6 POST /media/news/crawl-and-analyze

Request:

```json
{
  "runId": 6,
  "sources": ["impacton", "esgeconomy"],
  "dateFrom": "2024-01-01",
  "dateTo": "2024-12-31"
}
```

Success response:

```json
{
  "runId": 6,
  "requestedSources": ["impacton", "esgeconomy"],
  "allowedSources": ["impacton", "esgeconomy"],
  "rejectedSources": [],
  "companyKeywords": ["현대자동차"],
  "industryKeywords": ["자동차부품산업"],
  "keywordSource": "MVP_SERVICE_CONSTANT",
  "collectedArticleCount": 78,
  "filteredArticleCount": 40,
  "articleCount": 40,
  "savedSignalCount": 120,
  "observedSubIssueCount": 19,
  "sourceBreakdown": [],
  "topIssues": [],
  "coverage": {},
  "coverageStatus": "LIMITED",
  "errors": []
}
```

Empty/no data response:

```json
{
  "runId": 6,
  "requestedSources": ["impacton"],
  "allowedSources": ["impacton", "esgeconomy"],
  "rejectedSources": [],
  "collectedArticleCount": 0,
  "filteredArticleCount": 0,
  "articleCount": 0,
  "savedSignalCount": 0,
  "observedSubIssueCount": 0,
  "sourceBreakdown": [
    {
      "sourceKey": "impacton",
      "sourceLabel": "임팩트온",
      "requestedYn": true,
      "executedYn": true,
      "collectedCount": 0,
      "filteredCount": 0,
      "savedSignalCount": 0,
      "status": "SUCCESS",
      "errorMessage": null
    }
  ],
  "topIssues": [],
  "coverage": {},
  "coverageStatus": "NO_DATA",
  "errors": []
}
```

Error response:

```json
{ "detail": "dateFrom must be before or equal to dateTo" }
```

Field 설명: `sources`는 배열이다. MVP 허용값은 `impacton`, `esgeconomy` 두 개이며, 동시 실행은 `["impacton", "esgeconomy"]`로 호출한다. `["all"]` 계약은 사용하지 않는다.

### 11.7 GET /materiality/media/{runId}

Request:

```http
GET /api/v1/materiality/media/6
```

Success response:

```json
{
  "runId": 6,
  "summary": {
    "articleCount": 0,
    "agencyCount": 0,
    "regulationFrameCount": 0,
    "observedSubIssueCount": 0
  },
  "sourceBreakdown": [],
  "topIssues": [],
  "evidenceSamples": [],
  "coverage": {}
}
```

Empty/no data response는 success response와 동일하게 빈 배열/0 count를 반환한다.

Error response:

```json
{ "detail": "server error message" }
```

Field 설명: Media topIssues는 final score가 아니라 `media_external` stage score 기준이다.

### 11.8 Benchmark Upload/Analyze API

Upload request:

```http
POST /api/v1/benchmk
Content-Type: multipart/form-data
file=<PDF[]>
fileType=Leader
companyName=Peer Company
page=SR
```

Upload success response:

```json
{
  "status": true,
  "message": "파일이 성공적으로 업로드되었습니다.",
  "data": {
    "files": [{ "fileName": "uuid.pdf", "origin": "report.pdf" }],
    "page": "SR"
  }
}
```

Analyze request:

```json
{
  "file": ["uuid.pdf"],
  "page": "SR",
  "esg_materiality_run_id": 6,
  "source_step": "benchmark",
  "source_type": "leader_sr"
}
```

Analyze success response:

```json
{
  "status": true,
  "message": "분석이 성공적으로 완료되었습니다.",
  "data": {}
}
```

Empty/error response:

```json
{
  "status": false,
  "message": "존재하지 않는 파일이 포함되어 있습니다: uuid.pdf",
  "data": {}
}
```

Field 설명: 분석 API는 `esg_materiality_run_id`를 받아 `ESG_DMA_SIGNAL_DETAIL`과 `ESG_DMA_SCORE_SUMMARY`로 연결한다. runId 하드코딩은 사용하지 않는다.

### 11.9 GET /materiality/benchmark/{runId}

Request:

```http
GET /api/v1/materiality/benchmark/6
```

Success response:

```json
{
  "runId": 6,
  "summary": {
    "analyzedReportCount": 0,
    "leaderReportCount": 0,
    "peerReportCount": 0,
    "ownReportCount": 0,
    "identifiedIssueCount": 0,
    "commonIssueCount": 0,
    "blindSpotCount": 0
  },
  "topIssues": [],
  "commonIssues": [],
  "blindSpotIssues": [],
  "evidenceSummary": {
    "implementationStatus": "READY_WITH_GRACEFUL_EMPTY"
  }
}
```

Empty/no data response는 success response와 동일하게 빈 배열/0 count를 반환한다.

Error response:

```json
{ "detail": "server error message" }
```

Field 설명: benchmark upload/analyze API와 result API는 분리되어 있다.

## 12. Frontend Connection Notes

Media:

- `POST /media/news/analyze`는 수동 articles smoke/fallback용이다.
- `POST /media/news/crawl-and-analyze`가 Media.jsx 메인 플로우 대상이다.
- `sources`는 배열이며 `impacton`, `esgeconomy` 두 source를 동시에 보낼 수 있다.
- 실제 사이트 HTML이 crawler regex와 맞지 않으면 `collectedArticleCount=0` 또는 `filteredArticleCount=0`이 될 수 있다. 이 경우 UI는 실패가 아니라 empty state로 표시한다.

Benchmark:

- `POST /benchmk`는 upload, `PUT /benchmk`는 analyze다.
- `PUT /benchmk` request의 `esg_materiality_run_id`가 DMA run 연결 키다.
- 결과 조회는 `GET /materiality/benchmark/{runId}`를 사용한다.

Context:

- 적용은 `POST /materiality/context/{runId}/apply`.
- 재조회는 `GET /materiality/context/{runId}`.
- context가 없으면 404가 아니라 `200 + implementationStatus="NO_CONTEXT_PROFILE"`이다.

## 13. Backend Utility: getG0FinancialBasis()

`getG0FinancialBasis()`는 프론트 직접 호출 API가 아니라 DMA financial scoring redesign을 위한 backend repository utility다.

위치:

```text
backend/src/utils/dmafinancialrepository.py
```

목적:

- G0-02 재무 기준값을 companyId/reportingYear 기준으로 안정 조회한다.
- G0 입력, KPI fact, group rollup 결과 중 우선순위에 따라 하나의 basis source를 선택한다.
- 이후 financial scoring redesign에서 adapter가 사용할 재무 기준값 contract를 고정한다.

금지 원칙:

- `metric_id='G0-02'`만 사용한다.
- AP-E-06 등 selected subIssue 이후 본 온보딩 지표를 사용하지 않는다.
- G atomic과 Q atomic을 동시에 합산하지 않는다.
- 현재 단계에서는 `dmascoring.py`, `dmaaggregator.py`, media/benchmark adapter를 수정하지 않는다.

Source priority:

```text
preferConsolidated=true
1. GROUP_ROLLUP_RESULT_G
2. KPI_FACT_G
3. KPI_FACT_Q
4. ONBOARDING_INPUT_Q

preferConsolidated=false
1. KPI_FACT_Q
2. ONBOARDING_INPUT_Q
3. GROUP_ROLLUP_RESULT_G
4. KPI_FACT_G
```

Return contract 요약:

```json
{
  "companyId": 6,
  "reportingYear": 2025,
  "basisType": "CONSOLIDATED",
  "basisSource": "ESG_GROUP_ROLLUP_RESULT",
  "fallbackUsedYn": false,
  "unit": "KRW",
  "revenue": 12300000000000,
  "operatingProfit": 800000000000,
  "netIncome": 500000000000,
  "capex": 900000000000,
  "depreciation": 300000000000,
  "missingFields": [],
  "sourceRows": [
    {
      "sourceTable": "ESG_GROUP_ROLLUP_RESULT",
      "sourcePriority": "GROUP_ROLLUP_RESULT_G",
      "atomicMetricId": "G0-02__G0001",
      "fieldName": "revenue",
      "valueNumeric": 12300000000000,
      "unit": "KRW",
      "updatedAt": "2026-05-29T00:00:00"
    }
  ],
  "trace": {
    "selectedPriority": "GROUP_ROLLUP_RESULT_G",
    "partialBasisYn": false,
    "reason": "preferConsolidated=true and consolidated G values exist"
  }
}
```

Empty/no data:

```json
{
  "basisType": "NONE",
  "basisSource": null,
  "fallbackUsedYn": true,
  "missingFields": ["revenue", "operatingProfit", "netIncome", "capex", "depreciation"],
  "sourceRows": [],
  "trace": {
    "selectedPriority": "NONE",
    "reason": "No G0-02 financial basis rows found"
  }
}
```
