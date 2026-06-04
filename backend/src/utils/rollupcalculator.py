from __future__ import annotations
from typing import Any

from src.utils.calculationengine import (
    normalizeSources,
    groupSourcesByRule,
    calculateRule,
    STATUS_CALCULATED,
    topologicalSortRules,
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
        key = (companyId, atomicMetricId)
        factMap[key] = {
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
    companyIds: list[int]
) -> tuple[list[dict], list[dict], bool]:
    normalizedSources = normalizeSources(sources)
    groupedSources = groupSourcesByRule(normalizedSources)
    try:
        orderedRules = topologicalSortRules(rules, normalizedSources)
    except ValueError as e:
        return [], [{"ruleCode": "GRAPH", "error": str(e), "message": str(e)}], False

    results = []
    warnings = []
    consolidatedFactMap = {}

    for rule in orderedRules:
        ruleCode = rule.get("calculation_rule_code") or rule.get("ruleCode")
        ruleSources = groupedSources.get(ruleCode) or []
        try:
            res = _calculateConsolidatedRule(
                rule,
                ruleSources,
                currentFactsMap,
                priorFactsMap,
                companyIds,
                consolidatedFactMap,
            )
            results.append(res)
            consolidatedFactMap[res["groupAtomicMetricId"]] = {
                "atomicMetricId": res["groupAtomicMetricId"],
                "valueNumeric": res.get("valueNumeric"),
                "valueText": res.get("valueText"),
                "unit": res.get("unit"),
            }
        except CalculationError as e:
            warnings.append({"ruleCode": ruleCode, "error": e.code, "message": str(e)})
            return results, warnings, False
        except Exception as e:
            warnings.append({"ruleCode": ruleCode, "error": "CALCULATION_ENGINE_ERROR", "message": str(e)})
            return results, warnings, False
            
    return results, warnings, True

def _calculateConsolidatedRule(
    rule: dict,
    ruleSources: list[dict],
    currentFactsMap: dict[tuple[int, str], dict],
    priorFactsMap: dict[tuple[int, str], dict],
    companyIds: list[int],
    consolidatedFactMap: dict[str, dict],
) -> dict:
    ruleCode = rule["calculation_rule_code"]
    formula = str(rule.get("formula_type")).upper()
    targetAtomicId = rule["target_atomic_metric_id"]
    
    sourceAtomicIds = [s["sourceAtomicMetricId"] for s in ruleSources]
    
    def getValue(fact: dict) -> Any:
        if fact.get("valueNumeric") is not None:
            return fact.get("valueNumeric")
        if fact.get("value_numeric") is not None:
            return fact.get("value_numeric")
        if fact.get("valueText") is not None:
            return fact.get("valueText")
        return fact.get("value_text")

    def getCompanyValues(atomicId: str, fmap: dict, isPrior: bool = False) -> dict[int, Any]:
        cv = {}
        for cid in companyIds:
            f = fmap.get((cid, atomicId))
            value = getValue(f) if f else None
            if value is None:
                raise CalculationError("CALCULATION_SOURCE_NOT_READY", f"Rule {ruleCode} missing source {atomicId} for company {cid} (prior={isPrior})")
            cv[cid] = value
        return cv

    def getSourceValue(atomicId: str, fmap: dict) -> tuple[Any, dict]:
        consolidatedFact = consolidatedFactMap.get(atomicId)
        if consolidatedFact:
            value = getValue(consolidatedFact)
            if value is None:
                raise CalculationError("CALCULATION_SOURCE_NOT_READY", f"Rule {ruleCode} missing consolidated source {atomicId}")
            return value, {"__group__": value}
        companyValues = getCompanyValues(atomicId, fmap)
        return _aggregateSum(companyValues), companyValues

    if formula == FORMULA_ROLLUP_REFERENCE_COPY:
        if len(ruleSources) == 0:
            raise CalculationError("CALCULATION_SOURCE_NOT_READY", f"Rule {ruleCode} has no sources")
        if len(ruleSources) > 1:
            raise CalculationError("CALCULATION_REFERENCE_SOURCE_AMBIGUOUS", f"Rule {ruleCode} has multiple distinct semantic sources")
            
        atomicId = ruleSources[0]["sourceAtomicMetricId"]
        consolidatedFact = consolidatedFactMap.get(atomicId)
        if consolidatedFact:
            val = getValue(consolidatedFact)
            cv = {"__group__": val}
        else:
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
        sourceValue, cv = getSourceValue(atomicId, currentFactsMap)
        engineFactMap[atomicId] = {"value_numeric": sourceValue}
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
