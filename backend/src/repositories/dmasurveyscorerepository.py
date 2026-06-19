"""
dmasurveyscorerepository.py
레이어: Repository
역할: DMA 설문 응답 점수 계산 및 저장.
"""
from src.utils.db import getConn
from src.utils.dmaaggregator import calcFinal
from src.repositories.dmasurveyvalidation import validateRunId as _validateRunId, validateFormId as _validateFormId

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
  AND delete_yn = 0
  AND (survey_impact_score IS NOT NULL OR survey_financial_score IS NOT NULL)
"""

_CLEAR_STALE_SURVEY_ALL_SQL = """
UPDATE ESG_DMA_SCORE_SUMMARY
SET survey_impact_score = NULL,
    survey_financial_score = NULL
WHERE esg_materiality_run_id = ?
  AND delete_yn = 0
  AND (survey_impact_score IS NOT NULL OR survey_financial_score IS NOT NULL)
"""

_UPSERT_SURVEY_SCORE_SQL = """
INSERT INTO ESG_DMA_SCORE_SUMMARY (
    esg_materiality_run_id,
    sub_issue_code,
    survey_impact_score,
    survey_financial_score,
    delete_yn
)
VALUES (?, ?, ?, ?, 0)
ON DUPLICATE KEY UPDATE
    survey_impact_score = VALUES(survey_impact_score),
    survey_financial_score = VALUES(survey_financial_score),
    delete_yn = 0
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
  AND delete_yn = 0
  AND sub_issue_code IN ({placeholders})
"""

_UPDATE_FINAL_SQL = """
UPDATE ESG_DMA_SCORE_SUMMARY
SET final_impact_score = ?,
    final_financial_score = ?,
    final_score = ?
WHERE esg_materiality_run_id = ?
  AND sub_issue_code = ?
  AND delete_yn = 0
"""

_RESET_RANK_SQL = """
UPDATE ESG_DMA_SCORE_SUMMARY
SET rank_no = NULL
WHERE esg_materiality_run_id = ? AND delete_yn = 0
"""

_SELECT_RANKED_IDS_SQL = """
SELECT id
FROM ESG_DMA_SCORE_SUMMARY
WHERE esg_materiality_run_id = ?
  AND delete_yn = 0
  AND final_score IS NOT NULL
ORDER BY final_score DESC, sub_issue_code ASC
"""

_UPDATE_RANK_SQL = """
UPDATE ESG_DMA_SCORE_SUMMARY
SET rank_no = ?
WHERE id = ?
"""




# None이면 None, 아니면 float 변환
def _toFloat(val):
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# runId 기준 READY 상태 설문 폼 단건 조회 (점수 계산용)
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


# run·폼 기준 활성 설문 응답 목록 조회 (점수 계산용)
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


# 설문 점수 교체 및 최종 점수·순위 재계산 (트랜잭션)
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

        # 5단계: 기존 설문 점수 보유 서브이슈 조회
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT_EXISTING_SURVEY_CODES_SQL, (runId,))
            existing_rows = cur.fetchall()
        existing_codes = [r["sub_issue_code"] for r in existing_rows]

        # 6단계: 영향 코드 = 기존 + 활성 합집합
        affected_codes = list(set(existing_codes) | set(active_codes))

        # 7단계: 활성 외 기존 설문 점수 클리어
        with conn.cursor() as cur:
            if active_codes:
                ph = ",".join(["?"] * len(active_codes))
                cur.execute(
                    f"UPDATE ESG_DMA_SCORE_SUMMARY "
                    f"SET survey_impact_score = NULL, survey_financial_score = NULL "
                    f"WHERE esg_materiality_run_id = ? "
                    f"AND delete_yn = 0 "
                    f"AND (survey_impact_score IS NOT NULL OR survey_financial_score IS NOT NULL) "
                    f"AND sub_issue_code NOT IN ({ph})",
                    (runId, *active_codes),
                )
            else:
                cur.execute(_CLEAR_STALE_SURVEY_ALL_SQL, (runId,))

        # 8단계: 설문 점수 upsert
        if surveyScores:
            upsert_params = [
                (runId, s["subIssueCode"], s.get("surveyImpactScore"), s.get("surveyFinancialScore"))
                for s in surveyScores
            ]
            with conn.cursor() as cur:
                cur.executemany(_UPSERT_SURVEY_SCORE_SQL, upsert_params)

        # 9-11단계: 영향 받는 서브이슈 최종 점수 재계산
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

        # 12단계: rank_no 초기화
        with conn.cursor() as cur:
            cur.execute(_RESET_RANK_SQL, (runId,))

        # 12단계 (계속): final_score 내림차순 순위 재부여
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
