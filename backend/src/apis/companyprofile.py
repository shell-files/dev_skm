from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.models.companyprofile import (
    G0ProfileResponseDto,
    G0ProfileStatusResponseDto,
    G0ProfileUpsertRequestDto,
    G0ProfileUpsertResponseDto,
)
from src.services.company_profiles.service import getG0Profile, getG0ProfileStatus, saveG0Profile
from src.utils.auth import get_token


router = APIRouter(tags=["company-profile"])


@router.get(
    "/g0/{companyId}",
    response_model=G0ProfileResponseDto,
    summary="Get G0 company profile inputs",
)
async def get_g0_profile(
    companyId: int,
    reportingYear: Optional[int] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        return getG0Profile(companyId, reportingYear)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/g0/{companyId}",
    response_model=G0ProfileUpsertResponseDto,
    summary="Create G0 company profile inputs",
)
async def post_g0_profile(
    companyId: int,
    request: G0ProfileUpsertRequestDto,
    userModel=Depends(get_token),
):
    try:
        return saveG0Profile(companyId, request, _userId(userModel))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/g0/{companyId}",
    response_model=G0ProfileUpsertResponseDto,
    summary="Update G0 company profile inputs",
)
async def patch_g0_profile(
    companyId: int,
    request: G0ProfileUpsertRequestDto,
    userModel=Depends(get_token),
):
    try:
        return saveG0Profile(companyId, request, _userId(userModel))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/g0/{companyId}/status",
    response_model=G0ProfileStatusResponseDto,
    summary="Get G0 company profile input status",
)
async def get_g0_profile_status(
    companyId: int,
    reportingYear: Optional[int] = Query(default=None),
    userModel=Depends(get_token),
):
    try:
        return getG0ProfileStatus(companyId, reportingYear)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _userId(userModel) -> Optional[int]:
    if isinstance(userModel, dict):
        return userModel.get("id")
    return getattr(userModel, "id", None)
