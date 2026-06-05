from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import json

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
    def __init__(self, statusCode: int, code: str, message: str, data: Optional[dict] = None):
        super().__init__(message)
        self.statusCode = statusCode
        self.code = code
        self.message = message
        self.data = data or {}

def validatePurposeScope(
    rollupPurposeCode,
    metricScopeCode,
    runId,
    sourceCycleId,
    requireContext: bool = True,
) -> tuple[str, str]:
    rollupRepository = loadRepository()
    purposeCode = str(rollupPurposeCode or "").strip().upper()
    scopeCode = str(metricScopeCode or "").strip().upper()

    if (
        purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK
        and scopeCode == rollupRepository.METRIC_SCOPE_G0_02_FINANCIAL_BASIS
    ):
        if requireContext and not runId:
            raise RollupError(400, "RUN_ID_REQUIRED", "runId is required for DMA_PRECHECK")
        return purposeCode, scopeCode

    if (
        purposeCode == rollupRepository.ROLLUP_PURPOSE_REPORT_DISCLOSURE
        and scopeCode == rollupRepository.METRIC_SCOPE_SELECTED_DISCLOSURE
    ):
        if requireContext and not sourceCycleId:
            raise RollupError(400, "SOURCE_CYCLE_ID_REQUIRED", "sourceCycleId is required for REPORT_DISCLOSURE")
        return purposeCode, scopeCode

    raise RollupError(
        422,
        "ROLLUP_PURPOSE_SCOPE_UNSUPPORTED",
        "Unsupported rollup purpose and metric scope combination.",
        {"rollupPurposeCode": rollupPurposeCode, "metricScopeCode": metricScopeCode},
    )

