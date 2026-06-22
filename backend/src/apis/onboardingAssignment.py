"""
onboardingAssignment.py
레이어: API Router
역할: 온보딩 지표 배정·해제·조회 엔드포인트.

엔드포인트:
  POST /bulk-assign      — 온보딩 지표 일괄 배정
  GET  /                 — 온보딩 지표 배정 목록 조회
  GET  /{metricId}       — 온보딩 지표 배정 단건 조회
  PATCH /{metricId}      — 온보딩 지표 단건 배정
  POST /bulk-unassign    — 온보딩 지표 일괄 배정 취소
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response


from typing import Optional
from src.models.onboarding import (
    OnboardingAssignmentBulkAssignRequestDto,
    OnboardingAssignmentBulkAssignResponseDto,
    OnboardingAssignmentBulkUnassignRequestDto,
    OnboardingAssignmentBulkUnassignResponseDto,
    OnboardingAssignmentDetailResponseDto,
    OnboardingAssignmentListResponseDto,
    OnboardingAssignmentPatchRequestDto,
)
from src.services.onboardings.assignmentservice import (
    PreDmaG0CycleNotReadyError,
    bulkAssign,
    bulkUnassign,
    getAssignmentItem,
    listAssignmentItems,
    patchAssignment,
)


from src.utils.auth import get_token


router = APIRouter()

onboardingAssignmentRouter = APIRouter(
    prefix="/v1/onboarding-assignments",
    tags=["onboarding-assignments"],
)


def statusForValueError(error: ValueError) -> int:
    statusCode = getattr(error, "statusCode", None)
    if statusCode:
        return int(statusCode)
    detail = str(error)
    if detail.startswith(
        (
            "보고연도 프로젝트를 먼저 시작해 주세요.",
            "온보딩 지표 범위가 초기화되지 않았습니다.",
            "생성된 프로젝트를 먼저 초기화해 주세요.",
            "공시범위가 초기화되지 않았습니다.",
            "기존 프로젝트를 먼저 시작해 주세요.",
            "받은 요청 프로젝트가 초기화되지 않았습니다.",
            "받은 요청 데이터 범위가 초기화되지 않았습니다.",
            "공시범위가 준비되지 않았습니다.",
        )
    ):
        return 409
    return 422


@router.post(
    "/bulk-assign",
    response_model=OnboardingAssignmentBulkAssignResponseDto,
    summary="온보딩 지표 일괄 배정",
)
@onboardingAssignmentRouter.post(
    "/bulk-assign",
    response_model=OnboardingAssignmentBulkAssignResponseDto,
    summary="온보딩 지표 일괄 배정",
)
async def bulkAssignRoute(
    request: OnboardingAssignmentBulkAssignRequestDto,
    userModel=Depends(get_token),
):
    try:
        return bulkAssign(request, userModel)
    except PreDmaG0CycleNotReadyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "",
    response_model=OnboardingAssignmentListResponseDto,
    summary="온보딩 지표 배정 목록 조회",
)
@onboardingAssignmentRouter.get(
    "",
    response_model=OnboardingAssignmentListResponseDto,
    summary="온보딩 지표 배정 목록 조회",
)
async def listAssignmentItemsRoute(
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    cycleType: str = Query(default="PRE_DMA_G0"),
    batchId: Optional[int] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        return listAssignmentItems(companyId, reportingYear, cycleType, userModel, batchId=batchId)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{metricId}",
    response_model=OnboardingAssignmentDetailResponseDto,
    summary="온보딩 지표 배정 단건 조회",
)
@onboardingAssignmentRouter.get(
    "/{metricId}",
    response_model=OnboardingAssignmentDetailResponseDto,
    summary="온보딩 지표 배정 단건 조회",
)
async def getAssignmentItemRoute(
    metricId: str,
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    cycleType: str = Query(default="PRE_DMA_G0"),
    batchId: Optional[int] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        return getAssignmentItem(metricId, companyId, reportingYear, cycleType, userModel, batchId=batchId)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{metricId}",
    response_model=OnboardingAssignmentBulkAssignResponseDto,
    summary="온보딩 지표 단건 배정",
)
@onboardingAssignmentRouter.patch(
    "/{metricId}",
    response_model=OnboardingAssignmentBulkAssignResponseDto,
    summary="온보딩 지표 단건 배정",
)
async def patchAssignmentRoute(
    metricId: str,
    request: OnboardingAssignmentPatchRequestDto,
    userModel=Depends(get_token),
):
    try:
        return patchAssignment(metricId, request, userModel)
    except PreDmaG0CycleNotReadyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/bulk-unassign",
    response_model=OnboardingAssignmentBulkUnassignResponseDto,
    summary="온보딩 지표 일괄 배정 취소",
)
@onboardingAssignmentRouter.post(
    "/bulk-unassign",
    response_model=OnboardingAssignmentBulkUnassignResponseDto,
    summary="온보딩 지표 일괄 배정 취소",
)
async def bulkUnassignRoute(
    request: OnboardingAssignmentBulkUnassignRequestDto,
    userModel=Depends(get_token),
):
    try:
        return bulkUnassign(request, userModel)
    except PreDmaG0CycleNotReadyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router", "onboardingAssignmentRouter"]
