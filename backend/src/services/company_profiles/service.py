from __future__ import annotations

from typing import Optional

from src.models.companyprofile import (
    G0ProfileItemDto,
    G0ProfileResponseDto,
    G0ProfileStatusResponseDto,
    G0ProfileUpsertRequestDto,
    G0ProfileUpsertResponseDto,
)
from src.models.onboarding import OnboardingMetricValuesRequestDto, OnboardingValueItemDto
from src.services.onboardings.service import (
    CYCLE_TYPE_PRE_DMA_G0,
    listMetrics,
    saveMetricValueGroups,
    validateMetricValues,
)
from src.utils.onboardingrepository import resolveReportingYear


def getG0Profile(companyId: int, reportingYear: Optional[int] = None) -> G0ProfileResponseDto:
    year = resolveReportingYear(companyId, reportingYear)
    metrics = listMetrics(
        companyId=companyId,
        reportingYear=year,
        cycleType=CYCLE_TYPE_PRE_DMA_G0,
    )
    items = flattenG0Items(metrics.items)
    status = statusFromItems(items)
    missing = [item for item in items if item.requiredYn and item.editableYn and not hasValue(item)]
    return G0ProfileResponseDto(
        companyId=companyId,
        reportingYear=year,
        g0ProfileStatus=status,
        items=items,
        missingRequiredItems=missing,
        message="OK",
    )


def getG0ProfileStatus(companyId: int, reportingYear: Optional[int] = None) -> G0ProfileStatusResponseDto:
    year = resolveReportingYear(companyId, reportingYear)
    profile = getG0Profile(companyId, year)
    required = [item for item in profile.items if item.requiredYn and item.editableYn]
    completed = [item for item in required if hasValue(item)]
    return G0ProfileStatusResponseDto(
        companyId=companyId,
        reportingYear=year,
        g0ProfileStatus=profile.g0ProfileStatus,
        requiredItemCount=len(required),
        completedRequiredItemCount=len(completed),
        missingRequiredItemCount=max(0, len(required) - len(completed)),
        message="OK",
    )


def saveG0Profile(
    companyId: int,
    request: G0ProfileUpsertRequestDto,
    userId: Optional[int] = None,
) -> G0ProfileUpsertResponseDto:
    grouped = {}
    for item in request.items:
        grouped.setdefault(item.metricId, []).append(item)

    preparedGroups = []
    for metricId, items in grouped.items():
        preparedGroups.append(
            validateMetricValues(
                metricId=metricId,
                request=OnboardingMetricValuesRequestDto(
                    companyId=companyId,
                    reportingYear=request.reportingYear,
                    cycleType=CYCLE_TYPE_PRE_DMA_G0,
                    values=[
                        OnboardingValueItemDto(
                            atomicMetricId=item.atomicMetricId,
                            valueText=item.valueText,
                            valueNumeric=item.valueNumeric,
                            unit=item.unit,
                        )
                        for item in items
                    ],
                ),
                userId=userId,
            )
        )

    savedCount = saveMetricValueGroups(preparedGroups)

    status = getG0ProfileStatus(companyId, request.reportingYear)
    return G0ProfileUpsertResponseDto(
        companyId=companyId,
        reportingYear=request.reportingYear,
        savedItemCount=savedCount,
        g0ProfileStatus=status.g0ProfileStatus,
        message="OK",
    )


def flattenG0Items(metricItems) -> list[G0ProfileItemDto]:
    items = []
    for metric in metricItems:
        for atomic in metric.atomicItems:
            items.append(
                G0ProfileItemDto(
                    metricId=atomic.metricId,
                    atomicMetricId=atomic.atomicMetricId,
                    metricName=atomic.metricName or metric.metricName,
                    atomicName=atomic.atomicName,
                    dataValueType=atomic.dataValueType,
                    atomicDataRole=atomic.atomicDataRole,
                    rollupRole=atomic.rollupRole,
                    inputMode=atomic.inputMode,
                    editableYn=atomic.editableYn,
                    valueText=atomic.valueText,
                    valueNumeric=atomic.valueNumeric,
                    unit=atomic.unit,
                    requiredYn=atomic.requiredYn,
                    updatedAt=atomic.updatedAt,
                )
            )
    return items


def statusFromItems(items: list[G0ProfileItemDto]):
    required = [item for item in items if item.requiredYn and item.editableYn]
    if not required:
        return "NOT_STARTED"
    completedCount = sum(1 for item in required if hasValue(item))
    if completedCount == 0:
        return "NOT_STARTED"
    if completedCount < len(required):
        return "IN_PROGRESS"
    return "COMPLETED"


def hasValue(item: G0ProfileItemDto) -> bool:
    return item.valueNumeric is not None or bool((item.valueText or "").strip())
