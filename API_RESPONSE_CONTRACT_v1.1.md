# API Response Contract v1.1

## 1. 문서 목적

본 문서는 SKM ESG 지속가능경영보고서 AI 자동 생성 MVP의 9개 UI 화면에 필요한 API Response Contract를 고정하기 위한 설계 문서다.

이 문서의 기준 입력은 다음과 같다.

- `SKM_MVP_UI_API_기능정의서_v2.xlsx`
- `ANTIGRAVITY_UI_API_REQUIREMENTS_v1.md`
- 현재 레포의 backend/frontend 코드 분석 결과
- `SKM_ESG_v5_2_CLEAN_SCHEMA_v2_MariaDB.sql`
- `SKM_ESG_v5_2_DROP_ESG_FOR_CLEAN_SCHEMA_v2.sql`
- `SKM_ESG_v5_2_CLEAN_SCHEMA_v2_ONBOARDING_ONLY_SEED_company6789_COLLATION_FIXED.sql`
- 운영 DB 추가 컬럼: `ESG_DMA_SIGNAL_DETAIL.scoring_payload_json LONGTEXT NULL`

목표는 React 구현 전에 9개 화면이 요구하는 데이터를 API 단위로 확정하고, 현재 API로 제공 가능한 필드와 추가 구현이 필요한 필드를 분리하는 것이다. 본 문서 승인 전에는 backend API 구현 및 React mock 제거 작업을 진행하지 않는다.

### 1.1 v1.1 확정 결정사항

v1.1은 v1 검토 후 Open Questions에 대한 결정사항을 반영한 구현 착수용 Contract다.

| question | v1.1 결정 |
|---|---|
| API prefix | 외부 문서상 `/api/v1/...`를 유지한다. backend 내부 `APIRouter`에는 `/api/v1`, `/materiality`, `/media`, `/report` prefix를 중복 선언하지 않는다. `/api/v1`은 gateway/nginx/proxy 또는 frontend baseURL에서 처리한다고 가정한다. |
| 최종 선정 수 | MVP 보고서 생성 대상은 Top 5, 전체 결과 표/매트릭스는 Top 10까지 표시 가능하다. `selectedSubIssueCount` 기본값은 5다. |
| selected fallback | `ESG_MATERIALITY_SELECTED_SUB_ISSUE`가 비어 있으면 `ESG_DMA_SCORE_SUMMARY.rank_no` 기준 Top 5를 fallback 선정으로 사용한다. response에 `selectionSource = "TABLE" | "RANK_FALLBACK"`, `fallbackYn`을 포함한다. |
| survey denominator | 별도 target table이 없으므로 service-level default target을 허용한다. 기본값은 임직원 150, 경영진 20, 외부 이해관계자 80이며 `targetSource = "MVP_DEFAULT"`를 포함한다. |
| survey axis | v1에서는 survey score를 impact/financial에 동일하게 채우고 DTO field는 분리 유지한다. response에 `axisSeparatedYn = false`를 포함한다. |
| report edit schema | `ESG_REPORT_SECTION_DRAFT.edited_text`, `last_edited_by_user_id`, `last_edited_at` 컬럼 추가가 필요하다. Phase 2A에서는 DDL 제안만 문서화하고 report edit은 skeleton으로 둔다. |
| report order | `section_order`, `paragraph_order` 컬럼 추가를 권장한다. MVP skeleton은 `id ASC` fallback을 허용하고 response에 `orderSource = "ID_ASC_FALLBACK"`을 포함한다. |
| trace type | `reference_type = rollup_result`이면 `GROUP_ROLLUP`, `kpi_fact` 또는 `onboarding_input`이면 `DIRECT`, 불명확하면 `UNKNOWN`을 반환한다. |
| TE_SR_FILE | benchmark MVP 유지를 위해 clean schema 또는 migration에 포함하는 방향으로 문서화한다. Phase 2A는 기존 테이블이 있다는 전제로 작성하되 테이블 부재 시 graceful empty response를 허용한다. |
| scoring payload | `ESG_DMA_SIGNAL_DETAIL.scoring_payload_json` ALTER를 migration에 포함한다. 현재 DB에는 존재한다고 가정한다. |
| report download | Phase 2A는 skeleton과 response contract만 구현한다. 실제 PDF/DOCX 생성은 P1 후속이다. |

## 2. 공통 API 원칙

1. 외부 호출 경로는 문서상 `/api/v1/...`로 표기한다.
2. 현재 backend 내부 FastAPI router는 `backend/src/utils/fastset.py`가 `src.apis` 모듈명을 기준으로 prefix를 자동 부여한다.
3. 따라서 `backend/src/apis/materiality.py`, `backend/src/apis/media.py`, `backend/src/apis/survey.py`, `backend/src/apis/report.py` 내부에서는 `APIRouter(prefix="/...")`를 선언하지 않는다.
4. `backend/src/apis/`는 router와 endpoint만 담당한다.
5. 업무 흐름과 비즈니스 로직은 `backend/src/services/`에 둔다.
6. DB 조회, 저장, 집계 helper는 `backend/src/utils/` 또는 repository 계층에서 처리한다.
7. Pydantic request/response DTO는 `backend/src/models/`에 둔다.
8. DB column명은 snake_case를 유지한다.
9. Python 변수, 함수, Pydantic field명은 camelCase를 사용한다.
10. subIssue 기준은 `backend/src/utils/subissuemaster.py`를 단일 Source of Truth로 사용한다.
11. 한글 subIssue명은 `displaySubIssueName` 등 표시용 field로만 사용한다.
12. 저장, 집계, join 기준은 항상 `subIssueCode`이며, 값은 `subissuemaster.py`의 key여야 한다.
13. React는 `backend/src/apis`의 endpoint만 호출한다. services/utils를 직접 호출하는 구조는 만들지 않는다.
14. 본 Contract 승인 전 React mock data 제거 및 API 연결은 진행하지 않는다.
15. Phase 2A의 endpoint 소유 파일은 다음과 같이 확정한다: materiality 조회 API는 `backend/src/apis/materiality.py`, media 실행 API는 `backend/src/apis/media.py`, report skeleton API는 `backend/src/apis/report.py`.

## 3. 공통 응답 규칙

### 3.1 점수 규칙

DB canonical score는 0~5 기준이다. API는 모든 점수에 대해 `score05`와 `score10`을 함께 반환한다.

```text
score10 = score05 * 2
```

예시는 다음과 같다.

```json
{
  "finalScore05": 4.61,
  "finalScore10": 9.22
}
```

React 화면 기본 표시는 `score10`을 사용한다. `score05`는 tooltip, detail, debug, 감사 추적용으로 사용할 수 있다.

### 3.2 subIssue 공통 field

모든 이슈 item은 가능한 한 다음 field를 포함한다.

```json
{
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "domain": "Environment",
  "issueGroup": "기후변화",
  "rankNo": 1,
  "selectedYn": true,
  "quadrant": "HIGH_IMPACT_HIGH_FINANCIAL"
}
```

`domain`, `issueGroup`, `displaySubIssueName`은 `subissuemaster.py` metadata에서 파생한다. DB의 `ESG_SUB_ISSUE_MASTER`도 존재하지만 MVP API의 기준 사전은 `backend/src/utils/subissuemaster.py`로 고정한다.

