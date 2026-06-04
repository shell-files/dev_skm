from typing import Optional

from pydantic import BaseModel, Field

ROLLUP_PURPOSE_DMA_PRECHECK = "DMA_PRECHECK"
ROLLUP_PURPOSE_REPORT_DISCLOSURE = "REPORT_DISCLOSURE"

METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
METRIC_SCOPE_SELECTED_DISCLOSURE = "SELECTED_DISCLOSURE"
METRIC_SCOPE_ROLLUP = "ROLLUP_SCOPE"


class RollupSubsidiaryDto(BaseModel):
    companyId: int
    companyCode: Optional[str] = None
    companyName: Optional[str] = None


class RollupSubsidiaryListDto(BaseModel):
    runId: int
    items: list[RollupSubsidiaryDto]


class RollupSubsidiaryResponseDto(BaseModel):
    success: bool = True
    data: RollupSubsidiaryListDto


class RollupBatchRequestDto(BaseModel):
    runId: Optional[int] = None
    sourceCycleId: Optional[int] = None
    sourceCompanyIds: list[int] = Field(..., min_length=1)
    rollupPurposeCode: str = ROLLUP_PURPOSE_DMA_PRECHECK
    metricScopeCode: str = METRIC_SCOPE_G0_02_FINANCIAL_BASIS


class RollupBatchStatusDto(BaseModel):
    batchId: int
    runId: Optional[int] = None
    rollupPurposeCode: str
    metricScopeCode: str
    batchStatus: str
    dmaReadyYn: bool
    reportReadyYn: bool = False
    sourceCompanyIds: list[int]


class RollupBatchResponseDto(BaseModel):
    success: bool = True
    data: RollupBatchStatusDto


class RollupResultDto(BaseModel):
    groupAtomicMetricId: str
    sourceAtomicMetricIds: list[str]
    sourceAtomicMetricId: Optional[str] = None
    formulaType: str
    valueNumeric: Optional[float | int] = None
    valueText: Optional[str] = None
    unit: Optional[str] = None
    sourceCompanyValues: Optional[dict] = None
    calculationWarnings: Optional[list[str]] = None


class RollupCalculateStatusDto(RollupBatchStatusDto):
    results: list[RollupResultDto]


class RollupCalculateResponseDto(BaseModel):
    success: bool = True
    data: RollupCalculateStatusDto


class RollupRequestItemDto(BaseModel):
    batchId: int
    parentCompanyId: int
    parentCompanyCode: Optional[str] = None
    parentCompanyName: Optional[str] = None
    reportingYear: int
    rollupPurposeCode: str
    metricScopeCode: str
    requestStatus: str
    transferStatus: str
    sendReadyYn: bool
    missingAtomicMetricIds: list[str]


class RollupRequestListDto(BaseModel):
    items: list[RollupRequestItemDto]


class RollupRequestResponseDto(BaseModel):
    success: bool = True
    data: RollupRequestListDto


class RollupSourceSendStatusDto(BaseModel):
    batchId: int
    parentCompanyId: int
    sourceCompanyId: int
    requestStatus: str
    transferStatus: str
    sentAt: Optional[str] = None


class RollupSourceSendResponseDto(BaseModel):
    success: bool = True
    data: RollupSourceSendStatusDto


class RollupBatchSummaryDto(BaseModel):
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


class RollupBatchSummaryResponseDto(BaseModel):
    success: bool = True
    data: RollupBatchSummaryDto
