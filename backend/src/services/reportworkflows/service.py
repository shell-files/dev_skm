"""
service.py
레이어: Service (reportworkflows)
역할: 보고서 워크플로우 Step A 오케스트레이션 — 현재 상태 조회, 시작·재개, G0 승인 사이클 관리.

주요 함수:
  getCurrent / getRun              — 현재 상태 및 실행 정보 조회
  startWorkflow / resumeWorkflow   — 워크플로우 시작·재개
  getG0Status / listProjects       — G0 상태 조회 및 프로젝트 목록
  resolveWorkflow / resolveNextAction / resolveProjectStageLabel — 상태 판별 헬퍼
"""

from __future__ import annotations

from src.models.reportworkflow import (
    ReportWorkflowPostDmaScopeDataDto,
    ReportWorkflowPostDmaScopeResponseDto,
    ReportWorkflowProjectItemDto,
    ReportWorkflowProjectListDataDto,
    ReportWorkflowProjectListResponseDto,
    ReportWorkflowResponseDto,
    ReportWorkflowStartRequestDto,
    ReportWorkflowStatusDto,
)


PROTECTED_START_STATUSES = {
    "ENTITY_READY",
    "CONSOLIDATED_ROLLUP_PENDING",
    "CONSOLIDATED_READY",
    "DMA_RUNNING",
    "DMA_COMPLETED",
}
POST_DMA_READ_ONLY_RUN_STATUSES = {
    "COMPLETED",
    "ARCHIVED",
    "DELETED",
    "CANCELLED",
    "CANCELED",
}


def getCurrent(companyId: int, reportingYear: int) -> ReportWorkflowResponseDto:
    """회사·연도 기준 현재 활성 워크플로우 상태를 조회해 반환하며, 없으면 NO_RUN 상태를 반환한다."""
    reportWorkflowRepository = loadRepository()
    run = reportWorkflowRepository.getCurrent(companyId, reportingYear)
    if not run:
        return ReportWorkflowResponseDto(
            data=ReportWorkflowStatusDto(
                runId=None,
                companyId=companyId,
                reportingYear=reportingYear,
                reportBasisType=None,
                workflowStep="NO_RUN",
                readyYn=False,
                basisStatus="NO_RUN",
                basisRequirementStatus="NOT_STARTED",
                nextAction="SELECT_REPORT_BASIS",
                message="No active report workflow exists.",
            )
        )
    return buildStatusResponse(run)


def startWorkflow(
    request: ReportWorkflowStartRequestDto,
    actorUserId: int | None = None,
) -> ReportWorkflowResponseDto:
    """보고 기준을 설정해 워크플로우를 시작하거나, 기존 워크플로우의 기준을 갱신한다."""
    reportWorkflowRepository = loadRepository()
    run = reportWorkflowRepository.getCurrent(
        request.companyId,
        request.reportingYear,
    )
    if run:
        currentBasisStatus = reportWorkflowRepository.getBasisStatus(run)
        if currentBasisStatus.get("basisStatus") in PROTECTED_START_STATUSES:
            ensurePreDmaG0CycleForRun(run, actorUserId)
            return ReportWorkflowResponseDto(data=buildStatusDto(run, currentBasisStatus))
        run = reportWorkflowRepository.updateRunBasis(
            int(run["id"]),
            request.reportBasisType,
        )
        if run.get("_basisOverwriteBlockedYn"):
            ensurePreDmaG0CycleForRun(run, actorUserId)
            return buildStatusResponse(run)
    else:
        run = reportWorkflowRepository.createRun(
            request.companyId,
            request.reportingYear,
            request.reportBasisType,
        )

    if not run:
        raise RuntimeError("Failed to start report workflow")

    ensurePreDmaG0CycleForRun(run, actorUserId)

    basisStatus = {
        "readyYn": False,
        "basisStatus": "BASIS_SELECTED",
        "basisRequirementStatus": "PENDING",
        "nextAction": "OPEN_G0_ONBOARDING",
        "message": "Report basis selected. Continue with G0 onboarding.",
    }
    return ReportWorkflowResponseDto(data=buildStatusDto(run, basisStatus))


def getG0Status(runId: int) -> ReportWorkflowResponseDto:
    """runId로 G0 온보딩 기준 워크플로우 현재 상태를 조회해 반환한다."""
    reportWorkflowRepository = loadRepository()
    run = reportWorkflowRepository.getRun(runId)
    if not run:
        raise ValueError(f"No ESG_MATERIALITY_RUN found for runId={runId}")
    return buildStatusResponse(run)


