from __future__ import annotations

from typing import Optional

from src.utils.db import findAll, findOne, getConn
from src.utils.onboardingscoperepository import METRIC_ID_G0_02


def listValueRows(companyId: int, reportingYear: int, metricIds: list[str]) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    params = (
        companyId,
        reportingYear,
        *metricIds,
        companyId,
        reportingYear,
        *metricIds,
        companyId,
        reportingYear,
        *metricIds,
    )
    return findAll(
        f"""
        SELECT
            'onboarding_input' AS source_table,
            iv.metric_id,
            iv.atomic_metric_id,
            iv.value_text,
            iv.value_numeric,
            iv.unit,
            iv.input_status,
            iv.updated_at
        FROM ESG_ONBOARDING_INPUT_VALUE iv
        WHERE iv.company_id = ?
          AND iv.reporting_year = ?
          AND iv.metric_id IN ({placeholders})
          AND iv.delete_yn = 0

        UNION ALL

        SELECT
            'kpi_fact' AS source_table,
            kf.metric_id,
            kf.atomic_metric_id,
            kf.value_text,
            kf.value_numeric,
            kf.unit,
            kf.approval_status AS input_status,
            kf.updated_at
        FROM ESG_KPI_FACT kf
        WHERE kf.company_id = ?
          AND kf.reporting_year = ?
          AND kf.metric_id IN ({placeholders})
          AND LOWER(COALESCE(kf.approval_status, '')) = 'approved'
          AND kf.delete_yn = 0

        UNION ALL

        SELECT
            'group_rollup_result' AS source_table,
            gr.group_metric_id AS metric_id,
            gr.group_atomic_metric_id AS atomic_metric_id,
            gr.value_text,
            gr.value_numeric,
            gr.unit,
            'approved' AS input_status,
            gr.updated_at
        FROM ESG_GROUP_ROLLUP_RESULT gr
        WHERE gr.parent_company_id = ?
          AND gr.reporting_year = ?
          AND gr.group_metric_id IN ({placeholders})
          AND gr.delete_yn = 0
        """,
        params,
    ) or []

