"""
Benchmark Adapter (v1 Freeze)

AI가 반환한 분석 결과를 DMASignal 객체로 변환합니다.
AI가 반환한 iroHint는 isAllowedIro()로 검증하며,
scoring_axis_allowed에 없는 iroHint는 scoring 가능한 4개 IRO 중 허용된 값으로 대체합니다.
허용된 scoring IRO가 없으면 해당 축의 factor는 생성하지 않습니다.
"""

from typing import Optional, List
from src.models.dmaengine import DMASignal
from src.utils.subissuemaster import isAllowedIro, getScoringAllowedIros

def _validateIroHint(subIssueCode: str, iroHint: str) -> Optional[str]:
    """
    AI가 반환한 iroHint를 검증합니다.
    1. isAllowedIro()로 허용 여부 확인
    2. 불허 시 getScoringAllowedIros()에서 같은 축의 허용 값으로 대체
    3. 대체 불가 시 None 반환 (호출부에서 factor 제거)
    """
    if isAllowedIro(subIssueCode, iroHint):
        return iroHint
    
    # scoring 가능한 허용 IRO 목록에서 대체 시도
    allowedIros = getScoringAllowedIros(subIssueCode)
    
    if not allowedIros:
        return None  # 허용된 scoring IRO가 없으면 None 반환 → 호출부에서 factor 제거
    
    # 같은 축 내에서 대체 시도
    impactIros = {"negative_impact", "positive_impact"}
    financialIros = {"financial_risk", "financial_opportunity"}
    
    if iroHint in impactIros:
        for candidate in allowedIros:
            if candidate in impactIros:
                return candidate
    elif iroHint in financialIros:
        for candidate in allowedIros:
            if candidate in financialIros:
                return candidate
    
    # 같은 축에 대체 IRO가 없으면 None 반환 → 호출부에서 factor 제거
    return None

def convertToDmaSignals(resultList: list, fileId: Optional[int]) -> list[DMASignal]:
    """
    분석 결과를 DMASignal 객체 리스트로 변환한다.
    입력 result는 camelCase만 허용한다.
    AI가 반환한 iroHint는 isAllowedIro로 검증 후 적용한다.
    """
    signalsToSave = []

    for result in resultList:
        try:
            signalPayload = dict(result)
            signalPayload["teSrFileId"] = fileId
            
            # AI의 iroHint 검증 (subIssueCode가 있는 경우)
            subIssueCode = signalPayload.get("subIssueCode", "")
            if subIssueCode and "impactFactor" in signalPayload and signalPayload["impactFactor"]:
                impactDir = signalPayload["impactFactor"].get("impactDirection", "negative")
                iroHint = "negative_impact" if impactDir == "negative" else "positive_impact"
                validatedIro = _validateIroHint(subIssueCode, iroHint)
                # 검증 결과가 impact 축이 아니면 factor 제거
                if validatedIro is None or validatedIro not in {"negative_impact", "positive_impact"}:
                    signalPayload["impactFactor"] = None
                else:
                    signalPayload["impactFactor"]["impactDirection"] = "negative" if validatedIro == "negative_impact" else "positive"
            
            if subIssueCode and "financialFactor" in signalPayload and signalPayload["financialFactor"]:
                finType = signalPayload["financialFactor"].get("financialIroType", "risk")
                iroHint = "financial_risk" if finType == "risk" else "financial_opportunity"
                validatedIro = _validateIroHint(subIssueCode, iroHint)
                if validatedIro is None or validatedIro not in {"financial_risk", "financial_opportunity"}:
                    signalPayload["financialFactor"] = None
                else:
                    signalPayload["financialFactor"]["financialIroType"] = "risk" if validatedIro == "financial_risk" else "opportunity"

            signal = DMASignal(**signalPayload)
            signalsToSave.append(signal)
        except Exception as error:
            print(f"DMASignal parse error: {error}")

    return signalsToSave
