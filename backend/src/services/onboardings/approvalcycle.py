"""
approvalcycle.py
레이어: Service (onboardings)
역할: 온보딩 결재 사이클 관리 — 사이클 생성·조회·상태 전환.
"""
from __future__ import annotations

from typing import Optional

from src.repositories import onboardingapprovalrepository as approvalRepo
from src.repositories import onboardinginputrepository as inputRepo
from src.repositories import onboardingscoperepository as scopeRepo


def resolveRequiredApprovalAtomicIdsTx(
    cur,
    cycleType: str,
    batchId: Optional[int],
    metricId: str,
) -> list[str]:
    if str(cycleType or "").strip().upper() == scopeRepo.CYCLE_TYPE_ROLLUP_RESPONSE:
        if batchId is None:
            raise ValueError("batchId is required for ROLLUP_RESPONSE")

        from src.repositories import rolluprepository as rollupRepo

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
    return resolveExistingActiveCycleTx(
        cur,
        companyId,
        reportingYear,
        normalizedCycleType,
        batchId=batchId,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )


def resolveExistingActiveCycleTx(
    cur,
    companyId: int,
    reportingYear: int,
    cycleType: str,
    batchId: Optional[int] = None,
    sourceMaterialityRunId: Optional[int] = None,
) -> dict:
    normalizedCycleType = normalizeCycleType(cycleType)
    effectiveRunId = sourceMaterialityRunId
    if effectiveRunId is None and normalizedCycleType == scopeRepo.CYCLE_TYPE_POST_DMA_DISCLOSURE:
        from src.repositories import reportworkflowrepository

        currentRun = reportworkflowrepository.getCurrent(companyId, reportingYear)
        effectiveRunId = int(currentRun["id"]) if currentRun.get("id") is not None else 0
    cycle = scopeRepo.resolveCycle(
        cur,
        companyId,
        reportingYear,
        normalizedCycleType,
        batchId=batchId,
        sourceMaterialityRunId=effectiveRunId,
    )
    if not cycle:
        raise ValueError(f"{normalizedCycleType} cycle was not found")
    if str(cycle.get("cycle_status") or "").strip().lower() != "active":
        raise ValueError(f"{normalizedCycleType} cycle is not active")
    return cycle


def requireApprovalScopeTx(cur, cycle: dict, companyId: int, metricId: str) -> dict:
    from src.repositories import onboardingscoperepository as scopeRepo
    from src.repositories import onboardinginputrepository as inputRepo

    APPROVAL_POLICY_ROLLUP_READONLY = scopeRepo.APPROVAL_POLICY_ROLLUP_READONLY
    APPROVAL_POLICY_NO_APPROVAL_REQUIRED = scopeRepo.APPROVAL_POLICY_NO_APPROVAL_REQUIRED

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
    STATE_APPROVED = "approved"
    STATE_SUBMITTED = "submitted"
    STATE_REVIEWED = "reviewed"
    STATE_REJECTED = "rejected"

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
    from src.repositories import rolluprepository as rollupRepo

    rollupRepo.syncSourceReadinessTx(
        cur,
        batchId=int(batchId),
        sourceCompanyId=companyId,
        reportingYear=reportingYear,
    )


def normalizeCycleType(cycleType: str) -> str:
    normalizedCycleType = str(cycleType or scopeRepo.CYCLE_TYPE_PRE_DMA_G0).strip().upper()
    if normalizedCycleType not in {
        scopeRepo.CYCLE_TYPE_PRE_DMA_G0,
        scopeRepo.CYCLE_TYPE_POST_DMA_DISCLOSURE,
        scopeRepo.CYCLE_TYPE_ROLLUP_RESPONSE,
    }:
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
