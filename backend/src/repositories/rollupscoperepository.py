"""
rollupscoperepository.py
레이어: Repository
역할: 롤업 스코프 지표 목록 조회 및 계산 규칙 정렬.
"""
import json
from typing import Optional
from src.utils.db import findAll, findOne
from src.utils.calculationengine import normalizeSource, topologicalSortRules
from src.repositories.calculationrepository import listApprovedEntityFacts, listApprovedEntityFactsTx

# 부모 회사·연도·목적 기준 롤업 소스 회사 목록 조회
def listEffectiveSourceCompanies(parentCompanyId: int, reportingYear: int, rollupPurposeCode: str) -> list[dict]:
    # DB 기반 관계 — 자기 참조 체크는 호출자 책임
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

# 연결 스코프 활성 계산 규칙 목록 조회
def listBatchRules(metricIds: list[str]) -> list[dict]:
    from src.repositories.calculationrepository import listActiveRules
    return listActiveRules(executionScope="CONSOLIDATED", metricIds=metricIds)

# 계산 규칙 코드 기준 소스 목록 조회
def listBatchRuleSources(ruleCodes: list[str]) -> list[dict]:
    from src.repositories.calculationrepository import listRuleSources
    return listRuleSources(ruleCodes)

# 대상 원자 지표별 연결 스코프 계산 규칙 목록 조회
def listProducerRulesByTargetAtomicIds(atomicMetricIds: list[str]) -> list[dict]:
    from src.repositories.calculationrepository import listActiveRulesByTargetAtomicIds
    return listActiveRulesByTargetAtomicIds(atomicMetricIds, executionScope="CONSOLIDATED")

# 계산 규칙 의존성 클로저 재귀 탐색 — 위상 정렬된 (rules, sources) 반환
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

# 배치 스코프 기준 계산 규칙·소스 목록 검증 및 조회 — 스냅샷 불일치 시 ValueError (트랜잭션 커서용)
def resolveConsolidatedRulesFromBatchScopeTx(cur, batchId: int) -> tuple[list[dict], list[dict]]:
    from src.repositories.calculationrepository import listActiveRulesByTargetAtomicIdsTx, listRuleSourcesTx

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

# 배치 스코프 기준 계산 규칙·소스 목록 검증 및 조회
def resolveConsolidatedRulesFromBatchScope(batchId: int) -> tuple[list[dict], list[dict]]:
    from src.utils.db import getConn
    conn = getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            return resolveConsolidatedRulesFromBatchScopeTx(cur, batchId)
    finally:
        conn.close()

# 계산 규칙에서 배치 원자 스코프 행 INSERT — 기존 스코프 변경 시 ValueError (트랜잭션 커서용)
def saveScopeFromRulesTx(
    cur,
    batchId: int,
    rules: list[dict],
    sources: list[dict],
    scopeReason: str,
    directMetricIds: list[str] | None = None,
) -> None:
    sourceMap = {}
    for source in sources:
        ruleCode = source["calculation_rule_code"]
        sourceMap.setdefault(ruleCode, []).append(source)
    directMetricSet = {
        str(metricId or "").strip()
        for metricId in directMetricIds or []
        if str(metricId or "").strip()
    }

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
            ruleScopeReason = scopeReason
            if directMetricIds is not None:
                metricId = str(rule.get("metric_id") or "").strip()
                scopeKind = "DIRECT_REQUEST" if metricId in directMetricSet else "CLOSURE_DEPENDENCY"
                ruleScopeReason = f"{scopeReason}:{scopeKind}"

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
                    ruleScopeReason
                )
            )

# 배치 기준 활성 원자 스코프 목록 조회 (트랜잭션 커서용)
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

# source_atomic_metric_ids JSON 문자열 → list 파싱
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

# 배치 기준 활성 원자 스코프 목록 조회
def listScope(batchId: int) -> list[dict]:
    from src.utils.db import getConn
    conn = getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            return listScopeTx(cur, batchId)
    finally:
        conn.close()

# 배치에서 직접 요청된(DIRECT_REQUEST) 지표 ID 목록 조회
def listRequestedMetricIdsFromBatchScope(batchId: int) -> list[str]:
    rows = findAll(
        """
        SELECT DISTINCT metric_id
        FROM ESG_ROLLUP_BATCH_ATOMIC_SCOPE
        WHERE esg_rollup_batch_id = ?
          AND delete_yn = 0
          AND required_yn = 1
          AND scope_reason LIKE '%:DIRECT_REQUEST'
          AND metric_id IS NOT NULL
          AND metric_id <> ''
        ORDER BY metric_id
        """,
        (batchId,),
    ) or []
    return [
        str(row.get("metric_id") or "").strip()
        for row in rows
        if str(row.get("metric_id") or "").strip()
    ]

