"""
reportworkflowrepository.py
레이어: Repository
역할: ESG_MATERIALITY_RUN 보고서 워크플로우 상태 조회·갱신 — G0/DMA 재무 기준 준비도 판별.

주요 함수:
  getCurrent     — 현재 활성 run 조회
  getRun         — runId 기준 run 단건 조회
  createRun      — 새 run 생성
  updateRunBasis — 보고 기준 업데이트
  getBasisStatus — G0-02 재무 기준 준비 상태 반환
  getRollupBatch — 롤업 배치 단건 조회
"""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from src.utils.db import addKey, findAll, findOne, save
from src.repositories.financialbasisrepository import checkBasisReady


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


# 기업·연도 기준 현재 활성 materiality run 조회
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


# runId 기준 materiality run 단건 조회
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


# 기업별 연도별 최신 run 목록 조회
def listProjects(companyId: int) -> list[dict]:
    sql = """
        SELECT
            r.id,
            r.company_id,
            r.reporting_year,
            r.report_basis_type,
            r.financial_basis_status,
            r.required_rollup_batch_id,
            r.run_status
        FROM ESG_MATERIALITY_RUN r
        INNER JOIN (
            SELECT
                reporting_year,
                MAX(id) AS latest_id
            FROM ESG_MATERIALITY_RUN
            WHERE company_id = ?
              AND delete_yn = 0
              AND UPPER(COALESCE(run_status, 'ACTIVE')) NOT IN (
                  'DELETED',
                  'CANCELLED',
                  'CANCELED'
              )
            GROUP BY reporting_year
        ) latest
          ON latest.latest_id = r.id
        WHERE r.company_id = ?
          AND r.delete_yn = 0
        ORDER BY
            r.reporting_year DESC,
            r.id DESC
    """
    return findAll(sql, (companyId, companyId)) or []


# 새 materiality run 생성 후 저장된 행 반환
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


# run의 보고 기준(단독/연결) 업데이트 — PROTECTED 상태면 차단
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


# G0-02 재무 기준 준비 상태 및 다음 액션(nextAction) 반환
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


# rollupBatchId 기준 롤업 배치 단건 조회
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


# 기준 상태 응답 dict 구성 헬퍼
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


# 보고 기준 타입 정규화 — ENTITY / CONSOLIDATED 외 None 반환
def normalizeReportBasisType(value) -> Optional[str]:
    normalizedValue = str(value or "").strip().upper()
    if normalizedValue in {"ENTITY", "CONSOLIDATED"}:
        return normalizedValue
    return None


__all__ = [
    "getCurrent",
    "getRun",
    "listProjects",
    "createRun",
    "updateRunBasis",
    "getBasisStatus",
    "getRollupBatch",
    "checkBasisReady",
]
