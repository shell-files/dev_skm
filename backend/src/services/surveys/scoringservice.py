from src.utils.dmaaggregator import SURVEY_GROUP_WEIGHTS
from src.utils.dmasurveyscorerepository import (
    getReadySurveyFormForScore,
    listActiveSurveyResponsesForScore,
    replaceSurveyScoresAndRecalculateFinalTx,
)
from src.models.dmasurveyscore import (
    SurveyScorePreviewDto,
    SurveyScoreRecalculateResultDto,
)

_SCORABLE_AXES = frozenset({"impact", "financial"})
_EXCLUDED_AXES = frozenset({"ranking", "common"})
_ALLOWED_AXES = _SCORABLE_AXES | _EXCLUDED_AXES
_ALLOWED_GROUPS = frozenset({"employee", "management", "external"})


def _validateScorableRows(rows: list) -> None:
    for row in rows:
        axis = row.get("mapped_axis") or ""
        group = row.get("respondent_group") or ""
        score = row.get("normalized_score")

        if axis not in _ALLOWED_AXES:
            raise RuntimeError(
                f"Invalid mapped_axis {axis!r} in row. "
                f"Allowed: {sorted(_ALLOWED_AXES)}"
            )
        if group not in _ALLOWED_GROUPS:
            raise RuntimeError(
                f"Invalid respondent_group {group!r} in row. "
                f"Allowed: {sorted(_ALLOWED_GROUPS)}"
            )
        if score is not None:
            try:
                score_f = float(score)
            except (TypeError, ValueError):
                raise RuntimeError(f"normalized_score {score!r} is not numeric")
            if score_f < 1.0 or score_f > 5.0:
                raise RuntimeError(
                    f"normalized_score {score_f} is outside valid range 1~5"
                )


def _calcRespondentAxisScores(scorable_rows: list) -> dict:
    buckets: dict = {}
    for row in scorable_rows:
        key = (
            row["source_response_key"],
            row["respondent_group"],
            row["sub_issue_code"],
            row["mapped_axis"],
        )
        if key not in buckets:
            buckets[key] = []
        buckets[key].append(float(row["normalized_score"]))

    return {key: sum(vals) / len(vals) for key, vals in buckets.items()}


def _calcGroupAxisScores(respondent_scores: dict) -> dict:
    buckets: dict = {}
    for (resp_key, group, sub_issue, axis), avg in respondent_scores.items():
        key = (sub_issue, axis, group)
        if key not in buckets:
            buckets[key] = []
        buckets[key].append(avg)

    return {key: sum(vals) / len(vals) for key, vals in buckets.items()}


def _weightedAvailable(group_scores: dict, weights: dict):
    weighted_sum = 0.0
    weight_sum = 0.0
    for group, weight in weights.items():
        score = group_scores.get(group)
        if score is not None:
            weighted_sum += score * weight
            weight_sum += weight
    return weighted_sum / weight_sum if weight_sum > 0.0 else None


def _calcSurveyStageScores(group_scores: dict) -> dict:
    sub_issues = set()
    for sub_issue, axis, group in group_scores:
        sub_issues.add(sub_issue)

    result = {}
    for sub_issue in sub_issues:
        impact_by_group = {
            g: group_scores.get((sub_issue, "impact", g))
            for g in _ALLOWED_GROUPS
        }
        financial_by_group = {
            g: group_scores.get((sub_issue, "financial", g))
            for g in _ALLOWED_GROUPS
        }
        survey_impact = _weightedAvailable(impact_by_group, SURVEY_GROUP_WEIGHTS)
        survey_financial = _weightedAvailable(financial_by_group, SURVEY_GROUP_WEIGHTS)

        if survey_impact is None and survey_financial is None:
            continue

        result[sub_issue] = {
            "surveyImpactScore": survey_impact,
            "surveyFinancialScore": survey_financial,
            "groupScores": {
                "impact": {g: group_scores.get((sub_issue, "impact", g)) for g in _ALLOWED_GROUPS},
                "financial": {g: group_scores.get((sub_issue, "financial", g)) for g in _ALLOWED_GROUPS},
            },
        }

    return result


def _buildSurveyScoreBundle(*, runId: int, surveyForm: dict, rows: list) -> dict:
    _validateScorableRows(rows)

    scorable = []
    excluded = []
    for row in rows:
        axis = row.get("mapped_axis") or ""
        sub_issue = row.get("sub_issue_code") or None
        score = row.get("normalized_score")

        if axis in _SCORABLE_AXES and sub_issue and score is not None:
            scorable.append({
                "source_response_key": row.get("source_response_key"),
                "respondent_group": row.get("respondent_group"),
                "sub_issue_code": sub_issue,
                "mapped_axis": axis,
                "normalized_score": float(score),
            })
        else:
            excluded.append(row)

    respondent_scores = _calcRespondentAxisScores(scorable)
    group_scores = _calcGroupAxisScores(respondent_scores)
    stage_scores = _calcSurveyStageScores(group_scores)

    scores_list = [
        {
            "subIssueCode": code,
            "surveyImpactScore": data["surveyImpactScore"],
            "surveyFinancialScore": data["surveyFinancialScore"],
            "groupScores": data["groupScores"],
        }
        for code, data in stage_scores.items()
    ]

    return {
        "runId": runId,
        "surveyFormId": surveyForm["id"],
        "activeResponseCount": len(rows),
        "scorableResponseCount": len(scorable),
        "excludedResponseCount": len(excluded),
        "scoredSubIssueCount": len(stage_scores),
        "scores": scores_list,
    }


def previewSurveyScores(runId: int) -> SurveyScorePreviewDto:
    survey_form = getReadySurveyFormForScore(runId)
    rows = listActiveSurveyResponsesForScore(
        runId=runId,
        surveyFormId=survey_form["id"],
    )
    bundle = _buildSurveyScoreBundle(
        runId=runId,
        surveyForm=survey_form,
        rows=rows,
    )
    return SurveyScorePreviewDto(**bundle)


def recalculateSurveyScoresForRun(runId: int) -> SurveyScoreRecalculateResultDto:
    survey_form = getReadySurveyFormForScore(runId)
    rows = listActiveSurveyResponsesForScore(
        runId=runId,
        surveyFormId=survey_form["id"],
    )
    bundle = _buildSurveyScoreBundle(
        runId=runId,
        surveyForm=survey_form,
        rows=rows,
    )

    survey_scores = [
        {
            "subIssueCode": s["subIssueCode"],
            "surveyImpactScore": s["surveyImpactScore"],
            "surveyFinancialScore": s["surveyFinancialScore"],
        }
        for s in bundle["scores"]
    ]

    tx_result = replaceSurveyScoresAndRecalculateFinalTx(
        runId=runId,
        surveyScores=survey_scores,
    )

    return SurveyScoreRecalculateResultDto(
        runId=runId,
        surveyFormId=survey_form["id"],
        activeResponseCount=bundle["activeResponseCount"],
        scorableResponseCount=bundle["scorableResponseCount"],
        excludedResponseCount=bundle["excludedResponseCount"],
        scoredSubIssueCount=bundle["scoredSubIssueCount"],
        affectedSubIssueCount=tx_result["affectedSubIssueCount"],
        finalRecalculatedCount=tx_result["finalRecalculatedCount"],
        rankUpdatedCount=tx_result["rankUpdatedCount"],
        status="OK",
    )