### 3.3 coverage 공통 field

전체 결과 item의 coverage는 impact/financial 축을 분리한다.

```json
{
  "coverage": {
    "impactObservedStages": ["benchmark", "media_external", "survey"],
    "financialObservedStages": ["benchmark", "survey"],
    "impactCoverageStatus": "FULL",
    "financialCoverageStatus": "PARTIAL",
    "benchmarkObserved": true,
    "mediaObserved": true,
    "surveyObserved": true
  }
}
```

`coverageStatus` enum은 다음과 같다.

| status | 기준 |
|---|---|
| `FULL` | 3개 stage 관측 |
| `PARTIAL` | 2개 stage 관측 |
| `LIMITED` | 1개 stage 관측 |
| `NO_DATA` | 관측 stage 없음 |

### 3.4 인증 및 권한

모든 API는 token 기반 사용자 인증과 run/company 접근권한 검증을 전제로 한다.

- `runId`가 사용자의 `companyId` 또는 권한 범위에 속하는지 검증한다.
- 보고서와 rollup trace API는 지주사/자회사 데이터 접근권한을 검증한다.
- 현재 레포에는 `get_token` 기반 인증 흐름이 존재하나, 각 신규 endpoint의 run 권한 검증은 추가 구현 필요하다.

## 4. 화면별 API 매핑표

| screenId | 화면명 | MVP 우선순위 | 주 endpoint | 보조 endpoint | 현재 충족도 | 비고 |
|---|---|---:|---|---|---:|---|
| UI-01 | 벤치마킹 분석 결과 | P0 | `GET /api/v1/materiality/benchmark/{runId}` | 기존 `/benchmk` upload/analyze | 20% | 실행 API는 있으나 결과 조회 API 신규 필요 |
| UI-02 | 미디어 분석 결과 | P0 | `GET /api/v1/materiality/media/{runId}` | `POST /api/v1/media/news/analyze` | 45% | POST analyze 일부 구현, GET 결과 API 필요 |
| UI-03 | 이해관계자 설문 결과 | P0 | `GET /api/v1/materiality/survey/{runId}` | 없음 | 15% | survey stage 계산 helper 일부, 조회 API 없음 |
| UI-04 | 전체 결과 - 다음 단계 연결형 | P1 | `GET /api/v1/materiality/results/{runId}` | 필요 시 `selected/{runId}` 후속 | 35% | results response의 `nextStep` section으로 통합 |
| UI-05 | 전체 결과 - 점수 해석형 | P1 | `GET /api/v1/materiality/results/{runId}` | 없음 | 55% | stage score는 있음, contribution 설명 필요 |
| UI-06 | 전체 결과 - 후보군→최종 선정 과정형 | P1 | `GET /api/v1/materiality/results/{runId}` | `GET /api/v1/materiality/selection-process/{runId}` | 35% | funnel 일부는 results로, excluded reason은 별도 |
| UI-07 | 전체 결과 - 최종 요약형 | P0 | `GET /api/v1/materiality/results/{runId}` | 없음 | 60% | 대표 전체 결과 화면 |
| UI-08 | 보고서 생성 확인 | P0 | `GET /api/v1/report/drafts/{runId}` | `PATCH`, `download` | 0% | report API 신규 필요 |
| UI-09 | 데이터 추적 패널 | P0 | `GET /api/v1/report/drafts/{runId}/paragraphs/{paragraphId}/trace` | 없음 | 0% | trace API 신규 필요 |

## 5. Endpoint별 상세 Contract

### API-MAT-001. 전체 DMA 결과 조회

| 항목 | 내용 |
|---|---|
| endpoint | `GET /api/v1/materiality/results/{runId}` |
| backend router file | `backend/src/apis/materiality.py` |
| service file | `backend/src/services/materialities/service.py` |
| request params | path: `runId` |
| 사용 UI | UI-04, UI-05, UI-06, UI-07 |
| score05/score10 | 포함 |
| 정렬 기준 | `rankNo ASC`; rank 산정은 `final_score DESC` |
| DB/source | `ESG_DMA_SCORE_SUMMARY`, `ESG_MATERIALITY_SELECTED_SUB_ISSUE`, `ESG_SUB_ISSUE_ATOMIC_MAP`, `ESG_KPI_FACT`, `subissuemaster.py` |
| 현재 구현 여부 | 부분 구현 |
| 부족 구현 | `matrixItems`, `topIssues`, `selectedYn`, `quadrant`, `nextStep`, `selectionReasons`, `requiredMetricCount`, `onboardingMissingCount`, `highPriorityCount`, `selectionSource`, `fallbackYn` |

#### Response root fields

```json
{
  "runId": 1,
  "totalCandidateSubIssueCount": 62,
  "summaryRowCount": 25,
  "scoredSubIssueCount": 21,
  "selectedSubIssueCount": 5,
  "highPriorityCount": 5,
  "items": [],
  "matrixItems": [],
  "topIssues": [],
  "selectionReasons": [],
  "nextStep": {},
  "coverageSummary": {},
  "selectionSource": "RANK_FALLBACK",
  "fallbackYn": true
}
```

#### `items[]`

`items[]`는 전체 summary row를 rank 기준으로 제공한다.

```json
{
  "rankNo": 1,
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "domain": "Environment",
  "issueGroup": "기후변화",
  "selectedYn": true,
  "quadrant": "HIGH_IMPACT_HIGH_FINANCIAL",
  "benchmarkImpactScore05": 4.6,
  "benchmarkImpactScore10": 9.2,
  "benchmarkFinancialScore05": 4.35,
  "benchmarkFinancialScore10": 8.7,
  "mediaImpactScore05": 4.2,
  "mediaImpactScore10": 8.4,
  "mediaFinancialScore05": 4.0,
  "mediaFinancialScore10": 8.0,
  "surveyImpactScore05": 4.8,
  "surveyImpactScore10": 9.6,
  "surveyFinancialScore05": 4.7,
  "surveyFinancialScore10": 9.4,
  "finalImpactScore05": 4.4,
  "finalImpactScore10": 8.8,
  "finalFinancialScore05": 4.75,
  "finalFinancialScore10": 9.5,
  "finalScore05": 4.61,
  "finalScore10": 9.22,
  "coverage": {}
}
```

#### `matrixItems[]`

`matrixItems[]`는 UI-07 DMA matrix 전용 좌표 view다. `items[]`와 동일 row를 matrix 렌더링에 적합한 형태로 재구성한다.

```json
{
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "domain": "Environment",
  "issueGroup": "기후변화",
  "xFinancialScore10": 9.5,
  "yImpactScore10": 8.8,
  "finalScore10": 9.22,
  "rankNo": 1,
  "selectedYn": true,
  "quadrant": "HIGH_IMPACT_HIGH_FINANCIAL"
}
```

#### `topIssues[]`

전체 결과 Top Issues는 `final_score / rank_no` 기준이다.

```json
{
  "rankNo": 1,
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "domain": "Environment",
  "issueGroup": "기후변화",
  "finalScore05": 4.61,
  "finalScore10": 9.22,
  "summary": "최종 중대 이슈 요약 문장",
  "reportPage": 1,
  "selectedYn": true,
  "coverage": {}
}
```

