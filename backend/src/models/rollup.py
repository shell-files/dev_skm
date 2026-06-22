<<<<<<< HEAD
"""
rollup.py
레이어: Model
역할: ESG 롤업 배치·요청·전송·기준값 관련 요청/응답 DTO 정의.
"""
=======
>>>>>>> origin/skm_test
from typing import Optional

from pydantic import BaseModel, Field

ROLLUP_PURPOSE_DMA_PRECHECK = "DMA_PRECHECK"
ROLLUP_PURPOSE_REPORT_DISCLOSURE = "REPORT_DISCLOSURE"

METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
METRIC_SCOPE_SELECTED_DISCLOSURE = "SELECTED_DISCLOSURE"
METRIC_SCOPE_ROLLUP = "ROLLUP_SCOPE"


class RollupBaseModel(BaseModel):
    def model_dump(self, *args, **kwargs):
        if hasattr(BaseModel, "model_dump"):
            return super().model_dump(*args, **kwargs)
        return self.dict(*args, **kwargs)


class RollupSubsidiaryDto(RollupBaseModel):
    companyId: int
    companyCode: Optional[str] = None
    companyName: Optional[str] = None


class RollupSubsidiaryListDto(RollupBaseModel):
    runId: Optional[int] = None
    sourceCycleId: Optional[int] = None
    items: list[RollupSubsidiaryDto]


class RollupSubsidiaryResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupSubsidiaryListDto


class RollupBatchRequestDto(RollupBaseModel):
    runId: Optional[int] = None
    sourceCycleId: Optional[int] = None
    sourceCompanyIds: list[int] = Field(..., min_length=1)
    rollupPurposeCode: str = ROLLUP_PURPOSE_DMA_PRECHECK
    metricScopeCode: str = METRIC_SCOPE_G0_02_FINANCIAL_BASIS


class RollupBatchStatusDto(RollupBaseModel):
    batchId: int
    runId: Optional[int] = None
    sourceCycleId: Optional[int] = None
    rollupPurposeCode: str
    metricScopeCode: str
    batchStatus: str
    dmaReadyYn: bool
    reportReadyYn: bool = False
    sourceCompanyIds: list[int]


class RollupBatchResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupBatchStatusDto


class RollupActiveBatchResponseDto(RollupBaseModel):
    success: bool = True
    data: Optional[RollupBatchStatusDto] = None


class RollupResultDto(RollupBaseModel):
    groupAtomicMetricId: str
    sourceAtomicMetricIds: list[str]
    sourceAtomicMetricId: Optional[str] = None
    formulaType: str
    valueNumeric: Optional[float | int] = None
    valueText: Optional[str] = None
    unit: Optional[str] = None
    sourceCompanyValues: Optional[dict] = None
    calculationWarnings: Optional[list[str]] = None
    calculationStatus: Optional[str] = None


class RollupCalculateStatusDto(RollupBatchStatusDto):
    results: list[RollupResultDto]
    warnings: list[dict] = Field(default_factory=list)


class RollupCalculateResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupCalculateStatusDto


class RollupRequestItemDto(RollupBaseModel):
    batchId: int
    batchCode: Optional[str] = None
    sourceCycleId: Optional[int] = None
    parentCompanyId: int
    parentCompanyCode: Optional[str] = None
    parentCompanyName: Optional[str] = None
    reportingYear: int
    rollupPurposeCode: str
    metricScopeCode: str
    requestStatus: str
    inputStatus: str
    approvalStatus: str
    transferStatus: str
    sendReadyYn: bool
    missingAtomicMetricIds: list[str]
    readinessStatus: str = "NOT_STARTED"
    currentApprovedAtomicCount: int = 0
    currentMissingAtomicCount: int = 0
    metricCount: int = 0
    requiredAtomicCount: int = 0
    approvedAtomicCount: int = 0
    missingAtomicCount: int = 0
    metricIds: list[str] = Field(default_factory=list)
    requestedMetricCount: int = 0
    requestedMetricIds: list[str] = Field(default_factory=list)
    resolvedMetricCount: int = 0
    resolvedMetricIds: list[str] = Field(default_factory=list)
    dependencyMetricIds: list[str] = Field(default_factory=list)


class RollupRequestListDto(RollupBaseModel):
    items: list[RollupRequestItemDto]


class RollupRequestResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupRequestListDto


class RollupRequestMetricItemDto(RollupBaseModel):
    metricId: str
    metricName: Optional[str] = None
    requiredAtomicCount: int = 0
    approvedAtomicCount: int = 0
    missingAtomicMetricIds: list[str] = Field(default_factory=list)


class RollupScopePreviewDto(RollupBaseModel):
    runId: Optional[int] = None
    sourceCycleId: Optional[int] = None
    parentCompanyId: int
    reportingYear: int
    rollupPurposeCode: str
    metricScopeCode: str
    metricCount: int
    metricIds: list[str]
    requiredAtomicCount: int
    requiredAtomicMetricIds: list[str]
    items: list[RollupRequestMetricItemDto] = Field(default_factory=list)


class RollupScopePreviewResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupScopePreviewDto



class RollupInputWorkspaceDto(RollupBaseModel):
    availableYn: bool
    cycleId: Optional[int] = None
    cycleType: Optional[str] = None
    reportingYear: int
    reason: Optional[str] = None


