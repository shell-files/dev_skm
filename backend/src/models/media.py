from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class MediaAnalyzeRequest(BaseModel):
    runId: int
    articles: list[dict[str, Any]]
    keywords: Optional[list[str]] = Field(default_factory=list)


class MediaTopIssue(BaseModel):
    subIssueCode: str
    displaySubIssueName: str
    mediaImpactScore05: Optional[float] = None
    mediaFinancialScore05: Optional[float] = None
    mediaImpactScore10: Optional[float] = None
    mediaFinancialScore10: Optional[float] = None
    mediaAvgScore05: Optional[float] = None
    mediaAvgScore10: Optional[float] = None
    finalScore05: Optional[float] = None
    rankNo: Optional[int] = None


class MediaAnalyzeResponse(BaseModel):
    articleCount: int
    observedSubIssueCount: int
    savedSignalCount: int
    topIssues: list[MediaTopIssue]
    coverageStatus: str
    coverageDetail: dict[str, Any]


class MediaNewsCrawlAnalyzeRequest(BaseModel):
    runId: int
    sources: list[str]
    dateFrom: str
    dateTo: str


class MediaRejectedSource(BaseModel):
    sourceKey: str
    reason: Literal["NOT_REGISTERED", "DISABLED", "DUPLICATE_REQUEST"]
    message: Optional[str] = None


class MediaCrawlerError(BaseModel):
    sourceKey: str
    message: str
    recoverableYn: bool = True


class MediaSourceBreakdown(BaseModel):
    sourceKey: str
    sourceLabel: str
    requestedYn: bool
    executedYn: bool
    collectedCount: int = 0
    filteredCount: int = 0
    savedSignalCount: int = 0
    status: Literal["SUCCESS", "PARTIAL_FAILED", "FAILED", "SKIPPED"]
    errorMessage: Optional[str] = None


class MediaNewsCrawlAnalyzeResponse(BaseModel):
    runId: int
    requestedSources: list[str]
    allowedSources: list[str]
    rejectedSources: list[MediaRejectedSource]
    companyKeywords: list[str]
    industryKeywords: list[str]
    keywordSource: Literal["MVP_SERVICE_CONSTANT"] = "MVP_SERVICE_CONSTANT"
    collectedArticleCount: int
    filteredArticleCount: int
    articleCount: int
    savedSignalCount: int
    observedSubIssueCount: int
    sourceBreakdown: list[MediaSourceBreakdown]
    topIssues: list[MediaTopIssue]
    coverage: dict[str, Any]
    coverageStatus: str
    errors: list[MediaCrawlerError]
