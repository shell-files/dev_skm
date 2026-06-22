<<<<<<< HEAD
"""
onboarding.py
레이어: API Router
역할: 온보딩 지표 목록 조회 및 입력값 저장 엔드포인트.

엔드포인트:
  GET   /           — 사이클 범위별 온보딩 지표 목록 조회
  GET   /metrics    — 사이클 범위별 온보딩 지표 목록 조회 (alias)
  PATCH /{metricId} — 온보딩 지표 입력값 저장
  PATCH /metrics/{metricId} — 온보딩 지표 입력값 저장 (alias)
"""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="사이클 범위별 온보딩 지표 목록 조회",
=======
    summary="List onboarding metrics by cycle scope",
>>>>>>> origin/skm_test
)
@router.get(
    "/metrics",
    response_model=OnboardingMetricsResponseDto,
    include_in_schema=False,
<<<<<<< HEAD
    summary="사이클 범위별 온보딩 지표 목록 조회",
=======
    summary="List onboarding metrics by cycle scope",
>>>>>>> origin/skm_test
)
async def list_onboarding_metrics(
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    cycleType: str = Query(...),
    metricId: Optional[str] = Query(default=None),
    batchId: Optional[int] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        checkScope(companyId, userModel)
        return listMetrics(
            companyId=companyId,
            reportingYear=reportingYear,
            cycleType=cycleType,
            metricId=metricId,
            batchId=batchId,
            userModel=userModel,
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
<<<<<<< HEAD
    summary="온보딩 지표 입력값 저장",
=======
    summary="Save onboarding metric input values",
>>>>>>> origin/skm_test
)
@router.patch(
    "/metrics/{metricId}",
    response_model=OnboardingMetricValuesResponseDto,
    include_in_schema=False,
<<<<<<< HEAD
    summary="온보딩 지표 입력값 저장",
=======
    summary="Save onboarding metric input values",
>>>>>>> origin/skm_test
)
async def patch_onboarding_metric_values(
    metricId: str,
    request: OnboardingMetricValuesRequestDto,
    userModel=Depends(get_token),
):
    try:
        checkScope(request.companyId, userModel)
        return saveMetricValues(metricId=metricId, request=request, userId=userId(userModel), userModel=userModel)
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
    statusCode = getattr(error, "statusCode", None)
    if statusCode:
        return int(statusCode)
    err_str = str(error)
    if err_str.startswith(
        (
            "보고연도 프로젝트를 먼저 시작해 주세요.",
            "온보딩 지표 범위가 초기화되지 않았습니다.",
            "생성된 프로젝트를 먼저 초기화해 주세요.",
            "공시범위가 초기화되지 않았습니다.",
            "기존 프로젝트를 먼저 시작해 주세요.",
            "받은 요청함 프로젝트가 초기화되지 않았습니다.",
            "받은 요청함 지표 범위가 초기화되지 않았습니다.",
            "공시범위가 준비되지 않았습니다.",
        )
    ):
        return 409
    return 400


__all__ = ["router"]
