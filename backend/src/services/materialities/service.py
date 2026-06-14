from decimal import Decimal
from typing import Optional

from src.models.materiality import (
    BenchmarkObservationIssueDto,
    BenchmarkResponseDto,
    BenchmarkSummaryDto,
    BenchmarkTopIssueDto,
    CoverageDto,
    CoverageSummaryDto,
    EvidenceSampleDto,
    FinalizeSelectedSubIssueItemDto,
    FinalizeSelectedSubIssuesResponseDto,
    MaterialityResultItemDto,
    MaterialityResultsResponseDto,
    MatrixItemDto,
    MediaStageResponseDto,
    MediaSummaryDto,
    MediaTopIssueDto,
    NextStepDto,
    SelectionProcessResponseDto,
    SelectionReasonDto,
    SourceBreakdownDto,
    SurveyGroupBreakdownDto,
    SurveyResponseDto,
    SurveySummaryDto,
    SurveyTopIssueDto,
    TopIssueDto,
)
from src.utils.db import findAll, findOne
from src.utils.dmaaggregator import getCoverageStatus
from src.utils.dmarepository import (
    countObservedSubIssues,
    listResults,
    listEvidenceCounts,
    listEvidenceSamples,
    getLatestReportRun,
    getMediaCoverage,
    countMediaSubIssues,
    countMissingMetrics,
    countRequiredMetrics,
    listFinalTopSubIssues,
    listSelectedSubIssues,
    listSignalCounts,
    listSurveyCounts,
    listSurveyScores,
    listTopStageIssues,
    replaceSelectedSubIssuesTx,
)
from src.utils.subissuemaster import getSubIssueMeta, subissueMaster


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


def getMaterialityResults(runId: int) -> MaterialityResultsResponseDto:
    rows = listResults(runId)
    selectedContext = _resolveSelectedContext(runId, rows)
    selectedCodes = selectedContext["selectedCodes"]

    items = [_buildResultItem(row, selectedCodes) for row in rows]
    scoredItems = [item for item in items if item.finalScore05 is not None]
    matrixItems = [_buildMatrixItem(item) for item in scoredItems[:MATRIX_TOP_N]]
    topItems = _buildTopIssues(items, selectedCodes)
    highPriorityCount = sum(1 for item in matrixItems if item.quadrant == "HIGH_IMPACT_HIGH_FINANCIAL")
    selectionReasons = _buildSelectionReasons(selectedContext, items)

    requiredMetricCount = countRequiredMetrics(selectedCodes)
    onboardingMissingCount = countMissingMetrics(runId, selectedCodes)
    reportRun = getLatestReportRun(runId)
    reportRunId = int(reportRun["id"]) if reportRun.get("id") is not None else None
    reportDraftReadyYn = (
        bool(selectedCodes)
        and selectedContext.get("selectionSource") == "TABLE"
        and not bool(selectedContext.get("fallbackYn"))
        and requiredMetricCount > 0
        and onboardingMissingCount == 0
    )

    nextStep = NextStepDto(
        selectedIssueCount=len(selectedCodes),
        requiredMetricCount=requiredMetricCount,
        onboardingMissingCount=onboardingMissingCount,
        reportDraftReadyYn=reportDraftReadyYn,
        reportRunId=reportRunId,
        nextAction="OPEN_REPORT_DRAFT" if reportRunId else "GENERATE_REPORT_DRAFT",
        selectionSource=selectedContext["selectionSource"],
        fallbackYn=selectedContext["fallbackYn"],
    )

    return MaterialityResultsResponseDto(
        runId=runId,
        totalCandidateSubIssueCount=len(subissueMaster),
        summaryRowCount=len(items),
        scoredSubIssueCount=len(scoredItems),
        selectedSubIssueCount=len(selectedCodes),
        highPriorityCount=highPriorityCount,
        selectionSource=selectedContext["selectionSource"],
        fallbackYn=selectedContext["fallbackYn"],
        items=items,
        matrixItems=matrixItems,
        topIssues=topItems,
        selectionReasons=selectionReasons,
        nextStep=nextStep,
        coverageSummary=_buildCoverageSummary(items),
    )


