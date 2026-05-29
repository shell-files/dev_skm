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

from typing import Optional
from src.models.dmaengine import FinancialFactor, ImpactFactor

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
]
