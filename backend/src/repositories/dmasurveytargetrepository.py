"""
dmasurveytargetrepository.py
레이어: Repository
역할: DMA 설문 참여 대상 그룹 및 인원 데이터 조회·저장.
"""
from src.utils.db import getConn

SURVEY_TARGET_GROUPS = ("employee", "management", "external")

_GET_TARGETS_SQL = """
SELECT respondent_group, target_count
FROM ESG_DMA_SURVEY_TARGET
WHERE esg_materiality_run_id = ?
  AND delete_yn = 0
"""

_SOFT_DELETE_TARGETS_SQL = """
UPDATE ESG_DMA_SURVEY_TARGET
SET delete_yn = 1
WHERE esg_materiality_run_id = ? AND delete_yn = 0
"""

_INSERT_TARGET_SQL = """
INSERT INTO ESG_DMA_SURVEY_TARGET
  (esg_materiality_run_id, respondent_group, target_count)
VALUES (?, ?, ?)
ON DUPLICATE KEY UPDATE
  target_count = VALUES(target_count),
  delete_yn = 0,
  updated_at = CURRENT_TIMESTAMP
"""


# run 기준 설문 참여 대상 그룹별 인원 조회 — 미등록 그룹은 0으로 기본값
def getTargetsByRunId(runId: int) -> dict:
    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_GET_TARGETS_SQL, (runId,))
            rows = cur.fetchall()
        result = {g: 0 for g in SURVEY_TARGET_GROUPS}
        for row in rows:
            result[row["respondent_group"]] = row["target_count"]
        return result
    finally:
        conn.close()


# run 기준 설문 참여 대상 소프트 삭제 후 upsert (트랜잭션 커서용)
def upsertTargetsTx(conn, runId: int, targets: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(_SOFT_DELETE_TARGETS_SQL, (runId,))
        for group in SURVEY_TARGET_GROUPS:
            if group in targets:
                cur.execute(_INSERT_TARGET_SQL, (runId, group, targets[group]))
