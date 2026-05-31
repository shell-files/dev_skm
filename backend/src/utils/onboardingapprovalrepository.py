from __future__ import annotations

from typing import Optional

import mariadb

from src.utils.db import findAll, findOne, getConn


CYCLE_TYPE_PRE_DMA_G0 = "PRE_DMA_G0"
METRIC_ID_G0_02 = "G0-02"
METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
REQUIRED_ATOMIC_IDS = [
    "G0-02__Q0001",
    "G0-02__Q0002",
    "G0-02__Q0003",
    "G0-02__Q0004",
    "G0-02__Q0005",
]


def ensurePreDmaG0Cycle(
    companyId: int,
    reportingYear: int,
    reportBasisType: Optional[str] = None,
    sourceMaterialityRunId: Optional[int] = None,
    actorUserId: Optional[int] = None,
) -> dict:
    conn = getConn()
    if not conn:
        return {}
    try:
        with conn.cursor(dictionary=True) as cur:
            cycle = resolveCycle(cur, companyId, reportingYear)
            if cycle:
                return cycle
            try:
                insertCycle(
                    cur,
                    companyId=companyId,
                    reportingYear=reportingYear,
                    reportBasisType=reportBasisType,
                    sourceMaterialityRunId=sourceMaterialityRunId,
                    actorUserId=actorUserId,
                )
                conn.commit()
            except mariadb.IntegrityError:
                conn.rollback()
            return resolveCycle(cur, companyId, reportingYear)
    finally:
        conn.close()


def listG002Inputs(companyId: int, reportingYear: int) -> list[dict]:
    placeholders = ", ".join(["?"] * len(REQUIRED_ATOMIC_IDS))
    return findAll(
        f"""
        SELECT *
        FROM ESG_ONBOARDING_INPUT_VALUE
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id = ?
          AND atomic_metric_id IN ({placeholders})
          AND delete_yn = 0
        ORDER BY atomic_metric_id
        """,
        (companyId, reportingYear, METRIC_ID_G0_02, *REQUIRED_ATOMIC_IDS),
    ) or []


def listG002KpiFacts(companyId: int, reportingYear: int) -> list[dict]:
    placeholders = ", ".join(["?"] * len(REQUIRED_ATOMIC_IDS))
    return findAll(
        f"""
        SELECT *
        FROM ESG_KPI_FACT
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id = ?
          AND atomic_metric_id IN ({placeholders})
          AND LOWER(COALESCE(approval_status, '')) = 'approved'
          AND value_numeric IS NOT NULL
          AND delete_yn = 0
        ORDER BY atomic_metric_id
        """,
        (companyId, reportingYear, METRIC_ID_G0_02, *REQUIRED_ATOMIC_IDS),
    ) or []


def getMetricName(metricId: str) -> Optional[str]:
    row = findOne(
        """
        SELECT metric_name_kr
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE metric_id = ?
          AND delete_yn = 0
          AND active_yn = 1
        ORDER BY atomic_metric_id
        LIMIT 1
        """,
        (metricId,),
    ) or {}
    return row.get("metric_name_kr")


