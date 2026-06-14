"""
DMA Benchmark F1-B — Workflow Progress Polling Tests

Coverage:
§10.1  Repository Constants / Validation     (#01-#15)
§10.2  Repository Strict DB                  (#16-#30)
§10.3  API Endpoint                          (#31-#35)
§10.4  Benchmark Service Milestone           (#36-#44)
§10.5  Benchmark Service Failure Recording   (#45-#56)
§10.6  Frontend Static Contract              (#57-#77)
"""

import asyncio
import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

# ── env bootstrap ─────────────────────────────────────────────────────────────

_DUMMY_ENV = {
    "host_ip": "127.0.0.1", "domain": "test", "skm_domain": "test",
    "file_dir": "/tmp", "gemini_api_key": "test", "gemini_model": "test",
    "kafka_server": "test", "kafka_topic": "test",
    "mail_username": "test", "mail_password": "test", "mail_from": "t@t",
    "access_token_expire_minutes": "1", "refresh_token_expire_days": "1",
    "invite_token_expire_days": "1",
    "redis_host": "test", "redis_port": "6379", "redis_db1": "0",
    "redis_db2": "1", "redis_db3": "2",
    "service_key": "test", "maria_db_user": "test", "maria_db_password": "test",
    "maria_db_host": "test", "maria_db_database": "test", "maria_db_port": "3306",
    "maria_db_key": "test", "cookie_key": "test", "APPS_SCRIPT_URL": "test",
    "pg_db_host": "test", "pg_db_port": "5432", "pg_db_database": "test",
    "pg_db_user": "test", "pg_db_password": "test", "ollama_url": "http://test",
}
for _k, _v in _DUMMY_ENV.items():
    os.environ.setdefault(_k, _v)

if "mariadb" not in sys.modules:
    _mariadb = types.ModuleType("mariadb")
    _mariadb.Error = Exception
    _mariadb.connect = lambda **kwargs: None
    sys.modules["mariadb"] = _mariadb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.dmaworkflowrepository import (  # noqa: E402
    WORKFLOW_TYPES,
    OVERALL_STATUSES,
    PROGRESS_MODES,
    _validateUpsertArgs,
    upsertDmaWorkflowStatus,
    getDmaWorkflowStatus,
    getDmaWorkflowStatusOrDefault,
)

# ── file paths ─────────────────────────────────────────────────────────────────

_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src"
_BENCH_JSX = _FRONTEND_DIR / "homes" / "reports" / "BenchMarking.jsx"

# ── fake DB helpers ────────────────────────────────────────────────────────────

class _FakeCursor:
    def __init__(self, fetchone_result=None):
        self._fetchone_result = fetchone_result
        self.executed_sql = None
        self.executed_params = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self.executed_sql = sql
        self.executed_params = params

    def fetchone(self):
        return self._fetchone_result


class _FakeConn:
    def __init__(self, cursor=None):
        self._cursor = cursor or _FakeCursor()
        self.autocommit = None
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, dictionary=True):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _make_status_row(
    runId=1,
    workflowType="BENCHMARK",
    overallStatus="RUNNING",
    currentStage="PREPARE",
    progressPercent=20,
    progressMode="MILESTONE",
    processedCount=None,
    totalCount=None,
    errorStage=None,
    errorMessage=None,
    startedAt=None,
    completedAt=None,
    updatedAt=None,
):
    return {
        "runId": runId,
        "workflowType": workflowType,
        "overallStatus": overallStatus,
        "currentStage": currentStage,
        "progressPercent": progressPercent,
        "progressMode": progressMode,
        "processedCount": processedCount,
        "totalCount": totalCount,
        "errorStage": errorStage,
        "errorMessage": errorMessage,
        "startedAt": startedAt,
        "completedAt": completedAt,
        "updatedAt": updatedAt,
    }


