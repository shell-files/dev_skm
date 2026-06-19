"""
calculationrepository.py
레이어: Repository
역할: KPI 계산 규칙 및 승인된 Fact 데이터 조회.
"""
from __future__ import annotations

from typing import Optional

from src.utils.db import findAll


EXECUTION_SCOPE_ENTITY = "ENTITY"
EXECUTION_SCOPE_CONSOLIDATED = "CONSOLIDATED"
VALUE_SOURCE_TYPE_CALCULATION_ENGINE = "calculation_engine"
APPROVAL_STATUS_APPROVED = "approved"


# 실행 범위 기준 활성 계산 규칙 목록 조회
def listActiveRules(
    executionScope: str,
    metricIds: Optional[list[str]] = None,
) -> list[dict]:
    metricFilter, params = buildMetricFilter(metricIds)
    return findAll(
        f"""
        SELECT
            id,
            calculation_rule_code,
            target_atomic_metric_id,
            target_atomic_name_kr,
            metric_id,
            formula_type,
            execution_scope,
            applicable_company_scope,
            zero_division_policy,
            rounding_policy,
            result_table,
            output_unit,
            execution_order,
            yoy_direction_code
        FROM ESG_CALCULATION_RULE
        WHERE UPPER(COALESCE(execution_scope, '')) = ?
          AND active_yn = 1
          AND delete_yn = 0
          {metricFilter}
        ORDER BY COALESCE(execution_order, 0), calculation_rule_code
        """,
        (normalizeScope(executionScope), *params),
    ) or []


# 활성 계산 규칙 목록 조회 (트랜잭션 커서용)
def listActiveRulesTx(
    cur,
    executionScope: str,
    metricIds: Optional[list[str]] = None,
) -> list[dict]:
    metricFilter, params = buildMetricFilter(metricIds)
    cur.execute(
        f"""
        SELECT
            id,
            calculation_rule_code,
            target_atomic_metric_id,
            target_atomic_name_kr,
            metric_id,
            formula_type,
            execution_scope,
            applicable_company_scope,
            zero_division_policy,
            rounding_policy,
            result_table,
            output_unit,
            execution_order,
            yoy_direction_code
        FROM ESG_CALCULATION_RULE
        WHERE UPPER(COALESCE(execution_scope, '')) = ?
          AND active_yn = 1
          AND delete_yn = 0
          {metricFilter}
        ORDER BY COALESCE(execution_order, 0), calculation_rule_code
        """,
        (normalizeScope(executionScope), *params),
    )
    return cur.fetchall() or []


# 대상 원자 지표 ID 기준 활성 계산 규칙 조회
def listActiveRulesByTargetAtomicIds(
    targetAtomicMetricIds: list[str],
    executionScope: str = EXECUTION_SCOPE_CONSOLIDATED,
) -> list[dict]:
    cleaned = cleanList(targetAtomicMetricIds)
    if not cleaned:
        return []
    placeholders = ", ".join(["?"] * len(cleaned))
    return findAll(
        f"""
        SELECT
            id,
            calculation_rule_code,
            target_atomic_metric_id,
            target_atomic_name_kr,
            metric_id,
            formula_type,
            execution_scope,
            applicable_company_scope,
            zero_division_policy,
            rounding_policy,
            result_table,
            output_unit,
            execution_order,
            yoy_direction_code
        FROM ESG_CALCULATION_RULE
        WHERE UPPER(COALESCE(execution_scope, '')) = ?
          AND active_yn = 1
          AND delete_yn = 0
          AND target_atomic_metric_id IN ({placeholders})
        ORDER BY COALESCE(execution_order, 0), calculation_rule_code
        """,
        (normalizeScope(executionScope), *cleaned),
    ) or []