def getBenchmarkResult(runId: int) -> BenchmarkResponseDto:
    evidenceCounts = listEvidenceCounts(runId, "benchmark")
    observationRows = listSignalCounts(runId, "benchmark")
    observations = _buildObservationMap(observationRows)
    sourceCounts = _buildEvidenceSourceCounts(evidenceCounts)

    leaderReportCount = sourceCounts.get("leader_sr", {}).get("reportCount", 0)
    peerReportCount = sourceCounts.get("peer_sr", {}).get("reportCount", 0)
    ownReportCount = sourceCounts.get("own_sr", {}).get("reportCount", 0)
    analyzedReportCount = leaderReportCount + peerReportCount + ownReportCount
    if analyzedReportCount == 0:
        analyzedReportCount = sum(sourceCounts.get(sourceType, {}).get("evidenceCount", 0) for sourceType in BENCHMARK_SOURCE_TYPES)

    commonIssues = []
    blindSpotIssues = []
    for code in sorted(observations.keys(), key=_subIssueSortKey):
        issue = _buildBenchmarkObservationIssue(code, observations[code])
        if issue.leaderObserved and issue.peerObserved:
            commonIssues.append(issue)
        if issue.leaderObserved and issue.peerObserved and not issue.ownObserved:
            issue.blindSpotYn = True
            issue.summary = "리더/피어 보고서에서 반복 관측되었으나 자사 보고서에서는 관측되지 않은 이슈입니다."
            blindSpotIssues.append(issue)

    topIssues = []
    for index, row in enumerate(listTopStageIssues(runId, "benchmark", limit=SELECTED_TOP_N), start=1):
        code = row.get("sub_issue_code", "")
        obs = observations.get(code, {})
        topIssues.append(
            BenchmarkTopIssueDto(
                **_subIssueBase(code, rankNo=index),
                benchmarkImpactScore05=_safeFloat(row.get("impact_score")),
                benchmarkImpactScore10=_toScore10(row.get("impact_score")),
                benchmarkFinancialScore05=_safeFloat(row.get("financial_score")),
                benchmarkFinancialScore10=_toScore10(row.get("financial_score")),
                benchmarkAvgScore05=_safeFloat(row.get("avg_score")),
                benchmarkAvgScore10=_toScore10(row.get("avg_score")),
                leaderObserved=_isObserved(obs, "leader_sr"),
                peerObserved=_isObserved(obs, "peer_sr"),
                ownObserved=_isObserved(obs, "own_sr"),
                evidenceCount=sum(int(v.get("evidenceCount", 0)) for v in obs.values()),
            )
        )

    summary = BenchmarkSummaryDto(
        analyzedReportCount=analyzedReportCount,
        leaderReportCount=leaderReportCount,
        peerReportCount=peerReportCount,
        ownReportCount=ownReportCount,
        identifiedIssueCount=countObservedSubIssues(runId, "benchmark"),
        commonIssueCount=len(commonIssues),
        blindSpotCount=len(blindSpotIssues),
    )

    return BenchmarkResponseDto(
        runId=runId,
        summary=summary,
        topIssues=topIssues,
        commonIssues=commonIssues,
        blindSpotIssues=blindSpotIssues,
        evidenceSummary={
            "sourceCounts": sourceCounts,
            "sourceStep": "benchmark",
            "implementationStatus": "READY_WITH_GRACEFUL_EMPTY",
        },
    )


