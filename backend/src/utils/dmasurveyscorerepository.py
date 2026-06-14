from src.utils.db import getConn
from src.utils.dmaaggregator import calcFinal

_SELECT_READY_FORM_SQL = """
SELECT
    id,
    esg_materiality_run_id,
    survey_status,
    master_sheet_id
FROM ESG_DMA_SURVEY_FORM
WHERE esg_materiality_run_id = ?
  AND survey_status = 'READY'
  AND delete_yn = 0
"""

_SELECT_ACTIVE_RESPONSES_SQL = """
SELECT
    id,
    esg_materiality_run_id,
    survey_form_id,
    question_code,
    mapped_axis,
    respondent_group,
    source_response_key,
    department_code,
    sub_issue_code,
    answer_numeric,
    answer_text,
    normalized_score
FROM ESG_DMA_SURVEY_RESPONSE
WHERE esg_materiality_run_id = ?
  AND survey_form_id = ?
  AND delete_yn = 0
"""

_SELECT_EXISTING_SURVEY_CODES_SQL = """
SELECT sub_issue_code
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = ?
  AND (survey_impact_score IS NOT NULL OR survey_financial_score IS NOT NULL)
"""

_CLEAR_STALE_SURVEY_ALL_SQL = """
UPDATE ESG_DMA_SCORE_SUMMARY
SET survey_impact_score = NULL,
    survey_financial_score = NULL
WHERE esg_materiality_run_id = ?
  AND (survey_impact_score IS NOT NULL OR survey_financial_score IS NOT NULL)
"""

_UPSERT_SURVEY_SCORE_SQL = """
INSERT INTO ESG_DMA_SCORE_SUMMARY (
    esg_materiality_run_id,
    sub_issue_code,
    survey_impact_score,
    survey_financial_score
)
VALUES (?, ?, ?, ?)
ON DUPLICATE KEY UPDATE
    survey_impact_score = VALUES(survey_impact_score),
    survey_financial_score = VALUES(survey_financial_score)
"""

_SELECT_SUMMARY_FOR_FINAL_SQL = """
SELECT
    sub_issue_code,
    benchmark_impact_score,
    benchmark_financial_score,
    media_external_impact_score,
    media_external_financial_score,
    survey_impact_score,
    survey_financial_score,
    context_impact_modifier,
    context_financial_modifier
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = ?
  AND sub_issue_code IN ({placeholders})
"""

_UPDATE_FINAL_SQL = """
UPDATE ESG_DMA_SCORE_SUMMARY
SET final_impact_score = ?,
    final_financial_score = ?,
    final_score = ?
WHERE esg_materiality_run_id = ?
  AND sub_issue_code = ?
"""

_RESET_RANK_SQL = """
UPDATE ESG_DMA_SCORE_SUMMARY
SET rank_no = NULL
WHERE esg_materiality_run_id = ?
"""

_SELECT_RANKED_IDS_SQL = """
SELECT id
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = ?
  AND final_score IS NOT NULL
ORDER BY final_score DESC, sub_issue_code ASC
"""

_UPDATE_RANK_SQL = """
UPDATE ESG_DMA_SCORE_SUMMARY
SET rank_no = ?
WHERE id = ?
"""


def _validateRunId(runId) -> None:
    if isinstance(runId, bool) or not isinstance(runId, int):
        raise ValueError(f"runId must be a strict int, got {type(runId).__name__}")
    if runId <= 0:
        raise ValueError(f"runId must be > 0, got {runId}")


def _validateFormId(formId) -> None:
    if isinstance(formId, bool) or not isinstance(formId, int):
        raise ValueError(f"surveyFormId must be a strict int, got {type(formId).__name__}")
    if formId <= 0:
        raise ValueError(f"surveyFormId must be > 0, got {formId}")


def _toFloat(val):
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def getReadySurveyFormForScore(runId: int) -> dict:
    _validateRunId(runId)
    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT_READY_FORM_SQL, (runId,))
            row = cur.fetchone()
        if row is None:
            raise RuntimeError(
                f"No READY survey form found for runId={runId}."
                " Survey form generation (C4.0) must complete before scoring."
            )
        return dict(row)
    finally:
        conn.close()


