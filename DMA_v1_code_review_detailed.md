# DMA 점수 로직 v1 Freeze 코드 리뷰 및 의사결정 문서

작성 기준: `leeej9801-max/total` GitHub `main` 브랜치  
대상 루트: `dev_skm-feature-ai_score_ljb/`  
주요 대상: `backend/src/models/dmaengine.py`, `backend/src/utils/dmascoring.py`, `backend/src/utils/dmaaggregator.py`, `backend/src/utils/dmarepository.py`, `backend/src/services/medias/*`, `backend/src/services/benchmarks/*`, `backend/src/utils/ocraiv8.py`, `backend/src/apis/media.py`

이 문서는 지금까지 적용된 DMA 점수 로직 v1 Freeze의 실제 코드 흐름을 파일·함수 단위로 해체해서 설명한다. 목적은 “현재 코드가 어떤 순서로 실행되고, 어떤 데이터가 어떤 형태로 바뀌고, 어떤 지점에서 의사결정을 해야 하는지”를 팀원이 설명 가능할 정도로 이해하는 것이다.

---

## 0. 한 줄 결론

현재 구조는 아래 원칙을 따른다.

```text
외부 데이터
→ subIssueCode 매핑
→ DMASignal 생성
→ ImpactFactor / FinancialFactor 생성
→ dmascoring.py에서 0~5 점수 계산
→ dmarepository.py에서 evidence/signal 저장
→ dmaaggregator.py에서 stage score 집계
→ final score 및 rank 갱신
```

중요한 점은 다음이다.

```text
AI / embedding / adapter는 “증거 추출, 이슈 매핑, factor 생성”까지만 담당한다.
AI가 직접 0~5 점수를 주지 않는다.
0~5 점수는 dmascoring.py의 고정 산식이 계산한다.
```

현재 코어 점수 로직은 freeze 수준에 근접했다. 다만 `결과 API`, `coverage 노출`, `media topIssues DB summary 기반 반환`, `benchmark adapter fallback`은 추가 확인이 필요하다.

---

# 1. 전체 아키텍처 개요

## 1.1 소스 단계 구분

현재 DMA는 `sourceStep`과 `sourceType`을 분리한다.

```text
sourceStep:
- media_external
- benchmark
- survey

sourceType:
- news
- agency
- regulation
- leader_sr
- peer_sr
- own_sr
- survey_employee
- survey_management
- survey_external
```

의미는 다음과 같다.

```text
sourceStep = “어느 평가 단계에서 들어온 데이터인가”
sourceType = “그 단계 안에서 어떤 자료 유형인가”
```

예를 들어 언론 기사는 다음처럼 들어간다.

```text
sourceStep = media_external
sourceType = news
```

규제와 전문기관도 별도 stage가 아니라 `media_external` 안의 sourceType으로 처리하는 설계다.

```text
media_external
├─ news
├─ regulation
└─ agency
```

벤치마킹은 다음처럼 들어간다.

```text
sourceStep = benchmark
sourceType = leader_sr / peer_sr / own_sr
```

설문은 아직 별도 adapter는 약하지만, repository 수준에서는 다음 테이블을 읽어 집계한다.

```text
ESG_DMA_SURVEY_RESPONSE
```

---

## 1.2 핵심 데이터 객체: DMASignal

모든 소스는 최종적으로 `DMASignal`로 변환되어야 한다.

```text
media news result
benchmark LLM result
regulation rule result
agency rule/AI result
survey response
        ↓
DMASignal
        ↓
scoreDmaSignals()
        ↓
saveDmaSignals()
```

`DMASignal`은 “개별 근거 1건이 특정 subIssueCode에 대해 가진 scoring-ready signal”이다.

### DMASignal의 핵심 필드

파일: `backend/src/models/dmaengine.py`

```python
class DMASignal(BaseModel):
    subIssueCode: str
    sourceStep: Literal["benchmark", "media_external", "survey"]
    sourceType: str

    impactFactor: Optional[ImpactFactor]
    financialFactor: Optional[FinancialFactor]

    impactScore05: Optional[float]
    financialScore05: Optional[float]

    confidenceScore: float
    evidenceId: Optional[str]
    teSrFileId: Optional[int]

    rawIssueLabel: Optional[str]
    displaySubIssueName: Optional[str]

    similarityScore: Optional[float]
    similarityRank: Optional[int]
    mappingWeight: Optional[float]
    mappingMethod: Optional[str]
    judgeStatus: Optional[str]

    evidenceSpans: List[str]

    sourceTitle: Optional[str]
    sourceUrl: Optional[str]
    publishedAt: Optional[str]
    scoringPayloadJson: Optional[dict]
```

해석은 다음과 같다.

| 필드 | 의미 |
|---|---|
| `subIssueCode` | `subissuemaster.py`의 key. 예: `E_CLIMATE__CLIMATE_TARGETS_TRANSITION` |
| `sourceStep` | 평가 단계. `media_external`, `benchmark`, `survey` |
| `sourceType` | 자료 유형. `news`, `agency`, `regulation`, `leader_sr` 등 |
| `impactFactor` | Impact 점수 계산에 필요한 factor 묶음 |
| `financialFactor` | Financial 점수 계산에 필요한 factor 묶음 |
| `impactScore05` | 0~5 Impact 점수. dmascoring.py가 계산 |
| `financialScore05` | 0~5 Financial 점수. dmascoring.py가 계산 |
| `confidenceScore` | 해당 signal의 신뢰도/가중치. media에서는 similarity 기반 |
| `evidenceSpans` | 실제 근거 문장, 기사 chunk, 보고서 문장 |
| `sourceTitle/sourceUrl/publishedAt` | 기사 또는 자료 trace용 메타데이터 |
| `scoringPayloadJson` | 원본 similarity 결과, 근거 메타데이터 등 audit payload |

### 중요한 설계 원칙

```text
subIssueCode는 한글명이 아니라 subissuemaster.py의 key여야 한다.
displaySubIssueName은 표시용 한글명이다.
```

예:

```python
subIssueCode = "E_CLIMATE__CLIMATE_TARGETS_TRANSITION"
displaySubIssueName = "기후목표·전환계획"
```

---

# 2. 파일별 상세 코드 리뷰

---

# 2.1 `backend/src/models/dmaengine.py`

## 역할

이 파일은 DMA 파이프라인의 공통 계약서다. Pydantic 모델을 정의한다.

주요 모델은 다음이다.

```text
DMAContextProfile
ImpactAssessment
FinancialAssessment
DMAScoreDetail
LLMSubIssueExtraction
LLMExtractorOutput
DMAAgentRequest
ImpactFactor
FinancialFactor
DMASignal
StageScore
FinalMaterialityScore
```

현재 실제 점수 파이프라인에서 핵심적으로 쓰이는 것은 아래 5개다.

```text
ImpactFactor
FinancialFactor
DMASignal
StageScore
FinalMaterialityScore
```

---

## ImpactFactor

```python
class ImpactFactor(BaseModel):
    impactDirection: Literal["positive", "negative"]
    actuality: Literal["actual", "potential"]
    scale: int
    scope: int
    irremediability: Optional[int]
    likelihood: Optional[int]
    timeHorizon: Literal["short", "mid", "long"]
    evidenceSpans: List[str]
```

ImpactFactor는 사회·환경 영향 측면에서 점수를 계산하기 위한 factor다.

| 필드 | 의미 | 점수 영향 |
|---|---|---|
| `impactDirection` | 긍정/부정 영향 | positive/negative 산식 분기 |
| `actuality` | 실제/잠재 영향 | 현재 산식에는 직접 반영 안 됨 |
| `scale` | 영향 규모 | 핵심 |
| `scope` | 영향 범위 | 핵심 |
| `irremediability` | 회복 불가능성 | negative impact 산식에서 사용 |
| `likelihood` | 발생 가능성 | positive/negative 모두 사용 |
| `timeHorizon` | 단기/중기/장기 | urgency로 변환 |
| `evidenceSpans` | 근거 문장 | 저장/audit용 |

의사결정 포인트:

```text
actuality는 현재 점수 산식에 반영되지 않는다.
나중에 actual > potential 가중을 넣을지 결정 가능하다.
```

---

## FinancialFactor

```python
class FinancialFactor(BaseModel):
    financialIroType: Literal["risk", "opportunity"]
    revenueMagnitude: Optional[int]
    costMagnitude: Optional[int]
    capexMagnitude: Optional[int]
    assetLiabilityMagnitude: Optional[int]
    financingMagnitude: Optional[int]
    legalRegulatoryMagnitude: Optional[int]
    likelihood: Optional[int]
    timeHorizon: Literal["short", "mid", "long"]
    evidenceSpans: List[str]
```