# 원자 지표 ID 기준 지표명 메타데이터 목록 조회
def listAtomicMetadata(atomicMetricIds: list[str]) -> list[dict]:
    cleaned = [
        str(atomicMetricId or "").strip()
        for atomicMetricId in atomicMetricIds or []
        if str(atomicMetricId or "").strip()
    ]
    if not cleaned:
        return []
    placeholders = ", ".join(["?"] * len(cleaned))
    return findAll(
        f"""
        SELECT
            metric_id AS metricId,
            metric_name_kr AS metricName,
            atomic_metric_id AS atomicMetricId,
            atomic_name_kr AS atomicName
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE atomic_metric_id IN ({placeholders})
          AND active_yn = 1
          AND delete_yn = 0
        ORDER BY metric_id, atomic_metric_id
        """,
        tuple(cleaned),
    ) or []

# 스코프 목록에서 모든 소스 원자 지표 ID 추출
def resolveAllRuleSourceAtomicIdsFromScopes(scopes: list[dict]) -> list[str]:
    atomicIds = set()
    for s in scopes:
        for a in s.get("sourceAtomicMetricIds", []):
            atomicIds.add(a)
    return sorted(list(atomicIds))

# 스코프 목록에서 연결 대상 원자 지표 ID 추출
def resolveConsolidatedTargetAtomicIdsFromScopes(scopes: list[dict]) -> list[str]:
    return sorted({
        str(s.get("group_atomic_metric_id") or "").strip()
        for s in scopes
        if str(s.get("group_atomic_metric_id") or "").strip()
    })

# 스코프 목록에서 연결 대상 제외 외부 ENTITY 소스 원자 지표 ID 추출
def resolveExternalEntitySourceAtomicIdsFromScopes(scopes: list[dict]) -> list[str]:
    allRuleSourceAtomicIds = set(resolveAllRuleSourceAtomicIdsFromScopes(scopes))
    consolidatedTargetAtomicIds = set(resolveConsolidatedTargetAtomicIdsFromScopes(scopes))
    return sorted(allRuleSourceAtomicIds - consolidatedTargetAtomicIds)

# 규칙 소스에서 source_scope=CONSOLIDATED인 원자 지표 ID 추출
def resolveConsolidatedSourceAtomicIdsFromRuleSources(ruleSources: list[dict]) -> list[str]:
    atomicIds = set()
    for source in ruleSources or []:
        normalized = normalizeSource(source)
        if normalized.get("sourceScope") == "CONSOLIDATED":
            atomicId = normalized.get("sourceAtomicMetricId")
            if atomicId:
                atomicIds.add(atomicId)
    return sorted(atomicIds)

# 배치 스코프 규칙 소스에서 CONSOLIDATED scope 원자 ID 추출 (경량 조회, 트랜잭션 커서용)
def resolveConsolidatedSourceAtomicIdsFromBatchTx(cur, batchId: int) -> list[str]:
    from src.repositories.calculationrepository import listActiveRulesByTargetAtomicIdsTx, listRuleSourcesTx

    targetAtomicIds = resolveConsolidatedTargetAtomicIdsFromScopes(listScopeTx(cur, batchId))
    if not targetAtomicIds:
        return []
    rules = listActiveRulesByTargetAtomicIdsTx(cur, targetAtomicIds, executionScope="CONSOLIDATED")
    ruleCodes = sorted({
        str(rule.get("calculation_rule_code") or "").strip()
        for rule in rules
        if str(rule.get("calculation_rule_code") or "").strip()
    })
    if not ruleCodes:
        return []
    ruleSources = listRuleSourcesTx(cur, ruleCodes)
    return resolveConsolidatedSourceAtomicIdsFromRuleSources(ruleSources)

# 배치 스코프 규칙 소스에서 CONSOLIDATED scope 원자 ID 추출
def resolveConsolidatedSourceAtomicIdsFromBatch(batchId: int) -> list[str]:
    from src.utils.db import getConn
    conn = getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            return resolveConsolidatedSourceAtomicIdsFromBatchTx(cur, batchId)
    finally:
        conn.close()

# 배치 스코프 전체 소스 원자 지표 ID 목록 조회 (트랜잭션 커서용)
def resolveAllRuleSourceAtomicIdsTx(cur, batchId: int) -> list[str]:
    return resolveAllRuleSourceAtomicIdsFromScopes(listScopeTx(cur, batchId))

