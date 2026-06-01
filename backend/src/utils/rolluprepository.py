"""
Domain: ESG Rollup
Layer: utils/repository
Responsibility:
- Read rollup scope, batches, source status, and approved G0-02 KPI facts
- Create DMA precheck G0-02 rollup batches in a transaction
- Persist approved G0-02 group rollup SUM results and readiness state
Public functions:
- getRun
- listSubsidiaries
- getBatch
- getActiveBatch
- listRequests
- getSource
- listSources
- saveBatch
- saveSources
- saveScope
- listScope
- listApprovedFacts
- upsertResults
- updateSourceStatus
- updateSourceSent
- updateBatchReady
- updateRunReady
- getStatus
- listPendingSources
- checkTransferReady
Do not:
- do not modify DB schema
- do not use unapproved onboarding values
- do not execute arbitrary SQL templates
- do not connect benchmark/media or DMA scoring pipelines
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional


ROLLUP_PURPOSE_DMA_PRECHECK = "DMA_PRECHECK"
METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
REPORT_SCOPE_CONSOLIDATED = "CONSOLIDATED"
BATCH_STATUS_PENDING = "pending"
BATCH_STATUS_COMPLETED = "completed"
SOURCE_STATUS_RECEIVED = "received"
SOURCE_STATUS_REQUESTED = "requested"
SOURCE_STATUS_SENT = "sent"
INPUT_STATUS_APPROVED = "approved"
INPUT_STATUS_SUBMITTED = "submitted"
INPUT_STATUS_NOT_STARTED = "not_started"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_SUBMITTED = "submitted"
APPROVAL_STATUS_PENDING = "pending"
TRANSFER_STATUS_RECEIVED = "received"
TRANSFER_STATUS_SENT = "sent"
TRANSFER_STATUS_NOT_SENT = "not_sent"

ATOMIC_SCOPE = [
    ("G0-02__G0001", "G0-02__Q0001"),
    ("G0-02__G0002", "G0-02__Q0002"),
    ("G0-02__G0003", "G0-02__Q0003"),
    ("G0-02__G0004", "G0-02__Q0004"),
    ("G0-02__G0005", "G0-02__Q0005"),
]
SOURCE_ATOMIC_IDS = [sourceAtomicId for _, sourceAtomicId in ATOMIC_SCOPE]
GROUP_ATOMIC_IDS = [groupAtomicId for groupAtomicId, _ in ATOMIC_SCOPE]


def findOne(sql: str, params=None):
    from src.utils.db import findOne as dbFindOne

    return dbFindOne(sql, params)


def findAll(sql: str, params=None):
    from src.utils.db import findAll as dbFindAll

    return dbFindAll(sql, params)


def getConn():
    from src.utils.db import getConn as dbGetConn

    return dbGetConn()


def getRun(runId: int) -> dict:
    sql = """
        SELECT
            id,
            company_id,
            reporting_year,
            report_basis_type,
            financial_basis_status,
            required_rollup_batch_id,
            run_status
        FROM ESG_MATERIALITY_RUN
        WHERE id = ?
          AND delete_yn = 0
    """
    return findOne(sql, (runId,)) or {}


def listSubsidiaries(run: dict) -> list[dict]:
    companyColumn = getScopeCompanyColumn()
    companyId = int(run["company_id"])
    reportingYear = int(run["reporting_year"])
    sql = f"""
        SELECT DISTINCT
            s.{companyColumn} AS companyId,
            p.company_code AS companyCode,
            COALESCE(p.company_code, CAST(s.{companyColumn} AS CHAR)) AS companyName
        FROM ESG_COMPANY_ROLLUP_SCOPE s
        LEFT JOIN ESG_COMPANY_PROFILE p
          ON p.company_id = s.{companyColumn}
         AND p.delete_yn = 0
        WHERE s.parent_company_id = ?
          AND s.rollup_include_yn = 1
          AND s.delete_yn = 0
          AND (s.effective_from_year IS NULL OR s.effective_from_year <= ?)
          AND (s.effective_to_year IS NULL OR s.effective_to_year >= ?)
          AND s.{companyColumn} <> ?
        ORDER BY companyName, companyId
    """
    rows = findAll(sql, (companyId, reportingYear, reportingYear, companyId)) or []
    return [
        {
            "companyId": int(row["companyId"]),
            "companyCode": row.get("companyCode"),
            "companyName": row.get("companyName") or row.get("companyCode"),
        }
        for row in rows
    ]


def getScopeCompanyColumn() -> str:
    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'ESG_COMPANY_ROLLUP_SCOPE'
          AND column_name IN (
              'source_company_id',
              'subsidiary_company_id',
              'child_company_id',
              'company_id'
          )
        ORDER BY CASE column_name
            WHEN 'source_company_id' THEN 1
            WHEN 'subsidiary_company_id' THEN 2
            WHEN 'child_company_id' THEN 3
            WHEN 'company_id' THEN 4
            ELSE 5
        END
        LIMIT 1
    """
    row = findOne(sql) or {}
    columnName = row.get("column_name")
    if columnName in {"source_company_id", "subsidiary_company_id", "child_company_id", "company_id"}:
        return columnName
    return "source_company_id"


