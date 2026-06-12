"""
DMA v1.3 MVP — Phase C3.1.1 media_external.regulation Shadow Runtime Wiring Tests.

54 tests across 6 sections:
  §13.1  Namespace / Schema Guard   (#01-04)
  §13.2  Repository Reader          (#05-13)
  §13.3  Regulation Shadow Serializer (#14-27)
  §13.4  Replace-Active Transaction (#28-39)
  §13.5  Service Hook               (#40-48)
  §13.6  Static Guard               (#49-54)

Pure unit tests. No live DB, Docker, Redis, Kafka, or external API is exercised —
DB access is faked with mock connections/cursors and readers are patched.
"""

import importlib
import inspect
import json
import os
import re
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Standalone-safe environment + module stubs (mirrors the C3.1 foundation test)
# ---------------------------------------------------------------------------

_DUMMY_ENV = {
    "host_ip": "127.0.0.1", "domain": "test", "skm_domain": "test", "file_dir": "/tmp",
    "gemini_api_key": "test", "gemini_model": "test", "kafka_server": "test", "kafka_topic": "test",
    "mail_username": "test", "mail_password": "test", "mail_from": "test@test",
    "access_token_expire_minutes": "1", "refresh_token_expire_days": "1", "invite_token_expire_days": "1",
    "redis_host": "test", "redis_port": "6379", "redis_db1": "0", "redis_db2": "1", "redis_db3": "2",
    "service_key": "test", "maria_db_user": "test", "maria_db_password": "test", "maria_db_host": "test",
    "maria_db_database": "test", "maria_db_port": "3306", "maria_db_key": "test", "cookie_key": "test",
    "APPS_SCRIPT_URL": "test", "pg_db_host": "test", "pg_db_port": "5432", "pg_db_database": "test",
    "pg_db_user": "test", "pg_db_password": "test", "ollama_url": "http://test",
}
for _key, _value in _DUMMY_ENV.items():
    os.environ.setdefault(_key, _value)

if "mariadb" not in sys.modules:
    _mariadb = types.ModuleType("mariadb")
    _mariadb.Error = Exception
    _mariadb.connect = lambda **kwargs: None
    sys.modules["mariadb"] = _mariadb

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

import src.utils.dmaruleregistry as reg  # noqa: E402
import src.utils.dmarepository as repo  # noqa: E402
from src.services.materialities import orchestrator  # noqa: E402
from src.utils.dmarepository import (  # noqa: E402
    MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP,
)


REG_NAMESPACE = "media_external_regulation_v13_shadow"
INPUT_TABLE = "ESG_DMA_REGULATION__INPUT"
MAP_TABLE = "ESG_DMA_REGULATION_SUB_ISSUE_MAP"
RUN_ID = 7

CSRD_SUB = "G_DATA_GOVERNANCE__DISCLOSURE_ASSURANCE"
CBAM_SUB = "E_CLIMATE__GHG_SCOPE12_EMISSIONS"
DPP_SUB = "E_CIRCULARITY__RECYCLING_RECOVERY"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _resetPolicies():
    reg.resetDmaRulesForTest()


def _approvedInput(regime="CSRD", applicability="DIRECT_MANDATORY",
                   companyId=1001, reportingYear=2026):
    return {
        "companyId": companyId,
        "reportingYear": reportingYear,
        "regime": regime,
        "applicability": applicability,
        "inputMethod": "MANUAL",
        "sourceDocumentRef": "board-minutes-1",
        "reviewStatus": "APPROVED",
        "reviewerComment": "approved for shadow runtime test",
    }


def _approvedMapping(regime="CSRD", subIssueCode=CSRD_SUB):
    return {
        "regime": regime,
        "subIssueCode": subIssueCode,
        "mappingReason": "screening seed relation",
        "activeYn": True,
        "reviewStatus": "APPROVED",
    }


