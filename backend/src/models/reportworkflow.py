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


class ReportWorkflowResponseDto(BaseModel):
    success: bool = True
    data: ReportWorkflowStatusDto


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

