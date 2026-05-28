# ESG 플랫폼 개발 인수인계 문서 v1.0

문서 목적: 다음 채팅방 또는 Codex/Antigravity 작업자가 현재까지의 설계 의도, 코드 상태, 다음 작업 우선순위, 주의사항을 잃지 않고 이어서 작업할 수 있도록 정리한다. 이 문서는 API/DB/AI agent/Rule engine/UI/보고서 생성까지 이어지는 MVP 기준 인수인계 문서다.

작성 기준: 2026-05-28 현재 대화 및 `leeej9801-max/total` 레포의 `dev_skm-feature-ai_score_ljb` 작업 흐름 기준.

---

## 0. 프로젝트 한 줄 정의

SKM ESG 플랫폼 MVP는 기업의 이중중대성평가(DMA)를 수행하고, 선정된 중요 ESG 이슈에 연결된 지표 온보딩 데이터를 기반으로 지속가능경영보고서 초안을 AI가 생성하며, 생성 문단의 근거 KPI/롤업 데이터까지 추적할 수 있게 하는 서비스다.

핵심 흐름은 다음과 같다.

```text
벤치마킹 분석
+ 미디어 분석
+ 이해관계자 설문
        ↓
이중중대성평가 점수 산출
        ↓
최종 중요 subIssue 선정
        ↓
선정 subIssue에 매핑된 metric/atomic metric 온보딩
        ↓
KPI fact / rollup result 저장
        ↓
AI 보고서 문단 생성
        ↓
보고서 편집 및 데이터 추적
```

---

## 1. 현재까지 확정된 핵심 원칙

### 1.1 API / 서비스 계층 원칙

```text
backend/src/apis      = FastAPI endpoint/router만 담당
backend/src/services  = 업무 흐름 및 orchestration 담당
backend/src/utils     = scoring, repository, aggregation, 공통 유틸 담당
backend/src/models    = Pydantic request/response schema 담당
```

주의사항:

- `apis/*.py`에 복잡한 SQL, 점수 산식, crawler 로직을 직접 넣지 않는다.
- React는 `backend/src/apis` endpoint만 호출한다.
- services/utils를 프론트에서 직접 호출하는 구조는 만들지 않는다.
- DB 컬럼은 snake_case 유지.
- Python 변수/함수/Pydantic field는 camelCase 유지.
- `APIRouter(prefix="/materiality")`, `APIRouter(prefix="/media")` 같은 중복 prefix 선언 금지. 현재 프로젝트는 `fastset.py`가 모듈명 기준 prefix를 자동 부여하는 전제가 있다.

### 1.2 subIssue Source of Truth 원칙

모든 이중중대성평가 이슈 기준은 반드시 아래 파일을 기준으로 한다.

```text
backend/src/utils/subissuemaster.py
```

금지사항:

- reference 폴더 안의 별도 `subissuemaster.py`를 production 기준으로 사용하지 않는다.
- 한글 이슈명을 `subIssueCode`로 저장하지 않는다.
- production 저장/집계 기준은 반드시 `subissuemaster.py`의 key다.
- 한글명은 표시용 `displaySubIssueName`으로만 사용한다.

### 1.3 점수 스케일 원칙

```text
DB canonical score = 0~5
API canonical score = score05
UI display score = score10 = score05 * 2
```

모든 API는 가능한 경우 `score05`와 `score10`을 함께 내려준다. 프론트에서 임의로 `*2` 계산하는 구조를 방치하지 않는다.

### 1.4 AI와 Rule Engine 역할 분리

AI가 최종 점수를 직접 찍으면 안 된다. 현재 설계의 핵심은 아래다.

```text
AI / Embedding / LLM = 후보 추출, 문맥 판단, evidence 추출, factor 후보 생성
Rule Engine = 허용축 검증, factor 기반 0~5 점수 계산, 집계, rank 산출
```

특히 DMA 점수는 재현성과 감사 가능성이 중요하므로, 최종 점수는 `dmascoring.py`, `dmaaggregator.py`, `dmarepository.py` 계층에서 rule-based로 처리해야 한다.

---

## 2. 현재 시스템 아키텍처 개념도

