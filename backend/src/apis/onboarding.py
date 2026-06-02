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


onboardingRouter = APIRouter(
    prefix="/v1/onboarding",
    tags=["onboarding"],
)


@onboardingRouter.get(
    "/metrics",
    response_model=OnboardingMetricsResponseDto,
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


@onboardingRouter.patch(
    "/metrics/{metricId}/values",
    response_model=OnboardingMetricValuesResponseDto,
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
    if str(error).startswith("PRE_DMA_G0_CYCLE_NOT_READY"):
        return 409
    return 400


__all__ = ["onboardingRouter"]

