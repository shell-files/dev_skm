# COMPANY_CONTEXT_MODIFIER_PLAN_v1

작성일: 2026-05-28
대상: G0/회사 profile 기반 DMA final score additive 보정
구현 상태: MVP backend 구현 완료.

## 1. 문서 목적

Company Context Modifier는 회사의 사업모델, 가치사슬, 글로벌 고객 노출, 전환 리스크, 공급망 의존도 같은 G0/회사 context를 final materiality score에 제한적으로 반영하기 위한 장치다.

핵심 목적은 다음이다.

- 자동차부품산업/현대자동차 demo company 특성을 final score에 반영한다.
- AI가 직접 점수를 산정하지 않도록 한다.
- rule engine이 통제 가능한 범위에서 modifier를 산정한다.
- stage score의 설명 가능성을 유지한다.

## 2. 확정 원칙

### 2.1 additive modifier

`context_impact_modifier`, `context_financial_modifier`는 multiplier가 아니라 additive modifier다.

운영 DB와 clean schema는 `DECIMAL(6,4) NOT NULL DEFAULT 0.0000` 기준으로 정리 완료했다.

```text
final_impact_score =
  clamp(raw_final_impact_score + context_impact_modifier, 0, 5)

final_financial_score =
  clamp(raw_final_financial_score + context_financial_modifier, 0, 5)
```

기본값:

```text
0.0000
```

허용 범위:

```text
-0.5 ~ +0.5
```

### 2.2 적용 위치

modifier는 final aggregation 단계에서만 1회 적용한다.

적용 금지 대상:

- benchmark stage score
- media_external stage score
- survey stage score
- 개별 signal score
- factor score

### 2.3 AI 역할 제한

AI는 다음을 하지 않는다.

- 0~5 점수 직접 산정
- final score 직접 보정
- modifier 최종값 자유 산정
- subIssueCode를 한글명으로 생성/대체

AI는 다음만 수행한다.

- G0/회사 context 요약
- 구조화된 `CompanyContextProfile` 생성
- evidence metric id 연결
- rule engine이 사용할 exposure flag 생성
- modifier candidate의 설명 근거 작성

최종 modifier 값은 rule engine이 산정하고 clamp한다.

## 3. 처리 흐름

```text
G0 데이터 조회
  -> AI Company Context Profile 생성
  -> Rule Engine이 profile flag를 기준으로 modifier 산정
  -> ESG_DMA_CONTEXT_PROFILE에 context/modifier JSON 저장
  -> ESG_DMA_SCORE_SUMMARY.context_*_modifier 업데이트
  -> final aggregation 재계산
```

## 4. 데이터 source

우선 사용할 source:

- `ESG_MATERIALITY_RUN`
- `ESG_COMPANY_PROFILE`
- `ESG_ATOMIC_METRIC_MASTER`
- `ESG_ONBOARDING_INPUT_VALUE`
- `ESG_KPI_FACT`
- `ESG_GROUP_ROLLUP_RESULT`
- `ESG_DMA_CONTEXT_PROFILE`

우선 반영할 G0 metric:

| metricId | 의미 | 활용 |
|---|---|---|
| `G0-01` | 회사 개요 | 사업모델, 제품/서비스 |
| `G0-02` | 재무 개요 | 규모, 매출 노출 |
| `G0-03` | 사업장 현황 | 국내/해외 사업장 |
| `G0-04` | 가치사슬 | upstream/downstream, 공급망 |
| `G0-05` | 보고 기준 및 보고 범위 | 연결/보고범위 |
| `G0-06` | 연결 범위 | 그룹/자회사 범위 |

후속으로 사용할 수 있는 보조 metric:

- E1 기후 목표/감축/재생에너지 지표
- S6 공급망 감사/CAP 지표
- AP-E 저탄소 제품 지표
- AP-S 제품안전 지표

## 5. CompanyContextProfile 초안

AI가 생성해야 하는 구조는 아래처럼 제한한다.

```json
{
  "industryExposure": "automotive_parts_high",
  "valueChainExposure": "high",
  "globalCustomerExposure": "high",
  "euRegulationExposure": "medium",
  "transitionExposure": "high",
  "supplyChainDependency": "high",
  "productSafetyExposure": "medium",
  "businessScaleExposure": "medium",
  "evidenceMetricIds": ["G0-01", "G0-04", "G0-06"],
  "evidenceAtomicMetricIds": ["G0-01__QL0001", "G0-04__QL0001"],
  "profileSummary": "자동차부품산업 가치사슬과 글로벌 고객 요구에 노출된 회사 context"
}
```

허용 enum 초안:

