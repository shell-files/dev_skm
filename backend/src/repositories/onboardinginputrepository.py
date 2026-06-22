"""
onboardinginputrepository.py
레이어: Repository
역할: 온보딩 지표 입력값 DB 조회·저장·업데이트.
"""
from __future__ import annotations

from typing import Optional

from src.utils.db import findAll, findOne, getConn
from src.repositories.onboardingscoperepository import METRIC_ID_G0_02
from src.utils.typeutils import (
    safeFloat,
    safeInt,
    formatDatetime,
    truthy,
    firstNonNull,
    groupRows,
    normalizeIssueDomain,
)


# 지표 입력값 행 목록 조회 (온보딩·KPI·롤업 UNION)
def listValueRows(
    companyId: int,
    reportingYear: int,
    metricIds: list[str],
    includeGroupRollupResultYn: bool = True,
) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    
    baseQuery = f"""
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
    """
    
    params = [
        companyId,
        reportingYear,
        *metricIds,
        companyId,
        reportingYear,
        *metricIds,
    ]
    
    if includeGroupRollupResultYn:
        baseQuery += f"""
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
        """
        params.extend([
            companyId,
            reportingYear,
            *metricIds,
        ])
        
    return findAll(baseQuery, tuple(params)) or []

# 사이클·기업·지표 기준 배정 ID 조회 — 없으면 None
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

# 지표 입력값 upsert 저장 (트랜잭션 래퍼)
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

# 다중 지표 그룹 입력값 일괄 upsert — 실패 시 전체 롤백
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
                savedCount += upsertMetricInputValuesTx(
                    cur,
                    cycleId=group["cycleId"],
                    companyId=group["companyId"],
                    reportingYear=group["reportingYear"],
                    metricId=group["metricId"],
                    assignmentId=group.get("assignmentId"),
                    values=group["values"],
                    userId=group.get("userId"),
                )
        conn.commit()
        return savedCount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# 지표 입력값 upsert — 기존 행 UPDATE, 없으면 INSERT; 승인 Fact 무효화 포함 (트랜잭션 커서용)
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

# 입력값 변경 시 연결 KPI Fact 소프트 삭제 무효화 (트랜잭션 커서용)
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


# invalidateMetricKpiFactsTx G0-02 래퍼
def invalidateG002KpiFactTx(cur, companyId: int, reportingYear: int, metricId: str, atomicMetricId: str) -> None:
    invalidateMetricKpiFactsTx(cur, companyId, reportingYear, metricId, atomicMetricId)

# 지표 기준 온보딩 입력값 행 목록 조회 — 필수 원자 지표만 조회
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

# G0-02 지표 온보딩 입력값 목록 조회 래퍼
def listG002Inputs(companyId: int, reportingYear: int) -> list[dict]:
    return listMetricInputs(companyId, reportingYear, METRIC_ID_G0_02)

# 지표 기준 온보딩 연결 승인 KPI Fact 행 목록 조회
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

# G0-02 지표 KPI Fact 목록 조회 래퍼
def listG002KpiFacts(companyId: int, reportingYear: int) -> list[dict]:
    return listMetricKpiFacts(companyId, reportingYear, METRIC_ID_G0_02)

# 지표 ID 기준 한국어 지표명 조회 — 없으면 None
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

# 지표 필수 온보딩 원자 지표 ID 목록 조회
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

# 필수 온보딩 원자 지표 ID 목록 조회 (트랜잭션 커서용)
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

# 결재 필요 원자 지표 ID 목록 조회 (DERIVED/ROLLUP_READONLY 제외)
def listRequiredApprovalAtomicIds(metricId: str) -> list[str]:
    rows = findAll(
        """
        SELECT atomic_metric_id
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE metric_id = ?
          AND onboarding_input_yn = 1
          AND active_yn = 1
          AND delete_yn = 0
          AND UPPER(COALESCE(atomic_data_role, '')) NOT IN ('DERIVED', 'ROLLUP_READONLY')
        ORDER BY atomic_metric_id
        """,
        (metricId,),
    ) or []
    return [row["atomic_metric_id"] for row in rows if row.get("atomic_metric_id")]

# 결재 필요 원자 지표 ID 목록 조회 (트랜잭션 커서용)
def listRequiredApprovalAtomicIdsTx(cur, metricId: str) -> list[str]:
    cur.execute(
        """
        SELECT atomic_metric_id
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE metric_id = ?
          AND onboarding_input_yn = 1
          AND active_yn = 1
          AND delete_yn = 0
          AND UPPER(COALESCE(atomic_data_role, '')) NOT IN ('DERIVED', 'ROLLUP_READONLY')
        ORDER BY atomic_metric_id
        """,
        (metricId,),
    )
    rows = cur.fetchall() or []
    return [row["atomic_metric_id"] for row in rows if row.get("atomic_metric_id")]

