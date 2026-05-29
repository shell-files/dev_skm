from pydantic import BaseModel
from typing import List, Optional, Literal


class CoverageDto(BaseModel):
    impactObservedStages: List[str] = []
    financialObservedStages: List[str] = []
    impactCoverageStatus: str = "NO_DATA"
    financialCoverageStatus: str = "NO_DATA"
    benchmarkObserved: bool = False
    mediaObserved: bool = False
    surveyObserved: bool = False


class SubIssueBaseDto(BaseModel):
    subIssueCode: str
    displaySubIssueName: str
    domain: Optional[str] = None
    issueGroup: Optional[str] = None
    issueGroupCode: Optional[str] = None
    rankNo: Optional[int] = None
    selectedYn: bool = False
    quadrant: Optional[str] = None


class MaterialityResultItemDto(SubIssueBaseDto):
    benchmarkImpactScore05: Optional[float] = None
    benchmarkImpactScore10: Optional[float] = None
    benchmarkFinancialScore05: Optional[float] = None
    benchmarkFinancialScore10: Optional[float] = None
    mediaImpactScore05: Optional[float] = None
    mediaImpactScore10: Optional[float] = None
    mediaFinancialScore05: Optional[float] = None
    mediaFinancialScore10: Optional[float] = None
    surveyImpactScore05: Optional[float] = None
    surveyImpactScore10: Optional[float] = None
    surveyFinancialScore05: Optional[float] = None
    surveyFinancialScore10: Optional[float] = None
    finalImpactScore05: Optional[float] = None
    finalImpactScore10: Optional[float] = None
    finalFinancialScore05: Optional[float] = None
    finalFinancialScore10: Optional[float] = None
    finalScore05: Optional[float] = None
    finalScore10: Optional[float] = None
    coverage: CoverageDto


class MatrixItemDto(BaseModel):
    subIssueCode: str
    displaySubIssueName: str
    domain: Optional[str] = None
    issueGroup: Optional[str] = None
    issueGroupCode: Optional[str] = None
    xFinancialScore10: Optional[float] = None
    yImpactScore10: Optional[float] = None
    finalScore10: Optional[float] = None
    rankNo: Optional[int] = None
    selectedYn: bool = False
    quadrant: Optional[str] = None


class TopIssueDto(SubIssueBaseDto):
    finalImpactScore05: Optional[float] = None
    finalImpactScore10: Optional[float] = None
    finalFinancialScore05: Optional[float] = None
    finalFinancialScore10: Optional[float] = None
    finalScore05: Optional[float] = None
    finalScore10: Optional[float] = None
    summary: Optional[str] = None
    reportPage: Optional[int] = None
    coverage: Optional[CoverageDto] = None


class SelectionReasonDto(BaseModel):
    subIssueCode: str
    displaySubIssueName: str
    rankNo: Optional[int] = None
    selectedYn: bool
    selectionType: str
    selectionReason: Optional[str] = None
    selectionSource: Literal["TABLE", "RANK_FALLBACK"]
    fallbackYn: bool


class NextStepDto(BaseModel):
    selectedIssueCount: int
    requiredMetricCount: int
    onboardingMissingCount: int
    reportDraftReadyYn: bool
    reportRunId: Optional[int] = None
    nextAction: str
    selectionSource: Literal["TABLE", "RANK_FALLBACK"]
    fallbackYn: bool


class CoverageSummaryDto(BaseModel):
    fullCount: int = 0
    partialCount: int = 0
    limitedCount: int = 0
    noDataCount: int = 0


class MaterialityResultsResponseDto(BaseModel):
    runId: int
    totalCandidateSubIssueCount: int
    summaryRowCount: int
    scoredSubIssueCount: int
    selectedSubIssueCount: int
    highPriorityCount: int
    selectionSource: Literal["TABLE", "RANK_FALLBACK"]
    fallbackYn: bool
    items: List[MaterialityResultItemDto]
    matrixItems: List[MatrixItemDto]
    topIssues: List[TopIssueDto]
    selectionReasons: List[SelectionReasonDto]
    nextStep: NextStepDto
    coverageSummary: CoverageSummaryDto


class BenchmarkSummaryDto(BaseModel):
    analyzedReportCount: int = 0
    leaderReportCount: int = 0
    peerReportCount: int = 0
    ownReportCount: int = 0
    identifiedIssueCount: int = 0
    commonIssueCount: int = 0
    blindSpotCount: int = 0


