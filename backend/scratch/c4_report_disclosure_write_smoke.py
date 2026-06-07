from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PARENT_COMPANY_ID = 6
SOURCE_COMPANY_IDS = [6, 7, 8, 9]
REQUEST_SOURCE_COMPANY_IDS = [7, 8, 9]
REPORTING_YEAR = 2024
SOURCE_TEMPLATE_CYCLE_ID = 17
MARKER = "C4_REPORT_DISCLOSURE_SMOKE_2024"

ROLLUP_PURPOSE_CODE = "REPORT_DISCLOSURE"
METRIC_SCOPE_CODE = "SELECTED_DISCLOSURE"
POST_DMA_CYCLE_TYPE = "POST_DMA_DISCLOSURE"
ROLLUP_CYCLE_TYPE = "ROLLUP"
ROLLUP_SCOPE_CODE = "ROLLUP_SCOPE"
PROMOTE_AND_ROLLUP_POLICY = "PROMOTE_TO_KPI_FACT_AND_ROLLUP"
ROLLUP_READONLY_POLICY = "ROLLUP_READONLY"


def dump_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"MANIFEST_NOT_FOUND: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def model_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    raise TypeError(f"Unsupported response type: {type(value)!r}")


def response_data(value: Any) -> dict[str, Any]:
    data = model_to_dict(value).get("data")
    if data is None:
        raise RuntimeError(f"RESPONSE_DATA_NOT_FOUND: {value!r}")
    return data


def user_model(company_id: int, user_id: int | None = None) -> dict[str, Any]:
    return {
        "id": user_id,
        "companyId": int(company_id),
        "company_id": int(company_id),
        "role": "ESG",
        "role_name": "ESG담당자",
    }


def get_conn():
    from src.utils.db import getConn

    conn = getConn()
    if not conn:
        raise RuntimeError("DB_CONNECTION_FAILED")
    return conn


