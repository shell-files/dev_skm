from __future__ import annotations

from typing import Optional

from src.models.materiality import (
    BenchmarkObservationIssueDto,
    CoverageDto,
    CoverageSummaryDto,
    MaterialityResultItemDto,
    MatrixItemDto,
    SelectionReasonDto,
    TopIssueDto,
)
from src.repositories.dmarepository import listSelectedSubIssues
from src.utils.dmaaggregator import getCoverageStatus
from src.utils.subissuemaster import getSubIssueMeta, subissueMaster
from src.utils.typeutils import safeFloat as _safeFloat, safeInt as _safeInt


SELECTED_TOP_N = 5
MATRIX_TOP_N = 10
HIGH_PRIORITY_THRESHOLD_10 = 7.0
MVP_SURVEY_TARGETS = {
    "employee": 150,
    "management": 20,
    "external": 80,
}
GROUP_LABELS = {
    "employee": "임직원",
    "management": "경영진",
    "external": "외부 이해관계자",
}
MEDIA_SOURCE_LABELS = {
    "news": "언론 기사",
    "agency": "전문기관 자료",
    "regulation": "규제 프레임",
}
MEDIA_SOURCE_METHODS = {
    "news": "실제 기사 기반",
    "agency": "고가중치 전문 정보",
    "regulation": "고정 Rule Base",
}
BENCHMARK_SOURCE_TYPES = ["leader_sr", "peer_sr", "own_sr"]
MEDIA_SOURCE_TYPES = ["news", "agency", "regulation"]


def buildResultItem(row: dict, selectedCodes: list) -> MaterialityResultItemDto:
    code = row.get("sub_issue_code", "")
    benchImp = _safeFloat(row.get("benchmark_impact_score"))
    benchFin = _safeFloat(row.get("benchmark_financial_score"))
    mediaImp = _safeFloat(row.get("media_external_impact_score"))
    mediaFin = _safeFloat(row.get("media_external_financial_score"))
    surveyImp = _safeFloat(row.get("survey_impact_score"))
    surveyFin = _safeFloat(row.get("survey_financial_score"))
    finalImp = _safeFloat(row.get("final_impact_score"))
    finalFin = _safeFloat(row.get("final_financial_score"))
    finalScore = _safeFloat(row.get("final_score"))
    rankNo = _safeInt(row.get("rank_no"))
    finalImp10 = toScore10(finalImp)
    finalFin10 = toScore10(finalFin)

    return MaterialityResultItemDto(
        **subIssueBase(
            code,
            rankNo=rankNo,
            selectedYn=code in selectedCodes,
            quadrant=_quadrant(finalImp10, finalFin10),
        ),
        benchmarkImpactScore05=benchImp,
        benchmarkImpactScore10=toScore10(benchImp),
        benchmarkFinancialScore05=benchFin,
        benchmarkFinancialScore10=toScore10(benchFin),
        mediaImpactScore05=mediaImp,
        mediaImpactScore10=toScore10(mediaImp),
        mediaFinancialScore05=mediaFin,
        mediaFinancialScore10=toScore10(mediaFin),
        surveyImpactScore05=surveyImp,
        surveyImpactScore10=toScore10(surveyImp),
        surveyFinancialScore05=surveyFin,
        surveyFinancialScore10=toScore10(surveyFin),
        finalImpactScore05=finalImp,
        finalImpactScore10=finalImp10,
        finalFinancialScore05=finalFin,
        finalFinancialScore10=finalFin10,
        finalScore05=finalScore,
        finalScore10=toScore10(finalScore),
        coverage=_buildCoverage(benchImp, benchFin, mediaImp, mediaFin, surveyImp, surveyFin),
    )


def buildMatrixItem(item: MaterialityResultItemDto) -> MatrixItemDto:
    return MatrixItemDto(
        subIssueCode=item.subIssueCode,
        displaySubIssueName=item.displaySubIssueName,
        domain=item.domain,
        issueGroup=item.issueGroup,
        issueGroupCode=item.issueGroupCode,
        xFinancialScore10=item.finalFinancialScore10,
        yImpactScore10=item.finalImpactScore10,
        finalScore10=item.finalScore10,
        rankNo=item.rankNo,
        selectedYn=item.selectedYn,
        quadrant=item.quadrant,
    )


