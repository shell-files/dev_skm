from __future__ import annotations

from typing import Optional

from src.models.onboarding import (
    OnboardingAssignmentBulkAssignRequestDto,
    OnboardingAssignmentBulkAssignResponseDto,
    OnboardingAssignmentBulkUnassignRequestDto,
    OnboardingAssignmentBulkUnassignResponseDto,
    OnboardingAssignmentDetailResponseDto,
    OnboardingAssignmentItemDto,
    OnboardingAssignmentListResponseDto,
    OnboardingAssignmentPatchRequestDto,
)
from src.repositories import onboardingassignmentrepository as assignmentRepo
from src.repositories import onboardingrepository as repo
from src.utils.companyscope import checkScope


class PreDmaG0CycleNotReadyError(ValueError):
    pass


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
    from src.services.onboardings.service import PRE_DMA_G0_CYCLE_NOT_READY_MESSAGE
    cycle = repo.resolvePreDmaG0Cycle(companyId=companyId, reportingYear=reportingYear)
    if not cycle:
        raise PreDmaG0CycleNotReadyError(PRE_DMA_G0_CYCLE_NOT_READY_MESSAGE)
    return cycle


def checkCycleType(cycleType: str) -> None:
    if str(cycleType or "").upper() != repo.CYCLE_TYPE_PRE_DMA_G0:
        raise ValueError("Only PRE_DMA_G0 cycleType is supported")


def checkAssignmentCycleType(cycleType: str) -> str:
    from src.services.onboardings.service import SUPPORTED_ASSIGNMENT_CYCLE_TYPES
    normalizedCycleType = str(cycleType or "").strip().upper()
    if normalizedCycleType not in SUPPORTED_ASSIGNMENT_CYCLE_TYPES:
        raise ValueError("Only PRE_DMA_G0, POST_DMA_DISCLOSURE, or ROLLUP_RESPONSE cycleType is supported")
    return normalizedCycleType


def checkManager(userModel) -> None:
    from src.services.onboardings.service import isAssignmentManager
    if isAssignmentManager(userModel):
        return
    raise PermissionError("Only ESG담당자 or 관리자 can manage onboarding assignments")


def bulkAssign(request: OnboardingAssignmentBulkAssignRequestDto, userModel) -> OnboardingAssignmentBulkAssignResponseDto:
    from src.services.onboardings.service import requireCycle, getActorUserId
    checkScope(request.companyId, userModel)
    checkManager(userModel)
    normalizedCycleType = checkAssignmentCycleType(request.cycleType)
    cycle = requireCycle(request.companyId, request.reportingYear, normalizedCycleType, batchId=getattr(request, "batchId", None))
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
    batchId: Optional[int] = None,
) -> OnboardingAssignmentListResponseDto:
    from src.services.onboardings.service import requireCycle
    checkScope(companyId, userModel)
    checkManager(userModel)
    normalizedCycleType = checkAssignmentCycleType(cycleType)
    cycle = requireCycle(companyId, reportingYear, normalizedCycleType, batchId=batchId)
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
    batchId: Optional[int] = None,
) -> OnboardingAssignmentDetailResponseDto:
    from src.services.onboardings.service import requireCycle
    checkScope(companyId, userModel)
    checkManager(userModel)
    normalizedCycleType = checkAssignmentCycleType(cycleType)
    cycle = requireCycle(companyId, reportingYear, normalizedCycleType, batchId=batchId)
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
        batchId=getattr(request, "batchId", None),
        metricIds=[metricId],
        assigneeEmail=request.assigneeEmail,
        dueDate=request.dueDate,
        sendInviteYn=request.sendInviteYn,
    )
    return bulkAssign(bulkRequest, userModel)


def bulkUnassign(request: OnboardingAssignmentBulkUnassignRequestDto, userModel) -> OnboardingAssignmentBulkUnassignResponseDto:
    from src.services.onboardings.service import requireCycle
    checkScope(request.companyId, userModel)
    checkManager(userModel)
    normalizedCycleType = checkAssignmentCycleType(request.cycleType)
    cycle = requireCycle(request.companyId, request.reportingYear, normalizedCycleType, batchId=getattr(request, "batchId", None))
    metricIds = repo.validateCycleMetricIds(int(cycle["id"]), request.companyId, request.metricIds)
    result = assignmentRepo.bulkUnassignMetrics(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycle=cycle,
        metricIds=metricIds,
    )
    return OnboardingAssignmentBulkUnassignResponseDto(**result)


__all__ = [
    "PreDmaG0CycleNotReadyError",
    "bulkAssign",
    "bulkUnassign",
    "getAssignmentItem",
    "listAssignmentItems",
    "patchAssignment",
]
