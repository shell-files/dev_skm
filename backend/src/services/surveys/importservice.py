<<<<<<< HEAD
"""
importservice.py
레이어: Service (surveys)
역할: 설문 응답 데이터 가져오기 서비스 — Sheets 데이터 파싱·검증·저장.
"""
from __future__ import annotations

from src.repositories.dmasurveyresponserepository import (
    getReadySurveyFormForRun,
    replaceSurveyResponsesForFormTx,
)
from src.services.surveys import importmeta as _im
from src.services.surveys import importparser as _ip


def previewSurveyResponses(runId: int) -> dict:
    """Sheets 응답 데이터를 파싱해 미리보기 행(최대 20건)과 메타 정보를 반환한다. DB에 저장하지 않는다."""
=======
import re
from typing import Optional

from src.utils.dmasurveyresponserepository import (
    getReadySurveyFormForRun,
    replaceSurveyResponsesForFormTx,
)

_META_SHEETS = ["_FORM_REGISTRY", "_SELECTOR_MAP", "_QUESTION_MAP", "_ISSUE_MAP"]
_ALLOWED_GROUPS = frozenset({"employee", "management", "external"})
_SELECTOR_GROUPS = frozenset({"employee", "external"})


# =============================================================================
# Header / label normalization helpers
# =============================================================================

def _normalizeHeaderText(value: str) -> str:
    """Collapse whitespace (newline, tabs, multiple spaces) to a single space."""
    return re.sub(r"\s+", " ", str(value or "").strip())


def _normalizeIssueLabel(value: str) -> str:
    """Normalize issue label for lookup — same rule as header."""
    return re.sub(r"\s+", " ", str(value or "").strip())


def _extractBracketParts(header: str) -> list:
    """Return list of content strings inside [...] brackets, in order."""
    return re.findall(r"\[([^\]]+)\]", header or "")


def _parseQuestionMarker(part: str) -> "tuple | None":
    """Detect 'QUESTION_CODE|route' pattern inside a bracket.
    Returns (question_code, route) if detected, else None.
    """
    if "|" not in part:
        return None
    qcode, route = part.split("|", 1)
    return (qcode.strip(), route.strip())


# =============================================================================
# Sheets Service — lazy init (no import-time credential read)
# =============================================================================

def _getSheetsService():
    from src.utils.settings import settings
    from googleapiclient.discovery import build
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_APPLICATION_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return build("sheets", "v4", credentials=creds)


# =============================================================================
# Sheet table parser
# =============================================================================

def _sheetValuesToDictRows(values: list) -> list:
    """Convert raw Google Sheets values (list[list]) to list[dict].

    First row is header. Subsequent rows are data.
    Blank headers and duplicate headers are rejected.
    Short rows are padded with empty strings.
    """
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


# =============================================================================
# Workbook loader
# =============================================================================

def _loadWorkbookValues(masterSheetId: str) -> dict:
    """Load all relevant sheet values from MasterSheet."""
    svc = _getSheetsService()
    sheets_api = svc.spreadsheets()
    result: dict = {}

    # Load meta sheets; _SELECTOR_MAP may be empty — others must not be
    for sheet_name in _META_SHEETS:
        resp = sheets_api.values().get(
            spreadsheetId=masterSheetId,
            range=f"{sheet_name}!A:ZZ",
        ).execute()
        values = resp.get("values", [])
        if not values and sheet_name != "_SELECTOR_MAP":
            raise ValueError(f"Meta sheet {sheet_name!r} is empty or missing")
        result[sheet_name] = values or []

    # Parse _FORM_REGISTRY to discover response sheet names
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


# =============================================================================
# Meta sheet parser
# =============================================================================