def getLatestHistory(companyId: int, reportingYear: int, metricId: str) -> dict:
    return findOne(
        """
        SELECT *
        FROM ESG_ONBOARDING_APPROVAL_HISTORY
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id = ?
          AND delete_yn = 0
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (companyId, reportingYear, metricId),
    ) or {}


def listApprovalSummaries(
    companyId: int,
    reportingYear: Optional[int] = None,
    status: Optional[str] = None,
    cycleType: Optional[str] = None,
) -> list[dict]:
    params = [companyId]
    yearFilter = ""
    if reportingYear is not None:
        yearFilter = "AND iv.reporting_year = ?"
        params.append(reportingYear)
    inputRows = findAll(
        f"""
        SELECT
            iv.company_id,
            iv.reporting_year,
            iv.metric_id
        FROM ESG_ONBOARDING_INPUT_VALUE iv
        LEFT JOIN ESG_ONBOARDING_CYCLE c
          ON c.id = iv.esg_onboarding_cycle_id
         AND c.delete_yn = 0
        WHERE iv.company_id = ?
          {yearFilter}
          AND iv.metric_id = ?
          AND iv.atomic_metric_id IN ({", ".join(["?"] * len(REQUIRED_ATOMIC_IDS))})
          AND iv.delete_yn = 0
          {cycleTypeFilter(cycleType)}
        GROUP BY iv.company_id, iv.reporting_year, iv.metric_id
        ORDER BY iv.reporting_year DESC
        """,
        (*params, METRIC_ID_G0_02, *REQUIRED_ATOMIC_IDS),
    ) or []
    summaries = []
    for row in inputRows:
        summary = buildApprovalSummary(int(row["company_id"]), int(row["reporting_year"]), row["metric_id"])
        if status and str(summary.get("approvalStatus") or "").upper() != str(status).upper():
            continue
        summaries.append(summary)
    return summaries


def submitG002Approval(
    companyId: int,
    reportingYear: int,
    reportBasisType: Optional[str],
    sourceMaterialityRunId: Optional[int],
    actorUserId: Optional[int],
) -> dict:
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        with conn.cursor(dictionary=True) as cur:
            cycle = ensureCycleTx(
                cur,
                companyId,
                reportingYear,
                reportBasisType,
                sourceMaterialityRunId,
                actorUserId,
            )
            assignment = resolveAssignment(cur, int(cycle["id"]), companyId, METRIC_ID_G0_02)
            rows = selectInputRowsForUpdate(cur, companyId, reportingYear)
            validateCompleteRows(rows, allowedStatuses={"draft", "rejected", "submitted"})
            assignmentId = int(assignment["id"]) if assignment else None
            cur.execute(
                f"""
                UPDATE ESG_ONBOARDING_INPUT_VALUE
                SET esg_onboarding_cycle_id = ?,
                    esg_metric_assignment_id = ?,
                    input_status = 'submitted',
                    updated_at = CURRENT_TIMESTAMP
                WHERE company_id = ?
                  AND reporting_year = ?
                  AND metric_id = ?
                  AND atomic_metric_id IN ({", ".join(["?"] * len(REQUIRED_ATOMIC_IDS))})
                  AND delete_yn = 0
                """,
                (int(cycle["id"]), assignmentId, companyId, reportingYear, METRIC_ID_G0_02, *REQUIRED_ATOMIC_IDS),
            )
            insertHistory(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=assignmentId,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=METRIC_ID_G0_02,
                actionType="submit",
                actionStatus="submitted",
                actorUserId=actorUserId,
                assigneeUserId=assignment.get("assignee_user_id") if assignment else None,
                commentText=None,
            )
        conn.commit()
        return buildApprovalSummary(companyId, reportingYear, METRIC_ID_G0_02)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def approveG002Approval(
    companyId: int,
    reportingYear: int,
    actorUserId: Optional[int],
    commentText: Optional[str] = None,
) -> dict:
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        with conn.cursor(dictionary=True) as cur:
            cycle = resolveCycle(cur, companyId, reportingYear)
            if not cycle:
                raise ValueError("PRE_DMA_G0 cycle was not found")
            assignment = resolveAssignment(cur, int(cycle["id"]), companyId, METRIC_ID_G0_02)
            rows = selectInputRowsForUpdate(cur, companyId, reportingYear)
            validateCompleteRows(rows, allowedStatuses={"submitted", "reviewed", "approved"})
            assignmentId = int(assignment["id"]) if assignment else None
            for row in rows:
                if row["atomic_metric_id"] not in REQUIRED_ATOMIC_IDS:
                    continue
                upsertKpiFact(cur, row, actorUserId)
            cur.execute(
                f"""
                UPDATE ESG_ONBOARDING_INPUT_VALUE
                SET esg_onboarding_cycle_id = ?,
                    esg_metric_assignment_id = ?,
                    input_status = 'approved',
                    approved_by_user_id = ?,
                    approved_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE company_id = ?
                  AND reporting_year = ?
                  AND metric_id = ?
                  AND atomic_metric_id IN ({", ".join(["?"] * len(REQUIRED_ATOMIC_IDS))})
                  AND delete_yn = 0
                """,
                (int(cycle["id"]), assignmentId, actorUserId, companyId, reportingYear, METRIC_ID_G0_02, *REQUIRED_ATOMIC_IDS),
            )
            insertHistory(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=assignmentId,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=METRIC_ID_G0_02,
                actionType="approve",
                actionStatus="approved",
                actorUserId=actorUserId,
                assigneeUserId=assignment.get("assignee_user_id") if assignment else None,
                commentText=commentText,
            )
        conn.commit()
        return buildApprovalSummary(companyId, reportingYear, METRIC_ID_G0_02)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rejectG002Approval(
    companyId: int,
    reportingYear: int,
    actorUserId: Optional[int],
    commentText: str,
) -> dict:
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        with conn.cursor(dictionary=True) as cur:
            cycle = resolveCycle(cur, companyId, reportingYear)
            if not cycle:
                raise ValueError("PRE_DMA_G0 cycle was not found")
            assignment = resolveAssignment(cur, int(cycle["id"]), companyId, METRIC_ID_G0_02)
            rows = selectInputRowsForUpdate(cur, companyId, reportingYear)
            validateCompleteRows(rows, allowedStatuses={"submitted", "reviewed"})
            assignmentId = int(assignment["id"]) if assignment else None
            cur.execute(
                f"""
                UPDATE ESG_ONBOARDING_INPUT_VALUE
                SET input_status = 'rejected',
                    updated_at = CURRENT_TIMESTAMP
                WHERE company_id = ?
                  AND reporting_year = ?
                  AND metric_id = ?
                  AND atomic_metric_id IN ({", ".join(["?"] * len(REQUIRED_ATOMIC_IDS))})
                  AND delete_yn = 0
                """,
                (companyId, reportingYear, METRIC_ID_G0_02, *REQUIRED_ATOMIC_IDS),
            )
            insertHistory(
                cur,
                cycleId=int(cycle["id"]),
                assignmentId=assignmentId,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=METRIC_ID_G0_02,
                actionType="reject",
                actionStatus="rejected",
                actorUserId=actorUserId,
                assigneeUserId=assignment.get("assignee_user_id") if assignment else None,
                commentText=commentText,
            )
        conn.commit()
        return buildApprovalSummary(companyId, reportingYear, METRIC_ID_G0_02)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def buildApprovalSummary(companyId: int, reportingYear: int, metricId: str) -> dict:
    inputs = listG002Inputs(companyId, reportingYear)
    facts = listG002KpiFacts(companyId, reportingYear)
    cycle = findOne(
        """
        SELECT *
        FROM ESG_ONBOARDING_CYCLE
        WHERE company_id = ?
          AND reporting_year = ?
          AND cycle_type = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (companyId, reportingYear, CYCLE_TYPE_PRE_DMA_G0),
    ) or {}
    assignment = {}
    if cycle:
        assignment = findOne(
            """
            SELECT *
            FROM ESG_METRIC_ASSIGNMENT
            WHERE esg_onboarding_cycle_id = ?
              AND company_id = ?
              AND metric_id = ?
              AND delete_yn = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (cycle["id"], companyId, metricId),
        ) or {}
    latestHistory = getLatestHistory(companyId, reportingYear, metricId)
    approvedAtomicIds = {row["atomic_metric_id"] for row in facts}
    inputByAtomic = {row["atomic_metric_id"]: row for row in inputs}
    completedAtomicIds = {
        atomicId
        for atomicId, row in inputByAtomic.items()
        if atomicId in REQUIRED_ATOMIC_IDS and row.get("value_numeric") is not None
    }
    submittedAtomicIds = {
        atomicId
        for atomicId, row in inputByAtomic.items()
        if atomicId in REQUIRED_ATOMIC_IDS
        and str(row.get("input_status") or "").lower() in {"submitted", "reviewed", "approved"}
        and row.get("value_numeric") is not None
    }
    missingAtomicIds = [
        atomicId
        for atomicId in REQUIRED_ATOMIC_IDS
        if atomicId not in approvedAtomicIds
    ]
    return {
        "companyId": companyId,
        "reportingYear": reportingYear,
        "metricId": metricId,
        "metricName": getMetricName(metricId),
        "approvalStatus": resolveApprovalStatus(inputs, facts),
        "inputUserId": firstNonNull([row.get("input_user_id") for row in inputs]),
        "assigneeUserId": assignment.get("assignee_user_id"),
        "cycleId": int(cycle["id"]) if cycle else None,
        "assignmentId": int(assignment["id"]) if assignment else None,
        "requiredAtomicCount": len(REQUIRED_ATOMIC_IDS),
        "completedAtomicCount": len(completedAtomicIds),
        "submittedAtomicCount": len(submittedAtomicIds),
        "approvedAtomicCount": len(approvedAtomicIds),
        "missingAtomicMetricIds": missingAtomicIds,
        "submittedAt": formatDatetime(submittedAt(inputs, latestHistory)),
        "approvedAt": formatDatetime(approvedAt(inputs, facts, latestHistory)),
        "commentText": latestHistory.get("comment_text"),
        "selfSubmittedYn": False,
    }


def cycleTypeFilter(cycleType: Optional[str]) -> str:
    if not cycleType:
        return ""
    if str(cycleType).upper() != CYCLE_TYPE_PRE_DMA_G0:
        return "AND 1 = 0"
    return "AND (c.cycle_type = 'PRE_DMA_G0' OR c.id IS NULL)"


def resolveCycle(cur, companyId: int, reportingYear: int) -> dict:
    cur.execute(
        """
        SELECT *
        FROM ESG_ONBOARDING_CYCLE
        WHERE company_id = ?
          AND reporting_year = ?
          AND cycle_type = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (companyId, reportingYear, CYCLE_TYPE_PRE_DMA_G0),
    )
    return cur.fetchone() or {}


