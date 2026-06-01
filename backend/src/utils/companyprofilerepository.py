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


def resolveG0ReportingYear(companyId: int, reportingYear: Optional[int] = None) -> int:
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
              AND (metric_id LIKE 'G0-%' OR atomic_metric_id LIKE 'G0-%')
            UNION ALL
            SELECT reporting_year
            FROM ESG_KPI_FACT
            WHERE company_id = ?
              AND delete_yn = 0
              AND (metric_id LIKE 'G0-%' OR atomic_metric_id LIKE 'G0-%')
            UNION ALL
            SELECT reporting_year
            FROM ESG_GROUP_ROLLUP_RESULT
            WHERE parent_company_id = ?
              AND delete_yn = 0
              AND (group_metric_id LIKE 'G0-%' OR group_atomic_metric_id LIKE 'G0-%')
        ) y
        """,
        (companyId, companyId, companyId),
    ) or {}
    return int(row.get("reporting_year") or datetime.now().year)


def getG0MasterItems() -> list[dict]:
    return findAll(
        """
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
          AND (metric_id LIKE 'G0-%' OR atomic_metric_id LIKE 'G0-%')
        ORDER BY metric_id, atomic_metric_id
        """
    ) or []


def getG0ValueRows(companyId: int, reportingYear: int) -> list[dict]:
    return findAll(
        """
        SELECT
            'onboarding_input' AS source_table,
            iv.metric_id,
            iv.atomic_metric_id,
            iv.value_text,
            iv.value_numeric,
            iv.unit,
            iv.updated_at
        FROM ESG_ONBOARDING_INPUT_VALUE iv
        WHERE iv.company_id = ?
          AND iv.reporting_year = ?
          AND iv.delete_yn = 0
          AND (iv.metric_id LIKE 'G0-%' OR iv.atomic_metric_id LIKE 'G0-%')

        UNION ALL

        SELECT
            'kpi_fact' AS source_table,
            kf.metric_id,
            kf.atomic_metric_id,
            kf.value_text,
            kf.value_numeric,
            kf.unit,
            kf.updated_at
        FROM ESG_KPI_FACT kf
        WHERE kf.company_id = ?
          AND kf.reporting_year = ?
          AND kf.delete_yn = 0
          AND (kf.metric_id LIKE 'G0-%' OR kf.atomic_metric_id LIKE 'G0-%')

        UNION ALL

        SELECT
            'group_rollup_result' AS source_table,
            gr.group_metric_id AS metric_id,
            gr.group_atomic_metric_id AS atomic_metric_id,
            gr.value_text,
            gr.value_numeric,
            gr.unit,
            gr.updated_at
        FROM ESG_GROUP_ROLLUP_RESULT gr
        WHERE gr.parent_company_id = ?
          AND gr.reporting_year = ?
          AND gr.delete_yn = 0
          AND (gr.group_metric_id LIKE 'G0-%' OR gr.group_atomic_metric_id LIKE 'G0-%')
        """,
        (companyId, reportingYear, companyId, reportingYear, companyId, reportingYear),
    ) or []


def upsertG0InputValue(
    companyId: int,
    reportingYear: int,
    metricId: str,
    atomicMetricId: str,
    valueText: Optional[str],
    valueNumeric: Optional[float],
    unit: Optional[str],
    userId: Optional[int] = None,
) -> bool:
    conn = getConn()
    if not conn:
        return False
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT id, input_status
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
                (companyId, reportingYear, metricId, atomicMetricId),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE ESG_ONBOARDING_INPUT_VALUE
                    SET value_text = ?,
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
                    (valueText, valueNumeric, unit, userId, existing["id"]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO ESG_ONBOARDING_INPUT_VALUE (
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
                    ) VALUES (?, ?, 'ENTITY', ?, ?, ?, ?, ?, 'manual_input', 'draft', ?)
                    """,
                    (companyId, reportingYear, metricId, atomicMetricId, valueNumeric, valueText, unit, userId),
                )
            invalidateG002KpiFactTx(cur, companyId, reportingYear, metricId, atomicMetricId)
        conn.commit()
        return True
    except Exception as e:
        print(f"G0 input transaction error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def invalidateG002KpiFactTx(
    cur,
    companyId: int,
    reportingYear: int,
    metricId: str,
    atomicMetricId: str,
) -> None:
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