def getActiveBatch(runId: int) -> dict:
    sql = """
        SELECT
            b.*,
            r.id AS run_id
        FROM ESG_MATERIALITY_RUN r
        JOIN ESG_ROLLUP_BATCH b
          ON b.parent_company_id = r.company_id
         AND b.reporting_year = r.reporting_year
         AND b.delete_yn = 0
        WHERE r.id = ?
          AND r.delete_yn = 0
          AND b.rollup_purpose_code = ?
          AND b.metric_scope_code = ?
          AND LOWER(COALESCE(b.batch_status, '')) NOT IN ('deleted', 'cancelled', 'canceled', 'archived')
        ORDER BY
            CASE WHEN r.required_rollup_batch_id = b.id THEN 0 ELSE 1 END,
            b.id DESC
        LIMIT 1
    """
    return findOne(sql, (runId, ROLLUP_PURPOSE_DMA_PRECHECK, METRIC_SCOPE_G0_02_FINANCIAL_BASIS)) or {}


def getBatch(batchId: int) -> dict:
    sql = """
        SELECT
            b.*,
            r.id AS run_id
        FROM ESG_ROLLUP_BATCH b
        LEFT JOIN ESG_MATERIALITY_RUN r
          ON r.required_rollup_batch_id = b.id
         AND r.delete_yn = 0
        WHERE b.id = ?
          AND b.delete_yn = 0
    """
    return findOne(sql, (batchId,)) or {}


def listRequests(sourceCompanyId: int) -> list[dict]:
    sql = """
        SELECT
            s.esg_rollup_batch_id AS batchId,
            s.parent_company_id AS parentCompanyId,
            p.company_code AS parentCompanyCode,
            COALESCE(p.company_code, CAST(s.parent_company_id AS CHAR)) AS parentCompanyName,
            s.source_company_id AS sourceCompanyId,
            s.reporting_year AS reportingYear,
            s.rollup_purpose_code AS rollupPurposeCode,
            s.metric_scope_code AS metricScopeCode,
            s.request_status AS requestStatus,
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
          AND s.request_status = 'requested'
          AND s.transfer_status = 'not_sent'
          AND b.rollup_purpose_code = ?
          AND b.metric_scope_code = ?
          AND LOWER(COALESCE(b.batch_status, '')) NOT IN (
              'deleted',
              'cancelled',
              'canceled',
              'archived',
              'completed'
          )
        ORDER BY s.updated_at DESC, s.id DESC
    """
    return findAll(sql, (sourceCompanyId, ROLLUP_PURPOSE_DMA_PRECHECK, METRIC_SCOPE_G0_02_FINANCIAL_BASIS)) or []


def getSource(batchId: int, sourceCompanyId: int) -> dict:
    sql = """
        SELECT
            s.id,
            s.esg_rollup_batch_id,
            s.parent_company_id,
            s.source_company_id,
            s.reporting_year,
            s.rollup_purpose_code,
            s.metric_scope_code,
            s.request_status,
            s.input_status,
            s.approval_status,
            s.transfer_status,
            s.required_atomic_count,
            s.approved_atomic_count,
            s.missing_atomic_metric_ids_json,
            s.sent_at,
            s.received_at,
            s.approved_at
        FROM ESG_ROLLUP_SOURCE_STATUS s
        WHERE s.esg_rollup_batch_id = ?
          AND s.source_company_id = ?
          AND s.delete_yn = 0
        LIMIT 1
    """
    return findOne(sql, (batchId, sourceCompanyId)) or {}