FinancialFactor는 재무적 영향 점수를 계산하기 위한 factor다.

현재 산식은 여러 magnitude 중 최댓값을 사용한다.

```python
base_mag = max([
  revenueMagnitude,
  costMagnitude,
  capexMagnitude,
  assetLiabilityMagnitude,
  financingMagnitude,
  legalRegulatoryMagnitude
])
```

의사결정 포인트:

```text
현재는 재무 영향 규모를 “최대 magnitude”로 본다.
나중에 revenue/cost/capex/legal을 별도 가중 평균할지 결정 가능하다.
```

---

## StageScore

```python
class StageScore(BaseModel):
    impactScore05: Optional[float]
    financialScore05: Optional[float]
```

stage별 대표 점수를 담는다.

예:

```text
media_external_impact_score
media_external_financial_score
benchmark_impact_score
benchmark_financial_score
survey_impact_score
survey_financial_score
```

---

## FinalMaterialityScore

```python
class FinalMaterialityScore(BaseModel):
    subIssueCode: str
    finalImpactScore: Optional[float]
    finalFinancialScore: Optional[float]
    finalScore: Optional[float]
    coverage: dict
```

최종 점수와 coverage를 담는다.

주의할 점:

```text
coverage는 객체에는 존재하지만 현재 DB upsert에서는 저장되지 않는다.
따라서 coverage를 API에 보여주려면 조회 시 재계산하거나, summary 테이블에 JSON 컬럼을 추가해야 한다.
현재 v1에서는 “API에서 재계산”이 더 안전하다.
```

---

# 2.2 `backend/src/utils/subissuemaster.py`

## 역할

62개 서브이슈의 단일 source-of-truth다.

모든 소스에서 사용하는 `subIssueCode`는 이 파일의 `subissueMaster` key여야 한다.

## 핵심 유틸 함수

```python
def getSubissueCount():
    return len(subissueMaster)

def getSubIssueMeta(subIssueCode: str) -> dict:
    return subissueMaster.get(subIssueCode, {})

def getSubIssueDisplayName(subIssueCode: str) -> str:
    meta = subissueMaster.get(subIssueCode)
    return meta["subIssueNameKr"] if meta else subIssueCode

def isAllowedIro(subIssueCode: str, iroType: str) -> bool:
    meta = subissueMaster.get(subIssueCode)
    if not meta: return False
    allowed = meta.get("scoring_axis_allowed", "")
    return iroType in allowed.split(";")
```

## v1 freeze에서 추가된 scoring 가능한 IRO 필터

```python
SCORING_CAPABLE_IROS = {
  "negative_impact",
  "positive_impact",
  "financial_risk",
  "financial_opportunity"
}

def getScoringAllowedIros(subIssueCode: str) -> list:
    meta = subissueMaster.get(subIssueCode)
    if not meta: return []
    allowed = meta.get("scoring_axis_allowed", "")
    return [iro for iro in allowed.split(";") if iro in SCORING_CAPABLE_IROS]
```

이 함수가 중요하다.

`scoring_axis_allowed`에는 `governance_quality`, `risk_management_maturity`, `target_progress` 같은 보조 axis도 들어갈 수 있다. 하지만 현재 dmascoring.py가 처리 가능한 IRO는 4개뿐이다.

```text
negative_impact
positive_impact
financial_risk
financial_opportunity
```

따라서 `getScoringAllowedIros()`는 현재 점수 엔진이 처리할 수 있는 IRO만 걸러낸다.

## 의사결정 포인트

현재 v1은 scoring axis를 4개만 처리한다.

```text
허용:
- negative_impact
- positive_impact
- financial_risk
- financial_opportunity

보류:
- governance_quality
- risk_management_maturity
- target_progress
- transition_risk 등
```

후속 버전에서 보조 axis를 별도 factor로 확장할지 결정해야 한다.

---

# 2.3 `backend/src/utils/dmascoring.py`

## 역할

순수 점수 계산 엔진이다.

입력:

```text
ImpactFactor
FinancialFactor
```

출력:

```text
impactScore05
financialScore05
```

현재 파일 상단 docstring의 핵심은 다음이다.

```text
DB 저장: 0~5
UI 표시: score05 * 2
sourceType별 분기를 하지 않음
sourceType별 factor 생성 규칙은 baseline.py 담당
AI는 점수를 직접 주지 않음
```

## 상수

```python
SCORE_UI_MULTIPLIER = 2
```

의미:

```text
canonical score = 0~5
UI display score = 0~10
```

주의:

```text
현재 상수 선언과 문서화는 되어 있지만, API response나 프론트 formatter에서 실제 적용되는지는 별도 확인 필요.
```

---

## clamp()

```python
def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))
```

모든 점수를 0~5 범위로 제한한다.

---

## timeHorizonToUrgency()

```python
def timeHorizonToUrgency(timeHorizon: str) -> float:
    if timeHorizon == "short": return 5.0
    if timeHorizon == "mid": return 3.0
    if timeHorizon == "long": return 1.0
    return 0.0
```

단기 이슈일수록 시급성이 높게 계산된다.

| timeHorizon | urgency |
|---|---:|
| short | 5 |
| mid | 3 |
| long | 1 |
| 기타 | 0 |

의사결정 포인트:

```text
기후전환처럼 long이지만 지금 투자 의사결정에 영향을 주는 이슈는 baseline에서 timeHorizon을 mid/short로 조정하거나 context modifier로 보정해야 한다.
```

---

## calculateImpactScore()

```python
def calculateImpactScore(factor, sourceType="news", subIssueCode=""):
    urgency = timeHorizonToUrgency(factor.timeHorizon)
    likelihood = factor.likelihood if factor.likelihood is not None else 0.0
    irremediability = factor.irremediability if factor.irremediability is not None else 0.0
    scale = factor.scale
    scope = factor.scope

    if factor.impactDirection == "negative":
        score = (
          0.30 * scale
          + 0.25 * scope
          + 0.20 * likelihood
          + 0.15 * irremediability
          + 0.10 * urgency
        )
    else:
        score = (
          0.35 * scale
          + 0.30 * scope
          + 0.25 * likelihood
          + 0.10 * urgency
        )

    return clamp(score, 0.0, 5.0)
```

### Negative Impact 산식

```text
0.30 * scale
+ 0.25 * scope
+ 0.20 * likelihood
+ 0.15 * irremediability
+ 0.10 * urgency
```

### Positive Impact 산식

```text
0.35 * scale
+ 0.30 * scope
+ 0.25 * likelihood
+ 0.10 * urgency
```

차이:

```text
negative impact에는 irremediability가 들어간다.
positive impact에는 irremediability가 없다.
```

---

## calculateFinancialScore()

```python
def calculateFinancialScore(factor, sourceType="news", subIssueCode=""):
    magnitudes = [
        factor.revenueMagnitude,
        factor.costMagnitude,
        factor.capexMagnitude,
        factor.assetLiabilityMagnitude,
        factor.financingMagnitude,
        factor.legalRegulatoryMagnitude
    ]
    valid_mags = [m for m in magnitudes if m is not None]
    base_mag = float(max(valid_mags)) if valid_mags else 0.0
    urgency = timeHorizonToUrgency(factor.timeHorizon)
    likelihood = factor.likelihood if factor.likelihood is not None else 0.0

    if factor.financialIroType == "risk":
        score = 0.45 * base_mag + 0.35 * likelihood + 0.20 * urgency
    else:
        score = 0.55 * base_mag + 0.25 * likelihood + 0.20 * urgency

    return clamp(score, 0.0, 5.0)
```

### Financial Risk 산식

```text
0.45 * magnitude
+ 0.35 * likelihood
+ 0.20 * urgency
```

### Financial Opportunity 산식

```text
0.55 * magnitude
+ 0.25 * likelihood
+ 0.20 * urgency
```

차이:

```text
opportunity는 magnitude 비중이 더 높다.
risk는 likelihood 비중이 더 높다.
```

---

## scoreDmaSignals()

```python
def scoreDmaSignals(signals: list) -> list:
    for sig in signals:
        if sig.impactFactor:
            sig.impactScore05 = calculateImpactScore(
                sig.impactFactor,
                sig.sourceType,
                sig.subIssueCode
            )
        if sig.financialFactor:
            sig.financialScore05 = calculateFinancialScore(
                sig.financialFactor,
                sig.sourceType,
                sig.subIssueCode
            )
    return signals
```

역할:

```text
DMASignal 리스트를 받아 factor가 있는 축만 점수를 계산한다.
factor가 None이면 해당 축 점수도 None으로 남는다.
```

