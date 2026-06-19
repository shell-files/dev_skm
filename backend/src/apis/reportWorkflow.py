"""
reportWorkflow.py
레이어: API Router
역할: 보고서 워크플로우 시작·재개·현황 조회 및 POST_DMA 범위 초기화 엔드포인트.

엔드포인트:
  GET  /current                         — 현재 보고서 워크플로우 상태 조회
  POST /start                           — 보고서 워크플로우 기준 선택 시작
  GET  /projects                        — 연도별 보고서 워크플로우 프로젝트 목록 조회
  POST /{runId}/resume                  — 기존 보고서 워크플로우 재개 및 레거시 G0 사이클 복구
  POST /{runId}/post-dma-scope/initialize — 선정된 Sub-Issue 기반 POST_DMA_DISCLOSURE 온보딩 범위 초기화
  GET  /{runId}/g0-status               — 보고서 워크플로우 G0 준비 상태 조회
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.models.reportworkflow import (
    ReportWorkflowPostDmaScopeResponseDto,
    ReportWorkflowProjectListResponseDto,
    ReportWorkflowResponseDto,
    ReportWorkflowStartRequestDto,
)
from src.services.reportworkflows.service import (
    getCurrent,
    getG0Status,
    getRun,
    initializePostDmaDisclosureScope,
    listProjects,
    resumeWorkflow,
    startWorkflow,
)
from src.utils.companyscope import checkScope
from src.utils.settings import settings
from src.utils.validatetok import validateToken
from src.utils.auth import get_domain, get_token

_actionRouter = APIRouter()


@_actionRouter.get(
    "/current",
    response_model=ReportWorkflowResponseDto,
    summary="현재 보고서 워크플로우 상태 조회",
)
async def getCurrentRoute(
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    userModel = Depends(get_token)
):
    try:
        checkScope(companyId, userModel)

        return getCurrent(companyId, reportingYear)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.post(
    "/start",
    response_model=ReportWorkflowResponseDto,
    summary="보고서 워크플로우 기준 선택 시작",
)
async def startWorkflowRoute(
    request: ReportWorkflowStartRequestDto,
    userModel=Depends(get_token),
):
    try:
        checkScope(request.companyId, userModel)
        return startWorkflow(request, _userId(userModel))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.get(
    "/projects",
    response_model=ReportWorkflowProjectListResponseDto,
    summary="연도별 보고서 워크플로우 프로젝트 목록 조회",
)
async def listProjectsRoute(
    companyId: int = Query(...),
    userModel=Depends(get_token),
):
    try:
        checkScope(companyId, userModel)
        return listProjects(companyId)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.post(
    "/{runId}/resume",
    response_model=ReportWorkflowResponseDto,
    summary="기존 보고서 워크플로우 재개 및 레거시 G0 사이클 복구",
)
async def resumeWorkflowRoute(runId: int, userModel=Depends(get_token)):
    try:
        run = getRun(runId)
        if not run:
            raise HTTPException(status_code=404, detail=f"No ESG_MATERIALITY_RUN found for runId={runId}")
        checkScope(int(run["company_id"]), userModel)
        return resumeWorkflow(runId, _userId(userModel))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.post(
    "/{runId}/post-dma-scope/initialize",
    response_model=ReportWorkflowPostDmaScopeResponseDto,
    summary="선정된 Sub-Issue 기반 POST_DMA_DISCLOSURE 온보딩 범위 초기화",
)
async def initializePostDmaScopeRoute(runId: int, userModel=Depends(get_token)):
    try:
        run = getRun(runId)
        if not run:
            raise HTTPException(status_code=404, detail=f"No ESG_MATERIALITY_RUN found for runId={runId}")
        checkScope(int(run["company_id"]), userModel)
        return initializePostDmaDisclosureScope(runId, _userId(userModel))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=statusForValueError(e), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.get(
    "/{runId}/g0-status",
    response_model=ReportWorkflowResponseDto,
    summary="보고서 워크플로우 G0 준비 상태 조회",
)
async def getG0StatusRoute(runId: int, userModel=Depends(get_token)):
    try:
        run = getRun(runId)
        if not run:
            raise HTTPException(status_code=404, detail=f"No ESG_MATERIALITY_RUN found for runId={runId}")
        checkScope(int(run["company_id"]), userModel)
        return getG0Status(runId)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


router = APIRouter()
router.include_router(_actionRouter)

reportWorkflowRouter = APIRouter(prefix="/v1/report-workflow", tags=["report-workflow"])
reportWorkflowRouter.include_router(_actionRouter)


__all__ = ["router", "reportWorkflowRouter"]


def _userId(userModel):
    if isinstance(userModel, dict):
        return userModel.get("id")
    return getattr(userModel, "id", None)


def statusForValueError(error: ValueError) -> int:
    message = str(error)
    if message.startswith(
        (
            "MATERIALITY_SELECTION_NOT_CONFIRMED",
            "SELECTED_SUB_ISSUE_MAPPING_NOT_READY",
            "POST_DMA_DISCLOSURE_RUN_READ_ONLY",
            "POST_DMA_DISCLOSURE_SOURCE_RUN_CONFLICT",
            "POST_DMA_DISCLOSURE_CYCLE_NOT_ACTIVE",
            "POST_DMA_SCOPE_MISMATCH_REQUIRES_REVIEW",
        )
    ):
        return 409
    return 404
