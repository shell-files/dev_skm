"""
dmasurveyresponserepository.py
레이어: Repository
역할: DMA 설문 응답 데이터 저장·조회·제출 DB 처리.
"""
from src.utils.db import getConn
from src.repositories.dmasurveyvalidation import validateRunId as _validateRunId, validateFormId as _validateFormId

_ALLOWED_RESPONDENT_GROUPS = frozenset({"employee", "management", "external"})

_SELECT_READY_FORM_SQL = """
SELECT
    id, esg_materiality_run_id, master_sheet_id, survey_status,
    employee_form_url, management_form_url, external_form_url
FROM ESG_DMA_SURVEY_FORM
WHERE esg_materiality_run_id = ?
  AND survey_status = 'READY'
  AND delete_yn = 0
"""

_DELETE_RESPONSES_SQL = """
UPDATE ESG_DMA_SURVEY_RESPONSE
SET delete_yn = 1
WHERE survey_form_id = ?
  AND esg_materiality_run_id = ?
  AND delete_yn = 0
"""

_INSERT_RESPONSE_SQL = """
INSERT INTO ESG_DMA_SURVEY_RESPONSE (
    esg_materiality_run_id,
    survey_form_id,
    question_code,
    mapped_axis,
    respondent_group,
    source_response_key,
    respondent_user_id,
    department_code,
    sub_issue_code,
    answer_numeric,
    answer_text,
    normalized_score,
    delete_yn
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
"""


# runId 기준 READY 상태 설문 폼 단건 조회 — 없으면 RuntimeError
def getReadySurveyFormForRun(runId: int) -> dict:
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
                " Ensure survey form generation (C4.0) has completed."
            )
        return dict(row)
    finally:
        conn.close()


# 폼·run 기준 설문 응답 전체 교체 — 기존 행 소프트 삭제 후 재삽입 (트랜잭션)
def replaceSurveyResponsesForFormTx(
    *,
    runId: int,
    surveyFormId: int,
    rows: list,
) -> dict:
    _validateRunId(runId)
    _validateFormId(surveyFormId)
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")

    # 필수 필드 유효성 검증
    required_fields = {
        "runId", "surveyFormId", "questionCode",
        "mappedAxis", "respondentGroup", "sourceResponseKey",
    }
    for i, row in enumerate(rows):
        missing = required_fields - set(row.keys())
        if missing:
            raise ValueError(
                f"Row[{i}] missing required fields: {sorted(missing)}"
            )
        if row["respondentGroup"] not in _ALLOWED_RESPONDENT_GROUPS:
            raise ValueError(
                f"Row[{i}] invalid respondentGroup: {row['respondentGroup']!r}"
            )

    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    conn.autocommit = False
    deleted_count = 0
    try:
        # 1단계: 폼·run 기준 기존 응답 행 소프트 삭제 (멱등)
        with conn.cursor() as cur:
            cur.execute(_DELETE_RESPONSES_SQL, (surveyFormId, runId))
            deleted_count = cur.rowcount if cur.rowcount is not None else 0

        # 2단계: 새 응답 행 일괄 삽입
        if rows:
            params = [
                (
                    row["runId"],
                    row["surveyFormId"],
                    row["questionCode"],
                    row["mappedAxis"],
                    row["respondentGroup"],
                    row["sourceResponseKey"],
                    row.get("respondentUserId"),
                    row.get("departmentCode"),
                    row.get("subIssueCode"),
                    row.get("answerNumeric"),
                    row.get("answerText"),
                    row.get("normalizedScore"),
                )
                for row in rows
            ]
            with conn.cursor() as cur:
                cur.executemany(_INSERT_RESPONSE_SQL, params)

        conn.commit()
        return {"insertedCount": len(rows), "deletedCount": deleted_count, "updatedCount": 0}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()
