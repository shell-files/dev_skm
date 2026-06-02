from typing import Optional

from pydantic import BaseModel, Field


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
    runId: int
    sourceCompanyIds: list[int] = Field(..., min_length=1)


class RollupBatchStatusDto(BaseModel):
    batchId: int
    runId: Optional[int] = None
    rollupPurposeCode: str
    metricScopeCode: str
    batchStatus: str
    dmaReadyYn: bool
    sourceCompanyIds: list[int]


class RollupBatchResponseDto(BaseModel):
    success: bool = True
    data: RollupBatchStatusDto


class RollupResultDto(BaseModel):
    groupAtomicMetricId: str
    sourceAtomicMetricId: str
    formulaType: str
    valueNumeric: float | int
    unit: Optional[str] = None


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


class RollupBatchSummaryResponseDto(BaseModel):
    success: bool = True
    data: RollupBatchSummaryDto
