# NEXT_PHASE_HANDOFF_ESG_DMA_MVP_v2

## 0. 2026-05-28 아키텍처 정정 및 다음 단계 기준

이 핸드오프 문서는 최신 아키텍처 결정을 아래 기준으로 해석한다.

프로젝트의 최종 방향은 “AI 에이전트를 활용한 ESG 공시보고서 자동화”이지만, 모든 로직을 LangGraph/LangChain으로 바꾸지 않는다. 영역별 선택적 멀티에이전트화를 적용한다.

| 영역 | 다음 단계 적용 범위 | 비고 |
|---|---|---|
| G0 AI 판단 / Company Context Profile | WP-01에서 LangGraph profiler 제한 도입 | deterministic builder는 fallback으로 유지 |
| DMA 점수화 / 집계 / selected issue 확정 | LangGraph 비적용 | scoring, aggregation, ranking, selected issue rule은 deterministic pipeline 유지 |
| 보고서 생성 | 후속 WP의 핵심 LangGraph 적용 영역 | `references/sr` 기술 테스트를 기반으로 SR reference 검색, 문단 생성, QA/reviewer를 고도화 |

WP-01의 다음 구현 기준:

```text
loadG0Facts
  -> normalizeG0Context
  -> analyzeCompanyProfileByLLM
  -> validateProfileSchema
  -> verifyProfileAgainstEvidence
  -> fallbackIfLowConfidence
  -> returnCompanyContextProfile
  -> deterministic Rule Engine
  -> final score additive modifier
```

AI는 `CompanyContextProfile`만 생성한다. AI가 0~5 score, modifier, rank, selected subIssue를 직접 산정하거나 확정하지 않는다.

Rule Engine은 계속 아래를 담당한다.

- subIssue별 rule mapping
- modifier 산정과 clamp
- stage observation guard
- profile confidence guard
- rank movement guard
- final score와 rank 재계산

환경변수:

```text
COMPANY_CONTEXT_LLM_PROVIDER=ollama
COMPANY_CONTEXT_LLM_MODEL=qwen2.5
COMPANY_CONTEXT_LLM_TIMEOUT_SEC=60
COMPANY_CONTEXT_LLM_ENABLED=true
```

LangGraph/LLM 실패는 API 실패가 아니라 deterministic fallback으로 처리한다. 보고서 생성 LangGraph와 React 수정은 이번 WP-01 범위에서 제외한다.

작성일: 2026-05-28
대상 프로젝트: SKM ESG 지속가능경영보고서 AI 자동 생성 플랫폼 MVP

2026-05-28 추가 구현 상태:

- Company Context Modifier MVP backend 1차 구현 완료.
- 수동 실행 endpoint: `POST /materiality/context/{runId}/apply`
- 구현은 deterministic MVP context profile builder와 rule engine으로 구성.
- 실제 LLM profiler를 붙이더라도 AI는 profile flag만 만들고 modifier 산정은 rule engine이 담당한다.
- guard는 문서 기준 확정, deterministic rule guard 보강 완료: MVP range `-0.3 ~ +0.3`, system range `-0.5 ~ +0.5`, 최소 stage 관측, confidence >= 0.5, rank movement 최대 2단계, Top 5 진입 rawRank Top 8 제한을 필수 반영 기준으로 둔다.
- LangGraph profiler는 optional adapter 1차 추가. dependency/env 미설치, 비활성, 실패 시 deterministic fallback을 사용한다.

## 1. 문서 목적

이 문서는 `NEXT_PHASE_HANDOFF_ESG_DMA_MVP.md`를 현재 구현 상태와 확정 의사결정에 맞게 갱신한 다음 작업 인수인계 문서다.

이번 v2에서 특히 정정하는 항목은 다음과 같다.

- `ESG_DMA_SIGNAL_DETAIL.scoring_payload_json`은 운영 DB에 반영 완료.
- clean schema SQL에도 `scoring_payload_json` 반영 완료.
- `context_impact_modifier`, `context_financial_modifier`는 multiplier가 아니라 additive modifier로 확정.
- modifier 기본값은 `0.0000`, 허용 범위는 `-0.5 ~ +0.5`.
- modifier는 final aggregation 직후 1회만 적용하고 stage score에는 적용하지 않는다.
- Media WP-02는 대부분 완료로 재분류한다.

## 2. 현재 전체 상태 요약