def validateSourceCycle(rollupRepository, sourceCycleId: int) -> dict:
    conn = rollupRepository.getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT id, company_id, reporting_year, cycle_type, delete_yn
                FROM ESG_ONBOARDING_CYCLE
                WHERE id = ?
                  AND delete_yn = 0
                  AND cycle_type = 'POST_DMA_DISCLOSURE'
                """,
                (sourceCycleId,),
            )
            cycle = cur.fetchone()
            if not cycle:
                raise RollupError(422, "POST_DMA_SOURCE_CYCLE_INVALID", "Invalid source cycle")
            cur.execute(
                """
                SELECT COUNT(*) AS scope_count
                FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
                WHERE esg_onboarding_cycle_id = ?
                  AND active_yn = 1
                  AND delete_yn = 0
                """,
                (sourceCycleId,),
            )
            scopeRow = cur.fetchone() or {}
            if int(scopeRow.get("scope_count") or 0) < 1:
                raise RollupError(422, "POST_DMA_SOURCE_CYCLE_INVALID", "Invalid source cycle")
            return cycle
    finally:
        conn.close()

def resolveBatchContext(rollupRepository, purposeCode: str, runId: Optional[int], sourceCycleId: Optional[int]) -> dict:
    if purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK:
        run = getRunOrRaise(int(runId))
        checkConsolidatedRun(run)
        return {
            "parentCompanyId": int(run["company_id"]),
            "reportingYear": int(run["reporting_year"]),
            "run": run,
            "cycle": None,
        }

    cycle = validateSourceCycle(rollupRepository, int(sourceCycleId))
    return {
        "parentCompanyId": int(cycle["company_id"]),
        "reportingYear": int(cycle["reporting_year"]),
        "run": None,
        "cycle": cycle,
    }

def listSubsidiaries(runId, sourceCycleId, rollupPurposeCode, metricScopeCode, userModel) -> RollupSubsidiaryResponseDto:
    rollupRepository = loadRepository()
    purposeCode, scopeCode = validatePurposeScope(rollupPurposeCode, metricScopeCode, runId, sourceCycleId)
    context = resolveBatchContext(rollupRepository, purposeCode, runId, sourceCycleId)
    parentCompanyId = context["parentCompanyId"]
    reportingYear = context["reportingYear"]

    checkScope(parentCompanyId, userModel)

    items = rollupRepository.listEffectiveSourceCompanies(parentCompanyId, reportingYear, purposeCode)

    # UI presentation: Do not include parent in the subsidiary selection list
    items = [item for item in items if int(item["companyId"]) != parentCompanyId]

    resItems = [
        RollupSubsidiaryDto(
            companyId=item["companyId"],
            companyCode=item.get("companyCode"),
            companyName=item.get("companyName"),
        )
        for item in items
    ]

    return RollupSubsidiaryResponseDto(data=RollupSubsidiaryListDto(runId=runId, sourceCycleId=sourceCycleId, items=resItems))

def saveBatch(request: RollupBatchRequestDto, userModel) -> RollupBatchResponseDto:
    rollupRepository = loadRepository()
    purposeCode, metricScopeCode = validatePurposeScope(
        request.rollupPurposeCode,
        request.metricScopeCode,
        request.runId,
        request.sourceCycleId,
    )
    actorUserId = getActorUserId(userModel)
    context = resolveBatchContext(rollupRepository, purposeCode, request.runId, request.sourceCycleId)
    parentCompanyId = context["parentCompanyId"]
    reportingYear = context["reportingYear"]

    checkScope(parentCompanyId, userModel)

    selectedCompanyIds = normalizeCompanyIds(request.sourceCompanyIds)
    if not selectedCompanyIds:
        raise RollupError(422, "ROLLUP_SOURCE_REQUIRED", "At least one subsidiary source is required.")

    relations = rollupRepository.listEffectiveSourceCompanies(parentCompanyId, reportingYear, purposeCode)
    relation_ids = {r["companyId"] for r in relations}

    if parentCompanyId in selectedCompanyIds:
        raise RollupError(422, "ROLLUP_PARENT_SOURCE_NOT_ALLOWED", "Parent company is included automatically.")

    if purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK:
        if not set(selectedCompanyIds).issubset(relation_ids):
            raise RollupError(403, "ROLLUP_SOURCE_SCOPE_FORBIDDEN", "Requested subsidiary is outside of allowed relation scope.")
        includedCompanyIds = normalizeCompanyIds([parentCompanyId, *selectedCompanyIds])
    else:
        if parentCompanyId not in relation_ids:
            raise RollupError(422, "ROLLUP_PARENT_SCOPE_MISSING", "Parent company relation scope is missing.")
        if not set(selectedCompanyIds).issubset(relation_ids):
            raise RollupError(403, "ROLLUP_SOURCE_SCOPE_FORBIDDEN", "Requested subsidiary is outside of allowed relation scope.")
        includedCompanyIds = normalizeCompanyIds([parentCompanyId, *selectedCompanyIds])

    existingBatch = rollupRepository.getActiveBatch(request.runId, request.sourceCycleId, purposeCode, metricScopeCode)
    if existingBatch:
        return RollupBatchResponseDto(data=buildBatchStatus(existingBatch, rollupRepository.listSourceCompanyIds(int(existingBatch["id"]))))

    conn = rollupRepository.getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            # Determine metric scope
            if purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK:
                metricIds = ["G0-02"]
            else:
                from src.utils.onboardingscoperepository import listMetricScopesTx
                scopeRows = listMetricScopesTx(cur, request.sourceCycleId, parentCompanyId)
                metricIds = [r["metric_id"] for r in scopeRows if r.get("approval_policy_code") == "PROMOTE_TO_KPI_FACT_AND_ROLLUP"]
                if not metricIds:
                    raise RollupError(422, "ROLLUP_RULE_NOT_FOUND", "No valid consolidated metrics found in cycle scope.")

            rules, sources = rollupRepository.resolveConsolidatedRuleClosure(metricIds)
            ruleMetricIds = {r["metric_id"] for r in rules}
            missingMetricIds = [m for m in metricIds if m not in ruleMetricIds]
            if missingMetricIds:
                raise RollupError(422, "ROLLUP_RULE_NOT_FOUND", f"Missing rules for metrics: {missingMetricIds}")

            # Create Batch
            batchId = rollupRepository.saveBatchTx(
                cur=cur,
                parentCompanyId=parentCompanyId,
                reportingYear=reportingYear,
                includedCompanyIds=includedCompanyIds,
                rollupPurposeCode=purposeCode,
                metricScopeCode=metricScopeCode,
                sourceCycleId=request.sourceCycleId,
                actorUserId=actorUserId,
            )

            rollupRepository.saveScopeFromRulesTx(cur, batchId, rules, sources, purposeCode)

            # Determine readiness from Tx
            requiredAtomicIds = rollupRepository.resolveExternalEntitySourceAtomicIdsTx(cur, batchId)
            requiredAtomicCount = len(requiredAtomicIds)

            sourceStatuses = []
            for sourceCompanyId in includedCompanyIds:
                # Pre-calculate missing count for status insertion
                facts = rollupRepository.listApprovedFactsByCompany([sourceCompanyId], reportingYear, requiredAtomicIds)
                approvedKeys = {f["atomicMetricId"] for f in facts}
                missingAtomicIds = [a for a in requiredAtomicIds if a not in approvedKeys]

                approvedCount = requiredAtomicCount - len(missingAtomicIds)
                readyYn = approvedCount == requiredAtomicCount
                parentYn = sourceCompanyId == parentCompanyId

                currentTime = datetime.now(timezone.utc).replace(tzinfo=None)
                sourceStatuses.append({
                    "parentCompanyId": parentCompanyId,
                    "sourceCompanyId": sourceCompanyId,
                    "reportingYear": reportingYear,
                    "approvedCount": approvedCount,
                    "missingAtomicMetricIds": missingAtomicIds,
                    "requestStatus": rollupRepository.SOURCE_STATUS_RECEIVED if parentYn else rollupRepository.SOURCE_STATUS_REQUESTED,
                    "inputStatus": rollupRepository.INPUT_STATUS_APPROVED if readyYn else (rollupRepository.INPUT_STATUS_SUBMITTED if approvedCount > 0 else rollupRepository.INPUT_STATUS_NOT_STARTED),
                    "approvalStatus": rollupRepository.APPROVAL_STATUS_APPROVED if readyYn else (rollupRepository.APPROVAL_STATUS_SUBMITTED if approvedCount > 0 else rollupRepository.APPROVAL_STATUS_PENDING),
                    "transferStatus": rollupRepository.TRANSFER_STATUS_RECEIVED if parentYn else rollupRepository.TRANSFER_STATUS_NOT_SENT,
                    "sentAt": currentTime if parentYn else None,
                    "receivedAt": currentTime if parentYn else None,
                    "approvedAt": currentTime if readyYn else None,
                })

            rollupRepository.saveSourcesTx(cur, batchId, sourceStatuses, purposeCode, metricScopeCode, requiredAtomicCount)

            if purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK:
                cur.execute(
                    """
                    UPDATE ESG_MATERIALITY_RUN
                    SET required_rollup_batch_id = ?,
                        financial_basis_status = 'CONSOLIDATED_ROLLUP_PENDING',
                        financial_basis_checked_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND delete_yn = 0
                    """,
                    (batchId, request.runId),
                )

        conn.commit()
    except RollupError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise RollupError(500, "ROLLUP_BATCH_CREATE_FAILED", f"Failed to create rollup batch: {str(e)}")
    finally:
        conn.close()

    batch = rollupRepository.getBatch(batchId)
    return RollupBatchResponseDto(data=buildBatchStatus(batch, includedCompanyIds))

def calcBatch(batchId: int, userModel) -> RollupCalculateResponseDto:
    rollupRepository = loadRepository()
    rollupCalculator = loadCalculator()

    batch = rollupRepository.getBatch(batchId)
    if not batch:
        raise RollupError(404, "ROLLUP_BATCH_NOT_FOUND", "Rollup batch was not found.")
    checkScope(int(batch["parent_company_id"]), userModel)
    checkBatchActive(batch)

    sources = rollupRepository.listSources(batchId)
    if not sources:
        raise RollupError(409, "ROLLUP_SOURCE_NOT_FOUND", "Rollup source snapshot was not found.")

    transferStatus = checkTransferReady(batch, sources)
    if not transferStatus["readyYn"]:
        raise RollupError(
            409,
            "ROLLUP_SOURCE_NOT_SENT",
            "One or more subsidiary data transfers are not complete.",
            {"notSentCompanyIds": transferStatus["notSentCompanyIds"]},
        )

    includedCompanyIds = json.loads(batch.get("included_company_ids_json") or "[]")
    reportingYear = int(batch["reporting_year"])
    purposeCode = batch["rollup_purpose_code"]
    parentCompanyId = int(batch["parent_company_id"])

    conn = rollupRepository.getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            scopes = rollupRepository.listScope(batchId)
            metricIds = list(set([s["metric_id"] for s in scopes]))
            rules, ruleSources = rollupRepository.resolveConsolidatedRuleClosure(metricIds)
            requiredAtomicIds = rollupRepository.resolveExternalEntitySourceAtomicIdsTx(cur, batchId)

            historicalDepth = rollupCalculator.resolveHistoricalLookbackDepth(rules, ruleSources)
            entityFactMapsByYear = {}
            for factYear in range(reportingYear, reportingYear - historicalDepth - 1, -1):
                facts = rollupRepository.listApprovedFactsByCompany(includedCompanyIds, factYear, requiredAtomicIds)
                entityFactMapsByYear[factYear] = rollupCalculator.buildMultiCompanyFactMap(
                    includedCompanyIds,
                    requiredAtomicIds,
                    facts,
                )

            cur.execute("SELECT id FROM ESG_MATERIALITY_RUN WHERE required_rollup_batch_id = ?", (batchId,))
            r = cur.fetchone()
            runId = r["id"] if r else None
            if purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK and not runId:
                raise RollupError(409, "REPORT_RUN_NOT_FOUND", "Report workflow run was not found for rollup batch.")

            results, warnings, allSuccess = rollupCalculator.calculateConsolidatedRulesByYear(
                rules=rules,
                sources=ruleSources,
                entityFactMapsByYear=entityFactMapsByYear,
                reportingYear=reportingYear,
                companyIds=includedCompanyIds,
            )

            if not allSuccess:
                raise RollupError(422, "ROLLUP_CALCULATION_NOT_READY", "Calculation failed due to unready sources or calculation errors.", {"warnings": warnings})

            if purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK:
                for res in results:
                    res["groupMetricId"] = res.get("groupMetricId") or "G0-02"
            else:
                for res in results:
                    if not res.get("groupMetricId"):
                        raise RollupError(500, "ROLLUP_RESULT_ERROR", "Group Metric ID is required for generic rollup.")

            actorUserId = getActorUserId(userModel)
            rollupRepository.upsertGroupRollupResultsTx(cur, batch, results, includedCompanyIds, actorUserId)

            rollupRepository.updateSourceStatusTx(cur, batchId, len(requiredAtomicIds))

            if purposeCode == rollupRepository.ROLLUP_PURPOSE_DMA_PRECHECK:
                rollupRepository.finalizeDmaPrecheckTx(cur, batchId, runId, actorUserId)
            else:
                rollupRepository.finalizeReportDisclosureTx(cur, batchId, actorUserId)
                from src.utils.onboardingscoperepository import ensureRollupCycleTx, seedRollupMetricScopeTx
                ensureRollupCycleTx(cur, parentCompanyId, reportingYear, batchId)
                seedRollupMetricScopeTx(cur, parentCompanyId, reportingYear, actorUserId)

            conn.commit()
    except RollupError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise RollupError(500, "ROLLUP_CALCULATE_FAILED", f"Failed to save calculated rollup batch: {e}")
    finally:
        conn.close()

    refreshedBatch = rollupRepository.getBatch(batchId)
    status = buildBatchStatus(refreshedBatch, includedCompanyIds)
    return RollupCalculateResponseDto(
        data=RollupCalculateStatusDto(
            **dumpModel(status),
            results=[
                RollupResultDto(
                    groupAtomicMetricId=result["groupAtomicMetricId"],
                    sourceAtomicMetricIds=result.get("sourceAtomicMetricIds") or [],
                    sourceAtomicMetricId=result.get("sourceAtomicMetricId"),
                    formulaType=result.get("formulaType") or "",
                    valueNumeric=result.get("valueNumeric"),
                    valueText=result.get("valueText"),
                    unit=result.get("unit"),
                    sourceCompanyValues=result.get("sourceCompanyValues"),
                    calculationWarnings=result.get("calculationWarnings"),
                )
                for result in results
            ],
        )
    )

def listRequests(rollupPurposeCode: str, metricScopeCode: str, userModel) -> RollupRequestResponseDto:
    rollupRepository = loadRepository()
    purposeCode, scopeCode = validatePurposeScope(
        rollupPurposeCode,
        metricScopeCode,
        runId=None,
        sourceCycleId=None,
        requireContext=False,
    )
    sourceCompanyId = getSource(userModel)
    requests = rollupRepository.listRequests(sourceCompanyId, purposeCode, scopeCode)

    items = []
    for req in requests:
        batchId = req["batchId"]
        readiness = rollupRepository.buildSourceReadiness(batchId, [sourceCompanyId], int(req["reportingYear"]))
        items.append(RollupRequestItemDto(
            batchId=batchId,
            batchCode=req.get("batchCode"),
            parentCompanyId=req["parentCompanyId"],
            parentCompanyCode=req.get("parentCompanyCode"),
            parentCompanyName=req.get("parentCompanyName"),
            reportingYear=req["reportingYear"],
            rollupPurposeCode=req.get("rollupPurposeCode") or purposeCode,
            metricScopeCode=req.get("metricScopeCode") or scopeCode,
            requestStatus=req.get("requestStatus") or "",
            inputStatus=req.get("inputStatus") or "",
            approvalStatus=req.get("approvalStatus") or "",
            transferStatus=req.get("transferStatus") or "",
            sendReadyYn=bool(readiness["readyYn"]),
            missingAtomicMetricIds=readiness["missingByCompany"].get(str(sourceCompanyId), [])
        ))

    return RollupRequestResponseDto(data=RollupRequestListDto(items=items))

def sendSource(batchId: int, userModel) -> RollupSourceSendResponseDto:
    rollupRepository = loadRepository()
    sourceCompanyId = getSource(userModel)
    batch = rollupRepository.getBatch(batchId)
    if not batch:
        raise RollupError(404, "ROLLUP_BATCH_NOT_FOUND", "Rollup batch was not found.")
    checkBatchActive(batch)

    source = rollupRepository.getSource(batchId, sourceCompanyId)
    if not source:
        raise RollupError(404, "ROLLUP_SOURCE_REQUEST_NOT_FOUND", "Rollup source transfer request was not found.")
    if int(source["source_company_id"]) == int(source["parent_company_id"]):
        raise RollupError(409, "ROLLUP_PARENT_SEND_NOT_ALLOWED", "Parent company data is included automatically.")

    if str(source.get("transfer_status") or "").lower() in {"sent", "received"}:
        return RollupSourceSendResponseDto(data=buildSourceSendStatus(source))

    # Determine readiness
    requiredAtomicIds = rollupRepository.resolveExternalEntitySourceAtomicIds(batchId)
    readiness = rollupRepository.buildSourceReadiness(batchId, [sourceCompanyId], int(source["reporting_year"]))

    if not readiness["readyYn"]:
        raise RollupError(
            409,
            "SOURCE_NOT_READY",
            "Approved KPI facts are required before transfer.",
            {"missingAtomicMetricIds": readiness["missingAtomicMetricIds"]},
        )

    conn = rollupRepository.getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            rollupRepository.updateSourceSentTx(cur, batchId, sourceCompanyId, len(requiredAtomicIds))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise RollupError(500, "ROLLUP_SOURCE_SEND_FAILED", "Failed to update rollup source transfer status.")
    finally:
        conn.close()

    source = rollupRepository.getSource(batchId, sourceCompanyId)
    return RollupSourceSendResponseDto(data=buildSourceSendStatus(source))

def getStatus(batchId: int, userModel) -> RollupBatchSummaryResponseDto:
    rollupRepository = loadRepository()
    batch = rollupRepository.getBatch(batchId)
    if not batch:
        raise RollupError(404, "ROLLUP_BATCH_NOT_FOUND", "Rollup batch was not found.")
    checkScope(int(batch["parent_company_id"]), userModel)
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

def checkBatchActive(batch: dict) -> None:
    batchStatus = str(batch.get("batch_status") or "").lower()
    if batchStatus in {"deleted", "cancelled", "canceled", "archived", "completed"}:
        raise RollupError(409, "ROLLUP_BATCH_NOT_ACTIVE", "Rollup batch is not active.")

def checkTransferReady(batch: dict, sources: list[dict]) -> dict:
    rollupRepository = loadRepository()
    parentCompanyId = int(batch["parent_company_id"])
    parentReadyYn = any(
        int(source["source_company_id"]) == parentCompanyId
        and str(source.get("transfer_status") or "").lower() == rollupRepository.TRANSFER_STATUS_RECEIVED
        for source in sources
    )
    notSentCompanyIds = [
        int(source["source_company_id"])
        for source in sources
        if int(source["source_company_id"]) != parentCompanyId
        and str(source.get("transfer_status") or "").lower() not in {
            rollupRepository.TRANSFER_STATUS_SENT,
            rollupRepository.TRANSFER_STATUS_RECEIVED,
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

def getSource(userModel) -> int:
    sourceCompanyId = resolveScope(userModel)
    if sourceCompanyId is None:
        raise RollupError(403, "COMPANY_SCOPE_REQUIRED", "Company scope is required.")
    return int(sourceCompanyId)

def formatDateTime(value) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

def dumpModel(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()

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

__all__ = [
    "listSubsidiaries",
    "saveBatch",
    "calcBatch",
    "listRequests",
    "sendSource",
    "getStatus",
    "RollupError",
]