현재 코드는 LangGraph 기반 명시적 그래프가 아니라, 함수형 멀티에이전트형 파이프라인이다.

```text
[Frontend UI]
  Media.jsx / Benchmark / Survey / Result / Report
        ↓
[FastAPI API Router]
  backend/src/apis/*.py
        ↓
[Service Orchestrator]
  backend/src/services/*/service.py
        ↓
[Agent / Engine Layer]
  - Media Crawler Agent
  - Embedding Mapping Agent
  - Benchmark Extraction Agent
  - Survey Rule Agent
  - DMA Rule Scoring Agent
  - DMA Aggregation Agent
  - Report Generation Agent
  - Report Trace Agent
        ↓
[Repository / DB Layer]
  - dmarepository.py
  - reportrepository.py
  - surveyrepository.py 예정
        ↓
[DB]
  MariaDB ESG_DMA_*
  MariaDB ESG_REPORT_*
  MariaDB ESG_KPI_FACT
  MariaDB ESG_GROUP_ROLLUP_RESULT
  PostgreSQL pgvector ai_sr
```

---

## 3. 현재 완료된 주요 작업 상태

### 3.1 DMA 점수 로직 v1 Freeze

현재 핵심 구조:

```text
Raw Source
  ↓
Source-specific Adapter
  ↓
DMASignal
  ↓
Baseline / IRO Gate
  ↓
dmascoring.py
  ↓
dmarepository.saveDmaSignals()
  ↓
Stage Aggregation
  ↓
Final Aggregation
  ↓
ESG_DMA_SCORE_SUMMARY
```

핵심 파일:

```text
backend/src/models/dmaengine.py
backend/src/utils/dmascoring.py
backend/src/utils/dmaaggregator.py
backend/src/utils/dmarepository.py
```

점수 산식:

- Impact: scale, scope, likelihood, irremediability, urgency 기반.
- Financial: revenue/cost/capex/legal/asset/financing magnitude 중 최대값 + likelihood + urgency 기반.
- sourceType별 하드코딩 점수 반환 제거됨.
- `dmascoring.py`는 순수 factor → score 계산만 담당.

### 3.2 Materiality Result API Phase 2A

구현된 endpoint:

```text
GET /materiality/results/{runId}
GET /materiality/benchmark/{runId}
GET /materiality/media/{runId}
GET /materiality/survey/{runId}
GET /materiality/selection-process/{runId}
```

핵심 파일:

```text
backend/src/apis/materiality.py
backend/src/models/materiality.py
backend/src/services/materialities/service.py
backend/src/utils/dmarepository.py
```

역할:

- `ESG_DMA_SCORE_SUMMARY`를 기준으로 전체 결과, matrix, topIssues, coverage, nextStep, selectionReason 등을 조립.
- UI-04~UI-07 전체 결과 화면은 가능하면 하나의 materiality result 데이터로 대응한다.

### 3.3 Report API Skeleton

구현된 endpoint:

```text
GET /report/drafts/{runId}
PATCH /report/drafts/{draftId}
GET /report/drafts/{runId}/paragraphs/{paragraphId}/trace
POST /report/drafts/{runId}/download
```

핵심 파일:

```text
backend/src/apis/report.py
backend/src/models/report.py
backend/src/services/reports/service.py
backend/src/utils/reportrepository.py
```

현재 상태:

- 보고서 조회/trace skeleton은 존재.
- 실제 LLM 문단 생성, PDF/DOCX export, edited_text 저장은 아직 본구현 전.

### 3.4 Media News Crawler MVP 통합

현재 가장 많이 구현된 E2E 흐름.

프론트:

```text
frontend/src/homes/reports/Media.jsx
```

백엔드:

```text
backend/src/models/media.py
backend/src/apis/media.py
backend/src/services/medias/service.py
backend/src/services/medias/crawler.py
backend/src/services/medias/crawlers/base.py
backend/src/services/medias/crawlers/impacton.py
backend/src/services/medias/crawlers/esgeconomy.py
backend/src/services/medias/pipeline.py
backend/src/services/medias/adapter.py
backend/src/services/medias/baseline.py
```

