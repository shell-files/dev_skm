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

제약:

- 전체 FastAPI app boot 기반 HTTP smoke는 기존 `src.apis.auth` import 오류로 보류했다.
- materiality result API는 재계산된 final score/rank는 반환하지만 context guard transparency fields는 아직 직접 반환하지 않는다.

## 10. Open Questions

1. 결과 API에 context transparency section을 추가할지, 별도 `GET /materiality/context/{runId}`를 둘지 결정 필요.
2. branch `feature/onborading_renewal`의 오타를 `feature/onboarding_renewal`로 정리할지 결정 필요.
3. LangGraph dependency를 `pyproject.toml`에 명시할 시점 결정 필요.
