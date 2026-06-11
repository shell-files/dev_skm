import json as json_mod
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
    deleteDraftRows,
    getMetricTrendRows,
    getRollupSourceValuesRow,
    getCompanyNamesByIds,
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


def resetDraft(companyId: int, year: int, token) -> dict:
    deleteDraftRows(companyId, year)
    return {"success": True}


def _buildBreakdown(sourceValuesJson: str, unit: str) -> list:
    """source_company_values_json → [{l, v, contributionRate}] 리스트 변환."""
    if not sourceValuesJson:
        return []
    try:
        parsed = json_mod.loads(sourceValuesJson)
    except Exception:
        return []

    company_val_map = {}
    if isinstance(parsed, dict) and parsed:
        first_val = next(iter(parsed.values()))
        if isinstance(first_val, (int, float)):
            # 단순 {companyId: value} 형식
            for cid_str, val in parsed.items():
                try:
                    company_val_map[int(cid_str)] = float(val)
                except (ValueError, TypeError):
                    pass
        elif isinstance(first_val, dict):
            # 중첩 {atomicId: {companyId: value}} 형식 — 첫 번째 atomic만 사용
            first_atomic_vals = first_val
            for cid_str, val in first_atomic_vals.items():
                try:
                    v = float(val) if isinstance(val, (int, float)) else None
                    if v is not None:
                        company_val_map[int(cid_str)] = v
                except (ValueError, TypeError):
                    pass

    if not company_val_map:
        return []

    company_names = getCompanyNamesByIds(list(company_val_map.keys()))
    is_krw = (unit or "").upper() == "KRW"
    total = sum(company_val_map.values())

    result = []
    for cid, val in sorted(company_val_map.items()):
        cname = company_names.get(cid) or str(cid)
        if is_krw:
            uk = val / 100_000_000
            uk_r = round(uk * 10) / 10
            display_v = f"{int(uk_r):,} 억 원" if uk_r % 1 == 0 else f"{uk_r:,} 억 원"
        else:
            display_v = f"{int(val):,}{(' ' + unit) if unit else ''}" if val % 1 == 0 else f"{val:,.1f}{(' ' + unit) if unit else ''}"
        contrib = round((val / total) * 100, 1) if total > 0 else None
        result.append({"l": cname, "v": display_v, "contributionRate": contrib})

    return result


def fetchMetricTrend(companyId: int, year: int, metricId: str, token) -> dict:
    rows, isRollup = getMetricTrendRows(companyId, metricId, year)
    if not rows:
        return {"success": True, "data": {"trend": [], "unit": None, "isRollup": False, "breakdown": []}}
    unit = None
    trend = []
    for r in rows:
        v = r.get("valueNumeric")
        if v is not None:
            try:
                v = float(v)
            except (TypeError, ValueError):
                v = None
        if v is None and r.get("valueText"):
            try:
                v = float(str(r["valueText"]).replace(",", ""))
            except (TypeError, ValueError):
                pass
        trend.append({"year": str(r["year"]), "value": v})
        if r.get("unit") and not unit:
            unit = r["unit"]

    breakdown = []
    if isRollup:
        rollupRow = getRollupSourceValuesRow(companyId, metricId, year)
        if rollupRow:
            breakdown = _buildBreakdown(rollupRow.get("sourceValuesJson"), unit)

    return {"success": True, "data": {"trend": trend, "unit": unit, "isRollup": isRollup, "breakdown": breakdown}}