의사결정 포인트:

```text
점수를 0으로 넣지 않는다.
미관측 축은 None으로 남겨야 이후 집계에서 분모 제외가 가능하다.
```

---

# 2.4 `backend/src/utils/dmaaggregator.py`

## 역할

개별 signal 점수를 stage 대표 점수로 집계하고, stage 대표 점수를 final 점수로 집계한다.

---

## 상수

### MEDIA_SOURCE_TYPE_WEIGHTS

```python
MEDIA_SOURCE_TYPE_WEIGHTS = {
    "news": 1.0,
    "agency": 1.2,
    "regulation": 1.3
}
```

의미:

```text
media_external stage 내부에서 sourceType별 신뢰도/중요도를 반영한다.
```

### FINAL_STAGE_WEIGHTS

```python
FINAL_STAGE_WEIGHTS = {
    "survey": 0.40,
    "benchmark": 0.35,
    "media_external": 0.25
}
```

최종 점수의 stage 가중치다.

의사결정 의미:

```text
설문 40%: 이해관계자 신호를 가장 크게 반영
벤치마킹 35%: 업계·피어 관행 반영
미디어 25%: 외부 신호이나 noise 가능성이 있어 상대적으로 낮게 반영
```

### SURVEY_GROUP_WEIGHTS

```python
SURVEY_GROUP_WEIGHTS = {
    "employee": 0.30,
    "management": 0.40,
    "external": 0.30
}
```

v1에서는 경영진 40%, 임직원 30%, 외부 30%다.

의사결정 포인트:

```text
현재 설문은 impact/financial axis 분리 전 임시 구조다.
axis 분리 설문이 들어오면 그룹 weight와 axis별 weight를 재검토해야 한다.
```

---

## aggregateBenchmarkSignals()

```python
benchmarkSignal =
    0.40 * leaderRatio
  + 0.35 * peerRatio
  + 0.15 * ownRatio

if commonSelection:
    benchmarkSignal += 0.10

if blindSpot:
    benchmarkSignal += 0.10

benchmarkSignal = min(1.0, benchmarkSignal)
```

그 후:

```python
if evidenceCount == 0 or benchmarkSignal < MIN_BENCHMARK_SIGNAL:
    return StageScore(None, None)

multiplier = 0.5 + 0.5 * benchmarkSignal
benchmarkImpact = baselineImpactScore * multiplier
benchmarkFinancial = baselineFinancialScore * multiplier
```

### 의미

벤치마킹은 “개별 문장 점수”보다 “해당 이슈가 얼마나 자주, 누구에게서 관측됐는가”를 더 중시한다.

| 변수 | 의미 |
|---|---|
| `leaderRatio` | 리더 보고서 중 해당 이슈 관측 비율 |
| `peerRatio` | 피어 보고서 중 해당 이슈 관측 비율 |
| `ownRatio` | 자사 과거 보고서 중 해당 이슈 관측 비율 |
| `commonSelection` | leader와 peer에서 공통 관측 |
| `blindSpot` | leader/peer는 관측, own은 미관측 |

### 현재 상태

이 함수는 주석상 `v1 provisional`이다.

의사결정 포인트:

```text
benchmark는 후속에서 더 정교화해야 한다.
특히 totalLeader/totalPeer/totalOwn 모수 계산과 blind spot 기준을 운영 데이터에 맞춰 재검증해야 한다.
```

---

## aggregateSurveyScores()

```python
return weightedAvgAvailable([
    (employeeScore, 0.30),
    (executiveScore, 0.40),
    (externalScore, 0.30)
])
```

현재 설문 stage score는 응답자 그룹별 평균의 weighted average다.

주의:

```text
현재 repository에서는 survey score 하나를 impact/financial 양쪽에 복사한다.
이는 v1 MVP 임시 구조다.
```

---

## aggregateMediaSignals()

```python
for sig in signals:
    w = MEDIA_SOURCE_TYPE_WEIGHTS.get(sig.sourceType, 1.0) * sig.confidenceScore

    if sig.financialScore05 is not None:
        financialSum += sig.financialScore05 * w
        financialWeightSum += w

    if sig.impactScore05 is not None:
        impactSum += sig.impactScore05 * w
        impactWeightSum += w
```

이 함수의 핵심은 **impact와 financial의 분모를 분리**한다는 점이다.

### 왜 분모를 분리하나?

어떤 signal은 impactFactor만 있고 financialFactor는 없을 수 있다. 이때 financial score가 없다는 이유로 financial 평균이 낮아지면 안 된다.

따라서:

```text
impactScore05가 있는 signal만 impact 분모에 포함
financialScore05가 있는 signal만 financial 분모에 포함
```

---

## weightedAvgAvailable()

```python
def weightedAvgAvailable(items):
    scoreSum, weightSum = 0.0, 0.0
    for score, weight in items:
        if score is not None:
            scoreSum += score * weight
            weightSum += weight
    return scoreSum / weightSum if weightSum > 0 else None
```

이 함수는 DMA 전체에서 매우 중요하다.

```text
미관측 stage를 0점 처리하지 않는다.
None은 분모에서 제외한다.
```

예:

```text
survey 없음, benchmark=4, media=3인 경우
final = (4*0.35 + 3*0.25) / (0.35+0.25)
```

설문이 없다고 0점으로 깎지 않는다.

---

## getCoverageStatus()

```python
if count >= 3: return "FULL"
if count == 2: return "PARTIAL"
if count == 1: return "LIMITED"
return "NO_DATA"
```

coverage 상태 기준:

| 상태 | 의미 |
|---|---|
| FULL | 3개 stage 모두 있음 |
| PARTIAL | 2개 stage 있음 |
| LIMITED | 1개 stage만 있음 |
| NO_DATA | 없음 |

현재 `calculateFinalMateriality()` 내부에서는 impact와 financial 각각 coverage를 계산한다.

---

## calculateFinalMateriality()

입력:

```text
surveyImpact, surveyFinancial
benchmarkImpact, benchmarkFinancial
mediaImpact, mediaFinancial
contextImpactModifier
contextFinancialModifier
```

단계:

### 1. Raw final impact 계산

```python
rawFinalImpact = weightedAvgAvailable([
    (surveyImpact, 0.40),
    (benchmarkImpact, 0.35),
    (mediaImpact, 0.25)
])
```

### 2. Raw final financial 계산

```python
rawFinalFinancial = weightedAvgAvailable([
    (surveyFinancial, 0.40),
    (benchmarkFinancial, 0.35),
    (mediaFinancial, 0.25)
])
```

### 3. Coverage 계산

```python
impactCount = count non-null among surveyImpact, benchmarkImpact, mediaImpact
financialCount = count non-null among surveyFinancial, benchmarkFinancial, mediaFinancial
```

### 4. Context modifier 적용

```python
finalImpact = clamp(rawFinalImpact + contextImpactModifier, 0, 5)
finalFinancial = clamp(rawFinalFinancial + contextFinancialModifier, 0, 5)
```

현재 repository에서는 modifier를 0.0으로 넘긴다. 즉 아직 기업 context modifier는 실제 반영되지 않는다.

### 5. finalScore 산출

```python
if finalImpact is None and finalFinancial is None:
    finalScore = None
elif finalImpact is None:
    finalScore = finalFinancial
elif finalFinancial is None:
    finalScore = finalImpact
else:
    finalScore = (finalImpact + finalFinancial) / 2.0
```

의사결정 포인트:

```text
finalScore는 impact와 financial의 단순 평균이다.
나중에 finalScore에서 financial을 더 크게 볼지, impact를 더 크게 볼지 결정 가능하다.
```

---

# 2.5 `backend/src/utils/dmarepository.py`

## 역할

DB 저장과 재계산을 담당한다.

핵심 함수 흐름:

```text
saveDmaSignals()
→ getSignalsByGroup()
→ recalculateStageScore()
→ upsertStageScoreSummary()
→ recalculateFinalScore()
→ upsertFinalScoreSummary()
→ updateDmaRankings()
```

---

## saveDmaSignals()

```python
def saveDmaSignals(runId, signals, fileId=None, sourceTitle=""):
```

역할:

1. `ESG_DMA_EVIDENCE`에 근거 저장
2. `ESG_DMA_SIGNAL_DETAIL`에 signal 저장
3. 변경된 `(subIssueCode, sourceStep)` 목록 수집
4. 각 이슈별 stage score 재계산 호출

### 1. ESG_DMA_EVIDENCE 저장

```sql
INSERT INTO ESG_DMA_EVIDENCE (
  esg_materiality_run_id,
  source_step,
  source_type,
  source_title,
  te_sr_file_id,
  text_span
)
VALUES (?, ?, ?, ?, ?, ?)
```