현재 흐름:

```text
Media.jsx
  ↓
POST /media/news/crawl-and-analyze
  ↓
runMediaCrawlAndAnalyze()
  ↓
crawlNewsArticles()
  ↓
ImpactOnCrawler / EsgEconomyCrawler
  ↓
dateFrom/dateTo 필터
  ↓
현대자동차 OR 자동차부품산업 필터
  ↓
processMediaPipeline()
  ↓
KR-SBERT embedding + 62개 subIssue 유사도 매핑
  ↓
convertMediaToDmaSignals()
  ↓
applyMediaBaseline()
  ↓
scoreDmaSignals()
  ↓
saveDmaSignals()
  ↓
ESG_DMA_SIGNAL_DETAIL / ESG_DMA_EVIDENCE / ESG_DMA_SCORE_SUMMARY
```

현재 request:

```json
{
  "runId": 1,
  "sources": ["impacton"],
  "dateFrom": "2024-01-01",
  "dateTo": "2025-12-31"
}
```

중요 주의사항:

1. 현재 UI는 한 번에 `impacton` 또는 `esgeconomy` 하나만 실행한다.
2. 두 언론사를 동시에 돌리려면 multi-select 또는 “전체” 옵션이 필요하다.
3. 실제 DB 저장 여부는 별도 `runId`로 mutation smoke test를 해야 확정된다.
4. 실제 사이트 HTML이 crawler regex와 맞지 않으면 수집 0건이 나올 수 있다.
5. `sourceUrl` / `publishedAt`이 evidence table에 정식 컬럼으로 저장되는지는 추가 확인/보완 대상이다.

---

## 4. 현재 빠져 있는 중요 설계: G0 기반 Company Context Modifier

### 4.1 원래 의도

초기 기획에는 다음 파트가 있었다.

```text
G0 경영일반 / 회사 사업현황 / 가치사슬 / 재무규모 / 업종특성을 읽고
AI가 회사 context profile을 만든다.
이 profile을 바탕으로 rule engine이 제한된 context modifier를 적용한다.
```

현재 production 코드에는 이 파트가 아직 없다.

현재 들어가 있는 `MVP_DEMO_COMPANY_KEYWORDS = ["현대자동차"]`, `MVP_DEMO_INDUSTRY_KEYWORDS = ["자동차부품산업"]`는 기사 필터링용이지 점수 기준 보정용이 아니다.

### 4.2 반드시 지켜야 할 설계 방향

AI가 점수를 직접 조정하면 안 된다. 구조는 아래처럼 해야 한다.

```text
G0 데이터 조회
  ↓
AI Company Context Profiler
  ↓
구조화된 CompanyContextProfile 생성
  ↓
Rule-based Context Modifier 계산
  ↓
Final Aggregation 단계에서 제한적으로 반영
```

### 4.3 modifier 적용 위치

Stage score에는 modifier를 섞지 않는다.

```text
benchmark score = 순수 벤치마킹 결과
media score = 순수 미디어 결과
survey score = 순수 설문 결과
final score = raw final score + context modifier
```

이유:

- 단계별 UI 설명을 왜곡하지 않기 위해.
- 회사 context 보정은 최종 의사결정 보정값으로만 보여줘야 하기 때문.

### 4.4 modifier 범위

```text
contextImpactModifier: -0.5 ~ +0.5
contextFinancialModifier: -0.5 ~ +0.5
```

기본값은 0. 데이터 부족 시 0.

### 4.5 신규 설계 후보 파일

```text
backend/src/models/materialitycontext.py
backend/src/services/materialities/context.py
backend/src/utils/companycontextrepository.py
```

후보 함수:

```text
getCompanyContextForRun(runId)
buildCompanyContextProfile(contextFacts)
calculateContextModifiers(profile, subIssueCode)
applyContextModifiersToFinalScores(runId)
```

### 4.6 CompanyContextProfile 예시

