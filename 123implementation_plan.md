# 123implementation_plan

작성일: 2026-05-28
상태: 계획서 수정 단계. 코드 구현은 본 문서 승인 후 진행한다.

## 1. 목적

이 문서는 SKM ESG 지속가능경영보고서 AI 자동 생성 MVP의 아키텍처 방향을 정정하고, WP-01 Company Context Modifier의 다음 구현 범위를 고정하기 위한 계획서다.

최종 목표는 AI 에이전트를 활용한 ESG 공시보고서 자동화이지만, 모든 로직을 LangGraph 또는 LangChain 기반 에이전트로 전환하지 않는다. ESG DMA와 공시보고서 자동화는 AI 활용성과 감사가능성, 재현성을 동시에 만족해야 하므로 영역별 선택적 멀티에이전트화를 적용한다.

## 2. 영역별 아키텍처 원칙

| 영역 | Agent 적용 방향 | 유지 원칙 |
|---|---|---|
| G0 AI 판단 / Company Context Profile | LangGraph/LangChain 적용 후보 | AI는 profile만 생성하고 점수, modifier, selected issue를 직접 결정하지 않는다. |
| DMA 점수화 / 집계 / selected issue 확정 | LangGraph 비적용 | `dmascoring.py`, `dmaaggregator.py`, `dmarepository.py` 중심의 deterministic rule pipeline을 유지한다. |
| 보고서 생성 | 후속 WP에서 LangGraph/LangChain 본격 적용 | selected subIssue, 온보딩/KPI/rollup fact, SR reference retrieval, 문단 생성, evidence binding, QA/reviewer를 별도 설계한다. |

## 3. G0 Company Context Profiler 적용 범위

WP-01에서는 G0 회사 프로파일 판단 영역에만 제한적으로 LangGraph를 도입한다.

적용 구조:

```text
LangGraph profiler = 1순위
Deterministic builder = fallback
Rule Engine = 최종 modifier 산정
DMA scoring = 기존 pipeline 유지
```

기존 `_hasAny`, `_levelByKeywords`, `_businessScaleExposure` 기반 deterministic builder는 삭제하지 않는다. LLM 호출 실패, LangGraph import 실패, JSON parsing 실패, confidence 부족, evidence 부족, timeout 발생 시 fallback으로 사용한다.

## 4. LangGraph Node 설계

LangGraph는 단순 LLM wrapper가 아니라 최소 node 구조를 갖는다.

```text
loadG0Facts
  -> normalizeG0Context
  -> analyzeCompanyProfileByLLM
  -> validateProfileSchema
  -> verifyProfileAgainstEvidence
  -> fallbackIfLowConfidence
  -> returnCompanyContextProfile
```

### 4.1 loadG0Facts

- `getCompanyG0Facts(companyId, reportingYear)`로 G0 facts를 조회한다.
- `getMaterialityRunContext(runId)`로 run/company context를 조회한다.
- company id, reporting year, raw G0 facts를 graph state에 저장한다.

### 4.2 normalizeG0Context

- LLM 입력용 compact context를 만든다.
- `metricId`, `atomicMetricId`, `metricName`, `atomicName`, `valueText`, `valueNumeric`, `unit`을 포함한다.
- 긴 text는 truncate하되 evidence id는 보존한다.

### 4.3 analyzeCompanyProfileByLLM

- LangChain structured output 또는 Pydantic parser를 사용한다.
- LLM은 CompanyContextProfile 후보만 생성한다.
- LLM은 score, modifier, selected subIssue를 반환하지 않는다.

LLM output 후보:

```json
{
  "industryExposure": "automotive_parts_high",
  "valueChainExposure": "high",
  "globalCustomerExposure": "medium",
  "euRegulationExposure": "medium",
  "transitionExposure": "high",
  "supplyChainDependency": "high",
  "productSafetyExposure": "medium",
  "businessScaleExposure": "high",
  "profileSummary": "G0 facts indicate automotive parts exposure and high supply chain dependency.",
  "evidenceMetricIds": ["G0-01", "G0-SITE-01"],
  "evidenceAtomicMetricIds": ["G0-01__A0001"],
  "evidenceText": ["사업모델 설명 중 자동차 부품 및 공급망 구조 언급"],
  "confidence": 0.76
}
```