# ══════════════════════════════════════════════════════════════════════════════
# §10.1  Repository Constants / Validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF1BRepositoryConstants(unittest.TestCase):
    """#01-#10 Constant sets and validation logic."""

    def test_01_workflow_types_contains_benchmark(self):
        self.assertIn("BENCHMARK", WORKFLOW_TYPES)

    def test_02_workflow_types_contains_media(self):
        self.assertIn("MEDIA", WORKFLOW_TYPES)

    def test_03_workflow_types_contains_survey_form(self):
        self.assertIn("SURVEY_FORM", WORKFLOW_TYPES)

    def test_04_overall_statuses_contains_all_required(self):
        for s in ("WAITING", "RUNNING", "COMPLETED", "FAILED", "RETRYABLE"):
            with self.subTest(s=s):
                self.assertIn(s, OVERALL_STATUSES)

    def test_05_progress_modes_contains_milestone(self):
        self.assertIn("MILESTONE", PROGRESS_MODES)

    def test_06_progress_modes_contains_actual_count(self):
        self.assertIn("ACTUAL_COUNT", PROGRESS_MODES)

    def test_07_validate_rejects_bool_run_id(self):
        with self.assertRaises(ValueError):
            _validateUpsertArgs(True, "BENCHMARK", "RUNNING", "PREPARE", 0, "MILESTONE", None, None)

    def test_08_validate_rejects_zero_run_id(self):
        with self.assertRaises(ValueError):
            _validateUpsertArgs(0, "BENCHMARK", "RUNNING", "PREPARE", 0, "MILESTONE", None, None)

    def test_09_validate_rejects_negative_run_id(self):
        with self.assertRaises(ValueError):
            _validateUpsertArgs(-1, "BENCHMARK", "RUNNING", "PREPARE", 0, "MILESTONE", None, None)

    def test_10_validate_rejects_invalid_workflow_type(self):
        with self.assertRaises(ValueError):
            _validateUpsertArgs(1, "INVALID_TYPE", "RUNNING", "PREPARE", 0, "MILESTONE", None, None)

    def test_11_validate_rejects_invalid_overall_status(self):
        with self.assertRaises(ValueError):
            _validateUpsertArgs(1, "BENCHMARK", "PENDING", "PREPARE", 0, "MILESTONE", None, None)

    def test_12_validate_rejects_invalid_progress_mode(self):
        with self.assertRaises(ValueError):
            _validateUpsertArgs(1, "BENCHMARK", "RUNNING", "PREPARE", 0, "INCREMENTAL", None, None)

    def test_13_validate_rejects_blank_current_stage(self):
        with self.assertRaises(ValueError):
            _validateUpsertArgs(1, "BENCHMARK", "RUNNING", "   ", 0, "MILESTONE", None, None)

    def test_14_validate_rejects_progress_percent_out_of_range(self):
        with self.assertRaises(ValueError):
            _validateUpsertArgs(1, "BENCHMARK", "RUNNING", "PREPARE", 101, "MILESTONE", None, None)
        with self.assertRaises(ValueError):
            _validateUpsertArgs(1, "BENCHMARK", "RUNNING", "PREPARE", -1, "MILESTONE", None, None)

    def test_15_validate_rejects_processed_count_exceeding_total_count(self):
        with self.assertRaises(ValueError):
            _validateUpsertArgs(1, "BENCHMARK", "RUNNING", "PREPARE", 50, "ACTUAL_COUNT", 6, 5)


# ══════════════════════════════════════════════════════════════════════════════
# §10.2  Repository Strict DB
# ══════════════════════════════════════════════════════════════════════════════

import src.utils.dmaworkflowrepository as _repo  # noqa: E402