def getMediaResult(runId: int) -> MediaStageResponseDto:
    evidenceCounts = listEvidenceCounts(runId, "media_external")
    observationRows = listSignalCounts(runId, "media_external")
    observations = _buildObservationMap(observationRows)
    sourceCounts = _buildEvidenceSourceCounts(evidenceCounts)

    sourceBreakdown = []
    for sourceType in MEDIA_SOURCE_TYPES:
        sourceObservationCount = sum(1 for item in observations.values() if _isObserved(item, sourceType))
        sourceBreakdown.append(
            SourceBreakdownDto(
                sourceType=sourceType,
                sourceLabel=MEDIA_SOURCE_LABELS[sourceType],
                collectedCount=sourceCounts.get(sourceType, {}).get("evidenceCount", 0),
                observedIssueCount=sourceObservationCount,
                appliedMethod=MEDIA_SOURCE_METHODS[sourceType],
            )
        )

    topIssues = []
    for index, row in enumerate(listTopStageIssues(runId, "media_external", limit=SELECTED_TOP_N), start=1):
        code = row.get("sub_issue_code", "")
        obs = observations.get(code, {})
        sourceTypes = [sourceType for sourceType in MEDIA_SOURCE_TYPES if _isObserved(obs, sourceType)]
        topIssues.append(
            MediaTopIssueDto(
                **_subIssueBase(code, rankNo=index),
                mediaImpactScore05=_safeFloat(row.get("impact_score")),
                mediaImpactScore10=_toScore10(row.get("impact_score")),
                mediaFinancialScore05=_safeFloat(row.get("financial_score")),
                mediaFinancialScore10=_toScore10(row.get("financial_score")),
                mediaAvgScore05=_safeFloat(row.get("avg_score")),
                mediaAvgScore10=_toScore10(row.get("avg_score")),
                sourceTypes=sourceTypes,
                evidenceCount=sum(int(v.get("evidenceCount", 0)) for v in obs.values()),
            )
        )

    evidenceSamples = [
        EvidenceSampleDto(
            evidenceId=int(row.get("id")),
            sourceType=row.get("source_type", ""),
            sourceTitle=row.get("source_title"),
            sourceUrl=row.get("source_url"),
            publishedAt=str(row.get("source_published_at")) if row.get("source_published_at") is not None else None,
            textSpan=row.get("text_span") or row.get("summary_text"),
        )
        for row in listEvidenceSamples(runId, "media_external", limit=10)
        if row.get("id") is not None
    ]

    return MediaStageResponseDto(
        runId=runId,
        summary=MediaSummaryDto(
            articleCount=sourceCounts.get("news", {}).get("evidenceCount", 0),
            agencyCount=sourceCounts.get("agency", {}).get("evidenceCount", 0),
            regulationFrameCount=sourceCounts.get("regulation", {}).get("evidenceCount", 0),
            observedSubIssueCount=countMediaSubIssues(runId),
        ),
        sourceBreakdown=sourceBreakdown,
        topIssues=topIssues,
        evidenceSamples=evidenceSamples,
        coverage=getMediaCoverage(runId),
    )


