from typing import List, Optional

from pydantic import BaseModel, Field


class OnboardingInviteListItemDto(BaseModel):
    inviteId: int
    invitePublicId: str
    inviteEmailMasked: Optional[str] = None
    targetRoleCode: str
    inviteStatus: str
    expiresAt: Optional[str] = None
    lastSentAt: Optional[str] = None
    resendCount: int = 0
    assignedMetricIds: List[str] = Field(default_factory=list)


class OnboardingInviteListResponseDto(BaseModel):
    success: bool = True
    companyId: int
    cycleId: Optional[int] = None
    items: List[OnboardingInviteListItemDto] = Field(default_factory=list)


class OnboardingInviteCompanyRequestDto(BaseModel):
    companyId: int


class OnboardingInviteActionResponseDto(BaseModel):
    success: bool = True
    companyId: int
    inviteId: int
    inviteStatus: str
    mailQueuedYn: bool = False
    warning: Optional[str] = None


__all__ = [
    "OnboardingInviteListItemDto",
    "OnboardingInviteListResponseDto",
    "OnboardingInviteCompanyRequestDto",
    "OnboardingInviteActionResponseDto",
]
