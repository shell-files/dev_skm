from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.onboarding import (
    OnboardingMetricsResponseDto,
    OnboardingMetricValuesRequestDto,
    OnboardingMetricValuesResponseDto,
)
from src.services.onboardings.service import listMetrics, saveMetricValues
from src.utils.auth import get_token
from src.utils.companyscope import checkScope


router = APIRouter()


@router.get(
    "",
    response_model=OnboardingMetricsResponseDto,
    summary="List onboarding metrics by cycle scope",
)
@router.get(
    "/metrics",
    response_model=OnboardingMetricsResponseDto,
    include_in_schema=False,
    summary="List onboarding metrics by cycle scope",
)
async def list_onboarding_metrics(
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    cycleType: str = Query(...),
    metricId: Optional[str] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        checkScope(companyId, userModel)
        return listMetrics(
            companyId=companyId,
            reportingYear=reportingYear,
            cycleType=cycleType,
            metricId=metricId,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{metricId}",
    response_model=OnboardingMetricValuesResponseDto,
    summary="Save onboarding metric input values",
)
@router.patch(
    "/metrics/{metricId}",
    response_model=OnboardingMetricValuesResponseDto,
    include_in_schema=False,
    summary="Save onboarding metric input values",
)
async def patch_onboarding_metric_values(
    metricId: str,
    request: OnboardingMetricValuesRequestDto,
    userModel=Depends(get_token),
):
    try:
        checkScope(request.companyId, userModel)
        return saveMetricValues(metricId=metricId, request=request, userId=userId(userModel))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def userId(userModel) -> Optional[int]:
    if isinstance(userModel, dict):
        return userModel.get("id")
    return getattr(userModel, "id", None)


def statusForValueError(error: ValueError) -> int:
    if str(error).startswith(
        (
            "PRE_DMA_G0_CYCLE_NOT_READY",
            "PRE_DMA_G0_SCOPE_NOT_READY",
            "POST_DMA_DISCLOSURE_CYCLE_NOT_READY",
            "POST_DMA_DISCLOSURE_SCOPE_NOT_READY",
            "POST_DMA_SUB_ISSUE_METADATA_NOT_READY",
        )
    ):
        return 409
    return 400


__all__ = ["router"]
