"""
calculationengine.py
레이어: Utils
역할: KPI 계산 규칙 실행 엔진 — 위상 정렬 기반 의존성 해소 및 수식 평가.
"""
from __future__ import annotations

from collections import defaultdict, deque
from decimal import Decimal
from typing import Any, Optional


STATUS_CALCULATED = "CALCULATED"
STATUS_SOURCE_NOT_READY = "CALCULATION_SOURCE_NOT_READY"
STATUS_ZERO_DIVISION = "CALCULATION_ZERO_DIVISION"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_REFERENCE_SOURCE_AMBIGUOUS = "CALCULATION_REFERENCE_SOURCE_AMBIGUOUS"

FORMULA_REFERENCE_COPY = "REFERENCE_COPY"
FORMULA_ENTITY_SUM = "ENTITY_SUM"
FORMULA_ENTITY_RATIO = "ENTITY_RATIO"
FORMULA_ENTITY_DIVIDE = "ENTITY_DIVIDE"
FORMULA_ENTITY_YOY_DIFF = "ENTITY_YOY_DIFF"
FORMULA_ENTITY_YOY_RATE = "ENTITY_YOY_RATE"
FORMULA_ROLLUP_SUM = "ROLLUP_SUM"
FORMULA_ROLLUP_REFERENCE_COPY = "ROLLUP_REFERENCE_COPY"
FORMULA_ROLLUP_ADD = "ROLLUP_ADD"
FORMULA_ROLLUP_RATIO_RECALC = "ROLLUP_RATIO_RECALC"
FORMULA_ROLLUP_DIVIDE = "ROLLUP_DIVIDE"
FORMULA_ROLLUP_YOY_DIFF = "ROLLUP_YOY_DIFF"
FORMULA_ROLLUP_YOY_RATE = "ROLLUP_YOY_RATE"

ZERO_DIVISION_RETURN_NULL_AND_FLAG = "RETURN_NULL_AND_FLAG"
ZERO_DIVISION_NOT_APPLICABLE = "NOT_APPLICABLE"

YOY_DIRECTION_CURRENT_MINUS_PRIOR = "CURRENT_MINUS_PRIOR"
YOY_DIRECTION_PRIOR_MINUS_CURRENT = "PRIOR_MINUS_CURRENT"

ROUNDING_2DP = "ROUND_2DP"
ROUNDING_0 = "ROUND_0"

NUMERIC_SUM_FORMULAS = {FORMULA_ENTITY_SUM, FORMULA_ROLLUP_SUM, FORMULA_ROLLUP_ADD}
RATIO_FORMULAS = {FORMULA_ENTITY_RATIO, FORMULA_ROLLUP_RATIO_RECALC}
DIVIDE_FORMULAS = {FORMULA_ENTITY_DIVIDE, FORMULA_ROLLUP_DIVIDE}
YOY_DIFF_FORMULAS = {FORMULA_ENTITY_YOY_DIFF, FORMULA_ROLLUP_YOY_DIFF}
YOY_RATE_FORMULAS = {FORMULA_ENTITY_YOY_RATE, FORMULA_ROLLUP_YOY_RATE}
REFERENCE_COPY_FORMULAS = {FORMULA_REFERENCE_COPY, FORMULA_ROLLUP_REFERENCE_COPY}


def calculateRules(
    rules: list[dict],
    sources: list[dict],
    currentFacts: list[dict],
    priorFacts: Optional[list[dict]] = None,
) -> list[dict]:
    orderedRules = topologicalSortRules(rules, sources)
    sourceByRule = groupSourcesByRule(sources)
    currentFactMap = buildFactMap(currentFacts)
    for targetId in {targetAtomicMetricId(rule) for rule in orderedRules if targetAtomicMetricId(rule)}:
        currentFactMap.pop(targetId, None)
    priorFactMap = buildFactMap(priorFacts or [])
    results = []

    for rule in orderedRules:
        result = calculateRule(rule, sourceByRule.get(ruleCode(rule), []), currentFactMap, priorFactMap)
        results.append(result)
        if result["calculationStatus"] == STATUS_CALCULATED:
            currentFactMap[result["targetAtomicMetricId"]] = {
                "atomic_metric_id": result["targetAtomicMetricId"],
                "value_numeric": result.get("valueNumeric"),
                "value_text": result.get("valueText"),
                "unit": result.get("unit"),
            }
    return results