def listSources(batchId: int) -> list[dict]:
    sql = """
        SELECT
            id,
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
            approved_at
        FROM ESG_ROLLUP_SOURCE_STATUS
        WHERE esg_rollup_batch_id = ?
          AND delete_yn = 0
        ORDER BY source_company_id
    """
    return findAll(sql, (batchId,)) or []


def listSourceCompanyIds(batchId: int) -> list[int]:
    return [int(row["source_company_id"]) for row in listSources(batchId)]


def listScope(batchId: int) -> list[dict]:
    sql = """
        SELECT
            s.metric_id,
            s.group_atomic_metric_id,
            s.source_atomic_metric_ids,
            s.required_yn,
            s.scope_reason,
            COALESCE(amm.atomic_name_kr, s.group_atomic_metric_id) AS groupAtomicName,
            'SUM' AS formulaType
        FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE s
        LEFT JOIN ESG_ATOMIC_METRIC_MASTER amm
          ON amm.atomic_metric_id = s.group_atomic_metric_id
         AND amm.delete_yn = 0
        WHERE s.esg_rollup_batch_id = ?
          AND s.delete_yn = 0
          AND s.required_yn = 1
        ORDER BY s.group_atomic_metric_id
    """
    return findAll(sql, (batchId,)) or []


def listApprovedFacts(companyIds: list[int], reportingYear: int) -> list[dict]:
    if not companyIds:
        return []
    companyPlaceholders = ", ".join(["?"] * len(companyIds))
    atomicPlaceholders = ", ".join(["?"] * len(SOURCE_ATOMIC_IDS))
    sql = f"""
        SELECT
            company_id AS companyId,
            reporting_year AS reportingYear,
            atomic_metric_id AS atomicMetricId,
            value_numeric AS valueNumeric,
            COALESCE(unit, 'KRW') AS unit,
            approved_at AS approvedAt,
            updated_at AS updatedAt,
            id
        FROM (
            SELECT
                k.*,
                ROW_NUMBER() OVER (
                    PARTITION BY k.company_id, k.atomic_metric_id
                    ORDER BY
                        COALESCE(k.approved_at, k.updated_at) DESC,
                        k.updated_at DESC,
                        k.id DESC
                ) AS row_num
            FROM ESG_KPI_FACT k
            JOIN ESG_ONBOARDING_INPUT_VALUE iv
              ON iv.id = k.source_input_value_id
             AND iv.company_id = k.company_id
             AND iv.reporting_year = k.reporting_year
             AND iv.metric_id = k.metric_id
             AND iv.atomic_metric_id = k.atomic_metric_id
             AND iv.delete_yn = 0
             AND LOWER(COALESCE(iv.input_status, '')) = 'approved'
            WHERE k.company_id IN ({companyPlaceholders})
              AND k.reporting_year = ?
              AND k.metric_id = 'G0-02'
              AND k.atomic_metric_id IN ({atomicPlaceholders})
              AND LOWER(COALESCE(k.approval_status, '')) = 'approved'
              AND k.value_numeric IS NOT NULL
              AND k.delete_yn = 0
        ) ranked
        WHERE row_num = 1
        ORDER BY company_id, atomic_metric_id
    """
    return findAll(sql, (*companyIds, reportingYear, *SOURCE_ATOMIC_IDS)) or []


