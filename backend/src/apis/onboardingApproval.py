"""
onboardingApproval.py
레이어: API Router
역할: 온보딩 결재 상신·검토·승인·반려·조회 엔드포인트.

엔드포인트:
  POST /submit   — PRE_DMA_G0 G0-02 입력값 결재 상신
  POST /review   — 온보딩 입력값 검토
  GET  /         — 온보딩 결재 요청 목록 조회
  GET  /detail   — 온보딩 결재 상세 조회
  GET  /status   — PRE_DMA_G0 G0-02 결재 상태 조회
  POST /approve  — PRE_DMA_G0 G0-02 입력값 승인 및 KPI Fact 반영
  POST /reject   — PRE_DMA_G0 G0-02 입력값 반려
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.models.onboarding import (
    OnboardingApprovalActionResponseDto,
    OnboardingApprovalDecisionRequestDto,
    OnboardingApprovalDetailResponseDto,
    OnboardingApprovalListResponseDto,
    OnboardingApprovalRequestDto,
    OnboardingApprovalStatusResponseDto,
)
from src.services.onboardings.approvalhandler import (
    approveApproval,
    getApprovalDetail,
    getApprovalStatus,
    listApprovals,
    rejectApproval,
    reviewApproval,
    submitApproval,
)
from src.utils.auth import get_token


router = APIRouter()

onboardingApprovalRouter = APIRouter(
    prefix="/v1/onboarding-approvals",
    tags=["onboarding-approvals"],
)

def statusForValueError(error: ValueError) -> int:
    statusCode = getattr(error, "statusCode", None)
    if statusCode:
        return int(statusCode)
    return 409


@router.post(
    "/submit",
    response_model=OnboardingApprovalActionResponseDto,
    summary="PRE_DMA_G0 G0-02 입력값 결재 상신",
)
@onboardingApprovalRouter.post(
    "/submit",
    response_model=OnboardingApprovalActionResponseDto,
    summary="PRE_DMA_G0 G0-02 입력값 결재 상신",
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
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/review",
    response_model=OnboardingApprovalActionResponseDto,
    summary="온보딩 입력값 검토",
)
@onboardingApprovalRouter.post(
    "/review",
    response_model=OnboardingApprovalActionResponseDto,
    summary="온보딩 입력값 검토",
)
async def reviewApprovalRoute(
    request: OnboardingApprovalDecisionRequestDto,
    userModel=Depends(get_token),
):
    try:
        return reviewApproval(request, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "",
    response_model=OnboardingApprovalListResponseDto,
    summary="온보딩 결재 요청 목록 조회",
)
@onboardingApprovalRouter.get(
    "",
    response_model=OnboardingApprovalListResponseDto,
    summary="온보딩 결재 요청 목록 조회",
)
async def listApprovalsRoute(
    companyId: int = Query(...),
    reportingYear: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    cycleType: Optional[str] = Query(default=None),
    assignedOnlyYn: bool = Query(default=True),
    batchId: Optional[int] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        return listApprovals(companyId, reportingYear, status, cycleType, assignedOnlyYn, userModel, batchId=batchId)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/detail",
    response_model=OnboardingApprovalDetailResponseDto,
    summary="온보딩 결재 상세 조회",
)
@onboardingApprovalRouter.get(
    "/detail",
    response_model=OnboardingApprovalDetailResponseDto,
    summary="온보딩 결재 상세 조회",
)
async def getApprovalDetailRoute(
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    metricId: str = Query(...),
    cycleType: str = Query(default="PRE_DMA_G0"),
    batchId: Optional[int] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        return getApprovalDetail(companyId, reportingYear, metricId, cycleType, userModel, batchId=batchId)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/status",
    response_model=OnboardingApprovalStatusResponseDto,
    summary="PRE_DMA_G0 G0-02 결재 상태 조회",
)
@onboardingApprovalRouter.get(
    "/status",
    response_model=OnboardingApprovalStatusResponseDto,
    summary="PRE_DMA_G0 G0-02 결재 상태 조회",
)
async def getApprovalStatusRoute(
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    metricId: str = Query(default="G0-02"),
    cycleType: str = Query(default="PRE_DMA_G0"),
    batchId: Optional[int] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        return getApprovalStatus(companyId, reportingYear, metricId, userModel, cycleType, batchId=batchId)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/approve",
    response_model=OnboardingApprovalActionResponseDto,
    summary="PRE_DMA_G0 G0-02 입력값 승인 및 KPI Fact 반영",
)
@onboardingApprovalRouter.post(
    "/approve",
    response_model=OnboardingApprovalActionResponseDto,
    summary="PRE_DMA_G0 G0-02 입력값 승인 및 KPI Fact 반영",
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
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/reject",
    response_model=OnboardingApprovalActionResponseDto,
    summary="PRE_DMA_G0 G0-02 입력값 반려",
)
@onboardingApprovalRouter.post(
    "/reject",
    response_model=OnboardingApprovalActionResponseDto,
    summary="PRE_DMA_G0 G0-02 입력값 반려",
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
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router", "onboardingApprovalRouter"]