def _regPayload(regime="CSRD", applicability="DIRECT_MANDATORY",
                subIssueCode=CSRD_SUB, companyId=1001, reportingYear=2026):
    """Build a real Regulation Screening Payload through the pure orchestrator builder."""
    payloads = orchestrator.step2BuildRegulationScreeningPayloads(
        [_approvedInput(regime=regime, applicability=applicability,
                        companyId=companyId, reportingYear=reportingYear)],
        [_approvedMapping(regime=regime, subIssueCode=subIssueCode)],
    )
    assert len(payloads) == 1, "expected exactly one regulation payload"
    return payloads[0]


def _craftedRegDict():
    """Hand-built serialized payload dict mirroring a valid regulation shadow payload."""
    return {
        "scorePurpose": "PRESURVEY_SCREENING",
        "sourceChannel": "media_external",
        "subIssueCode": CSRD_SUB,
        "screeningTrace": [{
            "channel": "regulation_csrd",
            "scorePurpose": "PRESURVEY_SCREENING",
            "impactSignal": 3.0,
            "financialSignal": 4.0,
            "status": "OBSERVED",
            "rawInputs": {
                "regime": "CSRD",
                "applicability": "DIRECT_MANDATORY",
                "sourceStep": "media_external",
                "sourceType": "regulation",
                "companyId": 1001,
                "reportingYear": 2026,
            },
        }],
    }


# ---------------------------------------------------------------------------
# DB mock helpers
# ---------------------------------------------------------------------------

class _MockCursor:
    """Context-manager cursor with a fetchone queue; records every SQL call."""

    def __init__(self, fetchone_queue=None, raise_on_update=False):
        self.sql_log = []
        self._queue = list(fetchone_queue or [])
        self._raise_on_update = raise_on_update

    def execute(self, sql, params=None):
        self.sql_log.append(("x", sql.strip(), params))
        if self._raise_on_update and "UPDATE" in sql and "delete_yn" in sql:
            raise RuntimeError("Simulated DB write error")

    def executemany(self, sql, rows):
        self.sql_log.append(("xm", sql.strip(), rows))

    def fetchone(self):
        return self._queue.pop(0) if self._queue else None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _MockConn:
    def __init__(self, cursor=None):
        self.autocommit = True
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self._cursor = cursor or _MockCursor()

    def cursor(self, **kwargs):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _runTx(payloads, fetchone_queue):
    conn = _MockConn(cursor=_MockCursor(fetchone_queue=fetchone_queue))
    with patch("src.utils.dmarepository.getConn", return_value=conn):
        result = repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, payloads)
    return result, conn


# =========================================================
# §13.1  Namespace / Schema Guard  (#01-04)
# =========================================================

class PhaseC311NamespaceGuardTest(unittest.TestCase):

    def test_01_regulation_namespace_literal_ssot(self):
        # Constant value is the canonical namespace.
        self.assertEqual(MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP, REG_NAMESPACE)
        # The literal string appears only inside dmarepository.py across src.
        violations = []
        for py_file in (ROOT / "src").rglob("*.py"):
            if "dmarepository" in py_file.name:
                continue
            try:
                text = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if REG_NAMESPACE in text:
                violations.append(str(py_file.relative_to(ROOT)))
        self.assertEqual(violations, [], f"Namespace literal leaked outside dmarepository: {violations}")

    def test_02_real_double_underscore_table_name_used(self):
        source = (ROOT / "src/utils/dmarepository.py").read_text(encoding="utf-8")
        self.assertIn(INPUT_TABLE, source)

    def test_03_wrong_single_underscore_table_name_absent(self):
        # ESG_DMA_REGULATION_INPUT (single underscore) must never appear in src.
        bad = re.compile(r"ESG_DMA_REGULATION_(?!_)INPUT")
        offenders = []
        for py_file in (ROOT / "src").rglob("*.py"):
            try:
                text = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if bad.search(text):
                offenders.append(str(py_file.relative_to(ROOT)))
        self.assertEqual(offenders, [], f"Forbidden single-underscore table name found in: {offenders}")

    def test_04_no_new_source_step_ddl_in_code(self):
        for rel in ("src/utils/dmarepository.py", "src/services/medias/service.py"):
            source = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("VARCHAR(80)", source, f"{rel} must not re-declare source_step DDL")
            self.assertNotIn("ALTER TABLE", source, f"{rel} must not contain DDL")


