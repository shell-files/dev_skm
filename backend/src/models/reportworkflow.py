from typing import Literal, Optional

from pydantic import BaseModel


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