def fetch_one(cur, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    cur.execute(sql, params)
    return cur.fetchone() or {}


def fetch_all(cur, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    return cur.fetchall() or []


def count_one(cur, sql: str, params: tuple[Any, ...] = ()) -> int:
    row = fetch_one(cur, sql, params)
    if not row:
        return 0
    return int(next(iter(row.values())) or 0)


def placeholder(values: list[Any]) -> str:
    if not values:
        raise RuntimeError("EMPTY_PLACEHOLDER_VALUES")
    return ", ".join(["?"] * len(values))


def historical_counts(cur) -> dict[str, int]:
    batch_count = count_one(
        cur,
        """
        SELECT COUNT(*) AS row_count
        FROM ESG_ROLLUP_BATCH
        WHERE parent_company_id = ?
          AND reporting_year < ?
          AND rollup_purpose_code = ?
          AND delete_yn = 0
        """,
        (PARENT_COMPANY_ID, REPORTING_YEAR, ROLLUP_PURPOSE_CODE),
    )
    result_count = count_one(
        cur,
        """
        SELECT COUNT(*) AS row_count
        FROM ESG_GROUP_ROLLUP_RESULT r
        JOIN ESG_ROLLUP_BATCH b
          ON b.id = r.esg_rollup_batch_id
         AND b.delete_yn = 0
        WHERE b.parent_company_id = ?
          AND b.reporting_year < ?
          AND b.rollup_purpose_code = ?
          AND r.delete_yn = 0
        """,
        (PARENT_COMPANY_ID, REPORTING_YEAR, ROLLUP_PURPOSE_CODE),
    )
    return {
        "historicalReportDisclosureBatchCount": batch_count,
        "historicalGroupRollupResultCount": result_count,
    }


def existing_post_dma_cycle_count(cur) -> int:
    return count_one(
        cur,
        """
        SELECT COUNT(*) AS row_count
        FROM ESG_ONBOARDING_CYCLE
        WHERE company_id = ?
          AND reporting_year = ?
          AND cycle_type = ?
          AND delete_yn = 0
        """,
        (PARENT_COMPANY_ID, REPORTING_YEAR, POST_DMA_CYCLE_TYPE),
    )


def existing_report_batch_count(cur) -> int:
    return count_one(
        cur,
        """
        SELECT COUNT(*) AS row_count
        FROM ESG_ROLLUP_BATCH
        WHERE parent_company_id = ?
          AND reporting_year = ?
          AND rollup_purpose_code = ?
          AND delete_yn = 0
        """,
        (PARENT_COMPANY_ID, REPORTING_YEAR, ROLLUP_PURPOSE_CODE),
    )


def existing_rollup_cycle_count(cur) -> int:
    return count_one(
        cur,
        """
        SELECT COUNT(*) AS row_count
        FROM ESG_ONBOARDING_CYCLE
        WHERE company_id = ?
          AND reporting_year = ?
          AND cycle_type = ?
          AND delete_yn = 0
        """,
        (PARENT_COMPANY_ID, REPORTING_YEAR, ROLLUP_CYCLE_TYPE),
    )


def list_effective_rollup_relations(cur) -> list[int]:
    rows = fetch_all(
        cur,
        """
        SELECT DISTINCT source_company_id
        FROM ESG_COMPANY_ROLLUP_SCOPE
        WHERE parent_company_id = ?
          AND rollup_include_yn = 1
          AND delete_yn = 0
          AND (effective_from_year IS NULL OR effective_from_year <= ?)
          AND (effective_to_year IS NULL OR effective_to_year >= ?)
        ORDER BY source_company_id
        """,
        (PARENT_COMPANY_ID, REPORTING_YEAR, REPORTING_YEAR),
    )
    return [int(row["source_company_id"]) for row in rows]


def list_rollup_capable_metrics(cur) -> list[str]:
    rows = fetch_all(
        cur,
        """
        SELECT DISTINCT s.metric_id
        FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE s
        JOIN ESG_CALCULATION_RULE cr
          ON cr.metric_id = s.metric_id
         AND cr.active_yn = 1
         AND cr.delete_yn = 0
         AND UPPER(COALESCE(cr.execution_scope, 'CONSOLIDATED')) = 'CONSOLIDATED'
        WHERE s.esg_onboarding_cycle_id = ?
          AND s.company_id = ?
          AND s.active_yn = 1
          AND s.delete_yn = 0
        ORDER BY s.metric_id
        """,
        (SOURCE_TEMPLATE_CYCLE_ID, PARENT_COMPANY_ID),
    )
    return [row["metric_id"] for row in rows if row.get("metric_id")]


def direct_rule_snapshot(metric_ids: list[str]) -> dict[str, Any]:
    from src.utils.calculationengine import normalizeSource
    from src.utils.calculationrepository import listActiveRules, listRuleSources

    rules = listActiveRules(executionScope="CONSOLIDATED", metricIds=metric_ids)
    rule_codes = sorted({
        str(rule.get("calculation_rule_code") or "").strip()
        for rule in rules
        if str(rule.get("calculation_rule_code") or "").strip()
    })
    sources = listRuleSources(rule_codes)
    target_atomic_ids = {
        str(rule.get("target_atomic_metric_id") or "").strip()
        for rule in rules
        if str(rule.get("target_atomic_metric_id") or "").strip()
    }
    source_atomic_ids = {
        normalizeSource(source).get("sourceAtomicMetricId")
        for source in sources
        if normalizeSource(source).get("sourceAtomicMetricId")
    }
    return {
        "directRules": rules,
        "directRuleSources": sources,
        "directExternalEntityAtomicIds": sorted(source_atomic_ids - target_atomic_ids),
    }


def resolve_closure(metric_ids: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    from src.utils.calculationengine import normalizeSource
    from src.utils.rollupscoperepository import resolveConsolidatedRuleClosure

    rules, sources = resolveConsolidatedRuleClosure(metric_ids)
    target_atomic_ids = {
        str(rule.get("target_atomic_metric_id") or "").strip()
        for rule in rules
        if str(rule.get("target_atomic_metric_id") or "").strip()
    }
    source_atomic_ids = {
        normalizeSource(source).get("sourceAtomicMetricId")
        for source in sources
        if normalizeSource(source).get("sourceAtomicMetricId")
    }
    external_atomic_ids = sorted(source_atomic_ids - target_atomic_ids)
    return rules, sources, external_atomic_ids


def closure_snapshot(metric_ids: list[str]) -> dict[str, Any]:
    direct = direct_rule_snapshot(metric_ids)
    resolved_rules, resolved_sources, resolved_external_atomic_ids = resolve_closure(metric_ids)
    direct_rule_count = len(direct["directRules"])
    direct_external_count = len(direct["directExternalEntityAtomicIds"])
    resolved_rule_count = len(resolved_rules)
    resolved_source_count = len(resolved_sources)
    resolved_external_count = len(resolved_external_atomic_ids)

    if (
        resolved_rule_count < direct_rule_count
        or resolved_external_count < direct_external_count
        or resolved_rule_count <= 0
        or resolved_source_count <= 0
        or resolved_external_count <= 0
    ):
        raise RuntimeError(
            "PRECHECK_CLOSURE_INVALID: "
            f"directRuleCount={direct_rule_count}, "
            f"directExternalEntityAtomicCount={direct_external_count}, "
            f"resolvedRuleCount={resolved_rule_count}, "
            f"resolvedRuleSourceCount={resolved_source_count}, "
            f"resolvedExternalEntityAtomicCount={resolved_external_count}"
        )

    return {
        "directRuleCount": direct_rule_count,
        "directExternalEntityAtomicCount": direct_external_count,
        "resolvedRules": resolved_rules,
        "resolvedRuleSources": resolved_sources,
        "resolvedExternalEntityAtomicIds": resolved_external_atomic_ids,
        "resolvedRuleCount": resolved_rule_count,
        "resolvedRuleSourceCount": resolved_source_count,
        "resolvedExternalEntityAtomicCount": resolved_external_count,
        "closureAddedRuleCount": resolved_rule_count - direct_rule_count,
        "closureAddedExternalAtomicCount": resolved_external_count - direct_external_count,
    }


def source_readiness(cur, atomic_metric_ids: list[str]) -> dict[str, Any]:
    if not atomic_metric_ids:
        return {
            "readyYn": False,
            "missingByCompany": {str(company_id): [] for company_id in SOURCE_COMPANY_IDS},
            "approvedFactCount": 0,
            "requiredFactCount": 0,
        }
    placeholders = placeholder(atomic_metric_ids)
    company_placeholders = placeholder(SOURCE_COMPANY_IDS)
    rows = fetch_all(
        cur,
        f"""
        SELECT company_id, atomic_metric_id
        FROM ESG_KPI_FACT
        WHERE company_id IN ({company_placeholders})
          AND reporting_year = ?
          AND atomic_metric_id IN ({placeholders})
          AND UPPER(COALESCE(company_scope_type, 'ENTITY')) = 'ENTITY'
          AND LOWER(COALESCE(approval_status, '')) = 'approved'
          AND delete_yn = 0
        ORDER BY company_id, atomic_metric_id
        """,
        (*SOURCE_COMPANY_IDS, REPORTING_YEAR, *atomic_metric_ids),
    )
    approved_keys = {(int(row["company_id"]), row["atomic_metric_id"]) for row in rows}
    missing_by_company: dict[str, list[str]] = {}
    approved_by_company: dict[str, int] = {}
    for company_id in SOURCE_COMPANY_IDS:
        missing_by_company[str(company_id)] = [
            atomic_id for atomic_id in atomic_metric_ids if (company_id, atomic_id) not in approved_keys
        ]
        approved_by_company[str(company_id)] = len(atomic_metric_ids) - len(missing_by_company[str(company_id)])
    return {
        "readyYn": all(not items for items in missing_by_company.values()),
        "missingByCompany": missing_by_company,
        "companyReadiness": {
            str(company_id): {
                "requiredAtomicCount": len(atomic_metric_ids),
                "approvedAtomicCount": approved_by_company[str(company_id)],
                "missingAtomicMetricIds": missing_by_company[str(company_id)],
            }
            for company_id in SOURCE_COMPANY_IDS
        },
        "approvedFactCount": len(approved_keys),
        "requiredFactCount": len(atomic_metric_ids) * len(SOURCE_COMPANY_IDS),
    }


def decode_atomic_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw_value = str(value).strip()
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except Exception:
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [str(parsed).strip()] if str(parsed).strip() else []


def batch_scope_snapshot(cur, batch_id: int) -> dict[str, int]:
    rows = fetch_all(
        cur,
        """
        SELECT metric_id, group_atomic_metric_id, source_atomic_metric_ids
        FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE
        WHERE esg_rollup_batch_id = ?
          AND delete_yn = 0
        """,
        (batch_id,),
    )
    metric_ids = {str(row.get("metric_id") or "").strip() for row in rows if row.get("metric_id")}
    group_atomic_ids = {
        str(row.get("group_atomic_metric_id") or "").strip()
        for row in rows
        if row.get("group_atomic_metric_id")
    }
    source_atomic_ids = set()
    for row in rows:
        for atomic_id in decode_atomic_ids(row.get("source_atomic_metric_ids")):
            source_atomic_ids.add(atomic_id)
    return {
        "rowCount": len(rows),
        "distinctMetricCount": len(metric_ids),
        "distinctGroupAtomicCount": len(group_atomic_ids),
        "externalSourceAtomicCount": len(source_atomic_ids - group_atomic_ids),
    }


def run_preflight(cur) -> dict[str, Any]:
    post_dma_count = existing_post_dma_cycle_count(cur)
    if post_dma_count:
        raise RuntimeError("PRECHECK_POST_DMA_CYCLE_ALREADY_EXISTS")

    batch_count = existing_report_batch_count(cur)
    if batch_count:
        raise RuntimeError("PRECHECK_REPORT_DISCLOSURE_BATCH_ALREADY_EXISTS")

    rollup_count = existing_rollup_cycle_count(cur)
    if rollup_count:
        raise RuntimeError("PRECHECK_ROLLUP_CYCLE_ALREADY_EXISTS")

    relation_ids = list_effective_rollup_relations(cur)
    missing_relation_ids = [company_id for company_id in SOURCE_COMPANY_IDS if company_id not in relation_ids]
    if missing_relation_ids:
        raise RuntimeError(f"PRECHECK_ROLLUP_RELATION_NOT_READY: {missing_relation_ids}")

    direct_metric_ids = list_rollup_capable_metrics(cur)
    if not direct_metric_ids:
        raise RuntimeError("PRECHECK_ROLLUP_CAPABLE_METRIC_NOT_FOUND")

    closure = closure_snapshot(direct_metric_ids)

    readiness = source_readiness(cur, closure["resolvedExternalEntityAtomicIds"])
    if not readiness["readyYn"]:
        raise RuntimeError(f"PRECHECK_SOURCE_NOT_READY: {readiness['missingByCompany']}")

    return {
        "status": "PREFLIGHT_OK",
        "marker": MARKER,
        "parentCompanyId": PARENT_COMPANY_ID,
        "sourceCompanyIds": SOURCE_COMPANY_IDS,
        "requestSourceCompanyIds": REQUEST_SOURCE_COMPANY_IDS,
        "reportingYear": REPORTING_YEAR,
        "sourceTemplateCycleId": SOURCE_TEMPLATE_CYCLE_ID,
        "directMetricIds": direct_metric_ids,
        "directMetricCount": len(direct_metric_ids),
        "directRuleCount": closure["directRuleCount"],
        "directExternalEntityAtomicCount": closure["directExternalEntityAtomicCount"],
        "resolvedRuleCount": closure["resolvedRuleCount"],
        "resolvedRuleSourceCount": closure["resolvedRuleSourceCount"],
        "resolvedExternalEntityAtomicCount": closure["resolvedExternalEntityAtomicCount"],
        "closureAddedRuleCount": closure["closureAddedRuleCount"],
        "closureAddedExternalAtomicCount": closure["closureAddedExternalAtomicCount"],
        "sourceReadiness": readiness,
        "historicalCountsBefore": historical_counts(cur),
    }


def preflight(manifest_path: Path) -> None:
    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
            manifest = run_preflight(cur)
        dump_json(manifest)
    finally:
        conn.close()


def insert_test_cycle_and_scope(cur, direct_metric_ids: list[str]) -> int:
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
            parent_rollup_batch_id,
            created_by_user_id,
            delete_yn
        ) VALUES (?, ?, ?, ?, 'CONSOLIDATED', 0, 'approved', NULL, ?, NULL, NULL, 0)
        """,
        (PARENT_COMPANY_ID, REPORTING_YEAR, MARKER, POST_DMA_CYCLE_TYPE, METRIC_SCOPE_CODE),
    )
    cycle_id = int(cur.lastrowid)
    metric_placeholders = placeholder(direct_metric_ids)
    cur.execute(
        f"""
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
        )
        SELECT
            ?,
            company_id,
            metric_id,
            scope_source_type,
            source_materiality_run_id,
            source_selected_sub_issue_id,
            source_sub_issue_code,
            required_yn,
            input_required_yn,
            approval_required_yn,
            ?,
            0,
            display_order,
            1,
            created_by_user_id,
            0
        FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
        WHERE esg_onboarding_cycle_id = ?
          AND company_id = ?
          AND metric_id IN ({metric_placeholders})
          AND active_yn = 1
          AND delete_yn = 0
        ORDER BY display_order, metric_id
        """,
        (cycle_id, PROMOTE_AND_ROLLUP_POLICY, SOURCE_TEMPLATE_CYCLE_ID, PARENT_COMPANY_ID, *direct_metric_ids),
    )
    inserted_scope_count = int(cur.rowcount or 0)
    if inserted_scope_count != len(direct_metric_ids):
        raise RuntimeError(
            "TEST_SCOPE_INSERT_COUNT_MISMATCH: "
            f"inserted={inserted_scope_count}, expected={len(direct_metric_ids)}"
        )
    return cycle_id


def execute(manifest_path: Path) -> None:
    from src.models.rollup import RollupBatchRequestDto
    from src.services.rollups.service import calcBatch, getStatus, saveBatch, sendSource

    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
            manifest = run_preflight(cur)
            test_cycle_id = insert_test_cycle_and_scope(cur, manifest["directMetricIds"])
            manifest["testPostDmaCycleId"] = test_cycle_id
        conn.commit()
        write_manifest(manifest_path, manifest)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    parent_user = user_model(PARENT_COMPANY_ID)
    request = RollupBatchRequestDto(
        sourceCycleId=test_cycle_id,
        sourceCompanyIds=REQUEST_SOURCE_COMPANY_IDS,
        rollupPurposeCode=ROLLUP_PURPOSE_CODE,
        metricScopeCode=METRIC_SCOPE_CODE,
    )
    batch_response = saveBatch(request, parent_user)
    batch_id = int(response_data(batch_response)["batchId"])

    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
            scope_after_save = batch_scope_snapshot(cur, batch_id)
    finally:
        conn.close()

    manifest = read_manifest(manifest_path)
    manifest["batchId"] = batch_id
    manifest["batchScopeAfterSave"] = scope_after_save
    write_manifest(manifest_path, manifest)

    for source_company_id in REQUEST_SOURCE_COMPANY_IDS:
        sendSource(batch_id, user_model(source_company_id))

    status_response = getStatus(batch_id, parent_user)
    calc_response = calcBatch(batch_id, parent_user)

    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
            rollup_cycle = fetch_one(
                cur,
                """
                SELECT id
                FROM ESG_ONBOARDING_CYCLE
                WHERE parent_rollup_batch_id = ?
                  AND cycle_type = ?
                  AND delete_yn = 0
                ORDER BY id DESC
                LIMIT 1
                """,
                (batch_id, ROLLUP_CYCLE_TYPE),
            )
        manifest = read_manifest(manifest_path)
        manifest["rollupCycleId"] = int(rollup_cycle["id"]) if rollup_cycle else None
        write_manifest(manifest_path, manifest)
    finally:
        conn.close()

    dump_json(
        {
            "status": "EXECUTE_OK",
            "manifest": str(manifest_path),
            "testPostDmaCycleId": test_cycle_id,
            "batchId": batch_id,
            "rollupCycleId": manifest.get("rollupCycleId"),
            "batchScopeAfterSave": scope_after_save,
            "statusResponse": model_to_dict(status_response),
            "calcResultCount": len(response_data(calc_response).get("results") or []),
        }
    )


def verify(manifest_path: Path) -> None:
    manifest = read_manifest(manifest_path)
    test_cycle_id = int(manifest["testPostDmaCycleId"])
    batch_id = int(manifest["batchId"])
    rollup_cycle_id_raw = manifest.get("rollupCycleId")
    rollup_cycle_id = int(rollup_cycle_id_raw) if rollup_cycle_id_raw is not None else None

    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
            test_cycle = fetch_one(
                cur,
                """
                SELECT id, company_id, reporting_year, cycle_type, cycle_name, metric_scope_code, cycle_status
                FROM ESG_ONBOARDING_CYCLE
                WHERE id = ?
                  AND cycle_name = ?
                  AND cycle_type = ?
                  AND delete_yn = 0
                """,
                (test_cycle_id, MARKER, POST_DMA_CYCLE_TYPE),
            )
            test_scope_count = count_one(
                cur,
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
                WHERE esg_onboarding_cycle_id = ?
                  AND company_id = ?
                  AND active_yn = 1
                  AND delete_yn = 0
                """,
                (test_cycle_id, PARENT_COMPANY_ID),
            )
            batch = fetch_one(
                cur,
                """
                SELECT id, source_cycle_id, batch_status, rollup_purpose_code, metric_scope_code,
                       dma_ready_yn, report_ready_yn
                FROM ESG_ROLLUP_BATCH
                WHERE id = ?
                  AND source_cycle_id = ?
                  AND rollup_purpose_code = ?
                  AND reporting_year = ?
                  AND delete_yn = 0
                """,
                (batch_id, test_cycle_id, ROLLUP_PURPOSE_CODE, REPORTING_YEAR),
            )
            batch_scope = fetch_one(
                cur,
                """
                SELECT
                    COUNT(*) AS row_count,
                    COUNT(DISTINCT metric_id) AS metric_count,
                    COUNT(DISTINCT group_atomic_metric_id) AS group_atomic_count
                FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE
                WHERE esg_rollup_batch_id = ?
                  AND delete_yn = 0
                """,
                (batch_id,),
            )
            source_status = fetch_one(
                cur,
                """
                SELECT
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN transfer_status = 'received' THEN 1 ELSE 0 END) AS received_count,
                    SUM(
                        CASE
                            WHEN missing_atomic_metric_ids_json IS NOT NULL
                             AND missing_atomic_metric_ids_json <> ''
                            THEN 1 ELSE 0
                        END
                    ) AS missing_count
                FROM ESG_ROLLUP_SOURCE_STATUS
                WHERE esg_rollup_batch_id = ?
                  AND delete_yn = 0
                """,
                (batch_id,),
            )
            group_results = fetch_one(
                cur,
                """
                SELECT
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN rollup_status = 'approved' THEN 1 ELSE 0 END) AS approved_count,
                    COUNT(DISTINCT group_atomic_metric_id) AS group_atomic_count
                FROM ESG_GROUP_ROLLUP_RESULT
                WHERE esg_rollup_batch_id = ?
                  AND delete_yn = 0
                """,
                (batch_id,),
            )
            if rollup_cycle_id is not None:
                rollup_cycle = fetch_one(
                    cur,
                    """
                    SELECT id, parent_rollup_batch_id, metric_scope_code, cycle_status
                    FROM ESG_ONBOARDING_CYCLE
                    WHERE id = ?
                      AND parent_rollup_batch_id = ?
                      AND cycle_type = ?
                      AND delete_yn = 0
                    """,
                    (rollup_cycle_id, batch_id, ROLLUP_CYCLE_TYPE),
                )
                rollup_scope = fetch_one(
                    cur,
                    """
                    SELECT
                        COUNT(*) AS total_count,
                        SUM(CASE WHEN approval_policy_code = ? THEN 1 ELSE 0 END) AS readonly_policy_count,
                        SUM(CASE WHEN rollup_readonly_yn = 1 THEN 1 ELSE 0 END) AS readonly_yn_count
                    FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
                    WHERE esg_onboarding_cycle_id = ?
                      AND company_id = ?
                      AND active_yn = 1
                      AND delete_yn = 0
                    """,
                    (ROLLUP_READONLY_POLICY, rollup_cycle_id, PARENT_COMPANY_ID),
                )
            else:
                rollup_cycle = {}
                rollup_scope = {
                    "total_count": 0,
                    "readonly_policy_count": 0,
                    "readonly_yn_count": 0,
                }
            after_historical = historical_counts(cur)
    finally:
        conn.close()

    current_closure = closure_snapshot(manifest["directMetricIds"])
    closure_matches_manifest = all(
        int(manifest.get(field) or 0) == int(current_closure[field])
        for field in [
            "directRuleCount",
            "directExternalEntityAtomicCount",
            "resolvedRuleCount",
            "resolvedRuleSourceCount",
            "resolvedExternalEntityAtomicCount",
        ]
    )
    expected_rule_count = int(manifest["resolvedRuleCount"])
    write_smoke_ok = all(
        [
            closure_matches_manifest,
            bool(test_cycle),
            test_scope_count == len(manifest["directMetricIds"]),
            batch.get("batch_status") == "completed",
            int(batch.get("report_ready_yn") or 0) == 1,
            int(batch.get("dma_ready_yn") or 0) == 0,
            int(source_status.get("total_count") or 0) == len(SOURCE_COMPANY_IDS),
            int(source_status.get("received_count") or 0) == len(SOURCE_COMPANY_IDS),
            int(source_status.get("missing_count") or 0) == 0,
            int(group_results.get("total_count") or 0) == expected_rule_count,
            int(group_results.get("approved_count") or 0) == expected_rule_count,
            bool(rollup_cycle),
            rollup_scope.get("total_count") == rollup_scope.get("readonly_policy_count"),
            rollup_scope.get("total_count") == rollup_scope.get("readonly_yn_count"),
            manifest.get("historicalCountsBefore") == after_historical,
        ]
    )
    dump_json(
        {
            "status": "WRITE_SMOKE_OK" if write_smoke_ok else "WRITE_SMOKE_FAILED",
            "testCycle": test_cycle,
            "testScopeCount": test_scope_count,
            "batch": batch,
            "batchAtomicScope": batch_scope,
            "sourceStatus": source_status,
            "groupResults": group_results,
            "rollupCycle": rollup_cycle,
            "rollupReadonlyScope": rollup_scope,
            "closureMatchesManifest": closure_matches_manifest,
            "currentClosureSnapshot": {
                "directRuleCount": current_closure["directRuleCount"],
                "directExternalEntityAtomicCount": current_closure["directExternalEntityAtomicCount"],
                "resolvedRuleCount": current_closure["resolvedRuleCount"],
                "resolvedRuleSourceCount": current_closure["resolvedRuleSourceCount"],
                "resolvedExternalEntityAtomicCount": current_closure["resolvedExternalEntityAtomicCount"],
            },
            "historicalCountsBefore": manifest.get("historicalCountsBefore"),
            "historicalCountsAfter": after_historical,
        }
    )