# 대상 원자 지표 ID 기준 활성 계산 규칙 조회 (트랜잭션 커서용)
def listActiveRulesByTargetAtomicIdsTx(
    cur,
    targetAtomicMetricIds: list[str],
    executionScope: str = EXECUTION_SCOPE_CONSOLIDATED,
) -> list[dict]:
    cleaned = cleanList(targetAtomicMetricIds)
    if not cleaned:
        return []
    placeholders = ", ".join(["?"] * len(cleaned))
    cur.execute(
        f"""
        SELECT
            id,
            calculation_rule_code,
            target_atomic_metric_id,
            target_atomic_name_kr,
            metric_id,
            formula_type,
            execution_scope,
            applicable_company_scope,
            zero_division_policy,
            rounding_policy,
            result_table,
            output_unit,
            execution_order,
            yoy_direction_code
        FROM ESG_CALCULATION_RULE
        WHERE UPPER(COALESCE(execution_scope, '')) = ?
          AND active_yn = 1
          AND delete_yn = 0
          AND target_atomic_metric_id IN ({placeholders})
        ORDER BY COALESCE(execution_order, 0), calculation_rule_code
        """,
        (normalizeScope(executionScope), *cleaned),
    )
    return cur.fetchall() or []


# 계산 규칙 코드 기준 소스 지표 목록 조회
def listRuleSources(ruleCodes: list[str]) -> list[dict]:
    cleaned = cleanList(ruleCodes)
    if not cleaned:
        return []
    placeholders = ", ".join(["?"] * len(cleaned))
    return findAll(
        f"""
        SELECT
            id,
            calculation_rule_code,
            target_atomic_metric_id,
            source_atomic_metric_id,
            source_role,
            source_scope,
            source_metric_id
        FROM ESG_CALCULATION_RULE_SOURCE
        WHERE calculation_rule_code IN ({placeholders})
          AND delete_yn = 0
        ORDER BY calculation_rule_code, id
        """,
        tuple(cleaned),
    ) or []


# 계산 규칙 소스 목록 조회 (트랜잭션 커서용)
def listRuleSourcesTx(cur, ruleCodes: list[str]) -> list[dict]:
    cleaned = cleanList(ruleCodes)
    if not cleaned:
        return []
    placeholders = ", ".join(["?"] * len(cleaned))
    cur.execute(
        f"""
        SELECT
            id,
            calculation_rule_code,
            target_atomic_metric_id,
            source_atomic_metric_id,
            source_role,
            source_scope,
            source_metric_id
        FROM ESG_CALCULATION_RULE_SOURCE
        WHERE calculation_rule_code IN ({placeholders})
          AND delete_yn = 0
        ORDER BY calculation_rule_code, id
        """,
        tuple(cleaned),
    )
    return cur.fetchall() or []


# 기업·연도·원자 지표 기준 승인된 ENTITY Fact 목록 조회
def listApprovedEntityFacts(
    companyIds: list[int],
    reportingYear: int,
    atomicMetricIds: list[str],
) -> list[dict]:
    companyIds, atomicMetricIds = cleanFactInputs(companyIds, atomicMetricIds)
    if not companyIds or not atomicMetricIds:
        return []
    companyPlaceholders = ", ".join(["?"] * len(companyIds))
    atomicPlaceholders = ", ".join(["?"] * len(atomicMetricIds))
    return findAll(
        f"""
        SELECT
            id,
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
            approved_at
        FROM ESG_KPI_FACT
        WHERE company_id IN ({companyPlaceholders})
          AND reporting_year = ?
          AND atomic_metric_id IN ({atomicPlaceholders})
          AND UPPER(COALESCE(company_scope_type, 'ENTITY')) = 'ENTITY'
          AND LOWER(COALESCE(approval_status, '')) = 'approved'
          AND delete_yn = 0
        ORDER BY company_id, atomic_metric_id
        """,
        (*companyIds, reportingYear, *atomicMetricIds),
    ) or []


# 승인된 ENTITY Fact 목록 조회 (트랜잭션 커서용)
def listApprovedEntityFactsTx(
    cur,
    companyIds: list[int],
    reportingYear: int,
    atomicMetricIds: list[str],
) -> list[dict]:
    companyIds, atomicMetricIds = cleanFactInputs(companyIds, atomicMetricIds)
    if not companyIds or not atomicMetricIds:
        return []
    companyPlaceholders = ", ".join(["?"] * len(companyIds))
    atomicPlaceholders = ", ".join(["?"] * len(atomicMetricIds))
    cur.execute(
        f"""
        SELECT
            id,
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
            approved_at
        FROM ESG_KPI_FACT
        WHERE company_id IN ({companyPlaceholders})
          AND reporting_year = ?
          AND atomic_metric_id IN ({atomicPlaceholders})
          AND UPPER(COALESCE(company_scope_type, 'ENTITY')) = 'ENTITY'
          AND LOWER(COALESCE(approval_status, '')) = 'approved'
          AND delete_yn = 0
        ORDER BY company_id, atomic_metric_id
        """,
        (*companyIds, reportingYear, *atomicMetricIds),
    )
    return cur.fetchall() or []