| 영역 | 현재 상태 | 비고 |
|---|---|---|
| DMA scoring core | 1차 freeze 수준 완료 | AI는 factor/evidence 생성, 점수 산정은 `dmascoring.py` |
| score 기준 | 확정 | DB/API canonical `score05`, UI 표시 `score10 = score05 * 2` |
| final aggregation | 안정화 | survey 0.40, benchmark 0.35, media_external 0.25 |
| context modifier semantics | 확정/DB 반영 완료 | additive, 기본값 0.0000, final 단계 1회 |
| context modifier guard | deterministic guard 보강 완료 | MVP range, confidence, observed stage, rank movement, Top 5 entry guard 반영 |
| Materiality result API | 1차 구현 완료 | 결과/매트릭스/topIssues/selection fallback 포함 |
| Report API | skeleton 완료 | DB 조회 가능한 범위 반환, edit/export 본구현은 후속 |
| Media news crawler E2E | 대부분 완료 | 실제 사이트 fixed scope + 필터 결과 0건 가능성은 remaining risk |
| Media evidence URL/date 저장 | 완료 | `source_url`, `source_published_at` 저장 보완됨 |
| Benchmark | reference 통합 필요 | `TE_SR_FILE` 의존성 확인 필요 |
| Survey | reference 통합 필요 | MVP default target 유지, axis 분리는 후속 |
| Onboarding selected metric | 후속 필요 | selected subIssue 기반 metric onboarding 연결 필요 |
| Report generation | 후속 필요 | LangChain/RAG 기반 본구현 전 |

## 3. 확정된 점수 원칙

### 3.1 AI와 점수 계산 역할 분리

AI/embedding/adapter는 다음까지만 담당한다.

- evidence 추출
- subIssue 매핑
- IRO 후보 판단
- scoring factor 생성
- company context profile 생성
- modifier candidate 근거 생성

AI가 직접 0~5 점수를 산정하거나 final score를 올리고 내리는 구조는 금지한다.

### 3.2 canonical score

- DB 저장 점수: 0~5
- API canonical 점수: `score05`
- API/UI 표시 점수: `score10`
- 계산식: `score10 = score05 * 2`

### 3.3 final aggregation

현재 final score는 stage score를 가중 평균한 raw final score를 만든 뒤 context modifier를 더하는 구조로 확정한다.

```text
raw_final_impact_score =
  weighted_average(survey_impact, benchmark_impact, media_external_impact)

raw_final_financial_score =
  weighted_average(survey_financial, benchmark_financial, media_external_financial)

final_impact_score =
  clamp(raw_final_impact_score + context_impact_modifier, 0, 5)

final_financial_score =
  clamp(raw_final_financial_score + context_financial_modifier, 0, 5)

final_score =
  average(final_impact_score, final_financial_score)
```

### 3.4 context modifier 확정

`context_impact_modifier`, `context_financial_modifier`는 additive modifier다.

| 항목 | 확정값 |
|---|---|
| 의미 | raw final score에 더하는 보정값 |
| 기본값 | `0.0000` |
| 허용 범위 | `-0.5 ~ +0.5` |
| 적용 위치 | final aggregation 직후 1회 |
| stage score 적용 | 금지 |
| benchmark/media/survey 개별 점수 적용 | 금지 |

운영 DB와 clean schema 모두 `DEFAULT 0.0000`으로 반영 완료했다.

## 4. Media WP-02 재분류

### 4.1 완료로 보는 항목

Media News MVP 통합은 다음 기준을 대부분 충족했다.

- `POST /media/news/analyze` 유지: 수동 articles 입력 smoke/fallback API.
- `POST /media/news/crawl-and-analyze` 추가: Media.jsx 메인 UX용 API.
- request는 `runId`, `sources`, `dateFrom`, `dateTo`만 받는다.
- 사용자 keyword 입력 구조 제거.
- source registry는 `impacton`, `esgeconomy` 2개만 허용.
- unknown/disabled/duplicate source는 rejected/skipped 처리.
- 한 source 실패 시 다른 source는 계속 실행.
- dateFrom/dateTo는 수집 후 article date parsing 기반 필터.
- company/industry filter는 AND가 아니라 OR 조건.
- MVP 상수는 service 계층에 분리:
  - `MVP_DEMO_COMPANY_KEYWORDS = ["현대자동차"]`
  - `MVP_DEMO_INDUSTRY_KEYWORDS = ["자동차부품산업"]`
