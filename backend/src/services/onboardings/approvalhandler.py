"""
approvalhandler.py
레이어: Service (onboardings)
역할: 온보딩 결재 요청·처리 핸들러 — 결재 요청 생성 및 승인·반려 처리.
"""
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
)
from src.repositories import onboardingrepository as repo
from src.services.onboardings import approvalservice
from src.utils.companyscope import checkScope


def submitApproval(request: OnboardingApprovalRequestDto, userModel) -> OnboardingApprovalActionResponseDto:
    """입력 권한을 확인한 뒤 지표 결재 제출 요청을 처리하고 결재 현황 응답을 반환한다."""
    from src.services.onboardings.service import requireCycle, checkMetricInputPermission, getActorUserId
    checkScope(request.companyId, userModel)
    cycle = requireCycle(request.companyId, request.reportingYear, request.cycleType, batchId=getattr(request, "batchId", None))
    checkMetricInputPermission(
        cycle=cycle,
        companyId=request.companyId,
        metricId=request.metricId,
        userModel=userModel,
    )
    summary = approvalservice.submitMetricApproval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=request.metricId,
        actorUserId=getActorUserId(userModel),
        commentText=getattr(request, "commentText", None),
        batchId=getattr(request, "batchId", None),
    )
    return actionResponse(summary, "Submitted")


def reviewApproval(request, userModel) -> OnboardingApprovalActionResponseDto:
    """검토 권한을 확인한 뒤 지표를 reviewed 상태로 전환하고 결재 현황 응답을 반환한다."""
    from src.services.onboardings.service import getActorUserId
    checkScope(request.companyId, userModel)
    checkReviewer(userModel)
    summary = approvalservice.reviewMetricApproval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=request.metricId,
        actorUserId=getActorUserId(userModel),
        commentText=getattr(request, "commentText", None),
        batchId=getattr(request, "batchId", None),
    )
    return actionResponse(summary, "Reviewed")


def approveApproval(request, userModel) -> OnboardingApprovalActionResponseDto:
    """승인 권한을 확인한 뒤 지표를 approved 상태로 전환하고 결재 현황 응답을 반환한다."""
    from src.services.onboardings.service import getActorUserId
    checkScope(request.companyId, userModel)
    checkApprover(userModel)
    summary = approvalservice.approveMetricApproval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=request.metricId,
        actorUserId=getActorUserId(userModel),
        commentText=getattr(request, "commentText", None),
        batchId=getattr(request, "batchId", None),
    )
    return actionResponse(summary, "Approved")


def rejectApproval(request, userModel) -> OnboardingApprovalActionResponseDto:
    """검토 권한과 코멘트 필수 여부를 확인한 뒤 지표를 rejected 상태로 전환한다."""
    from src.services.onboardings.service import getActorUserId
    checkScope(request.companyId, userModel)
    checkReviewer(userModel)
    commentText = (getattr(request, "commentText", None) or "").strip()
    if not commentText:
        raise ValueError("commentText is required for rejection")
    summary = approvalservice.rejectMetricApproval(
        companyId=request.companyId,
        reportingYear=request.reportingYear,
        cycleType=request.cycleType,
        metricId=request.metricId,
        actorUserId=getActorUserId(userModel),
        commentText=commentText,
        batchId=getattr(request, "batchId", None),
    )
    return actionResponse(summary, "Rejected")


