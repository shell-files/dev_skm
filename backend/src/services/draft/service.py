"""
service.py
레이어: Service (draft)
역할: ESG 보고서 초안 섹션 KPI 데이터 조회 및 저장 서비스.
"""
import ast
import json as json_mod
import operator
import re
from datetime import datetime, timedelta

from src.models.draft import DraftSaveRequestDto
from src.repositories.draftrepository import (
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
    getRollupDetailRow,
    getCompanyNamesByIds,
    getSourceMetricRollupRows,
)

# metric_id 패턴: E1-06__G0001, S6-04__N0002 등
_METRIC_ID_RE = re.compile(r'[A-Za-z][0-9]+-[0-9]+__[A-Za-z0-9]+')


def _nowKst() -> str:
    return (datetime.now() + timedelta(hours=9)).isoformat(timespec="seconds")


def fetchDraftMetrics(companyId: int, year: int, token) -> dict:
    """개별 KPI와 롤업 지표를 중복 없이 합쳐 초안 지표 목록을 반환한다."""
    rows = getKpiMetricRows(companyId, year)
    existingIds = {r["metricId"] for r in rows}
    for r in getRollupMetricRows(companyId, year):
        if r["metricId"] not in existingIds:
            rows.append(r)
    return {"success": True, "data": rows}


def fetchDraftSection(companyId: int, year: int, subIssueId: str, token) -> dict:
    """서브이슈별 AI 생성 보고서 섹션 텍스트와 참조 지표 ID 목록을 반환한다."""
    row = getAiSectionRow(companyId, year, subIssueId)
    if not row:
        return {"success": True, "data": None}
    traces = getAiMetricTraceRows(row["sectionId"])
    metricIds = [t["metricId"] for t in traces] if traces else []
    return {"success": True, "data": {"reportText": row["reportText"], "metricIds": metricIds}}


def saveDraft(req: DraftSaveRequestDto, token) -> dict:
    """페이지별 지표 값과 서술 텍스트를 초안 DB에 저장한다."""
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
    """저장된 초안 지표와 서술 텍스트를 페이지 키 기준으로 조합해 반환한다."""
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
    """저장된 초안 데이터를 전부 삭제해 초기화한다."""
    deleteDraftRows(companyId, year)
    return {"success": True}


# ── 롤업 breakdown 헬퍼 ─────────────────────────────────────────────────────

def _extractSourceMetricIds(calculationTrace: str) -> list:
    """
    calculation_trace(JSON 또는 수식 문자열)에서 참조 metric_id 목록 추출.
    JSON이면 formula / dependencies 필드를 탐색하고,
    raw string이면 직접 패턴 매칭.
    """
    if not calculationTrace:
        return []
    found: set = set()
    raw = str(calculationTrace)
    # JSON 구조 탐색
    try:
        parsed = json_mod.loads(raw)
        if isinstance(parsed, dict):
            formula = str(parsed.get("formula") or parsed.get("formulaExpression") or "")
            found.update(_METRIC_ID_RE.findall(formula))
            for dep in parsed.get("dependencies", []):
                sid = dep.get("sourceAtomicMetricId") or dep.get("atomicMetricId") or ""
                if sid:
                    found.add(str(sid))
    except Exception:
        pass
    # raw string에서 추가 추출 (JSON 파싱 성공 여부와 무관)
    found.update(_METRIC_ID_RE.findall(raw))
    return list(found)


def _extractFormula(calculationTrace: str) -> str:
    """calculation_trace에서 수식 문자열 추출. 없으면 빈 문자열."""
    if not calculationTrace:
        return ""
    try:
        parsed = json_mod.loads(calculationTrace)
        if isinstance(parsed, dict):
            return str(parsed.get("formula") or parsed.get("formulaExpression") or "")
    except Exception:
        pass
    return ""