def _parseMetaSheets(workbook: dict) -> dict:
    """Parse meta sheets into lookup structures."""
    registry = _sheetValuesToDictRows(workbook["_FORM_REGISTRY"])

    raw_selector = workbook.get("_SELECTOR_MAP", [])
    selector_rows = _sheetValuesToDictRows(raw_selector) if raw_selector else []

    question_rows = _sheetValuesToDictRows(workbook["_QUESTION_MAP"])
    issue_rows = _sheetValuesToDictRows(workbook["_ISSUE_MAP"])

    # Validate registry
    sheet_to_group: dict = {}
    for row in registry:
        group = row.get("respondent_group", "")
        if group not in _ALLOWED_GROUPS:
            raise ValueError(
                f"Unknown respondent_group in _FORM_REGISTRY: {group!r}"
            )
        sheet_name = row.get("response_sheet_name", "").strip()
        if not sheet_name:
            raise ValueError("Blank response_sheet_name in _FORM_REGISTRY")
        sheet_to_group[sheet_name] = group

    # Selector lookup: {(respondent_group, selector_title, selector_label): {selector_value, route}}
    selector_lookup: dict = {}
    selector_titles: dict = {}  # {respondent_group: selector_title}
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

    # Question lookups
    question_lookup: dict = {}             # sheet_header_title → qinfo
    question_lookup_normalized: dict = {}  # normalized header/title → qinfo
    question_code_route_lookup: dict = {}  # (code, route, group|None) → qinfo
    question_code_lookup: dict = {}        # code → qinfo (last wins)

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

    # Issue lookup: {sub_issue_name: sub_issue_code} + normalized keys
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


# =============================================================================
# Source response key builder
# =============================================================================

def _buildSourceResponseKey(
    *,
    master_sheet_id: str,
    response_sheet_name: str,
    row_index: int,
    row_dict: dict,
) -> str:
    timestamp = (
        row_dict.get("Timestamp", "")
        or row_dict.get("타임스탬프", "")
        or row_dict.get("timestamp", "")
    )
    email = (
        row_dict.get("Email Address", "")
        or row_dict.get("이메일 주소", "")
        or row_dict.get("email", "")
        or row_dict.get("Email", "")
    )
    if timestamp or email:
        return f"{master_sheet_id}:{response_sheet_name}:{row_index}:{timestamp}:{email}"
    return f"{master_sheet_id}:{response_sheet_name}:{row_index}"


# =============================================================================
# Grid answer parser
# =============================================================================

def _parseGridAnswer(
    *,
    cell_value: str,
    issue_lookup: dict,
    question_code: str,
    mapped_axis: str,
    respondent_group: str,
    department_code: Optional[str],
    survey_form_id: int,
    run_id: int,
    source_response_key: str,
    skipped: list,
) -> list:
    """Case A: cell contains 'issue_name: score' pairs, newline or comma separated."""
    result = []
    cell = cell_value.strip()
    if not cell:
        return result

    lines = re.split(r"[\n,]+", cell)
    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(r"^(.+?):\s*(\d+)\s*$", line)
        if match:
            issue_name = match.group(1).strip()
            score_str = match.group(2)
        else:
            match2 = re.match(r"^(.+?)\s+(\d+)\s*$", line)
            if match2:
                issue_name = match2.group(1).strip()
                score_str = match2.group(2)
            else:
                skipped.append({"reason": "cannot_parse_grid_line", "line": line[:200]})
                continue

        sub_issue_code = issue_lookup.get(issue_name)
        if sub_issue_code is None:
            skipped.append({"reason": "unknown_issue_label", "issue_name": issue_name[:200]})
            continue

        try:
            score = int(score_str)
        except ValueError:
            skipped.append({"reason": "invalid_score", "score_str": score_str[:20]})
            continue

        if score < 1 or score > 5:
            skipped.append({"reason": "score_out_of_range", "score": score})
            continue

        result.append({
            "runId": run_id,
            "surveyFormId": survey_form_id,
            "questionCode": question_code,
            "mappedAxis": mapped_axis,
            "respondentGroup": respondent_group,
            "sourceResponseKey": source_response_key,
            "respondentUserId": None,
            "departmentCode": department_code,
            "subIssueCode": sub_issue_code,
            "answerNumeric": score,
            "answerText": None,
            "normalizedScore": float(score),
        })

    return result


