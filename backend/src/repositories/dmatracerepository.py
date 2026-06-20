"""
dmatracerepository.py
레이어: Repository
역할: DMA STEP 4 Shadow Trace 페이로드 빌드·저장·조회 — Benchmark / Media / Regulation / KCGS / ExternalMax 소스별 트레이스 트랜잭션.
"""

import copy
import json
from typing import List, Dict, Any, Optional, Sequence, Union, Literal
from src.utils.db import save, addKey, findAll, findOne, getConn
from src.utils.typeutils import safeFloat as _safeFloatBase
from src.utils.dmaaggregator import calcFinal
from src.utils.subissuemaster import subissueMaster
from src.models.dmaengine import (
    DMASignal,
    FinalMaterialityScore,
    FactorTraceV13,
    LegacyCompatibilityV13,
    ScoringPayloadV13,
    ScorePurposeV13,
)

def safeFloatOrNone(value):
    return _safeFloatBase(value, default=None)
# =========================================================
# STEP 4. TRACE PAYLOAD BUILD / READ / UPDATE / SHADOW PERSISTENCE
# =========================================================
# PURE builders / readers:
# - step4BuildTrace
# - step4WriteTrace
# - step4ReadTrace
# - step4UpdateTrace
# - appendFactorTrace
#
# Phase C shadow persistence:
# - legacy append-only writer (test compatibility only): step4SaveBenchmarkShadowTraces
# - active runtime writer (replace-active transaction): step4ReplaceBenchmarkShadowTracesTx
# - audit/debug read: listBenchmarkShadowObservationRows
#
# Legacy payloads are NEVER auto-migrated, their scores NEVER reused, NEVER overwritten.

_V13_RULE_VERSION = "dma-rule-v1.3-mvp"
BENCHMARK_V13_SHADOW_SOURCE_STEP = "benchmark_v13_shadow"
BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP = "benchmark_v13_screening_shadow"
MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP = "media_external_news_v13_shadow"
MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP = (
    "media_external_news_v13_canonical_shadow"
)
# media_external.regulation Shadow namespace SSOT.
# Regulation stays a media_external internal source type (regulation), never a top-level stage.
MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP = (
    "media_external_regulation_v13_shadow"
)
MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP = (
    "media_external_agency_kcgs_v13_shadow"
)
MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP = (
    "media_external_v13_external_max_shadow"
)

_SHADOW_INSERT_SQL = """
    INSERT INTO ESG_DMA_SIGNAL_DETAIL (
        esg_materiality_run_id,
        evidence_id,
        raw_issue_label,
        sub_issue_code,
        source_step,
        source_type,
        impact_score,
        financial_score,
        confidence_score,
        scoring_payload_json
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
"""


def _buildBenchmarkShadowRows(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
    shadowKind: Literal["fact", "screening"],
) -> list[tuple]:
    """Row-serialization SSOT for Benchmark Shadow INSERT. No DB access."""
    if shadowKind not in ("fact", "screening"):
        raise ValueError(f"Unknown benchmark shadow kind: {shadowKind!r}")
    rows = []
    for payload in payloads:
        payloadJson = step4WriteTrace(payload, asJson=True)
        payloadData = json.loads(payloadJson)
        if shadowKind == "fact":
            extractedFacts = payloadData.get("extractedFacts")
            if not isinstance(extractedFacts, dict):
                raise ValueError("extractedFacts is required for benchmark shadow trace")
            subIssueCode = extractedFacts.get("subIssueCode")
            if not subIssueCode:
                raise ValueError("extractedFacts.subIssueCode is required for benchmark shadow trace")
            rawMetadata = extractedFacts.get("rawMetadata") or {}
            rows.append((
                runId,
                None,
                rawMetadata.get("rawIssueLabel") or "",
                subIssueCode,
                BENCHMARK_V13_SHADOW_SOURCE_STEP,
                extractedFacts.get("sourceType") or "benchmark",
                None,
                None,
                extractedFacts.get("classificationConfidence"),
                payloadJson,
            ))
        else:
            subIssueCode = payloadData.get("subIssueCode")
            screeningTrace = payloadData.get("screeningTrace") or []
            if not subIssueCode:
                raise ValueError("subIssueCode is required for benchmark screening shadow trace")
            if not screeningTrace:
                raise ValueError("screeningTrace is required for benchmark screening shadow trace")
            rawInputs = screeningTrace[0].get("rawInputs") if isinstance(screeningTrace[0], dict) else {}
            rows.append((
                runId,
                None,
                (rawInputs or {}).get("observation") or "",
                subIssueCode,
                BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP,
                "benchmark",
                None,
                None,
                None,
                payloadJson,
            ))
    return rows


def _coercePayload(raw: Union[str, Dict[str, Any], None]) -> Optional[Dict[str, Any]]:
    """scoring_payload_json 값을 dict으로 파싱한다. 실패 시 None 반환."""
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None
    if isinstance(raw, dict):
        return raw
    return None


# STEP 4. v1.3 payload 여부 판단 — False면 v1.3, True면 Legacy(또는 빈 값).
# Input: scoring_payload_json 값 (str | dict | None).
# Output: bool. True = legacy.
def isLegacyPayload(raw: Union[str, Dict[str, Any], None]) -> bool:
    payload = _coercePayload(raw)
    if not payload:
        return True
    hasSchema = "factorPayloadSchemaVersion" in payload
    isV13Rule = payload.get("ruleVersion") == _V13_RULE_VERSION
    return not (hasSchema and isV13Rule)


# STEP 4. v1.3 Canonical payload dict를 구성한다 (DB 저장 없음).
# Input: payload 구성 요소 (rule_version/config_hash는 Registry에서 기본값 조회).
# Output: JSON-직렬화 가능한 camelCase dict.
def step4BuildTrace(
    *,
    scorePurpose: Union[ScorePurposeV13, str] = ScorePurposeV13.CANONICAL_IRO,
    sourceChannel: Optional[str] = None,
    subIssueCode: Optional[str] = None,
    extractedFacts: Any = None,
    factorTrace: Optional[Sequence[Any]] = None,
    axisScores: Optional[Sequence[Any]] = None,
    screeningTrace: Optional[Sequence[Any]] = None,
    aggregationTrace: Any = None,
    legacyCompatibility: Any = None,
    ruleVersion: Optional[str] = None,
    configHash: Optional[str] = None,
    evaluatedAt: Optional[str] = None,
    eventResolutionTrace: Any = None,
) -> Dict[str, Any]:
    if ruleVersion is None or configHash is None:
        from src.utils import dmaruleregistry
        if ruleVersion is None:
            ruleVersion = dmaruleregistry.getRuleVersion()
        if configHash is None:
            configHash = dmaruleregistry.getConfigHash()
    payload = ScoringPayloadV13(
        ruleVersion=ruleVersion,
        configHash=configHash,
        scorePurpose=scorePurpose,
        sourceChannel=sourceChannel,
        subIssueCode=subIssueCode,
        extractedFacts=extractedFacts,
        factorTrace=list(factorTrace) if factorTrace else [],
        axisScores=list(axisScores) if axisScores else [],
        screeningTrace=list(screeningTrace) if screeningTrace else [],
        aggregationTrace=aggregationTrace,
        legacyCompatibility=legacyCompatibility or LegacyCompatibilityV13(),
        evaluatedAt=evaluatedAt,
        eventResolutionTrace=eventResolutionTrace,
    )
    return payload.model_dump(mode="json", by_alias=False)


