from __future__ import annotations

from typing import Optional

from src.utils.db import getConn
from src.utils import onboardingapprovalrepository as approvalRepo
from src.utils import onboardinginputrepository as inputRepo
from src.utils import onboardingscoperepository as scopeRepo
from src.services.calculations.service import calculateAffectedEntityFactsTx


STATE_DRAFT = "draft"
STATE_SUBMITTED = "submitted"
STATE_REVIEWED = "reviewed"
STATE_APPROVED = "approved"
STATE_REJECTED = "rejected"

APPROVAL_POLICY_INPUT_APPROVAL_ONLY = scopeRepo.APPROVAL_POLICY_INPUT_APPROVAL_ONLY
APPROVAL_POLICY_PROMOTE_TO_KPI_FACT = scopeRepo.APPROVAL_POLICY_PROMOTE_TO_KPI_FACT
APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP = scopeRepo.APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP
APPROVAL_POLICY_ROLLUP_READONLY = scopeRepo.APPROVAL_POLICY_ROLLUP_READONLY
APPROVAL_POLICY_NO_APPROVAL_REQUIRED = scopeRepo.APPROVAL_POLICY_NO_APPROVAL_REQUIRED

def resolveRequiredApprovalAtomicIdsTx(
    cur,
    cycleType: str,
    batchId: Optional[int],
    metricId: str,
) -> list[str]:
    if str(cycleType or "").strip().upper() == scopeRepo.CYCLE_TYPE_ROLLUP_RESPONSE:
        if batchId is None:
            raise ValueError("batchId is required for ROLLUP_RESPONSE")

        from src.utils import rolluprepository as rollupRepo

        atomicIds = rollupRepo.resolveExternalEntitySourceAtomicIdsByMetricTx(
            cur,
            int(batchId),
            metricId,
        )
        if not atomicIds:
            raise ValueError(
                f"ROLLUP_RESPONSE_MISSING_SOURCE_ATOMIC_IDS: batchId={batchId}, metricId={metricId}"
            )
        return atomicIds

    return inputRepo.listRequiredApprovalAtomicIdsTx(cur, metricId)

