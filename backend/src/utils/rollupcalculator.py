from __future__ import annotations
from typing import Any
from collections import defaultdict, deque

from src.utils.calculationengine import (
    normalizeSources,
    groupSourcesByRule,
    calculateRule,
    STATUS_CALCULATED
)

class CalculationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

# Supported formulas
FORMULA_ROLLUP_SUM = "ROLLUP_SUM"
FORMULA_ROLLUP_REFERENCE_COPY = "ROLLUP_REFERENCE_COPY"
FORMULA_ROLLUP_ADD = "ROLLUP_ADD"
FORMULA_ROLLUP_RATIO_RECALC = "ROLLUP_RATIO_RECALC"
FORMULA_ROLLUP_DIVIDE = "ROLLUP_DIVIDE"
FORMULA_ROLLUP_YOY_DIFF = "ROLLUP_YOY_DIFF"
FORMULA_ROLLUP_YOY_RATE = "ROLLUP_YOY_RATE"

def _aggregateSum(factsByCompany: dict[int, float|int|str]) -> float|int:
    from decimal import Decimal
    total = Decimal("0")
    for val in factsByCompany.values():
        if val is None:
            continue
        total += Decimal(str(val))
    if total == total.to_integral_value():
        return int(total)
    return float(total)

def _aggregateReference(factsByCompany: dict[int, Any], ruleCode: str) -> Any:
    distinct_values = set()
    first_val = None
    for val in factsByCompany.values():
        if val is not None:
            distinct_values.add(str(val))
            if first_val is None:
                first_val = val
                
    if len(distinct_values) == 0:
        return None
    if len(distinct_values) > 1:
        raise CalculationError(f"CALCULATION_REFERENCE_VALUE_AMBIGUOUS", f"Rule {ruleCode} reference values differ across companies")
    return first_val

def buildMultiCompanyFactMap(
    companyIds: list[int],
    atomicMetricIds: list[str],
    facts: list[dict],
) -> dict[tuple[int, str], dict]:
    factMap = {}
    for fact in facts:
        key = (int(fact["companyId"]), fact["atomicMetricId"])
        factMap[key] = fact
    return factMap

def calculateConsolidatedRules(
    rules: list[dict],
    sources: list[dict],
    currentFactsMap: dict[tuple[int, str], dict],
    priorFactsMap: dict[tuple[int, str], dict],
    companyIds: list[int]
) -> tuple[list[dict], list[dict], bool]:
    
    # Group rules by code
    ruleMap = {r["calculation_rule_code"]: r for r in rules}
    normalizedSources = normalizeSources(sources)
    groupedSources = groupSourcesByRule(normalizedSources)
    
    # Topo sort
    inDegree = defaultdict(int)
    graph = defaultdict(list)
    
    atomicToRuleCode = {r["target_atomic_metric_id"]: r["calculation_rule_code"] for r in rules}
    
    for ruleCode, ruleSources in groupedSources.items():
        if ruleCode not in inDegree:
            inDegree[ruleCode] = 0
            
        for src in ruleSources:
            srcAtomic = src["sourceAtomicMetricId"]
            if srcAtomic in atomicToRuleCode:
                parentRule = atomicToRuleCode[srcAtomic]
                graph[parentRule].append(ruleCode)
                inDegree[ruleCode] += 1

    for rCode in ruleMap:
        if rCode not in inDegree:
            inDegree[rCode] = 0

    queue = deque([r for r, deg in inDegree.items() if deg == 0])
    sortedRuleCodes = []
    
    while queue:
        curr = queue.popleft()
        sortedRuleCodes.append(curr)
        for child in graph[curr]:
            inDegree[child] -= 1
            if inDegree[child] == 0:
                queue.append(child)
                
    if len(sortedRuleCodes) != len(ruleMap):
        # Cycle detected
        return [], [{"ruleCode": "CYCLE", "error": "Dependency cycle detected in rules"}], False

    results = []
    warnings = []
    allSuccess = True
    
    # Calculate in order
    for ruleCode in sortedRuleCodes:
        rule = ruleMap[ruleCode]
        ruleSources = groupedSources.get(ruleCode) or []
        try:
            res = _calculateConsolidatedRule(rule, ruleSources, currentFactsMap, priorFactsMap, companyIds)
            results.append(res)
            # Update currentFactsMap with result for dependent rules?
            # Wait, consolidated result is at the group level!
            # If a dependent rule is also consolidated, it actually reads from the group level?
            # BUT getCompanyValues looks at companyIds (subsidiaries).
            # The calculationengine actually does NOT support inter-group-metric dependency for generic consolidated unless it's calculated.
            # For this context, standard dependency is supported if the graph is properly fed. We feed it to all companyIds so the dependent rule sees the same value for all companies.
            for cid in companyIds:
                currentFactsMap[(cid, rule["target_atomic_metric_id"])] = {
                    "companyId": cid,
                    "atomicMetricId": rule["target_atomic_metric_id"],
                    "valueNumeric": res.get("valueNumeric"),
                    "valueText": res.get("valueText")
                }
        except CalculationError as e:
            warnings.append({"ruleCode": ruleCode, "error": e.code, "message": str(e)})
            allSuccess = False
            break # Fail fast for batch
            
    return results, warnings, allSuccess

