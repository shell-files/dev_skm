from __future__ import annotations
from typing import Any
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
    # If all companies have the same value, copy it.
    # If they differ, it's CALCULATION_REFERENCE_VALUE_AMBIGUOUS
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
    # Returns (companyId, atomicMetricId) -> fact dict
    factMap = {}
    for fact in facts:
        key = (int(fact["companyId"]), fact["atomicMetricId"])
        factMap[key] = fact
    return factMap

def calculateConsolidatedRule(
    rule: dict,
    sources: list[dict],
    currentFactsMap: dict[tuple[int, str], dict],
    priorFactsMap: dict[tuple[int, str], dict],
    companyIds: list[int]
) -> dict:
    ruleCode = rule["calculation_rule_code"]
    formula = str(rule.get("formula_type")).upper()
    targetAtomicId = rule["target_atomic_metric_id"]
    
    # 1. Normalize and dedupe sources for the rule
    normalizedSources = normalizeSources(sources)
    grouped = groupSourcesByRule(normalizedSources)
    ruleSources = grouped.get(ruleCode) or []
    
    sourceAtomicIds = [s["sourceAtomicMetricId"] for s in ruleSources]
    
    # 2. Extract company values per source atomic ID
    def getCompanyValues(atomicId: str, fmap: dict) -> dict[int, Any]:
        cv = {}
        for cid in companyIds:
            f = fmap.get((cid, atomicId))
            if f and f.get("valueNumeric") is not None:
                cv[cid] = f["valueNumeric"]
            elif f and f.get("valueText") is not None:
                cv[cid] = f["valueText"]
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
            "groupAtomicMetricId": targetAtomicId,
            "sourceAtomicMetricIds": sourceAtomicIds,
            "formulaType": formula,
            "valueNumeric": val if is_numeric else None,
            "valueText": str(val) if not is_numeric else None,
            "sourceCompanyValues": {str(k): v for k,v in cv.items()},
        }

    # All other formulas are numeric aggregations
    # Build pre-aggregated engine map for calculationengine.py
    # Since calculationengine expects atomicId -> fact
    engineFactMap = {}
    sourceCompanyValuesTrace = {}
    
    for s in ruleSources:
        atomicId = s["sourceAtomicMetricId"]
        cv = getCompanyValues(atomicId, currentFactsMap)
        sumVal = _aggregateSum(cv)
        engineFactMap[atomicId] = {"valueNumeric": sumVal}
        # Keep trace of first source for simple trace (or we can combine them, but MVP keep it simple)
        if atomicId not in sourceCompanyValuesTrace:
            sourceCompanyValuesTrace[atomicId] = cv
            
    # For YoY, we need prior pre-aggregated values
    enginePriorFactMap = {}
    if formula in (FORMULA_ROLLUP_YOY_DIFF, FORMULA_ROLLUP_YOY_RATE):
        for s in ruleSources:
            atomicId = s["sourceAtomicMetricId"]
            cv_prior = getCompanyValues(atomicId, priorFactsMap)
            sumValPrior = _aggregateSum(cv_prior)
            enginePriorFactMap[atomicId] = {"valueNumeric": sumValPrior}

    # 3. Delegate to Calculation Engine
    try:
        engineResult = calculateRule(rule, ruleSources, engineFactMap, enginePriorFactMap)
        
        if engineResult.get("calculationStatus") != STATUS_CALCULATED:
            raise CalculationError(
                engineResult.get("calculationStatus") or "CALCULATION_ERROR",
                engineResult.get("warning") or f"Calculation failed for rule {ruleCode}"
            )
            
        return {
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

__all__ = ["buildMultiCompanyFactMap", "calculateConsolidatedRule", "CalculationError"]
