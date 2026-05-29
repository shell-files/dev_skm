# Financial Exposure Rule Design v1

작성일: 2026-05-29

## 1. 문서 목적

이 문서는 `getG0FinancialBasis()`로 조회한 G0-02 재무 기준값을 사용해 `DMASignal.financialFactor`의 6개 magnitude 입력값을 어떻게 보강할지 정의한다.

이번 문서는 설계 확정용이다. 아직 다음 작업은 하지 않는다.

- `dmascoring.py` 산식 변경
- media/benchmark adapter 연결
- `FinancialFactor` DTO 변경
- survey weight 분리
- benchmark common/blind spot bonus 변경

## 2. 설계 원칙

1. financial basis는 G0-02만 사용한다.
2. AP-E-06 등 DMA 이후 selected subIssue 기반 본 온보딩 지표는 사용하지 않는다.
3. `getG0FinancialBasis(companyId, reportingYear, preferConsolidated=True)`를 통해 `revenue`, `operatingProfit`, `netIncome`, `capex`, `depreciation`을 조회한다.
4. AI는 financial score를 직접 산정하지 않는다.
5. Rule engine이 `FinancialFactor` magnitude를 산정한다.
6. `dmascoring.py`의 `calculateFinancialScore()`는 이번 MVP에서 유지한다.
7. `FinancialFactor` 입력값만 G0 기반으로 개선한다.
8. `DMASignal.scoringPayloadJson.financialExposureTrace`에 판단 근거를 저장한다.
9. G consolidated 값과 Q entity 값을 동시에 합산하지 않는다.
10. `subIssueCode`는 반드시 `backend/src/utils/subissuemaster.py`의 key를 사용한다.

## 3. 위치 제안

후속 구현 파일:

```text
backend/src/services/materialities/financial_exposure.py
```

사용 repository:

```text
backend/src/utils/dmafinancialrepository.py
```

후속 연결 지점 후보:

```text
benchmark/media adapter가 DMASignal 생성
-> financial_exposure.py가 FinancialFactor magnitude 보강
-> dmascoring.py scoreDmaSignals()
-> dmarepository.py saveDmaSignals()
```

## 4. Financial Channel 정의

현재 `FinancialFactor`가 지원하는 channel은 아래 6개다.

| Channel | 의미 | Primary denominator | Fallback denominator | 사용 G0 basis field | 미사용/부족 시 처리 |
|---|---|---|---|---|---|
| `revenueMagnitude` | 매출 감소, 수요 변화, 가격 전가, 제품/서비스 기회 | `revenue` | 없음 | `revenue` | revenue가 없으면 channel 미설정 |
| `costMagnitude` | 운영비, 원가, 공급망 대응비, 교육/안전/품질 비용 | `operatingProfit` | `revenue` | `operatingProfit`, `revenue` | 영업이익이 없거나 0 이하이면 revenue fallback |
| `capexMagnitude` | 설비 전환, 친환경 투자, 에너지 효율/공정 개선 투자 | `capex` | `revenue` | `capex`, `revenue` | capex가 없거나 0이면 revenue fallback |
| `assetLiabilityMagnitude` | 자산 손상, 부채/충당부채, 재고/설비 좌초 리스크 | 없음 | `revenue` | MVP에서는 제한적으로 `revenue`만 fallback | MVP 기본 미사용. 명시적 rule hit가 있을 때만 최대 3으로 제한 |
| `financingMagnitude` | 조달비용, 신용등급, 보험료, 투자자 요구수익률 영향 | `revenue` | `capex` | `revenue`, `capex` | debt/interest basis가 없으므로 MVP에서는 보수적으로 산정 |
| `legalRegulatoryMagnitude` | 과징금, 소송, 규제 대응비, 인증/감사 비용 | `operatingProfit` | `revenue` | `operatingProfit`, `revenue` | regulation source 또는 compliance subIssue에서 우선 사용 |

주의:

- channel이 해당 subIssue에 맞지 않으면 `None`으로 둔다.
- `calculateFinancialScore()`는 현재 magnitude 중 max 값을 사용하므로, 관련 없는 channel에 관성적으로 값을 채우지 않는다.
- denominator가 없으면 임의 추정하지 않고 trace warning을 남긴다.