# 전년도(reportingYear - 1) 승인 Fact 목록 조회
def listPriorYearFacts(
    companyIds: list[int],
    reportingYear: int,
    atomicMetricIds: list[str],
) -> list[dict]:
    return listApprovedEntityFacts(companyIds, reportingYear - 1, atomicMetricIds)


# 전년도 승인 Fact 목록 조회 (트랜잭션 커서용)
def listPriorYearFactsTx(
    cur,
    companyIds: list[int],
    reportingYear: int,
    atomicMetricIds: list[str],
) -> list[dict]:
    return listApprovedEntityFactsTx(cur, companyIds, reportingYear - 1, atomicMetricIds)


# 변경된 소스 원자 지표에 영향 받는 계산 규칙 목록 조회
def listAffectedRules(
    sourceAtomicMetricIds: list[str],
    executionScope: str = EXECUTION_SCOPE_ENTITY,
) -> list[dict]:
    cleaned = cleanList(sourceAtomicMetricIds)
    if not cleaned:
        return []
    placeholders = ", ".join(["?"] * len(cleaned))
    return findAll(
        f"""
        SELECT DISTINCT
            cr.id,
            cr.calculation_rule_code,
            cr.target_atomic_metric_id,
            cr.target_atomic_name_kr,
            cr.metric_id,
            cr.formula_type,
            cr.execution_scope,
            cr.applicable_company_scope,
            cr.zero_division_policy,
            cr.rounding_policy,
            cr.result_table,
            cr.output_unit,
            cr.execution_order,
            cr.yoy_direction_code
        FROM ESG_CALCULATION_RULE cr
        JOIN ESG_CALCULATION_RULE_SOURCE src
          ON src.calculation_rule_code = cr.calculation_rule_code
         AND src.delete_yn = 0
        WHERE UPPER(COALESCE(cr.execution_scope, '')) = ?
          AND cr.active_yn = 1
          AND cr.delete_yn = 0
          AND src.source_atomic_metric_id IN ({placeholders})
        ORDER BY COALESCE(cr.execution_order, 0), cr.calculation_rule_code
        """,
        (normalizeScope(executionScope), *cleaned),
    ) or []


# 영향 받는 계산 규칙 목록 조회 (트랜잭션 커서용)
def listAffectedRulesTx(
    cur,
    sourceAtomicMetricIds: list[str],
    executionScope: str = EXECUTION_SCOPE_ENTITY,
) -> list[dict]:
    cleaned = cleanList(sourceAtomicMetricIds)
    if not cleaned:
        return []
    placeholders = ", ".join(["?"] * len(cleaned))
    cur.execute(
        f"""
        SELECT DISTINCT
            cr.id,
            cr.calculation_rule_code,
            cr.target_atomic_metric_id,
            cr.target_atomic_name_kr,
            cr.metric_id,
            cr.formula_type,
            cr.execution_scope,
            cr.applicable_company_scope,
            cr.zero_division_policy,
            cr.rounding_policy,
            cr.result_table,
            cr.output_unit,
            cr.execution_order,
            cr.yoy_direction_code
        FROM ESG_CALCULATION_RULE cr
        JOIN ESG_CALCULATION_RULE_SOURCE src
          ON src.calculation_rule_code = cr.calculation_rule_code
         AND src.delete_yn = 0
        WHERE UPPER(COALESCE(cr.execution_scope, '')) = ?
          AND cr.active_yn = 1
          AND cr.delete_yn = 0
          AND src.source_atomic_metric_id IN ({placeholders})
        ORDER BY COALESCE(cr.execution_order, 0), cr.calculation_rule_code
        """,
        (normalizeScope(executionScope), *cleaned),
    )
    return cur.fetchall() or []