# STEP 4. payload를 직렬화한다. Phase C에서 DB 저장 경로에 연결한다.
# Input: ScoringPayloadV13 또는 dict, as_json=True이면 JSON 문자열 반환.
# Output: dict 또는 JSON 문자열.
def step4WriteTrace(
    payload: Union[ScoringPayloadV13, Dict[str, Any]],
    *,
    asJson: bool = False,
) -> Union[Dict[str, Any], str]:
    if isinstance(payload, ScoringPayloadV13):
        data = payload.model_dump(mode="json", by_alias=False)
    elif isinstance(payload, dict):
        data = ScoringPayloadV13(**payload).model_dump(mode="json", by_alias=False)
    else:
        raise TypeError("payload must be a ScoringPayloadV13 or dict")
    if asJson:
        return json.dumps(data, ensure_ascii=False)
    return data


# STEP 4. Benchmark v1.3 Extracted Fact Trace를 Shadow Row로 저장한다.
# Input: runId와 ScoringPayloadV13 payload 목록.
# Output: 저장 Row 수. Legacy 집계, 랭킹, 선정은 호출하지 않는다.
def listBenchmarkShadowObservationRows(runId: int) -> list[dict]:
    sql = """
        SELECT
            sub_issue_code,
            MAX(CASE WHEN source_type = 'leader_sr' THEN 1 ELSE 0 END) AS leader_observed,
            MAX(CASE WHEN source_type = 'peer_sr' THEN 1 ELSE 0 END) AS peer_observed,
            MAX(CASE WHEN source_type = 'own_sr' THEN 1 ELSE 0 END) AS own_observed
        FROM ESG_DMA_SIGNAL_DETAIL
        WHERE esg_materiality_run_id = ?
          AND source_step = ?
          AND delete_yn = 0
        GROUP BY sub_issue_code
        ORDER BY sub_issue_code
    """
    return findAll(sql, (runId, BENCHMARK_V13_SHADOW_SOURCE_STEP))


# LEGACY TEST COMPATIBILITY ONLY — do not call from runtime code.
# Runtime shadow persistence uses step4ReplaceBenchmarkShadowTracesTx.
def step4SaveBenchmarkShadowTraces(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
    *,
    shadowKind: Literal["fact", "screening"] = "fact",
) -> int:
    if not payloads:
        return 0
    rows = _buildBenchmarkShadowRows(runId, payloads, shadowKind)
    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection is not available for benchmark shadow trace save")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.executemany(_SHADOW_INSERT_SQL, rows)
        conn.commit()
        return len(rows)
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        if hasattr(conn, "close"):
            conn.close()


def step4ReplaceBenchmarkShadowTracesTx(
    runId: int,
    factPayloads: Sequence[Dict[str, Any]],
    screeningPayloads: Sequence[Dict[str, Any]],
    expectedScreeningCount: int,
) -> int:
    """
    Replace-Active Transaction for Benchmark Shadow rows.
    Within a single transaction:
      1. Row-lock ESG_MATERIALITY_RUN
      2. Soft-delete active Fact + Screening shadow rows for runId
      3. INSERT new Fact shadow rows
      4. INSERT new Screening shadow rows
      5. Verify screening completeness (count == expectedScreeningCount)
      6. COMMIT on success, ROLLBACK on any failure
    Returns total rows inserted.
    """
    # Pre-DB validation — fail before opening any connection
    if expectedScreeningCount <= 0:
        raise ValueError("expectedScreeningCount must be greater than zero")
    if len(screeningPayloads) != expectedScreeningCount:
        raise ValueError(
            f"screeningPayloads count mismatch: "
            f"expected={expectedScreeningCount}, got={len(screeningPayloads)}"
        )

    factRows = _buildBenchmarkShadowRows(runId, factPayloads, "fact") if factPayloads else []
    screeningRows = _buildBenchmarkShadowRows(runId, screeningPayloads, "screening") if screeningPayloads else []

    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection is not available for benchmark shadow replace transaction")
    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id FROM ESG_MATERIALITY_RUN WHERE id = ? FOR UPDATE",
                (runId,),
            )
            lockRow = cur.fetchone()
            if not lockRow:
                raise RuntimeError(f"ESG_MATERIALITY_RUN row not found for runId={runId}")

            cur.execute(
                """
                UPDATE ESG_DMA_SIGNAL_DETAIL
                SET delete_yn = 1
                WHERE esg_materiality_run_id = ?
                  AND source_step IN (?, ?)
                  AND delete_yn = 0
                """,
                (runId, BENCHMARK_V13_SHADOW_SOURCE_STEP, BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP),
            )

            if factRows:
                cur.executemany(_SHADOW_INSERT_SQL, factRows)
            if screeningRows:
                cur.executemany(_SHADOW_INSERT_SQL, screeningRows)

            cur.execute(
                """
                SELECT
                    COUNT(*) AS row_count,
                    COUNT(DISTINCT sub_issue_code) AS distinct_count
                FROM ESG_DMA_SIGNAL_DETAIL
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP),
            )
            verifyRow = cur.fetchone() or {}
            rowCount = int(verifyRow.get("row_count") or 0)
            distinctCount = int(verifyRow.get("distinct_count") or 0)
            if rowCount != expectedScreeningCount or distinctCount != expectedScreeningCount:
                raise RuntimeError(
                    f"Screening completeness check failed: "
                    f"expected={expectedScreeningCount}, "
                    f"row_count={rowCount}, distinct_count={distinctCount}"
                )

        conn.commit()
        return len(factRows) + len(screeningRows)
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        if hasattr(conn, "close"):
            conn.close()


def _buildMediaNewsShadowRows(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> list[tuple]:
    """Row-serialization SSOT for media_external.news Shadow INSERT. No DB access."""
    rows = []
    for payload in payloads:
        payloadJson = step4WriteTrace(payload, asJson=True)
        payloadData = json.loads(payloadJson)
        extractedFacts = payloadData.get("extractedFacts")
        if not isinstance(extractedFacts, dict):
            raise ValueError("extractedFacts is required for media_external.news shadow trace")
        subIssueCode = extractedFacts.get("subIssueCode")
        if not subIssueCode:
            raise ValueError("extractedFacts.subIssueCode is required for media_external.news shadow trace")
        sourceType = extractedFacts.get("sourceType")
        if sourceType != "news":
            raise ValueError(
                f"media_external.news shadow trace requires sourceType='news', got {sourceType!r}"
            )
        rawMetadata = extractedFacts.get("rawMetadata") or {}
        rows.append((
            runId,
            None,
            rawMetadata.get("rawIssueLabel") or "",
            subIssueCode,
            MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP,
            "news",
            None,
            None,
            extractedFacts.get("classificationConfidence"),
            payloadJson,
        ))
    return rows


def step4ReplaceMediaNewsShadowTracesTx(
    runId: int,
    factPayloads: Sequence[Dict[str, Any]],
) -> int:
    """
    LEGACY TEST COMPATIBILITY ONLY.
    Active Runtime uses step4ReplaceMediaNewsShadowBundleTx().
    factPayloads=[] is a valid empty-observation result — still runs the transaction.
    """
    factRows = _buildMediaNewsShadowRows(runId, factPayloads)

    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection is not available for media news shadow replace transaction")
    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id FROM ESG_MATERIALITY_RUN WHERE id = ? FOR UPDATE",
                (runId,),
            )
            lockRow = cur.fetchone()
            if not lockRow:
                raise RuntimeError(f"ESG_MATERIALITY_RUN row not found for runId={runId}")

            cur.execute(
                """
                UPDATE ESG_DMA_SIGNAL_DETAIL
                SET delete_yn = 1
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP),
            )

            if factRows:
                cur.executemany(_SHADOW_INSERT_SQL, factRows)

            cur.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_DMA_SIGNAL_DETAIL
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP),
            )
            verifyRow = cur.fetchone() or {}
            rowCount = int(verifyRow.get("row_count") or 0)
            if rowCount != len(factRows):
                raise RuntimeError(
                    f"News shadow count check failed: expected={len(factRows)}, row_count={rowCount}"
                )
        conn.commit()
        return len(factRows)
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        if hasattr(conn, "close"):
            conn.close()


