"""
Domain: DMA Materiality
Layer: utils/scoring + screening + selection
Responsibility:
- LEGACY: 기존 DMA Pipeline 점수 계산 (서비스 호환용)
- STEP 1: Canonical Impact / Financial IRO 점수 계산
- STEP 2: Pre-Survey Screening 신호 계산
- STEP 3: Materiality 후보 선정 / 정렬 / 거버넌스
Do not:
- do not mutate DB state
- do not eval / exec config strings
- do not connect to DB / Redis / Kafka
- do not hardcode weights, thresholds, rule-card values (SSOT: runtime JSON)
"""

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from src.models.dmaengine import (
    FinancialFactor,
    ImpactFactor,
    AxisScoreTraceV13,
    DecisionSourceV13,
    FactorStatusV13,
    FactorTraceV13,
    ScorePurposeV13,
    ScreeningTraceV13,
)

# =========================================================
# LEGACY. 기존 경로
# =========================================================
# LEGACY: 기존 DMA Pipeline 호환용이다.
# 신규 Orchestrator에서는 호출하지 않는다.
# Phase C 전환 완료 후 삭제 여부를 판단한다.

SCORE_UI_MULTIPLIER = 2


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))


def mapUrgency(timeHorizon: str) -> float:
    if timeHorizon == "short": return 5.0
    if timeHorizon == "mid": return 3.0
    if timeHorizon == "long": return 1.0
    return 0.0


def calcImpact(factor: ImpactFactor, sourceType: str = "news", subIssueCode: str = "") -> float:
    urgency = mapUrgency(factor.timeHorizon)
    likelihood = factor.likelihood if factor.likelihood is not None else 0.0
    irremediability = factor.irremediability if factor.irremediability is not None else 0.0
    scale = factor.scale
    scope = factor.scope
    if factor.impactDirection == "negative":
        score = (0.30 * scale) + (0.25 * scope) + (0.20 * likelihood) + (0.15 * irremediability) + (0.10 * urgency)
    else:
        score = (0.35 * scale) + (0.30 * scope) + (0.25 * likelihood) + (0.10 * urgency)
    return clamp(score, 0.0, 5.0)


def calcFinancial(factor: FinancialFactor, sourceType: str = "news", subIssueCode: str = "") -> float:
    magnitudes = [
        factor.revenueMagnitude, factor.costMagnitude, factor.capexMagnitude,
        factor.assetLiabilityMagnitude, factor.financingMagnitude, factor.legalRegulatoryMagnitude,
    ]
    validMags = [m for m in magnitudes if m is not None]
    baseMag = float(max(validMags)) if validMags else 0.0
    urgency = mapUrgency(factor.timeHorizon)
    likelihood = factor.likelihood if factor.likelihood is not None else 0.0
    if factor.financialIroType == "risk":
        score = (0.45 * baseMag) + (0.35 * likelihood) + (0.20 * urgency)
    else:
        score = (0.55 * baseMag) + (0.25 * likelihood) + (0.20 * urgency)
    return clamp(score, 0.0, 5.0)


def scoreSignals(signals: list) -> list:
    for sig in signals:
        if sig.impactFactor:
            sig.impactScore05 = calcImpact(sig.impactFactor, sig.sourceType, sig.subIssueCode)
        if sig.financialFactor:
            sig.financialScore05 = calcFinancial(sig.financialFactor, sig.sourceType, sig.subIssueCode)
    return signals


def timeHorizonToUrgency(timeHorizon: str) -> float:
    return mapUrgency(timeHorizon)


def calculateImpactScore(factor: ImpactFactor, sourceType: str = "news", subIssueCode: str = "") -> float:
    return calcImpact(factor, sourceType, subIssueCode)


def calculateFinancialScore(factor: FinancialFactor, sourceType: str = "news", subIssueCode: str = "") -> float:
    return calcFinancial(factor, sourceType, subIssueCode)


def scoreDmaSignals(signals: list) -> list:
    return scoreSignals(signals)


# =========================================================
# STEP 1. CANONICAL IRO SCORE
# =========================================================

# UNOBSERVED sentinel: a required factor was missing; score is None, never 0.
UNOBSERVED = "UNOBSERVED"

# Financial magnitude tie-break precedence (rulebook 08.2).
_FINANCIAL_MAGNITUDE_TIEBREAK = (
    "legalRegulatoryMagnitude",
    "capexMagnitude",
    "costMagnitude",
    "revenueMagnitude",
    "financingMagnitude",
    "assetLiabilityMagnitude",
)


