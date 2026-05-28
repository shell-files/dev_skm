from collections import Counter
from datetime import date
from typing import Optional

from src.models.media import (
    MediaAnalyzeResponse,
    MediaNewsCrawlAnalyzeRequest,
    MediaNewsCrawlAnalyzeResponse,
    MediaTopIssue,
)
from src.services.medias.adapter import convertMediaToDmaSignals
from src.services.medias.baseline import applyMediaBaseline
from src.services.medias.crawler import applySavedSignalCounts, crawlNewsArticles
from src.services.medias.pipeline import processMediaPipeline
from src.utils.dmarepository import (
    getMediaCoverageFromSummary,
    getMediaObservedSubIssueCount,
    getTopIssuesByMediaScore,
    saveDmaSignals,
)
from src.utils.dmascoring import SCORE_UI_MULTIPLIER, scoreDmaSignals
from src.utils.subissuemaster import getSubIssueDisplayName


MVP_DEMO_COMPANY_KEYWORDS = ["현대자동차"]
MVP_DEMO_INDUSTRY_KEYWORDS = ["자동차부품산업"]


def runMediaAnalysis(
    articles: list,
    runId: int,
    keywords: Optional[list[str]] = None,
    industryKeywords: Optional[list[str]] = None,
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
    scoredSignals = scoreDmaSignals(baselinedSignals)

    if scoredSignals:
        saveDmaSignals(runId=runId, signals=scoredSignals, fileId=None, sourceTitle="Media Analysis")

    return scoredSignals


def buildMediaAnalyzeResponse(
    runId: int,
    articleCount: int,
    savedSignalCount: int,
) -> MediaAnalyzeResponse:
    coverageInfo = getMediaCoverageFromSummary(runId)
    return MediaAnalyzeResponse(
        articleCount=articleCount,
        observedSubIssueCount=getMediaObservedSubIssueCount(runId),
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

    scoredSignals = []
    savedSignalCountsBySource = {}
    if crawlResult.articles:
        scoredSignals = runMediaAnalysis(
            articles=crawlResult.articles,
            runId=request.runId,
            keywords=MVP_DEMO_COMPANY_KEYWORDS,
            industryKeywords=MVP_DEMO_INDUSTRY_KEYWORDS,
        )
        savedSignalCountsBySource = _countSavedSignalsBySource(scoredSignals)

    sourceBreakdown = applySavedSignalCounts(
        crawlResult.sourceBreakdown,
        savedSignalCountsBySource,
    )
    coverageInfo = getMediaCoverageFromSummary(request.runId)
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
        observedSubIssueCount=getMediaObservedSubIssueCount(request.runId),
        sourceBreakdown=sourceBreakdown,
        topIssues=_buildMediaTopIssues(request.runId),
        coverage=coverageInfo,
        coverageStatus=coverageInfo["coverageStatus"],
        errors=crawlResult.errors,
    )


def _buildMediaTopIssues(runId: int) -> list[MediaTopIssue]:
    topIssues = []
    for row in getTopIssuesByMediaScore(runId, limit=5):
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


def _parseRequestDate(value: str, fieldName: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"{fieldName} must use YYYY-MM-DD format.") from exc