def cleanup(manifest_path: Path) -> None:
    manifest = read_manifest(manifest_path)
    test_cycle_id = int(manifest["testPostDmaCycleId"])
    batch_id = int(manifest["batchId"])
    rollup_cycle_id_raw = manifest.get("rollupCycleId")
    rollup_cycle_id = int(rollup_cycle_id_raw) if rollup_cycle_id_raw is not None else None

    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
            test_cycle = fetch_one(
                cur,
                """
                SELECT id
                FROM ESG_ONBOARDING_CYCLE
                WHERE id = ?
                  AND cycle_name = ?
                  AND cycle_type = ?
                  AND delete_yn = 0
                """,
                (test_cycle_id, MARKER, POST_DMA_CYCLE_TYPE),
            )
            batch = fetch_one(
                cur,
                """
                SELECT id
                FROM ESG_ROLLUP_BATCH
                WHERE id = ?
                  AND source_cycle_id = ?
                  AND rollup_purpose_code = ?
                  AND reporting_year = ?
                  AND delete_yn = 0
                """,
                (batch_id, test_cycle_id, ROLLUP_PURPOSE_CODE, REPORTING_YEAR),
            )
            if rollup_cycle_id is not None:
                rollup_cycle = fetch_one(
                    cur,
                    """
                    SELECT id
                    FROM ESG_ONBOARDING_CYCLE
                    WHERE id = ?
                      AND parent_rollup_batch_id = ?
                      AND cycle_type = ?
                      AND delete_yn = 0
                    """,
                    (rollup_cycle_id, batch_id, ROLLUP_CYCLE_TYPE),
                )
            else:
                rollup_cycle = fetch_one(
                    cur,
                    """
                    SELECT id
                    FROM ESG_ONBOARDING_CYCLE
                    WHERE parent_rollup_batch_id = ?
                      AND cycle_type = ?
                      AND delete_yn = 0
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (batch_id, ROLLUP_CYCLE_TYPE),
                )
                rollup_cycle_id = int(rollup_cycle["id"]) if rollup_cycle else None
            if not test_cycle or not batch:
                raise RuntimeError("CLEANUP_GUARD_FAILED")

            if rollup_cycle_id is not None:
                cur.execute(
                    """
                    DELETE FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
                    WHERE esg_onboarding_cycle_id IN (?, ?)
                    """,
                    (test_cycle_id, rollup_cycle_id),
                )
            else:
                cur.execute(
                    """
                    DELETE FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
                    WHERE esg_onboarding_cycle_id = ?
                    """,
                    (test_cycle_id,),
                )
            cur.execute("DELETE FROM ESG_GROUP_ROLLUP_RESULT WHERE esg_rollup_batch_id = ?", (batch_id,))
            cur.execute("DELETE FROM ESG_ROLLUP_SOURCE_STATUS WHERE esg_rollup_batch_id = ?", (batch_id,))
            cur.execute("DELETE FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE WHERE esg_rollup_batch_id = ?", (batch_id,))
            if rollup_cycle_id is not None:
                cur.execute(
                    """
                    DELETE FROM ESG_ONBOARDING_CYCLE
                    WHERE id = ?
                      AND parent_rollup_batch_id = ?
                      AND cycle_type = ?
                    """,
                    (rollup_cycle_id, batch_id, ROLLUP_CYCLE_TYPE),
                )
            cur.execute(
                """
                DELETE FROM ESG_ROLLUP_BATCH
                WHERE id = ?
                  AND source_cycle_id = ?
                  AND rollup_purpose_code = ?
                """,
                (batch_id, test_cycle_id, ROLLUP_PURPOSE_CODE),
            )
            cur.execute(
                """
                DELETE FROM ESG_ONBOARDING_CYCLE
                WHERE id = ?
                  AND cycle_name = ?
                  AND cycle_type = ?
                """,
                (test_cycle_id, MARKER, POST_DMA_CYCLE_TYPE),
            )

            remaining = {
                "cycleMetricScope": count_one(
                    cur,
                    "SELECT COUNT(*) AS row_count FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE WHERE esg_onboarding_cycle_id IN (?, ?)",
                    (test_cycle_id, rollup_cycle_id or 0),
                ),
                "groupRollupResult": count_one(
                    cur,
                    "SELECT COUNT(*) AS row_count FROM ESG_GROUP_ROLLUP_RESULT WHERE esg_rollup_batch_id = ?",
                    (batch_id,),
                ),
                "sourceStatus": count_one(
                    cur,
                    "SELECT COUNT(*) AS row_count FROM ESG_ROLLUP_SOURCE_STATUS WHERE esg_rollup_batch_id = ?",
                    (batch_id,),
                ),
                "batchAtomicScope": count_one(
                    cur,
                    "SELECT COUNT(*) AS row_count FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE WHERE esg_rollup_batch_id = ?",
                    (batch_id,),
                ),
                "rollupCycle": count_one(
                    cur,
                    "SELECT COUNT(*) AS row_count FROM ESG_ONBOARDING_CYCLE WHERE id = ?",
                    (rollup_cycle_id,),
                ),
                "rollupBatch": count_one(
                    cur,
                    "SELECT COUNT(*) AS row_count FROM ESG_ROLLUP_BATCH WHERE id = ?",
                    (batch_id,),
                ),
                "testPostDmaCycle": count_one(
                    cur,
                    "SELECT COUNT(*) AS row_count FROM ESG_ONBOARDING_CYCLE WHERE id = ?",
                    (test_cycle_id,),
                ),
            }
            if any(remaining.values()):
                raise RuntimeError(f"CLEANUP_REMAINING_ROWS: {remaining}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    manifest_path.unlink(missing_ok=True)
    dump_json({"status": "CLEANUP_OK", "remaining": remaining, "manifestDeletedYn": not manifest_path.exists()})


def main() -> None:
    parser = argparse.ArgumentParser(description="C4 REPORT_DISCLOSURE write smoke")
    parser.add_argument("--mode", choices=["preflight", "execute", "verify", "cleanup"], required=True)
    parser.add_argument("--manifest", default="/workspace/c4_report_disclosure_manifest.json")
    args = parser.parse_args()
    manifest_path = Path(args.manifest)

    if args.mode == "preflight":
        preflight(manifest_path)
    elif args.mode == "execute":
        execute(manifest_path)
    elif args.mode == "verify":
        verify(manifest_path)
    elif args.mode == "cleanup":
        cleanup(manifest_path)


if __name__ == "__main__":
    main()