| field | allowed values |
|---|---|
| `industryExposure` | `automotive_parts_high`, `automotive_parts_medium`, `general`, `unknown` |
| `valueChainExposure` | `low`, `medium`, `high`, `unknown` |
| `globalCustomerExposure` | `low`, `medium`, `high`, `unknown` |
| `euRegulationExposure` | `low`, `medium`, `high`, `unknown` |
| `transitionExposure` | `low`, `medium`, `high`, `unknown` |
| `supplyChainDependency` | `low`, `medium`, `high`, `unknown` |
| `productSafetyExposure` | `low`, `medium`, `high`, `unknown` |
| `businessScaleExposure` | `low`, `medium`, `high`, `unknown` |

## 6. Modifier rule engine 초안

Rule engine은 `CompanyContextProfile`과 `subIssueCode`를 입력받아 modifier를 산정한다.

출력:

```json
{
  "subIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
  "impactModifier": 0.0,
  "financialModifier": 0.3,
  "appliedRules": [
    {
      "ruleId": "CTX_AUTO_TRANSITION_FIN_001",
      "reason": "자동차부품산업 전환 노출이 높아 전환계획의 재무 중요도를 보정"
    }
  ]
}
```

### 6.1 rule examples

| subIssueCode | 조건 | impactModifier | financialModifier |
|---|---|---:|---:|
| `E_CLIMATE__CLIMATE_TARGETS_TRANSITION` | `transitionExposure = high` | `0.0` | `+0.3` |
| `E_CLIMATE__ENERGY_TRANSITION` | `transitionExposure = high` | `+0.1` | `+0.2` |
| `S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP` | `supplyChainDependency = high` | `+0.2` | `+0.2` |
| `E_PRODUCT__LOW_CARBON_PRODUCTS` | `industryExposure = automotive_parts_high` | `0.0` | `+0.3` |
| `S_CONSUMER__PRODUCT_SAFETY_QUALITY` | `productSafetyExposure = high` | `+0.2` | `+0.2` |
| `G_GOVERNANCE__BUSINESS_MODEL_VALUE_CHAIN` | `valueChainExposure = high` | `+0.1` | `+0.1` |

최종 modifier는 rule hit 합산 후 clamp한다.

```text
impactModifier = clamp(sum(rule.impactModifier), -0.5, 0.5)
financialModifier = clamp(sum(rule.financialModifier), -0.5, 0.5)
```

## 7. 저장 위치

### 7.1 ESG_DMA_CONTEXT_PROFILE

`ESG_DMA_CONTEXT_PROFILE`을 1차 저장소로 사용한다.

- `context_json`: AI CompanyContextProfile
- `modifier_json`: subIssue별 modifier 후보, rule hit, clamp 결과
- `confidence_score`: context profile 생성 신뢰도 또는 coverage

예시:

```json
{
  "contextProfile": {
    "industryExposure": "automotive_parts_high",
    "valueChainExposure": "high",
    "globalCustomerExposure": "high",
    "transitionExposure": "high",
    "supplyChainDependency": "high",
    "productSafetyExposure": "medium",
    "evidenceMetricIds": ["G0-01", "G0-04"]
  },
  "generatedBy": "AI_COMPANY_CONTEXT_PROFILER",
  "ruleVersion": "company-context-modifier-v1"
}
```

modifier 적용 전후 점수 설명 가능성을 위해 `modifier_json`에는 raw final score와 modifier 적용 후 score를 함께 저장한다.

예시:

```json
{
  "rawFinalImpactScore": 3.62,
  "contextImpactModifier": 0.2,
  "finalImpactScoreAfterModifier": 3.82,
  "rawFinalFinancialScore": 3.41,
  "contextFinancialModifier": 0.3,
  "finalFinancialScoreAfterModifier": 3.71,
  "appliedRules": []
}
```

### 7.2 ESG_DMA_SCORE_SUMMARY

최종 적용값은 subIssue별로 `ESG_DMA_SCORE_SUMMARY`에 저장한다.

- `context_impact_modifier`
- `context_financial_modifier`

기본값은 반드시 `0.0000`이어야 한다.

## 8. Backend 파일 구조 초안

신규 또는 보강 후보:

```text
backend/src/models/materialitycontext.py
backend/src/services/materialities/context.py
backend/src/utils/companycontextrepository.py
backend/src/utils/dmaaggregator.py
backend/src/utils/dmarepository.py
backend/src/apis/materiality.py
```

역할:

| 파일 | 역할 |
|---|---|
| `models/materialitycontext.py` | context profile, modifier response DTO |
| `services/materialities/context.py` | workflow orchestration and deterministic MVP profile/rule engine |
| `utils/companycontextrepository.py` | G0/context DB 조회 및 저장 |
| `utils/dmaaggregator.py` | additive formula 유지 |
| `utils/dmarepository.py` | final recalc 시 modifier 조회/적용 |
| `apis/materiality.py` | thin apply endpoint |

