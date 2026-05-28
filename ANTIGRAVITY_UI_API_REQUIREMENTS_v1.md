# ANTIGRAVITY 전달용 UI/API 요구사항 명세서 v1.0

본 문서는 **SKM ESG 플랫폼 MVP의 이중중대성평가 결과 화면 및 보고서 생성 화면** 구현을 위한 상위 요구사항 명세서다.  
API Contract와 React 구현은 이 문서를 기준으로 작성한다.

대상 화면은 총 9개다.

1. 벤치마킹 분석 결과
2. 미디어 분석 결과
3. 이해관계자 설문 결과
4. 전체 결과 - 다음 단계 연결형
5. 전체 결과 - 점수 해석형
6. 전체 결과 - 후보군→최종 선정 과정형
7. 전체 결과 - 최종 요약형
8. 보고서 생성 확인
9. 데이터 추적 패널

---

## 1. 구현 원칙

### 1.1 폴더 역할

API endpoint는 반드시 `backend/src/apis/` 아래에 구현한다.

```text
backend/src/apis/
  materiality.py   # 전체 결과 및 단계별 결과 조회 API
  media.py         # 미디어 분석 실행 API
  benchmk.py       # 벤치마킹 업로드/분석 실행 API
  survey.py        # 설문 실행/결과 조회 API
  report.py        # 보고서 초안/데이터 추적 API 신규 필요
```

비즈니스 로직은 `backend/src/services/` 아래에 둔다.

```text
backend/src/services/
  materialities/
  medias/
  benchmarks/
  surveys/
  reports/
```

공통 점수 계산, aggregation, repository는 `backend/src/utils/`를 사용한다.

```text
backend/src/utils/
  dmascoring.py
  dmaaggregator.py
  dmarepository.py
  subissuemaster.py
```

### 1.2 FastAPI Router prefix 주의

현재 `fastset.py`가 `src.apis`의 모듈명을 기준으로 prefix를 자동 부여한다.  
따라서 `apis/materiality.py`, `apis/media.py`, `apis/report.py` 내부에서 `APIRouter(prefix="/...")`를 중복 선언하지 않는다.

권장:

```python
router = APIRouter(tags=["materiality"])
```

금지:

```python
router = APIRouter(prefix="/materiality", tags=["materiality"])
```

### 1.3 점수 스케일

DB와 내부 계산의 canonical score는 0~5다.  
UI 표시용 score는 0~10이다.

API response에서는 반드시 `score05`와 `score10`을 함께 반환한다.

```text
score10 = score05 * 2
```

예시:

```json
{
  "finalScore05": 4.61,
  "finalScore10": 9.22
}
```

React 화면은 기본적으로 `score10`을 표시하고, tooltip/detail/debug에는 `score05`를 쓸 수 있다.

### 1.4 subIssue 기준

`subIssueCode`는 반드시 `backend/src/utils/subissuemaster.py`의 key를 사용한다.  
한글명은 `displaySubIssueName` 또는 `subIssueNameKr`로만 사용한다.

```text
subIssueCode = E_CLIMATE__CLIMATE_TARGETS_TRANSITION
displaySubIssueName = 기후목표·전환계획
```

### 1.5 topIssues 정렬 기준

전체 결과 화면의 Top Issues는 `final_score`와 `rank_no` 기준이다.

미디어 화면의 Top Issues는 `final_score`가 아니라 `media_external` stage score 기준이다.

벤치마킹 화면의 Top Issues는 `benchmark` stage score 기준이다.

설문 화면의 Top Issues는 `survey` stage score 기준이다.

---

## 2. 화면별 요구사항

## UI-01. 벤치마킹 분석 결과

### 목적

리더/피어/자사 지속가능경영보고서에서 관측된 이중중대성 이슈를 62개 `subIssueCode` 기준으로 매핑하고, 공통 이슈와 자사 Blind Spot을 보여준다.

### 필수 컴포넌트

