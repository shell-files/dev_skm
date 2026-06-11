from typing import Any, Mapping, Optional


VALID_RESPONDENT_GROUPS = {"employee", "management", "external"}
VALID_AXES = {"impact", "financial"}


def firstPresent(row: Mapping[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return default


def normalizeScore(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalizeBool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "y", "yes", "priority"}


def resolveQuestionMeta(rawRowsKey: Any, questionMap: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
    if rawRowsKey is None:
        return {}
    return questionMap.get(str(rawRowsKey), {})


def step0NormalizeSurveyRows(rawRows: list, questionMap: Mapping[str, Mapping[str, Any]]) -> list[dict]:
    normalized: list[dict] = []
    for row in rawRows or []:
        if not isinstance(row, Mapping):
            continue
        responseKey = firstPresent(row, ("responseKey", "response_key", "id", "questionKey", "question_key"))
        questionKey = firstPresent(row, ("questionKey", "question_key", "questionId", "question_id", "metricId"))
        meta = resolveQuestionMeta(questionKey, questionMap or {})
        subIssueCode = firstPresent(row, ("subIssueCode", "sub_issue_code"), firstPresent(meta, ("subIssueCode", "sub_issue_code")))
        mappedAxis = str(firstPresent(row, ("mappedAxis", "mapped_axis"), firstPresent(meta, ("mappedAxis", "mapped_axis"), ""))).lower()
        respondentGroup = str(firstPresent(row, ("respondentGroup", "respondent_group"), firstPresent(meta, ("respondentGroup", "respondent_group"), ""))).lower()
        if not subIssueCode or mappedAxis not in VALID_AXES or respondentGroup not in VALID_RESPONDENT_GROUPS:
            continue
        normalized.append({
            "responseKey": responseKey,
            "subIssueCode": str(subIssueCode),
            "respondentGroup": respondentGroup,
            "mappedAxis": mappedAxis,
            "normalizedScore": normalizeScore(firstPresent(row, ("normalizedScore", "normalized_score", "score", "value"))),
            "departmentType": firstPresent(row, ("departmentType", "department_type"), firstPresent(meta, ("departmentType", "department_type"))),
            "externalSubtype": firstPresent(row, ("externalSubtype", "external_subtype"), firstPresent(meta, ("externalSubtype", "external_subtype"))),
            "priorityYn": normalizeBool(firstPresent(row, ("priorityYn", "priority_yn", "priority"), firstPresent(meta, ("priorityYn", "priority_yn", "priority")))),
        })
    return normalized


__all__ = ["step0NormalizeSurveyRows"]