# 계산 엔진 결과 Fact upsert 저장 — 미완료 결과 포함 시 ValueError (트랜잭션용)
def upsertCalculatedEntityFactsTx(
    cur,
    *,
    companyId: int,
    reportingYear: int,
    results: list[dict],
    actorUserId: Optional[int] = None,
) -> int:
    if not results:
        return 0
    for result in results:
        if str(result.get("calculationStatus") or "").upper() != "CALCULATED":
            raise ValueError(
                "CALCULATION_RESULTS_NOT_READY: all results must be CALCULATED before saving, "
                f"found {result.get('calculationStatus')} for {result.get('targetAtomicMetricId')}"
            )
    savedCount = 0
    for result in results:
        if not result.get("targetAtomicMetricId"):
            continue
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
            ) VALUES (NULL, ?, ?, 'ENTITY', ?, ?, ?, ?, ?, ?, 'approved', ?, CURRENT_TIMESTAMP, 0)
            ON DUPLICATE KEY UPDATE
                source_input_value_id = NULL,
                company_scope_type = 'ENTITY',
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
                companyId,
                reportingYear,
                result.get("metricId"),
                result.get("targetAtomicMetricId"),
                result.get("valueNumeric"),
                result.get("valueText"),
                result.get("unit"),
                VALUE_SOURCE_TYPE_CALCULATION_ENGINE,
                actorUserId,
            ),
        )
        savedCount += 1
    return savedCount


# 계산 엔진 생성 Fact 무효화 소프트 삭제 (트랜잭션용)
def invalidateCalculatedEntityFactsTx(
    cur,
    *,
    companyId: int,
    reportingYear: int,
    atomicMetricIds: list[str],
) -> int:
    cleaned = cleanList(atomicMetricIds)
    if not cleaned:
        return 0
    placeholders = ", ".join(["?"] * len(cleaned))
    cur.execute(
        f"""
        UPDATE ESG_KPI_FACT
        SET approval_status = 'invalidated',
            delete_yn = 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE company_id = ?
          AND reporting_year = ?
          AND atomic_metric_id IN ({placeholders})
          AND value_source_type = ?
          AND UPPER(COALESCE(company_scope_type, 'ENTITY')) = 'ENTITY'
          AND LOWER(COALESCE(approval_status, '')) = 'approved'
          AND delete_yn = 0
        """,
        (companyId, reportingYear, *cleaned, VALUE_SOURCE_TYPE_CALCULATION_ENGINE),
    )
    return max(0, int(cur.rowcount or 0))


# metric_id IN (...) 필터 SQL 조각 및 파라미터 생성
def buildMetricFilter(metricIds: Optional[list[str]]) -> tuple[str, list[str]]:
    cleaned = cleanList(metricIds or [])
    if not cleaned:
        return "", []
    placeholders = ", ".join(["?"] * len(cleaned))
    return f"AND metric_id IN ({placeholders})", cleaned


# 문자열 목록 공백 제거 및 중복 제거
def cleanList(values: list) -> list:
    cleaned = []
    for value in values or []:
        normalized = str(value).strip()
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


# Fact 조회용 companyId·atomicMetricId 목록 정규화
def cleanFactInputs(companyIds: list[int], atomicMetricIds: list[str]) -> tuple[list[int], list[str]]:
    cleanedCompanyIds = []
    for companyId in companyIds or []:
        try:
            value = int(companyId)
        except (TypeError, ValueError):
            continue
        if value not in cleanedCompanyIds:
            cleanedCompanyIds.append(value)
    return cleanedCompanyIds, cleanList(atomicMetricIds)


# execution scope 대문자 정규화
def normalizeScope(executionScope: str) -> str:
    return str(executionScope or EXECUTION_SCOPE_ENTITY).strip().upper()


__all__ = [
    "EXECUTION_SCOPE_ENTITY",
    "EXECUTION_SCOPE_CONSOLIDATED",
    "VALUE_SOURCE_TYPE_CALCULATION_ENGINE",
    "APPROVAL_STATUS_APPROVED",
    "listActiveRules",
    "listActiveRulesTx",
    "listActiveRulesByTargetAtomicIds",
    "listActiveRulesByTargetAtomicIdsTx",
    "listRuleSources",
    "listRuleSourcesTx",
    "listApprovedEntityFacts",
    "listApprovedEntityFactsTx",
    "listPriorYearFacts",
    "listPriorYearFactsTx",
    "listAffectedRules",
    "listAffectedRulesTx",
    "upsertCalculatedEntityFactsTx",
    "invalidateCalculatedEntityFactsTx",
]
