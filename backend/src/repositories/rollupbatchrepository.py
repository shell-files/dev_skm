"""
rollupbatchrepository.py
레이어: Repository
역할: 롤업 배치 CRUD — 배치 생성·상태 업데이트·조회.
"""
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
    rollupPurposeCode: Optional[str],
    metricScopeCode: Optional[str],
    includeSentYn: bool = True,
    transferStatus: Optional[str] = None,
) -> list[dict]:
    transferFilter = ""
    requestFilter = ""
    purposeFilter = ""
    scopeFilter = ""
    params = [sourceCompanyId]
    
    if rollupPurposeCode is not None:
        purposeFilter = "AND b.rollup_purpose_code = ?"
        params.append(rollupPurposeCode)
        
    if metricScopeCode is not None:
        scopeFilter = "AND b.metric_scope_code = ?"
        params.append(metricScopeCode)
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
          {purposeFilter}
          {scopeFilter}
          {requestFilter}
          {transferFilter}
          AND LOWER(COALESCE(b.batch_status, '')) NOT IN (
              'deleted',
              'cancelled',
              'canceled',
              'archived'
          )
          AND (
              b.rollup_purpose_code <> 'DMA_PRECHECK'
              OR b.id IN (SELECT required_rollup_batch_id FROM ESG_MATERIALITY_RUN WHERE delete_yn = 0)
          )
        ORDER BY s.updated_at DESC, s.id DESC
    """.format(purposeFilter=purposeFilter, scopeFilter=scopeFilter, requestFilter=requestFilter, transferFilter=transferFilter)
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
          AND c.cycle_type IN ('ROLLUP_RESPONSE', 'POST_DMA_DISCLOSURE', 'PRE_DMA_G0')
          AND c.delete_yn = 0
        GROUP BY c.id, c.cycle_type, c.reporting_year
        HAVING matchedMetricCount = ?
        ORDER BY
            CASE c.cycle_type
                WHEN 'ROLLUP_RESPONSE' THEN 1
                WHEN 'POST_DMA_DISCLOSURE' THEN 2
                WHEN 'PRE_DMA_G0' THEN 3
                ELSE 4
            END,
            c.id DESC
        LIMIT 1
    """
    return findOne(sql, (*metricIds, companyId, reportingYear, len(metricIds))) or {}

def listSourceCompanyIds(batchId: int) -> list[int]:
    return [int(row["source_company_id"]) for row in listSources(batchId)]

def listConflictingActiveSourceRequests(
    sourceCompanyIds: list[int],
    reportingYear: int,
    rollupPurposeCode: str,
    metricScopeCode: str,
) -> list[dict]:
    cleanedCompanyIds = [
        int(companyId)
        for companyId in sourceCompanyIds or []
        if companyId is not None
    ]
    if not cleanedCompanyIds:
        return []
    placeholders = ", ".join(["?"] * len(cleanedCompanyIds))
    return findAll(
        f"""
        SELECT
            s.source_company_id AS sourceCompanyId,
            s.esg_rollup_batch_id AS existingBatchId,
            s.reporting_year AS reportingYear,
            s.rollup_purpose_code AS rollupPurposeCode,
            s.metric_scope_code AS metricScopeCode,
            s.transfer_status AS transferStatus
        FROM ESG_ROLLUP_SOURCE_STATUS s
        JOIN ESG_ROLLUP_BATCH b
          ON b.id = s.esg_rollup_batch_id
         AND b.delete_yn = 0
        WHERE s.source_company_id IN ({placeholders})
          AND s.source_company_id <> s.parent_company_id
          AND s.reporting_year = ?
          AND s.rollup_purpose_code = ?
          AND s.metric_scope_code = ?
          AND s.delete_yn = 0
          AND LOWER(COALESCE(s.transfer_status, '')) NOT IN ('sent', 'received')
          AND LOWER(COALESCE(b.batch_status, '')) NOT IN (
              'deleted',
              'cancelled',
              'canceled',
              'archived'
          )
        ORDER BY s.source_company_id, s.esg_rollup_batch_id
        """,
        (
            *cleanedCompanyIds,
            reportingYear,
            rollupPurposeCode,
            metricScopeCode,
        ),
    ) or []

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

