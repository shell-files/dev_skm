from __future__ import annotations

from datetime import datetime
from typing import Optional

import mariadb

from src.utils.db import findAll, findOne, getConn
from src.utils.settings import settings


CYCLE_TYPE_PRE_DMA_G0 = "PRE_DMA_G0"
CYCLE_TYPE_POST_DMA_DISCLOSURE = "POST_DMA_DISCLOSURE"
CYCLE_TYPE_ROLLUP = "ROLLUP"
CYCLE_TYPE_ROLLUP_RESPONSE = "ROLLUP_RESPONSE"

METRIC_SCOPE_PRE_DMA_G0_PROFILE = "PRE_DMA_G0_PROFILE"
METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
METRIC_SCOPE_SELECTED_DISCLOSURE = "SELECTED_DISCLOSURE"
METRIC_SCOPE_ROLLUP = "ROLLUP_SCOPE"
METRIC_SCOPE_ROLLUP_RESPONSE = "ROLLUP_RESPONSE"

SCOPE_SOURCE_TYPE_PRE_DMA_G0 = "PRE_DMA_G0"
SCOPE_SOURCE_TYPE_MATERIAL_SUB_ISSUE = "MATERIAL_SUB_ISSUE"
SCOPE_SOURCE_TYPE_ROLLUP = "ROLLUP"
SCOPE_SOURCE_TYPE_ROLLUP_RESPONSE = "ROLLUP_RESPONSE"

MAP_SCOPE_MVP_SELECTED = "MVP_SELECTED"

APPROVAL_POLICY_INPUT_APPROVAL_ONLY = "INPUT_APPROVAL_ONLY"
APPROVAL_POLICY_PROMOTE_TO_KPI_FACT = "PROMOTE_TO_KPI_FACT"
APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP = "PROMOTE_TO_KPI_FACT_AND_ROLLUP"
APPROVAL_POLICY_ROLLUP_READONLY = "ROLLUP_READONLY"
APPROVAL_POLICY_NO_APPROVAL_REQUIRED = "NO_APPROVAL_REQUIRED"

METRIC_ID_G0_02 = "G0-02"
SUPPORTED_CYCLE_TYPE = CYCLE_TYPE_PRE_DMA_G0

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

