from __future__ import annotations

from typing import Optional

from src.models.onboarding import (
    OnboardingAssignmentDto,
    OnboardingAtomicItemDto,
    OnboardingMetricItemDto,
    OnboardingMetricsResponseDto,
    OnboardingMetricValuesRequestDto,
    OnboardingMetricValuesResponseDto,
)
from src.utils import onboardingrepository as repo


CYCLE_TYPE_PRE_DMA_G0 = "PRE_DMA_G0"
PRE_DMA_G0_CYCLE_NOT_READY = "PRE_DMA_G0_CYCLE_NOT_READY: 보고서 발행 기준을 먼저 선택해 주세요."
STRUCTURED_LOOKUP_IDS = {"G0-05__QL0002", "G0-06__QL0001"}
EDITABLE_INPUT_MODES = {"MANUAL_NUMBER", "MANUAL_TEXTAREA", "YEAR_RANGE"}


def listMetrics(
    *,
    companyId: int,
    reportingYear: Optional[int],
    cycleType: str,
    metricId: Optional[str] = None,
) -> OnboardingMetricsResponseDto:
    year = repo.resolveReportingYear(companyId, reportingYear)
    cycle = requireCycle(companyId, year, cycleType)
    scopes = repo.listMetricScopes(int(cycle["id"]), companyId, metricId)
    metricIds = [row["metric_id"] for row in scopes]
    masterRows = repo.listAtomicMaster(metricIds)
    valueRows = repo.listValueRows(companyId, year, metricIds)
    assignmentRows = repo.listAssignmentRows(int(cycle["id"]), companyId)
    assignmentByMetric = {row["metric_id"]: buildAssignment(row) for row in assignmentRows}
    atomicRowsByMetric = groupBy(masterRows, "metric_id")

    items = []
    for scope in scopes:
        scopedMetricId = scope["metric_id"]
        atomicItems = [
            buildAtomicItem(row, latestValueForInputMode(valueRows, row.get("atomic_metric_id"), resolveInputMode(row)))
            for row in atomicRowsByMetric.get(scopedMetricId, [])
        ]
        items.append(
            OnboardingMetricItemDto(
                metricId=scopedMetricId,
                metricName=scope.get("metric_name_kr"),
                scopeSourceType=scope.get("scope_source_type") or "PRE_DMA_G0",
                requiredYn=bool(scope.get("required_yn")),
                inputRequiredYn=bool(scope.get("input_required_yn")),
                approvalRequiredYn=bool(scope.get("approval_required_yn")),
                approvalPolicyCode=scope.get("approval_policy_code") or "INPUT_APPROVAL_ONLY",
                rollupReadonlyYn=bool(scope.get("rollup_readonly_yn")),
                displayOrder=int(scope.get("display_order") or 0),
                assignment=assignmentByMetric.get(scopedMetricId),
                atomicItems=atomicItems,
            )
        )

    return OnboardingMetricsResponseDto(
        companyId=companyId,
        reportingYear=year,
        cycleId=int(cycle["id"]),
        cycleType=cycle.get("cycle_type") or CYCLE_TYPE_PRE_DMA_G0,
        metricScopeCode=cycle.get("metric_scope_code"),
        items=items,
    )


def saveMetricValues(
    *,
    metricId: str,
    request: OnboardingMetricValuesRequestDto,
    userId: Optional[int] = None,
) -> OnboardingMetricValuesResponseDto:
    cycle = requireCycle(request.companyId, request.reportingYear, request.cycleType)
    metrics = listMetrics(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=metricId,
    )
    if not metrics.items:
        raise ValueError(f"Unsupported metricId for cycle scope: {metricId}")
    metric = metrics.items[0]
    atomicById = {item.atomicMetricId: item for item in metric.atomicItems}
    cleanedValues = []
    for item in request.values or []:
        atomic = atomicById.get(item.atomicMetricId)
        if not atomic:
            raise ValueError(f"atomicMetricId does not belong to metricId={metricId}: {item.atomicMetricId}")
        if not atomic.editableYn:
            raise ValueError(f"Manual input is not allowed for atomicMetricId={item.atomicMetricId}, inputMode={atomic.inputMode}")
        cleanedValues.append(
            {
                "atomicMetricId": item.atomicMetricId,
                "valueNumeric": item.valueNumeric,
                "valueText": item.valueText,
                "unit": item.unit or atomic.unit,
            }
        )
    if not cleanedValues:
        raise ValueError("values is required")

    assignmentId = repo.resolveAssignmentId(int(cycle["id"]), request.companyId, metricId)
    savedCount = repo.upsertMetricInputValues(
        cycleId=int(cycle["id"]),
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        metricId=metricId,
        assignmentId=assignmentId,
        values=cleanedValues,
        userId=userId,
    )
    return OnboardingMetricValuesResponseDto(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleId=int(cycle["id"]),
        cycleType=request.cycleType,
        metricId=metricId,
        savedItemCount=savedCount,
    )


