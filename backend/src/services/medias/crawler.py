from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from src.models.media import MediaCrawlerError, MediaRejectedSource, MediaSourceBreakdown
from src.services.medias.crawlers.base import NewsArticle, normalizeUrl, parseKoreanNewsDate
from src.services.medias.crawlers.esgeconomy import EsgEconomyCrawler
from src.services.medias.crawlers.impacton import ImpactOnCrawler


MEDIA_NEWS_SOURCE_REGISTRY = {
    "impacton": {
        "label": "임팩트온",
        "enabled": True,
        "mvpFixedScope": True,
        "crawler": ImpactOnCrawler,
    },
    "esgeconomy": {
        "label": "ESG경제",
        "enabled": True,
        "mvpFixedScope": True,
        "crawler": EsgEconomyCrawler,
    },
}


@dataclass
class CrawlExecutionResult:
    requestedSources: list[str]
    allowedSources: list[str] = field(default_factory=list)
    rejectedSources: list[MediaRejectedSource] = field(default_factory=list)
    sourceBreakdown: list[MediaSourceBreakdown] = field(default_factory=list)
    articles: list[dict] = field(default_factory=list)
    collectedArticleCount: int = 0
    filteredArticleCount: int = 0
    errors: list[MediaCrawlerError] = field(default_factory=list)


def crawlNewsArticles(
    sources: list[str],
    dateFrom: date,
    dateTo: date,
    companyKeywords: list[str],
    industryKeywords: list[str],
) -> CrawlExecutionResult:
    requestedSources = sources or []
    result = CrawlExecutionResult(requestedSources=requestedSources)
    executableSources = _validateSources(requestedSources, result)
    seenUrls: set[str] = set()

    for sourceKey in executableSources:
        registryItem = MEDIA_NEWS_SOURCE_REGISTRY[sourceKey]
        sourceLabel = registryItem["label"]
        crawlerClass = registryItem["crawler"]
        collectedCount = 0
        filteredArticles = []
        errorMessages = []
        status = "SUCCESS"

        try:
            crawler = crawlerClass()
            crawlerResult = crawler.crawl(dateFrom=dateFrom)
            collectedCount = len(crawlerResult.articles)
            result.collectedArticleCount += collectedCount

            for crawlerError in crawlerResult.errors:
                message = crawlerError.message
                errorMessages.append(message)
                result.errors.append(
                    MediaCrawlerError(
                        sourceKey=sourceKey,
                        message=message,
                        recoverableYn=crawlerError.recoverableYn,
                    )
                )

            dateParseFailedCount = 0
            for article in crawlerResult.articles:
                articleDate = _getArticleDate(article)
                if articleDate is None:
                    dateParseFailedCount += 1
                    continue
                if articleDate < dateFrom or articleDate > dateTo:
                    continue
                if not _matchesAnyKeyword(article, companyKeywords + industryKeywords):
                    continue

                normalizedUrl = normalizeUrl(article.url)
                if not normalizedUrl or normalizedUrl in seenUrls:
                    continue

                seenUrls.add(normalizedUrl)
                article.url = normalizedUrl
                filteredArticles.append(article.toPipelineDict())

            if dateParseFailedCount:
                errorMessages.append(f"dateParseFailedCount={dateParseFailedCount}")
                result.errors.append(
                    MediaCrawlerError(
                        sourceKey=sourceKey,
                        message=f"dateParseFailedCount={dateParseFailedCount}",
                        recoverableYn=True,
                    )
                )

            if errorMessages:
                status = "PARTIAL_FAILED" if filteredArticles else "FAILED"

            result.articles.extend(filteredArticles)
            result.filteredArticleCount += len(filteredArticles)
            result.allowedSources.append(sourceKey)
            result.sourceBreakdown.append(
                MediaSourceBreakdown(
                    sourceKey=sourceKey,
                    sourceLabel=sourceLabel,
                    requestedYn=True,
                    executedYn=True,
                    collectedCount=collectedCount,
                    filteredCount=len(filteredArticles),
                    savedSignalCount=0,
                    status=status,
                    errorMessage="; ".join(errorMessages) if errorMessages else None,
                )
            )

        except Exception as exc:
            result.allowedSources.append(sourceKey)
            result.errors.append(
                MediaCrawlerError(sourceKey=sourceKey, message=str(exc), recoverableYn=True)
            )
            result.sourceBreakdown.append(
                MediaSourceBreakdown(
                    sourceKey=sourceKey,
                    sourceLabel=sourceLabel,
                    requestedYn=True,
                    executedYn=True,
                    collectedCount=collectedCount,
                    filteredCount=0,
                    savedSignalCount=0,
                    status="FAILED",
                    errorMessage=str(exc),
                )
            )

    return result


