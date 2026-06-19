"""
dmaworkflowrepository.py
레이어: Repository
역할: DMA 워크플로우 단계 상태 조회 및 업데이트.
"""
from datetime import datetime
from typing import Optional

from src.utils.db import getConn

WORKFLOW_TYPES = frozenset({
    "BENCHMARK",
    "MEDIA",
    "SURVEY_FORM",
})

OVERALL_STATUSES = frozenset({
    "WAITING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "RETRYABLE",
})

PROGRESS_MODES = frozenset({
    "MILESTONE",
    "ACTUAL_COUNT",
})

_UPSERT_SQL = """
INSERT INTO ESG_DMA_WORKFLOW_STATUS (
    esg_materiality_run_id,
    workflow_type,
    overall_status,
    current_stage,
    progress_percent,
    progress_mode,
    processed_count,
    total_count,
    error_stage,
    error_message,
    started_at,
    completed_at,
    delete_yn
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
ON DUPLICATE KEY UPDATE
    overall_status = VALUES(overall_status),
    current_stage = VALUES(current_stage),
    progress_percent = VALUES(progress_percent),
    progress_mode = VALUES(progress_mode),
    processed_count = VALUES(processed_count),
    total_count = VALUES(total_count),
    error_stage = VALUES(error_stage),
    error_message = VALUES(error_message),
    started_at = CASE
        WHEN VALUES(started_at) IS NULL THEN started_at
        ELSE VALUES(started_at)
    END,
    completed_at = VALUES(completed_at),
    delete_yn = 0
"""

_SELECT_SQL = """
SELECT
    esg_materiality_run_id AS runId,
    workflow_type AS workflowType,
    overall_status AS overallStatus,
    current_stage AS currentStage,
    progress_percent AS progressPercent,
    progress_mode AS progressMode,
    processed_count AS processedCount,
    total_count AS totalCount,
    error_stage AS errorStage,
    error_message AS errorMessage,
    started_at AS startedAt,
    completed_at AS completedAt,
    updated_at AS updatedAt
FROM ESG_DMA_WORKFLOW_STATUS
WHERE esg_materiality_run_id = ?
  AND workflow_type = ?
  AND delete_yn = 0
"""


def _validateUpsertArgs(
    runId,
    workflowType: str,
    overallStatus: str,
    currentStage: str,
    progressPercent: int,
    progressMode: str,
    processedCount,
    totalCount,
) -> None:
    if isinstance(runId, bool) or not isinstance(runId, int):
        raise ValueError(f"runId must be a strict int, got {type(runId).__name__}")
    if runId <= 0:
        raise ValueError(f"runId must be > 0, got {runId}")
    if workflowType not in WORKFLOW_TYPES:
        raise ValueError(f"Invalid workflowType: {workflowType!r}. Allowed: {WORKFLOW_TYPES}")
    if overallStatus not in OVERALL_STATUSES:
        raise ValueError(f"Invalid overallStatus: {overallStatus!r}. Allowed: {OVERALL_STATUSES}")
    if progressMode not in PROGRESS_MODES:
        raise ValueError(f"Invalid progressMode: {progressMode!r}. Allowed: {PROGRESS_MODES}")
    if not currentStage or not currentStage.strip():
        raise ValueError("currentStage must not be blank")
    if not isinstance(progressPercent, int) or isinstance(progressPercent, bool):
        raise ValueError(f"progressPercent must be int, got {type(progressPercent).__name__}")
    if progressPercent < 0 or progressPercent > 100:
        raise ValueError(f"progressPercent must be 0..100, got {progressPercent}")
    if processedCount is not None:
        if isinstance(processedCount, bool) or not isinstance(processedCount, int):
            raise ValueError("processedCount must be int or None")
        if processedCount < 0:
            raise ValueError(f"processedCount must be >= 0, got {processedCount}")
    if totalCount is not None:
        if isinstance(totalCount, bool) or not isinstance(totalCount, int):
            raise ValueError("totalCount must be int or None")
        if totalCount < 0:
            raise ValueError(f"totalCount must be >= 0, got {totalCount}")
    if processedCount is not None and totalCount is not None:
        if processedCount > totalCount:
            raise ValueError(
                f"processedCount ({processedCount}) must be <= totalCount ({totalCount})"
            )


def upsertDmaWorkflowStatus(
    *,
    runId: int,
    workflowType: str,
    overallStatus: str,
    currentStage: str,
    progressPercent: int,
    progressMode: str = "MILESTONE",
    processedCount: Optional[int] = None,
    totalCount: Optional[int] = None,
    errorStage: Optional[str] = None,
    errorMessage: Optional[str] = None,
    startedYn: bool = False,
    completedYn: bool = False,
) -> None:
    _validateUpsertArgs(
        runId, workflowType, overallStatus, currentStage,
        progressPercent, progressMode, processedCount, totalCount,
    )

    started_at_val = datetime.now() if startedYn else None
    completed_at_val = datetime.now() if completedYn else None

    params = (
        runId,
        workflowType,
        overallStatus,
        currentStage,
        progressPercent,
        progressMode,
        processedCount,
        totalCount,
        errorStage,
        errorMessage,
        started_at_val,
        completed_at_val,
    )

    conn = getConn()
    if conn is None:
        raise RuntimeError("upsertDmaWorkflowStatus: DB connection unavailable")

    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_UPSERT_SQL, params)
        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise RuntimeError(f"upsertDmaWorkflowStatus failed: {e}") from e
    finally:
        try:
            conn.close()
        except Exception:
            pass


def getDmaWorkflowStatus(
    *,
    runId: int,
    workflowType: str,
) -> Optional[dict]:
    if isinstance(runId, bool) or not isinstance(runId, int):
        raise ValueError(f"runId must be a strict int, got {type(runId).__name__}")
    if runId <= 0:
        raise ValueError(f"runId must be > 0, got {runId}")
    if workflowType not in WORKFLOW_TYPES:
        raise ValueError(f"Invalid workflowType: {workflowType!r}")

    conn = getConn()
    if conn is None:
        raise RuntimeError("getDmaWorkflowStatus: DB connection unavailable")

    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT_SQL, (runId, workflowType))
            return cur.fetchone()
    except Exception as e:
        raise RuntimeError(f"getDmaWorkflowStatus failed: {e}") from e
    finally:
        try:
            conn.close()
        except Exception:
            pass


def getDmaWorkflowStatusOrDefault(
    *,
    runId: int,
    workflowType: str,
) -> dict:
    row = getDmaWorkflowStatus(runId=runId, workflowType=workflowType)
    if row is not None:
        return row
    return {
        "runId": runId,
        "workflowType": workflowType,
        "overallStatus": "WAITING",
        "currentStage": "PREPARE",
        "progressPercent": 0,
        "progressMode": "MILESTONE",
        "processedCount": None,
        "totalCount": None,
        "errorStage": None,
        "errorMessage": None,
        "startedAt": None,
        "completedAt": None,
        "updatedAt": None,
    }