class BenchmarkTopIssueDto(SubIssueBaseDto):
    benchmarkImpactScore05: Optional[float] = None
    benchmarkImpactScore10: Optional[float] = None
    benchmarkFinancialScore05: Optional[float] = None
    benchmarkFinancialScore10: Optional[float] = None
    benchmarkAvgScore05: Optional[float] = None
    benchmarkAvgScore10: Optional[float] = None
    leaderObserved: bool = False
    peerObserved: bool = False
    ownObserved: bool = False
    evidenceCount: int = 0


class BenchmarkObservationIssueDto(SubIssueBaseDto):
    leaderObserved: bool = False
    peerObserved: bool = False
    ownObserved: bool = False
    leaderEvidenceCount: int = 0
    peerEvidenceCount: int = 0
    ownEvidenceCount: int = 0
    blindSpotYn: bool = False
    summary: Optional[str] = None


class BenchmarkResponseDto(BaseModel):
    runId: int
    summary: BenchmarkSummaryDto
    topIssues: List[BenchmarkTopIssueDto]
    commonIssues: List[BenchmarkObservationIssueDto]
    blindSpotIssues: List[BenchmarkObservationIssueDto]
    evidenceSummary: dict


class MediaSummaryDto(BaseModel):
    articleCount: int = 0
    agencyCount: int = 0
    regulationFrameCount: int = 0
    observedSubIssueCount: int = 0


class SourceBreakdownDto(BaseModel):
    sourceType: str
    sourceLabel: str
    collectedCount: int = 0
    observedIssueCount: int = 0
    appliedMethod: str


class MediaTopIssueDto(SubIssueBaseDto):
    mediaImpactScore05: Optional[float] = None
    mediaImpactScore10: Optional[float] = None
    mediaFinancialScore05: Optional[float] = None
    mediaFinancialScore10: Optional[float] = None
    mediaAvgScore05: Optional[float] = None
    mediaAvgScore10: Optional[float] = None
    sourceTypes: List[str] = []
    evidenceCount: int = 0


class EvidenceSampleDto(BaseModel):
    evidenceId: int
    subIssueCode: Optional[str] = None
    sourceType: str
    sourceTitle: Optional[str] = None
    sourceUrl: Optional[str] = None
    publishedAt: Optional[str] = None
    textSpan: Optional[str] = None


class MediaStageResponseDto(BaseModel):
    runId: int
    summary: MediaSummaryDto
    sourceBreakdown: List[SourceBreakdownDto]
    topIssues: List[MediaTopIssueDto]
    evidenceSamples: List[EvidenceSampleDto]
    coverage: dict


class SurveySummaryDto(BaseModel):
    employeeRespondentCount: int = 0
    managementRespondentCount: int = 0
    externalRespondentCount: int = 0
    totalRespondentCount: int = 0
    employeeTargetCount: int = 150
    managementTargetCount: int = 20
    externalTargetCount: int = 80
    employeeResponseRate: Optional[float] = None
    managementResponseRate: Optional[float] = None
    externalResponseRate: Optional[float] = None
    totalResponseRate: Optional[float] = None
    targetSource: str = "MVP_DEFAULT"


class SurveyGroupBreakdownDto(BaseModel):
    respondentGroup: str
    respondentGroupLabel: str
    respondentCount: int
    targetCount: int
    responseRate: Optional[float] = None


class SurveyTopIssueDto(SubIssueBaseDto):
    surveyImpactScore05: Optional[float] = None
    surveyImpactScore10: Optional[float] = None
    surveyFinancialScore05: Optional[float] = None
    surveyFinancialScore10: Optional[float] = None
    employeeImpactScore05: Optional[float] = None
    employeeImpactScore10: Optional[float] = None
    employeeFinancialScore05: Optional[float] = None
    employeeFinancialScore10: Optional[float] = None
    managementImpactScore05: Optional[float] = None
    managementImpactScore10: Optional[float] = None
    managementFinancialScore05: Optional[float] = None
    managementFinancialScore10: Optional[float] = None
    externalImpactScore05: Optional[float] = None
    externalImpactScore10: Optional[float] = None
    externalFinancialScore05: Optional[float] = None
    externalFinancialScore10: Optional[float] = None


class SurveyResponseDto(BaseModel):
    runId: int
    summary: SurveySummaryDto
    groupBreakdown: List[SurveyGroupBreakdownDto]
    topIssues: List[SurveyTopIssueDto]
    responseQuality: dict
    summaryText: str
    axisSeparatedYn: bool = False
    targetSource: str = "MVP_DEFAULT"


class SelectionProcessResponseDto(BaseModel):
    runId: int
    candidateCount: int
    scoredCount: int
    selectedCount: int
    selectionSource: Literal["TABLE", "RANK_FALLBACK"]
    fallbackYn: bool
    selectionRules: dict
    selectedIssues: List[SelectionReasonDto]
    excludedIssues: List[SelectionReasonDto]
