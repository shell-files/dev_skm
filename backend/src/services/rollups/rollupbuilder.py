"""
rollupbuilder.py
레이어: Service (rollups)
역할: 롤업 배치 빌더 — 배치 생성·스코프 미리보기·요청 목록 구성.
"""
from __future__ import annotations

from typing import Optional

from src.models.rollup import (
    RollupBatchStatusDto,
    RollupBatchSummaryDto,
    RollupInputWorkspaceDto,
    RollupRequestItemDto,
    RollupRequestMetricItemDto,
    RollupSourceSendStatusDto,
)
from src.utils.calculationengine import normalizeSource
from src.utils.companyscope import resolveScope
from src.utils.typeutils import formatDatetime as formatDateTime
from src.services.rollups.rollupexceptions import RollupError


def loadRepository():
    """rolluprepository 모듈을 지연 임포트해 반환한다."""
    from src.repositories import rolluprepository
    return rolluprepository


def loadCalculator():
    """롤업 계산기 모듈을 지연 임포트해 반환한다."""
    from src.services.rollups import calculator
    return calculator


def getActorUserId(userModel) -> Optional[int]:
    """dict 또는 객체 형태의 userModel에서 현재 사용자 ID를 int로 추출한다."""
    if isinstance(userModel, dict):
        userId = userModel.get("id")
    else:
        userId = getattr(userModel, "id", None)
    try:
        return int(userId) if userId is not None else None
    except (TypeError, ValueError):
        return None


def getSource(userModel) -> int:
    """userModel에서 소스 기업 ID를 추출하고 없으면 RollupError를 발생시킨다."""
    sourceCompanyId = resolveScope(userModel)
    if sourceCompanyId is None:
        raise RollupError(403, "COMPANY_SCOPE_REQUIRED", "Company scope is required.")
    return int(sourceCompanyId)


