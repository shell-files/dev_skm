from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.models.onboardingapproval import (
    OnboardingApprovalActionResponseDto,
    OnboardingApprovalDecisionRequestDto,
    OnboardingApprovalListResponseDto,
    OnboardingApprovalRequestDto,
    OnboardingApprovalStatusResponseDto,
)
from src.services.onboarding_approvals.service import (
    approveApproval,
    getApprovalStatus,
    listApprovals,
    rejectApproval,
    submitApproval,
)
from src.utils.auth import get_token


onboardingApprovalRouter = APIRouter(
    prefix="/v1/onboarding-approvals",
    tags=["onboarding-approvals"],
)




@onboardingApprovalRouter.post(
    "/submit",
    response_model=OnboardingApprovalActionResponseDto,
    summary="Submit PRE_DMA_G0 G0-02 inputs for approval",
)
async def submitApprovalRoute(
    request: OnboardingApprovalRequestDto,
    userModel=Depends(get_token),
):
    try:
        return submitApproval(request, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingApprovalRouter.get(
    "",
    response_model=OnboardingApprovalListResponseDto,
    summary="List onboarding approval requests",
)
async def listApprovalsRoute(
    companyId: int = Query(...),
    reportingYear: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    cycleType: Optional[str] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        return listApprovals(companyId, reportingYear, status, cycleType, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingApprovalRouter.get(
    "/status",
    response_model=OnboardingApprovalStatusResponseDto,
    summary="Get PRE_DMA_G0 G0-02 approval status",
)
async def getApprovalStatusRoute(
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    metricId: str = Query(default="G0-02"),
    userModel=Depends(get_token),
):
    try:
        return getApprovalStatus(companyId, reportingYear, metricId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingApprovalRouter.post(
    "/approve",
    response_model=OnboardingApprovalActionResponseDto,
    summary="Approve PRE_DMA_G0 G0-02 inputs and promote to KPI facts",
)
async def approveApprovalRoute(
    request: OnboardingApprovalDecisionRequestDto,
    userModel=Depends(get_token),
):
    try:
        return approveApproval(request, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingApprovalRouter.post(
    "/reject",
    response_model=OnboardingApprovalActionResponseDto,
    summary="Reject PRE_DMA_G0 G0-02 inputs",
)
async def rejectApprovalRoute(
    request: OnboardingApprovalDecisionRequestDto,
    userModel=Depends(get_token),
):
    try:
        return rejectApproval(request, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["onboardingApprovalRouter"]