입력값:

```python
runId
sig.sourceStep
sig.sourceType
currentSourceTitle
fileId
evidenceText
```

`currentSourceTitle`은 다음 순서로 정한다.

```python
sig.sourceTitle if exists else sourceTitle
```

의미:

```text
media에서는 기사 제목을 sig.sourceTitle에 넣으면 article title이 evidence에 저장된다.
benchmark에서는 file sourceTitle이 저장된다.
```

주의:

```text
sourceUrl, publishedAt은 ESG_DMA_EVIDENCE 컬럼에는 직접 저장되지 않는다.
대신 scoring_payload_json 안에 보존될 수 있다.
```

### 2. ESG_DMA_SIGNAL_DETAIL 저장

```sql
INSERT INTO ESG_DMA_SIGNAL_DETAIL (
  esg_materiality_run_id,
  evidence_id,
  raw_issue_label,
  sub_issue_code,
  source_step,
  source_type,
  impact_score,
  financial_score,
  confidence_score,
  scoring_payload_json
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

payload는 다음처럼 생성한다.

```python
payload = sig.model_dump(by_alias=False)
payloadJson = json.dumps(payload, ensure_ascii=False)
```

의미:

```text
scoring_payload_json은 camelCase field 기준으로 저장된다.
DB 컬럼명은 snake_case지만 JSON 내부는 camelCase다.
```

### 3. Stage 재계산 트리거

```python
updatedSubIssues.add((sig.subIssueCode, sig.sourceStep))

for subIssueCode, sourceStep in updatedSubIssues:
    recalculateStageScore(runId, subIssueCode, sourceStep)
```

즉 signal 저장이 끝나면 해당 이슈의 stage score가 자동으로 다시 계산된다.

---

## getSignalsByGroup()

```python
SELECT scoring_payload_json
FROM ESG_DMA_SIGNAL_DETAIL
WHERE esg_materiality_run_id = ?
  AND sub_issue_code = ?
  AND source_step = ?
  AND delete_yn = 0
```

이 함수는 저장된 JSON을 다시 `DMASignal(**payload)`로 복원한다.

의미:

```text
Stage aggregation은 방금 들어온 signal만 보는 게 아니라,
DB에 누적된 전체 signal을 다시 읽어서 계산한다.
```

이 설계는 맞다. 같은 subIssue에 여러 기사가 들어오거나 여러 SR 문서가 들어와도 누적 집계된다.

---

## recalculateStageScore()

입력:

```python
runId
subIssueCode
sourceStep
```

처리 분기:

```python
if sourceStep == "benchmark":
    benchmark 집계
elif sourceStep == "media_external":
    media 집계
elif sourceStep == "survey":
    survey 집계
```

### benchmark 분기

1. signal에서 file id set 추출

```python
leaderFiles = set(s.teSrFileId for s in signals if s.sourceType == "leader_sr")
peerFiles = set(...)
ownFiles = set(...)
```

2. TE_SR_FILE 전체 파일 type count 조회

```sql
SELECT aes_d(type, key) as raw_source_type
FROM TE_SR_FILE
WHERE delete_yn = 0
```

3. raw type을 문자열 기반으로 표준화

```python
if "leader" in raw_type or "리더" in raw_type:
    typeCounts["leader_sr"] += 1
elif "peer" in raw_type or "피어" in raw_type or "동종" in raw_type:
    typeCounts["peer_sr"] += 1
elif "own" in raw_type or "자사" in raw_type:
    typeCounts["own_sr"] += 1
```

4. ratio 계산

```python
leaderRatio = len(leaderFiles) / totalLeader
peerRatio = len(peerFiles) / totalPeer
ownRatio = len(ownFiles) / totalOwn
```

5. aggregateBenchmarkSignals 호출

```python
stageScore = aggregateBenchmarkSignals(
  leaderRatio,
  peerRatio,
  ownRatio,
  commonSelection,
  blindSpot,
  evidenceCount,
  baselineImpactScore,
  baselineFinancialScore
)
```

### benchmark 의사결정 포인트

현재 total file count는 전체 `TE_SR_FILE` 기준이다. 이게 특정 run/company/year 기준인지 확인이 필요하다.

```text
현재:
전체 TE_SR_FILE 중 leader/peer/own count

더 정확한 운영 기준:
해당 esg_materiality_run_id 또는 해당 분석 batch에 포함된 file scope 기준
```

이 부분은 benchmark 정교화 단계에서 반드시 재검토해야 한다.

---

### media_external 분기

```python
stageScore = aggregateMediaSignals(signals)
impactScore = stageScore.impactScore05
financialScore = stageScore.financialScore05
```

그 후:

```python
upsertStageScoreSummary(runId, subIssueCode, "media_external", impactScore, financialScore)
```

---

### survey 분기

```python
recalculateSurveyScore(runId, subIssueCode)
```

그 후 final score 재계산.

---

## recalculateSurveyScore()

```sql
SELECT respondent_group, AVG(normalized_score) as avg_score
FROM ESG_DMA_SURVEY_RESPONSE
WHERE esg_materiality_run_id = ?
  AND sub_issue_code = ?
  AND delete_yn = 0
GROUP BY respondent_group
```

그룹별 평균을 계산한다.

```python
employeeScore = groupScores.get("employee")
executiveScore = groupScores.get("management")
externalScore = groupScores.get("external")
```

그리고:

```python
finalSurveyScore = aggregateSurveyScores(...)
upsertStageScoreSummary(runId, subIssueCode, "survey", finalSurveyScore, finalSurveyScore)
```

중요:

```text
현재 survey는 impact/financial을 분리하지 않고 같은 finalSurveyScore를 양쪽에 넣는다.
이는 MVP 임시 구조다.
```

의사결정 포인트:

```text
설문 문항 설계에서 axis=impact/financial 분리가 필요하다.
분리되면 ESG_DMA_SURVEY_RESPONSE에 axis 컬럼 또는 문항별 axis 매핑이 필요하다.
```

---

## upsertStageScoreSummary()

stage별로 다른 컬럼을 upsert한다.

### benchmark

```sql
INSERT INTO ESG_DMA_SCORE_SUMMARY (
  esg_materiality_run_id,
  sub_issue_code,
  benchmark_impact_score,
  benchmark_financial_score
)
VALUES (?, ?, ?, ?)
ON DUPLICATE KEY UPDATE ...
```

### media_external

```sql
media_external_impact_score
media_external_financial_score
```

### survey

```sql
survey_impact_score
survey_financial_score
```

필수 DB 조건:

```sql
UNIQUE KEY (esg_materiality_run_id, sub_issue_code)
```

이 unique key가 없으면 `ON DUPLICATE KEY UPDATE`가 의도대로 동작하지 않는다.

---

## recalculateFinalScore()

1. `ESG_DMA_SCORE_SUMMARY`에서 stage score 조회

```sql
SELECT
  benchmark_impact_score,
  benchmark_financial_score,
  media_external_impact_score,
  media_external_financial_score,
  survey_impact_score,
  survey_financial_score
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = ?
  AND sub_issue_code = ?
```

2. `calculateFinalMateriality()` 호출

```python
finalScoreObj = calculateFinalMateriality(
    subIssueCode=subIssueCode,
    surveyImpact=row.get("survey_impact_score"),
    surveyFinancial=row.get("survey_financial_score"),
    benchmarkImpact=row.get("benchmark_impact_score"),
    benchmarkFinancial=row.get("benchmark_financial_score"),
    mediaImpact=row.get("media_external_impact_score"),
    mediaFinancial=row.get("media_external_financial_score"),
    contextImpactModifier=0.0,
    contextFinancialModifier=0.0
)
```

3. final score upsert

```python
upsertFinalScoreSummary(runId, finalScoreObj)
```

4. rank 갱신

```python
updateDmaRankings(runId)
```

---

## upsertFinalScoreSummary()

```sql
INSERT INTO ESG_DMA_SCORE_SUMMARY (
  esg_materiality_run_id,
  sub_issue_code,
  final_impact_score,
  final_financial_score,
  final_score
)
VALUES (?, ?, ?, ?, ?)
ON DUPLICATE KEY UPDATE ...
```

주의:

```text
coverage는 FinalMaterialityScore 객체에 있지만 DB에는 저장하지 않는다.
```

---

## updateDmaRankings()

```sql
SELECT id
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = ?
  AND final_score IS NOT NULL
