from typing import Optional
from src.models.dma_engine import FinancialFactor, ImpactFactor

def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))

def time_horizon_to_urgency(time_horizon: str) -> float:
    if time_horizon == "short": return 5.0
    if time_horizon == "mid": return 3.0
    if time_horizon == "long": return 1.0
    return 0.0

def calculate_impact_score(
    factor: ImpactFactor, 
    source_type: str = "news", 
    sub_issue_code: str = ""
) -> float:
    """
    환경/사회적 중대성(Impact) 요소를 기반으로 v3.2 산식에 따라 점수를 산출합니다.
    """
    if source_type == "regulation":
        if sub_issue_code == "공급망 관리" or "SUPPLY_CHAIN" in sub_issue_code:
            return 4.0
        elif sub_issue_code in ["기후변화", "온실가스 배출"] or "CLIMATE" in sub_issue_code:
            return 3.5
        elif sub_issue_code in ["데이터 보안", "개인정보 보호"] or "DATA_SECURITY" in sub_issue_code:
            return 3.0

    urgency = time_horizon_to_urgency(factor.time_horizon)
    likelihood = factor.likelihood if factor.likelihood else 0.0
    irremediability = factor.irremediability if factor.irremediability else 0.0
    scale = factor.scale
    scope = factor.scope

    if factor.impact_direction == "negative":
        score = (0.30 * scale) + (0.25 * scope) + (0.20 * likelihood) + (0.15 * irremediability) + (0.10 * urgency)
    else:
        # positive impact
        score = (0.35 * scale) + (0.30 * scope) + (0.25 * likelihood) + (0.10 * urgency)
        
    return clamp(score, 0.0, 5.0)

def calculate_financial_score(
    factor: FinancialFactor, 
    source_type: str = "news", 
    sub_issue_code: str = ""
) -> float:
    """
    재무적 중대성(Financial) 요소를 기반으로 v3.2 산식에 따라 점수를 산출합니다.
    """
    if source_type == "regulation":
        if sub_issue_code == "공급망 관리" or "SUPPLY_CHAIN" in sub_issue_code:
            return 4.0
        elif sub_issue_code in ["기후변화", "온실가스 배출"] or "CLIMATE" in sub_issue_code:
            return 3.5
        elif sub_issue_code in ["데이터 보안", "개인정보 보호"] or "DATA_SECURITY" in sub_issue_code:
            return 3.0

    magnitudes = [
        factor.revenue_magnitude,
        factor.cost_magnitude,
        factor.capex_magnitude,
        factor.asset_liability_magnitude,
        factor.financing_magnitude,
        factor.legal_regulatory_magnitude
    ]
    valid_mags = [m for m in magnitudes if m is not None]
    
    base_mag = float(max(valid_mags)) if valid_mags else 0.0
    urgency = time_horizon_to_urgency(factor.time_horizon)
    likelihood = factor.likelihood if factor.likelihood else 0.0
    
    if factor.financial_iro_type == "risk":
        score = (0.45 * base_mag) + (0.35 * likelihood) + (0.20 * urgency)
    else:
        # opportunity
        score = (0.55 * base_mag) + (0.25 * likelihood) + (0.20 * urgency)
        
    return clamp(score, 0.0, 5.0)

def score_dma_signals(signals: list) -> list:
    """
    DB 저장 직전에 호출되어 DMASignal 내 factor를 기반으로 점수를 계산하여 채워넣습니다.
    """
    for sig in signals:
        if sig.impact_factor:
            sig.impact_score_0_5 = calculate_impact_score(sig.impact_factor, sig.source_type, sig.sub_issue_code)
        if sig.financial_factor:
            sig.financial_score_0_5 = calculate_financial_score(sig.financial_factor, sig.source_type, sig.sub_issue_code)
    return signals
