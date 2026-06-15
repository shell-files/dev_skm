from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Optional

from src.utils.calculationengine import (
    STATUS_CALCULATED,
    calculateRule,
    groupSourcesByRule,
    normalizeSources,
    topologicalSortRules,
)


class CalculationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


FORMULA_ROLLUP_SUM = "ROLLUP_SUM"
FORMULA_ROLLUP_REFERENCE_COPY = "ROLLUP_REFERENCE_COPY"
FORMULA_ROLLUP_ADD = "ROLLUP_ADD"
FORMULA_ROLLUP_RATIO_RECALC = "ROLLUP_RATIO_RECALC"
FORMULA_ROLLUP_DIVIDE = "ROLLUP_DIVIDE"
FORMULA_ROLLUP_YOY_DIFF = "ROLLUP_YOY_DIFF"
FORMULA_ROLLUP_YOY_RATE = "ROLLUP_YOY_RATE"


def _aggregateSum(factsByCompany: dict[int, float | int | str]) -> float | int:
    total = Decimal("0")
    for value in factsByCompany.values():
        if value is None:
            continue
        total += Decimal(str(value))
    if total == total.to_integral_value():
        return int(total)
    return float(total)


def _aggregateReference(factsByCompany: dict[int, Any], code: str) -> Any:
    distinctValues = set()
    firstValue = None
    for value in factsByCompany.values():
        if value is None:
            continue
        distinctValues.add(str(value))
        if firstValue is None:
            firstValue = value

    if len(distinctValues) == 0:
        return None
    if len(distinctValues) > 1:
        raise CalculationError(
            "CALCULATION_REFERENCE_VALUE_AMBIGUOUS",
            f"Rule {code} reference values differ across companies",
        )
    return firstValue


def buildSourceTrace(sourceCompanyValuesTrace: dict[str, dict]) -> dict:
    return {
        str(atomicId): {
            str(companyId): value
            for companyId, value in companyValues.items()
        }
        for atomicId, companyValues in sourceCompanyValuesTrace.items()
    }


def buildMultiCompanyFactMap(
    companyIds: list[int],
    atomicMetricIds: list[str],
    facts: list[dict],
) -> dict[tuple[int, str], dict]:
    allowedCompanyIds = {int(companyId) for companyId in companyIds or []}
    allowedAtomicMetricIds = {str(atomicMetricId) for atomicMetricId in atomicMetricIds or []}
    factMap = {}
    for fact in facts or []:
        companyId = fact.get("companyId") if fact.get("companyId") is not None else fact.get("company_id")
        atomicMetricId = fact.get("atomicMetricId") or fact.get("atomic_metric_id")
        if companyId is None or not atomicMetricId:
            continue
        companyId = int(companyId)
        atomicMetricId = str(atomicMetricId)
        if allowedCompanyIds and companyId not in allowedCompanyIds:
            continue
        if allowedAtomicMetricIds and atomicMetricId not in allowedAtomicMetricIds:
            continue
        factMap[(companyId, atomicMetricId)] = {
            "companyId": companyId,
            "atomicMetricId": atomicMetricId,
            "valueNumeric": fact.get("valueNumeric") if fact.get("valueNumeric") is not None else fact.get("value_numeric"),
            "valueText": fact.get("valueText") if fact.get("valueText") is not None else fact.get("value_text"),
            "unit": fact.get("unit"),
        }
    return factMap


def calculateConsolidatedRules(
    rules: list[dict],
    sources: list[dict],
    currentFactsMap: dict[tuple[int, str], dict],
    priorFactsMap: dict[tuple[int, str], dict],
    companyIds: list[int],
) -> tuple[list[dict], list[dict], bool]:
    return calculateConsolidatedRulesByYear(
        rules=rules,
        sources=sources,
        entityFactMapsByYear={0: currentFactsMap or {}, -1: priorFactsMap or {}},
        reportingYear=0,
        companyIds=companyIds,
    )


