from collections import Counter
from datetime import date
from typing import Optional

from src.models.media import (
    MediaNewsCrawlAnalyzeRequest,
    MediaNewsCrawlAnalyzeResponse,
    MediaTopIssue,
)
from src.models.model import UserModel
from src.models.dmaengine import KcgsGradeInputV13
from src.models.dmakcgsgrade import KcgsGradeSaveRequest
from src.services.medias.adapter import convertMediaToDmaSignals, step0NormalizeMediaFacts
from src.services.medias.baseline import applyMediaBaseline
from src.services.medias.crawler import applySavedSignalCounts, crawlNewsArticles
from src.services.medias.pg_pipeline import fetchMediaChunksFromPg
from src.services.medias.pipeline import processMediaPipeline
from src.services.materialities.orchestrator import (
    step0BuildFactTrace,
    step1BuildMediaNewsCanonicalPayloads,
    step2BuildKcgsPillarBoostPayloads,
    step2BuildMediaExternalMaxPayloads,
    step2BuildRegulationScreeningPayloads,
)
from src.services.surveys.formservice import ensureSurveyFormForRun
from src.repositories.dmarepository import (
    getMediaCoverage,
    countMediaSubIssues,
    listTopMediaIssues,
    saveSignals,
    step4ReplaceMediaNewsShadowBundleTx,
    findRegulationRunContext,
    listApprovedKcgsGradeInputs,
    listApprovedRegulationInputs,
    listApprovedActiveRegulationMappings,
    step4ReplaceKcgsShadowTracesTx,
    step4ReplaceRegulationShadowTracesTx,
    listExternalMaxEligibleMediaRows,
    step4ReplaceMediaExternalMaxShadowAndSummaryTx,
    resetMediaData,
    countTop20RankedSubIssues,
    saveKcgsGradeInputRows,
)
from src.repositories.dmaworkflowrepository import upsertDmaWorkflowStatus
from src.utils.dmascoring import SCORE_UI_MULTIPLIER, scoreSignals
from src.utils.settings import settings
from src.utils.subissuemaster import getSubIssueDisplayName
from src.utils.typeutils import safeFloat


MVP_DEMO_COMPANY_KEYWORDS = ["현대모비스"]
MVP_DEMO_INDUSTRY_KEYWORDS = ["자동차부품산업"]


def _writeMediaWorkflowStatus(
    *,
    runId: int,
    overallStatus: str,
    currentStage: str,
    progressPercent: int,
    progressMode: str = "MILESTONE",
    processedCount=None,
    totalCount=None,
    errorStage=None,
    errorMessage=None,
    startedYn: bool = False,
    completedYn: bool = False,
) -> None:
    try:
        upsertDmaWorkflowStatus(
            runId=runId,
            workflowType="MEDIA",
            overallStatus=overallStatus,
            currentStage=currentStage,
            progressPercent=progressPercent,
            progressMode=progressMode,
            processedCount=processedCount,
            totalCount=totalCount,
            errorStage=errorStage,
            errorMessage=errorMessage,
            startedYn=startedYn,
            completedYn=completedYn,
        )
    except Exception as statusError:
        print(f"Warning: MEDIA workflow status write skipped ({currentStage}): {statusError}")


def _recordMediaWorkflowFailureBestEffort(
    *,
    runId: int,
    currentStage: str,
    progressPercent: int,
    error: Exception,
) -> None:
    try:
        _writeMediaWorkflowStatus(
            runId=runId,
            overallStatus="FAILED",
            currentStage=currentStage,
            progressPercent=progressPercent,
            errorStage=currentStage,
            errorMessage=str(error)[:1000],
        )
    except Exception as statusError:
        print(f"Warning: MEDIA workflow FAILED status write failed: {statusError}")


def _resolvePgMode(requestFlag: Optional[bool]) -> bool:
    if requestFlag is not None:
        return requestFlag
    return settings.use_pg_pipeline


