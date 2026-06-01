from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.models.reportworkflow import (
    ReportWorkflowResponseDto,
    ReportWorkflowStartRequestDto,
)
from src.services.reportworkflows.service import getCurrent, getG0Status, getRun, resumeWorkflow, startWorkflow
from src.utils.companyscope import checkScope


reportWorkflowRouter = APIRouter(prefix="/v1/report-workflow", tags=["report-workflow"])


def requireUser(response: Response, request: Request):
    from src.utils.auth import get_token
    from src.utils.settings import settings

    token = request.cookies.get(settings.cookie_key)
    return get_token(response, token)


@reportWorkflowRouter.get(
    "/current",
    response_model=ReportWorkflowResponseDto,
    summary="Get current report workflow status",
)
async def getCurrentRoute(
    companyId: int = Query(...),
    reportingYear: int = Query(...),
    userModel=Depends(requireUser),
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


@reportWorkflowRouter.post(
    "/start",
    response_model=ReportWorkflowResponseDto,
    summary="Start report workflow basis selection",
)
async def startWorkflowRoute(
    request: ReportWorkflowStartRequestDto,
    userModel=Depends(requireUser),
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


@reportWorkflowRouter.post(
    "/{runId}/resume",
    response_model=ReportWorkflowResponseDto,
    summary="Resume existing report workflow and repair legacy G0 cycle",
)
async def resumeWorkflowRoute(runId: int, userModel=Depends(requireUser)):
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


@reportWorkflowRouter.get(
    "/{runId}/g0-status",
    response_model=ReportWorkflowResponseDto,
    summary="Get G0 readiness for report workflow",
)
async def getG0StatusRoute(runId: int, userModel=Depends(requireUser)):
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


__all__ = ["reportWorkflowRouter"]


def _userId(userModel):
    if isinstance(userModel, dict):
        return userModel.get("id")
    return getattr(userModel, "id", None)