ORDER BY final_score DESC
```

그리고 순서대로:

```sql
UPDATE ESG_DMA_SCORE_SUMMARY
SET rank_no = ?
WHERE id = ?
```

의사결정 포인트:

```text
현재 rank는 final_score 단일 기준이다.
동점 처리 방식은 없음.
동점 시 id 순서가 아니라 DB 반환 순서에 좌우될 수 있다.
후속에서 final_score DESC, final_impact_score DESC, final_financial_score DESC, sub_issue_code ASC 같은 tie-breaker가 필요할 수 있다.
```

---

# 2.6 `backend/src/services/medias/pipeline.py`

## 역할

언론 기사 또는 더미 기사 입력을 받아 subIssueCode를 매핑한다.

현재는 실제 KR-SBERT 기반 pipeline으로 교체된 상태다.

핵심 흐름:

```text
articles
→ chunk 분할
→ subissueMaster keyword 1차 후보 매핑
→ chunk embedding
→ 후보 subIssue prototype embedding과 cosine similarity
→ bestSubIssueId 산출
→ result list 반환
```

---

## get_model()

```python
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("snunlp/KR-SBERT-V40K-klueNLI-augSTS")
    return _model
```

의미:

```text
KR-SBERT 모델을 lazy loading한다.
최초 요청 시 모델 다운로드/로드 시간이 발생할 수 있다.
```

운영 의사결정:

```text
배포 환경에 sentence-transformers, torch 설치 필요.
서버가 외부 모델 다운로드를 못 하면 사전에 모델 캐시가 필요하다.
```

---

## get_subissue_vectors()

```python
for subId, info in subissueMaster.items():
    anchorSentence = info.get("sentence", "")
    keywordsKr = " ".join(info.get("keywordKr", []))
    keywordsEn = " ".join(info.get("keywordForeignEn", []))
    combinedText = f"{anchorSentence} {keywordsKr} {keywordsEn}".strip()
```

이 함수는 62개 subIssue의 prototype text를 만든다.

사용 필드:

```text
sentence
keywordKr
keywordForeignEn
```

그 다음:

```python
embeddings = model.encode(texts)
```

해서 62개 기준 벡터를 생성한다.

의미:

```text
각 subIssue를 하나의 의미 벡터로 만들어 두고,
기사 chunk와의 cosine similarity 비교 기준으로 사용한다.
```

---

## splitChunk()

```python
for paragraph in text.split("\n"):
    if len(paragraph) > 20:
        chunks.append(paragraph)
```

현재는 단순 줄바꿈/문단 기반 chunking이다.

의사결정 포인트:

```text
긴 기사에는 토큰 길이 기반 chunking이 더 적절하다.
현재는 MVP 수준이다.
```

---

## mapSubissues()

```python
for subId, info in subissueMaster.items():
    keywords = info.get("keywordKr", []) + info.get("keywordForeignEn", [])
    for keyword in keywords:
        ...
        if keyword in text:
            matchedIds.append(subId)
```

역할:

```text
embedding 계산 전에 keyword 기반으로 후보 subIssue를 줄인다.
```

이유:

```text
62개 전체와 매번 비교해도 가능하지만, noise를 줄이고 속도를 높이기 위해 1차 후보를 좁힌다.
```

주의:

```text
keyword가 없으면 해당 이슈는 후보에 오르지 않는다.
따라서 keyword 사전 품질이 중요하다.
```

---

## findTopMatches()

```python
score = cosineSimilarity(chunkEmbedding, sub["embedding"])
scores.sort(key=lambda x: x["score"], reverse=True)
return scores[:topK]
```

역할:

```text
후보 subIssue 중 similarity topK를 반환한다.
```

---

## processMediaPipeline()

입력:

```python
articles: list
companyKeywords: list = None
industryKeywords: list = None
similarityThreshold: float = 0.45
topK: int = 3
```

현재 `companyKeywords`, `industryKeywords`는 인자로 존재하지만, 실제 필터링에 거의 사용되지 않는다. 내부 주석도 `companyKeywords가 있다면 추가 필터링에 사용할 수 있으나 지금은 subissueMaster 키워드 매칭을 사용`이라고 되어 있다.

처리:

1. subIssue prototype vector 로드
2. 기사마다 content/title 읽기
3. content를 chunk로 분할
4. title을 별도 chunk로 추가
5. 각 chunk에서 keyword 기반 후보 subIssue 산출
6. 후보가 없으면 skip
7. chunk embedding 생성
8. 후보 subIssue vector와 cosine similarity 계산
9. bestMatch score가 threshold 이상이면 결과 추가

출력 예:

```python
{
  "source": "news",
  "title": "...",
  "url": "...",
  "publishedAt": "...",
  "chunk": "...",
  "bestSubIssueId": "...",
  "bestSubIssueNameKr": "...",
  "bestSimilarityScore": 0.72,
  "issueSimilarityMatches": [...]
}
```

의사결정 포인트:

```text
현재 실제 crawler는 붙지 않았다.
Media.jsx 또는 API에서 articles list를 넘겨야 한다.
crawler.py 연동은 후속 단계다.
```

---

# 2.7 `backend/src/services/medias/adapter.py`

## 역할

media pipeline 결과를 `DMASignal`로 변환한다.

```python
def convertMediaToDmaSignals(analysisResults: list) -> list[DMASignal]:
```

핵심 매핑:

```python
subIssueCode = res["bestSubIssueId"]
sourceStep = "media_external"
sourceType = "news"
confidenceScore = res["bestSimilarityScore"]
similarityScore = res["bestSimilarityScore"]
mappingWeight = res["bestSimilarityScore"]
displaySubIssueName = res["bestSubIssueNameKr"]
evidenceSpans = [res["chunk"]]
rawIssueLabel = res["title"]
sourceTitle = res["title"]
sourceUrl = res["url"]
publishedAt = res["publishedAt"]
scoringPayloadJson = {
  "source": res["source"],
  "issueSimilarityMatches": res["issueSimilarityMatches"]
}
```

중요:

```text
bestSimilarityScore를 impact/financial 점수로 쓰지 않는다.
confidenceScore, similarityScore, mappingWeight로만 사용한다.
```

의사결정 포인트:

```text
confidenceScore = bestSimilarityScore로 바로 쓰고 있다.
cosine similarity가 0~1이라고 가정하지만, 안정성을 위해 clamp(0,1)를 넣을지 검토할 수 있다.
```

---

# 2.8 `backend/src/services/medias/baseline.py`

## 역할

media signal에 ImpactFactor / FinancialFactor를 붙인다.

즉:

```text
DMASignal(subIssueCode only)
→ applyMediaBaseline()
→ DMASignal(impactFactor/financialFactor 포함)
```

---

## MEDIA_BASELINE_BY_SUB_ISSUE

현재 MVP 5대 이슈에 대해 baseline이 있다.

```python
MEDIA_BASELINE_BY_SUB_ISSUE = {
  "E_CLIMATE__CLIMATE_TARGETS_TRANSITION": {...},
  "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP": {...},
  "S_TALENT__TRAINING_DEVELOPMENT": {...},
  "E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE": {...},
  "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY": {...}
}
```

각 항목은 다음을 가진다.

```text
impact: ImpactFactor
financial: FinancialFactor
```

의사결정 포인트:

```text
현재 baseline은 5대 MVP 이슈 중심이다.
62개 전체 이슈에 대해 baseline을 확장할지, fallback factor로 처리할지 결정해야 한다.
```

---

## _resolveIroDirection()

```python
allowed = getScoringAllowedIros(subIssueCode)

if "negative_impact" in allowed:
    impactDirection = "negative"
elif "positive_impact" in allowed:
    impactDirection = "positive"

if "financial_risk" in allowed:
    financialIroType = "risk"
elif "financial_opportunity" in allowed:
    financialIroType = "opportunity"
```

이 함수는 subissueMaster의 `scoring_axis_allowed` 중 현재 엔진이 처리 가능한 IRO만 보고 factor 생성 가능성을 결정한다.

주의:

```text
negative_impact가 있으면 positive_impact보다 우선한다.
financial_risk가 있으면 financial_opportunity보다 우선한다.
```

의사결정 포인트:

```text
어떤 subIssue가 risk와 opportunity를 모두 허용하는 경우, 현재는 risk 우선이다.
이 우선순위가 맞는지 확인이 필요하다.
```

---

## applyMediaBaseline()

처리:

1. signal의 subIssueCode로 baseline 조회
2. baseline이 있으면 allowed IRO 검증 후 factor 부여
3. allowed IRO가 없으면 factor를 None으로 둠
4. baseline이 없으면 scoring 가능한 IRO를 기준으로 fallback factor 생성

### baseline이 있는 경우

```python
if baseline:
    iroResolved = _resolveIroDirection(sig.subIssueCode)

    if iroResolved["impactDirection"] is not None:
        sig.impactFactor = baseline["impact"]
    else:
        sig.impactFactor = None

    if iroResolved["financialIroType"] is not None:
        sig.financialFactor = baseline["financial"]
    else:
        sig.financialFactor = None