def clampScore(value: float, lo: float, hi: float) -> float:
    return max(lo, min(value, hi))


# STEP 1. Urgency 해석 — time_horizon을 urgency policy 값으로 변환한다.
# Input: time_horizon 문자열, urgency policy, explicit_no_urgency 플래그.
# Output: float 또는 UNOBSERVED sentinel. UNOBSERVED는 근거 없음을 의미한다.
def getUrgencyScore(
    timeHorizon: Optional[str],
    urgencyPolicy: Mapping[str, Any],
    explicitNoUrgency: bool = False,
):
    if explicitNoUrgency:
        return float(urgencyPolicy["explicitNoUrgency"])
    if timeHorizon in ("short", "mid", "long"):
        return float(urgencyPolicy[timeHorizon])
    return UNOBSERVED


# STEP 1. Financial exposure ratio를 magnitude 점수(0~5)로 변환한다.
# Input: ratio (None이면 UNOBSERVED 반환, 0 이하면 명시적 0), policy bands.
# Output: None(UNOBSERVED) | 0.0(명시적 노출 없음) | 1~5(band 점수).
def getRatioScore(ratio: Optional[float], bands: Sequence[Mapping[str, Any]]) -> Optional[int]:
    if ratio is None:
        # 근거 없음 — 명시적 노출 없음(0)과 구별한다.
        return None
    if ratio <= 0:
        return 0
    for band in bands:
        lo = band.get("min")
        hi = band.get("max")
        loOk = (ratio >= lo) if bool(band.get("minInclusive", False)) else (ratio > lo)
        if hi is None:
            hiOk = True
        else:
            hiOk = (ratio < hi) if bool(band.get("maxExclusive", False)) else (ratio <= hi)
        if loOk and hiOk:
            return int(band["score"])
    return 0


# STEP 1. MAX 채널의 재무 magnitude를 반환한다. 동점은 rulebook 우선순위로 결정한다.
# Input: 채널별 magnitude dict (None은 미관측).
# Output: (value, channelName) 또는 (None, None) if 모두 미관측.
def getDominantMagnitude(channels: Mapping[str, Optional[float]]) -> Tuple[Optional[float], Optional[str]]:
    observed = {k: float(v) for k, v in channels.items() if v is not None}
    if not observed:
        return None, None
    maxVal = max(observed.values())
    for name in _FINANCIAL_MAGNITUDE_TIEBREAK:
        if name in observed and observed[name] == maxVal:
            return maxVal, name
    for name in sorted(observed):
        if observed[name] == maxVal:
            return maxVal, name
    return maxVal, None


# STEP 1. AI 추출 Facts를 ai_fact_validation_policy 기준으로 검증한다.
# Input: AI가 추출한 fact dict, policy.
# Output: {"valid": bool, "violations": [...], "acceptedFacts": {...}}
def validateAiFacts(facts: Mapping[str, Any], policy: Mapping[str, Any]) -> Dict[str, Any]:
    allowed = set(policy.get("allowedFactFields", []))
    forbidden = set(policy.get("forbiddenFields", []))
    tristateFields = set(policy.get("triStateFields", []))
    tristateValues = set(policy.get("triStateAllowedValues", ["TRUE", "FALSE", "UNKNOWN"]))

    violations: List[Dict[str, str]] = []
    accepted: Dict[str, Any] = {}

    for field, value in facts.items():
        if field in forbidden:
            violations.append({"field": field, "reason": "FORBIDDEN_FIELD"})
            continue
        if field not in allowed:
            violations.append({"field": field, "reason": "UNKNOWN_FIELD"})
            continue
        if field in tristateFields and value is not None and str(value) not in tristateValues:
            violations.append({"field": field, "reason": "INVALID_TRI_STATE"})
            continue
        accepted[field] = value

    valid = len(violations) == 0
    return {"valid": valid, "violations": violations, "acceptedFacts": accepted if valid else {}}


