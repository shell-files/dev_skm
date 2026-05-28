from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin
import re

from src.services.medias.crawlers.base import (
    BaseNewsCrawler,
    CrawlerError,
    NewsArticle,
    NewsCrawlerResult,
    cleanText,
    extractParagraphs,
    fetchHtml,
    normalizeUrl,
    parseKoreanNewsDate,
)


class EsgEconomyCrawler(BaseNewsCrawler):
    sourceKey = "esgeconomy"
    sourceLabel = "ESG경제"
    baseUrl = "https://www.esgeconomy.com/news/articleList.html?page={page}"
    maxPage = 30

    def crawl(self, dateFrom: Optional[date] = None) -> NewsCrawlerResult:
        result = NewsCrawlerResult(sourceKey=self.sourceKey, sourceLabel=self.sourceLabel)
        links = []
        stopCrawling = False

        for page in range(1, self.maxPage + 1):
            try:
                listHtml = fetchHtml(self.baseUrl.format(page=page))
            except Exception as exc:
                result.errors.append(CrawlerError(self.sourceKey, f"list page {page}: {exc}"))
                continue

            pageLinks = self._parseListPage(listHtml)
            if not pageLinks:
                break

            for item in pageLinks:
                articleDate = parseKoreanNewsDate(item.get("date", ""), currentYear=datetime.now().year)
                if dateFrom and articleDate and articleDate < dateFrom:
                    stopCrawling = True
                    break
                links.append(item)

            if stopCrawling:
                break

        seenUrls = set()
        for item in links:
            url = normalizeUrl(item.get("url", ""))
            if not url or url in seenUrls:
                continue
            seenUrls.add(url)

            try:
                detailHtml = fetchHtml(url)
                paragraphs = self._extractArticleParagraphs(detailHtml)
                if not paragraphs:
                    continue
                publishedDate = parseKoreanNewsDate(item.get("date", ""), currentYear=datetime.now().year)
                result.articles.append(
                    NewsArticle(
                        sourceKey=self.sourceKey,
                        sourceLabel=self.sourceLabel,
                        title=item.get("title", ""),
                        url=url,
                        publishedAt=publishedDate.isoformat() if publishedDate else "",
                        rawDateText=item.get("date", ""),
                        content="\n".join(paragraphs),
                        paragraphs=paragraphs,
                    )
                )
            except Exception as exc:
                result.errors.append(CrawlerError(self.sourceKey, f"article {url}: {exc}"))

        return result

    def _parseListPage(self, html: str) -> list[dict]:
        items = []
        for match in re.finditer(
            r"<a[^>]+href=[\"'](?P<href>[^\"']*articleView\.html[^\"']+)[\"'][^>]*>(?P<title>[\s\S]*?)</a>",
            html,
            flags=re.I,
        ):
            href = urljoin("https://www.esgeconomy.com", match.group("href"))
            title = cleanText(match.group("title"))
            contextStart = max(0, match.start() - 700)
            contextEnd = min(len(html), match.end() + 900)
            context = html[contextStart:contextEnd]
            dateMatch = re.search(
                r"(?:\d{4}\.)?\d{1,2}\.\d{1,2}\s+\d{1,2}:\d{1,2}",
                context,
            )
            if not title or not dateMatch:
                continue
            items.append({"title": title, "url": href, "date": dateMatch.group(0)})
        return self._dedupeItems(items)

    def _extractArticleParagraphs(self, html: str) -> list[str]:
        marker = re.search(
            r"<div[^>]*id=[\"']article-view-content-div[\"'][^>]*>(?P<body>[\s\S]*?)(?:<div[^>]+class=[\"']article-copy|</body>)",
            html,
            flags=re.I,
        )
        bodyHtml = marker.group("body") if marker else html
        excludeKeywords = ["무단전재", "재배포금지", "Copyright", "사진=", "제보"]
        return [
            paragraph
            for paragraph in extractParagraphs(bodyHtml, minLength=35)
            if not any(keyword in paragraph for keyword in excludeKeywords)
        ]

    def _dedupeItems(self, items: list[dict]) -> list[dict]:
        seen = set()
        deduped = []
        for item in items:
            url = normalizeUrl(item.get("url", ""))
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append({**item, "url": url})
        return deduped