| 컴포넌트 | 표시 데이터 | 기준 |
|---|---|---|
| 요약 KPI 카드 | 분석 보고서 수, 식별 이슈 수, 공통 이슈 수, 자사 Blind Spot 수 | TE_SR_FILE + ESG_DMA_SIGNAL_DETAIL |
| 벤치마킹 Top 이슈 표 | rank, subIssueName, benchmarkImpactScore10, benchmarkFinancialScore10 | ESG_DMA_SCORE_SUMMARY benchmark score |
| 공통 선정 이슈 표 | subIssueName, leaderObserved, peerObserved, ownObserved | sourceType별 signal 존재 여부 |
| 자사 Blind Spot 패널 | blindSpotIssue 목록, 요약 문장 | leader/peer 관측, own 미관측 rule |

### API 후보

```http
GET /api/v1/materiality/benchmark/{runId}
```

### Response 최소 구조

```json
{
  "runId": 1,
  "summary": {
    "analyzedReportCount": 24,
    "observedSubIssueCount": 28,
    "commonIssueCount": 19,
    "blindSpotCount": 9
  },
  "topIssues": [
    {
      "rankNo": 1,
      "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
      "displaySubIssueName": "기후목표·전환계획",
      "benchmarkImpactScore05": 4.6,
      "benchmarkImpactScore10": 9.2,
      "benchmarkFinancialScore05": 4.35,
      "benchmarkFinancialScore10": 8.7
    }
  ],
  "commonIssues": [],
  "blindSpotIssues": []
}
```

### 주의사항

리더/피어/자사별 개별 점수는 산정하지 않는다.  
MVP에서는 관측 여부, ratio, common selection, blind spot 중심으로 표현한다.

---

## UI-02. 미디어 분석 결과

### 목적

언론 기사, 전문기관 자료, 규제 프레임에서 관측된 외부 ESG 시그널을 `media_external` stage로 통합 표시한다.

### 필수 컴포넌트

| 컴포넌트 | 표시 데이터 | 기준 |
|---|---|---|
| 요약 KPI 카드 | 언론 기사 수, 전문기관 자료 수, 규제 프레임 수, 종합 관측 이슈 수 | ESG_DMA_SIGNAL_DETAIL sourceType |
| Source별 반영 현황 | sourceType, collectedCount, observedIssueCount, appliedMethod | sourceType group by |
| Media Top 이슈 표 | subIssueName, mediaImpactScore10, mediaFinancialScore10, mediaAvgScore10 | media_external stage score |
| 반영 방식 안내 | news/agency/regulation 설명 | 고정 문구 + API source 상태 |

### API 후보

```http
GET /api/v1/materiality/media/{runId}
POST /api/v1/media/news/analyze
```

### GET Response 최소 구조

```json
{
  "runId": 1,
  "summary": {
    "articleCount": 78,
    "agencyCount": 4,
    "regulationFrameCount": 4,
    "observedSubIssueCount": 21
  },
  "sourceBreakdown": [
    {
      "sourceType": "news",
      "sourceLabel": "언론 기사",
      "collectedCount": 78,
      "observedIssueCount": 19,
      "appliedMethod": "실제 기사 기반"
    }
  ],
  "topIssues": [
    {
      "rankNo": 1,
      "subIssueCode": "E_CLIMATE__GHG_EMISSIONS",
      "displaySubIssueName": "온실가스 배출 감축",
      "mediaImpactScore05": 4.2,
      "mediaImpactScore10": 8.4,
      "mediaFinancialScore05": 4.0,
      "mediaFinancialScore10": 8.0,
      "mediaAvgScore05": 4.1,
      "mediaAvgScore10": 8.2,
      "sourceTypes": ["news", "regulation"],
      "evidenceCount": 6
    }
  ],
  "coverage": {
    "stageCount": 1,
    "coverageStatus": "LIMITED",
    "mediaObserved": true,
    "benchmarkObserved": false,
    "surveyObserved": false
  }
}
```

### 정렬 기준

`topIssues`는 `final_score`가 아니라 `media_external_impact_score`, `media_external_financial_score`의 null 제외 평균 기준으로 정렬한다.

### 주의사항

현재 MVP에서는 `news` 먼저 연결한다.  
`agency`, `regulation`은 같은 `media_external` stage의 하위 sourceType으로 확장한다.

---

## UI-03. 이해관계자 설문 결과

### 목적

임직원, 경영진, 외부 이해관계자 응답 결과를 기반으로 survey stage의 이슈 중요도를 표시한다.

### 필수 컴포넌트