def _parseGridAnswerFromHeader(
    *,
    issue_name: str,
    cell_value: str,
    issue_lookup: dict,
    question_code: str,
    mapped_axis: str,
    respondent_group: str,
    department_code: Optional[str],
    survey_form_id: int,
    run_id: int,
    source_response_key: str,
    skipped: list,
) -> list:
    """Case B: column header already contains '[issue_name]' bracket."""
    result = []
    cell = cell_value.strip()
    if not cell:
        return result

    sub_issue_code = issue_lookup.get(issue_name)
    if sub_issue_code is None:
        skipped.append({"reason": "unknown_issue_label_from_header", "issue_name": issue_name[:200]})
        return result

    try:
        score = int(cell)
    except ValueError:
        skipped.append({"reason": "invalid_score_case_b", "score_str": cell[:20]})
        return result

    if score < 1 or score > 5:
        skipped.append({"reason": "score_out_of_range_case_b", "score": score})
        return result

    result.append({
        "runId": run_id,
        "surveyFormId": survey_form_id,
        "questionCode": question_code,
        "mappedAxis": mapped_axis,
        "respondentGroup": respondent_group,
        "sourceResponseKey": source_response_key,
        "respondentUserId": None,
        "departmentCode": department_code,
        "subIssueCode": sub_issue_code,
        "answerNumeric": score,
        "answerText": None,
        "normalizedScore": float(score),
    })
    return result


# =============================================================================
# Top5 answer parser
# =============================================================================

def _parseTop5Answer(
    *,
    cell_value: str,
    issue_lookup: dict,
    question_code: str,
    respondent_group: str,
    department_code: Optional[str],
    survey_form_id: int,
    run_id: int,
    source_response_key: str,
    skipped: list,
) -> list:
    result = []
    cell = cell_value.strip()
    if not cell:
        return result

    labels = re.split(r"[\n,]+", cell)
    for label in labels:
        label = label.strip()
        if not label:
            continue

        sub_issue_code = issue_lookup.get(label)
        if sub_issue_code is None:
            skipped.append({"reason": "unknown_top5_label", "label": label[:200]})
            continue

        result.append({
            "runId": run_id,
            "surveyFormId": survey_form_id,
            "questionCode": question_code,
            "mappedAxis": "ranking",
            "respondentGroup": respondent_group,
            "sourceResponseKey": source_response_key,
            "respondentUserId": None,
            "departmentCode": department_code,
            "subIssueCode": sub_issue_code,
            "answerNumeric": None,
            "answerText": label,
            "normalizedScore": None,
        })

    return result


# =============================================================================
# Header resolver — supports 5 Google Forms column header patterns
# =============================================================================

def _resolveQuestionHeader(
    header: str,
    respondent_group: str,
    meta: dict,
) -> "dict | None":
    """Resolve a response-sheet column header to qinfo dict.

    Returns dict with keys: question_code, mapped_axis, question_type,
    route, respondent_group, question_title, issue_name.
    Returns None if the header is not recognized.
    """
    question_lookup = meta["question_lookup"]
    question_lookup_normalized = meta.get("question_lookup_normalized", {})
    question_code_route_lookup = meta.get("question_code_route_lookup", {})
    question_code_lookup = meta.get("question_code_lookup", {})

    # Pattern 1: exact match (sheet_header_title)
    if header in question_lookup:
        result = dict(question_lookup[header])
        result["issue_name"] = None
        return result

    # Pattern 2: normalized whitespace match
    normalized = _normalizeHeaderText(header)
    if normalized in question_lookup_normalized:
        result = dict(question_lookup_normalized[normalized])
        result["issue_name"] = None
        return result

    # Bracket-based patterns (3, 4, 5)
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

    # Pattern 3/5: marker-based lookup (QUESTION_CODE|route inside header)
    if markers:
        qcode, route = markers[-1]
        qinfo = (
            question_code_route_lookup.get((qcode, route, respondent_group))
            or question_code_route_lookup.get((qcode, route, None))
            or question_code_lookup.get(qcode)
        )

    # Pattern 4: base text before first bracket (no marker or marker not found)
    if qinfo is None:
        base = re.sub(r"\s*\[.*", "", header, flags=re.DOTALL).strip()
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


# =============================================================================
# Response sheet parser
# =============================================================================