```

### baseline이 없는 경우

```python
if iroResolved["impactDirection"] is not None:
    sig.impactFactor = ImpactFactor(...)
else:
    sig.impactFactor = None

if iroResolved["financialIroType"] is not None:
    sig.financialFactor = FinancialFactor(...)
else:
    sig.financialFactor = None
```

중요:

```text
scoring 가능한 IRO가 없으면 factor를 만들지 않는다.
그 결과 해당 축의 score는 None이 된다.
```

---

# 2.9 `backend/src/services/medias/service.py`

## 역할

media news 분석의 orchestration layer다.

```python
def runMediaAnalysis(articles: list, runId: int, keywords: list = None):
```

실행 순서:

```python
pipelineResults = processMediaPipeline(articles, companyKeywords=keywords)
signals = convertMediaToDmaSignals(pipelineResults)
baselinedSignals = applyMediaBaseline(signals)
scoredSignals = scoreDmaSignals(baselinedSignals)
saveDmaSignals(runId=runId, signals=scoredSignals, fileId=None, sourceTitle="Media Analysis")
return scoredSignals
```

해석:

1. 기사를 subIssue에 매핑
2. DMASignal로 변환
3. factor baseline 부여
4. 0~5 점수 계산
5. DB 저장
6. 저장 후 repository가 stage/final/rank 재계산

현재 이 함수가 media news E2E의 핵심 진입점이다.

의사결정 포인트:

```text
keywords는 companyKeywords로만 전달된다.
industryKeywords는 사용되지 않는다.
현재 실제 crawler가 아니라 articles를 외부에서 받아야 한다.
```

---

# 2.10 `backend/src/apis/media.py`

## 역할

프론트에서 media analysis 요청을 받는 API router다.

FastAPI 등록 구조상 `fastset.py`가 `src.apis.media` 파일명을 기준으로 `/media` prefix를 자동 부여하므로, 파일 내부 router에는 prefix가 없다.

```python
router = APIRouter(tags=["media"])
```

endpoint:

```python
@router.post("/news/analyze")
async def analyze_media_news(request: MediaAnalyzeRequest, userModel = Depends(get_token)):
```

실제 path는 환경 prefix까지 고려하면 대략 다음 중 하나가 될 수 있다.

```text
/media/news/analyze
/api/v1/media/news/analyze
```

프로젝트 gateway/proxy 구조에 따라 앞 prefix가 붙는다.

---

## MediaAnalyzeRequest

```python
class MediaAnalyzeRequest(BaseModel):
    runId: int
    articles: List[dict]
    keywords: Optional[List[str]] = []
```

요청에는 기사 list가 들어온다.

중요:

```text
현재 API는 crawler를 직접 호출하지 않는다.
프론트 또는 호출자가 articles를 보내야 한다.
```

---

## analyze_media_news()

처리:

1. `runMediaAnalysis(request.articles, request.runId, request.keywords)` 호출
2. 반환된 scoredSignals로 articleCount, savedSignalCount 계산
3. signal count와 confidenceScore 합으로 topIssues 생성
4. savedSignalCount가 있으면 coverageStatus = LIMITED
5. response 반환

현재 topIssues 계산:

```python
issue_counts[code]["count"] += 1
issue_counts[code]["score_sum"] += sig.confidenceScore
sorted by (count, score_sum)
```

주의:

```text
현재 topIssues는 DB summary/rank 기반이 아니다.
실시간 signal count 기반이다.
```

후속 권장:

```text
saveDmaSignals 이후 ESG_DMA_SCORE_SUMMARY를 조회해서
media_external_impact_score, media_external_financial_score, final_score, rank_no 기반으로 topIssues를 반환해야 한다.
```

---

# 2.11 `frontend/src/homes/reports/Media.jsx`

## 역할

미디어 분석 화면이다.

현재 핵심 흐름:

```text
사용자 입력
→ startMediaCollection()
→ POST /api/v1/media/news/analyze
→ response.data 또는 response를 analysisResult에 저장
→ 화면에 articleCount/savedSignalCount/observedSubIssueCount 표시
```

현재 중요한 점:

```text
DUMMY_ARTICLES가 프론트에 하드코딩되어 있다.
즉 버튼을 눌러도 실제 크롤링이 아니라 더미 기사 5개를 백엔드로 보낸다.
```

요청 payload:

```javascript
{
  runId: 1,
  articles: DUMMY_ARTICLES,
  keywords: formData.pressKeyword.split(",").map(k => k.trim())
}
```

주의:

```text
runId = 1 하드코딩이다.
운영에서는 현재 DMA run id를 상태/라우터/DB에서 받아야 한다.
```

UI 출력:

```text
articleCount
savedSignalCount
observedSubIssueCount
```

후속 권장:

```text
runId 하드코딩 제거
실제 crawler API 연결
DB summary 기반 topIssues 표시
0~10 score 변환 표시
```

---

# 2.12 `backend/src/services/benchmarks/service.py`

## 역할

벤치마킹 PDF 업로드와 분석 실행을 담당한다.

두 핵심 함수:

```python
uploadSr()
findSr()
```

---

## normalizeSourceType()

```python
mapping = {
  "Leader": "leader_sr",
  "leader": "leader_sr",
  "리더": "leader_sr",
  "Peer": "peer_sr",
  "peer": "peer_sr",
  "피어": "peer_sr",
  "Own": "own_sr",
  "owner": "own_sr",
  "자사": "own_sr",
  "news": "news",
  "agency": "agency",
  "regulation": "regulation",
}
```

허용값:

```text
leader_sr
peer_sr
own_sr
news
agency
regulation
survey_employee
survey_management
survey_external
```

이 함수는 sourceType 표준화에 중요하다.

---

## uploadSr()

역할:

1. PDF 확장자 검증
2. `TE_SR_FILE`에 파일 정보 암호화 저장
3. 로컬 파일 저장

DB 저장:

```sql
INSERT INTO skm.TE_SR_FILE (
  origin,
  file_name,
  type,
  company_name,
  create_user_id
)
VALUES (
  aes_e(...),
  aes_e(...),
  aes_e(fileModel.fileType),
  aes_e(fileModel.companyName),
  userModel.id
)
```

주의:

```text
fileModel.fileType은 저장 시 normalizeSourceType을 거치지 않는다.
현재 repository의 total count 계산은 raw type 문자열에서 leader/peer/own을 추론한다.
운영 안정성을 위해 업로드 시점부터 leader_sr/peer_sr/own_sr로 저장하는 것이 더 낫다.
```

---

## findSr()

역할:

1. DB에서 업로드 파일 metadata 조회
2. 로컬 파일 path 확인
3. sourceType 정규화
4. `ocraiv8.gemini()` 호출
5. 결과를 DMASignal로 변환
6. scoreDmaSignals()
7. saveDmaSignals()
8. ResponseModel 반환

핵심 부분:

```python
finalResult = await gemini(results, filePaths)
```

그 후 파일별 결과에 대해:

```python
signalsToSave = convertToDmaSignals(resultList, fileId)
scoredSignals = scoreDmaSignals(signalsToSave)
saveDmaSignals(
    runId=fileFindModel.esgMaterialityRunId,
    signals=scoredSignals,
    fileId=fileId,
    sourceTitle=sourceTitle
)
```

주의:

```text
fileMetaByName은 dbFileName을 key로 한다.
ocraiv8 결과의 fileName과 dbFileName이 정확히 같아야 metadata 매칭이 된다.
```

---

# 2.13 `backend/src/services/benchmarks/adapter.py`

## 역할

LLM/ocraiv8 결과 dict를 DMASignal로 변환하고, AI가 만든 IRO hint를 검증한다.

---

## _validateIroHint()

```python
if isAllowedIro(subIssueCode, iroHint):
    return iroHint

allowedIros = getScoringAllowedIros(subIssueCode)

if not allowedIros:
    return iroHint
```

그 후 같은 축 내에서 대체 시도:

```python
if iroHint in impactIros:
    for candidate in allowedIros:
        if candidate in impactIros:
            return candidate
elif iroHint in financialIros:
    for candidate in allowedIros:
        if candidate in financialIros:
            return candidate
