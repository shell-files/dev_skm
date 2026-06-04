from __future__ import annotations

from datetime import datetime
from typing import Optional

import mariadb

from src.utils.db import findAll, findOne, getConn
from src.utils.settings import settings


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
            m.metric_name_kr,
            selected.id AS sub_issue_id,
            s.source_sub_issue_code AS sub_issue_code,
            sub_master.sub_issue_name_kr AS sub_issue_name,
            sub_master.issue_group_code AS sub_issue_domain
        FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE s
        LEFT JOIN (
            SELECT metric_id, MIN(metric_name_kr) AS metric_name_kr
            FROM ESG_ATOMIC_METRIC_MASTER
            WHERE delete_yn = 0
              AND active_yn = 1
            GROUP BY metric_id
        ) m
          ON m.metric_id = s.metric_id
        LEFT JOIN ESG_MATERIALITY_SELECTED_SUB_ISSUE selected
          ON selected.id = s.source_selected_sub_issue_id
         AND selected.esg_materiality_run_id = s.source_materiality_run_id
         AND selected.sub_issue_code = s.source_sub_issue_code
         AND selected.delete_yn = 0
        LEFT JOIN ESG_SUB_ISSUE_MASTER sub_master
          ON sub_master.sub_issue_code = s.source_sub_issue_code
         AND sub_master.delete_yn = 0
         AND sub_master.active_yn = 1
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
        invalidateG002KpiFactTx(cur, companyId, reportingYear, metricId, value["atomicMetricId"])
        savedCount += 1
    return savedCount


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


SUPPORTED_CYCLE_TYPE = "PRE_DMA_G0"
def listG0MetricMaster() -> list[dict]:
    return findAll(
        """
        SELECT DISTINCT metric_id, metric_name_kr
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE delete_yn = 0
          AND active_yn = 1
          AND metric_id LIKE 'G0-%'
        ORDER BY metric_id
        """
    ) or []


def validateG0MetricIds(metricIds: list[str]) -> list[str]:
    cleaned = []
    for metricId in metricIds or []:
        value = str(metricId or "").strip()
        if not value:
            continue
        if "__" in value:
            raise ValueError(f"atomic_metric_id is not allowed: {value}")
        if value not in cleaned:
            cleaned.append(value)
    if not cleaned:
        raise ValueError("metricIds is required")
    allowed = {row["metric_id"] for row in listG0MetricMaster()}
    invalid = [metricId for metricId in cleaned if metricId not in allowed]
    if invalid:
        raise ValueError(f"Unsupported metricId: {', '.join(invalid)}")
    return cleaned


def getCompanyName(companyId: int) -> str:
    companyName = getCompanyNameFromCompanyTable(companyId)
    if companyName:
        return companyName
    row = findOne(
        f"""
        SELECT COALESCE(company_code, CAST(company_id AS CHAR)) AS company_name
        FROM ESG_COMPANY_PROFILE
        WHERE company_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (companyId,),
    ) or {}
    return row.get("company_name") or str(companyId)


def getCompanyNameFromCompanyTable(companyId: int) -> Optional[str]:
    for schemaName in [None, "skm", "with"]:
        tableInfo = getCompanyTableInfo(schemaName)
        if not tableInfo:
            continue
        qualifiedTable = tableInfo["qualifiedTable"]
        idColumn = tableInfo["idColumn"]
        nameColumn = tableInfo["nameColumn"]
        deleteFilter = "AND delete_yn = 0" if tableInfo.get("hasDeleteYn") else ""
        try:
            row = findOne(
                f"""
                SELECT aes_d({nameColumn}, '{settings.maria_db_key}') AS company_name
                FROM {qualifiedTable}
                WHERE {idColumn} = ?
                  {deleteFilter}
                ORDER BY {idColumn} DESC
                LIMIT 1
                """,
                (companyId,),
            ) or {}
        except Exception:
            continue
        companyName = str(row.get("company_name") or "").strip()
        if companyName:
            return companyName
    return None


def getCompanyTableInfo(schemaName: Optional[str]) -> Optional[dict]:
    schemaFilter = "DATABASE()" if schemaName is None else "?"
    params = [] if schemaName is None else [schemaName]
    rows = findAll(
        f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = {schemaFilter}
          AND table_name = 'COMPANY'
        """,
        tuple(params),
    ) or []
    columns = {str(row.get("column_name") or "").lower() for row in rows}
    if not columns:
        return None
    idColumn = "company_id" if "company_id" in columns else "id" if "id" in columns else None
    nameColumn = "company_name" if "company_name" in columns else "name" if "name" in columns else None
    if not idColumn or not nameColumn:
        return None
    qualifiedTable = "COMPANY" if schemaName is None else f"`{schemaName}`.`COMPANY`"
    return {
        "qualifiedTable": qualifiedTable,
        "idColumn": idColumn,
        "nameColumn": nameColumn,
        "hasDeleteYn": "delete_yn" in columns,
    }


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
            try:
                cycle = ensureCycleTx(
                    cur,
                    companyId,
                    reportingYear,
                    reportBasisType,
                    sourceMaterialityRunId,
                    actorUserId,
                )
                conn.commit()
            except mariadb.IntegrityError:
                conn.rollback()
                with conn.cursor(dictionary=True) as retryCur:
                    cycle = ensureCycleTx(
                        retryCur,
                        companyId,
                        reportingYear,
                        reportBasisType,
                        sourceMaterialityRunId,
                        actorUserId,
                    )
                    conn.commit()
            return cycle
    finally:
        conn.close()


