from src.utils.db import findAll, findOne, saveMany


def getKpiMetricRows(companyId: int, year: int) -> list:
    sql = """
        SELECT f.atomic_metric_id AS metricId,
               f.value_numeric    AS valueNumeric,
               f.value_text       AS valueText,
               f.unit
        FROM ESG_KPI_FACT f
        WHERE f.company_id     = ?
          AND f.reporting_year = ?
          AND f.delete_yn      = 0
    """
    return findAll(sql, (companyId, year))


def getRollupMetricRows(companyId: int, year: int) -> list:
    sql = """
        SELECT group_atomic_metric_id AS metricId,
               value_numeric          AS valueNumeric,
               value_text             AS valueText,
               unit
        FROM ESG_GROUP_ROLLUP_RESULT
        WHERE parent_company_id = ?
          AND reporting_year    = ?
          AND delete_yn         = 0
    """
    return findAll(sql, (companyId, year))


def getAiSectionRow(companyId: int, year: int, subIssueId: str) -> dict:
    sql = """
        SELECT s.section_id  AS sectionId,
               s.report_text AS reportText
        FROM ESG_REPORT_AI_SECTION s
        JOIN ESG_REPORT_AI_RUN r ON s.ai_run_id = r.ai_run_id
        WHERE r.company_id     = ?
          AND r.reporting_year = ?
          AND s.sub_issue_code = ?
        ORDER BY r.created_at DESC
        LIMIT 1
    """
    return findOne(sql, (companyId, year, subIssueId))


def getAiMetricTraceRows(sectionId: int) -> list:
    sql = """
        SELECT atomic_metric_id AS metricId
        FROM ESG_REPORT_AI_METRIC_TRACE
        WHERE section_id = ?
    """
    return findAll(sql, (sectionId,))


def lookupAiRunSection(companyId: int, year: int, subIssueId: str) -> dict:
    """최신 AI run 기준 (aiRunId, sectionId) 조회. 없으면 빈 dict."""
    sql = """
        SELECT r.ai_run_id  AS aiRunId,
               s.section_id AS sectionId
        FROM ESG_REPORT_AI_SECTION s
        JOIN ESG_REPORT_AI_RUN r ON s.ai_run_id = r.ai_run_id
        WHERE r.company_id     = ?
          AND r.reporting_year = ?
          AND s.sub_issue_code = ?
        ORDER BY r.created_at DESC
        LIMIT 1
    """
    return findOne(sql, (companyId, year, subIssueId)) or {}


def saveDraftMetricRows(rows: list):
    sql = """
        INSERT INTO ESG_REPORT_DRAFT_METRIC
            (company_id, reporting_year, page_key, atomic_metric_id, display_value, saved_at, delete_yn)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        ON DUPLICATE KEY UPDATE
            display_value = VALUES(display_value),
            saved_at      = VALUES(saved_at),
            delete_yn     = 0
    """
    saveMany(sql, rows)


def saveDraftNarrativeRows(rows: list):
    sql = """
        INSERT INTO ESG_REPORT_DRAFT_NARRATIVE
            (company_id, reporting_year, page_key, ai_run_id, section_id, narrative_text, saved_at, delete_yn)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ON DUPLICATE KEY UPDATE
            ai_run_id      = VALUES(ai_run_id),
            section_id     = VALUES(section_id),
            narrative_text = VALUES(narrative_text),
            saved_at       = VALUES(saved_at),
            delete_yn      = 0
    """
    saveMany(sql, rows)


def getDraftMetricRows(companyId: int, year: int) -> list:
    sql = """
        SELECT page_key         AS pageKey,
               atomic_metric_id AS metricId,
               display_value    AS displayValue,
               saved_at         AS savedAt
        FROM ESG_REPORT_DRAFT_METRIC
        WHERE company_id     = ?
          AND reporting_year = ?
          AND delete_yn      = 0
    """
    return findAll(sql, (companyId, year))


def getDraftNarrativeRows(companyId: int, year: int) -> list:
    sql = """
        SELECT page_key       AS pageKey,
               narrative_text AS narrativeText,
               saved_at       AS savedAt
        FROM ESG_REPORT_DRAFT_NARRATIVE
        WHERE company_id     = ?
          AND reporting_year = ?
          AND delete_yn      = 0
    """
    return findAll(sql, (companyId, year))