def listApprovals(
    companyId: int,
    reportingYear: Optional[int],
    status: Optional[str],
    cycleType: Optional[str],
    assignedOnlyYn: bool,
    userModel,
    batchId: Optional[int] = None,
) -> OnboardingApprovalListResponseDto:
    """역할에 따라 열람 가능한 결재 현황 목록을 조회해 반환한다."""
    from src.services.onboardings.service import (
        resolveCycleSourceMaterialityRunId,
        isEmployee, isReviewer, isAssignmentManager,
        checkMetricStatusPermission,
    )
    checkScope(companyId, userModel)
    year = repo.resolveReportingYear(companyId, reportingYear)
    sourceMaterialityRunId = resolveCycleSourceMaterialityRunId(companyId, year, cycleType)
    rows = repo.listCycleApprovalInboxRows(
        companyId=companyId,
        reportingYear=year,
        status=status,
        cycleType=cycleType,
        assignedOnlyYn=assignedOnlyYn,
        batchId=batchId,
        sourceMaterialityRunId=sourceMaterialityRunId,
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
    cycleType: str = "PRE_DMA_G0",
    batchId: Optional[int] = None,
) -> OnboardingApprovalStatusResponseDto:
    """열람 권한을 확인한 뒤 특정 지표의 결재 상태 요약을 반환한다."""
    from src.services.onboardings.service import resolveCycleSourceMaterialityRunId, checkMetricStatusPermission
    checkScope(companyId, userModel)
    sourceMaterialityRunId = resolveCycleSourceMaterialityRunId(companyId, reportingYear, cycleType)
    summary = approvalservice.buildMetricApprovalSummary(
        companyId,
        reportingYear,
        metricId,
        cycleType,
        batchId=batchId,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
    if not checkMetricStatusPermission(summary, userModel):
        raise PermissionError("Only approvers, reviewers, or the assigned employee can view approval status")
    return OnboardingApprovalStatusResponseDto(data=statusDto(summary, userModel))


def getApprovalDetail(
    companyId: int,
    reportingYear: int,
    metricId: str,
    cycleType: str,
    userModel,
    batchId: Optional[int] = None,
) -> OnboardingApprovalDetailResponseDto:
    """결재 현황과 원자 지표별 입력값 상세 내역을 포함한 결재 상세 응답을 반환한다."""
    from src.services.onboardings.service import requireCycle, resolveCycleSourceMaterialityRunId, checkMetricStatusPermission
    checkScope(companyId, userModel)
    sourceMaterialityRunId = resolveCycleSourceMaterialityRunId(companyId, reportingYear, cycleType)
    cycle = requireCycle(
        companyId,
        reportingYear,
        cycleType,
        batchId=batchId,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
    summary = approvalservice.buildMetricApprovalSummary(
        companyId,
        reportingYear,
        metricId,
        cycleType,
        batchId=batchId,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )
    if not checkMetricStatusPermission(summary, userModel):
        raise PermissionError("Only approvers, reviewers, or the assigned employee can view approval status")
    scopes = repo.listMetricScopes(int(cycle["id"]), companyId, metricId)
    if not scopes:
        raise ValueError("Metric is not in active cycle scope")
    atomicRows = repo.listApprovalAtomicDetailRows(
        companyId,
        reportingYear,
        int(cycle["id"]),
        metricId,
        cycleType=cycleType,
        batchId=batchId,
    )
    return OnboardingApprovalDetailResponseDto(
        data=detailDto(summary, atomicRows, userModel)
    )


def actionResponse(summary: dict, message: str) -> OnboardingApprovalActionResponseDto:
    """결재 현황 요약과 메시지를 OnboardingApprovalActionResponseDto로 래핑한다."""
    return OnboardingApprovalActionResponseDto(
        data=statusDto(summary, None),
        message=message,
    )


def itemDto(summary: dict, userModel) -> OnboardingApprovalItemDto:
    """결재 현황 요약을 목록 항목 DTO로 변환하면서 본인 제출 여부를 설정한다."""
    payload = dict(summary)
    payload.pop("selfSubmittedYn", None)
    return OnboardingApprovalItemDto(
        **payload,
        selfSubmittedYn=checkSelfSubmitted(summary, userModel),
    )


def statusDto(summary: dict, userModel) -> OnboardingApprovalStatusDataDto:
    """결재 현황 요약을 상태 DTO로 변환하면서 롤업 준비 여부와 본인 제출 여부를 계산해 설정한다."""
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
    """상태 DTO에 원자 지표별 입력 상세 항목을 추가해 상세 DTO를 생성한다."""
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


def checkApprover(userModel) -> None:
    """승인 권한이 없으면 PermissionError를 발생시킨다."""
    if isApprover(userModel):
        return
    raise PermissionError("Only ESG담당자 or 관리자 can approve/reject onboarding inputs")


def checkReviewer(userModel) -> None:
    """검토 권한이 없으면 PermissionError를 발생시킨다."""
    from src.services.onboardings.service import isReviewer
    if isReviewer(userModel):
        return
    raise PermissionError("Only consultants, ESG담당자, or 관리자 can review onboarding inputs")


def isApprover(userModel) -> bool:
    """사용자가 ADMIN 또는 ESG 담당자 역할(승인 권한)인지 여부를 반환한다."""
    from src.services.onboardings.service import APPROVER_ROLES, APPROVER_ROLE_NAMES, readUserField
    role = str(readUserField(userModel, "role") or "").strip().upper()
    roleName = str(readUserField(userModel, "role_name") or "").strip()
    return role in APPROVER_ROLES or roleName in APPROVER_ROLE_NAMES


def checkSelfSubmitted(summary: dict, userModel) -> bool:
    """현재 사용자가 해당 지표를 직접 제출한 사람인지 여부를 반환한다."""
    from src.services.onboardings.service import getActorUserId
    actorUserId = getActorUserId(userModel)
    inputUserId = summary.get("inputUserId")
    return actorUserId is not None and inputUserId is not None and int(actorUserId) == int(inputUserId)


__all__ = [
    "approveApproval",
    "getApprovalDetail",
    "getApprovalStatus",
    "listApprovals",
    "rejectApproval",
    "reviewApproval",
    "submitApproval",
]