#### `selectionReasons[]`

```json
{
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "rankNo": 1,
  "selectedYn": true,
  "selectionType": "rank_based",
  "selectionReason": "최종 점수 상위 이슈로 MVP 기본 선정"
}
```

#### `nextStep`

UI-04는 별도 endpoint보다 `results.nextStep`으로 우선 제공한다.

```json
{
  "selectedIssueCount": 5,
  "requiredMetricCount": 24,
  "onboardingMissingCount": 3,
  "reportDraftReadyYn": true,
  "reportRunId": 12,
  "nextAction": "GENERATE_REPORT_DRAFT",
  "selectionSource": "RANK_FALLBACK",
  "fallbackYn": true
}
```

### API-MAT-002. 벤치마킹 단계 결과 조회

| 항목 | 내용 |
|---|---|
| endpoint | `GET /api/v1/materiality/benchmark/{runId}` |
| backend router file | `backend/src/apis/materiality.py` |
| service file | `backend/src/services/materialities/service.py` 또는 `backend/src/services/benchmarks/service.py` |
| request params | path: `runId` |
| 사용 UI | UI-01 |
| score05/score10 | 포함 |
| 정렬 기준 | benchmark stage avg score DESC |
| DB/source | `TE_SR_FILE`, `ESG_DMA_SIGNAL_DETAIL`, `ESG_DMA_SCORE_SUMMARY`, `ESG_DMA_EVIDENCE` |
| 현재 구현 여부 | 신규 필요 |
| 부족 구현 | summary, topIssues, commonIssues, blindSpotIssues 조회 |

#### Response root fields

```json
{
  "runId": 1,
  "summary": {},
  "topIssues": [],
  "commonIssues": [],
  "blindSpotIssues": [],
  "evidenceSummary": {}
}
```

#### `summary`

```json
{
  "analyzedReportCount": 24,
  "leaderReportCount": 9,
  "peerReportCount": 12,
  "ownReportCount": 3,
  "identifiedIssueCount": 28,
  "commonIssueCount": 19,
  "blindSpotCount": 9
}
```

#### `topIssues[]`

```json
{
  "rankNo": 1,
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "domain": "Environment",
  "issueGroup": "기후변화",
  "benchmarkImpactScore05": 4.6,
  "benchmarkImpactScore10": 9.2,
  "benchmarkFinancialScore05": 4.35,
  "benchmarkFinancialScore10": 8.7,
  "benchmarkAvgScore05": 4.48,
  "benchmarkAvgScore10": 8.96,
  "leaderObserved": true,
  "peerObserved": true,
  "ownObserved": false,
  "evidenceCount": 6
}
```

#### `commonIssues[]`

```json
{
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "leaderObserved": true,
  "peerObserved": true,
  "ownObserved": true,
  "leaderEvidenceCount": 3,
  "peerEvidenceCount": 4,
  "ownEvidenceCount": 1
}
```

#### `blindSpotIssues[]`

```json
{
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "leaderObserved": true,
  "peerObserved": true,
  "ownObserved": false,
  "blindSpotYn": true,
  "summary": "리더/피어 보고서에서 반복 관측되었으나 자사 보고서에서는 관측되지 않은 이슈"
}
```

### API-MAT-003. 미디어 단계 결과 조회

| 항목 | 내용 |
|---|---|
| endpoint | `GET /api/v1/materiality/media/{runId}` |
| backend router file | `backend/src/apis/materiality.py` 또는 `backend/src/apis/media.py` |
| service file | `backend/src/services/materialities/service.py` 또는 `backend/src/services/medias/service.py` |
| request params | path: `runId` |
| 사용 UI | UI-02 |
| score05/score10 | 포함 |
| 정렬 기준 | `media_external` stage avg score DESC |
| DB/source | `ESG_DMA_SIGNAL_DETAIL`, `ESG_DMA_SCORE_SUMMARY`, `ESG_DMA_EVIDENCE` |
| 현재 구현 여부 | 부분 구현 |
| 부족 구현 | GET result endpoint, sourceBreakdown, evidenceSamples, sourceTypes/evidenceCount |

#### Response root fields

```json
{
  "runId": 1,
  "summary": {},
  "sourceBreakdown": [],
  "topIssues": [],
  "evidenceSamples": [],
  "coverage": {}
}
```

#### `summary`

```json
{
  "articleCount": 78,
  "agencyCount": 4,
  "regulationFrameCount": 4,
  "observedSubIssueCount": 21
}
```

#### `sourceBreakdown[]`

```json
{
  "sourceType": "news",
  "sourceLabel": "언론 기사",
  "collectedCount": 78,
  "observedIssueCount": 19,
  "appliedMethod": "실제 기사 기반"
}
```

#### `topIssues[]`

```json
{
  "rankNo": 1,
  "subIssueCode": "E_CLIMATE__GHG_EMISSIONS",
  "displaySubIssueName": "온실가스 배출 감축",
  "domain": "Environment",
  "issueGroup": "기후변화",
  "mediaImpactScore05": 4.2,
  "mediaImpactScore10": 8.4,
  "mediaFinancialScore05": 4.0,
  "mediaFinancialScore10": 8.0,
  "mediaAvgScore05": 4.1,
  "mediaAvgScore10": 8.2,
  "sourceTypes": ["news", "regulation"],
  "evidenceCount": 6
}
```

#### `evidenceSamples[]`

```json
{
  "evidenceId": 1001,
  "subIssueCode": "E_CLIMATE__GHG_EMISSIONS",
  "sourceType": "news",
  "sourceTitle": "기사 제목",
  "sourceUrl": "https://example.com/news/1",
  "publishedAt": "2026-05-27T00:00:00",
  "textSpan": "근거 문장"
}
```

### API-MED-001. 언론 기사 분석 실행 및 저장

| 항목 | 내용 |
|---|---|
| endpoint | `POST /api/v1/media/news/analyze` |
| backend router file | `backend/src/apis/media.py` |
| service file | `backend/src/services/medias/service.py` |
| request body | `runId`, `articles[]`, `keywords[]` |
| 사용 UI | UI-02 |
| score05/score10 | 포함 |
| 정렬 기준 | response `topIssues`는 media stage avg score DESC |
| DB/source | `ESG_DMA_EVIDENCE`, `ESG_DMA_SIGNAL_DETAIL`, `ESG_DMA_SCORE_SUMMARY` |
| 현재 구현 여부 | 부분 구현 |
| 부족 구현 | sourceTypes, evidenceCount, sourceBreakdown alignment, response DTO model 이동 |

#### Request

```json
{
  "runId": 1,
  "articles": [
    {
      "source": "news",
      "title": "기사 제목",
      "url": "https://example.com/news/1",
      "publishedAt": "2026-05-27",
      "content": "본문"
    }
  ],
  "keywords": ["기후", "공급망"]
}
```

#### Response

```json
{
  "runId": 1,
  "articleCount": 5,
  "observedSubIssueCount": 3,
  "savedSignalCount": 12,
  "topIssues": [],
  "coverageStatus": "LIMITED",
  "coverageDetail": {}
}
```