class TestF1BRepositoryStrictDB(unittest.TestCase):
    """#16-#30 DB interaction tests using fake connection."""

    def _upsert(self, conn, **kwargs):
        defaults = dict(
            runId=1, workflowType="BENCHMARK", overallStatus="RUNNING",
            currentStage="PREPARE", progressPercent=20,
        )
        defaults.update(kwargs)
        with patch.object(_repo, "getConn", return_value=conn):
            upsertDmaWorkflowStatus(**defaults)

    def test_16_upsert_commits_on_success(self):
        conn = _FakeConn()
        self._upsert(conn)
        self.assertTrue(conn.committed)

    def test_17_upsert_calls_close_on_success(self):
        conn = _FakeConn()
        self._upsert(conn)
        self.assertTrue(conn.closed)

    def test_18_upsert_sets_autocommit_false(self):
        conn = _FakeConn()
        self._upsert(conn)
        self.assertFalse(conn.autocommit)

    def test_19_upsert_executes_insert_into_workflow_status_table(self):
        conn = _FakeConn()
        self._upsert(conn)
        sql = conn._cursor.executed_sql or ""
        self.assertIn("ESG_DMA_WORKFLOW_STATUS", sql)
        self.assertIn("INSERT", sql.upper())

    def test_20_upsert_sql_contains_on_duplicate_key_update(self):
        conn = _FakeConn()
        self._upsert(conn)
        sql = conn._cursor.executed_sql or ""
        self.assertIn("ON DUPLICATE KEY UPDATE", sql.upper())

    def test_21_upsert_raises_runtime_error_when_conn_is_none(self):
        with patch.object(_repo, "getConn", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                upsertDmaWorkflowStatus(
                    runId=1, workflowType="BENCHMARK", overallStatus="RUNNING",
                    currentStage="PREPARE", progressPercent=20,
                )
            self.assertIn("unavailable", str(ctx.exception))

    def test_22_upsert_rollback_and_reraise_on_execute_failure(self):
        cur = _FakeCursor()
        cur.execute = MagicMock(side_effect=Exception("db error"))
        conn = _FakeConn(cursor=cur)
        with patch.object(_repo, "getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                upsertDmaWorkflowStatus(
                    runId=1, workflowType="BENCHMARK", overallStatus="RUNNING",
                    currentStage="PREPARE", progressPercent=20,
                )
        self.assertTrue(conn.rolled_back)

    def test_23_upsert_close_called_even_on_execute_failure(self):
        cur = _FakeCursor()
        cur.execute = MagicMock(side_effect=Exception("db error"))
        conn = _FakeConn(cursor=cur)
        with patch.object(_repo, "getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                upsertDmaWorkflowStatus(
                    runId=1, workflowType="BENCHMARK", overallStatus="RUNNING",
                    currentStage="PREPARE", progressPercent=20,
                )
        self.assertTrue(conn.closed)

    def test_24_upsert_started_at_set_when_started_yn_true(self):
        conn = _FakeConn()
        self._upsert(conn, startedYn=True)
        params = conn._cursor.executed_params
        self.assertIsNotNone(params[10])  # started_at index

    def test_25_upsert_started_at_none_when_started_yn_false(self):
        conn = _FakeConn()
        self._upsert(conn, startedYn=False)
        params = conn._cursor.executed_params
        self.assertIsNone(params[10])  # started_at index

    def test_26_upsert_completed_at_set_when_completed_yn_true(self):
        conn = _FakeConn()
        self._upsert(conn, completedYn=True)
        params = conn._cursor.executed_params
        self.assertIsNotNone(params[11])  # completed_at index

    def test_27_upsert_completed_at_none_when_completed_yn_false(self):
        conn = _FakeConn()
        self._upsert(conn, completedYn=False)
        params = conn._cursor.executed_params
        self.assertIsNone(params[11])  # completed_at index

    def test_28_get_raises_runtime_error_when_conn_is_none(self):
        with patch.object(_repo, "getConn", return_value=None):
            with self.assertRaises(RuntimeError):
                getDmaWorkflowStatus(runId=1, workflowType="BENCHMARK")

    def test_29_get_or_default_returns_waiting_row_when_no_db_row(self):
        cur = _FakeCursor(fetchone_result=None)
        conn = _FakeConn(cursor=cur)
        with patch.object(_repo, "getConn", return_value=conn):
            result = getDmaWorkflowStatusOrDefault(runId=5, workflowType="BENCHMARK")
        self.assertEqual(result["overallStatus"], "WAITING")
        self.assertEqual(result["progressPercent"], 0)
        self.assertEqual(result["runId"], 5)
        self.assertEqual(result["workflowType"], "BENCHMARK")

    def test_30_get_or_default_returns_db_row_when_found(self):
        row = _make_status_row(runId=5, overallStatus="RUNNING", progressPercent=35)
        cur = _FakeCursor(fetchone_result=row)
        conn = _FakeConn(cursor=cur)
        with patch.object(_repo, "getConn", return_value=conn):
            result = getDmaWorkflowStatusOrDefault(runId=5, workflowType="BENCHMARK")
        self.assertEqual(result["overallStatus"], "RUNNING")
        self.assertEqual(result["progressPercent"], 35)


# ══════════════════════════════════════════════════════════════════════════════
# §10.3  API Endpoint
# ══════════════════════════════════════════════════════════════════════════════

class TestF1BApiEndpoint(unittest.TestCase):
    """#31-#35 materiality.py route contract."""

    def _load_api(self):
        sys.modules.pop("src.apis.materiality", None)
        return importlib.import_module("src.apis.materiality")

    def test_31_materiality_module_imports_workflow_status_dto(self):
        api = self._load_api()
        self.assertTrue(hasattr(api, "DmaWorkflowStatusResponseDto"))

    def test_32_materiality_module_imports_get_workflow_status_or_default(self):
        api = self._load_api()
        self.assertTrue(hasattr(api, "getDmaWorkflowStatusOrDefault"))

    def test_33_router_has_workflow_status_route(self):
        api = self._load_api()
        routes = [r.path for r in api.router.routes]
        self.assertTrue(
            any("workflow-status" in r for r in routes),
            f"No workflow-status route found: {routes}",
        )

    def test_34_workflow_status_route_returns_dto_on_success(self):
        import asyncio as _asyncio
        api = self._load_api()
        row = _make_status_row(runId=7, overallStatus="RUNNING", progressPercent=35)
        with patch.object(api, "getDmaWorkflowStatusOrDefault", return_value=row):
            result = _asyncio.run(api.get_dma_workflow_status(
                runId=7, workflowType="BENCHMARK", userModel=MagicMock()
            ))
        self.assertEqual(result["overallStatus"], "RUNNING")
        self.assertEqual(result["progressPercent"], 35)

    def test_35_workflow_status_route_raises_400_on_value_error(self):
        import asyncio as _asyncio
        from fastapi import HTTPException
        api = self._load_api()
        with patch.object(api, "getDmaWorkflowStatusOrDefault", side_effect=ValueError("bad type")):
            with self.assertRaises(HTTPException) as ctx:
                _asyncio.run(api.get_dma_workflow_status(
                    runId=1, workflowType="GARBAGE", userModel=MagicMock()
                ))
        self.assertEqual(ctx.exception.status_code, 400)


# ══════════════════════════════════════════════════════════════════════════════
# §10.4  Benchmark Service Milestone Writes
# ══════════════════════════════════════════════════════════════════════════════

import tempfile  # noqa: E402

from src.models.benchmk import FileFindModel  # noqa: E402
from src.models.model import UserModel  # noqa: E402


def _load_service():
    fakeOcraiv8 = types.ModuleType("src.utils.ocraiv8")

    async def fakeGemini(results, filePaths):
        return {"data": [{"fileName": "abc.pdf", "result": [{"subIssueCode": "E-01"}], "type": "SUCCESS"}]}

    fakeOcraiv8.gemini = fakeGemini
    sys.modules["src.utils.ocraiv8"] = fakeOcraiv8
    sys.modules.pop("src.services.benchmarks.service", None)
    return importlib.import_module("src.services.benchmarks.service")


def _make_find_model(**overrides):
    defaults = dict(file=["abc.pdf"], page="SR", esgMaterialityRunId=10,
                    sourceStep="benchmark", sourceType=None)
    defaults.update(overrides)
    return FileFindModel(**defaults)


def _make_user_model():
    return UserModel(id=1, email="t@t.com", name="test",
                     uuid="test-uuid", role="admin", role_name="관리자")


def _run_find_sr(service, fileFindModel, userModel, extra_patches=None):
    extra_patches = extra_patches or {}
    upsert_mock = extra_patches.get("upsertDmaWorkflowStatus", MagicMock())
    find_one_mock = extra_patches.get("findOne", MagicMock(return_value={
        "id": 42, "origin": "test.pdf", "file_name": "abc.pdf",
        "type": "Leader", "company_name": "Co", "create_user_id": 1,
    }))
    save_signals_mock = extra_patches.get("saveSignals", MagicMock())
    normalize_mock = extra_patches.get("step0NormalizeBenchmarkFacts",
                                        MagicMock(return_value=[MagicMock()]))
    build_fact_mock = extra_patches.get("step0BuildFactTrace", MagicMock(return_value={"dummy": True}))
    screening_mock = extra_patches.get("step2BuildBenchmarkScreeningPayloads",
                                        MagicMock(return_value=[]))
    tx_mock = extra_patches.get("step4ReplaceBenchmarkShadowTracesTx", MagicMock())
    gemini_mock = extra_patches.get("gemini", None)

    if gemini_mock is None:
        async def _g(*a, **kw):
            return {"data": [{"fileName": "abc.pdf", "result": [{"subIssueCode": "E-01"}], "type": "SUCCESS"}]}
        gemini_mock = _g

    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "abc.pdf").write_text("pdf", encoding="utf-8")
        service.settings.file_dir = tmp

        with patch.object(service, "findOne", find_one_mock), \
             patch.object(service, "gemini", gemini_mock), \
             patch.object(service, "saveSignals", save_signals_mock), \
             patch.object(service, "step0NormalizeBenchmarkFacts", normalize_mock), \
             patch.object(service, "step0BuildFactTrace", build_fact_mock), \
             patch.object(service, "step2BuildBenchmarkScreeningPayloads", screening_mock), \
             patch.object(service, "step4ReplaceBenchmarkShadowTracesTx", tx_mock), \
             patch.object(service, "upsertDmaWorkflowStatus", upsert_mock), \
             patch.object(service, "dmaruleregistry") as mockReg, \
             patch.object(service, "subissueMaster",
                         {"E-01": {"materiality_issue_pool_yn": "Y"}}):
            mockReg.getPolicy = MagicMock(return_value={"threshold": 0.5})
            return asyncio.run(service.findSr(fileFindModel, userModel)), upsert_mock


