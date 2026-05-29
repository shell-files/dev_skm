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


def getG0Profile(companyId: int, reportingYear: Optional[int] = None) -> G0ProfileResponseDto:
    year = resolveG0ReportingYear(companyId, reportingYear)
    items = _buildG0Items(companyId, year)
    status = _statusFromItems(items)
    missing = [item for item in items if item.requiredYn and not _hasValue(item)]
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
    items = _buildG0Items(companyId, year)
    required = [item for item in items if item.requiredYn]
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
    savedCount = 0
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
    valueByAtomic = _latestValueByAtomic(getG0ValueRows(companyId, reportingYear))
    items = []
    for row in masterRows:
        atomicMetricId = row.get("atomic_metric_id")
        value = valueByAtomic.get(atomicMetricId, {})
        items.append(
            G0ProfileItemDto(
                metricId=row.get("metric_id"),
                atomicMetricId=atomicMetricId,
                metricName=row.get("metric_name_kr"),
                atomicName=row.get("atomic_name_kr"),
                valueText=value.get("value_text"),
                valueNumeric=_floatOrNone(value.get("value_numeric")),
                unit=value.get("unit") or row.get("unit"),
                requiredYn=bool(row.get("onboarding_input_yn")),
                updatedAt=str(value.get("updated_at")) if value.get("updated_at") is not None else None,
            )
        )
    return items


def _latestValueByAtomic(rows: list[dict]) -> dict[str, dict]:
    priority = {
        "onboarding_input": 0,
        "kpi_fact": 1,
        "group_rollup_result": 2,
    }
    result = {}
    for row in sorted(rows, key=lambda item: priority.get(item.get("source_table"), 99)):
        atomicMetricId = row.get("atomic_metric_id")
        if atomicMetricId and atomicMetricId not in result:
            result[atomicMetricId] = row
    return result


def _statusFromItems(items: list[G0ProfileItemDto]):
    required = [item for item in items if item.requiredYn]
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