## 5. Ratio to Magnitude 변환 기준

MVP 기본 변환표는 모든 channel에 공통 적용한다. channel별로 별도 threshold를 만들지 않는다.

국제 기준(ISSB/IFRS S1, ESRS)은 sustainability-related risks and opportunities가 현금흐름, 재무성과, 재무상태, 자본 접근성, 자본비용에 영향을 줄 수 있다는 관점을 제공한다. 다만 아래 ratio threshold 자체는 국제 기준에 명시된 값이 아니라 SKM MVP 내부 scoring methodology다. GRI는 financial materiality score보다는 impact score/evidence rationale의 근거로 우선 사용한다.

```text
ratio = estimatedFinancialExposure / selectedDenominator
```

| Ratio | Magnitude |
|---|---:|
| no applicable exposure 또는 denominator 없음 | 0 |
| `ratio = 0` 또는 없음 | 0 |
| `0 < ratio < 0.001` | 1 |
| `0.001 <= ratio < 0.005` | 2 |
| `0.005 <= ratio < 0.01` | 3 |
| `0.01 <= ratio < 0.03` | 4 |
| `ratio >= 0.03` | 5 |

MVP에서는 실제 금액이 없는 경우가 많으므로, `defaultImpactRatioPreset`을 subIssue/source/timeHorizon/confidence에 따라 조정해 `estimatedFinancialExposureRatio`로 사용한다.

```text
estimatedFinancialExposureRatio =
    defaultImpactRatioPreset
    * sourceTypeRatioMultiplier
    * timeHorizonMultiplier
    * confidenceMultiplier
```

channel별 차이는 threshold가 아니라 아래에서만 반영한다.

- denominator 차이
- subIssue별 ratio preset 차이
- sourceType adjustment
- confidence adjustment
- 일부 channel cap

Channel별 처리:

- `legalRegulatoryMagnitude`: 공통 threshold 적용 후 `sourceType=regulation`이면 magnitude +1, max 5.
- `capexMagnitude`: denominator가 `capex`이면 공통표를 쓰고, revenue fallback이면 보수 multiplier `0.7`을 적용한다.
- `assetLiabilityMagnitude`: G0-02에는 총자산/총부채가 없으므로 MVP에서는 기본 미사용. revenue fallback을 쓰더라도 magnitude 3을 상한으로 둔다.

## 6. Adjustment Rule

### 6.1 Source Type Adjustment

| sourceType | 적용 방향 |
|---|---|
| `news` | confidence 기반. 낮은 confidence면 보정 없음 |
| `agency` | high confidence일 때 관련 channel +1 후보. MVP에서는 정수 보정으로 단순화 |
| `regulation` | `legalRegulatoryMagnitude` +1, max 5. likelihood +1 후보 |
| `benchmark` | financial exposure에서는 중립. common/blind spot bonus와 분리 |
| `survey` | 이번 MVP financial exposure 연결 제외. 후속에서 axis 분리 후 검토 |

### 6.2 Time Horizon Adjustment

`dmascoring.py`가 이미 time horizon을 urgency로 반영하므로 magnitude multiplier는 작게 둔다.

| timeHorizon | multiplier |
|---|---:|
| `short` | 1.10 |
| `mid` | 1.00 |
| `long` | 0.90 |

### 6.3 Confidence Adjustment

| confidenceScore | 처리 |
|---|---|
| `< 0.40` | financial exposure 보강 제외 또는 magnitude 0 |
| `0.40 ~ 0.60` | multiplier 0.80, trace warning |
| `0.60 ~ 0.80` | multiplier 1.00 |
| `>= 0.80` | multiplier 1.10 |

`likelihood`는 별도 rule로 산정하되, confidence를 그대로 score로 넣지 않는다. 예시는 다음과 같다.

```text
confidence < 0.40 -> likelihood 1
0.40 ~ 0.60       -> likelihood 2
0.60 ~ 0.80       -> likelihood 3
>= 0.80           -> likelihood 4
regulation source -> +1, max 5
```

## 7. MVP subIssue Financial Channel Mapping

