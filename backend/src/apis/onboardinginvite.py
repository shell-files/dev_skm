from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.models.onboardinginvite import (
    OnboardingInviteActionResponseDto,
    OnboardingInviteCompanyRequestDto,
    OnboardingInviteListResponseDto,
)
from src.services.onboarding_invites.service import (
    listInviteItems,
    resendInviteMail,
    revokeInviteMail,
)
from src.utils.auth import get_token




onboardingInviteRouter = APIRouter(
    prefix="/v1/onboarding-invites",
    tags=["onboarding-invites"],
)




@onboardingInviteRouter.get(
    "",
    response_model=OnboardingInviteListResponseDto,
    summary="List onboarding invites",
)
async def listInviteItemsRoute(
    companyId: int = Query(...),
    cycleId: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        return listInviteItems(companyId, cycleId, status, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingInviteRouter.post(
    "/{inviteId}/resend",
    response_model=OnboardingInviteActionResponseDto,
    summary="Resend onboarding invite",
)
async def resendInviteMailRoute(
    inviteId: int,
    request: OnboardingInviteCompanyRequestDto,
    userModel=Depends(get_token),
):
    try:
        return resendInviteMail(inviteId, request.companyId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingInviteRouter.post(
    "/{inviteId}/revoke",
    response_model=OnboardingInviteActionResponseDto,
    summary="Revoke onboarding invite",
)
async def revokeInviteMailRoute(
    inviteId: int,
    request: OnboardingInviteCompanyRequestDto,
    userModel=Depends(get_token),
):
    try:
        return revokeInviteMail(inviteId, request.companyId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["onboardingInviteRouter"]
