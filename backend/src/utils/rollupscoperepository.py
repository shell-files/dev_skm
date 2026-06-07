import json
from typing import Optional
from src.utils.db import findAll, findOne
from src.utils.calculationengine import normalizeSource, topologicalSortRules
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
    from src.utils.calculationrepository import listActiveRules
    return listActiveRules(executionScope="CONSOLIDATED", metricIds=metricIds)

def listBatchRuleSources(ruleCodes: list[str]) -> list[dict]:
    from src.utils.calculationrepository import listRuleSources
    return listRuleSources(ruleCodes)

def listProducerRulesByTargetAtomicIds(atomicMetricIds: list[str]) -> list[dict]:
    from src.utils.calculationrepository import listActiveRulesByTargetAtomicIds
    return listActiveRulesByTargetAtomicIds(atomicMetricIds, executionScope="CONSOLIDATED")

def resolveConsolidatedRuleClosure(initialMetricIds: list[str]) -> tuple[list[dict], list[dict]]:
    rules = listBatchRules(initialMetricIds)
    ruleByCode = {
        rule["calculation_rule_code"]: rule
        for rule in rules
        if rule.get("calculation_rule_code")
    }
    sourceByRuleCode = {}
    searchedAtomicIds = set()

    while True:
        ruleCodes = sorted(ruleByCode.keys())
        sources = listBatchRuleSources(ruleCodes)
        sourceByRuleCode = {}
        for source in sources:
            ruleCode = source.get("calculation_rule_code")
            if ruleCode in ruleByCode:
                sourceByRuleCode.setdefault(ruleCode, []).append(source)

        targetAtomicIds = {
            str(rule.get("target_atomic_metric_id") or "").strip()
            for rule in ruleByCode.values()
            if rule.get("target_atomic_metric_id")
        }
        sourceAtomicIds = {
            normalizeSource(source)["sourceAtomicMetricId"]
            for source in sources
            if normalizeSource(source)["sourceAtomicMetricId"]
        }
        candidateAtomicIds = sorted(sourceAtomicIds - targetAtomicIds - searchedAtomicIds)
        if not candidateAtomicIds:
            break
        searchedAtomicIds.update(candidateAtomicIds)

        producerRules = listProducerRulesByTargetAtomicIds(candidateAtomicIds)
        addedYn = False
        for producerRule in producerRules:
            ruleCode = producerRule.get("calculation_rule_code")
            if ruleCode and ruleCode not in ruleByCode:
                ruleByCode[ruleCode] = producerRule
                addedYn = True
        if not addedYn:
            continue

    closureSources = [
        source
        for ruleSources in sourceByRuleCode.values()
        for source in ruleSources
    ]
    orderedRules = topologicalSortRules(list(ruleByCode.values()), closureSources)
    orderedRuleCodes = {rule["calculation_rule_code"] for rule in orderedRules}
    return orderedRules, [
        source
        for source in closureSources
        if source.get("calculation_rule_code") in orderedRuleCodes
    ]

def resolveConsolidatedRulesFromBatchScopeTx(cur, batchId: int) -> tuple[list[dict], list[dict]]:
    from src.utils.calculationrepository import listActiveRulesByTargetAtomicIdsTx, listRuleSourcesTx

    scopes = listScopeTx(cur, batchId)
    snapshotTargetAtomicIds = sorted({
        str(scope.get("group_atomic_metric_id") or "").strip()
        for scope in scopes
        if str(scope.get("group_atomic_metric_id") or "").strip()
    })
    if not snapshotTargetAtomicIds:
        raise ValueError("ROLLUP_BATCH_SCOPE_RULE_MISMATCH")

    rules = listActiveRulesByTargetAtomicIdsTx(
        cur,
        snapshotTargetAtomicIds,
        executionScope="CONSOLIDATED",
    )
    resolvedTargetAtomicIds = sorted({
        str(rule.get("target_atomic_metric_id") or "").strip()
        for rule in rules
        if str(rule.get("target_atomic_metric_id") or "").strip()
    })
    if resolvedTargetAtomicIds != snapshotTargetAtomicIds:
        raise ValueError("ROLLUP_BATCH_SCOPE_RULE_MISMATCH")

    ruleCodes = sorted({
        str(rule.get("calculation_rule_code") or "").strip()
        for rule in rules
        if str(rule.get("calculation_rule_code") or "").strip()
    })
    sources = listRuleSourcesTx(cur, ruleCodes)

    snapshotSourcesByTarget = {}
    for scope in scopes:
        targetAtomicId = str(scope.get("group_atomic_metric_id") or "").strip()
        if not targetAtomicId:
            continue
        snapshotSourcesByTarget[targetAtomicId] = sorted(set(scope.get("sourceAtomicMetricIds") or []))

    ruleTargetByCode = {
        str(rule.get("calculation_rule_code") or "").strip(): str(rule.get("target_atomic_metric_id") or "").strip()
        for rule in rules
        if str(rule.get("calculation_rule_code") or "").strip()
    }
    metadataSourcesByTarget = {targetAtomicId: set() for targetAtomicId in snapshotTargetAtomicIds}
    for source in sources:
        ruleCode = str(source.get("calculation_rule_code") or "").strip()
        targetAtomicId = ruleTargetByCode.get(ruleCode)
        if not targetAtomicId:
            continue
        sourceAtomicId = normalizeSource(source).get("sourceAtomicMetricId")
        if sourceAtomicId:
            metadataSourcesByTarget.setdefault(targetAtomicId, set()).add(sourceAtomicId)

    for targetAtomicId in snapshotTargetAtomicIds:
        snapshotSourceIds = snapshotSourcesByTarget.get(targetAtomicId, [])
        metadataSourceIds = sorted(metadataSourcesByTarget.get(targetAtomicId, set()))
        if metadataSourceIds != snapshotSourceIds:
            raise ValueError("ROLLUP_BATCH_SCOPE_METADATA_CHANGED")

    orderedRules = topologicalSortRules(rules, sources)
    orderedRuleCodes = {rule["calculation_rule_code"] for rule in orderedRules}
    return orderedRules, [
        source
        for source in sources
        if source.get("calculation_rule_code") in orderedRuleCodes
    ]