class TestF1BServiceMilestones(unittest.TestCase):
    """#36-#44 Milestone writes triggered during findSr."""

    def test_36_prepare_milestone_written_with_started_yn_true(self):
        service = _load_service()
        _, upsert = _run_find_sr(service, _make_find_model(), _make_user_model())
        prepare_calls = [
            c for c in upsert.call_args_list
            if c.kwargs.get("currentStage") == "PREPARE"
               and c.kwargs.get("startedYn") is True
        ]
        self.assertGreaterEqual(len(prepare_calls), 1)

    def test_37_prepare_milestone_progress_is_20(self):
        service = _load_service()
        _, upsert = _run_find_sr(service, _make_find_model(), _make_user_model())
        prepare_calls = [
            c for c in upsert.call_args_list
            if c.kwargs.get("currentStage") == "PREPARE"
        ]
        self.assertTrue(any(c.kwargs.get("progressPercent") == 20 for c in prepare_calls))

    def test_38_document_analysis_milestone_written(self):
        service = _load_service()
        _, upsert = _run_find_sr(service, _make_find_model(), _make_user_model())
        stages = [c.kwargs.get("currentStage") for c in upsert.call_args_list]
        self.assertIn("DOCUMENT_ANALYSIS", stages)

    def test_39_document_analysis_progress_is_35(self):
        service = _load_service()
        _, upsert = _run_find_sr(service, _make_find_model(), _make_user_model())
        da_calls = [c for c in upsert.call_args_list if c.kwargs.get("currentStage") == "DOCUMENT_ANALYSIS"]
        self.assertTrue(any(c.kwargs.get("progressPercent") == 35 for c in da_calls))

    def test_40_benchmark_scoring_milestone_written(self):
        service = _load_service()
        _, upsert = _run_find_sr(service, _make_find_model(), _make_user_model())
        stages = [c.kwargs.get("currentStage") for c in upsert.call_args_list]
        self.assertIn("BENCHMARK_SCORING", stages)

    def test_41_benchmark_shadow_milestone_written(self):
        service = _load_service()
        _, upsert = _run_find_sr(service, _make_find_model(), _make_user_model())
        stages = [c.kwargs.get("currentStage") for c in upsert.call_args_list]
        self.assertIn("BENCHMARK_SHADOW", stages)

    def test_42_benchmark_shadow_progress_is_95(self):
        service = _load_service()
        _, upsert = _run_find_sr(service, _make_find_model(), _make_user_model())
        shadow_calls = [c for c in upsert.call_args_list if c.kwargs.get("currentStage") == "BENCHMARK_SHADOW"]
        self.assertTrue(any(c.kwargs.get("progressPercent") == 95 for c in shadow_calls))

    def test_43_completed_milestone_written_with_completed_yn_and_100_percent(self):
        service = _load_service()
        _, upsert = _run_find_sr(service, _make_find_model(), _make_user_model())
        completed_calls = [
            c for c in upsert.call_args_list
            if c.kwargs.get("currentStage") == "COMPLETED"
               and c.kwargs.get("completedYn") is True
               and c.kwargs.get("progressPercent") == 100
               and c.kwargs.get("overallStatus") == "COMPLETED"
        ]
        self.assertGreaterEqual(len(completed_calls), 1)

    def test_44_per_file_actual_count_milestone_written(self):
        service = _load_service()
        _, upsert = _run_find_sr(service, _make_find_model(), _make_user_model())
        actual_count_calls = [
            c for c in upsert.call_args_list
            if c.kwargs.get("progressMode") == "ACTUAL_COUNT"
        ]
        self.assertGreaterEqual(len(actual_count_calls), 1)