```

마지막 fallback:

```python
return allowedIros[0]
```

## 중요 문제

이 마지막 fallback은 이전에 정한 원칙과 약간 다르다.

우리가 확정했던 원칙:

```text
같은 축에 대체 가능한 IRO가 없으면 factor를 None으로 둔다.
다른 축의 IRO로 강제 대체하지 않는다.
```

현재 코드는 같은 축에 없으면 `allowedIros[0]`를 반환한다. 이 경우 impact factor가 financial IRO로 대체되거나, financial factor가 impact IRO로 대체될 가능성이 있다. 다만 convertToDmaSignals 내부에서 축 검사를 다시 하므로 실제 factor 제거로 이어질 수는 있지만, 로직은 더 명확하게 바꾸는 편이 안전하다.

권장 수정:

```python
# 같은 축에 대체 후보가 없으면 None 또는 original return 후 factor 제거
return None
```

그리고 호출부에서:

```python
if validatedIro not in impactIros:
    signalPayload["impactFactor"] = None
```

이 구조가 더 명확하다.

---

## convertToDmaSignals()

처리:

1. result dict 복사
2. `teSrFileId` 주입
3. impactFactor가 있으면 IRO 검증
4. financialFactor가 있으면 IRO 검증
5. DMASignal 생성

중요:

```text
입력 result는 camelCase만 허용한다고 주석 처리되어 있다.
따라서 ocraiv8.py도 camelCase payload를 반환해야 한다.
```

---

# 2.14 `backend/src/utils/ocraiv8.py`

## 역할

SR/PDF 문서 기반 벤치마킹 분석 엔진이다.

핵심 구조:

```text
PDF 업로드
→ Gemini LLM으로 이슈 추출
→ raw issue label을 62개 subIssue에 embedding similarity 매핑
→ ImpactFactor / FinancialFactor 생성
→ DMASignal dict 반환
```

---

## load_issue_dictionary()

현재 코드:

```python
text = meta.get("subIssueSentence") or meta.get("subIssueNameKr")
```

주의:

```text
현재 total subissuemaster.py는 sentence 필드를 사용한다.
여기서는 subIssueSentence를 먼저 찾고 없으면 subIssueNameKr를 사용한다.
즉 sentence 설명문이 제대로 반영되지 않을 수 있다.
```

권장 수정:

```python
text = meta.get("sentence") or meta.get("subIssueSentence") or meta.get("subIssueNameKr")
```

이건 media pipeline에서는 이미 `sentence`를 사용한다.

---

## normalize_mapping_weights()

역할:

1. raw_label 임베딩
2. 62개 issue vector와 cosine similarity
3. threshold 이상만 추출
4. top_k 상위 후보만 유지
5. mapping_weight 정규화

출력:

```python
{
  "term": subIssueNameKr,
  "similarity": 0.72,
  "raw_weight": ...,
  "key": subIssueCode,
  "mapping_weight": ...,
  "similarity_rank": ...
}
```

---

## get_baseline_factors()

현재 자동차부품 산업 기준 baseline factor를 하드코딩한다.

```python
if "CLIMATE" in sub_issue_code:
    scale, scope, likelihood = 4, 4, 4
elif "SUPPLY_CHAIN" in sub_issue_code:
    scale, scope = 4, 3
elif "PRODUCT_SAFETY" in sub_issue_code:
    ...
```

주의:

```text
이 함수는 benchmark/SR용 baseline이다.
media baseline.py와 별도다.
나중에 source별 baseline을 통합할지, 각 service에 둘지 결정해야 한다.
```

---

## gemini()

핵심 단계:

### 1. Issue dictionary 로드

```python
issue_dict_str, issue_dict_list = load_issue_dictionary()
```

### 2. PDF를 Gemini에 업로드

```python
uploadedFile = client.files.upload(...)
```

### 3. LLM extractor prompt 실행

Prompt 핵심:

```text
Do NOT score them from 1 to 5.
Extract raw issue labels, candidate terms, IRO Hint, Time Horizon Hint, evidence spans.
```

이는 “AI가 직접 점수 매기지 않는다”는 원칙과 맞다.

### 4. LLM 결과 파싱

```python
extracted_issues = extractor_data.get("extracted_issues", [])
```

### 5. evidence 없으면 reject

```python
if not evidence_spans:
    judge_status = "reject"
    confidence_score = 0.0
    continue
```

### 6. raw_label을 subIssueCode에 embedding 매핑

```python
mapped_terms = normalize_mapping_weights(raw_label, threshold=0.35, alpha=1.5, top_k=3)
```

### 7. 각 mapped subIssue에 대해 factor 생성

```python
if iro_hint in ["negative_impact", "positive_impact"]:
    impact_factor = ImpactFactor(...)

if iro_hint in ["financial_risk", "financial_opportunity"]:
    financial_factor = FinancialFactor(...)
```

### 8. DMASignal 생성

```python
signal = DMASignal(
    subIssueCode=key,
    sourceStep=source_step,
    sourceType=source_type,
    impactFactor=impact_factor,
    financialFactor=financial_factor,
    impactScore05=None,
    financialScore05=None,
    confidenceScore=confidence_score * weight,
    rawIssueLabel=f"{raw_label} ({term})",
    displaySubIssueName=term,
    similarityScore=sim,
    similarityRank=mapped.get("similarity_rank"),
    mappingWeight=weight,
    judgeStatus=judge_status,
    evidenceSpans=evidence_spans
)
```

### 9. dict 반환

```python
sig_dict = signal.model_dump()
final_results.append(sig_dict)
```

이 결과가 benchmark adapter → scoreDmaSignals → saveDmaSignals로 들어간다.

---

# 3. 소스별 E2E 흐름

---

## 3.1 Media News E2E

```text
Media.jsx
→ POST /media/news/analyze
→ apis/media.py::analyze_media_news()
→ services/medias/service.py::runMediaAnalysis()
→ services/medias/pipeline.py::processMediaPipeline()
→ services/medias/adapter.py::convertMediaToDmaSignals()
→ services/medias/baseline.py::applyMediaBaseline()
→ utils/dmascoring.py::scoreDmaSignals()
→ utils/dmarepository.py::saveDmaSignals()
→ ESG_DMA_EVIDENCE insert
→ ESG_DMA_SIGNAL_DETAIL insert
→ recalculateStageScore(media_external)
→ aggregateMediaSignals()
→ upsertStageScoreSummary(media_external)
→ recalculateFinalScore()
→ calculateFinalMateriality()
→ upsertFinalScoreSummary()
→ updateDmaRankings()
```

### 현재 미디어 경로의 상태

```text
완료:
- 실제 KR-SBERT 기반 similarity pipeline
- subissuemaster.py 기준 subIssueCode 사용
- DMASignal 변환
- factor baseline
- scoreDmaSignals
- DB 저장과 stage/final/rank 재계산

미완:
- 실제 crawler 연결
- companyKeywords/industryKeywords의 정교한 필터링
- API topIssues를 DB summary 기반으로 반환
- 0~10 UI 환산 표시
```

---

## 3.2 Benchmark E2E

```text
BenchMarking.jsx
→ apis/benchmk.py
→ services/benchmarks/service.py::uploadSr()
→ TE_SR_FILE 저장

분석 시:
apis/benchmk.py
→ services/benchmarks/service.py::findSr()
→ utils/ocraiv8.py::gemini()
→ services/benchmarks/adapter.py::convertToDmaSignals()
→ utils/dmascoring.py::scoreDmaSignals()
→ utils/dmarepository.py::saveDmaSignals()
→ recalculateStageScore(benchmark)
→ aggregateBenchmarkSignals()
→ upsertStageScoreSummary(benchmark)
→ recalculateFinalScore()
→ updateDmaRankings()
```

### 현재 benchmark 경로의 상태

```text
완료:
- 파일 업로드/저장
- Gemini 기반 이슈 추출
- subIssue embedding 매핑
- DMASignal 변환
- score 계산
- DB 저장 및 stage/final/rank 갱신

주의:
- ocraiv8.py의 issue dictionary text가 sentence 필드를 쓰지 않을 수 있음
- benchmark adapter의 fallback 로직은 더 명확히 수정 필요
- benchmark total file count는 run scope가 아니라 전체 TE_SR_FILE 기준일 가능성
```

---

## 3.3 Survey E2E

현재 survey는 별도 service/adapter가 아니라 repository에서 직접 집계한다.

```text
ESG_DMA_SURVEY_RESPONSE
→ dmarepository.py::recalculateSurveyScore()
→ aggregateSurveyScores()
→ upsertStageScoreSummary(survey)
→ recalculateFinalScore()
```

### 현재 survey 경로의 상태

```text
완료:
- 그룹별 평균 집계
- employee/management/external weight 적용
- survey stage summary 저장