```json
{
  "companyContextProfile": {
    "companyName": "현대자동차",
    "industry": "자동차부품산업",
    "valueChainExposure": "high",
    "globalCustomerExposure": "high",
    "supplyChainDependency": "high",
    "transitionExposure": "high",
    "productSafetyExposure": "high",
    "evidenceMetricIds": ["G0-01", "G0-04", "G0-05"]
  },
  "contextModifiers": [
    {
      "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
      "impactModifier": 0.1,
      "financialModifier": 0.3,
      "reason": "자동차부품산업 특성상 완성차 고객의 전환계획 요구와 제품 포트폴리오 전환 영향이 큼"
    }
  ]
}
```

### 4.7 다음 작업 지시 요약

```text
다음 작업 1순위 중 하나는 Company Context Modifier 설계/구현이다.
단, AI가 최종 점수를 직접 주는 구조가 아니라,
AI가 context profile을 만들고 rule engine이 제한된 modifier만 적용하는 구조여야 한다.
```

---

## 5. 다음 작업 패키지별 상세 지시

## WP-01. Company Context Modifier 설계 및 구현

### 목표

G0 경영일반/회사 현황 데이터를 기반으로 회사별 점수 민감도를 반영한다.

### 주요 데이터 후보

```text
ESG_COMPANY_PROFILE
ESG_KPI_FACT
ESG_GROUP_ROLLUP_RESULT
G0 metric/atomic metric
- 조직 정보
- 보고 경계
- 가치사슬
- 사업모델
- 매출/자산/사업장/임직원 등 기초 규모
```

### 구현 순서

```text
1. COMPANY_CONTEXT_MODIFIER_PLAN_v1.md 작성
2. G0 데이터 조회 repository 설계
3. CompanyContextProfile DTO 설계
4. AI profiler prompt 설계
5. Rule modifier 산식 설계
6. final score 적용 위치 설계
7. DB 저장 방식 결정
8. API response에 contextModifierReason 포함
```

### 금지사항

- Stage score에 modifier를 섞지 말 것.
- AI에게 score05를 직접 산출하게 하지 말 것.
- modifier 범위를 무제한으로 열지 말 것.
- G0 데이터가 부족한데 강제로 modifier를 적용하지 말 것.

---

## WP-02. Media News 통합 로직화 마무리

### 현재 상태

MVP 구조는 이미 구현됐다.

남은 검증/보완:

```text
1. DB mutation smoke test
2. sourceUrl/publishedAt evidence 저장 확인
3. 실제 사이트 HTML 변경 대응
4. 단일 선택 vs 2개 동시 선택 UI 결정
5. GET /materiality/media/{runId} 실제 반영 확인
```

### Smoke Test 기준

별도 테스트 runId를 사용한다.

```text
POST /media/news/crawl-and-analyze
→ ESG_DMA_SIGNAL_DETAIL 저장 여부
→ ESG_DMA_EVIDENCE 저장 여부
→ ESG_DMA_SCORE_SUMMARY media_external_impact_score / financial_score 갱신 여부
→ rank_no 갱신 여부
→ GET /materiality/media/{runId} response 반영 여부
```

### 보완 권장

```text
1. Media.jsx에 “전체” 옵션 추가 여부 결정
2. ESG_DMA_EVIDENCE에 source_url, source_published_at 저장 보완
3. sourceBreakdown의 PARTIAL_FAILED / FAILED 실제 시나리오 검증
```

---

## WP-03. Benchmark Reference 통합

### 목표

벤치마킹도 미디어 분석-언론처럼 reference 코드를 기반으로 production 서비스에 통합한다.

목표 흐름:

```text
SR 파일 업로드/선택
  ↓
OCR 또는 텍스트 추출
  ↓
임베딩/유사도 매핑
  ↓
62개 subIssue 매핑
  ↓
DMASignal 변환
  ↓
benchmark baseline / scoring
  ↓
DB 저장
  ↓
ESG_DMA_SCORE_SUMMARY benchmark score 갱신
  ↓
Frontend benchmark result API 반영
```

### 현재 전제

- benchmark API 실행 흐름은 일부 존재.
- 그러나 reference 기반 수집/임베딩/서브이슈 매핑/결과 DB 적재/프론트 연동까지 완전 통합은 아직 정리 필요.

### 신규 문서 필요

```text
BENCHMARK_REFERENCE_INTEGRATION_PLAN_v1.md
```

