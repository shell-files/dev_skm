"""
Domain: Report Workflow
Layer: services
Responsibility:
- Orchestrate report workflow Step A API behavior
- Resolve current workflow status and next action from repository state
- Preserve existing progressing run basis selections
Public functions:
- getCurrent
- startWorkflow
- getG0Status
- getRun
- resolveWorkflow
- resolveNextAction
Do not:
- do not create G0 input or approval data
- do not create or calculate rollup batches
- do not call benchmark/media pipelines
- do not connect applyRunExposure
"""

from __future__ import annotations

from src.models.reportworkflow import (
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
                companyRole=reportWorkflowRepository.resolveCompanyRole(companyId, reportingYear),
                requiredRollupBatchId=None,
                workflowStep="NO_RUN",
                readyYn=False,
                basisStatus="NO_RUN",
                basisRequirementStatus="NOT_STARTED",
                nextAction="SELECT_REPORT_BASIS",
                message="활성화된 DMA 실행이 없습니다.",
            )
        )
    return buildStatusResponse(run)


def startWorkflow(request: ReportWorkflowStartRequestDto) -> ReportWorkflowResponseDto:
    reportWorkflowRepository = loadRepository()
    run = reportWorkflowRepository.getCurrent(request.companyId, request.reportingYear)
    if run:
        currentBasisStatus = reportWorkflowRepository.getBasisStatus(run)
        if currentBasisStatus.get("basisStatus") in PROTECTED_START_STATUSES:
            return ReportWorkflowResponseDto(data=buildStatusDto(run, currentBasisStatus))
        run = reportWorkflowRepository.updateRunBasis(int(run["id"]), request.reportBasisType)
        if run.get("_basisOverwriteBlockedYn"):
            return buildStatusResponse(run)
    else:
        run = reportWorkflowRepository.createRun(
            request.companyId,
            request.reportingYear,
            request.reportBasisType,
        )

    if not run:
        raise RuntimeError("Failed to start report workflow")

    basisStatus = {
        "readyYn": False,
        "basisStatus": "BASIS_SELECTED",
        "basisRequirementStatus": "PENDING",
        "nextAction": "OPEN_G0_ONBOARDING",
        "message": "보고서 기준이 선택되었습니다. G0 온보딩 상태를 확인하세요.",
    }
    return ReportWorkflowResponseDto(data=buildStatusDto(run, basisStatus))


def getG0Status(runId: int) -> ReportWorkflowResponseDto:
    reportWorkflowRepository = loadRepository()
    run = reportWorkflowRepository.getRun(runId)
    if not run:
        raise ValueError(f"No ESG_MATERIALITY_RUN found for runId={runId}")
    return buildStatusResponse(run)


def getRun(runId: int) -> dict:
    reportWorkflowRepository = loadRepository()
    return reportWorkflowRepository.getRun(runId)


def buildStatusResponse(run: dict) -> ReportWorkflowResponseDto:
    reportWorkflowRepository = loadRepository()
    basisStatus = reportWorkflowRepository.getBasisStatus(run)
    return ReportWorkflowResponseDto(data=buildStatusDto(run, basisStatus))


def buildStatusDto(run: dict, basisStatus: dict) -> ReportWorkflowStatusDto:
    reportBasisType = normalizeReportBasisType(run.get("report_basis_type"))
    reportWorkflowRepository = loadRepository()
    return ReportWorkflowStatusDto(
        runId=int(run["id"]) if run.get("id") is not None else None,
        companyId=int(run["company_id"]),
        reportingYear=int(run["reporting_year"]),
        reportBasisType=reportBasisType,
        companyRole=reportWorkflowRepository.resolveCompanyRole(
            int(run["company_id"]),
            int(run["reporting_year"]),
        ),
        requiredRollupBatchId=(
            int(run["required_rollup_batch_id"])
            if run.get("required_rollup_batch_id") is not None
            else None
        ),
        workflowStep=resolveWorkflow(basisStatus.get("basisStatus")),
        readyYn=bool(basisStatus.get("readyYn")),
        basisStatus=basisStatus.get("basisStatus") or "BASIS_SELECTED",
        basisRequirementStatus=basisStatus.get("basisRequirementStatus") or "PENDING",
        nextAction=resolveNextAction(basisStatus.get("basisStatus"), basisStatus.get("nextAction")),
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


def normalizeReportBasisType(value):
    normalizedValue = str(value or "").strip().upper()
    if normalizedValue in {"ENTITY", "CONSOLIDATED"}:
        return normalizedValue
    return None


def loadRepository():
    from src.utils import reportworkflowrepository

    return reportworkflowrepository


__all__ = [
    "getCurrent",
    "startWorkflow",
    "getG0Status",
    "getRun",
    "resolveWorkflow",
    "resolveNextAction",
]