def reweightScore(
    axis: str,
    polarity: str,
    factorValues: Mapping[str, Optional[float]],
    axisPolicy: Mapping[str, Any],
    ruleVersion: Optional[str],
    scorePurpose: ScorePurposeV13,
) -> AxisScoreTraceV13:
    """관측된 인자만으로 가중치를 재정규화하여 점수를 계산한다. Required 누락 시 UNOBSERVED."""
    weights: Dict[str, float] = {k: float(v) for k, v in axisPolicy["weights"].items()}
    required: List[str] = list(axisPolicy.get("required", []))
    optional: List[str] = list(axisPolicy.get("optional", []))

    observed = [k for k in weights if factorValues.get(k) is not None]
    missingRequired = [k for k in required if factorValues.get(k) is None]
    missingOptional = [k for k in optional if factorValues.get(k) is None]

    if missingRequired:
        traces = [
            FactorTraceV13(
                factorName=name,
                observedValue=(None if factorValues.get(name) is None else float(factorValues[name])),
                status=(FactorStatusV13.UNOBSERVED if factorValues.get(name) is None else FactorStatusV13.AUTO_CONFIRMED),
                decisionSource=(DecisionSourceV13.UNOBSERVED if factorValues.get(name) is None else DecisionSourceV13.RULE_AUTO),
                baseWeight=weights[name],
                effectiveWeight=None,
                contribution=None,
            )
            for name in weights
        ]
        return AxisScoreTraceV13(
            axis=axis, polarity=polarity, score=None, status=FactorStatusV13.UNOBSERVED,
            scorePurpose=scorePurpose, requiredFactors=required, optionalFactors=optional,
            observedFactors=observed, missingRequired=missingRequired, missingOptional=missingOptional,
            reweightApplied=False, offsettingAllowed=False, factorTraces=traces, ruleVersion=ruleVersion,
        )

    observedWeightSum = sum(weights[k] for k in observed)
    reweightApplied = len(observed) != len(weights)
    factorTraces: List[FactorTraceV13] = []
    score = 0.0

    for name in weights:
        value = factorValues.get(name)
        if value is None:
            factorTraces.append(FactorTraceV13(
                factorName=name, observedValue=None,
                status=FactorStatusV13.UNOBSERVED, decisionSource=DecisionSourceV13.UNOBSERVED,
                baseWeight=weights[name], effectiveWeight=0.0, contribution=0.0,
                note="optional factor missing; reweighted out",
            ))
            continue
        effectiveWeight = weights[name] / observedWeightSum if observedWeightSum > 0 else 0.0
        contribution = effectiveWeight * float(value)
        score += contribution
        factorTraces.append(FactorTraceV13(
            factorName=name, observedValue=float(value),
            status=FactorStatusV13.AUTO_CONFIRMED, decisionSource=DecisionSourceV13.RULE_AUTO,
            baseWeight=weights[name], effectiveWeight=effectiveWeight, contribution=contribution,
        ))

    return AxisScoreTraceV13(
        axis=axis, polarity=polarity, score=clampScore(score, 0.0, 5.0),
        status=FactorStatusV13.AUTO_CONFIRMED, scorePurpose=scorePurpose,
        requiredFactors=required, optionalFactors=optional,
        observedFactors=observed, missingRequired=[], missingOptional=missingOptional,
        reweightApplied=reweightApplied, offsettingAllowed=False,
        factorTraces=factorTraces, ruleVersion=ruleVersion,
    )


# STEP 1. Canonical Impact 점수 계산.
# Input: 정규화된 Impact Factor 값들과 SSOT Policy.
# Output: AxisScoreTraceV13. score=None은 UNOBSERVED를 의미한다.
def step1CalcImpact(
    impactDirection: str,
    scale: Optional[float],
    likelihood: Optional[float],
    policy: Mapping[str, Any],
    scope: Optional[float] = None,
    irremediability: Optional[float] = None,
    timeHorizon: Optional[str] = None,
    explicitNoUrgency: bool = False,
) -> AxisScoreTraceV13:
    if impactDirection not in ("negative", "positive"):
        raise ValueError(f"Unknown impactDirection: {impactDirection!r}")
    axisPolicy = policy["impact"][impactDirection]
    urgency = getUrgencyScore(timeHorizon, policy["urgency"], explicitNoUrgency)
    factorValues: Dict[str, Optional[float]] = {}
    wk = axisPolicy["weights"].keys()
    if "scale" in wk: factorValues["scale"] = None if scale is None else float(scale)
    if "scope" in wk: factorValues["scope"] = None if scope is None else float(scope)
    if "likelihood" in wk: factorValues["likelihood"] = None if likelihood is None else float(likelihood)
    if "irremediability" in wk: factorValues["irremediability"] = None if irremediability is None else float(irremediability)
    if "urgency" in wk: factorValues["urgency"] = None if urgency == UNOBSERVED else float(urgency)
    return reweightScore(
        axis="impact", polarity=impactDirection, factorValues=factorValues,
        axisPolicy=axisPolicy, ruleVersion=policy.get("ruleVersion"),
        scorePurpose=ScorePurposeV13.CANONICAL_IRO,
    )


