from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from src.models.dmaengine import DMASignal, FinancialFactor
from src.utils.companycontextrepository import getMaterialityRunContext
from src.utils.dmafinancialrepository import getG0FinancialBasis
from src.utils.subissuemaster import getScoringAllowedIros


FINANCIAL_EXPOSURE_RULE_VERSION = "financial-exposure-rule-v1"

FINANCIAL_CHANNELS = [
    "revenueMagnitude",
    "costMagnitude",
    "capexMagnitude",
    "assetLiabilityMagnitude",
    "financingMagnitude",
    "legalRegulatoryMagnitude",
]

CHANNEL_DENOMINATORS = {
    "revenueMagnitude": {
        "primary": "revenue",
        "fallback": None,
        "cap": None,
    },
    "costMagnitude": {
        "primary": "operatingProfit",
        "fallback": "revenue",
        "cap": None,
    },
    "capexMagnitude": {
        "primary": "capex",
        "fallback": "revenue",
        "cap": None,
    },
    "assetLiabilityMagnitude": {
        "primary": None,
        "fallback": "revenue",
        "cap": 3,
    },
    "financingMagnitude": {
        "primary": "revenue",
        "fallback": "capex",
        "cap": None,
    },
    "legalRegulatoryMagnitude": {
        "primary": "operatingProfit",
        "fallback": "revenue",
        "cap": None,
    },
}

DOMINANT_MAGNITUDE_PRIORITY = [
    "legalRegulatoryMagnitude",
    "capexMagnitude",
    "costMagnitude",
    "revenueMagnitude",
    "financingMagnitude",
    "assetLiabilityMagnitude",
]

FINANCIAL_EXPOSURE_RULES = {
    "E_CLIMATE__CLIMATE_TARGETS_TRANSITION": {
        "financialIroType": "opportunity",
        "rationale": "Transition planning may require transition capex and can affect revenue resilience.",
        "channels": [
            {
                "channel": "capexMagnitude",
                "ratioPreset": 0.010,
                "rationale": "Transition planning may require capex for decarbonization and process conversion.",
            },
            {
                "channel": "revenueMagnitude",
                "ratioPreset": 0.005,
                "rationale": "Transition risk may affect customer demand and market access.",
            },
        ],
    },
    "E_CLIMATE__GHG_SCOPE12_EMISSIONS": {
        "financialIroType": "risk",
        "rationale": "Scope 1 and 2 emissions may create energy cost, carbon price, or compliance exposure.",
        "channels": [
            {
                "channel": "costMagnitude",
                "ratioPreset": 0.005,
                "rationale": "GHG and energy exposure can increase operating cost.",
            },
            {
                "channel": "legalRegulatoryMagnitude",
                "ratioPreset": 0.003,
                "rationale": "GHG regulation can create compliance and penalty exposure.",
            },
        ],
    },
    "E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE": {
        "financialIroType": "opportunity",
        "rationale": "Low-carbon or eco product performance can affect product revenue and transition investment.",
        "channels": [
            {
                "channel": "revenueMagnitude",
                "ratioPreset": 0.010,
                "rationale": "Low-carbon product strategy may create revenue opportunity.",
            },
            {
                "channel": "capexMagnitude",
                "ratioPreset": 0.005,
                "rationale": "Product transition may require process or product capex.",
            },
        ],
    },
    "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP": {
        "financialIroType": "risk",
        "rationale": "Supplier due diligence can create audit, remediation, and customer compliance cost exposure.",
        "channels": [
            {
                "channel": "costMagnitude",
                "ratioPreset": 0.005,
                "rationale": "Supplier audit and remediation can increase operating cost.",
            },
            {
                "channel": "financingMagnitude",
                "ratioPreset": 0.003,
                "rationale": "Supply-chain risk can affect customer/investor risk perception.",
            },
        ],
    },
    "S_SAFETY__OHS_MANAGEMENT": {
        "financialIroType": "risk",
        "rationale": "Occupational health and safety management can affect safety investment, incident cost, and legal exposure.",
        "channels": [
            {
                "channel": "costMagnitude",
                "ratioPreset": 0.003,
                "rationale": "OHS programs and incident prevention can increase operating cost.",
            },
            {
                "channel": "legalRegulatoryMagnitude",
                "ratioPreset": 0.002,
                "rationale": "Safety incidents can create legal or regulatory exposure.",
            },
        ],
    },
    "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY": {
        "financialIroType": "risk",
        "rationale": "Product safety and quality can create recall, warranty, litigation, and compliance exposure.",
        "channels": [
            {
                "channel": "legalRegulatoryMagnitude",
                "ratioPreset": 0.005,
                "rationale": "Product safety issues can create litigation, penalty, or regulatory cost.",
            },
            {
                "channel": "costMagnitude",
                "ratioPreset": 0.004,
                "rationale": "Quality defects can create recall and warranty costs.",
            },
        ],
    },
    "G_BUSINESS_CONDUCT__LEGAL_COMPLIANCE_VIOLATIONS": {
        "financialIroType": "risk",
        "rationale": "Legal compliance violations can create penalties, remediation cost, and financing access impact.",
        "channels": [
            {
                "channel": "legalRegulatoryMagnitude",
                "ratioPreset": 0.003,
                "rationale": "Compliance violations can create fine, litigation, and remediation exposure.",
            },
            {
                "channel": "financingMagnitude",
                "ratioPreset": 0.002,
                "rationale": "Compliance failures can affect investor or lender perception.",
            },
        ],
    },
    "S_PRIVACY__DATA_BREACH_SECURITY_INCIDENTS": {
        "financialIroType": "risk",
        "rationale": "Data breach and security incidents can create fines, response cost, and business disruption.",
        "channels": [
            {
                "channel": "legalRegulatoryMagnitude",
                "ratioPreset": 0.004,
                "rationale": "Data privacy incidents can create regulatory penalties and litigation.",
            },
            {
                "channel": "costMagnitude",
                "ratioPreset": 0.003,
                "rationale": "Security incidents can create recovery and control remediation cost.",
            },
        ],
    },
    "E_CLIMATE__CLIMATE_RISK": {
        "financialIroType": "risk",
        "rationale": "Climate risk can affect assets, operations, financing, and transition exposure.",
        "channels": [
            {
                "channel": "assetLiabilityMagnitude",
                "ratioPreset": 0.050,
                "rationale": "Asset/liability basis is unavailable in G0-02, so MVP caps this channel at 3.",
            },
        ],
    },
}