def resolveAssignmentId(cycleId: int, companyId: int, metricId: str) -> Optional[int]:
    row = findOne(
        """
        SELECT id
        FROM ESG_METRIC_ASSIGNMENT
        WHERE esg_onboarding_cycle_id = ?
          AND company_id = ?
          AND metric_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (cycleId, companyId, metricId),
    ) or {}
    return int(row["id"]) if row.get("id") is not None else None

def upsertMetricInputValues(
    *,
    cycleId: int,
    companyId: int,
    reportingYear: int,
    metricId: str,
    assignmentId: Optional[int],
    values: list[dict],
    userId: Optional[int],
) -> int:
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        with conn.cursor(dictionary=True) as cur:
            savedCount = upsertMetricInputValuesTx(
                cur,
                cycleId=cycleId,
                companyId=companyId,
                reportingYear=reportingYear,
                metricId=metricId,
                assignmentId=assignmentId,
                values=values,
                userId=userId,
            )
        conn.commit()
        return savedCount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def upsertMetricValueGroups(groups: list[dict]) -> int:
    if not groups:
        return 0
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        savedCount = 0
        with conn.cursor(dictionary=True) as cur:
            for group in groups:
                savedCount += upsertMetricInputValuesTx(cur, **group)
        conn.commit()
        return savedCount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def upsertMetricInputValuesTx(
    cur,
    *,
    cycleId: int,
    companyId: int,
    reportingYear: int,
    metricId: str,
    assignmentId: Optional[int],
    values: list[dict],
    userId: Optional[int],
) -> int:
    savedCount = 0
    for value in values:
        cur.execute(
            """
            SELECT id
            FROM ESG_ONBOARDING_INPUT_VALUE
            WHERE company_id = ?
              AND reporting_year = ?
              AND metric_id = ?
              AND atomic_metric_id = ?
              AND delete_yn = 0
            ORDER BY id DESC
            LIMIT 1
            FOR UPDATE
            """,
            (
                companyId,
                reportingYear,
                metricId,
                value["atomicMetricId"],
            ),
        )
        existing = cur.fetchone()
        if existing:
            cur.execute(
                """
                UPDATE ESG_ONBOARDING_INPUT_VALUE
                SET esg_onboarding_cycle_id = ?,
                    esg_metric_assignment_id = ?,
                    value_text = ?,
                    value_numeric = ?,
                    unit = ?,
                    value_source_type = 'manual_input',
                    input_status = 'draft',
                    input_user_id = ?,
                    approved_by_user_id = NULL,
                    approved_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    cycleId,
                    assignmentId,
                    value.get("valueText"),
                    value.get("valueNumeric"),
                    value.get("unit"),
                    userId,
                    existing["id"],
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO ESG_ONBOARDING_INPUT_VALUE (
                    esg_onboarding_cycle_id,
                    esg_metric_assignment_id,
                    company_id,
                    reporting_year,
                    company_scope_type,
                    metric_id,
                    atomic_metric_id,
                    value_numeric,
                    value_text,
                    unit,
                    value_source_type,
                    input_status,
                    input_user_id
                ) VALUES (?, ?, ?, ?, 'ENTITY', ?, ?, ?, ?, ?, 'manual_input', 'draft', ?)
                """,
                (
                    cycleId,
                    assignmentId,
                    companyId,
                    reportingYear,
                    metricId,
                    value["atomicMetricId"],
                    value.get("valueNumeric"),
                    value.get("valueText"),
                    value.get("unit"),
                    userId,
                ),
            )
        invalidateMetricKpiFactsTx(cur, companyId, reportingYear, metricId, value["atomicMetricId"])
        savedCount += 1
    return savedCount

def invalidateMetricKpiFactsTx(cur, companyId: int, reportingYear: int, metricId: str, atomicMetricId: str) -> None:
    cur.execute(
        """
        UPDATE ESG_KPI_FACT k
        JOIN ESG_ONBOARDING_INPUT_VALUE iv
          ON iv.id = k.source_input_value_id
         AND iv.company_id = k.company_id
         AND iv.reporting_year = k.reporting_year
         AND iv.metric_id = k.metric_id
         AND iv.atomic_metric_id = k.atomic_metric_id
        SET k.approval_status = 'invalidated',
            k.delete_yn = 1,
            k.updated_at = CURRENT_TIMESTAMP
        WHERE iv.company_id = ?
          AND iv.reporting_year = ?
          AND iv.metric_id = ?
          AND iv.atomic_metric_id = ?
          AND iv.delete_yn = 0
          AND k.delete_yn = 0
          AND LOWER(COALESCE(k.approval_status, '')) = 'approved'
        """,
        (companyId, reportingYear, metricId, atomicMetricId),
    )


def invalidateG002KpiFactTx(cur, companyId: int, reportingYear: int, metricId: str, atomicMetricId: str) -> None:
    invalidateMetricKpiFactsTx(cur, companyId, reportingYear, metricId, atomicMetricId)

def listMetricInputs(companyId: int, reportingYear: int, metricId: str) -> list[dict]:
    requiredAtomicIds = listRequiredAtomicIds(metricId)
    if not requiredAtomicIds:
        return []
    placeholders = ", ".join(["?"] * len(requiredAtomicIds))
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
        (companyId, reportingYear, metricId, *requiredAtomicIds),
    ) or []

def listG002Inputs(companyId: int, reportingYear: int) -> list[dict]:
    return listMetricInputs(companyId, reportingYear, METRIC_ID_G0_02)

def listMetricKpiFacts(companyId: int, reportingYear: int, metricId: str) -> list[dict]:
    requiredAtomicIds = listRequiredAtomicIds(metricId)
    if not requiredAtomicIds:
        return []
    placeholders = ", ".join(["?"] * len(requiredAtomicIds))
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
          AND source_input_value_id IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM ESG_ONBOARDING_INPUT_VALUE iv
              WHERE iv.id = ESG_KPI_FACT.source_input_value_id
                AND iv.company_id = ESG_KPI_FACT.company_id
                AND iv.reporting_year = ESG_KPI_FACT.reporting_year
                AND iv.metric_id = ESG_KPI_FACT.metric_id
                AND iv.atomic_metric_id = ESG_KPI_FACT.atomic_metric_id
                AND LOWER(COALESCE(iv.input_status, '')) = 'approved'
                AND iv.delete_yn = 0
          )
        ORDER BY atomic_metric_id
        """,
        (companyId, reportingYear, metricId, *requiredAtomicIds),
    ) or []

