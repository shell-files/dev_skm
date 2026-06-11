from datetime import datetime, timedelta

from src.models.draft import DraftSaveRequestDto
from src.utils.draftrepository import (
    getKpiMetricRows,
    getRollupMetricRows,
    getAiSectionRow,
    getAiMetricTraceRows,
    lookupAiRunSection,
    saveDraftMetricRows,
    saveDraftNarrativeRows,
    getDraftMetricRows,
    getDraftNarrativeRows,
)


def _nowKst() -> str:
    return (datetime.now() + timedelta(hours=9)).isoformat(timespec="seconds")


def fetchDraftMetrics(companyId: int, year: int, token) -> dict:
    rows = getKpiMetricRows(companyId, year)
    existingIds = {r["metricId"] for r in rows}
    for r in getRollupMetricRows(companyId, year):
        if r["metricId"] not in existingIds:
            rows.append(r)
    return {"success": True, "data": rows}


def fetchDraftSection(companyId: int, year: int, subIssueId: str, token) -> dict:
    row = getAiSectionRow(companyId, year, subIssueId)
    if not row:
        return {"success": True, "data": None}
    traces = getAiMetricTraceRows(row["sectionId"])
    metricIds = [t["metricId"] for t in traces] if traces else []
    return {"success": True, "data": {"reportText": row["reportText"], "metricIds": metricIds}}


def saveDraft(req: DraftSaveRequestDto, token) -> dict:
    now = _nowKst()

    if req.metrics:
        metricRows = [
            (req.companyId, req.year, pageKey, metricId, displayVal, now)
            for pageKey, metrics in req.metrics.items()
            for metricId, displayVal in metrics.items()
        ]
        if metricRows:
            saveDraftMetricRows(metricRows)

    if req.narrative:
        narrativeRows = []
        for pageKey, text in req.narrative.items():
            subIssueId = req.pageSubIssueMap.get(pageKey)
            ref = lookupAiRunSection(req.companyId, req.year, subIssueId) if subIssueId else {}
            narrativeRows.append((
                req.companyId, req.year, pageKey,
                ref.get("aiRunId"),
                ref.get("sectionId"),
                text, now,
            ))
        if narrativeRows:
            saveDraftNarrativeRows(narrativeRows)

    return {"success": True, "savedAt": now}


def loadDraft(companyId: int, year: int, token) -> dict:
    metricRows = getDraftMetricRows(companyId, year)
    narrativeRows = getDraftNarrativeRows(companyId, year)

    if not metricRows and not narrativeRows:
        return {"success": False, "data": None}

    metrics: dict = {}
    latestAt = None
    for r in metricRows:
        metrics.setdefault(r["pageKey"], {})[r["metricId"]] = r["displayValue"] or ""
        if r.get("savedAt"):
            t = str(r["savedAt"])
            if latestAt is None or t > latestAt:
                latestAt = t

    narrative: dict = {}
    for r in narrativeRows:
        narrative[r["pageKey"]] = r["narrativeText"] or ""
        if r.get("savedAt"):
            t = str(r["savedAt"])
            if latestAt is None or t > latestAt:
                latestAt = t

    return {"success": True, "data": {"metrics": metrics, "narrative": narrative, "savedAt": latestAt}}