# STEP 1. Canonical Financial 점수 계산.
# Input: 정규화된 Financial Factor 값들과 SSOT Policy.
# Output: AxisScoreTraceV13. score=None은 UNOBSERVED를 의미한다.
def step1CalcFinancial(
    financialIroType: str,
    magnitude: Optional[float],
    policy: Mapping[str, Any],
    likelihood: Optional[float] = None,
    timeHorizon: Optional[str] = None,
    explicitNoUrgency: bool = False,
) -> AxisScoreTraceV13:
    if financialIroType not in ("risk", "opportunity"):
        raise ValueError(f"Unknown financialIroType: {financialIroType!r}")
    axisPolicy = policy["financial"][financialIroType]
    urgency = getUrgencyScore(timeHorizon, policy["urgency"], explicitNoUrgency)
    factorValues: Dict[str, Optional[float]] = {
        "magnitude": None if magnitude is None else float(magnitude),
        "likelihood": None if likelihood is None else float(likelihood),
        "urgency": None if urgency == UNOBSERVED else float(urgency),
    }
    return reweightScore(
        axis="financial", polarity=financialIroType, factorValues=factorValues,
        axisPolicy=axisPolicy, ruleVersion=policy.get("ruleVersion"),
        scorePurpose=ScorePurposeV13.CANONICAL_IRO,
    )


# STEP 1. Impact + Financial 두 축을 한 번에 계산한다.
# Input: impact / financial kwarg dicts (각 step1CalcImpact/step1CalcFinancial에 전달).
# Output: {"impact": AxisScoreTraceV13|None, "financial": AxisScoreTraceV13|None}
def step1CalcAxes(
    policy: Mapping[str, Any],
    impact: Optional[Mapping[str, Any]] = None,
    financial: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Optional[AxisScoreTraceV13]]:
    result: Dict[str, Optional[AxisScoreTraceV13]] = {"impact": None, "financial": None}
    if impact is not None:
        result["impact"] = step1CalcImpact(policy=policy, **impact)
    if financial is not None:
        result["financial"] = step1CalcFinancial(policy=policy, **financial)
    return result


# STEP 1. Sub-issue 집계 = MAX (상계 금지).
# Input: 복수 소스의 axis 점수 목록 (None은 UNOBSERVED 소스).
# Output: MAX 점수 또는 None (전체 미관측).
def step1AggSubIssue(scores: Sequence[Optional[float]]) -> Optional[float]:
    observed = [float(s) for s in scores if s is not None]
    if not observed:
        return None
    return max(observed)


# =========================================================
# STEP 2. PRE-SURVEY SCREENING
# =========================================================

# Screening signal != Canonical IRO Score != Final DMA Rank.
# 가중치·Rule Card는 screening_policy.json에 있고, 계산 알고리즘은 여기 Python에 둔다.

STATUS_OBSERVED = "OBSERVED"
STATUS_UNOBSERVED = "UNOBSERVED"
STATUS_CAPABILITY_PENDING = "CAPABILITY_PENDING"


def _sigVal(raw: Any) -> Optional[float]:
    """Policy 셀 값을 float 또는 None(UNOBSERVED)으로 변환한다."""
    if raw is None or (isinstance(raw, str) and raw == UNOBSERVED):
        return None
    return float(raw)


# STEP 2. Benchmark 스크리닝 신호 계산.
# Input: observation in {NONE, COMMON_ISSUE, BLIND_SPOT}, screening policy.
# Output: ScreeningTraceV13 (scorePurpose=PRESURVEY_SCREENING).
def step2CalcBenchmark(observation: str, policy: Mapping[str, Any]) -> ScreeningTraceV13:
    bench = policy["benchmark"]
    if observation not in bench or observation == "aggregation":
        raise ValueError(f"Unknown benchmark observation: {observation!r}")
    value = float(bench[observation])
    return ScreeningTraceV13(
        channel="benchmark", scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        impactSignal=value, financialSignal=value, status=STATUS_OBSERVED,
        rawInputs={"observation": observation},
    )