# 배치 스코프 전체 소스 원자 지표 ID 목록 조회
def resolveAllRuleSourceAtomicIds(batchId: int) -> list[str]:
    return resolveAllRuleSourceAtomicIdsFromScopes(listScope(batchId))

# CONSOLIDATED scope 소스 제외 후 외부 ENTITY 소스 원자 ID 목록 조회 (트랜잭션 커서용)
def resolveExternalEntitySourceAtomicIdsTx(cur, batchId: int) -> list[str]:
    # source_scope=CONSOLIDATED 소스(예: 연결 기준값 E1-06__G0003)는 회사별 ENTITY
    # KPI_FACT 입력 대상이 아니므로 readiness/missing 계산에서 제외한다.
    entityCandidates = resolveExternalEntitySourceAtomicIdsFromScopes(listScopeTx(cur, batchId))
    consolidatedSet = set(resolveConsolidatedSourceAtomicIdsFromBatchTx(cur, batchId))
    return [atomicId for atomicId in entityCandidates if atomicId not in consolidatedSet]

# CONSOLIDATED scope 소스 제외 후 외부 ENTITY 소스 원자 ID 목록 조회
def resolveExternalEntitySourceAtomicIds(batchId: int) -> list[str]:
    entityCandidates = resolveExternalEntitySourceAtomicIdsFromScopes(listScope(batchId))
    consolidatedSet = set(resolveConsolidatedSourceAtomicIdsFromBatch(batchId))
    return [atomicId for atomicId in entityCandidates if atomicId not in consolidatedSet]

# 지표별 외부 ENTITY 소스 원자 ID 목록 조회 (트랜잭션 커서용)
def resolveExternalEntitySourceAtomicIdsByMetricTx(
    cur,
    batchId: int,
    metricId: str,
) -> list[str]:
    requiredAtomicIds = resolveExternalEntitySourceAtomicIdsTx(cur, batchId)

    if not requiredAtomicIds:
        return []

    placeholders = ", ".join(["?"] * len(requiredAtomicIds))

    cur.execute(
        f"""
        SELECT atomic_metric_id
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE metric_id = ?
          AND atomic_metric_id IN ({placeholders})
          AND onboarding_input_yn = 1
          AND active_yn = 1
          AND delete_yn = 0
          AND UPPER(COALESCE(atomic_data_role, ''))
              NOT IN ('DERIVED', 'ROLLUP_READONLY')
        ORDER BY atomic_metric_id
        """,
        (metricId, *requiredAtomicIds),
    )

    return [
        row["atomic_metric_id"]
        for row in cur.fetchall() or []
        if row.get("atomic_metric_id")
    ]

def resolveExternalEntitySourceAtomicIdsByMetric(
    batchId: int,
    metricId: str,
) -> list[str]:
    from src.utils.db import getConn
    conn = getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            return resolveExternalEntitySourceAtomicIdsByMetricTx(cur, batchId, metricId)
    finally:
        conn.close()

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

def listApprovedFactsByCompanyTx(cur, companyIds: list[int], reportingYear: int, atomicMetricIds: list[str]) -> list[dict]:
    if not companyIds or not atomicMetricIds:
        return []
    rows = listApprovedEntityFactsTx(cur, companyIds, reportingYear, atomicMetricIds)
    return [normalizeFact(r) for r in rows]

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

def buildSourceReadinessFromFacts(
    requiredAtomicIds: list[str],
    sourceCompanyIds: list[int],
    facts: list[dict],
) -> dict:
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

def buildSourceReadinessTx(cur, batchId: int, sourceCompanyIds: list[int], reportingYear: int) -> dict:
    requiredAtomicIds = resolveExternalEntitySourceAtomicIdsTx(cur, batchId)
    facts = listApprovedFactsByCompanyTx(cur, sourceCompanyIds, reportingYear, requiredAtomicIds)
    return buildSourceReadinessFromFacts(requiredAtomicIds, sourceCompanyIds, facts)

def buildSourceReadiness(batchId: int, sourceCompanyIds: list[int], reportingYear: int) -> dict:
    requiredAtomicIds = resolveExternalEntitySourceAtomicIds(batchId)
    facts = listApprovedFactsByCompany(sourceCompanyIds, reportingYear, requiredAtomicIds)
    return buildSourceReadinessFromFacts(requiredAtomicIds, sourceCompanyIds, facts)