_SAFE_EVAL_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _safeEvalFormula(formula: str, values: dict) -> float | None:
    """
    metric_id를 값으로 치환한 수식을 ast 기반으로 안전하게 계산.
    +, -, *, / 만 허용. 제로 나누기·파싱 오류는 None 반환.
    """
    if not formula or not values:
        return None
    expr = formula
    # 긴 ID 먼저 치환(부분 일치 방지)
    for mid, val in sorted(values.items(), key=lambda x: -len(x[0])):
        if val is None:
            return None
        expr = expr.replace(mid, str(float(val)))

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp):
            op_fn = _SAFE_EVAL_OPS.get(type(node.op))
            if op_fn is None:
                raise ValueError("unsupported op")
            right = _eval(node.right)
            if right == 0 and isinstance(node.op, ast.Div):
                raise ZeroDivisionError
            return op_fn(_eval(node.left), right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval(node.operand)
        raise ValueError(f"unsupported node: {type(node)}")

    try:
        return _eval(ast.parse(expr, mode="eval").body)
    except Exception:
        return None


def _formatBreakdown(company_val_map: dict, name_map: dict, unit: str) -> list:
    """
    company_val_map + name_map → [{l, v, contributionRate}] 공통 포맷터.
    key는 str(회사코드) 또는 int(companyId) 모두 허용.
    """
    is_krw = (unit or "").upper() == "KRW"
    total = sum(v for v in company_val_map.values() if v is not None and v > 0)
    result = []
    for key, val in sorted(company_val_map.items(), key=lambda x: str(x[0])):
        if val is None:
            continue
        cname = name_map.get(key) or str(key)
        if is_krw:
            uk = val / 100_000_000
            uk_r = round(uk * 10) / 10
            display_v = f"{int(uk_r):,} 억 원" if uk_r % 1 == 0 else f"{uk_r:,} 억 원"
        else:
            display_v = f"{int(val):,}{(' ' + unit) if unit else ''}" if val % 1 == 0 else f"{val:,.1f}{(' ' + unit) if unit else ''}"
        contrib = round((val / total) * 100, 1) if total > 0 else None
        result.append({"l": cname, "v": display_v, "contributionRate": contrib})
    return result


def _parseSourceValuesJson(sourceValuesJson: str) -> dict:
    """
    source_company_values_json → {key(str): value(float)} 파싱.
    형식 1: {"A_GROUP": 1332000000000, ...}       → 회사 코드 키 (직접 매핑)
    형식 2: {"atomicId": {"6": "123.0", ...}, ...} → 중첩형, 회사ID별 합산
    """
    if not sourceValuesJson:
        return {}
    try:
        parsed = json_mod.loads(sourceValuesJson)
    except Exception:
        return {}
    if not isinstance(parsed, dict) or not parsed:
        return {}

    first_val = next(iter(parsed.values()))
    if isinstance(first_val, dict):
        # 중첩형: {atomicId: {companyKey: value}} → 회사키별 합산
        result: dict = {}
        for _, company_vals in parsed.items():
            if not isinstance(company_vals, dict):
                continue
            for ckey, val in company_vals.items():
                try:
                    result[str(ckey)] = result.get(str(ckey), 0.0) + float(val)
                except (ValueError, TypeError):
                    pass
        return result
    else:
        # 단순형: {key: value}
        result = {}
        for k, v in parsed.items():
            if v is None:
                continue
            try:
                result[str(k)] = float(v)
            except (ValueError, TypeError):
                pass
        return result


def _resolveNameMap(company_val_map: dict) -> dict:
    """
    키가 모두 순수 숫자이면 DB에서 회사명 조회, 아니면 키 자체를 이름으로 사용.
    반환: {str_key: displayName}
    """
    if all(k.isdigit() for k in company_val_map):
        raw = getCompanyNamesByIds([int(k) for k in company_val_map])
        return {str(k): v for k, v in raw.items()}
    return {k: k for k in company_val_map}


def _buildRollupBreakdown(companyId: int, metricId: str, year: int, unit: str) -> list:
    """
    롤업 지표의 자회사별 내역 구성. DB 조회 최대 2회.

    1차: getRollupDetailRow → source_company_values_json 파싱
    2차(비어있으면): calculation_trace에서 source metric 추출
                    → getSourceMetricRollupRows 배치 조회 (ESG_GROUP_ROLLUP_RESULT)
                    → source metric별 source_company_values_json를 회사코드 기준으로 합산
    """
    detail = getRollupDetailRow(companyId, metricId, year)
    if not detail:
        return []

    # 1차: source_company_values_json
    company_val_map = _parseSourceValuesJson(detail.get("sourceValuesJson"))
    if company_val_map:
        return _formatBreakdown(company_val_map, _resolveNameMap(company_val_map), unit)

    # 2차: calculation_trace 기반 fallback
    calc_trace = detail.get("calculationTrace") or ""
    source_metric_ids = _extractSourceMetricIds(calc_trace)
    if not source_metric_ids:
        return []

    # source metric들의 rollup 결과를 단일 배치 쿼리 (ESG_GROUP_ROLLUP_RESULT)
    source_rows = getSourceMetricRollupRows(companyId, source_metric_ids, year)
    if not source_rows:
        return []

    # metricId별 최신 1건: {metricId: {companyCode: value}}
    source_data: dict[str, dict] = {}
    seen: set = set()
    for r in source_rows:
        mid = str(r["metricId"])
        if mid not in seen:
            seen.add(mid)
            source_data[mid] = _parseSourceValuesJson(r.get("sourceValuesJson"))

    # 회사코드 기준 재편: {companyCode: {metricId: value}}
    company_sources: dict[str, dict] = {}
    for mid, cvals in source_data.items():
        for ccode, val in cvals.items():
            company_sources.setdefault(ccode, {})[mid] = val

    if not company_sources:
        return []

    formula = _extractFormula(calc_trace)
    company_val_map = {}
    for ccode, src_vals in company_sources.items():
        if formula:
            computed = _safeEvalFormula(formula, src_vals)
        elif len(src_vals) == 1:
            computed = next(iter(src_vals.values()))
        else:
            # 수식 없고 source 여러 개 → SUM
            vals = [v for v in src_vals.values() if v is not None]
            computed = sum(vals) if vals else None
        company_val_map[ccode] = computed

    return _formatBreakdown(company_val_map, _resolveNameMap(company_val_map), unit)


# ── 공개 서비스 함수 ────────────────────────────────────────────────────────

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

    breakdown = _buildRollupBreakdown(companyId, metricId, year, unit) if isRollup else []
    return {"success": True, "data": {"trend": trend, "unit": unit, "isRollup": isRollup, "breakdown": breakdown}}
