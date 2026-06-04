from typing import Optional
from src.utils.db import findAll, findOne
from src.utils.calculationengine import normalizeSource
from src.utils.calculationrepository import listApprovedEntityFacts

def listEffectiveSourceCompanies(parentCompanyId: int, reportingYear: int, rollupPurposeCode: str) -> list[dict]:
    # strict DB-driven relation. self relation check is done by caller if needed
    sql = """
        SELECT DISTINCT
            s.source_company_id AS companyId,
            p.company_code AS companyCode,
            COALESCE(p.company_code, CAST(s.source_company_id AS CHAR)) AS companyName
        FROM ESG_COMPANY_ROLLUP_SCOPE s
        LEFT JOIN ESG_COMPANY_PROFILE p
          ON p.company_id = s.source_company_id
         AND p.delete_yn = 0
        WHERE s.parent_company_id = ?
          AND s.rollup_include_yn = 1
          AND s.delete_yn = 0
          AND (s.effective_from_year IS NULL OR s.effective_from_year <= ?)
          AND (s.effective_to_year IS NULL OR s.effective_to_year >= ?)
        ORDER BY companyName, companyId
    """
    rows = findAll(sql, (parentCompanyId, reportingYear, reportingYear)) or []
    return [
        {
            "companyId": int(row["companyId"]),
            "companyCode": row.get("companyCode"),
            "companyName": row.get("companyName") or row.get("companyCode") or str(row["companyId"]),
        }
        for row in rows
    ]

def listBatchRules(metricIds: list[str]) -> list[dict]:
    if not metricIds:
        return []
    placeholders = ", ".join(["?"] * len(metricIds))
    sql = f"""
        SELECT *
        FROM ESG_CALCULATION_RULE
        WHERE target_metric_id IN ({placeholders})
          AND UPPER(COALESCE(execution_scope, '')) = 'CONSOLIDATED'
          AND active_yn = 1
          AND delete_yn = 0
        ORDER BY sort_order, calculation_rule_code
    """
    return findAll(sql, tuple(metricIds)) or []

def listBatchRuleSources(ruleCodes: list[str]) -> list[dict]:
    if not ruleCodes:
        return []
    placeholders = ", ".join(["?"] * len(ruleCodes))
    sql = f"""
        SELECT *
        FROM ESG_CALCULATION_RULE_SOURCE
        WHERE calculation_rule_code IN ({placeholders})
          AND delete_yn = 0
    """
    return findAll(sql, tuple(ruleCodes)) or []

def saveScopeFromRulesTx(cur, batchId: int, rules: list[dict], sources: list[dict], scopeReason: str) -> None:
    sourceMap = {}
    for source in sources:
        ruleCode = source["calculation_rule_code"]
        sourceMap.setdefault(ruleCode, []).append(source)

    sql = """
        INSERT INTO ESG_ROLLUP_BATCH_ATOMIC_SCOPE (
            esg_rollup_batch_id,
            metric_id,
            group_atomic_metric_id,
            source_atomic_metric_ids,
            required_yn,
            scope_reason,
            delete_yn,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, 1, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON DUPLICATE KEY UPDATE
            source_atomic_metric_ids = VALUES(source_atomic_metric_ids),
            required_yn = VALUES(required_yn),
            scope_reason = VALUES(scope_reason),
            delete_yn = 0,
            updated_at = CURRENT_TIMESTAMP
    """
    import json
    for rule in rules:
        ruleCode = rule["calculation_rule_code"]
        ruleSources = sourceMap.get(ruleCode, [])
        sourceIds = []
        for s in ruleSources:
            norm = normalizeSource(s)
            sourceId = norm.get("sourceAtomicMetricId")
            if sourceId and sourceId not in sourceIds:
                sourceIds.append(sourceId)
        
        cur.execute(sql, (
            batchId,
            rule["target_metric_id"],
            rule["target_atomic_metric_id"],
            json.dumps(sourceIds) if sourceIds else None,
            scopeReason
        ))