아래 표의 `canonicalSubIssueCode`는 후속 구현에서 반드시 `subissuemaster.py` key로 검증한다. 사용자가 제시한 후보명이 현재 master key와 다른 경우 `requestedCandidate`에 남기고 canonical key를 별도로 둔다.

| requestedCandidate | canonicalSubIssueCode | primaryChannel | secondaryChannel | defaultImpactRatioPreset | sourceType adjustment | timeHorizon adjustment | confidence adjustment | rationale |
|---|---|---|---|---:|---|---|---|---|
| `E_CLIMATE__CLIMATE_TARGETS_TRANSITION` | `E_CLIMATE__CLIMATE_TARGETS_TRANSITION` | `capexMagnitude` | `revenueMagnitude` | 0.010 | regulation이면 legal도 보조 생성 가능, benchmark는 중립 | short 1.10, mid 1.00, long 0.90 | 기본 confidence table | 전환계획, 감축투자, 설비 전환과 매출/시장 접근성 영향. 현재 master allowed IRO 기준 financial type은 `opportunity` |
| `E_CLIMATE__GHG_ENERGY` | `E_CLIMATE__GHG_SCOPE12_EMISSIONS` | `costMagnitude` | `legalRegulatoryMagnitude` | 0.005 | regulation이면 legal +1, news는 confidence 중심 | short 강화 | 기본 confidence table | 배출권, 에너지 비용, 탄소가격, Scope 1/2 규제 노출 |
| `E_PRODUCT__LOW_CARBON_PRODUCTS` | `E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE` | `revenueMagnitude` | `capexMagnitude` | 0.010 | benchmark는 opportunity 중립, news는 실제 수주/제품 근거 필요 | long은 0.90이지만 opportunity likelihood 유지 | confidence 낮으면 opportunity 보강 제외 | 저탄소 제품 매출 기회와 제품 전환 투자 |
| `S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP` | `S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP` | `costMagnitude` | `financingMagnitude` | 0.005 | regulation/agency는 audit/compliance 비용 강화 | short 강화 | confidence 낮으면 cost만 보수 적용 | 공급망 실사, 감사, 협력사 개선 비용과 고객/투자자 요구 |
| `S_WORKFORCE__OHS_SAFETY` | `S_SAFETY__OHS_MANAGEMENT` | `costMagnitude` | `legalRegulatoryMagnitude` | 0.003 | news 중 중대재해/사망 사고면 legal 보조 강화 | short 강화 | confidence 낮으면 legal 제외 | 산업안전 투자, 사고 비용, 벌금/소송 가능성 |
| `S_CONSUMER__PRODUCT_SAFETY_QUALITY` | `S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY` | `legalRegulatoryMagnitude` | `costMagnitude` | 0.005 | news/agency에서 리콜·품질 사고 evidence 있으면 legal 강화 | short 강화 | confidence 낮으면 magnitude dampen | 제품 리콜, 품질 비용, 소송/규제 리스크 |
| `G_GOVERNANCE__ETHICS_COMPLIANCE` | `G_BUSINESS_CONDUCT__LEGAL_COMPLIANCE_VIOLATIONS` | `legalRegulatoryMagnitude` | `financingMagnitude` | 0.003 | regulation/agency 강화, benchmark는 보수 | short/mid 중심 | confidence 낮으면 보강 제외 | 법규 위반, 부패, 제재, 평판 및 조달비용 영향 |
| `G_GOVERNANCE__DATA_PRIVACY_SECURITY` | `S_PRIVACY__DATA_BREACH_SECURITY_INCIDENTS` | `legalRegulatoryMagnitude` | `costMagnitude` | 0.004 | news에서 침해 사고 evidence 있으면 short/legal 강화 | short 강화 | confidence 낮으면 cost만 제한 적용 | 개인정보 유출, 보안 사고, 벌금/복구 비용 |

추가 후보:

- `E_ENERGY__ENERGY_USE_MIX`, `E_ENERGY__ENERGY_EFFICIENCY`: `costMagnitude`, `capexMagnitude`.
- `E_CLIMATE__SCOPE3_VALUE_CHAIN_EMISSIONS`: `costMagnitude`, `financingMagnitude`.
- `G_ETHICS__ETHICS_ANTI_CORRUPTION`: `legalRegulatoryMagnitude`, `financingMagnitude`.

