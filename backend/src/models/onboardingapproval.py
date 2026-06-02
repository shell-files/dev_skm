from typing import List, Literal, Optional

from pydantic import BaseModel, Field


ApprovalActionStatus = Literal[
    "NOT_STARTED",
    "DRAFT",
    "SUBMITTED",
    "REVIEWED",
    "APPROVED",
    "REJECTED",
]


class OnboardingApprovalRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    metricId: str = "G0-02"


class OnboardingApprovalDecisionRequestDto(OnboardingApprovalRequestDto):
    commentText: Optional[str] = None


class OnboardingApprovalItemDto(BaseModel):
    companyId: int
    reportingYear: int
    metricId: str
    metricName: Optional[str] = None
    approvalStatus: ApprovalActionStatus
    inputUserId: Optional[int] = None
    assigneeUserId: Optional[int] = None
    cycleId: Optional[int] = None
    assignmentId: Optional[int] = None
    requiredAtomicCount: int = 0
    completedAtomicCount: int = 0
    submittedAtomicCount: int = 0
    approvedAtomicCount: int = 0
    missingAtomicMetricIds: List[str] = Field(default_factory=list)
    submittedAt: Optional[str] = None
    approvedAt: Optional[str] = None
    commentText: Optional[str] = None
    selfSubmittedYn: bool = False


class OnboardingApprovalListDataDto(BaseModel):
    items: List[OnboardingApprovalItemDto] = Field(default_factory=list)


class OnboardingApprovalListResponseDto(BaseModel):
    success: bool = True
    data: OnboardingApprovalListDataDto


class OnboardingApprovalStatusDataDto(OnboardingApprovalItemDto):
    rollupReadyYn: bool = False


class OnboardingApprovalStatusResponseDto(BaseModel):
    success: bool = True
    data: OnboardingApprovalStatusDataDto


class OnboardingApprovalActionResponseDto(BaseModel):
    success: bool = True
    data: OnboardingApprovalStatusDataDto
    message: str = "OK"


__all__ = [
    "OnboardingApprovalRequestDto",
    "OnboardingApprovalDecisionRequestDto",
    "OnboardingApprovalItemDto",
    "OnboardingApprovalListDataDto",
    "OnboardingApprovalListResponseDto",
    "OnboardingApprovalStatusDataDto",
    "OnboardingApprovalStatusResponseDto",
    "OnboardingApprovalActionResponseDto",
]
