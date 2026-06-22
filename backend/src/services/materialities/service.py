"""
service.py
레이어: Service (materialities)
역할: DMA 중대성 평가 서비스 — 결과 조회·저장·이슈 선정 API 처리.
"""
from typing import Optional

from src.utils.typeutils import safeFloat as _safeFloat, safeInt as _safeInt

from src.models.materiality import (
    BenchmarkResponseDto,
    BenchmarkSummaryDto,
    BenchmarkTopIssueDto,
    EvidenceSampleDto,
    FinalizeSelectedSubIssueItemDto,
    FinalizeSelectedSubIssuesResponseDto,
    MaterialityResultsResponseDto,
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
)
from src.utils.db import findAll, findOne
from src.repositories.dmaworkflowrepository import getDmaWorkflowStatusOrDefault as _getDmaWorkflowStatusOrDefault
from src.repositories.dmarepository import (
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
    listSignalCounts,
    listSurveyCounts,
    listSurveyScores,
    listTopStageIssues,
    replaceSelectedSubIssuesTx,
)
from src.services.materialities import materialitybuilder as _mb
from src.services.reportworkflows.service import initializePostDmaDisclosureScope


def getMaterialityResults(runId: int) -> MaterialityResultsResponseDto:
    """중대성 평가 전체 결과(이슈 목록·매트릭스·Top 이슈·다음 단계)를 조합해 반환한다."""
    rows = listResults(runId)
    selectedContext = _mb.resolveSelectedContext(runId, rows)
    selectedCodes = selectedContext["selectedCodes"]

    items = [_mb.buildResultItem(row, selectedCodes) for row in rows]
    scoredItems = [item for item in items if item.finalScore05 is not None]
    matrixItems = [_mb.buildMatrixItem(item) for item in scoredItems]
    topItems = _mb.buildTopIssues(items, selectedCodes)
    highPriorityCount = sum(1 for item in matrixItems if item.quadrant == "HIGH_IMPACT_HIGH_FINANCIAL")
    selectionReasons = _mb.buildSelectionReasons(selectedContext, items)

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
        totalCandidateSubIssueCount=len(_mb.subissueMaster),
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
        coverageSummary=_mb.buildCoverageSummary(items),
    )