def lockSourceStatusTx(cur, batchId: int, sourceCompanyId: int) -> dict:
    cur.execute(
        """
        SELECT *
        FROM ESG_ROLLUP_SOURCE_STATUS
        WHERE esg_rollup_batch_id = ?
          AND source_company_id = ?
          AND delete_yn = 0
        LIMIT 1
        FOR UPDATE
        """,
        (batchId, sourceCompanyId),
    )
    return cur.fetchone() or {}

def syncSourceReadinessTx(
    cur,
    batchId: int,
    sourceCompanyId: int,
    reportingYear: int,
) -> dict:
    from src.repositories.rollupscoperepository import buildSourceReadinessTx

    readiness = buildSourceReadinessTx(cur, batchId, [sourceCompanyId], reportingYear)
    requiredAtomicCount = int(readiness.get("requiredAtomicCount") or 0)
    missingAtomicIds = readiness.get("missingByCompany", {}).get(
        str(sourceCompanyId),
        readiness.get("missingAtomicMetricIds") or [],
    )
    approvedAtomicCount = max(requiredAtomicCount - len(missingAtomicIds), 0)
    readyYn = requiredAtomicCount > 0 and not missingAtomicIds

    if readyYn:
        inputStatus = "approved"
        approvalStatus = "approved"
    elif approvedAtomicCount > 0:
        inputStatus = "submitted"
        approvalStatus = "submitted"
    else:
        inputStatus = "not_started"
        approvalStatus = "pending"

    cur.execute(
        """
        UPDATE ESG_ROLLUP_SOURCE_STATUS
        SET input_status = ?,
            approval_status = ?,
            required_atomic_count = ?,
            approved_atomic_count = ?,
            missing_atomic_metric_ids_json = ?,
            approved_at = CASE
                WHEN ? = 1 THEN COALESCE(approved_at, CURRENT_TIMESTAMP)
                ELSE NULL
            END,
            updated_at = CURRENT_TIMESTAMP
        WHERE esg_rollup_batch_id = ?
          AND source_company_id = ?
          AND delete_yn = 0
        """,
        (
            inputStatus,
            approvalStatus,
            requiredAtomicCount,
            approvedAtomicCount,
            json.dumps(missingAtomicIds) if missingAtomicIds else None,
            1 if readyYn else 0,
            batchId,
            sourceCompanyId,
        ),
    )
    return readiness

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

# ESG_GROUP_ROLLUP_RESULT.calculation_trace(TEXT) 저장용 compact trace의 안전 상한.
# 초과 시 dependencySummary를 절단하고 무거운 원문(pre-aggregated map/engineTrace)은 절대 저장하지 않는다.
CALCULATION_TRACE_MAX_BYTES = 60000