def saveBatch(
    run: dict,
    includedCompanyIds: list[int],
    sourceStatuses: list[dict],
    actorUserId: Optional[int] = None,
) -> dict:
    conn = getConn()
    if not conn:
        return {}
    batchId = None
    try:
        with conn.cursor(dictionary=True) as cur:
            batchCode = buildBatchCode(int(run["company_id"]), int(run["reporting_year"]))
            cur.execute(
                """
                INSERT INTO ESG_ROLLUP_BATCH (
                    rollup_batch_code,
                    parent_company_id,
                    reporting_year,
                    report_scope_type,
                    included_company_ids_json,
                    batch_status,
                    rollup_purpose_code,
                    metric_scope_code,
                    dma_ready_yn,
                    report_ready_yn,
                    requested_by_user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
                """,
                (
                    batchCode,
                    int(run["company_id"]),
                    int(run["reporting_year"]),
                    REPORT_SCOPE_CONSOLIDATED,
                    dumpJson(includedCompanyIds),
                    BATCH_STATUS_PENDING,
                    ROLLUP_PURPOSE_DMA_PRECHECK,
                    METRIC_SCOPE_G0_02_FINANCIAL_BASIS,
                    actorUserId,
                ),
            )
            batchId = int(cur.lastrowid)
            saveSources(cur, batchId, sourceStatuses)
            saveScope(cur, batchId)
            cur.execute(
                """
                UPDATE ESG_MATERIALITY_RUN
                SET required_rollup_batch_id = ?,
                    financial_basis_status = 'CONSOLIDATED_ROLLUP_PENDING',
                    financial_basis_checked_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND delete_yn = 0
                """,
                (batchId, int(run["id"])),
            )
        conn.commit()
    except Exception as e:
        print(f"Rollup batch transaction error: {e}")
        conn.rollback()
        return {}
    finally:
        conn.close()
    return getBatch(batchId) if batchId else {}


def saveSources(cur, batchId: int, sourceStatuses: list[dict]) -> None:
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
                ROLLUP_PURPOSE_DMA_PRECHECK,
                METRIC_SCOPE_G0_02_FINANCIAL_BASIS,
                status["requestStatus"],
                status["inputStatus"],
                status["approvalStatus"],
                status["transferStatus"],
                len(SOURCE_ATOMIC_IDS),
                status["approvedCount"],
                dumpJson(status["missingAtomicMetricIds"]) if status["missingAtomicMetricIds"] else None,
                status.get("sentAt"),
                status.get("receivedAt"),
                status.get("approvedAt"),
            ),
        )


def saveScope(cur, batchId: int) -> None:
    sql = """
        INSERT INTO ESG_ROLLUP_BATCH_ATOMIC_SCOPE (
            esg_rollup_batch_id,
            metric_id,
            group_atomic_metric_id,
            source_atomic_metric_ids,
            required_yn,
            scope_reason,
            delete_yn
        ) VALUES (?, 'G0-02', ?, ?, 1, ?, 0)
        ON DUPLICATE KEY UPDATE
            source_atomic_metric_ids = VALUES(source_atomic_metric_ids),
            required_yn = VALUES(required_yn),
            scope_reason = VALUES(scope_reason),
            delete_yn = 0,
            updated_at = CURRENT_TIMESTAMP
    """
    for groupAtomicId, sourceAtomicId in ATOMIC_SCOPE:
        cur.execute(sql, (batchId, groupAtomicId, sourceAtomicId, ROLLUP_PURPOSE_DMA_PRECHECK))


def upsertResults(batch: dict, results: list[dict], actorUserId: Optional[int] = None) -> bool:
    conn = getConn()
    if not conn:
        return False
    try:
        with conn.cursor(dictionary=True) as cur:
            includedCompanyIds = loadJson(batch.get("included_company_ids_json")) or []
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
                    updateResult(cur, batch, result, includedCompanyIds, actorUserId, int(existing["id"]))
                else:
                    insertResult(cur, batch, result, includedCompanyIds, actorUserId)
            updateSourceStatus(cur, int(batch["id"]))
            updateBatchReady(cur, int(batch["id"]), actorUserId)
            updateRunReady(cur, int(batch["id"]), results)
        conn.commit()
        return True
    except Exception as e:
        print(f"Rollup calculate transaction error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def updateSourceSent(batchId: int, sourceCompanyId: int) -> dict:
    conn = getConn()
    if not conn:
        return {}
    try:
        with conn.cursor(dictionary=True) as cur:
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
                (len(SOURCE_ATOMIC_IDS), batchId, sourceCompanyId),
            )
        conn.commit()
    except Exception as e:
        print(f"Rollup source send transaction error: {e}")
        conn.rollback()
        return {}
    finally:
        conn.close()
    return getSource(batchId, sourceCompanyId)


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
            b.dma_ready_yn AS dmaReadyYn
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
            b.dma_ready_yn
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