def _runMediaAnalysis(
    articles: list,
    runId: int,
    keywords: Optional[list[str]] = None,
    industryKeywords: Optional[list[str]] = None,
    shadowReplaceYn: bool = True,
    usePgPipeline: Optional[bool] = None,
) -> list:
    if keywords is None:
        keywords = []
    if industryKeywords is None:
        industryKeywords = []

    if _resolvePgMode(usePgPipeline):
        pipelineResults = fetchMediaChunksFromPg()
    else:
        pipelineResults = processMediaPipeline(
            articles,
            companyKeywords=keywords,
            industryKeywords=industryKeywords,
        )
    signals = convertMediaToDmaSignals(pipelineResults)
    baselinedSignals = applyMediaBaseline(signals)
    scoredSignals = scoreSignals(baselinedSignals)

    if scoredSignals:
        saveSignals(runId=runId, signals=scoredSignals, fileId=None, sourceTitle="Media Analysis")

    if shadowReplaceYn:
        try:
            _replaceMediaNewsShadowFromPipelineResults(runId=runId, pipelineResults=pipelineResults)
        except Exception as shadowError:
            print(f"Warning: media news shadow replace skipped: {shadowError}")

    return scoredSignals


def _runMediaCrawlAndAnalyzePg(request: MediaNewsCrawlAnalyzeRequest) -> MediaNewsCrawlAnalyzeResponse:
    runId = request.runId
    currentStage = "PREPARE"
    currentProgress = 10
    _writeMediaWorkflowStatus(
        runId=runId, overallStatus="RUNNING", currentStage=currentStage,
        progressPercent=currentProgress, startedYn=True,
    )

    try:
        currentStage = "NEWS_ANALYSIS"
        currentProgress = 55
        _writeMediaWorkflowStatus(
            runId=runId, overallStatus="RUNNING", currentStage=currentStage,
            progressPercent=currentProgress,
        )
        scoredSignals = _runMediaAnalysis(
            articles=[],
            runId=request.runId,
            keywords=MVP_DEMO_COMPANY_KEYWORDS,
            industryKeywords=MVP_DEMO_INDUSTRY_KEYWORDS,
            shadowReplaceYn=True,
            usePgPipeline=True,
        )

        currentStage = "REGULATION_REFRESH"
        currentProgress = 70
        _writeMediaWorkflowStatus(
            runId=runId, overallStatus="RUNNING", currentStage=currentStage,
            progressPercent=currentProgress,
        )
        try:
            refreshRegulationShadowForRun(request.runId)
        except Exception as _exc:
            print(f"Warning: [pg_media] regulation shadow refresh skipped: {_exc}")

        currentStage = "KCGS_REFRESH"
        currentProgress = 80
        _writeMediaWorkflowStatus(
            runId=runId, overallStatus="RUNNING", currentStage=currentStage,
            progressPercent=currentProgress,
        )
        try:
            refreshKcgsShadowForRun(request.runId)
        except Exception as _exc:
            print(f"Warning: [pg_media] kcgs shadow refresh skipped: {_exc}")

        if countTop20RankedSubIssues(request.runId) >= 1:
            currentStage = "SURVEY_FORM_FREEZE"
            currentProgress = 95
            _writeMediaWorkflowStatus(
                runId=runId, overallStatus="RUNNING", currentStage=currentStage,
                progressPercent=currentProgress,
            )
            ensureSurveyFormForRun(request.runId)

        coverageInfo = getMediaCoverage(request.runId)
        savedSignalCount = len(scoredSignals) if scoredSignals else 0
        response = MediaNewsCrawlAnalyzeResponse(
            runId=request.runId,
            requestedSources=request.sources,
            allowedSources=request.sources,
            rejectedSources=[],
            companyKeywords=MVP_DEMO_COMPANY_KEYWORDS,
            industryKeywords=MVP_DEMO_INDUSTRY_KEYWORDS,
            collectedArticleCount=0,
            filteredArticleCount=0,
            articleCount=0,
            savedSignalCount=savedSignalCount,
            observedSubIssueCount=countMediaSubIssues(request.runId),
            sourceBreakdown=[],
            topIssues=_buildMediaTopIssues(request.runId),
            coverage=coverageInfo,
            coverageStatus=coverageInfo["coverageStatus"],
            errors=[],
        )

        currentStage = "COMPLETED"
        currentProgress = 100
        _writeMediaWorkflowStatus(
            runId=runId, overallStatus="COMPLETED", currentStage=currentStage,
            progressPercent=currentProgress, completedYn=True,
        )
        return response
    except Exception as e:
        _recordMediaWorkflowFailureBestEffort(
            runId=runId, currentStage=currentStage,
            progressPercent=currentProgress, error=e,
        )
        raise


def runMediaCrawlAndAnalyze(
    request: MediaNewsCrawlAnalyzeRequest, userModel: UserModel
) -> MediaNewsCrawlAnalyzeResponse:
    if _resolvePgMode(request.usePgPipeline):
        return _runMediaCrawlAndAnalyzePg(request)

    dateFrom = _parseRequestDate(request.dateFrom, "dateFrom")
    dateTo = _parseRequestDate(request.dateTo, "dateTo")
    if dateFrom > dateTo:
        raise ValueError("dateFrom must be earlier than or equal to dateTo.")

    runId = request.runId
    currentStage = "PREPARE"
    currentProgress = 10
    _writeMediaWorkflowStatus(
        runId=runId, overallStatus="RUNNING", currentStage=currentStage,
        progressPercent=currentProgress, startedYn=True,
    )

    try:
        resetMediaData(runId)

        currentStage = "NEWS_CRAWL"
        currentProgress = 30
        _writeMediaWorkflowStatus(
            runId=runId, overallStatus="RUNNING", currentStage=currentStage,
            progressPercent=currentProgress,
        )

        crawlResult = crawlNewsArticles(
            sources=request.sources,
            dateFrom=dateFrom,
            dateTo=dateTo,
            companyKeywords=MVP_DEMO_COMPANY_KEYWORDS,
            industryKeywords=MVP_DEMO_INDUSTRY_KEYWORDS,
        )

        crawlCompleteYn = _isCrawlComplete(crawlResult)
        scoredSignals = []
        savedSignalCountsBySource = {}
        if crawlResult.articles:
            currentStage = "NEWS_ANALYSIS"
            currentProgress = 55
            _writeMediaWorkflowStatus(
                runId=runId, overallStatus="RUNNING", currentStage=currentStage,
                progressPercent=currentProgress,
            )
            scoredSignals = _runMediaAnalysis(
                articles=crawlResult.articles,
                runId=request.runId,
                keywords=MVP_DEMO_COMPANY_KEYWORDS,
                industryKeywords=MVP_DEMO_INDUSTRY_KEYWORDS,
                shadowReplaceYn=crawlCompleteYn,
            )
            savedSignalCountsBySource = _countSavedSignalsBySource(scoredSignals)
        elif crawlCompleteYn:
            _replaceMediaNewsShadowFromPipelineResults(runId=request.runId, pipelineResults=[])

        _shadowRefreshErrors: list[tuple[str, Exception]] = []

        currentStage = "REGULATION_REFRESH"
        currentProgress = 70
        _writeMediaWorkflowStatus(
            runId=runId, overallStatus="RUNNING", currentStage=currentStage,
            progressPercent=currentProgress,
        )
        try:
            refreshRegulationShadowForRun(request.runId)
        except Exception as _exc:
            _shadowRefreshErrors.append(("regulation", _exc))

        currentStage = "KCGS_REFRESH"
        currentProgress = 80
        _writeMediaWorkflowStatus(
            runId=runId, overallStatus="RUNNING", currentStage=currentStage,
            progressPercent=currentProgress,
        )
        try:
            refreshKcgsShadowForRun(request.runId)
        except Exception as _exc:
            _shadowRefreshErrors.append(("kcgs", _exc))

        if crawlCompleteYn:
            if _shadowRefreshErrors:
                raise RuntimeError(
                    "media_external source refresh failed; externalMax summary update aborted: "
                    + "; ".join(f"{k}: {v}" for k, v in _shadowRefreshErrors)
                )
            currentStage = "EXTERNAL_MAX_SUMMARY"
            currentProgress = 95
            _writeMediaWorkflowStatus(
                runId=runId, overallStatus="RUNNING", currentStage=currentStage,
                progressPercent=currentProgress,
            )
            refreshMediaExternalMaxForRun(request.runId)
            if countTop20RankedSubIssues(request.runId) >= 1:
                ensureSurveyFormForRun(request.runId)
        else:
            if countTop20RankedSubIssues(request.runId) >= 1:
                currentStage = "SURVEY_FORM_FREEZE"
                currentProgress = 95
                _writeMediaWorkflowStatus(
                    runId=runId, overallStatus="RUNNING", currentStage=currentStage,
                    progressPercent=currentProgress,
                )
                ensureSurveyFormForRun(request.runId)

        sourceBreakdown = applySavedSignalCounts(
            crawlResult.sourceBreakdown,
            savedSignalCountsBySource,
        )
        coverageInfo = getMediaCoverage(request.runId)
        savedSignalCount = len(scoredSignals) if scoredSignals else 0

        response = MediaNewsCrawlAnalyzeResponse(
            runId=request.runId,
            requestedSources=crawlResult.requestedSources,
            allowedSources=crawlResult.allowedSources,
            rejectedSources=crawlResult.rejectedSources,
            companyKeywords=MVP_DEMO_COMPANY_KEYWORDS,
            industryKeywords=MVP_DEMO_INDUSTRY_KEYWORDS,
            collectedArticleCount=crawlResult.collectedArticleCount,
            filteredArticleCount=crawlResult.filteredArticleCount,
            articleCount=crawlResult.filteredArticleCount,
            savedSignalCount=savedSignalCount,
            observedSubIssueCount=countMediaSubIssues(request.runId),
            sourceBreakdown=sourceBreakdown,
            topIssues=_buildMediaTopIssues(request.runId),
            coverage=coverageInfo,
            coverageStatus=coverageInfo["coverageStatus"],
            errors=crawlResult.errors,
        )

        currentStage = "COMPLETED"
        currentProgress = 100
        _writeMediaWorkflowStatus(
            runId=runId, overallStatus="COMPLETED", currentStage=currentStage,
            progressPercent=currentProgress, completedYn=True,
        )
        return response
    except Exception as e:
        _recordMediaWorkflowFailureBestEffort(
            runId=runId, currentStage=currentStage,
            progressPercent=currentProgress, error=e,
        )
        raise