def getSurveyResult(runId: int) -> SurveyResponseDto:
    groupRows = listSurveyCounts(runId)
    groupCounts = {}
    for row in groupRows:
        group = row.get("respondent_group")
        if not group:
            continue
        uniqueCount = int(row.get("unique_respondent_count") or 0)
        responseCount = int(row.get("response_count") or 0)
        groupCounts[group] = uniqueCount if uniqueCount > 0 else responseCount

    groupBreakdown = []
    for group, target in MVP_SURVEY_TARGETS.items():
        count = groupCounts.get(group, 0)
        groupBreakdown.append(
            SurveyGroupBreakdownDto(
                respondentGroup=group,
                respondentGroupLabel=GROUP_LABELS[group],
                respondentCount=count,
                targetCount=target,
                responseRate=_rate(count, target),
            )
        )

    topIssueRows = listTopStageIssues(runId, "survey", limit=SELECTED_TOP_N)
    groupScoreMap = _buildSurveyGroupScoreMap(listSurveyScores(runId))
    topIssues = []
    for index, row in enumerate(topIssueRows, start=1):
        code = row.get("sub_issue_code", "")
        scores = groupScoreMap.get(code, {})
        topIssues.append(
            SurveyTopIssueDto(
                **_subIssueBase(code, rankNo=index),
                surveyImpactScore05=_safeFloat(row.get("impact_score")),
                surveyImpactScore10=_toScore10(row.get("impact_score")),
                surveyFinancialScore05=_safeFloat(row.get("financial_score")),
                surveyFinancialScore10=_toScore10(row.get("financial_score")),
                employeeImpactScore05=_safeFloat(scores.get("employee", {}).get("impact")),
                employeeImpactScore10=_toScore10(scores.get("employee", {}).get("impact")),
                employeeFinancialScore05=_safeFloat(scores.get("employee", {}).get("financial")),
                employeeFinancialScore10=_toScore10(scores.get("employee", {}).get("financial")),
                managementImpactScore05=_safeFloat(scores.get("management", {}).get("impact")),
                managementImpactScore10=_toScore10(scores.get("management", {}).get("impact")),
                managementFinancialScore05=_safeFloat(scores.get("management", {}).get("financial")),
                managementFinancialScore10=_toScore10(scores.get("management", {}).get("financial")),
                externalImpactScore05=_safeFloat(scores.get("external", {}).get("impact")),
                externalImpactScore10=_toScore10(scores.get("external", {}).get("impact")),
                externalFinancialScore05=_safeFloat(scores.get("external", {}).get("financial")),
                externalFinancialScore10=_toScore10(scores.get("external", {}).get("financial")),
            )
        )

    totalCount = sum(groupCounts.get(group, 0) for group in MVP_SURVEY_TARGETS)
    totalTarget = sum(MVP_SURVEY_TARGETS.values())
    summary = SurveySummaryDto(
        employeeRespondentCount=groupCounts.get("employee", 0),
        managementRespondentCount=groupCounts.get("management", 0),
        externalRespondentCount=groupCounts.get("external", 0),
        totalRespondentCount=totalCount,
        employeeTargetCount=MVP_SURVEY_TARGETS["employee"],
        managementTargetCount=MVP_SURVEY_TARGETS["management"],
        externalTargetCount=MVP_SURVEY_TARGETS["external"],
        employeeResponseRate=_rate(groupCounts.get("employee", 0), MVP_SURVEY_TARGETS["employee"]),
        managementResponseRate=_rate(groupCounts.get("management", 0), MVP_SURVEY_TARGETS["management"]),
        externalResponseRate=_rate(groupCounts.get("external", 0), MVP_SURVEY_TARGETS["external"]),
        totalResponseRate=_rate(totalCount, totalTarget),
        targetSource="MVP_DEFAULT",
    )

    return SurveyResponseDto(
        runId=runId,
        summary=summary,
        groupBreakdown=groupBreakdown,
        topIssues=topIssues,
        responseQuality={
            "axisSeparatedYn": True,
            "targetSource": "MVP_DEFAULT",
            "observedSubIssueCount": len(topIssueRows),
        },
        summaryText="설문 응답은 impact/financial 축을 분리하여 집계합니다.",
        axisSeparatedYn=True,
        targetSource="MVP_DEFAULT",
    )


def getSelectionProcess(runId: int, userModel) -> SelectionProcessResponseDto:
    rows = listResults(runId)
    selectedContext = _resolveSelectedContext(runId, rows)
    items = [_buildResultItem(row, selectedContext["selectedCodes"]) for row in rows]
    selectedIssues = _buildSelectionReasons(selectedContext, items)
    selectedCodeSet = set(selectedContext["selectedCodes"])

    excludedIssues = []
    for item in items:
        if item.subIssueCode in selectedCodeSet:
            continue
        excludedIssues.append(
            SelectionReasonDto(
                subIssueCode=item.subIssueCode,
                displaySubIssueName=item.displaySubIssueName,
                rankNo=item.rankNo,
                selectedYn=False,
                selectionType="not_selected",
                selectionReason="Top 5 최종 선정 범위 밖의 이슈입니다.",
                selectionSource=selectedContext["selectionSource"],
                fallbackYn=selectedContext["fallbackYn"],
            )
        )

    return SelectionProcessResponseDto(
        runId=runId,
        candidateCount=len(subissueMaster),
        scoredCount=sum(1 for item in items if item.finalScore05 is not None),
        selectedCount=len(selectedIssues),
        selectionSource=selectedContext["selectionSource"],
        fallbackYn=selectedContext["fallbackYn"],
        selectionRules={
            "selectedTopN": SELECTED_TOP_N,
            "fallbackRule": "ESG_DMA_SCORE_SUMMARY.rank_no ASC",
            "tableRule": "ESG_MATERIALITY_SELECTED_SUB_ISSUE.selected_rank_no ASC",
        },
        selectedIssues=selectedIssues,
        excludedIssues=excludedIssues,
    )


