"""
onboardingworkspacerepository.py
레이어: Repository
역할: 롤업 사이클 및 응답 워크스페이스 초기화·검증 — ROLLUP / ROLLUP_RESPONSE 전용 Tx 헬퍼.
"""
from __future__ import annotations
from typing import Optional

from src.utils.db import findAll, findOne, getConn
from src.repositories.onboardingscoperepository import (
    CYCLE_TYPE_ROLLUP_RESPONSE,
    METRIC_SCOPE_ROLLUP_RESPONSE,
    SCOPE_SOURCE_TYPE_PRE_DMA_G0,
    SCOPE_SOURCE_TYPE_ROLLUP_RESPONSE,
    APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP,
    APPROVAL_POLICY_INPUT_APPROVAL_ONLY,
    APPROVAL_POLICY_PROMOTE_TO_KPI_FACT,
)
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
        SELECT source_cycle_id, rollup_purpose_code
        FROM ESG_ROLLUP_BATCH 
        WHERE id = ? AND delete_yn = 0
        """,
        (batchId,)
    )
    batch = cur.fetchone()
    sourceCycleId = batch["source_cycle_id"] if batch else None
    rollupPurposeCode = batch["rollup_purpose_code"] if batch else None

    parentScopeByMetric = {}
    if sourceCycleId:
        cur.execute(
            """
            SELECT metric_id, scope_source_type, source_materiality_run_id, source_selected_sub_issue_id, source_sub_issue_code
            FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
            WHERE esg_onboarding_cycle_id = ? AND delete_yn = 0 AND active_yn = 1
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
          AND parent_rollup_batch_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (companyId, reportingYear, CYCLE_TYPE_ROLLUP_RESPONSE, batchId),
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
        # ROLLUP_RESPONSE cycle은 batch별 workspace이다.
        # 조회를 parent_rollup_batch_id로 한정했으므로 이 cycle은 이미 해당 batch 전용이다.
        # 따라서 다른 batch로의 재바인딩은 하지 않으며(batch19/batch20 분리 유지),
        # 재진입 시 scope만 비활성화한 뒤 아래에서 batch source 기준으로 재시드한다.
        cycleId = cycle["id"]
        cur.execute(
            """
            UPDATE ESG_ONBOARDING_CYCLE_METRIC_SCOPE
            SET active_yn = 0, updated_at = CURRENT_TIMESTAMP
            WHERE esg_onboarding_cycle_id = ?
            """,
            (cycleId,)
        )

    from src.repositories.rollupscoperepository import resolveExternalEntitySourceAtomicIdsByMetricTx
    for displayIndex, metricId in enumerate(actionableInputMetricIds, start=1):
        sourceAtomicIds = resolveExternalEntitySourceAtomicIdsByMetricTx(cur, batchId, metricId)
        if not sourceAtomicIds:
            raise ValueError(
                "ROLLUP_RESPONSE_MISSING_SOURCE_ATOMIC_IDS: "
                f"batchId={batchId}, metricId={metricId}"
            )
        approvalPolicy = APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP
        parentScope = parentScopeByMetric.get(metricId) or {}
        
        if rollupPurposeCode == "DMA_PRECHECK" and metricId == "G0-02":
            scopeSourceType = SCOPE_SOURCE_TYPE_PRE_DMA_G0
        else:
            scopeSourceType = parentScope.get("scope_source_type") or SCOPE_SOURCE_TYPE_ROLLUP_RESPONSE

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
                scopeSourceType,
                parentScope.get("source_materiality_run_id"),
                parentScope.get("source_selected_sub_issue_id"),
                parentScope.get("source_sub_issue_code"),
                approvalPolicy,
                displayIndex * 10,
                actorUserId
            )
        )


def requireRollupResponseBatchId(cycleType: str, batchId: Optional[int]) -> None:
    if (
        str(cycleType or "").strip().upper() == CYCLE_TYPE_ROLLUP_RESPONSE
        and batchId is None
    ):
        err = ValueError("batchId is required for ROLLUP_RESPONSE")
        err.statusCode = 409
        raise err


def requireRollupResponseBatchContext(cycle: dict, batchId: Optional[int]) -> None:
    cycleType = str(cycle.get("cycle_type") or "").strip().upper()
    requireRollupResponseBatchId(cycleType, batchId)
    if cycleType != CYCLE_TYPE_ROLLUP_RESPONSE:
        return

    if (
        cycle.get("parent_rollup_batch_id") is None
        or int(cycle["parent_rollup_batch_id"]) != int(batchId)
    ):
        err = ValueError("ROLLUP_RESPONSE batch context mismatch")
        err.statusCode = 409
        raise err


def requireWritableCycleTx(cur, cycle: dict, companyId: int, batchId: Optional[int] = None) -> None:
    requireRollupResponseBatchContext(cycle, batchId)
    if str(cycle.get("cycle_type") or "").strip().upper() != CYCLE_TYPE_ROLLUP_RESPONSE:
        return
    dbBatchId = cycle.get("parent_rollup_batch_id")
    if dbBatchId is None:
        return
    cur.execute(
        """
        SELECT transfer_status
        FROM ESG_ROLLUP_SOURCE_STATUS
        WHERE esg_rollup_batch_id = ?
          AND source_company_id = ?
          AND delete_yn = 0
        LIMIT 1
        FOR UPDATE
        """,
        (int(dbBatchId), companyId),
    )
    row = cur.fetchone()
    if row and str(row.get("transfer_status") or "").lower() in {"sent", "received"}:
        err = ValueError("ROLLUP_RESPONSE workspace is read-only after transfer.")
        err.statusCode = 409
        raise err