def resolveConsolidatedRulesFromBatchScope(batchId: int) -> tuple[list[dict], list[dict]]:
    from src.utils.db import getConn
    conn = getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            return resolveConsolidatedRulesFromBatchScopeTx(cur, batchId)
    finally:
        conn.close()

def saveScopeFromRulesTx(cur, batchId: int, rules: list[dict], sources: list[dict], scopeReason: str) -> None:
    sourceMap = {}
    for source in sources:
        ruleCode = source["calculation_rule_code"]
        sourceMap.setdefault(ruleCode, []).append(source)

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
        sourceIds = sorted(set(sourceIds))
        payloadStr = json.dumps(sourceIds) if sourceIds else None

        cur.execute(
            """
            SELECT id, source_atomic_metric_ids
            FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE
            WHERE esg_rollup_batch_id = ? AND group_atomic_metric_id = ?
            """,
            (batchId, rule["target_atomic_metric_id"])
        )
        existing = cur.fetchone()
        if existing:
            existingPayload = existing["source_atomic_metric_ids"]
            existingIds = sorted(set(decodeAtomicIds(existingPayload)))
            payloadIds = sorted(set(decodeAtomicIds(payloadStr)))
            if existingIds != payloadIds:
                raise ValueError("ROLLUP_BATCH_SCOPE_IMMUTABLE")
        else:
            cur.execute(
                """
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
                """,
                (
                    batchId,
                    rule.get("metric_id"),
                    rule["target_atomic_metric_id"],
                    payloadStr,
                    scopeReason
                )
            )

def listScopeTx(cur, batchId: int) -> list[dict]:
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
    cur.execute(sql, (batchId,))
    rows = cur.fetchall()
    for row in rows:
        row["sourceAtomicMetricIds"] = decodeAtomicIds(row.get("source_atomic_metric_ids"))
    return rows

