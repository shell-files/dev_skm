<<<<<<< HEAD
"""
calculationengine.py
레이어: Utils
역할: KPI 계산 규칙 실행 엔진 — 위상 정렬 기반 의존성 해소 및 수식 평가.
"""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """
    규칙 목록을 위상 정렬 후 순서대로 실행하여 계산 결과 목록을 반환한다.
    계산된 결과는 이후 규칙의 입력(factMap)으로 즉시 반영된다.
    """
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """formulaType을 식별하여 해당 계산 함수로 위임하고 결과 dict를 반환한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """단일 소스 값을 그대로 복사한다. 소스가 2개 이상이면 AMBIGUOUS 상태를 반환한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """모든 소스 값을 합산하고 roundingPolicy를 적용한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """
    분자 합계 / 분모 합계 * multiplier 를 계산한다.
    multiplier=100이면 비율(%), multiplier=1이면 단순 나눗셈(DIVIDE)이다.
    분모가 0이면 zeroDivisionPolicy에 따라 처리한다.
    """
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """
    전년 대비 차이(diff) 또는 증감률(rate)을 계산한다.
    rateYn=True 이면 (delta / priorValue * 100), False 이면 절대 delta.
    yoyDirectionCode로 current-prior 또는 prior-current 방향을 지정한다.
    """
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """
    변경된 atomic metric ID에서 시작해 의존 그래프를 BFS로 탐색하여
    영향받는 규칙을 위상 정렬된 순서로 반환한다.
    """
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """
    규칙 간 의존성을 분석하여 Kahn's algorithm으로 위상 정렬된 실행 순서를 반환한다.
    중복 target이나 순환 의존이 감지되면 ValueError를 발생시킨다.
    """
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """규칙 목록에서 동일한 target atomic metric ID를 가진 중복 규칙의 ID 집합을 반환한다."""
=======
>>>>>>> origin/skm_test
    counts = defaultdict(int)
    for rule in rules:
        targetId = targetAtomicMetricId(rule)
        if targetId:
            counts[targetId] += 1
    return {targetId for targetId, count in counts.items() if count > 1}


def allResultsCalculated(results: list[dict]) -> bool:
<<<<<<< HEAD
    """결과 목록이 비어있지 않고 모든 항목이 CALCULATED 상태인지 확인한다."""
=======
>>>>>>> origin/skm_test
    return bool(results) and all(
        str(result.get("calculationStatus") or "").strip().upper() == STATUS_CALCULATED
        for result in results
    )


def buildFactMap(facts: list[dict]) -> dict[str, dict]:
<<<<<<< HEAD
    """fact 목록을 atomic_metric_id 키의 dict로 변환한다 (camelCase/snake_case 모두 지원)."""
=======
>>>>>>> origin/skm_test
    result = {}
    for fact in facts or []:
        atomicId = fact.get("atomic_metric_id") or fact.get("atomicMetricId")
        if atomicId:
            result[str(atomicId)] = fact
    return result


def semanticSourceKey(source: dict) -> tuple[str, str, str, str]:
<<<<<<< HEAD
    """source의 ruleCode·sourceAtomicMetricId·role·scope 네 필드를 조합한 의미 중복 판별용 키를 반환한다."""
=======
>>>>>>> origin/skm_test
    return (
        source["ruleCode"],
        source["sourceAtomicMetricId"],
        source["sourceRole"],
        source["sourceScope"],
    )


def groupSourcesByRule(sources: list[dict]) -> dict[str, list[dict]]:
<<<<<<< HEAD
    """source 목록을 ruleCode 기준으로 그룹핑하고 sourceOrder로 정렬한다. 의미 중복은 제거한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """source 목록을 정규화하고 의미 중복(동일 ruleCode+sourceAtomicMetricId+role+scope)을 제거한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """snake_case·camelCase 혼용 source dict를 camelCase 표준 필드로 정규화해 반환한다."""
=======
>>>>>>> origin/skm_test
    return {
        "ruleCode": str(source.get("calculation_rule_code") or source.get("ruleCode") or "").strip(),
        "sourceAtomicMetricId": str(source.get("source_atomic_metric_id") or source.get("sourceAtomicMetricId") or "").strip(),
        "sourceRole": str(source.get("source_role") or source.get("sourceRole") or "SOURCE").strip().upper(),
        "sourceScope": str(source.get("source_scope") or source.get("sourceScope") or "").strip().upper(),
        "sourceOrder": int(source.get("source_order") or source.get("sourceOrder") or source.get("id") or 0),
    }


def valuesForSources(sources: list[dict], factMap: dict[str, dict]) -> tuple[list[float], list[str]]:
<<<<<<< HEAD
    """source 목록에서 factMap을 조회해 유효한 숫자 값 목록과 누락된 atomicMetricId 목록을 반환한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """base에 계산 결과값과 STATUS_CALCULATED 상태를 병합한 결과 dict를 반환한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """누락된 source atomicMetricId 목록을 포함해 STATUS_SOURCE_NOT_READY 상태의 결과 dict를 반환한다."""
=======
>>>>>>> origin/skm_test
    return {
        **base,
        "valueNumeric": None,
        "valueText": None,
        "calculationStatus": STATUS_SOURCE_NOT_READY,
        "calculationTrace": {"missingSourceAtomicMetricIds": missingAtomicMetricIds},
        "warning": STATUS_SOURCE_NOT_READY,
    }


def zeroDivision(base: dict, denominatorSources: list[dict]) -> dict:
<<<<<<< HEAD
    """zeroDivisionPolicy에 따라 NOT_APPLICABLE 또는 ZERO_DIVISION 상태의 결과 dict를 반환한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """rule 메타데이터로부터 계산 결과의 공통 기본 필드(ruleCode, unit, policy 등)를 구성해 반환한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    """YoY 방향 코드를 대문자로 정규화하고, 유효하지 않은 값은 CURRENT_MINUS_PRIOR로 기본값을 반환한다."""
=======
>>>>>>> origin/skm_test
    normalized = str(value or "").strip().upper()
    if normalized == YOY_DIRECTION_PRIOR_MINUS_CURRENT:
        return YOY_DIRECTION_PRIOR_MINUS_CURRENT
    return YOY_DIRECTION_CURRENT_MINUS_PRIOR


def applyRounding(value: float, roundingPolicy: Optional[str]) -> float:
<<<<<<< HEAD
    """roundingPolicy(2DP/0)에 따라 소수점 2자리 또는 정수로 반올림한 값을 반환한다."""
=======
>>>>>>> origin/skm_test
    policy = str(roundingPolicy or "").strip().upper()
    if policy == ROUNDING_2DP:
        return round(value, 2)
    if policy == ROUNDING_0:
        return round(value)
    return value


def toNumber(value: Any) -> Optional[float]:
<<<<<<< HEAD
    """임의 타입 값을 float으로 변환하며, None이거나 변환 불가한 경우 None을 반환한다."""
=======
>>>>>>> origin/skm_test
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalizeFormulaType(value: Any) -> str:
<<<<<<< HEAD
    """formula type 값을 대문자 strip 문자열로 정규화해 반환한다."""
=======
>>>>>>> origin/skm_test
    return str(value or "").strip().upper()


def ruleCode(rule: dict) -> str:
<<<<<<< HEAD
    """rule dict에서 calculation_rule_code 또는 ruleCode를 추출해 strip된 문자열로 반환한다."""
=======
>>>>>>> origin/skm_test
    return str(rule.get("calculation_rule_code") or rule.get("ruleCode") or "").strip()


def targetAtomicMetricId(rule: dict) -> str:
<<<<<<< HEAD
    """rule dict에서 target_atomic_metric_id 또는 targetAtomicMetricId를 추출해 strip된 문자열로 반환한다."""
=======
>>>>>>> origin/skm_test
    return str(rule.get("target_atomic_metric_id") or rule.get("targetAtomicMetricId") or "").strip()


def sortKey(rule: dict) -> tuple[int, str]:
<<<<<<< HEAD
    """rule의 execution_order와 ruleCode를 조합해 위상 정렬용 정렬 키를 반환한다."""
=======
>>>>>>> origin/skm_test
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
<<<<<<< HEAD
    "normalizeSources",
    "ruleCode",
    "targetAtomicMetricId",
=======
>>>>>>> origin/skm_test
    "STATUS_REFERENCE_SOURCE_AMBIGUOUS",
]