def calculateRule(
    rule: dict,
    sources: list[dict],
    currentFactMap: dict[str, dict],
    priorFactMap: Optional[dict[str, dict]] = None,
) -> dict:
    formulaType = normalizeFormulaType(rule.get("formula_type") or rule.get("formulaType"))
    normalizedSources = normalizeSources(sources)
    priorFactMap = priorFactMap or {}
    base = buildResultBase(rule, formulaType)

    if not normalizedSources:
        return sourceNotReady(base, [])

    if formulaType in REFERENCE_COPY_FORMULAS:
        return calculateReferenceCopy(base, normalizedSources, currentFactMap)
    if formulaType in NUMERIC_SUM_FORMULAS:
        return calculateSum(base, normalizedSources, currentFactMap)
    if formulaType in RATIO_FORMULAS:
        return calculateRatio(base, normalizedSources, currentFactMap, multiplier=100)
    if formulaType in DIVIDE_FORMULAS:
        return calculateRatio(base, normalizedSources, currentFactMap, multiplier=1)
    if formulaType in YOY_DIFF_FORMULAS:
        return calculateYoy(base, normalizedSources, currentFactMap, priorFactMap, rateYn=False)
    if formulaType in YOY_RATE_FORMULAS:
        return calculateYoy(base, normalizedSources, currentFactMap, priorFactMap, rateYn=True)

    return {
        **base,
        "calculationStatus": "CALCULATION_FORMULA_NOT_SUPPORTED",
        "calculationTrace": {"formulaType": formulaType, "sourceCount": len(normalizedSources)},
        "warning": f"Unsupported formulaType: {formulaType}",
    }


def calculateReferenceCopy(base: dict, sources: list[dict], currentFactMap: dict[str, dict]) -> dict:
    if len(sources) >= 2:
        return {
            **base,
            "valueNumeric": None,
            "valueText": None,
            "calculationStatus": STATUS_REFERENCE_SOURCE_AMBIGUOUS,
            "calculationTrace": {"sourceAtomicMetricIds": [s["sourceAtomicMetricId"] for s in sources]},
            "warning": STATUS_REFERENCE_SOURCE_AMBIGUOUS,
        }
    source = sources[0]
    fact = currentFactMap.get(source["sourceAtomicMetricId"])
    if fact is None:
        return sourceNotReady(base, [source["sourceAtomicMetricId"]])
    return calculated(
        base,
        valueNumeric=toNumber(fact.get("value_numeric")),
        valueText=fact.get("value_text"),
        unit=fact.get("unit") or base.get("unit"),
        trace={"sourceAtomicMetricIds": [source["sourceAtomicMetricId"]]},
    )


def calculateSum(base: dict, sources: list[dict], currentFactMap: dict[str, dict]) -> dict:
    values, missing = valuesForSources(sources, currentFactMap)
    if missing:
        return sourceNotReady(base, missing)
    return calculated(
        base,
        valueNumeric=applyRounding(sum(values), base.get("roundingPolicy")),
        unit=base.get("unit"),
        trace={"sourceAtomicMetricIds": [source["sourceAtomicMetricId"] for source in sources]},
    )