def _getAxisScore(payloadData: Dict[str, Any], axis: str) -> Optional[float]:
    """Extract score for a named axis from a serialized ScoringPayloadV13 dict."""
    for entry in payloadData.get("axisScores") or []:
        if isinstance(entry, dict) and entry.get("axis") == axis:
            score = entry.get("score")
            return float(score) if score is not None else None
    return None


def _buildMediaNewsCanonicalShadowRows(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> list[tuple]:
    """Row-serialization SSOT for media_external.news Canonical Shadow INSERT. No DB access."""
    rows = []
    for payload in payloads:
        payloadJson = step4WriteTrace(payload, asJson=True)
        payloadData = json.loads(payloadJson)

        if payloadData.get("scorePurpose") != "CANONICAL_IRO":
            raise ValueError(
                f"Canonical Shadow scorePurpose must be 'CANONICAL_IRO', got {payloadData.get('scorePurpose')!r}"
            )
        if payloadData.get("sourceChannel") != "media_external":
            raise ValueError(
                f"Canonical Shadow sourceChannel must be 'media_external', got {payloadData.get('sourceChannel')!r}"
            )
        subIssueCode = payloadData.get("subIssueCode")
        if not subIssueCode:
            raise ValueError("subIssueCode is required for Canonical Shadow trace")

        extractedFacts = payloadData.get("extractedFacts")
        if not isinstance(extractedFacts, dict):
            raise ValueError("extractedFacts is required for Canonical Shadow trace")
        efCode = extractedFacts.get("subIssueCode")
        if not efCode:
            raise ValueError("extractedFacts.subIssueCode is required for Canonical Shadow trace")
        if efCode != subIssueCode:
            raise ValueError(
                f"extractedFacts.subIssueCode mismatch: payload={subIssueCode!r}, ef={efCode!r}"
            )
        if extractedFacts.get("sourceType") != "news":
            raise ValueError(
                f"Canonical Shadow requires sourceType='news', got {extractedFacts.get('sourceType')!r}"
            )

        ert = payloadData.get("eventResolutionTrace")
        if not isinstance(ert, dict):
            raise ValueError("eventResolutionTrace is required for Canonical Shadow trace")
        if ert.get("subIssueCode") != subIssueCode:
            raise ValueError(
                f"eventResolutionTrace.subIssueCode mismatch: payload={subIssueCode!r}, trace={ert.get('subIssueCode')!r}"
            )

        axisScores = payloadData.get("axisScores") or []
        if not isinstance(axisScores, list):
            raise ValueError("axisScores must be a list")
        seen_axes: set = set()
        for entry in axisScores:
            axis = entry.get("axis") if isinstance(entry, dict) else None
            if axis is not None:
                if axis in seen_axes:
                    raise ValueError(f"Duplicate axis in axisScores: {axis!r}")
                seen_axes.add(axis)
                if axis not in ("impact", "financial"):
                    raise ValueError(f"Invalid axis in axisScores: {axis!r}")

        rawMetadata = extractedFacts.get("rawMetadata") or {}
        rows.append((
            runId,
            None,
            rawMetadata.get("rawIssueLabel") or "",
            subIssueCode,
            MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP,
            "news",
            _getAxisScore(payloadData, "impact"),
            _getAxisScore(payloadData, "financial"),
            extractedFacts.get("classificationConfidence"),
            payloadJson,
        ))
    return rows


def step4ReplaceMediaNewsShadowBundleTx(
    runId: int,
    factPayloads: Sequence[Dict[str, Any]],
    canonicalPayloads: Sequence[Dict[str, Any]],
) -> int:
    """
    Replace-Active Transaction for Fact + Canonical Shadow Bundles.

    Serializes all rows before opening a DB connection, then within a single
    transaction: row-locks the run, soft-deletes both namespaces, inserts new
    rows, verifies counts, and commits. Any failure triggers ROLLBACK.
    """
    # Serialize before acquiring DB connection
    factRows = _buildMediaNewsShadowRows(runId, factPayloads)
    canonicalRows = _buildMediaNewsCanonicalShadowRows(runId, canonicalPayloads)

    conn = getConn()
    if conn is None:
        raise RuntimeError(
            "DB connection is not available for media news shadow bundle replace transaction"
        )
    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id FROM ESG_MATERIALITY_RUN WHERE id = ? FOR UPDATE",
                (runId,),
            )
            lockRow = cur.fetchone()
            if not lockRow:
                raise RuntimeError(f"ESG_MATERIALITY_RUN row not found for runId={runId}")

            cur.execute(
                """
                UPDATE ESG_DMA_SIGNAL_DETAIL
                SET delete_yn = 1
                WHERE esg_materiality_run_id = ?
                  AND source_step IN (?, ?)
                  AND delete_yn = 0
                """,
                (
                    runId,
                    MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP,
                    MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP,
                ),
            )

            if factRows:
                cur.executemany(_SHADOW_INSERT_SQL, factRows)
            if canonicalRows:
                cur.executemany(_SHADOW_INSERT_SQL, canonicalRows)

            cur.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_DMA_SIGNAL_DETAIL
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP),
            )
            factVerify = cur.fetchone() or {}
            factRowCount = int(factVerify.get("row_count") or 0)
            if factRowCount != len(factRows):
                raise RuntimeError(
                    f"Fact shadow count check failed: expected={len(factRows)}, row_count={factRowCount}"
                )

            cur.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_DMA_SIGNAL_DETAIL
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP),
            )
            canonicalVerify = cur.fetchone() or {}
            canonicalRowCount = int(canonicalVerify.get("row_count") or 0)
            if canonicalRowCount != len(canonicalRows):
                raise RuntimeError(
                    f"Canonical shadow count check failed: "
                    f"expected={len(canonicalRows)}, row_count={canonicalRowCount}"
                )

        conn.commit()
        return len(factRows) + len(canonicalRows)
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        if hasattr(conn, "close"):
            conn.close()


# =========================================================
# STEP 4. media_external.regulation Shadow Runtime
# =========================================================
# Regulation Applicability Input + Approved Active Mapping
#   → APPROVED-only Repository Reader
#   → step2BuildRegulationScreeningPayloads() (pure builder, reused as-is)
#   → _buildRegulationShadowRows() (row serializer, no DB access)
#   → step4ReplaceRegulationShadowTracesTx() (replace-active transaction)
#   → ESG_DMA_SIGNAL_DETAIL (source_step = MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP)
#
# NOTE: ESG_DMA_REGULATION__INPUT carries an intentional double underscore between
# REGULATION and INPUT — it is the real table name, not a typo.


# STEP 4. Strict DB reader helpers — raise instead of silently returning [] / None on error.
#
# The shared findAll / findOne helpers in db.py silently swallow mariadb.Error and return
# [] / None, which makes a DB failure indistinguishable from a genuine empty result. For the
# Regulation reader path this is unsafe: an empty reader result drives a Replace-Active
# Transaction that soft-deletes all existing Regulation Shadow rows. These private helpers
# raise RuntimeError on any connection or execution failure so the Replace-Active TX is
# never reached when the DB is unavailable or broken.
def _findOneRegulationRowOrRaise(sql: str, params=None) -> Optional[dict]:
    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection is not available for regulation reader")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    except Exception as exc:
        raise RuntimeError(f"Regulation reader failed: {exc}") from exc
    finally:
        if hasattr(conn, "close"):
            conn.close()


