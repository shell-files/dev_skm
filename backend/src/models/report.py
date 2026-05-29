from pydantic import BaseModel
from typing import List, Literal, Optional


class ReportDraftSummaryDto(BaseModel):
    generatedPageCount: int = 0
    referencedKpiCount: int = 0
    evidenceLinkRate: float = 0.0
    revisionRequiredCount: int = 0


class ReportDraftParagraphDto(BaseModel):
    paragraphId: int
    draftId: int
    paragraphOrder: Optional[int] = None
    originalGeneratedText: str = ""
    editableText: str = ""
    editedText: Optional[str] = None
    approvalStatus: str = "draft"
    qaStatus: Optional[str] = None
    lastEditedAt: Optional[str] = None
    referencedMetricIds: List[str] = []
    traceAvailableYn: bool = False


class ReportDraftSectionDto(BaseModel):
    sectionId: str
    sectionCode: Optional[str] = None
    sectionTitle: str
    subIssueCode: Optional[str] = None
    displaySubIssueName: Optional[str] = None
    paragraphs: List[ReportDraftParagraphDto]


class DownloadOptionDto(BaseModel):
    fileType: Literal["pdf", "docx"]
    label: str
    availableYn: bool


class ReportDraftResponseDto(BaseModel):
    runId: int
    reportRunId: Optional[int] = None
    summary: ReportDraftSummaryDto
    sections: List[ReportDraftSectionDto]
    downloadOptions: List[DownloadOptionDto]
    implementationStatus: str = "SKELETON"
    missingSchemaFields: List[str] = []
    orderSource: str = "ID_ASC_FALLBACK"


class ReportDraftPatchRequestDto(BaseModel):
    editedText: str
    editComment: Optional[str] = None


class ReportDraftPatchResponseDto(BaseModel):
    draftId: int
    editStatus: str
    lastEditedAt: Optional[str] = None
    implementationStatus: str = "SKELETON"
    missingSchemaFields: List[str] = []


class ReportMetricTraceDto(BaseModel):
    metricId: Optional[str] = None
    atomicMetricId: Optional[str] = None
    metricName: Optional[str] = None
    atomicMetricName: Optional[str] = None
    unit: Optional[str] = None
    dataType: Optional[str] = None


class YearValueDto(BaseModel):
    year: int
    value: Optional[float | str] = None
    unit: Optional[str] = None
    approvalStatus: Optional[str] = None


class CompanyBreakdownDto(BaseModel):
    companyId: Optional[int] = None
    companyName: Optional[str] = None
    year: Optional[int] = None
    value: Optional[float | str] = None
    unit: Optional[str] = None
    contributionRate: Optional[float] = None


class RelatedParagraphDto(BaseModel):
    paragraphId: int
    sectionTitle: Optional[str] = None
    label: Optional[str] = None


class ReportTraceResponseDto(BaseModel):
    runId: int
    paragraphId: int
    traceType: Literal["DIRECT", "GROUP_ROLLUP", "UNKNOWN"]
    sourceModeLabel: str
    metrics: List[ReportMetricTraceDto]
    latestValue: Optional[float | str] = None
    valuesByYear: List[YearValueDto]
    companyBreakdown: List[CompanyBreakdownDto]
    calculationFormula: Optional[str] = None
    aiEvidenceSummary: Optional[str] = None
    relatedParagraphs: List[RelatedParagraphDto]
    implementationStatus: str = "SKELETON"
    missingSchemaFields: List[str] = []


class ReportDownloadRequestDto(BaseModel):
    fileType: Literal["pdf", "docx"]


class ReportDownloadResponseDto(BaseModel):
    runId: int
    reportRunId: Optional[int] = None
    fileType: Literal["pdf", "docx"]
    downloadUrl: Optional[str] = None
    expiresAt: Optional[str] = None
    availableYn: bool = False
    implementationStatus: str = "SKELETON"
    message: str
