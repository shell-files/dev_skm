from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from html import unescape
from typing import Optional
from urllib.parse import urldefrag
from urllib.request import Request, urlopen
import re


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


@dataclass
class NewsArticle:
    sourceKey: str
    sourceLabel: str
    title: str
    url: str
    publishedAt: str
    content: str
    paragraphs: list[str] = field(default_factory=list)
    rawDateText: Optional[str] = None

    def toPipelineDict(self) -> dict:
        return {
            "source": self.sourceKey,
            "sourceType": "news",
            "sourceKey": self.sourceKey,
            "sourceLabel": self.sourceLabel,
            "title": self.title,
            "url": self.url,
            "publishedAt": self.publishedAt,
            "content": self.content,
            "paragraphs": self.paragraphs,
            "rawDateText": self.rawDateText,
        }


@dataclass
class CrawlerError:
    sourceKey: str
    message: str
    recoverableYn: bool = True


@dataclass
class NewsCrawlerResult:
    sourceKey: str
    sourceLabel: str
    articles: list[NewsArticle] = field(default_factory=list)
    errors: list[CrawlerError] = field(default_factory=list)


class BaseNewsCrawler:
    sourceKey: str
    sourceLabel: str

    def crawl(self, dateFrom: Optional[date] = None) -> NewsCrawlerResult:
        raise NotImplementedError


def fetchHtml(url: str, timeout: int = 15) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def cleanText(value: str) -> str:
    text = re.sub(r"<(script|style|figure)[\s\S]*?</\1>", " ", value, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalizeUrl(url: str) -> str:
    url, _fragment = urldefrag((url or "").strip())
    return url.rstrip("/")


def parseKoreanNewsDate(value: str, currentYear: Optional[int] = None) -> Optional[date]:
    text = (value or "").strip()
    if not text:
        return None

    currentYear = currentYear or datetime.now().year
    patterns = [
        (r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", False),
        (r"(\d{1,2})[.](\d{1,2})\s+\d{1,2}:\d{1,2}", True),
        (r"(\d{1,2})[.](\d{1,2})", True),
    ]
    for pattern, missingYear in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            if missingYear:
                month, day = int(match.group(1)), int(match.group(2))
                return date(currentYear, month, day)
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return date(year, month, day)
        except ValueError:
            return None
    return None


def extractParagraphs(html: str, minLength: int = 25) -> list[str]:
    paragraphs = []
    for raw in re.findall(r"<p[^>]*>([\s\S]*?)</p>", html, flags=re.I):
        text = cleanText(raw)
        if len(text) >= minLength:
            paragraphs.append(text)

    if paragraphs:
        return paragraphs

    text = cleanText(html)
    return [text] if len(text) >= minLength else []