def applySavedSignalCounts(
    sourceBreakdown: list[MediaSourceBreakdown],
    savedSignalCountsBySource: dict[str, int],
) -> list[MediaSourceBreakdown]:
    updated = []
    for item in sourceBreakdown:
        savedCount = savedSignalCountsBySource.get(item.sourceKey, 0)
        updated.append(item.model_copy(update={"savedSignalCount": savedCount}))
    return updated


def _validateSources(requestedSources: list[str], result: CrawlExecutionResult) -> list[str]:
    executableSources = []
    seen = set()
    for sourceKey in requestedSources:
        if sourceKey in seen:
            result.rejectedSources.append(
                MediaRejectedSource(
                    sourceKey=sourceKey,
                    reason="DUPLICATE_REQUEST",
                    message="Duplicate source is executed only once.",
                )
            )
            result.sourceBreakdown.append(_skippedBreakdown(sourceKey, "중복 요청 source입니다."))
            continue
        seen.add(sourceKey)

        registryItem = MEDIA_NEWS_SOURCE_REGISTRY.get(sourceKey)
        if registryItem is None:
            result.rejectedSources.append(
                MediaRejectedSource(
                    sourceKey=sourceKey,
                    reason="NOT_REGISTERED",
                    message="MVP allows only impacton and esgeconomy.",
                )
            )
            result.sourceBreakdown.append(_skippedBreakdown(sourceKey, "MVP 허용 source가 아닙니다."))
            continue

        if not registryItem.get("enabled", False):
            result.rejectedSources.append(
                MediaRejectedSource(
                    sourceKey=sourceKey,
                    reason="DISABLED",
                    message="Source is disabled in registry.",
                )
            )
            result.sourceBreakdown.append(
                _skippedBreakdown(sourceKey, "비활성화된 source입니다.", registryItem.get("label", sourceKey))
            )
            continue

        executableSources.append(sourceKey)

    return executableSources


def _skippedBreakdown(
    sourceKey: str,
    errorMessage: str,
    sourceLabel: Optional[str] = None,
) -> MediaSourceBreakdown:
    return MediaSourceBreakdown(
        sourceKey=sourceKey,
        sourceLabel=sourceLabel or sourceKey,
        requestedYn=True,
        executedYn=False,
        collectedCount=0,
        filteredCount=0,
        savedSignalCount=0,
        status="SKIPPED",
        errorMessage=errorMessage,
    )


def _getArticleDate(article: NewsArticle) -> Optional[date]:
    parsed = parseKoreanNewsDate(article.publishedAt or "")
    if parsed is not None:
        return parsed
    return parseKoreanNewsDate(article.rawDateText or "")


def _matchesAnyKeyword(article: NewsArticle, keywords: list[str]) -> bool:
    normalizedKeywords = [keyword.strip() for keyword in keywords if keyword and keyword.strip()]
    if not normalizedKeywords:
        return True

    textParts = [
        article.title or "",
        article.content or "",
        " ".join(article.paragraphs or []),
    ]
    haystack = " ".join(textParts).lower()
    return any(keyword.lower() in haystack for keyword in normalizedKeywords)