### API-MAT-004. 설문 단계 결과 조회

| 항목 | 내용 |
|---|---|
| endpoint | `GET /api/v1/materiality/survey/{runId}` |
| backend router file | `backend/src/apis/materiality.py` 또는 `backend/src/apis/survey.py` |
| service file | `backend/src/services/surveys/service.py` |
| request params | path: `runId` |
| 사용 UI | UI-03 |
| score05/score10 | 포함 |
| 정렬 기준 | survey stage avg score DESC |
| DB/source | `ESG_DMA_SURVEY_RESPONSE`, `ESG_DMA_SURVEY_QUESTION`, `ESG_DMA_SCORE_SUMMARY` |
| 현재 구현 여부 | 신규 필요 |
| 부족 구현 | summary, groupBreakdown, topIssues, responseQuality |

#### Response root fields

```json
{
  "runId": 1,
  "summary": {},
  "groupBreakdown": [],
  "topIssues": [],
  "responseQuality": {},
  "summaryText": "설문 결과 요약",
  "axisSeparatedYn": false,
  "targetSource": "MVP_DEFAULT"
}
```

#### `summary`

```json
{
  "employeeRespondentCount": 124,
  "managementRespondentCount": 18,
  "externalRespondentCount": 45,
  "totalRespondentCount": 187,
  "employeeResponseRate": 82.7,
  "managementResponseRate": 90.0,
  "externalResponseRate": 56.3,
  "totalResponseRate": 74.8
}
```

응답률 분모는 현재 schema만으로는 명확하지 않다. MVP에서는 화면 입력값 또는 별도 survey target table이 없으면 `responseRate`를 null로 허용한다.

#### `groupBreakdown[]`

```json
{
  "respondentGroup": "employee",
  "respondentGroupLabel": "임직원",
  "respondentCount": 124,
  "targetCount": 150,
  "responseRate": 82.7
}
```

#### `topIssues[]`

survey axis가 분리되지 않은 경우 impact/financial field에는 동일 survey score를 채운다.

```json
{
  "rankNo": 1,
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "domain": "Environment",
  "issueGroup": "기후변화",
  "surveyImpactScore05": 4.5,
  "surveyImpactScore10": 9.0,
  "surveyFinancialScore05": 4.5,
  "surveyFinancialScore10": 9.0,
  "employeeImpactScore05": 4.2,
  "employeeImpactScore10": 8.4,
  "employeeFinancialScore05": 4.2,
  "employeeFinancialScore10": 8.4,
  "managementImpactScore05": 4.8,
  "managementImpactScore10": 9.6,
  "managementFinancialScore05": 4.8,
  "managementFinancialScore10": 9.6,
  "externalImpactScore05": 4.4,
  "externalImpactScore10": 8.8,
  "externalFinancialScore05": 4.4,
  "externalFinancialScore10": 8.8
}
```

### API-MAT-005. 후보군→최종 선정 과정 조회

| 항목 | 내용 |
|---|---|
| endpoint | `GET /api/v1/materiality/selection-process/{runId}` |
| backend router file | `backend/src/apis/materiality.py` |
| service file | `backend/src/services/materialities/service.py` |
| request params | path: `runId` |
| 사용 UI | UI-06 |
| score05/score10 | 포함 |
| 정렬 기준 | selectedIssues: selected rank ASC; excludedIssues: rank ASC |
| DB/source | `ESG_DMA_SCORE_SUMMARY`, `ESG_MATERIALITY_SELECTED_SUB_ISSUE`, `subissuemaster.py` |
| 현재 구현 여부 | 신규 필요 |
| 부족 구현 | selected/excluded reason 산출 |

#### Response

```json
{
  "runId": 1,
  "funnel": {
    "totalCandidateSubIssueCount": 62,
    "summaryRowCount": 25,
    "scoredSubIssueCount": 21,
    "selectedSubIssueCount": 5
  },
  "threshold": {
    "selectionRule": "TOP_N_BY_FINAL_SCORE",
    "selectedTopN": 5,
    "minimumFinalScore10": 8.0
  },
  "selectedIssues": [],
  "excludedIssues": []
}
```

### API-REP-001. 보고서 초안 조회

| 항목 | 내용 |
|---|---|
| endpoint | `GET /api/v1/report/drafts/{runId}` |
| backend router file | `backend/src/apis/report.py` |
| service file | `backend/src/services/reports/service.py` |
| request params | path: `runId` |
| 사용 UI | UI-08 |
| score05/score10 | 해당 없음 |
| 정렬 기준 | section order ASC, paragraph order ASC. 현 schema에는 order column이 없어 `id ASC` 임시 사용 |
| DB/source | `ESG_REPORT_RUN`, `ESG_REPORT_SECTION_DRAFT`, `ESG_REPORT_REFERENCE`, `ESG_MATERIALITY_SELECTED_SUB_ISSUE` |
| 현재 구현 여부 | 신규 필요 |
| 부족 구현 | report router/service/model 전체 |

#### Response root fields

```json
{
  "runId": 1,
  "reportRunId": 12,
  "summary": {},
  "sections": [],
  "downloadOptions": [],
  "implementationStatus": "SKELETON",
  "missingSchemaFields": ["edited_text", "last_edited_by_user_id", "last_edited_at", "section_order", "paragraph_order"],
  "orderSource": "ID_ASC_FALLBACK"
}
```

#### `summary`

```json
{
  "generatedPageCount": 5,
  "referencedKpiCount": 24,
  "evidenceLinkRate": 92.0,
  "revisionRequiredCount": 2
}
```

#### `sections[]`

현 schema의 `ESG_REPORT_SECTION_DRAFT`는 문단 단위 테이블에 가깝다. API에서는 UI가 쓰기 쉬운 section/paragraph 구조로 변환한다.

```json
{
  "sectionId": "E_CLIMATE",
  "sectionCode": "DMA_E_CLIMATE",
  "sectionTitle": "기후변화",
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "paragraphs": [
    {
      "paragraphId": 101,
      "draftId": 101,
      "paragraphOrder": 1,
      "originalGeneratedText": "AI가 생성한 원문",
      "editableText": "현재 편집창에 표시할 텍스트",
      "editedText": null,
      "approvalStatus": "draft",
      "qaStatus": "pass",
      "lastEditedAt": "2026-05-28T13:00:00",
      "referencedMetricIds": ["GHG_SCOPE1_TOTAL"],
      "traceAvailableYn": true
    }
  ]
}
```

#### `downloadOptions[]`

```json
{
  "fileType": "pdf",
  "label": "PDF",
  "availableYn": true
}
```

### API-REP-002. 보고서 문단 수정 저장

| 항목 | 내용 |
|---|---|
| endpoint | `PATCH /api/v1/report/drafts/{draftId}` |
| backend router file | `backend/src/apis/report.py` |
| service file | `backend/src/services/reports/service.py` |
| request params | path: `draftId`, body: `editedText` |
| 사용 UI | UI-08 |
| score05/score10 | 해당 없음 |
| 정렬 기준 | 해당 없음 |
| DB/source | `ESG_REPORT_SECTION_DRAFT` |
| 현재 구현 여부 | 신규 필요 |
| 부족 구현 | 현 schema에는 `edited_text`, `last_edited_at` column 없음 |

