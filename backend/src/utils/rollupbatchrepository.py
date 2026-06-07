import json
from decimal import Decimal
from typing import Any, Optional
from src.utils.db import findAll, findOne

BATCH_STATUS_PENDING = "pending"
BATCH_STATUS_COMPLETED = "completed"

def _jsonDefault(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

def _jsonDumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_jsonDefault)

def getActiveBatch(runId: Optional[int], sourceCycleId: Optional[int], rollupPurposeCode: str, metricScopeCode: str) -> dict:
    sql = """
        SELECT
            b.*
        FROM ESG_ROLLUP_BATCH b
        WHERE b.delete_yn = 0
          AND b.rollup_purpose_code = ?
          AND b.metric_scope_code = ?
          AND LOWER(COALESCE(b.batch_status, '')) NOT IN ('deleted', 'cancelled', 'canceled', 'archived')
    """
    params = [rollupPurposeCode, metricScopeCode]
    if runId is not None:
        sql += " AND b.id IN (SELECT required_rollup_batch_id FROM ESG_MATERIALITY_RUN WHERE id = ? AND delete_yn = 0) "
        params.append(runId)
    if sourceCycleId is not None:
        sql += " AND b.source_cycle_id = ? "
        params.append(sourceCycleId)

    sql += " ORDER BY b.id DESC LIMIT 1 "
    return findOne(sql, tuple(params)) or {}

def getBatch(batchId: int) -> dict:
    sql = """
        SELECT
            b.*
        FROM ESG_ROLLUP_BATCH b
        WHERE b.id = ?
          AND b.delete_yn = 0
    """
    return findOne(sql, (batchId,)) or {}

def listRequests(
    sourceCompanyId: int,
    rollupPurposeCode: str,
    metricScopeCode: str,
    includeSentYn: bool = True,
    transferStatus: Optional[str] = None,
) -> list[dict]:
    transferFilter = ""
    requestFilter = ""
    params = [sourceCompanyId, rollupPurposeCode, metricScopeCode]
    normalizedTransferStatus = str(transferStatus or "").strip().lower()
    if normalizedTransferStatus:
        transferFilter = "AND LOWER(COALESCE(s.transfer_status, '')) = ?"
        params.append(normalizedTransferStatus)
    elif not includeSentYn:
        requestFilter = "AND s.request_status = 'requested'"
        transferFilter = "AND s.transfer_status = 'not_sent'"
    sql = """
        SELECT
            s.esg_rollup_batch_id AS batchId,
            b.rollup_batch_code AS batchCode,
            b.source_cycle_id AS sourceCycleId,
            s.parent_company_id AS parentCompanyId,
            p.company_code AS parentCompanyCode,
            COALESCE(p.company_code, CAST(s.parent_company_id AS CHAR)) AS parentCompanyName,
            s.source_company_id AS sourceCompanyId,
            s.reporting_year AS reportingYear,
            s.rollup_purpose_code AS rollupPurposeCode,
            s.metric_scope_code AS metricScopeCode,
            s.request_status AS requestStatus,
            s.input_status AS inputStatus,
            s.approval_status AS approvalStatus,
            s.transfer_status AS transferStatus
        FROM ESG_ROLLUP_SOURCE_STATUS s
        JOIN ESG_ROLLUP_BATCH b
          ON b.id = s.esg_rollup_batch_id
         AND b.delete_yn = 0
        LEFT JOIN ESG_COMPANY_PROFILE p
          ON p.company_id = s.parent_company_id
         AND p.delete_yn = 0
        WHERE s.source_company_id = ?
          AND s.source_company_id <> s.parent_company_id
          AND s.delete_yn = 0
          AND b.rollup_purpose_code = ?
          AND b.metric_scope_code = ?
          {requestFilter}
          {transferFilter}
          AND LOWER(COALESCE(b.batch_status, '')) NOT IN (
              'deleted',
              'cancelled',
              'canceled',
              'archived'
          )
        ORDER BY s.updated_at DESC, s.id DESC
    """.format(requestFilter=requestFilter, transferFilter=transferFilter)
    return findAll(sql, tuple(params)) or []

