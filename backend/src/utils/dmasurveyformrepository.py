import json

from src.utils.db import getConn

SURVEY_FORM_STATUSES = frozenset({
    "GENERATING",
    "READY",
    "RETRYABLE",
    "CLOSED",
})

SURVEY_FORM_WORKFLOW_TYPE = "SURVEY_FORM"
SURVEY_TEMPLATE_VERSION = "v2"

_TOP20_SQL = """
SELECT
    s.sub_issue_code,
    m.sub_issue_name_kr,
    s.rank_no,
    s.final_impact_score,
    s.final_financial_score,
    s.final_score
FROM ESG_DMA_SCORE_SUMMARY s
INNER JOIN ESG_SUB_ISSUE_MASTER m
        ON m.sub_issue_code = s.sub_issue_code
WHERE s.esg_materiality_run_id = ?
  AND s.rank_no IS NOT NULL
ORDER BY s.rank_no ASC, s.sub_issue_code ASC
LIMIT 20
"""

_INSERT_FORM_SQL = """
INSERT INTO ESG_DMA_SURVEY_FORM (
    esg_materiality_run_id,
    template_version,
    survey_status,
    top20_snapshot_json,
    delete_yn
)
VALUES (?, ?, 'GENERATING', ?, 0)
"""

_SELECT_FORM_SQL = """
SELECT
    id, esg_materiality_run_id, template_version, survey_status,
    top20_snapshot_json, master_sheet_id, employee_form_url,
    management_form_url, external_form_url, error_message,
    generated_at, created_at, updated_at, delete_yn
FROM ESG_DMA_SURVEY_FORM
WHERE esg_materiality_run_id = ?
  AND delete_yn = 0
"""

_SELECT_FORM_FOR_UPDATE_SQL = """
SELECT
    id, esg_materiality_run_id, template_version, survey_status,
    top20_snapshot_json, master_sheet_id, employee_form_url,
    management_form_url, external_form_url, error_message,
    generated_at, created_at, updated_at, delete_yn
FROM ESG_DMA_SURVEY_FORM
WHERE esg_materiality_run_id = ?
  AND delete_yn = 0
FOR UPDATE
"""

_UPDATE_READY_SQL = """
UPDATE ESG_DMA_SURVEY_FORM
SET survey_status = 'READY',
    master_sheet_id = ?,
    employee_form_url = ?,
    management_form_url = ?,
    external_form_url = ?,
    error_message = NULL,
    generated_at = CURRENT_TIMESTAMP
WHERE id = ?
  AND delete_yn = 0
"""

_UPDATE_RETRYABLE_SQL = """
UPDATE ESG_DMA_SURVEY_FORM
SET survey_status = 'RETRYABLE',
    error_message = ?
WHERE id = ?
  AND delete_yn = 0
"""

_CLAIM_RETRYABLE_SQL = """
UPDATE ESG_DMA_SURVEY_FORM
SET survey_status = 'GENERATING'
WHERE id = ?
  AND survey_status = 'RETRYABLE'
  AND delete_yn = 0
"""


def _validateRunId(runId) -> None:
    if isinstance(runId, bool) or not isinstance(runId, int):
        raise ValueError(f"runId must be a strict int, got {type(runId).__name__}")
    if runId <= 0:
        raise ValueError(f"runId must be > 0, got {runId}")


def _parseSnapshot(raw) -> list:
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, list):
        return raw
    return []


def findSurveyRunContext(runId: int) -> dict:
    _validateRunId(runId)
    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id AS runId, company_id AS companyId, reporting_year AS reportingYear"
                " FROM ESG_MATERIALITY_RUN WHERE id = ? AND delete_yn = 0",
                (runId,),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"ESG_MATERIALITY_RUN row not found for runId={runId}")
        return dict(row)
    finally:
        conn.close()


def getSurveyFormByRunId(runId: int) -> "dict | None":
    _validateRunId(runId)
    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT_FORM_SQL, (runId,))
            row = cur.fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()


