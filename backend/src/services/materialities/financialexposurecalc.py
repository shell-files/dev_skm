from __future__ import annotations

from typing import Optional

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


def resolvePreferConsolidated(runContext: dict) -> tuple[bool, list]:
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
        from src.utils.typeutils import safeFloat as _safeFloat
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


def dominantMagnitude(magnitudes: dict) -> tuple[Optional[str], Optional[int]]:
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


def _financialIroToAllowedAxis(financialIroType: str) -> Optional[str]:
    normalized = str(financialIroType or "").lower()
    if normalized in {"risk", "financial_risk"}:
        return "financial_risk"
    if normalized in {"opportunity", "financial_opportunity"}:
        return "financial_opportunity"
    return None