def compactCalculationTrace(result: dict) -> dict:
    """
    DB 저장용 compact trace를 만든다. full trace(currentPreAggregatedMap,
    priorPreAggregatedMap, engineTrace 원문 등)는 TEXT 컬럼 한계를 넘으므로 저장하지 않고,
    상태/연도/의존성 요약만 남긴다. (API response warning trace 는 별도로 full 유지)
    """
    trace = result.get("calculationTrace") or {}
    dependencySummary = [
        {
            "sourceAtomicMetricId": dependency.get("sourceAtomicMetricId"),
            "sourceTiming": dependency.get("sourceTiming"),
            "evaluatedYear": dependency.get("evaluatedYear"),
            "status": dependency.get("status"),
            "sourceScope": dependency.get("sourceScope"),
            "missingCompanyIds": dependency.get("missingCompanyIds"),
            "missingConsolidatedSource": dependency.get("missingConsolidatedSource"),
            "requiredReportingYear": dependency.get("requiredReportingYear"),
        }
        for dependency in trace.get("historicalDependencies") or []
    ]
    compact = {
        "calculationStatus": result.get("calculationStatus"),
        "formulaType": result.get("formulaType"),
        "reportingYear": trace.get("reportingYear"),
        "evaluatedYear": trace.get("evaluatedYear"),
        "historicalLookbackDepth": trace.get("historicalLookbackDepth"),
        "sourceAtomicMetricIds": result.get("sourceAtomicMetricIds") or [],
        "dependencySummary": dependencySummary,
        "engineStatus": (trace.get("engineTrace") or {}).get("calculationStatus"),
    }

    # optional safety: compact 가 여전히 상한을 넘으면 dependencySummary 만 절단해 남긴다.
    # 무거운 원문 맵/engineTrace 는 애초에 compact 에 포함하지 않으므로 절대 저장되지 않는다.
    if len(_jsonDumps(compact).encode("utf-8")) > CALCULATION_TRACE_MAX_BYTES:
        compact = {
            "calculationStatus": compact["calculationStatus"],
            "formulaType": compact["formulaType"],
            "reportingYear": compact["reportingYear"],
            "evaluatedYear": compact["evaluatedYear"],
            "historicalLookbackDepth": compact["historicalLookbackDepth"],
            "sourceAtomicMetricIds": compact["sourceAtomicMetricIds"],
            "engineStatus": compact["engineStatus"],
            "dependencyCount": len(dependencySummary),
            "dependencySummary": dependencySummary[:50],
            "traceTruncatedYn": True,
        }
    return compact


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
        _jsonDumps(compactCalculationTrace(result)),
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


CONSOLIDATED_RESULT_READY_STATUSES = ("approved", "completed", "calculated")


def listConsolidatedRollupResultsByYearTx(
    cur,
    parentCompanyId: int,
    reportingYear: int,
    groupAtomicMetricIds: list[str],
) -> list[dict]:
    """
    ESG_GROUP_ROLLUP_RESULT 에서 parent company 의 연결 결과값을 연도별로 조회한다.
    source_scope=CONSOLIDATED 인 source(예: 전년도 연결 기준값) 의 입력으로 사용된다.
    동일 (parent, year, group_atomic) 에 여러 batch 결과가 있으면 최신(id DESC) 1건만 사용한다.
    """
    cleaned = [
        str(atomicId or "").strip()
        for atomicId in groupAtomicMetricIds or []
        if str(atomicId or "").strip()
    ]
    if not cleaned:
        return []
    placeholders = ", ".join(["?"] * len(cleaned))
    statusPlaceholders = ", ".join(["?"] * len(CONSOLIDATED_RESULT_READY_STATUSES))
    cur.execute(
        f"""
        SELECT g.group_atomic_metric_id, g.value_numeric, g.value_text, g.unit
        FROM ESG_GROUP_ROLLUP_RESULT g
        INNER JOIN (
            SELECT group_atomic_metric_id, MAX(id) AS max_id
            FROM ESG_GROUP_ROLLUP_RESULT
            WHERE parent_company_id = ?
              AND reporting_year = ?
              AND group_atomic_metric_id IN ({placeholders})
              AND LOWER(COALESCE(rollup_status, '')) IN ({statusPlaceholders})
              AND delete_yn = 0
            GROUP BY group_atomic_metric_id
        ) latest
          ON latest.group_atomic_metric_id = g.group_atomic_metric_id
         AND latest.max_id = g.id
        """,
        (parentCompanyId, reportingYear, *cleaned, *CONSOLIDATED_RESULT_READY_STATUSES),
    )
    return cur.fetchall() or []


