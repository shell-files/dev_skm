<<<<<<< HEAD
"""
rollup.py
레이어: API Router
역할: ESG 데이터 롤업 배치 생성·계산·전송·상태 조회 엔드포인트.

엔드포인트:
  GET  /scope-preview                        — 롤업 지표 및 원자 스코프 미리보기
  GET  /subsidiaries                         — DMA 사전 점검 롤업 가능 자회사 목록 조회
  POST /batches                              — 롤업 배치 생성
  GET  /batches/active                       — 활성 롤업 배치 상태 조회
  POST /batches/{batchId}/calculate          — 롤업 배치 계산 실행
  GET  /requests                             — 현재 소스 회사의 롤업 이전 요청 목록 조회
  GET  /requests/{batchId}                   — 롤업 이전 요청 상세 조회
  POST /requests/{batchId}/workspace/ensure  — 롤업 응답 워크스페이스 확보 및 조회
  GET  /batches/{batchId}/sources            — 롤업 배치 소스 이전 상태 목록 조회
  POST /batches/{batchId}/sources/send       — 승인된 소스 데이터 전송
  GET  /batches/{batchId}/status             — 롤업 배치 소스 이전 상태 조회
  GET  /batches/{batchId}/baseline-requirements — YoY 규칙용 전년도 연결 기준값 요건 목록 조회
  POST /batches/{batchId}/baseline-values    — 전년도 연결 기준값을 ESG_KPI_FACT에 저장
"""
=======
>>>>>>> origin/skm_test
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from src.utils.auth import get_token

from src.models.rollup import (
    RollupBaselineRequirementResponseDto,
    RollupBaselineSaveResponseDto,
    RollupBaselineValuesRequestDto,
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
    getBaselineRequirements,
    getRequestDetail,
    getScopePreview,
    getStatus,
    listBatchSources,
    listRequestsForSource,
    listSubsidiaries,
    saveBaselineValues,
    saveBatch,
    sendSource,
)

_actionRouter = APIRouter()


@_actionRouter.get(
    "/scope-preview",
    response_model=RollupScopePreviewResponseDto,
<<<<<<< HEAD
    summary="롤업 지표 및 원자 스코프 미리보기",
=======
    summary="Preview rollup metric and atomic scope",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="DMA 사전 점검 롤업 가능 자회사 목록 조회",
=======
    summary="List subsidiaries available for DMA precheck rollup",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="롤업 배치 생성",
=======
    summary="Create rollup batch",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="활성 롤업 배치 상태 조회",
=======
    summary="Get active rollup batch status",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="롤업 배치 계산 실행",
=======
    summary="Calculate rollup batch",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="현재 소스 회사의 롤업 이전 요청 목록 조회",
=======
    summary="List rollup transfer requests for current source company",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="롤업 이전 요청 상세 조회",
=======
    summary="Get rollup transfer request detail for current source company",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="롤업 응답 워크스페이스 확보 및 조회",
=======
    summary="Ensure and return rollup response workspace",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="롤업 배치 소스 이전 상태 목록 조회",
=======
    summary="List rollup batch source transfer status",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="승인된 소스 데이터 전송",
=======
    summary="Send approved source data",
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    summary="롤업 배치 소스 이전 상태 조회",
=======
    summary="Get rollup batch source transfer status",
>>>>>>> origin/skm_test
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


@_actionRouter.get(
    "/batches/{batchId}/baseline-requirements",
    response_model=RollupBaselineRequirementResponseDto,
<<<<<<< HEAD
    summary="YoY 규칙용 전년도 연결 기준값 요건 목록 조회",
=======
    summary="List prior-year consolidated baseline requirements for YoY rules",
>>>>>>> origin/skm_test
)
async def getBaselineRequirementsRoute(batchId: int, userModel=Depends(get_token)):
    try:
        return getBaselineRequirements(batchId, userModel)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RollupError as e:
        return buildErrorResponse(e)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@_actionRouter.post(
    "/batches/{batchId}/baseline-values",
    response_model=RollupBaselineSaveResponseDto,
<<<<<<< HEAD
    summary="전년도 연결 기준값을 ESG_KPI_FACT에 저장",
=======
    summary="Save prior-year consolidated baseline values into ESG_KPI_FACT",
>>>>>>> origin/skm_test
)
async def saveBaselineValuesRoute(
    batchId: int,
    request: RollupBaselineValuesRequestDto,
    userModel=Depends(get_token),
):
    try:
        return saveBaselineValues(batchId, request, userModel)
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
