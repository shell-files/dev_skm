"""
Domain: DMA Materiality
Layer: utils/scoring
Responsibility:
- Calculate deterministic 0-5 impact score from ImpactFactor
- Calculate deterministic 0-5 financial score from FinancialFactor
- Score DMASignal objects without AI deciding final score
Public functions:
- calcImpact
- calculateImpactScore
- calcFinancial
- calculateFinancialScore
- scoreSignals
- scoreDmaSignals
- mapUrgency
- timeHorizonToUrgency
- clamp
Do not:
- do not mutate unrelated DB state
- do not change scoring formula unless explicitly requested
- do not change score formula in this step
- do not change score scale
- do not perform DB mutation
- do not call FastAPI router directly
- do not modify auth/token/common code

DMA Scoring Engine v1 (Freeze)

이 모듈은 ImpactFactor / FinancialFactor를 입력받아 0~5 스케일의 점수를 반환합니다.
- DB 저장: 0~5 (canonical score)
- UI 표시: score05 * SCORE_UI_MULTIPLIER (0~10)

이 함수는 sourceType별 분기를 하지 않습니다.
sourceType별 factor 생성 규칙은 각 서비스의 baseline.py가 담당합니다.
AI는 점수를 직접 주지 않습니다. factor만 생성하고, 이 모듈이 산식으로 점수를 계산합니다.
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
)

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────
SCORE_UI_MULTIPLIER = 2  # UI display score = score05 * 2

def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))

def mapUrgency(timeHorizon: str) -> float:
    if timeHorizon == "short": return 5.0
    if timeHorizon == "mid": return 3.0
    if timeHorizon == "long": return 1.0
    return 0.0

def calcImpact(
    factor: ImpactFactor, 
    sourceType: str = "news", 
    subIssueCode: str = ""
) -> float:
    """
    환경/사회적 중대성(Impact) 요소를 기반으로 v3.2 산식에 따라 점수를 산출합니다.
    반환값: 0.0 ~ 5.0 (canonical score)
    
    sourceType별 분기 없이 순수하게 factor의 수치만으로 계산합니다.
    sourceType/subIssueCode별 factor 값 조정은 baseline.py에서 사전에 수행해야 합니다.
    """
    urgency = mapUrgency(factor.timeHorizon)
    likelihood = factor.likelihood if factor.likelihood is not None else 0.0
    irremediability = factor.irremediability if factor.irremediability is not None else 0.0
    scale = factor.scale
    scope = factor.scope

    if factor.impactDirection == "negative":
        score = (0.30 * scale) + (0.25 * scope) + (0.20 * likelihood) + (0.15 * irremediability) + (0.10 * urgency)
    else:
        # positive impact
        score = (0.35 * scale) + (0.30 * scope) + (0.25 * likelihood) + (0.10 * urgency)
        
    return clamp(score, 0.0, 5.0)

def calcFinancial(
    factor: FinancialFactor, 
    sourceType: str = "news", 
    subIssueCode: str = ""
) -> float:
    """
    재무적 중대성(Financial) 요소를 기반으로 v3.2 산식에 따라 점수를 산출합니다.
    반환값: 0.0 ~ 5.0 (canonical score)
    
    sourceType별 분기 없이 순수하게 factor의 수치만으로 계산합니다.
    sourceType/subIssueCode별 factor 값 조정은 baseline.py에서 사전에 수행해야 합니다.
    """
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
    urgency = mapUrgency(factor.timeHorizon)
    likelihood = factor.likelihood if factor.likelihood is not None else 0.0
    
    if factor.financialIroType == "risk":
        score = (0.45 * base_mag) + (0.35 * likelihood) + (0.20 * urgency)
    else:
        # opportunity
        score = (0.55 * base_mag) + (0.25 * likelihood) + (0.20 * urgency)
        
    return clamp(score, 0.0, 5.0)

def scoreSignals(signals: list) -> list:
    """
    DMASignal 리스트의 factor를 기반으로 0~5 점수를 계산하여 채워넣습니다.
    AI가 직접 점수를 주지 않고, 이 함수가 factor → score 변환을 수행합니다.
    """
    for sig in signals:
        if sig.impactFactor:
            sig.impactScore05 = calcImpact(sig.impactFactor, sig.sourceType, sig.subIssueCode)
        if sig.financialFactor:
            sig.financialScore05 = calcFinancial(sig.financialFactor, sig.sourceType, sig.subIssueCode)
    return signals


# Compatibility wrappers for previous public names

def timeHorizonToUrgency(timeHorizon: str) -> float:
    return mapUrgency(timeHorizon)


def calculateImpactScore(
    factor: ImpactFactor,
    sourceType: str = "news",
    subIssueCode: str = "",
) -> float:
    return calcImpact(factor, sourceType, subIssueCode)


def calculateFinancialScore(
    factor: FinancialFactor,
    sourceType: str = "news",
    subIssueCode: str = "",
) -> float:
    return calcFinancial(factor, sourceType, subIssueCode)


def scoreDmaSignals(signals: list) -> list:
    return scoreSignals(signals)


# =====================================================================================
# DMA v1.3 MVP Slim Canonical Engine — pure scoring functions (PARALLEL ADDITION)
# =====================================================================================
# All legacy functions above remain unchanged. The v1.3 canonical engine differs from
# legacy in three deliberate ways:
#   1. Missing REQUIRED factor -> axis UNOBSERVED (score=None), never a 0 substitution.
#   2. Missing OPTIONAL factor -> observed factor weights are RE-NORMALIZED (reweighted).
#   3. Explicit zero is a real observation and participates in the score.
# Positive/Negative impact and Risk/Opportunity financial are NEVER offset; sub-issue
# aggregation is MAX. No string-formula eval anywhere — algorithms live here in Python,
# weights/thresholds live in the slim JSON policy.
# =====================================================================================

# Sentinel returned by urgency resolution when urgency is genuinely unobserved.
UNOBSERVED = "UNOBSERVED"

# Dominant financial magnitude tie-break order (rulebook 08.2).
_FINANCIAL_MAGNITUDE_TIEBREAK = (
    "legalRegulatoryMagnitude",
    "capexMagnitude",
    "costMagnitude",
    "revenueMagnitude",
    "financingMagnitude",
    "assetLiabilityMagnitude",
)


def validate_ai_extracted_facts_v13(
    facts: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Validate a raw AI fact dict against ai_fact_validation_policy.json.

    Returns a result dict::

        {"valid": bool, "violations": [{"field","reason"}, ...], "acceptedFacts": {...}}

    Rejection rules:
      - any forbidden field present (scores, magnitudes, confirmed dedup ids) -> reject
      - any unknown field (not in allowedFactFields) -> reject
      - any tri-state field with a value outside {TRUE, FALSE, UNKNOWN} -> reject

    AI never decides a score. This function does not raise on invalid facts; it
    reports them so the caller can route to a review queue.
    """
    allowed = set(policy.get("allowedFactFields", []))
    forbidden = set(policy.get("forbiddenFields", []))
    tristate_fields = set(policy.get("triStateFields", []))
    tristate_values = set(policy.get("triStateAllowedValues", ["TRUE", "FALSE", "UNKNOWN"]))

    violations: List[Dict[str, str]] = []
    accepted: Dict[str, Any] = {}

    for field, value in facts.items():
        if field in forbidden:
            violations.append({"field": field, "reason": "FORBIDDEN_FIELD"})
            continue
        if field not in allowed:
            violations.append({"field": field, "reason": "UNKNOWN_FIELD"})
            continue
        if field in tristate_fields and value is not None and str(value) not in tristate_values:
            violations.append({"field": field, "reason": "INVALID_TRI_STATE"})
            continue
        accepted[field] = value

    valid = len(violations) == 0
    return {
        "valid": valid,
        "violations": violations,
        "acceptedFacts": accepted if valid else {},
    }