def _parseResponseSheets(
    *,
    run_id: int,
    survey_form_id: int,
    master_sheet_id: str,
    workbook: dict,
    meta: dict,
) -> tuple:
    """Parse all response sheets into flat rows. Returns (rows, skipped)."""
    all_rows: list = []
    all_skipped: list = []

    sheet_to_group = meta["sheet_to_group"]
    selector_lookup = meta["selector_lookup"]
    selector_titles = meta["selector_titles"]
    question_lookup = meta["question_lookup"]
    issue_lookup = meta["issue_lookup"]

    for sheet_name, respondent_group in sheet_to_group.items():
        if sheet_name not in workbook:
            raise ValueError(f"Response sheet {sheet_name!r} not found in workbook")

        sheet_values = workbook[sheet_name]
        if not sheet_values:
            continue

        headers = [str(h).strip() for h in sheet_values[0]]

        # Find selector column for groups that have selectors
        selector_col_idx = None
        selector_title = selector_titles.get(respondent_group)
        if respondent_group in _SELECTOR_GROUPS and selector_title:
            try:
                selector_col_idx = headers.index(selector_title)
            except ValueError:
                pass

        # Map each header column to question info using multi-pattern resolver
        # header_question_map: {col_idx: {question_code, mapped_axis, question_type, issue_name}}
        header_question_map: dict = {}
        for col_idx, header in enumerate(headers):
            qinfo = _resolveQuestionHeader(
                header=header,
                respondent_group=respondent_group,
                meta=meta,
            )
            if qinfo is not None:
                header_question_map[col_idx] = qinfo

        for row_idx, raw_row in enumerate(sheet_values[1:], start=2):
            padded = list(raw_row) + [""] * (len(headers) - len(raw_row))
            row_dict = dict(zip(headers, [str(c) for c in padded]))

            source_key = _buildSourceResponseKey(
                master_sheet_id=master_sheet_id,
                response_sheet_name=sheet_name,
                row_index=row_idx,
                row_dict=row_dict,
            )

            # Determine department_code
            if selector_col_idx is not None:
                selector_label = padded[selector_col_idx].strip()
                lookup_key = (respondent_group, selector_title, selector_label)
                if lookup_key not in selector_lookup:
                    all_skipped.append({
                        "reason": "unknown_selector_label",
                        "respondent_group": respondent_group,
                        "selector_label": selector_label[:200],
                    })
                    continue
                sel_info = selector_lookup[lookup_key]
                department_code: Optional[str] = sel_info["selector_value"]
            elif respondent_group == "management":
                department_code = None
            else:
                department_code = None

            for col_idx, qinfo in header_question_map.items():
                cell_value = padded[col_idx] if col_idx < len(padded) else ""
                cell_value = str(cell_value).strip()

                question_code = qinfo["question_code"]
                mapped_axis = qinfo["mapped_axis"]
                question_type = qinfo["question_type"]
                issue_name = qinfo.get("issue_name")

                if question_type == "top5" or question_code == "RANKING_TOP5":
                    rows = _parseTop5Answer(
                        cell_value=cell_value,
                        issue_lookup=issue_lookup,
                        question_code=question_code,
                        respondent_group=respondent_group,
                        department_code=department_code,
                        survey_form_id=survey_form_id,
                        run_id=run_id,
                        source_response_key=source_key,
                        skipped=all_skipped,
                    )
                    all_rows.extend(rows)

                elif issue_name is not None:
                    rows = _parseGridAnswerFromHeader(
                        issue_name=issue_name,
                        cell_value=cell_value,
                        issue_lookup=issue_lookup,
                        question_code=question_code,
                        mapped_axis=mapped_axis,
                        respondent_group=respondent_group,
                        department_code=department_code,
                        survey_form_id=survey_form_id,
                        run_id=run_id,
                        source_response_key=source_key,
                        skipped=all_skipped,
                    )
                    all_rows.extend(rows)

                elif question_type == "grid" or mapped_axis in ("impact", "financial"):
                    rows = _parseGridAnswer(
                        cell_value=cell_value,
                        issue_lookup=issue_lookup,
                        question_code=question_code,
                        mapped_axis=mapped_axis,
                        respondent_group=respondent_group,
                        department_code=department_code,
                        survey_form_id=survey_form_id,
                        run_id=run_id,
                        source_response_key=source_key,
                        skipped=all_skipped,
                    )
                    all_rows.extend(rows)

                else:
                    if not cell_value:
                        continue
                    all_rows.append({
                        "runId": run_id,
                        "surveyFormId": survey_form_id,
                        "questionCode": question_code,
                        "mappedAxis": mapped_axis,
                        "respondentGroup": respondent_group,
                        "sourceResponseKey": source_key,
                        "respondentUserId": None,
                        "departmentCode": department_code,
                        "subIssueCode": None,
                        "answerNumeric": None,
                        "answerText": cell_value,
                        "normalizedScore": None,
                    })

    return all_rows, all_skipped


