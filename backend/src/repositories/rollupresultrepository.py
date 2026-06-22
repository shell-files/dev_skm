"""
rollupresultrepository.py
레이어: Repository
역할: 롤업 결과 저장·조회 및 연결 기준값(consolidated baseline) CRUD.
"""
import json
from decimal import Decimal
from typing import Any, Optional
from src.utils.db import findAll, findOne

def _jsonDefault(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

def _jsonDumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_jsonDefault)
def buildResultCode(batchId: int, groupAtomicMetricId: str) -> str:
    import hashlib
    base = f"{batchId}_{groupAtomicMetricId}"
    return f"RR_{hashlib.md5(base.encode()).hexdigest()[:8].upper()}"

# ESG_GROUP_ROLLUP_RESULT.calculation_trace(TEXT) 저장용 compact trace의 안전 상한.
# 초과 시 dependencySummary를 절단하고 무거운 원문(pre-aggregated map/engineTrace)은 절대 저장하지 않는다.
CALCULATION_TRACE_MAX_BYTES = 60000


# DB 저장용 compact 계산 추적 정보 구성 — full trace 제외, 상태·연도·의존성 요약만 보존
def compactCalculationTrace(result: dict) -> dict:
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


# rollup 결과 upsert 파라미터 튜플 생성
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

# 그룹 롤업 결과 upsert — 기존 행 UPDATE, 없으면 INSERT (트랜잭션 커서용)
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


# 부모 회사 연결 롤업 결과 조회 — 동일 지표는 최신 배치 1건만 사용 (트랜잭션 커서용)
def listConsolidatedRollupResultsByYearTx(
    cur,
    parentCompanyId: int,
    reportingYear: int,
    groupAtomicMetricIds: list[str],
) -> list[dict]:
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


# 연결 baseline Fact 목록 조회 — CONSOLIDATED scope, 동일 원자는 최신 1건 (트랜잭션 커서용)
def listConsolidatedBaselineFactsTx(
    cur,
    parentCompanyId: int,
    reportingYear: int,
    atomicMetricIds: list[str],
) -> list[dict]:
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


# 연결 baseline Fact 상세 맵 조회 — atomicMetricId → 값/단위/소스 타입 매핑 (트랜잭션 커서용)
def listConsolidatedBaselineDetailsTx(
    cur,
    parentCompanyId: int,
    reportingYear: int,
    atomicMetricIds: list[str],
) -> dict[str, dict]:
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


# 연결 baseline Fact upsert — 일반 ENTITY fact 충돌 시 'conflict_protected' 반환 (트랜잭션 커서용)
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