def resolve_urgency_v13(
    time_horizon: Optional[str],
    urgency_policy: Mapping[str, Any],
    explicit_no_urgency: bool = False,
):
    """
    Resolve urgency from a time horizon.

    - explicit_no_urgency=True -> explicit observed zero (urgency_policy["explicitNoUrgency"])
    - short/mid/long -> mapped value
    - otherwise -> UNOBSERVED sentinel (missing evidence; never 0-substituted)
    """
    if explicit_no_urgency:
        return float(urgency_policy.get("explicitNoUrgency", 0))
    if time_horizon in ("short", "mid", "long"):
        return float(urgency_policy[time_horizon])
    return UNOBSERVED


def ratio_to_financial_magnitude_v13(
    ratio: Optional[float],
    bands: Sequence[Mapping[str, Any]],
) -> int:
    """
    Map an exposure ratio to a 0..5 magnitude using the configured bands.

    ratio is None or <= 0 -> 0 (no exposure). Band edges honour minInclusive /
    maxExclusive flags so boundaries are deterministic.
    """
    if ratio is None or ratio <= 0:
        return 0
    for band in bands:
        lo = band.get("min")
        hi = band.get("max")
        min_inclusive = bool(band.get("minInclusive", False))
        max_exclusive = bool(band.get("maxExclusive", False))
        lo_ok = (ratio >= lo) if min_inclusive else (ratio > lo)
        if hi is None:
            hi_ok = True
        else:
            hi_ok = (ratio < hi) if max_exclusive else (ratio <= hi)
        if lo_ok and hi_ok:
            return int(band["score"])
    return 0


