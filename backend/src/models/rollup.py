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


class RollupCalculateStatusDto(RollupBatchStatusDto):
    results: list[RollupResultDto]


class RollupCalculateResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupCalculateStatusDto


class RollupRequestItemDto(RollupBaseModel):
    batchId: int
    batchCode: Optional[str] = None
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


class RollupRequestListDto(RollupBaseModel):
    items: list[RollupRequestItemDto]


class RollupRequestResponseDto(RollupBaseModel):
    success: bool = True
    data: RollupRequestListDto


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