# ──────────────────────────────────────────────────────────────────────────
# S5-B14 PRIOR_YEAR_BASELINE: 전년도 연결 기준값을 신규 테이블 없이 ESG_KPI_FACT 에
# 저장/조회한다. parent company 의 consolidated baseline fact 로 처리하며, 일반 ENTITY
# 운영 fact 와는 value_source_type / company_scope_type 로 구분한다.
# ──────────────────────────────────────────────────────────────────────────
PRIOR_YEAR_BASELINE_VALUE_SOURCE_TYPE = "PRIOR_YEAR_BASELINE_INPUT"
CONSOLIDATED_BASELINE_SCOPE_TYPE = "CONSOLIDATED_BASELINE"
CONSOLIDATED_BASELINE_SCOPE_TYPES = ("CONSOLIDATED", "CONSOLIDATED_BASELINE")


def listConsolidatedBaselineFactsTx(
    cur,
    parentCompanyId: int,
    reportingYear: int,
    atomicMetricIds: list[str],
) -> list[dict]:
    """
    ESG_KPI_FACT 에서 parent company 의 연결 baseline 입력값을 조회한다.
    company_scope_type IN (CONSOLIDATED, CONSOLIDATED_BASELINE), approved, delete_yn=0.
    PRIOR + CONSOLIDATED source 평가용 consolidatedFactMapsByYear seed 로 사용된다.
    동일 (company, year, atomic) 에 여러 row 가 있으면 최신(id DESC) 1건만 사용한다.
    반환 행은 buildConsolidatedFactMap 이 바로 사용할 수 있도록 group_atomic_metric_id 로 alias.
    """
    cleaned = [
        str(atomicId or "").strip()
        for atomicId in atomicMetricIds or []
        if str(atomicId or "").strip()
    ]
    if not cleaned:
        return []
    placeholders = ", ".join(["?"] * len(cleaned))
    scopeUpper = tuple(scope.upper() for scope in CONSOLIDATED_BASELINE_SCOPE_TYPES)
    scopePlaceholders = ", ".join(["?"] * len(scopeUpper))
    cur.execute(
        f"""
        SELECT f.atomic_metric_id AS group_atomic_metric_id,
               f.value_numeric,
               f.value_text,
               f.unit
        FROM ESG_KPI_FACT f
        INNER JOIN (
            SELECT atomic_metric_id, MAX(id) AS max_id
            FROM ESG_KPI_FACT
            WHERE company_id = ?
              AND reporting_year = ?
              AND atomic_metric_id IN ({placeholders})
              AND UPPER(COALESCE(company_scope_type, '')) IN ({scopePlaceholders})
              AND LOWER(COALESCE(approval_status, '')) = 'approved'
              AND delete_yn = 0
            GROUP BY atomic_metric_id
        ) latest
          ON latest.atomic_metric_id = f.atomic_metric_id
         AND latest.max_id = f.id
        """,
        (parentCompanyId, reportingYear, *cleaned, *scopeUpper),
    )
    return cur.fetchall() or []


