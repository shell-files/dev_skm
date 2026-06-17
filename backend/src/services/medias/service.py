from collections import Counter
from datetime import date
from typing import Optional

from src.models.media import (
    MediaAnalyzeResponse,
    MediaNewsCrawlAnalyzeRequest,
    MediaNewsCrawlAnalyzeResponse,
    MediaTopIssue,
)
from src.models.model import UserModel
from src.services.medias.adapter import convertMediaToDmaSignals, step0NormalizeMediaFacts
from src.services.medias.baseline import applyMediaBaseline
from src.services.medias.crawler import applySavedSignalCounts, crawlNewsArticles
from src.services.medias.pg_pipeline import fetchMediaChunksFromPg
from src.services.medias.pipeline import processMediaPipeline
from src.utils.settings import settings
from src.services.materialities.orchestrator import (
    step0BuildFactTrace,
    step1BuildMediaNewsCanonicalPayloads,
    step2BuildKcgsPillarBoostPayloads,
    step2BuildMediaExternalMaxPayloads,
    step2BuildRegulationScreeningPayloads,
)
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
from src.models.dmaengine import KcgsGradeInputV13
from src.models.dmakcgsgrade import KcgsGradeSaveRequest
from src.utils.dmascoring import SCORE_UI_MULTIPLIER, scoreSignals
from src.repositories.dmaworkflowrepository import upsertDmaWorkflowStatus
from src.utils.subissuemaster import getSubIssueDisplayName
from src.services.surveys.formservice import ensureSurveyFormForRun


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
    """
    S5-B16: 미디어 분석 진행 상태를 ESG_DMA_WORKFLOW_STATUS(workflow_type='MEDIA')에 기록한다.
    벤치마킹(_writeBenchmarkWorkflowStatus)과 동일한 polling 구조를 위해 단계별로 호출된다.
    산식/스코어링에는 관여하지 않으며 진행 상태만 기록한다.

    진행 상태 기록은 보조적이므로 best-effort 로 처리한다. status write 실패가
    미디어 분석 critical path(크롤링/shadow/external max)를 중단시켜서는 안 된다.
    """
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


def runMediaAnalysis(
    articles: list,
    runId: int,
    keywords: Optional[list[str]] = None,
    industryKeywords: Optional[list[str]] = None,
    shadowReplaceYn: bool = True,
    usePgPipeline: Optional[bool] = None,
):
    """
    미디어 언론 분석 전체 워크플로우를 실행합니다.
    기존 POST /media/news/analyze smoke/fallback API가 사용하므로 request 구조는 유지합니다.
    """
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
        # News canonical shadow replace 는 보조 경로다. canonical builder / bundle TX 실패가
        # smoke/fallback 분석(scoredSignals 저장·반환)을 중단시켜서는 안 된다. 실패는 경고로만
        # 남기고 분석 응답은 유지한다. (산식/summary/regulation/KCGS/external max 미변경)
        try:
            _replaceMediaNewsShadowFromPipelineResults(runId=runId, pipelineResults=pipelineResults)
        except Exception as shadowError:
            print(f"Warning: media news shadow replace skipped: {shadowError}")

    return scoredSignals


def buildMediaAnalyzeResponse(
    runId: int,
    articleCount: int,
    savedSignalCount: int,
) -> MediaAnalyzeResponse:
    coverageInfo = getMediaCoverage(runId)
    return MediaAnalyzeResponse(
        articleCount=articleCount,
        observedSubIssueCount=countMediaSubIssues(runId),
        savedSignalCount=savedSignalCount,
        topIssues=_buildMediaTopIssues(runId),
        coverageStatus=coverageInfo["coverageStatus"],
        coverageDetail=coverageInfo,
    )


def _runMediaCrawlAndAnalyzePg(request: MediaNewsCrawlAnalyzeRequest) -> MediaNewsCrawlAnalyzeResponse:
    runId = request.runId
    currentStage = "PREPARE"
    currentProgress = 10
    _writeMediaWorkflowStatus(
        runId=runId,
        overallStatus="RUNNING",
        currentStage=currentStage,
        progressPercent=currentProgress,
        startedYn=True,
    )

    try:
        currentStage = "NEWS_ANALYSIS"
        currentProgress = 55
        _writeMediaWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )
        scoredSignals = runMediaAnalysis(
            articles=[],
            runId=request.runId,
            keywords=MVP_DEMO_COMPANY_KEYWORDS,
            industryKeywords=MVP_DEMO_INDUSTRY_KEYWORDS,
            shadowReplaceYn=True,
            usePgPipeline=True,
        )

        # Regulation/KCGS shadow refresh: best-effort, 실패해도 분석 결과는 보존한다.
        # ExternalMax/Summary/Final/Rank는 materiality 전체 사이클 완료 후에만 유효하므로
        # PG 모드에서는 재계산하지 않는다(기존 랭크를 그대로 사용).
        currentStage = "REGULATION_REFRESH"
        currentProgress = 70
        _writeMediaWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )
        try:
            refreshRegulationShadowForRun(request.runId)
        except Exception as _exc:
            print(f"Warning: [pg_media] regulation shadow refresh skipped: {_exc}")

        currentStage = "KCGS_REFRESH"
        currentProgress = 80
        _writeMediaWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )
        try:
            refreshKcgsShadowForRun(request.runId)
        except Exception as _exc:
            print(f"Warning: [pg_media] kcgs shadow refresh skipped: {_exc}")

        # PG 모드는 External MAX/Rank 를 재계산하지 않지만, 전체 사이클에서 이미 산정된
        # 랭크가 있으면 그 기준으로 설문 폼(Top20, 최대 20개)을 생성한다.
        # 랭크가 0개면(아직 산정 전) 폼 생성을 건너뛰고 분석은 정상 완료시킨다.
        if countTop20RankedSubIssues(request.runId) >= 1:
            currentStage = "SURVEY_FORM_FREEZE"
            currentProgress = 95
            _writeMediaWorkflowStatus(
                runId=runId,
                overallStatus="RUNNING",
                currentStage=currentStage,
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
            runId=runId,
            overallStatus="COMPLETED",
            currentStage=currentStage,
            progressPercent=currentProgress,
            completedYn=True,
        )
        return response
    except Exception as e:
        _recordMediaWorkflowFailureBestEffort(
            runId=runId,
            currentStage=currentStage,
            progressPercent=currentProgress,
            error=e,
        )
        raise


