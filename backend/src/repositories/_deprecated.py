# 이 파일의 함수들은 사용처가 없거나 계층 위반으로 분리된 코드입니다.
# 안정성 확인 후 일괄 제거 예정.

from typing import Optional

from src.repositories.onboardingscoperepository import (
    CYCLE_TYPE_PRE_DMA_G0,
    METRIC_ID_G0_02,
)


# --- onboardingapprovalrepository에서 이동 ---
# Repository → Service 순환 의존성 위반.
# approval_service에 동일한 원본 함수가 존재하므로 이 wrapper들은 불필요.

def submitG002Approval(companyId: int, reportingYear: int, reportBasisType=None, sourceMaterialityRunId=None, actorUserId=None) -> dict:
    from src.services.onboardings.approvalService import submitMetricApproval

    return submitMetricApproval(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleType=CYCLE_TYPE_PRE_DMA_G0,
        metricId=METRIC_ID_G0_02,
        actorUserId=actorUserId,
        commentText=None,
        reportBasisType=reportBasisType,
        sourceMaterialityRunId=sourceMaterialityRunId,
    )


def approveG002Approval(companyId: int, reportingYear: int, actorUserId: Optional[int], commentText: Optional[str] = None) -> dict:
    from src.services.onboardings.approvalService import approveMetricApproval

    return approveMetricApproval(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleType=CYCLE_TYPE_PRE_DMA_G0,
        metricId=METRIC_ID_G0_02,
        actorUserId=actorUserId,
        commentText=commentText,
    )


def rejectG002Approval(companyId: int, reportingYear: int, actorUserId: Optional[int], commentText: str) -> dict:
    from src.services.onboardings.approvalService import rejectMetricApproval

    return rejectMetricApproval(
        companyId=companyId,
        reportingYear=reportingYear,
        cycleType=CYCLE_TYPE_PRE_DMA_G0,
        metricId=METRIC_ID_G0_02,
        actorUserId=actorUserId,
        commentText=commentText,
    )