def resumeWorkflow(
    runId: int,
    actorUserId: int | None = None,
) -> ReportWorkflowResponseDto:
    """중단된 워크플로우를 재개하고 PRE-DMA G0 사이클이 존재하는지 보장한다."""
    reportWorkflowRepository = loadRepository()
    run = reportWorkflowRepository.getRun(runId)
    if not run:
        raise ValueError(f"No ESG_MATERIALITY_RUN found for runId={runId}")

    ensurePreDmaG0CycleForRun(run, actorUserId)
    return buildStatusResponse(run)


def initializePostDmaDisclosureScope(
    runId: int,
    actorUserId: int | None = None,
) -> ReportWorkflowPostDmaScopeResponseDto:
    """DMA 선정 확정 후 POST_DMA_DISCLOSURE 사이클과 공시 지표 scope를 idempotent하게 초기화한다."""
    reportWorkflowRepository = loadRepository()
    run = reportWorkflowRepository.getRun(runId)
    if not run:
        raise ValueError(f"No ESG_MATERIALITY_RUN found for runId={runId}")

    runStatus = str(run.get("run_status") or "ACTIVE").strip().upper()
    if runStatus in POST_DMA_READ_ONLY_RUN_STATUSES:
        raise ValueError(
            "POST_DMA_DISCLOSURE_RUN_READ_ONLY: "
            f"runId={runId}, runStatus={runStatus}"
        )

    result = ensureWorkflowPostDmaDisclosureCycle(run, actorUserId)
    return ReportWorkflowPostDmaScopeResponseDto(
        data=ReportWorkflowPostDmaScopeDataDto(
            runId=int(run["id"]),
            companyId=int(run["company_id"]),
            reportingYear=int(run["reporting_year"]),
            sourceMaterialityRunId=int(result["cycle"].get("source_materiality_run_id") or run["id"]),
            cycleId=int(result["cycle"]["id"]),
            cycleType=result["cycle"].get("cycle_type") or "POST_DMA_DISCLOSURE",
            metricScopeCode=result["cycle"].get("metric_scope_code") or "SELECTED_DISCLOSURE",
            selectedSubIssueCount=int(result.get("selectedSubIssueCount") or 0),
            scopeMetricCount=int(result.get("scopeMetricCount") or 0),
            metricIds=list(result.get("metricIds") or []),
            cycleCreatedYn=bool(result.get("cycleCreatedYn")),
            cycleReusedYn=bool(result.get("cycleReusedYn")),
            message="POST_DMA_DISCLOSURE scope initialized.",
        )
    )


def getRun(runId: int) -> dict:
    """runId에 해당하는 ESG_MATERIALITY_RUN 행을 반환한다."""
    reportWorkflowRepository = loadRepository()
    return reportWorkflowRepository.getRun(runId)


def listProjects(companyId: int) -> ReportWorkflowProjectListResponseDto:
    """회사의 전체 보고 프로젝트 목록과 각 프로젝트의 현재 단계 레이블을 반환한다."""
    reportWorkflowRepository = loadRepository()
    items = []
    for run in reportWorkflowRepository.listProjects(companyId):
        runStatus = str(run.get("run_status") or "ACTIVE").strip().upper()
        readOnlyYn = runStatus in {"COMPLETED", "ARCHIVED"}
        if readOnlyYn:
            workflowStep = runStatus
            currentStageLabel = (
                "All approvals completed"
                if runStatus == "COMPLETED"
                else "Archived"
            )
        else:
            basisStatus = reportWorkflowRepository.getBasisStatus(run)
            workflowStep = resolveWorkflow(basisStatus.get("basisStatus"))
            currentStageLabel = resolveProjectStageLabel(run, basisStatus)

        items.append(
            ReportWorkflowProjectItemDto(
                runId=int(run["id"]),
                companyId=int(run["company_id"]),
                reportingYear=int(run["reporting_year"]),
                reportBasisType=normalizeReportBasisType(
                    run.get("report_basis_type")
                ),
                runStatus=runStatus,
                workflowStep=workflowStep,
                currentStageLabel=currentStageLabel,
                pendingCount=countPendingPreDmaG0Approvals(
                    int(run["company_id"]),
                    int(run["reporting_year"]),
                ),
                readOnlyYn=readOnlyYn,
            )
        )
    return ReportWorkflowProjectListResponseDto(
        data=ReportWorkflowProjectListDataDto(items=items)
    )


