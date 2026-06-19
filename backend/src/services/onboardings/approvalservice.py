"""
approvalservice.py
레이어: Service (onboardings)
역할: 온보딩 결재 서비스 — 결재 현황 조회 및 결재 실행 API 처리.
"""
from __future__ import annotations

from typing import Optional

from src.utils.db import getConn
from src.repositories import onboardingapprovalrepository as approvalRepo
from src.repositories import onboardinginputrepository as inputRepo
from src.repositories import onboardingscoperepository as scopeRepo
from src.services.calculations.service import calculateAffectedEntityFactsTx
from src.services.onboardings import approvalcycle as _ac


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
            cycle = _ac.resolveActiveCycleTx(
                cur,
                companyId=companyId,
                reportingYear=reportingYear,
                cycleType=cycleType,
                reportBasisType=reportBasisType,
                sourceMaterialityRunId=sourceMaterialityRunId,
                actorUserId=actorUserId,
                batchId=batchId,
            )
            scopeRepo.requireWritableCycleTx(cur, cycle, companyId, batchId=batchId)
            scope = _ac.requireApprovalScopeTx(cur, cycle, companyId, metricId)
            requiredAtomicIds = _ac.resolveRequiredApprovalAtomicIdsTx(cur, cycleType, batchId, metricId)
            assignment = inputRepo.resolveAssignment(cur, int(cycle["id"]), companyId, metricId)
            rows = inputRepo.selectInputRowsForUpdate(cur, companyId, reportingYear, metricId, requiredAtomicIds)
            if _ac.checkRowsAllStatus(rows, requiredAtomicIds, STATE_SUBMITTED):
                conn.commit()
                return buildMetricApprovalSummary(
                    companyId,
                    reportingYear,
                    metricId,
                    cycle.get("cycle_type") or cycleType,
                    batchId=batchId,
                    sourceMaterialityRunId=cycle.get("source_materiality_run_id"),
                )
            if _ac.checkRowsAnyStatus(rows, requiredAtomicIds, {STATE_REVIEWED, STATE_APPROVED}):
                raise ValueError(f"Cannot resubmit {metricId} from reviewed or approved status")
            inputRepo.validateCompleteRows(rows, requiredAtomicIds, allowedStatuses={STATE_DRAFT, STATE_REJECTED, STATE_SUBMITTED})
            _ac.setMetricInputStatusTx(
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
            sourceMaterialityRunId=cycle.get("source_materiality_run_id"),
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
            cycle = _ac.resolveExistingActiveCycleTx(cur, companyId, reportingYear, cycleType, batchId=batchId)
            scopeRepo.requireWritableCycleTx(cur, cycle, companyId, batchId=batchId)
            _ac.requireApprovalScopeTx(cur, cycle, companyId, metricId)
            requiredAtomicIds = _ac.resolveRequiredApprovalAtomicIdsTx(cur, cycleType, batchId, metricId)
            assignment = inputRepo.resolveAssignment(cur, int(cycle["id"]), companyId, metricId)
            rows = inputRepo.selectInputRowsForUpdate(cur, companyId, reportingYear, metricId, requiredAtomicIds)
            inputRepo.validateCompleteRows(rows, requiredAtomicIds, allowedStatuses={STATE_SUBMITTED})
            _ac.setMetricInputStatusTx(
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
            sourceMaterialityRunId=cycle.get("source_materiality_run_id"),
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
            cycle = _ac.resolveExistingActiveCycleTx(cur, companyId, reportingYear, cycleType, batchId=batchId)
            scopeRepo.requireWritableCycleTx(cur, cycle, companyId, batchId=batchId)
            scope = _ac.requireApprovalScopeTx(cur, cycle, companyId, metricId)
            requiredAtomicIds = _ac.resolveRequiredApprovalAtomicIdsTx(cur, cycleType, batchId, metricId)
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
                _ac.syncRollupSourceReadinessIfNeededTx(
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
                    sourceMaterialityRunId=cycle.get("source_materiality_run_id"),
                )
            if _ac.checkRowsAllStatus(rows, requiredAtomicIds, STATE_APPROVED):
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
                _ac.syncRollupSourceReadinessIfNeededTx(
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
                    sourceMaterialityRunId=cycle.get("source_materiality_run_id"),
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
            _ac.setMetricInputStatusTx(
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
            _ac.syncRollupSourceReadinessIfNeededTx(
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
            sourceMaterialityRunId=cycle.get("source_materiality_run_id"),
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
            cycle = _ac.resolveExistingActiveCycleTx(cur, companyId, reportingYear, cycleType, batchId=batchId)
            scopeRepo.requireWritableCycleTx(cur, cycle, companyId, batchId=batchId)
            _ac.requireApprovalScopeTx(cur, cycle, companyId, metricId)
            requiredAtomicIds = _ac.resolveRequiredApprovalAtomicIdsTx(cur, cycleType, batchId, metricId)
            assignment = inputRepo.resolveAssignment(cur, int(cycle["id"]), companyId, metricId)
            rows = inputRepo.selectInputRowsForUpdate(cur, companyId, reportingYear, metricId, requiredAtomicIds)
            inputRepo.validateCompleteRows(rows, requiredAtomicIds, allowedStatuses={STATE_SUBMITTED, STATE_REVIEWED})
            _ac.setMetricInputStatusTx(
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
            sourceMaterialityRunId=cycle.get("source_materiality_run_id"),
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
    sourceMaterialityRunId: Optional[int] = None,
) -> dict:
    summary = approvalRepo.buildApprovalSummary(
        companyId,
        reportingYear,
        metricId,
        cycleType,
        batchId=batchId,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
    if calculationSummary:
        summary["calculationReadyYn"] = calculationSummary.get("calculationReadyYn")
        summary["affectedRuleCount"] = calculationSummary.get("affectedRuleCount", 0)
        summary["invalidatedFactCount"] = calculationSummary.get("invalidatedFactCount", 0)
        summary["calculatedFactCount"] = calculationSummary.get("calculatedFactCount", 0)
        summary["calculationWarnings"] = calculationSummary.get("calculationWarnings", [])
    return summary


# 이 모듈에서 직접 임포트하는 호출자를 위한 호환성 재내보내기
resolveRequiredApprovalAtomicIdsTx = _ac.resolveRequiredApprovalAtomicIdsTx
resolveActiveCycleTx = _ac.resolveActiveCycleTx
resolveExistingActiveCycleTx = _ac.resolveExistingActiveCycleTx
requireApprovalScopeTx = _ac.requireApprovalScopeTx
setMetricInputStatusTx = _ac.setMetricInputStatusTx
syncRollupSourceReadinessIfNeededTx = _ac.syncRollupSourceReadinessIfNeededTx
normalizeCycleType = _ac.normalizeCycleType
checkRowsAllStatus = _ac.checkRowsAllStatus
checkRowsAnyStatus = _ac.checkRowsAnyStatus