def calculateRatio(
    base: dict,
    sources: list[dict],
    currentFactMap: dict[str, dict],
    multiplier: int,
) -> dict:
    numeratorSources = [source for source in sources if source["sourceRole"] == "NUMERATOR"]
    denominatorSources = [source for source in sources if source["sourceRole"] == "DENOMINATOR"]
    if not numeratorSources or not denominatorSources:
        if len(sources) >= 2:
            numeratorSources = [sources[0]]
            denominatorSources = sources[1:]
        else:
            return sourceNotReady(base, [source["sourceAtomicMetricId"] for source in sources])

    numeratorValues, numeratorMissing = valuesForSources(numeratorSources, currentFactMap)
    denominatorValues, denominatorMissing = valuesForSources(denominatorSources, currentFactMap)
    missing = numeratorMissing + denominatorMissing
    if missing:
        return sourceNotReady(base, missing)

    denominator = sum(denominatorValues)
    if denominator == 0:
        return zeroDivision(base, denominatorSources)

    value = sum(numeratorValues) / denominator * multiplier
    return calculated(
        base,
        valueNumeric=applyRounding(value, base.get("roundingPolicy")),
        unit=base.get("unit"),
        trace={
            "numeratorAtomicMetricIds": [source["sourceAtomicMetricId"] for source in numeratorSources],
            "denominatorAtomicMetricIds": [source["sourceAtomicMetricId"] for source in denominatorSources],
            "multiplier": multiplier,
        },
    )


def calculateYoy(
    base: dict,
    sources: list[dict],
    currentFactMap: dict[str, dict],
    priorFactMap: dict[str, dict],
    rateYn: bool,
) -> dict:
    currentSources = [source for source in sources if source["sourceRole"] == "CURRENT"] or [sources[0]]
    priorSources = [source for source in sources if source["sourceRole"] == "PRIOR"] or currentSources
    currentValues, currentMissing = valuesForSources(currentSources, currentFactMap)
    priorValues, priorMissing = valuesForSources(priorSources, priorFactMap)
    missing = currentMissing + priorMissing
    if missing:
        return sourceNotReady(base, missing)

    currentValue = sum(currentValues)
    priorValue = sum(priorValues)
    if rateYn and priorValue == 0:
        return zeroDivision(base, priorSources)

    directionCode = normalizeYoyDirection(base.get("yoyDirectionCode"))
    delta = (
        priorValue - currentValue
        if directionCode == YOY_DIRECTION_PRIOR_MINUS_CURRENT
        else currentValue - priorValue
    )
    value = (delta / priorValue * 100) if rateYn else delta
    return calculated(
        base,
        valueNumeric=applyRounding(value, base.get("roundingPolicy")),
        unit=base.get("unit"),
        trace={
            "currentAtomicMetricIds": [source["sourceAtomicMetricId"] for source in currentSources],
            "priorAtomicMetricIds": [source["sourceAtomicMetricId"] for source in priorSources],
            "yoyDirectionCode": directionCode,
            "currentValue": currentValue,
            "priorValue": priorValue,
            "delta": delta,
        },
    )


def resolveAffectedRuleGraph(
    rules: list[dict],
    sources: list[dict],
    changedAtomicMetricIds: list[str],
) -> list[dict]:
    changed = set(changedAtomicMetricIds or [])
    if not changed:
        return []
    ruleByCode = {ruleCode(rule): rule for rule in rules}
    sourceByRule = groupSourcesByRule(sources)
    targetByRuleCode = {code: targetAtomicMetricId(rule) for code, rule in ruleByCode.items()}

    affectedCodes = set()
    queue = deque(changed)
    while queue:
        atomicId = queue.popleft()
        for code, ruleSources in sourceByRule.items():
            if code in affectedCodes:
                continue
            if any(source["sourceAtomicMetricId"] == atomicId for source in ruleSources):
                affectedCodes.add(code)
                targetId = targetByRuleCode.get(code)
                if targetId:
                    queue.append(targetId)

    ordered = topologicalSortRules([ruleByCode[code] for code in affectedCodes], sources)
    return ordered