def buildTopIssues(items: list, selectedCodes: list) -> list:
    byCode = {item.subIssueCode: item for item in items}
    selectedItems = [byCode[code] for code in selectedCodes if code in byCode]
    if not selectedItems:
        selectedItems = [item for item in items if item.finalScore05 is not None][:SELECTED_TOP_N]

    topIssues = []
    for pageIndex, item in enumerate(selectedItems[:SELECTED_TOP_N], start=1):
        meta = getSubIssueMeta(item.subIssueCode)
        topIssues.append(
            TopIssueDto(
                subIssueCode=item.subIssueCode,
                displaySubIssueName=item.displaySubIssueName,
                domain=item.domain,
                issueGroup=item.issueGroup,
                issueGroupCode=item.issueGroupCode,
                rankNo=item.rankNo,
                selectedYn=item.selectedYn,
                quadrant=item.quadrant,
                finalImpactScore05=item.finalImpactScore05,
                finalImpactScore10=item.finalImpactScore10,
                finalFinancialScore05=item.finalFinancialScore05,
                finalFinancialScore10=item.finalFinancialScore10,
                finalScore05=item.finalScore05,
                finalScore10=item.finalScore10,
                summary=meta.get("sentence"),
                reportPage=pageIndex,
                coverage=item.coverage,
            )
        )
    return topIssues


def buildCoverageSummary(items: list) -> CoverageSummaryDto:
    counts = {"FULL": 0, "PARTIAL": 0, "LIMITED": 0, "NO_DATA": 0}
    for item in items:
        observedCount = sum([item.coverage.benchmarkObserved, item.coverage.mediaObserved, item.coverage.surveyObserved])
        counts[getCoverageStatus(observedCount)] += 1
    return CoverageSummaryDto(
        fullCount=counts["FULL"],
        partialCount=counts["PARTIAL"],
        limitedCount=counts["LIMITED"],
        noDataCount=counts["NO_DATA"],
    )


def resolveSelectedContext(runId: int, rows: list) -> dict:
    selectedRows = listSelectedSubIssues(runId)
    if selectedRows:
        selectedCodes = [row["sub_issue_code"] for row in selectedRows if row.get("sub_issue_code")][:SELECTED_TOP_N]
        return {
            "selectionSource": "TABLE",
            "fallbackYn": False,
            "selectedCodes": selectedCodes,
            "selectedRows": selectedRows,
        }

    rankedRows = [row for row in rows if row.get("rank_no") is not None and row.get("final_score") is not None]
    selectedCodes = [row["sub_issue_code"] for row in rankedRows[:SELECTED_TOP_N] if row.get("sub_issue_code")]
    return {
        "selectionSource": "RANK_FALLBACK",
        "fallbackYn": True,
        "selectedCodes": selectedCodes,
        "selectedRows": [],
    }


def buildSelectionReasons(selectedContext: dict, items: list) -> list:
    byCode = {item.subIssueCode: item for item in items}
    selectedRowsByCode = {row.get("sub_issue_code"): row for row in selectedContext.get("selectedRows", [])}
    reasons = []
    for code in selectedContext["selectedCodes"]:
        item = byCode.get(code)
        if not item:
            base = subIssueBase(code, selectedYn=True)
            rankNo = None
            displayName = base["displaySubIssueName"]
        else:
            rankNo = item.rankNo
            displayName = item.displaySubIssueName
        tableRow = selectedRowsByCode.get(code, {})
        reasons.append(
            SelectionReasonDto(
                subIssueCode=code,
                displaySubIssueName=displayName,
                rankNo=rankNo,
                selectedYn=True,
                selectionType=tableRow.get("selection_type") or "rank_based",
                selectionReason=tableRow.get("selection_reason") or "최종 점수 상위 이슈로 MVP 기본 선정되었습니다.",
                selectionSource=selectedContext["selectionSource"],
                fallbackYn=selectedContext["fallbackYn"],
            )
        )
    return reasons


def buildObservationMap(rows: list) -> dict:
    observations = {}
    for row in rows:
        code = row.get("sub_issue_code")
        sourceType = row.get("source_type")
        if not code or not sourceType:
            continue
        observations.setdefault(code, {})
        observations[code][sourceType] = {
            "signalCount": int(row.get("signal_count") or 0),
            "evidenceCount": int(row.get("evidence_count") or 0),
        }
    return observations