# STEP 2. Regulation BASE 스크리닝 신호 계산 (Rule-card 조회만).
# Input: regime in {CSRD, CBAM, DPP}, applicability, screening policy.
# Output: ScreeningTraceV13. UNKNOWN applicability → 두 축 모두 None(UNOBSERVED).
def step2CalcRegulation(regime: str, applicability: str, policy: Mapping[str, Any]) -> ScreeningTraceV13:
    regulation = policy["regulation"]
    if regime not in regulation:
        raise ValueError(f"Unknown regulation regime: {regime!r}")
    regimeRules = regulation[regime]
    if applicability not in regimeRules:
        raise ValueError(f"Unknown applicability {applicability!r} for regime {regime!r}")
    cell = regimeRules[applicability]
    impact = _sigVal(cell.get("impact"))
    financial = _sigVal(cell.get("financial"))
    status = STATUS_UNOBSERVED if (impact is None and financial is None) else STATUS_OBSERVED
    return ScreeningTraceV13(
        channel=f"regulation_{regime.lower()}", scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        impactSignal=impact, financialSignal=financial, status=status,
        capability=policy.get("capabilities", {}).get("regulationAutoClassification"),
        rawInputs={"regime": regime, "applicability": applicability},
    )


# STEP 2. KCGS Pillar 리스크 신호 계산.
# Input: grade, trend, screening policy.
# Output: dict with pillarSignal (최대 pillarSignalMax), status, gradeRisk, trendModifier.
def step2CalcKcgs(grade: str, trend: str, policy: Mapping[str, Any]) -> dict:
    kcgs = policy["kcgs"]
    gradeRiskMap = kcgs["gradeRisk"]
    trendMap = kcgs["trendModifier"]
    if grade not in gradeRiskMap:
        raise ValueError(f"Unknown KCGS grade: {grade!r}")
    if trend not in trendMap:
        raise ValueError(f"Unknown KCGS trend: {trend!r}")
    gradeRisk = float(gradeRiskMap[grade])
    trendRaw = trendMap[trend]
    if isinstance(trendRaw, str) and trendRaw == UNOBSERVED:
        return {"pillarSignal": None, "status": STATUS_UNOBSERVED, "gradeRisk": gradeRisk, "trendModifier": None}
    trendMod = float(trendRaw)
    # KCGS Pillar Signal 상한 처리 — gradeRisk + trendModifier가 pillarSignalMax를 초과할 수 있다.
    pillarMax = float(kcgs["pillarSignalMax"])
    pillarSignal = min(pillarMax, gradeRisk + trendMod)
    return {"pillarSignal": pillarSignal, "status": STATUS_OBSERVED, "gradeRisk": gradeRisk, "trendModifier": trendMod}


# STEP 2. KCGS Sub-issue boost 계산 (bounded).
# Input: pillarSignal (None이면 None 반환), screening policy.
# Output: min(maxSubIssueBoost, pillarSignal * boostMultiplier) 또는 None.
def step2CalcKcgsBoost(pillarSignal: Optional[float], policy: Mapping[str, Any]) -> Optional[float]:
    if pillarSignal is None:
        return None
    kcgs = policy["kcgs"]
    boost = float(pillarSignal) * float(kcgs["boostMultiplier"])
    return min(float(kcgs["maxSubIssueBoost"]), boost)


# STEP 2. KIS 재무 회복력 Capability 상태 확인 (Phase A: 수치 신호 없음).
# Input: screening policy.
# Output: ScreeningTraceV13 with STATUS_CAPABILITY_PENDING.
def step2GetKisState(policy: Mapping[str, Any]) -> ScreeningTraceV13:
    kis = policy["kis"]
    return ScreeningTraceV13(
        channel="kis_financial_resilience", scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        impactSignal=None, financialSignal=None, status=STATUS_CAPABILITY_PENDING,
        capability=kis.get("capability"),
        rawInputs={
            "reason": kis.get("reason"),
            "creditRatingPredictionAllowedYn": kis.get("creditRatingPredictionAllowedYn"),
            "officialCreditRatingLabelAllowedYn": kis.get("officialCreditRatingLabelAllowedYn"),
        },
    )