def _findAllRegulationRowsOrRaise(sql: str, params=None) -> list[dict]:
    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection is not available for regulation reader")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            return cur.fetchall() or []
    except Exception as exc:
        raise RuntimeError(f"Regulation reader failed: {exc}") from exc
    finally:
        if hasattr(conn, "close"):
            conn.close()


# STEP 4. Regulation Run Context Reader. Resolves company/year for a materiality run.
# Input: runId. Output: dict with runId / companyId / reportingYear camelCase aliases.
# RuntimeError when the run row is missing (or soft-deleted).
def findRegulationRunContext(runId: int) -> dict:
    sql = """
        SELECT
            id AS runId,
            company_id AS companyId,
            reporting_year AS reportingYear
        FROM ESG_MATERIALITY_RUN
        WHERE id = ?
          AND delete_yn = 0
    """
    row = _findOneRegulationRowOrRaise(sql, (runId,))
    if not row:
        raise RuntimeError(f"ESG_MATERIALITY_RUN row not found for runId={runId}")
    return row


# STEP 4. APPROVED-only Regulation Applicability Input Reader (first-pass filter).
# Input: companyId, reportingYear. Output: APPROVED, non-deleted rows as camelCase dicts.
# DRAFT / REVIEWED and delete_yn=1 are excluded here; the pure builder re-validates fail-closed.
def listApprovedRegulationInputs(
    companyId: int,
    reportingYear: int,
) -> list[dict]:
    sql = """
        SELECT
            company_id AS companyId,
            reporting_year AS reportingYear,
            regime,
            applicability,
            input_method AS inputMethod,
            source_document_ref AS sourceDocumentRef,
            review_status AS reviewStatus,
            reviewer_comment AS reviewerComment
        FROM ESG_DMA_REGULATION__INPUT
        WHERE company_id = ?
          AND reporting_year = ?
          AND review_status = 'APPROVED'
          AND delete_yn = 0
        ORDER BY regime
    """
    return _findAllRegulationRowsOrRaise(sql, (companyId, reportingYear))


# STEP 4. APPROVED + active Regulation Sub-Issue Mapping Reader (first-pass filter).
# Output: APPROVED, active_yn=1, non-deleted mapping rows as camelCase dicts.
# source_document_ref is not a DTO field, so it is intentionally omitted from the builder input.
# activeYn / reviewStatus are kept so the pure builder can re-check fail-closed.
def listApprovedActiveRegulationMappings() -> list[dict]:
    sql = """
        SELECT
            regime,
            sub_issue_code AS subIssueCode,
            mapping_reason AS mappingReason,
            active_yn AS activeYn,
            review_status AS reviewStatus
        FROM ESG_DMA_REGULATION_SUB_ISSUE_MAP
        WHERE review_status = 'APPROVED'
          AND active_yn = 1
          AND delete_yn = 0
        ORDER BY regime, sub_issue_code
    """
    return _findAllRegulationRowsOrRaise(sql)