#### Request

```json
{
  "editedText": "사용자가 수정한 문단",
  "editComment": "선택"
}
```

#### Response

```json
{
  "draftId": 101,
  "editStatus": "saved",
  "lastEditedAt": "2026-05-28T13:20:00"
}
```

현 schema는 `generated_text`, `reviewer_comment`, `approval_status`, `updated_at`만 제공한다. Contract field인 `editedText`, `lastEditedAt`을 본구현하려면 DB 컬럼 추가 또는 `generated_text` overwrite 정책 중 하나를 결정해야 한다.

### API-REP-003. 문단별 데이터 추적 조회

| 항목 | 내용 |
|---|---|
| endpoint | `GET /api/v1/report/drafts/{runId}/paragraphs/{paragraphId}/trace` |
| backend router file | `backend/src/apis/report.py` |
| service file | `backend/src/services/reports/service.py` |
| request params | path: `runId`, `paragraphId` |
| 사용 UI | UI-09 |
| score05/score10 | 해당 없음 |
| 정렬 기준 | metrics sort by map/order if available, else reference id ASC |
| DB/source | `ESG_REPORT_REFERENCE`, `ESG_KPI_FACT`, `ESG_GROUP_ROLLUP_RESULT`, `ESG_CALCULATION_RULE`, `ESG_ATOMIC_METRIC_MASTER` |
| 현재 구현 여부 | 신규 필요 |
| 부족 구현 | direct/rollup trace service |

#### Response

```json
{
  "runId": 1,
  "paragraphId": 101,
  "traceType": "GROUP_ROLLUP",
  "sourceModeLabel": "그룹 통합 지표",
  "metrics": [],
  "latestValue": 1234.56,
  "valuesByYear": [],
  "companyBreakdown": [],
  "calculationFormula": "A + B + C",
  "aiEvidenceSummary": "이 문단은 그룹 통합 배출량과 3개년 추이를 근거로 생성되었습니다.",
  "relatedParagraphs": [],
  "implementationStatus": "SKELETON"
}
```

#### `metrics[]`

```json
{
  "metricId": "GHG_SCOPE1_TOTAL",
  "atomicMetricId": "GHG_SCOPE1_TOTAL_VALUE",
  "metricName": "Scope 1 배출량",
  "atomicMetricName": "Scope 1 총 배출량",
  "unit": "tCO2e",
  "dataType": "QUANT"
}
```

#### `valuesByYear[]`

```json
{
  "year": 2025,
  "value": 1234.56,
  "unit": "tCO2e",
  "approvalStatus": "approved"
}
```

#### `companyBreakdown[]`

`traceType=DIRECT`일 때는 빈 배열을 허용한다. `traceType=GROUP_ROLLUP`일 때만 제공한다.

```json
{
  "companyId": 6,
  "companyName": "A_GROUP",
  "year": 2025,
  "value": 700.0,
  "unit": "tCO2e",
  "contributionRate": 56.7
}
```

### API-REP-004. 보고서 다운로드 생성

| 항목 | 내용 |
|---|---|
| endpoint | `POST /api/v1/report/drafts/{runId}/download` |
| backend router file | `backend/src/apis/report.py` |
| service file | `backend/src/services/reports/export.py` |
| request params | path: `runId`, body: `fileType` |
| 사용 UI | UI-08 |
| score05/score10 | 해당 없음 |
| 정렬 기준 | 해당 없음 |
| DB/source | report export service, `ESG_REPORT_SECTION_DRAFT` |
| 현재 구현 여부 | 신규 필요 |
| 부족 구현 | export service |

#### Request

```json
{
  "fileType": "pdf"
}
```

#### Response

```json
{
  "runId": 1,
  "reportRunId": 12,
  "fileType": "pdf",
  "downloadUrl": "/api/v1/report/downloads/12.pdf",
  "expiresAt": "2026-05-28T14:00:00"
}
```

## 6. Response DTO 초안

DTO는 `backend/src/models/materiality.py`와 `backend/src/models/report.py`에 배치한다.

### 6.1 materiality DTO

```python
class CoverageDto(BaseModel):
    impactObservedStages: list[str]
    financialObservedStages: list[str]
    impactCoverageStatus: str
    financialCoverageStatus: str
    benchmarkObserved: bool
    mediaObserved: bool
    surveyObserved: bool

class SubIssueBaseDto(BaseModel):
    subIssueCode: str
    displaySubIssueName: str
    domain: str | None = None
    issueGroup: str | None = None
    rankNo: int | None = None
    selectedYn: bool = False
    quadrant: str | None = None

class MaterialityResultItemDto(SubIssueBaseDto):
    benchmarkImpactScore05: float | None = None
    benchmarkImpactScore10: float | None = None
    benchmarkFinancialScore05: float | None = None
    benchmarkFinancialScore10: float | None = None
    mediaImpactScore05: float | None = None
    mediaImpactScore10: float | None = None
    mediaFinancialScore05: float | None = None
    mediaFinancialScore10: float | None = None
    surveyImpactScore05: float | None = None
    surveyImpactScore10: float | None = None
    surveyFinancialScore05: float | None = None
    surveyFinancialScore10: float | None = None
    finalImpactScore05: float | None = None
    finalImpactScore10: float | None = None
    finalFinancialScore05: float | None = None
    finalFinancialScore10: float | None = None
    finalScore05: float | None = None
    finalScore10: float | None = None
    coverage: CoverageDto

class MaterialityResultsResponseDto(BaseModel):
    runId: int
    totalCandidateSubIssueCount: int
    summaryRowCount: int
    scoredSubIssueCount: int
    selectedSubIssueCount: int
    highPriorityCount: int
    selectionSource: Literal["TABLE", "RANK_FALLBACK"]
    fallbackYn: bool
    items: list[MaterialityResultItemDto]
    matrixItems: list[dict]
    topIssues: list[dict]
    selectionReasons: list[dict]
    nextStep: dict
    coverageSummary: dict
```

### 6.2 report DTO

```python
class ReportDraftParagraphDto(BaseModel):
    paragraphId: int
    draftId: int
    paragraphOrder: int | None = None
    originalGeneratedText: str
    editableText: str
    editedText: str | None = None
    approvalStatus: str
    qaStatus: str | None = None
    lastEditedAt: str | None = None
    referencedMetricIds: list[str]
    traceAvailableYn: bool

class ReportDraftSectionDto(BaseModel):
    sectionId: str
    sectionCode: str | None = None
    sectionTitle: str
    subIssueCode: str | None = None
    displaySubIssueName: str | None = None
    paragraphs: list[ReportDraftParagraphDto]

class ReportDraftResponseDto(BaseModel):
    runId: int
    reportRunId: int
    summary: dict
    sections: list[ReportDraftSectionDto]
    downloadOptions: list[dict]

class ReportTraceResponseDto(BaseModel):
    runId: int
    paragraphId: int
    traceType: Literal["DIRECT", "GROUP_ROLLUP", "UNKNOWN"]
    sourceModeLabel: str
    metrics: list[dict]
    latestValue: float | str | None = None
    valuesByYear: list[dict]
    companyBreakdown: list[dict]
    calculationFormula: str | None = None
    aiEvidenceSummary: str | None = None
    relatedParagraphs: list[dict]
    implementationStatus: str = "SKELETON"
```

