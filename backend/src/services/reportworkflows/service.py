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


def buildStatusDto(run: dict, basisStatus: dict) -> ReportWorkflowStatusDto:
    reportBasisType = normalizeReportBasisType(run.get("report_basis_type"))
    return ReportWorkflowStatusDto(
        runId=int(run["id"]) if run.get("id") is not None else None,
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


def loadRepository():
    from src.utils import reportworkflowrepository

    return reportworkflowrepository


__all__ = [
    "getCurrent",
    "startWorkflow",
    "resumeWorkflow",
    "getG0Status",
    "getRun",
    "listProjects",
    "resolveWorkflow",
    "resolveNextAction",
    "resolveProjectStageLabel",
]
