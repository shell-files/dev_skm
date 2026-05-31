"""
Domain: Report Workflow
Layer: utils/repository
Responsibility:
- Read and update ESG_MATERIALITY_RUN report workflow state
- Resolve G0/DMA basis readiness for Step A API responses
- Read rollup batch DMA readiness without calculating rollup results
Public functions:
- getCurrent
- getRun
- createRun
- updateRunBasis
- getBasisStatus
- getRollupBatch
Do not:
- do not mutate auth/token/common code
- do not calculate rollup batches
- do not call benchmark/media pipelines
- do not change DB schema or scoring formulas
"""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from src.utils.db import addKey, findOne, save
from src.utils.dmafinancialrepository import checkBasisReady


BASIS_SELECTED_STATUS = "BASIS_SELECTED"
ACTIVE_RUN_STATUS = "active"
ROLLUP_PURPOSE_DMA_PRECHECK = "DMA_PRECHECK"
METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
MUTABLE_BASIS_STATUSES = {"", "BASIS_SELECTED", "BASIS_NOT_SELECTED"}
PROTECTED_BASIS_STATUSES = {
    "ENTITY_READY",
    "CONSOLIDATED_ROLLUP_PENDING",
    "CONSOLIDATED_READY",
    "DMA_RUNNING",
    "DMA_COMPLETED",
}


def getCurrent(companyId: int, reportingYear: int) -> dict:
    sql = """
        SELECT
            id,
            company_id,
            reporting_year,
            report_basis_type,
            financial_basis_status,
            required_rollup_batch_id,
            run_status
        FROM ESG_MATERIALITY_RUN
        WHERE company_id = ?
          AND reporting_year = ?
          AND delete_yn = 0
          AND UPPER(COALESCE(run_status, 'ACTIVE')) NOT IN (
              'DELETED',
              'CANCELLED',
              'CANCELED',
              'ARCHIVED',
              'COMPLETED'
          )
        ORDER BY id DESC
        LIMIT 1
    """
    return findOne(sql, (companyId, reportingYear)) or {}


def getRun(runId: int) -> dict:
    sql = """
        SELECT
            id,
            company_id,
            reporting_year,
            report_basis_type,
            financial_basis_status,
            required_rollup_batch_id,
            run_status
        FROM ESG_MATERIALITY_RUN
        WHERE id = ?
          AND delete_yn = 0
    """
    return findOne(sql, (runId,)) or {}