## 7. DB/로직 Source 매핑

| 용도 | source | 주요 column/logic |
|---|---|---|
| subIssue metadata | `backend/src/utils/subissuemaster.py` | `subIssueCode`, `subIssueNameKr`, domain/issue group metadata |
| 전체 score | `ESG_DMA_SCORE_SUMMARY` | `benchmark_*`, `media_external_*`, `survey_*`, `final_*`, `rank_no` |
| 최종 선정 | `ESG_MATERIALITY_SELECTED_SUB_ISSUE` | `selected_rank_no`, `selection_type`, `selection_reason` |
| 벤치마킹 evidence/source | `TE_SR_FILE`, `ESG_DMA_SIGNAL_DETAIL`, `ESG_DMA_EVIDENCE` | `source_step='benchmark'`, `source_type in leader_sr/peer_sr/own_sr` |
| 미디어 evidence/source | `ESG_DMA_SIGNAL_DETAIL`, `ESG_DMA_EVIDENCE` | `source_step='media_external'`, `source_type in news/agency/regulation` |
| 설문 응답 | `ESG_DMA_SURVEY_RESPONSE`, `ESG_DMA_SURVEY_QUESTION` | `respondent_group`, `normalized_score`, `mapped_axis` |
| 필요 지표 매핑 | `ESG_SUB_ISSUE_ATOMIC_MAP`, `ESG_ATOMIC_METRIC_MASTER` | `sub_issue_code`, `metric_id`, `atomic_metric_id`, `required_yn` |
| 직접 KPI | `ESG_KPI_FACT` | `company_id`, `reporting_year`, `metric_id`, `atomic_metric_id`, value fields |
| rollup KPI | `ESG_GROUP_ROLLUP_RESULT` | `parent_company_id`, `group_metric_id`, `group_atomic_metric_id`, `source_company_values_json` |
| 계산식 | `ESG_CALCULATION_RULE`, `ESG_CALCULATION_RULE_SOURCE` | `calculation_rule_code`, `calculation_formula_label`, source atomic ids |
| 보고서 실행 | `ESG_REPORT_RUN` | `source_materiality_run_id`, `report_status` |
| 보고서 문단 | `ESG_REPORT_SECTION_DRAFT` | `generated_text`, `qa_status`, `approval_status`, `sub_issue_code` |
| 보고서 trace | `ESG_REPORT_REFERENCE` | `reference_type`, `reference_id`, `atomic_metric_id`, `trace_label_json` |
| DMASignal payload trace | `ESG_DMA_SIGNAL_DETAIL.scoring_payload_json` | 운영 DB 추가 컬럼. clean schema에는 별도 ALTER 필요 |

## 8. 계산/정렬 기준

### 8.1 score 변환

```text
score10 = round(score05 * 2, 2)
```

`score05`가 null이면 대응되는 `score10`도 null이다.

### 8.2 stage/final score

- benchmark score: `ESG_DMA_SCORE_SUMMARY.benchmark_impact_score`, `benchmark_financial_score`
- media score: `media_external_impact_score`, `media_external_financial_score`
- survey score: `survey_impact_score`, `survey_financial_score`
- final score: `final_impact_score`, `final_financial_score`, `final_score`

### 8.3 final aggregation weight

현행 `dmaaggregator.py` 기준 final stage weight는 다음과 같다.

| stage | weight |
|---|---:|
| survey | 0.40 |
| benchmark | 0.35 |
| media_external | 0.25 |

null stage는 0점 처리하지 않고 분모에서 제외한다.

### 8.4 정렬 기준

| 화면/API | 정렬 기준 |
|---|---|
| 전체 결과 `topIssues`, `items` | `rank_no ASC`; rank는 `final_score DESC` 기준 |
| 벤치마킹 `topIssues` | benchmark impact/financial non-null 평균 DESC |
| 미디어 `topIssues` | media_external impact/financial non-null 평균 DESC |
| 설문 `topIssues` | survey impact/financial non-null 평균 DESC |
| 후보군 selected | `selected_rank_no ASC`, 없으면 `rank_no ASC` |
| report sections/paragraphs | order column 미정. MVP는 `id ASC` 임시 |

### 8.5 quadrant 기준

MVP 기본 quadrant는 final score10 기준으로 산정한다.

| quadrant | 기준 |
|---|---|
| `HIGH_IMPACT_HIGH_FINANCIAL` | impact >= 7 and financial >= 7 |
| `HIGH_IMPACT_LOW_FINANCIAL` | impact >= 7 and financial < 7 |
| `LOW_IMPACT_HIGH_FINANCIAL` | impact < 7 and financial >= 7 |
| `LOW_IMPACT_LOW_FINANCIAL` | impact < 7 and financial < 7 |
| `NO_DATA` | impact 또는 financial 좌표가 없음 |

threshold 7은 MVP 기본값이며, UI 승인 후 config화할 수 있다.

## 9. 현재 구현 상태

| 파일 | 현재 상태 |
|---|---|
| `backend/src/apis/materiality.py` | `GET /results/{runId}` 부분 구현. DTO가 API 파일 내부에 있으며 service 계층을 거치지 않고 utils를 직접 호출 |
| `backend/src/apis/media.py` | `POST /news/analyze` 부분 구현. media topIssues는 `media_external` score 기준 조회 |
| `backend/src/apis/survey.py` | 빈 파일 |
| `backend/src/apis/benchmk.py` | SR upload/analyze 실행 API 존재. 결과 조회 API 없음 |
| `backend/src/apis/report.py` | 없음 |
| `backend/src/services/materialities/orchestrator.py` | 빈 파일 |
| `backend/src/services/medias/service.py` | media 분석 실행 흐름 존재 |
| `backend/src/services/surveys/service.py` | 빈 파일 |
| `backend/src/utils/dmarepository.py` | score 저장/재계산/results/media helper 일부 존재 |
| `backend/src/utils/dmaaggregator.py` | benchmark/media/survey/final aggregation 로직 존재 |
| `backend/src/utils/subissuemaster.py` | subIssue 단일 기준 사전 존재 |
| `frontend/src/homes/reports/*.jsx` | mock/dummy 중심. API Contract 승인 전 수정 금지 |

현재 API로 가능한 것은 다음이다.

- 전체 결과 기본 `items[]`: rank, subIssueCode, displaySubIssueName, stage/final score05/10 일부, coverage 일부
- media analyze 실행: DUMMY article 기반 signal 저장, media topIssues 일부, observedSubIssueCount
- benchmark 실행: SR 파일 업로드 및 AI 분석 후 DMA signal 저장 흐름
- repository level: final rank 갱신, media score 기준 topIssues 조회

## 10. 부족 필드 및 추가 구현 필요사항

### 10.1 공통 부족 필드

- `domain`
- `issueGroup`
- `selectedYn`
- `quadrant`
- `impactObservedStages`
- `financialObservedStages`

### 10.2 전체 결과 부족 필드

