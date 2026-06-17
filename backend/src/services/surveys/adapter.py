from typing import Any, Mapping, Optional

from src.utils.typeutils import firstPresent

VALID_RESPONDENT_GROUPS = {"employee", "management", "external"}
VALID_AXES = {"impact", "financial"}


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


# STEP 0 internal helper. Decides why a survey row is excluded.
# Input: mapped row interpretation.
# Output: skipReason or None.
def getSkipReason(
    *,
    subIssueCode: Any,
    mappedAxis: str,
    respondentGroup: str,
) -> Optional[str]:
    if not subIssueCode:
        return "SUB_ISSUE_CODE_MISSING"
    if not mappedAxis:
        return "MAPPED_AXIS_MISSING"
    if mappedAxis not in VALID_AXES:
        return "MAPPED_AXIS_INVALID"
    if not respondentGroup:
        return "RESPONDENT_GROUP_MISSING"
    if respondentGroup not in VALID_RESPONDENT_GROUPS:
        return "RESPONDENT_GROUP_INVALID"
    return None


# STEP 0. Normalizes survey source rows into overlay input rows.
# Input: external response rows and question map.
# Output: normalizedRows and skippedRows. Invalid rows are never silently dropped.
def step0NormalizeSurveyRows(rawRows: list, questionMap: Mapping[str, Mapping[str, Any]]) -> dict:
    normalized: list[dict] = []
    skipped: list[dict] = []
    for rowIndex, row in enumerate(rawRows or []):
        if not isinstance(row, Mapping):
            skipped.append({
                "rowIndex": rowIndex,
                "responseKey": None,
                "questionKey": None,
                "skipReason": "RAW_ROW_INVALID",
            })
            continue
        responseKey = firstPresent(row, ("responseKey", "response_key", "id", "questionKey", "question_key"))
        questionKey = firstPresent(row, ("questionKey", "question_key", "questionId", "question_id", "metricId"))
        meta = resolveQuestionMeta(questionKey, questionMap or {})
        subIssueCode = firstPresent(row, ("subIssueCode", "sub_issue_code"), firstPresent(meta, ("subIssueCode", "sub_issue_code")))
        mappedAxis = str(firstPresent(row, ("mappedAxis", "mapped_axis"), firstPresent(meta, ("mappedAxis", "mapped_axis"), ""))).lower()
        respondentGroup = str(firstPresent(row, ("respondentGroup", "respondent_group"), firstPresent(meta, ("respondentGroup", "respondent_group"), ""))).lower()
        skipReason = getSkipReason(
            subIssueCode=subIssueCode,
            mappedAxis=mappedAxis,
            respondentGroup=respondentGroup,
        )
        if skipReason:
            skipped.append({
                "rowIndex": rowIndex,
                "responseKey": responseKey,
                "questionKey": questionKey,
                "skipReason": skipReason,
            })
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
    return {"normalizedRows": normalized, "skippedRows": skipped}


__all__ = ["step0NormalizeSurveyRows"]