def listConsolidatedBaselineDetailsTx(
    cur,
    parentCompanyId: int,
    reportingYear: int,
    atomicMetricIds: list[str],
) -> dict[str, dict]:
    """
    baseline-requirements API 용. 입력 atomic 별 현재 저장된 baseline 값 상세를
    atomicMetricId -> {valueNumeric, valueText, unit, valueSourceType} 맵으로 반환한다.
    """
    cleaned = [
        str(atomicId or "").strip()
        for atomicId in atomicMetricIds or []
        if str(atomicId or "").strip()
    ]
    if not cleaned:
        return {}
    placeholders = ", ".join(["?"] * len(cleaned))
    scopeUpper = tuple(scope.upper() for scope in CONSOLIDATED_BASELINE_SCOPE_TYPES)
    scopePlaceholders = ", ".join(["?"] * len(scopeUpper))
    cur.execute(
        f"""
        SELECT f.atomic_metric_id,
               f.value_numeric,
               f.value_text,
               f.unit,
               f.value_source_type
        FROM ESG_KPI_FACT f
        INNER JOIN (
            SELECT atomic_metric_id, MAX(id) AS max_id
            FROM ESG_KPI_FACT
            WHERE company_id = ?
              AND reporting_year = ?
              AND atomic_metric_id IN ({placeholders})
              AND UPPER(COALESCE(company_scope_type, '')) IN ({scopePlaceholders})
              AND LOWER(COALESCE(approval_status, '')) = 'approved'
              AND delete_yn = 0
            GROUP BY atomic_metric_id
        ) latest
          ON latest.atomic_metric_id = f.atomic_metric_id
         AND latest.max_id = f.id
        """,
        (parentCompanyId, reportingYear, *cleaned, *scopeUpper),
    )
    rows = cur.fetchall() or []
    details: dict[str, dict] = {}
    for row in rows:
        atomicId = str(row.get("atomic_metric_id") or "").strip()
        if not atomicId:
            continue
        details[atomicId] = {
            "valueNumeric": row.get("value_numeric"),
            "valueText": row.get("value_text"),
            "unit": row.get("unit"),
            "valueSourceType": row.get("value_source_type"),
        }
    return details


def upsertConsolidatedBaselineFactTx(
    cur,
    *,
    parentCompanyId: int,
    reportingYear: int,
    metricId: Optional[str],
    atomicMetricId: str,
    valueNumeric: Optional[float],
    valueText: Optional[str],
    unit: Optional[str],
    actorUserId: Optional[int],
) -> str:
    """
    prior-year 연결 baseline 을 ESG_KPI_FACT 에 upsert 한다.
    - 기존 row 가 없으면 INSERT.
    - 기존 row 가 PRIOR_YEAR_BASELINE_INPUT 이거나 company_scope_type 이 CONSOLIDATED% 면 UPDATE.
    - 일반 운영 ENTITY fact 면 덮어쓰지 않고 'conflict_protected' 를 반환한다.
    반환: 'inserted' | 'updated' | 'conflict_protected'
    """
    atomicId = str(atomicMetricId or "").strip()
    if not atomicId:
        return "conflict_protected"

    cur.execute(
        """
        SELECT id, company_scope_type, value_source_type
        FROM ESG_KPI_FACT
        WHERE company_id = ?
          AND reporting_year = ?
          AND atomic_metric_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (parentCompanyId, reportingYear, atomicId),
    )
    existing = cur.fetchone()

    if existing:
        scope = str(existing.get("company_scope_type") or "").strip().upper()
        srcType = str(existing.get("value_source_type") or "").strip().upper()
        protected = (
            srcType != PRIOR_YEAR_BASELINE_VALUE_SOURCE_TYPE
            and not scope.startswith("CONSOLIDATED")
        )
        if protected:
            return "conflict_protected"
        cur.execute(
            """
            UPDATE ESG_KPI_FACT
            SET source_input_value_id = NULL,
                company_scope_type = ?,
                metric_id = ?,
                value_numeric = ?,
                value_text = ?,
                unit = ?,
                value_source_type = ?,
                approval_status = 'approved',
                approved_by_user_id = ?,
                approved_at = CURRENT_TIMESTAMP,
                delete_yn = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                CONSOLIDATED_BASELINE_SCOPE_TYPE,
                metricId,
                valueNumeric,
                valueText,
                unit,
                PRIOR_YEAR_BASELINE_VALUE_SOURCE_TYPE,
                actorUserId,
                int(existing["id"]),
            ),
        )
        return "updated"

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
        ) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?, CURRENT_TIMESTAMP, 0)
        """,
        (
            parentCompanyId,
            reportingYear,
            CONSOLIDATED_BASELINE_SCOPE_TYPE,
            metricId,
            atomicId,
            valueNumeric,
            valueText,
            unit,
            PRIOR_YEAR_BASELINE_VALUE_SOURCE_TYPE,
            actorUserId,
        ),
    )
    return "inserted"
