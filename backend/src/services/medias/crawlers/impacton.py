from __future__ import annotations

from datetime import date
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


class ImpactOnCrawler(BaseNewsCrawler):
    sourceKey = "impacton"
    sourceLabel = "임팩트온"
    baseUrl = (
        "https://www.impacton.net/news/articleList.html"
        "?page={page}&sc_sub_section_code=S2N14&view_type=sm"
    )
    maxPage = 3

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
                articleDate = parseKoreanNewsDate(item.get("date", ""))
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
                publishedDate = parseKoreanNewsDate(item.get("date", ""))
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
            href = urljoin("https://www.impacton.net", match.group("href"))
            title = cleanText(match.group("title"))
            context = html[match.start() : match.end() + 900]
            dateMatch = re.search(r"\d{4}\.\d{1,2}\.\d{1,2}(?:\s+\d{1,2}:\d{1,2})?", context)
            if not title or not dateMatch:
                continue
            items.append({"title": title, "url": href, "date": dateMatch.group(0)})
        return self._dedupeItems(items)

    def _extractArticleParagraphs(self, html: str) -> list[str]:
        marker = re.search(
            r"<article[^>]*id=[\"']article-view-content-div[\"'][^>]*>(?P<body>[\s\S]*?)</article>",
            html,
            flags=re.I,
        )
        bodyHtml = marker.group("body") if marker else html
        paragraphs = extractParagraphs(bodyHtml, minLength=20)
        return [
            paragraph
            for paragraph in paragraphs
            if "<임팩트온>은 지난주 지속가능경영" not in paragraph
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
