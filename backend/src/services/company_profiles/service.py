from __future__ import annotations

from typing import Optional

from src.models.companyprofile import (
    G0ProfileItemDto,
    G0ProfileResponseDto,
    G0ProfileStatusResponseDto,
    G0ProfileUpsertRequestDto,
    G0ProfileUpsertResponseDto,
)
from src.utils.companyprofilerepository import (
    getG0MasterItems,
    getG0ValueRows,
    resolveG0ReportingYear,
    upsertG0InputValue,
)
from src.utils.onboardingapprovalrepository import resolvePreDmaG0Cycle

STRUCTURED_LOOKUP_IDS = {
    "G0-05__QL0002",
    "G0-06__QL0001",
}

GENERIC_EDITABLE_INPUT_MODES = {
    "MANUAL_NUMBER",
    "MANUAL_TEXTAREA",
    "YEAR_RANGE",
}
PRE_DMA_G0_CYCLE_NOT_READY = "PRE_DMA_G0_CYCLE_NOT_READY: 보고서 발행 기준을 먼저 선택해 주세요."


def getG0Profile(companyId: int, reportingYear: Optional[int] = None) -> G0ProfileResponseDto:
    year = resolveG0ReportingYear(companyId, reportingYear)
    _requirePreDmaG0Cycle(companyId, year)
    items = _buildG0Items(companyId, year)
    status = _statusFromItems(items)
    missing = [item for item in items if item.requiredYn and item.editableYn and not _hasValue(item)]
    return G0ProfileResponseDto(
        companyId=companyId,
        reportingYear=year,
        g0ProfileStatus=status,
        items=items,
        missingRequiredItems=missing,
        message="OK",
    )


def getG0ProfileStatus(companyId: int, reportingYear: Optional[int] = None) -> G0ProfileStatusResponseDto:
    year = resolveG0ReportingYear(companyId, reportingYear)
    _requirePreDmaG0Cycle(companyId, year)
    items = _buildG0Items(companyId, year)
    required = [item for item in items if item.requiredYn and item.editableYn]
    completed = [item for item in required if _hasValue(item)]
    missingCount = max(0, len(required) - len(completed))
    return G0ProfileStatusResponseDto(
        companyId=companyId,
        reportingYear=year,
        g0ProfileStatus=_statusFromItems(items),
        requiredItemCount=len(required),
        completedRequiredItemCount=len(completed),
        missingRequiredItemCount=missingCount,
        message="OK",
    )


def saveG0Profile(
    companyId: int,
    request: G0ProfileUpsertRequestDto,
    userId: Optional[int] = None,
) -> G0ProfileUpsertResponseDto:
    _requirePreDmaG0Cycle(companyId, request.reportingYear)
    savedCount = 0
    masterByAtomic = {
        row.get("atomic_metric_id"): row
        for row in getG0MasterItems()
        if row.get("atomic_metric_id")
    }

    for item in request.items:
        _validateGenericEditableItem(
            metricId=item.metricId,
            atomicMetricId=item.atomicMetricId,
            masterByAtomic=masterByAtomic,
        )

    for item in request.items:
        if upsertG0InputValue(
            companyId=companyId,
            reportingYear=request.reportingYear,
            metricId=item.metricId,
            atomicMetricId=item.atomicMetricId,
            valueText=item.valueText,
            valueNumeric=item.valueNumeric,
            unit=item.unit,
            userId=userId,
        ):
            savedCount += 1

    status = getG0ProfileStatus(companyId, request.reportingYear)
    return G0ProfileUpsertResponseDto(
        companyId=companyId,
        reportingYear=request.reportingYear,
        savedItemCount=savedCount,
        g0ProfileStatus=status.g0ProfileStatus,
        message="OK",
    )