# =============================================================================
# Public API
# =============================================================================

def previewSurveyResponses(runId: int) -> dict:
>>>>>>> origin/skm_test
    form = getReadySurveyFormForRun(runId)
    master_sheet_id = form["master_sheet_id"]
    survey_form_id = form["id"]

<<<<<<< HEAD
    workbook = _im._loadWorkbookValues(master_sheet_id)
    meta = _im._parseMetaSheets(workbook)

    rows, skipped = _ip.parseResponseSheets(
=======
    workbook = _loadWorkbookValues(master_sheet_id)
    meta = _parseMetaSheets(workbook)

    rows, skipped = _parseResponseSheets(
>>>>>>> origin/skm_test
        run_id=runId,
        survey_form_id=survey_form_id,
        master_sheet_id=master_sheet_id,
        workbook=workbook,
        meta=meta,
    )

    return {
        "runId": runId,
        "surveyFormId": survey_form_id,
        "masterSheetId": master_sheet_id,
        "metaSheets": {
            "formRegistry": meta["formRegistry"],
            "selectorMap": meta["selectorMap"],
            "questionMap": meta["questionMap"],
            "issueMap": meta["issueMap"],
        },
        "responseSheets": meta["response_sheets"],
        "previewRows": rows[:20],
    }


def importSurveyResponsesForRun(runId: int) -> dict:
<<<<<<< HEAD
    """Sheets 응답을 파싱해 DB에 UPSERT하고 그룹별 응답자 수와 처리 결과를 반환한다."""
=======
>>>>>>> origin/skm_test
    form = getReadySurveyFormForRun(runId)
    master_sheet_id = form["master_sheet_id"]
    survey_form_id = form["id"]

<<<<<<< HEAD
    workbook = _im._loadWorkbookValues(master_sheet_id)
    meta = _im._parseMetaSheets(workbook)

    rows, skipped = _ip.parseResponseSheets(
=======
    workbook = _loadWorkbookValues(master_sheet_id)
    meta = _parseMetaSheets(workbook)

    rows, skipped = _parseResponseSheets(
>>>>>>> origin/skm_test
        run_id=runId,
        survey_form_id=survey_form_id,
        master_sheet_id=master_sheet_id,
        workbook=workbook,
        meta=meta,
    )

    db_result = replaceSurveyResponsesForFormTx(
        runId=runId,
        surveyFormId=survey_form_id,
        rows=rows,
    )

<<<<<<< HEAD
=======
    # Count unique respondents (unique source_response_key) per group
>>>>>>> origin/skm_test
    respondent_sets: dict = {}
    for row in rows:
        group = row["respondentGroup"]
        key = row["sourceResponseKey"]
        if group not in respondent_sets:
            respondent_sets[group] = set()
        respondent_sets[group].add(key)
    respondent_counts = {g: len(ks) for g, ks in respondent_sets.items()}

    return {
        "runId": runId,
        "surveyFormId": survey_form_id,
        "masterSheetId": master_sheet_id,
        "importedRowCount": len(rows),
        "insertedCount": db_result.get("insertedCount", len(rows)),
        "updatedCount": db_result.get("updatedCount", 0),
        "skippedCount": len(skipped),
        "respondentCounts": respondent_counts,
        "status": "success",
    }
