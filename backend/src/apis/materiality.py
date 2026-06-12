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


@router.get("/results/{runId}/onboarding-progress", summary="이슈별 온보딩 입력 진행 현황 (Dashboard용)")
async def get_onboarding_progress(runId: int, userModel=Depends(get_token)):
    """source_materiality_run_id로 직접 조인 — 사이클 조회 없이 이슈별 지표 전체/완료 집계."""
    try:
        from src.utils.db import findAll, findOne

        # runId → company_id, reporting_year (approval 이력 필터용)
        run = findOne(
            "SELECT company_id, reporting_year FROM ESG_MATERIALITY_RUN WHERE id = ? AND delete_yn = 0",
            (runId,),
        )
        if not run:
            raise HTTPException(status_code=404, detail="Materiality run not found")

        rows = findAll(
            """
            SELECT
                sub.sub_issue_code,
                COALESCE(sub_master.sub_issue_name_kr, '기타') AS sub_issue_name,
                COUNT(DISTINCT master.atomic_metric_id)        AS total_count,
                COUNT(DISTINCT CASE
                    WHEN fact.atomic_metric_id   IS NOT NULL
                      OR rollup.group_atomic_metric_id IS NOT NULL
                    THEN master.atomic_metric_id
                END)                                           AS done_count
            FROM ESG_MATERIALITY_SELECTED_SUB_ISSUE sub
            LEFT JOIN ESG_SUB_ISSUE_MASTER sub_master
                ON sub.sub_issue_code = sub_master.sub_issue_code
            LEFT JOIN ESG_ATOMIC_METRIC_MASTER master
                ON sub.sub_issue_code = master.sub_issue_code
            LEFT JOIN ESG_KPI_FACT fact
                ON master.atomic_metric_id = fact.atomic_metric_id
            LEFT JOIN ESG_GROUP_ROLLUP_RESULT rollup
                ON master.atomic_metric_id = rollup.group_atomic_metric_id
            WHERE sub.esg_materiality_run_id = ?
            GROUP BY sub.sub_issue_code, sub_master.sub_issue_name_kr
            ORDER BY sub.selected_rank_no ASC
            """,
            (runId,),
        )

        items = [
            {
                "subIssueCode": r["sub_issue_code"],
                "subIssueName": r["sub_issue_name"],
                "totalCount": int(r["total_count"] or 0),
                "doneCount": int(r["done_count"] or 0),
            }
            for r in (rows or [])
        ]

        return {"runId": runId, "items": items}
    except HTTPException:
        raise
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