def topologicalSortRules(rules: list[dict], sources: list[dict]) -> list[dict]:
    duplicateTargets = duplicateTargetAtomicIds(rules)
    if duplicateTargets:
        raise ValueError(f"CALCULATION_TARGET_DUPLICATED: {', '.join(sorted(duplicateTargets))}")

    ruleByCode = {ruleCode(rule): rule for rule in rules}
    targetToRuleCode = {targetAtomicMetricId(rule): code for code, rule in ruleByCode.items()}
    sourceByRule = groupSourcesByRule(sources)
    indegree = {code: 0 for code in ruleByCode}
    downstream = defaultdict(set)
    dependencyEdges = set()

    for code in ruleByCode:
        for source in sourceByRule.get(code, []):
            dependencyCode = targetToRuleCode.get(source["sourceAtomicMetricId"])
            if dependencyCode == code:
                raise ValueError("CALCULATION_RULE_CYCLE")
            if dependencyCode:
                edge = (dependencyCode, code)
                if edge in dependencyEdges:
                    continue
                dependencyEdges.add(edge)
                downstream[dependencyCode].add(code)
                indegree[code] += 1

    ready = sorted(
        [code for code, degree in indegree.items() if degree == 0],
        key=lambda code: sortKey(ruleByCode[code]),
    )
    queue = deque(ready)
    orderedCodes = []
    while queue:
        code = queue.popleft()
        orderedCodes.append(code)
        nextCodes = []
        for childCode in downstream.get(code, set()):
            indegree[childCode] -= 1
            if indegree[childCode] == 0:
                nextCodes.append(childCode)
        for childCode in sorted(nextCodes, key=lambda value: sortKey(ruleByCode[value])):
            queue.append(childCode)

    if len(orderedCodes) != len(ruleByCode):
        raise ValueError("CALCULATION_RULE_CYCLE")
    return [ruleByCode[code] for code in orderedCodes]


def duplicateTargetAtomicIds(rules: list[dict]) -> set[str]:
    counts = defaultdict(int)
    for rule in rules:
        targetId = targetAtomicMetricId(rule)
        if targetId:
            counts[targetId] += 1
    return {targetId for targetId, count in counts.items() if count > 1}


def allResultsCalculated(results: list[dict]) -> bool:
    return bool(results) and all(
        str(result.get("calculationStatus") or "").strip().upper() == STATUS_CALCULATED
        for result in results
    )


def buildFactMap(facts: list[dict]) -> dict[str, dict]:
    result = {}
    for fact in facts or []:
        atomicId = fact.get("atomic_metric_id") or fact.get("atomicMetricId")
        if atomicId:
            result[str(atomicId)] = fact
    return result


def semanticSourceKey(source: dict) -> tuple[str, str, str, str]:
    return (
        source["ruleCode"],
        source["sourceAtomicMetricId"],
        source["sourceRole"],
        source["sourceScope"],
    )