# STEP 2. 외부 스크리닝 신호를 MAX로 집계한다 (축별, 비가산적).
# Input: ScreeningTraceV13 목록, screening policy.
# Output: 축별 MAX 신호를 담은 단일 ScreeningTraceV13.
def step2CalcExternalMax(signals: Sequence[ScreeningTraceV13], policy: Mapping[str, Any]) -> ScreeningTraceV13:
    impacts: List[float] = [s.impactSignal for s in signals if s.impactSignal is not None]
    financials: List[float] = [s.financialSignal for s in signals if s.financialSignal is not None]
    impactMax = max(impacts) if impacts else None
    financialMax = max(financials) if financials else None
    status = STATUS_UNOBSERVED if (impactMax is None and financialMax is None) else STATUS_OBSERVED
    return ScreeningTraceV13(
        channel="external_screening_max", scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        impactSignal=impactMax, financialSignal=financialMax, status=status,
        rawInputs={
            "additiveYn": policy.get("externalAggregation", {}).get("additiveYn", False),
            "contributingChannels": [s.channel for s in signals],
            "impactObservedCount": len(impacts),
            "financialObservedCount": len(financials),
        },
    )


# =========================================================
# STEP 3. MATERIALITY SELECTION
# =========================================================

# Threshold·정렬·Top-N은 selection_policy.json에 있고, 알고리즘은 여기 Python에 둔다.
# Selection은 점수를 바꾸지 않는다. 후보 선정/정렬/거버넌스 게이트만 담당한다.

SELECTION_TYPE_AUTO = "AUTO_SELECTED"
SELECTION_TYPE_MANUAL_ADD = "MANUAL_ADD"
SELECTION_TYPE_MANUAL_EXCLUDE = "MANUAL_EXCLUDE"

_SCORE_OVERRIDE_KEYS = frozenset({
    "score", "finalScore", "impactScore", "financialScore", "overrideScore",
    "scoreOverride", "proposedScore", "assignedScore", "confirmedScore", "scoreCandidate",
})


class SelectionGovernanceError(ValueError):
    """Raised when a selection action attempts a forbidden manual score override."""


def getMaxAxis(impact: Optional[float], financial: Optional[float]) -> float:
    candidates = [v for v in (impact, financial) if v is not None]
    return max(candidates) if candidates else 0.0


def getMinAxis(impact: Optional[float], financial: Optional[float], missingVal: float = 0.0) -> float:
    # 정렬에서만 사용하는 보조값이다. 실제 Canonical Score를 0으로 저장하지 않는다.
    observed = [v for v in (impact, financial) if v is not None]
    return min(observed) if len(observed) == 2 else missingVal


