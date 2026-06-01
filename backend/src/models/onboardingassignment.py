from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class OnboardingAssignmentBulkAssignRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleType: str = "PRE_DMA_G0"
    metricIds: List[str] = Field(..., min_length=1)
    assigneeEmail: str
    dueDate: Optional[date] = None
    sendInviteYn: bool = True


class OnboardingAssignmentBulkUnassignRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleType: str = "PRE_DMA_G0"
    metricIds: List[str] = Field(..., min_length=1)


class OnboardingAssignmentPatchRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleType: str = "PRE_DMA_G0"
    assigneeEmail: str
    dueDate: Optional[date] = None
    sendInviteYn: bool = True


class OnboardingAssignmentBulkAssignResponseDto(BaseModel):
    success: bool = True
    companyId: int
    reportingYear: int
    cycleId: int
    metricIds: List[str]
    assignmentCount: int
    assignmentStatus: str
    assigneeResolvedYn: bool
    inviteCreatedYn: bool = False
    inviteReusedYn: bool = False
    inviteId: Optional[int] = None
    mailQueuedYn: bool = False
    warning: Optional[str] = None


class OnboardingAssignmentBulkUnassignResponseDto(BaseModel):
    success: bool = True
    companyId: int
    reportingYear: int
    cycleId: int
    metricIds: List[str]
    unassignedCount: int
    revokedInviteIds: List[int] = Field(default_factory=list)
    warning: Optional[str] = None


class OnboardingAssignmentItemDto(BaseModel):
    metricId: str
    metricName: Optional[str] = None
    assignmentStatus: str
    assigneeUserId: Optional[int] = None
    assigneeEmailMasked: Optional[str] = None
    dueDate: Optional[str] = None
    inviteId: Optional[int] = None
    inviteStatus: Optional[str] = None


class OnboardingAssignmentListResponseDto(BaseModel):
    success: bool = True
    companyId: int
    reportingYear: int
    cycleId: Optional[int] = None
    cycleType: str
    items: List[OnboardingAssignmentItemDto] = Field(default_factory=list)


class OnboardingAssignmentDetailResponseDto(BaseModel):
    success: bool = True
    companyId: int
    reportingYear: int
    cycleId: Optional[int] = None
    cycleType: str
    item: OnboardingAssignmentItemDto


__all__ = [
    "OnboardingAssignmentBulkAssignRequestDto",
    "OnboardingAssignmentBulkUnassignRequestDto",
    "OnboardingAssignmentPatchRequestDto",
    "OnboardingAssignmentBulkAssignResponseDto",
    "OnboardingAssignmentBulkUnassignResponseDto",
    "OnboardingAssignmentItemDto",
    "OnboardingAssignmentListResponseDto",
    "OnboardingAssignmentDetailResponseDto",
]