def groupSourcesByRule(sources: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    seen = set()
    for source in sources or []:
        normalized = normalizeSource(source)
        if normalized["ruleCode"]:
            key = semanticSourceKey(normalized)
            if key in seen:
                continue
            seen.add(key)
            grouped[normalized["ruleCode"]].append(normalized)
    for ruleSources in grouped.values():
        ruleSources.sort(key=lambda source: source["sourceOrder"])
    return dict(grouped)


def normalizeSources(sources: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for source in sources or []:
        normalized = normalizeSource(source)
        key = semanticSourceKey(normalized)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def normalizeSource(source: dict) -> dict:
    return {
        "ruleCode": str(source.get("calculation_rule_code") or source.get("ruleCode") or "").strip(),
        "sourceAtomicMetricId": str(source.get("source_atomic_metric_id") or source.get("sourceAtomicMetricId") or "").strip(),
        "sourceRole": str(source.get("source_role") or source.get("sourceRole") or "SOURCE").strip().upper(),
        "sourceScope": str(source.get("source_scope") or source.get("sourceScope") or "").strip().upper(),
        "sourceOrder": int(source.get("source_order") or source.get("sourceOrder") or source.get("id") or 0),
    }


def valuesForSources(sources: list[dict], factMap: dict[str, dict]) -> tuple[list[float], list[str]]:
    values = []
    missing = []
    for source in sources:
        atomicId = source["sourceAtomicMetricId"]
        fact = factMap.get(atomicId)
        value = toNumber(fact.get("value_numeric")) if fact else None
        if value is None:
            missing.append(atomicId)
        else:
            values.append(value)
    return values, missing


def calculated(
    base: dict,
    *,
    valueNumeric: Optional[float] = None,
    valueText: Optional[str] = None,
    unit: Optional[str] = None,
    trace: Optional[dict] = None,
) -> dict:
    return {
        **base,
        "valueNumeric": valueNumeric,
        "valueText": valueText,
        "unit": unit,
        "calculationStatus": STATUS_CALCULATED,
        "calculationTrace": trace or {},
        "warning": None,
    }


def sourceNotReady(base: dict, missingAtomicMetricIds: list[str]) -> dict:
    return {
        **base,
        "valueNumeric": None,
        "valueText": None,
        "calculationStatus": STATUS_SOURCE_NOT_READY,
        "calculationTrace": {"missingSourceAtomicMetricIds": missingAtomicMetricIds},
        "warning": STATUS_SOURCE_NOT_READY,
    }


def zeroDivision(base: dict, denominatorSources: list[dict]) -> dict:
    policy = str(base.get("zeroDivisionPolicy") or "").strip().upper()
    status = STATUS_NOT_APPLICABLE if policy == ZERO_DIVISION_NOT_APPLICABLE else STATUS_ZERO_DIVISION
    return {
        **base,
        "valueNumeric": None,
        "valueText": None,
        "calculationStatus": status,
        "calculationTrace": {
            "denominatorAtomicMetricIds": [source["sourceAtomicMetricId"] for source in denominatorSources],
            "zeroDivisionPolicy": policy or ZERO_DIVISION_RETURN_NULL_AND_FLAG,
        },
        "warning": "ZERO_DIVISION",
    }


def buildResultBase(rule: dict, formulaType: str) -> dict:
    return {
        "ruleCode": ruleCode(rule),
        "targetAtomicMetricId": targetAtomicMetricId(rule),
        "metricId": rule.get("metric_id") or rule.get("metricId"),
        "valueNumeric": None,
        "valueText": None,
        "unit": rule.get("output_unit") or rule.get("unit"),
        "formulaType": formulaType,
        "zeroDivisionPolicy": rule.get("zero_division_policy") or rule.get("zeroDivisionPolicy"),
        "roundingPolicy": rule.get("rounding_policy") or rule.get("roundingPolicy"),
        "yoyDirectionCode": normalizeYoyDirection(
            rule.get("yoy_direction_code") or rule.get("yoyDirectionCode")
        ),
    }


def normalizeYoyDirection(value: Optional[str]) -> str:
    normalized = str(value or "").strip().upper()
    if normalized == YOY_DIRECTION_PRIOR_MINUS_CURRENT:
        return YOY_DIRECTION_PRIOR_MINUS_CURRENT
    return YOY_DIRECTION_CURRENT_MINUS_PRIOR


def applyRounding(value: float, roundingPolicy: Optional[str]) -> float:
    policy = str(roundingPolicy or "").strip().upper()
    if policy == ROUNDING_2DP:
        return round(value, 2)
    if policy == ROUNDING_0:
        return round(value)
    return value


def toNumber(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalizeFormulaType(value: Any) -> str:
    return str(value or "").strip().upper()


def ruleCode(rule: dict) -> str:
    return str(rule.get("calculation_rule_code") or rule.get("ruleCode") or "").strip()


def targetAtomicMetricId(rule: dict) -> str:
    return str(rule.get("target_atomic_metric_id") or rule.get("targetAtomicMetricId") or "").strip()


def sortKey(rule: dict) -> tuple[int, str]:
    try:
        order = int(rule.get("execution_order") or rule.get("executionOrder") or 0)
    except (TypeError, ValueError):
        order = 0
    return order, ruleCode(rule)


__all__ = [
    "STATUS_CALCULATED",
    "STATUS_SOURCE_NOT_READY",
    "STATUS_ZERO_DIVISION",
    "STATUS_NOT_APPLICABLE",
    "YOY_DIRECTION_CURRENT_MINUS_PRIOR",
    "YOY_DIRECTION_PRIOR_MINUS_CURRENT",
    "normalizeYoyDirection",
    "calculateRules",
    "calculateRule",
    "resolveAffectedRuleGraph",
    "topologicalSortRules",
    "duplicateTargetAtomicIds",
    "allResultsCalculated",
    "buildFactMap",
    "groupSourcesByRule",
    "normalizeSources",
    "ruleCode",
    "targetAtomicMetricId",
    "STATUS_REFERENCE_SOURCE_AMBIGUOUS",
]