## 8. Financial IRO Type Rule

기본값은 `subissuemaster.py`의 allowed IRO와 기존 adapter의 IRO hint를 우선한다.

Rule:

```text
financial_risk allowed and evidence is risk/compliance/cost -> risk
financial_opportunity allowed and evidence is product/revenue/market -> opportunity
둘 다 가능하면 source/evidence keyword로 판단
판단 불가하면 기존 adapter fallback 유지
```

AI가 IRO type을 최종 확정하지 않는다. AI/embedding/adapter는 hint를 제공하고, rule engine이 allowed IRO 범위 안에서 선택한다.

## 9. Trace 구조

`DMASignal.scoringPayloadJson`에 아래 구조를 추가한다.

```json
{
  "financialExposureTrace": {
    "basisType": "CONSOLIDATED",
    "basisSource": "ESG_GROUP_ROLLUP_RESULT",
    "selectedPriority": "GROUP_ROLLUP_RESULT_G",
    "fallbackUsedYn": false,
    "basis": {
      "revenue": 12300000000000,
      "operatingProfit": 800000000000,
      "netIncome": 500000000000,
      "capex": 900000000000,
      "depreciation": 300000000000
    },
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
    "subIssueRule": {
      "requestedCandidate": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
      "canonicalSubIssueCode": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
      "financialIroType": "opportunity",
      "primaryChannel": "capexMagnitude",
      "secondaryChannel": "revenueMagnitude",
      "defaultImpactRatioPreset": 0.01
    },
    "adjustments": {
      "sourceType": "regulation",
      "sourceTypeRatioMultiplier": 1.0,
      "sourceTypeMagnitudeBonus": {
        "legalRegulatoryMagnitude": 1
      },
      "timeHorizon": "mid",
      "timeHorizonMultiplier": 1.0,
      "confidenceScore": 0.82,
      "confidenceMultiplier": 1.1
    },
    "channelScores": {
      "capexMagnitude": {
        "ratio": 0.011,
        "magnitude": 4,
        "denominator": "capex",
        "denominatorValue": 900000000000,
        "reason": "transition capex exposure preset"
      },
      "revenueMagnitude": {
        "ratio": 0.0055,
        "magnitude": 3,
        "denominator": "revenue",
        "denominatorValue": 12300000000000,
        "reason": "secondary revenue exposure"
      }
    },
    "dominantMagnitudeType": "capexMagnitude",
    "dominantMagnitudeValue": 4,
    "financialIroType": "opportunity",
    "likelihood": 4,
    "fallbackUsedYn": false,
    "warnings": []
  }
}
```

No basis 예시:

```json
{
  "financialExposureTrace": {
    "basisType": "NONE",
    "basisSource": null,
    "selectedPriority": "NONE",
    "fallbackUsedYn": true,
    "channelScores": {},
    "dominantMagnitudeType": null,
    "dominantMagnitudeValue": null,
    "warnings": ["No G0-02 financial basis found; financial factor kept as adapter fallback"]
  }
}
```

## 10. Excluded Scope

이번 설계/후속 1차 구현에서 제외한다.

- AP-E-06 등 selected subIssue 이후 온보딩 지표 사용
- `dmascoring.py` 산식 변경
- AI가 financial score 직접 산정
- G/Q 동시 합산
- survey weight impact/financial 분리
- benchmark common/blind spot bonus 변경
- `FinancialFactor` DTO 변경
- auth/user/token/fastset 수정
- report generation LangGraph 설계

## 11. 다음 구현 제안

1. `backend/src/services/materialities/financial_exposure.py` 생성.
2. `getG0FinancialBasis()` 호출 wrapper 작성.
3. subIssue canonical mapping table 작성.
4. source/time/confidence adjustment function 작성.
5. ratio to magnitude 변환 function 작성.
6. 기존 adapter가 만든 `FinancialFactor`를 삭제하지 않고, G0 basis가 유효할 때 magnitude만 보강.
7. `DMASignal.scoringPayloadJson.financialExposureTrace`에 trace 저장.
8. controlled fixture로 channel별 magnitude 산정 smoke.
9. 이후 media/benchmark adapter 연결 위치를 별도 승인 후 반영.

