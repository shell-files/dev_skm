from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from src.utils.auth import get_token

from src.models.rollup import (
    RollupBatchRequestDto,
    RollupBatchResponseDto,
    RollupActiveBatchResponseDto,
    RollupBatchSourceListResponseDto,
    RollupBatchSummaryResponseDto,
    RollupCalculateResponseDto,
    RollupRequestDetailResponseDto,
    RollupRequestResponseDto,
    RollupScopePreviewResponseDto,
    RollupSourceSendResponseDto,
    RollupSubsidiaryResponseDto,
)
from src.services.rollups.service import (
    RollupError,
    calcBatch,
    getActiveBatchStatus,
    getRequestDetail,
    getScopePreview,
    getStatus,
    listBatchSources,
    listRequestsForSource,
    listSubsidiaries,
    saveBatch,
    sendSource,
)

_actionRouter = APIRouter()


@_actionRouter.get(
    "/scope-preview",
    response_model=RollupScopePreviewResponseDto,
    summary="Preview rollup metric and atomic scope",
)
async def getScopePreviewRoute(
    runId: Optional[int] = Query(None),
    sourceCycleId: Optional[int] = Query(None),
    rollupPurposeCode: Optional[str] = Query("DMA_PRECHECK"),
    metricScopeCode: Optional[str] = Query("G0_02_FINANCIAL_BASIS"),
    userModel=Depends(get_token),
):
    try:
        return getScopePreview(runId, sourceCycleId, rollupPurposeCode, metricScopeCode, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.get(
    "/subsidiaries",
    response_model=RollupSubsidiaryResponseDto,
    summary="List subsidiaries available for DMA precheck rollup",
)
async def listSubsidiariesRoute(
    runId: Optional[int] = Query(None),
    sourceCycleId: Optional[int] = Query(None),
    rollupPurposeCode: Optional[str] = Query("DMA_PRECHECK"),
    metricScopeCode: Optional[str] = Query("G0_02_FINANCIAL_BASIS"),
    userModel=Depends(get_token),
):
    try:
        return listSubsidiaries(runId, sourceCycleId, rollupPurposeCode, metricScopeCode, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.post(
    "/batches",
    response_model=RollupBatchResponseDto,
    summary="Create rollup batch",
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


@_actionRouter.get(
    "/batches/active",
    response_model=RollupActiveBatchResponseDto,
    summary="Get active rollup batch status",
)
async def getActiveBatchRoute(
    runId: Optional[int] = Query(None),
    sourceCycleId: Optional[int] = Query(None),
    rollupPurposeCode: str = Query("DMA_PRECHECK"),
    metricScopeCode: str = Query("G0_02_FINANCIAL_BASIS"),
    userModel=Depends(get_token),
):
    try:
        return getActiveBatchStatus(runId, sourceCycleId, rollupPurposeCode, metricScopeCode, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.post(
    "/batches/{batchId}/calculate",
    response_model=RollupCalculateResponseDto,
    summary="Calculate rollup batch",
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


@_actionRouter.get(
    "/requests",
    response_model=RollupRequestResponseDto,
    summary="List rollup transfer requests for current source company",
)
async def listRequestsRoute(
    rollupPurposeCode: Optional[str] = Query("DMA_PRECHECK"),
    metricScopeCode: Optional[str] = Query("G0_02_FINANCIAL_BASIS"),
    includeSentYn: bool = Query(True),
    transferStatus: Optional[str] = Query(None),
    allPurposesYn: bool = Query(False),
    userModel=Depends(get_token)
):
    try:
        return listRequestsForSource(rollupPurposeCode, metricScopeCode, includeSentYn, transferStatus, allPurposesYn, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.get(
    "/requests/{batchId}",
    response_model=RollupRequestDetailResponseDto,
    summary="Get rollup transfer request detail for current source company",
)
async def getRequestDetailRoute(batchId: int, userModel=Depends(get_token)):
    try:
        return getRequestDetail(batchId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.post(
    "/requests/{batchId}/workspace/ensure",
    response_model=RollupRequestDetailResponseDto,
    summary="Ensure and return rollup response workspace",
)
async def ensureRollupResponseWorkspaceRoute(batchId: int, userModel=Depends(get_token)):
    from src.services.rollups.service import ensureRollupResponseWorkspace
    try:
        return ensureRollupResponseWorkspace(batchId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.get(
    "/batches/{batchId}/sources",
    response_model=RollupBatchSourceListResponseDto,
    summary="List rollup batch source transfer status",
)
async def listBatchSourcesRoute(batchId: int, userModel=Depends(get_token)):
    try:
        return listBatchSources(batchId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.post(
    "/batches/{batchId}/sources/send",
    response_model=RollupSourceSendResponseDto,
    summary="Send approved source data",
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


@_actionRouter.get(
    "/batches/{batchId}/status",
    response_model=RollupBatchSummaryResponseDto,
    summary="Get rollup batch source transfer status",
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


router = APIRouter()
router.include_router(_actionRouter)

rollupRouter = APIRouter(prefix="/v1/rollups", tags=["rollups"])
rollupRouter.include_router(_actionRouter)


__all__ = ["router", "rollupRouter"]
