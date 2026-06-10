from datetime import datetime, timedelta
from fastapi import APIRouter, Depends

from src.utils.db import findAll, findOne, saveMany
from src.utils.auth import get_token
from src.models.draft import DraftSaveRequestDto

router = APIRouter()


def _nowKst() -> str:
    return (datetime.now() + timedelta(hours=9)).isoformat(timespec="seconds")


def _lookupSection(companyId: int, year: int, subIssueId: str) -> dict:
    """최신 AI run 기준 (aiRunId, sectionId) 조회. 없으면 빈 dict."""
    sql = """
        SELECT r.ai_run_id  AS aiRunId,
               s.section_id AS sectionId
        FROM ESG_REPORT_AI_SECTION s
        JOIN ESG_REPORT_AI_RUN r ON s.ai_run_id = r.ai_run_id
        WHERE r.company_id     = ?
          AND r.reporting_year = ?
          AND s.sub_issue_id   = ?
        ORDER BY r.created_at DESC
        LIMIT 1
    """
    return findOne(sql, (companyId, year, subIssueId)) or {}


# ──────────────────────────────────────────────────────────────
# GET /draft/metrics  — KPI Fact + Rollup 지표 rows
# ──────────────────────────────────────────────────────────────
@router.get("/metrics", summary="보고서 초안 지표 조회")
async def getDraftMetrics(companyId: int, year: int, userModel=Depends(get_token)):
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
    rows = findAll(sql, (companyId, year))
    existingIds = {r["metricId"] for r in rows}

    rollupSql = """
        SELECT group_atomic_metric_id AS metricId,
               value_numeric          AS valueNumeric,
               value_text             AS valueText,
               unit
        FROM ESG_GROUP_ROLLUP_RESULT
        WHERE parent_company_id = ?
          AND reporting_year    = ?
          AND delete_yn         = 0
    """
    for r in findAll(rollupSql, (companyId, year)):
        if r["metricId"] not in existingIds:
            rows.append(r)

    return {"success": True, "data": rows}


# ──────────────────────────────────────────────────────────────
# GET /draft/section  — AI 생성 서브이슈 본문 (최신 run)
# ──────────────────────────────────────────────────────────────
@router.get("/section", summary="AI 생성 서브이슈 본문 조회")
async def getDraftSection(companyId: int, year: int, subIssueId: str, userModel=Depends(get_token)):
    sql = """
        SELECT s.report_text AS reportText
        FROM ESG_REPORT_AI_SECTION s
        JOIN ESG_REPORT_AI_RUN r ON s.ai_run_id = r.ai_run_id
        WHERE r.company_id     = ?
          AND r.reporting_year = ?
          AND s.sub_issue_id   = ?
        ORDER BY r.created_at DESC
        LIMIT 1
    """
    row = findOne(sql, (companyId, year, subIssueId))
    return {"success": True, "data": row}


# ──────────────────────────────────────────────────────────────
# POST /draft/save  — 편집값 행 단위 upsert
# ──────────────────────────────────────────────────────────────
@router.post("/save", summary="보고서 초안 편집값 저장")
async def saveDraft(req: DraftSaveRequestDto, userModel=Depends(get_token)):
    now = _nowKst()

    # ── 지표 편집값 upsert ──
    if req.metrics:
        metricSql = """
            INSERT INTO ESG_REPORT_DRAFT_METRIC
                (company_id, reporting_year, page_key, atomic_metric_id, display_value, saved_at, delete_yn)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            ON DUPLICATE KEY UPDATE
                display_value = VALUES(display_value),
                saved_at      = VALUES(saved_at),
                delete_yn     = 0
        """
        metricRows = [
            (req.companyId, req.year, pageKey, metricId, displayVal, now)
            for pageKey, metrics in req.metrics.items()
            for metricId, displayVal in metrics.items()
        ]
        if metricRows:
            saveMany(metricSql, metricRows)

    # ── 본문 편집값 upsert (section_id / ai_run_id auto-lookup) ──
    if req.narrative:
        narrativeSql = """
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
        narrativeRows = []
        for pageKey, text in req.narrative.items():
            subIssueId = req.pageSubIssueMap.get(pageKey)
            ref = _lookupSection(req.companyId, req.year, subIssueId) if subIssueId else {}
            narrativeRows.append((
                req.companyId, req.year, pageKey,
                ref.get("aiRunId"),
                ref.get("sectionId"),
                text, now,
            ))
        if narrativeRows:
            saveMany(narrativeSql, narrativeRows)

    return {"success": True, "savedAt": now}


# ──────────────────────────────────────────────────────────────
# GET /draft/load  — 저장된 편집값 전체 조회 → 프론트 구조로 재조립
# ──────────────────────────────────────────────────────────────
@router.get("/load", summary="보고서 초안 편집값 불러오기")
async def loadDraft(companyId: int, year: int, userModel=Depends(get_token)):
    metricSql = """
        SELECT page_key         AS pageKey,
               atomic_metric_id AS metricId,
               display_value    AS displayValue,
               saved_at         AS savedAt
        FROM ESG_REPORT_DRAFT_METRIC
        WHERE company_id     = ?
          AND reporting_year = ?
          AND delete_yn      = 0
    """
    narrativeSql = """
        SELECT page_key       AS pageKey,
               narrative_text AS narrativeText,
               saved_at       AS savedAt
        FROM ESG_REPORT_DRAFT_NARRATIVE
        WHERE company_id     = ?
          AND reporting_year = ?
          AND delete_yn      = 0
    """

    metricRows    = findAll(metricSql, (companyId, year))
    narrativeRows = findAll(narrativeSql, (companyId, year))

    if not metricRows and not narrativeRows:
        return {"success": False, "data": None}

    # { pageKey: { metricId: displayValue } }
    metrics: dict = {}
    latestAt = None
    for r in metricRows:
        metrics.setdefault(r["pageKey"], {})[r["metricId"]] = r["displayValue"] or ""
        if r.get("savedAt"):
            t = str(r["savedAt"])
            if latestAt is None or t > latestAt:
                latestAt = t

    # { pageKey: narrativeText }
    narrative: dict = {}
    for r in narrativeRows:
        narrative[r["pageKey"]] = r["narrativeText"] or ""
        if r.get("savedAt"):
            t = str(r["savedAt"])
            if latestAt is None or t > latestAt:
                latestAt = t

    return {
        "success": True,
        "data": {"metrics": metrics, "narrative": narrative, "savedAt": latestAt},
    }
