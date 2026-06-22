"""
base.py
레이어: Service (medias/crawlers)
역할: 미디어 크롤러 공통 기반 클래스 — HTML 파싱 및 뉴스 아이템 추상화.
"""
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
        """크롤링 결과를 파이프라인 처리용 딕셔너리로 변환한다."""
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
        """지정 날짜 이후 기사를 크롤링해 NewsCrawlerResult를 반환한다. 서브클래스에서 구현한다."""
        raise NotImplementedError

    def _dedupeItems(self, items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        deduped: list[dict] = []
        for item in items:
            url = normalizeUrl(item.get("url", ""))
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append({**item, "url": url})
        return deduped


def fetchHtml(url: str, timeout: int = 15) -> str:
    """지정 URL의 HTML을 HTTP GET으로 가져온다. Content-Type charset을 우선 적용하고 fallback은 utf-8이다."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def cleanText(value: str) -> str:
    """HTML에서 script/style/figure 태그와 모든 HTML 태그를 제거하고 공백을 정규화한다."""
    text = re.sub(r"<(script|style|figure)[\s\S]*?</\1>", " ", value, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalizeUrl(url: str) -> str:
    """URL에서 fragment(#)를 제거하고 끝의 슬래시를 정규화한다."""
    url, _fragment = urldefrag((url or "").strip())
    return url.rstrip("/")


def parseKoreanNewsDate(value: str, currentYear: Optional[int] = None) -> Optional[date]:
    """
    한국 뉴스 날짜 문자열을 date 객체로 파싱한다.
    YYYY-MM-DD, MM.DD HH:MM, MM.DD 형식을 순서대로 시도하며 연도 생략 시 currentYear를 사용한다.
    """
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
    """
    HTML에서 <p> 태그 내 텍스트를 추출하여 minLength 이상인 단락 목록을 반환한다.
    <p> 태그가 없으면 전체 텍스트를 정제하여 단락으로 반환한다.
    """
    paragraphs = []
    for raw in re.findall(r"<p[^>]*>([\s\S]*?)</p>", html, flags=re.I):
        text = cleanText(raw)
        if len(text) >= minLength:
            paragraphs.append(text)

    if paragraphs:
        return paragraphs

    text = cleanText(html)
    return [text] if len(text) >= minLength else []
