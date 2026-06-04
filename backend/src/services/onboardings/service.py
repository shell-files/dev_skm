from __future__ import annotations

from typing import Optional

from src.models.onboarding import (
    OnboardingApprovalActionResponseDto,
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


CYCLE_TYPE_PRE_DMA_G0 = "PRE_DMA_G0"
CYCLE_TYPE_POST_DMA_DISCLOSURE = "POST_DMA_DISCLOSURE"
PRE_DMA_G0_CYCLE_NOT_READY = "PRE_DMA_G0_CYCLE_NOT_READY: 보고연도 프로젝트를 먼저 시작해 주세요."
PRE_DMA_G0_SCOPE_NOT_READY = "PRE_DMA_G0_SCOPE_NOT_READY: 온보딩 지표 범위가 초기화되지 않았습니다. 기존 프로젝트를 재개해 주세요."
POST_DMA_DISCLOSURE_CYCLE_NOT_READY = "POST_DMA_DISCLOSURE_CYCLE_NOT_READY: POST_DMA_DISCLOSURE cycle을 먼저 초기화해 주세요."
POST_DMA_DISCLOSURE_SCOPE_NOT_READY = "POST_DMA_DISCLOSURE_SCOPE_NOT_READY: POST_DMA_DISCLOSURE 지표 범위가 초기화되지 않았습니다."
STRUCTURED_LOOKUP_IDS = {"G0-05__QL0002", "G0-06__QL0001"}
EDITABLE_INPUT_MODES = {"MANUAL_NUMBER", "MANUAL_TEXTAREA", "YEAR_RANGE"}
SUPPORTED_CYCLE_TYPE = "PRE_DMA_G0"
SUPPORTED_INPUT_CYCLE_TYPES = {CYCLE_TYPE_PRE_DMA_G0, CYCLE_TYPE_POST_DMA_DISCLOSURE}
SUPPORTED_ASSIGNMENT_CYCLE_TYPES = {CYCLE_TYPE_PRE_DMA_G0, CYCLE_TYPE_POST_DMA_DISCLOSURE}
ASSIGNMENT_MANAGER_ROLES = {"ADMIN", "ESG"}
ASSIGNMENT_MANAGER_ROLE_NAMES = {"관리자", "ESG담당자"}
PRE_DMA_G0_CYCLE_NOT_READY_MESSAGE = "PRE_DMA_G0_CYCLE_NOT_READY: 기존 PRE_DMA_G0 workflow를 먼저 시작해 주세요."
APPROVER_ROLES = {"ADMIN", "ESG"}
APPROVER_ROLE_NAMES = {"관리자", "ESG담당자"}


class PreDmaG0CycleNotReadyError(ValueError):
    pass


def listMetrics(
    *,
    companyId: int,
    reportingYear: Optional[int],
    cycleType: str,
    metricId: Optional[str] = None,
) -> OnboardingMetricsResponseDto:
    year = repo.resolveReportingYear(companyId, reportingYear)
    cycle = requireCycle(companyId, year, cycleType)
    allScopes = repo.listMetricScopes(int(cycle["id"]), companyId)
    if not allScopes:
        raise ValueError(scopeNotReadyMessage(cycle.get("cycle_type") or cycleType))
    scopes = allScopes
    if metricId:
        scopes = [row for row in allScopes if row.get("metric_id") == metricId]
        if not scopes:
            raise ValueError(f"Unsupported metricId for cycle scope: {metricId}")
    metricIds = [row["metric_id"] for row in scopes]
    masterRows = repo.listAtomicMaster(metricIds)
    valueRows = repo.listValueRows(companyId, year, metricIds)
    assignmentRows = assignmentRepo.listAssignmentRows(int(cycle["id"]), companyId)
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
) -> OnboardingMetricValuesResponseDto:
    prepared = validateMetricValues(metricId=metricId, request=request, userId=userId)
    cycle = prepared["cycle"]
    savedCount = saveMetricValueGroups([prepared])
    return OnboardingMetricValuesResponseDto(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleId=int(cycle["id"]),
        cycleType=request.cycleType,
        metricId=metricId,
        savedItemCount=savedCount,
    )


def validateMetricValues(
    *,
    metricId: str,
    request: OnboardingMetricValuesRequestDto,
    userId: Optional[int] = None,
) -> dict:
    cycle = requireCycle(request.companyId, request.reportingYear, request.cycleType)
    metrics = listMetrics(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=metricId,
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
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    if role in ASSIGNMENT_MANAGER_ROLES or roleName in ASSIGNMENT_MANAGER_ROLE_NAMES:
        return
    raise PermissionError("Only ESG담당자 or 관리자 can manage onboarding assignments")


def submitApproval(request: OnboardingApprovalRequestDto, userModel) -> OnboardingApprovalActionResponseDto:
    checkScope(request.companyId, userModel)
    checkSupportedMetric(request.metricId)
    summary = repo.submitG002Approval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        reportBasisType=None,
        sourceMaterialityRunId=None,
        actorUserId=getActorUserId(userModel),
    )
    return actionResponse(summary, "Submitted")


def approveApproval(request, userModel) -> OnboardingApprovalActionResponseDto:
    checkScope(request.companyId, userModel)
    checkSupportedMetric(request.metricId)
    checkApprover(userModel)
    summary = repo.approveG002Approval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        actorUserId=getActorUserId(userModel),
        commentText=getattr(request, "commentText", None),
    )
    return actionResponse(summary, "Approved")


def rejectApproval(request, userModel) -> OnboardingApprovalActionResponseDto:
    checkScope(request.companyId, userModel)
    checkSupportedMetric(request.metricId)
    checkApprover(userModel)
    commentText = (getattr(request, "commentText", None) or "").strip()
    if not commentText:
        raise ValueError("commentText is required for rejection")
    summary = repo.rejectG002Approval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
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
    if cycleType and str(cycleType).upper() != repo.CYCLE_TYPE_PRE_DMA_G0:
        return OnboardingApprovalListResponseDto(data=OnboardingApprovalListDataDto(items=[]))
    items = [
        itemDto(summary, userModel)
        for summary in repo.listCycleApprovalInboxRows(
            companyId=companyId,
            reportingYear=reportingYear,
            status=status,
            cycleType=cycleType,
            assignedOnlyYn=assignedOnlyYn,
        )
    ]
    return OnboardingApprovalListResponseDto(data=OnboardingApprovalListDataDto(items=items))


def getApprovalStatus(
    companyId: int,
    reportingYear: int,
    metricId: str,
    userModel,
) -> OnboardingApprovalStatusResponseDto:
    checkScope(companyId, userModel)
    checkSupportedMetric(metricId)
    summary = repo.buildApprovalSummary(companyId, reportingYear, metricId)
    return OnboardingApprovalStatusResponseDto(data=statusDto(summary, userModel))


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
    return OnboardingApprovalStatusDataDto(
        **payload,
        selfSubmittedYn=checkSelfSubmitted(summary, userModel),
        rollupReadyYn=int(summary.get("approvedAtomicCount") or 0) >= len(repo.REQUIRED_ATOMIC_IDS),
    )


def checkSupportedMetric(metricId: str) -> None:
    if metricId != repo.METRIC_ID_G0_02:
        raise ValueError("Only G0-02 approval is supported in MVP")


def checkApprover(userModel) -> None:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    if role in APPROVER_ROLES or roleName in APPROVER_ROLE_NAMES:
        return
    raise PermissionError("Only ESG담당자 or 관리자 can approve/reject G0-02 inputs")


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