def dominant_financial_magnitude_v13(
    channels: Mapping[str, Optional[float]],
) -> Tuple[Optional[float], Optional[str]]:
    """
    Return (value, channel) of the dominant (MAX) financial magnitude channel.

    Only observed (non-None) channels participate. Ties are broken by the rulebook
    precedence order. Returns (None, None) if no channel is observed (UNOBSERVED).
    """
    observed = {k: float(v) for k, v in channels.items() if v is not None}
    if not observed:
        return None, None
    max_value = max(observed.values())
    for name in _FINANCIAL_MAGNITUDE_TIEBREAK:
        if name in observed and observed[name] == max_value:
            return max_value, name
    # Channel not in tie-break list: deterministic fallback by name.
    for name in sorted(observed):
        if observed[name] == max_value:
            return max_value, name
    return max_value, None


def _score_observed_reweighted(
    axis: str,
    polarity: str,
    factor_values: Mapping[str, Optional[float]],
    axis_policy: Mapping[str, Any],
    rule_version: Optional[str],
    score_purpose: ScorePurposeV13,
) -> AxisScoreTraceV13:
    """
    Core canonical algorithm shared by impact and financial axes.

    factor_values maps each weighted factor name -> observed value or None (missing).
    An explicit 0 is observed; None is missing. If any REQUIRED factor is missing the
    axis is UNOBSERVED (score None). Otherwise observed weights are re-normalised over
    the observed factors and the 0..5 score is the weighted average.
    """
    weights: Dict[str, float] = {k: float(v) for k, v in axis_policy["weights"].items()}
    required: List[str] = list(axis_policy.get("required", []))
    optional: List[str] = list(axis_policy.get("optional", []))

    observed = [k for k in weights if factor_values.get(k) is not None]
    missing = [k for k in weights if factor_values.get(k) is None]
    missing_required = [k for k in required if factor_values.get(k) is None]
    missing_optional = [k for k in optional if factor_values.get(k) is None]

    if missing_required:
        traces = [
            FactorTraceV13(
                factorName=name,
                observedValue=(None if factor_values.get(name) is None else float(factor_values[name])),
                status=(FactorStatusV13.UNOBSERVED if factor_values.get(name) is None
                        else FactorStatusV13.AUTO_CONFIRMED),
                decisionSource=(DecisionSourceV13.UNOBSERVED if factor_values.get(name) is None
                                else DecisionSourceV13.RULE_AUTO),
                baseWeight=weights[name],
                effectiveWeight=None,
                contribution=None,
            )
            for name in weights
        ]
        return AxisScoreTraceV13(
            axis=axis,
            polarity=polarity,
            score=None,
            status=FactorStatusV13.UNOBSERVED,
            scorePurpose=score_purpose,
            requiredFactors=required,
            optionalFactors=optional,
            observedFactors=observed,
            missingRequired=missing_required,
            missingOptional=missing_optional,
            reweightApplied=False,
            offsettingAllowed=False,
            factorTraces=traces,
            ruleVersion=rule_version,
        )

    observed_weight_sum = sum(weights[k] for k in observed)
    reweight_applied = len(observed) != len(weights)

    factor_traces: List[FactorTraceV13] = []
    score = 0.0
    for name in weights:
        value = factor_values.get(name)
        if value is None:
            factor_traces.append(
                FactorTraceV13(
                    factorName=name,
                    observedValue=None,
                    status=FactorStatusV13.UNOBSERVED,
                    decisionSource=DecisionSourceV13.UNOBSERVED,
                    baseWeight=weights[name],
                    effectiveWeight=0.0,
                    contribution=0.0,
                    note="optional factor missing; reweighted out",
                )
            )
            continue
        effective_weight = weights[name] / observed_weight_sum if observed_weight_sum > 0 else 0.0
        contribution = effective_weight * float(value)
        score += contribution
        factor_traces.append(
            FactorTraceV13(
                factorName=name,
                observedValue=float(value),
                status=FactorStatusV13.AUTO_CONFIRMED,
                decisionSource=DecisionSourceV13.RULE_AUTO,
                baseWeight=weights[name],
                effectiveWeight=effective_weight,
                contribution=contribution,
            )
        )

    return AxisScoreTraceV13(
        axis=axis,
        polarity=polarity,
        score=clamp(score, 0.0, 5.0),
        status=FactorStatusV13.AUTO_CONFIRMED,
        scorePurpose=score_purpose,
        requiredFactors=required,
        optionalFactors=optional,
        observedFactors=observed,
        missingRequired=[],
        missingOptional=missing_optional,
        reweightApplied=reweight_applied,
        offsettingAllowed=False,
        factorTraces=factor_traces,
        ruleVersion=rule_version,
    )


