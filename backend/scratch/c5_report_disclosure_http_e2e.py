from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


HTTP_BASE_URL = "http://127.0.0.1:8000/api/v1/rollups"
LEGACY_BASE_URL = "http://127.0.0.1:8000/rollup"
DEFAULT_MANIFEST = "/workspace/c5_report_disclosure_http_manifest.json"

PARENT_COMPANY_ID = 6
SOURCE_COMPANY_IDS = [7, 8, 9]
INCLUDED_COMPANY_IDS = [6, 7, 8, 9]
REPORTING_YEAR = 2024
SOURCE_TEMPLATE_CYCLE_ID = 17
MARKER = "C5_REPORT_DISCLOSURE_HTTP_SMOKE_2024"

ROLLUP_PURPOSE_CODE = "REPORT_DISCLOSURE"
METRIC_SCOPE_CODE = "SELECTED_DISCLOSURE"
POST_DMA_CYCLE_TYPE = "POST_DMA_DISCLOSURE"
ROLLUP_CYCLE_TYPE = "ROLLUP"
PROMOTE_AND_ROLLUP_POLICY = "PROMOTE_TO_KPI_FACT_AND_ROLLUP"
ROLLUP_READONLY_POLICY = "ROLLUP_READONLY"

EXPECTED_DIRECT_METRIC_COUNT = 9
EXPECTED_DIRECT_RULE_COUNT = 35
EXPECTED_RESOLVED_RULE_COUNT = 36
EXPECTED_RESOLVED_EXTERNAL_ATOMIC_COUNT = 82
EXPECTED_APPROVED_FACT_COUNT = 328
EXPECTED_REQUIRED_FACT_COUNT = 328


def dump_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def manifest_path(value: str) -> Path:
    return Path(value)


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


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


def placeholders(values: list[Any]) -> str:
    if not values:
        raise RuntimeError("EMPTY_PLACEHOLDER_VALUES")
    return ", ".join(["?"] * len(values))


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


