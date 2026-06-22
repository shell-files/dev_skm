<<<<<<< HEAD
"""
adapter.py
레이어: Service (medias)
역할: 미디어 AI 분석 결과를 DMASignal 객체로 변환.
"""
from typing import Any, List, Mapping, Optional, Sequence

from src.models.dmaengine import DMASignal, EvidenceSpanV13, ExtractedFactsV13
from src.utils.typeutils import firstPresent, asFloat


def buildEvidenceSpan(result: Mapping[str, Any]) -> List[EvidenceSpanV13]:
    """분석 결과 딕셔너리에서 텍스트 증거를 EvidenceSpanV13 리스트로 변환한다. 증거가 없으면 빈 리스트를 반환한다."""
=======
from typing import Any, List, Mapping, Optional, Sequence

from src.models.dmaengine import DMASignal, EvidenceSpanV13, ExtractedFactsV13


def firstPresent(row: Mapping[str, Any], keys: Sequence[str], default: Any = None) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return default


def asFloat(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def buildEvidenceSpan(result: Mapping[str, Any]) -> List[EvidenceSpanV13]:
>>>>>>> origin/skm_test
    chunk = firstPresent(result, ("chunk", "textSpan", "text_span", "evidence"))
    if not chunk:
        return []
    return [EvidenceSpanV13(
        textSpan=str(chunk),
        sourceType="news",
        sourceTitle=result.get("title"),
        sourceUrl=result.get("url"),
        publishedAt=result.get("publishedAt"),
        teCrawlingId=result.get("teCrawlingId") or result.get("te_crawling_id"),
    )]


def _resolveNewsProviderKey(result: Mapping[str, Any]) -> str:
    raw = result.get("source")
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    return "unknown"


def _sanitizeIssueSimilarityMatches(rawMatches) -> list:
    if not isinstance(rawMatches, list):
        return []
    sanitized = []
    for match in rawMatches:
        if not isinstance(match, Mapping):
            continue
        issueId = match.get("issueId")
        subIssueNameKr = match.get("subIssueNameKr")
        score = asFloat(match.get("score"))
        sanitized.append({
            "issueId": str(issueId) if issueId is not None and not isinstance(issueId, (dict, list, tuple, set)) else None,
            "subIssueNameKr": str(subIssueNameKr) if subIssueNameKr is not None and not isinstance(subIssueNameKr, (dict, list, tuple, set)) else None,
            "score": score,
        })
    return sanitized


def step0NormalizeMediaFacts(analysisResults: list) -> list[ExtractedFactsV13]:
<<<<<<< HEAD
    """뉴스 AI 분석 결과 목록을 ExtractedFactsV13 형식으로 정규화한다."""
=======
>>>>>>> origin/skm_test
    facts: list[ExtractedFactsV13] = []
    for result in analysisResults or []:
        if not isinstance(result, Mapping):
            raise ValueError("media news raw result must be a mapping")
        subIssueCode = firstPresent(result, ("bestSubIssueId", "subIssueCode", "sub_issue_code"))
        if not subIssueCode:
            raise ValueError("media news raw result subIssueCode is required")
        rawIssueLabel = firstPresent(result, ("rawIssueLabel", "title"), "")
        displayName = firstPresent(result, ("bestSubIssueNameKr", "displaySubIssueName", "display_sub_issue_name"))
        similarityScore = asFloat(firstPresent(result, ("bestSimilarityScore", "similarityScore", "similarity_score")))
        mappingWeight = asFloat(firstPresent(result, ("mappingWeight", "mapping_weight", "bestSimilarityScore")))
        metadata = {
            "rawIssueLabel": rawIssueLabel,
            "displaySubIssueName": displayName,
            "similarityScore": similarityScore,
            "mappingWeight": mappingWeight,
            "source": result.get("source"),
            "mediaExternalSourceType": "news",
            "providerKey": _resolveNewsProviderKey(result),
            "sourceUrl": result.get("url"),
            "publishedAt": result.get("publishedAt"),
            "issueSimilarityMatches": _sanitizeIssueSimilarityMatches(result.get("issueSimilarityMatches")),
        }
        facts.append(ExtractedFactsV13(
            subIssueCode=str(subIssueCode),
            sourceType="news",
            classificationConfidence=similarityScore,
            eventType=result.get("eventType"),
            impactDirection=result.get("impactDirection"),
            financialIroType=result.get("financialIroType"),
            actualYn=result.get("actualYn"),
            officialConfirmedYn=result.get("officialConfirmedYn"),
            explicitImmediateActionYn=result.get("explicitImmediateActionYn"),
            explicitNoUrgencyYn=result.get("explicitNoUrgencyYn"),
            affectedCount=result.get("affectedCount"),
            financialAmount=result.get("financialAmount"),
            ratioValue=result.get("ratioValue"),
            probabilityValue=result.get("probabilityValue"),
            eventDate=result.get("eventDate"),
            effectiveDate=result.get("effectiveDate"),
            deadlineDate=result.get("deadlineDate"),
            eventGroupCandidateId=result.get("eventGroupCandidateId"),
            evidenceSpans=buildEvidenceSpan(result),
            rawMetadata=metadata,
        ))
    return facts


<<<<<<< HEAD
# [레거시] 기존 미디어 → DMASignal 변환 경로. v1.3 오케스트레이터에서 사용 안 함.
# Phase C 런타임 마이그레이션 완료 후 삭제 예정.
=======
# LEGACY ONLY:
# Existing media -> DMASignal conversion path. Not called by the new v1.3 Orchestrator.
# Delete after Phase C Runtime Migration confirms import count is 0.
>>>>>>> origin/skm_test
def convertMediaToDmaSignals(analysisResults: list) -> list[DMASignal]:
    """
    미디어/언론 분석 결과를 DMASignal 객체 리스트로 변환합니다.
    """
    signalsToSave = []
    for res in analysisResults:
        sig = DMASignal(
            subIssueCode=res["bestSubIssueId"],
            sourceStep="media_external",
            sourceType="news",
            # bestSimilarityScore를 점수로 직접 쓰지 않고 confidence/mapping weight로 사용
            confidenceScore=res["bestSimilarityScore"],
            similarityScore=res["bestSimilarityScore"],
            mappingWeight=res["bestSimilarityScore"],
            displaySubIssueName=res["bestSubIssueNameKr"],
            evidenceSpans=[res["chunk"]] if res.get("chunk") else [],
            rawIssueLabel=res.get("title", ""),
            # 확장 메타데이터 (DB 보존용)
            sourceTitle=res.get("title", ""),
            sourceUrl=res.get("url", ""),
            publishedAt=res.get("publishedAt", ""),
            scoringPayloadJson={
                "source": res.get("source", ""),
                "issueSimilarityMatches": res.get("issueSimilarityMatches", [])
            }
        )
        signalsToSave.append(sig)
    return signalsToSave
