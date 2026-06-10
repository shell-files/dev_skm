"""
Domain: DMA Materiality (v1.3 MVP Slim Engine)
Layer: utils/screening
Responsibility:
- Pre-survey SCREENING signal helpers (NOT canonical IRO scores, NOT final rank)
- Benchmark presence screening (NONE / COMMON_ISSUE / BLIND_SPOT)
- Regulation base screening (CSRD / CBAM / DPP base rule cards)
- KCGS pillar signal + sub-issue boost (bounded)
- KIS financial resilience capability gate (DATA_EXPORT_REQUIRED)
- External screening MAX aggregation (no additive stacking)
Public functions:
- calculate_benchmark_screening_v13
- calculate_regulation_base_screening_v13
- calculate_kcgs_pillar_signal_v13
- calculate_kcgs_subissue_boost_v13
- calculate_kis_financial_resilience_capability_v13
- aggregate_external_screening_by_max_v13
Do not:
- do not treat a screening signal as a canonical impact/financial score
- do not implement CSRD/CBAM/DPP auto applicability truth tables (CONFIG_PENDING)
- do not invent KIS grid thresholds (DATA_EXPORT_REQUIRED)
- do not hardcode KCGS pillar -> sub-issue mapping (DATA_EXPORT_REQUIRED)
- do not eval / exec config strings
- do not connect to a DB / Redis / Kafka

Screening Signal != Canonical Impact Score != Canonical Financial Score != Final DMA Rank.
가중치/Threshold/Rule Card는 screening_policy.json에 있고, 계산 알고리즘은 여기 Python에 둔다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.models.dmaengine import ScorePurposeV13, ScreeningTraceV13

# Screening status vocabulary.
STATUS_OBSERVED = "OBSERVED"
STATUS_UNOBSERVED = "UNOBSERVED"
STATUS_CAPABILITY_PENDING = "CAPABILITY_PENDING"

# Marker the policy uses for "do not score this; it is unobserved".
_UNOBSERVED_TOKEN = "UNOBSERVED"


def _signal_value(raw: Any) -> Optional[float]:
    """Convert a policy cell to a numeric signal, or None when it is UNOBSERVED."""
    if raw is None or (isinstance(raw, str) and raw == _UNOBSERVED_TOKEN):
        return None
    return float(raw)


def calculate_benchmark_screening_v13(
    observation: str,
    policy: Mapping[str, Any],
) -> ScreeningTraceV13:
    """
    Benchmark presence screening.

    observation in {NONE, COMMON_ISSUE, BLIND_SPOT}. The benchmark presence signal is
    a generic materiality-presence indicator applied equally to both axes
    (NONE=0, COMMON_ISSUE=3, BLIND_SPOT=4). This is a pre-survey screening signal, not
    a canonical score.
    """
    bench = policy["benchmark"]
    if observation not in bench or observation == "aggregation":
        raise ValueError(f"Unknown benchmark observation: {observation!r}")
    value = float(bench[observation])
    return ScreeningTraceV13(
        channel="benchmark",
        scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        impactSignal=value,
        financialSignal=value,
        status=STATUS_OBSERVED,
        rawInputs={"observation": observation},
    )


def calculate_regulation_base_screening_v13(
    regime: str,
    applicability: str,
    policy: Mapping[str, Any],
) -> ScreeningTraceV13:
    """
    Regulation BASE screening (rule-card lookup only; NOT auto-classification).

    regime in {CSRD, CBAM, DPP}; applicability in {DIRECT_MANDATORY, MATERIAL_VALUE_CHAIN,
    MONITORING_ONLY, NOT_APPLICABLE, UNKNOWN}. UNKNOWN -> UNOBSERVED (both axes None).
    NOT_APPLICABLE -> observed explicit zero. The automatic applicability truth table is
    intentionally out of scope (capability regulationAutoClassification = CONFIG_PENDING).
    """
    regulation = policy["regulation"]
    if regime not in regulation:
        raise ValueError(f"Unknown regulation regime: {regime!r}")
    regime_rules = regulation[regime]
    if applicability not in regime_rules:
        raise ValueError(f"Unknown applicability {applicability!r} for regime {regime!r}")

    cell = regime_rules[applicability]
    impact = _signal_value(cell.get("impact"))
    financial = _signal_value(cell.get("financial"))
    status = STATUS_UNOBSERVED if (impact is None and financial is None) else STATUS_OBSERVED

    return ScreeningTraceV13(
        channel=f"regulation_{regime.lower()}",
        scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        impactSignal=impact,
        financialSignal=financial,
        status=status,
        capability=policy.get("capabilities", {}).get("regulationAutoClassification"),
        rawInputs={"regime": regime, "applicability": applicability},
    )


def calculate_kcgs_pillar_signal_v13(
    grade: str,
    trend: str,
    policy: Mapping[str, Any],
):
    """
    KCGS pillar risk signal = gradeRisk[grade] + trendModifier[trend].

    Returns a dict::

        {"pillarSignal": float|None, "status": "OBSERVED"|"UNOBSERVED",
         "gradeRisk": float, "trendModifier": float|None}

    insufficientData trend -> UNOBSERVED (pillarSignal None). This is a governance
    screening signal; it is not added directly to a canonical final score.
    """
    kcgs = policy["kcgs"]
    grade_risk_map = kcgs["gradeRisk"]
    trend_map = kcgs["trendModifier"]
    if grade not in grade_risk_map:
        raise ValueError(f"Unknown KCGS grade: {grade!r}")
    if trend not in trend_map:
        raise ValueError(f"Unknown KCGS trend: {trend!r}")

    grade_risk = float(grade_risk_map[grade])
    trend_raw = trend_map[trend]
    if isinstance(trend_raw, str) and trend_raw == _UNOBSERVED_TOKEN:
        return {
            "pillarSignal": None,
            "status": STATUS_UNOBSERVED,
            "gradeRisk": grade_risk,
            "trendModifier": None,
        }
    trend_modifier = float(trend_raw)
    return {
        "pillarSignal": grade_risk + trend_modifier,
        "status": STATUS_OBSERVED,
        "gradeRisk": grade_risk,
        "trendModifier": trend_modifier,
    }


def calculate_kcgs_subissue_boost_v13(
    pillar_signal: Optional[float],
    policy: Mapping[str, Any],
) -> Optional[float]:
    """
    Bounded KCGS sub-issue boost = min(maxSubIssueBoost, pillarSignal * boostMultiplier).

    pillar_signal None -> None (unobserved). The pillar -> sub-issue propagation mapping
    itself is DATA_EXPORT_REQUIRED and not implemented here.
    """
    if pillar_signal is None:
        return None
    kcgs = policy["kcgs"]
    boost = float(pillar_signal) * float(kcgs["boostMultiplier"])
    return min(float(kcgs["maxSubIssueBoost"]), boost)


def calculate_kis_financial_resilience_capability_v13(
    policy: Mapping[str, Any],
) -> ScreeningTraceV13:
    """
    KIS financial resilience is a CAPABILITY gate only in Phase A.

    Grid thresholds are not available (DATA_EXPORT_REQUIRED), so this emits no numeric
    signal and never predicts/labels a credit rating.
    """
    kis = policy["kis"]
    return ScreeningTraceV13(
        channel="kis_financial_resilience",
        scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        impactSignal=None,
        financialSignal=None,
        status=STATUS_CAPABILITY_PENDING,
        capability=kis.get("capability"),
        rawInputs={
            "reason": kis.get("reason"),
            "creditRatingPredictionAllowedYn": kis.get("creditRatingPredictionAllowedYn"),
            "officialCreditRatingLabelAllowedYn": kis.get("officialCreditRatingLabelAllowedYn"),
        },
    )


def aggregate_external_screening_by_max_v13(
    signals: Sequence[ScreeningTraceV13],
    policy: Mapping[str, Any],
) -> ScreeningTraceV13:
    """
    Aggregate multiple screening signals by MAX per axis (never additive).

    Only observed (non-None) signals participate. Returns a combined ScreeningTraceV13
    whose impactSignal / financialSignal are the per-axis maxima, or None if no source
    observed that axis.
    """
    # external aggregation policy is declared; MAX / non-additive is enforced here.
    impacts: List[float] = [s.impactSignal for s in signals if s.impactSignal is not None]
    financials: List[float] = [s.financialSignal for s in signals if s.financialSignal is not None]

    impact_max = max(impacts) if impacts else None
    financial_max = max(financials) if financials else None
    status = STATUS_UNOBSERVED if (impact_max is None and financial_max is None) else STATUS_OBSERVED

    return ScreeningTraceV13(
        channel="external_screening_max",
        scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        impactSignal=impact_max,
        financialSignal=financial_max,
        status=status,
        rawInputs={
            "additiveYn": policy.get("externalAggregation", {}).get("additiveYn", False),
            "contributingChannels": [s.channel for s in signals],
            "impactObservedCount": len(impacts),
            "financialObservedCount": len(financials),
        },
    )


__all__ = [
    "STATUS_OBSERVED",
    "STATUS_UNOBSERVED",
    "STATUS_CAPABILITY_PENDING",
    "calculate_benchmark_screening_v13",
    "calculate_regulation_base_screening_v13",
    "calculate_kcgs_pillar_signal_v13",
    "calculate_kcgs_subissue_boost_v13",
    "calculate_kis_financial_resilience_capability_v13",
    "aggregate_external_screening_by_max_v13",
]
