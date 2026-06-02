from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


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
    scopeSourceType: str
    requiredYn: bool = True
    inputRequiredYn: bool = True
    approvalRequiredYn: bool = True
    approvalPolicyCode: str = "INPUT_APPROVAL_ONLY"
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


class OnboardingValueItemDto(BaseModel):
    atomicMetricId: str
    valueNumeric: Optional[float] = None
    valueText: Optional[str] = None
    unit: Optional[str] = None


class OnboardingMetricValuesRequestDto(BaseModel):
    companyId: int
    reportingYear: int
    cycleType: str
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

