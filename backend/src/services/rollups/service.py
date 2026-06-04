"""
Domain: ESG Rollup
Layer: service/workflow
Responsibility:
- List subsidiaries eligible for DMA precheck rollup
- Create DMA precheck G0-02 rollup batches
- Calculate approved G0-02 consolidated SUM results
Public functions:
- listSubsidiaries
- saveBatch
- calcBatch
- listRequests
- sendSource
- getStatus
Do not:
- do not modify DB schema
- do not calculate unsupported formulas
- do not use unapproved onboarding values
- do not bypass company scope isolation
- do not connect DMA scoring pipelines
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.models.rollup import (
    RollupBatchRequestDto,
    RollupBatchResponseDto,
    RollupBatchSummaryDto,
    RollupBatchSummaryResponseDto,
    RollupBatchStatusDto,
    RollupCalculateResponseDto,
    RollupCalculateStatusDto,
    RollupRequestItemDto,
    RollupRequestListDto,
    RollupRequestResponseDto,
    RollupResultDto,
    RollupSourceSendResponseDto,
    RollupSourceSendStatusDto,
    RollupSubsidiaryDto,
    RollupSubsidiaryListDto,
    RollupSubsidiaryResponseDto,
)
from src.utils.companyscope import checkScope, resolveScope


class RollupError(Exception):
    def __init__(
        self,
        statusCode: int,
        code: str,
        message: str,
        data: Optional[dict] = None,
    ):
        super().__init__(message)
        self.statusCode = statusCode
        self.code = code
        self.message = message
        self.data = data or {}


def listSubsidiaries(runId: int, userModel) -> RollupSubsidiaryResponseDto:
    rollupRepository = loadRepository()
    run = getRunOrRaise(runId)
    checkScope(int(run["company_id"]), userModel)
    checkConsolidatedRun(run)
    items = [
        RollupSubsidiaryDto(
            companyId=item["companyId"],
            companyCode=item.get("companyCode"),
            companyName=item.get("companyName"),
        )
        for item in rollupRepository.listSubsidiaries(run)
    ]
    return RollupSubsidiaryResponseDto(data=RollupSubsidiaryListDto(runId=runId, items=items))


def saveBatch(request: RollupBatchRequestDto, userModel) -> RollupBatchResponseDto:
    rollupRepository = loadRepository()
    run = getRunOrRaise(request.runId)
    checkScope(int(run["company_id"]), userModel)
    checkConsolidatedRun(run)

    parentCompanyId = int(run["company_id"])
    selectedCompanyIds = normalizeCompanyIds(request.sourceCompanyIds)
    if not selectedCompanyIds:
        raise RollupError(422, "ROLLUP_SOURCE_REQUIRED", "At least one subsidiary source is required.")
    if parentCompanyId in selectedCompanyIds:
        raise RollupError(422, "ROLLUP_PARENT_SOURCE_NOT_ALLOWED", "Parent company is included automatically.")

    eligibleCompanyIds = {
        int(item["companyId"])
        for item in rollupRepository.listSubsidiaries(run)
    }
    invalidCompanyIds = [
        companyId
        for companyId in selectedCompanyIds
        if companyId not in eligibleCompanyIds
    ]
    if invalidCompanyIds:
        raise RollupError(
            403,
            "ROLLUP_SOURCE_SCOPE_FORBIDDEN",
            "One or more source companies are outside rollup scope.",
            {"invalidCompanyIds": invalidCompanyIds},
        )

    parentFacts = rollupRepository.listApprovedFacts([parentCompanyId], int(run["reporting_year"]))
    parentMissing = getMissingAtomicIds(parentCompanyId, parentFacts)
    if parentMissing:
        raise RollupError(
            409,
            "PARENT_G0_02_NOT_READY",
            "Parent G0-02 approved KPI facts are required before requesting subsidiary data.",
            {"missingAtomicMetricIds": parentMissing},
        )

    existingBatch = rollupRepository.getActiveBatch(request.runId)
    if existingBatch:
        return RollupBatchResponseDto(data=buildBatchStatus(existingBatch, rollupRepository.listSourceCompanyIds(int(existingBatch["id"]))))

    includedCompanyIds = [parentCompanyId, *selectedCompanyIds]
    facts = rollupRepository.listApprovedFacts(includedCompanyIds, int(run["reporting_year"]))
    sourceStatuses = buildSourceStatuses(run, includedCompanyIds, facts)
    batch = rollupRepository.saveBatch(
        run=run,
        includedCompanyIds=includedCompanyIds,
        sourceStatuses=sourceStatuses,
        actorUserId=getActorUserId(userModel),
    )
    if not batch:
        raise RollupError(500, "ROLLUP_BATCH_CREATE_FAILED", "Failed to create rollup batch.")
    return RollupBatchResponseDto(data=buildBatchStatus(batch, includedCompanyIds))


def calcBatch(batchId: int, userModel) -> RollupCalculateResponseDto:
    rollupRepository = loadRepository()
    rollupCalculator = loadCalculator()
    batch = rollupRepository.getBatch(batchId)
    if not batch:
        raise RollupError(404, "ROLLUP_BATCH_NOT_FOUND", "Rollup batch was not found.")
    checkScope(int(batch["parent_company_id"]), userModel)
    checkBatchScope(batch)

    sources = rollupRepository.listSources(batchId)
    if not sources:
        raise RollupError(409, "ROLLUP_SOURCE_NOT_FOUND", "Rollup source snapshot was not found.")
    transferStatus = checkTransferReady(batch, sources)
    if not transferStatus["readyYn"]:
        raise RollupError(
            409,
            "ROLLUP_SOURCE_NOT_SENT",
            "One or more subsidiary G0-02 data transfers are not complete.",
            {"notSentCompanyIds": transferStatus["notSentCompanyIds"]},
        )

    scopes = rollupRepository.listScope(batchId)
    scopeGroupAtoms = {scope.get("group_atomic_metric_id") for scope in scopes}
    unsupportedGroupAtoms = [
        atomicId
        for atomicId in scopeGroupAtoms
        if atomicId not in rollupRepository.GROUP_ATOMIC_IDS
    ]
    if unsupportedGroupAtoms:
        raise RollupError(
            422,
            "ROLLUP_SCOPE_UNSUPPORTED",
            "Only G0-02 group financial basis atomic scope is supported.",
            {"unsupportedGroupAtomicMetricIds": unsupportedGroupAtoms},
        )

    missingGroupAtoms = [
        atomicId
        for atomicId in rollupRepository.GROUP_ATOMIC_IDS
        if atomicId not in scopeGroupAtoms
    ]
    if missingGroupAtoms:
        raise RollupError(
            409,
            "ROLLUP_SCOPE_NOT_READY",
            "Rollup atomic scope is incomplete.",
            {"missingGroupAtomicMetricIds": missingGroupAtoms},
        )

    sourceCompanyIds = [int(source["source_company_id"]) for source in sources]
    facts = rollupRepository.listApprovedFacts(sourceCompanyIds, int(batch["reporting_year"]))
    missingSources = buildMissingSources(sourceCompanyIds, facts)
    if missingSources:
        raise RollupError(
            409,
            "ROLLUP_SOURCE_NOT_READY",
            "One or more source companies have incomplete approved G0-02 KPI facts.",
            {"missingSources": missingSources},
        )

    factMap = buildFactMap(facts)
    try:
        results = rollupCalculator.calcBatch(batch, sources, scopes, factMap)
    except ValueError as e:
        raise RollupError(422, "ROLLUP_FORMULA_UNSUPPORTED", str(e))

    if not rollupRepository.upsertResults(batch, results, getActorUserId(userModel)):
        raise RollupError(500, "ROLLUP_CALCULATE_FAILED", "Failed to calculate rollup batch.")

    refreshedBatch = rollupRepository.getBatch(batchId) or batch
    resultDtos = [
        RollupResultDto(
            groupAtomicMetricId=result["groupAtomicMetricId"],
            sourceAtomicMetricId=result["sourceAtomicMetricId"],
            formulaType=result["formulaType"],
            valueNumeric=result["valueNumeric"],
            unit=result.get("unit"),
        )
        for result in results
    ]
    statusDto = buildBatchStatus(refreshedBatch, sourceCompanyIds)
    return RollupCalculateResponseDto(
        data=RollupCalculateStatusDto(
            **statusDto.model_dump(),
            results=resultDtos,
        )
    )


def listRequests(userModel) -> RollupRequestResponseDto:
    rollupRepository = loadRepository()
    sourceCompanyId = getSource(userModel)
    requests = rollupRepository.listRequests(sourceCompanyId)
    facts = []
    for reportingYear in getRequestYears(requests):
        facts.extend(rollupRepository.listApprovedFacts([sourceCompanyId], reportingYear))
    items = [
        buildRequestItem(request, sourceCompanyId, facts)
        for request in requests
    ]
    return RollupRequestResponseDto(data=RollupRequestListDto(items=items))


def sendSource(batchId: int, userModel) -> RollupSourceSendResponseDto:
    rollupRepository = loadRepository()
    sourceCompanyId = getSource(userModel)
    batch = rollupRepository.getBatch(batchId)
    if not batch:
        raise RollupError(404, "ROLLUP_BATCH_NOT_FOUND", "Rollup batch was not found.")
    checkBatchScope(batch)
    checkBatchActive(batch)

    source = rollupRepository.getSource(batchId, sourceCompanyId)
    if not source:
        raise RollupError(
            404,
            "ROLLUP_SOURCE_REQUEST_NOT_FOUND",
            "Rollup source transfer request was not found.",
        )
    if int(source["source_company_id"]) == int(source["parent_company_id"]):
        raise RollupError(
            409,
            "ROLLUP_PARENT_SEND_NOT_ALLOWED",
            "Parent company data is included automatically and cannot be sent separately.",
        )

    if str(source.get("transfer_status") or "").lower() in {"sent", "received"}:
        return RollupSourceSendResponseDto(data=buildSourceSendStatus(source))

    facts = rollupRepository.listApprovedFacts([sourceCompanyId], int(source["reporting_year"]))
    missingAtomicIds = getMissingAtomicIds(sourceCompanyId, facts)
    if missingAtomicIds:
        raise RollupError(
            409,
            "SOURCE_G0_02_NOT_READY",
            "Approved G0-02 data is required before transfer.",
            {"missingAtomicMetricIds": missingAtomicIds},
        )

    updatedSource = rollupRepository.updateSourceSent(batchId, sourceCompanyId)
    if not updatedSource:
        raise RollupError(500, "ROLLUP_SOURCE_SEND_FAILED", "Failed to update rollup source transfer status.")
    return RollupSourceSendResponseDto(data=buildSourceSendStatus(updatedSource))


def getStatus(batchId: int, userModel) -> RollupBatchSummaryResponseDto:
    rollupRepository = loadRepository()
    batch = rollupRepository.getBatch(batchId)
    if not batch:
        raise RollupError(404, "ROLLUP_BATCH_NOT_FOUND", "Rollup batch was not found.")
    checkScope(int(batch["parent_company_id"]), userModel)
    checkBatchScope(batch)
    summary = rollupRepository.getStatus(batchId)
    if not summary:
        raise RollupError(404, "ROLLUP_BATCH_NOT_FOUND", "Rollup batch was not found.")
    return RollupBatchSummaryResponseDto(data=buildSummary(summary))


def getRunOrRaise(runId: int) -> dict:
    rollupRepository = loadRepository()
    run = rollupRepository.getRun(runId)
    if not run:
        raise RollupError(404, "REPORT_RUN_NOT_FOUND", "Report workflow run was not found.")
    return run


def checkConsolidatedRun(run: dict) -> None:
    if str(run.get("report_basis_type") or "").upper() != "CONSOLIDATED":
        raise RollupError(409, "REPORT_BASIS_NOT_CONSOLIDATED", "Rollup is available only for consolidated report basis.")


def checkBatchScope(batch: dict) -> None:
    rollupRepository = loadRepository()
    if str(batch.get("rollup_purpose_code") or "").upper() != rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK:
        raise RollupError(422, "ROLLUP_PURPOSE_UNSUPPORTED", "Unsupported rollup purpose.")
    if str(batch.get("metric_scope_code") or "").upper() != rollupRepository.METRIC_SCOPE_G0_02_FINANCIAL_BASIS:
        raise RollupError(422, "ROLLUP_METRIC_SCOPE_UNSUPPORTED", "Unsupported rollup metric scope.")


def checkBatchActive(batch: dict) -> None:
    batchStatus = str(batch.get("batch_status") or "").lower()
    if batchStatus in {"deleted", "cancelled", "canceled", "archived", "completed"}:
        raise RollupError(409, "ROLLUP_BATCH_NOT_ACTIVE", "Rollup batch is not active.")


def checkTransferReady(batch: dict, sources: list[dict]) -> dict:
    parentCompanyId = int(batch["parent_company_id"])
    parentReadyYn = any(
        int(source["source_company_id"]) == parentCompanyId
        and str(source.get("transfer_status") or "").lower() == TRANSFER_STATUS_RECEIVED
        for source in sources
    )
    notSentCompanyIds = [
        int(source["source_company_id"])
        for source in sources
        if int(source["source_company_id"]) != parentCompanyId
        and str(source.get("transfer_status") or "").lower() not in {
            TRANSFER_STATUS_SENT,
            TRANSFER_STATUS_RECEIVED,
        }
    ]
    if not parentReadyYn:
        notSentCompanyIds.insert(0, parentCompanyId)
    return {
        "readyYn": len(notSentCompanyIds) == 0,
        "notSentCompanyIds": notSentCompanyIds,
    }


def normalizeCompanyIds(companyIds: list[int]) -> list[int]:
    normalizedIds = []
    seenIds = set()
    for companyId in companyIds:
        numericCompanyId = int(companyId)
        if numericCompanyId in seenIds:
            raise RollupError(422, "ROLLUP_SOURCE_DUPLICATED", "Duplicate source company id is not allowed.")
        seenIds.add(numericCompanyId)
        normalizedIds.append(numericCompanyId)
    return normalizedIds


def buildSourceStatuses(run: dict, sourceCompanyIds: list[int], facts: list[dict]) -> list[dict]:
    rollupRepository = loadRepository()
    parentCompanyId = int(run["company_id"])
    reportingYear = int(run["reporting_year"])
    currentTime = datetime.now(timezone.utc).replace(tzinfo=None)
    statuses = []
    for sourceCompanyId in sourceCompanyIds:
        missingAtomicIds = getMissingAtomicIds(sourceCompanyId, facts)
        approvedCount = len(rollupRepository.SOURCE_ATOMIC_IDS) - len(missingAtomicIds)
        readyYn = approvedCount == len(rollupRepository.SOURCE_ATOMIC_IDS)
        parentYn = sourceCompanyId == parentCompanyId
        statuses.append(
            {
                "parentCompanyId": parentCompanyId,
                "sourceCompanyId": sourceCompanyId,
                "reportingYear": reportingYear,
                "approvedCount": approvedCount,
                "missingAtomicMetricIds": missingAtomicIds,
                "requestStatus": SOURCE_STATUS_RECEIVED if parentYn else SOURCE_STATUS_REQUESTED,
                "inputStatus": INPUT_STATUS_APPROVED if readyYn else (INPUT_STATUS_SUBMITTED if approvedCount > 0 else INPUT_STATUS_NOT_STARTED),
                "approvalStatus": APPROVAL_STATUS_APPROVED if readyYn else (APPROVAL_STATUS_SUBMITTED if approvedCount > 0 else APPROVAL_STATUS_PENDING),
                "transferStatus": TRANSFER_STATUS_RECEIVED if parentYn else TRANSFER_STATUS_NOT_SENT,
                "sentAt": currentTime if parentYn else None,
                "receivedAt": currentTime if parentYn else None,
                "approvedAt": currentTime if readyYn else None,
            }
        )
    return statuses


def buildMissingSources(companyIds: list[int], facts: list[dict]) -> list[dict]:
    missingSources = []
    for companyId in companyIds:
        missingAtomicIds = getMissingAtomicIds(companyId, facts)
        if missingAtomicIds:
            missingSources.append(
                {
                    "companyId": companyId,
                    "missingAtomicMetricIds": missingAtomicIds,
                }
            )
    return missingSources


def getMissingAtomicIds(companyId: int, facts: list[dict]) -> list[str]:
    rollupRepository = loadRepository()
    approvedAtomicIds = {
        fact["atomicMetricId"]
        for fact in facts
        if int(fact["companyId"]) == int(companyId)
    }
    return [
        atomicId
        for atomicId in rollupRepository.SOURCE_ATOMIC_IDS
        if atomicId not in approvedAtomicIds
    ]


def buildFactMap(facts: list[dict]) -> dict[tuple[int, str], dict]:
    return {
        (int(fact["companyId"]), fact["atomicMetricId"]): fact
        for fact in facts
    }


def buildRequestItem(request: dict, sourceCompanyId: int, facts: list[dict]) -> RollupRequestItemDto:
    missingAtomicIds = getMissingAtomicIdsForYear(
        sourceCompanyId,
        int(request["reportingYear"]),
        facts,
    )
    return RollupRequestItemDto(
        batchId=int(request["batchId"]),
        parentCompanyId=int(request["parentCompanyId"]),
        parentCompanyCode=request.get("parentCompanyCode"),
        parentCompanyName=request.get("parentCompanyName") or request.get("parentCompanyCode"),
        reportingYear=int(request["reportingYear"]),
        rollupPurposeCode=request.get("rollupPurposeCode") or "",
        metricScopeCode=request.get("metricScopeCode") or "",
        requestStatus=request.get("requestStatus") or "",
        transferStatus=request.get("transferStatus") or "",
        sendReadyYn=len(missingAtomicIds) == 0,
        missingAtomicMetricIds=missingAtomicIds,
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
    )


def buildBatchStatus(batch: dict, sourceCompanyIds: list[int]) -> RollupBatchStatusDto:
    return RollupBatchStatusDto(
        batchId=int(batch["id"]),
        runId=int(batch["run_id"]) if batch.get("run_id") is not None else None,
        rollupPurposeCode=batch.get("rollup_purpose_code") or "",
        metricScopeCode=batch.get("metric_scope_code") or "",
        batchStatus=batch.get("batch_status") or "pending",
        dmaReadyYn=bool(batch.get("dma_ready_yn")),
        sourceCompanyIds=[int(companyId) for companyId in sourceCompanyIds],
    )


def getSource(userModel) -> int:
    sourceCompanyId = resolveScope(userModel)
    if sourceCompanyId is None:
        raise RollupError(403, "COMPANY_SCOPE_REQUIRED", "Company scope is required.")
    return int(sourceCompanyId)


def getRequestYears(requests: list[dict]) -> list[int]:
    return sorted({int(request["reportingYear"]) for request in requests})


def getMissingAtomicIdsForYear(companyId: int, reportingYear: int, facts: list[dict]) -> list[str]:
    filteredFacts = [
        fact
        for fact in facts
        if int(fact["companyId"]) == int(companyId)
        and int(fact.get("reportingYear") or reportingYear) == int(reportingYear)
    ]
    return getMissingAtomicIds(companyId, filteredFacts)


def formatDateTime(value) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def getActorUserId(userModel) -> Optional[int]:
    if isinstance(userModel, dict):
        userId = userModel.get("id")
    else:
        userId = getattr(userModel, "id", None)
    try:
        return int(userId) if userId is not None else None
    except (TypeError, ValueError):
        return None


def loadRepository():
    from src.utils import rolluprepository

    return rolluprepository


def loadCalculator():
    from src.utils import rollupcalculator

    return rollupcalculator


SOURCE_STATUS_RECEIVED = "received"
SOURCE_STATUS_REQUESTED = "requested"
SOURCE_STATUS_SENT = "sent"
INPUT_STATUS_APPROVED = "approved"
INPUT_STATUS_SUBMITTED = "submitted"
INPUT_STATUS_NOT_STARTED = "not_started"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_SUBMITTED = "submitted"
APPROVAL_STATUS_PENDING = "pending"
TRANSFER_STATUS_RECEIVED = "received"
TRANSFER_STATUS_SENT = "sent"
TRANSFER_STATUS_NOT_SENT = "not_sent"


__all__ = [
    "listSubsidiaries",
    "saveBatch",
    "calcBatch",
    "listRequests",
    "sendSource",
    "getStatus",
    "RollupError",
]