def getOrFreezeSurveyFormSnapshotTx(*, runId: int, templateVersion: str) -> dict:
    _validateRunId(runId)
    if not templateVersion or not templateVersion.strip():
        raise ValueError("templateVersion must not be blank")

    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    conn.autocommit = False
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_SELECT_FORM_FOR_UPDATE_SQL, (runId,))
            existing = cur.fetchone()

        if existing is not None:
            status = existing["survey_status"]
            if status == "GENERATING":
                conn.rollback()
                raise RuntimeError(
                    f"Survey form generation already in progress for runId={runId}"
                )
            if status == "CLOSED":
                conn.rollback()
                raise RuntimeError(
                    f"Survey form is CLOSED and cannot be regenerated for runId={runId}"
                )
            # READY or RETRYABLE — return existing snapshot
            conn.commit()
            snapshot = _parseSnapshot(existing["top20_snapshot_json"])
            result = dict(existing)
            result["snapshot"] = snapshot
            result["surveyStatus"] = status
            return result

        # No existing row — query Top20 and insert
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_TOP20_SQL, (runId,))
            rows = cur.fetchall()

        if len(rows) != 20:
            conn.rollback()
            raise RuntimeError(
                f"Top20 snapshot requires exactly 20 rows with rank_no IS NOT NULL,"
                f" got {len(rows)} for runId={runId}"
            )

        codes_seen = set()
        for row in rows:
            code = row["sub_issue_code"]
            if code in codes_seen:
                conn.rollback()
                raise RuntimeError(
                    f"Duplicate sub_issue_code in Top20 snapshot: {code!r}"
                )
            codes_seen.add(code)
            rank = row["rank_no"]
            if rank is None:
                conn.rollback()
                raise RuntimeError("rank_no IS NULL found in Top20 snapshot row")
            if int(rank) <= 0:
                conn.rollback()
                raise RuntimeError(
                    f"rank_no must be positive, got {rank}"
                )

        snapshot = [
            {
                "rankNo": int(row["rank_no"]),
                "subIssueCode": row["sub_issue_code"],
                "subIssueName": row["sub_issue_name_kr"],
                "finalImpactScore": float(row["final_impact_score"]) if row["final_impact_score"] is not None else None,
                "finalFinancialScore": float(row["final_financial_score"]) if row["final_financial_score"] is not None else None,
                "finalScore": float(row["final_score"]) if row["final_score"] is not None else None,
            }
            for row in rows
        ]

        snapshot_json = json.dumps(
            snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        with conn.cursor(dictionary=True) as cur:
            cur.execute(_INSERT_FORM_SQL, (runId, templateVersion, snapshot_json))
            new_id = cur.lastrowid

        conn.commit()

        return {
            "id": new_id,
            "esg_materiality_run_id": runId,
            "template_version": templateVersion,
            "survey_status": "GENERATING",
            "surveyStatus": "GENERATING",
            "top20_snapshot_json": snapshot_json,
            "snapshot": snapshot,
            "master_sheet_id": None,
            "employee_form_url": None,
            "management_form_url": None,
            "external_form_url": None,
            "error_message": None,
            "generated_at": None,
            "updated_at": None,
        }

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def claimRetryableSurveyFormTx(formId: int) -> None:
    if isinstance(formId, bool) or not isinstance(formId, int):
        raise ValueError(f"formId must be a strict int, got {type(formId).__name__}")
    if formId <= 0:
        raise ValueError(f"formId must be > 0, got {formId}")

    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    conn.autocommit = False
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(_CLAIM_RETRYABLE_SQL, (formId,))
            if cur.rowcount != 1:
                conn.rollback()
                raise RuntimeError(
                    f"Failed to claim RETRYABLE form id={formId}:"
                    f" rowcount={cur.rowcount} (status may have changed)"
                )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def markSurveyFormReadyTx(
    *,
    formId: int,
    masterSheetId: str,
    employeeFormUrl: str,
    managementFormUrl: str,
    externalFormUrl: str,
) -> None:
    if isinstance(formId, bool) or not isinstance(formId, int) or formId <= 0:
        raise ValueError(f"formId must be a positive int, got {formId!r}")
    if not masterSheetId or not masterSheetId.strip():
        raise ValueError("masterSheetId must not be blank")
    if not employeeFormUrl or not employeeFormUrl.strip():
        raise ValueError("employeeFormUrl must not be blank")
    if not managementFormUrl or not managementFormUrl.strip():
        raise ValueError("managementFormUrl must not be blank")
    if not externalFormUrl or not externalFormUrl.strip():
        raise ValueError("externalFormUrl must not be blank")

    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection unavailable")
    conn.autocommit = False
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                _UPDATE_READY_SQL,
                (masterSheetId, employeeFormUrl, managementFormUrl, externalFormUrl, formId),
            )
            if cur.rowcount != 1:
                conn.rollback()
                raise RuntimeError(
                    f"markSurveyFormReadyTx rowcount mismatch: expected 1, got {cur.rowcount}"
                    f" for formId={formId}"
                )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def markSurveyFormRetryableBestEffort(*, formId: int, errorMessage: str) -> None:
    truncated = str(errorMessage or "")[:1000]
    try:
        conn = getConn()
        if conn is None:
            print(f"[WARN] markSurveyFormRetryableBestEffort: DB unavailable for formId={formId}")
            return
        conn.autocommit = False
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(_UPDATE_RETRYABLE_SQL, (truncated, formId))
            conn.commit()
        except Exception as inner:
            try:
                conn.rollback()
            except Exception:
                pass
            print(f"[WARN] markSurveyFormRetryableBestEffort failed for formId={formId}: {inner}")
        finally:
            conn.close()
    except Exception as outer:
        print(f"[WARN] markSurveyFormRetryableBestEffort outer failure for formId={formId}: {outer}")


def toSurveyFormResponse(row: dict) -> dict:
    snapshot_raw = row.get("top20_snapshot_json")
    if isinstance(snapshot_raw, str):
        try:
            snapshot = json.loads(snapshot_raw)
        except Exception:
            snapshot = []
    elif isinstance(snapshot_raw, list):
        snapshot = snapshot_raw
    else:
        snapshot = []

    return {
        "id": row["id"],
        "runId": row["esg_materiality_run_id"],
        "templateVersion": row.get("template_version", ""),
        "surveyStatus": row.get("survey_status", ""),
        "top20Snapshot": snapshot,
        "masterSheetId": row.get("master_sheet_id"),
        "employeeFormUrl": row.get("employee_form_url"),
        "managementFormUrl": row.get("management_form_url"),
        "externalFormUrl": row.get("external_form_url"),
        "errorMessage": row.get("error_message"),
        "generatedAt": row.get("generated_at"),
        "updatedAt": row.get("updated_at"),
    }