def listG002KpiFacts(companyId: int, reportingYear: int) -> list[dict]:
    return listMetricKpiFacts(companyId, reportingYear, METRIC_ID_G0_02)

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

def listRequiredAtomicIds(metricId: str) -> list[str]:
    rows = findAll(
        """
        SELECT atomic_metric_id
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE metric_id = ?
          AND onboarding_input_yn = 1
          AND active_yn = 1
          AND delete_yn = 0
        ORDER BY atomic_metric_id
        """,
        (metricId,),
    ) or []
    return [row["atomic_metric_id"] for row in rows if row.get("atomic_metric_id")]

def listRequiredAtomicIdsTx(cur, metricId: str) -> list[str]:
    cur.execute(
        """
        SELECT atomic_metric_id
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE metric_id = ?
          AND onboarding_input_yn = 1
          AND active_yn = 1
          AND delete_yn = 0
        ORDER BY atomic_metric_id
        """,
        (metricId,),
    )
    rows = cur.fetchall() or []
    return [row["atomic_metric_id"] for row in rows if row.get("atomic_metric_id")]

def selectInputRowsForUpdate(
    cur,
    companyId: int,
    reportingYear: int,
    metricId: str,
    requiredAtomicIds: list[str],
) -> list[dict]:
    if not requiredAtomicIds:
        return []
    placeholders = ", ".join(["?"] * len(requiredAtomicIds))
    cur.execute(
        f"""
        SELECT *
        FROM ESG_ONBOARDING_INPUT_VALUE
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id = ?
          AND atomic_metric_id IN ({placeholders})
          AND delete_yn = 0
        ORDER BY atomic_metric_id
        FOR UPDATE
        """,
        (companyId, reportingYear, metricId, *requiredAtomicIds),
    )
    return cur.fetchall() or []

def validateCompleteRows(rows: list[dict], requiredAtomicIds: list[str], allowedStatuses: set[str]) -> None:
    rowByAtomic = {row["atomic_metric_id"]: row for row in rows}
    missing = [atomicId for atomicId in requiredAtomicIds if atomicId not in rowByAtomic]
    if missing:
        raise ValueError(f"Missing input rows: {', '.join(missing)}")
    invalidValues = [
        atomicId
        for atomicId in requiredAtomicIds
        if not hasMetricValue(rowByAtomic[atomicId])
    ]
    if invalidValues:
        raise ValueError(f"Missing values: {', '.join(invalidValues)}")
    invalidStatuses = [
        f"{atomicId}:{rowByAtomic[atomicId].get('input_status')}"
        for atomicId in requiredAtomicIds
        if str(rowByAtomic[atomicId].get("input_status") or "").lower() not in allowedStatuses
    ]
    if invalidStatuses:
        raise ValueError(f"Invalid input status: {', '.join(invalidStatuses)}")