def buildStatusResponse(run: dict) -> ReportWorkflowResponseDto:
    """run 행으로 기준 상태를 조회해 표준 워크플로우 응답 DTO를 생성한다."""
    reportWorkflowRepository = loadRepository()
    basisStatus = reportWorkflowRepository.getBasisStatus(run)
    return ReportWorkflowResponseDto(data=buildStatusDto(run, basisStatus))


def _resolvePostDmaState(run: dict) -> tuple:
    """
    DB를 조회하여 DMA 선정/POST_DMA 온보딩 상태를 반환한다.
    반환: (selectionSource, fallbackYn, selectedSubIssueCount, postDmaCycleId, postDmaScopeMetricCount, currentCycleType)
    예외 발생 시 안전한 기본값(PRE_DMA_G0)을 반환한다.
    """
    try:
        from src.repositories.dmarepository import listSelectedSubIssues
        from src.repositories.onboardingscoperepository import getCycle, listMetricScopes

        runId = int(run["id"])
        companyId = int(run["company_id"])
        reportingYear = int(run["reporting_year"])

        selectedRows = listSelectedSubIssues(runId)
        selectedSubIssueCount = len(selectedRows)

        selectionSource = "TABLE" if selectedSubIssueCount > 0 else None
        fallbackYn = False if selectedSubIssueCount > 0 else None

        postDmaCycle = getCycle(
            companyId,
            reportingYear,
            "POST_DMA_DISCLOSURE",
            sourceMaterialityRunId=runId,
        )
        postDmaCycleId = int(postDmaCycle["id"]) if postDmaCycle.get("id") is not None else None

        postDmaScopeMetricCount = 0
        if postDmaCycleId:
            scopeRows = listMetricScopes(postDmaCycleId, companyId)
            postDmaScopeMetricCount = len(scopeRows)

        currentCycleType = None
        if (
            selectionSource == "TABLE"
            and not fallbackYn
            and selectedSubIssueCount >= 5
            and postDmaCycleId is not None
            and postDmaScopeMetricCount > 0
        ):
            currentCycleType = "POST_DMA_DISCLOSURE"

        return selectionSource, fallbackYn, selectedSubIssueCount, postDmaCycleId, postDmaScopeMetricCount, currentCycleType

    except Exception:
        return None, None, 0, None, 0, None


def buildStatusDto(run: dict, basisStatus: dict) -> ReportWorkflowStatusDto:
    """run과 기준 상태 dict를 결합해 POST-DMA 상태까지 포함한 상세 워크플로우 상태 DTO를 생성한다."""
    reportBasisType = normalizeReportBasisType(run.get("report_basis_type"))
    runId = int(run["id"]) if run.get("id") is not None else None

    selectionSource, fallbackYn, selectedSubIssueCount, postDmaCycleId, postDmaScopeMetricCount, currentCycleType = (
        _resolvePostDmaState(run) if runId else (None, None, 0, None, 0, None)
    )

    return ReportWorkflowStatusDto(
        runId=runId,
        companyId=int(run["company_id"]),
        reportingYear=int(run["reporting_year"]),
        reportBasisType=reportBasisType,
        workflowStep=resolveWorkflow(basisStatus.get("basisStatus")),
        readyYn=bool(basisStatus.get("readyYn")),
        basisStatus=basisStatus.get("basisStatus") or "BASIS_SELECTED",
        basisRequirementStatus=basisStatus.get("basisRequirementStatus") or "PENDING",
        nextAction=resolveNextAction(
            basisStatus.get("basisStatus"),
            basisStatus.get("nextAction"),
        ),
        message=basisStatus.get("message") or "OK",
        selectionSource=selectionSource,
        fallbackYn=fallbackYn,
        selectedSubIssueCount=selectedSubIssueCount,
        postDmaCycleId=postDmaCycleId,
        postDmaScopeMetricCount=postDmaScopeMetricCount,
        currentCycleType=currentCycleType,
    )


def resolveWorkflow(basisStatus: str) -> str:
    """basisStatus 값을 워크플로우 단계 레이블(NO_RUN·REPORT_BASIS·G0_ONBOARDING·DMA_READY)로 변환한다."""
    if basisStatus == "NO_RUN":
        return "NO_RUN"
    if basisStatus == "BASIS_NOT_SELECTED":
        return "REPORT_BASIS"
    if basisStatus in {"ENTITY_READY", "CONSOLIDATED_READY"}:
        return "DMA_READY"
    return "G0_ONBOARDING"