MVP 수동 실행 endpoint:

```text
POST /materiality/context/{runId}/apply
```

외부 gateway/baseURL 기준 문서 경로:

```text
POST /api/v1/materiality/context/{runId}/apply
```

## 9. 함수 설계 초안

```python
def getCompanyContextForRun(runId: int) -> CompanyContextFacts:
    ...

def buildCompanyContextProfile(contextFacts: CompanyContextFacts) -> CompanyContextProfile:
    ...

def calculateContextModifiers(
    profile: CompanyContextProfile,
    subIssueCodes: list[str],
) -> list[SubIssueContextModifier]:
    ...

def saveCompanyContextProfile(
    runId: int,
    profile: CompanyContextProfile,
    modifiers: list[SubIssueContextModifier],
) -> int:
    ...

def applyContextModifiersToScoreSummary(
    runId: int,
    modifiers: list[SubIssueContextModifier],
) -> int:
    ...

def recalculateFinalScoresWithContext(runId: int) -> None:
    ...
```

## 10. Final aggregation 연결 방식

현재 `calculateFinalMateriality`는 이미 additive parameter를 받을 수 있다.

필요한 변경 방향:

1. `ESG_DMA_SCORE_SUMMARY`에서 stage score와 context modifier를 함께 조회한다.
2. modifier가 NULL이면 0.0으로 처리한다.
3. `calculateFinalMateriality(..., contextImpactModifier=..., contextFinancialModifier=...)`에 전달한다.
4. final score/rank를 갱신한다.

중요:

- context modifier 적용 전 stage score 재계산 결과는 바꾸지 않는다.
- final recalc만 다시 수행한다.
- modifier 변경 후에는 rank도 다시 갱신한다.

## 11. 검증 기준

### 11.1 unit smoke

- profile flag가 없는 경우 modifier는 모두 0.0.
- rule hit가 여러 개여도 최종 modifier는 -0.5~+0.5.
- unknown subIssueCode는 modifier 0.0.
- `subissuemaster.py`에 없는 subIssueCode는 저장하지 않는다.

### 11.2 DB smoke

검증 SQL:

```sql
SELECT
    sub_issue_code,
    benchmark_impact_score,
    media_external_impact_score,
    survey_impact_score,
    context_impact_modifier,
    final_impact_score,
    context_financial_modifier,
    final_financial_score,
    final_score,
    rank_no
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = :runId
ORDER BY rank_no;
```

확인할 것:

- modifier 변경 전후 stage score는 동일.
- modifier 변경 전후 final score만 바뀜.
- clamp가 0~5 범위를 보장.
- rank_no가 final_score 기준으로 재정렬.

### 11.3 regression

- Media topIssues는 여전히 `media_external` stage 기준.
- 전체 결과 topIssues는 `final_score/rank_no` 기준.
- score05/score10 응답 규칙 유지.

## 12. Open Questions

1. Company Context Modifier를 자동 실행할 trigger는 언제인가?
   - materiality run 생성 직후
   - 모든 stage score 생성 후
   - 결과 화면 진입 시 lazy execution

2. modifier rule version을 어디에 노출할 것인가?
   - `ESG_DMA_CONTEXT_PROFILE.modifier_json`
   - `ESG_MATERIALITY_RUN.scoring_rule_version`
   - 둘 다

3. modifier 적용값에 승인 workflow가 필요한가?
   - MVP는 자동 적용
   - P1 이후 reviewer 승인 가능

4. context profile 생성에 LLM 실패 시 fallback은 무엇인가?
   - profile unknown
   - all modifier 0.0
   - warning만 기록

## 13. 구현 우선순위

1. `CompanyContextProfile` DTO 작성. 완료.
2. G0/company context repository 작성. 완료.
3. deterministic MVP context profile builder 작성. 완료.
4. deterministic rule engine 작성. 완료.
5. `ESG_DMA_CONTEXT_PROFILE` 저장. 완료.
6. `ESG_DMA_SCORE_SUMMARY.context_*_modifier` 업데이트. 완료.
7. final recalc에서 modifier 조회/적용. 완료.
8. smoke test와 regression test. 완료.

후속: 실제 LLM profiler가 필요하면 현재 deterministic profile builder를 AI profiler adapter로 교체하되, rule engine과 final aggregation 적용 원칙은 유지한다.

## 14. 결론

Company Context Modifier는 다음 구조로만 구현한다.

```text
G0 데이터 조회
-> AI가 회사 context profile 생성
-> rule engine이 modifier 산정
-> final score에 additive 적용
```

이 구조를 지키면 AI가 회사 상황은 해석하되, 점수 보정은 통제 가능한 rule engine이 담당한다. 이것이 현재 DMA scoring 원칙과 가장 잘 맞는 방향이다.
