from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.models.reportworkflow import (
    ReportWorkflowProjectListResponseDto,
    ReportWorkflowResponseDto,
    ReportWorkflowStartRequestDto,
)
from src.services.reportworkflows.service import getCurrent, getG0Status, getRun, listProjects, resumeWorkflow, startWorkflow
from src.utils.companyscope import checkScope
from src.utils.settings import settings
from src.utils.validatetok import validateToken
from src.utils.auth import get_domain, get_token

_actionRouter = APIRouter()


@_actionRouter.get(
    "/current",
    response_model=ReportWorkflowResponseDto,
    summary="Get current report workflow status",
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
    summary="Start report workflow basis selection",
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
    summary="List yearly report workflow projects",
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
    summary="Resume existing report workflow and repair legacy G0 cycle",
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


@_actionRouter.get(
    "/{runId}/g0-status",
    response_model=ReportWorkflowResponseDto,
    summary="Get G0 readiness for report workflow",
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