def ratioToMagnitude(ratio: Optional[float]) -> int:
    if ratio is None or ratio <= 0:
        return 0
    if ratio < 0.001:
        return 1
    if ratio < 0.005:
        return 2
    if ratio < 0.01:
        return 3
    if ratio < 0.03:
        return 4
    return 5


def buildFinancialExposureForSignal(
    signal: DMASignal,
    companyId: int,
    reportingYear: int,
    preferConsolidated: bool = True,
) -> tuple[DMASignal, dict]:
    basis = getG0FinancialBasis(companyId, reportingYear, preferConsolidated)
    return buildFinancialExposureForSignalWithBasis(signal, basis)


def applyG0FinancialExposure(
    signals: list[DMASignal],
    companyId: int,
    reportingYear: int,
    preferConsolidated: bool = True,
) -> list[DMASignal]:
    basis = getG0FinancialBasis(companyId, reportingYear, preferConsolidated)
    updatedSignals = []
    for signal in signals:
        updatedSignal, _ = buildFinancialExposureForSignalWithBasis(signal, basis)
        updatedSignals.append(updatedSignal)
    return updatedSignals


def applyG0FinancialExposureForRun(
    signals: list[DMASignal],
    runId: int,
) -> list[DMASignal]:
    runContext = getMaterialityRunContext(runId)
    if not runContext:
        return [
            _appendTraceWarning(
                signal,
                f"NO_RUN_CONTEXT: no ESG_MATERIALITY_RUN row found for runId={runId}.",
            )
            for signal in signals
        ]

    companyId = int(runContext["company_id"])
    reportingYear = int(runContext["reporting_year"])
    preferConsolidated, warnings = resolvePreferConsolidated(runContext)
    basis = getG0FinancialBasis(companyId, reportingYear, preferConsolidated)
    if warnings:
        basis = deepcopy(basis)
        basis.setdefault("trace", {})["runContextWarnings"] = warnings

    updatedSignals = []
    for signal in signals:
        updatedSignal, _ = buildFinancialExposureForSignalWithBasis(signal, basis)
        updatedSignals.append(updatedSignal)
    return updatedSignals