def ensurePostDmaDisclosureCycle(
    companyId: int,
    reportingYear: int,
    sourceMaterialityRunId: int,
    reportBasisType: Optional[str] = None,
    actorUserId: Optional[int] = None,
) -> dict:
    conn = getConn()
    if not conn:
        return {}
    try:
        with conn.cursor(dictionary=True) as cur:
            try:
                result = ensurePostDmaDisclosureCycleTx(
                    cur,
                    companyId=companyId,
                    reportingYear=reportingYear,
                    sourceMaterialityRunId=sourceMaterialityRunId,
                    reportBasisType=reportBasisType,
                    actorUserId=actorUserId,
                )
                conn.commit()
            except mariadb.IntegrityError:
                conn.rollback()
                with conn.cursor(dictionary=True) as retryCur:
                    result = ensurePostDmaDisclosureCycleTx(
                        retryCur,
                        companyId=companyId,
                        reportingYear=reportingYear,
                        sourceMaterialityRunId=sourceMaterialityRunId,
                        reportBasisType=reportBasisType,
                        actorUserId=actorUserId,
                    )
                    conn.commit()
            return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def resolvePreDmaG0Cycle(companyId: int, reportingYear: int) -> dict:
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
        (companyId, reportingYear, CYCLE_TYPE_PRE_DMA_G0),
    ) or {}


def listPreDmaG0MetricMaster() -> list[dict]:
    return findAll(
        """
        SELECT DISTINCT metric_id, metric_name_kr
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE delete_yn = 0
          AND active_yn = 1
          AND metric_id LIKE 'G0-%'
        ORDER BY metric_id
        """
    ) or []


def listCycleMetricScope(cycleId: int, companyId: int) -> list[dict]:
    return listMetricScopes(cycleId, companyId)


def validateCycleMetricIds(cycleId: int, companyId: int, metricIds: list[str]) -> list[str]:
    cleaned = []
    for metricId in metricIds or []:
        value = str(metricId or "").strip()
        if not value:
            continue
        if "__" in value:
            raise ValueError(f"atomic_metric_id is not allowed: {value}")
        if value not in cleaned:
            cleaned.append(value)
    if not cleaned:
        raise ValueError("metricIds is required")
    allowed = {row["metric_id"] for row in listCycleMetricScope(cycleId, companyId)}
    invalid = [metricId for metricId in cleaned if metricId not in allowed]
    if invalid:
        raise ValueError(f"Unsupported metricId for cycle scope: {', '.join(invalid)}")
    return cleaned


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


