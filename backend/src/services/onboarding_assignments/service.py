from __future__ import annotations

from typing import Optional

from src.models.onboardingassignment import (
    OnboardingAssignmentBulkAssignRequestDto,
    OnboardingAssignmentBulkAssignResponseDto,
    OnboardingAssignmentBulkUnassignRequestDto,
    OnboardingAssignmentBulkUnassignResponseDto,
    OnboardingAssignmentDetailResponseDto,
    OnboardingAssignmentItemDto,
    OnboardingAssignmentListResponseDto,
    OnboardingAssignmentPatchRequestDto,
)
from src.utils.companyscope import checkScope
from src.utils.onboardingapprovalrepository import (
    CYCLE_TYPE_PRE_DMA_G0,
    resolvePreDmaG0Cycle,
    validateCycleMetricIds,
)
from src.utils.onboardingassignmentrepository import (
    bulkAssignMetrics,
    bulkUnassignMetrics,
    listAssignments,
)


SUPPORTED_CYCLE_TYPE = "PRE_DMA_G0"
SUPPORTED_TARGET_ROLE = "EMPLOYEE"
INVITE_EXPIRE_DAYS = 7
ASSIGNMENT_MANAGER_ROLES = {"ADMIN", "ESG"}
ASSIGNMENT_MANAGER_ROLE_NAMES = {"관리자", "ESG담당자"}
PRE_DMA_G0_CYCLE_NOT_READY_MESSAGE = "PRE_DMA_G0_CYCLE_NOT_READY: 보고서 기준 선택 후 온보딩 workflow를 먼저 시작해 주세요."


class PreDmaG0CycleNotReadyError(ValueError):
    pass


def bulkAssign(request: OnboardingAssignmentBulkAssignRequestDto, userModel) -> OnboardingAssignmentBulkAssignResponseDto:
    checkScope(request.companyId, userModel)
    checkManager(userModel)
    checkCycleType(request.cycleType)
    cycle = requirePreDmaG0Cycle(request.companyId, request.reportingYear)
    metricIds = validateCycleMetricIds(int(cycle["id"]), request.companyId, request.metricIds)
    result = bulkAssignMetrics(
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
    checkCycleType(cycleType)
    cycle = resolvePreDmaG0Cycle(companyId=companyId, reportingYear=reportingYear)
    items = [OnboardingAssignmentItemDto(**item) for item in listAssignments(companyId, reportingYear, cycle)]
    return OnboardingAssignmentListResponseDto(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleId=int(cycle["id"]) if cycle else None,
        cycleType=SUPPORTED_CYCLE_TYPE,
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
    checkCycleType(cycleType)
    cycle = requirePreDmaG0Cycle(companyId, reportingYear)
    metricIds = validateCycleMetricIds(int(cycle["id"]), companyId, [metricId])
    response = OnboardingAssignmentListResponseDto(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleId=int(cycle["id"]),
        cycleType=SUPPORTED_CYCLE_TYPE,
        items=[OnboardingAssignmentItemDto(**item) for item in listAssignments(companyId, reportingYear, cycle)],
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
    checkCycleType(request.cycleType)
    cycle = requirePreDmaG0Cycle(request.companyId, request.reportingYear)
    metricIds = validateCycleMetricIds(int(cycle["id"]), request.companyId, request.metricIds)
    result = bulkUnassignMetrics(
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
    cycle = resolvePreDmaG0Cycle(companyId=companyId, reportingYear=reportingYear)
    if not cycle:
        raise PreDmaG0CycleNotReadyError(PRE_DMA_G0_CYCLE_NOT_READY_MESSAGE)
    return cycle


def checkCycleType(cycleType: str) -> None:
    if str(cycleType or "").upper() != CYCLE_TYPE_PRE_DMA_G0:
        raise ValueError("Only PRE_DMA_G0 cycleType is supported")


def checkManager(userModel) -> None:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    if role in ASSIGNMENT_MANAGER_ROLES or roleName in ASSIGNMENT_MANAGER_ROLE_NAMES:
        return
    raise PermissionError("Only ESG 담당자 or 관리자 can manage onboarding assignments")


def getActorUserId(userModel) -> Optional[int]:
    value = readUserField(userModel, "id")
    return int(value) if value is not None else None


def readUserField(userModel, key: str):
    if userModel is None:
        return None
    if isinstance(userModel, dict):
        return userModel.get(key)
    return getattr(userModel, key, None)


__all__ = [
    "bulkAssign",
    "listAssignmentItems",
    "getAssignmentItem",
    "patchAssignment",
    "bulkUnassign",
    "requirePreDmaG0Cycle",
    "checkManager",
    "publishMailEvent",
    "PreDmaG0CycleNotReadyError",
]
