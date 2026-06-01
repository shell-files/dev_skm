from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.models.onboardingassignment import (
    OnboardingAssignmentBulkAssignRequestDto,
    OnboardingAssignmentBulkAssignResponseDto,
    OnboardingAssignmentBulkUnassignRequestDto,
    OnboardingAssignmentBulkUnassignResponseDto,
    OnboardingAssignmentDetailResponseDto,
    OnboardingAssignmentListResponseDto,
    OnboardingAssignmentPatchRequestDto,
)
from src.services.onboarding_assignments.service import (
    PreDmaG0CycleNotReadyError,
    bulkAssign,
    bulkUnassign,
    getAssignmentItem,
    listAssignmentItems,
    patchAssignment,
)


onboardingAssignmentRouter = APIRouter(
    prefix="/v1/onboarding-assignments",
    tags=["onboarding-assignments"],
)


def requireUser(response: Response, request: Request):
    from src.utils.auth import get_token
    from src.utils.settings import settings

    token = request.cookies.get(settings.cookie_key)
    return get_token(response, token)


@onboardingAssignmentRouter.post(
    "/bulk-assign",
    response_model=OnboardingAssignmentBulkAssignResponseDto,
    summary="Bulk assign PRE_DMA_G0 metrics",
)
async def bulkAssignRoute(
    request: OnboardingAssignmentBulkAssignRequestDto,
    userModel=Depends(requireUser),
):
    try:
        return bulkAssign(request, userModel)
    except PreDmaG0CycleNotReadyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingAssignmentRouter.get(
    "",
    response_model=OnboardingAssignmentListResponseDto,
    summary="List PRE_DMA_G0 metric assignments",
)
async def listAssignmentItemsRoute(
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    cycleType: str = Query(default="PRE_DMA_G0"),
    userModel=Depends(requireUser),
):
    try:
        return listAssignmentItems(companyId, reportingYear, cycleType, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingAssignmentRouter.get(
    "/{metricId}",
    response_model=OnboardingAssignmentDetailResponseDto,
    summary="Get one PRE_DMA_G0 metric assignment",
)
async def getAssignmentItemRoute(
    metricId: str,
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    cycleType: str = Query(default="PRE_DMA_G0"),
    userModel=Depends(requireUser),
):
    try:
        return getAssignmentItem(metricId, companyId, reportingYear, cycleType, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingAssignmentRouter.patch(
    "/{metricId}",
    response_model=OnboardingAssignmentBulkAssignResponseDto,
    summary="Assign one PRE_DMA_G0 metric",
)
async def patchAssignmentRoute(
    metricId: str,
    request: OnboardingAssignmentPatchRequestDto,
    userModel=Depends(requireUser),
):
    try:
        return patchAssignment(metricId, request, userModel)
    except PreDmaG0CycleNotReadyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@onboardingAssignmentRouter.post(
    "/bulk-unassign",
    response_model=OnboardingAssignmentBulkUnassignResponseDto,
    summary="Bulk unassign PRE_DMA_G0 metrics",
)
async def bulkUnassignRoute(
    request: OnboardingAssignmentBulkUnassignRequestDto,
    userModel=Depends(requireUser),
):
    try:
        return bulkUnassign(request, userModel)
    except PreDmaG0CycleNotReadyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["onboardingAssignmentRouter"]