| 컴포넌트 | 표시 데이터 | 기준 |
|---|---|---|
| 응답 KPI 카드 | 그룹별 응답자 수, 응답률, 전체 응답률 | ESG_DMA_SURVEY_RESPONSE |
| 설문 Top 이슈 표 | subIssueName, surveyImpactScore10, surveyFinancialScore10 | ESG_DMA_SCORE_SUMMARY survey score |
| 그룹별 관점 차이 | employee/management/external score | respondent_group별 avg |
| 설문 요약 문장 | 주요 이슈 및 그룹별 차이 | API generated summary 또는 static summary |

### API 후보

```http
GET /api/v1/materiality/survey/{runId}
```

### 주의사항

현재 v1에서는 survey impact/financial axis가 완전히 분리되지 않았을 수 있다.  
그 경우 API는 impact/financial 동일 점수 구조를 허용하되, response field는 axis 분리 형태로 유지한다.

---

## UI-04. 전체 결과 - 다음 단계 연결형

### 목적

최종 선정된 이슈에서 온보딩 지표 확인, 부족 데이터 입력, 보고서 초안 생성으로 이어지는 연결 화면이다.

### 필수 데이터

| 항목 | 설명 |
|---|---|
| selectedIssueCount | 최종 선정 이슈 수 |
| requiredMetricCount | 선정 이슈와 연결된 필요 지표 수 |
| onboardingMissingCount | 부족한 온보딩 지표 수 |
| reportDraftReadyYn | 보고서 초안 생성 가능 여부 |

### API 후보

```http
GET /api/v1/materiality/results/{runId}
GET /api/v1/materiality/selected/{runId}
```

MVP에서는 UI-07과 통합 가능하다.

---

## UI-05. 전체 결과 - 점수 해석형

### 목적

최종 점수가 어떤 stage에서 기여했는지 설명한다.

### 필수 데이터

| 항목 | 설명 |
|---|---|
| benchmarkImpactScore10 / benchmarkFinancialScore10 | 벤치마킹 stage 점수 |
| mediaImpactScore10 / mediaFinancialScore10 | 미디어 stage 점수 |
| surveyImpactScore10 / surveyFinancialScore10 | 설문 stage 점수 |
| finalImpactScore10 / finalFinancialScore10 | 최종 점수 |
| coverageStatus | FULL/PARTIAL/LIMITED/NO_DATA |

### API 후보

```http
GET /api/v1/materiality/results/{runId}
```

### 주의사항

기여도는 단순 점수가 아니라 final stage weight를 적용한 해석이다.  
현행 final weight는 다음 기준을 따른다.

```text
survey = 0.40
benchmark = 0.35
media_external = 0.25
```

---

## UI-06. 전체 결과 - 후보군→최종 선정 과정형

### 목적

62개 후보군에서 summary row, scored issue, selected issue로 좁혀지는 과정을 보여준다.

### 필수 데이터

| 항목 | 설명 |
|---|---|
| totalCandidateSubIssueCount | subissueMaster 기준 전체 후보군 수 |
| summaryRowCount | ESG_DMA_SCORE_SUMMARY에 존재하는 row 수 |
| scoredSubIssueCount | finalScore05가 존재하는 이슈 수 |
| selectedSubIssueCount | 최종 선정 이슈 수 |
| selectedIssues | 최종 선정 이슈 목록 |
| excludedIssues | 제외 이슈 목록 및 사유 |

### API 후보

```http
GET /api/v1/materiality/results/{runId}
GET /api/v1/materiality/selection-process/{runId}
```

MVP에서는 selected/excluded reason이 부족하면 rank 기반 임시 선정으로 표시한다.

---

## UI-07. 전체 결과 - 최종 요약형

### 목적

MVP의 대표 전체 결과 화면이다. 최종 이슈, 이중중대성 매트릭스, Top 이슈 요약을 보여준다.

### 필수 컴포넌트

| 컴포넌트 | 표시 데이터 | 기준 |
|---|---|---|
| 최종 선정 요약 카드 | 평가 대상, 후보군, 최종 선정, High 영역 | materiality results |
| DMA Matrix | x=financialScore10, y=impactScore10 | ESG_DMA_SCORE_SUMMARY |
| Top 이슈 요약 표 | rankNo, issueName, summary, reportPage | final rank |
| Stage 점수 표 | benchmark/media/survey/final score | summary scores |

