from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class OnboardingAssignmentDto(BaseModel):
    assignmentId: Optional[int] = None
    assignmentStatus: Optional[str] = None
    assigneeUserId: Optional[int] = None
    assigneeEmailMasked: Optional[str] = None
    dueDate: Optional[str] = None


class OnboardingAtomicItemDto(BaseModel):
    metricId: str
    atomicMetricId: str
    metricName: Optional[str] = None
    atomicName: Optional[str] = None
    dataValueType: Optional[str] = None
    atomicDataRole: Optional[str] = None
    rollupRole: Optional[str] = None
    inputMode: str = "MANUAL_TEXTAREA"
    editableYn: bool = True
    requiredYn: bool = True
    valueText: Optional[str] = None
    valueNumeric: Optional[float] = None
    unit: Optional[str] = None
    inputStatus: Optional[str] = None
    updatedAt: Optional[str] = None


class OnboardingMetricItemDto(BaseModel):
    metricId: str
    metricName: Optional[str] = None
    issueDomain: Optional[str] = None
    subIssueId: Optional[int] = None
    subIssueCode: Optional[str] = None
    subIssueName: Optional[str] = None
    scopeSourceType: str
    requiredYn: bool = True
    inputRequiredYn: bool = True
    approvalRequiredYn: bool = True
    approvalPolicyCode: str = "INPUT_APPROVAL_ONLY"
    approvalStatus: Optional[str] = None
    rollupReadonlyYn: bool = False
    displayOrder: int = 0
    assignment: Optional[OnboardingAssignmentDto] = None
    atomicItems: List[OnboardingAtomicItemDto] = Field(default_factory=list)


class OnboardingMetricsResponseDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleId: int
    cycleType: str
    metricScopeCode: Optional[str] = None
    items: List[OnboardingMetricItemDto] = Field(default_factory=list)
    message: str = "OK"
    implementationStatus: str = "READY"
    status: bool = True
    message: Optional[str] = None

class OnboardingValueItemDto(BaseModel):
    atomicMetricId: str
    valueNumeric: Optional[float] = None
    valueText: Optional[str] = None
    unit: Optional[str] = None


class OnboardingMetricValuesRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleType: str
    batchId: Optional[int] = None
    values: List[OnboardingValueItemDto]


class OnboardingMetricValuesResponseDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleId: int
    cycleType: str
    metricId: str
    savedItemCount: int = 0
    message: str = "OK"
    implementationStatus: str = "READY"


class OnboardingAssignmentBulkAssignRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleType: str = "PRE_DMA_G0"
    batchId: Optional[int] = None
    metricIds: List[str] = Field(..., min_length=1)
    assigneeEmail: EmailStr
    dueDate: Optional[date] = None
    sendInviteYn: bool = True


class OnboardingAssignmentBulkUnassignRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleType: str = "PRE_DMA_G0"
    batchId: Optional[int] = None
    metricIds: List[str] = Field(..., min_length=1)


class OnboardingAssignmentPatchRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleType: str = "PRE_DMA_G0"
    batchId: Optional[int] = None
    assigneeEmail: EmailStr
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
    metricId: str
    cycleType: str = "PRE_DMA_G0"
    batchId: Optional[int] = None


class OnboardingApprovalDecisionRequestDto(OnboardingApprovalRequestDto):
    commentText: Optional[str] = None


class OnboardingApprovalItemDto(BaseModel):
    companyId: int
    reportingYear: int
    metricId: str
    metricName: Optional[str] = None
    cycleType: Optional[str] = None
    issueDomain: Optional[str] = None
    issueGroup: Optional[str] = None
    subIssueId: Optional[int] = None
    subIssueCode: Optional[str] = None
    subIssueName: Optional[str] = None
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
    approvalPolicyCode: Optional[str] = None
    rollupReadonlyYn: bool = False
    promotedQuantAtomicCount: int = 0
    approvedPromotedFactCount: int = 0
    submittedAt: Optional[str] = None
    approvedAt: Optional[str] = None
    commentText: Optional[str] = None
    selfSubmittedYn: bool = False
    actionSupportedYn: bool = False
    actionDisabledReason: Optional[str] = None


class OnboardingApprovalListDataDto(BaseModel):
    items: List[OnboardingApprovalItemDto] = Field(default_factory=list)


class OnboardingApprovalListResponseDto(BaseModel):
    success: bool = True
    data: OnboardingApprovalListDataDto


class OnboardingApprovalStatusDataDto(OnboardingApprovalItemDto):
    rollupReadyYn: bool = False
    calculationReadyYn: Optional[bool] = None
    affectedRuleCount: int = 0
    invalidatedFactCount: int = 0
    calculatedFactCount: int = 0
    calculationWarnings: List[str] = Field(default_factory=list)


class OnboardingApprovalStatusResponseDto(BaseModel):
    success: bool = True
    data: OnboardingApprovalStatusDataDto


class OnboardingApprovalAtomicDetailItemDto(BaseModel):
    atomicMetricId: str
    atomicName: Optional[str] = None
    dataValueType: Optional[str] = None
    atomicDataRole: Optional[str] = None
    inputMode: Optional[str] = None
    valueText: Optional[str] = None
    valueNumeric: Optional[float] = None
    unit: Optional[str] = None
    inputStatus: Optional[str] = None
    updatedAt: Optional[str] = None
    evidenceCount: int = 0


class OnboardingApprovalDetailDataDto(OnboardingApprovalStatusDataDto):
    atomicItems: List[OnboardingApprovalAtomicDetailItemDto] = Field(default_factory=list)


class OnboardingApprovalDetailResponseDto(BaseModel):
    success: bool = True
    data: OnboardingApprovalDetailDataDto


class OnboardingApprovalActionResponseDto(BaseModel):
    success: bool = True
    data: OnboardingApprovalStatusDataDto
    message: str = "OK"
