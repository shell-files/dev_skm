"""
onboardingscoperepository.py
레이어: Repository
역할: 온보딩 스코프 초기화·조회 — 사이클별 지표 목록 및 진행 상태 관리.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import mariadb

from src.utils.db import findAll, findOne, getConn
from src.utils.settings import settings
from src.repositories.companyutils import (
    getCompanyName,
    getCompanyNameFromCompanyTable,
    getCompanyTableInfo,
)


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

# 최근 입력 데이터 기준 보고 연도 조회 — 없으면 현재 연도 반환
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

# 기업·연도·유형 기준 온보딩 사이클 단건 조회 — 없으면 빈 dict
def getCycle(
    companyId: int,
    reportingYear: int,
    cycleType: str,
    batchId: Optional[int] = None,
    sourceMaterialityRunId: Optional[int] = None,
) -> dict:
    requireRollupResponseBatchId(cycleType, batchId)
    batchFilter = "AND parent_rollup_batch_id = ?" if batchId is not None else ""
    sourceRunFilter = "AND source_materiality_run_id = ?" if sourceMaterialityRunId is not None else ""
    params = [companyId, reportingYear, cycleType]
    if batchId is not None:
        params.append(batchId)
    if sourceMaterialityRunId is not None:
        params.append(sourceMaterialityRunId)
    return findOne(
        f"""
        SELECT *
        FROM ESG_ONBOARDING_CYCLE
        WHERE company_id = ?
          AND reporting_year = ?
          AND cycle_type = ?
          {batchFilter}
          {sourceRunFilter}
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        tuple(params),
    ) or {}

# 사이클·기업 기준 활성 지표 스코프 목록 조회 — 지표 ID 필터 지원
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

# 지표 ID 기준 활성 원자 지표 마스터 목록 조회
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

# G0 필수 컨텍스트 지표 마스터 목록 조회
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

# G0 지표 ID 목록 유효성 검증 — 미등록 ID 있으면 ValueError
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

# Pre-DMA G0 온보딩 사이클 생성 또는 조회 — 중복 키 충돌 시 재시도
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

# Post-DMA 공시 온보딩 사이클 생성 또는 조회 — 중복 키 충돌 시 재시도
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

# 기업·연도 기준 Pre-DMA G0 사이클 단건 조회 — 없으면 빈 dict
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

# G0 필수 컨텍스트 지표 마스터 목록 조회 래퍼
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

# 사이클·기업 기준 지표 스코프 목록 조회 래퍼
def listCycleMetricScope(cycleId: int, companyId: int) -> list[dict]:
    return listMetricScopes(cycleId, companyId)

# 사이클 스코프 지표 ID 목록 유효성 검증 — 미등록 ID 있으면 ValueError
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

# 사이클 유형별 WHERE 절 필터 문자열 생성 — 유효하지 않으면 항상 거짓 필터 반환
def cycleTypeFilter(cycleType: Optional[str]) -> str:
    if not cycleType:
        return ""
    normalizedCycleType = str(cycleType).strip().upper()
    if normalizedCycleType not in {CYCLE_TYPE_PRE_DMA_G0, CYCLE_TYPE_POST_DMA_DISCLOSURE, CYCLE_TYPE_ROLLUP, CYCLE_TYPE_ROLLUP_RESPONSE}:
        return "AND 1 = 0"
    return f"AND (c.cycle_type = '{normalizedCycleType}' OR c.id IS NULL)"