def submitMetricApproval(
    *,
    companyId: int,
    reportingYear: int,
    cycleType: str,
    metricId: str,
    actorUserId: Optional[int],
    commentText: Optional[str] = None,
    reportBasisType: Optional[str] = None,
    sourceMaterialityRunId: Optional[int] = None,
    batchId: Optional[int] = None,
) -> dict:
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        with conn.cursor(dictionary=True) as cur:
            cycle = resolveActiveCycleTx(
                cur,
                companyId=companyId,
                reportingYear=reportingYear,
                cycleType=cycleType,
                reportBasisType=reportBasisType,
                sourceMaterialityRunId=sourceMaterialityRunId,
                actorUserId=actorUserId,
                batchId=batchId,
            )
            requireWritableCycleTx(cur, cycle, companyId, batchId=batchId)
            scope = requireApprovalScopeTx(cur, cycle, companyId, metricId)
            requiredAtomicIds = resolveRequiredApprovalAtomicIdsTx(cur, cycleType, batchId, metricId)
            assignment = inputRepo.resolveAssignment(cur, int(cycle["id"]), companyId, metricId)
            rows = inputRepo.selectInputRowsForUpdate(cur, companyId, reportingYear, metricId, requiredAtomicIds)
            if checkRowsAllStatus(rows, requiredAtomicIds, STATE_SUBMITTED):
                conn.commit()
                return buildMetricApprovalSummary(
                    companyId,
                    reportingYear,
                    metricId,
                    cycle.get("cycle_type") or cycleType,
                    batchId=batchId,
                )
            if checkRowsAnyStatus(rows, requiredAtomicIds, {STATE_REVIEWED, STATE_APPROVED}):
                raise ValueError(f"Cannot resubmit {metricId} from reviewed or approved status")
            inputRepo.validateCompleteRows(rows, requiredAtomicIds, allowedStatuses={STATE_DRAFT, STATE_REJECTED, STATE_SUBMITTED})
            setMetricInputStatusTx(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=int(assignment["id"]) if assignment else None,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=metricId,
                requiredAtomicIds=requiredAtomicIds,
                status=STATE_SUBMITTED,
                actorUserId=None,
            )
            approvalRepo.insertHistory(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=int(assignment["id"]) if assignment else None,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=metricId,
                actionType="submit",
                actionStatus=STATE_SUBMITTED,
                actorUserId=actorUserId,
                assigneeUserId=assignment.get("assignee_user_id") if assignment else None,
                commentText=commentText,
            )
        conn.commit()
        return buildMetricApprovalSummary(
            companyId,
            reportingYear,
            metricId,
            cycle.get("cycle_type") or cycleType,
            batchId=batchId,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reviewMetricApproval(
    *,
    companyId: int,
    reportingYear: int,
    cycleType: str,
    metricId: str,
    actorUserId: Optional[int],
    commentText: Optional[str] = None,
    batchId: Optional[int] = None,
) -> dict:
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        with conn.cursor(dictionary=True) as cur:
            cycle = resolveExistingActiveCycleTx(cur, companyId, reportingYear, cycleType, batchId=batchId)
            requireWritableCycleTx(cur, cycle, companyId, batchId=batchId)
            requireApprovalScopeTx(cur, cycle, companyId, metricId)
            requiredAtomicIds = resolveRequiredApprovalAtomicIdsTx(cur, cycleType, batchId, metricId)
            assignment = inputRepo.resolveAssignment(cur, int(cycle["id"]), companyId, metricId)
            rows = inputRepo.selectInputRowsForUpdate(cur, companyId, reportingYear, metricId, requiredAtomicIds)
            inputRepo.validateCompleteRows(rows, requiredAtomicIds, allowedStatuses={STATE_SUBMITTED})
            setMetricInputStatusTx(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=int(assignment["id"]) if assignment else None,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=metricId,
                requiredAtomicIds=requiredAtomicIds,
                status=STATE_REVIEWED,
                actorUserId=None,
            )
            approvalRepo.insertHistory(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=int(assignment["id"]) if assignment else None,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=metricId,
                actionType="review",
                actionStatus=STATE_REVIEWED,
                actorUserId=actorUserId,
                assigneeUserId=assignment.get("assignee_user_id") if assignment else None,
                commentText=commentText,
            )
        conn.commit()
        return buildMetricApprovalSummary(
            companyId,
            reportingYear,
            metricId,
            cycle.get("cycle_type") or cycleType,
            batchId=batchId,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def approveMetricApproval(
    *,
    companyId: int,
    reportingYear: int,
    cycleType: str,
    metricId: str,
    actorUserId: Optional[int],
    commentText: Optional[str] = None,
    batchId: Optional[int] = None,
) -> dict:
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        with conn.cursor(dictionary=True) as cur:
            cycle = resolveExistingActiveCycleTx(cur, companyId, reportingYear, cycleType, batchId=batchId)
            requireWritableCycleTx(cur, cycle, companyId, batchId=batchId)
            scope = requireApprovalScopeTx(cur, cycle, companyId, metricId)
            requiredAtomicIds = resolveRequiredApprovalAtomicIdsTx(cur, cycleType, batchId, metricId)
            assignment = inputRepo.resolveAssignment(cur, int(cycle["id"]), companyId, metricId)
            rows = inputRepo.selectInputRowsForUpdate(cur, companyId, reportingYear, metricId, requiredAtomicIds)
            policy = str(scope.get("approval_policy_code") or APPROVAL_POLICY_INPUT_APPROVAL_ONLY).strip().upper()
            promotedAtomicIds = []
            actualCycleType = str(cycle.get("cycle_type") or cycleType).strip().upper()
            if policy in {
                APPROVAL_POLICY_PROMOTE_TO_KPI_FACT,
                APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP,
            }:
                if actualCycleType == scopeRepo.CYCLE_TYPE_ROLLUP_RESPONSE:
                    promotedAtomicIds = list(requiredAtomicIds)
                else:
                    promotedAtomicIds = inputRepo.listPromotableInputAtomicIdsTx(cur, metricId)
            requireKpiFactYn = bool(promotedAtomicIds)
            if policy in {
                APPROVAL_POLICY_PROMOTE_TO_KPI_FACT,
                APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP,
            } and not promotedAtomicIds:
                raise ValueError(f"No INPUT atomic metrics are available for KPI promotion: {metricId}")
            if inputRepo.checkAlreadyApprovedTx(
                cur,
                rows,
                companyId,
                reportingYear,
                metricId,
                requiredAtomicIds,
                expectedPromotedAtomicIds=promotedAtomicIds,
            ):
                syncRollupSourceReadinessIfNeededTx(
                    cur,
                    cycle=cycle,
                    companyId=companyId,
                    reportingYear=reportingYear,
                    batchId=batchId,
                )
                conn.commit()
                return buildMetricApprovalSummary(
                    companyId,
                    reportingYear,
                    metricId,
                    cycle.get("cycle_type") or cycleType,
                    batchId=batchId,
                )
            if checkRowsAllStatus(rows, requiredAtomicIds, STATE_APPROVED):
                calculationSummary = None
                if requireKpiFactYn:
                    quantAtomicIds = set(promotedAtomicIds)
                    changedAtomicIds = []
                    for row in rows:
                        if row.get("atomic_metric_id") in quantAtomicIds:
                            inputRepo.upsertKpiFact(cur, row, actorUserId)
                            changedAtomicIds.append(row.get("atomic_metric_id"))
                    if changedAtomicIds:
                        calculationSummary = calculateAffectedEntityFactsTx(
                            cur,
                            companyId=companyId,
                            reportingYear=reportingYear,
                            changedAtomicMetricIds=changedAtomicIds,
                            actorUserId=actorUserId,
                        )
                syncRollupSourceReadinessIfNeededTx(
                    cur,
                    cycle=cycle,
                    companyId=companyId,
                    reportingYear=reportingYear,
                    batchId=batchId,
                )
                conn.commit()
                return buildMetricApprovalSummary(
                    companyId,
                    reportingYear,
                    metricId,
                    cycle.get("cycle_type") or cycleType,
                    calculationSummary=calculationSummary,
                    batchId=batchId,
                )
            inputRepo.validateCompleteRows(rows, requiredAtomicIds, allowedStatuses={STATE_SUBMITTED, STATE_REVIEWED})
            calculationSummary = None
            if requireKpiFactYn:
                quantAtomicIds = set(promotedAtomicIds)
                changedAtomicIds = []
                for row in rows:
                    if row.get("atomic_metric_id") in quantAtomicIds:
                        inputRepo.upsertKpiFact(cur, row, actorUserId)
                        changedAtomicIds.append(row.get("atomic_metric_id"))
                calculationSummary = calculateAffectedEntityFactsTx(
                    cur,
                    companyId=companyId,
                    reportingYear=reportingYear,
                    changedAtomicMetricIds=changedAtomicIds,
                    actorUserId=actorUserId,
                )
            setMetricInputStatusTx(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=int(assignment["id"]) if assignment else None,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=metricId,
                requiredAtomicIds=requiredAtomicIds,
                status=STATE_APPROVED,
                actorUserId=actorUserId,
            )
            approvalRepo.insertHistory(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=int(assignment["id"]) if assignment else None,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=metricId,
                actionType="approve",
                actionStatus=STATE_APPROVED,
                actorUserId=actorUserId,
                assigneeUserId=assignment.get("assignee_user_id") if assignment else None,
                commentText=commentText,
            )
            syncRollupSourceReadinessIfNeededTx(
                cur,
                cycle=cycle,
                companyId=companyId,
                reportingYear=reportingYear,
                batchId=batchId,
            )
        conn.commit()
        return buildMetricApprovalSummary(
            companyId, reportingYear, metricId,
            cycle.get("cycle_type") or cycleType,
            calculationSummary=calculationSummary,
            batchId=batchId,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rejectMetricApproval(
    *,
    companyId: int,
    reportingYear: int,
    cycleType: str,
    metricId: str,
    actorUserId: Optional[int],
    commentText: str,
    batchId: Optional[int] = None,
) -> dict:
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        with conn.cursor(dictionary=True) as cur:
            cycle = resolveExistingActiveCycleTx(cur, companyId, reportingYear, cycleType, batchId=batchId)
            requireWritableCycleTx(cur, cycle, companyId, batchId=batchId)
            requireApprovalScopeTx(cur, cycle, companyId, metricId)
            requiredAtomicIds = resolveRequiredApprovalAtomicIdsTx(cur, cycleType, batchId, metricId)
            assignment = inputRepo.resolveAssignment(cur, int(cycle["id"]), companyId, metricId)
            rows = inputRepo.selectInputRowsForUpdate(cur, companyId, reportingYear, metricId, requiredAtomicIds)
            inputRepo.validateCompleteRows(rows, requiredAtomicIds, allowedStatuses={STATE_SUBMITTED, STATE_REVIEWED})
            setMetricInputStatusTx(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=int(assignment["id"]) if assignment else None,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=metricId,
                requiredAtomicIds=requiredAtomicIds,
                status=STATE_REJECTED,
                actorUserId=None,
            )
            approvalRepo.insertHistory(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=int(assignment["id"]) if assignment else None,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=metricId,
                actionType="reject",
                actionStatus=STATE_REJECTED,
                actorUserId=actorUserId,
                assigneeUserId=assignment.get("assignee_user_id") if assignment else None,
                commentText=commentText,
            )
        conn.commit()
        return buildMetricApprovalSummary(
            companyId,
            reportingYear,
            metricId,
            cycle.get("cycle_type") or cycleType,
            batchId=batchId,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def buildMetricApprovalSummary(
    companyId: int,
    reportingYear: int,
    metricId: str,
    cycleType: str = scopeRepo.CYCLE_TYPE_PRE_DMA_G0,
    calculationSummary: dict = None,
    batchId: Optional[int] = None,
) -> dict:
    summary = approvalRepo.buildApprovalSummary(companyId, reportingYear, metricId, cycleType, batchId=batchId)
    if calculationSummary:
        summary["calculationReadyYn"] = calculationSummary.get("calculationReadyYn")
        summary["affectedRuleCount"] = calculationSummary.get("affectedRuleCount", 0)
        summary["invalidatedFactCount"] = calculationSummary.get("invalidatedFactCount", 0)
        summary["calculatedFactCount"] = calculationSummary.get("calculatedFactCount", 0)
        summary["calculationWarnings"] = calculationSummary.get("calculationWarnings", [])
    return summary


def resolveActiveCycleTx(
    cur,
    *,
    companyId: int,
    reportingYear: int,
    cycleType: str,
    reportBasisType: Optional[str],
    sourceMaterialityRunId: Optional[int],
    actorUserId: Optional[int],
    batchId: Optional[int] = None,
) -> dict:
    normalizedCycleType = normalizeCycleType(cycleType)
    if normalizedCycleType == scopeRepo.CYCLE_TYPE_PRE_DMA_G0:
        return scopeRepo.ensureCycleTx(
            cur,
            companyId,
            reportingYear,
            reportBasisType,
            sourceMaterialityRunId,
            actorUserId,
        )
    return resolveExistingActiveCycleTx(cur, companyId, reportingYear, normalizedCycleType, batchId=batchId)


def resolveExistingActiveCycleTx(cur, companyId: int, reportingYear: int, cycleType: str, batchId: Optional[int] = None) -> dict:
    normalizedCycleType = normalizeCycleType(cycleType)
    cycle = scopeRepo.resolveCycle(cur, companyId, reportingYear, normalizedCycleType, batchId=batchId)
    if not cycle:
        raise ValueError(f"{normalizedCycleType} cycle was not found")
    if str(cycle.get("cycle_status") or "").strip().lower() != "active":
        raise ValueError(f"{normalizedCycleType} cycle is not active")
    return cycle


def requireApprovalScopeTx(cur, cycle: dict, companyId: int, metricId: str) -> dict:
    scopes = scopeRepo.listMetricScopesTx(cur, int(cycle["id"]), companyId)
    scope = next((row for row in scopes if row.get("metric_id") == metricId), None)
    if not scope:
        raise ValueError(f"Unsupported metricId for cycle scope: {metricId}")
    if not inputRepo.truthy(scope.get("active_yn")):
        raise ValueError(f"Metric scope is not active: {metricId}")
    if inputRepo.truthy(scope.get("rollup_readonly_yn")):
        raise ValueError(f"ROLLUP_READONLY scope cannot be approved: {metricId}")
    policy = str(scope.get("approval_policy_code") or "").strip().upper()
    if policy == APPROVAL_POLICY_ROLLUP_READONLY:
        raise ValueError(f"ROLLUP_READONLY policy cannot be approved: {metricId}")
    if policy == APPROVAL_POLICY_NO_APPROVAL_REQUIRED or not inputRepo.truthy(scope.get("approval_required_yn")):
        raise ValueError(f"Approval is not required for metricId={metricId}")
    return scope


def setMetricInputStatusTx(
    cur,
    *,
    cycleId: int,
    assignmentId: Optional[int],
    companyId: int,
    reportingYear: int,
    metricId: str,
    requiredAtomicIds: list[str],
    status: str,
    actorUserId: Optional[int],
) -> None:
    if not requiredAtomicIds:
        return
    placeholders = ", ".join(["?"] * len(requiredAtomicIds))
    approvalColumns = ""
    params = [cycleId, assignmentId, status]
    if status == STATE_APPROVED:
        approvalColumns = ", approved_by_user_id = ?, approved_at = CURRENT_TIMESTAMP"
        params.append(actorUserId)
    elif status in {STATE_SUBMITTED, STATE_REVIEWED, STATE_REJECTED}:
        approvalColumns = ", approved_by_user_id = NULL, approved_at = NULL"
    params.extend([companyId, reportingYear, metricId, *requiredAtomicIds])
    cur.execute(
        f"""
        UPDATE ESG_ONBOARDING_INPUT_VALUE
        SET esg_onboarding_cycle_id = ?,
            esg_metric_assignment_id = ?,
            input_status = ?{approvalColumns},
            updated_at = CURRENT_TIMESTAMP
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id = ?
          AND atomic_metric_id IN ({placeholders})
          AND delete_yn = 0
        """,
        tuple(params),
    )


def requireWritableCycleTx(cur, cycle: dict, companyId: int, batchId: Optional[int] = None) -> None:
    scopeRepo.requireRollupResponseBatchContext(cycle, batchId)
    if str(cycle.get("cycle_type") or "").strip().upper() != scopeRepo.CYCLE_TYPE_ROLLUP_RESPONSE:
        return
    dbBatchId = cycle.get("parent_rollup_batch_id")
    if dbBatchId is None:
        return
    cur.execute(
        """
        SELECT transfer_status
        FROM ESG_ROLLUP_SOURCE_STATUS
        WHERE esg_rollup_batch_id = ?
          AND source_company_id = ?
          AND delete_yn = 0
        LIMIT 1
        FOR UPDATE
        """,
        (int(dbBatchId), companyId),
    )
    row = cur.fetchone()
    if row and str(row.get("transfer_status") or "").lower() in {"sent", "received"}:
        err = ValueError("ROLLUP_RESPONSE workspace is read-only after transfer.")
        err.statusCode = 409
        raise err

def syncRollupSourceReadinessIfNeededTx(
    cur,
    *,
    cycle: dict,
    companyId: int,
    reportingYear: int,
    batchId: Optional[int] = None,
) -> None:
    if (
        str(cycle.get("cycle_type") or "").strip().upper()
        != scopeRepo.CYCLE_TYPE_ROLLUP_RESPONSE
        or batchId is None
    ):
        return
    from src.utils import rolluprepository as rollupRepo

    rollupRepo.syncSourceReadinessTx(
        cur,
        batchId=int(batchId),
        sourceCompanyId=companyId,
        reportingYear=reportingYear,
    )

def normalizeCycleType(cycleType: str) -> str:
    normalizedCycleType = str(cycleType or scopeRepo.CYCLE_TYPE_PRE_DMA_G0).strip().upper()
    if normalizedCycleType not in {scopeRepo.CYCLE_TYPE_PRE_DMA_G0, scopeRepo.CYCLE_TYPE_POST_DMA_DISCLOSURE, scopeRepo.CYCLE_TYPE_ROLLUP_RESPONSE}:
        raise ValueError(f"Unsupported cycleType: {normalizedCycleType}")
    return normalizedCycleType


def checkRowsAllStatus(rows: list[dict], requiredAtomicIds: list[str], status: str) -> bool:
    if not requiredAtomicIds:
        return False
    rowByAtomic = {row.get("atomic_metric_id"): row for row in rows}
    return all(
        atomicId in rowByAtomic
        and inputRepo.hasMetricValue(rowByAtomic[atomicId])
        and str(rowByAtomic[atomicId].get("input_status") or "").strip().lower() == status
        for atomicId in requiredAtomicIds
    )


def checkRowsAnyStatus(rows: list[dict], requiredAtomicIds: list[str], statuses: set[str]) -> bool:
    rowByAtomic = {row.get("atomic_metric_id"): row for row in rows}
    return any(
        atomicId in rowByAtomic
        and str(rowByAtomic[atomicId].get("input_status") or "").strip().lower() in statuses
        for atomicId in requiredAtomicIds
    )