def ensureCycleTx(
    cur,
    companyId: int,
    reportingYear: int,
    reportBasisType: Optional[str],
    sourceMaterialityRunId: Optional[int],
    actorUserId: Optional[int],
) -> dict:
    cycle = resolveCycle(cur, companyId, reportingYear)
    if cycle:
        return cycle
    insertCycle(cur, companyId, reportingYear, reportBasisType, sourceMaterialityRunId, actorUserId)
    return resolveCycle(cur, companyId, reportingYear)


def insertCycle(
    cur,
    companyId: int,
    reportingYear: int,
    reportBasisType: Optional[str],
    sourceMaterialityRunId: Optional[int],
    actorUserId: Optional[int],
) -> None:
    cur.execute(
        """
        INSERT INTO ESG_ONBOARDING_CYCLE (
            company_id,
            reporting_year,
            cycle_name,
            cycle_type,
            report_basis_type,
            required_before_dma_yn,
            cycle_status,
            source_materiality_run_id,
            metric_scope_code,
            created_by_user_id
        ) VALUES (?, ?, ?, ?, ?, 1, 'active', ?, ?, ?)
        """,
        (
            companyId,
            reportingYear,
            f"PRE-DMA G0 {reportingYear}",
            CYCLE_TYPE_PRE_DMA_G0,
            reportBasisType,
            sourceMaterialityRunId,
            METRIC_SCOPE_G0_02_FINANCIAL_BASIS,
            actorUserId,
        ),
    )