미완:
- impact/financial axis 분리
- survey adapter/API 경로
- 설문 응답 수 기반 confidence 보정
```

---

## 3.4 Regulation / Agency

현재 코드에서는 아직 구현되지 않았다.

현재 상태:

```text
media baseline.py 주석에 sourceType=regulation/agency 방향만 있음
실제 adapter/service는 미구현
```

권장 흐름:

```text
regulation rule input
→ services/medias/regulation.py 또는 regulations/adapter.py
→ DMASignal(sourceStep=media_external, sourceType=regulation)
→ baseline factor
→ scoreDmaSignals
→ saveDmaSignals
```

agency도 동일하다.

```text
agency document/rule input
→ DMASignal(sourceStep=media_external, sourceType=agency)
→ scoreDmaSignals
→ saveDmaSignals
```

---

# 4. DB 테이블별 역할

## ESG_DMA_EVIDENCE

역할:

```text
근거 원문 저장
```

현재 insert 컬럼:

```text
esg_materiality_run_id
source_step
source_type
source_title
te_sr_file_id
text_span
```

주의:

```text
source_url, published_at은 직접 컬럼으로 저장되지 않는다.
scoring_payload_json에는 남을 수 있다.
```

## ESG_DMA_SIGNAL_DETAIL

역할:

```text
개별 signal 원장
```

현재 insert 컬럼:

```text
esg_materiality_run_id
evidence_id
raw_issue_label
sub_issue_code
source_step
source_type
impact_score
financial_score
confidence_score
scoring_payload_json
```

`scoring_payload_json`은 나중에 stage aggregation에서 다시 DMASignal로 복원하는 핵심이다.

## ESG_DMA_SCORE_SUMMARY

역할:

```text
subIssueCode별 stage score + final score + rank 저장
```

주요 컬럼:

```text
benchmark_impact_score
benchmark_financial_score
media_external_impact_score
media_external_financial_score
survey_impact_score
survey_financial_score
final_impact_score
final_financial_score
final_score
rank_no
```

필수 조건:

```text
UNIQUE KEY (esg_materiality_run_id, sub_issue_code)
```

## ESG_DMA_SURVEY_RESPONSE

역할:

```text
설문 응답 점수 저장
```

현재 repository가 기대하는 컬럼:

```text
esg_materiality_run_id
sub_issue_code
respondent_group
normalized_score
delete_yn
```

후속 필요:

```text
axis = impact / financial
```

---

# 5. 현재 코드 기준 리스크 및 보완 포인트

## 5.1 API topIssues가 DB summary 기반이 아님

현재 media API는 방금 생성된 signal count로 topIssues를 만든다.

```text
정렬 기준:
count, score_sum(confidenceScore)
```

하지만 최종 UI는 다음 기준이어야 한다.

```text
ESG_DMA_SCORE_SUMMARY.final_score
ESG_DMA_SCORE_SUMMARY.rank_no
media_external_impact_score
media_external_financial_score
```

보완 필요.

---

## 5.2 coverage는 aggregator 객체에는 있으나 DB에는 없음

현재 `FinalMaterialityScore.coverage`는 객체에 존재한다. 그러나 `upsertFinalScoreSummary()`는 coverage를 저장하지 않는다.

MVP 선택지는 다음이다.

```text
안 A: 결과 API에서 summary 컬럼을 보고 coverage 재계산
안 B: coverage_payload_json 컬럼 추가
```

현재 v1에서는 안 A가 맞다.

---

## 5.3 media API coverage는 단순 LIMITED

현재 media API는 `savedSignalCount > 0`이면 `stageCount=1`로 보고 coverageStatus를 LIMITED로 준다.

이건 media API smoke response로는 괜찮지만, 최종 결과 coverage가 아니다.

---

## 5.4 ocraiv8.py issue dictionary field 수정 필요

현재:

```python
text = meta.get("subIssueSentence") or meta.get("subIssueNameKr")
```

권장:

```python
text = meta.get("sentence") or meta.get("subIssueSentence") or meta.get("subIssueNameKr")
```

이 수정은 benchmark mapping 품질에 중요하다.

---

## 5.5 benchmark adapter fallback 수정 필요

현재 `_validateIroHint()`는 같은 축에 허용 IRO가 없으면 `allowedIros[0]`를 반환한다.

권장:

```text
같은 축 대체 불가 시 None 반환
호출부에서 factor 제거
```

---

## 5.6 benchmark total count scope

현재 ratio 분모는 전체 TE_SR_FILE 기준이다. 실제로는 해당 materiality run에서 선택된 파일 scope 기준이어야 할 가능성이 높다.

후속 의사결정 필요:

```text
전체 파일 기준
vs
해당 run에 포함된 파일 기준
```

운영 관점에서는 run scope 기준이 더 맞다.

---

## 5.7 survey axis 분리 필요

현재 survey score는 impact/financial에 동일 복사된다.

후속:

```text
설문 문항별 axis 정의
ESG_DMA_SURVEY_RESPONSE.axis 컬럼 추가 또는 별도 question master 매핑
impact/financial 별도 집계
```

---

# 6. 의사결정 체크리스트

아래 항목은 사용자/팀이 결정해야 한다.

## A. 점수 산식 관련

- [ ] Impact/Financial finalScore는 계속 단순 평균으로 갈 것인가?
- [ ] context modifier는 언제부터 실제 적용할 것인가?
- [ ] timeHorizon `long=1`이 기후전환 이슈에 과소평가를 만들지 않는가?
- [ ] Financial magnitude는 max 방식 유지인가, 가중평균인가?

## B. Media 관련

- [ ] 실제 crawler 연결 시점을 언제로 할 것인가?
- [ ] companyKeywords/industryKeywords를 mandatory 필터로 쓸 것인가?
- [ ] similarityThreshold 0.45 유지인가?
- [ ] confidenceScore를 cosine similarity 그대로 쓸 것인가, 구간 변환할 것인가?

## C. Benchmark 관련

- [ ] benchmark ratio 분모는 전체 TE_SR_FILE인가, run scope인가?
- [ ] leader/peer/own 비중 0.40/0.35/0.15 유지인가?
- [ ] blindSpot +0.10 유지인가?
- [ ] ownRatio가 높을 때 감점/가점 논리를 어떻게 볼 것인가?

## D. Survey 관련

- [ ] respondent group weight 0.30/0.40/0.30 유지인가?
- [ ] axis 분리 설문을 MVP에 포함할 것인가, 후속으로 둘 것인가?
- [ ] 응답 수 기반 confidence 보정을 넣을 것인가?

## E. API/UI 관련

- [ ] UI 표시는 0~10으로 통일할 것인가?
- [ ] API에서 0~5와 0~10을 모두 내려줄 것인가?
- [ ] topIssues는 final_score 기준인가, stage별 score 기준인가?
- [ ] coverage를 DB 저장할 것인가, API 계산할 것인가?

---

# 7. 다음 작업 우선순위

현재 코드 기준으로 다음 순서가 맞다.

## 1순위: 결과 API 정리

```text
ESG_DMA_SCORE_SUMMARY 기준으로
rankNo, subIssueCode, displaySubIssueName, finalScore05, finalScore10,
finalImpactScore05, finalFinancialScore05,
stage별 score,
coverage
를 반환하는 API 필요
```

## 2순위: Media API 응답 변경

현재 `scoredSignals` count 기반 topIssues를 DB summary 기반으로 교체한다.

## 3순위: ocraiv8.py sentence field 수정

benchmark/SR 문서 매핑 품질 보정.

## 4순위: benchmark adapter fallback 정리

같은 축 대체 불가 시 factor None 처리.

## 5순위: regulation adapter

`sourceStep=media_external`, `sourceType=regulation`으로 DMASignal 생성.

## 6순위: agency adapter

`sourceStep=media_external`, `sourceType=agency`로 DMASignal 생성.

## 7순위: survey axis 분리

impact/financial 문항 분리.

## 8순위: benchmark 정교화

run scope 기반 ratio, blind spot 로직 정교화.

---

# 8. 최종 평가

현재 DMA 점수 로직 v1 Freeze는 “core scoring engine” 기준으로는 승인 가능한 수준이다.

```text
Core scoring: 안정화됨
Stage aggregation: 안정화됨
Final aggregation: 안정화됨
Repository save/recalculate flow: 작동 구조 확보
Media embedding pipeline: 1차 이식됨
Benchmark pipeline: 작동하지만 후속 정교화 필요
Survey pipeline: MVP 임시 구조
Regulation/Agency: 미구현
Result API: 아직 부족
```

정확한 상태 표현은 다음이다.

```text
DMA 점수 로직 v1 Core Freeze 완료.
다만 Result API Freeze와 source별 adapter 완성은 아직 후속 작업.
```