# 기업·연도·유형 기준 사이클 단건 조회 (트랜잭션 커서용)
def resolveCycle(
    cur,
    companyId: int,
    reportingYear: int,
    cycleType: str = CYCLE_TYPE_PRE_DMA_G0,
    batchId: Optional[int] = None,
    sourceMaterialityRunId: Optional[int] = None,
) -> dict:
    requireRollupResponseBatchId(cycleType, batchId)
    batchFilter = "AND parent_rollup_batch_id = ?" if batchId is not None else ""
    sourceRunFilter = "AND source_materiality_run_id = ?" if sourceMaterialityRunId is not None else ""
    params = [companyId, reportingYear, cycleType]
    if batchId is not None:
        params.append(batchId)
    if sourceMaterialityRunId is not None:
        params.append(sourceMaterialityRunId)
    cur.execute(
        f"""
        SELECT *
        FROM ESG_ONBOARDING_CYCLE
        WHERE company_id = ?
          AND reporting_year = ?
          AND cycle_type = ?
          {batchFilter}
          {sourceRunFilter}
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        tuple(params),
    )
    return cur.fetchone() or {}

# Pre-DMA G0 사이클 생성 또는 조회 및 스코프 시드 (트랜잭션 커서용)
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

# Post-DMA 공시 사이클 생성 또는 조회 및 스코프 시드 — 스코프 불일치 시 ValueError (트랜잭션 커서용)
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
    cycle = resolvePostDmaCycleTx(
        cur,
        companyId,
        reportingYear,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
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
    cycle = resolvePostDmaCycleTx(
        cur,
        companyId,
        reportingYear,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
    if not cycle:
        insertPostDmaCycleTx(
            cur,
            companyId=companyId,
            reportingYear=reportingYear,
            reportBasisType=reportBasisType,
            sourceMaterialityRunId=sourceMaterialityRunId,
            actorUserId=actorUserId,
        )
        cycle = resolvePostDmaCycleTx(
            cur,
            companyId,
            reportingYear,
            sourceMaterialityRunId=sourceMaterialityRunId,
        )
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
        cycle = resolvePostDmaCycleTx(
            cur,
            companyId,
            reportingYear,
            sourceMaterialityRunId=sourceMaterialityRunId,
        )
    cycle["_createdYn"] = False
    return cycle

def resolvePostDmaCycleTx(
    cur,
    companyId: int,
    reportingYear: int,
    sourceMaterialityRunId: Optional[int] = None,
) -> dict:
    sourceRunFilter = "AND source_materiality_run_id = ?" if sourceMaterialityRunId is not None else ""
    params = [companyId, reportingYear, CYCLE_TYPE_POST_DMA_DISCLOSURE]
    if sourceMaterialityRunId is not None:
        params.append(sourceMaterialityRunId)
    cur.execute(
        f"""
        SELECT *
        FROM ESG_ONBOARDING_CYCLE
        WHERE company_id = ?
          AND reporting_year = ?
          AND cycle_type = ?
          {sourceRunFilter}
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        tuple(params),
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

def listPromotableInputAtomicIdsTx(cur, metricId: str) -> list[str]:
    cur.execute(
        """
        SELECT atomic_metric_id
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE metric_id = ?
          AND onboarding_input_yn = 1
          AND active_yn = 1
          AND delete_yn = 0
          AND UPPER(COALESCE(atomic_data_role, '')) = 'INPUT'
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
    promotableAtomicIds = listPromotableInputAtomicIdsTx(cur, metricId)
    if not promotableAtomicIds:
        return APPROVAL_POLICY_INPUT_APPROVAL_ONLY
    if checkConsolidatedCalculationSourceTx(cur, promotableAtomicIds):
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
    "listPromotableInputAtomicIdsTx",
    "checkConsolidatedCalculationSourceTx",
    "resolveDefaultApprovalPolicyTx",
    "listMetricScopesTx",
    "ensureRollupCycleTx",
    "resolveRollupMetricScopeRowsTx",
    "seedRollupMetricScopeTx",
    "requireRollupResponseBatchId",
    "requireRollupResponseBatchContext",
]


# ── Rollup workspace 함수 re-export (onboardingworkspacerepository로 분리됨) ──
from src.repositories.onboardingworkspacerepository import (
    listMetricScopesTx,
    ensureRollupCycleTx,
    resolveRollupMetricScopeRowsTx,
    seedRollupMetricScopeTx,
    ensureRollupResponseWorkspaceTx,
    requireRollupResponseBatchId,
    requireRollupResponseBatchContext,
    requireWritableCycleTx,
)