def _buildRegulationShadowRows(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> list[tuple]:
    """Row-serialization SSOT for media_external.regulation Shadow INSERT. No DB access.

    Validates each Regulation Screening Payload and maps it to a _SHADOW_INSERT_SQL tuple.
    UNKNOWN applicability yields impact/financial = None; NOT_APPLICABLE yields 0.0/0.0 —
    the calculator already encodes this distinction in the screening trace signals, and the
    None vs 0.0 difference must be preserved end-to-end.
    """
    rows = []
    for payload in payloads:
        payloadJson = step4WriteTrace(payload, asJson=True)
        payloadData = json.loads(payloadJson)

        if payloadData.get("scorePurpose") != "PRESURVEY_SCREENING":
            raise ValueError(
                f"Regulation Shadow scorePurpose must be 'PRESURVEY_SCREENING', "
                f"got {payloadData.get('scorePurpose')!r}"
            )
        if payloadData.get("sourceChannel") != "media_external":
            raise ValueError(
                f"Regulation Shadow sourceChannel must be 'media_external', "
                f"got {payloadData.get('sourceChannel')!r}"
            )
        subIssueCode = payloadData.get("subIssueCode")
        if not subIssueCode:
            raise ValueError("subIssueCode is required for Regulation Shadow trace")

        screeningTrace = payloadData.get("screeningTrace")
        if not isinstance(screeningTrace, list):
            raise ValueError("screeningTrace is required for Regulation Shadow trace")
        if len(screeningTrace) != 1:
            raise ValueError(
                f"Regulation Shadow requires exactly 1 screeningTrace, got {len(screeningTrace)}"
            )
        trace = screeningTrace[0]
        if not isinstance(trace, dict):
            raise ValueError("Regulation Shadow screeningTrace[0] must be a dict")

        channel = trace.get("channel")
        if not (isinstance(channel, str) and channel.startswith("regulation_")):
            raise ValueError(
                f"Regulation Shadow screeningTrace channel must start with 'regulation_', "
                f"got {channel!r}"
            )

        rawInputs = trace.get("rawInputs")
        if not isinstance(rawInputs, dict):
            raise ValueError("Regulation Shadow rawInputs is required")
        if rawInputs.get("sourceStep") != "media_external":
            raise ValueError(
                f"Regulation Shadow rawInputs.sourceStep must be 'media_external', "
                f"got {rawInputs.get('sourceStep')!r}"
            )
        if rawInputs.get("sourceType") != "regulation":
            raise ValueError(
                f"Regulation Shadow rawInputs.sourceType must be 'regulation', "
                f"got {rawInputs.get('sourceType')!r}"
            )
        companyId = rawInputs.get("companyId")
        if not isinstance(companyId, int) or isinstance(companyId, bool) or companyId <= 0:
            raise ValueError(
                f"Regulation Shadow rawInputs.companyId must be a positive int, got {companyId!r}"
            )
        reportingYear = rawInputs.get("reportingYear")
        if not isinstance(reportingYear, int) or isinstance(reportingYear, bool):
            raise ValueError(
                f"Regulation Shadow rawInputs.reportingYear must be an int, got {reportingYear!r}"
            )
        regime = rawInputs.get("regime")
        if not regime:
            raise ValueError("Regulation Shadow rawInputs.regime is required")
        expectedChannel = f"regulation_{str(regime).lower()}"
        if channel != expectedChannel:
            raise ValueError(
                f"Regulation Shadow channel/regime mismatch: "
                f"expected={expectedChannel!r}, got={channel!r}"
            )
        applicability = rawInputs.get("applicability")
        if not applicability:
            raise ValueError("Regulation Shadow rawInputs.applicability is required")

        # UNKNOWN → None / None, NOT_APPLICABLE → 0.0 / 0.0 (passed through from the trace).
        rows.append((
            runId,
            None,
            regime,
            subIssueCode,
            MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP,
            "regulation",
            trace.get("impactSignal"),
            trace.get("financialSignal"),
            None,
            payloadJson,
        ))
    return rows


def step4ReplaceRegulationShadowTracesTx(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> int:
    """
    Replace-Active Transaction for media_external.regulation Shadow rows.

    Serializes all rows before opening a DB connection, then within a single
    transaction: row-locks the run, soft-deletes the regulation shadow namespace,
    inserts the new rows, verifies the active COUNT(*), and commits. Any failure
    triggers ROLLBACK, preserving the prior active regulation shadow set.

    payloads=[] is a valid empty-clear result — the transaction still runs,
    soft-deletes the prior active rows, inserts nothing, verifies COUNT(*)==0,
    and commits. Returns the number of rows inserted.
    """
    # Serialize before acquiring DB connection — Serializer failure must not call getConn().
    rows = _buildRegulationShadowRows(runId, payloads)

    conn = getConn()
    if conn is None:
        raise RuntimeError(
            "DB connection is not available for regulation shadow replace transaction"
        )
    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id FROM ESG_MATERIALITY_RUN WHERE id = ? FOR UPDATE",
                (runId,),
            )
            lockRow = cur.fetchone()
            if not lockRow:
                raise RuntimeError(f"ESG_MATERIALITY_RUN row not found for runId={runId}")

            cur.execute(
                """
                UPDATE ESG_DMA_SIGNAL_DETAIL
                SET delete_yn = 1
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP),
            )

            if rows:
                cur.executemany(_SHADOW_INSERT_SQL, rows)

            # One Sub-Issue can map to multiple regimes (CSRD + CBAM); a plain COUNT(*)
            # preserves the regime trace. A distinct-collapse over sub_issue_code would drop
            # that trace and is intentionally NOT used here.
            cur.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_DMA_SIGNAL_DETAIL
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP),
            )
            verifyRow = cur.fetchone() or {}
            rowCount = int(verifyRow.get("row_count") or 0)
            if rowCount != len(rows):
                raise RuntimeError(
                    f"Regulation shadow count check failed: "
                    f"expected={len(rows)}, row_count={rowCount}"
                )

        conn.commit()
        return len(rows)
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        if hasattr(conn, "close"):
            conn.close()


# STEP 4. scoring_payload_json 값을 읽어 v1.3 payload dict로 반환한다.
# Input: scoring_payload_json 값 (str | dict | None).
# Output: 정규화된 v1.3 payload dict 또는 None (legacy / 빈 값).
# =========================================================
# STEP 4. media_external.agency.kcgs Shadow Runtime
# =========================================================


def listApprovedKcgsGradeInputs(companyId: int) -> list[dict]:
    sql = """
        SELECT
            company_id AS companyId,
            rating_year AS ratingYear,
            overall_grade AS overallGrade,
            environment_grade AS environmentGrade,
            social_grade AS socialGrade,
            governance_grade AS governanceGrade,
            source_type AS inputSourceType,
            source_document_ref AS sourceDocumentRef,
            review_status AS reviewStatus
        FROM ESG_DMA_KCGS_GRADE_INPUT
        WHERE company_id = ?
          AND review_status = 'APPROVED'
          AND delete_yn = 0
        ORDER BY rating_year DESC
        LIMIT 3
    """
    return _findAllRegulationRowsOrRaise(sql, (companyId,))


def _buildKcgsShadowRows(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> list[tuple]:
    """Row-serialization SSOT for media_external.agency.kcgs Shadow INSERT. No DB access."""
    rows = []
    for payload in payloads:
        payloadJson = step4WriteTrace(payload, asJson=True)
        payloadData = json.loads(payloadJson)

        if payloadData.get("scorePurpose") != "PRESURVEY_SCREENING":
            raise ValueError(
                f"KCGS Shadow scorePurpose must be 'PRESURVEY_SCREENING', "
                f"got {payloadData.get('scorePurpose')!r}"
            )
        if payloadData.get("sourceChannel") != "media_external":
            raise ValueError(
                f"KCGS Shadow sourceChannel must be 'media_external', "
                f"got {payloadData.get('sourceChannel')!r}"
            )
        subIssueCode = payloadData.get("subIssueCode")
        if not subIssueCode:
            raise ValueError("subIssueCode is required for KCGS Shadow trace")
        if subIssueCode not in subissueMaster:
            raise ValueError(f"Unknown KCGS Shadow subIssueCode: {subIssueCode!r}")

        screeningTrace = payloadData.get("screeningTrace")
        if not isinstance(screeningTrace, list):
            raise ValueError("screeningTrace is required for KCGS Shadow trace")
        if len(screeningTrace) != 1:
            raise ValueError(
                f"KCGS Shadow requires exactly 1 screeningTrace, got {len(screeningTrace)}"
            )
        trace = screeningTrace[0]
        if not isinstance(trace, dict):
            raise ValueError("KCGS Shadow screeningTrace[0] must be a dict")
        if trace.get("channel") != "kcgs_pillar_domain_signal":
            raise ValueError(
                f"KCGS Shadow channel must be 'kcgs_pillar_domain_signal', got {trace.get('channel')!r}"
            )
        impactSignal = trace.get("impactSignal")
        financialSignal = trace.get("financialSignal")
        if isinstance(impactSignal, bool) or not isinstance(impactSignal, (int, float)):
            raise ValueError(
                f"KCGS Shadow impactSignal must be numeric, got {impactSignal!r}"
            )
        if isinstance(financialSignal, bool) or not isinstance(financialSignal, (int, float)):
            raise ValueError(
                f"KCGS Shadow financialSignal must be numeric, got {financialSignal!r}"
            )

        rawInputs = trace.get("rawInputs")
        if not isinstance(rawInputs, dict):
            raise ValueError("KCGS Shadow rawInputs is required")
        pillarSignalRaw = rawInputs.get("pillarSignal")
        if (
            isinstance(pillarSignalRaw, bool)
            or not isinstance(pillarSignalRaw, (int, float))
            or float(impactSignal) != float(pillarSignalRaw)
        ):
            raise ValueError(
                f"KCGS Shadow impactSignal must equal rawInputs.pillarSignal "
                f"(SYMMETRIC_DOMAIN_SIGNAL), got impactSignal={impactSignal!r}, "
                f"pillarSignal={pillarSignalRaw!r}"
            )
        if float(financialSignal) != float(pillarSignalRaw):
            raise ValueError(
                f"KCGS Shadow financialSignal must equal rawInputs.pillarSignal "
                f"(SYMMETRIC_DOMAIN_SIGNAL), got financialSignal={financialSignal!r}, "
                f"pillarSignal={pillarSignalRaw!r}"
            )
        if rawInputs.get("sourceStep") != "media_external":
            raise ValueError(
                f"KCGS Shadow rawInputs.sourceStep must be 'media_external', "
                f"got {rawInputs.get('sourceStep')!r}"
            )
        if rawInputs.get("sourceType") != "agency":
            raise ValueError(
                f"KCGS Shadow rawInputs.sourceType must be 'agency', "
                f"got {rawInputs.get('sourceType')!r}"
            )
        if rawInputs.get("providerKey") != "kcgs":
            raise ValueError(
                f"KCGS Shadow rawInputs.providerKey must be 'kcgs', "
                f"got {rawInputs.get('providerKey')!r}"
            )
        companyId = rawInputs.get("companyId")
        if not isinstance(companyId, int) or isinstance(companyId, bool) or companyId <= 0:
            raise ValueError(
                f"KCGS Shadow rawInputs.companyId must be a positive int, got {companyId!r}"
            )
        pillar = rawInputs.get("pillar")
        if pillar not in ("E", "S", "G"):
            raise ValueError(f"KCGS Shadow rawInputs.pillar must be one of E/S/G, got {pillar!r}")
        if subissueMaster[subIssueCode].get("domain") != pillar:
            raise ValueError(
                f"KCGS Shadow subIssueCode/domain mismatch: "
                f"subIssueCode={subIssueCode!r}, pillar={pillar!r}"
            )
        subIssueBoost = rawInputs.get("subIssueBoost")
        if (
            isinstance(subIssueBoost, bool)
            or not isinstance(subIssueBoost, (int, float))
            or not (0.0 <= float(subIssueBoost) <= 1.0)
        ):
            raise ValueError(
                f"KCGS Shadow rawInputs.subIssueBoost must be numeric in 0..1, got {subIssueBoost!r}"
            )
        if rawInputs.get("externalMaxEligibleYn") is not True:
            raise ValueError("KCGS Shadow rawInputs.externalMaxEligibleYn must be true")
        if rawInputs.get("top20BoostOnlyYn") is not False:
            raise ValueError("KCGS Shadow rawInputs.top20BoostOnlyYn must be false")
        if rawInputs.get("axisMode") != "SYMMETRIC_DOMAIN_SIGNAL":
            raise ValueError("KCGS Shadow rawInputs.axisMode must be 'SYMMETRIC_DOMAIN_SIGNAL'")
        if rawInputs.get("directCanonicalFinalAllowedYn") is not False:
            raise ValueError("KCGS Shadow rawInputs.directCanonicalFinalAllowedYn must be false")

        rows.append((
            runId,
            None,
            f"KCGS:{pillar}",
            subIssueCode,
            MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP,
            "agency",
            trace.get("impactSignal"),
            trace.get("financialSignal"),
            None,
            payloadJson,
        ))
    return rows


def step4ReplaceKcgsShadowTracesTx(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> int:
    """
    Replace-Active Transaction for media_external.agency.kcgs Shadow rows.

    payloads=[] is a valid empty-clear result: prior active KCGS shadow rows are
    soft-deleted, no rows are inserted, and COUNT(*) must verify as zero.
    """
    rows = _buildKcgsShadowRows(runId, payloads)

    conn = getConn()
    if conn is None:
        raise RuntimeError(
            "DB connection is not available for KCGS shadow replace transaction"
        )
    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id FROM ESG_MATERIALITY_RUN WHERE id = ? FOR UPDATE",
                (runId,),
            )
            lockRow = cur.fetchone()
            if not lockRow:
                raise RuntimeError(f"ESG_MATERIALITY_RUN row not found for runId={runId}")

            cur.execute(
                """
                UPDATE ESG_DMA_SIGNAL_DETAIL
                SET delete_yn = 1
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP),
            )

            if rows:
                cur.executemany(_SHADOW_INSERT_SQL, rows)

            cur.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_DMA_SIGNAL_DETAIL
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP),
            )
            verifyRow = cur.fetchone() or {}
            rowCount = int(verifyRow.get("row_count") or 0)
            if rowCount != len(rows):
                raise RuntimeError(
                    f"KCGS shadow count check failed: expected={len(rows)}, row_count={rowCount}"
                )

        conn.commit()
        return len(rows)
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        if hasattr(conn, "close"):
            conn.close()