def buildConsolidatedFactMap(rows: list[dict]) -> dict[str, dict]:
    """
    ESG_GROUP_ROLLUP_RESULT 조회 행을 atomicId -> fact dict 로 변환한다.
    source_scope=CONSOLIDATED source 평가용 연결 결과 맵으로 사용된다.
    """
    factMap: dict[str, dict] = {}
    for row in rows or []:
        atomicId = (
            row.get("groupAtomicMetricId")
            or row.get("group_atomic_metric_id")
            or row.get("atomicMetricId")
            or row.get("atomic_metric_id")
        )
        if not atomicId:
            continue
        atomicId = str(atomicId)
        factMap[atomicId] = {
            "atomicMetricId": atomicId,
            "valueNumeric": row.get("valueNumeric") if row.get("valueNumeric") is not None else row.get("value_numeric"),
            "valueText": row.get("valueText") if row.get("valueText") is not None else row.get("value_text"),
            "unit": row.get("unit"),
        }
    return factMap


def resolveHistoricalLookbackDepth(rules: list[dict], sources: list[dict]) -> int:
    ruleByCode = {ruleCode(rule): rule for rule in rules or [] if ruleCode(rule)}
    producerByAtomicId = {
        targetAtomicMetricId(rule): ruleCode(rule)
        for rule in rules or []
        if targetAtomicMetricId(rule) and ruleCode(rule)
    }
    sourceByRule = groupSourcesByRule(normalizeSources(sources))
    memo = {}

    def atomicDepth(atomicId: str, stack: set[str]) -> int:
        producerCode = producerByAtomicId.get(atomicId)
        if not producerCode:
            return 0
        return ruleDepth(producerCode, stack)

    def ruleDepth(code: str, stack: set[str]) -> int:
        if code in memo:
            return memo[code]
        if code in stack:
            raise ValueError("CALCULATION_RULE_CYCLE")
        stack.add(code)
        rule = ruleByCode.get(code)
        if not rule:
            stack.remove(code)
            return 0

        depth = 0
        ruleSources = sourceByRule.get(code) or []
        if isYoyFormula(rule):
            currentSources, priorSources = splitYoySources(ruleSources)
            for source in currentSources:
                depth = max(depth, atomicDepth(source["sourceAtomicMetricId"], stack))
            for source in priorSources:
                depth = max(depth, 1 + atomicDepth(source["sourceAtomicMetricId"], stack))
        else:
            for source in ruleSources:
                depth = max(depth, atomicDepth(source["sourceAtomicMetricId"], stack))
        stack.remove(code)
        memo[code] = depth
        return depth

    return max((ruleDepth(code, set()) for code in ruleByCode), default=0)