def _calculateConsolidatedRule(
    rule: dict,
    ruleSources: list[dict],
    currentFactsMap: dict[tuple[int, str], dict],
    priorFactsMap: dict[tuple[int, str], dict],
    companyIds: list[int]
) -> dict:
    ruleCode = rule["calculation_rule_code"]
    formula = str(rule.get("formula_type")).upper()
    targetAtomicId = rule["target_atomic_metric_id"]
    
    sourceAtomicIds = [s["sourceAtomicMetricId"] for s in ruleSources]
    
    def getCompanyValues(atomicId: str, fmap: dict, isPrior: bool = False) -> dict[int, Any]:
        cv = {}
        for cid in companyIds:
            f = fmap.get((cid, atomicId))
            if f and f.get("valueNumeric") is not None:
                cv[cid] = f["valueNumeric"]
            elif f and f.get("valueText") is not None:
                cv[cid] = f["valueText"]
            else:
                # HIGH: strict prior readiness
                # ANY missing source -> Exception
                raise CalculationError("CALCULATION_SOURCE_NOT_READY", f"Rule {ruleCode} missing source {atomicId} for company {cid} (prior={isPrior})")
        return cv

    if formula == FORMULA_ROLLUP_REFERENCE_COPY:
        if len(ruleSources) == 0:
            raise CalculationError("CALCULATION_SOURCE_NOT_READY", f"Rule {ruleCode} has no sources")
        if len(ruleSources) > 1:
            raise CalculationError("CALCULATION_REFERENCE_SOURCE_AMBIGUOUS", f"Rule {ruleCode} has multiple distinct semantic sources")
            
        atomicId = ruleSources[0]["sourceAtomicMetricId"]
        cv = getCompanyValues(atomicId, currentFactsMap)
        val = _aggregateReference(cv, ruleCode)
        if val is None:
            raise CalculationError("CALCULATION_SOURCE_NOT_READY", f"Rule {ruleCode} source missing or null")
            
        is_numeric = isinstance(val, (int, float))
        return {
            "groupMetricId": rule.get("metric_id"),
            "groupAtomicMetricId": targetAtomicId,
            "sourceAtomicMetricIds": sourceAtomicIds,
            "formulaType": formula,
            "valueNumeric": val if is_numeric else None,
            "valueText": str(val) if not is_numeric else None,
            "sourceCompanyValues": {str(k): v for k,v in cv.items()},
        }

    engineFactMap = {}
    sourceCompanyValuesTrace = {}
    
    for s in ruleSources:
        atomicId = s["sourceAtomicMetricId"]
        cv = getCompanyValues(atomicId, currentFactsMap)
        sumVal = _aggregateSum(cv)
        engineFactMap[atomicId] = {"value_numeric": sumVal}
        if atomicId not in sourceCompanyValuesTrace:
            sourceCompanyValuesTrace[atomicId] = cv
            
    enginePriorFactMap = {}
    if formula in (FORMULA_ROLLUP_YOY_DIFF, FORMULA_ROLLUP_YOY_RATE):
        for s in ruleSources:
            atomicId = s["sourceAtomicMetricId"]
            cv_prior = getCompanyValues(atomicId, priorFactsMap, isPrior=True)
            sumValPrior = _aggregateSum(cv_prior)
            enginePriorFactMap[atomicId] = {"value_numeric": sumValPrior}

    try:
        engineResult = calculateRule(rule, ruleSources, engineFactMap, enginePriorFactMap)
        
        if engineResult.get("calculationStatus") != STATUS_CALCULATED:
            raise CalculationError(
                engineResult.get("calculationStatus") or "CALCULATION_ERROR",
                engineResult.get("warning") or f"Calculation failed for rule {ruleCode}"
            )
            
        return {
            "groupMetricId": rule.get("metric_id"),
            "groupAtomicMetricId": targetAtomicId,
            "sourceAtomicMetricIds": sourceAtomicIds,
            "formulaType": formula,
            "valueNumeric": engineResult.get("valueNumeric"),
            "valueText": engineResult.get("valueText"),
            "unit": engineResult.get("unit"),
            "sourceCompanyValues": {str(cid): val for cid, val in sourceCompanyValuesTrace.get(sourceAtomicIds[0], {}).items()} if sourceAtomicIds else {},
            "calculationTrace": {"preAggregatedMap": engineFactMap, "priorPreAggregatedMap": enginePriorFactMap, "engineTrace": engineResult.get("calculationTrace")}
        }
    except CalculationError as e:
        raise e
    except Exception as e:
        raise CalculationError("CALCULATION_ENGINE_ERROR", str(e))

__all__ = ["buildMultiCompanyFactMap", "calculateConsolidatedRules", "CalculationError"]
