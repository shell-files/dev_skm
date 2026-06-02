from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from src.utils.auth import get_token

from src.models.rollup import (
    RollupBatchRequestDto,
    RollupBatchResponseDto,
    RollupBatchSummaryResponseDto,
    RollupCalculateResponseDto,
    RollupRequestResponseDto,
    RollupSourceSendResponseDto,
    RollupSubsidiaryResponseDto,
)
from src.services.rollups.service import (
    RollupError,
    calcBatch,
    getStatus,
    listRequests,
    listSubsidiaries,
    saveBatch,
    sendSource,
)

rollupRouter = APIRouter(prefix="/v1/rollups", tags=["rollups"])


# def requireUser(response: Response, request: Request):
#     from src.utils.auth import get_token
#     from src.utils.settings import settings

#     token = request.cookies.get(settings.cookie_key)
#     return get_token(response, token)


@rollupRouter.get(
    "/subsidiaries",
    response_model=RollupSubsidiaryResponseDto,
    summary="List subsidiaries available for DMA precheck rollup",
)
async def listSubsidiariesRoute(
    runId: int = Query(...),
    userModel=Depends(get_token),
):
    try:
        return listSubsidiaries(runId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rollupRouter.post(
    "/batches",
    response_model=RollupBatchResponseDto,
    summary="Create DMA precheck G0-02 rollup batch",
)
async def saveBatchRoute(
    request: RollupBatchRequestDto,
    userModel=Depends(get_token),
):
    try:
        return saveBatch(request, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rollupRouter.post(
    "/batches/{batchId}/calculate",
    response_model=RollupCalculateResponseDto,
    summary="Calculate DMA precheck G0-02 rollup batch",
)
async def calcBatchRoute(batchId: int, userModel=Depends(get_token)):
    try:
        return calcBatch(batchId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rollupRouter.get(
    "/requests",
    response_model=RollupRequestResponseDto,
    summary="List rollup transfer requests for current source company",
)
async def listRequestsRoute(userModel=Depends(get_token)):
    try:
        return listRequests(userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rollupRouter.post(
    "/batches/{batchId}/sources/send",
    response_model=RollupSourceSendResponseDto,
    summary="Send approved G0-02 source data to parent rollup batch",
)
async def sendSourceRoute(batchId: int, userModel=Depends(get_token)):
    try:
        return sendSource(batchId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rollupRouter.get(
    "/batches/{batchId}/status",
    response_model=RollupBatchSummaryResponseDto,
    summary="Get DMA precheck rollup batch source transfer status",
)
async def getStatusRoute(batchId: int, userModel=Depends(get_token)):
    try:
        return getStatus(batchId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def buildErrorResponse(error: RollupError) -> JSONResponse:
    return JSONResponse(
        status_code=error.statusCode,
        content={
            "success": False,
            "code": error.code,
            "message": error.message,
            "data": error.data,
        },
    )


__all__ = ["rollupRouter"]