## 12. Implementation Status

2026-05-29 기준 pure function 모듈을 구현했다.

파일:

```text
backend/src/services/materialities/financial_exposure.py
```

주요 함수:

```text
ratioToMagnitude(ratio)
buildFinancialExposureForSignal(signal, companyId, reportingYear, preferConsolidated=True)
applyG0FinancialExposure(signals, companyId, reportingYear, preferConsolidated=True)
applyG0FinancialExposureForRun(signals, runId)
buildFinancialExposureForSignalWithBasis(signal, financialBasis)
canApplyFinancialExposure(subIssueCode, financialIroType)
calculateChannelScore(...)
selectDenominator(...)
sourceTypeMagnitudeBonus(...)
confidenceMagnitudeCap(...)
dominantMagnitude(...)
buildEnhancedFinancialFactor(...)
resolvePreferConsolidated(runContext)
```

현재 상태:

- G0-02 financial basis 조회와 rule 기반 magnitude 산정 가능.
- `FinancialFactor` DTO는 변경하지 않음.
- `dmascoring.py` 산식은 변경하지 않음.
- media/benchmark adapter에는 아직 연결하지 않음.
- DB 저장 연결은 아직 하지 않고, `DMASignal.scoringPayloadJson.financialExposureTrace`에 trace를 붙이는 pure function 수준.
- trace 위치는 `updatedSignal.scoringPayloadJson.financialExposureTrace`.
- `canApplyFinancialExposure()`는 `subissuemaster.py`의 `getScoringAllowedIros()`를 사용한다.
- `applyG0FinancialExposureForRun()`은 `getMaterialityRunContext(runId)`에서 companyId/reportingYear/company_scope_type을 조회한다.

Smoke 결과:

```text
subIssue key check:
- FINANCIAL_EXPOSURE_RULES 9개 key 모두 subissuemaster.py에 존재
- missing 없음

IRO guard:
- E_CLIMATE__CLIMATE_TARGETS_TRANSITION opportunity 허용, risk 미허용
- G_BUSINESS_CONDUCT__LEGAL_COMPLIANCE_VIOLATIONS risk 허용
- S_SAFETY__OHS_MANAGEMENT risk 미허용, financialFactor 제거 확인

runId wrapper:
- runId=6: companyId=6, reportingYear=2024, company_scope_type=PARENT -> preferConsolidated=True
- mock scope SUBSIDIARY/ENTITY -> preferConsolidated=False
- unknown scope -> preferConsolidated=True + warning

Climate transition:
- subIssueCode=E_CLIMATE__CLIMATE_TARGETS_TRANSITION
- sourceType=news
- confidence=0.8
- dominantMagnitudeType=capexMagnitude
- dominantMagnitudeValue=4
- financialIroType=opportunity
- channelScores.capexMagnitude.previousMagnitude/overrideYn 확인

Regulation legal risk:
- subIssueCode=G_BUSINESS_CONDUCT__LEGAL_COMPLIANCE_VIOLATIONS
- sourceType=regulation
- legalRegulatoryMagnitude sourceTypeMagnitudeBonus=+1
- dominantMagnitudeType=legalRegulatoryMagnitude

Low confidence:
- confidence=0.3
- LOW_CONFIDENCE_CAP_2 warning
- magnitudeAfterAdjustment max 2

Asset liability cap:
- subIssueCode=E_CLIMATE__CLIMATE_RISK
- assetLiabilityMagnitude magnitudeBeforeAdjustment=5
- channelCapAppliedYn=true
- magnitudeAfterAdjustment=3

No basis:
- basisType=NONE
- factor kept as adapter fallback
- warning returned
```

다음 단계:

```text
1. media/benchmark adapter 연결 위치 승인
2. adapter가 만든 DMASignal에 applyG0FinancialExposure() 적용
3. saveDmaSignals() 경로에서 scoring_payload_json 저장 확인
4. controlled DB smoke로 ESG_DMA_SIGNAL_DETAIL.scoring_payload_json 확인
```