def buildFinancialExposureForSignalWithBasis(
    signal: DMASignal,
    financialBasis: dict,
) -> tuple[DMASignal, dict]:
    trace = _baseTrace(signal, financialBasis)
    sourceType = _normalizedSourceType(signal)
    confidence = _safeFloat(getattr(signal, "confidenceScore", None), 1.0)
    existingFactor = getattr(signal, "financialFactor", None)
    existingIroType = getattr(existingFactor, "financialIroType", None)

    if sourceType == "survey":
        trace["warnings"].append("SURVEY_EXCLUDED: survey financial exposure is excluded in MVP.")
        return _attachTrace(signal, trace), {"financialExposureTrace": trace}

    if existingIroType and not canApplyFinancialExposure(signal.subIssueCode, existingIroType):
        trace["warnings"].append(
            f"IRO_NOT_ALLOWED: existing financialFactor '{existingIroType}' is not allowed for {signal.subIssueCode}."
        )
        return _copySignal(signal, financialFactor=None, financialExposureTrace=trace), {"financialExposureTrace": trace}

    if financialBasis.get("basisType") == "NONE":
        trace["warnings"].append("No G0-02 financial basis found; financial factor kept as adapter fallback.")
        return _attachTrace(signal, trace), {"financialExposureTrace": trace}

    rule = FINANCIAL_EXPOSURE_RULES.get(signal.subIssueCode)
    if not rule:
        trace["warnings"].append(f"No financial exposure rule found for subIssueCode={signal.subIssueCode}.")
        return _attachTrace(signal, trace), {"financialExposureTrace": trace}

    if not canApplyFinancialExposure(signal.subIssueCode, rule["financialIroType"]):
        trace["subIssueRule"] = {
            "subIssueCode": signal.subIssueCode,
            "financialIroType": rule["financialIroType"],
            "rationale": rule["rationale"],
        }
        trace["warnings"].append(
            f"IRO_NOT_ALLOWED: {rule['financialIroType']} is not allowed for {signal.subIssueCode}."
        )
        return _copySignal(signal, financialFactor=None, financialExposureTrace=trace), {"financialExposureTrace": trace}

    trace["subIssueRule"] = {
        "subIssueCode": signal.subIssueCode,
        "financialIroType": rule["financialIroType"],
        "rationale": rule["rationale"],
    }

    channelScores = {}
    newMagnitudes = {}
    for channelRule in rule.get("channels", []):
        channel = channelRule.get("channel")
        channelScore = calculateChannelScore(
            channel=channel,
            ratioPreset=_safeFloat(channelRule.get("ratioPreset"), 0.0),
            rationale=channelRule.get("rationale", ""),
            financialBasis=financialBasis,
            sourceType=sourceType,
            confidence=confidence,
        )
        channelScores[channel] = channelScore
        newMagnitudes[channel] = channelScore["magnitudeAfterAdjustment"]
        previousMagnitude = _getFactorChannelValue(existingFactor, channel)
        channelScores[channel]["previousMagnitude"] = previousMagnitude
        channelScores[channel]["overrideYn"] = _isOverride(
            previousMagnitude,
            channelScore["magnitudeAfterAdjustment"],
        )
        if channelScore.get("warning"):
            trace["warnings"].append(channelScore["warning"])
        if channelScore.get("confidenceWarning") and channelScore["confidenceWarning"] not in trace["warnings"]:
            trace["warnings"].append(channelScore["confidenceWarning"])

    trace["channelScores"] = channelScores
    dominantType, dominantValue = dominantMagnitude(newMagnitudes)
    trace["dominantMagnitudeType"] = dominantType
    trace["dominantMagnitudeValue"] = dominantValue

    financialFactor = buildEnhancedFinancialFactor(
        existingFactor=existingFactor,
        rule=rule,
        newMagnitudes=newMagnitudes,
        sourceType=sourceType,
        confidence=confidence,
    )
    trace["financialIroType"] = financialFactor.financialIroType if financialFactor else rule["financialIroType"]
    trace["likelihood"] = financialFactor.likelihood if financialFactor else None
    trace["timeHorizon"] = financialFactor.timeHorizon if financialFactor else _factorTimeHorizon(existingFactor)
    trace["existingFinancialFactor"] = _factorMagnitudeSnapshot(existingFactor)
    trace["enhancedFinancialFactor"] = _factorMagnitudeSnapshot(financialFactor)

    updatedSignal = _copySignal(
        signal,
        financialFactor=financialFactor,
        financialExposureTrace=trace,
    )
    return updatedSignal, {"financialExposureTrace": trace}