def getSource(batchId: int, sourceCompanyId: int) -> dict:
    sql = """
        SELECT
            s.*
        FROM ESG_ROLLUP_SOURCE_STATUS s
        WHERE s.esg_rollup_batch_id = ?
          AND s.source_company_id = ?
          AND s.delete_yn = 0
        LIMIT 1
    """
    return findOne(sql, (batchId, sourceCompanyId)) or {}

def listSources(batchId: int) -> list[dict]:
    sql = """
        SELECT s.*
        FROM ESG_ROLLUP_SOURCE_STATUS s
        WHERE s.esg_rollup_batch_id = ?
          AND s.delete_yn = 0
        ORDER BY s.source_company_id
    """
    return findAll(sql, (batchId,)) or []

def listSourceDetails(batchId: int) -> list[dict]:
    sql = """
        SELECT
            s.*,
            p.company_code AS sourceCompanyCode,
            COALESCE(p.company_code, CAST(s.source_company_id AS CHAR)) AS sourceCompanyName
        FROM ESG_ROLLUP_SOURCE_STATUS s
        LEFT JOIN ESG_COMPANY_PROFILE p
          ON p.company_id = s.source_company_id
         AND p.delete_yn = 0
        WHERE s.esg_rollup_batch_id = ?
          AND s.delete_yn = 0
        ORDER BY s.source_company_id
    """
    return findAll(sql, (batchId,)) or []

def getCompanyProfile(companyId: int) -> dict:
    sql = """
        SELECT
            company_id AS companyId,
            company_code AS companyCode,
            COALESCE(company_code, CAST(company_id AS CHAR)) AS companyName
        FROM ESG_COMPANY_PROFILE
        WHERE company_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
    """
    return findOne(sql, (companyId,)) or {
        "companyId": companyId,
        "companyCode": None,
        "companyName": str(companyId),
    }

def findActiveInputWorkspace(companyId: int, reportingYear: int, requestedMetricIds: list[str]) -> dict:
    metricIds = [
        str(metricId or "").strip()
        for metricId in requestedMetricIds or []
        if str(metricId or "").strip()
    ]
    if not metricIds:
        return {}
    placeholders = ", ".join(["?"] * len(metricIds))
    sql = f"""
        SELECT
            c.id AS cycleId,
            c.cycle_type AS cycleType,
            c.reporting_year AS reportingYear,
            COUNT(DISTINCT s.metric_id) AS matchedMetricCount
        FROM ESG_ONBOARDING_CYCLE c
        JOIN ESG_ONBOARDING_CYCLE_METRIC_SCOPE s
          ON s.esg_onboarding_cycle_id = c.id
         AND s.company_id = c.company_id
         AND s.metric_id IN ({placeholders})
         AND s.active_yn = 1
         AND s.delete_yn = 0
        WHERE c.company_id = ?
          AND c.reporting_year = ?
          AND c.cycle_status = 'active'
          AND c.cycle_type IN ('POST_DMA_DISCLOSURE', 'PRE_DMA_G0')
          AND c.delete_yn = 0
        GROUP BY c.id, c.cycle_type, c.reporting_year
        HAVING matchedMetricCount = ?
        ORDER BY
            CASE c.cycle_type
                WHEN 'POST_DMA_DISCLOSURE' THEN 1
                WHEN 'PRE_DMA_G0' THEN 2
                ELSE 3
            END,
            c.id DESC
        LIMIT 1
    """
    return findOne(sql, (*metricIds, companyId, reportingYear, len(metricIds))) or {}

def listSourceCompanyIds(batchId: int) -> list[int]:
    return [int(row["source_company_id"]) for row in listSources(batchId)]

def buildBatchCode(companyId: int, reportingYear: int, rollupPurposeCode: str) -> str:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%y%m%d%H%M")
    prefix = "RD" if rollupPurposeCode == "REPORT_DISCLOSURE" else "RB"
    return f"{prefix}-{reportingYear}-{companyId}-{ts}"