def listActiveSurveyResponsesForScore(*, runId: int, surveyFormId: int) -> list:
    _validateRunId(runId)
    _validateFormId(surveyFormId)
    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT_ACTIVE_RESPONSES_SQL, (runId, surveyFormId))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def replaceSurveyScoresAndRecalculateFinalTx(
    *,
    runId: int,
    surveyScores: list,
) -> dict:
    _validateRunId(runId)
    if not isinstance(surveyScores, list):
        raise ValueError("surveyScores must be a list")
    for i, s in enumerate(surveyScores):
        if not s.get("subIssueCode"):
            raise ValueError(f"surveyScores[{i}] missing subIssueCode")

    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    conn.autocommit = False
    try:
        active_codes = [s["subIssueCode"] for s in surveyScores]

        # Step 5: existing sub_issues with survey scores
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT_EXISTING_SURVEY_CODES_SQL, (runId,))
            existing_rows = cur.fetchall()
        existing_codes = [r["sub_issue_code"] for r in existing_rows]

        # Step 6: affected = union of existing + active
        affected_codes = list(set(existing_codes) | set(active_codes))

        # Step 7: stale survey score cleanup
        with conn.cursor() as cur:
            if active_codes:
                ph = ",".join(["?"] * len(active_codes))
                cur.execute(
                    f"UPDATE ESG_DMA_SCORE_SUMMARY "
                    f"SET survey_impact_score = NULL, survey_financial_score = NULL "
                    f"WHERE esg_materiality_run_id = ? "
                    f"AND (survey_impact_score IS NOT NULL OR survey_financial_score IS NOT NULL) "
                    f"AND sub_issue_code NOT IN ({ph})",
                    (runId, *active_codes),
                )
            else:
                cur.execute(_CLEAR_STALE_SURVEY_ALL_SQL, (runId,))

        # Step 8: survey scores upsert
        if surveyScores:
            upsert_params = [
                (runId, s["subIssueCode"], s.get("surveyImpactScore"), s.get("surveyFinancialScore"))
                for s in surveyScores
            ]
            with conn.cursor() as cur:
                cur.executemany(_UPSERT_SURVEY_SCORE_SQL, upsert_params)

        # Steps 9-11: final score recalculation for affected sub_issues
        final_recalculated = 0
        if affected_codes:
            ph = ",".join(["?"] * len(affected_codes))
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    _SELECT_SUMMARY_FOR_FINAL_SQL.format(placeholders=ph),
                    (runId, *affected_codes),
                )
                summary_rows = cur.fetchall()

            update_params = []
            for row in summary_rows:
                final = calcFinal(
                    subIssueCode=row["sub_issue_code"],
                    surveyImpact=_toFloat(row.get("survey_impact_score")),
                    surveyFinancial=_toFloat(row.get("survey_financial_score")),
                    benchmarkImpact=_toFloat(row.get("benchmark_impact_score")),
                    benchmarkFinancial=_toFloat(row.get("benchmark_financial_score")),
                    mediaImpact=_toFloat(row.get("media_external_impact_score")),
                    mediaFinancial=_toFloat(row.get("media_external_financial_score")),
                    contextImpactModifier=float(row.get("context_impact_modifier") or 0.0),
                    contextFinancialModifier=float(row.get("context_financial_modifier") or 0.0),
                )
                update_params.append((
                    final.finalImpactScore,
                    final.finalFinancialScore,
                    final.finalScore,
                    runId,
                    row["sub_issue_code"],
                ))

            if update_params:
                with conn.cursor() as cur:
                    cur.executemany(_UPDATE_FINAL_SQL, update_params)
                final_recalculated = len(update_params)

        # Step 12: rank_no reset
        with conn.cursor() as cur:
            cur.execute(_RESET_RANK_SQL, (runId,))

        # Step 12 (cont): re-rank by final_score DESC, sub_issue_code ASC
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT_RANKED_IDS_SQL, (runId,))
            ranked_rows = cur.fetchall()

        rank_updated = 0
        if ranked_rows:
            rank_params = [(i + 1, r["id"]) for i, r in enumerate(ranked_rows)]
            with conn.cursor() as cur:
                cur.executemany(_UPDATE_RANK_SQL, rank_params)
            rank_updated = len(rank_params)

        conn.commit()
        return {
            "insertedCount": len(surveyScores),
            "affectedSubIssueCount": len(affected_codes),
            "finalRecalculatedCount": final_recalculated,
            "rankUpdatedCount": rank_updated,
        }

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()