- `selectedSubIssueCount`
- `highPriorityCount`
- `matrixItems`
- `topIssues`
- `selectionReasons`
- `nextStep.requiredMetricCount`
- `nextStep.onboardingMissingCount`
- `nextStep.reportDraftReadyYn`

### 10.3 벤치마킹 부족 필드

- `analyzedReportCount`
- `leaderReportCount`
- `peerReportCount`
- `ownReportCount`
- `identifiedIssueCount`
- `commonIssueCount`
- `blindSpotCount`
- `commonIssues[]`
- `blindSpotIssues[]`
- `leaderObserved`, `peerObserved`, `ownObserved`

### 10.4 미디어 부족 필드

- `GET /materiality/media/{runId}`
- `sourceBreakdown[]`
- `agencyCount`
- `regulationFrameCount`
- `sourceTypes`
- `evidenceCount`
- `evidenceSamples[]`

### 10.5 설문 부족 필드

- `employeeRespondentCount`
- `managementRespondentCount`
- `externalRespondentCount`
- `totalResponseRate`
- `groupBreakdown[]`
- group별 impact/financial score05/10
- response denominator source

### 10.6 보고서/trace 부족 필드

- `reportRunId`
- `generatedPageCount`
- `referencedKpiCount`
- `evidenceLinkRate`
- `revisionRequiredCount`
- `sections[]`
- `paragraphs[]`
- `editableText`
- `originalGeneratedText`
- `editedText`
- `lastEditedAt`
- `downloadOptions`
- `traceType`
- `metrics[]`
- `latestValue`
- `valuesByYear[]`
- `companyBreakdown[]`
- `calculationFormula`
- `aiEvidenceSummary`
- `relatedParagraphs[]`

## 11. MVP 포함/제외 범위

### MVP 포함

- UI-01 벤치마킹 분석 결과
- UI-02 미디어 분석 결과
- UI-03 이해관계자 설문 결과
- UI-07 전체 결과 최종 요약형
- UI-08 보고서 생성 확인
- UI-09 데이터 추적 패널
- UI-04/05/06은 `materiality results` response의 section으로 지원
- score05/score10 동시 반환
- direct/rollup trace 유형 분리
- media topIssues를 media_external stage score 기준으로 정렬
- 전체 결과 topIssues를 final_score/rank_no 기준으로 정렬

### MVP 제외

- 실제 embedding repo 기반 media crawling/embedding pipeline 완전 이식
- regulation adapter 본구현
- agency adapter 본구현
- survey impact/financial axis 완전 분리
- benchmark ratio/blind spot 고도화
- report draft trace API 고도화
- 사용자 편집본 기준 trace 재생성
- 온보딩 이상치 점검 탭
- Fact Data Book UI
- React 전체 화면 최종 연결

## 12. 구현 우선순위

1. `backend/src/models/materiality.py`, `backend/src/services/materialities/service.py`를 만들고 `GET /materiality/results/{runId}` 로직을 service 계층으로 이동한다.
2. `GET /api/v1/materiality/results/{runId}`에 `matrixItems`, `topIssues`, `nextStep`, `selectionReasons`, `selectedYn`, `quadrant`를 보강한다.
3. `GET /api/v1/materiality/benchmark/{runId}`를 추가한다.
4. `GET /api/v1/materiality/media/{runId}`를 추가하고 기존 `POST /media/news/analyze` response와 field를 정렬한다.
5. `GET /api/v1/materiality/survey/{runId}` skeleton을 구현한다.
6. `GET /api/v1/materiality/selection-process/{runId}`를 구현한다. 단, UI-06이 P1이므로 results section으로 충분하면 후순위로 둔다.
7. `backend/src/models/report.py`, `backend/src/apis/report.py`, `backend/src/services/reports/service.py`를 만들고 `GET /report/drafts/{runId}` skeleton을 구현한다.
8. `GET /report/drafts/{runId}/paragraphs/{paragraphId}/trace`를 DIRECT/GROUP_ROLLUP 분기로 구현한다.
9. `PATCH /report/drafts/{draftId}`와 `POST /report/drafts/{runId}/download`를 skeleton 또는 최소 구현한다.
10. backend compile/smoke test를 수행한다.
11. Contract 승인 후 React mock 제거 및 API 연결을 진행한다.

## 13. 검증 SQL 및 smoke test 기준

### 13.1 score summary

```sql
SELECT
    esg_materiality_run_id,
    sub_issue_code,
    benchmark_impact_score,
    benchmark_financial_score,
    media_external_impact_score,
    media_external_financial_score,
    survey_impact_score,
    survey_financial_score,
    final_impact_score,
    final_financial_score,
    final_score,
    rank_no
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = ?
ORDER BY rank_no;
```

### 13.2 stage/source signal count

```sql
SELECT
    source_step,
    source_type,
    COUNT(*) AS signal_count,
    COUNT(DISTINCT sub_issue_code) AS observed_sub_issue_count
FROM ESG_DMA_SIGNAL_DETAIL
WHERE esg_materiality_run_id = ?
  AND delete_yn = 0
GROUP BY source_step, source_type;
```

### 13.3 media top issues 정렬 검증

```sql
SELECT
    sub_issue_code,
    media_external_impact_score,
    media_external_financial_score,
    (
        (COALESCE(media_external_impact_score, 0) + COALESCE(media_external_financial_score, 0))
        / CASE
            WHEN media_external_impact_score IS NOT NULL AND media_external_financial_score IS NOT NULL THEN 2
            WHEN media_external_impact_score IS NOT NULL OR media_external_financial_score IS NOT NULL THEN 1
            ELSE 1
          END
    ) AS media_avg_score
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = ?
  AND (media_external_impact_score IS NOT NULL OR media_external_financial_score IS NOT NULL)
ORDER BY media_avg_score DESC
LIMIT 10;
```

### 13.4 evidence sample

```sql
SELECT
    id,
    source_step,
    source_type,
    source_title,
    source_url,
    source_published_at,
    text_span
FROM ESG_DMA_EVIDENCE
WHERE esg_materiality_run_id = ?
  AND delete_yn = 0
ORDER BY id DESC
LIMIT 20;
```

### 13.5 survey group aggregation

```sql
SELECT
    respondent_group,
    sub_issue_code,
    COUNT(*) AS response_count,
    AVG(normalized_score) AS avg_score
FROM ESG_DMA_SURVEY_RESPONSE
WHERE esg_materiality_run_id = ?
  AND delete_yn = 0
GROUP BY respondent_group, sub_issue_code;
```

### 13.6 selected issues

```sql
SELECT
    esg_materiality_run_id,
    sub_issue_code,
    selected_rank_no,
    selection_type,
    selection_reason
FROM ESG_MATERIALITY_SELECTED_SUB_ISSUE
WHERE esg_materiality_run_id = ?
  AND delete_yn = 0
ORDER BY selected_rank_no;
```

### 13.7 subIssue metric mapping

