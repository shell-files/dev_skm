"""
draftrepository.py
레이어: Repository
역할: ESG 보고서 초안 KPI 데이터 조회 및 저장.
"""
from src.utils.db import findAll, findOne, saveMany, save


# 기업·연도 기준 KPI Fact 지표 행 조회
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


# 기업·연도 기준 롤업 결과 지표 행 조회
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


# 기업·연도·이슈 기준 최신 AI 섹션 데이터 단건 조회
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


# sectionId 기준 AI 메트릭 추적 행 조회
def getAiMetricTraceRows(sectionId: int) -> list:
    sql = """
        SELECT atomic_metric_id AS metricId
        FROM ESG_REPORT_AI_METRIC_TRACE
        WHERE section_id = ?
    """
    return findAll(sql, (sectionId,))


# 최신 AI run 기준 aiRunId·sectionId 조회 — 없으면 빈 dict
def lookupAiRunSection(companyId: int, year: int, subIssueId: str) -> dict:
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


# 보고서 초안 지표 행 upsert 저장
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


# 보고서 초안 서술 행 upsert 저장
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


# 기업·연도 기준 저장된 초안 지표 행 조회
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


# 기업·연도 기준 저장된 초안 서술 행 조회
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


# 기업·연도의 초안 지표·서술 행 소프트 삭제
def deleteDraftRows(companyId: int, year: int):
    save("UPDATE ESG_REPORT_DRAFT_METRIC SET delete_yn=1 WHERE company_id=? AND reporting_year=?", (companyId, year))
    save("UPDATE ESG_REPORT_DRAFT_NARRATIVE SET delete_yn=1 WHERE company_id=? AND reporting_year=?", (companyId, year))


# 지표 연도별 추이 조회 — KPI_FACT 우선, 없으면 ROLLUP 폴백; (rows, isRollup) 반환
def getMetricTrendRows(companyId: int, metricId: str, baseYear: int) -> tuple:
    sql_kpi = """
        SELECT reporting_year AS year,
               value_numeric  AS valueNumeric,
               value_text     AS valueText,
               unit
        FROM ESG_KPI_FACT
        WHERE company_id       = ?
          AND atomic_metric_id = ?
          AND reporting_year  <= ?
          AND delete_yn        = 0
        ORDER BY reporting_year ASC
    """
    rows = findAll(sql_kpi, (companyId, metricId, baseYear))
    if rows:
        return rows, False
    sql_rollup = """
        SELECT reporting_year        AS year,
               value_numeric         AS valueNumeric,
               value_text            AS valueText,
               unit
        FROM ESG_GROUP_ROLLUP_RESULT
        WHERE parent_company_id      = ?
          AND group_atomic_metric_id = ?
          AND reporting_year        <= ?
          AND delete_yn              = 0
        ORDER BY reporting_year ASC
    """
    return findAll(sql_rollup, (companyId, metricId, baseYear)), True


# baseYear 이하 최근 롤업 결과 1건 조회 — sourceValues·trace·unit 포함
def getRollupDetailRow(parentCompanyId: int, metricId: str, year: int) -> dict:
    sql = """
        SELECT source_company_values_json AS sourceValuesJson,
               calculation_trace          AS calculationTrace,
               unit,
               reporting_year             AS year
        FROM ESG_GROUP_ROLLUP_RESULT
        WHERE parent_company_id      = ?
          AND group_atomic_metric_id = ?
          AND reporting_year        <= ?
          AND delete_yn              = 0
        ORDER BY reporting_year DESC, id DESC
        LIMIT 1
    """
    return findOne(sql, (parentCompanyId, metricId, year))


# company_id 목록 → {companyId: companyName} 맵 조회
def getCompanyNamesByIds(companyIds: list) -> dict:
    if not companyIds:
        return {}
    placeholders = ",".join("?" * len(companyIds))
    sql = f"""
        SELECT company_id AS companyId,
               COALESCE(company_code, CAST(company_id AS CHAR)) AS companyName
        FROM ESG_COMPANY_PROFILE
        WHERE company_id IN ({placeholders})
          AND delete_yn = 0
    """
    rows = findAll(sql, tuple(companyIds))
    return {int(r["companyId"]): r["companyName"] for r in rows}


# RECALCULATE fallback: 소스 지표 롤업 결과 일괄 조회 — 최신 연도 우선
def getSourceMetricRollupRows(parentCompanyId: int, metricIds: list, year: int) -> list:
    if not metricIds:
        return []
    placeholders = ",".join("?" * len(metricIds))
    sql = f"""
        SELECT group_atomic_metric_id AS metricId,
               source_company_values_json AS sourceValuesJson,
               unit,
               reporting_year AS year
        FROM ESG_GROUP_ROLLUP_RESULT
        WHERE parent_company_id      = ?
          AND group_atomic_metric_id IN ({placeholders})
          AND reporting_year        <= ?
          AND delete_yn              = 0
        ORDER BY reporting_year DESC, id DESC
    """
    return findAll(sql, (parentCompanyId, *metricIds, year))
