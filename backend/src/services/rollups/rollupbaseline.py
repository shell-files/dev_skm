"""
rollupbaseline.py
레이어: Service (rollups)
역할: 롤업 전년도 기준값 관리 서비스 — 요구사항 조회 및 기준값 저장.
"""
from __future__ import annotations

from src.models.rollup import (
    RollupBaselineRequirementItemDto,
    RollupBaselineRequirementListDto,
    RollupBaselineRequirementResponseDto,
    RollupBaselineSaveResponseDto,
    RollupBaselineSaveResultDto,
    RollupBaselineSaveResultItemDto,
    RollupBaselineValuesRequestDto,
)
from src.utils.calculationengine import normalizeSource
from src.utils.companyscope import checkScope
from src.services.rollups.rollupexceptions import RollupError
from src.services.rollups.rollupbuilder import loadRepository, loadCalculator, getActorUserId


def resolveBaselineRequirementTuples(rollupCalculator, rules: list[dict], ruleSources: list[dict]) -> list[tuple]:
    """YoY 공식 규칙 중 CONSOLIDATED 소스를 갖는 (ruleCode, rule, sourceAtomicId) 튜플 목록을 반환한다."""
    rulesByCode = {}
    for rule in rules or []:
        code = str(rule.get("calculation_rule_code") or "").strip()
        if code:
            rulesByCode[code] = rule

    sourcesByRule: dict[str, list[dict]] = {}
    for src in ruleSources or []:
        normalized = normalizeSource(src)
        code = normalized.get("ruleCode")
        if code:
            sourcesByRule.setdefault(code, []).append(normalized)

    requirementTuples = []
    seen = set()
    for code, rule in rulesByCode.items():
        if not rollupCalculator.isYoyFormula(rule):
            continue
        for normalized in sourcesByRule.get(code, []):
            if normalized.get("sourceScope") != "CONSOLIDATED":
                continue
            sourceAtomicId = normalized.get("sourceAtomicMetricId")
            if not sourceAtomicId:
                continue
            key = (code, sourceAtomicId)
            if key in seen:
                continue
            seen.add(key)
            requirementTuples.append((code, rule, sourceAtomicId))
    return requirementTuples


def getBaselineRequirements(batchId: int, userModel) -> RollupBaselineRequirementResponseDto:
    """배치에 필요한 전년도 연결 기준값 요구사항 목록과 현재 입력 상태를 반환한다."""
    rollupRepository = loadRepository()
    rollupCalculator = loadCalculator()

    batch = rollupRepository.getBatch(batchId)
    if not batch:
        raise RollupError(404, "ROLLUP_BATCH_NOT_FOUND", "Rollup batch was not found.")
    parentCompanyId = int(batch["parent_company_id"])
    reportingYear = int(batch["reporting_year"])
    checkScope(parentCompanyId, userModel)
    requiredYear = reportingYear - 1

    items = []
    conn = rollupRepository.getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            try:
                rules, ruleSources = rollupRepository.resolveConsolidatedRulesFromBatchScopeTx(cur, batchId)
            except ValueError:
                rules, ruleSources = [], []

            requirementTuples = resolveBaselineRequirementTuples(rollupCalculator, rules, ruleSources)
            baselineAtomicIds = sorted({sourceAtomicId for _, _, sourceAtomicId in requirementTuples})

            metaByAtomic = {}
            details = {}
            if baselineAtomicIds:
                metaList = rollupRepository.listAtomicMetadata(baselineAtomicIds)
                metaByAtomic = {str(m.get("atomicMetricId")): m for m in metaList}
                details = rollupRepository.listConsolidatedBaselineDetailsTx(
                    cur, parentCompanyId, requiredYear, baselineAtomicIds
                )

            for code, rule, sourceAtomicId in requirementTuples:
                meta = metaByAtomic.get(sourceAtomicId, {})
                detail = details.get(sourceAtomicId)
                unit = (detail or {}).get("unit") or rule.get("output_unit") or rule.get("unit")
                items.append(RollupBaselineRequirementItemDto(
                    ruleCode=code,
                    metricId=rule.get("metric_id"),
                    targetAtomicMetricId=rule.get("target_atomic_metric_id"),
                    sourceMetricId=meta.get("metricId"),
                    sourceAtomicMetricId=sourceAtomicId,
                    sourceAtomicName=meta.get("atomicName"),
                    requiredReportingYear=requiredYear,
                    unit=unit,
                    status="READY" if detail else "MISSING",
                    valueNumeric=(detail or {}).get("valueNumeric"),
                    valueText=(detail or {}).get("valueText"),
                    valueSourceType=(detail or {}).get("valueSourceType"),
                ))
    finally:
        conn.close()

    return RollupBaselineRequirementResponseDto(
        data=RollupBaselineRequirementListDto(
            batchId=batchId,
            parentCompanyId=parentCompanyId,
            reportingYear=reportingYear,
            items=items,
        )
    )