```sql
SELECT
    sam.sub_issue_code,
    sam.metric_id,
    sam.atomic_metric_id,
    sam.required_yn,
    amm.metric_name_kr,
    amm.atomic_name_kr,
    amm.unit,
    amm.data_value_type
FROM ESG_SUB_ISSUE_ATOMIC_MAP sam
JOIN ESG_ATOMIC_METRIC_MASTER amm
  ON amm.atomic_metric_id = sam.atomic_metric_id
WHERE sam.sub_issue_code = ?
  AND sam.delete_yn = 0
  AND amm.delete_yn = 0
ORDER BY sam.sort_order, sam.id;
```

### 13.8 report draft

```sql
SELECT
    rr.id AS report_run_id,
    rr.source_materiality_run_id,
    rr.report_status,
    sd.id AS draft_id,
    sd.section_code,
    sd.sub_issue_code,
    sd.owner_metric_id,
    sd.generated_text,
    sd.qa_status,
    sd.approval_status
FROM ESG_REPORT_RUN rr
JOIN ESG_REPORT_SECTION_DRAFT sd
  ON sd.report_run_id = rr.id
WHERE rr.source_materiality_run_id = ?
  AND rr.delete_yn = 0
  AND sd.delete_yn = 0
ORDER BY sd.id;
```

### 13.9 paragraph trace

```sql
SELECT
    ref.id,
    ref.report_section_draft_id,
    ref.reference_type,
    ref.reference_id,
    ref.atomic_metric_id,
    ref.trace_label_json
FROM ESG_REPORT_REFERENCE ref
WHERE ref.report_section_draft_id = ?
  AND ref.delete_yn = 0
ORDER BY ref.id;
```

### 13.10 smoke test endpoint

```text
GET /api/v1/materiality/results/{runId}
GET /api/v1/materiality/benchmark/{runId}
GET /api/v1/materiality/media/{runId}
GET /api/v1/materiality/survey/{runId}
GET /api/v1/materiality/selection-process/{runId}
POST /api/v1/media/news/analyze
GET /api/v1/report/drafts/{runId}
PATCH /api/v1/report/drafts/{draftId}
GET /api/v1/report/drafts/{runId}/paragraphs/{paragraphId}/trace
POST /api/v1/report/drafts/{runId}/download
```

### 13.11 backend compile

```bash
cd backend
python -m compileall src
```

주의: 현재 로컬 코드에는 일부 UTF-8 BOM 관련 parse 이슈가 관측될 수 있다. 본 Contract 작성 단계에서는 backend 코드를 수정하지 않는다.

## 14. Open Questions

| id | 영역 | 질문 | 권장 결정 | 상태 |
|---|---|---|---|---|
| Q-001 | API prefix | 외부 `/api/v1` prefix는 gateway/nginx에서 붙이는가, FastAPI app에서 붙이는가? | backend router 내부 중복 prefix는 금지. 배포 레이어에서 `/api/v1` 정렬 | Open |
| Q-002 | 최종 선정 수 | 보고서 생성 대상 최종 이슈 수는 5개인가 10개인가? | MVP 보고서 생성은 Top 5, 전체 결과 표는 Top 10 | Proposed |
| Q-003 | selected source | `ESG_MATERIALITY_SELECTED_SUB_ISSUE`가 비어 있으면 rank 기반 자동 선정으로 볼 것인가? | MVP는 Top N rank 기반 fallback 허용 | Proposed |
| Q-004 | survey denominator | group별 응답률 분모 target count를 어디서 가져올 것인가? | 별도 survey target table 전까지 API에서 null 허용 또는 FE 입력값 저장 필요 | Open |
| Q-005 | survey axis | 설문 impact/financial 축이 완전히 분리되어 있는가? | v1은 동일 score를 impact/financial에 채우고 DTO는 분리 유지 | Proposed |
| Q-006 | report edit schema | `editedText`, `lastEditedAt` 저장 컬럼을 추가할 것인가? | `ESG_REPORT_SECTION_DRAFT`에 `edited_text`, `last_edited_at` 추가 권장 | Open |
| Q-007 | report order | section/paragraph 순서를 저장하는 column이 필요한가? | `section_order`, `paragraph_order` 추가 권장. MVP는 `id ASC` fallback | Open |
| Q-008 | trace type 판단 | `GROUP_ROLLUP`/`DIRECT` 판단을 `reference_type`만으로 할 것인가? | `rollup_result`는 GROUP_ROLLUP, `kpi_fact/onboarding_input`은 DIRECT | Proposed |
| Q-009 | TE_SR_FILE | clean schema에는 `TE_SR_FILE`이 없고 기존 앱 테이블로 보인다. 신규 clean DB에 포함할 것인가? | benchmark MVP 유지 시 필요 | Open |
| Q-010 | `scoring_payload_json` | clean schema DDL에 추가 컬럼을 반영할 것인가? | schema migration에 ALTER 포함 | Proposed |
| Q-011 | report download | 실제 PDF/DOCX 생성까지 MVP에 포함할 것인가? | API skeleton과 URL contract 우선, 실제 export는 P1 | Proposed |

v1.1 기준 위 항목은 다음과 같이 정리한다.

- Q-001: Closed. `/api/v1`은 gateway/nginx/proxy 또는 frontend baseURL 책임이다.
- Q-002: Closed. 보고서 대상 Top 5, 결과 화면 Top 10.
- Q-003: Closed. `selectionSource`, `fallbackYn`으로 fallback 여부를 명시한다.
- Q-004: Closed for MVP. service 상수 `MVP_SURVEY_TARGETS`와 `targetSource="MVP_DEFAULT"`를 사용한다.
- Q-005: Closed for v1. `axisSeparatedYn=false`.
- Q-006: Phase 2B. DDL 제안만 반영한다.
- Q-007: Phase 2B. Phase 2A는 `orderSource="ID_ASC_FALLBACK"`.
- Q-008: Closed. `rollup_result`는 `GROUP_ROLLUP`, `kpi_fact/onboarding_input`은 `DIRECT`, 그 외는 `UNKNOWN`.
- Q-009: Phase 2A graceful handling. migration에는 `TE_SR_FILE` 포함 권장.
- Q-010: migration에 아래 ALTER 포함 권장.
- Q-011: Phase 2A skeleton, 실제 export는 P1.

### 14.1 권장 migration DDL

```sql
ALTER TABLE ESG_DMA_SIGNAL_DETAIL
ADD COLUMN scoring_payload_json LONGTEXT NULL
COMMENT 'DMASignal camelCase payload and evidence trace JSON';

ALTER TABLE ESG_REPORT_SECTION_DRAFT
ADD COLUMN edited_text LONGTEXT NULL COMMENT '사용자 수정 문단',
ADD COLUMN last_edited_by_user_id BIGINT NULL COMMENT '마지막 수정 사용자',
ADD COLUMN last_edited_at DATETIME NULL COMMENT '마지막 수정 시각',
ADD COLUMN section_order INT NULL COMMENT '보고서 섹션 표시 순서',
ADD COLUMN paragraph_order INT NULL COMMENT '섹션 내 문단 표시 순서';
```

`TE_SR_FILE`은 기존 benchmark upload/analyze 흐름이 의존하므로 clean schema 또는 별도 migration에 포함해야 한다. Phase 2A 조회 API는 해당 테이블이 없을 때 500을 전파하지 않고 빈 summary를 반환한다.
