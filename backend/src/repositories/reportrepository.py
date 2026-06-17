from src.utils.db import findAll, findOne


def getLatestReportRunByMaterialityRun(runId: int) -> dict:
    sql = """
        SELECT id, company_id, reporting_year, report_status, source_materiality_run_id
        FROM ESG_REPORT_RUN
        WHERE source_materiality_run_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
    """
    return findOne(sql, (runId,)) or {}


def getReportDraftRows(reportRunId: int) -> list:
    sql = """
        SELECT
            id,
            report_run_id,
            section_code,
            sub_issue_code,
            owner_metric_id,
            generated_text,
            qa_status,
            approval_status,
            reviewer_comment,
            updated_at
        FROM ESG_REPORT_SECTION_DRAFT
        WHERE report_run_id = ?
          AND delete_yn = 0
        ORDER BY id ASC
    """
    return findAll(sql, (reportRunId,)) or []


def getReferencesForDraftIds(draftIds: list[int]) -> list:
    if not draftIds:
        return []
    placeholders = ",".join(["?"] * len(draftIds))
    sql = f"""
        SELECT
            id,
            report_section_draft_id,
            reference_type,
            reference_id,
            atomic_metric_id,
            trace_label_json
        FROM ESG_REPORT_REFERENCE
        WHERE report_section_draft_id IN ({placeholders})
          AND delete_yn = 0
        ORDER BY id ASC
    """
    return findAll(sql, tuple(draftIds)) or []


def getReferencesForParagraph(paragraphId: int) -> list:
    sql = """
        SELECT
            id,
            report_section_draft_id,
            reference_type,
            reference_id,
            atomic_metric_id,
            trace_label_json
        FROM ESG_REPORT_REFERENCE
        WHERE report_section_draft_id = ?
          AND delete_yn = 0
        ORDER BY id ASC
    """
    return findAll(sql, (paragraphId,)) or []


def getDraftById(draftId: int) -> dict:
    sql = """
        SELECT id, report_run_id, section_code, sub_issue_code, generated_text, qa_status, approval_status, updated_at
        FROM ESG_REPORT_SECTION_DRAFT
        WHERE id = ?
          AND delete_yn = 0
    """
    return findOne(sql, (draftId,)) or {}


def getAtomicMetricRows(atomicMetricIds: list[str]) -> list:
    if not atomicMetricIds:
        return []
    placeholders = ",".join(["?"] * len(atomicMetricIds))
    sql = f"""
        SELECT
            metric_id,
            metric_name_kr,
            atomic_metric_id,
            atomic_name_kr,
            unit,
            data_value_type,
            calculation_formula,
            calculation_rule_code
        FROM ESG_ATOMIC_METRIC_MASTER
        WHERE atomic_metric_id IN ({placeholders})
          AND delete_yn = 0
    """
    return findAll(sql, tuple(atomicMetricIds)) or []


def getKpiFactById(factId: int) -> dict:
    sql = """
        SELECT
            id,
            company_id,
            reporting_year,
            metric_id,
            atomic_metric_id,
            value_numeric,
            value_text,
            unit,
            approval_status
        FROM ESG_KPI_FACT
        WHERE id = ?
          AND delete_yn = 0
    """
    return findOne(sql, (factId,)) or {}


def getKpiFactsByCompanyAtomic(companyId: int, atomicMetricId: str) -> list:
    sql = """
        SELECT
            reporting_year,
            value_numeric,
            value_text,
            unit,
            approval_status
        FROM ESG_KPI_FACT
        WHERE company_id = ?
          AND atomic_metric_id = ?
          AND delete_yn = 0
        ORDER BY reporting_year ASC
    """
    return findAll(sql, (companyId, atomicMetricId)) or []


def getRollupResultById(rollupResultId: int) -> dict:
    sql = """
        SELECT
            id,
            reporting_year,
            parent_company_id,
            group_metric_id,
            group_atomic_metric_id,
            group_atomic_name,
            value_numeric,
            value_text,
            unit,
            source_company_values_json,
            rollup_method,
            calculation_trace,
            rollup_status
        FROM ESG_GROUP_ROLLUP_RESULT
        WHERE id = ?
          AND delete_yn = 0
    """
    return findOne(sql, (rollupResultId,)) or {}


def getRollupResultsByParentAtomic(parentCompanyId: int, atomicMetricId: str) -> list:
    sql = """
        SELECT
            reporting_year,
            value_numeric,
            value_text,
            unit,
            rollup_status
        FROM ESG_GROUP_ROLLUP_RESULT
        WHERE parent_company_id = ?
          AND group_atomic_metric_id = ?
          AND delete_yn = 0
        ORDER BY reporting_year ASC
    """
    return findAll(sql, (parentCompanyId, atomicMetricId)) or []


def getCalculationRuleByAtomicMetric(atomicMetricId: str) -> dict:
    sql = """
        SELECT calculation_rule_code, calculation_formula_label
        FROM ESG_CALCULATION_RULE
        WHERE target_atomic_metric_id = ?
          AND delete_yn = 0
        ORDER BY execution_order ASC
        LIMIT 1
    """
    return findOne(sql, (atomicMetricId,)) or {}
