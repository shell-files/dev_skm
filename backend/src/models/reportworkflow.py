"""
reportworkflow.py
레이어: Model
역할: 보고서 워크플로우 시작·상태·POST_DMA 범위·프로젝트 목록 DTO 정의.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


ReportBasisType = Literal["ENTITY", "CONSOLIDATED"]


class ReportWorkflowStartRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    reportBasisType: ReportBasisType


class ReportWorkflowStatusDto(BaseModel):
    runId: Optional[int] = None
    companyId: int
    reportingYear: int
    reportBasisType: Optional[ReportBasisType] = None
    workflowStep: str
    readyYn: bool = False
    basisStatus: str
    basisRequirementStatus: str
    nextAction: str
    message: str
    # DMA 선정 및 POST_DMA 온보딩 상태 (자동 판단용)
    selectionSource: Optional[str] = None
    fallbackYn: Optional[bool] = None
    selectedSubIssueCount: int = 0
    postDmaCycleId: Optional[int] = None
    postDmaScopeMetricCount: int = 0
    currentCycleType: Optional[str] = None


class ReportWorkflowResponseDto(BaseModel):
    success: bool = True
    data: ReportWorkflowStatusDto


class ReportWorkflowPostDmaScopeDataDto(BaseModel):
    runId: int
    companyId: int
    reportingYear: int
    sourceMaterialityRunId: int
    cycleId: int
    cycleType: str
    metricScopeCode: str
    selectedSubIssueCount: int
    scopeMetricCount: int
    metricIds: List[str] = Field(default_factory=list)
    cycleCreatedYn: bool
    cycleReusedYn: bool
    message: str


class ReportWorkflowPostDmaScopeResponseDto(BaseModel):
    success: bool = True
    data: ReportWorkflowPostDmaScopeDataDto


class ReportWorkflowProjectItemDto(BaseModel):
    runId: int
    companyId: int
    reportingYear: int
    reportBasisType: Optional[ReportBasisType] = None
    runStatus: str
    workflowStep: str
    currentStageLabel: str
    pendingCount: int = 0
    readOnlyYn: bool = False


class ReportWorkflowProjectListDataDto(BaseModel):
    items: List[ReportWorkflowProjectItemDto] = Field(default_factory=list)


class ReportWorkflowProjectListResponseDto(BaseModel):
    success: bool = True
    data: ReportWorkflowProjectListDataDto