def getOnboardingProgress(runId: int) -> dict:
    run = findOne(
        "SELECT id FROM ESG_MATERIALITY_RUN WHERE id = ? AND delete_yn = 0",
        (runId,),
    )
    if not run:
        raise ValueError(f"Materiality run not found: {runId}")

    rows = findAll(
        """
        SELECT
            sub.sub_issue_code,
            COALESCE(sub_master.sub_issue_name_kr, '기타') AS sub_issue_name,
            COUNT(DISTINCT master.atomic_metric_id)        AS total_count,
            COUNT(DISTINCT CASE
                WHEN fact.atomic_metric_id   IS NOT NULL
                  OR rollup.group_atomic_metric_id IS NOT NULL
                THEN master.atomic_metric_id
            END)                                           AS done_count
        FROM ESG_MATERIALITY_SELECTED_SUB_ISSUE sub
        LEFT JOIN ESG_SUB_ISSUE_MASTER sub_master
            ON sub.sub_issue_code = sub_master.sub_issue_code
        LEFT JOIN ESG_ATOMIC_METRIC_MASTER master
            ON sub.sub_issue_code = master.sub_issue_code
        LEFT JOIN ESG_KPI_FACT fact
            ON master.atomic_metric_id = fact.atomic_metric_id
        LEFT JOIN ESG_GROUP_ROLLUP_RESULT rollup
            ON master.atomic_metric_id = rollup.group_atomic_metric_id
        WHERE sub.esg_materiality_run_id = ?
        GROUP BY sub.sub_issue_code, sub_master.sub_issue_name_kr
        ORDER BY sub.selected_rank_no ASC
        """,
        (runId,),
    )

    items = [
        {
            "subIssueCode": r["sub_issue_code"],
            "subIssueName": r["sub_issue_name"],
            "totalCount": int(r["total_count"] or 0),
            "doneCount": int(r["done_count"] or 0),
        }
        for r in (rows or [])
    ]
    return {"runId": runId, "items": items}


def finalizeSelectedSubIssues(runId: int, userModel) -> FinalizeSelectedSubIssuesResponseDto:
    run = findOne(
        "SELECT id FROM ESG_MATERIALITY_RUN WHERE id = ? AND delete_yn = 0",
        (runId,),
    )
    if not run:
        raise ValueError(f"Materiality run not found: {runId}")

    topRows = listFinalTopSubIssues(runId, limit=5)
    if len(topRows) < 5:
        raise ValueError(f"Top 5 candidates not sufficient: found {len(topRows)}")

    userId = getattr(userModel, "id", None) or getattr(userModel, "user_id", None)

    rowsToInsert = [
        {
            "sub_issue_code": row["sub_issue_code"],
            "selected_rank_no": idx + 1,
            "selection_type": "rank_based",
            "selection_reason": "최종 DMA 점수 기준 Top 5 자동 선정",
        }
        for idx, row in enumerate(topRows[:5])
    ]

    replaceSelectedSubIssuesTx(runId, rowsToInsert, userId=userId)

    # 선정 확정 직후 온보딩 지표 scope 자동 초기화 (idempotent).
    # 사용자가 별도 버튼을 누르는 것이 아니라, Top 5 확정의 후속 단계로 시스템이 자동 처리한다.
    _initPostDmaScopeAfterFinalize(runId, userId)

    selectedIssues = [
        FinalizeSelectedSubIssueItemDto(
            subIssueCode=row["sub_issue_code"],
            selectedRankNo=idx + 1,
            rankNo=_safeInt(row.get("rank_no")),
            finalScore05=_safeFloat(row.get("final_score")),
            selectionType="rank_based",
            selectionReason="최종 DMA 점수 기준 Top 5 자동 선정",
        )
        for idx, row in enumerate(topRows[:5])
    ]

    return FinalizeSelectedSubIssuesResponseDto(
        runId=runId,
        selectedCount=len(selectedIssues),
        selectionSource="TABLE",
        fallbackYn=False,
        selectedIssues=selectedIssues,
    )


def _initPostDmaScopeAfterFinalize(runId: int, userId: Optional[int]) -> None:
    """선정 확정 후 온보딩 지표 scope를 자동 초기화한다.

    reportworkflows 서비스의 idempotent scope 초기화 로직을 재사용한다.
    (지연 import로 materialities ↔ reportworkflows 순환 참조 방지)
    동일 runId 재호출 시 기존 cycle/scope를 재사용하므로 중복 생성되지 않는다.
    """
    from src.services.reportworkflows.service import initializePostDmaDisclosureScope

    initializePostDmaDisclosureScope(runId, userId)