# ══════════════════════════════════════════════════════════════════════════════
# §10.5  Benchmark Service Failure Recording
# ══════════════════════════════════════════════════════════════════════════════

class TestF1BServiceFailureRecording(unittest.TestCase):
    """#45-#56 FAILED status written on various failure paths."""

    def _run_expecting_failure(self, service, patches, fileFindModel=None, userModel=None):
        if fileFindModel is None:
            fileFindModel = _make_find_model()
        if userModel is None:
            userModel = _make_user_model()
        upsert_mock = patches.get("upsertDmaWorkflowStatus", MagicMock())
        patches["upsertDmaWorkflowStatus"] = upsert_mock

        with self.assertRaises(Exception):
            _run_find_sr(service, fileFindModel, userModel, patches)

        return upsert_mock

    def test_45_failed_status_written_when_file_not_found(self):
        service = _load_service()
        upsert = self._run_expecting_failure(service, {
            "findOne": MagicMock(return_value=None),
        })
        failed_calls = [c for c in upsert.call_args_list if c.kwargs.get("overallStatus") == "FAILED"]
        self.assertGreaterEqual(len(failed_calls), 1)

    def test_46_failed_status_error_message_not_empty(self):
        service = _load_service()
        upsert = self._run_expecting_failure(service, {
            "findOne": MagicMock(return_value=None),
        })
        failed_calls = [c for c in upsert.call_args_list if c.kwargs.get("overallStatus") == "FAILED"]
        self.assertTrue(any(c.kwargs.get("errorMessage") for c in failed_calls))

    def test_47_failed_status_written_when_gemini_returns_none(self):
        service = _load_service()

        async def bad_gemini(*a, **kw):
            return None

        upsert = self._run_expecting_failure(service, {"gemini": bad_gemini})
        failed_calls = [c for c in upsert.call_args_list if c.kwargs.get("overallStatus") == "FAILED"]
        self.assertGreaterEqual(len(failed_calls), 1)

    def test_48_failed_error_message_truncated_to_1000_chars(self):
        service = _load_service()
        long_err = "x" * 2000

        async def bad_gemini(*a, **kw):
            raise RuntimeError(long_err)

        upsert = self._run_expecting_failure(service, {"gemini": bad_gemini})
        failed_calls = [c for c in upsert.call_args_list if c.kwargs.get("overallStatus") == "FAILED"]
        for c in failed_calls:
            msg = c.kwargs.get("errorMessage") or ""
            self.assertLessEqual(len(msg), 1000)

    def test_49_failed_status_written_when_shadow_fact_build_fails(self):
        service = _load_service()
        upsert = self._run_expecting_failure(service, {
            "step0NormalizeBenchmarkFacts": MagicMock(side_effect=RuntimeError("fact build error")),
        })
        failed_calls = [c for c in upsert.call_args_list if c.kwargs.get("overallStatus") == "FAILED"]
        self.assertGreaterEqual(len(failed_calls), 1)

    def test_50_failed_status_written_when_replace_tx_fails(self):
        service = _load_service()
        upsert = self._run_expecting_failure(service, {
            "step4ReplaceBenchmarkShadowTracesTx": MagicMock(side_effect=RuntimeError("tx exploded")),
        })
        failed_calls = [c for c in upsert.call_args_list if c.kwargs.get("overallStatus") == "FAILED"]
        self.assertGreaterEqual(len(failed_calls), 1)

    def test_51_replace_tx_still_raises_after_failed_record(self):
        service = _load_service()
        with self.assertRaises(RuntimeError) as ctx:
            _run_find_sr(service, _make_find_model(), _make_user_model(), {
                "step4ReplaceBenchmarkShadowTracesTx": MagicMock(side_effect=RuntimeError("tx boom")),
            })
        self.assertIn("tx boom", str(ctx.exception))

    def test_52_prepare_write_failure_propagates_before_analysis_starts(self):
        service = _load_service()

        def _upsert_fail_on_prepare(**kwargs):
            if kwargs.get("currentStage") == "PREPARE":
                raise RuntimeError("prepare write failed")

        upsert_mock = MagicMock(side_effect=_upsert_fail_on_prepare)
        with self.assertRaises(RuntimeError):
            _run_find_sr(service, _make_find_model(), _make_user_model(), {
                "upsertDmaWorkflowStatus": upsert_mock,
            })

    def test_53_failed_record_best_effort_does_not_swallow_original_error(self):
        service = _load_service()
        with self.assertRaises(RuntimeError) as ctx:
            _run_find_sr(service, _make_find_model(), _make_user_model(), {
                "findOne": MagicMock(return_value=None),
            })
        self.assertIn("존재하지 않는 파일", str(ctx.exception))

    def test_54_completed_write_failure_prevents_success_response(self):
        service = _load_service()
        call_count = {"n": 0}

        def _upsert_fail_on_completed(**kwargs):
            call_count["n"] += 1
            if kwargs.get("currentStage") == "COMPLETED":
                raise RuntimeError("completed write failed")

        with self.assertRaises(RuntimeError):
            _run_find_sr(service, _make_find_model(), _make_user_model(), {
                "upsertDmaWorkflowStatus": MagicMock(side_effect=_upsert_fail_on_completed),
            })

    def test_55_failed_status_error_stage_matches_current_stage(self):
        service = _load_service()
        upsert = self._run_expecting_failure(service, {
            "findOne": MagicMock(return_value=None),
        })
        failed_calls = [c for c in upsert.call_args_list if c.kwargs.get("overallStatus") == "FAILED"]
        for c in failed_calls:
            self.assertEqual(c.kwargs.get("errorStage"), c.kwargs.get("currentStage"))

    def test_56_failed_record_write_failure_is_swallowed_and_original_reraises(self):
        service = _load_service()
        call_count = {"n": 0}

        def _upsert_behavior(**kwargs):
            call_count["n"] += 1
            if kwargs.get("overallStatus") == "FAILED":
                raise RuntimeError("failed write also failed")

        with self.assertRaises(RuntimeError) as ctx:
            _run_find_sr(service, _make_find_model(), _make_user_model(), {
                "findOne": MagicMock(return_value=None),
                "upsertDmaWorkflowStatus": MagicMock(side_effect=_upsert_behavior),
            })
        self.assertIn("존재하지 않는 파일", str(ctx.exception))


