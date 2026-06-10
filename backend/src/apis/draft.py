from datetime import datetime, timedelta
from fastapi import APIRouter

from src.utils.db import findAll, findOne, save, saveMany
from src.models.draft import DraftSaveRequestDto

router = APIRouter()



def _now_kst() -> str:
    return (datetime.now() + timedelta(hours=9)).isoformat(timespec="seconds")


# ──────────────────────────────────────────────────────────────
# GET /draft/metrics  — KPI Fact + Rollup 지표 rows
# ──────────────────────────────────────────────────────────────
@router.get("/metrics", summary="보고서 초안 지표 조회")
async def get_draft_metrics(companyId: int, year: int):
    sql = """
        SELECT f.atomic_metric_id AS metricId,
               f.value_numeric    AS valueNumeric,
               f.value_text       AS valueText,
               f.unit
        FROM ESG_KPI_FACT f
        WHERE f.company_id = ?
          AND f.reporting_year = ?
          AND f.delete_yn = 0
    """
    rows = findAll(sql, (companyId, year))
    existing_ids = {r["metricId"] for r in rows}

    rollup_sql = """
        SELECT group_atomic_metric_id AS metricId,
               value_numeric          AS valueNumeric,
               value_text             AS valueText,
               unit
        FROM ESG_GROUP_ROLLUP_RESULT
        WHERE parent_company_id = ?
          AND reporting_year = ?
          AND delete_yn = 0
    """
    for r in findAll(rollup_sql, (companyId, year)):
        if r["metricId"] not in existing_ids:
            rows.append(r)

    return {"success": True, "data": rows}


# ──────────────────────────────────────────────────────────────
# GET /draft/section  — AI 생성 서브이슈 본문 (최신 run)
# ──────────────────────────────────────────────────────────────
@router.get("/section", summary="AI 생성 서브이슈 본문 조회")
async def get_draft_section(companyId: int, year: int, subIssueId: str):
    sql = """
        SELECT s.report_text
        FROM ESG_REPORT_AI_SECTION s
        JOIN ESG_REPORT_AI_RUN r ON s.ai_run_id = r.id
        WHERE r.company_id = ?
          AND r.reporting_year = ?
          AND s.sub_issue_id = ?
        ORDER BY r.created_at DESC
        LIMIT 1
    """
    row = findOne(sql, (companyId, year, subIssueId))
    return {"success": True, "data": row}


# ──────────────────────────────────────────────────────────────
# POST /draft/save  — 편집값 행 단위 upsert
# ──────────────────────────────────────────────────────────────
@router.post("/save", summary="보고서 초안 편집값 저장")
async def save_draft(req: DraftSaveRequestDto):
    now = _now_kst()

    # ── 지표 편집값: (company, year, page_key, atomic_metric_id) 단위 upsert ──
    if req.metrics:
        metric_sql = """
            INSERT INTO ESG_REPORT_DRAFT_METRIC
                (company_id, reporting_year, page_key, atomic_metric_id, display_value, saved_at, delete_yn)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            ON DUPLICATE KEY UPDATE
                display_value = VALUES(display_value),
                saved_at      = VALUES(saved_at),
                delete_yn     = 0
        """
        metric_rows = [
            (req.companyId, req.year, page_key, metric_id, display_val, now)
            for page_key, metrics in req.metrics.items()
            for metric_id, display_val in metrics.items()
        ]
        if metric_rows:
            saveMany(metric_sql, metric_rows)

    # ── 본문 편집값: (company, year, page_key) 단위 upsert ──
    if req.narrative:
        narrative_sql = """
            INSERT INTO ESG_REPORT_DRAFT_NARRATIVE
                (company_id, reporting_year, page_key, narrative_text, saved_at, delete_yn)
            VALUES (?, ?, ?, ?, ?, 0)
            ON DUPLICATE KEY UPDATE
                narrative_text = VALUES(narrative_text),
                saved_at       = VALUES(saved_at),
                delete_yn      = 0
        """
        narrative_rows = [
            (req.companyId, req.year, page_key, text, now)
            for page_key, text in req.narrative.items()
        ]
        if narrative_rows:
            saveMany(narrative_sql, narrative_rows)

    return {"success": True, "savedAt": now}


# ──────────────────────────────────────────────────────────────
# GET /draft/load  — 저장된 편집값 전체 조회 → 프론트 구조로 재조립
# ──────────────────────────────────────────────────────────────
@router.get("/load", summary="보고서 초안 편집값 불러오기")
async def load_draft(companyId: int, year: int):
    metric_sql = """
        SELECT page_key, atomic_metric_id, display_value, saved_at
        FROM ESG_REPORT_DRAFT_METRIC
        WHERE company_id = ?
          AND reporting_year = ?
          AND delete_yn = 0
    """
    narrative_sql = """
        SELECT page_key, narrative_text, saved_at
        FROM ESG_REPORT_DRAFT_NARRATIVE
        WHERE company_id = ?
          AND reporting_year = ?
          AND delete_yn = 0
    """

    metric_rows    = findAll(metric_sql, (companyId, year))
    narrative_rows = findAll(narrative_sql, (companyId, year))

    if not metric_rows and not narrative_rows:
        return {"success": False, "data": None}

    # { pageKey: { metricId: displayValue } }
    metrics: dict = {}
    latest_at = None
    for r in metric_rows:
        pk = r["page_key"]
        metrics.setdefault(pk, {})[r["atomic_metric_id"]] = r["display_value"] or ""
        if r.get("saved_at"):
            t = str(r["saved_at"])
            if latest_at is None or t > latest_at:
                latest_at = t

    # { pageKey: narrativeText }
    narrative: dict = {}
    for r in narrative_rows:
        narrative[r["page_key"]] = r["narrative_text"] or ""
        if r.get("saved_at"):
            t = str(r["saved_at"])
            if latest_at is None or t > latest_at:
                latest_at = t

    return {
        "success": True,
        "data": {
            "metrics":   metrics,
            "narrative": narrative,
            "savedAt":   latest_at,
        },
    }