### 4.4 validateProfileSchema

- Pydantic schema validation을 수행한다.
- enum 허용값을 검증한다.
- 허용되지 않은 값은 `unknown`으로 낮추거나 제거한다.
- JSON parsing 실패 시 fallback flag를 설정한다.

### 4.5 verifyProfileAgainstEvidence

- exposure 판단이 G0 fact 근거와 연결되어 있는지 검증한다.
- evidenceMetricIds/evidenceAtomicMetricIds가 비어 있는 판단은 confidence를 낮춘다.
- evidence 없는 high exposure는 medium 또는 unknown으로 낮춘다.
- hallucination 방지를 위해 evidence id가 실제 normalizedFacts에 존재하는지 확인한다.

### 4.6 fallbackIfLowConfidence

아래 조건 중 하나라도 발생하면 deterministic builder를 사용한다.

- LangGraph import 실패
- LLM provider/model 미설정
- LLM disabled
- LLM timeout 또는 호출 실패
- JSON parsing 실패
- schema validation 실패
- evidence 부족
- confidence < 0.5

### 4.7 returnCompanyContextProfile

- 최종 CompanyContextProfileDto를 반환한다.
- `profileSource`는 `LANGGRAPH_LLM`, `DETERMINISTIC_FALLBACK`, `HYBRID` 중 하나를 사용한다.
- `context_json`에는 graph node trace, fallback reason, evidence verification 결과를 남긴다.

## 5. Rule Engine 유지 원칙

LangGraph가 만든 profile은 rule engine으로만 전달한다.

Rule Engine에서만 수행할 일:

- subIssue별 rule mapping
- impact modifier 산정
- financial modifier 산정
- modifier clamp
- 관측 stage 조건 검사
- confidence guard
- rank movement guard
- final score 재계산

유지 흐름:

```text
CompanyContextProfile
  -> calculateContextModifier()
  -> guardContextModifier()
  -> updateContextModifiers()
  -> recalculateFinalScore()
```

## 6. Guard 전략

### 6.1 Modifier range 이중화

- MVP 적용 범위: -0.3 ~ +0.3
- 시스템 절대 상한: -0.5 ~ +0.5
- `calculateContextModifier()`에서는 MVP 범위로 clamp한다.
- DB 저장 전과 final 재계산 단계에서는 시스템 절대 상한으로 한 번 더 방어한다.

### 6.2 최소 관측 조건

benchmark/media/survey 중 최소 1개 stage score가 있는 subIssue에만 modifier를 적용한다.

모든 stage score가 NULL이면:

- impactModifier = 0.0000
- financialModifier = 0.0000
- guardAppliedYn = true
- guardReason = `NO_STAGE_OBSERVATION`

G0만으로 새로운 이슈 점수를 만들지 않는다.

### 6.3 Profile confidence guard

MVP 기준:

```text
MIN_PROFILE_CONFIDENCE_FOR_MODIFIER = 0.5
```

confidence < 0.5이면:

- modifier = 0.0000
- guardAppliedYn = true
- guardReason = `LOW_CONTEXT_CONFIDENCE`

### 6.4 Rank movement guard

- raw final score 기준 rawRank를 먼저 계산한다.
- context modifier 적용 후 adjustedRank를 계산한다.
- 순위 변동은 최대 2단계까지만 허용한다.
- Top 5 진입은 rawRank Top 8 이내 이슈만 허용한다.
- rawRank 9위 이하가 modifier만으로 Top 5에 들어오면 modifier를 축소하거나 0 처리한다.
- rawFinalScore 없는 이슈는 보정 대상에서 제외한다.

### 6.5 Transparency field

`SubIssueContextModifierDto`, API response, `modifier_json`에 아래 필드를 포함한다.

- rawRank
- adjustedRank
- rankChangedYn
- rankDelta
- guardAppliedYn
- guardReason
- profileSource
- profileConfidence

## 7. G0 입력과 일반 온보딩 순서

사용자 흐름은 아래처럼 고정한다.