def calculateChannelScore(
    channel: str,
    ratioPreset: float,
    rationale: str,
    financialBasis: dict,
    sourceType: str,
    confidence: float,
) -> dict:
    denominatorField, denominatorValue = selectDenominator(channel, financialBasis)
    estimatedExposure = None
    ratio = None
    warning = None

    if denominatorValue and denominatorValue > 0:
        ratio = ratioPreset
        estimatedExposure = denominatorValue * ratioPreset
    else:
        warning = f"No usable denominator for {channel}; magnitude set to 0."

    magnitude = ratioToMagnitude(ratio)
    sourceBonus = sourceTypeMagnitudeBonus(channel, magnitude, sourceType, confidence)
    magnitudeAfterSource = min(5, magnitude + sourceBonus)

    channelCap = CHANNEL_DENOMINATORS.get(channel, {}).get("cap")
    channelCapAppliedYn = False
    if channelCap is not None and magnitudeAfterSource > channelCap:
        magnitudeAfterSource = channelCap
        channelCapAppliedYn = True

    confidenceCap = confidenceMagnitudeCap(confidence)
    confidenceCapAppliedYn = False
    if confidenceCap is not None and magnitudeAfterSource > confidenceCap:
        magnitudeAfterSource = confidenceCap
        confidenceCapAppliedYn = True

    result = {
        "denominatorField": denominatorField,
        "denominatorValue": denominatorValue,
        "ratioPreset": ratioPreset,
        "estimatedExposure": estimatedExposure,
        "ratio": ratio,
        "magnitudeBeforeAdjustment": magnitude,
        "magnitudeAfterAdjustment": magnitudeAfterSource,
        "sourceTypeMagnitudeBonus": sourceBonus,
        "confidenceCapAppliedYn": confidenceCapAppliedYn,
        "channelCapAppliedYn": channelCapAppliedYn,
        "rationale": rationale,
    }
    if warning:
        result["warning"] = warning
    if confidence < 0.4:
        result["confidenceWarning"] = "LOW_CONFIDENCE_CAP_2"
    elif confidence < 0.7:
        result["confidenceWarning"] = "MEDIUM_CONFIDENCE_CAP_4"
    return result


def canApplyFinancialExposure(subIssueCode: str, financialIroType: str) -> bool:
    expectedIro = _financialIroToAllowedAxis(financialIroType)
    if not expectedIro:
        return False
    return expectedIro in getScoringAllowedIros(subIssueCode)


def resolvePreferConsolidated(runContext: dict) -> tuple[bool, list[str]]:
    scope = str(runContext.get("company_scope_type") or "").upper()
    if scope in {"PARENT", "GROUP", "HOLDING", "CONSOLIDATED"}:
        return True, []
    if scope in {"SUBSIDIARY", "ENTITY", "STANDALONE", "COMPANY"}:
        return False, []
    return True, [
        "UNKNOWN_COMPANY_SCOPE: preferConsolidated defaulted to True for MVP.",
    ]


def selectDenominator(channel: str, financialBasis: dict) -> tuple[Optional[str], Optional[float]]:
    config = CHANNEL_DENOMINATORS.get(channel) or {}
    for fieldName in (config.get("primary"), config.get("fallback")):
        if not fieldName:
            continue
        value = _safeFloat(financialBasis.get(fieldName), None)
        if value is not None and value > 0:
            return fieldName, value
    return None, None


def sourceTypeMagnitudeBonus(
    channel: str,
    magnitude: int,
    sourceType: str,
    confidence: float,
) -> int:
    if magnitude <= 0:
        return 0
    if sourceType == "regulation" and channel == "legalRegulatoryMagnitude":
        return 1
    if sourceType == "agency" and confidence >= 0.75:
        return 1
    return 0