def calculateConsolidatedRulesByYear(
    rules: list[dict],
    sources: list[dict],
    entityFactMapsByYear: dict[int, dict[tuple[int, str], dict]],
    reportingYear: int,
    companyIds: list[int],
    consolidatedFactMapsByYear: Optional[dict[int, dict[str, dict]]] = None,
) -> tuple[list[dict], list[dict], bool]:
    normalizedSources = normalizeSources(sources)
    groupedSources = groupSourcesByRule(normalizedSources)
    ruleByCode = {ruleCode(rule): rule for rule in rules or [] if ruleCode(rule)}
    producerByAtomicId = {
        targetAtomicMetricId(rule): ruleCode(rule)
        for rule in rules or []
        if targetAtomicMetricId(rule) and ruleCode(rule)
    }

    try:
        orderedRules = topologicalSortRules(rules, normalizedSources)
        historicalLookbackDepth = resolveHistoricalLookbackDepth(rules, normalizedSources)
    except ValueError as error:
        return [], [{"ruleCode": "GRAPH", "error": str(error), "message": str(error)}], False

    # source_scope=CONSOLIDATED source(예: 전년도 연결 기준값)는 ESG_GROUP_ROLLUP_RESULT
    # 에서 조회한 연결 결과로 시드한다. 이번 batch에서 producer rule이 산출하는 연결값은
    # 계산 중 같은 맵에 누적되어 후속 rule이 참조한다.
    seededConsolidated = consolidatedFactMapsByYear or {}
    consolidatedFactMapsByYear: dict[int, dict[str, dict]] = defaultdict(dict)
    for seedYear, seedFacts in seededConsolidated.items():
        for seedAtomicId, seedFact in (seedFacts or {}).items():
            consolidatedFactMapsByYear[int(seedYear)][str(seedAtomicId)] = seedFact
    atomicMemo: dict[tuple[int, str], dict] = {}
    ruleMemo: dict[tuple[int, str], dict] = {}
    activeRuleStack: set[tuple[int, str]] = set()

    def resolveConsolidatedSourceAtYear(atomicId: str, year: int) -> dict:
        factsForYear = consolidatedFactMapsByYear.get(int(year), {})
        fact = factsForYear.get(atomicId)
        value = getFactValue(fact) if fact else None
        if value is None:
            return {
                "status": "CALCULATION_SOURCE_NOT_READY",
                "fact": None,
                "trace": {
                    "atomicMetricId": atomicId,
                    "evaluatedYear": year,
                    "sourceScope": "CONSOLIDATED",
                    "missingConsolidatedSource": True,
                },
            }
        numericValue = fact.get("valueNumeric") if fact.get("valueNumeric") is not None else fact.get("value_numeric")
        textValue = fact.get("valueText") if fact.get("valueText") is not None else fact.get("value_text")
        return {
            "status": STATUS_CALCULATED,
            "fact": {
                "atomicMetricId": atomicId,
                "valueNumeric": numericValue,
                "valueText": textValue,
                "unit": fact.get("unit"),
            },
            "trace": {
                "atomicMetricId": atomicId,
                "evaluatedYear": year,
                "sourceScope": "CONSOLIDATED",
                "valueNumeric": numericValue,
            },
        }

    def evaluateAtomicAtYear(
        atomicId: str,
        year: int,
        contextRule: Optional[dict] = None,
        sourceScope: Optional[str] = None,
    ) -> dict:
        memoKey = (int(year), atomicId)
        producerCode = producerByAtomicId.get(atomicId)
        if producerCode:
            if memoKey not in atomicMemo:
                produced = evaluateRuleAtYear(producerCode, year)
                if produced.get("calculationStatus") != STATUS_CALCULATED:
                    atomicMemo[memoKey] = {
                        "status": produced.get("calculationStatus") or "CALCULATION_SOURCE_NOT_READY",
                        "fact": None,
                        "trace": {
                            "atomicMetricId": atomicId,
                            "evaluatedYear": year,
                            "producerRuleCode": producerCode,
                            "producerStatus": produced.get("calculationStatus"),
                            "producerTrace": produced.get("calculationTrace"),
                        },
                    }
                else:
                    atomicMemo[memoKey] = {
                        "status": STATUS_CALCULATED,
                        "fact": {
                            "atomicMetricId": atomicId,
                            "valueNumeric": produced.get("valueNumeric"),
                            "valueText": produced.get("valueText"),
                            "unit": produced.get("unit"),
                        },
                        "trace": {
                            "atomicMetricId": atomicId,
                            "evaluatedYear": year,
                            "producerRuleCode": producerCode,
                            "valueNumeric": produced.get("valueNumeric"),
                        },
                    }
            return atomicMemo[memoKey]

        if str(sourceScope or "").strip().upper() == "CONSOLIDATED":
            return resolveConsolidatedSourceAtYear(atomicId, year)

        return aggregateEntityFactsAtYear(
            atomicId=atomicId,
            year=year,
            companyIds=companyIds,
            entityFactMapsByYear=entityFactMapsByYear,
            rule=contextRule,
        )

    def evaluateRuleAtYear(code: str, year: int) -> dict:
        memoKey = (int(year), code)
        if memoKey in ruleMemo:
            return ruleMemo[memoKey]
        if memoKey in activeRuleStack:
            result = buildRuleResult(ruleByCode.get(code), [], "CALCULATION_RULE_CYCLE", year)
            ruleMemo[memoKey] = result
            return result

        rule = ruleByCode.get(code)
        if not rule:
            result = buildRuleResult({}, [], "CALCULATION_SOURCE_NOT_READY", year)
            ruleMemo[memoKey] = result
            return result

        activeRuleStack.add(memoKey)
        try:
            ruleSources = groupedSources.get(code) or []
            engineFactMap = {}
            enginePriorFactMap = {}
            sourceCompanyValuesTrace = {}
            dependencyTrace = []

            if isYoyFormula(rule):
                currentSources, priorSources = splitYoySources(ruleSources)
                for source in currentSources:
                    sourceResult = evaluateAtomicAtYear(source["sourceAtomicMetricId"], year, rule, source.get("sourceScope"))
                    dependencyTrace.append(traceSource(source, sourceResult, year, "current"))
                    if sourceResult["status"] == STATUS_CALCULATED:
                        engineFactMap[source["sourceAtomicMetricId"]] = normalizeEngineFact(sourceResult["fact"])
                        sourceCompanyValuesTrace[source["sourceAtomicMetricId"]] = sourceCompanyValues(sourceResult)
                for source in priorSources:
                    sourceResult = evaluateAtomicAtYear(source["sourceAtomicMetricId"], year - 1, rule, source.get("sourceScope"))
                    dependencyTrace.append(traceSource(source, sourceResult, year - 1, "prior"))
                    if sourceResult["status"] == STATUS_CALCULATED:
                        enginePriorFactMap[source["sourceAtomicMetricId"]] = normalizeEngineFact(sourceResult["fact"])
            else:
                for source in ruleSources:
                    sourceResult = evaluateAtomicAtYear(source["sourceAtomicMetricId"], year, rule, source.get("sourceScope"))
                    dependencyTrace.append(traceSource(source, sourceResult, year, "current"))
                    if sourceResult["status"] == STATUS_CALCULATED:
                        engineFactMap[source["sourceAtomicMetricId"]] = normalizeEngineFact(sourceResult["fact"])
                        sourceCompanyValuesTrace[source["sourceAtomicMetricId"]] = sourceCompanyValues(sourceResult)

            engineResult = calculateRule(rule, ruleSources, engineFactMap, enginePriorFactMap)
            result = buildRuleResult(rule, ruleSources, engineResult.get("calculationStatus"), year)
            result.update(
                {
                    "valueNumeric": engineResult.get("valueNumeric"),
                    "valueText": engineResult.get("valueText"),
                    "unit": engineResult.get("unit"),
                    "sourceCompanyValues": buildSourceTrace(sourceCompanyValuesTrace),
                    "calculationTrace": {
                        "reportingYear": reportingYear,
                        "evaluatedYear": year,
                        "historicalLookbackDepth": historicalLookbackDepth,
                        "currentPreAggregatedMap": engineFactMap,
                        "priorPreAggregatedMap": enginePriorFactMap,
                        "historicalDependencies": dependencyTrace,
                        "engineTrace": engineResult.get("calculationTrace"),
                    },
                }
            )

            if result["calculationStatus"] == STATUS_CALCULATED:
                consolidatedFactMapsByYear[int(year)][result["groupAtomicMetricId"]] = {
                    "atomicMetricId": result["groupAtomicMetricId"],
                    "valueNumeric": result.get("valueNumeric"),
                    "valueText": result.get("valueText"),
                    "unit": result.get("unit"),
                }

        except CalculationError as error:
            result = buildRuleResult(rule, ruleSources, error.code, year)
            result["calculationTrace"] = {
                "reportingYear": reportingYear,
                "evaluatedYear": year,
                "historicalLookbackDepth": historicalLookbackDepth,
                "errorCode": error.code,
                "errorMessage": error.message,
                "historicalDependencies": dependencyTrace,
            }

        finally:
            activeRuleStack.discard(memoKey)

        ruleMemo[memoKey] = result
        return result

    results = []
    warnings = []
    for rule in orderedRules:
        code = ruleCode(rule)
        result = evaluateRuleAtYear(code, reportingYear)
        results.append(result)
        if result.get("calculationStatus") != STATUS_CALCULATED:
            errorCode = result.get("calculationStatus") or "CALCULATION_ENGINE_ERROR"
            warnings.append({"ruleCode": code, "error": errorCode, "message": errorCode})
            return results, warnings, False

    return results, warnings, True