def saveBatchTx(
    cur,
    parentCompanyId: int,
    reportingYear: int,
    includedCompanyIds: list[int],
    rollupPurposeCode: str,
    metricScopeCode: str,
    sourceCycleId: Optional[int] = None,
    actorUserId: Optional[int] = None,
) -> int:
    batchCode = buildBatchCode(parentCompanyId, reportingYear, rollupPurposeCode)

    cur.execute(
        """
        INSERT INTO ESG_ROLLUP_BATCH (
            rollup_batch_code,
            parent_company_id,
            reporting_year,
            source_cycle_id,
            report_scope_type,
            included_company_ids_json,
            batch_status,
            rollup_purpose_code,
            metric_scope_code,
            dma_ready_yn,
            report_ready_yn,
            requested_by_user_id
        ) VALUES (?, ?, ?, ?, 'CONSOLIDATED', ?, ?, ?, ?, 0, 0, ?)
        """,
        (
            batchCode,
            parentCompanyId,
            reportingYear,
            sourceCycleId,
            json.dumps(includedCompanyIds),
            BATCH_STATUS_PENDING,
            rollupPurposeCode,
            metricScopeCode,
            actorUserId,
        ),
    )
    return int(cur.lastrowid)

def saveSourcesTx(
    cur,
    batchId: int,
    sourceStatuses: list[dict],
    rollupPurposeCode: str,
    metricScopeCode: str,
    requiredAtomicCount: int
) -> None:
    sql = """
        INSERT INTO ESG_ROLLUP_SOURCE_STATUS (
            esg_rollup_batch_id,
            parent_company_id,
            source_company_id,
            reporting_year,
            rollup_purpose_code,
            metric_scope_code,
            request_status,
            input_status,
            approval_status,
            transfer_status,
            required_atomic_count,
            approved_atomic_count,
            missing_atomic_metric_ids_json,
            sent_at,
            received_at,
            approved_at,
            delete_yn
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ON DUPLICATE KEY UPDATE
            rollup_purpose_code = VALUES(rollup_purpose_code),
            metric_scope_code = VALUES(metric_scope_code),
            request_status = VALUES(request_status),
            input_status = VALUES(input_status),
            approval_status = VALUES(approval_status),
            transfer_status = VALUES(transfer_status),
            required_atomic_count = VALUES(required_atomic_count),
            approved_atomic_count = VALUES(approved_atomic_count),
            missing_atomic_metric_ids_json = VALUES(missing_atomic_metric_ids_json),
            sent_at = VALUES(sent_at),
            received_at = VALUES(received_at),
            approved_at = VALUES(approved_at),
            delete_yn = 0,
            updated_at = CURRENT_TIMESTAMP
    """
    for status in sourceStatuses:
        cur.execute(
            sql,
            (
                batchId,
                status["parentCompanyId"],
                status["sourceCompanyId"],
                status["reportingYear"],
                rollupPurposeCode,
                metricScopeCode,
                status["requestStatus"],
                status["inputStatus"],
                status["approvalStatus"],
                status["transferStatus"],
                requiredAtomicCount,
                status["approvedCount"],
                json.dumps(status["missingAtomicMetricIds"]) if status["missingAtomicMetricIds"] else None,
                status.get("sentAt"),
                status.get("receivedAt"),
                status.get("approvedAt"),
            ),
        )

def updateSourceSentTx(cur, batchId: int, sourceCompanyId: int, requiredAtomicCount: int) -> None:
    cur.execute(
        """
        UPDATE ESG_ROLLUP_SOURCE_STATUS
        SET request_status = 'sent',
            input_status = 'approved',
            approval_status = 'approved',
            transfer_status = 'sent',
            approved_atomic_count = ?,
            missing_atomic_metric_ids_json = NULL,
            sent_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE esg_rollup_batch_id = ?
          AND source_company_id = ?
          AND delete_yn = 0
        """,
        (requiredAtomicCount, batchId, sourceCompanyId),
    )

