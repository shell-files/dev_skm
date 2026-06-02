from fastapi import APIRouter, Depends, HTTPException

from src.models.materiality import (
    BenchmarkResponseDto,
    MaterialityResultsResponseDto,
    MediaStageResponseDto,
    SelectionProcessResponseDto,
    SurveyResponseDto,
)
from src.models.materialitycontext import (
    CompanyContextModifierResponseDto,
    CompanyContextProfileResponseDto,
)
from src.services.materialities.context import applyCompanyContextModifiers, getCompanyContextProfile
from src.services.materialities.service import (
    getBenchmarkResult,
    getMaterialityResults,
    getMediaResult,
    getSelectionProcess,
    getSurveyResult,
)
from src.utils.auth import get_token


router = APIRouter(tags=["materiality"])


@router.get("/results/{runId}", response_model=MaterialityResultsResponseDto, summary="DMA 통합 결과 조회")
async def get_dma_results(runId: int, userModel=Depends(get_token)):
    try:
        return getMaterialityResults(runId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmark/{runId}", response_model=BenchmarkResponseDto, summary="벤치마킹 단계 결과 조회")
async def get_benchmark_result(runId: int, userModel=Depends(get_token)):
    try:
        return getBenchmarkResult(runId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media/{runId}", response_model=MediaStageResponseDto, summary="미디어 단계 결과 조회")
async def get_media_result(runId: int, userModel=Depends(get_token)):
    try:
        return getMediaResult(runId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/survey/{runId}", response_model=SurveyResponseDto, summary="설문 단계 결과 조회")
async def get_survey_result(runId: int, userModel=Depends(get_token)):
    try:
        return getSurveyResult(runId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/selection-process/{runId}",
    response_model=SelectionProcessResponseDto,
    summary="후보군에서 최종 선정 과정 조회",
)
async def get_selection_process(runId: int, userModel=Depends(get_token)):
    try:
        return getSelectionProcess(runId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/context/{runId}/apply",
    response_model=CompanyContextModifierResponseDto,
    summary="Apply company context modifiers",
)
async def apply_company_context_modifiers(runId: int, userModel=Depends(get_token)):
    try:
        return applyCompanyContextModifiers(runId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/context/{runId}",
    response_model=CompanyContextProfileResponseDto,
    summary="Get latest company context profile and modifiers",
)
async def get_company_context_profile(runId: int, userModel=Depends(get_token)):
    try:
        return getCompanyContextProfile(runId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
