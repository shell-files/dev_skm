"""
importparser.py
레이어: Service (surveys)
역할: 설문 응답 데이터 파싱 — Google Sheets 원시 데이터를 응답 DTO로 변환.
"""
from __future__ import annotations

import re
from typing import Optional

from src.services.surveys.importmeta import (
    _SELECTOR_GROUPS,
    _resolveQuestionHeader,
)


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


def parseResponseSheets(
    *,
    run_id: int,
    survey_form_id: int,
    master_sheet_id: str,
    workbook: dict,
    meta: dict,
) -> tuple:
    """워크북의 응답 시트를 읽어 grid·top5·텍스트 유형별로 파싱하고 응답 행 목록과 건너뛴 항목 목록을 반환한다."""
    all_rows: list = []
    all_skipped: list = []

    sheet_to_group = meta["sheet_to_group"]
    selector_lookup = meta["selector_lookup"]
    selector_titles = meta["selector_titles"]
    issue_lookup = meta["issue_lookup"]

    for sheet_name, respondent_group in sheet_to_group.items():
        if sheet_name not in workbook:
            raise ValueError(f"Response sheet {sheet_name!r} not found in workbook")

        sheet_values = workbook[sheet_name]
        if not sheet_values:
            continue

        headers = [str(h).strip() for h in sheet_values[0]]

        selector_col_idx = None
        selector_title = selector_titles.get(respondent_group)
        if respondent_group in _SELECTOR_GROUPS and selector_title:
            try:
                selector_col_idx = headers.index(selector_title)
            except ValueError:
                pass

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