def confidenceMagnitudeCap(confidence: float) -> Optional[int]:
    if confidence < 0.4:
        return 2
    if confidence < 0.7:
        return 4
    return None


def dominantMagnitude(magnitudes: dict[str, Optional[int]]) -> tuple[Optional[str], Optional[int]]:
    bestType = None
    bestValue = None
    for channel in DOMINANT_MAGNITUDE_PRIORITY:
        value = magnitudes.get(channel)
        if value is None:
            continue
        if bestValue is None or value > bestValue:
            bestType = channel
            bestValue = value
    return bestType, bestValue


def buildEnhancedFinancialFactor(
    existingFactor: Optional[FinancialFactor],
    rule: dict,
    newMagnitudes: dict[str, int],
    sourceType: str,
    confidence: float,
) -> FinancialFactor:
    baseValues = _factorMagnitudeSnapshot(existingFactor)
    for channel in FINANCIAL_CHANNELS:
        if channel in newMagnitudes:
            baseValues[channel] = newMagnitudes[channel]

    financialIroType = (
        existingFactor.financialIroType
        if existingFactor and existingFactor.financialIroType
        else rule["financialIroType"]
    )
    timeHorizon = _factorTimeHorizon(existingFactor)
    likelihood = existingFactor.likelihood if existingFactor and existingFactor.likelihood is not None else _likelihoodFromConfidence(confidence, sourceType)

    return FinancialFactor(
        financialIroType=financialIroType,
        revenueMagnitude=baseValues.get("revenueMagnitude"),
        costMagnitude=baseValues.get("costMagnitude"),
        capexMagnitude=baseValues.get("capexMagnitude"),
        assetLiabilityMagnitude=baseValues.get("assetLiabilityMagnitude"),
        financingMagnitude=baseValues.get("financingMagnitude"),
        legalRegulatoryMagnitude=baseValues.get("legalRegulatoryMagnitude"),
        likelihood=likelihood,
        timeHorizon=timeHorizon,
        evidenceSpans=list(getattr(existingFactor, "evidenceSpans", []) or []),
    )


def _likelihoodFromConfidence(confidence: float, sourceType: str) -> int:
    if confidence < 0.4:
        likelihood = 1
    elif confidence < 0.7:
        likelihood = 2
    elif confidence < 0.85:
        likelihood = 3
    else:
        likelihood = 4
    if sourceType == "regulation":
        likelihood += 1
    return max(0, min(5, likelihood))


def _baseTrace(signal: DMASignal, financialBasis: dict) -> dict:
    basisTrace = financialBasis.get("trace") or {}
    runContextWarnings = list(basisTrace.get("runContextWarnings") or [])
    return {
        "ruleVersion": FINANCIAL_EXPOSURE_RULE_VERSION,
        "basisType": financialBasis.get("basisType"),
        "basisSource": financialBasis.get("basisSource"),
        "selectedPriority": basisTrace.get("selectedPriority"),
        "fallbackUsedYn": bool(financialBasis.get("fallbackUsedYn")),
        "basis": {
            "revenue": financialBasis.get("revenue"),
            "operatingProfit": financialBasis.get("operatingProfit"),
            "netIncome": financialBasis.get("netIncome"),
            "capex": financialBasis.get("capex"),
            "depreciation": financialBasis.get("depreciation"),
        },
        "sourceRows": financialBasis.get("sourceRows", []),
        "subIssueRule": {
            "subIssueCode": signal.subIssueCode,
            "financialIroType": None,
            "rationale": None,
        },
        "channelScores": {},
        "dominantMagnitudeType": None,
        "dominantMagnitudeValue": None,
        "financialIroType": None,
        "likelihood": None,
        "timeHorizon": _factorTimeHorizon(getattr(signal, "financialFactor", None)),
        "sourceType": getattr(signal, "sourceType", None),
        "normalizedSourceType": _normalizedSourceType(signal),
        "confidenceScore": _safeFloat(getattr(signal, "confidenceScore", None), 1.0),
        "warnings": runContextWarnings,
    }


def _attachTrace(signal: DMASignal, trace: dict) -> DMASignal:
    return _copySignal(signal, financialFactor=getattr(signal, "financialFactor", None), financialExposureTrace=trace)


