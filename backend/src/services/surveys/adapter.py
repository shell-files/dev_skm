<<<<<<< HEAD
"""
adapter.py
레이어: Service (surveys)
역할: 설문 응답 데이터 어댑터 — 외부 데이터 포맷을 내부 DTO로 변환.
"""
from typing import Any, Mapping, Optional

from src.utils.typeutils import firstPresent
=======
from typing import Any, Mapping, Optional

>>>>>>> origin/skm_test

VALID_RESPONDENT_GROUPS = {"employee", "management", "external"}
VALID_AXES = {"impact", "financial"}


<<<<<<< HEAD
def normalizeScore(value: Any) -> Optional[float]:
    """숫자로 변환 가능한 값은 float으로, 그 외는 None으로 반환한다."""
=======
def firstPresent(row: Mapping[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return default


def normalizeScore(value: Any) -> Optional[float]:
>>>>>>> origin/skm_test
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalizeBool(value: Any) -> bool:
<<<<<<< HEAD
    """문자열 '1'·'true'·'y'·'priority' 등을 True로 정규화한다."""
=======
>>>>>>> origin/skm_test
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "y", "yes", "priority"}


def resolveQuestionMeta(rawRowsKey: Any, questionMap: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
<<<<<<< HEAD
    """questionKey로 메타 딕셔너리를 조회하고, 없으면 빈 딕셔너리를 반환한다."""
=======
>>>>>>> origin/skm_test
    if rawRowsKey is None:
        return {}
    return questionMap.get(str(rawRowsKey), {})


<<<<<<< HEAD
=======
# STEP 0 internal helper. Decides why a survey row is excluded.
# Input: mapped row interpretation.
# Output: skipReason or None.
>>>>>>> origin/skm_test
def getSkipReason(
    *,
    subIssueCode: Any,
    mappedAxis: str,
    respondentGroup: str,
) -> Optional[str]:
<<<<<<< HEAD
    """필수 필드 누락 또는 허용되지 않은 값이 있으면 skip 사유 코드를 반환하고, 정상이면 None을 반환한다."""
=======
>>>>>>> origin/skm_test
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


<<<<<<< HEAD
def step0NormalizeSurveyRows(rawRows: list, questionMap: Mapping[str, Mapping[str, Any]]) -> dict:
    """원시 설문 행을 내부 DTO 포맷으로 정규화하고, 필수 필드 누락 행은 skippedRows로 분리해 반환한다."""
=======
# STEP 0. Normalizes survey source rows into overlay input rows.
# Input: external response rows and question map.
# Output: normalizedRows and skippedRows. Invalid rows are never silently dropped.
def step0NormalizeSurveyRows(rawRows: list, questionMap: Mapping[str, Mapping[str, Any]]) -> dict:
>>>>>>> origin/skm_test
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