포함 내용:

```text
1. 현재 benchmark 코드 분석
2. reference 코드 분석
3. production으로 이식할 기능
4. 버릴 reference 코드
5. sourceType 구분: leader_sr / peer_sr / own_sr
6. TE_SR_FILE 유지 여부
7. evidence 저장 방식
8. benchmark ratio / blind spot 계산
9. UI-01 benchmark result API 연동
10. smoke test 기준
```

### 주의사항

- benchmark topIssues는 final_score가 아니라 benchmark stage score 기준으로 보여야 한다.
- 전체 결과 topIssues는 final_score/rank_no 기준이다.
- benchmark ratio는 단순 signal count가 아니라 source report 단위 기준이 더 적절하다.
- blind spot은 리더/피어에는 관측되나 자사에는 미관측인 이슈를 의미한다.

---

## WP-04. Stakeholder Survey Google Form 통합

### 목표

설문셋 JSON을 업로드 또는 생성하면 Google Apps Script API를 통해 Google Form을 만들고, 응답 결과를 수집하여 점수화하고 DB에 반영한다.

### reference 현황

```text
backend/references/survey/main.py
backend/references/survey/surveyTemplate.json
```

reference 기능:

- Google Apps Script URL로 form 생성 payload 전송.
- Google Sheets API로 응답 export.
- 현재는 CSV 저장 중심이며 production DB 저장 구조가 아님.

### production 목표 흐름

```text
설문 JSON 업로드/생성
  ↓
selected subIssue 기반 설문 문항 구성
  ↓
Google Form 생성
  ↓
formId/formUrl/sheetId 저장
  ↓
응답 수집/sync
  ↓
ESG_DMA_SURVEY_RESPONSE 정규화 저장
  ↓
survey stage score 계산
  ↓
ESG_DMA_SCORE_SUMMARY survey score 갱신
  ↓
GET /materiality/survey/{runId} 반영
```

### 신규 문서 필요

```text
SURVEY_GOOGLE_FORM_INTEGRATION_PLAN_v1.md
```

### 신규/수정 파일 후보

```text
backend/src/apis/survey.py
backend/src/models/survey.py
backend/src/services/surveys/service.py
backend/src/services/surveys/googleform.py
backend/src/utils/surveyrepository.py
```

### 필요한 API 후보

```text
POST /survey/forms/{runId}/create
GET /survey/forms/{runId}
POST /survey/forms/{runId}/sync-responses
GET /materiality/survey/{runId}
```

### 주의사항

- 현재 v1은 `axisSeparatedYn=false`다.
- 장기적으로 impact/financial 분리 설문 구조가 필요하다.
- 응답률 분모는 MVP에서는 default target을 쓸 수 있으나, 반드시 `targetSource="MVP_DEFAULT"`로 표시해야 한다.
- Google credential 및 Apps Script URL은 환경변수/setting으로 관리해야 한다.

---

## WP-05. 전체 결과 화면 고도화

### 목표

최종 선정된 subIssue 결과를 전체 결과 단계에서 정확히 표현한다.

관련 화면:

```text
UI-04 전체 결과 - 다음 단계 연결형
UI-05 전체 결과 - 점수 해석형
UI-06 전체 결과 - 후보군→최종 선정 과정형
UI-07 전체 결과 - 최종 요약형
```

### 현재 원칙

UI-04~UI-07은 가능하면 하나의 `GET /materiality/results/{runId}` response를 서로 다른 레이아웃으로 보여주는 구조로 간다.

### 필요한 데이터

```text
totalCandidateSubIssueCount
summaryRowCount
scoredSubIssueCount
selectedSubIssueCount
highPriorityCount
matrixItems
topIssues
selectionReasons
nextStep
coverageSummary
selectionSource
fallbackYn
```

### 주의사항

- 최종 선정 대상은 MVP에서 Top 5.
- 전체 표/매트릭스는 Top 10까지 표시 가능.
- selected table이 비어 있으면 rank fallback 사용.
- `selectionSource = TABLE | RANK_FALLBACK` 표시.
- score05/score10 동시 반환.

---