def resolveAssignment(cur, cycleId: int, companyId: int, metricId: str) -> dict:
    cur.execute(
        """
        SELECT *
        FROM ESG_METRIC_ASSIGNMENT
        WHERE esg_onboarding_cycle_id = ?
          AND company_id = ?
          AND metric_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (cycleId, companyId, metricId),
    )
    return cur.fetchone() or {}


def selectInputRowsForUpdate(cur, companyId: int, reportingYear: int) -> list[dict]:
    cur.execute(
        f"""
        SELECT *
        FROM ESG_ONBOARDING_INPUT_VALUE
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id = ?
          AND atomic_metric_id IN ({", ".join(["?"] * len(REQUIRED_ATOMIC_IDS))})
          AND delete_yn = 0
        ORDER BY atomic_metric_id
        FOR UPDATE
        """,
        (companyId, reportingYear, METRIC_ID_G0_02, *REQUIRED_ATOMIC_IDS),
    )
    return cur.fetchall() or []


def validateCompleteRows(rows: list[dict], allowedStatuses: set[str]) -> None:
    rowByAtomic = {row["atomic_metric_id"]: row for row in rows}
    missing = [atomicId for atomicId in REQUIRED_ATOMIC_IDS if atomicId not in rowByAtomic]
    if missing:
        raise ValueError(f"Missing G0-02 input rows: {', '.join(missing)}")
    invalidValues = [
        atomicId
        for atomicId in REQUIRED_ATOMIC_IDS
        if rowByAtomic[atomicId].get("value_numeric") is None
    ]
    if invalidValues:
        raise ValueError(f"Missing numeric values: {', '.join(invalidValues)}")
    invalidStatuses = [
        f"{atomicId}:{rowByAtomic[atomicId].get('input_status')}"
        for atomicId in REQUIRED_ATOMIC_IDS
        if str(rowByAtomic[atomicId].get("input_status") or "").lower() not in allowedStatuses
    ]
    if invalidStatuses:
        raise ValueError(f"Invalid input status: {', '.join(invalidStatuses)}")


def upsertKpiFact(cur, inputRow: dict, actorUserId: Optional[int]) -> None:
    cur.execute(
        """
        INSERT INTO ESG_KPI_FACT (
            source_input_value_id,
            company_id,
            reporting_year,
            company_scope_type,
            metric_id,
            atomic_metric_id,
            value_numeric,
            value_text,
            unit,
            value_source_type,
            approval_status,
            approved_by_user_id,
            approved_at,
            delete_yn
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'onboarding_approval', 'approved', ?, CURRENT_TIMESTAMP, 0)
        ON DUPLICATE KEY UPDATE
            source_input_value_id = VALUES(source_input_value_id),
            company_scope_type = VALUES(company_scope_type),
            metric_id = VALUES(metric_id),
            value_numeric = VALUES(value_numeric),
            value_text = VALUES(value_text),
            unit = VALUES(unit),
            value_source_type = VALUES(value_source_type),
            approval_status = 'approved',
            approved_by_user_id = VALUES(approved_by_user_id),
            approved_at = CURRENT_TIMESTAMP,
            delete_yn = 0,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            inputRow.get("id"),
            inputRow.get("company_id"),
            inputRow.get("reporting_year"),
            inputRow.get("company_scope_type") or "ENTITY",
            inputRow.get("metric_id"),
            inputRow.get("atomic_metric_id"),
            inputRow.get("value_numeric"),
            inputRow.get("value_text"),
            inputRow.get("unit"),
            actorUserId,
        ),
    )


