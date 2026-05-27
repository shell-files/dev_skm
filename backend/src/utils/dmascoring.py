from typing import Optional
from src.models.dmaengine import FinancialFactor, ImpactFactor

def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))

def timeHorizonToUrgency(timeHorizon: str) -> float:
    if timeHorizon == "short": return 5.0
    if timeHorizon == "mid": return 3.0
    if timeHorizon == "long": return 1.0
    return 0.0

def calculateImpactScore(
    factor: ImpactFactor, 
    sourceType: str = "news", 
    subIssueCode: str = ""
) -> float:
    """
    환경/사회적 중대성(Impact) 요소를 기반으로 v3.2 산식에 따라 점수를 산출합니다.
    """
    if sourceType == "regulation":
        if "SUPPLY_CHAIN" in subIssueCode:
            return 4.0
        elif "CLIMATE" in subIssueCode:
            return 3.5
        elif "DATA_SECURITY" in subIssueCode:
            return 3.0

    urgency = timeHorizonToUrgency(factor.timeHorizon)
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

def calculateFinancialScore(
    factor: FinancialFactor, 
    sourceType: str = "news", 
    subIssueCode: str = ""
) -> float:
    """
    재무적 중대성(Financial) 요소를 기반으로 v3.2 산식에 따라 점수를 산출합니다.
    """
    if sourceType == "regulation":
        if "SUPPLY_CHAIN" in subIssueCode:
            return 4.0
        elif "CLIMATE" in subIssueCode:
            return 3.5
        elif "DATA_SECURITY" in subIssueCode:
            return 3.0

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
        score = (0.45 * base_mag) + (0.35 * likelihood) + (0.20 * urgency)
    else:
        # opportunity
        score = (0.55 * base_mag) + (0.25 * likelihood) + (0.20 * urgency)
        
    return clamp(score, 0.0, 5.0)

def scoreDmaSignals(signals: list) -> list:
    """
    DB 저장 직전에 추출되어 DMASignal 의 factor를 기반으로 점수를 계산하여 채워넣습니다.
    """
    for sig in signals:
        if sig.impactFactor:
            sig.impactScore05 = calculateImpactScore(sig.impactFactor, sig.sourceType, sig.subIssueCode)
        if sig.financialFactor:
            sig.financialScore05 = calculateFinancialScore(sig.financialFactor, sig.sourceType, sig.subIssueCode)
    return signals