# =========================================================
# STEP 4. media_external External MAX Shadow Runtime
# =========================================================


def listExternalMaxEligibleMediaRows(runId: int) -> list[dict]:
    """
    Read External MAX eligible shadow rows for a run.
    Eligible:
      - news canonical shadow
      - regulation screening shadow
      - KCGS domain signal shadow
    Excluded: news fact shadow, KIS (CAPABILITY_PENDING), legacy rows.
    Uses _findAllRegulationRowsOrRaise (fail-closed; RuntimeError on any failure).
    """
    sql = """
        SELECT
            id,
            sub_issue_code AS subIssueCode,
            raw_issue_label AS rawIssueLabel,
            source_step AS sourceStep,
            source_type AS sourceType,
            impact_score AS impactSignal,
            financial_score AS financialSignal,
            scoring_payload_json AS scoringPayloadJson
        FROM ESG_DMA_SIGNAL_DETAIL
        WHERE esg_materiality_run_id = ?
          AND source_step IN (?, ?, ?)
          AND delete_yn = 0
        ORDER BY sub_issue_code, source_step, id
    """
    return _findAllRegulationRowsOrRaise(
        sql,
        (
            runId,
            MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP,
            MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP,
            MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP,
        ),
    )


def _buildMediaExternalMaxShadowRows(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> list[tuple]:
    """Row-serialization SSOT for External MAX Audit Shadow INSERT. No DB access."""
    rows = []
    for payload in payloads:
        payloadJson = step4WriteTrace(payload, asJson=True)
        payloadData = json.loads(payloadJson)

        if payloadData.get("scorePurpose") != "PRESURVEY_SCREENING":
            raise ValueError(
                f"External MAX Shadow scorePurpose must be 'PRESURVEY_SCREENING', "
                f"got {payloadData.get('scorePurpose')!r}"
            )
        if payloadData.get("sourceChannel") != "media_external":
            raise ValueError(
                f"External MAX Shadow sourceChannel must be 'media_external', "
                f"got {payloadData.get('sourceChannel')!r}"
            )
        subIssueCode = payloadData.get("subIssueCode")
        if not subIssueCode:
            raise ValueError("subIssueCode is required for External MAX Shadow trace")
        if subIssueCode not in subissueMaster:
            raise ValueError(f"Unknown External MAX Shadow subIssueCode: {subIssueCode!r}")

        screeningTrace = payloadData.get("screeningTrace")
        if not isinstance(screeningTrace, list):
            raise ValueError("screeningTrace is required for External MAX Shadow trace")
        if len(screeningTrace) != 1:
            raise ValueError(
                f"External MAX Shadow requires exactly 1 screeningTrace, got {len(screeningTrace)}"
            )
        trace = screeningTrace[0]
        if not isinstance(trace, dict):
            raise ValueError("External MAX Shadow screeningTrace[0] must be a dict")
        if trace.get("channel") != "external_screening_max":
            raise ValueError(
                f"External MAX Shadow channel must be 'external_screening_max', "
                f"got {trace.get('channel')!r}"
            )
        rawInputs = trace.get("rawInputs")
        if not isinstance(rawInputs, dict):
            raise ValueError("External MAX Shadow rawInputs is required")
        if rawInputs.get("additiveYn") is not False:
            raise ValueError("External MAX Shadow rawInputs.additiveYn must be false")

        rows.append((
            runId,
            None,
            "external_screening_max",
            subIssueCode,
            MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP,
            "external_max",
            trace.get("impactSignal"),
            trace.get("financialSignal"),
            None,
            payloadJson,
        ))
    return rows


def step4ReplaceMediaExternalMaxShadowAndSummaryTx(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> int:
    """
    Replace-Active Transaction: External MAX Shadow + Summary + Final + Rank.

    Pre-DB: serializes shadow rows and validates no duplicate subIssueCodes.
    TX (single atomic block):
      1. getConn / autocommit=False
      2. ESG_MATERIALITY_RUN row lock
      3. Soft-delete existing External MAX shadow (namespace-only)
      4. INSERT new External MAX shadow rows
      5. NULL clear Summary media_external_* for this run
      6. UPSERT Summary media_external_* per payload
      7. Read all Summary rows for this run
      8. Recalculate final_* via calcFinal() for each sub-issue
      9. NULL clear rank_no
      10. Re-rank non-null final_score rows (DESC final_score, ASC sub_issue_code)
      11. Verify shadow COUNT(*)
      12. Verify Summary observed count
      13. COMMIT / close

    payloads=[] is a valid empty-clear: clears shadow + summary, recalcs final/rank,
    and commits. Any failure triggers ROLLBACK preserving the prior state.
    Returns the number of shadow rows inserted.
    """
    # Pre-DB: serialize shadow rows (validates all payloads before DB touch)
    shadowRows = _buildMediaExternalMaxShadowRows(runId, payloads)

    # Pre-DB: derive summary data and validate no duplicate subIssueCodes
    seenCodes: set[str] = set()
    summaryRows: list[tuple] = []
    for payload in payloads:
        subIssueCode = str(payload.get("subIssueCode") or "")
        if subIssueCode in seenCodes:
            raise ValueError(
                f"Duplicate subIssueCode in External MAX payloads: {subIssueCode!r}"
            )
        seenCodes.add(subIssueCode)
        traces = payload.get("screeningTrace") or []
        tr = traces[0] if traces else {}
        impactSignal = tr.get("impactSignal") if isinstance(tr, dict) else None
        financialSignal = tr.get("financialSignal") if isinstance(tr, dict) else None
        summaryRows.append((runId, subIssueCode, impactSignal, financialSignal))

    conn = getConn()
    if conn is None:
        raise RuntimeError(
            "DB connection is not available for External MAX shadow+summary replace transaction"
        )
    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT id FROM ESG_MATERIALITY_RUN WHERE id = ? FOR UPDATE",
                (runId,),
            )
            lockRow = cur.fetchone()
            if not lockRow:
                raise RuntimeError(f"ESG_MATERIALITY_RUN row not found for runId={runId}")

            cur.execute(
                """
                UPDATE ESG_DMA_SIGNAL_DETAIL
                SET delete_yn = 1
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP),
            )

            if shadowRows:
                cur.executemany(_SHADOW_INSERT_SQL, shadowRows)

            cur.execute(
                """
                UPDATE ESG_DMA_SCORE_SUMMARY
                SET
                    media_external_impact_score = NULL,
                    media_external_financial_score = NULL
                WHERE esg_materiality_run_id = ? AND delete_yn = 0
                """,
                (runId,),
            )

            if summaryRows:
                cur.executemany(
                    """
                    INSERT INTO ESG_DMA_SCORE_SUMMARY (
                        esg_materiality_run_id,
                        sub_issue_code,
                        media_external_impact_score,
                        media_external_financial_score,
                        delete_yn
                    )
                    VALUES (?, ?, ?, ?, 0)
                    ON DUPLICATE KEY UPDATE
                        media_external_impact_score = VALUES(media_external_impact_score),
                        media_external_financial_score = VALUES(media_external_financial_score),
                        delete_yn = 0
                    """,
                    summaryRows,
                )

            cur.execute(
                """
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
                WHERE esg_materiality_run_id = ? AND delete_yn = 0
                ORDER BY sub_issue_code
                """,
                (runId,),
            )
            summaryAllRows = cur.fetchall() or []

            for row in summaryAllRows:
                finalScore = calcFinal(
                    subIssueCode=str(row.get("sub_issue_code") or ""),
                    surveyImpact=safeFloatOrNone(row.get("survey_impact_score")),
                    surveyFinancial=safeFloatOrNone(row.get("survey_financial_score")),
                    benchmarkImpact=safeFloatOrNone(row.get("benchmark_impact_score")),
                    benchmarkFinancial=safeFloatOrNone(row.get("benchmark_financial_score")),
                    mediaImpact=safeFloatOrNone(row.get("media_external_impact_score")),
                    mediaFinancial=safeFloatOrNone(row.get("media_external_financial_score")),
                    contextImpactModifier=clampContextModifier(row.get("context_impact_modifier")),
                    contextFinancialModifier=clampContextModifier(row.get("context_financial_modifier")),
                )
                cur.execute(
                    """
                    UPDATE ESG_DMA_SCORE_SUMMARY
                    SET final_impact_score = ?,
                        final_financial_score = ?,
                        final_score = ?
                    WHERE esg_materiality_run_id = ?
                      AND sub_issue_code = ?
                      AND delete_yn = 0
                    """,
                    (
                        finalScore.finalImpactScore,
                        finalScore.finalFinancialScore,
                        finalScore.finalScore,
                        runId,
                        row.get("sub_issue_code"),
                    ),
                )

            cur.execute(
                "UPDATE ESG_DMA_SCORE_SUMMARY SET rank_no = NULL WHERE esg_materiality_run_id = ? AND delete_yn = 0",
                (runId,),
            )

            cur.execute(
                """
                SELECT id
                FROM ESG_DMA_SCORE_SUMMARY
                WHERE esg_materiality_run_id = ?
                  AND final_score IS NOT NULL
                  AND delete_yn = 0
                ORDER BY final_score DESC, sub_issue_code ASC
                """,
                (runId,),
            )
            rankRows = cur.fetchall() or []
            for idx, rankRow in enumerate(rankRows):
                cur.execute(
                    "UPDATE ESG_DMA_SCORE_SUMMARY SET rank_no = ? WHERE id = ?",
                    (idx + 1, rankRow["id"]),
                )

            cur.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM ESG_DMA_SIGNAL_DETAIL
                WHERE esg_materiality_run_id = ?
                  AND source_step = ?
                  AND delete_yn = 0
                """,
                (runId, MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP),
            )
            verifyRow = cur.fetchone() or {}
            rowCount = int(verifyRow.get("row_count") or 0)
            if rowCount != len(shadowRows):
                raise RuntimeError(
                    f"External MAX shadow count check failed: "
                    f"expected={len(shadowRows)}, row_count={rowCount}"
                )

            cur.execute(
                """
                SELECT COUNT(*) AS observed_count
                FROM ESG_DMA_SCORE_SUMMARY
                WHERE esg_materiality_run_id = ?
                  AND delete_yn = 0
                  AND (
                    media_external_impact_score IS NOT NULL
                    OR media_external_financial_score IS NOT NULL
                  )
                """,
                (runId,),
            )
            obsRow = cur.fetchone() or {}
            observedCount = int(obsRow.get("observed_count") or 0)
            expectedObserved = sum(
                1 for _, _, imp, fin in summaryRows
                if imp is not None or fin is not None
            )
            if observedCount != expectedObserved:
                raise RuntimeError(
                    f"External MAX summary observed count check failed: "
                    f"expected={expectedObserved}, observed_count={observedCount}"
                )

        conn.commit()
        return len(shadowRows)
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        if hasattr(conn, "close"):
            conn.close()


def step4ReadTrace(raw: Union[str, Dict[str, Any], None]) -> Optional[Dict[str, Any]]:
    if isLegacyPayload(raw):
        return None
    payload = _coercePayload(raw)
    try:
        return ScoringPayloadV13(**payload).model_dump(mode="json", by_alias=False)
    except Exception:
        return None


# STEP 4. 기존 v1.3 payload에 factor trace를 추가한 새 dict를 반환한다.
# Input: 기존 v1.3 payload (legacy이면 ValueError), 추가할 FactorTraceV13 목록.
# Output: factorTrace가 추가된 새 payload dict.
def appendFactorTrace(
    existingPayload: Union[str, Dict[str, Any]],
    newFactorTraces: Sequence[Any],
) -> Dict[str, Any]:
    if isLegacyPayload(existingPayload):
        raise ValueError("Refusing to update factor trace on a legacy payload (no legacy migration)")
    payload = copy.deepcopy(_coercePayload(existingPayload)) or {}
    traces = list(payload.get("factorTrace", []))
    for trace in newFactorTraces:
        if isinstance(trace, FactorTraceV13):
            traces.append(trace.model_dump(mode="json", by_alias=False))
        elif isinstance(trace, dict):
            traces.append(FactorTraceV13(**trace).model_dump(mode="json", by_alias=False))
        else:
            raise TypeError("newFactorTraces items must be FactorTraceV13 or dict")
    payload["factorTrace"] = traces
    return payload


# STEP 4. 시그널의 factor trace payload를 갱신한다. Legacy이면 새 v1.3 payload 생성.
# Input: 기존 raw payload (legacy 또는 v1.3), 추가할 traces.
# Output: 갱신된 v1.3 payload dict (DB 저장은 Phase C에서 수행).
def step4UpdateTrace(
    existingRawPayload: Union[str, Dict[str, Any], None],
    newFactorTraces: Sequence[Any],
    *,
    scorePurpose: Union[ScorePurposeV13, str] = ScorePurposeV13.CANONICAL_IRO,
    sourceChannel: Optional[str] = None,
    subIssueCode: Optional[str] = None,
    ruleVersion: Optional[str] = None,
    configHash: Optional[str] = None,
) -> Dict[str, Any]:
    if not isLegacyPayload(existingRawPayload):
        return appendFactorTrace(existingRawPayload, newFactorTraces)

    legacyPresent = _coercePayload(existingRawPayload) is not None
    legacyCompat = LegacyCompatibilityV13(
        legacyScoringPayloadPresentYn=legacyPresent,
        legacyMigratedYn=False,
        legacyScoreReusedYn=False,
        legacyUpdatedYn=False,
    )
    return step4BuildTrace(
        scorePurpose=scorePurpose,
        sourceChannel=sourceChannel,
        subIssueCode=subIssueCode,
        factorTrace=list(newFactorTraces),
        legacyCompatibility=legacyCompat,
        ruleVersion=ruleVersion,
        configHash=configHash,
    )


def resetBenchmarkData(runId: int) -> dict:
    """벤치마킹 재실행 전 기존 데이터 논리 삭제."""
    conn = getConn()
    if not conn:
        raise RuntimeError("resetBenchmarkData: DB 연결 실패")
    try:
        with conn.cursor(dictionary=True) as cur:
            # 기존 evidence에 연결된 TE_SR_FILE을 먼저 논리 삭제
            cur.execute("""
                UPDATE skm.TE_SR_FILE SET delete_yn = 1
                WHERE id IN (
                    SELECT te_sr_file_id FROM ESG_DMA_EVIDENCE
                    WHERE esg_materiality_run_id = ? AND source_step = 'benchmark'
                      AND te_sr_file_id IS NOT NULL AND delete_yn = 0
                )
            """, (runId,))
            cur.execute(
                "UPDATE ESG_DMA_EVIDENCE SET delete_yn = 1 WHERE esg_materiality_run_id = ? AND source_step = 'benchmark' AND delete_yn = 0",
                (runId,),
            )
            evidence_count = cur.rowcount
            cur.execute(
                "UPDATE ESG_DMA_SIGNAL_DETAIL SET delete_yn = 1 WHERE esg_materiality_run_id = ? AND source_step = 'benchmark' AND delete_yn = 0",
                (runId,),
            )
            signal_count = cur.rowcount
            cur.execute(
                "UPDATE ESG_DMA_SCORE_SUMMARY SET benchmark_impact_score = NULL, benchmark_financial_score = NULL WHERE esg_materiality_run_id = ? AND delete_yn = 0",
                (runId,),
            )
        conn.commit()
        return {"evidenceDeleted": evidence_count, "signalsDeleted": signal_count}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def resetMediaData(runId: int) -> dict:
    """미디어 분석 재실행 전 기존 데이터 논리 삭제."""
    conn = getConn()
    if not conn:
        raise RuntimeError("resetMediaData: DB 연결 실패")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "UPDATE ESG_DMA_EVIDENCE SET delete_yn = 1 WHERE esg_materiality_run_id = ? AND source_step = 'media_external' AND delete_yn = 0",
                (runId,),
            )
            evidence_count = cur.rowcount
            cur.execute(
                "UPDATE ESG_DMA_SIGNAL_DETAIL SET delete_yn = 1 WHERE esg_materiality_run_id = ? AND source_step = 'media_external' AND delete_yn = 0",
                (runId,),
            )
            signal_count = cur.rowcount
            cur.execute(
                "UPDATE ESG_DMA_SCORE_SUMMARY SET media_external_impact_score = NULL, media_external_financial_score = NULL WHERE esg_materiality_run_id = ? AND delete_yn = 0",
                (runId,),
            )
        conn.commit()
        return {"evidenceDeleted": evidence_count, "signalsDeleted": signal_count}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def countTop20RankedSubIssues(runId: int) -> int:
    sql = """
        SELECT COUNT(*) AS cnt
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ?
          AND rank_no IS NOT NULL
          AND rank_no <= 20
          AND delete_yn = 0
    """
    row = findOne(sql, (runId,))
    return int(row["cnt"]) if row else 0


