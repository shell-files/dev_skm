from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.utils.db import findAll, findOne, getConn


METRIC_ID_G0_02 = "G0-02"
G0_02_ENTITY_ATOMIC_IDS = {
    "G0-02__Q0001",
    "G0-02__Q0002",
    "G0-02__Q0003",
    "G0-02__Q0004",
    "G0-02__Q0005",
}


def resolveReportingYear(companyId: int, reportingYear: Optional[int] = None) -> int:
    if reportingYear is not None:
        return int(reportingYear)

    row = findOne(
        """
        SELECT MAX(reporting_year) AS reporting_year
        FROM (
            SELECT reporting_year
            FROM ESG_ONBOARDING_INPUT_VALUE
            WHERE company_id = ?
              AND delete_yn = 0
            UNION ALL
            SELECT reporting_year
            FROM ESG_KPI_FACT
            WHERE company_id = ?
              AND delete_yn = 0
            UNION ALL
            SELECT reporting_year
            FROM ESG_GROUP_ROLLUP_RESULT
            WHERE parent_company_id = ?
              AND delete_yn = 0
        ) y
        """,
        (companyId, companyId, companyId),
    ) or {}
    return int(row.get("reporting_year") or datetime.now().year)


def getCycle(companyId: int, reportingYear: int, cycleType: str) -> dict:
    return findOne(
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
        (companyId, reportingYear, cycleType),
    ) or {}


def listMetricScopes(cycleId: int, companyId: int, metricId: Optional[str] = None) -> list[dict]:
    params = [cycleId, companyId]
    metricFilter = ""
    if metricId:
        metricFilter = "AND s.metric_id = ?"
        params.append(metricId)
    return findAll(
        f"""
        SELECT
            s.*,
            m.metric_name_kr
        FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE s
        LEFT JOIN (
            SELECT metric_id, MIN(metric_name_kr) AS metric_name_kr
            FROM ESG_ATOMIC_METRIC_MASTER
            WHERE delete_yn = 0
              AND active_yn = 1
            GROUP BY metric_id
        ) m
          ON m.metric_id = s.metric_id
        WHERE s.esg_onboarding_cycle_id = ?
          AND s.company_id = ?
          AND s.active_yn = 1
          AND s.delete_yn = 0
          {metricFilter}
        ORDER BY s.display_order, s.metric_id
        """,
        tuple(params),
    ) or []


def listAtomicMaster(metricIds: list[str]) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    return findAll(
        f"""
        SELECT
            metric_id,
            atomic_metric_id,
            metric_name_kr,
            atomic_name_kr,
            data_value_type,
            atomic_data_role,
            rollup_role,
            unit,
            onboarding_input_yn
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE delete_yn = 0
          AND active_yn = 1
          AND metric_id IN ({placeholders})
        ORDER BY metric_id, atomic_metric_id
        """,
        tuple(metricIds),
    ) or []


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


def listAssignmentRows(cycleId: int, companyId: int) -> list[dict]:
    return findAll(
        """
        SELECT
            a.id AS assignment_id,
            a.metric_id,
            a.assignment_status,
            a.assignee_user_id,
            a.assignee_email,
            a.due_date,
            a.invite_id,
            i.invite_status,
            i.invite_email_enc,
            u.email AS user_email
        FROM ESG_METRIC_ASSIGNMENT a
        LEFT JOIN ESG_ONBOARDING_INVITE i
          ON i.id = a.invite_id
         AND i.delete_yn = 0
        LEFT JOIN `with`.`USER` u
          ON u.id = a.assignee_user_id
         AND u.delete_yn = 0
        WHERE a.esg_onboarding_cycle_id = ?
          AND a.company_id = ?
          AND a.delete_yn = 0
        ORDER BY a.metric_id
        """,
        (cycleId, companyId),
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
        savedCount = 0
        with conn.cursor(dictionary=True) as cur:
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
                invalidateG002KpiFactTx(cur, companyId, reportingYear, metricId, value["atomicMetricId"])
                savedCount += 1
        conn.commit()
        return savedCount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def invalidateG002KpiFactTx(cur, companyId: int, reportingYear: int, metricId: str, atomicMetricId: str) -> None:
    if metricId != METRIC_ID_G0_02 or atomicMetricId not in G0_02_ENTITY_ATOMIC_IDS:
        return
    cur.execute(
        """
        UPDATE ESG_KPI_FACT
        SET approval_status = 'invalidated',
            delete_yn = 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id = ?
          AND atomic_metric_id = ?
          AND LOWER(COALESCE(approval_status, '')) = 'approved'
          AND delete_yn = 0
        """,
        (companyId, reportingYear, metricId, atomicMetricId),
    )