def _buildG0Items(companyId: int, reportingYear: int) -> list[G0ProfileItemDto]:
    masterRows = getG0MasterItems()
    valueRows = getG0ValueRows(companyId, reportingYear)
    items = []
    for row in masterRows:
        atomicMetricId = row.get("atomic_metric_id")
        inputMode = _resolveInputMode(row)
        value = _latestValueForInputMode(valueRows, atomicMetricId, inputMode)
        items.append(
            G0ProfileItemDto(
                metricId=row.get("metric_id"),
                atomicMetricId=atomicMetricId,
                metricName=row.get("metric_name_kr"),
                atomicName=row.get("atomic_name_kr"),
                dataValueType=row.get("data_value_type"),
                atomicDataRole=row.get("atomic_data_role"),
                rollupRole=row.get("rollup_role"),
                inputMode=inputMode,
                editableYn=_isGenericEditable(inputMode),
                valueText=value.get("value_text"),
                valueNumeric=_floatOrNone(value.get("value_numeric")),
                unit=value.get("unit") or row.get("unit"),
                requiredYn=bool(row.get("onboarding_input_yn")),
                updatedAt=str(value.get("updated_at")) if value.get("updated_at") is not None else None,
            )
        )
    return items


def _requirePreDmaG0Cycle(companyId: int, reportingYear: int) -> dict:
    cycle = resolvePreDmaG0Cycle(companyId, reportingYear)
    if not cycle or str(cycle.get("cycle_status") or "").strip().lower() != "active":
        raise ValueError(PRE_DMA_G0_CYCLE_NOT_READY)
    return cycle


def _resolveInputMode(row: dict) -> str:
    atomicMetricId = row.get("atomic_metric_id")
    atomicRole = row.get("atomic_data_role")
    rollupRole = row.get("rollup_role")
    onboardingYn = bool(row.get("onboarding_input_yn"))

    if (
        not onboardingYn
        or atomicRole != "INPUT"
        or rollupRole == "consolidated_result"
    ):
        return "ROLLUP_READONLY"

    if atomicMetricId in STRUCTURED_LOOKUP_IDS:
        return "STRUCTURED_LOOKUP"

    if atomicMetricId == "G0-05__QL0001":
        return "YEAR_RANGE"

    dataValueType = str(row.get("data_value_type") or "").strip().upper()
    if dataValueType in {"QUANT", "NUMBER", "NUMERIC"} or row.get("data_value_type") == "정량":
        return "MANUAL_NUMBER"

    return "MANUAL_TEXTAREA"


def _isGenericEditable(inputMode: str) -> bool:
    return inputMode in GENERIC_EDITABLE_INPUT_MODES


def _validateGenericEditableItem(
    metricId: str,
    atomicMetricId: str,
    masterByAtomic: dict[str, dict],
) -> None:
    row = masterByAtomic.get(atomicMetricId)

    if not row:
        raise ValueError(f"Unknown atomic metric: {atomicMetricId}")

    if row.get("metric_id") != metricId:
        raise ValueError(
            f"Metric mismatch: metricId={metricId}, atomicMetricId={atomicMetricId}"
        )

    inputMode = _resolveInputMode(row)
    if not _isGenericEditable(inputMode):
        raise ValueError(
            f"Manual input is not allowed for atomicMetricId={atomicMetricId}, "
            f"inputMode={inputMode}"
        )


def _latestValueForInputMode(rows: list[dict], atomicMetricId: str, inputMode: str) -> dict:
    if inputMode == "ROLLUP_READONLY":
        allowedSources = {"group_rollup_result"}
        priority = {"group_rollup_result": 0}
    elif inputMode == "STRUCTURED_LOOKUP":
        return {}
    else:
        allowedSources = {"onboarding_input", "kpi_fact"}
        priority = {"onboarding_input": 0, "kpi_fact": 1}

    candidates = [
        row
        for row in rows
        if row.get("atomic_metric_id") == atomicMetricId
        and row.get("source_table") in allowedSources
    ]
    if not candidates:
        return {}

    bestPriority = min(
        priority.get(row.get("source_table"), 99)
        for row in candidates
    )
    samePriorityRows = [
        row
        for row in candidates
        if priority.get(row.get("source_table"), 99) == bestPriority
    ]

    return max(
        samePriorityRows,
        key=lambda row: str(row.get("updated_at") or ""),
    )


def _statusFromItems(items: list[G0ProfileItemDto]):
    required = [item for item in items if item.requiredYn and item.editableYn]
    if not required:
        return "NOT_STARTED"
    completedCount = sum(1 for item in required if _hasValue(item))
    if completedCount == 0:
        return "NOT_STARTED"
    if completedCount < len(required):
        return "IN_PROGRESS"
    return "COMPLETED"


def _hasValue(item: G0ProfileItemDto) -> bool:
    return item.valueNumeric is not None or bool((item.valueText or "").strip())


def _floatOrNone(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