def insertHistory(
    cur,
    cycleId: int,
    assignmentId: Optional[int],
    companyId: int,
    reportingYear: int,
    metricId: str,
    actionType: str,
    actionStatus: str,
    actorUserId: Optional[int],
    assigneeUserId: Optional[int],
    commentText: Optional[str],
) -> None:
    cur.execute(
        """
        INSERT INTO ESG_ONBOARDING_APPROVAL_HISTORY (
            esg_onboarding_cycle_id,
            esg_metric_assignment_id,
            company_id,
            reporting_year,
            metric_id,
            atomic_metric_id,
            action_type,
            action_status,
            actor_user_id,
            assignee_user_id,
            comment_text
        ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
        """,
        (
            cycleId,
            assignmentId,
            companyId,
            reportingYear,
            metricId,
            actionType,
            actionStatus,
            actorUserId,
            assigneeUserId,
            commentText,
        ),
    )


def resolveApprovalStatus(inputs: list[dict], facts: list[dict]) -> str:
    if len(facts) >= len(REQUIRED_ATOMIC_IDS):
        return "APPROVED"
    statuses = {str(row.get("input_status") or "").lower() for row in inputs}
    if "rejected" in statuses:
        return "REJECTED"
    if statuses and statuses.issubset({"submitted", "reviewed", "approved"}):
        return "SUBMITTED"
    if inputs:
        return "DRAFT"
    return "NOT_STARTED"


def submittedAt(inputs: list[dict], latestHistory: dict):
    if str(latestHistory.get("action_status") or "").lower() == "submitted":
        return latestHistory.get("created_at")
    submittedRows = [
        row.get("updated_at")
        for row in inputs
        if str(row.get("input_status") or "").lower() in {"submitted", "reviewed", "approved"}
    ]
    return max(submittedRows) if submittedRows else None


def approvedAt(inputs: list[dict], facts: list[dict], latestHistory: dict):
    if str(latestHistory.get("action_status") or "").lower() == "approved":
        return latestHistory.get("created_at")
    approvedValues = [row.get("approved_at") for row in inputs if row.get("approved_at")]
    approvedValues.extend([row.get("approved_at") for row in facts if row.get("approved_at")])
    return max(approvedValues) if approvedValues else None


def firstNonNull(values: list) -> Optional[int]:
    for value in values:
        if value is not None:
            return int(value)
    return None


def formatDatetime(value) -> Optional[str]:
    if value is None:
        return None
    return str(value)


__all__ = [
    "CYCLE_TYPE_PRE_DMA_G0",
    "METRIC_ID_G0_02",
    "METRIC_SCOPE_G0_02_FINANCIAL_BASIS",
    "REQUIRED_ATOMIC_IDS",
    "ensurePreDmaG0Cycle",
    "listG002Inputs",
    "listG002KpiFacts",
    "listApprovalSummaries",
    "submitG002Approval",
    "approveG002Approval",
    "rejectG002Approval",
    "buildApprovalSummary",
]
