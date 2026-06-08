from __future__ import annotations

from typing import Optional

from src.models.onboarding import (
    OnboardingApprovalActionResponseDto,
    OnboardingApprovalAtomicDetailItemDto,
    OnboardingApprovalDetailDataDto,
    OnboardingApprovalDetailResponseDto,
    OnboardingApprovalItemDto,
    OnboardingApprovalListDataDto,
    OnboardingApprovalListResponseDto,
    OnboardingApprovalRequestDto,
    OnboardingApprovalStatusDataDto,
    OnboardingApprovalStatusResponseDto,
    OnboardingAssignmentDto,
    OnboardingAssignmentBulkAssignRequestDto,
    OnboardingAssignmentBulkAssignResponseDto,
    OnboardingAssignmentBulkUnassignRequestDto,
    OnboardingAssignmentBulkUnassignResponseDto,
    OnboardingAssignmentDetailResponseDto,
    OnboardingAssignmentItemDto,
    OnboardingAssignmentListResponseDto,
    OnboardingAssignmentPatchRequestDto,
    OnboardingAtomicItemDto,
    OnboardingMetricItemDto,
    OnboardingMetricsResponseDto,
    OnboardingMetricValuesRequestDto,
    OnboardingMetricValuesResponseDto,
)
from src.utils import onboardingassignmentrepository as assignmentRepo
from src.utils import onboardingrepository as repo
from src.utils.companyscope import checkScope
from src.services.onboardings import approval_service as approvalService
from src.services.calculations.service import invalidateAffectedEntityFactsTx


CYCLE_TYPE_PRE_DMA_G0 = "PRE_DMA_G0"
CYCLE_TYPE_POST_DMA_DISCLOSURE = "POST_DMA_DISCLOSURE"
PRE_DMA_G0_CYCLE_NOT_READY = "PRE_DMA_G0_CYCLE_NOT_READY: 보고연도 프로젝트를 먼저 시작해 주세요."
PRE_DMA_G0_SCOPE_NOT_READY = "PRE_DMA_G0_SCOPE_NOT_READY: 온보딩 지표 범위가 초기화되지 않았습니다. 기존 프로젝트를 재개해 주세요."
POST_DMA_DISCLOSURE_CYCLE_NOT_READY = "POST_DMA_DISCLOSURE_CYCLE_NOT_READY: POST_DMA_DISCLOSURE cycle을 먼저 초기화해 주세요."
POST_DMA_DISCLOSURE_SCOPE_NOT_READY = "POST_DMA_DISCLOSURE_SCOPE_NOT_READY: POST_DMA_DISCLOSURE 지표 범위가 초기화되지 않았습니다."
STRUCTURED_LOOKUP_IDS = {"G0-05__QL0002", "G0-06__QL0001"}
EDITABLE_INPUT_MODES = {"MANUAL_NUMBER", "MANUAL_TEXTAREA", "YEAR_RANGE", "STRUCTURED_LOOKUP"}
SUPPORTED_CYCLE_TYPE = "PRE_DMA_G0"
SUPPORTED_INPUT_CYCLE_TYPES = {CYCLE_TYPE_PRE_DMA_G0, CYCLE_TYPE_POST_DMA_DISCLOSURE}
SUPPORTED_ASSIGNMENT_CYCLE_TYPES = {CYCLE_TYPE_PRE_DMA_G0, CYCLE_TYPE_POST_DMA_DISCLOSURE}
ASSIGNMENT_MANAGER_ROLES = {"ADMIN", "ESG"}
ASSIGNMENT_MANAGER_ROLE_NAMES = {"관리자", "ESG담당자", "ESG 담당자"}
EMPLOYEE_ROLES = {"EMPLOYEE", "ASSIGNEE"}
EMPLOYEE_ROLE_NAMES = {"부서담당자", "부서 담당자"}
CONSULTANT_ROLES = {"CONSULTANT"}
CONSULTANT_ROLE_NAMES = {"컨설턴트"}
REVIEWER_ROLES = {"CONSULTANT", "ADMIN", "ESG"}
REVIEWER_ROLE_NAMES = {"컨설턴트", "관리자", "ESG담당자", "ESG 담당자"}
PRE_DMA_G0_CYCLE_NOT_READY_MESSAGE = "PRE_DMA_G0_CYCLE_NOT_READY: 기존 PRE_DMA_G0 workflow를 먼저 시작해 주세요."
APPROVER_ROLES = {"ADMIN", "ESG"}
APPROVER_ROLE_NAMES = {"관리자", "ESG담당자", "ESG 담당자"}


