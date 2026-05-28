"""
미디어/언론 전용 Factor Baseline (v1 Freeze)

sourceType별 factor 생성 규칙:
- news: embedding similarity → baseline factor + keyword hint
- regulation: 고정 rule 우선 (향후 regulations/baseline.py로 이관 후 독립)
- agency: 자료 유형 rule 우선

IRO 결정 우선순위:
1순위: sourceType별 hard rule
2순위: subissuemaster.py의 scoring_axis_allowed (isAllowedIro)
3순위: 이 파일의 subIssue별 기본 factor
4순위: AI/keyword hint

bestSimilarityScore는 impact/financial 점수로 직접 쓰지 않습니다.
bestSimilarityScore → confidenceScore / mappingWeight로만 사용합니다.
실제 0~5 점수는 dmascoring.py가 factor 기반으로 계산합니다.
"""

from src.models.dmaengine import ImpactFactor, FinancialFactor
from src.utils.subissuemaster import getScoringAllowedIros

# ──────────────────────────────────────────────
# subIssue별 사전 정의 baseline factor
# 향후 62개 전체로 확장 예정
# ──────────────────────────────────────────────

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

# ──────────────────────────────────────────────
# IRO 결정 로직
# ──────────────────────────────────────────────

def _resolveIroDirection(subIssueCode: str) -> dict:
    """
    subIssue의 scoring_axis_allowed 중 scoring 가능한 4개 IRO를 기반으로
    impact direction과 financial iro type을 결정합니다.
    
    scoring 가능한 IRO: negative_impact, positive_impact, financial_risk, financial_opportunity
    허용된 IRO가 없으면 해당 축은 None으로 반환합니다.
    """
    allowed = getScoringAllowedIros(subIssueCode)
    
    result = {
        "impactDirection": None,
        "financialIroType": None
    }
    
    # Impact 축 결정
    if "negative_impact" in allowed:
        result["impactDirection"] = "negative"
    elif "positive_impact" in allowed:
        result["impactDirection"] = "positive"
    
    # Financial 축 결정
    if "financial_risk" in allowed:
        result["financialIroType"] = "risk"
    elif "financial_opportunity" in allowed:
        result["financialIroType"] = "opportunity"
    
    return result

def applyMediaBaseline(signals: list) -> list:
    """
    미디어/언론 전용 factor baseline을 적용합니다.
    isAllowedIro 검증을 거쳐 허용된 축만 factor를 생성합니다.
    """
    for sig in signals:
        baseline = MEDIA_BASELINE_BY_SUB_ISSUE.get(sig.subIssueCode)
        
        if baseline:
            # 사전 정의된 baseline이 있으면 그대로 사용하되, IRO 허용 여부 검증
            iroResolved = _resolveIroDirection(sig.subIssueCode)
            
            if iroResolved["impactDirection"] is not None:
                sig.impactFactor = baseline["impact"]
            else:
                sig.impactFactor = None
                
            if iroResolved["financialIroType"] is not None:
                sig.financialFactor = baseline["financial"]
            else:
                sig.financialFactor = None
        else:
            # 사전 정의 baseline이 없는 subIssue → scoring_axis_allowed 기반 fallback
            iroResolved = _resolveIroDirection(sig.subIssueCode)
            
            if iroResolved["impactDirection"] is not None:
                sig.impactFactor = ImpactFactor(
                    impactDirection=iroResolved["impactDirection"],
                    actuality="potential",
                    scale=3, scope=3,
                    timeHorizon="mid"
                )
            else:
                sig.impactFactor = None
                
            if iroResolved["financialIroType"] is not None:
                sig.financialFactor = FinancialFactor(
                    financialIroType=iroResolved["financialIroType"],
                    timeHorizon="mid",
                    likelihood=3
                )
            else:
                sig.financialFactor = None
                
    return signals