## WP-06. 선정 subIssue 기반 지표 온보딩

### 목표

최종 선정된 subIssue에 매핑되는 지표/atomic metric을 사용자에게 입력하게 하고, 입력 후 DB에 저장한다.

### 필요 흐름

```text
selected subIssue Top 5
  ↓
subIssue → metric → atomic metric mapping 조회
  ↓
온보딩 입력 UI 렌더링
  ↓
사용자 입력
  ↓
ESG_ONBOARDING_INPUT_VALUE 저장
  ↓
승인/검증
  ↓
ESG_KPI_FACT 적재
  ↓
필요 시 ESG_GROUP_ROLLUP_RESULT 생성
```

### 기존 대화상 중요한 원칙

- 지주사/자회사 롤업은 MVP에서 핵심.
- 각 회사는 자기 company_id로 온보딩한다.
- 롤업 승인 전에는 group rollup result를 보고서에 사용하면 안 된다.
- 롤업 승인 후에만 그룹 통합 지표로 사용한다.
- 보고서 데이터 추적에서는 direct 지표와 group rollup 지표를 구분해서 보여줘야 한다.

### 주의사항

- subIssue는 온보딩 UI에 직접 과하게 노출하지 않아도 되지만, 내부 매핑 기준으로는 필요하다.
- metric_id와 atomic_metric_id를 혼동하지 말 것.
- 보고서 생성용 fact는 atomic metric 기준으로 trace 가능해야 한다.

---

## WP-07. AI 보고서 생성 통합

### 목표

선정된 subIssue와 온보딩/롤업 데이터를 기반으로 AI가 보고서 문단을 생성하고, 생성 결과와 근거를 DB에 저장한다.

### reference 현황

```text
backend/references/sr/airag.py
backend/references/sr/uploadServer.py
backend/references/storage/ocr/chunks/2023~2025
PostgreSQL pgvector ai_sr
```

reference의 주요 흐름:

```text
ESG_KPI_FACT 조회
ESG_GROUP_ROLLUP_RESULT 조회
pgvector ai_sr 검색
LangChain ChatPromptTemplate
ChatOllama
StrOutputParser
보고서 문단 생성
```

### production 목표 흐름

```text
selected Top 5 subIssue
  ↓
metric/atomic metric binding 조회
  ↓
KPI fact / rollup result 조회
  ↓
SR style retrieval from pgvector ai_sr
  ↓
LLM paragraph generation
  ↓
ESG_REPORT_RUN 생성
  ↓
ESG_REPORT_SECTION_DRAFT 저장
  ↓
ESG_REPORT_REFERENCE 저장
  ↓
GET /report/drafts/{runId}로 조회
  ↓
trace API로 근거 표시
```

### 신규 문서 필요

```text
REPORT_GENERATION_INTEGRATION_PLAN_v1.md
```

### 신규/수정 파일 후보

```text
backend/src/services/reports/generation.py
backend/src/services/reports/srstyle.py
backend/src/utils/reportgenerationrepository.py 또는 reportrepository.py 확장
backend/src/models/report.py 확장
backend/src/apis/report.py에 POST /report/drafts/{runId}/generate 추가
```

### 반드시 버릴 reference 요소

- 하드코딩 issueMap.
- 한글 이슈명을 production key로 쓰는 방식.
- 하드코딩 templates.
- 독립 실행부 `if __name__ == "__main__"`.
- settings 직접 import 방식.

### LangChain 사용 위치

LangChain은 전체 백엔드가 아니라 보고서 생성 agent에 적용한다.

```text
Fact Retrieval
  ↓
SR Style Retrieval
  ↓
Prompt Template
  ↓
LLM
  ↓
Output Parser
  ↓
DB Save
```

---

## WP-08. 보고서 편집 및 데이터 추적

### 목표

생성된 보고서 초안을 사용자가 수정할 수 있고, 각 문단의 근거 지표/롤업 데이터/AI 근거를 추적할 수 있게 한다.

### 현재 API Skeleton

```text
GET /report/drafts/{runId}
PATCH /report/drafts/{draftId}
GET /report/drafts/{runId}/paragraphs/{paragraphId}/trace
POST /report/drafts/{runId}/download
```