def _copySignal(
    signal: DMASignal,
    financialFactor: Optional[FinancialFactor],
    financialExposureTrace: dict,
) -> DMASignal:
    scoringPayload = deepcopy(getattr(signal, "scoringPayloadJson", None) or {})
    scoringPayload["financialExposureTrace"] = financialExposureTrace
    if hasattr(signal, "model_copy"):
        return signal.model_copy(
            update={
                "financialFactor": financialFactor,
                "scoringPayloadJson": scoringPayload,
            }
        )
    return signal.copy(
        update={
            "financialFactor": financialFactor,
            "scoringPayloadJson": scoringPayload,
        }
    )


def _factorMagnitudeSnapshot(factor: Optional[FinancialFactor]) -> dict:
    if factor is None:
        return {channel: None for channel in FINANCIAL_CHANNELS}
    return {
        "revenueMagnitude": factor.revenueMagnitude,
        "costMagnitude": factor.costMagnitude,
        "capexMagnitude": factor.capexMagnitude,
        "assetLiabilityMagnitude": factor.assetLiabilityMagnitude,
        "financingMagnitude": factor.financingMagnitude,
        "legalRegulatoryMagnitude": factor.legalRegulatoryMagnitude,
    }


def _getFactorChannelValue(factor: Optional[FinancialFactor], channel: str) -> Optional[int]:
    if factor is None or channel not in FINANCIAL_CHANNELS:
        return None
    return getattr(factor, channel, None)


def _isOverride(previousMagnitude: Optional[int], newMagnitude: Optional[int]) -> bool:
    if previousMagnitude is None:
        return bool(newMagnitude and newMagnitude > 0)
    return previousMagnitude != newMagnitude


def _factorTimeHorizon(factor: Optional[FinancialFactor]) -> str:
    if factor and factor.timeHorizon:
        return factor.timeHorizon
    return "mid"


def _normalizedSourceType(signal: DMASignal) -> str:
    sourceStep = str(getattr(signal, "sourceStep", "") or "").lower()
    sourceType = str(getattr(signal, "sourceType", "") or "").lower()
    if sourceStep == "benchmark":
        return "benchmark"
    if sourceStep == "survey" or sourceType == "survey":
        return "survey"
    if sourceType in {"regulation", "agency", "news"}:
        return sourceType
    if "regulation" in sourceType:
        return "regulation"
    if "agency" in sourceType:
        return "agency"
    return "news"


def _financialIroToAllowedAxis(financialIroType: str) -> Optional[str]:
    normalized = str(financialIroType or "").lower()
    if normalized in {"risk", "financial_risk"}:
        return "financial_risk"
    if normalized in {"opportunity", "financial_opportunity"}:
        return "financial_opportunity"
    return None


def _appendTraceWarning(signal: DMASignal, warning: str) -> DMASignal:
    scoringPayload = deepcopy(getattr(signal, "scoringPayloadJson", None) or {})
    trace = scoringPayload.get("financialExposureTrace") or {}
    warnings = list(trace.get("warnings") or [])
    warnings.append(warning)
    trace["warnings"] = warnings
    trace.setdefault("ruleVersion", FINANCIAL_EXPOSURE_RULE_VERSION)
    scoringPayload["financialExposureTrace"] = trace
    if hasattr(signal, "model_copy"):
        return signal.model_copy(update={"scoringPayloadJson": scoringPayload})
    return signal.copy(update={"scoringPayloadJson": scoringPayload})


def _safeFloat(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


__all__ = [
    "CHANNEL_DENOMINATORS",
    "DOMINANT_MAGNITUDE_PRIORITY",
    "FINANCIAL_CHANNELS",
    "FINANCIAL_EXPOSURE_RULES",
    "applyG0FinancialExposure",
    "applyG0FinancialExposureForRun",
    "buildEnhancedFinancialFactor",
    "buildFinancialExposureForSignal",
    "buildFinancialExposureForSignalWithBasis",
    "canApplyFinancialExposure",
    "calculateChannelScore",
    "confidenceMagnitudeCap",
    "dominantMagnitude",
    "ratioToMagnitude",
    "resolvePreferConsolidated",
    "selectDenominator",
    "sourceTypeMagnitudeBonus",
]