def saveKcgsGradeInputs(request: KcgsGradeSaveRequest, userModel) -> int:
    if len(request.grades) != 3:
        raise ValueError("KCGS 등급은 정확히 3개년(연속) 입력이 필요합니다.")

    inputs = [
        KcgsGradeInputV13(
            companyId=request.companyId,
            ratingYear=g.ratingYear,
            overallGrade=g.overallGrade,
            environmentGrade=g.environmentGrade,
            socialGrade=g.socialGrade,
            governanceGrade=g.governanceGrade,
            inputSourceType="MANUAL",
            sourceDocumentRef=g.sourceDocumentRef,
            reviewStatus="APPROVED",
        )
        for g in request.grades
    ]

    step2BuildKcgsPillarBoostPayloads(inputs)

    if isinstance(userModel, dict):
        userId = userModel.get("id")
    else:
        userId = getattr(userModel, "id", None)

    rows = [
        {
            "ratingYear": g.ratingYear,
            "overallGrade": g.overallGrade,
            "environmentGrade": g.environmentGrade,
            "socialGrade": g.socialGrade,
            "governanceGrade": g.governanceGrade,
            "sourceDocumentRef": g.sourceDocumentRef,
        }
        for g in request.grades
    ]
    return saveKcgsGradeInputRows(
        companyId=request.companyId,
        rows=rows,
        reviewStatus="APPROVED",
        createdByUserId=userId,
    )