```text
G0 입력: DMA 전
G0 읽기: DMA final aggregation 시점
G0 활용: selected subIssue 확정 전
일반 온보딩: selected subIssue 확정 후
```

G0는 일반 온보딩이 아니다. G0는 DMA 전 company profile 입력이다.

일반 온보딩은 DMA 결과에서 selected subIssue가 확정된 뒤, 해당 subIssue에 매핑된 `metrics_id` / `atomic_metrics_id`를 입력하는 단계다.

## 8. 이번 WP-01 제외 범위

- DMA scoring pipeline을 LangGraph로 바꾸지 않는다.
- benchmark/media/survey stage score를 LangGraph에서 계산하지 않는다.
- LLM이 impact/financial score를 직접 반환하게 하지 않는다.
- LLM이 selected subIssue를 직접 결정하게 하지 않는다.
- deterministic fallback builder를 삭제하지 않는다.
- 보고서 생성 LangGraph를 이번 작업에 포함하지 않는다.
- React 화면은 수정하지 않는다.

## 9. 수정/추가 대상 파일 목록

계획 승인 후 코드 구현 시 예상 파일은 아래와 같다.

### Backend

- `backend/src/models/materialitycontext.py`
- `backend/src/services/materialities/context.py`
- `backend/src/services/materialities/context_graph.py` 신규
- `backend/src/services/materialities/context_prompt.py` 신규 후보
- `backend/src/utils/companycontextrepository.py`
- `backend/src/utils/dmarepository.py`
- `backend/src/utils/dmaaggregator.py`
- `backend/src/apis/materiality.py`

### Docs

- `123implementation_plan.md`
- `COMPANY_CONTEXT_MODIFIER_PLAN_v1.md`
- `NEXT_PHASE_HANDOFF_ESG_DMA_MVP_v2.md`

## 10. 필요한 dependency

계획 승인 후 실제 도입 전 dependency 존재 여부를 먼저 확인한다.

- `langgraph`
- `langchain-core`
- `langchain-ollama`
- `pydantic` existing

LangGraph/LangChain dependency가 없거나 import 실패하면 deterministic fallback을 사용한다. dependency 부재는 API mutation 실패 사유가 아니다.

## 11. 환경변수

Ollama 모델명은 코드에 하드코딩하지 않는다.

```text
COMPANY_CONTEXT_LLM_PROVIDER=ollama
COMPANY_CONTEXT_LLM_MODEL=qwen2.5
COMPANY_CONTEXT_LLM_TIMEOUT_SEC=60
COMPANY_CONTEXT_LLM_ENABLED=true
```

`COMPANY_CONTEXT_LLM_ENABLED`가 false이거나 provider/model이 비어 있으면 deterministic fallback을 사용한다.

## 12. Smoke Test 계획

코드 구현 후 아래를 확인한다.

- LangGraph dependency 미설치 시 deterministic fallback 사용
- `COMPANY_CONTEXT_LLM_ENABLED=false` 시 deterministic fallback 사용
- LLM timeout/호출 실패 시 API 실패가 아니라 fallback 사용
- LLM invalid JSON 반환 시 fallback 사용
- confidence < 0.5 시 modifier 0.0000 및 `LOW_CONTEXT_CONFIDENCE`
- stage observation 없음 시 modifier 0.0000 및 `NO_STAGE_OBSERVATION`
- rank movement 2단계 초과 시 guard 적용
- rawRank 9위 이하 Top 5 진입 시 guard 적용
- benchmark/media/survey stage score 불변
- `ESG_DMA_CONTEXT_PROFILE.context_json`에 node trace 저장
- `modifier_json`에 raw/final score, rawRank/adjustedRank, guardReason 저장

## 13. 승인 후 구현 순서

1. 현재 deterministic context builder와 guard 동작을 기준선으로 고정한다.
2. LangGraph dependency와 env 설정을 optional로 로딩한다.
3. `context_graph.py`에 graph node를 구현한다.
4. LLM structured output schema와 prompt를 추가한다.
5. evidence verification과 fallback 조건을 구현한다.
6. 기존 rule engine으로 profile을 전달한다.
7. modifier guard와 rank guard 결과를 response 및 `modifier_json`에 남긴다.
8. compile과 smoke test를 실행한다.