### 필요한 DB migration

```sql
ALTER TABLE ESG_REPORT_SECTION_DRAFT
ADD COLUMN edited_text LONGTEXT NULL,
ADD COLUMN last_edited_by_user_id BIGINT NULL,
ADD COLUMN last_edited_at DATETIME NULL,
ADD COLUMN section_order INT NULL,
ADD COLUMN paragraph_order INT NULL;
```

### MVP 편집 원칙

- 수정 가능해야 한다.
- 다만 MVP에서는 edited_text에 대한 별도 근거 추적은 하지 않는다.
- 추적은 original_generated_text 기준으로 한다.
- 사용자가 수정한 문단의 근거 재계산/재추적은 고도화로 둔다.

### Trace type

```text
reference_type = kpi_fact 또는 onboarding_input → DIRECT
reference_type = rollup_result → GROUP_ROLLUP
불명확 → UNKNOWN
```

### 데이터 추적 패널 필수 표시

```text
paragraphId
traceType: DIRECT | GROUP_ROLLUP | UNKNOWN
metricId
atomicMetricId
metricName
unit
dataType
latestValue
valuesByYear
companyBreakdown
calculationFormula
aiEvidenceSummary
relatedParagraphs
```

---

## 6. UI 관련 주의사항

### 6.1 9개 UI 화면 기준

```text
UI-01 벤치마킹 분석 결과
UI-02 미디어 분석 결과
UI-03 이해관계자 설문 결과
UI-04 전체 결과 - 다음 단계 연결형
UI-05 전체 결과 - 점수 해석형
UI-06 전체 결과 - 후보군→최종 선정 과정형
UI-07 전체 결과 - 최종 요약형
UI-08 보고서 생성 확인
UI-09 데이터 추적 패널
```

MVP 필수 우선순위:

```text
1. UI-01 벤치마킹 분석 결과
2. UI-02 미디어 분석 결과
3. UI-03 이해관계자 설문 결과
4. UI-07 전체 결과 최종 요약형
5. UI-08 보고서 생성 확인
6. UI-09 데이터 추적 패널
```

UI-04~UI-06은 UI-07과 같은 result API를 다른 패널/섹션으로 표현하는 후보로 본다.

### 6.2 Media.jsx 주의사항

현재 MVP 기준:

```text
사용자는 언론사와 기간만 선택한다.
키워드 입력은 없다.
언론사 option은 impacton, esgeconomy 2개만 있다.
자동 적용 필터는 read-only 안내로 표시한다.
```

자동 적용 필터:

```text
현대자동차 · 자동차부품산업
```

주의:

- 실제로는 백엔드 하드코딩 service constant다.
- 사용자가 수정하는 입력값이 아니다.
- 현재는 단일 select다. 2개 동시 실행이 필요하면 multi-select 또는 “전체” 옵션을 추가해야 한다.

### 6.3 보고서 생성 확인 UI 주의사항

- 보고서 본문이 메인 영역이다.
- KPI 카드는 작게 위쪽에 표시한다.
- 오른쪽 패널은 데이터 추적 영역이다.
- 보고서 본문에 회사 스코프 데이터 행을 별도로 과하게 노출하지 않는다.
- 데이터 추적 패널에서만 회사별 direct/rollup 구성과 계산식을 보여준다.
- rollup 지표와 direct 지표는 같은 UI 틀에서 내용만 다르게 보여준다.

---

## 7. DB 관련 주의사항

### 7.1 현재 중요 테이블

```text
ESG_DMA_SIGNAL_DETAIL
ESG_DMA_EVIDENCE
ESG_DMA_SCORE_SUMMARY
ESG_DMA_SURVEY_RESPONSE
ESG_KPI_FACT
ESG_GROUP_ROLLUP_RESULT
ESG_REPORT_RUN
ESG_REPORT_SECTION_DRAFT
ESG_REPORT_REFERENCE
ESG_ATOMIC_METRIC_MASTER
ESG_CALCULATION_RULE
TE_SR_FILE
```

### 7.2 migration 필요 후보