def dumpModel(model) -> dict:
    """Pydantic v1/v2 모델을 dict로 직렬화한다."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def resolvePreviewMetricIds(rollupRepository, purposeCode: str, parentCompanyId: int, sourceCycleId: Optional[int]) -> list[str]:
    """목적 코드에 따라 미리보기 대상 지표 ID 목록을 조회해 반환한다."""
    if purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK:
        return ["G0-02"]
    from src.repositories.onboardingscoperepository import listMetricScopes
    scopeRows = listMetricScopes(int(sourceCycleId), parentCompanyId)
    metricIds = [
        str(row.get("metric_id") or "").strip()
        for row in scopeRows
        if str(row.get("approval_policy_code") or "").strip().upper() == "PROMOTE_TO_KPI_FACT_AND_ROLLUP"
    ]
    return sorted({metricId for metricId in metricIds if metricId})


def resolveExternalAtomicIdsFromRules(rules: list[dict], sources: list[dict]) -> list[str]:
    """계산 규칙 소스 원자 지표 중 산출 대상이 아닌 외부 입력용 원자 지표 ID 목록을 반환한다."""
    targetAtomicIds = {
        str(rule.get("target_atomic_metric_id") or "").strip()
        for rule in rules
        if str(rule.get("target_atomic_metric_id") or "").strip()
    }
    sourceAtomicIds = {
        normalizeSource(source).get("sourceAtomicMetricId")
        for source in sources
        if normalizeSource(source).get("sourceAtomicMetricId")
    }
    return sorted(sourceAtomicIds - targetAtomicIds)


def resolveBatchRequestedMetricIds(batch: dict) -> list[str]:
    """배치 스냅샷 또는 목적 코드·사이클로부터 요청된 지표 ID 목록을 결정한다."""
    rollupRepository = loadRepository()
    batchId = batch.get("batchId") if batch.get("batchId") is not None else batch.get("id")
    if batchId is not None:
        snapshotMetricIds = rollupRepository.listRequestedMetricIdsFromBatchScope(int(batchId))
        if snapshotMetricIds:
            return snapshotMetricIds
    purposeCode = str(batch.get("rollupPurposeCode") or batch.get("rollup_purpose_code") or "").strip().upper()
    sourceCycleId = batch.get("sourceCycleId") if batch.get("sourceCycleId") is not None else batch.get("source_cycle_id")
    parentCompanyId = batch.get("parentCompanyId") if batch.get("parentCompanyId") is not None else batch.get("parent_company_id")
    if purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK:
        return ["G0-02"]
    if purposeCode == rollupRepository.ROLLUP_PURPOSE_REPORT_DISCLOSURE and sourceCycleId is not None:
        return resolvePreviewMetricIds(rollupRepository, purposeCode, int(parentCompanyId), int(sourceCycleId))
    return []


def buildReadinessStatus(requiredAtomicCount: int, approvedAtomicCount: int, missingAtomicCount: int) -> str:
    """필수·승인·미승인 원자 수를 기반으로 NOT_STARTED·PARTIAL·READY 준비 상태 문자열을 반환한다."""
    if requiredAtomicCount <= 0:
        return "NOT_STARTED"
    if approvedAtomicCount <= 0:
        return "NOT_STARTED"
    if missingAtomicCount > 0:
        return "PARTIAL"
    return "READY"


def buildActionableInputMetricIds(
    requestedMetricIds: list[str],
    dependencyItems: list[RollupRequestMetricItemDto],
) -> list[str]:
    metricIds = {
        str(metricId or "").strip()
        for metricId in requestedMetricIds or []
        if str(metricId or "").strip()
    }
    for item in dependencyItems or []:
        if item.missingAtomicMetricIds:
            metricIds.add(item.metricId)
    return sorted(metricIds)


def buildBatchMetricScope(batch: dict) -> dict:
    rollupRepository = loadRepository()
    requestedMetricIds = resolveBatchRequestedMetricIds(batch)
    scopes = rollupRepository.listScope(int(batch["batchId"] if batch.get("batchId") is not None else batch["id"]))
    resolvedMetricIds = sorted({
        str(scope.get("metric_id") or "").strip()
        for scope in scopes
        if str(scope.get("metric_id") or "").strip()
    })
    dependencyMetricIds = [mid for mid in resolvedMetricIds if mid not in set(requestedMetricIds)]
    return {
        "requestedMetricIds": requestedMetricIds,
        "resolvedMetricIds": resolvedMetricIds,
        "dependencyMetricIds": dependencyMetricIds,
    }


def buildMetricReadinessItems(
    batchId: int,
    missingAtomicIds: list[str],
    metricIds: Optional[list[str]] = None,
) -> list[RollupRequestMetricItemDto]:
    rollupRepository = loadRepository()
    scopes = rollupRepository.listScope(batchId)
    metricFilter = set(metricIds or [])
    targetAtomicIds = {
        str(scope.get("group_atomic_metric_id") or "").strip()
        for scope in scopes
        if str(scope.get("group_atomic_metric_id") or "").strip()
    }
    requiredByMetric = {}
    for scope in scopes:
        metricId = str(scope.get("metric_id") or "").strip()
        if not metricId:
            continue
        if metricFilter and metricId not in metricFilter:
            continue
        for atomicId in scope.get("sourceAtomicMetricIds") or []:
            if atomicId and atomicId not in targetAtomicIds:
                requiredByMetric.setdefault(metricId, set()).add(atomicId)
    atomicMetadata = rollupRepository.listAtomicMetadata(
        sorted({atomicId for atomicIds in requiredByMetric.values() for atomicId in atomicIds})
    )
    metricNameByMetric = {}
    for row in atomicMetadata:
        metricId = row.get("metricId")
        if metricId and row.get("metricName"):
            metricNameByMetric.setdefault(metricId, row.get("metricName"))
    missingSet = set(missingAtomicIds or [])
    items = []
    for metricId in sorted(requiredByMetric.keys()):
        requiredAtomicIds = sorted(requiredByMetric[metricId])
        metricMissingIds = [atomicId for atomicId in requiredAtomicIds if atomicId in missingSet]
        items.append(
            RollupRequestMetricItemDto(
                metricId=metricId,
                metricName=metricNameByMetric.get(metricId),
                requiredAtomicCount=len(requiredAtomicIds),
                approvedAtomicCount=max(0, len(requiredAtomicIds) - len(metricMissingIds)),
                missingAtomicMetricIds=metricMissingIds,
            )
        )
    return items


def buildRequestItem(req: dict, sourceCompanyId: int) -> RollupRequestItemDto:
    batchId = int(req["batchId"])
    rollupRepository = loadRepository()
    readiness = rollupRepository.buildSourceReadiness(batchId, [sourceCompanyId], int(req["reportingYear"]))
    missingAtomicIds = readiness["missingByCompany"].get(str(sourceCompanyId), [])
    metricScope = buildBatchMetricScope(req)
    requestedMetricIds = metricScope["requestedMetricIds"]
    requiredAtomicCount = int(readiness.get("requiredAtomicCount") or 0)
    approvedAtomicCount = max(0, requiredAtomicCount - len(missingAtomicIds))
    return RollupRequestItemDto(
        batchId=batchId,
        batchCode=req.get("batchCode"),
        sourceCycleId=int(req["sourceCycleId"]) if req.get("sourceCycleId") is not None else None,
        parentCompanyId=req["parentCompanyId"],
        parentCompanyCode=req.get("parentCompanyCode"),
        parentCompanyName=req.get("parentCompanyName"),
        reportingYear=req["reportingYear"],
        rollupPurposeCode=req.get("rollupPurposeCode") or "",
        metricScopeCode=req.get("metricScopeCode") or "",
        requestStatus=req.get("requestStatus") or "",
        inputStatus=req.get("inputStatus") or "",
        approvalStatus=req.get("approvalStatus") or "",
        transferStatus=req.get("transferStatus") or "",
        sendReadyYn=bool(readiness["readyYn"]),
        missingAtomicMetricIds=missingAtomicIds,
        readinessStatus=buildReadinessStatus(requiredAtomicCount, approvedAtomicCount, len(missingAtomicIds)),
        currentApprovedAtomicCount=approvedAtomicCount,
        currentMissingAtomicCount=len(missingAtomicIds),
        metricCount=len(requestedMetricIds),
        requiredAtomicCount=requiredAtomicCount,
        approvedAtomicCount=approvedAtomicCount,
        missingAtomicCount=len(missingAtomicIds),
        metricIds=requestedMetricIds,
        requestedMetricCount=len(requestedMetricIds),
        requestedMetricIds=requestedMetricIds,
        resolvedMetricCount=len(metricScope["resolvedMetricIds"]),
        resolvedMetricIds=metricScope["resolvedMetricIds"],
        dependencyMetricIds=metricScope["dependencyMetricIds"],
    )


def resolveInputWorkspace(
    sourceCompanyId: int,
    reportingYear: int,
    metricIds: list[str],
) -> RollupInputWorkspaceDto:
    rollupRepository = loadRepository()
    workspace = rollupRepository.findActiveInputWorkspace(sourceCompanyId, reportingYear, metricIds)
    if not workspace:
        return RollupInputWorkspaceDto(
            availableYn=False,
            reportingYear=reportingYear,
            reason="INPUT_WORKSPACE_NOT_READY",
        )
    return RollupInputWorkspaceDto(
        availableYn=True,
        cycleId=int(workspace["cycleId"]),
        cycleType=workspace.get("cycleType"),
        reportingYear=int(workspace.get("reportingYear") or reportingYear),
    )


def buildSourceSendStatus(source: dict) -> RollupSourceSendStatusDto:
    return RollupSourceSendStatusDto(
        batchId=int(source["esg_rollup_batch_id"]),
        parentCompanyId=int(source["parent_company_id"]),
        sourceCompanyId=int(source["source_company_id"]),
        requestStatus=source.get("request_status") or "",
        transferStatus=source.get("transfer_status") or "",
        sentAt=formatDateTime(source.get("sent_at")),
    )


def buildSummary(summary: dict) -> RollupBatchSummaryDto:
    requestedCount = int(summary.get("requestedCount") or 0)
    pendingCount = int(summary.get("pendingCount") or 0)
    return RollupBatchSummaryDto(
        batchId=int(summary["batchId"]),
        parentCompanyId=int(summary["parentCompanyId"]),
        reportingYear=int(summary["reportingYear"]),
        rollupPurposeCode=summary.get("rollupPurposeCode") or "",
        metricScopeCode=summary.get("metricScopeCode") or "",
        batchStatus=summary.get("batchStatus") or "",
        requestedCount=requestedCount,
        sentCount=int(summary.get("sentCount") or 0),
        pendingCount=pendingCount,
        calculateReadyYn=requestedCount > 0 and pendingCount == 0,
        dmaReadyYn=bool(summary.get("dmaReadyYn")),
        reportReadyYn=bool(summary.get("reportReadyYn")),
    )


def buildBatchStatus(batch: dict, sourceCompanyIds: list[int]) -> RollupBatchStatusDto:
    return RollupBatchStatusDto(
        batchId=int(batch["id"]),
        runId=int(batch.get("run_id") or 0) if batch.get("run_id") else None,
        sourceCycleId=int(batch.get("source_cycle_id") or 0) if batch.get("source_cycle_id") else None,
        rollupPurposeCode=batch.get("rollup_purpose_code") or "",
        metricScopeCode=batch.get("metric_scope_code") or "",
        batchStatus=batch.get("batch_status") or "pending",
        dmaReadyYn=bool(batch.get("dma_ready_yn")),
        reportReadyYn=bool(batch.get("report_ready_yn")),
        sourceCompanyIds=[int(companyId) for companyId in sourceCompanyIds],
    )