def insertResult(
    cur,
    batch: dict,
    result: dict,
    includedCompanyIds: list[int],
    actorUserId: Optional[int],
) -> None:
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
        ) VALUES (?, ?, ?, ?, ?, ?, 'G0-02', ?, ?, ?, NULL, ?, ?, ?, ?, 'approved', ?, CURRENT_TIMESTAMP, 0)
        """,
        resultParams(batch, result, includedCompanyIds, actorUserId),
    )


def updateResult(
    cur,
    batch: dict,
    result: dict,
    includedCompanyIds: list[int],
    actorUserId: Optional[int],
    resultId: int,
) -> None:
    cur.execute(
        """
        UPDATE ESG_GROUP_ROLLUP_RESULT
        SET rollup_result_code = ?,
            reporting_year = ?,
            parent_company_id = ?,
            parent_company_scope_type = ?,
            included_company_ids = ?,
            group_metric_id = 'G0-02',
            group_atomic_metric_id = ?,
            group_atomic_name = ?,
            value_numeric = ?,
            value_text = NULL,
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
        resultParams(batch, result, includedCompanyIds, actorUserId)[1:] + (resultId,),
    )


def resultParams(
    batch: dict,
    result: dict,
    includedCompanyIds: list[int],
    actorUserId: Optional[int],
) -> tuple:
    resultCode = buildResultCode(int(batch["id"]), result["groupAtomicMetricId"])
    baseParams = (
        int(batch["id"]),
        resultCode,
        int(batch["reporting_year"]),
        int(batch["parent_company_id"]),
        REPORT_SCOPE_CONSOLIDATED,
        dumpJson(includedCompanyIds),
        result["groupAtomicMetricId"],
        result.get("groupAtomicName") or result["groupAtomicMetricId"],
        result["valueNumeric"],
        result.get("unit") or "KRW",
        dumpJson(result.get("sourceCompanyValues") or {}),
        result["formulaType"],
        dumpJson(result.get("calculationTrace") or {}),
        actorUserId,
    )
    return baseParams


def updateSourceStatus(cur, batchId: int) -> None:
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
        (len(SOURCE_ATOMIC_IDS), batchId),
    )


def updateBatchReady(cur, batchId: int, actorUserId: Optional[int]) -> None:
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


def updateRunReady(cur, batchId: int, results: list[dict]) -> None:
    tracePayload = {
        "batchId": batchId,
        "metricScopeCode": METRIC_SCOPE_G0_02_FINANCIAL_BASIS,
        "resultCount": len(results),
        "groupAtomicMetricIds": [result["groupAtomicMetricId"] for result in results],
    }
    cur.execute(
        """
        UPDATE ESG_MATERIALITY_RUN
        SET financial_basis_status = 'CONSOLIDATED_READY',
            financial_basis_checked_at = CURRENT_TIMESTAMP,
            financial_basis_trace_json = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE required_rollup_batch_id = ?
          AND delete_yn = 0
        """,
        (dumpJson(tracePayload), batchId),
    )


def buildBatchCode(parentCompanyId: int, reportingYear: int) -> str:
    suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"DMA_PRECHECK_G0_02_{parentCompanyId}_{reportingYear}_{suffix}"


def buildResultCode(batchId: int, groupAtomicMetricId: str) -> str:
    safeAtomicId = groupAtomicMetricId.replace("-", "_").replace("__", "_")
    return f"G0_02_ROLLUP_{batchId}_{safeAtomicId}"


def dumpJson(value) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def loadJson(value):
    if not value:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ATOMIC_SCOPE",
    "GROUP_ATOMIC_IDS",
    "SOURCE_ATOMIC_IDS",
    "METRIC_SCOPE_G0_02_FINANCIAL_BASIS",
    "ROLLUP_PURPOSE_DMA_PRECHECK",
    "getRun",
    "listSubsidiaries",
    "getBatch",
    "getActiveBatch",
    "listRequests",
    "getSource",
    "listSources",
    "listSourceCompanyIds",
    "saveBatch",
    "saveSources",
    "saveScope",
    "listScope",
    "listApprovedFacts",
    "upsertResults",
    "updateSourceStatus",
    "updateSourceSent",
    "updateBatchReady",
    "updateRunReady",
    "getStatus",
    "listPendingSources",
    "checkTransferReady",
]