def calculate_impact_observed_reweighted_v13(
    impact_direction: str,
    scale: Optional[float],
    likelihood: Optional[float],
    policy: Mapping[str, Any],
    scope: Optional[float] = None,
    irremediability: Optional[float] = None,
    time_horizon: Optional[str] = None,
    explicit_no_urgency: bool = False,
) -> AxisScoreTraceV13:
    """
    Canonical Impact axis score (0..5) with observed-only reweighting.

    impact_direction: 'negative' | 'positive'. Required factors: scale, likelihood.
    Optional: scope, (irremediability for negative only), urgency (from time_horizon).
    """
    if impact_direction not in ("negative", "positive"):
        raise ValueError(f"Unknown impact_direction: {impact_direction!r}")
    axis_policy = policy["impact"][impact_direction]
    urgency = resolve_urgency_v13(time_horizon, policy["urgency"], explicit_no_urgency)

    factor_values: Dict[str, Optional[float]] = {}
    weight_keys = axis_policy["weights"].keys()
    if "scale" in weight_keys:
        factor_values["scale"] = None if scale is None else float(scale)
    if "scope" in weight_keys:
        factor_values["scope"] = None if scope is None else float(scope)
    if "likelihood" in weight_keys:
        factor_values["likelihood"] = None if likelihood is None else float(likelihood)
    if "irremediability" in weight_keys:
        factor_values["irremediability"] = None if irremediability is None else float(irremediability)
    if "urgency" in weight_keys:
        factor_values["urgency"] = None if urgency == UNOBSERVED else float(urgency)

    return _score_observed_reweighted(
        axis="impact",
        polarity=impact_direction,
        factor_values=factor_values,
        axis_policy=axis_policy,
        rule_version=policy.get("ruleVersion"),
        score_purpose=ScorePurposeV13.CANONICAL_IRO,
    )


def calculate_financial_observed_reweighted_v13(
    financial_iro_type: str,
    magnitude: Optional[float],
    policy: Mapping[str, Any],
    likelihood: Optional[float] = None,
    time_horizon: Optional[str] = None,
    explicit_no_urgency: bool = False,
) -> AxisScoreTraceV13:
    """
    Canonical Financial axis score (0..5) with observed-only reweighting.

    financial_iro_type: 'risk' | 'opportunity'. Required: magnitude (dominant channel).
    Optional: likelihood, urgency (from time_horizon).
    """
    if financial_iro_type not in ("risk", "opportunity"):
        raise ValueError(f"Unknown financial_iro_type: {financial_iro_type!r}")
    axis_policy = policy["financial"][financial_iro_type]
    urgency = resolve_urgency_v13(time_horizon, policy["urgency"], explicit_no_urgency)

    factor_values: Dict[str, Optional[float]] = {
        "magnitude": None if magnitude is None else float(magnitude),
        "likelihood": None if likelihood is None else float(likelihood),
        "urgency": None if urgency == UNOBSERVED else float(urgency),
    }

    return _score_observed_reweighted(
        axis="financial",
        polarity=financial_iro_type,
        factor_values=factor_values,
        axis_policy=axis_policy,
        rule_version=policy.get("ruleVersion"),
        score_purpose=ScorePurposeV13.CANONICAL_IRO,
    )


def calculate_canonical_axis_scores_v13(
    policy: Mapping[str, Any],
    impact: Optional[Mapping[str, Any]] = None,
    financial: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Optional[AxisScoreTraceV13]]:
    """
    Convenience combiner. ``impact`` / ``financial`` are kwarg dicts forwarded to the
    per-axis functions. Returns {"impact": AxisScoreTraceV13|None, "financial": ...}.
    A signal that only carries one axis leaves the other None.
    """
    result: Dict[str, Optional[AxisScoreTraceV13]] = {"impact": None, "financial": None}
    if impact is not None:
        result["impact"] = calculate_impact_observed_reweighted_v13(policy=policy, **impact)
    if financial is not None:
        result["financial"] = calculate_financial_observed_reweighted_v13(policy=policy, **financial)
    return result


def aggregate_axis_scores_max_v13(scores: Sequence[Optional[float]]) -> Optional[float]:
    """
    Sub-issue axis aggregation = MAX over observed (non-None) scores.

    Returns None if every contributing source is unobserved. MAX inherently never
    offsets positive against negative (or risk against opportunity).
    """
    observed = [float(s) for s in scores if s is not None]
    if not observed:
        return None
    return max(observed)


__all__ = [
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
    # v1.3 MVP slim canonical engine
    "UNOBSERVED",
    "validate_ai_extracted_facts_v13",
    "resolve_urgency_v13",
    "ratio_to_financial_magnitude_v13",
    "dominant_financial_magnitude_v13",
    "calculate_impact_observed_reweighted_v13",
    "calculate_financial_observed_reweighted_v13",
    "calculate_canonical_axis_scores_v13",
    "aggregate_axis_scores_max_v13",
]