def http_request(
    method: str,
    url: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    cookie_uuid: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    final_url = url
    if query:
        final_url = f"{url}?{urlencode({k: v for k, v in query.items() if v is not None})}"
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if cookie_uuid:
        from src.utils.settings import settings

        headers["Cookie"] = f"{settings.cookie_key}={cookie_uuid}"
    request = Request(final_url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
            return {
                "method": method.upper(),
                "url": final_url,
                "status": int(response.status),
                "bodyText": raw_body,
                "json": parse_json(raw_body),
            }
    except HTTPError as error:
        raw_body = error.read().decode("utf-8")
        return {
            "method": method.upper(),
            "url": final_url,
            "status": int(error.code),
            "bodyText": raw_body,
            "json": parse_json(raw_body),
        }
    except URLError as error:
        raise RuntimeError(f"HTTP_REQUEST_FAILED: {method.upper()} {final_url}: {error}") from error


def parse_json(raw_body: str) -> Any:
    if not raw_body:
        return None
    try:
        return json.loads(raw_body)
    except Exception:
        return None


def assert_status(response: dict[str, Any], expected: int | list[int]) -> None:
    expected_values = expected if isinstance(expected, list) else [expected]
    if response["status"] not in expected_values:
        raise AssertionError(
            "HTTP_STATUS_MISMATCH: "
            f"method={response['method']}, url={response['url']}, "
            f"expected={expected_values}, actual={response['status']}, body={response['bodyText']}"
        )


def assert_code(response: dict[str, Any], expected_code: str) -> None:
    body = response.get("json") or {}
    actual_code = body.get("code") if isinstance(body, dict) else None
    if actual_code != expected_code:
        raise AssertionError(
            "HTTP_CODE_MISMATCH: "
            f"method={response['method']}, url={response['url']}, "
            f"expected={expected_code}, actual={actual_code}, body={response['bodyText']}"
        )


def assert_success(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("json")
    if not isinstance(body, dict) or body.get("success") is not True:
        raise AssertionError(
            "HTTP_SUCCESS_FALSE: "
            f"method={response['method']}, url={response['url']}, status={response['status']}, body={response['bodyText']}"
        )
    data = body.get("data")
    if not isinstance(data, dict):
        raise AssertionError(f"HTTP_DATA_MISSING: {response['bodyText']}")
    return data


def canonical_url(path: str) -> str:
    return f"{HTTP_BASE_URL}{path}"


def legacy_url(path: str) -> str:
    return f"{LEGACY_BASE_URL}{path}"


def historical_counts(cur) -> dict[str, int]:
    return {
        "historicalReportDisclosureBatchCount": count_one(
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
        ),
        "historicalGroupRollupResultCount": count_one(
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
        ),
    }


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


def resolve_closure(metric_ids: list[str]) -> dict[str, Any]:
    from src.utils.calculationengine import normalizeSource
    from src.utils.rollupscoperepository import resolveConsolidatedRuleClosure

    direct = direct_rule_snapshot(metric_ids)
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
    return {
        "directMetricIds": metric_ids,
        "directMetricCount": len(metric_ids),
        "directRuleCount": len(direct["directRules"]),
        "directExternalEntityAtomicCount": len(direct["directExternalEntityAtomicIds"]),
        "resolvedRules": rules,
        "resolvedRuleSources": sources,
        "resolvedRuleCount": len(rules),
        "resolvedRuleSourceCount": len(sources),
        "resolvedExternalEntityAtomicIds": external_atomic_ids,
        "resolvedExternalEntityAtomicCount": len(external_atomic_ids),
    }


def source_readiness(cur, atomic_metric_ids: list[str]) -> dict[str, Any]:
    if not atomic_metric_ids:
        return {
            "readyYn": False,
            "requiredFactCount": 0,
            "approvedFactCount": 0,
            "companyReadiness": {},
        }
    company_placeholders = placeholders(INCLUDED_COMPANY_IDS)
    atomic_placeholders = placeholders(atomic_metric_ids)
    rows = fetch_all(
        cur,
        f"""
        SELECT company_id, atomic_metric_id
        FROM ESG_KPI_FACT
        WHERE company_id IN ({company_placeholders})
          AND reporting_year = ?
          AND atomic_metric_id IN ({atomic_placeholders})
          AND UPPER(COALESCE(company_scope_type, 'ENTITY')) = 'ENTITY'
          AND LOWER(COALESCE(approval_status, '')) = 'approved'
          AND delete_yn = 0
        ORDER BY company_id, atomic_metric_id
        """,
        (*INCLUDED_COMPANY_IDS, REPORTING_YEAR, *atomic_metric_ids),
    )
    approved_keys = {(int(row["company_id"]), row["atomic_metric_id"]) for row in rows}
    company_readiness = {}
    for company_id in INCLUDED_COMPANY_IDS:
        missing = [atomic_id for atomic_id in atomic_metric_ids if (company_id, atomic_id) not in approved_keys]
        company_readiness[str(company_id)] = {
            "requiredAtomicCount": len(atomic_metric_ids),
            "approvedAtomicCount": len(atomic_metric_ids) - len(missing),
            "missingAtomicMetricIds": missing,
        }
    return {
        "readyYn": all(not item["missingAtomicMetricIds"] for item in company_readiness.values()),
        "requiredFactCount": len(atomic_metric_ids) * len(INCLUDED_COMPANY_IDS),
        "approvedFactCount": len(approved_keys),
        "companyReadiness": company_readiness,
    }


def assert_preflight_expected(snapshot: dict[str, Any], readiness: dict[str, Any]) -> None:
    expected = {
        "directMetricCount": EXPECTED_DIRECT_METRIC_COUNT,
        "directRuleCount": EXPECTED_DIRECT_RULE_COUNT,
        "resolvedRuleCount": EXPECTED_RESOLVED_RULE_COUNT,
        "resolvedExternalEntityAtomicCount": EXPECTED_RESOLVED_EXTERNAL_ATOMIC_COUNT,
    }
    actual = {key: snapshot[key] for key in expected}
    if actual != expected:
        raise RuntimeError(f"PRECHECK_CLOSURE_UNEXPECTED: expected={expected}, actual={actual}")
    fact_expected = {
        "approvedFactCount": EXPECTED_APPROVED_FACT_COUNT,
        "requiredFactCount": EXPECTED_REQUIRED_FACT_COUNT,
        "readyYn": True,
    }
    fact_actual = {key: readiness[key] for key in fact_expected}
    if fact_actual != fact_expected:
        raise RuntimeError(f"PRECHECK_SOURCE_NOT_READY: expected={fact_expected}, actual={fact_actual}")


def redis_ping() -> dict[str, bool]:
    from src.utils.rediscl import client1, client3

    client1.ping()
    client3.ping()
    return {"db1": True, "db3": True}


def redis_key_exists(smoke_uuid: str) -> dict[str, bool]:
    from src.utils.rediscl import client1, client3

    return {
        "db1": bool(client1.exists(smoke_uuid)),
        "db3": bool(client3.exists(smoke_uuid)),
    }


def generate_unused_smoke_uuid() -> str:
    for _ in range(20):
        smoke_uuid = uuid.uuid4().hex
        exists = redis_key_exists(smoke_uuid)
        if not exists["db1"] and not exists["db3"]:
            return smoke_uuid
    raise RuntimeError("SMOKE_UUID_REDIS_COLLISION")


def smoke_uuid_collision_probe() -> dict[str, Any]:
    try:
        generate_unused_smoke_uuid()
    except RuntimeError:
        return {"availableYn": False}
    return {"availableYn": True}


def delete_smoke_redis_key(smoke_uuid: str) -> None:
    from src.utils.rediscl import delCompanyRedis, delTokenRedis

    delTokenRedis(smoke_uuid)
    delCompanyRedis(smoke_uuid)


def find_actor_users(cur) -> dict[str, Any]:
    target_company_ids = INCLUDED_COMPANY_IDS
    company_placeholders = placeholders(target_company_ids)
    rows = fetch_all(
        cur,
        f"""
        SELECT ur.company_id, MIN(ur.user_id) AS user_id
        FROM `with`.`USER_ROLE` ur
        JOIN `with`.`USER` u
          ON u.id = ur.user_id
         AND u.delete_yn = 0
        WHERE ur.company_id IN ({company_placeholders})
          AND ur.delete_yn = 0
        GROUP BY ur.company_id
        ORDER BY ur.company_id
        """,
        tuple(target_company_ids),
    )
    actors = {str(int(row["company_id"])): int(row["user_id"]) for row in rows if row.get("user_id")}
    fallback = fetch_one(
        cur,
        """
        SELECT MIN(id) AS user_id
        FROM `with`.`USER`
        WHERE delete_yn = 0
        """,
    )
    fallback_user_id = int(fallback["user_id"]) if fallback.get("user_id") else None
    if fallback_user_id is None:
        raise RuntimeError("PRECHECK_ACTOR_USER_NOT_FOUND")
    for company_id in target_company_ids:
        actors.setdefault(str(company_id), fallback_user_id)
    not_requested_source = fetch_one(
        cur,
        f"""
        SELECT ur.company_id, MIN(ur.user_id) AS user_id
        FROM `with`.`USER_ROLE` ur
        JOIN `with`.`USER` u
          ON u.id = ur.user_id
         AND u.delete_yn = 0
        WHERE ur.company_id NOT IN ({company_placeholders})
          AND ur.delete_yn = 0
        GROUP BY ur.company_id
        ORDER BY ur.company_id
        LIMIT 1
        """,
        tuple(target_company_ids),
    )
    relation_company_ids = relation_ids(cur)
    relation_placeholders = placeholders(relation_company_ids)
    out_of_relation_source = fetch_one(
        cur,
        f"""
        SELECT ur.company_id, MIN(ur.user_id) AS user_id
        FROM `with`.`USER_ROLE` ur
        JOIN `with`.`USER` u
          ON u.id = ur.user_id
         AND u.delete_yn = 0
        WHERE ur.company_id NOT IN ({relation_placeholders})
          AND ur.delete_yn = 0
        GROUP BY ur.company_id
        ORDER BY ur.company_id
        LIMIT 1
        """,
        tuple(relation_company_ids),
    )
    return {
        "actorsByCompany": actors,
        "fallbackUserId": fallback_user_id,
        "notRequestedSource": {
            "companyId": int(not_requested_source["company_id"]),
            "userId": int(not_requested_source["user_id"]),
        } if not_requested_source.get("company_id") and not_requested_source.get("user_id") else None,
        "outOfRelationSource": {
            "companyId": int(out_of_relation_source["company_id"]),
            "userId": int(out_of_relation_source["user_id"]),
        } if out_of_relation_source.get("company_id") and out_of_relation_source.get("user_id") else None,
    }


def source_template_cycle(cur) -> dict[str, Any]:
    return fetch_one(
        cur,
        """
        SELECT id, company_id, reporting_year, cycle_type, metric_scope_code, cycle_status
        FROM ESG_ONBOARDING_CYCLE
        WHERE id = ?
          AND company_id = ?
          AND cycle_type = ?
          AND delete_yn = 0
        """,
        (SOURCE_TEMPLATE_CYCLE_ID, PARENT_COMPANY_ID, POST_DMA_CYCLE_TYPE),
    )


def relation_ids(cur) -> list[int]:
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


def existing_collision_counts(cur) -> dict[str, int]:
    return {
        "postDmaCycle2024": count_one(
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
        ),
        "reportDisclosureBatch2024": count_one(
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
        ),
        "rollupCycle2024": count_one(
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
        ),
        "markerCycle": count_one(
            cur,
            """
            SELECT COUNT(*) AS row_count
            FROM ESG_ONBOARDING_CYCLE
            WHERE cycle_name = ?
              AND delete_yn = 0
            """,
            (MARKER,),
        ),
    }


def preflight(manifest_file: Path) -> None:
    if manifest_file.exists():
        raise RuntimeError(f"MANIFEST_ALREADY_EXISTS: {manifest_file}")

    conn = get_conn()
    try:
        canonical_probe = http_request("GET", canonical_url("/subsidiaries"))
        assert_status(canonical_probe, 401)
        legacy_probe = http_request("GET", legacy_url("/subsidiaries"))
        redis_status = redis_ping()

        with conn.cursor(dictionary=True) as cur:
            cycle = source_template_cycle(cur)
            if not cycle:
                raise RuntimeError("PRECHECK_SOURCE_TEMPLATE_CYCLE_NOT_FOUND")
            relations = relation_ids(cur)
            missing_relations = [company_id for company_id in INCLUDED_COMPANY_IDS if company_id not in relations]
            if missing_relations:
                raise RuntimeError(f"PRECHECK_RELATION_NOT_READY: {missing_relations}")
            collisions = existing_collision_counts(cur)
            blocking_collisions = {
                key: value
                for key, value in collisions.items()
                if value
            }
            if blocking_collisions:
                raise RuntimeError(f"PRECHECK_COLLISION_FOUND: {blocking_collisions}")
            direct_metric_ids = list_rollup_capable_metrics(cur)
            snapshot = resolve_closure(direct_metric_ids)
            readiness = source_readiness(cur, snapshot["resolvedExternalEntityAtomicIds"])
            assert_preflight_expected(snapshot, readiness)
            actors = find_actor_users(cur)
            history = historical_counts(cur)
            smoke_uuid_probe = smoke_uuid_collision_probe()
            if not smoke_uuid_probe.get("availableYn"):
                raise RuntimeError("PRECHECK_SMOKE_UUID_NOT_AVAILABLE")

        dump_json(
            {
                "status": "PREFLIGHT_OK",
                "manifestExists": manifest_file.exists(),
                "redis": redis_status,
                "canonicalProbe": {
                    "method": canonical_probe["method"],
                    "url": canonical_probe["url"],
                    "status": canonical_probe["status"],
                },
                "legacyProbeInfoOnly": {
                    "method": legacy_probe["method"],
                    "url": legacy_probe["url"],
                    "status": legacy_probe["status"],
                    "body": legacy_probe["json"],
                },
                "sourceTemplateCycle": cycle,
                "relations": relations,
                "closure": {
                    "directMetricCount": snapshot["directMetricCount"],
                    "directMetricIds": snapshot["directMetricIds"],
                    "directRuleCount": snapshot["directRuleCount"],
                    "directExternalEntityAtomicCount": snapshot["directExternalEntityAtomicCount"],
                    "resolvedRuleCount": snapshot["resolvedRuleCount"],
                    "resolvedRuleSourceCount": snapshot["resolvedRuleSourceCount"],
                    "resolvedExternalEntityAtomicCount": snapshot["resolvedExternalEntityAtomicCount"],
                },
                "sourceReadiness": readiness,
                "historicalCountsBefore": history,
                "actorUsers": actors,
                "smokeUuidCollisionProbe": smoke_uuid_probe,
                "notRequestedSourceCase": "AVAILABLE" if actors.get("notRequestedSource") else "SKIPPED",
                "outOfRelationSourceCase": "AVAILABLE" if actors.get("outOfRelationSource") else "SKIPPED",
            }
        )
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
    metric_placeholders = placeholders(direct_metric_ids)
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
    if int(cur.rowcount or 0) != len(direct_metric_ids):
        raise RuntimeError(f"TEST_SCOPE_INSERT_COUNT_MISMATCH: inserted={cur.rowcount}, expected={len(direct_metric_ids)}")
    return cycle_id


def make_session(manifest_file: Path, manifest: dict[str, Any], label: str, company_id: int, user_id: int) -> str:
    from src.models.model import UserModel
    from src.utils.rediscl import setCompanyRedis, setTokenRedis
    from src.utils.tokenset import generateAccessWithUuid

    smoke_uuid = generate_unused_smoke_uuid()
    manifest.setdefault("sessions", {})[label] = {
        "uuid": smoke_uuid,
        "companyId": company_id,
        "userId": user_id,
        "tokenRedisSetYn": False,
        "companyRedisSetYn": False,
    }
    write_manifest(manifest_file, manifest)

    user_claims = UserModel(
        uuid=smoke_uuid,
        id=user_id,
        name=f"Smoke User {user_id}",
        email=f"smoke-{user_id}@example.com",
        role="ESG",
        role_name="ESG",
    )
    token = generateAccessWithUuid(user_claims)
    token_result = setTokenRedis(smoke_uuid, token)
    if not token_result.get("status"):
        raise RuntimeError(f"SMOKE_TOKEN_REDIS_SET_FAILED: {label}")
    manifest["sessions"][label]["tokenRedisSetYn"] = True
    write_manifest(manifest_file, manifest)

    company_result = setCompanyRedis(smoke_uuid, int(company_id))
    if not company_result.get("status"):
        raise RuntimeError(f"SMOKE_COMPANY_REDIS_SET_FAILED: {label}")
    manifest["sessions"][label]["companyRedisSetYn"] = True
    write_manifest(manifest_file, manifest)
    return smoke_uuid


def execute(manifest_file: Path) -> None:
    if manifest_file.exists():
        raise RuntimeError(f"MANIFEST_ALREADY_EXISTS: {manifest_file}")

    manifest: dict[str, Any] = {
        "marker": MARKER,
        "httpBaseUrl": HTTP_BASE_URL,
        "createdAtEpoch": int(time.time()),
    }
    write_manifest(manifest_file, manifest)
    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
            collisions = existing_collision_counts(cur)
            blocking_collisions = {key: value for key, value in collisions.items() if value}
            if blocking_collisions:
                raise RuntimeError(f"PRECHECK_COLLISION_FOUND: {blocking_collisions}")
            direct_metric_ids = list_rollup_capable_metrics(cur)
            snapshot = resolve_closure(direct_metric_ids)
            readiness = source_readiness(cur, snapshot["resolvedExternalEntityAtomicIds"])
            assert_preflight_expected(snapshot, readiness)
            actors = find_actor_users(cur)
            history = historical_counts(cur)
            cycle_id = insert_test_cycle_and_scope(cur, direct_metric_ids)
            manifest.update(
                {
                    "testPostDmaCycleId": cycle_id,
                    "directMetricIds": direct_metric_ids,
                    "closure": {
                        "directMetricCount": snapshot["directMetricCount"],
                        "directRuleCount": snapshot["directRuleCount"],
                        "resolvedRuleCount": snapshot["resolvedRuleCount"],
                        "resolvedExternalEntityAtomicCount": snapshot["resolvedExternalEntityAtomicCount"],
                    },
                    "sourceReadiness": {
                        "approvedFactCount": readiness["approvedFactCount"],
                        "requiredFactCount": readiness["requiredFactCount"],
                    },
                    "historicalCountsBefore": history,
                    "actorUsers": actors,
                }
            )
            write_manifest(manifest_file, manifest)
        conn.commit()
        manifest["testCycleCommittedYn"] = True
        write_manifest(manifest_file, manifest)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    actors = manifest["actorUsers"]
    parent_uuid = make_session(
        manifest_file,
        manifest,
        "parent",
        PARENT_COMPANY_ID,
        int(actors["actorsByCompany"][str(PARENT_COMPANY_ID)]),
    )
    source_uuids = {}
    for company_id in SOURCE_COMPANY_IDS:
        source_uuids[str(company_id)] = make_session(
            manifest_file,
            manifest,
            f"source{company_id}",
            company_id,
            int(actors["actorsByCompany"][str(company_id)]),
        )
    not_requested_source = actors.get("notRequestedSource")
    not_requested_uuid = None
    if not_requested_source:
        not_requested_uuid = make_session(
            manifest_file,
            manifest,
            "notRequestedSource",
            int(not_requested_source["companyId"]),
            int(not_requested_source["userId"]),
        )

    query = {
        "sourceCycleId": manifest["testPostDmaCycleId"],
        "rollupPurposeCode": ROLLUP_PURPOSE_CODE,
        "metricScopeCode": METRIC_SCOPE_CODE,
    }
    subsidiaries = http_request("GET", canonical_url("/subsidiaries"), query=query, cookie_uuid=parent_uuid)
    assert_status(subsidiaries, 200)
    assert_success(subsidiaries)

    body = {
        "sourceCycleId": manifest["testPostDmaCycleId"],
        "sourceCompanyIds": SOURCE_COMPANY_IDS,
        "rollupPurposeCode": ROLLUP_PURPOSE_CODE,
        "metricScopeCode": METRIC_SCOPE_CODE,
    }
    out_of_relation = actors.get("outOfRelationSource")
    out_of_relation_result = {"status": "SKIPPED"}
    if out_of_relation:
        forbidden_body = {
            **body,
            "sourceCompanyIds": [*SOURCE_COMPANY_IDS, int(out_of_relation["companyId"])],
        }
        forbidden_batch_response = http_request("POST", canonical_url("/batches"), body=forbidden_body, cookie_uuid=parent_uuid)
        assert_status(forbidden_batch_response, 403)
        assert_code(forbidden_batch_response, "ROLLUP_SOURCE_SCOPE_FORBIDDEN")
        out_of_relation_result = {
            "status": "EXECUTED",
            "companyId": int(out_of_relation["companyId"]),
            "httpStatus": forbidden_batch_response["status"],
        }

    batch_response = http_request("POST", canonical_url("/batches"), body=body, cookie_uuid=parent_uuid)
    assert_status(batch_response, 200)
    batch_data = assert_success(batch_response)
    batch_id = int(batch_data["batchId"])
    manifest["batchId"] = batch_id
    write_manifest(manifest_file, manifest)

    duplicate_batch_response = http_request("POST", canonical_url("/batches"), body=body, cookie_uuid=parent_uuid)
    assert_status(duplicate_batch_response, 200)
    duplicate_batch_data = assert_success(duplicate_batch_response)
    if int(duplicate_batch_data["batchId"]) != batch_id:
        raise AssertionError(f"DUPLICATE_BATCH_REUSE_FAILED: expected={batch_id}, actual={duplicate_batch_data['batchId']}")

    pre_send_calc = http_request("POST", canonical_url(f"/batches/{batch_id}/calculate"), cookie_uuid=parent_uuid)
    assert_status(pre_send_calc, 409)
    assert_code(pre_send_calc, "ROLLUP_SOURCE_NOT_SENT")

    source_status_forbidden = http_request("GET", canonical_url(f"/batches/{batch_id}/status"), cookie_uuid=source_uuids["7"])
    assert_status(source_status_forbidden, 403)
    source_calc_forbidden = http_request("POST", canonical_url(f"/batches/{batch_id}/calculate"), cookie_uuid=source_uuids["7"])
    assert_status(source_calc_forbidden, 403)
    parent_send = http_request("POST", canonical_url(f"/batches/{batch_id}/sources/send"), cookie_uuid=parent_uuid)
    assert_status(parent_send, 409)
    assert_code(parent_send, "ROLLUP_PARENT_SEND_NOT_ALLOWED")
    not_requested_result = {"status": "SKIPPED"}
    if not_requested_uuid:
        not_requested_send = http_request("POST", canonical_url(f"/batches/{batch_id}/sources/send"), cookie_uuid=not_requested_uuid)
        assert_status(not_requested_send, 404)
        assert_code(not_requested_send, "ROLLUP_SOURCE_REQUEST_NOT_FOUND")
        not_requested_result = {"status": "EXECUTED", "httpStatus": not_requested_send["status"]}

    for company_id in SOURCE_COMPANY_IDS:
        requests_response = http_request(
            "GET",
            canonical_url("/requests"),
            query={"rollupPurposeCode": ROLLUP_PURPOSE_CODE, "metricScopeCode": METRIC_SCOPE_CODE},
            cookie_uuid=source_uuids[str(company_id)],
        )
        assert_status(requests_response, 200)
        items = assert_success(requests_response).get("items") or []
        if batch_id not in [int(item["batchId"]) for item in items]:
            raise AssertionError(f"SOURCE_REQUEST_BATCH_NOT_FOUND: companyId={company_id}, batchId={batch_id}, items={items}")

    send_7 = http_request("POST", canonical_url(f"/batches/{batch_id}/sources/send"), cookie_uuid=source_uuids["7"])
    assert_status(send_7, 200)
    send_7_again = http_request("POST", canonical_url(f"/batches/{batch_id}/sources/send"), cookie_uuid=source_uuids["7"])
    assert_status(send_7_again, 200)
    for company_id in [8, 9]:
        send_response = http_request("POST", canonical_url(f"/batches/{batch_id}/sources/send"), cookie_uuid=source_uuids[str(company_id)])
        assert_status(send_response, 200)

    ready_status = http_request("GET", canonical_url(f"/batches/{batch_id}/status"), cookie_uuid=parent_uuid)
    assert_status(ready_status, 200)
    ready_data = assert_success(ready_status)
    if ready_data.get("calculateReadyYn") is not True or int(ready_data.get("pendingCount") or 0) != 0:
        raise AssertionError(f"ROLLUP_STATUS_NOT_READY: {ready_data}")

    calc_response = http_request("POST", canonical_url(f"/batches/{batch_id}/calculate"), cookie_uuid=parent_uuid, timeout=120)
    assert_status(calc_response, 200)
    calc_data = assert_success(calc_response)
    results = calc_data.get("results") or []
    if len(results) != EXPECTED_RESOLVED_RULE_COUNT:
        raise AssertionError(f"ROLLUP_RESULT_COUNT_MISMATCH: expected={EXPECTED_RESOLVED_RULE_COUNT}, actual={len(results)}")

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
        if rollup_cycle:
            manifest["rollupCycleId"] = int(rollup_cycle["id"])
            write_manifest(manifest_file, manifest)
    finally:
        conn.close()

    completed_status = http_request("GET", canonical_url(f"/batches/{batch_id}/status"), cookie_uuid=parent_uuid)
    assert_status(completed_status, 200)
    completed_data = assert_success(completed_status)
    if (
        completed_data.get("batchStatus") != "completed"
        or completed_data.get("reportReadyYn") is not True
        or completed_data.get("dmaReadyYn") is not False
    ):
        raise AssertionError(f"ROLLUP_COMPLETED_STATUS_INVALID: {completed_data}")

    recalc_response = http_request("POST", canonical_url(f"/batches/{batch_id}/calculate"), cookie_uuid=parent_uuid)
    assert_status(recalc_response, 409)
    assert_code(recalc_response, "ROLLUP_BATCH_NOT_ACTIVE")

    dump_json(
        {
            "status": "HTTP_EXECUTE_OK",
            "testPostDmaCycleId": manifest["testPostDmaCycleId"],
            "batchId": batch_id,
            "rollupCycleId": manifest.get("rollupCycleId"),
            "notRequestedSource": not_requested_result,
            "outOfRelationSource": out_of_relation_result,
            "resultCount": len(results),
        }
    )


def verify(manifest_file: Path) -> None:
    manifest = read_manifest(manifest_file)
    if not manifest:
        raise RuntimeError("MANIFEST_NOT_FOUND")
    if manifest.get("marker") != MARKER:
        raise RuntimeError("VERIFY_MANIFEST_MARKER_MISMATCH")

    test_cycle_id = int(manifest["testPostDmaCycleId"])
    batch_id = int(manifest["batchId"])
    rollup_cycle_id = manifest.get("rollupCycleId")
    rollup_cycle_id = int(rollup_cycle_id) if rollup_cycle_id is not None else None
    current_snapshot = resolve_closure(manifest.get("directMetricIds") or [])
    closure_keys = [
        "directRuleCount",
        "resolvedRuleCount",
        "resolvedExternalEntityAtomicCount",
    ]
    current_closure = {key: current_snapshot.get(key) for key in closure_keys}
    manifest_closure = {
        key: (manifest.get("closure") or {}).get(key)
        for key in closure_keys
    }
    expected_closure = {
        "directRuleCount": EXPECTED_DIRECT_RULE_COUNT,
        "resolvedRuleCount": EXPECTED_RESOLVED_RULE_COUNT,
        "resolvedExternalEntityAtomicCount": EXPECTED_RESOLVED_EXTERNAL_ATOMIC_COUNT,
    }
    closure_matches_manifest = current_closure == manifest_closure

    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
            test_cycle_count = count_one(
                cur,
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_ONBOARDING_CYCLE
                WHERE id = ?
                  AND cycle_name = ?
                  AND cycle_type = ?
                  AND delete_yn = 0
                """,
                (test_cycle_id, MARKER, POST_DMA_CYCLE_TYPE),
            )
            cycle_scope_count = count_one(
                cur,
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
                WHERE esg_onboarding_cycle_id = ?
                  AND active_yn = 1
                  AND delete_yn = 0
                """,
                (test_cycle_id,),
            )
            batch = fetch_one(
                cur,
                """
                SELECT id, batch_status, report_ready_yn, dma_ready_yn
                FROM ESG_ROLLUP_BATCH
                WHERE id = ?
                  AND source_cycle_id = ?
                  AND rollup_purpose_code = ?
                  AND delete_yn = 0
                """,
                (batch_id, test_cycle_id, ROLLUP_PURPOSE_CODE),
            )
            batch_scope_count = count_one(
                cur,
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE
                WHERE esg_rollup_batch_id = ?
                  AND delete_yn = 0
                """,
                (batch_id,),
            )
            result_counts = fetch_one(
                cur,
                """
                SELECT
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN rollup_status = 'approved' THEN 1 ELSE 0 END) AS approved_count
                FROM ESG_GROUP_ROLLUP_RESULT
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
                    SUM(CASE WHEN LOWER(COALESCE(transfer_status, '')) = 'received' THEN 1 ELSE 0 END) AS received_count,
                    SUM(CASE WHEN LOWER(COALESCE(transfer_status, '')) != 'received' THEN 1 ELSE 0 END) AS missing_count
                FROM ESG_ROLLUP_SOURCE_STATUS
                WHERE esg_rollup_batch_id = ?
                  AND delete_yn = 0
                """,
                (batch_id,),
            )
            if rollup_cycle_id is not None:
                rollup_cycle_count = count_one(
                    cur,
                    """
                    SELECT COUNT(*) AS row_count
                    FROM ESG_ONBOARDING_CYCLE
                    WHERE id = ?
                      AND parent_rollup_batch_id = ?
                      AND cycle_type = ?
                      AND delete_yn = 0
                    """,
                    (rollup_cycle_id, batch_id, ROLLUP_CYCLE_TYPE),
                )
                readonly_scope = fetch_one(
                    cur,
                    """
                    SELECT
                        COUNT(*) AS total_count,
                        SUM(CASE WHEN approval_policy_code = ? THEN 1 ELSE 0 END) AS readonly_policy_count,
                        SUM(CASE WHEN rollup_readonly_yn = 1 THEN 1 ELSE 0 END) AS readonly_yn_count
                    FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE
                    WHERE esg_onboarding_cycle_id = ?
                      AND active_yn = 1
                      AND delete_yn = 0
                    """,
                    (ROLLUP_READONLY_POLICY, rollup_cycle_id),
                )
            else:
                rollup_cycle_count = 0
                readonly_scope = {"total_count": 0, "readonly_policy_count": 0, "readonly_yn_count": 0}
            after_history = historical_counts(cur)
    finally:
        conn.close()

    session_checks = {
        label: redis_key_exists(session["uuid"])
        for label, session in (manifest.get("sessions") or {}).items()
    }
    ok = all(
        [
            test_cycle_count == 1,
            cycle_scope_count == EXPECTED_DIRECT_METRIC_COUNT,
            batch.get("batch_status") == "completed",
            int(batch.get("report_ready_yn") or 0) == 1,
            int(batch.get("dma_ready_yn") or 0) == 0,
            batch_scope_count == EXPECTED_RESOLVED_RULE_COUNT,
            int(result_counts.get("total_count") or 0) == EXPECTED_RESOLVED_RULE_COUNT,
            int(result_counts.get("approved_count") or 0) == EXPECTED_RESOLVED_RULE_COUNT,
            rollup_cycle_count == 1,
            int(readonly_scope.get("total_count") or 0) == 10,
            int(readonly_scope.get("readonly_policy_count") or 0) == 10,
            int(readonly_scope.get("readonly_yn_count") or 0) == 10,
            closure_matches_manifest,
            current_closure == expected_closure,
            int(source_status.get("total_count") or 0) == 4,
            int(source_status.get("received_count") or 0) == 4,
            int(source_status.get("missing_count") or 0) == 0,
            manifest.get("historicalCountsBefore") == after_history,
            all(value["db1"] and value["db3"] for value in session_checks.values()),
        ]
    )
    dump_json(
        {
            "status": "HTTP_WRITE_SMOKE_OK" if ok else "HTTP_WRITE_SMOKE_FAILED",
            "testPostDmaCycleCount": test_cycle_count,
            "cycleMetricScopeCount": cycle_scope_count,
            "batch": batch,
            "batchAtomicScopeCount": batch_scope_count,
            "groupRollupResultCounts": result_counts,
            "sourceStatus": source_status,
            "rollupCycleCount": rollup_cycle_count,
            "rollupReadonlyScope": readonly_scope,
            "currentClosureSnapshot": current_closure,
            "manifestClosureSnapshot": manifest_closure,
            "closureMatchesManifest": closure_matches_manifest,
            "historicalCountsBefore": manifest.get("historicalCountsBefore"),
            "historicalCountsAfter": after_history,
            "smokeRedisKeys": session_checks,
        }
    )
    if not ok:
        raise RuntimeError("HTTP_WRITE_SMOKE_VERIFY_FAILED")


def cleanup(manifest_file: Path) -> None:
    manifest = read_manifest(manifest_file)
    if not manifest:
        dump_json({"status": "CLEANUP_OK", "manifestFoundYn": False})
        return
    if manifest.get("marker") != MARKER:
        raise RuntimeError("CLEANUP_MANIFEST_MARKER_MISMATCH")

    test_cycle_id = manifest.get("testPostDmaCycleId")
    batch_id = manifest.get("batchId")
    rollup_cycle_id = manifest.get("rollupCycleId")
    test_cycle_id = int(test_cycle_id) if test_cycle_id is not None else None
    batch_id = int(batch_id) if batch_id is not None else None
    rollup_cycle_id = int(rollup_cycle_id) if rollup_cycle_id is not None else None

    conn = get_conn()
    try:
        with conn.cursor(dictionary=True) as cur:
            if batch_id is not None and rollup_cycle_id is None:
                row = fetch_one(
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
                rollup_cycle_id = int(row["id"]) if row.get("id") else None
            if test_cycle_id is not None:
                guard = fetch_one(
                    cur,
                    """
                    SELECT id, cycle_name, cycle_type
                    FROM ESG_ONBOARDING_CYCLE
                    WHERE id = ?
                    """,
                    (test_cycle_id,),
                )
                if guard and (
                    guard.get("cycle_name") != MARKER
                    or guard.get("cycle_type") != POST_DMA_CYCLE_TYPE
                ):
                    raise RuntimeError("CLEANUP_TEST_CYCLE_GUARD_FAILED")
            if batch_id is not None:
                guard = fetch_one(
                    cur,
                    """
                    SELECT id, source_cycle_id, rollup_purpose_code
                    FROM ESG_ROLLUP_BATCH
                    WHERE id = ?
                    """,
                    (batch_id,),
                )
                if guard and (
                    test_cycle_id is None
                    or int(guard.get("source_cycle_id") or 0) != test_cycle_id
                    or guard.get("rollup_purpose_code") != ROLLUP_PURPOSE_CODE
                ):
                    raise RuntimeError("CLEANUP_BATCH_GUARD_FAILED")
            if rollup_cycle_id is not None:
                guard = fetch_one(
                    cur,
                    """
                    SELECT id, parent_rollup_batch_id, cycle_type
                    FROM ESG_ONBOARDING_CYCLE
                    WHERE id = ?
                    """,
                    (rollup_cycle_id,),
                )
                if guard and (
                    batch_id is None
                    or int(guard.get("parent_rollup_batch_id") or 0) != batch_id
                    or guard.get("cycle_type") != ROLLUP_CYCLE_TYPE
                ):
                    raise RuntimeError("CLEANUP_ROLLUP_CYCLE_GUARD_FAILED")

            if test_cycle_id is not None and rollup_cycle_id is not None:
                cur.execute(
                    "DELETE FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE WHERE esg_onboarding_cycle_id IN (?, ?)",
                    (test_cycle_id, rollup_cycle_id),
                )
            elif test_cycle_id is not None:
                cur.execute(
                    "DELETE FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE WHERE esg_onboarding_cycle_id = ?",
                    (test_cycle_id,),
                )
            if batch_id is not None:
                cur.execute("DELETE FROM ESG_GROUP_ROLLUP_RESULT WHERE esg_rollup_batch_id = ?", (batch_id,))
                cur.execute("DELETE FROM ESG_ROLLUP_SOURCE_STATUS WHERE esg_rollup_batch_id = ?", (batch_id,))
                cur.execute("DELETE FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE WHERE esg_rollup_batch_id = ?", (batch_id,))
            if rollup_cycle_id is not None and batch_id is not None:
                cur.execute(
                    """
                    DELETE FROM ESG_ONBOARDING_CYCLE
                    WHERE id = ?
                      AND parent_rollup_batch_id = ?
                      AND cycle_type = ?
                    """,
                    (rollup_cycle_id, batch_id, ROLLUP_CYCLE_TYPE),
                )
            if batch_id is not None:
                cur.execute(
                    """
                    DELETE FROM ESG_ROLLUP_BATCH
                    WHERE id = ?
                      AND source_cycle_id = ?
                      AND rollup_purpose_code = ?
                    """,
                    (batch_id, test_cycle_id, ROLLUP_PURPOSE_CODE),
                )
            if test_cycle_id is not None:
                cur.execute(
                    """
                    DELETE FROM ESG_ONBOARDING_CYCLE
                    WHERE id = ?
                      AND cycle_name = ?
                      AND cycle_type = ?
                    """,
                    (test_cycle_id, MARKER, POST_DMA_CYCLE_TYPE),
                )
            remaining = remaining_counts(cur, test_cycle_id, batch_id, rollup_cycle_id)
            if any(remaining.values()):
                raise RuntimeError(f"CLEANUP_REMAINING_ROWS: {remaining}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    for session in (manifest.get("sessions") or {}).values():
        delete_smoke_redis_key(session["uuid"])
    remaining_redis = {
        label: redis_key_exists(session["uuid"])
        for label, session in (manifest.get("sessions") or {}).items()
    }
    if any(value["db1"] or value["db3"] for value in remaining_redis.values()):
        raise RuntimeError(f"CLEANUP_REMAINING_REDIS_KEYS: {remaining_redis}")
    manifest_file.unlink(missing_ok=True)
    dump_json({
        "status": "CLEANUP_OK",
        "remaining": remaining,
        "remainingRedis": remaining_redis,
        "manifestDeletedYn": not manifest_file.exists(),
    })


def remaining_counts(cur, test_cycle_id: int | None, batch_id: int | None, rollup_cycle_id: int | None) -> dict[str, int]:
    return {
        "testCycleScope": count_one(
            cur,
            "SELECT COUNT(*) AS row_count FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE WHERE esg_onboarding_cycle_id = ?",
            (test_cycle_id or 0,),
        ),
        "rollupCycleScope": count_one(
            cur,
            "SELECT COUNT(*) AS row_count FROM ESG_ONBOARDING_CYCLE_METRIC_SCOPE WHERE esg_onboarding_cycle_id = ?",
            (rollup_cycle_id or 0,),
        ),
        "groupRollupResult": count_one(
            cur,
            "SELECT COUNT(*) AS row_count FROM ESG_GROUP_ROLLUP_RESULT WHERE esg_rollup_batch_id = ?",
            (batch_id or 0,),
        ),
        "sourceStatus": count_one(
            cur,
            "SELECT COUNT(*) AS row_count FROM ESG_ROLLUP_SOURCE_STATUS WHERE esg_rollup_batch_id = ?",
            (batch_id or 0,),
        ),
        "batchAtomicScope": count_one(
            cur,
            "SELECT COUNT(*) AS row_count FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE WHERE esg_rollup_batch_id = ?",
            (batch_id or 0,),
        ),
        "rollupCycle": count_one(
            cur,
            "SELECT COUNT(*) AS row_count FROM ESG_ONBOARDING_CYCLE WHERE id = ?",
            (rollup_cycle_id or 0,),
        ),
        "rollupBatch": count_one(
            cur,
            "SELECT COUNT(*) AS row_count FROM ESG_ROLLUP_BATCH WHERE id = ?",
            (batch_id or 0,),
        ),
        "testPostDmaCycle": count_one(
            cur,
            "SELECT COUNT(*) AS row_count FROM ESG_ONBOARDING_CYCLE WHERE id = ?",
            (test_cycle_id or 0,),
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="C5 REPORT_DISCLOSURE HTTP E2E smoke")
    parser.add_argument("--mode", choices=["preflight", "execute", "verify", "cleanup"], required=True)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    path = manifest_path(args.manifest)

    if args.mode == "preflight":
        preflight(path)
    elif args.mode == "execute":
        execute(path)
    elif args.mode == "verify":
        verify(path)
    elif args.mode == "cleanup":
        cleanup(path)


if __name__ == "__main__":
    main()