def aggregateEntityFactsAtYear(
    *,
    atomicId: str,
    year: int,
    companyIds: list[int],
    entityFactMapsByYear: dict[int, dict[tuple[int, str], dict]],
    rule: Optional[dict],
) -> dict:
    factsForYear = entityFactMapsByYear.get(int(year), {})
    companyValues = {}
    missingCompanyIds = []
    for companyId in companyIds:
        fact = factsForYear.get((int(companyId), atomicId))
        value = getFactValue(fact) if fact else None
        if value is None:
            missingCompanyIds.append(int(companyId))
        else:
            companyValues[int(companyId)] = value

    if missingCompanyIds:
        return {
            "status": "CALCULATION_SOURCE_NOT_READY",
            "fact": None,
            "trace": {
                "atomicMetricId": atomicId,
                "evaluatedYear": year,
                "missingCompanyIds": missingCompanyIds,
                "sourceCompanyValues": companyValues,
            },
        }

    formula = str((rule or {}).get("formula_type") or "").upper()
    if formula == FORMULA_ROLLUP_REFERENCE_COPY:
        value = _aggregateReference(companyValues, ruleCode(rule or {}))
    else:
        value = _aggregateSum(companyValues)
    numericYn = isinstance(value, (int, float))
    return {
        "status": STATUS_CALCULATED,
        "fact": {
            "atomicMetricId": atomicId,
            "valueNumeric": value if numericYn else None,
            "valueText": None if numericYn else str(value),
            "unit": None,
        },
        "trace": {
            "atomicMetricId": atomicId,
            "evaluatedYear": year,
            "valueNumeric": value if numericYn else None,
            "sourceCompanyValues": companyValues,
        },
    }