def refreshRegulationShadowForRun(runId: int) -> int:
    runContext = findRegulationRunContext(runId)
    companyId = runContext["companyId"]
    reportingYear = runContext["reportingYear"]
    approvedInputs = listApprovedRegulationInputs(companyId, reportingYear)
    approvedMappings = listApprovedActiveRegulationMappings()
    payloads = step2BuildRegulationScreeningPayloads(approvedInputs, approvedMappings)
    return step4ReplaceRegulationShadowTracesTx(runId, payloads)


def refreshMediaExternalMaxForRun(runId: int) -> int:
    rows = listExternalMaxEligibleMediaRows(runId)
    payloads = step2BuildMediaExternalMaxPayloads(rows)
    return step4ReplaceMediaExternalMaxShadowAndSummaryTx(runId, payloads)


def refreshKcgsShadowForRun(runId: int) -> int:
    runContext = findRegulationRunContext(runId)
    companyId = runContext["companyId"]
    gradeRows = listApprovedKcgsGradeInputs(companyId)
    payloads = step2BuildKcgsPillarBoostPayloads(gradeRows)
    return step4ReplaceKcgsShadowTracesTx(runId, payloads)


def _buildMediaTopIssues(runId: int) -> list[MediaTopIssue]:
    topIssues = []
    for row in listTopMediaIssues(runId, limit=5):
        code = row.get("sub_issue_code", "")
        mediaImp = safeFloat(row.get("media_external_impact_score"))
        mediaFin = safeFloat(row.get("media_external_financial_score"))
        mediaAvg = safeFloat(row.get("media_avg_score"))
        finalScore = safeFloat(row.get("final_score"))
        rankNo = int(row["rank_no"]) if row.get("rank_no") is not None else None
        topIssues.append(
            MediaTopIssue(
                subIssueCode=code,
                displaySubIssueName=getSubIssueDisplayName(code),
                mediaImpactScore05=mediaImp,
                mediaFinancialScore05=mediaFin,
                mediaImpactScore10=_score10(mediaImp),
                mediaFinancialScore10=_score10(mediaFin),
                mediaAvgScore05=mediaAvg,
                mediaAvgScore10=_score10(mediaAvg),
                finalScore05=finalScore,
                rankNo=rankNo,
            )
        )
    return topIssues


def _countSavedSignalsBySource(scoredSignals: list) -> dict[str, int]:
    counter = Counter()
    for signal in scoredSignals or []:
        payload = getattr(signal, "scoringPayloadJson", None) or {}
        source = payload.get("source") or getattr(signal, "sourceType", None)
        if source:
            counter[str(source)] += 1
    return dict(counter)


def _score10(score05):
    return round(score05 * SCORE_UI_MULTIPLIER, 2) if score05 is not None else None


def _replaceMediaNewsShadowFromPipelineResults(runId: int, pipelineResults: list) -> None:
    shadowFacts = step0NormalizeMediaFacts(pipelineResults)
    factPayloads = [
        step0BuildFactTrace(extractedFact=fact, sourceChannel="media_external")
        for fact in shadowFacts
    ]
    canonicalPayloads = step1BuildMediaNewsCanonicalPayloads(
        shadowFacts,
        evaluationDate=date.today().isoformat(),
    )
    step4ReplaceMediaNewsShadowBundleTx(
        runId=runId,
        factPayloads=factPayloads,
        canonicalPayloads=canonicalPayloads,
    )


def _isCrawlComplete(crawlResult) -> bool:
    if not crawlResult.allowedSources:
        return False
    if crawlResult.errors:
        return False
    return bool(crawlResult.sourceBreakdown) and all(
        item.status == "SUCCESS" for item in crawlResult.sourceBreakdown
    )


def _parseRequestDate(value: str, fieldName: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"{fieldName} must use YYYY-MM-DD format.") from exc