def decodeAtomicIds(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    rawValue = str(value).strip()
    if not rawValue:
        return []
    try:
        parsedValue = json.loads(rawValue)
        if isinstance(parsedValue, list):
            return [str(item).strip() for item in parsedValue if str(item).strip()]
        if parsedValue:
            return [str(parsedValue).strip()]
        return []
    except Exception:
        return [item.strip() for item in rawValue.split(",") if item.strip()]

def listScope(batchId: int) -> list[dict]:
    from src.utils.db import getConn
    conn = getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            return listScopeTx(cur, batchId)
    finally:
        conn.close()

def resolveAllRuleSourceAtomicIdsFromScopes(scopes: list[dict]) -> list[str]:
    atomicIds = set()
    for s in scopes:
        for a in s.get("sourceAtomicMetricIds", []):
            atomicIds.add(a)
    return sorted(list(atomicIds))

def resolveConsolidatedTargetAtomicIdsFromScopes(scopes: list[dict]) -> list[str]:
    return sorted({
        str(s.get("group_atomic_metric_id") or "").strip()
        for s in scopes
        if str(s.get("group_atomic_metric_id") or "").strip()
    })

def resolveExternalEntitySourceAtomicIdsFromScopes(scopes: list[dict]) -> list[str]:
    allRuleSourceAtomicIds = set(resolveAllRuleSourceAtomicIdsFromScopes(scopes))
    consolidatedTargetAtomicIds = set(resolveConsolidatedTargetAtomicIdsFromScopes(scopes))
    return sorted(allRuleSourceAtomicIds - consolidatedTargetAtomicIds)

def resolveAllRuleSourceAtomicIdsTx(cur, batchId: int) -> list[str]:
    return resolveAllRuleSourceAtomicIdsFromScopes(listScopeTx(cur, batchId))

def resolveAllRuleSourceAtomicIds(batchId: int) -> list[str]:
    return resolveAllRuleSourceAtomicIdsFromScopes(listScope(batchId))

def resolveExternalEntitySourceAtomicIdsTx(cur, batchId: int) -> list[str]:
    return resolveExternalEntitySourceAtomicIdsFromScopes(listScopeTx(cur, batchId))

def resolveExternalEntitySourceAtomicIds(batchId: int) -> list[str]:
    return resolveExternalEntitySourceAtomicIdsFromScopes(listScope(batchId))

def resolveRequiredSourceAtomicIdsTx(cur, batchId: int) -> list[str]:
    return resolveExternalEntitySourceAtomicIdsTx(cur, batchId)

def resolveRequiredSourceAtomicIds(batchId: int) -> list[str]:
    return resolveExternalEntitySourceAtomicIds(batchId)

def resolveRequiredGroupAtomicIdsTx(cur, batchId: int) -> list[str]:
    scopes = listScopeTx(cur, batchId)
    return sorted([s["group_atomic_metric_id"] for s in scopes if s.get("group_atomic_metric_id")])

def resolveRequiredGroupAtomicIds(batchId: int) -> list[str]:
    scopes = listScope(batchId)
    return sorted([s["group_atomic_metric_id"] for s in scopes if s.get("group_atomic_metric_id")])

def normalizeFact(row: dict) -> dict:
    companyId = row.get("companyId") if row.get("companyId") is not None else row.get("company_id")
    reportingYear = row.get("reportingYear") if row.get("reportingYear") is not None else row.get("reporting_year")
    atomicMetricId = row.get("atomicMetricId") or row.get("atomic_metric_id")
    return {
        "companyId": int(companyId),
        "reportingYear": int(reportingYear),
        "atomicMetricId": atomicMetricId,
        "metricId": row.get("metricId") or row.get("metric_id"),
        "valueNumeric": row.get("valueNumeric") if row.get("valueNumeric") is not None else row.get("value_numeric"),
        "valueText": row.get("valueText") if row.get("valueText") is not None else row.get("value_text"),
        "unit": row.get("unit"),
        "approvalStatus": row.get("approvalStatus") or row.get("approval_status"),
    }

def listApprovedFactsByCompany(companyIds: list[int], reportingYear: int, atomicMetricIds: list[str]) -> list[dict]:
    if not companyIds or not atomicMetricIds:
        return []
    rows = listApprovedEntityFacts(companyIds, reportingYear, atomicMetricIds)
    return [normalizeFact(r) for r in rows]

def listPriorYearApprovedFactsByCompany(companyIds: list[int], reportingYear: int, atomicMetricIds: list[str]) -> list[dict]:
    if not companyIds or not atomicMetricIds:
        return []
    rows = listApprovedEntityFacts(companyIds, reportingYear - 1, atomicMetricIds)
    return [normalizeFact(r) for r in rows]

def buildSourceReadiness(batchId: int, sourceCompanyIds: list[int], reportingYear: int) -> dict:
    requiredAtomicIds = resolveExternalEntitySourceAtomicIds(batchId)
    requiredFactCount = len(requiredAtomicIds) * len(sourceCompanyIds)
    if not requiredAtomicIds or not sourceCompanyIds:
        return {
            "requiredAtomicCount": len(requiredAtomicIds),
            "requiredFactCount": requiredFactCount,
            "approvedFactCount": 0,
            "missingByCompany": {
                str(companyId): requiredAtomicIds
                for companyId in sourceCompanyIds
            },
            "approvedAtomicCount": 0,
            "missingAtomicMetricIds": requiredAtomicIds,
            "sourceCompanyCount": len(sourceCompanyIds),
            "readySourceCompanyCount": 0,
            "readyYn": False
        }

    facts = listApprovedFactsByCompany(sourceCompanyIds, reportingYear, requiredAtomicIds)
    approvedKeys = set()
    for f in facts:
        approvedKeys.add((f["companyId"], f["atomicMetricId"]))

    readySourceCompanyCount = 0
    allMissing = set()
    missingByCompany = {}
    for cid in sourceCompanyIds:
        companyMissing = [a for a in requiredAtomicIds if (cid, a) not in approvedKeys]
        missingByCompany[str(cid)] = companyMissing
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
        "requiredFactCount": requiredFactCount,
        "approvedFactCount": len(approvedKeys),
        "missingByCompany": missingByCompany,
        "approvedAtomicCount": len(requiredAtomicIds) - len(allMissing),
        "missingAtomicMetricIds": sorted(list(allMissing)),
        "sourceCompanyCount": len(sourceCompanyIds),
        "readySourceCompanyCount": readySourceCompanyCount,
        "readyYn": len(allMissing) == 0
    }