def listCycleApprovalInboxRows(
    companyId: int,
    reportingYear: Optional[int] = None,
    status: Optional[str] = None,
    cycleType: Optional[str] = None,
    assignedOnlyYn: bool = True,
) -> list[dict]:
    normalizedCycleType = str(cycleType or CYCLE_TYPE_PRE_DMA_G0).strip().upper()
    if normalizedCycleType != CYCLE_TYPE_PRE_DMA_G0:
        return []

    year = resolveReportingYear(companyId, reportingYear)
    cycle = getCycle(companyId, year, normalizedCycleType)
    if not cycle or str(cycle.get("cycle_status") or "").strip().lower() != "active":
        return []

    cycleId = int(cycle["id"])
    scopes = listMetricScopes(cycleId, companyId)
    if not scopes:
        return []

    metricIds = [row["metric_id"] for row in scopes if row.get("metric_id")]
    masterRows = listAtomicMaster(metricIds)
    inputRows = listApprovalInputRows(companyId, year, metricIds)
    factRows = listApprovalFactRows(companyId, year, metricIds)
    from src.utils.onboardingassignmentrepository import listAssignmentRows

    assignmentRows = listAssignmentRows(cycleId, companyId)
    historyRows = listLatestApprovalHistories(companyId, year, metricIds, cycleId)

    masterByMetric = groupRows(masterRows, "metric_id")
    inputByMetric = groupRows(inputRows, "metric_id")
    factByMetric = groupRows(factRows, "metric_id")
    assignmentByMetric = {row.get("metric_id"): row for row in assignmentRows}
    historyByMetric = {row.get("metric_id"): row for row in historyRows}
    statusFilter = str(status or "").strip().upper()

    items = []
    for scope in scopes:
        metricId = scope.get("metric_id")
        if not metricId:
            continue

        metricInputRows = inputByMetric.get(metricId, [])
        metricFactRows = factByMetric.get(metricId, [])
        assignment = assignmentByMetric.get(metricId) or {}
        latestHistory = historyByMetric.get(metricId) or {}

        if assignedOnlyYn and not assignment and not metricInputRows and not latestHistory:
            continue

        requiredAtomicIds = [
            row["atomic_metric_id"]
            for row in masterByMetric.get(metricId, [])
            if row.get("atomic_metric_id") and truthy(row.get("onboarding_input_yn"))
        ]
        requiredAtomicSet = set(requiredAtomicIds)
        completedAtomicIds = {
            row.get("atomic_metric_id")
            for row in metricInputRows
            if row.get("atomic_metric_id") in requiredAtomicSet and hasMetricValue(row)
        }
        completedAtomicIds.update(
            row.get("atomic_metric_id")
            for row in metricFactRows
            if row.get("atomic_metric_id") in requiredAtomicSet and hasMetricValue(row)
        )
        submittedAtomicIds = {
            row.get("atomic_metric_id")
            for row in metricInputRows
            if row.get("atomic_metric_id") in requiredAtomicSet
            and hasMetricValue(row)
            and str(row.get("input_status") or "").strip().lower() in {"submitted", "reviewed", "approved"}
        }
        approvedAtomicIds = {
            row.get("atomic_metric_id")
            for row in metricFactRows
            if row.get("atomic_metric_id") in requiredAtomicSet and hasMetricValue(row)
        }
        approvedAtomicIds.update(
            row.get("atomic_metric_id")
            for row in metricInputRows
            if row.get("atomic_metric_id") in requiredAtomicSet
            and hasMetricValue(row)
            and str(row.get("input_status") or "").strip().lower() == "approved"
        )

        approvalStatus = resolveCycleApprovalStatus(
            requiredAtomicCount=len(requiredAtomicSet),
            completedAtomicCount=len(completedAtomicIds),
            submittedAtomicCount=len(submittedAtomicIds),
            approvedAtomicCount=len(approvedAtomicIds),
            inputRows=metricInputRows,
            latestHistory=latestHistory,
        )
        if statusFilter and approvalStatus != statusFilter:
            continue

        actionSupportedYn = metricId == METRIC_ID_G0_02
        items.append(
            {
                "companyId": companyId,
                "reportingYear": year,
                "metricId": metricId,
                "metricName": scope.get("metric_name_kr") or getMetricName(metricId),
                "cycleType": cycle.get("cycle_type") or CYCLE_TYPE_PRE_DMA_G0,
                "issueDomain": normalizeIssueDomain(scope.get("sub_issue_domain")) or "general",
                "issueGroup": scope.get("issue_group") or None,
                "subIssueId": int(scope["sub_issue_id"]) if scope.get("sub_issue_id") is not None else None,
                "subIssueCode": scope.get("sub_issue_code"),
                "subIssueName": scope.get("sub_issue_name"),
                "approvalStatus": approvalStatus,
                "inputUserId": firstNonNull([row.get("input_user_id") for row in metricInputRows]),
                "assigneeUserId": assignment.get("assignee_user_id"),
                "cycleId": cycleId,
                "assignmentId": int(assignment["assignment_id"]) if assignment.get("assignment_id") is not None else None,
                "requiredAtomicCount": len(requiredAtomicSet),
                "completedAtomicCount": len(completedAtomicIds),
                "submittedAtomicCount": len(submittedAtomicIds),
                "approvedAtomicCount": len(approvedAtomicIds),
                "missingAtomicMetricIds": [
                    atomicId for atomicId in requiredAtomicIds if atomicId not in completedAtomicIds
                ],
                "submittedAt": formatDatetime(submittedAt(metricInputRows, latestHistory)),
                "approvedAt": formatDatetime(approvedAt(metricInputRows, metricFactRows, latestHistory)),
                "commentText": latestHistory.get("comment_text"),
                "selfSubmittedYn": False,
                "actionSupportedYn": actionSupportedYn,
                "actionDisabledReason": None
                if actionSupportedYn
                else "현재 MVP에서는 G0-02 승인 처리만 지원합니다.",
            }
        )
    return items