def checkAlreadyApprovedTx(
    cur,
    rows: list[dict],
    companyId: int,
    reportingYear: int,
    metricId: str,
    requiredAtomicIds: list[str],
    requireKpiFactYn: bool = False,
) -> bool:
    if not requiredAtomicIds:
        return False
    rowByAtomic = {row["atomic_metric_id"]: row for row in rows}
    if any(atomicId not in rowByAtomic for atomicId in requiredAtomicIds):
        return False
    if any(
        str(rowByAtomic[atomicId].get("input_status") or "").lower() != "approved"
        or not hasMetricValue(rowByAtomic[atomicId])
        for atomicId in requiredAtomicIds
    ):
        return False
    if not requireKpiFactYn:
        return True
    placeholders = ", ".join(["?"] * len(requiredAtomicIds))
    cur.execute(
        f"""
        SELECT COUNT(*) AS approved_count
        FROM ESG_KPI_FACT k
        JOIN ESG_ONBOARDING_INPUT_VALUE iv
          ON iv.id = k.source_input_value_id
         AND iv.company_id = k.company_id
         AND iv.reporting_year = k.reporting_year
         AND iv.metric_id = k.metric_id
         AND iv.atomic_metric_id = k.atomic_metric_id
         AND iv.delete_yn = 0
         AND LOWER(COALESCE(iv.input_status, '')) = 'approved'
        WHERE k.company_id = ?
          AND k.reporting_year = ?
          AND k.metric_id = ?
          AND k.atomic_metric_id IN ({placeholders})
          AND LOWER(COALESCE(k.approval_status, '')) = 'approved'
          AND k.value_numeric IS NOT NULL
          AND k.delete_yn = 0
        """,
        (companyId, reportingYear, metricId, *requiredAtomicIds),
    )
    row = cur.fetchone() or {}
    return int(row.get("approved_count") or 0) >= len(requiredAtomicIds)

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

def resolveApprovalStatus(inputs: list[dict], facts: list[dict], requiredAtomicIds: Optional[list[str]] = None) -> str:
    requiredAtomicCount = len(requiredAtomicIds or [])
    if requiredAtomicCount and len(facts) >= requiredAtomicCount:
        return "APPROVED"
    if requiredAtomicCount:
        inputByAtomic = {row.get("atomic_metric_id"): row for row in inputs}
        if all(
            atomicId in inputByAtomic
            and hasMetricValue(inputByAtomic[atomicId])
            and str(inputByAtomic[atomicId].get("input_status") or "").lower() == "approved"
            for atomicId in requiredAtomicIds or []
        ):
            return "APPROVED"
    statuses = {str(row.get("input_status") or "").lower() for row in inputs}
    if "rejected" in statuses:
        return "REJECTED"
    if "reviewed" in statuses:
        return "REVIEWED"
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

def hasMetricValue(row: dict) -> bool:
    if row.get("value_numeric") is not None:
        return True
    return str(row.get("value_text") or "").strip() != ""

def truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        return int(value) != 0
    except (TypeError, ValueError):
        return str(value).strip().lower() in {"y", "yes", "true", "1"}

def groupRows(rows: list[dict], key: str) -> dict[str, list[dict]]:
    grouped = {}
    for row in rows:
        grouped.setdefault(row.get(key), []).append(row)
    return grouped

def normalizeIssueDomain(value: Optional[str]) -> Optional[str]:
    normalizedValue = str(value or "").strip().upper()
    if normalizedValue in {"E", "ENVIRONMENT", "ENVIRONMENTAL"} or normalizedValue.startswith("E_"):
        return "environmental"
    if normalizedValue in {"S", "SOCIAL"} or normalizedValue.startswith("S_"):
        return "social"
    if normalizedValue in {"G", "GOVERNANCE"} or normalizedValue.startswith("G_"):
        return "governance"
    if normalizedValue in {"G0", "GENERAL"}:
        return "general"
    return None

def listQuantInputAtomicRowsTx(cur, metricId: str) -> list[dict]:
    cur.execute(
        """
        SELECT atomic_metric_id, data_value_type, atomic_data_role
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE metric_id = ?
          AND onboarding_input_yn = 1
          AND active_yn = 1
          AND delete_yn = 0
          AND UPPER(COALESCE(atomic_data_role, '')) = 'INPUT'
          AND (
              UPPER(COALESCE(data_value_type, '')) IN ('QUANT', 'NUMBER', 'NUMERIC')
              OR data_value_type = '정량'
          )
        ORDER BY atomic_metric_id
        """,
        (metricId,),
    )
    return cur.fetchall() or []


def listQuantInputAtomicIdsTx(cur, metricId: str) -> list[str]:
    return [row["atomic_metric_id"] for row in listQuantInputAtomicRowsTx(cur, metricId) if row.get("atomic_metric_id")]


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