def listScope(batchId: int) -> list[dict]:
    sql = """
        SELECT
            s.metric_id,
            s.group_atomic_metric_id,
            s.source_atomic_metric_ids,
            s.required_yn,
            s.scope_reason,
            COALESCE(amm.atomic_name_kr, s.group_atomic_metric_id) AS groupAtomicName
        FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE s
        LEFT JOIN ESG_ATOMIC_METRIC_MASTER amm
          ON amm.atomic_metric_id = s.group_atomic_metric_id
         AND amm.delete_yn = 0
        WHERE s.esg_rollup_batch_id = ?
          AND s.delete_yn = 0
          AND s.required_yn = 1
        ORDER BY s.group_atomic_metric_id
    """
    import json
    rows = findAll(sql, (batchId,)) or []
    for row in rows:
        val = row.get("source_atomic_metric_ids")
        row["sourceAtomicMetricIds"] = json.loads(val) if val else []
    return rows

def resolveRequiredSourceAtomicIds(batchId: int) -> list[str]:
    scopes = listScope(batchId)
    atomicIds = set()
    for s in scopes:
        for a in s.get("sourceAtomicMetricIds", []):
            atomicIds.add(a)
    return sorted(list(atomicIds))

def resolveRequiredGroupAtomicIds(batchId: int) -> list[str]:
    scopes = listScope(batchId)
    return sorted([s["group_atomic_metric_id"] for s in scopes if s.get("group_atomic_metric_id")])

def listApprovedFactsByCompany(companyIds: list[int], reportingYear: int, atomicMetricIds: list[str]) -> list[dict]:
    if not companyIds or not atomicMetricIds:
        return []
    return listApprovedEntityFacts(companyIds, reportingYear, atomicMetricIds)

def listPriorYearApprovedFactsByCompany(companyIds: list[int], reportingYear: int, atomicMetricIds: list[str]) -> list[dict]:
    if not companyIds or not atomicMetricIds:
        return []
    return listApprovedEntityFacts(companyIds, reportingYear - 1, atomicMetricIds)

def buildSourceReadiness(batchId: int, sourceCompanyIds: list[int], reportingYear: int) -> dict:
    requiredAtomicIds = resolveRequiredSourceAtomicIds(batchId)
    if not requiredAtomicIds or not sourceCompanyIds:
        return {
            "requiredAtomicCount": len(requiredAtomicIds),
            "approvedAtomicCount": 0,
            "missingAtomicMetricIds": requiredAtomicIds,
            "sourceCompanyCount": len(sourceCompanyIds),
            "readySourceCompanyCount": 0,
            "readyYn": False
        }
        
    facts = listApprovedEntityFacts(sourceCompanyIds, reportingYear, requiredAtomicIds)
    approvedKeys = set()
    for f in facts:
        approvedKeys.add((f["companyId"], f["atomicMetricId"]))
        
    readySourceCompanyCount = 0
    allMissing = set()
    for cid in sourceCompanyIds:
        companyMissing = [a for a in requiredAtomicIds if (cid, a) not in approvedKeys]
        for m in companyMissing:
            allMissing.add(m)
        if not companyMissing:
            readySourceCompanyCount += 1
            
    # For readiness of the batch overall, we look at the union of all facts. 
    # Actually, readiness is per source company usually.
    # The return format should match what was used in the service.
    # Service needs missing count to compute approved count.
    # Let's return missing atomic metric IDs (union across all companies).
    return {
        "requiredAtomicCount": len(requiredAtomicIds),
        "approvedAtomicCount": len(requiredAtomicIds) - len(allMissing),
        "missingAtomicMetricIds": sorted(list(allMissing)),
        "sourceCompanyCount": len(sourceCompanyIds),
        "readySourceCompanyCount": readySourceCompanyCount,
        "readyYn": len(allMissing) == 0
    }