def runMediaCrawlAndAnalyze(
    request: MediaNewsCrawlAnalyzeRequest, userModel: UserModel
) -> MediaNewsCrawlAnalyzeResponse:
    if _resolvePgMode(request.usePgPipeline):
        return _runMediaCrawlAndAnalyzePg(request)

    # 입력 검증은 workflow status 기록 이전에 수행한다. (잘못된 날짜는 400으로 처리하고
    # MEDIA workflow row 를 생성하지 않는다.)
    dateFrom = _parseRequestDate(request.dateFrom, "dateFrom")
    dateTo = _parseRequestDate(request.dateTo, "dateTo")
    if dateFrom > dateTo:
        raise ValueError("dateFrom must be earlier than or equal to dateTo.")

    # S5-B16: MEDIA workflow 진행 상태를 단계별로 기록한다. (벤치마킹과 동일한 polling 구조)
    runId = request.runId
    currentStage = "PREPARE"
    currentProgress = 10
    _writeMediaWorkflowStatus(
        runId=runId,
        overallStatus="RUNNING",
        currentStage=currentStage,
        progressPercent=currentProgress,
        startedYn=True,
    )

    try:
        resetMediaData(runId)

        currentStage = "NEWS_CRAWL"
        currentProgress = 30
        _writeMediaWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
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
                runId=runId,
                overallStatus="RUNNING",
                currentStage=currentStage,
                progressPercent=currentProgress,
            )
            scoredSignals = runMediaAnalysis(
                articles=crawlResult.articles,
                runId=request.runId,
                keywords=MVP_DEMO_COMPANY_KEYWORDS,
                industryKeywords=MVP_DEMO_INDUSTRY_KEYWORDS,
                shadowReplaceYn=crawlCompleteYn,
            )
            savedSignalCountsBySource = _countSavedSignalsBySource(scoredSignals)
        elif crawlCompleteYn:
            # Complete crawl with no articles — empty-clear is critical path.
            # Failure propagates; External MAX must not run against a stale news shadow.
            _replaceMediaNewsShadowFromPipelineResults(runId=request.runId, pipelineResults=[])

        # Refresh Regulation and KCGS source shadows — run regardless of crawl result.
        _shadowRefreshErrors: list[tuple[str, Exception]] = []

        currentStage = "REGULATION_REFRESH"
        currentProgress = 70
        _writeMediaWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )

        try:
            refreshRegulationShadowForRun(request.runId)
        except Exception as _exc:
            _shadowRefreshErrors.append(("regulation", _exc))

        currentStage = "KCGS_REFRESH"
        currentProgress = 80
        _writeMediaWorkflowStatus(
            runId=runId,
            overallStatus="RUNNING",
            currentStage=currentStage,
            progressPercent=currentProgress,
        )

        try:
            refreshKcgsShadowForRun(request.runId)
        except Exception as _exc:
            _shadowRefreshErrors.append(("kcgs", _exc))

        # External MAX is gated on news canonical freshness (crawlCompleteYn).
        # Partial/failed crawl: skip External MAX; existing Summary/Final/Rank preserved unchanged.
        if crawlCompleteYn:
            if _shadowRefreshErrors:
                raise RuntimeError(
                    "media_external source refresh failed; externalMax summary update aborted: "
                    + "; ".join(f"{k}: {v}" for k, v in _shadowRefreshErrors)
                )
            currentStage = "EXTERNAL_MAX_SUMMARY"
            currentProgress = 95
            _writeMediaWorkflowStatus(
                runId=runId,
                overallStatus="RUNNING",
                currentStage=currentStage,
                progressPercent=currentProgress,
            )
            # media_external External MAX Shadow + Summary + Final + Rank — critical path.
            refreshMediaExternalMaxForRun(request.runId)
            # 폼은 랭크가 1개 이상일 때만 생성한다. 이번 run 의 신호가 비어
            # refresh 결과 랭크가 0개로 재계산되면(크롤 0건 + 규제/KCGS 미승인 등),
            # 폼 생성을 건너뛰고 미디어 분석은 정상 완료시킨다.
            # (got 0 으로 미디어 워크플로 전체를 FAILED 시키지 않는다.)
            if countTop20RankedSubIssues(request.runId) >= 1:
                ensureSurveyFormForRun(request.runId)
        else:
            # 크롤 미완료(기사 0건 등)로 External MAX 재계산은 건너뛰지만,
            # 이미 랭크된 서브이슈가 있으면 그 기존 랭크 기준으로 설문 폼을 생성한다.
            # Top20 은 최대 20개이며, 20개 미만이어도 현재 랭크 기준으로 생성한다.
            # (점수는 덮어쓰지 않고, 폼 freeze 만 별도로 수행)
            if countTop20RankedSubIssues(request.runId) >= 1:
                currentStage = "SURVEY_FORM_FREEZE"
                currentProgress = 95
                _writeMediaWorkflowStatus(
                    runId=runId,
                    overallStatus="RUNNING",
                    currentStage=currentStage,
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
            runId=runId,
            overallStatus="COMPLETED",
            currentStage=currentStage,
            progressPercent=currentProgress,
            completedYn=True,
        )

        return response
    except Exception as e:
        _recordMediaWorkflowFailureBestEffort(
            runId=runId,
            currentStage=currentStage,
            progressPercent=currentProgress,
            error=e,
        )
        raise