def listApprovalInputRows(companyId: int, reportingYear: int, metricIds: list[str]) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    return findAll(
        f"""
        SELECT
            metric_id,
            atomic_metric_id,
            value_text,
            value_numeric,
            unit,
            input_status,
            input_user_id,
            approved_at,
            updated_at
        FROM ESG_ONBOARDING_INPUT_VALUE
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id IN ({placeholders})
          AND delete_yn = 0
        ORDER BY metric_id, atomic_metric_id
        """,
        (companyId, reportingYear, *metricIds),
    ) or []


def listApprovalFactRows(companyId: int, reportingYear: int, metricIds: list[str]) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    return findAll(
        f"""
        SELECT
            metric_id,
            atomic_metric_id,
            value_text,
            value_numeric,
            unit,
            approval_status AS input_status,
            approved_at,
            updated_at
        FROM ESG_KPI_FACT
        WHERE company_id = ?
          AND reporting_year = ?
          AND metric_id IN ({placeholders})
          AND LOWER(COALESCE(approval_status, '')) = 'approved'
          AND delete_yn = 0
        ORDER BY metric_id, atomic_metric_id
        """,
        (companyId, reportingYear, *metricIds),
    ) or []


def listLatestApprovalHistories(
    companyId: int,
    reportingYear: int,
    metricIds: list[str],
    cycleId: Optional[int] = None,
) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    params = [companyId, reportingYear, *metricIds]
    cycleFilter = ""
    if cycleId is not None:
        cycleFilter = "AND esg_onboarding_cycle_id = ?"
        params.append(cycleId)
    return findAll(
        f"""
        SELECT h.*
        FROM ESG_ONBOARDING_APPROVAL_HISTORY h
        JOIN (
            SELECT metric_id, MAX(id) AS latest_id
            FROM ESG_ONBOARDING_APPROVAL_HISTORY
            WHERE company_id = ?
              AND reporting_year = ?
              AND metric_id IN ({placeholders})
              {cycleFilter}
              AND delete_yn = 0
            GROUP BY metric_id
        ) latest
          ON latest.latest_id = h.id
        ORDER BY h.metric_id
        """,
        tuple(params),
    ) or []


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


def groupRows(rows: list[dict], key: str) -> dict[str, list[dict]]:
    grouped = {}
    for row in rows:
        grouped.setdefault(row.get(key), []).append(row)
    return grouped


def resolveCycleApprovalStatus(
    *,
    requiredAtomicCount: int,
    completedAtomicCount: int,
    submittedAtomicCount: int,
    approvedAtomicCount: int,
    inputRows: list[dict],
    latestHistory: dict,
) -> str:
    if requiredAtomicCount > 0 and approvedAtomicCount >= requiredAtomicCount:
        return "APPROVED"
    latestStatus = str(latestHistory.get("action_status") or "").strip().lower()
    inputStatuses = {str(row.get("input_status") or "").strip().lower() for row in inputRows}
    if latestStatus == "rejected" or "rejected" in inputStatuses:
        return "REJECTED"
    if completedAtomicCount > 0 and submittedAtomicCount >= completedAtomicCount:
        return "SUBMITTED"
    if completedAtomicCount > 0:
        return "DRAFT"
    return "NOT_STARTED"


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
            if checkAlreadyApprovedTx(cur, rows, companyId, reportingYear):
                conn.commit()
                return buildApprovalSummary(companyId, reportingYear, METRIC_ID_G0_02)
            validateCompleteRows(rows, allowedStatuses={"draft", "rejected", "submitted", "approved"})
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
            if checkAlreadyApprovedTx(cur, rows, companyId, reportingYear):
                conn.commit()
                return buildApprovalSummary(companyId, reportingYear, METRIC_ID_G0_02)
            validateCompleteRows(rows, allowedStatuses={"submitted", "reviewed"})
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
        normalizeCycleTx(
            cur,
            cycle,
            reportBasisType=reportBasisType,
            sourceMaterialityRunId=sourceMaterialityRunId,
        )
        cycle = resolveCycle(cur, companyId, reportingYear)
        effectiveRunId = resolveScopeRunId(cycle, sourceMaterialityRunId)
        seedPreDmaG0ScopeTx(
            cur,
            cycleId=int(cycle["id"]),
            companyId=companyId,
            sourceMaterialityRunId=effectiveRunId,
            actorUserId=actorUserId,
        )
        return cycle
    insertCycle(cur, companyId, reportingYear, reportBasisType, sourceMaterialityRunId, actorUserId)
    cycle = resolveCycle(cur, companyId, reportingYear)
    effectiveRunId = resolveScopeRunId(cycle, sourceMaterialityRunId)
    seedPreDmaG0ScopeTx(
        cur,
        cycleId=int(cycle["id"]),
        companyId=companyId,
        sourceMaterialityRunId=effectiveRunId,
        actorUserId=actorUserId,
    )
    return cycle


