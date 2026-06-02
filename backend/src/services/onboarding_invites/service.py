from __future__ import annotations

from typing import Optional

from src.models.onboardinginvite import (
    OnboardingInviteActionResponseDto,
    OnboardingInviteListItemDto,
    OnboardingInviteListResponseDto,
)
from src.services.onboarding_assignments.service import checkManager, publishMailEvent
from src.utils.companyscope import checkScope
from src.utils.onboardinginviterepository import listInvites, resendInvite, revokeInvite


def listInviteItems(companyId: int, cycleId: Optional[int], status: Optional[str], userModel) -> OnboardingInviteListResponseDto:
    checkScope(companyId, userModel)
    checkManager(userModel)
    return OnboardingInviteListResponseDto(
        companyId=companyId,
        cycleId=cycleId,
        items=[
            OnboardingInviteListItemDto(**item)
            for item in listInvites(companyId, cycleId, status)
        ],
    )


def resendInviteMail(inviteId: int, companyId: int, userModel) -> OnboardingInviteActionResponseDto:
    checkScope(companyId, userModel)
    checkManager(userModel)
    result = resendInvite(inviteId, companyId)
    mailQueuedYn, warning = publishMailEvent(result.get("mailEvent"))
    return OnboardingInviteActionResponseDto(
        companyId=companyId,
        inviteId=inviteId,
        inviteStatus=result["inviteStatus"],
        mailQueuedYn=mailQueuedYn,
        warning=warning,
    )


def revokeInviteMail(inviteId: int, companyId: int, userModel) -> OnboardingInviteActionResponseDto:
    checkScope(companyId, userModel)
    checkManager(userModel)
    result = revokeInvite(inviteId, companyId)
    return OnboardingInviteActionResponseDto(
        companyId=companyId,
        inviteId=inviteId,
        inviteStatus=result["inviteStatus"],
        mailQueuedYn=False,
        warning=None,
    )


__all__ = ["listInviteItems", "resendInviteMail", "revokeInviteMail"]