def _buildResultItem(row: dict, selectedCodes: list[str]) -> MaterialityResultItemDto:
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
    finalImp10 = _toScore10(finalImp)
    finalFin10 = _toScore10(finalFin)

    return MaterialityResultItemDto(
        **_subIssueBase(
            code,
            rankNo=rankNo,
            selectedYn=code in selectedCodes,
            quadrant=_quadrant(finalImp10, finalFin10),
        ),
        benchmarkImpactScore05=benchImp,
        benchmarkImpactScore10=_toScore10(benchImp),
        benchmarkFinancialScore05=benchFin,
        benchmarkFinancialScore10=_toScore10(benchFin),
        mediaImpactScore05=mediaImp,
        mediaImpactScore10=_toScore10(mediaImp),
        mediaFinancialScore05=mediaFin,
        mediaFinancialScore10=_toScore10(mediaFin),
        surveyImpactScore05=surveyImp,
        surveyImpactScore10=_toScore10(surveyImp),
        surveyFinancialScore05=surveyFin,
        surveyFinancialScore10=_toScore10(surveyFin),
        finalImpactScore05=finalImp,
        finalImpactScore10=finalImp10,
        finalFinancialScore05=finalFin,
        finalFinancialScore10=finalFin10,
        finalScore05=finalScore,
        finalScore10=_toScore10(finalScore),
        coverage=_buildCoverage(benchImp, benchFin, mediaImp, mediaFin, surveyImp, surveyFin),
    )


def _buildMatrixItem(item: MaterialityResultItemDto) -> MatrixItemDto:
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


def _buildTopIssues(items: list[MaterialityResultItemDto], selectedCodes: list[str]) -> list[TopIssueDto]:
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


def _buildCoverageSummary(items: list[MaterialityResultItemDto]) -> CoverageSummaryDto:
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


def _resolveSelectedContext(runId: int, rows: list[dict]) -> dict:
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


def _buildSelectionReasons(selectedContext: dict, items: list[MaterialityResultItemDto]) -> list[SelectionReasonDto]:
    byCode = {item.subIssueCode: item for item in items}
    selectedRowsByCode = {row.get("sub_issue_code"): row for row in selectedContext.get("selectedRows", [])}
    reasons = []
    for code in selectedContext["selectedCodes"]:
        item = byCode.get(code)
        if not item:
            base = _subIssueBase(code, selectedYn=True)
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


def _buildObservationMap(rows: list[dict]) -> dict:
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


def _buildEvidenceSourceCounts(rows: list[dict]) -> dict:
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


def _buildBenchmarkObservationIssue(code: str, obs: dict) -> BenchmarkObservationIssueDto:
    return BenchmarkObservationIssueDto(
        **_subIssueBase(code),
        leaderObserved=_isObserved(obs, "leader_sr"),
        peerObserved=_isObserved(obs, "peer_sr"),
        ownObserved=_isObserved(obs, "own_sr"),
        leaderEvidenceCount=int(obs.get("leader_sr", {}).get("evidenceCount", 0)),
        peerEvidenceCount=int(obs.get("peer_sr", {}).get("evidenceCount", 0)),
        ownEvidenceCount=int(obs.get("own_sr", {}).get("evidenceCount", 0)),
    )


def _buildSurveyGroupScoreMap(rows: list[dict]) -> dict:
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


def _subIssueBase(
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


def _subIssueSortKey(code: str):
    meta = getSubIssueMeta(code)
    return (meta.get("domain", ""), meta.get("issueGroup", ""), meta.get("subIssueSort", 999), code)


def _isObserved(obs: dict, sourceType: str) -> bool:
    return int(obs.get(sourceType, {}).get("signalCount", 0)) > 0


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


def _safeFloat(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safeInt(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _toScore10(score05) -> Optional[float]:
    value = _safeFloat(score05)
    if value is None:
        return None
    return round(value * 2, 2)


def _rate(value: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return round((value / total) * 100, 1)
