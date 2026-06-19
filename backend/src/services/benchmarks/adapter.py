"""
adapter.py
레이어: Service (benchmarks)
역할: 벤치마크 AI 분석 결과를 DMASignal 객체로 변환 (v1 Freeze).
  iroHint 검증: scoring_axis_allowed 없으면 허용 IRO 대체값 사용, 없으면 factor 제외.
"""

from typing import Any, List, Mapping, Optional, Sequence

from src.models.dmaengine import DMASignal, EvidenceSpanV13, ExtractedFactsV13
from src.utils.subissuemaster import isAllowedIro, getScoringAllowedIros
from src.utils.typeutils import firstPresent, asFloat


def buildEvidenceSpans(rawSpans: Any, sourceType: Optional[str]) -> List[EvidenceSpanV13]:
    """raw 증거 스팬 데이터를 EvidenceSpanV13 목록으로 정규화한다."""
    if rawSpans is None:
        return []
    if isinstance(rawSpans, (str, bytes)):
        values = [rawSpans]
    else:
        values = list(rawSpans) if isinstance(rawSpans, list) else [rawSpans]
    spans: List[EvidenceSpanV13] = []
    for item in values:
        if isinstance(item, Mapping):
            text = firstPresent(item, ("textSpan", "text_span", "text", "chunk", "evidence"), "")
            if not text:
                continue
            spans.append(EvidenceSpanV13(
                textSpan=str(text),
                sourceType=item.get("sourceType") or item.get("source_type") or sourceType,
                sourceTitle=item.get("sourceTitle") or item.get("source_title"),
                sourceUrl=item.get("sourceUrl") or item.get("source_url"),
                sourcePageNo=item.get("sourcePageNo") or item.get("source_page_no"),
                publishedAt=item.get("publishedAt") or item.get("published_at"),
            ))
        elif item:
            spans.append(EvidenceSpanV13(textSpan=str(item), sourceType=sourceType))
    return spans


def sanitizeMetadata(value: Any, forbiddenFields: set[str]) -> Any:
    """중첩 구조에서 금지 필드를 재귀적으로 제거해 AI 정책 준수 메타데이터를 반환한다."""
    if isinstance(value, Mapping):
        return {
            key: sanitizeMetadata(child, forbiddenFields)
            for key, child in value.items()
            if key not in forbiddenFields
        }
    if isinstance(value, list):
        return [sanitizeMetadata(item, forbiddenFields) for item in value]
    return value


def step0NormalizeBenchmarkFacts(
    resultList: list,
    fileId: Optional[int],
    sourceType: Optional[str],
    aiPolicy: Mapping[str, Any],
) -> list[ExtractedFactsV13]:
    """벤치마크 AI 분석 결과를 검증하고 금지 필드를 제거해 ExtractedFactsV13 목록으로 변환한다."""
    forbiddenFields = set(aiPolicy["forbiddenFields"])
    facts: list[ExtractedFactsV13] = []
    for result in resultList or []:
        if not isinstance(result, Mapping):
            raise ValueError("benchmark raw result must be a mapping")
        subIssueCode = firstPresent(result, ("subIssueCode", "sub_issue_code", "bestSubIssueId", "best_sub_issue_id"))
        if not subIssueCode:
            raise ValueError("benchmark raw result subIssueCode is required")
        resolvedSourceType = sourceType or firstPresent(result, ("sourceType", "source_type"), "benchmark")
        rawIssueLabel = firstPresent(result, ("rawIssueLabel", "raw_issue_label", "issueLabel", "title"), "")
        displayName = firstPresent(
            result,
            ("displaySubIssueName", "display_sub_issue_name", "bestSubIssueNameKr", "subIssueName"),
        )
        spans = buildEvidenceSpans(firstPresent(result, ("evidenceSpans", "evidence_spans", "chunk"), []), resolvedSourceType)
        metadata = {
            "teSrFileId": fileId,
            "rawIssueLabel": rawIssueLabel,
            "displaySubIssueName": displayName,
            "sourceType": resolvedSourceType,
            "originalResult": sanitizeMetadata(dict(result), forbiddenFields),
        }
        facts.append(ExtractedFactsV13(
            subIssueCode=str(subIssueCode),
            sourceType=str(resolvedSourceType),
            classificationConfidence=asFloat(firstPresent(
                result,
                ("classificationConfidence", "classification_confidence", "confidenceScore", "similarityScore"),
            )),
            evidenceSpans=spans,
            rawMetadata=metadata,
        ))
    return facts

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


# [레거시] 기존 벤치마크 → DMASignal 변환 경로. v1.3 오케스트레이터에서 사용 안 함.
# Phase C 런타임 마이그레이션 완료 후 삭제 예정.
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