class PreDmaG0CycleNotReadyError(ValueError):
    pass


def listMetrics(
    *,
    companyId: int,
    reportingYear: Optional[int],
    cycleType: str,
    metricId: Optional[str] = None,
    userModel=None,
) -> OnboardingMetricsResponseDto:
    year = repo.resolveReportingYear(companyId, reportingYear)
    cycle = requireCycle(companyId, year, cycleType)
    allScopes = repo.listMetricScopes(int(cycle["id"]), companyId)
    if not allScopes:
        raise ValueError(scopeNotReadyMessage(cycle.get("cycle_type") or cycleType))
    assignmentRows = assignmentRepo.listAssignmentRows(int(cycle["id"]), companyId)
    scopes = listVisibleMetricScopesForUser(allScopes, assignmentRows, userModel)
    if metricId:
        scopes = [row for row in allScopes if row.get("metric_id") == metricId]
        scopes = listVisibleMetricScopesForUser(scopes, assignmentRows, userModel)
        if not scopes:
            raise ValueError(f"Unsupported metricId for cycle scope: {metricId}")
    metricIds = [row["metric_id"] for row in scopes]
    masterRows = repo.listAtomicMaster(metricIds)
    valueRows = repo.listValueRows(companyId, year, metricIds)
    assignmentByMetric = {row["metric_id"]: buildAssignment(row) for row in assignmentRows}
    atomicRowsByMetric = groupBy(masterRows, "metric_id")

    items = []
    for scope in scopes:
        scopedMetricId = scope["metric_id"]
        scopeMetadata = resolveScopeMetadata(scope, cycle)
        atomicItems = [
            buildAtomicItem(row, latestValueForInputMode(valueRows, row.get("atomic_metric_id"), resolveInputMode(row)))
            for row in atomicRowsByMetric.get(scopedMetricId, [])
        ]
        items.append(
            OnboardingMetricItemDto(
                metricId=scopedMetricId,
                metricName=scope.get("metric_name_kr"),
                issueDomain=scopeMetadata["issueDomain"],
                subIssueId=scopeMetadata["subIssueId"],
                subIssueCode=scopeMetadata["subIssueCode"],
                subIssueName=scopeMetadata["subIssueName"],
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
    userModel=None,
) -> OnboardingMetricValuesResponseDto:
    prepared = validateMetricValues(metricId=metricId, request=request, userId=userId, userModel=userModel)
    cycle = prepared["cycle"]
    group = prepared["group"]
    savedCount = saveMetricValueGroupsWithInvalidation([group])
    return OnboardingMetricValuesResponseDto(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleId=int(cycle["id"]),
        cycleType=request.cycleType,
        metricId=metricId,
        savedItemCount=savedCount,
    )


def saveMetricValueGroupsWithInvalidation(groups: list[dict]) -> int:
    """Save metric values and invalidate downstream derived Facts for changed atomics."""
    if not groups:
        return 0
    from src.utils.db import getConn
    from src.utils import onboardinginputrepository as inputRepo
    conn = getConn()
    if not conn:
        raise RuntimeError("DB connection failed")
    try:
        savedCount = 0
        with conn.cursor(dictionary=True) as cur:
            for group in groups:
                companyId = group["companyId"]
                reportingYear = group["reportingYear"]
                metricId = group["metricId"]
                values = group["values"]

                # Collect old values for change detection
                oldByAtomic = {}
                for value in values:
                    atomicId = value["atomicMetricId"]
                    cur.execute(
                        """
                        SELECT value_numeric, value_text
                        FROM ESG_ONBOARDING_INPUT_VALUE
                        WHERE company_id = ?
                          AND reporting_year = ?
                          AND metric_id = ?
                          AND atomic_metric_id = ?
                          AND delete_yn = 0
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (companyId, reportingYear, metricId, atomicId),
                    )
                    oldByAtomic[atomicId] = cur.fetchone()

                # Save
                savedCount += inputRepo.upsertMetricInputValuesTx(cur, **group)

                # Detect changed atomics
                changedAtomicIds = []
                for value in values:
                    atomicId = value["atomicMetricId"]
                    old = oldByAtomic.get(atomicId)
                    if _atomicValueChanged(old, value):
                        changedAtomicIds.append(atomicId)

                # Downstream invalidation for changed atomics
                if changedAtomicIds:
                    invalidateAffectedEntityFactsTx(
                        cur,
                        companyId=companyId,
                        reportingYear=reportingYear,
                        changedAtomicMetricIds=changedAtomicIds,
                    )
        conn.commit()
        return savedCount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _atomicValueChanged(oldRow: dict, newValue: dict) -> bool:
    """Return True if the value actually changed compared to the existing DB row."""
    if oldRow is None:
        # New insert — always counts as a change
        return True
    oldNumeric = oldRow.get("value_numeric")
    newNumeric = newValue.get("valueNumeric")
    oldText = str(oldRow.get("value_text") or "").strip()
    newText = str(newValue.get("valueText") or "").strip()
    # Compare numeric
    if oldNumeric is not None or newNumeric is not None:
        try:
            if float(oldNumeric or 0) != float(newNumeric or 0):
                return True
        except (TypeError, ValueError):
            return True
    # Compare text
    if oldText != newText:
        return True
    return False


def validateMetricValues(
    *,
    metricId: str,
    request: OnboardingMetricValuesRequestDto,
    userId: Optional[int] = None,
    userModel=None,
) -> dict:
    cycle = requireCycle(request.companyId, request.reportingYear, request.cycleType)
    checkMetricInputPermission(
        cycle=cycle,
        companyId=request.companyId,
        metricId=metricId,
        userModel=userModel,
    )
    metrics = listMetrics(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=metricId,
        userModel=userModel,
    )
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
    return {
        "cycle": cycle,
        "metric": metric,
        "group": {
            "cycleId": int(cycle["id"]),
            "companyId": request.companyId,
            "reportingYear": request.reportingYear,
            "metricId": metricId,
            "assignmentId": assignmentId,
            "values": cleanedValues,
            "userId": userId,
        },
    }


def saveMetricValueGroups(groups: list[dict]) -> int:
    return repo.upsertMetricValueGroups([group["group"] if "group" in group else group for group in groups])


def requireCycle(companyId: int, reportingYear: int, cycleType: str) -> dict:
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType not in SUPPORTED_INPUT_CYCLE_TYPES:
        raise ValueError("Only PRE_DMA_G0 or POST_DMA_DISCLOSURE cycleType is supported")
    cycle = repo.getCycle(companyId, reportingYear, normalizedCycleType)
    if not cycle or str(cycle.get("cycle_status") or "").strip().lower() != "active":
        raise ValueError(cycleNotReadyMessage(normalizedCycleType))
    return cycle


def cycleNotReadyMessage(cycleType: str) -> str:
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType == CYCLE_TYPE_POST_DMA_DISCLOSURE:
        return POST_DMA_DISCLOSURE_CYCLE_NOT_READY
    return PRE_DMA_G0_CYCLE_NOT_READY


def scopeNotReadyMessage(cycleType: str) -> str:
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType == CYCLE_TYPE_POST_DMA_DISCLOSURE:
        return POST_DMA_DISCLOSURE_SCOPE_NOT_READY
    return PRE_DMA_G0_SCOPE_NOT_READY


def resolveScopeMetadata(scope: dict, cycle: dict) -> dict:
    cycleType = str(cycle.get("cycle_type") or "").strip().upper()
    if cycleType != CYCLE_TYPE_POST_DMA_DISCLOSURE:
        return {
            "issueDomain": "general",
            "subIssueId": None,
            "subIssueCode": None,
            "subIssueName": None,
        }

    issueDomain = normalizeIssueDomain(scope.get("sub_issue_domain"))
    subIssueId = scope.get("sub_issue_id")
    subIssueCode = scope.get("sub_issue_code")
    subIssueName = scope.get("sub_issue_name")
    if not issueDomain or subIssueId is None or not subIssueCode or not subIssueName:
        raise ValueError(
            "POST_DMA_SUB_ISSUE_METADATA_NOT_READY: "
            f"cycleId={cycle.get('id')}, "
            f"metricId={scope.get('metric_id')}, "
            f"subIssueCode={scope.get('source_sub_issue_code') or subIssueCode}"
        )
    return {
        "issueDomain": issueDomain,
        "subIssueId": int(subIssueId),
        "subIssueCode": subIssueCode,
        "subIssueName": subIssueName,
    }


def normalizeIssueDomain(value: Optional[str]) -> Optional[str]:
    normalizedValue = str(value or "").strip().upper()
    if normalizedValue in {"E", "ENVIRONMENT", "ENVIRONMENTAL"} or normalizedValue.startswith("E_"):
        return "environmental"
    if normalizedValue in {"S", "SOCIAL"} or normalizedValue.startswith("S_"):
        return "social"
    if normalizedValue in {"G", "GOVERNANCE"} or normalizedValue.startswith("G_"):
        return "governance"
    if normalizedValue in {"G0", "GENERAL"}:
        return "general"
    return None


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
        allowedSources = {"onboarding_input"}
        priority = {"onboarding_input": 0}
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
    assignmentStatus = row.get("assignment_status")
    email = None
    if str(assignmentStatus or "").strip().lower() != "unassigned":
        email = row.get("invite_email") or row.get("user_email") or row.get("assignee_email")
    return OnboardingAssignmentDto(
        assignmentId=int(row["assignment_id"]) if row.get("assignment_id") is not None else None,
        assignmentStatus=assignmentStatus,
        assigneeUserId=int(row["assignee_user_id"]) if row.get("assignee_user_id") is not None else None,
        assigneeEmailMasked=maskEmail(email),
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


def bulkAssign(request: OnboardingAssignmentBulkAssignRequestDto, userModel) -> OnboardingAssignmentBulkAssignResponseDto:
    checkScope(request.companyId, userModel)
    checkManager(userModel)
    normalizedCycleType = checkAssignmentCycleType(request.cycleType)
    cycle = requireCycle(request.companyId, request.reportingYear, normalizedCycleType)
    metricIds = repo.validateCycleMetricIds(int(cycle["id"]), request.companyId, request.metricIds)
    result = assignmentRepo.bulkAssignMetrics(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycle=cycle,
        metricIds=metricIds,
        assigneeEmail=request.assigneeEmail,
        dueDate=request.dueDate,
        sendInviteYn=request.sendInviteYn,
        actorUserId=getActorUserId(userModel),
    )
    mailQueuedYn, warning = publishMailEvent(result.get("mailEvent"))
    return OnboardingAssignmentBulkAssignResponseDto(
        companyId=result["companyId"],
        reportingYear=result["reportingYear"],
        cycleId=result["cycleId"],
        metricIds=result["metricIds"],
        assignmentCount=result["assignmentCount"],
        assignmentStatus=result["assignmentStatus"],
        assigneeResolvedYn=result["assigneeResolvedYn"],
        inviteCreatedYn=result["inviteCreatedYn"],
        inviteReusedYn=result["inviteReusedYn"],
        inviteId=result.get("inviteId"),
        mailQueuedYn=mailQueuedYn,
        warning=warning,
    )


def listAssignmentItems(
    companyId: int,
    reportingYear: int,
    cycleType: str,
    userModel,
) -> OnboardingAssignmentListResponseDto:
    checkScope(companyId, userModel)
    checkManager(userModel)
    normalizedCycleType = checkAssignmentCycleType(cycleType)
    cycle = requireCycle(companyId, reportingYear, normalizedCycleType)
    items = [OnboardingAssignmentItemDto(**item) for item in assignmentRepo.listAssignments(companyId, reportingYear, cycle)]
    return OnboardingAssignmentListResponseDto(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleId=int(cycle["id"]) if cycle else None,
        cycleType=str(cycle.get("cycle_type") or normalizedCycleType),
        items=items,
    )


def getAssignmentItem(
    metricId: str,
    companyId: int,
    reportingYear: int,
    cycleType: str,
    userModel,
) -> OnboardingAssignmentDetailResponseDto:
    checkScope(companyId, userModel)
    checkManager(userModel)
    normalizedCycleType = checkAssignmentCycleType(cycleType)
    cycle = requireCycle(companyId, reportingYear, normalizedCycleType)
    metricIds = repo.validateCycleMetricIds(int(cycle["id"]), companyId, [metricId])
    response = OnboardingAssignmentListResponseDto(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleId=int(cycle["id"]),
        cycleType=str(cycle.get("cycle_type") or normalizedCycleType),
        items=[OnboardingAssignmentItemDto(**item) for item in assignmentRepo.listAssignments(companyId, reportingYear, cycle)],
    )
    for item in response.items:
        if item.metricId == metricIds[0]:
            return OnboardingAssignmentDetailResponseDto(
                companyId=companyId,
                reportingYear=reportingYear,
                cycleId=response.cycleId,
                cycleType=response.cycleType,
                item=item,
            )
    raise ValueError(f"metricId was not found: {metricId}")


def patchAssignment(metricId: str, request: OnboardingAssignmentPatchRequestDto, userModel) -> OnboardingAssignmentBulkAssignResponseDto:
    bulkRequest = OnboardingAssignmentBulkAssignRequestDto(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricIds=[metricId],
        assigneeEmail=request.assigneeEmail,
        dueDate=request.dueDate,
        sendInviteYn=request.sendInviteYn,
    )
    return bulkAssign(bulkRequest, userModel)


def bulkUnassign(request: OnboardingAssignmentBulkUnassignRequestDto, userModel) -> OnboardingAssignmentBulkUnassignResponseDto:
    checkScope(request.companyId, userModel)
    checkManager(userModel)
    normalizedCycleType = checkAssignmentCycleType(request.cycleType)
    cycle = requireCycle(request.companyId, request.reportingYear, normalizedCycleType)
    metricIds = repo.validateCycleMetricIds(int(cycle["id"]), request.companyId, request.metricIds)
    result = assignmentRepo.bulkUnassignMetrics(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycle=cycle,
        metricIds=metricIds,
    )
    return OnboardingAssignmentBulkUnassignResponseDto(**result)


def publishMailEvent(mailEvent: Optional[dict]) -> tuple[bool, Optional[str]]:
    if not mailEvent:
        return False, None
    try:
        from src.utils.kafkasv import sendToKafka

        sendToKafka(mailEvent)
        return True, None
    except Exception as e:
        return False, f"Mail queue failed: {type(e).__name__}"


def requirePreDmaG0Cycle(companyId: int, reportingYear: int) -> dict:
    cycle = repo.resolvePreDmaG0Cycle(companyId=companyId, reportingYear=reportingYear)
    if not cycle:
        raise PreDmaG0CycleNotReadyError(PRE_DMA_G0_CYCLE_NOT_READY_MESSAGE)
    return cycle


def checkCycleType(cycleType: str) -> None:
    if str(cycleType or "").upper() != repo.CYCLE_TYPE_PRE_DMA_G0:
        raise ValueError("Only PRE_DMA_G0 cycleType is supported")


def checkAssignmentCycleType(cycleType: str) -> str:
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType not in SUPPORTED_ASSIGNMENT_CYCLE_TYPES:
        raise ValueError("Only PRE_DMA_G0 or POST_DMA_DISCLOSURE cycleType is supported")
    return normalizedCycleType


def checkManager(userModel) -> None:
    if isAssignmentManager(userModel):
        return
    raise PermissionError("Only ESG담당자 or 관리자 can manage onboarding assignments")


def listVisibleMetricScopesForUser(scopes: list[dict], assignmentRows: list[dict], userModel) -> list[dict]:
    if userModel is None or isAssignmentManager(userModel):
        return scopes
    if isConsultant(userModel):
        raise PermissionError("Consultants cannot access onboarding input metrics")
    if not isEmployee(userModel):
        raise PermissionError("Only assigned users can access onboarding input metrics")
    actorUserId = getActorUserId(userModel)
    assignedMetricIds = {
        row.get("metric_id")
        for row in assignmentRows
        if row.get("assignee_user_id") is not None
        and actorUserId is not None
        and int(row.get("assignee_user_id")) == int(actorUserId)
        and str(row.get("assignment_status") or "").strip().lower() == assignmentRepo.ASSIGNMENT_STATUS_ASSIGNED
    }
    return [scope for scope in scopes if scope.get("metric_id") in assignedMetricIds]


def checkMetricInputPermission(*, cycle: dict, companyId: int, metricId: str, userModel) -> None:
    if userModel is None:
        return
    if isConsultant(userModel):
        raise PermissionError("Consultants cannot input onboarding metrics")
    if isAssignmentManager(userModel):
        return
    actorUserId = getActorUserId(userModel)
    if actorUserId is None:
        raise PermissionError("Authenticated user id is required")
    assignmentRows = assignmentRepo.listAssignmentRows(int(cycle["id"]), companyId)
    assignment = next((row for row in assignmentRows if row.get("metric_id") == metricId), None)
    if not assignment:
        raise PermissionError(f"Metric assignment is required: {metricId}")
    if str(assignment.get("assignment_status") or "").strip().lower() != assignmentRepo.ASSIGNMENT_STATUS_ASSIGNED:
        raise PermissionError(f"Metric assignment must be assigned before input: {metricId}")
    if assignment.get("assignee_user_id") is None or int(assignment.get("assignee_user_id")) != int(actorUserId):
        raise PermissionError(f"Only the assigned user can input metricId={metricId}")


def checkMetricStatusPermission(summary: dict, userModel) -> bool:
    if isReviewer(userModel) or isAssignmentManager(userModel):
        return True
    if isEmployee(userModel):
        actorUserId = getActorUserId(userModel)
        return (
            actorUserId is not None
            and summary.get("assigneeUserId") is not None
            and int(summary.get("assigneeUserId")) == int(actorUserId)
        )
    return False


def isAssignmentManager(userModel) -> bool:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in ASSIGNMENT_MANAGER_ROLES or roleName in ASSIGNMENT_MANAGER_ROLE_NAMES


def isEmployee(userModel) -> bool:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in EMPLOYEE_ROLES or roleName in EMPLOYEE_ROLE_NAMES


def isConsultant(userModel) -> bool:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in CONSULTANT_ROLES or roleName in CONSULTANT_ROLE_NAMES


def isReviewer(userModel) -> bool:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in REVIEWER_ROLES or roleName in REVIEWER_ROLE_NAMES


def submitApproval(request: OnboardingApprovalRequestDto, userModel) -> OnboardingApprovalActionResponseDto:
    checkScope(request.companyId, userModel)
    cycle = requireCycle(request.companyId, request.reportingYear, request.cycleType)
    checkMetricInputPermission(
        cycle=cycle,
        companyId=request.companyId,
        metricId=request.metricId,
        userModel=userModel,
    )
    summary = approvalService.submitMetricApproval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=request.metricId,
        actorUserId=getActorUserId(userModel),
        commentText=getattr(request, "commentText", None),
    )
    return actionResponse(summary, "Submitted")


def reviewApproval(request, userModel) -> OnboardingApprovalActionResponseDto:
    checkScope(request.companyId, userModel)
    checkReviewer(userModel)
    summary = approvalService.reviewMetricApproval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=request.metricId,
        actorUserId=getActorUserId(userModel),
        commentText=getattr(request, "commentText", None),
    )
    return actionResponse(summary, "Reviewed")


def approveApproval(request, userModel) -> OnboardingApprovalActionResponseDto:
    checkScope(request.companyId, userModel)
    checkApprover(userModel)
    summary = approvalService.approveMetricApproval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=request.metricId,
        actorUserId=getActorUserId(userModel),
        commentText=getattr(request, "commentText", None),
    )
    return actionResponse(summary, "Approved")


def rejectApproval(request, userModel) -> OnboardingApprovalActionResponseDto:
    checkScope(request.companyId, userModel)
    checkReviewer(userModel)
    commentText = (getattr(request, "commentText", None) or "").strip()
    if not commentText:
        raise ValueError("commentText is required for rejection")
    summary = approvalService.rejectMetricApproval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=request.metricId,
        actorUserId=getActorUserId(userModel),
        commentText=commentText,
    )
    return actionResponse(summary, "Rejected")


def listApprovals(
    companyId: int,
    reportingYear: Optional[int],
    status: Optional[str],
    cycleType: Optional[str],
    assignedOnlyYn: bool,
    userModel,
) -> OnboardingApprovalListResponseDto:
    checkScope(companyId, userModel)
    rows = repo.listCycleApprovalInboxRows(
        companyId=companyId,
        reportingYear=reportingYear,
        status=status,
        cycleType=cycleType,
        assignedOnlyYn=assignedOnlyYn,
    )
    if isEmployee(userModel):
        rows = [row for row in rows if checkMetricStatusPermission(row, userModel)]
    elif not (isReviewer(userModel) or isAssignmentManager(userModel)):
        raise PermissionError("Only approvers, reviewers, or assigned employees can view approval status")
    items = [itemDto(summary, userModel) for summary in rows]
    return OnboardingApprovalListResponseDto(data=OnboardingApprovalListDataDto(items=items))


def getApprovalStatus(
    companyId: int,
    reportingYear: int,
    metricId: str,
    userModel,
    cycleType: str = CYCLE_TYPE_PRE_DMA_G0,
) -> OnboardingApprovalStatusResponseDto:
    checkScope(companyId, userModel)
    summary = approvalService.buildMetricApprovalSummary(companyId, reportingYear, metricId, cycleType)
    if not checkMetricStatusPermission(summary, userModel):
        raise PermissionError("Only approvers, reviewers, or the assigned employee can view approval status")
    return OnboardingApprovalStatusResponseDto(data=statusDto(summary, userModel))


def getApprovalDetail(
    companyId: int,
    reportingYear: int,
    metricId: str,
    cycleType: str,
    userModel,
) -> OnboardingApprovalDetailResponseDto:
    checkScope(companyId, userModel)
    cycle = requireCycle(companyId, reportingYear, cycleType)
    summary = approvalService.buildMetricApprovalSummary(companyId, reportingYear, metricId, cycleType)
    if not checkMetricStatusPermission(summary, userModel):
        raise PermissionError("Only approvers, reviewers, or the assigned employee can view approval status")
    scopes = repo.listMetricScopes(int(cycle["id"]), companyId, metricId)
    if not scopes:
        raise ValueError("Metric is not in active cycle scope")
    atomicRows = repo.listApprovalAtomicDetailRows(companyId, reportingYear, int(cycle["id"]), metricId)
    return OnboardingApprovalDetailResponseDto(
        data=detailDto(summary, atomicRows, userModel)
    )


def ensureWorkflowPreDmaG0Cycle(run: dict, actorUserId: Optional[int] = None) -> dict:
    if not run:
        return {}
    return repo.ensurePreDmaG0Cycle(
        companyId=int(run["company_id"]),
        reportingYear=int(run["reporting_year"]),
        reportBasisType=run.get("report_basis_type"),
        sourceMaterialityRunId=int(run["id"]) if run.get("id") is not None else None,
        actorUserId=actorUserId,
    )


def ensureWorkflowPostDmaDisclosureCycle(run: dict, actorUserId: Optional[int] = None) -> dict:
    if not run:
        return {}
    return repo.ensurePostDmaDisclosureCycle(
        companyId=int(run["company_id"]),
        reportingYear=int(run["reporting_year"]),
        reportBasisType=run.get("report_basis_type"),
        sourceMaterialityRunId=int(run["id"]),
        actorUserId=actorUserId,
    )


def actionResponse(summary: dict, message: str) -> OnboardingApprovalActionResponseDto:
    return OnboardingApprovalActionResponseDto(
        data=statusDto(summary, None),
        message=message,
    )


def itemDto(summary: dict, userModel) -> OnboardingApprovalItemDto:
    payload = dict(summary)
    payload.pop("selfSubmittedYn", None)
    return OnboardingApprovalItemDto(
        **payload,
        selfSubmittedYn=checkSelfSubmitted(summary, userModel),
    )


def statusDto(summary: dict, userModel) -> OnboardingApprovalStatusDataDto:
    payload = dict(summary)
    payload.pop("selfSubmittedYn", None)
    approvalPolicyCode = str(summary.get("approvalPolicyCode") or "").strip().upper()
    promotedQuantAtomicCount = int(summary.get("promotedQuantAtomicCount") or 0)
    approvedPromotedFactCount = int(summary.get("approvedPromotedFactCount") or 0)
    return OnboardingApprovalStatusDataDto(
        **payload,
        selfSubmittedYn=checkSelfSubmitted(summary, userModel),
        rollupReadyYn=(
            approvalPolicyCode == repo.APPROVAL_POLICY_PROMOTE_TO_KPI_FACT_AND_ROLLUP
            and promotedQuantAtomicCount > 0
            and approvedPromotedFactCount >= promotedQuantAtomicCount
        ),
    )


def detailDto(
    summary: dict,
    atomicRows: list[dict],
    userModel,
) -> OnboardingApprovalDetailDataDto:
    base = statusDto(summary, userModel)
    payload = base.model_dump() if hasattr(base, "model_dump") else base.dict()
    return OnboardingApprovalDetailDataDto(
        **payload,
        atomicItems=[
            OnboardingApprovalAtomicDetailItemDto(
                atomicMetricId=row["atomic_metric_id"],
                atomicName=row.get("atomic_name"),
                dataValueType=row.get("data_value_type"),
                atomicDataRole=row.get("atomic_data_role"),
                inputMode=row.get("input_mode"),
                valueText=row.get("value_text"),
                valueNumeric=row.get("value_numeric"),
                unit=row.get("unit"),
                inputStatus=row.get("input_status"),
                updatedAt=row.get("updated_at"),
                evidenceCount=int(row.get("evidence_count") or 0),
            )
            for row in atomicRows
            if row.get("atomic_metric_id")
        ],
    )


def checkSupportedMetric(metricId: str) -> None:
    return None


def checkApprover(userModel) -> None:
    if isApprover(userModel):
        return
    raise PermissionError("Only ESG담당자 or 관리자 can approve/reject onboarding inputs")


def checkReviewer(userModel) -> None:
    if isReviewer(userModel):
        return
    raise PermissionError("Only consultants, ESG담당자, or 관리자 can review onboarding inputs")


def isApprover(userModel) -> bool:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in APPROVER_ROLES or roleName in APPROVER_ROLE_NAMES


def checkSelfSubmitted(summary: dict, userModel) -> bool:
    actorUserId = getActorUserId(userModel)
    inputUserId = summary.get("inputUserId")
    return actorUserId is not None and inputUserId is not None and int(actorUserId) == int(inputUserId)


def getActorUserId(userModel) -> Optional[int]:
    value = readUserField(userModel, "id")
    return int(value) if value is not None else None


def readUserField(userModel, key: str):
    if userModel is None:
        return None
    if isinstance(userModel, dict):
        return userModel.get(key)
    return getattr(userModel, key, None)