def getBenchmarkResult(runId: int) -> BenchmarkResponseDto:
    """벤치마크 단계 증거 현황·관측 이슈·Top 이슈를 집계해 반환한다."""
    evidenceCounts = listEvidenceCounts(runId, "benchmark")
    observationRows = listSignalCounts(runId, "benchmark")
    observations = _mb.buildObservationMap(observationRows)
    sourceCounts = _mb.buildEvidenceSourceCounts(evidenceCounts)

    leaderReportCount = sourceCounts.get("leader_sr", {}).get("reportCount", 0)
    peerReportCount = sourceCounts.get("peer_sr", {}).get("reportCount", 0)
    ownReportCount = sourceCounts.get("own_sr", {}).get("reportCount", 0)
    analyzedReportCount = leaderReportCount + peerReportCount + ownReportCount
    if analyzedReportCount == 0:
        analyzedReportCount = sum(sourceCounts.get(sourceType, {}).get("evidenceCount", 0) for sourceType in _mb.BENCHMARK_SOURCE_TYPES)

    commonIssues = []
    blindSpotIssues = []
    for code in sorted(observations.keys(), key=_mb.subIssueSortKey):
        issue = _mb.buildBenchmarkObservationIssue(code, observations[code])
        if issue.leaderObserved or issue.peerObserved:
            commonIssues.append(issue)
        if (issue.leaderObserved or issue.peerObserved) and not issue.ownObserved:
            issue.blindSpotYn = True
            issue.summary = "외부 벤치마크(리더/피어)에서 관측되었으나 자사 보고서에서는 관측되지 않은 이슈입니다."
            blindSpotIssues.append(issue)

    topIssues = []
    for index, row in enumerate(listTopStageIssues(runId, "benchmark", limit=_mb.SELECTED_TOP_N), start=1):
        code = row.get("sub_issue_code", "")
        obs = observations.get(code, {})
        topIssues.append(
            BenchmarkTopIssueDto(
                **_mb.subIssueBase(code, rankNo=index),
                benchmarkImpactScore05=_safeFloat(row.get("impact_score")),
                benchmarkImpactScore10=_mb.toScore10(row.get("impact_score")),
                benchmarkFinancialScore05=_safeFloat(row.get("financial_score")),
                benchmarkFinancialScore10=_mb.toScore10(row.get("financial_score")),
                benchmarkAvgScore05=_safeFloat(row.get("avg_score")),
                benchmarkAvgScore10=_mb.toScore10(row.get("avg_score")),
                leaderObserved=_mb.isObserved(obs, "leader_sr"),
                peerObserved=_mb.isObserved(obs, "peer_sr"),
                ownObserved=_mb.isObserved(obs, "own_sr"),
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
    """미디어·규제·전문기관 출처별 관측 결과와 Top 이슈를 집계해 반환한다."""
    evidenceCounts = listEvidenceCounts(runId, "media_external")
    observationRows = listSignalCounts(runId, "media_external")
    observations = _mb.buildObservationMap(observationRows)
    sourceCounts = _mb.buildEvidenceSourceCounts(evidenceCounts)

    sourceBreakdown = []
    for sourceType in _mb.MEDIA_SOURCE_TYPES:
        sourceObservationCount = sum(1 for item in observations.values() if _mb.isObserved(item, sourceType))
        sourceBreakdown.append(
            SourceBreakdownDto(
                sourceType=sourceType,
                sourceLabel=_mb.MEDIA_SOURCE_LABELS[sourceType],
                collectedCount=sourceCounts.get(sourceType, {}).get("evidenceCount", 0),
                observedIssueCount=sourceObservationCount,
                appliedMethod=_mb.MEDIA_SOURCE_METHODS[sourceType],
            )
        )

    topIssues = []
    for index, row in enumerate(listTopStageIssues(runId, "media_external", limit=_mb.SELECTED_TOP_N), start=1):
        code = row.get("sub_issue_code", "")
        obs = observations.get(code, {})
        sourceTypes = [sourceType for sourceType in _mb.MEDIA_SOURCE_TYPES if _mb.isObserved(obs, sourceType)]
        topIssues.append(
            MediaTopIssueDto(
                **_mb.subIssueBase(code, rankNo=index),
                mediaImpactScore05=_safeFloat(row.get("impact_score")),
                mediaImpactScore10=_mb.toScore10(row.get("impact_score")),
                mediaFinancialScore05=_safeFloat(row.get("financial_score")),
                mediaFinancialScore10=_mb.toScore10(row.get("financial_score")),
                mediaAvgScore05=_safeFloat(row.get("avg_score")),
                mediaAvgScore10=_mb.toScore10(row.get("avg_score")),
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
    """설문 응답자 그룹별 현황과 이슈별 impact/financial 점수를 집계해 반환한다."""
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
    for group, target in _mb.MVP_SURVEY_TARGETS.items():
        count = groupCounts.get(group, 0)
        groupBreakdown.append(
            SurveyGroupBreakdownDto(
                respondentGroup=group,
                respondentGroupLabel=_mb.GROUP_LABELS[group],
                respondentCount=count,
                targetCount=target,
                responseRate=_mb.rate(count, target),
            )
        )

    topIssueRows = listTopStageIssues(runId, "survey", limit=_mb.SELECTED_TOP_N)
    groupScoreMap = _mb.buildSurveyGroupScoreMap(listSurveyScores(runId))
    topIssues = []
    for index, row in enumerate(topIssueRows, start=1):
        code = row.get("sub_issue_code", "")
        scores = groupScoreMap.get(code, {})
        topIssues.append(
            SurveyTopIssueDto(
                **_mb.subIssueBase(code, rankNo=index),
                surveyImpactScore05=_safeFloat(row.get("impact_score")),
                surveyImpactScore10=_mb.toScore10(row.get("impact_score")),
                surveyFinancialScore05=_safeFloat(row.get("financial_score")),
                surveyFinancialScore10=_mb.toScore10(row.get("financial_score")),
                employeeImpactScore05=_safeFloat(scores.get("employee", {}).get("impact")),
                employeeImpactScore10=_mb.toScore10(scores.get("employee", {}).get("impact")),
                employeeFinancialScore05=_safeFloat(scores.get("employee", {}).get("financial")),
                employeeFinancialScore10=_mb.toScore10(scores.get("employee", {}).get("financial")),
                managementImpactScore05=_safeFloat(scores.get("management", {}).get("impact")),
                managementImpactScore10=_mb.toScore10(scores.get("management", {}).get("impact")),
                managementFinancialScore05=_safeFloat(scores.get("management", {}).get("financial")),
                managementFinancialScore10=_mb.toScore10(scores.get("management", {}).get("financial")),
                externalImpactScore05=_safeFloat(scores.get("external", {}).get("impact")),
                externalImpactScore10=_mb.toScore10(scores.get("external", {}).get("impact")),
                externalFinancialScore05=_safeFloat(scores.get("external", {}).get("financial")),
                externalFinancialScore10=_mb.toScore10(scores.get("external", {}).get("financial")),
            )
        )

    totalCount = sum(groupCounts.get(group, 0) for group in _mb.MVP_SURVEY_TARGETS)
    totalTarget = sum(_mb.MVP_SURVEY_TARGETS.values())
    summary = SurveySummaryDto(
        employeeRespondentCount=groupCounts.get("employee", 0),
        managementRespondentCount=groupCounts.get("management", 0),
        externalRespondentCount=groupCounts.get("external", 0),
        totalRespondentCount=totalCount,
        employeeTargetCount=_mb.MVP_SURVEY_TARGETS["employee"],
        managementTargetCount=_mb.MVP_SURVEY_TARGETS["management"],
        externalTargetCount=_mb.MVP_SURVEY_TARGETS["external"],
        employeeResponseRate=_mb.rate(groupCounts.get("employee", 0), _mb.MVP_SURVEY_TARGETS["employee"]),
        managementResponseRate=_mb.rate(groupCounts.get("management", 0), _mb.MVP_SURVEY_TARGETS["management"]),
        externalResponseRate=_mb.rate(groupCounts.get("external", 0), _mb.MVP_SURVEY_TARGETS["external"]),
        totalResponseRate=_mb.rate(totalCount, totalTarget),
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
    """이슈 선정 과정(선정·미선정 이슈, 선정 규칙, 근거)을 상세히 반환한다."""
    from src.utils.subissuemaster import subissueMaster
    rows = listResults(runId)
    selectedContext = _mb.resolveSelectedContext(runId, rows)
    items = [_mb.buildResultItem(row, selectedContext["selectedCodes"]) for row in rows]
    selectedIssues = _mb.buildSelectionReasons(selectedContext, items)
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
            "selectedTopN": _mb.SELECTED_TOP_N,
            "fallbackRule": "ESG_DMA_SCORE_SUMMARY.rank_no ASC",
            "tableRule": "ESG_MATERIALITY_SELECTED_SUB_ISSUE.selected_rank_no ASC",
        },
        selectedIssues=selectedIssues,
        excludedIssues=excludedIssues,
    )


def getOnboardingProgress(runId: int) -> dict:
    """선정된 서브이슈별 필수 지표 입력 완료율을 조회해 반환한다."""
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
    """최종 점수 기준 Top 5 서브이슈를 선정 테이블에 확정하고 POST-DMA 온보딩 Scope를 초기화한다."""
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


def getWorkflowStatus(runId: int, workflowType: str) -> dict:
    """지정된 DMA 워크플로우 타입의 현재 상태를 조회해 반환한다."""
    return _getDmaWorkflowStatusOrDefault(runId=runId, workflowType=workflowType)


def _initPostDmaScopeAfterFinalize(runId: int, userId: Optional[int]) -> None:
    """선정 확정 후 온보딩 지표 scope를 자동 초기화한다.

    동일 runId 재호출 시 기존 cycle/scope를 재사용하므로 중복 생성되지 않는다.
    """
    initializePostDmaDisclosureScope(runId, userId)