# =========================================================
# §13.2  Repository Reader  (#05-13)
# =========================================================

class PhaseC311ReaderTest(unittest.TestCase):

    def _captureFindOne(self, return_value):
        captured = {}

        def fake(sql, params=None):
            captured["sql"] = sql
            captured["params"] = params
            return return_value

        return captured, fake

    def _captureFindAll(self, return_value):
        captured = {}

        def fake(sql, params=None):
            captured["sql"] = sql
            captured["params"] = params
            return return_value

        return captured, fake

    def test_05_run_context_camelcase_alias(self):
        captured, fake = self._captureFindOne(
            {"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026}
        )
        with patch("src.utils.dmarepository.findOne", side_effect=fake):
            result = repo.findRegulationRunContext(RUN_ID)
        self.assertEqual(result["companyId"], 1001)
        self.assertEqual(result["reportingYear"], 2026)
        self.assertIn("id AS runId", captured["sql"])
        self.assertIn("company_id AS companyId", captured["sql"])
        self.assertIn("reporting_year AS reportingYear", captured["sql"])
        self.assertEqual(captured["params"], (RUN_ID,))

    def test_06_run_context_missing_row_raises_runtime_error(self):
        _, fake = self._captureFindOne(None)
        with patch("src.utils.dmarepository.findOne", side_effect=fake):
            with self.assertRaises(RuntimeError) as ctx:
                repo.findRegulationRunContext(RUN_ID)
        self.assertIn("not found", str(ctx.exception))

    def test_07_input_reader_approved_only_sql(self):
        captured, fake = self._captureFindAll([])
        with patch("src.utils.dmarepository.findAll", side_effect=fake):
            repo.listApprovedRegulationInputs(1001, 2026)
        self.assertIn("review_status = 'APPROVED'", captured["sql"])
        self.assertIn(INPUT_TABLE, captured["sql"])
        self.assertEqual(captured["params"], (1001, 2026))

    def test_08_input_reader_delete_yn_zero_sql(self):
        captured, fake = self._captureFindAll([])
        with patch("src.utils.dmarepository.findAll", side_effect=fake):
            repo.listApprovedRegulationInputs(1001, 2026)
        self.assertIn("delete_yn = 0", captured["sql"])

    def test_09_input_reader_camelcase_alias(self):
        captured, fake = self._captureFindAll([])
        with patch("src.utils.dmarepository.findAll", side_effect=fake):
            repo.listApprovedRegulationInputs(1001, 2026)
        for alias in ("company_id AS companyId", "reporting_year AS reportingYear",
                      "input_method AS inputMethod", "source_document_ref AS sourceDocumentRef",
                      "review_status AS reviewStatus", "reviewer_comment AS reviewerComment"):
            self.assertIn(alias, captured["sql"])

    def test_10_mapping_reader_approved_only_sql(self):
        captured, fake = self._captureFindAll([])
        with patch("src.utils.dmarepository.findAll", side_effect=fake):
            repo.listApprovedActiveRegulationMappings()
        self.assertIn("review_status = 'APPROVED'", captured["sql"])
        self.assertIn(MAP_TABLE, captured["sql"])

    def test_11_mapping_reader_active_yn_sql(self):
        captured, fake = self._captureFindAll([])
        with patch("src.utils.dmarepository.findAll", side_effect=fake):
            repo.listApprovedActiveRegulationMappings()
        self.assertIn("active_yn = 1", captured["sql"])

    def test_12_mapping_reader_delete_yn_zero_sql(self):
        captured, fake = self._captureFindAll([])
        with patch("src.utils.dmarepository.findAll", side_effect=fake):
            repo.listApprovedActiveRegulationMappings()
        self.assertIn("delete_yn = 0", captured["sql"])

    def test_13_mapping_reader_deterministic_order_by(self):
        captured, fake = self._captureFindAll([])
        with patch("src.utils.dmarepository.findAll", side_effect=fake):
            repo.listApprovedActiveRegulationMappings()
        self.assertIn("ORDER BY regime, sub_issue_code", captured["sql"])


# =========================================================
# §13.3  Regulation Shadow Serializer  (#14-27)
# =========================================================

class PhaseC311SerializerTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    def _serializeCrafted(self, mutator):
        data = _craftedRegDict()
        mutator(data)
        with patch("src.utils.dmarepository.step4WriteTrace", return_value=json.dumps(data)):
            return repo._buildRegulationShadowRows(RUN_ID, [{}])

    def test_14_valid_direct_mandatory_payload_yields_one_row(self):
        rows = repo._buildRegulationShadowRows(RUN_ID, [_regPayload()])
        self.assertEqual(len(rows), 1)

    def test_15_raw_issue_label_is_regime(self):
        rows = repo._buildRegulationShadowRows(RUN_ID, [_regPayload(regime="CBAM", subIssueCode=CBAM_SUB)])
        self.assertEqual(rows[0][2], "CBAM")

    def test_16_source_step_is_regulation_namespace(self):
        rows = repo._buildRegulationShadowRows(RUN_ID, [_regPayload()])
        self.assertEqual(rows[0][4], MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP)

    def test_17_source_type_is_regulation(self):
        rows = repo._buildRegulationShadowRows(RUN_ID, [_regPayload()])
        self.assertEqual(rows[0][5], "regulation")

    def test_18_impact_and_financial_signal_stored(self):
        # CSRD DIRECT_MANDATORY → impact 3.0, financial 4.0
        rows = repo._buildRegulationShadowRows(RUN_ID, [_regPayload()])
        self.assertEqual(rows[0][6], 3.0)
        self.assertEqual(rows[0][7], 4.0)

    def test_19_unknown_applicability_yields_none_scores(self):
        rows = repo._buildRegulationShadowRows(RUN_ID, [_regPayload(applicability="UNKNOWN")])
        self.assertIsNone(rows[0][6])
        self.assertIsNone(rows[0][7])

    def test_20_not_applicable_yields_zero_scores(self):
        rows = repo._buildRegulationShadowRows(RUN_ID, [_regPayload(applicability="NOT_APPLICABLE")])
        self.assertEqual(rows[0][6], 0.0)
        self.assertEqual(rows[0][7], 0.0)
        # Explicit zero must NOT be None.
        self.assertIsNotNone(rows[0][6])
        self.assertIsNotNone(rows[0][7])

    def test_21_score_purpose_mismatch_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self._serializeCrafted(lambda d: d.__setitem__("scorePurpose", "CANONICAL_IRO"))
        self.assertIn("scorePurpose", str(ctx.exception))

    def test_22_source_channel_mismatch_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self._serializeCrafted(lambda d: d.__setitem__("sourceChannel", "benchmark"))
        self.assertIn("sourceChannel", str(ctx.exception))

    def test_23_missing_sub_issue_code_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self._serializeCrafted(lambda d: d.__setitem__("subIssueCode", None))
        self.assertIn("subIssueCode", str(ctx.exception))

    def test_24_missing_screening_trace_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self._serializeCrafted(lambda d: d.__setitem__("screeningTrace", []))
        self.assertIn("screeningTrace", str(ctx.exception))

    def test_25_multiple_screening_trace_rows_raise_value_error(self):
        def mutate(d):
            d["screeningTrace"] = [d["screeningTrace"][0], dict(d["screeningTrace"][0])]
        with self.assertRaises(ValueError) as ctx:
            self._serializeCrafted(mutate)
        self.assertIn("screeningTrace", str(ctx.exception))

    def test_26_raw_inputs_source_type_mismatch_raises_value_error(self):
        def mutate(d):
            d["screeningTrace"][0]["rawInputs"]["sourceType"] = "news"
        with self.assertRaises(ValueError) as ctx:
            self._serializeCrafted(mutate)
        self.assertIn("sourceType", str(ctx.exception))

    def test_27_non_positive_company_id_raises_value_error(self):
        def mutate(d):
            d["screeningTrace"][0]["rawInputs"]["companyId"] = 0
        with self.assertRaises(ValueError) as ctx:
            self._serializeCrafted(mutate)
        self.assertIn("companyId", str(ctx.exception))


# =========================================================
# §13.4  Replace-Active Transaction  (#28-39)
# =========================================================

class PhaseC311ReplaceTxTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    def test_28_pre_db_serialization_failure_skips_getconn(self):
        bad_json = json.dumps(_craftedRegDict() | {"sourceChannel": "benchmark"})
        with patch("src.utils.dmarepository.step4WriteTrace", return_value=bad_json), \
             patch("src.utils.dmarepository.getConn") as mock_gc:
            with self.assertRaises(ValueError):
                repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, [{}])
            mock_gc.assert_not_called()

    def test_29_none_conn_raises_runtime_error(self):
        with patch("src.utils.dmarepository.getConn", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, [])
        self.assertIn("not available", str(ctx.exception))

    def test_30_autocommit_set_false(self):
        _, conn = _runTx([_regPayload()], [{"id": RUN_ID}, {"row_count": 1}])
        self.assertFalse(conn.autocommit)

    def test_31_run_row_locked_for_update(self):
        _, conn = _runTx([_regPayload()], [{"id": RUN_ID}, {"row_count": 1}])
        lock = [(s, p) for kind, s, p in conn._cursor.sql_log
                if kind == "x" and "FOR UPDATE" in s]
        self.assertEqual(len(lock), 1)
        self.assertIn("ESG_MATERIALITY_RUN", lock[0][0])
        self.assertEqual(lock[0][1], (RUN_ID,))

    def test_32_soft_delete_only_regulation_namespace(self):
        _, conn = _runTx([_regPayload()], [{"id": RUN_ID}, {"row_count": 1}])
        updates = [(s, p) for kind, s, p in conn._cursor.sql_log
                   if kind == "x" and "SET delete_yn = 1" in s]
        self.assertEqual(len(updates), 1)
        params = updates[0][1]
        self.assertEqual(len(params), 2)
        self.assertIn(MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP, params)
        for other in (
            repo.MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP,
            repo.MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP,
            repo.BENCHMARK_V13_SHADOW_SOURCE_STEP,
        ):
            self.assertNotIn(other, params)

    def test_33_insert_rows_via_executemany(self):
        _, conn = _runTx([_regPayload()], [{"id": RUN_ID}, {"row_count": 1}])
        inserts = [rows for kind, s, rows in conn._cursor.sql_log if kind == "xm"]
        self.assertEqual(len(inserts), 1)
        self.assertEqual(len(inserts[0]), 1)

    def test_34_active_count_verified_with_count_star(self):
        _, conn = _runTx([_regPayload()], [{"id": RUN_ID}, {"row_count": 1}])
        counts = [s for kind, s, p in conn._cursor.sql_log
                  if kind == "x" and "COUNT(*)" in s]
        self.assertEqual(len(counts), 1)

    def test_35_count_distinct_is_forbidden(self):
        _, conn = _runTx([_regPayload()], [{"id": RUN_ID}, {"row_count": 1}])
        for kind, s, p in conn._cursor.sql_log:
            self.assertNotIn("COUNT(DISTINCT", s)
        source = inspect.getsource(repo.step4ReplaceRegulationShadowTracesTx)
        self.assertNotIn("COUNT(DISTINCT", source)

    def test_36_empty_clear_inserts_nothing_and_commits(self):
        result, conn = _runTx([], [{"id": RUN_ID}, {"row_count": 0}])
        self.assertEqual(result, 0)
        self.assertEqual([c for c in conn._cursor.sql_log if c[0] == "xm"], [])
        self.assertTrue(conn.committed)
        # Empty clear still soft-deletes the prior active set.
        self.assertTrue(any("SET delete_yn = 1" in s for kind, s, p in conn._cursor.sql_log))

    def test_37_count_mismatch_triggers_rollback_and_close(self):
        conn = _MockConn(cursor=_MockCursor(fetchone_queue=[{"id": RUN_ID}, {"row_count": 99}]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError) as ctx:
                repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, [_regPayload()])
        self.assertIn("count check failed", str(ctx.exception).lower())
        self.assertTrue(conn.rolled_back)
        self.assertTrue(conn.closed)

    def test_38_run_not_found_triggers_rollback_and_close(self):
        conn = _MockConn(cursor=_MockCursor(fetchone_queue=[None]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError) as ctx:
                repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, [])
        self.assertIn("not found", str(ctx.exception))
        self.assertTrue(conn.rolled_back)
        self.assertTrue(conn.closed)

    def test_39_happy_path_commits_and_closes(self):
        result, conn = _runTx([_regPayload()], [{"id": RUN_ID}, {"row_count": 1}])
        self.assertEqual(result, 1)
        self.assertTrue(conn.committed)
        self.assertFalse(conn.rolled_back)
        self.assertTrue(conn.closed)