def saveKcgsGradeInputRows(
    companyId: int,
    rows: list[dict],
    reviewStatus: str = "APPROVED",
    createdByUserId=None,
) -> int:
    sql = """
        INSERT INTO ESG_DMA_KCGS_GRADE_INPUT (
            company_id, rating_year, overall_grade,
            environment_grade, social_grade, governance_grade,
            source_type, source_document_ref,
            review_status, created_by_user_id, delete_yn
        )
        VALUES (?, ?, ?, ?, ?, ?, 'MANUAL', ?, ?, ?, 0)
        ON DUPLICATE KEY UPDATE
            overall_grade = VALUES(overall_grade),
            environment_grade = VALUES(environment_grade),
            social_grade = VALUES(social_grade),
            governance_grade = VALUES(governance_grade),
            source_document_ref = VALUES(source_document_ref),
            review_status = VALUES(review_status),
            created_by_user_id = VALUES(created_by_user_id),
            delete_yn = 0
    """
    saved = 0
    for row in rows:
        params = (
            companyId,
            row["ratingYear"],
            row.get("overallGrade"),
            row.get("environmentGrade"),
            row.get("socialGrade"),
            row.get("governanceGrade"),
            row.get("sourceDocumentRef"),
            reviewStatus,
            createdByUserId,
        )
        save(sql, params)
        saved += 1
    return saved