def ensurePostDmaDisclosureCycleTx(
    cur,
    companyId: int,
    reportingYear: int,
    sourceMaterialityRunId: int,
    reportBasisType: Optional[str],
    actorUserId: Optional[int],
) -> dict:
    selectedRows = listSelectedSubIssueRowsTx(cur, sourceMaterialityRunId)
    if not selectedRows:
        raise ValueError(
            "MATERIALITY_SELECTION_NOT_CONFIRMED: "
            f"runId={sourceMaterialityRunId}"
        )

    mappingRows = listSelectedDisclosureMappingRowsTx(
        cur,
        [row["sub_issue_code"] for row in selectedRows if row.get("sub_issue_code")],
    )
    selectedByCode = {row["sub_issue_code"]: row for row in selectedRows}
    mappedSubIssueCodes = {
        row.get("sub_issue_code")
        for row in mappingRows
        if row.get("sub_issue_code")
    }
    missingSubIssueCodes = [
        row["sub_issue_code"]
        for row in selectedRows
        if row.get("sub_issue_code") not in mappedSubIssueCodes
    ]
    if missingSubIssueCodes:
        raise ValueError(
            "SELECTED_SUB_ISSUE_MAPPING_NOT_READY: "
            f"runId={sourceMaterialityRunId}, "
            f"missingSubIssueCodes={', '.join(missingSubIssueCodes)}"
        )

    scopeRows = buildSelectedDisclosureScopeRows(selectedByCode, mappingRows)
    expectedMetricIds = [row["metricId"] for row in scopeRows]
    cycle = ensurePostDmaCycleTx(
        cur,
        companyId=companyId,
        reportingYear=reportingYear,
        reportBasisType=reportBasisType,
        sourceMaterialityRunId=sourceMaterialityRunId,
        actorUserId=actorUserId,
    )
    cycleCreatedYn = bool(cycle.get("_createdYn"))
    existingScopeRows = listMetricScopesTx(cur, int(cycle["id"]), companyId)
    existingMetricIds = sorted({row["metric_id"] for row in existingScopeRows if row.get("metric_id")})
    if existingMetricIds and existingMetricIds != sorted(expectedMetricIds):
        raise ValueError(
            "POST_DMA_SCOPE_MISMATCH_REQUIRES_REVIEW: "
            f"cycleId={cycle['id']}, "
            f"existingMetricIds={', '.join(existingMetricIds)}, "
            f"expectedMetricIds={', '.join(sorted(expectedMetricIds))}"
        )

    seedSelectedDisclosureScopeTx(
        cur,
        cycleId=int(cycle["id"]),
        companyId=companyId,
        sourceMaterialityRunId=sourceMaterialityRunId,
        scopeRows=scopeRows,
        actorUserId=actorUserId,
    )
    cycle = resolvePostDmaCycleTx(cur, companyId, reportingYear)
    return {
        "cycle": cycle,
        "selectedSubIssueCount": len(selectedRows),
        "scopeMetricCount": len(scopeRows),
        "metricIds": expectedMetricIds,
        "cycleCreatedYn": cycleCreatedYn,
        "cycleReusedYn": not cycleCreatedYn,
    }


def listSelectedSubIssueRowsTx(cur, sourceMaterialityRunId: int) -> list[dict]:
    cur.execute(
        """
        SELECT
            id,
            esg_materiality_run_id,
            sub_issue_code,
            selected_rank_no,
            selection_type,
            selection_reason
        FROM ESG_MATERIALITY_SELECTED_SUB_ISSUE
        WHERE esg_materiality_run_id = ?
          AND delete_yn = 0
        ORDER BY
            CASE WHEN selected_rank_no IS NULL THEN 1 ELSE 0 END,
            selected_rank_no ASC,
            sub_issue_code ASC,
            id ASC
        """,
        (sourceMaterialityRunId,),
    )
    return cur.fetchall() or []