def requireCycle(companyId: int, reportingYear: int, cycleType: str) -> dict:
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType != CYCLE_TYPE_PRE_DMA_G0:
        raise ValueError("Only PRE_DMA_G0 cycleType is supported")
    cycle = repo.getCycle(companyId, reportingYear, normalizedCycleType)
    if not cycle or str(cycle.get("cycle_status") or "").strip().lower() != "active":
        raise ValueError(PRE_DMA_G0_CYCLE_NOT_READY)
    return cycle


def buildAtomicItem(row: dict, value: dict) -> OnboardingAtomicItemDto:
    inputMode = resolveInputMode(row)
    return OnboardingAtomicItemDto(
        metricId=row.get("metric_id"),
        atomicMetricId=row.get("atomic_metric_id"),
        metricName=row.get("metric_name_kr"),
        atomicName=row.get("atomic_name_kr"),
        dataValueType=row.get("data_value_type"),
        atomicDataRole=row.get("atomic_data_role"),
        rollupRole=row.get("rollup_role"),
        inputMode=inputMode,
        editableYn=isEditable(inputMode),
        requiredYn=bool(row.get("onboarding_input_yn")) and isEditable(inputMode),
        valueText=value.get("value_text"),
        valueNumeric=floatOrNone(value.get("value_numeric")),
        unit=value.get("unit") or row.get("unit"),
        inputStatus=value.get("input_status"),
        updatedAt=str(value.get("updated_at")) if value.get("updated_at") is not None else None,
    )


def resolveInputMode(row: dict) -> str:
    atomicMetricId = row.get("atomic_metric_id")
    atomicRole = row.get("atomic_data_role")
    rollupRole = row.get("rollup_role")

    if (
        atomicRole == "DERIVED"
        or rollupRole == "consolidated_result"
        or str(atomicMetricId or "").startswith("G0-02__G")
        or atomicMetricId == "G0-03__G0001"
    ):
        return "ROLLUP_READONLY"

    if atomicMetricId in STRUCTURED_LOOKUP_IDS:
        return "STRUCTURED_LOOKUP"

    if atomicMetricId == "G0-05__QL0001":
        return "YEAR_RANGE"

    dataValueType = str(row.get("data_value_type") or "").strip().upper()
    if (
        str(atomicMetricId or "").startswith("G0-02__Q")
        or str(atomicMetricId or "").startswith("G0-03__Q")
        or dataValueType in {"QUANT", "NUMBER", "NUMERIC"}
        or row.get("data_value_type") == "정량"
    ):
        return "MANUAL_NUMBER"

    return "MANUAL_TEXTAREA"


def isEditable(inputMode: str) -> bool:
    return inputMode in EDITABLE_INPUT_MODES


def latestValueForInputMode(rows: list[dict], atomicMetricId: str, inputMode: str) -> dict:
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

    bestPriority = min(priority.get(row.get("source_table"), 99) for row in candidates)
    samePriorityRows = [
        row
        for row in candidates
        if priority.get(row.get("source_table"), 99) == bestPriority
    ]
    return max(samePriorityRows, key=lambda row: str(row.get("updated_at") or ""))


def buildAssignment(row: dict) -> OnboardingAssignmentDto:
    return OnboardingAssignmentDto(
        assignmentId=int(row["assignment_id"]) if row.get("assignment_id") is not None else None,
        assignmentStatus=row.get("assignment_status"),
        assigneeUserId=int(row["assignee_user_id"]) if row.get("assignee_user_id") is not None else None,
        assigneeEmailMasked=maskEmail(row.get("assignee_email")),
        dueDate=str(row.get("due_date")) if row.get("due_date") is not None else None,
    )


def maskEmail(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if not name:
        return f"***@{domain}"
    return f"{name[0]}***@{domain}"


def groupBy(rows: list[dict], key: str) -> dict[str, list[dict]]:
    grouped = {}
    for row in rows:
        grouped.setdefault(row.get(key), []).append(row)
    return grouped


def floatOrNone(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

