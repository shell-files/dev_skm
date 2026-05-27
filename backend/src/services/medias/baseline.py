from src.models.dmaengine import ImpactFactor, FinancialFactor

MEDIA_BASELINE_BY_SUB_ISSUE = {
    "E_CLIMATE__CLIMATE_TARGETS_TRANSITION": {
        "impact": ImpactFactor(impactDirection="negative", actuality="potential", scale=4, scope=4, timeHorizon="mid"),
        "financial": FinancialFactor(financialIroType="risk", timeHorizon="mid", revenueMagnitude=4, likelihood=4)
    },
    "S_SUPPLY_CHAIN_SOCIAL__SUPPLIER_RISK_AUDIT_CAP": {
        "impact": ImpactFactor(impactDirection="negative", actuality="actual", scale=4, scope=3, timeHorizon="short"),
        "financial": FinancialFactor(financialIroType="risk", timeHorizon="short", costMagnitude=3, likelihood=3)
    },
    "S_TALENT__TRAINING_DEVELOPMENT": {
        "impact": ImpactFactor(impactDirection="positive", actuality="actual", scale=3, scope=3, timeHorizon="mid"),
        "financial": FinancialFactor(financialIroType="opportunity", timeHorizon="long", revenueMagnitude=2, likelihood=3)
    },
    "E_PRODUCT_ENV__PRODUCT_ENV_PERFORMANCE": {
        "impact": ImpactFactor(impactDirection="positive", actuality="potential", scale=4, scope=5, timeHorizon="long"),
        "financial": FinancialFactor(financialIroType="opportunity", timeHorizon="mid", revenueMagnitude=4, likelihood=3)
    },
    "S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY": {
        "impact": ImpactFactor(impactDirection="negative", actuality="actual", scale=5, scope=4, timeHorizon="short"),
        "financial": FinancialFactor(financialIroType="risk", timeHorizon="short", legalRegulatoryMagnitude=5, likelihood=4)
    }
}

def applyMediaBaseline(signals: list) -> list:
    """
    미디어/언론 전용 factor baseline을 적용합니다.
    """
    for sig in signals:
        baseline = MEDIA_BASELINE_BY_SUB_ISSUE.get(sig.subIssueCode)
        if baseline:
            sig.impactFactor = baseline["impact"]
            sig.financialFactor = baseline["financial"]
        else:
            sig.impactFactor = ImpactFactor(impactDirection="negative", actuality="potential", scale=3, scope=3, timeHorizon="mid")
            sig.financialFactor = FinancialFactor(financialIroType="risk", timeHorizon="mid", likelihood=3)
    return signals