def listSelectedDisclosureMappingRowsTx(cur, subIssueCodes: list[str]) -> list[dict]:
    cleanedCodes = [code for code in subIssueCodes if code]
    if not cleanedCodes:
        return []
    placeholders = ", ".join(["?"] * len(cleanedCodes))
    cur.execute(
        f"""
        SELECT
            id,
            sub_issue_code,
            metric_id,
            atomic_metric_id,
            sort_order
        FROM ESG_SUB_ISSUE_ATOMIC_MAP
        WHERE sub_issue_code IN ({placeholders})
          AND map_scope = ?
          AND required_yn = 1
          AND delete_yn = 0
        ORDER BY sub_issue_code, sort_order, metric_id, atomic_metric_id, id
        """,
        (*cleanedCodes, MAP_SCOPE_MVP_SELECTED),
    )
    return cur.fetchall() or []


def buildSelectedDisclosureScopeRows(
    selectedByCode: dict[str, dict],
    mappingRows: list[dict],
) -> list[dict]:
    candidates = []
    for mappingRow in mappingRows:
        metricId = mappingRow.get("metric_id")
        subIssueCode = mappingRow.get("sub_issue_code")
        selectedRow = selectedByCode.get(subIssueCode)
        if not metricId or not selectedRow:
            continue
        candidates.append(
            {
                "metricId": metricId,
                "sourceSelectedSubIssueId": int(selectedRow["id"]),
                "sourceSubIssueCode": subIssueCode,
                "selectedRankNo": selectedRow.get("selected_rank_no"),
                "sortOrder": mappingRow.get("sort_order"),
            }
        )
    candidates.sort(
        key=lambda row: (
            1 if row.get("selectedRankNo") is None else 0,
            int(row.get("selectedRankNo") or 0),
            int(row.get("sortOrder") or 0),
            str(row.get("sourceSubIssueCode") or ""),
            int(row.get("sourceSelectedSubIssueId") or 0),
        )
    )

    rowsByMetric = {}
    for candidate in candidates:
        rowsByMetric.setdefault(candidate["metricId"], candidate)

    scopeRows = []
    for displayIndex, metricId in enumerate(rowsByMetric.keys(), start=1):
        candidate = rowsByMetric[metricId]
        scopeRows.append(
            {
                **candidate,
                "displayOrder": displayIndex * 10,
                "approvalPolicyCode": resolvePostDmaApprovalPolicy(candidate),
            }
        )
    return scopeRows


def resolvePostDmaApprovalPolicy(metricRow: dict) -> str:
    return APPROVAL_POLICY_INPUT_APPROVAL_ONLY


def ensurePostDmaCycleTx(
    cur,
    companyId: int,
    reportingYear: int,
    reportBasisType: Optional[str],
    sourceMaterialityRunId: int,
    actorUserId: Optional[int],
) -> dict:
    cycle = resolvePostDmaCycleTx(cur, companyId, reportingYear)
    if not cycle:
        insertPostDmaCycleTx(
            cur,
            companyId=companyId,
            reportingYear=reportingYear,
            reportBasisType=reportBasisType,
            sourceMaterialityRunId=sourceMaterialityRunId,
            actorUserId=actorUserId,
        )
        cycle = resolvePostDmaCycleTx(cur, companyId, reportingYear)
        cycle["_createdYn"] = True
        return cycle

    existingRunId = cycle.get("source_materiality_run_id")
    if existingRunId is not None and int(existingRunId) != int(sourceMaterialityRunId):
        raise ValueError(
            "POST_DMA_DISCLOSURE_SOURCE_RUN_CONFLICT: "
            f"cycleId={cycle['id']}, "
            f"existingRunId={existingRunId}, "
            f"requestedRunId={sourceMaterialityRunId}"
        )
    cycleStatus = str(cycle.get("cycle_status") or "").strip().lower()
    if cycleStatus != "active":
        raise ValueError(
            "POST_DMA_DISCLOSURE_CYCLE_NOT_ACTIVE: "
            f"cycleId={cycle['id']}, cycleStatus={cycle.get('cycle_status')}"
        )

    updates = []
    params = []
    if existingRunId is None:
        updates.append("source_materiality_run_id = ?")
        params.append(sourceMaterialityRunId)
    if cycle.get("report_basis_type") is None and reportBasisType is not None:
        updates.append("report_basis_type = ?")
        params.append(reportBasisType)
    if cycle.get("metric_scope_code") != METRIC_SCOPE_SELECTED_DISCLOSURE:
        updates.append("metric_scope_code = ?")
        params.append(METRIC_SCOPE_SELECTED_DISCLOSURE)
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(cycle["id"])
        cur.execute(
            f"""
            UPDATE ESG_ONBOARDING_CYCLE
            SET {", ".join(updates)}
            WHERE id = ?
              AND delete_yn = 0
            """,
            tuple(params),
        )
        cycle = resolvePostDmaCycleTx(cur, companyId, reportingYear)
    cycle["_createdYn"] = False
    return cycle


