"""
Calculation bounded context orchestration.

Responsibilities:
- Affected Entity Rule graph resolution
- Stale calculated Fact invalidation
- Engine execution
- All-or-none derived Fact persistence
- Input modification downstream invalidation

Import graph:
  calculations.service -> calculationrepository, calculationengine
  approval_service -> calculations.service
  onboardings.service -> calculations.service

This module must NOT import from onboardings.service or approval_service.
"""
from __future__ import annotations

from typing import Optional

from src.utils import calculationengine as calcEngine
from src.repositories import calculationrepository as calcRepo


def calculateAffectedEntityFactsTx(
    cur,
    *,
    companyId: int,
    reportingYear: int,
    changedAtomicMetricIds: list[str],
    actorUserId: Optional[int],
) -> dict:
    """
    Resolve affected Entity Rule graph, invalidate stale derived Facts,
    execute Engine, and persist all-or-none derived Facts.

    Returns a calculationSummary dict with observability fields.
    """
    changedAtomicMetricIds = [atomicId for atomicId in changedAtomicMetricIds if atomicId]
    if not changedAtomicMetricIds:
        return _emptySummary()

    activeRules = calcRepo.listActiveRulesTx(cur, calcRepo.EXECUTION_SCOPE_ENTITY)
    if not activeRules:
        return _emptySummary()

    activeRuleCodes = [
        rule["calculation_rule_code"]
        for rule in activeRules
        if rule.get("calculation_rule_code")
    ]
    sources = calcRepo.listRuleSourcesTx(cur, activeRuleCodes)
    affectedRules = calcEngine.resolveAffectedRuleGraph(activeRules, sources, changedAtomicMetricIds)
    if not affectedRules:
        return _emptySummary()

    affectedRuleCodes = {
        rule["calculation_rule_code"]
        for rule in affectedRules
        if rule.get("calculation_rule_code")
    }
    affectedSources = [
        source for source in sources
        if source.get("calculation_rule_code") in affectedRuleCodes
    ]
    affectedTargetAtomicIds = [
        rule.get("target_atomic_metric_id")
        for rule in affectedRules
        if rule.get("target_atomic_metric_id")
    ]
    atomicMetricIds = sorted(
        {
            source.get("source_atomic_metric_id")
            for source in affectedSources
            if source.get("source_atomic_metric_id")
        }
        | set(affectedTargetAtomicIds)
    )

    invalidatedFactCount = calcRepo.invalidateCalculatedEntityFactsTx(
        cur,
        companyId=companyId,
        reportingYear=reportingYear,
        atomicMetricIds=affectedTargetAtomicIds,
    )

    currentFacts = calcRepo.listApprovedEntityFactsTx(cur, [companyId], reportingYear, atomicMetricIds)
    priorFacts = calcRepo.listPriorYearFactsTx(cur, [companyId], reportingYear, atomicMetricIds)
    results = calcEngine.calculateRules(affectedRules, affectedSources, currentFacts, priorFacts)

    warnings = _collectWarnings(results)

    if not calcEngine.allResultsCalculated(results):
        return {
            "affectedRuleCount": len(affectedRules),
            "invalidatedFactCount": invalidatedFactCount,
            "calculatedFactCount": 0,
            "calculationReadyYn": False,
            "calculationWarnings": warnings,
            "results": results,
        }

    calculatedFactCount = calcRepo.upsertCalculatedEntityFactsTx(
        cur,
        companyId=companyId,
        reportingYear=reportingYear,
        results=results,
        actorUserId=actorUserId,
    )

    return {
        "affectedRuleCount": len(affectedRules),
        "invalidatedFactCount": invalidatedFactCount,
        "calculatedFactCount": calculatedFactCount,
        "calculationReadyYn": True,
        "calculationWarnings": warnings,
        "results": results,
    }


def invalidateAffectedEntityFactsTx(
    cur,
    *,
    companyId: int,
    reportingYear: int,
    changedAtomicMetricIds: list[str],
) -> dict:
    """
    Input modification downstream invalidation.

    Policy:
      input value change
      -> resolve affected Entity Rule graph
      -> invalidate existing calculation_engine derived Facts
      -> return summary (no recalculation; recalculation happens at approval time)
    """
    changedAtomicMetricIds = [atomicId for atomicId in changedAtomicMetricIds if atomicId]
    if not changedAtomicMetricIds:
        return {"affectedRuleCount": 0, "invalidatedFactCount": 0}

    affectedRules, affectedSources = resolveAffectedEntityRulesTx(cur, changedAtomicMetricIds)
    if not affectedRules:
        return {"affectedRuleCount": 0, "invalidatedFactCount": 0}

    affectedTargetAtomicIds = [
        rule.get("target_atomic_metric_id")
        for rule in affectedRules
        if rule.get("target_atomic_metric_id")
    ]

    invalidatedFactCount = calcRepo.invalidateCalculatedEntityFactsTx(
        cur,
        companyId=companyId,
        reportingYear=reportingYear,
        atomicMetricIds=affectedTargetAtomicIds,
    )

    return {
        "affectedRuleCount": len(affectedRules),
        "invalidatedFactCount": invalidatedFactCount,
    }


def resolveAffectedEntityRulesTx(
    cur,
    changedAtomicMetricIds: list[str],
) -> tuple[list[dict], list[dict]]:
    """
    Resolve the affected Entity Rule graph for the given changed atomic metric IDs.

    Returns (affectedRules, affectedSources).
    """
    changedAtomicMetricIds = [atomicId for atomicId in changedAtomicMetricIds if atomicId]
    if not changedAtomicMetricIds:
        return [], []

    activeRules = calcRepo.listActiveRulesTx(cur, calcRepo.EXECUTION_SCOPE_ENTITY)
    if not activeRules:
        return [], []

    activeRuleCodes = [
        rule["calculation_rule_code"]
        for rule in activeRules
        if rule.get("calculation_rule_code")
    ]
    sources = calcRepo.listRuleSourcesTx(cur, activeRuleCodes)
    affectedRules = calcEngine.resolveAffectedRuleGraph(activeRules, sources, changedAtomicMetricIds)
    if not affectedRules:
        return [], []

    affectedRuleCodes = {
        rule["calculation_rule_code"]
        for rule in affectedRules
        if rule.get("calculation_rule_code")
    }
    affectedSources = [
        source for source in sources
        if source.get("calculation_rule_code") in affectedRuleCodes
    ]
    return affectedRules, affectedSources


def _emptySummary() -> dict:
    return {
        "affectedRuleCount": 0,
        "invalidatedFactCount": 0,
        "calculatedFactCount": 0,
        "calculationReadyYn": True,
        "calculationWarnings": [],
        "results": [],
    }


def _collectWarnings(results: list[dict]) -> list[str]:
    warnings = []
    for result in results or []:
        warning = result.get("warning")
        if warning and warning not in warnings:
            warnings.append(str(warning))
    return warnings