def resolveNextAction(basisStatus: str, fallbackAction: str | None = None) -> str:
    """basisStatus를 프론트엔드 nextAction 문자열로 매핑하며, 알 수 없는 상태는 fallback 액션을 반환한다."""
    nextActionMap = {
        "NO_RUN": "SELECT_REPORT_BASIS",
        "BASIS_NOT_SELECTED": "SELECT_REPORT_BASIS",
        "BASIS_SELECTED": "OPEN_G0_ONBOARDING",
        "ENTITY_NO_BASIS": "OPEN_G0_ONBOARDING",
        "ENTITY_READY": "START_DMA",
        "CONSOLIDATED_ROLLUP_REQUIRED": "REQUEST_ROLLUP",
        "CONSOLIDATED_ROLLUP_PENDING": "WAIT_ROLLUP",
        "CONSOLIDATED_READY": "START_DMA",
    }
    return nextActionMap.get(basisStatus) or fallbackAction or "OPEN_G0_ONBOARDING"


def resolveProjectStageLabel(run: dict, basisStatus: dict | None = None) -> str:
    """프로젝트 목록 UI에 표시할 현재 단계 한 줄 레이블을 결정한다."""
    runStatus = str(run.get("run_status") or "").strip().upper()
    if runStatus == "COMPLETED":
        return "All approvals completed"
    if runStatus == "ARCHIVED":
        return "Archived"

    basisStatusValue = str((basisStatus or {}).get("basisStatus") or "").strip().upper()
    if basisStatusValue == "CONSOLIDATED_ROLLUP_REQUIRED":
        return "Rollup request required"
    if basisStatusValue == "CONSOLIDATED_ROLLUP_PENDING":
        return "Rollup in progress"
    if basisStatusValue in {"ENTITY_READY", "CONSOLIDATED_READY"}:
        return "DMA ready"
    return "G0 approval"


def countPendingPreDmaG0Approvals(companyId: int, reportingYear: int) -> int:
    """PRE_DMA_G0 사이클에서 미승인 항목 수를 반환하며, 오류 발생 시 0을 반환한다."""
    try:
        from src.repositories import onboardingrepository

        rows = onboardingrepository.listCycleApprovalInboxRows(
            companyId=companyId,
            reportingYear=reportingYear,
            cycleType="PRE_DMA_G0",
            assignedOnlyYn=True,
        )
        return sum(
            1
            for row in rows
            if str(row.get("approvalStatus") or "").strip().upper() != "APPROVED"
        )
    except Exception:
        return 0


def normalizeReportBasisType(value):
    """보고 기준 타입을 ENTITY·CONSOLIDATED 중 하나로 정규화하며, 유효하지 않으면 None을 반환한다."""
    normalizedValue = str(value or "").strip().upper()
    if normalizedValue in {"ENTITY", "CONSOLIDATED"}:
        return normalizedValue
    return None


def ensurePreDmaG0CycleForRun(run: dict, actorUserId: int | None = None) -> None:
    """onboardings 서비스로 PRE_DMA_G0 사이클 생성을 위임하는 진입점."""
    from src.services.onboardings.service import ensureWorkflowPreDmaG0Cycle

    ensureWorkflowPreDmaG0Cycle(run, actorUserId)


def ensureWorkflowPostDmaDisclosureCycle(run: dict, actorUserId: int | None = None) -> dict:
    """onboardings 서비스로 POST_DMA_DISCLOSURE 사이클 생성을 위임하는 진입점."""
    from src.services.onboardings.service import ensureWorkflowPostDmaDisclosureCycle as ensurePostDmaCycle

    return ensurePostDmaCycle(run, actorUserId)


def loadRepository():
    """순환 참조 방지를 위해 reportworkflowrepository를 지연 임포트해 반환한다."""
    from src.repositories import reportworkflowrepository

    return reportworkflowrepository


__all__ = [
    "getCurrent",
    "startWorkflow",
    "resumeWorkflow",
    "initializePostDmaDisclosureScope",
    "getG0Status",
    "getRun",
    "listProjects",
    "resolveWorkflow",
    "resolveNextAction",
    "resolveProjectStageLabel",
]
