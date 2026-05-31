from __future__ import annotations

from typing import Optional

from src.models.onboardingapproval import (
    OnboardingApprovalActionResponseDto,
    OnboardingApprovalItemDto,
    OnboardingApprovalListDataDto,
    OnboardingApprovalListResponseDto,
    OnboardingApprovalRequestDto,
    OnboardingApprovalStatusDataDto,
    OnboardingApprovalStatusResponseDto,
)
from src.utils.companyscope import checkScope
from src.utils.onboardingapprovalrepository import (
    CYCLE_TYPE_PRE_DMA_G0,
    METRIC_ID_G0_02,
    REQUIRED_ATOMIC_IDS,
    approveG002Approval,
    buildApprovalSummary,
    ensurePreDmaG0Cycle,
    listApprovalSummaries,
    rejectG002Approval,
    submitG002Approval,
)


APPROVER_ROLES = {"ADMIN", "ESG"}
APPROVER_ROLE_NAMES = {"관리자", "ESG담당자"}


def submitApproval(request: OnboardingApprovalRequestDto, userModel) -> OnboardingApprovalActionResponseDto:
    checkScope(request.companyId, userModel)
    checkSupportedMetric(request.metricId)
    summary = submitG002Approval(
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
    summary = approveG002Approval(
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
    summary = rejectG002Approval(
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
    userModel,
) -> OnboardingApprovalListResponseDto:
    checkScope(companyId, userModel)
    if cycleType and str(cycleType).upper() != CYCLE_TYPE_PRE_DMA_G0:
        return OnboardingApprovalListResponseDto(data=OnboardingApprovalListDataDto(items=[]))
    items = [
        itemDto(summary, userModel)
        for summary in listApprovalSummaries(companyId, reportingYear, status, cycleType)
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
    summary = buildApprovalSummary(companyId, reportingYear, metricId)
    return OnboardingApprovalStatusResponseDto(data=statusDto(summary, userModel))


def ensureWorkflowPreDmaG0Cycle(run: dict, actorUserId: Optional[int] = None) -> dict:
    if not run:
        return {}
    return ensurePreDmaG0Cycle(
        companyId=int(run["company_id"]),
        reportingYear=int(run["reporting_year"]),
        reportBasisType=run.get("report_basis_type"),
        sourceMaterialityRunId=int(run["id"]) if run.get("id") is not None else None,
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
        rollupReadyYn=int(summary.get("approvedAtomicCount") or 0) >= len(REQUIRED_ATOMIC_IDS),
    )


def checkSupportedMetric(metricId: str) -> None:
    if metricId != METRIC_ID_G0_02:
        raise ValueError("Only G0-02 approval is supported in MVP")


def checkApprover(userModel) -> None:
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    if role in APPROVER_ROLES or roleName in APPROVER_ROLE_NAMES:
        return
    raise PermissionError("Only ESG 담당자 or 관리자 can approve/reject G0-02 inputs")


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


__all__ = [
    "submitApproval",
    "approveApproval",
    "rejectApproval",
    "listApprovals",
    "getApprovalStatus",
    "ensureWorkflowPreDmaG0Cycle",
    "checkApprover",
]