def updateSourceStatusTx(cur, batchId: int, requiredAtomicCount: int) -> None:
    cur.execute(
        """
        UPDATE ESG_ROLLUP_SOURCE_STATUS
        SET request_status = 'received',
            input_status = 'approved',
            approval_status = 'approved',
            transfer_status = 'received',
            approved_atomic_count = ?,
            missing_atomic_metric_ids_json = NULL,
            received_at = CURRENT_TIMESTAMP,
            approved_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE esg_rollup_batch_id = ?
          AND delete_yn = 0
        """,
        (requiredAtomicCount, batchId),
    )

def finalizeDmaPrecheckTx(cur, batchId: int, runId: int, actorUserId: Optional[int] = None) -> None:
    cur.execute(
        """
        UPDATE ESG_ROLLUP_BATCH
        SET batch_status = ?,
            dma_ready_yn = 1,
            approved_by_user_id = ?,
            approved_at = CURRENT_TIMESTAMP,
            completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND delete_yn = 0
        """,
        (BATCH_STATUS_COMPLETED, actorUserId, batchId),
    )

    tracePayload = {
        "batchId": batchId,
        "metricScopeCode": "G0_02_FINANCIAL_BASIS",
        "calculatedAt": "CURRENT_TIMESTAMP",
    }
    cur.execute(
        """
        UPDATE ESG_MATERIALITY_RUN
        SET financial_basis_status = 'CONSOLIDATED_READY',
            financial_basis_trace_json = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND delete_yn = 0
        """,
        (json.dumps(tracePayload), runId),
    )

def updateBatchStatusTx(cur, batchId: int, status: str) -> None:
    cur.execute(
        """
        UPDATE ESG_ROLLUP_BATCH
        SET batch_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND delete_yn = 0
        """,
        (status, batchId)
    )

def finalizeReportDisclosureTx(cur, batchId: int, actorUserId: Optional[int] = None) -> None:
    cur.execute(
        """
        UPDATE ESG_ROLLUP_BATCH
        SET batch_status = ?,
            report_ready_yn = 1,
            approved_by_user_id = ?,
            approved_at = CURRENT_TIMESTAMP,
            completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND delete_yn = 0
        """,
        (BATCH_STATUS_COMPLETED, actorUserId, batchId),
    )

def getStatus(batchId: int) -> dict:
    sql = """
        SELECT
            b.id AS batchId,
            b.parent_company_id AS parentCompanyId,
            b.reporting_year AS reportingYear,
            b.rollup_purpose_code AS rollupPurposeCode,
            b.metric_scope_code AS metricScopeCode,
            b.batch_status AS batchStatus,
            COALESCE(COUNT(s.id), 0) AS requestedCount,
            COALESCE(SUM(
                CASE
                    WHEN LOWER(COALESCE(s.transfer_status, '')) IN ('sent', 'received')
                    THEN 1 ELSE 0
                END
            ), 0) AS sentCount,
            COALESCE(SUM(
                CASE
                    WHEN LOWER(COALESCE(s.transfer_status, '')) NOT IN ('sent', 'received')
                    THEN 1 ELSE 0
                END
            ), 0) AS pendingCount,
            b.dma_ready_yn AS dmaReadyYn,
            b.report_ready_yn AS reportReadyYn
        FROM ESG_ROLLUP_BATCH b
        LEFT JOIN ESG_ROLLUP_SOURCE_STATUS s
          ON s.esg_rollup_batch_id = b.id
         AND s.delete_yn = 0
         AND s.source_company_id <> b.parent_company_id
        WHERE b.id = ?
          AND b.delete_yn = 0
        GROUP BY
            b.id,
            b.parent_company_id,
            b.reporting_year,
            b.rollup_purpose_code,
            b.metric_scope_code,
            b.batch_status,
            b.dma_ready_yn,
            b.report_ready_yn
    """
    return findOne(sql, (batchId,)) or {}