def saveBaselineValues(batchId: int, request: RollupBaselineValuesRequestDto, userModel) -> RollupBaselineSaveResponseDto:
    """요청된 전년도 기준값을 검증해 CONSOLIDATED Fact로 UPSERT하고 저장 결과를 반환한다."""
    rollupRepository = loadRepository()
    rollupCalculator = loadCalculator()

    batch = rollupRepository.getBatch(batchId)
    if not batch:
        raise RollupError(404, "ROLLUP_BATCH_NOT_FOUND", "Rollup batch was not found.")
    parentCompanyId = int(batch["parent_company_id"])
    reportingYear = int(batch["reporting_year"])
    checkScope(parentCompanyId, userModel)
    actorUserId = getActorUserId(userModel)
    requiredYear = reportingYear - 1

    values = request.values or []
    if not values:
        raise RollupError(422, "ROLLUP_BASELINE_VALUE_REQUIRED", "At least one baseline value is required.")

    saveItems = []
    savedCount = 0
    conn = rollupRepository.getConn()
    try:
        with conn.cursor(dictionary=True) as cur:
            try:
                rules, ruleSources = rollupRepository.resolveConsolidatedRulesFromBatchScopeTx(cur, batchId)
            except ValueError:
                rules, ruleSources = [], []

            requirementTuples = resolveBaselineRequirementTuples(rollupCalculator, rules, ruleSources)
            allowedAtomicIds = {sourceAtomicId for _, _, sourceAtomicId in requirementTuples}

            for value in values:
                atomicMetricId = str(value.atomicMetricId or "").strip()
                inputYear = int(value.reportingYear)

                if inputYear != requiredYear:
                    raise RollupError(
                        422,
                        "ROLLUP_BASELINE_YEAR_INVALID",
                        f"Baseline reportingYear must be {requiredYear}.",
                        {"atomicMetricId": atomicMetricId, "reportingYear": inputYear, "requiredReportingYear": requiredYear},
                    )
                if atomicMetricId not in allowedAtomicIds:
                    raise RollupError(
                        422,
                        "ROLLUP_BASELINE_ATOMIC_INVALID",
                        "Atomic is not a prior-year consolidated baseline source for this batch.",
                        {"atomicMetricId": atomicMetricId},
                    )

                result = rollupRepository.upsertConsolidatedBaselineFactTx(
                    cur,
                    parentCompanyId=parentCompanyId,
                    reportingYear=inputYear,
                    metricId=value.metricId,
                    atomicMetricId=atomicMetricId,
                    valueNumeric=value.valueNumeric,
                    valueText=value.valueText,
                    unit=value.unit,
                    actorUserId=actorUserId,
                )
                saved = result in ("inserted", "updated")
                if saved:
                    savedCount += 1
                saveItems.append(RollupBaselineSaveResultItemDto(
                    atomicMetricId=atomicMetricId,
                    reportingYear=inputYear,
                    result=result,
                    saved=saved,
                ))

            conn.commit()
    except RollupError:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise RollupError(500, "ROLLUP_BASELINE_SAVE_FAILED", f"Failed to save prior-year baseline values: {e}")
    finally:
        conn.close()

    return RollupBaselineSaveResponseDto(
        data=RollupBaselineSaveResultDto(
            batchId=batchId,
            parentCompanyId=parentCompanyId,
            reportingYear=reportingYear,
            savedCount=savedCount,
            items=saveItems,
        )
    )