```sql
-- DMA signal trace
ALTER TABLE ESG_DMA_SIGNAL_DETAIL
ADD COLUMN scoring_payload_json LONGTEXT NULL;

-- Media evidence 보완 후보
ALTER TABLE ESG_DMA_EVIDENCE
ADD COLUMN source_url VARCHAR(1000) NULL,
ADD COLUMN source_published_at VARCHAR(50) NULL;

-- Report edit/order
ALTER TABLE ESG_REPORT_SECTION_DRAFT
ADD COLUMN edited_text LONGTEXT NULL,
ADD COLUMN last_edited_by_user_id BIGINT NULL,
ADD COLUMN last_edited_at DATETIME NULL,
ADD COLUMN section_order INT NULL,
ADD COLUMN paragraph_order INT NULL;
```

주의:

- 실제 DB에 이미 존재하는 컬럼은 중복 추가하지 않는다.
- migration 전 `SHOW COLUMNS`로 확인한다.
- MVP에서는 JSON 타입보다 MariaDB 호환성 때문에 LONGTEXT가 안전하다.

---

## 8. 다음 채팅방에서 바로 사용할 작업 지시 요약

아래 순서대로 가는 것을 권장한다.

```text
1. Media News 실제 DB smoke test
2. Media evidence source_url/source_published_at 저장 보완
3. Company Context Modifier 설계 문서 작성
4. Benchmark Reference Integration Plan 작성
5. Survey Google Form Integration Plan 작성
6. Report Generation Integration Plan 작성
7. 각 plan 승인 후 구현 착수
```

### 8.1 다음 채팅방 첫 지시 예시

```text
현재 프로젝트는 SKM ESG 지속가능경영보고서 AI 자동 생성 플랫폼 MVP입니다.
먼저 /mnt/data/ESG_MVP_NEXT_PHASE_HANDOFF_v1.md 문서를 읽고, 현재 레포 구조와 작업 의도를 파악하세요.

코드 수정 전에 다음을 보고하세요.
1. 현재 media news E2E가 문서와 일치하는지
2. DB smoke test에 필요한 runId와 쿼리
3. source_url/source_published_at 저장 보완 필요 여부
4. Company Context Modifier를 어디에 넣어야 하는지
5. 다음 구현 우선순위

아직 React나 scoring 산식은 임의 수정하지 마세요.
```

---

## 9. 금지사항 요약

```text
- AI가 final score를 직접 산출하게 하지 말 것.
- Stage score에 context modifier를 섞지 말 것.
- subissuemaster.py 외 별도 이슈 기준을 만들지 말 것.
- 한글 이슈명을 subIssueCode로 저장하지 말 것.
- Media topIssues를 final_score 기준으로 정렬하지 말 것.
- 전체 결과 topIssues는 final_score/rank_no 기준이다.
- 사용자가 media keyword를 입력하는 구조로 되돌리지 말 것.
- MVP에서 임의 언론사 URL 추가 기능을 구현하지 말 것.
- report edited_text 기준 trace를 MVP에서 구현하려고 하지 말 것.
- reference 코드를 그대로 production에 복붙하지 말 것.
- LangGraph를 전체 시스템에 무리하게 적용하지 말 것.
```

---

## 10. 최종 요약

현재 시스템은 다음 상태다.

```text
DMA scoring core: 1차 freeze 완료
Materiality result API: 1차 구현 완료
Report API: skeleton 완료
Media news crawler E2E: 코드상 연결 완료, DB smoke 필요
Benchmark: reference 통합 필요
Survey: reference 통합 필요
Company context modifier: 설계/구현 필요
Onboarding: selected subIssue 기반 연동 필요
Report generation: reference LangChain/RAG 기반 production 통합 필요
Report editing/trace: skeleton → 본구현 필요
```

가장 중요한 다음 방향은 두 가지다.

```text
1. 미디어-언론 E2E를 실제 DB smoke test로 닫는다.
2. G0 기반 Company Context Modifier를 AI profile + rule modifier 구조로 설계한다.
```

이 문서를 기준으로 다음 작업자는 이전 대화 맥락 없이도 같은 방향으로 이어서 작업해야 한다.