- pipeline 흐름:
  - crawler
  - `processMediaPipeline`
  - `convertMediaToDmaSignals`
  - `applyMediaBaseline`
  - `scoreDmaSignals`
  - `saveDmaSignals`
  - `ESG_DMA_SCORE_SUMMARY` 재계산
- `ESG_DMA_EVIDENCE.source_url`, `source_published_at` 저장 보완 완료.
- Media.jsx는 source select, `전체`, 기간 입력, read-only 자동 필터 안내를 갖는다.

### 4.2 remaining risk

실제 사이트 fixed section/list crawling은 정상 실행되더라도, 현재 demo filter인 `현대자동차 OR 자동차부품산업`에 걸리는 기사가 없으면 결과가 0건일 수 있다.

이건 API/DB 로직 실패가 아니라 MVP fixed scope와 demo filter 조합의 리스크다. 시연 전에는 다음 중 하나를 확인해야 한다.

- 실제 기간 범위를 넓혀 필터 통과 기사 존재 여부 확인.
- controlled smoke 기사로 DB write 경로 검증.
- 필요 시 demo 기간/필터 상수를 시연 데이터에 맞게 조정하되 사용자 keyword 입력으로 되돌리지 않는다.

### 4.3 Media smoke 기준

다음 smoke는 유지한다.

- 정상 요청: `POST /media/news/crawl-and-analyze`
- unknown source 요청
- 한 source 실패 시 partial response
- `ESG_DMA_SIGNAL_DETAIL` 저장 여부
- `ESG_DMA_EVIDENCE` 저장 여부
- `ESG_DMA_EVIDENCE.source_url`, `source_published_at` 저장 여부
- `ESG_DMA_SCORE_SUMMARY.media_external_*_score` 갱신 여부
- `GET /materiality/media/{runId}` 결과 반영 여부

## 5. scoring_payload_json 정정

운영 DB에는 아래 ALTER가 이미 반영된 상태로 본다.

```sql
ALTER TABLE ESG_DMA_SIGNAL_DETAIL
ADD COLUMN scoring_payload_json LONGTEXT NULL
COMMENT 'DMASignal camelCase payload and evidence trace JSON';
```

따라서 runtime DB 기준으로는 완료 항목이다.

`SKM_ESG_v5_2_28_table.sql` clean schema에도 반영 완료했다. 구버전 DB migration용 DDL은 문서에 유지한다.

## 6. DB schema gap 요약

상세 내용은 `DB_SCHEMA_GAP_CHECK_v1.md`를 기준으로 한다.

| 항목 | 현재 판단 | 조치 |
|---|---|---|
| `scoring_payload_json` | 운영 DB 반영 완료, clean schema 반영 완료 | 구버전 DB migration만 필요 |
| `context_impact_modifier` | 운영 DB와 clean schema 모두 0.0000 반영 완료 | Company Context Modifier 구현 전제 |
| `context_financial_modifier` | 운영 DB와 clean schema 모두 0.0000 반영 완료 | Company Context Modifier 구현 전제 |
| report edit columns | 미반영 | Phase 2B 전 DDL 필요 |
| report order columns | 미반영 | Phase 2B 전 DDL 필요 |
| media evidence URL/date | clean schema에 존재 | 코드 저장 완료, DATETIME 유지 |
| `TE_SR_FILE` | clean ESG schema에는 없음 | benchmark 통합 전 base table 의존성 확인 |

## 7. 다음 작업 우선순위

### WP-01. Company Context Modifier 설계 및 구현

MVP backend 1차 구현 완료. deterministic guard는 보강 완료했고, LangGraph profiler는 optional adapter로만 1차 추가했다.

구현 파일:

```text
backend/src/models/materialitycontext.py
backend/src/services/materialities/context.py
backend/src/utils/companycontextrepository.py
backend/src/utils/dmarepository.py
backend/src/apis/materiality.py
```

수동 실행 endpoint:

```text
POST /materiality/context/{runId}/apply
```

다음 단계 1순위였으며, 현재 MVP backend 구현은 완료된 상태다.

필수 원칙:

- G0/회사 profile 데이터를 조회한다.
- AI는 구조화된 `CompanyContextProfile`만 만든다.
- AI가 modifier 값을 직접 최종 확정하지 않는다.
- rule engine이 profile flag를 기준으로 modifier를 산정한다.
- modifier는 MVP 적용 범위 `-0.3 ~ +0.3`로 clamp하고, DB/재계산 직전 시스템 절대 상한 `-0.5 ~ +0.5`로 한 번 더 방어한다.
- final aggregation 단계에서만 additive 적용한다.
- stage score는 순수 benchmark/media/survey 결과로 유지한다.
- 판단 근거는 `ESG_DMA_CONTEXT_PROFILE.context_json`, `modifier_json` 또는 `scoring_payload_json` 계열 payload에 보존한다.
- stage score가 하나도 없는 subIssue에는 modifier를 적용하지 않는다.
- profile confidence가 0.5 미만이면 modifier는 0.0000이다.
- rawRank 대비 adjustedRank 변동은 최대 2단계로 제한한다.
- rawRank 9위 이하 이슈는 context modifier만으로 Top 5에 진입할 수 없다.

설계 문서는 `COMPANY_CONTEXT_MODIFIER_PLAN_v1.md`를 따른다.

### WP-02. Media News 통합 마무리

분류: 대부분 완료, smoke/운영 리스크 관리.

남은 일:

- 실제 사이트 기간별 통과 기사 존재 여부 점검.
- 시연용 runId와 데이터 생성 절차 정리.
- crawler HTML 변경 시 실패 정책 점검.

### WP-03. Benchmark Reference 통합

목표:

- reference SR upload/analyze 흐름을 production service 구조로 정리.
- `TE_SR_FILE` 또는 현재 파일 저장 테이블 의존성 확정.
- benchmark topIssues/commonIssues/blindSpotIssues API 결과 품질 개선.
- benchmark adapter fallback은 allowed IRO가 없으면 factor 제거 원칙 유지.

### WP-04. Survey Reference 통합

목표:

- 설문 응답 수집/집계 reference 흐름 production 반영.
- MVP default denominator 유지:
  - 임직원 150
  - 경영진 20
  - 외부 이해관계자 80
- `targetSource = "MVP_DEFAULT"`
- v1에서는 impact/financial 동일값 복사, `axisSeparatedYn = false`.

### WP-05. Result 화면 품질 개선

목표:

- UI-04~UI-07 공통 materiality result response 안정화.
- selected/fallback source 표시.
- final topIssues는 `final_score/rank_no` 기준.
- media topIssues와 혼동 금지.

### WP-06. Selected subIssue 기반 metric onboarding

목표:

- selected Top 5 subIssue 기준 required metric 산출.
- onboarding missing count 산출.
- report draft readiness 판단.

### WP-07. AI Report Generation

목표:

- selected Top 5 기반 report section/paragraph 생성.
- KPI/evidence trace 연결.
- 실제 PDF/DOCX export는 P1 후속으로 분리 가능.

### WP-08. Report Edit/Data Trace

목표:

- edit columns 반영 후 paragraph edit 저장.
- reference trace panel의 DIRECT/GROUP_ROLLUP 구분 본구현.
- edited text 기준 trace 고도화는 MVP 이후.

## 8. 다음 작업에서 금지할 것

- AI가 final score나 modifier 최종값을 자유 산정하게 하지 않는다.
- modifier를 stage score에 적용하지 않는다.
- `context_*_modifier = 1.0000`을 multiplier처럼 사용하지 않는다.
- Media topIssues를 final_score 기준으로 정렬하지 않는다.
- 전체 결과 topIssues를 media_external stage 기준으로 정렬하지 않는다.
- 사용자 media keyword 입력 구조로 되돌리지 않는다.
- MVP에서 임의 언론사/임의 URL crawling을 구현하지 않는다.
- `subissuemaster.py` 외 별도 subIssue 기준을 만들지 않는다.
- 한글 subIssue명을 subIssueCode로 저장하지 않는다.

## 9. 다음 담당자에게 남기는 결론

Company Context Modifier의 MVP backend 구현은 완료됐다.

다만 구현 전에 반드시 다음 두 가지가 선행되어야 한다.

1. DB modifier default를 additive 의미에 맞게 `0.0000`으로 고정한다. 완료.
2. AI profile과 rule engine의 역할 경계를 문서와 코드 구조에 반영한다.

권장 순서:

1. `DB_SCHEMA_GAP_CHECK_v1.md` 확인 및 DDL 확정.
2. `COMPANY_CONTEXT_MODIFIER_PLAN_v1.md` 승인.
3. context profile service/repository 구현.
4. final aggregation에 modifier 조회/적용 연결.
5. regression smoke: stage score 불변, final score만 modifier 반영 확인.
