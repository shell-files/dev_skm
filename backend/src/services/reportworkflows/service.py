"""
Domain: Report Workflow
Layer: services
Responsibility:
- Orchestrate report workflow Step A API behavior
- Resolve current workflow status and next action from repository state
- Preserve existing progressing run basis selections
- Ensure PRE_DMA_G0 approval cycle exists after workflow start or resume
Public functions:
- getCurrent
- startWorkflow
- resumeWorkflow
- getG0Status
- getRun
- listProjects
- resolveWorkflow
- resolveNextAction
- resolveProjectStageLabel
Do not:
- do not create G0 input values or approval decisions
- do not create or calculate rollup batches
- do not call benchmark/media pipelines
- do not connect applyRunExposure
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
    reportWorkflowRepository = loadRepository()
    run = reportWorkflowRepository.getRun(runId)
    if not run:
        raise ValueError(f"No ESG_MATERIALITY_RUN found for runId={runId}")
    return buildStatusResponse(run)


def resumeWorkflow(
    runId: int,
    actorUserId: int | None = None,
) -> ReportWorkflowResponseDto:
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
    reportWorkflowRepository = loadRepository()
    return reportWorkflowRepository.getRun(runId)


def listProjects(companyId: int) -> ReportWorkflowProjectListResponseDto:
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
        from src.utils.dmarepository import listSelectedSubIssues
        from src.utils.onboardingscoperepository import getCycle, listMetricScopes

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
    if basisStatus == "NO_RUN":
        return "NO_RUN"
    if basisStatus == "BASIS_NOT_SELECTED":
        return "REPORT_BASIS"
    if basisStatus in {"ENTITY_READY", "CONSOLIDATED_READY"}:
        return "DMA_READY"
    return "G0_ONBOARDING"


def resolveNextAction(basisStatus: str, fallbackAction: str | None = None) -> str:
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
    try:
        from src.utils import onboardingrepository

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
    normalizedValue = str(value or "").strip().upper()
    if normalizedValue in {"ENTITY", "CONSOLIDATED"}:
        return normalizedValue
    return None


def ensurePreDmaG0CycleForRun(run: dict, actorUserId: int | None = None) -> None:
    from src.services.onboardings.service import ensureWorkflowPreDmaG0Cycle

    ensureWorkflowPreDmaG0Cycle(run, actorUserId)


def ensureWorkflowPostDmaDisclosureCycle(run: dict, actorUserId: int | None = None) -> dict:
    from src.services.onboardings.service import ensureWorkflowPostDmaDisclosureCycle as ensurePostDmaCycle

    return ensurePostDmaCycle(run, actorUserId)


def loadRepository():
    from src.utils import reportworkflowrepository

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