def createRun(companyId: int, reportingYear: int, reportBasisType: str) -> dict:
    runName = (
        f"REPORT_WORKFLOW_"
        f"{companyId}_"
        f"{reportingYear}_"
        f"{reportBasisType}_"
        f"{uuid4().hex[:8]}"
    )

    result = addKey(
        """
        INSERT INTO ESG_MATERIALITY_RUN (
            company_id,
            reporting_year,
            run_name,
            report_basis_type,
            financial_basis_status,
            run_status
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            companyId,
            reportingYear,
            runName,
            reportBasisType,
            BASIS_SELECTED_STATUS,
            ACTIVE_RUN_STATUS,
        ),
    )
    if not result or not result[0]:
        return {}
    return getRun(int(result[1]))


def updateRunBasis(runId: int, reportBasisType: str) -> dict:
    currentRun = getRun(runId)
    if not currentRun:
        return {}

    currentBasisStatus = str(currentRun.get("financial_basis_status") or "").strip().upper()
    currentBasisType = normalizeReportBasisType(currentRun.get("report_basis_type"))
    if currentBasisStatus in PROTECTED_BASIS_STATUSES:
        currentRun["_basisOverwriteBlockedYn"] = True
        return currentRun
    if currentBasisType and currentBasisStatus not in MUTABLE_BASIS_STATUSES:
        currentRun["_basisOverwriteBlockedYn"] = True
        return currentRun

    save(
        """
        UPDATE ESG_MATERIALITY_RUN
        SET report_basis_type = ?,
            financial_basis_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND delete_yn = 0
        """,
        (reportBasisType, BASIS_SELECTED_STATUS, runId),
    )
    return getRun(runId)


def getBasisStatus(run: dict) -> dict:
    reportBasisType = normalizeReportBasisType(run.get("report_basis_type"))
    if not reportBasisType:
        return {
            "readyYn": False,
            "basisStatus": "BASIS_NOT_SELECTED",
            "basisRequirementStatus": "BLOCKED",
            "nextAction": "SELECT_REPORT_BASIS",
            "message": "보고서 기준을 먼저 선택해야 합니다.",
            "basisReady": {},
        }

    companyId = int(run["company_id"])
    reportingYear = int(run["reporting_year"])
    requiredRollupBatchId = run.get("required_rollup_batch_id")

    if reportBasisType == "ENTITY":
        basisReady = checkBasisReady(companyId, reportingYear, reportBasisType)
        if basisReady.get("readyYn"):
            return buildBasisStatus(
                readyYn=True,
                basisStatus="ENTITY_READY",
                basisRequirementStatus="PASSED",
                nextAction="START_DMA",
                message="독립기준 G0-02 승인이 완료되었습니다.",
                basisReady=basisReady,
            )
        return buildBasisStatus(
            readyYn=False,
            basisStatus="ENTITY_NO_BASIS",
            basisRequirementStatus="BLOCKED",
            nextAction="OPEN_G0_ONBOARDING",
            message="독립기준 DMA를 위해 G0-02 승인 입력이 필요합니다.",
            basisReady=basisReady,
        )

    if not requiredRollupBatchId:
        return buildBasisStatus(
            readyYn=False,
            basisStatus="CONSOLIDATED_ROLLUP_REQUIRED",
            basisRequirementStatus="BLOCKED",
            nextAction="REQUEST_ROLLUP",
            message="연결기준 DMA를 위해 G0-02 롤업 승인이 필요합니다.",
            basisReady={},
        )

    rollupBatch = getRollupBatch(int(requiredRollupBatchId))
    if rollupBatch and (
        int(rollupBatch.get("parent_company_id") or 0) != companyId
        or int(rollupBatch.get("reporting_year") or 0) != reportingYear
        or str(rollupBatch.get("rollup_purpose_code") or "").upper() != ROLLUP_PURPOSE_DMA_PRECHECK
        or str(rollupBatch.get("metric_scope_code") or "").upper() != METRIC_SCOPE_G0_02_FINANCIAL_BASIS
    ):
        rollupBatch = {}
    basisReady = checkBasisReady(
        companyId,
        reportingYear,
        reportBasisType,
        requiredRollupBatchId,
    )
    if not rollupBatch:
        return buildBasisStatus(
            readyYn=False,
            basisStatus="CONSOLIDATED_ROLLUP_REQUIRED",
            basisRequirementStatus="BLOCKED",
            nextAction="REQUEST_ROLLUP",
            message="연결기준 DMA를 위해 G0-02 롤업 승인이 필요합니다.",
            basisReady=basisReady,
        )

    if not bool(rollupBatch.get("dma_ready_yn")):
        return buildBasisStatus(
            readyYn=False,
            basisStatus="CONSOLIDATED_ROLLUP_PENDING",
            basisRequirementStatus="PENDING",
            nextAction="WAIT_ROLLUP",
            message="G0-02 롤업 처리가 진행 중입니다.",
            basisReady=basisReady,
        )

    if basisReady.get("readyYn"):
        return buildBasisStatus(
            readyYn=True,
            basisStatus="CONSOLIDATED_READY",
            basisRequirementStatus="PASSED",
            nextAction="START_DMA",
            message="연결기준 G0-02 롤업 승인이 완료되었습니다.",
            basisReady=basisReady,
        )

    return buildBasisStatus(
        readyYn=False,
        basisStatus="CONSOLIDATED_ROLLUP_REQUIRED",
        basisRequirementStatus="BLOCKED",
        nextAction="REQUEST_ROLLUP",
        message="연결기준 DMA를 위해 G0-02 롤업 승인이 필요합니다.",
        basisReady=basisReady,
    )


def getRollupBatch(rollupBatchId: int) -> dict:
    sql = """
        SELECT
            id,
            parent_company_id,
            reporting_year,
            rollup_purpose_code,
            metric_scope_code,
            dma_ready_yn,
            batch_status
        FROM ESG_ROLLUP_BATCH
        WHERE id = ?
          AND delete_yn = 0
    """
    return findOne(sql, (rollupBatchId,)) or {}


def buildBasisStatus(
    readyYn: bool,
    basisStatus: str,
    basisRequirementStatus: str,
    nextAction: str,
    message: str,
    basisReady: Optional[dict] = None,
) -> dict:
    return {
        "readyYn": readyYn,
        "basisStatus": basisStatus,
        "basisRequirementStatus": basisRequirementStatus,
        "nextAction": nextAction,
        "message": message,
        "basisReady": basisReady or {},
    }


def normalizeReportBasisType(value) -> Optional[str]:
    normalizedValue = str(value or "").strip().upper()
    if normalizedValue in {"ENTITY", "CONSOLIDATED"}:
        return normalizedValue
    return None


__all__ = [
    "getCurrent",
    "getRun",
    "createRun",
    "updateRunBasis",
    "getBasisStatus",
    "getRollupBatch",
    "checkBasisReady",
]