# 지표 원자별 입력값 행 FOR UPDATE 잠금 조회 (트랜잭션 커서용)
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

# 입력값 완전성·값 존재·허용 상태 유효성 검증 — 실패 시 ValueError
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

# 이미 승인 완료 여부 확인 — KPI Fact 승격까지 검증 (트랜잭션 커서용)
def checkAlreadyApprovedTx(
    cur,
    rows: list[dict],
    companyId: int,
    reportingYear: int,
    metricId: str,
    requiredAtomicIds: list[str],
    expectedPromotedAtomicIds: Optional[list[str]] = None,
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
    promotedAtomicIds = expectedPromotedAtomicIds or []
    if not promotedAtomicIds:
        return True
    placeholders = ", ".join(["?"] * len(promotedAtomicIds))
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
          AND (
              k.value_numeric IS NOT NULL
              OR TRIM(COALESCE(k.value_text, '')) <> ''
          )
          AND k.delete_yn = 0
        """,
        (companyId, reportingYear, metricId, *promotedAtomicIds),
    )
    row = cur.fetchone() or {}
    return int(row.get("approved_count") or 0) >= len(promotedAtomicIds)

# 온보딩 입력값 → KPI Fact upsert (트랜잭션 커서용)
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

# 입력·Fact 기준 결재 상태 문자열 결정
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

# 가장 최근 제출 시각 반환 — 이력 우선, 없으면 입력값 updated_at 사용
def submittedAt(inputs: list[dict], latestHistory: dict):
    if str(latestHistory.get("action_status") or "").lower() == "submitted":
        return latestHistory.get("created_at")
    submittedRows = [
        row.get("updated_at")
        for row in inputs
        if str(row.get("input_status") or "").lower() in {"submitted", "reviewed", "approved"}
    ]
    return max(submittedRows) if submittedRows else None

# 가장 최근 승인 시각 반환 — 이력 우선, 없으면 입력·Fact approved_at 최댓값
def approvedAt(inputs: list[dict], facts: list[dict], latestHistory: dict):
    if str(latestHistory.get("action_status") or "").lower() == "approved":
        return latestHistory.get("created_at")
    approvedValues = [row.get("approved_at") for row in inputs if row.get("approved_at")]
    approvedValues.extend([row.get("approved_at") for row in facts if row.get("approved_at")])
    return max(approvedValues) if approvedValues else None

# 입력 행에 값(숫자 또는 비어 있지 않은 텍스트) 존재 여부 확인
def hasMetricValue(row: dict) -> bool:
    if row.get("value_numeric") is not None:
        return True
    return str(row.get("value_text") or "").strip() != ""

# KPI Fact 승격 가능한 INPUT 역할 원자 행 목록 조회 (트랜잭션 커서용)
def listPromotableInputAtomicRowsTx(cur, metricId: str) -> list[dict]:
    cur.execute(
        """
        SELECT atomic_metric_id, data_value_type, atomic_data_role
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
    return cur.fetchall() or []


# KPI Fact 승격 가능한 원자 ID 목록 조회 (트랜잭션 커서용)
def listPromotableInputAtomicIdsTx(cur, metricId: str) -> list[str]:
    return [row["atomic_metric_id"] for row in listPromotableInputAtomicRowsTx(cur, metricId) if row.get("atomic_metric_id")]


# KPI Fact 승격 가능한 원자 ID 목록 조회
def listPromotableInputAtomicIds(metricId: str) -> list[str]:
    rows = findAll(
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
    ) or []
    return [row["atomic_metric_id"] for row in rows if row.get("atomic_metric_id")]


# 사이클·기업·지표 기준 배정 행 단건 조회 (트랜잭션 커서용)
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

__all__ = [
    "listValueRows",
    "resolveAssignmentId",
    "upsertMetricInputValues",
    "upsertMetricValueGroups",
    "upsertMetricInputValuesTx",
    "invalidateMetricKpiFactsTx",
    "invalidateG002KpiFactTx",
    "listMetricInputs",
    "listG002Inputs",
    "listMetricKpiFacts",
    "listG002KpiFacts",
    "getMetricName",
    "listRequiredAtomicIds",
    "listRequiredAtomicIdsTx",
    "listRequiredApprovalAtomicIds",
    "listRequiredApprovalAtomicIdsTx",
    "selectInputRowsForUpdate",
    "validateCompleteRows",
    "checkAlreadyApprovedTx",
    "upsertKpiFact",
    "resolveApprovalStatus",
    "submittedAt",
    "approvedAt",
    "firstNonNull",
    "formatDatetime",
    "hasMetricValue",
    "truthy",
    "groupRows",
    "normalizeIssueDomain",
    "listPromotableInputAtomicRowsTx",
    "listPromotableInputAtomicIdsTx",
    "listPromotableInputAtomicIds",
    "resolveAssignment",
]