def _buildMediaTopIssues(runId: int) -> list[MediaTopIssue]:
    topIssues = []
    for row in listTopMediaIssues(runId, limit=5):
        code = row.get("sub_issue_code", "")
        mediaImp = _safeFloatOrNone(row.get("media_external_impact_score"))
        mediaFin = _safeFloatOrNone(row.get("media_external_financial_score"))
        mediaAvg = _safeFloatOrNone(row.get("media_avg_score"))
        finalScore = _safeFloatOrNone(row.get("final_score"))
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


def _safeFloatOrNone(value):
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


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


def refreshRegulationShadowForRun(runId: int) -> int:
    """
    Refresh the media_external.regulation Shadow set for a materiality run.

    Independent of the news crawl result. Reads the run's company/year, the APPROVED
    applicability inputs and the APPROVED + active regime→sub-issue mappings, rebuilds
    the regulation screening payloads via the pure orchestrator builder, then replaces
    the active regulation shadow rows within a single transaction.

    Empty approved input or empty active mapping yields payloads=[], which is a valid
    empty-clear (prior active regulation shadow rows are soft-deleted, nothing inserted).
    Returns the number of regulation shadow rows persisted.
    """
    runContext = findRegulationRunContext(runId)
    companyId = runContext["companyId"]
    reportingYear = runContext["reportingYear"]

    approvedInputs = listApprovedRegulationInputs(companyId, reportingYear)
    approvedMappings = listApprovedActiveRegulationMappings()

    payloads = step2BuildRegulationScreeningPayloads(approvedInputs, approvedMappings)

    return step4ReplaceRegulationShadowTracesTx(runId, payloads)


def refreshMediaExternalMaxForRun(runId: int) -> int:
    """
    Refresh the External MAX Shadow, Summary, Final, and Rank for a materiality run.
    Reads eligible shadow rows (news canonical + regulation + KCGS domain signal),
    builds External MAX Audit payloads via the pure orchestrator builder, then replaces
    the active External MAX shadow and updates Summary / Final / Rank within a single
    transaction. Critical path: any failure raises RuntimeError.
    Returns the number of External MAX shadow rows persisted.
    """
    rows = listExternalMaxEligibleMediaRows(runId)
    payloads = step2BuildMediaExternalMaxPayloads(rows)
    return step4ReplaceMediaExternalMaxShadowAndSummaryTx(runId, payloads)


def refreshKcgsShadowForRun(runId: int) -> int:
    """
    Refresh the media_external.agency.kcgs Shadow set for a materiality run.

    Reads APPROVED latest 3-year KCGS grade inputs for the run company, rebuilds
    pillar boost metadata traces via the pure orchestrator builder, then replaces
    the active KCGS shadow rows in one transaction. Empty approved input yields a
    valid empty-clear. Partial or non-consecutive APPROVED input fails before the
    writer is called.
    """
    runContext = findRegulationRunContext(runId)
    companyId = runContext["companyId"]

    gradeRows = listApprovedKcgsGradeInputs(companyId)
    payloads = step2BuildKcgsPillarBoostPayloads(gradeRows)

    return step4ReplaceKcgsShadowTracesTx(runId, payloads)


def saveKcgsGradeInputs(request: KcgsGradeSaveRequest, userModel) -> int:
    """
    모달에서 입력한 KCGS 등급(정확히 3개 연속 연도)을 APPROVED 로 저장한다.
    저장 전, 미디어 분석이 실제로 쓰는 동일 빌더(step2BuildKcgsPillarBoostPayloads)로
    fail-closed 검증한다. (3개·연속연도·단일회사·유효등급) 검증 통과 시에만 DB 반영.
    이후 미디어 분석을 다시 실행하면 refreshKcgsShadowForRun 이 이 행들을 읽어 점수에 반영한다.
    """
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

    # 저장 전 검증: 등급 유효성/연속연도/3개/단일회사 — 실패 시 ValueError -> 400
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
