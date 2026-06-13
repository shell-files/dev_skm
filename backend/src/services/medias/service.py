from collections import Counter
from datetime import date
from typing import Optional

from src.models.media import (
    MediaAnalyzeResponse,
    MediaNewsCrawlAnalyzeRequest,
    MediaNewsCrawlAnalyzeResponse,
    MediaTopIssue,
)
from src.services.medias.adapter import convertMediaToDmaSignals, step0NormalizeMediaFacts
from src.services.medias.baseline import applyMediaBaseline
from src.services.medias.crawler import applySavedSignalCounts, crawlNewsArticles
from src.services.medias.pipeline import processMediaPipeline
from src.services.materialities.orchestrator import (
    step0BuildFactTrace,
    step1BuildMediaNewsCanonicalPayloads,
    step2BuildKcgsPillarBoostPayloads,
    step2BuildMediaExternalMaxPayloads,
    step2BuildRegulationScreeningPayloads,
)
from src.utils.dmarepository import (
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
)
from src.utils.dmascoring import SCORE_UI_MULTIPLIER, scoreSignals
from src.utils.subissuemaster import getSubIssueDisplayName
from src.services.surveys.formservice import ensureSurveyFormForRun


MVP_DEMO_COMPANY_KEYWORDS = ["현대자동차"]
MVP_DEMO_INDUSTRY_KEYWORDS = ["자동차부품산업"]


def runMediaAnalysis(
    articles: list,
    runId: int,
    keywords: Optional[list[str]] = None,
    industryKeywords: Optional[list[str]] = None,
    shadowReplaceYn: bool = True,
):
    """
    미디어 언론 분석 전체 워크플로우를 실행합니다.
    기존 POST /media/news/analyze smoke/fallback API가 사용하므로 request 구조는 유지합니다.
    """
    if keywords is None:
        keywords = []
    if industryKeywords is None:
        industryKeywords = []

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
        _replaceMediaNewsShadowFromPipelineResults(runId=runId, pipelineResults=pipelineResults)

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


def runMediaCrawlAndAnalyze(
    request: MediaNewsCrawlAnalyzeRequest,
) -> MediaNewsCrawlAnalyzeResponse:
    dateFrom = _parseRequestDate(request.dateFrom, "dateFrom")
    dateTo = _parseRequestDate(request.dateTo, "dateTo")
    if dateFrom > dateTo:
        raise ValueError("dateFrom must be earlier than or equal to dateTo.")

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

    try:
        refreshRegulationShadowForRun(request.runId)
    except Exception as _exc:
        _shadowRefreshErrors.append(("regulation", _exc))

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
        # media_external External MAX Shadow + Summary + Final + Rank — critical path.
        refreshMediaExternalMaxForRun(request.runId)
        ensureSurveyFormForRun(request.runId)

    sourceBreakdown = applySavedSignalCounts(
        crawlResult.sourceBreakdown,
        savedSignalCountsBySource,
    )
    coverageInfo = getMediaCoverage(request.runId)
    savedSignalCount = len(scoredSignals) if scoredSignals else 0

    return MediaNewsCrawlAnalyzeResponse(
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
