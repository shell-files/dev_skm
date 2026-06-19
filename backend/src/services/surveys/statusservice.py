"""
statusservice.py
레이어: Service (surveys)
역할: 설문 현황 서비스 — 그룹별 참여 현황·제출 상태 조회.
"""
from src.utils.db import getConn
from src.repositories.dmasurveyformrepository import getSurveyFormByRunId
from src.repositories.dmasurveytargetrepository import (
    SURVEY_TARGET_GROUPS,
    getTargetsByRunId,
    upsertTargetsTx,
)
from src.models.dmasurveyresponsestatus import (
    SurveyGroupStatusDto,
    SurveyResponseStatusDto,
    SurveyTotalsDto,
)

_GROUP_LABELS = {
    "employee": "임직원",
    "management": "경영진",
    "external": "외부이해관계자",
}

_RESPONSE_COUNT_SQL = """
SELECT
  respondent_group,
  COUNT(DISTINCT source_response_key) AS response_count
FROM ESG_DMA_SURVEY_RESPONSE
WHERE esg_materiality_run_id = ?
  AND survey_form_id = ?
  AND delete_yn = 0
GROUP BY respondent_group
"""


def _validateRunId(runId) -> None:
    if isinstance(runId, bool) or not isinstance(runId, int) or runId <= 0:
        raise ValueError(f"runId must be a positive int, got {runId!r}")


def _validateTargets(targets: dict) -> None:
    for group, count in targets.items():
        if group not in SURVEY_TARGET_GROUPS:
            raise ValueError(f"Invalid respondent_group: {group!r}")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(
                f"target_count for {group!r} must be a non-negative int, got {count!r}"
            )


def _buildGroups(targets: dict, counts: dict) -> dict:
    groups = {}
    for g in SURVEY_TARGET_GROUPS:
        tc = targets.get(g, 0)
        rc = counts.get(g, 0)
        rate = round(rc / tc, 4) if tc > 0 else 0.0
        groups[g] = SurveyGroupStatusDto(
            label=_GROUP_LABELS[g],
            targetCount=tc,
            responseCount=rc,
            responseRate=rate,
        )
    return groups


def getSurveyResponseStatus(runId: int) -> SurveyResponseStatusDto:
    _validateRunId(runId)

    form = getSurveyFormByRunId(runId)
    targets = getTargetsByRunId(runId)

    if form is None:
        groups = _buildGroups(targets, {})
        total_target = sum(g.targetCount for g in groups.values())
        return SurveyResponseStatusDto(
            runId=runId,
            surveyFormId=None,
            surveyStatus=None,
            masterSheetId=None,
            lastImportedAt=None,
            groups=groups,
            totals=SurveyTotalsDto(
                targetCount=total_target,
                responseCount=0,
                responseRate=0.0,
            ),
        )

    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_RESPONSE_COUNT_SQL, (runId, form["id"]))
            rows = cur.fetchall()
    finally:
        conn.close()

    counts = {g: 0 for g in SURVEY_TARGET_GROUPS}
    for row in rows:
        counts[row["respondent_group"]] = row["response_count"]

    groups = _buildGroups(targets, counts)
    total_target = sum(g.targetCount for g in groups.values())
    total_response = sum(g.responseCount for g in groups.values())
    total_rate = round(total_response / total_target, 4) if total_target > 0 else 0.0

    return SurveyResponseStatusDto(
        runId=runId,
        surveyFormId=form["id"],
        surveyStatus=form.get("survey_status"),
        masterSheetId=form.get("master_sheet_id"),
        lastImportedAt=None,
        groups=groups,
        totals=SurveyTotalsDto(
            targetCount=total_target,
            responseCount=total_response,
            responseRate=total_rate,
        ),
    )


def saveSurveyResponseTargets(runId: int, targets: dict) -> SurveyResponseStatusDto:
    _validateRunId(runId)
    _validateTargets(targets)

    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    conn.autocommit = False
    try:
        upsertTargetsTx(conn, runId, targets)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return getSurveyResponseStatus(runId)
