from __future__ import annotations

import re

_META_SHEETS = ["_FORM_REGISTRY", "_SELECTOR_MAP", "_QUESTION_MAP", "_ISSUE_MAP"]
_ALLOWED_GROUPS = frozenset({"employee", "management", "external"})
_SELECTOR_GROUPS = frozenset({"employee", "external"})


def _normalizeHeaderText(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _normalizeIssueLabel(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _extractBracketParts(header: str) -> list:
    return re.findall(r"\[([^\]]+)\]", header or "")


def _parseQuestionMarker(part: str):
    if "|" not in part:
        return None
    qcode, route = part.split("|", 1)
    return (qcode.strip(), route.strip())


from src.utils.sheetsutils import getSheetsService as _getSheetsService


def _sheetValuesToDictRows(values: list) -> list:
    if not values:
        return []

    headers = [str(h).strip() for h in values[0]]

    for i, h in enumerate(headers):
        if not h:
            raise ValueError(f"Blank header at column index {i}")

    seen: set = set()
    for h in headers:
        if h in seen:
            raise ValueError(f"Duplicate header: {h!r}")
        seen.add(h)

    rows = []
    for raw_row in values[1:]:
        padded = list(raw_row) + [""] * (len(headers) - len(raw_row))
        rows.append(dict(zip(headers, [str(c) for c in padded])))
    return rows


def _loadWorkbookValues(masterSheetId: str) -> dict:
    svc = _getSheetsService()
    sheets_api = svc.spreadsheets()
    result: dict = {}

    for sheet_name in _META_SHEETS:
        resp = sheets_api.values().get(
            spreadsheetId=masterSheetId,
            range=f"{sheet_name}!A:ZZ",
        ).execute()
        values = resp.get("values", [])
        if not values and sheet_name != "_SELECTOR_MAP":
            raise ValueError(f"Meta sheet {sheet_name!r} is empty or missing")
        result[sheet_name] = values or []

    registry_rows = _sheetValuesToDictRows(result["_FORM_REGISTRY"])
    for reg_row in registry_rows:
        sheet_name = reg_row.get("response_sheet_name", "").strip()
        if not sheet_name:
            raise ValueError("_FORM_REGISTRY has blank response_sheet_name")
        if sheet_name not in result:
            resp = sheets_api.values().get(
                spreadsheetId=masterSheetId,
                range=f"{sheet_name}!A:ZZ",
            ).execute()
            values = resp.get("values", [])
            if not values:
                raise ValueError(f"Response sheet {sheet_name!r} is empty or missing")
            result[sheet_name] = values

    return result


def _parseMetaSheets(workbook: dict) -> dict:
    registry = _sheetValuesToDictRows(workbook["_FORM_REGISTRY"])

    raw_selector = workbook.get("_SELECTOR_MAP", [])
    selector_rows = _sheetValuesToDictRows(raw_selector) if raw_selector else []

    question_rows = _sheetValuesToDictRows(workbook["_QUESTION_MAP"])
    issue_rows = _sheetValuesToDictRows(workbook["_ISSUE_MAP"])

    sheet_to_group: dict = {}
    for row in registry:
        group = row.get("respondent_group", "")
        if group not in _ALLOWED_GROUPS:
            raise ValueError(f"Unknown respondent_group in _FORM_REGISTRY: {group!r}")
        sheet_name = row.get("response_sheet_name", "").strip()
        if not sheet_name:
            raise ValueError("Blank response_sheet_name in _FORM_REGISTRY")
        sheet_to_group[sheet_name] = group

    selector_lookup: dict = {}
    selector_titles: dict = {}
    for row in selector_rows:
        group = row.get("respondent_group", "")
        title = row.get("selector_title", "").strip()
        label = row.get("selector_label", "").strip()
        key = (group, title, label)
        selector_lookup[key] = {
            "selector_value": row.get("selector_value", ""),
            "route": row.get("route", ""),
        }
        if group not in selector_titles:
            selector_titles[group] = title

    question_lookup: dict = {}
    question_lookup_normalized: dict = {}
    question_code_route_lookup: dict = {}
    question_code_lookup: dict = {}

    for row in question_rows:
        header_title = row.get("sheet_header_title", "").strip()
        if not header_title:
            continue
        qinfo = {
            "question_code": row.get("question_code", ""),
            "mapped_axis": row.get("mapped_axis", ""),
            "question_type": row.get("question_type", ""),
            "route": row.get("route", ""),
            "respondent_group": row.get("respondent_group", ""),
            "question_title": row.get("question_title", "").strip(),
        }
        question_lookup[header_title] = qinfo
        question_lookup_normalized[_normalizeHeaderText(header_title)] = qinfo

        qt = qinfo["question_title"]
        if qt and qt != header_title:
            question_lookup_normalized[_normalizeHeaderText(qt)] = qinfo

        code = qinfo["question_code"]
        route_val = qinfo["route"]
        group_val = qinfo["respondent_group"]
        if code:
            question_code_route_lookup[(code, route_val, group_val)] = qinfo
            question_code_route_lookup[(code, route_val, None)] = qinfo
            question_code_lookup[code] = qinfo

    issue_lookup: dict = {}
    for row in issue_rows:
        name = row.get("sub_issue_name", "").strip()
        code = row.get("sub_issue_code", "").strip()
        if name and code:
            issue_lookup[name] = code
            norm_name = _normalizeIssueLabel(name)
            if norm_name != name:
                issue_lookup[norm_name] = code

    return {
        "registry": registry,
        "sheet_to_group": sheet_to_group,
        "selector_lookup": selector_lookup,
        "selector_titles": selector_titles,
        "question_lookup": question_lookup,
        "question_lookup_normalized": question_lookup_normalized,
        "question_code_route_lookup": question_code_route_lookup,
        "question_code_lookup": question_code_lookup,
        "issue_lookup": issue_lookup,
        "response_sheets": list(sheet_to_group.keys()),
        "formRegistry": bool(registry),
        "selectorMap": bool(selector_rows),
        "questionMap": bool(question_rows),
        "issueMap": bool(issue_rows),
    }


def _resolveQuestionHeader(header: str, respondent_group: str, meta: dict):
    import re as _re
    question_lookup = meta["question_lookup"]
    question_lookup_normalized = meta.get("question_lookup_normalized", {})
    question_code_route_lookup = meta.get("question_code_route_lookup", {})
    question_code_lookup = meta.get("question_code_lookup", {})

    if header in question_lookup:
        result = dict(question_lookup[header])
        result["issue_name"] = None
        return result

    normalized = _normalizeHeaderText(header)
    if normalized in question_lookup_normalized:
        result = dict(question_lookup_normalized[normalized])
        result["issue_name"] = None
        return result

    parts = _extractBracketParts(header)
    if not parts:
        return None

    markers = []
    non_markers = []
    for p in parts:
        m = _parseQuestionMarker(p)
        if m:
            markers.append(m)
        else:
            non_markers.append(p)

    issue_name = _normalizeIssueLabel(non_markers[-1]) if non_markers else None

    qinfo = None

    if markers:
        qcode, route = markers[-1]
        qinfo = (
            question_code_route_lookup.get((qcode, route, respondent_group))
            or question_code_route_lookup.get((qcode, route, None))
            or question_code_lookup.get(qcode)
        )

    if qinfo is None:
        base = _re.sub(r"\s*\[.*", "", header, flags=_re.DOTALL).strip()
        norm_base = _normalizeHeaderText(base)
        qinfo = (
            question_lookup.get(base)
            or question_lookup_normalized.get(norm_base)
        )

    if qinfo is None:
        return None

    result = dict(qinfo)
    result["issue_name"] = issue_name
    return result