### API 후보

```http
GET /api/v1/materiality/results/{runId}
```

### Response 최소 구조

```json
{
  "runId": 1,
  "totalCandidateSubIssueCount": 62,
  "summaryRowCount": 25,
  "scoredSubIssueCount": 21,
  "items": [
    {
      "rankNo": 1,
      "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
      "displaySubIssueName": "기후목표·전환계획",
      "finalImpactScore05": 4.4,
      "finalImpactScore10": 8.8,
      "finalFinancialScore05": 4.75,
      "finalFinancialScore10": 9.5,
      "finalScore05": 4.61,
      "finalScore10": 9.22,
      "coverage": {
        "impactCoverageStatus": "FULL",
        "financialCoverageStatus": "PARTIAL"
      }
    }
  ]
}
```

---

## UI-08. 보고서 생성 확인

### 목적

최종 선정된 이슈를 기반으로 생성된 지속가능경영보고서 초안을 확인하고, 수정/저장/다운로드할 수 있게 한다.

### 필수 컴포넌트

| 컴포넌트 | 표시 데이터 | 기준 |
|---|---|---|
| 상단 KPI 카드 | 생성 이슈 페이지 수, 참조 KPI 수, 근거 연결률, 수정 필요 수 | report run/reference count |
| 보고서 본문 | section title, paragraph text, table/chart blocks | ESG_REPORT_SECTION_DRAFT |
| 편집 툴바 | 수정, 저장, 코멘트, 더보기 | FE state + PATCH API |
| 다운로드 메뉴 | PDF, DOCX | export API |
| 데이터 추적 패널 | paragraph trace | UI-09 API |

### API 후보

```http
GET /api/v1/report/drafts/{runId}
PATCH /api/v1/report/drafts/{draftId}
POST /api/v1/report/drafts/{runId}/download
```

### 주의사항

MVP에서는 AI 초안 기준 trace만 제공한다.  
사용자 편집본 기준 trace 재생성은 제외한다.

---

## UI-09. 데이터 추적 패널

### 목적

보고서 문단이 어떤 KPI, atomic metric, rollup result, calculation rule을 근거로 생성됐는지 설명한다.

### traceType

```text
GROUP_ROLLUP
DIRECT
```

### GROUP_ROLLUP 표시 항목

| 항목 | 설명 |
|---|---|
| metricId / atomicMetricId | 참조 지표 |
| groupValue | 그룹 통합 값 |
| companyBreakdown | A_GROUP, B_SUB_KR, C_SUB_EU, D_SUB_US 등 회사별 구성 |
| calculationFormula | 계산식 또는 산출 방식 |
| yearValues | 3개년 값 추이 |
| aiEvidenceSummary | AI 근거 설명 |

### DIRECT 표시 항목

| 항목 | 설명 |
|---|---|
| metricId / atomicMetricId | 참조 지표 |
| latestValue | 최신 연도 값 |
| yearValues | 3개년 값 추이 |
| sourceModeLabel | 직접 관리 지표 |
| aiEvidenceSummary | AI 근거 설명 |

### API 후보

```http
GET /api/v1/report/drafts/{runId}/paragraphs/{paragraphId}/trace
```

### 주의사항

사용자에게 DB 내부 테이블명을 그대로 노출하지 않는다.  
필요한 경우 “그룹 통합 지표”, “직접 관리 지표”, “계산 지표” 같은 업무 용어로 변환한다.

---

## 3. 공통 API Response 원칙

### 3.1 점수 필드

모든 점수는 다음 쌍으로 내려준다.

```json
{
  "finalScore05": 4.61,
  "finalScore10": 9.22
}
```

### 3.2 coverage 필드

```json
{
  "coverage": {
    "impactObservedStages": ["benchmark", "media_external", "survey"],
    "financialObservedStages": ["benchmark", "survey"],
    "impactCoverageStatus": "FULL",
    "financialCoverageStatus": "PARTIAL"
  }
}
```

### 3.3 subIssue 필드

```json
{
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "displaySubIssueName": "기후목표·전환계획",
  "domain": "Environment",
  "issueGroup": "기후변화"
}
```

### 3.4 권한/인증

모든 API는 아래를 전제로 한다.

