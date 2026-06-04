from typing import Optional
from src.utils.db import findAll, findOne, getConn

# Enums
ROLLUP_PURPOSE_DMA_PRECHECK = "DMA_PRECHECK"
METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
REPORT_SCOPE_CONSOLIDATED = "CONSOLIDATED"
BATCH_STATUS_PENDING = "pending"
BATCH_STATUS_COMPLETED = "completed"
SOURCE_STATUS_RECEIVED = "received"
SOURCE_STATUS_REQUESTED = "requested"
SOURCE_STATUS_SENT = "sent"
INPUT_STATUS_APPROVED = "approved"
INPUT_STATUS_SUBMITTED = "submitted"
INPUT_STATUS_NOT_STARTED = "not_started"
APPROVAL_STATUS_APPROVED = "approved"
APPROVAL_STATUS_SUBMITTED = "submitted"
APPROVAL_STATUS_PENDING = "pending"
TRANSFER_STATUS_RECEIVED = "received"
TRANSFER_STATUS_SENT = "sent"
TRANSFER_STATUS_NOT_SENT = "not_sent"

# Explicit re-exports from new repositories
from src.utils.rollupscoperepository import (
    listEffectiveSourceCompanies,
    listBatchRules,
    listBatchRuleSources,
    resolveRequiredSourceAtomicIds,
    resolveRequiredGroupAtomicIds,
    saveScopeFromRulesTx,
    listScope,
    listApprovedFactsByCompany,
    listPriorYearApprovedFactsByCompany,
    buildSourceReadiness,
)

from src.utils.rollupbatchrepository import (
    getActiveBatch,
    listRequests,
    getBatch,
    getSource,
    listSources,
    listSourceCompanyIds,
    saveBatchTx,
    saveSourcesTx,
    updateSourceStatusTx,
    updateSourceSentTx,
    finalizeDmaPrecheckTx,
    finalizeReportDisclosureTx,
    getStatus,
    listPendingSources,
    checkTransferReady,
    upsertGroupRollupResultsTx,
    buildBatchCode,
    buildResultCode,
)

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

def getScopeCompanyColumn() -> str:
    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'ESG_COMPANY_ROLLUP_SCOPE'
          AND column_name IN (
              'source_company_id',
              'subsidiary_company_id',
              'child_company_id',
              'company_id'
          )
        ORDER BY CASE column_name
            WHEN 'source_company_id' THEN 1
            WHEN 'subsidiary_company_id' THEN 2
            WHEN 'child_company_id' THEN 3
            WHEN 'company_id' THEN 4
            ELSE 5
        END
        LIMIT 1
    """
    row = findOne(sql) or {}
    columnName = row.get("column_name")
    if columnName in {"source_company_id", "subsidiary_company_id", "child_company_id", "company_id"}:
        return columnName
    return "source_company_id"

def listSubsidiaries(run: dict) -> list[dict]:
    companyColumn = getScopeCompanyColumn()
    companyId = int(run["company_id"])
    reportingYear = int(run["reporting_year"])
    sql = f"""
        SELECT DISTINCT
            s.{companyColumn} AS companyId,
            p.company_code AS companyCode,
            COALESCE(p.company_code, CAST(s.{companyColumn} AS CHAR)) AS companyName
        FROM ESG_COMPANY_ROLLUP_SCOPE s
        LEFT JOIN ESG_COMPANY_PROFILE p
          ON p.company_id = s.{companyColumn}
         AND p.delete_yn = 0
        WHERE s.parent_company_id = ?
          AND s.rollup_include_yn = 1
          AND s.delete_yn = 0
          AND (s.effective_from_year IS NULL OR s.effective_from_year <= ?)
          AND (s.effective_to_year IS NULL OR s.effective_to_year >= ?)
          AND s.{companyColumn} <> ?
        ORDER BY companyName, companyId
    """
    rows = findAll(sql, (companyId, reportingYear, reportingYear, companyId)) or []
    return [
        {
            "companyId": int(row["companyId"]),
            "companyCode": row.get("companyCode"),
            "companyName": row.get("companyName") or row.get("companyCode"),
        }
        for row in rows
    ]

__all__ = [
    "ROLLUP_PURPOSE_DMA_PRECHECK",
    "METRIC_SCOPE_G0_02_FINANCIAL_BASIS",
    "REPORT_SCOPE_CONSOLIDATED",
    "BATCH_STATUS_PENDING",
    "BATCH_STATUS_COMPLETED",
    "SOURCE_STATUS_RECEIVED",
    "SOURCE_STATUS_REQUESTED",
    "SOURCE_STATUS_SENT",
    "INPUT_STATUS_APPROVED",
    "INPUT_STATUS_SUBMITTED",
    "INPUT_STATUS_NOT_STARTED",
    "APPROVAL_STATUS_APPROVED",
    "APPROVAL_STATUS_SUBMITTED",
    "APPROVAL_STATUS_PENDING",
    "TRANSFER_STATUS_RECEIVED",
    "TRANSFER_STATUS_SENT",
    "TRANSFER_STATUS_NOT_SENT",
    "getRun",
    "getScopeCompanyColumn",
    "listSubsidiaries",
    "listEffectiveSourceCompanies",
    "listBatchRules",
    "listBatchRuleSources",
    "resolveRequiredSourceAtomicIds",
    "resolveRequiredGroupAtomicIds",
    "saveScopeFromRulesTx",
    "listScope",
    "listApprovedFactsByCompany",
    "listPriorYearApprovedFactsByCompany",
    "buildSourceReadiness",
    "getActiveBatch",
    "listRequests",
    "getBatch",
    "getSource",
    "listSources",
    "listSourceCompanyIds",
    "saveBatchTx",
    "saveSourcesTx",
    "updateSourceStatusTx",
    "updateSourceSentTx",
    "finalizeDmaPrecheckTx",
    "finalizeReportDisclosureTx",
    "getStatus",
    "listPendingSources",
    "checkTransferReady",
    "upsertGroupRollupResultsTx",
    "buildBatchCode",
    "buildResultCode",
    "getConn",
]