def resolvePostDmaCycleTx(cur, companyId: int, reportingYear: int) -> dict:
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
        (companyId, reportingYear, CYCLE_TYPE_POST_DMA_DISCLOSURE),
    )
    return cur.fetchone() or {}


def insertPostDmaCycleTx(
    cur,
    companyId: int,
    reportingYear: int,
    reportBasisType: Optional[str],
    sourceMaterialityRunId: int,
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
        ) VALUES (?, ?, ?, ?, ?, 0, 'active', ?, ?, ?)
        """,
        (
            companyId,
            reportingYear,
            f"POST-DMA Disclosure {reportingYear}",
            CYCLE_TYPE_POST_DMA_DISCLOSURE,
            reportBasisType,
            sourceMaterialityRunId,
            METRIC_SCOPE_SELECTED_DISCLOSURE,
            actorUserId,
        ),
    )


def listMetricScopesTx(cur, cycleId: int, companyId: int) -> list[dict]:
    cur.execute(
        """
        SELECT *
        FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
        WHERE esg_onboarding_cycle_id = ?
          AND company_id = ?
          AND active_yn = 1
          AND delete_yn = 0
        ORDER BY display_order, metric_id
        """,
        (cycleId, companyId),
    )
    return cur.fetchall() or []


def seedSelectedDisclosureScopeTx(
    cur,
    cycleId: int,
    companyId: int,
    sourceMaterialityRunId: int,
    scopeRows: list[dict],
    actorUserId: Optional[int],
) -> None:
    for row in scopeRows:
        cur.execute(
            """
            INSERT INTO ESG_ONBOARDING_CYCLE_METRIC_SCOPE (
                esg_onboarding_cycle_id,
                company_id,
                metric_id,
                scope_source_type,
                source_materiality_run_id,
                source_selected_sub_issue_id,
                source_sub_issue_code,
                required_yn,
                input_required_yn,
                approval_required_yn,
                approval_policy_code,
                rollup_readonly_yn,
                display_order,
                active_yn,
                created_by_user_id,
                delete_yn
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 1, ?, 0, ?, 1, ?, 0)
            ON DUPLICATE KEY UPDATE
                scope_source_type = VALUES(scope_source_type),
                source_materiality_run_id = VALUES(source_materiality_run_id),
                source_selected_sub_issue_id = VALUES(source_selected_sub_issue_id),
                source_sub_issue_code = VALUES(source_sub_issue_code),
                required_yn = 1,
                input_required_yn = 1,
                approval_required_yn = 1,
                approval_policy_code = VALUES(approval_policy_code),
                rollup_readonly_yn = 0,
                display_order = VALUES(display_order),
                active_yn = 1,
                delete_yn = 0,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                cycleId,
                companyId,
                row["metricId"],
                SCOPE_SOURCE_TYPE_MATERIAL_SUB_ISSUE,
                sourceMaterialityRunId,
                row["sourceSelectedSubIssueId"],
                row["sourceSubIssueCode"],
                row["approvalPolicyCode"],
                row["displayOrder"],
                actorUserId,
            ),
        )


def resolveScopeRunId(cycle: dict, sourceMaterialityRunId: Optional[int]) -> Optional[int]:
    if sourceMaterialityRunId is not None:
        return int(sourceMaterialityRunId)
    cycleRunId = cycle.get("source_materiality_run_id") if cycle else None
    return int(cycleRunId) if cycleRunId is not None else None