def buildRuleResult(rule: Optional[dict], ruleSources: list[dict], status: str, year: int) -> dict:
    return {
        "groupMetricId": (rule or {}).get("metric_id"),
        "groupAtomicMetricId": targetAtomicMetricId(rule or {}),
        "sourceAtomicMetricIds": [source["sourceAtomicMetricId"] for source in ruleSources],
        "formulaType": str((rule or {}).get("formula_type") or "").upper(),
        "valueNumeric": None,
        "valueText": None,
        "unit": (rule or {}).get("output_unit") or (rule or {}).get("unit"),
        "sourceCompanyValues": {},
        "calculationStatus": status,
        "calculationTrace": {"evaluatedYear": year},
    }


def normalizeEngineFact(fact: dict) -> dict:
    return {
        "value_numeric": fact.get("valueNumeric") if fact.get("valueNumeric") is not None else fact.get("value_numeric"),
        "value_text": fact.get("valueText") if fact.get("valueText") is not None else fact.get("value_text"),
        "unit": fact.get("unit"),
    }


def sourceCompanyValues(sourceResult: dict) -> dict:
    trace = sourceResult.get("trace") or {}
    if trace.get("sourceCompanyValues") is not None:
        return trace["sourceCompanyValues"]
    fact = sourceResult.get("fact") or {}
    return {"__group__": fact.get("valueNumeric")}


def traceSource(source: dict, sourceResult: dict, year: int, sourceTiming: str) -> dict:
    trace = sourceResult.get("trace") or {}
    fact = sourceResult.get("fact") or {}
    return {
        "sourceAtomicMetricId": source.get("sourceAtomicMetricId"),
        "sourceRole": source.get("sourceRole"),
        "sourceTiming": sourceTiming,
        "evaluatedYear": year,
        "status": sourceResult.get("status"),
        "valueNumeric": fact.get("valueNumeric"),
        "sourceCompanyValues": trace.get("sourceCompanyValues"),
        "missingCompanyIds": trace.get("missingCompanyIds"),
        "missingConsolidatedSource": trace.get("missingConsolidatedSource"),
        "sourceScope": trace.get("sourceScope"),
        "producerRuleCode": trace.get("producerRuleCode"),
    }


def isYoyFormula(rule: dict) -> bool:
    return str(rule.get("formula_type") or rule.get("formulaType") or "").upper() in {
        FORMULA_ROLLUP_YOY_DIFF,
        FORMULA_ROLLUP_YOY_RATE,
    }


def splitYoySources(sources: list[dict]) -> tuple[list[dict], list[dict]]:
    currentSources = [source for source in sources if source["sourceRole"] == "CURRENT"]
    if not currentSources and sources:
        currentSources = [sources[0]]
    priorSources = [source for source in sources if source["sourceRole"] == "PRIOR"]
    if not priorSources:
        priorSources = currentSources
    return currentSources, priorSources


def ruleCode(rule: dict) -> str:
    return str(rule.get("calculation_rule_code") or rule.get("ruleCode") or "").strip()


def targetAtomicMetricId(rule: dict) -> str:
    return str(rule.get("target_atomic_metric_id") or rule.get("targetAtomicMetricId") or "").strip()


def getFactValue(fact: Optional[dict]) -> Any:
    if not fact:
        return None
    if fact.get("valueNumeric") is not None:
        return fact.get("valueNumeric")
    if fact.get("value_numeric") is not None:
        return fact.get("value_numeric")
    if fact.get("valueText") is not None:
        return fact.get("valueText")
    return fact.get("value_text")


__all__ = [
    "buildMultiCompanyFactMap",
    "buildConsolidatedFactMap",
    "calculateConsolidatedRules",
    "calculateConsolidatedRulesByYear",
    "resolveHistoricalLookbackDepth",
    "CalculationError",
]