# ══════════════════════════════════════════════════════════════════════════════
# §10.6  Frontend Static Contract
# ══════════════════════════════════════════════════════════════════════════════

def _jsx() -> str:
    return _BENCH_JSX.read_text(encoding="utf-8")


class TestF1BFrontendStatic(unittest.TestCase):
    """#57-#77 BenchMarking.jsx source code assertions."""

    def test_57_use_effect_imported(self):
        self.assertIn("useEffect", _jsx())

    def test_58_benchmark_poll_timer_ref_declared(self):
        self.assertIn("benchmarkPollTimerRef", _jsx())

    def test_59_benchmark_workflow_error_ref_declared(self):
        self.assertIn("benchmarkWorkflowErrorRef", _jsx())

    def test_60_stop_benchmark_polling_function_defined(self):
        self.assertIn("stopBenchmarkPolling", _jsx())

    def test_61_fetch_benchmark_workflow_status_function_defined(self):
        self.assertIn("fetchBenchmarkWorkflowStatus", _jsx())

    def test_62_start_benchmark_polling_function_defined(self):
        self.assertIn("startBenchmarkPolling", _jsx())

    def test_63_polling_url_contains_workflow_status_benchmark(self):
        self.assertIn("/materiality/workflow-status/", _jsx())
        self.assertIn("BENCHMARK", _jsx())

    def test_64_set_interval_used_for_polling(self):
        self.assertIn("setInterval", _jsx())

    def test_65_clear_interval_used_for_cleanup(self):
        self.assertIn("clearInterval", _jsx())

    def test_66_use_effect_cleanup_calls_stop_polling(self):
        src = _jsx()
        self.assertIn("useEffect", src)
        self.assertIn("stopBenchmarkPolling", src)

    def test_67_monotonic_progress_via_math_max(self):
        self.assertIn("Math.max", _jsx())

    def test_68_overallStatus_completed_stops_polling(self):
        src = _jsx()
        self.assertIn("COMPLETED", src)
        self.assertIn("stopBenchmarkPolling", src)

    def test_69_overallStatus_failed_stops_polling(self):
        src = _jsx()
        self.assertIn("FAILED", src)
        self.assertIn("stopBenchmarkPolling", src)

    def test_70_overallStatus_failed_sets_workflow_error_ref(self):
        self.assertIn("benchmarkWorkflowErrorRef.current", _jsx())

    def test_71_analyze_promise_pattern_used_not_await_inline(self):
        src = _jsx()
        self.assertIn("analyzePromise", src)
        self.assertNotIn("const analyzeResponse = await PUT(", src)

    def test_72_start_polling_called_before_await_analyze_promise(self):
        src = _jsx()
        polling_idx = src.find("startBenchmarkPolling(runId)")
        await_idx = src.find("await analyzePromise")
        self.assertGreater(polling_idx, 0)
        self.assertGreater(await_idx, 0)
        self.assertLess(polling_idx, await_idx)

    def test_73_workflow_error_ref_checked_after_await(self):
        src = _jsx()
        await_idx = src.find("await analyzePromise")
        # Look for the guard check pattern (if ...) which appears after the await
        error_check_idx = src.find("if (benchmarkWorkflowErrorRef.current)")
        self.assertGreater(await_idx, 0)
        self.assertGreater(error_check_idx, 0)
        self.assertGreater(error_check_idx, await_idx)

    def test_74_set_progress_50_removed(self):
        self.assertNotIn("setProgress(50)", _jsx())

    def test_75_stop_polling_called_in_catch_block(self):
        src = _jsx()
        catch_idx = src.find("} catch (err) {")
        stop_after_catch = src.find("stopBenchmarkPolling()", catch_idx)
        self.assertGreater(catch_idx, 0)
        self.assertGreater(stop_after_catch, catch_idx)

    def test_76_progress_percent_from_dto_used_in_set_progress(self):
        self.assertIn("dto.progressPercent", _jsx())

    def test_77_final_workflow_check_after_await_promise(self):
        src = _jsx()
        self.assertIn("finalWorkflow", src)
        self.assertIn("finalWorkflow.overallStatus", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