__all__ = [
    # STEP 4: v1.3 Payload Trace helpers and shadow persistence
    "BENCHMARK_V13_SHADOW_SOURCE_STEP",
    "BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP",
    "isLegacyPayload",
    "step4BuildTrace",
    "step4WriteTrace",
    "step4ReadTrace",
    "step4UpdateTrace",
    "appendFactorTrace",
    "listBenchmarkShadowObservationRows",
    # step4SaveBenchmarkShadowTraces is intentionally omitted — test compatibility only
    "step4ReplaceBenchmarkShadowTracesTx",
    "step4ReplaceMediaNewsShadowTracesTx",
    "step4ReplaceMediaNewsShadowBundleTx",
    # media_external.regulation Shadow Runtime
    "findRegulationRunContext",
    "listApprovedRegulationInputs",
    "listApprovedActiveRegulationMappings",
    "step4ReplaceRegulationShadowTracesTx",
    # media_external.agency.kcgs Shadow Runtime
    "listApprovedKcgsGradeInputs",
    "step4ReplaceKcgsShadowTracesTx",
    # media_external External MAX Shadow Runtime
    "listExternalMaxEligibleMediaRows",
    "step4ReplaceMediaExternalMaxShadowAndSummaryTx",
    "resetBenchmarkData",
    "resetMediaData",
    "countTop20RankedSubIssues",
    "saveKcgsGradeInputRows",
]