```text
- token 기반 사용자 인증
- runId가 사용자의 companyId 또는 권한 범위에 속하는지 검증
- 지주사/자회사 rollup 데이터 접근권한 검증
```

---

## 4. DB/로직 매핑 요약

| 용도 | 주요 소스 |
|---|---|
| 전체 결과 점수 | ESG_DMA_SCORE_SUMMARY |
| 벤치마킹 source 관측 | ESG_DMA_SIGNAL_DETAIL, TE_SR_FILE |
| 미디어 source 관측 | ESG_DMA_SIGNAL_DETAIL, ESG_DMA_EVIDENCE |
| 설문 응답 | ESG_DMA_SURVEY_RESPONSE |
| subIssue 표준 사전 | backend/src/utils/subissuemaster.py |
| 보고서 초안 | ESG_REPORT_RUN, ESG_REPORT_SECTION_DRAFT |
| 보고서 근거 추적 | ESG_REPORT_REFERENCE |
| 직접 KPI | ESG_KPI_FACT, ESG_ONBOARDING_INPUT_VALUE |
| 그룹 통합 KPI | ESG_GROUP_ROLLUP_RESULT |
| 계산식 | ESG_CALCULATION_RULE |

---

## 5. MVP 포함/제외

### MVP 포함

```text
- 벤치마킹 결과 화면
- 미디어 결과 화면
- 이해관계자 설문 결과 화면
- 전체 결과 최종 요약형
- 보고서 생성 확인
- 데이터 추적 패널
- score05/score10 동시 반환
- direct/rollup trace 유형 분리
```

### MVP 제외

```text
- 온보딩 데이터 이상치 점검 탭
- Fact Data Book UI
- 수정본 기준 trace 재계산
- 유료 외부평가기관 원문 자동 수집
- 복잡한 수동 심의 workflow
```

---

## 6. Antigravity 작업 순서

### Phase 2-1. API Contract 문서화

이 문서와 Excel을 기준으로 endpoint별 request/response DTO를 정리한다.

완료 기준:

```text
- 9개 screenId가 endpoint와 매핑됨
- 화면별 필수 데이터가 response field로 존재함
- 부족 필드는 Open Question으로 분리됨
```

### Phase 2-2. Backend API 보강

우선순위:

1. `materiality.py` 전체 결과 API 보강
2. benchmark result API 추가
3. media result API 정리
4. survey result API skeleton
5. report draft API skeleton
6. paragraph trace API skeleton

### Phase 2-3. React 연결

API Contract 확정 후 진행한다.  
Mock data 추가 금지.  
필요 시 loading / empty / error state만 임시 처리한다.

---

## 7. 검증 기준

### Backend

```bash
cd backend
python -m compileall src
```

### API Smoke Test

```text
GET /api/v1/materiality/results/{runId}
GET /api/v1/materiality/media/{runId}
GET /api/v1/materiality/benchmark/{runId}
GET /api/v1/materiality/survey/{runId}
GET /api/v1/report/drafts/{runId}
GET /api/v1/report/drafts/{runId}/paragraphs/{paragraphId}/trace
```

### DB 확인

```sql
SELECT *
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = ?
ORDER BY rank_no;

SELECT source_step, source_type, COUNT(*)
FROM ESG_DMA_SIGNAL_DETAIL
WHERE esg_materiality_run_id = ?
GROUP BY source_step, source_type;

SELECT *
FROM ESG_DMA_EVIDENCE
WHERE esg_materiality_run_id = ?
ORDER BY evidence_id DESC;
```

---

## 8. 금지사항

```text
- React 화면을 먼저 구현하지 말 것
- API 없이 mock 결과값을 늘리지 말 것
- final_score를 media/benchmark/survey 단계 화면 정렬 기준으로 쓰지 말 것
- subIssueCode에 한글명을 넣지 말 것
- APIRouter prefix를 중복 선언하지 말 것
- services에 endpoint를 만들지 말 것
- backend/src/apis 외부에 라우터 파일을 만들지 말 것
- DB 내부 테이블명을 사용자 화면에 그대로 노출하지 말 것
```

---

## 9. 전달 파일

상세 Excel:

```text
SKM_MVP_UI_API_기능정의서_v2.xlsx
```

코딩 지시 Markdown:

```text
ANTIGRAVITY_UI_API_REQUIREMENTS_v1.md
```
