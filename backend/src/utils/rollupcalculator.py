"""
Domain: ESG Rollup
Layer: utils/calculator
Responsibility:
- Calculate enabled rollup formulas for DMA precheck G0-02 batches
- Support SUM and ROLLUP_SUM only
- Return deterministic group rollup result payloads
Public functions:
- calcBatch
- calcSum
Do not:
- do not execute SQL templates
- do not calculate unsupported formulas
- do not mutate DB state
- do not connect DMA scoring pipelines
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


FORMULA_SUM = "SUM"
FORMULA_ROLLUP_SUM = "ROLLUP_SUM"
SUPPORTED_FORMULA_TYPES = {FORMULA_SUM, FORMULA_ROLLUP_SUM}


def calcSum(values: list[Any]) -> float | int:
    totalValue = Decimal("0")
    for value in values:
        if value is None:
            raise ValueError("Rollup source value is null")
        totalValue += Decimal(str(value))
    if totalValue == totalValue.to_integral_value():
        return int(totalValue)
    return float(totalValue)


def calcBatch(
    batch: dict,
    sources: list[dict],
    scopes: list[dict],
    factMap: dict[tuple[int, str], dict],
) -> list[dict]:
    results = []
    sourceCompanyIds = [int(source["source_company_id"]) for source in sources]
    for scope in scopes:
        formulaType = str(scope.get("formulaType") or FORMULA_SUM).upper()
        if formulaType not in SUPPORTED_FORMULA_TYPES:
            raise ValueError("Unsupported rollup formula type")

        sourceAtomicMetricId = str(scope.get("source_atomic_metric_ids") or "").split(",")[0].strip()
        groupAtomicMetricId = scope["group_atomic_metric_id"]
        sourceValues = {}
        values = []
        unit = None
        for companyId in sourceCompanyIds:
            fact = factMap.get((companyId, sourceAtomicMetricId))
            if not fact:
                raise ValueError("Rollup source fact is missing")
            valueNumeric = fact.get("valueNumeric")
            if valueNumeric is None:
                raise ValueError("Rollup source value is null")
            values.append(valueNumeric)
            sourceValues[str(companyId)] = valueNumeric
            unit = unit or fact.get("unit") or "KRW"

        results.append(
            {
                "groupAtomicMetricId": groupAtomicMetricId,
                "groupAtomicName": scope.get("groupAtomicName") or groupAtomicMetricId,
                "sourceAtomicMetricId": sourceAtomicMetricId,
                "formulaType": formulaType,
                "valueNumeric": calcSum(values),
                "unit": unit or "KRW",
                "sourceCompanyValues": sourceValues,
                "sourceCompanyIds": sourceCompanyIds,
                "calculationTrace": {
                    "batchId": int(batch["id"]),
                    "metricScopeCode": batch.get("metric_scope_code"),
                    "formulaType": formulaType,
                    "sourceAtomicMetricId": sourceAtomicMetricId,
                    "targetAtomicMetricId": groupAtomicMetricId,
                    "sourceCompanyIds": sourceCompanyIds,
                },
            }
        )
    return results


__all__ = ["calcBatch", "calcSum"]