def _axisVal(item: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key in item and item[key] is not None:
            return float(item[key])
    return None


def _normalizeItem(item: Mapping[str, Any], missingVal: float = 0.0) -> Dict[str, Any]:
    impact = _axisVal(item, "impactScore", "impact_score", "finalImpactScore", "final_impact_score")
    financial = _axisVal(item, "financialScore", "financial_score", "finalFinancialScore", "final_financial_score")
    surveyRate = _axisVal(item, "surveyPriorityRate", "survey_priority_rate")
    code = item.get("subIssueCode") or item.get("sub_issue_code") or ""
    return {
        "subIssueCode": code,
        "impactScore": impact,
        "financialScore": financial,
        "surveyPriorityRate": surveyRate if surveyRate is not None else 0.0,
        "maxAxis": getMaxAxis(impact, financial),
        # 정렬에서만 사용하는 보조값이다. 실제 Canonical Score를 0으로 저장하지 않는다.
        "sortMinAxis": getMinAxis(impact, financial, missingVal),
    }


# STEP 3. Threshold를 충족하는 후보 목록을 구성한다.
# Input: sub-issue 점수 목록, selection policy.
# Output: 정규화된 candidate dict 목록. 점수 원본은 변경하지 않는다.
def step3BuildCandidates(
    items: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    threshold = float(policy["candidateThreshold"])
    missingVal = float(policy["ranking"]["missingAxisSortValue"])
    candidates: List[Dict[str, Any]] = []
    for item in items:
        norm = _normalizeItem(item, missingVal)
        impact = norm["impactScore"]
        financial = norm["financialScore"]
        qualifies = (impact is not None and impact >= threshold) or (financial is not None and financial >= threshold)
        if qualifies:
            candidates.append(norm)
    return candidates


# STEP 3. 후보를 4단 정렬한다: MAX↓, sortMinAxis↓, surveyRate↓, code↑.
# Input: candidate 목록, selection policy.
# Output: 정렬된 candidate 목록.
def step3RankIssues(
    candidates: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    missingVal = float(policy["ranking"]["missingAxisSortValue"])
    normalized = [c if "sortMinAxis" in c else _normalizeItem(c, missingVal) for c in candidates]
    return sorted(
        normalized,
        key=lambda c: (-c["maxAxis"], -c["sortMinAxis"], -c["surveyPriorityRate"], c["subIssueCode"]),
    )


# STEP 3. 이미 정렬된 후보 목록에서 상위 n개를 반환한다.
# Input: 정렬된 candidate 목록, n.
# Output: 상위 n개 dict 목록.
def step3PickTop(sortedCandidates: Sequence[Mapping[str, Any]], n: int) -> List[Dict[str, Any]]:
    if n < 0:
        raise ValueError("n must be >= 0")
    return [dict(c) for c in sortedCandidates[:n]]


# STEP 3. 전체 Selection 패스: 후보 → 정렬 → Top10/Top5.
# Input: sub-issue 점수 목록, selection policy.
# Output: {"candidates", "sorted", "recommendedTop10", "recommendedTop5"}
def step3RunSelection(
    items: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    candidates = step3BuildCandidates(items, policy)
    ordered = step3RankIssues(candidates, policy)
    top10 = step3PickTop(ordered, int(policy["recommendedTop10"]))
    top5 = step3PickTop(ordered, int(policy["recommendedTop5"]))
    return {"candidates": candidates, "sorted": ordered, "recommendedTop10": top10, "recommendedTop5": top5}


# STEP 3. 수동 거버넌스 결정(ADD/EXCLUDE)을 검증하고 정규화한다.
# Input: action dict, selection policy.
# Output: 정규화된 action dict. Score override 시도 시 SelectionGovernanceError.
def step3ApplyDecision(
    action: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    gate = policy.get("governanceGate", {})
    overrideAllowed = bool(gate.get("manualScoreOverrideAllowedYn", False))
    offending = sorted(set(action.keys()) & _SCORE_OVERRIDE_KEYS)
    if offending and not overrideAllowed:
        raise SelectionGovernanceError(f"Manual score override is not allowed (offending keys: {offending})")
    allowedActions = set(gate.get("manualSelectionActionsAllowed", [SELECTION_TYPE_MANUAL_ADD, SELECTION_TYPE_MANUAL_EXCLUDE]))
    selectionType = action.get("selectionType") or action.get("selection_type")
    if selectionType not in allowedActions:
        raise SelectionGovernanceError(
            f"selectionType {selectionType!r} is not an allowed manual action {sorted(allowedActions)}"
        )
    return {
        "subIssueCode": action.get("subIssueCode") or action.get("sub_issue_code"),
        "selectionType": selectionType,
        "selectionReason": action.get("selectionReason") or action.get("selection_reason"),
    }


__all__ = [
    # LEGACY
    "SCORE_UI_MULTIPLIER",
    "clamp",
    "mapUrgency",
    "timeHorizonToUrgency",
    "calcImpact",
    "calculateImpactScore",
    "calcFinancial",
    "calculateFinancialScore",
    "scoreSignals",
    "scoreDmaSignals",
    # STEP 1
    "UNOBSERVED",
    "clampScore",
    "getUrgencyScore",
    "getRatioScore",
    "getDominantMagnitude",
    "validateAiFacts",
    "reweightScore",
    "step1CalcImpact",
    "step1CalcFinancial",
    "step1CalcAxes",
    "step1AggSubIssue",
    # STEP 2
    "STATUS_OBSERVED",
    "STATUS_UNOBSERVED",
    "STATUS_CAPABILITY_PENDING",
    "step2CalcBenchmark",
    "step2CalcRegulation",
    "step2CalcKcgs",
    "step2CalcKcgsBoost",
    "step2GetKisState",
    "step2CalcExternalMax",
    # STEP 3
    "SELECTION_TYPE_AUTO",
    "SELECTION_TYPE_MANUAL_ADD",
    "SELECTION_TYPE_MANUAL_EXCLUDE",
    "SelectionGovernanceError",
    "getMaxAxis",
    "getMinAxis",
    "step3BuildCandidates",
    "step3RankIssues",
    "step3PickTop",
    "step3RunSelection",
    "step3ApplyDecision",
]