def listPendingSources(batchId: int) -> list[dict]:
    sql = """
        SELECT
            source_company_id,
            transfer_status
        FROM ESG_ROLLUP_SOURCE_STATUS
        WHERE esg_rollup_batch_id = ?
          AND source_company_id <> parent_company_id
          AND LOWER(COALESCE(transfer_status, '')) NOT IN ('sent', 'received')
          AND delete_yn = 0
        ORDER BY source_company_id
    """
    return findAll(sql, (batchId,)) or []

def checkTransferReady(batchId: int) -> dict:
    pendingSources = listPendingSources(batchId)
    return {
        "readyYn": len(pendingSources) == 0,
        "notSentCompanyIds": [
            int(source["source_company_id"])
            for source in pendingSources
        ],
    }

def buildResultCode(batchId: int, groupAtomicMetricId: str) -> str:
    import hashlib
    base = f"{batchId}_{groupAtomicMetricId}"
    return f"RR_{hashlib.md5(base.encode()).hexdigest()[:8].upper()}"

def resultParams(
    batch: dict,
    result: dict,
    includedCompanyIds: list[int],
    actorUserId: Optional[int],
) -> tuple:
    resultCode = buildResultCode(int(batch["id"]), result["groupAtomicMetricId"])
    groupMetricId = result.get("groupMetricId")
    if not groupMetricId:
        raise ValueError("ROLLUP_GROUP_METRIC_ID_REQUIRED")
    baseParams = (
        int(batch["id"]),
        resultCode,
        int(batch["reporting_year"]),
        int(batch["parent_company_id"]),
        "CONSOLIDATED",
        _jsonDumps(includedCompanyIds),
        groupMetricId,
        result["groupAtomicMetricId"],
        result.get("groupAtomicName") or result["groupAtomicMetricId"],
        result.get("valueNumeric"),
        result.get("valueText"),
        result.get("unit") or "KRW",
        _jsonDumps(result.get("sourceCompanyValues") or {}),
        result.get("formulaType"),
        _jsonDumps(result.get("calculationTrace") or {}),
        actorUserId,
    )
    return baseParams

def upsertGroupRollupResultsTx(
    cur,
    batch: dict,
    results: list[dict],
    includedCompanyIds: list[int],
    actorUserId: Optional[int],
) -> None:
    for result in results:
        cur.execute(
            """
            SELECT id
            FROM ESG_GROUP_ROLLUP_RESULT
            WHERE esg_rollup_batch_id = ?
              AND group_atomic_metric_id = ?
              AND delete_yn = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(batch["id"]), result["groupAtomicMetricId"]),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                """
                UPDATE ESG_GROUP_ROLLUP_RESULT
                SET rollup_result_code = ?,
                    reporting_year = ?,
                    parent_company_id = ?,
                    parent_company_scope_type = ?,
                    included_company_ids = ?,
                    group_metric_id = ?,
                    group_atomic_metric_id = ?,
                    group_atomic_name = ?,
                    value_numeric = ?,
                    value_text = ?,
                    unit = ?,
                    source_company_values_json = ?,
                    rollup_method = ?,
                    calculation_trace = ?,
                    rollup_status = 'approved',
                    approved_by_user_id = ?,
                    approved_at = CURRENT_TIMESTAMP,
                    delete_yn = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                resultParams(batch, result, includedCompanyIds, actorUserId)[1:] + (int(existing["id"]),),
            )
        else:
            cur.execute(
                """
                INSERT INTO ESG_GROUP_ROLLUP_RESULT (
                    esg_rollup_batch_id,
                    rollup_result_code,
                    reporting_year,
                    parent_company_id,
                    parent_company_scope_type,
                    included_company_ids,
                    group_metric_id,
                    group_atomic_metric_id,
                    group_atomic_name,
                    value_numeric,
                    value_text,
                    unit,
                    source_company_values_json,
                    rollup_method,
                    calculation_trace,
                    rollup_status,
                    approved_by_user_id,
                    approved_at,
                    delete_yn
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?, CURRENT_TIMESTAMP, 0)
                """,
                resultParams(batch, result, includedCompanyIds, actorUserId),
            )