def seedPreDmaG0ScopeTx(
    cur,
    cycleId: int,
    companyId: int,
    sourceMaterialityRunId: Optional[int],
    actorUserId: Optional[int],
) -> None:
    metricRows = listPreDmaG0MetricMasterTx(cur)
    expectedMetricIds = set(PRE_DMA_G0_SCOPE_POLICIES.keys())
    actualMetricIds = {
        row["metric_id"]
        for row in metricRows
        if row.get("metric_id") in expectedMetricIds
    }
    missingMetricIds = sorted(expectedMetricIds - actualMetricIds)
    if missingMetricIds:
        raise RuntimeError(
            "PRE_DMA_G0 master metrics are missing: "
            + ", ".join(missingMetricIds)
        )
    metricIds = sorted(
        expectedMetricIds,
        key=lambda metricId: PRE_DMA_G0_SCOPE_POLICIES[metricId]["displayOrder"],
    )
    for metricId in metricIds:
        policy = PRE_DMA_G0_SCOPE_POLICIES[metricId]
        cur.execute(
            """
            INSERT INTO ESG_ONBOARDING_CYCLE_METRIC_SCOPE (
                esg_onboarding_cycle_id,
                company_id,
                metric_id,
                scope_source_type,
                source_materiality_run_id,
                source_selected_sub_issue_id,
                source_sub_issue_code,
                required_yn,
                input_required_yn,
                approval_required_yn,
                approval_policy_code,
                rollup_readonly_yn,
                display_order,
                active_yn,
                created_by_user_id,
                delete_yn
            ) VALUES (?, ?, ?, ?, ?, NULL, NULL, 1, 1, 1, ?, 0, ?, 1, ?, 0)
            ON DUPLICATE KEY UPDATE
                scope_source_type = VALUES(scope_source_type),
                source_materiality_run_id = COALESCE(VALUES(source_materiality_run_id), source_materiality_run_id),
                source_selected_sub_issue_id = NULL,
                source_sub_issue_code = NULL,
                required_yn = 1,
                input_required_yn = 1,
                approval_required_yn = 1,
                approval_policy_code = VALUES(approval_policy_code),
                rollup_readonly_yn = 0,
                display_order = VALUES(display_order),
                active_yn = 1,
                delete_yn = 0,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                cycleId,
                companyId,
                metricId,
                SCOPE_SOURCE_TYPE_PRE_DMA_G0,
                sourceMaterialityRunId,
                policy["approvalPolicyCode"],
                policy["displayOrder"],
                actorUserId,
            ),
        )


def listPreDmaG0MetricMasterTx(cur) -> list[dict]:
    cur.execute(
        """
        SELECT DISTINCT metric_id, metric_name_kr
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE delete_yn = 0
          AND active_yn = 1
          AND metric_id LIKE 'G0-%'
        ORDER BY metric_id
        """
    )
    return cur.fetchall() or []


def normalizeCycleTx(
    cur,
    cycle: dict,
    reportBasisType: Optional[str],
    sourceMaterialityRunId: Optional[int],
) -> None:
    updates = []
    params = []
    metricScopeCode = cycle.get("metric_scope_code")
    if metricScopeCode in (None, "", METRIC_SCOPE_G0_02_FINANCIAL_BASIS):
        updates.append("metric_scope_code = ?")
        params.append(METRIC_SCOPE_PRE_DMA_G0_PROFILE)
    if cycle.get("report_basis_type") is None and reportBasisType is not None:
        updates.append("report_basis_type = ?")
        params.append(reportBasisType)
    if cycle.get("source_materiality_run_id") is None and sourceMaterialityRunId is not None:
        updates.append("source_materiality_run_id = ?")
        params.append(sourceMaterialityRunId)
    if not updates:
        return
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(int(cycle["id"]))
    cur.execute(
        f"""
        UPDATE ESG_ONBOARDING_CYCLE
        SET {", ".join(updates)}
        WHERE id = ?
          AND delete_yn = 0
        """,
        tuple(params),
    )


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
            METRIC_SCOPE_PRE_DMA_G0_PROFILE,
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


def checkAlreadyApprovedTx(cur, rows: list[dict], companyId: int, reportingYear: int) -> bool:
    rowByAtomic = {row["atomic_metric_id"]: row for row in rows}
    if any(atomicId not in rowByAtomic for atomicId in REQUIRED_ATOMIC_IDS):
        return False
    if any(
        str(rowByAtomic[atomicId].get("input_status") or "").lower() != "approved"
        for atomicId in REQUIRED_ATOMIC_IDS
    ):
        return False
    placeholders = ", ".join(["?"] * len(REQUIRED_ATOMIC_IDS))
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
        (companyId, reportingYear, METRIC_ID_G0_02, *REQUIRED_ATOMIC_IDS),
    )
    row = cur.fetchone() or {}
    return int(row.get("approved_count") or 0) >= len(REQUIRED_ATOMIC_IDS)


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