def buildEvidenceSourceCounts(rows: list) -> dict:
    result = {}
    for row in rows:
        sourceType = row.get("source_type")
        if not sourceType:
            continue
        result[sourceType] = {
            "evidenceCount": int(row.get("evidence_count") or 0),
            "reportCount": int(row.get("report_count") or 0),
        }
    return result


def buildBenchmarkObservationIssue(code: str, obs: dict) -> BenchmarkObservationIssueDto:
    return BenchmarkObservationIssueDto(
        **subIssueBase(code),
        leaderObserved=isObserved(obs, "leader_sr"),
        peerObserved=isObserved(obs, "peer_sr"),
        ownObserved=isObserved(obs, "own_sr"),
        leaderEvidenceCount=int(obs.get("leader_sr", {}).get("evidenceCount", 0)),
        peerEvidenceCount=int(obs.get("peer_sr", {}).get("evidenceCount", 0)),
        ownEvidenceCount=int(obs.get("own_sr", {}).get("evidenceCount", 0)),
    )


def buildSurveyGroupScoreMap(rows: list) -> dict:
    result = {}
    for row in rows:
        code = row.get("sub_issue_code")
        group = row.get("respondent_group")
        mappedAxis = row.get("mapped_axis")
        if not code or not group or not mappedAxis:
            continue
        result.setdefault(code, {})
        result[code].setdefault(group, {})
        result[code][group][mappedAxis] = row.get("avg_score")
    return result


def subIssueBase(
    code: str,
    rankNo: Optional[int] = None,
    selectedYn: bool = False,
    quadrant: Optional[str] = None,
) -> dict:
    meta = getSubIssueMeta(code)
    return {
        "subIssueCode": code,
        "displaySubIssueName": meta.get("subIssueNameKr") or code,
        "domain": meta.get("domain"),
        "issueGroup": meta.get("issueGroupNameKr") or meta.get("issueGroup"),
        "issueGroupCode": meta.get("issueGroup"),
        "rankNo": rankNo,
        "selectedYn": selectedYn,
        "quadrant": quadrant,
    }


def subIssueSortKey(code: str):
    meta = getSubIssueMeta(code)
    return (meta.get("domain", ""), meta.get("issueGroup", ""), meta.get("subIssueSort", 999), code)


def isObserved(obs: dict, sourceType: str) -> bool:
    return int(obs.get(sourceType, {}).get("signalCount", 0)) > 0


def toScore10(score05) -> Optional[float]:
    value = _safeFloat(score05)
    if value is None:
        return None
    return round(value * 2, 2)


def rate(value: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return round((value / total) * 100, 1)


def _buildCoverage(
    benchImp: Optional[float],
    benchFin: Optional[float],
    mediaImp: Optional[float],
    mediaFin: Optional[float],
    surveyImp: Optional[float],
    surveyFin: Optional[float],
) -> CoverageDto:
    impactStages = []
    financialStages = []
    if benchImp is not None:
        impactStages.append("benchmark")
    if mediaImp is not None:
        impactStages.append("media_external")
    if surveyImp is not None:
        impactStages.append("survey")
    if benchFin is not None:
        financialStages.append("benchmark")
    if mediaFin is not None:
        financialStages.append("media_external")
    if surveyFin is not None:
        financialStages.append("survey")

    return CoverageDto(
        impactObservedStages=impactStages,
        financialObservedStages=financialStages,
        impactCoverageStatus=getCoverageStatus(len(impactStages)),
        financialCoverageStatus=getCoverageStatus(len(financialStages)),
        benchmarkObserved=benchImp is not None or benchFin is not None,
        mediaObserved=mediaImp is not None or mediaFin is not None,
        surveyObserved=surveyImp is not None or surveyFin is not None,
    )


def _quadrant(impactScore10: Optional[float], financialScore10: Optional[float]) -> str:
    if impactScore10 is None or financialScore10 is None:
        return "NO_DATA"
    impactHigh = impactScore10 >= HIGH_PRIORITY_THRESHOLD_10
    financialHigh = financialScore10 >= HIGH_PRIORITY_THRESHOLD_10
    if impactHigh and financialHigh:
        return "HIGH_IMPACT_HIGH_FINANCIAL"
    if impactHigh:
        return "HIGH_IMPACT_LOW_FINANCIAL"
    if financialHigh:
        return "LOW_IMPACT_HIGH_FINANCIAL"
    return "LOW_IMPACT_LOW_FINANCIAL"