# =========================================================
# §13.5  Service Hook  (#40-48)
# =========================================================

class PhaseC311ServiceHookTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()
        sys.modules.pop("src.services.medias.service", None)
        self.svc = importlib.import_module("src.services.medias.service")

    def _fakeCrawlResult(self, articles=None, allowedSources=None, errors=None):
        return types.SimpleNamespace(
            articles=articles or [],
            allowedSources=allowedSources or [],
            errors=errors or [],
            sourceBreakdown=[],
            requestedSources=[],
            rejectedSources=[],
            collectedArticleCount=0,
            filteredArticleCount=0,
        )

    def _request(self):
        from src.models.media import MediaNewsCrawlAnalyzeRequest
        return MediaNewsCrawlAnalyzeRequest(
            runId=RUN_ID, sources=["naver"], dateFrom="2026-01-01", dateTo="2026-01-31"
        )

    def test_40_refresh_runs_reader_builder_writer_in_order(self):
        svc = self.svc
        ctx = MagicMock(return_value={"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026})
        inputs = MagicMock(return_value=[_approvedInput()])
        mappings = MagicMock(return_value=[_approvedMapping()])
        builder = MagicMock(return_value=["PAYLOAD"])
        writer = MagicMock(return_value=1)
        manager = MagicMock()
        manager.attach_mock(ctx, "ctx")
        manager.attach_mock(inputs, "inputs")
        manager.attach_mock(mappings, "mappings")
        manager.attach_mock(builder, "builder")
        manager.attach_mock(writer, "writer")

        with patch.object(svc, "findRegulationRunContext", ctx), \
             patch.object(svc, "listApprovedRegulationInputs", inputs), \
             patch.object(svc, "listApprovedActiveRegulationMappings", mappings), \
             patch.object(svc, "step2BuildRegulationScreeningPayloads", builder), \
             patch.object(svc, "step4ReplaceRegulationShadowTracesTx", writer):
            result = svc.refreshRegulationShadowForRun(RUN_ID)

        self.assertEqual(result, 1)
        inputs.assert_called_once_with(1001, 2026)
        builder.assert_called_once_with([_approvedInput()], [_approvedMapping()])
        writer.assert_called_once_with(RUN_ID, ["PAYLOAD"])
        ordered = [c[0] for c in manager.mock_calls]
        self.assertEqual(
            ordered, ["ctx", "inputs", "mappings", "builder", "writer"]
        )

    def test_41_empty_approved_input_writes_empty_payloads(self):
        svc = self.svc
        with patch.object(svc, "findRegulationRunContext",
                          return_value={"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026}), \
             patch.object(svc, "listApprovedRegulationInputs", return_value=[]), \
             patch.object(svc, "listApprovedActiveRegulationMappings",
                          return_value=[_approvedMapping()]), \
             patch.object(svc, "step4ReplaceRegulationShadowTracesTx", return_value=0) as writer:
            svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_called_once_with(RUN_ID, [])

    def test_42_empty_mapping_writes_empty_payloads(self):
        svc = self.svc
        with patch.object(svc, "findRegulationRunContext",
                          return_value={"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026}), \
             patch.object(svc, "listApprovedRegulationInputs",
                          return_value=[_approvedInput()]), \
             patch.object(svc, "listApprovedActiveRegulationMappings", return_value=[]), \
             patch.object(svc, "step4ReplaceRegulationShadowTracesTx", return_value=0) as writer:
            svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_called_once_with(RUN_ID, [])

    def test_43_reader_failure_skips_writer(self):
        svc = self.svc
        with patch.object(svc, "findRegulationRunContext",
                          side_effect=RuntimeError("run missing")), \
             patch.object(svc, "step4ReplaceRegulationShadowTracesTx") as writer:
            with self.assertRaises(RuntimeError):
                svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_not_called()

    def test_44_builder_failure_skips_writer(self):
        svc = self.svc
        with patch.object(svc, "findRegulationRunContext",
                          return_value={"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026}), \
             patch.object(svc, "listApprovedRegulationInputs",
                          return_value=[_approvedInput()]), \
             patch.object(svc, "listApprovedActiveRegulationMappings",
                          return_value=[_approvedMapping()]), \
             patch.object(svc, "step2BuildRegulationScreeningPayloads",
                          side_effect=ValueError("builder broke")), \
             patch.object(svc, "step4ReplaceRegulationShadowTracesTx") as writer:
            with self.assertRaises(ValueError):
                svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_not_called()

    def test_45_crawl_and_analyze_refreshes_regulation_exactly_once(self):
        svc = self.svc
        crawl_result = self._fakeCrawlResult()
        with patch.object(svc, "crawlNewsArticles", return_value=crawl_result), \
             patch.object(svc, "applySavedSignalCounts", return_value=[]), \
             patch.object(svc, "getMediaCoverage", return_value={"coverageStatus": "NO_DATA"}), \
             patch.object(svc, "countMediaSubIssues", return_value=0), \
             patch.object(svc, "_buildMediaTopIssues", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0) as refresh:
            svc.runMediaCrawlAndAnalyze(self._request())
        refresh.assert_called_once_with(RUN_ID)

    def test_46_regulation_refresh_attempted_even_when_crawl_failed(self):
        svc = self.svc
        crawl_result = self._fakeCrawlResult(
            allowedSources=["naver"],
            errors=[{"sourceKey": "naver", "message": "timeout", "recoverableYn": True}],
        )
        with patch.object(svc, "crawlNewsArticles", return_value=crawl_result), \
             patch.object(svc, "applySavedSignalCounts", return_value=[]), \
             patch.object(svc, "getMediaCoverage", return_value={"coverageStatus": "NO_DATA"}), \
             patch.object(svc, "countMediaSubIssues", return_value=0), \
             patch.object(svc, "_buildMediaTopIssues", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0) as refresh:
            svc.runMediaCrawlAndAnalyze(self._request())
        refresh.assert_called_once_with(RUN_ID)

    def test_47_regulation_refresh_failure_preserves_media_response(self):
        svc = self.svc
        crawl_result = self._fakeCrawlResult()
        with patch.object(svc, "crawlNewsArticles", return_value=crawl_result), \
             patch.object(svc, "applySavedSignalCounts", return_value=[]), \
             patch.object(svc, "getMediaCoverage", return_value={"coverageStatus": "NO_DATA"}), \
             patch.object(svc, "countMediaSubIssues", return_value=0), \
             patch.object(svc, "_buildMediaTopIssues", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun",
                          side_effect=RuntimeError("regulation TX kaboom")), \
             patch("builtins.print"):
            response = svc.runMediaCrawlAndAnalyze(self._request())
        self.assertEqual(response.runId, RUN_ID)
        self.assertEqual(response.coverageStatus, "NO_DATA")

    def test_48_run_media_analysis_does_not_refresh_regulation(self):
        svc = self.svc
        with patch.object(svc, "processMediaPipeline", return_value=[]), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=[]), \
             patch.object(svc, "_replaceMediaNewsShadowFromPipelineResults"), \
             patch.object(svc, "refreshRegulationShadowForRun") as refresh:
            svc.runMediaAnalysis(articles=[], runId=RUN_ID, shadowReplaceYn=True)
        refresh.assert_not_called()
        self.assertNotIn(
            "refreshRegulationShadowForRun",
            inspect.getsource(svc.runMediaAnalysis),
        )


# =========================================================
# §13.6  Static Guard  (#49-54)
# =========================================================

class PhaseC311StaticGuardTest(unittest.TestCase):

    def _regulationSources(self):
        return "\n".join([
            inspect.getsource(repo.findRegulationRunContext),
            inspect.getsource(repo.listApprovedRegulationInputs),
            inspect.getsource(repo.listApprovedActiveRegulationMappings),
            inspect.getsource(repo._buildRegulationShadowRows),
            inspect.getsource(repo.step4ReplaceRegulationShadowTracesTx),
        ])

    def _gitNames(self, *paths):
        result = subprocess.run(
            ["git", "diff", "--name-only", "--", *paths],
            cwd=REPO, text=True, capture_output=True, check=True,
        )
        return [line for line in result.stdout.splitlines() if line.strip()]

    def test_49_no_summary_or_rank_calls_in_regulation_path(self):
        svc = importlib.import_module("src.services.medias.service")
        sources = self._regulationSources() + inspect.getsource(svc.refreshRegulationShadowForRun)
        for banned in ("recalcStage(", "upsertStage(", "recalcFinal(", "updateRanks("):
            self.assertNotIn(banned, sources)

    def test_50_no_external_max_in_regulation_path(self):
        svc = importlib.import_module("src.services.medias.service")
        sources = self._regulationSources() + inspect.getsource(svc.refreshRegulationShadowForRun)
        self.assertNotIn("externalMax", sources)

    def test_51_kcgs_kis_sources_untouched(self):
        # Only dmarepository.py and service.py may appear in the production diff.
        changed = self._gitNames("backend/src")
        allowed = {
            "backend/src/utils/dmarepository.py",
            "backend/src/services/medias/service.py",
        }
        self.assertTrue(set(changed).issubset(allowed), f"Unexpected production diff: {changed}")

    def test_52_no_api_or_frontend_diff(self):
        self.assertEqual(self._gitNames("backend/src/apis", "frontend"), [])

    def test_53_no_sql_or_ddl_diff(self):
        self.assertEqual(self._gitNames("*.sql"), [])
        for rel in ("src/utils/dmarepository.py", "src/services/medias/service.py"):
            source = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("CREATE TABLE", source)
            self.assertNotIn("ALTER TABLE", source)

    def test_54_no_eval_or_exec(self):
        for rel in ("src/utils/dmarepository.py", "src/services/medias/service.py"):
            source = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("eval(", source)
            self.assertNotIn("exec(", source)


if __name__ == "__main__":
    unittest.main()
