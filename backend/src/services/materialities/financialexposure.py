from __future__ import annotations

from copy import deepcopy
from typing import Optional

from src.models.dmaengine import DMASignal, FinancialFactor
from src.repositories.companycontextrepository import getMaterialityRunContext
from src.repositories.financialbasisrepository import getBasis
from src.utils.typeutils import safeFloat as _safeFloat
from src.services.materialities import financialexposurecalc as _fc

# LEGACY ONLY:
# Applies existing G0 financial basis to legacy DMASignal financial factors.
# Not called by the new v1.3 Orchestrator foundation in Phase B.
# Keep formula behavior unchanged until a later runtime migration explicitly rewires it.


def buildFinancialExposureForSignal(
    signal: DMASignal,
    companyId: int,
    reportingYear: int,
    preferConsolidated: bool = True,
) -> tuple[DMASignal, dict]:
    basis = getBasis(companyId, reportingYear, preferConsolidated)
    return buildFinancialExposureForSignalWithBasis(signal, basis)


def applyG0FinancialExposure(
    signals: list[DMASignal],
    companyId: int,
    reportingYear: int,
    preferConsolidated: bool = True,
) -> list[DMASignal]:
    basis = getBasis(companyId, reportingYear, preferConsolidated)
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
    preferConsolidated, warnings = _fc.resolvePreferConsolidated(runContext)
    basis = getBasis(companyId, reportingYear, preferConsolidated)
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

    if existingIroType and not _fc.canApplyFinancialExposure(signal.subIssueCode, existingIroType):
        trace["warnings"].append(
            f"IRO_NOT_ALLOWED: existing financialFactor '{existingIroType}' is not allowed for {signal.subIssueCode}."
        )
        return _copySignal(signal, financialFactor=None, financialExposureTrace=trace), {"financialExposureTrace": trace}

    if financialBasis.get("basisType") == "NONE":
        trace["warnings"].append("No G0-02 financial basis found; financial factor kept as adapter fallback.")
        return _attachTrace(signal, trace), {"financialExposureTrace": trace}

    rule = _fc.FINANCIAL_EXPOSURE_RULES.get(signal.subIssueCode)
    if not rule:
        trace["warnings"].append(f"No financial exposure rule found for subIssueCode={signal.subIssueCode}.")
        return _attachTrace(signal, trace), {"financialExposureTrace": trace}

    if not _fc.canApplyFinancialExposure(signal.subIssueCode, rule["financialIroType"]):
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
        channelScore = _fc.calculateChannelScore(
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
    dominantType, dominantValue = _fc.dominantMagnitude(newMagnitudes)
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


def buildEnhancedFinancialFactor(
    existingFactor: Optional[FinancialFactor],
    rule: dict,
    newMagnitudes: dict,
    sourceType: str,
    confidence: float,
) -> FinancialFactor:
    baseValues = _factorMagnitudeSnapshot(existingFactor)
    for channel in _fc.FINANCIAL_CHANNELS:
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
        "ruleVersion": _fc.FINANCIAL_EXPOSURE_RULE_VERSION,
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
        return {channel: None for channel in _fc.FINANCIAL_CHANNELS}
    return {
        "revenueMagnitude": factor.revenueMagnitude,
        "costMagnitude": factor.costMagnitude,
        "capexMagnitude": factor.capexMagnitude,
        "assetLiabilityMagnitude": factor.assetLiabilityMagnitude,
        "financingMagnitude": factor.financingMagnitude,
        "legalRegulatoryMagnitude": factor.legalRegulatoryMagnitude,
    }


def _getFactorChannelValue(factor: Optional[FinancialFactor], channel: str) -> Optional[int]:
    if factor is None or channel not in _fc.FINANCIAL_CHANNELS:
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


def _appendTraceWarning(signal: DMASignal, warning: str) -> DMASignal:
    scoringPayload = deepcopy(getattr(signal, "scoringPayloadJson", None) or {})
    trace = scoringPayload.get("financialExposureTrace") or {}
    warnings = list(trace.get("warnings") or [])
    warnings.append(warning)
    trace["warnings"] = warnings
    trace.setdefault("ruleVersion", _fc.FINANCIAL_EXPOSURE_RULE_VERSION)
    scoringPayload["financialExposureTrace"] = trace
    if hasattr(signal, "model_copy"):
        return signal.model_copy(update={"scoringPayloadJson": scoringPayload})
    return signal.copy(update={"scoringPayloadJson": scoringPayload})


# Compatibility aliases

def applyExposure(
    signals: list[DMASignal],
    companyId: int,
    reportingYear: int,
    preferConsolidated: bool = True,
) -> list[DMASignal]:
    return applyG0FinancialExposure(signals, companyId, reportingYear, preferConsolidated)


def applyRunExposure(signals: list[DMASignal], runId: int) -> list[DMASignal]:
    return applyG0FinancialExposureForRun(signals, runId)


def buildExposure(
    signal: DMASignal,
    companyId: int,
    reportingYear: int,
    preferConsolidated: bool = True,
) -> tuple[DMASignal, dict]:
    return buildFinancialExposureForSignal(signal, companyId, reportingYear, preferConsolidated)


def buildExposureWithBasis(signal: DMASignal, financialBasis: dict) -> tuple[DMASignal, dict]:
    return buildFinancialExposureForSignalWithBasis(signal, financialBasis)


def calcChannelScore(
    channel: str,
    ratioPreset: float,
    rationale: str,
    financialBasis: dict,
    sourceType: str,
    confidence: float,
) -> dict:
    return _fc.calculateChannelScore(channel, ratioPreset, rationale, financialBasis, sourceType, confidence)


def calcSourceBonus(channel: str, magnitude: int, sourceType: str, confidence: float) -> int:
    return _fc.sourceTypeMagnitudeBonus(channel, magnitude, sourceType, confidence)


def calcConfidenceCap(confidence: float) -> Optional[int]:
    return _fc.confidenceMagnitudeCap(confidence)


def resolveDominant(magnitudes: dict) -> tuple[Optional[str], Optional[int]]:
    return _fc.dominantMagnitude(magnitudes)


def checkIro(subIssueCode: str, financialIroType: str) -> bool:
    return _fc.canApplyFinancialExposure(subIssueCode, financialIroType)


def resolveScope(runContext: dict) -> tuple[bool, list]:
    return _fc.resolvePreferConsolidated(runContext)


__all__ = [
    "CHANNEL_DENOMINATORS",
    "DOMINANT_MAGNITUDE_PRIORITY",
    "FINANCIAL_CHANNELS",
    "FINANCIAL_EXPOSURE_RULES",
    "applyG0FinancialExposure",
    "applyG0FinancialExposureForRun",
    "applyExposure",
    "applyRunExposure",
    "buildEnhancedFinancialFactor",
    "buildFinancialExposureForSignal",
    "buildFinancialExposureForSignalWithBasis",
    "buildExposure",
    "buildExposureWithBasis",
    "calcChannelScore",
    "calcConfidenceCap",
    "calcSourceBonus",
    "canApplyFinancialExposure",
    "calculateChannelScore",
    "checkIro",
    "confidenceMagnitudeCap",
    "dominantMagnitude",
    "ratioToMagnitude",
    "resolveDominant",
    "resolvePreferConsolidated",
    "resolveScope",
    "selectDenominator",
    "sourceTypeMagnitudeBonus",
]