def listG0MetricMaster() -> list[dict]:
    return findAll(
        """
        SELECT metric_id, metric_name_kr
        FROM ESG_METRIC_MASTER
        WHERE delete_yn = 0
          AND active_yn = 1
          AND mandatory_context_yn = 1
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
        SELECT metric_id, metric_name_kr
        FROM ESG_METRIC_MASTER
        WHERE delete_yn = 0
          AND active_yn = 1
          AND mandatory_context_yn = 1
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

def cycleTypeFilter(cycleType: Optional[str]) -> str:
    if not cycleType:
        return ""
    normalizedCycleType = str(cycleType).strip().upper()
    if normalizedCycleType not in {CYCLE_TYPE_PRE_DMA_G0, CYCLE_TYPE_POST_DMA_DISCLOSURE, CYCLE_TYPE_ROLLUP, CYCLE_TYPE_ROLLUP_RESPONSE}:
        return "AND 1 = 0"
    return f"AND (c.cycle_type = '{normalizedCycleType}' OR c.id IS NULL)"

def resolveCycle(cur, companyId: int, reportingYear: int, cycleType: str = CYCLE_TYPE_PRE_DMA_G0) -> dict:
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
        (companyId, reportingYear, cycleType),
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
    scopeRows = resolveCycleMetricScopeRowsTx(
        cur,
        cycleType=CYCLE_TYPE_POST_DMA_DISCLOSURE,
        companyId=companyId,
        reportingYear=reportingYear,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
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

    seedCycleMetricScopeTx(
        cur,
        cycleId=int(cycle["id"]),
        companyId=companyId,
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
    cur,
    selectedByCode: dict[str, dict],
    mappingRows: list[dict],
    sourceMaterialityRunId: int,
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
                "scopeSourceType": SCOPE_SOURCE_TYPE_MATERIAL_SUB_ISSUE,
                "sourceMaterialityRunId": sourceMaterialityRunId,
                "sourceSelectedSubIssueId": candidate["sourceSelectedSubIssueId"],
                "sourceSubIssueCode": candidate["sourceSubIssueCode"],
                "requiredYn": 1,
                "inputRequiredYn": 1,
                "approvalRequiredYn": 1,
                "displayOrder": displayIndex * 10,
                "approvalPolicyCode": resolvePostDmaApprovalPolicy(cur, metricId),
                "rollupReadonlyYn": 0,
            }
        )
    return scopeRows

def resolvePostDmaApprovalPolicy(cur, metricId: str) -> str:
    return resolveDefaultApprovalPolicyTx(cur, metricId)

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

def resolveCycleMetricScopeRowsTx(
    cur,
    *,
    cycleType: str,
    companyId: int,
    reportingYear: int,
    sourceMaterialityRunId: Optional[int] = None,
) -> list[dict]:
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType == CYCLE_TYPE_PRE_DMA_G0:
        return listPreDmaMetricScopeRowsTx(cur, sourceMaterialityRunId)
    if normalizedCycleType == CYCLE_TYPE_POST_DMA_DISCLOSURE:
        if sourceMaterialityRunId is None:
            raise ValueError("sourceMaterialityRunId is required")
        return listPostDmaMetricScopeRowsTx(cur, sourceMaterialityRunId)
    raise ValueError(f"Unsupported cycleType: {normalizedCycleType}")

def listPreDmaMetricScopeRowsTx(
    cur,
    sourceMaterialityRunId: Optional[int],
) -> list[dict]:
    metricRows = listPreDmaG0MetricMasterTx(cur)
    scopeRows = []
    for displayIndex, row in enumerate(metricRows, start=1):
        scopeRows.append(
            {
                "metricId": row["metric_id"],
                "scopeSourceType": SCOPE_SOURCE_TYPE_PRE_DMA_G0,
                "sourceMaterialityRunId": sourceMaterialityRunId,
                "sourceSelectedSubIssueId": None,
                "sourceSubIssueCode": None,
                "requiredYn": 1,
                "inputRequiredYn": 1,
                "approvalRequiredYn": 1,
                "approvalPolicyCode": resolveDefaultApprovalPolicyTx(cur, row["metric_id"]),
                "rollupReadonlyYn": 0,
                "displayOrder": displayIndex * 10,
            }
        )
    return scopeRows

def listPostDmaMetricScopeRowsTx(cur, sourceMaterialityRunId: int) -> list[dict]:
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
    return buildSelectedDisclosureScopeRows(
        cur,
        selectedByCode,
        mappingRows,
        sourceMaterialityRunId,
    )

def seedCycleMetricScopeTx(
    cur,
    cycleId: int,
    companyId: int,
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
            ON DUPLICATE KEY UPDATE
                scope_source_type = VALUES(scope_source_type),
                source_materiality_run_id = COALESCE(VALUES(source_materiality_run_id), source_materiality_run_id),
                source_selected_sub_issue_id = VALUES(source_selected_sub_issue_id),
                source_sub_issue_code = VALUES(source_sub_issue_code),
                required_yn = VALUES(required_yn),
                input_required_yn = VALUES(input_required_yn),
                approval_required_yn = VALUES(approval_required_yn),
                approval_policy_code = approval_policy_code,
                rollup_readonly_yn = rollup_readonly_yn,
                display_order = VALUES(display_order),
                active_yn = 1,
                delete_yn = 0,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                cycleId,
                companyId,
                row["metricId"],
                row["scopeSourceType"],
                row.get("sourceMaterialityRunId"),
                row.get("sourceSelectedSubIssueId"),
                row.get("sourceSubIssueCode"),
                int(row.get("requiredYn") if row.get("requiredYn") is not None else 1),
                int(row.get("inputRequiredYn") if row.get("inputRequiredYn") is not None else 1),
                int(row.get("approvalRequiredYn") if row.get("approvalRequiredYn") is not None else 1),
                row.get("approvalPolicyCode") or APPROVAL_POLICY_INPUT_APPROVAL_ONLY,
                int(row.get("rollupReadonlyYn") or 0),
                int(row.get("displayOrder") or 0),
                actorUserId,
            ),
        )

def seedSelectedDisclosureScopeTx(
    cur,
    cycleId: int,
    companyId: int,
    sourceMaterialityRunId: int,
    scopeRows: list[dict],
    actorUserId: Optional[int],
) -> None:
    seedCycleMetricScopeTx(
        cur,
        cycleId=cycleId,
        companyId=companyId,
        scopeRows=[
            {
                **row,
                "sourceMaterialityRunId": row.get("sourceMaterialityRunId") or sourceMaterialityRunId,
                "scopeSourceType": row.get("scopeSourceType") or SCOPE_SOURCE_TYPE_MATERIAL_SUB_ISSUE,
            }
            for row in scopeRows
        ],
        actorUserId=actorUserId,
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
    scopeRows = resolveCycleMetricScopeRowsTx(
        cur,
        cycleType=CYCLE_TYPE_PRE_DMA_G0,
        companyId=companyId,
        reportingYear=0,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
    if not scopeRows:
        raise RuntimeError("PRE_DMA_G0 mandatory context metrics are missing")
    seedCycleMetricScopeTx(
        cur,
        cycleId=cycleId,
        companyId=companyId,
        scopeRows=scopeRows,
        actorUserId=actorUserId,
    )

def listPreDmaG0MetricMasterTx(cur) -> list[dict]:
    cur.execute(
        """
        SELECT metric_id, metric_name_kr
        FROM ESG_METRIC_MASTER
        WHERE delete_yn = 0
          AND active_yn = 1
          AND mandatory_context_yn = 1
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

def listQuantInputAtomicIdsTx(cur, metricId: str) -> list[str]:
    cur.execute(
        """
        SELECT atomic_metric_id
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE metric_id = ?
          AND onboarding_input_yn = 1
          AND active_yn = 1
          AND delete_yn = 0
          AND UPPER(COALESCE(atomic_data_role, '')) = 'INPUT'
          AND (
              UPPER(COALESCE(data_value_type, '')) IN ('QUANT', 'NUMBER', 'NUMERIC')
              OR data_value_type = '?뺣웾'
          )
        ORDER BY atomic_metric_id
        """,
        (metricId,),
    )
    rows = cur.fetchall() or []
    return [row["atomic_metric_id"] for row in rows if row.get("atomic_metric_id")]


def checkConsolidatedCalculationSourceTx(cur, atomicMetricIds: list[str]) -> bool:
    if not atomicMetricIds:
        return False
    placeholders = ", ".join(["?"] * len(atomicMetricIds))
    cur.execute(
        f"""
        SELECT COUNT(*) AS source_count
        FROM ESG_CALCULATION_RULE cr
        JOIN ESG_CALCULATION_RULE_SOURCE src
          ON src.calculation_rule_code = cr.calculation_rule_code
         AND src.delete_yn = 0
        WHERE cr.delete_yn = 0
          AND cr.active_yn = 1
          AND UPPER(COALESCE(cr.execution_scope, '')) = 'CONSOLIDATED'
          AND src.source_atomic_metric_id IN ({placeholders})
        """,
        tuple(atomicMetricIds),
    )
    row = cur.fetchone() or {}
    return int(row.get("source_count") or 0) > 0


def resolveDefaultApprovalPolicyTx(cur, metricId: str) -> str:
    quantAtomicIds = listQuantInputAtomicIdsTx(cur, metricId)
    if not quantAtomicIds:
        return APPROVAL_POLICY_INPUT_APPROVAL_ONLY
    if checkConsolidatedCalculationSourceTx(cur, quantAtomicIds):
        return APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP
    return APPROVAL_POLICY_PROMOTE_TO_KPI_FACT

__all__ = [
    "CYCLE_TYPE_PRE_DMA_G0",
    "CYCLE_TYPE_POST_DMA_DISCLOSURE",
    "CYCLE_TYPE_ROLLUP",
    "CYCLE_TYPE_ROLLUP_RESPONSE",
    "METRIC_SCOPE_PRE_DMA_G0_PROFILE",
    "METRIC_SCOPE_G0_02_FINANCIAL_BASIS",
    "METRIC_SCOPE_SELECTED_DISCLOSURE",
    "METRIC_SCOPE_ROLLUP",
    "METRIC_SCOPE_ROLLUP_RESPONSE",
    "SCOPE_SOURCE_TYPE_PRE_DMA_G0",
    "SCOPE_SOURCE_TYPE_MATERIAL_SUB_ISSUE",
    "SCOPE_SOURCE_TYPE_ROLLUP",
    "SCOPE_SOURCE_TYPE_ROLLUP_RESPONSE",
    "MAP_SCOPE_MVP_SELECTED",
    "APPROVAL_POLICY_INPUT_APPROVAL_ONLY",
    "APPROVAL_POLICY_PROMOTE_TO_KPI_FACT",
    "APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP",
    "APPROVAL_POLICY_ROLLUP_READONLY",
    "APPROVAL_POLICY_NO_APPROVAL_REQUIRED",
    "METRIC_ID_G0_02",
    "SUPPORTED_CYCLE_TYPE",
    "ensureRollupResponseWorkspaceTx",
    "resolveReportingYear",
    "getCycle",
    "listMetricScopes",
    "listAtomicMaster",
    "listG0MetricMaster",
    "validateG0MetricIds",
    "getCompanyName",
    "getCompanyNameFromCompanyTable",
    "getCompanyTableInfo",
    "ensurePreDmaG0Cycle",
    "ensurePostDmaDisclosureCycle",
    "resolvePreDmaG0Cycle",
    "listPreDmaG0MetricMaster",
    "listCycleMetricScope",
    "validateCycleMetricIds",
    "cycleTypeFilter",
    "resolveCycle",
    "ensureCycleTx",
    "ensurePostDmaDisclosureCycleTx",
    "listSelectedSubIssueRowsTx",
    "listSelectedDisclosureMappingRowsTx",
    "buildSelectedDisclosureScopeRows",
    "resolvePostDmaApprovalPolicy",
    "ensurePostDmaCycleTx",
    "resolvePostDmaCycleTx",
    "insertPostDmaCycleTx",
    "listMetricScopesTx",
    "resolveCycleMetricScopeRowsTx",
    "listPreDmaMetricScopeRowsTx",
    "listPostDmaMetricScopeRowsTx",
    "seedCycleMetricScopeTx",
    "seedSelectedDisclosureScopeTx",
    "resolveScopeRunId",
    "seedPreDmaG0ScopeTx",
    "listPreDmaG0MetricMasterTx",
    "normalizeCycleTx",
    "insertCycle",
    "listQuantInputAtomicIdsTx",
    "checkConsolidatedCalculationSourceTx",
    "resolveDefaultApprovalPolicyTx",
    "listMetricScopesTx",
    "ensureRollupCycleTx",
    "resolveRollupMetricScopeRowsTx",
    "seedRollupMetricScopeTx",
]

def listMetricScopesTx(cur, cycleId: int, companyId: int, metricId: Optional[str] = None) -> list[dict]:
    params = [cycleId, companyId]
    metricFilter = ""
    if metricId:
        metricFilter = "AND s.metric_id = ?"
        params.append(metricId)
    cur.execute(
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
    )
    return cur.fetchall() or []

def ensureRollupCycleTx(cur, companyId: int, reportingYear: int, batchId: int) -> int:
    cur.execute(
        """
        SELECT id FROM ESG_ONBOARDING_CYCLE
        WHERE company_id = ? AND reporting_year = ? AND cycle_type = 'ROLLUP' AND delete_yn = 0
        """,
        (companyId, reportingYear)
    )
    cycle = cur.fetchone()
    if cycle:
        cur.execute(
            """
            UPDATE ESG_ONBOARDING_CYCLE
            SET parent_rollup_batch_id = ?,
                metric_scope_code = 'ROLLUP_SCOPE',
                cycle_status = 'approved',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (batchId, cycle["id"])
        )
        return int(cycle["id"])
    else:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%y%m%d%H%M")
        cycleName = f"ROLLUP_{reportingYear}_{ts}"
        cur.execute(
            """
            INSERT INTO ESG_ONBOARDING_CYCLE (
                cycle_type, company_id, reporting_year, cycle_name, cycle_status,
                parent_rollup_batch_id, metric_scope_code, delete_yn, created_at, updated_at
            ) VALUES ('ROLLUP', ?, ?, ?, 'approved', ?, 'ROLLUP_SCOPE', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (companyId, reportingYear, cycleName, batchId)
        )
        return cur.lastrowid

def resolveRollupMetricScopeRowsTx(cur, batchId: int) -> list[dict]:
    cur.execute(
        """
        SELECT metric_id
        FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE
        WHERE esg_rollup_batch_id = ? AND delete_yn = 0
        GROUP BY metric_id
        ORDER BY metric_id
        """,
        (batchId,)
    )
    return cur.fetchall() or []

def seedRollupMetricScopeTx(cur, companyId: int, reportingYear: int, actorUserId: Optional[int] = None) -> None:
    cur.execute(
        """
        SELECT id, parent_rollup_batch_id FROM ESG_ONBOARDING_CYCLE
        WHERE company_id = ? AND reporting_year = ? AND cycle_type = 'ROLLUP' AND delete_yn = 0
        """,
        (companyId, reportingYear)
    )
    cycle = cur.fetchone()
    if not cycle or not cycle["parent_rollup_batch_id"]:
        return

    cycleId = cycle["id"]
    batchId = cycle["parent_rollup_batch_id"]

    metrics = resolveRollupMetricScopeRowsTx(cur, batchId)

    for displayIndex, m in enumerate(metrics, start=1):
        metricId = m["metric_id"]
        cur.execute(
            """
            INSERT INTO ESG_ONBOARDING_CYCLE_METRIC_SCOPE (
                esg_onboarding_cycle_id,
                company_id,
                metric_id,
                scope_source_type,
                required_yn,
                input_required_yn,
                approval_required_yn,
                approval_policy_code,
                rollup_readonly_yn,
                display_order,
                active_yn,
                created_by_user_id,
                delete_yn
            ) VALUES (?, ?, ?, 'ROLLUP', 1, 0, 0, 'ROLLUP_READONLY', 1, ?, 1, ?, 0)
            ON DUPLICATE KEY UPDATE
                scope_source_type = VALUES(scope_source_type),
                required_yn = VALUES(required_yn),
                input_required_yn = VALUES(input_required_yn),
                approval_required_yn = VALUES(approval_required_yn),
                approval_policy_code = VALUES(approval_policy_code),
                rollup_readonly_yn = VALUES(rollup_readonly_yn),
                display_order = VALUES(display_order),
                active_yn = VALUES(active_yn),
                updated_at = CURRENT_TIMESTAMP
            """,
            (cycleId, companyId, metricId, displayIndex * 10, actorUserId)
        )

def ensureRollupResponseWorkspaceTx(
    cur,
    companyId: int,
    reportingYear: int,
    batchId: int,
    actionableInputMetricIds: list[str],
    actorUserId: Optional[int] = None,
) -> None:
    cur.execute(
        """
        SELECT source_cycle_id 
        FROM ESG_ROLLUP_BATCH 
        WHERE id = ? AND delete_yn = 0
        """,
        (batchId,)
    )
    batch = cur.fetchone()
    sourceCycleId = batch["source_cycle_id"] if batch else None

    parentScopeByMetric = {}
    if sourceCycleId:
        cur.execute(
            """
            SELECT metric_id, scope_source_type, source_materiality_run_id, source_selected_sub_issue_id, source_sub_issue_code
            FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
            WHERE esg_onboarding_cycle_id = ? AND delete_yn = 0
            """,
            (sourceCycleId,)
        )
        for row in cur.fetchall():
            parentScopeByMetric[row["metric_id"]] = row

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
        (companyId, reportingYear, CYCLE_TYPE_ROLLUP_RESPONSE),
    )
    cycle = cur.fetchone()
    if not cycle:
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
                metric_scope_code,
                parent_rollup_batch_id,
                created_by_user_id
            ) VALUES (?, ?, ?, ?, 'ENTITY', 0, 'active', ?, ?, ?)
            """,
            (
                companyId,
                reportingYear,
                f"Rollup Response {reportingYear}",
                CYCLE_TYPE_ROLLUP_RESPONSE,
                METRIC_SCOPE_ROLLUP_RESPONSE,
                batchId,
                actorUserId,
            ),
        )
        cycleId = cur.lastrowid
    else:
        cycleId = cycle["id"]
        cur.execute(
            """
            UPDATE ESG_ONBOARDING_CYCLE
            SET parent_rollup_batch_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (batchId, cycleId)
        )
        cur.execute(
            """
            UPDATE ESG_ONBOARDING_CYCLE_METRIC_SCOPE
            SET active_yn = 0, updated_at = CURRENT_TIMESTAMP
            WHERE esg_onboarding_cycle_id = ?
            """,
            (cycleId,)
        )

    for displayIndex, metricId in enumerate(actionableInputMetricIds, start=1):
        approvalPolicy = resolveDefaultApprovalPolicyTx(cur, metricId)
        parentScope = parentScopeByMetric.get(metricId) or {}
        
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
                required_yn = VALUES(required_yn),
                input_required_yn = VALUES(input_required_yn),
                approval_required_yn = VALUES(approval_required_yn),
                approval_policy_code = VALUES(approval_policy_code),
                rollup_readonly_yn = VALUES(rollup_readonly_yn),
                display_order = VALUES(display_order),
                active_yn = VALUES(active_yn),
                updated_at = CURRENT_TIMESTAMP

            """,
            (
                cycleId, 
                companyId, 
                metricId, 
                parentScope.get("scope_source_type") or SCOPE_SOURCE_TYPE_ROLLUP_RESPONSE,
                parentScope.get("source_materiality_run_id"),
                parentScope.get("source_selected_sub_issue_id"),
                parentScope.get("source_sub_issue_code"),
                approvalPolicy,
                displayIndex * 10,
                actorUserId
            )
        )