class RollupRequestDetailDto(RollupBaseModel):
    batchId: int
    batchCode: Optional[str] = None
    sourceCycleId: Optional[int] = None
    parentCompanyId: int
    parentCompanyCode: Optional[str] = None
    parentCompanyName: Optional[str] = None
    sourceCompanyId: int
    sourceCompanyCode: Optional[str] = None
    sourceCompanyName: Optional[str] = None
    reportingYear: int
    rollupPurposeCode: str
    metricScopeCode: str
    requestStatus: str
    inputStatus: str
    approvalStatus: str
    transferStatus: str
    sendReadyYn: bool
    readinessStatus: str = "NOT_STARTED"
    metricCount: int
    requiredAtomicCount: int
    approvedAtomicCount: int
    missingAtomicCount: int
    currentApprovedAtomicCount: int = 0
    currentMissingAtomicCount: int = 0
    missingAtomicMetricIds: list[str]
    metricIds: list[str]
    requestedMetricCount: int = 0
    requestedMetricIds: list[str] = Field(default_factory=list)
    resolvedMetricCount: int = 0
    resolvedMetricIds: list[str] = Field(default_factory=list)
    dependencyMetricIds: list[str] = Field(default_factory=list)
    actionableInputMetricIds: list[str] = Field(default_factory=list)
    inputWorkspace: RollupInputWorkspaceDto
    items: list[RollupRequestMetricItemDto] = Field(default_factory=list)
    dependencyItems: list[RollupRequestMetricItemDto] = Field(default_factory=list)


class RollupRequestDetailResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupRequestDetailDto


class RollupBatchSourceItemDto(RollupBaseModel):
    sourceCompanyId: int
    sourceCompanyCode: Optional[str] = None
    sourceCompanyName: Optional[str] = None
    requestStatus: str
    inputStatus: str
    approvalStatus: str
    transferStatus: str
    sendReadyYn: bool
    readinessStatus: str = "NOT_STARTED"
    requiredAtomicCount: int = 0
    approvedAtomicCount: int = 0
    missingAtomicCount: int = 0
    currentApprovedAtomicCount: int = 0
    currentMissingAtomicCount: int = 0
    sentAt: Optional[str] = None
    receivedAt: Optional[str] = None


class RollupBatchSourceListDto(RollupBaseModel):
    batchId: int
    parentCompanyId: int
    reportingYear: int
    rollupPurposeCode: str
    metricScopeCode: str
    items: list[RollupBatchSourceItemDto] = Field(default_factory=list)


class RollupBatchSourceListResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupBatchSourceListDto


class RollupSourceSendStatusDto(RollupBaseModel):
    batchId: int
    parentCompanyId: int
    sourceCompanyId: int
    requestStatus: str
    transferStatus: str
    sentAt: Optional[str] = None


class RollupSourceSendResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupSourceSendStatusDto


class RollupBatchSummaryDto(RollupBaseModel):
    batchId: int
    parentCompanyId: int
    reportingYear: int
    rollupPurposeCode: str
    metricScopeCode: str
    batchStatus: str
    requestedCount: int
    sentCount: int
    pendingCount: int
    calculateReadyYn: bool
    dmaReadyYn: bool
    reportReadyYn: bool = False


class RollupBatchSummaryResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupBatchSummaryDto


<<<<<<< HEAD

=======
# ── S5-B14 Prior-year baseline (전년도 연결 기준값 수동입력) ──────────────────
>>>>>>> origin/skm_test
class RollupBaselineRequirementItemDto(RollupBaseModel):
    ruleCode: str
    metricId: Optional[str] = None
    targetAtomicMetricId: Optional[str] = None
    sourceMetricId: Optional[str] = None
    sourceAtomicMetricId: str
    sourceAtomicName: Optional[str] = None
    requiredReportingYear: int
    unit: Optional[str] = None
    status: str = "MISSING"
    valueNumeric: Optional[float | int] = None
    valueText: Optional[str] = None
    valueSourceType: Optional[str] = None


class RollupBaselineRequirementListDto(RollupBaseModel):
    batchId: int
    parentCompanyId: int
    reportingYear: int
    items: list[RollupBaselineRequirementItemDto] = Field(default_factory=list)


class RollupBaselineRequirementResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupBaselineRequirementListDto


class RollupBaselineValueInputDto(RollupBaseModel):
    metricId: Optional[str] = None
    atomicMetricId: str
    reportingYear: int
    valueNumeric: Optional[float | int] = None
    valueText: Optional[str] = None
    unit: Optional[str] = None
    sourceNote: Optional[str] = None


class RollupBaselineValuesRequestDto(RollupBaseModel):
    values: list[RollupBaselineValueInputDto] = Field(..., min_length=1)


class RollupBaselineSaveResultItemDto(RollupBaseModel):
    atomicMetricId: str
    reportingYear: int
    result: str
    saved: bool


class RollupBaselineSaveResultDto(RollupBaseModel):
    batchId: int
    parentCompanyId: int
    reportingYear: int
    savedCount: int = 0
    items: list[RollupBaselineSaveResultItemDto] = Field(default_factory=list)


class RollupBaselineSaveResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupBaselineSaveResultDto
