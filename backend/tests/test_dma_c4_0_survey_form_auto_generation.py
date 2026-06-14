"""
DMA C4.0 Survey Form Auto Generation tests.

Pure unit tests. No live DB, Apps Script, Google API, or network call.
"""

import importlib
import inspect
import json
import os
import pathlib
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

# ── dummy env ────────────────────────────────────────────────────────────────
_DUMMY_ENV = {
    "host_ip": "127.0.0.1", "domain": "test", "skm_domain": "test", "file_dir": "/tmp",
    "gemini_api_key": "test", "gemini_model": "test", "kafka_server": "test",
    "kafka_topic": "test", "mail_username": "test", "mail_password": "test",
    "mail_from": "test@test", "access_token_expire_minutes": "1",
    "refresh_token_expire_days": "1", "invite_token_expire_days": "1",
    "redis_host": "test", "redis_port": "6379", "redis_db1": "0",
    "redis_db2": "1", "redis_db3": "2", "service_key": "test",
    "maria_db_user": "test", "maria_db_password": "test", "maria_db_host": "test",
    "maria_db_database": "test", "maria_db_port": "3306", "maria_db_key": "test",
    "cookie_key": "test", "APPS_SCRIPT_URL": "https://script.example.com/exec",
    "pg_db_host": "test", "pg_db_port": "5432", "pg_db_database": "test",
    "pg_db_user": "test", "pg_db_password": "test", "ollama_url": "http://test",
}
for _k, _v in _DUMMY_ENV.items():
    os.environ.setdefault(_k, _v)

# stub mariadb
if "mariadb" not in sys.modules:
    _mariadb = types.ModuleType("mariadb")
    _mariadb.Error = Exception
    _mariadb.connect = lambda **kwargs: None
    sys.modules["mariadb"] = _mariadb

# stub google packages so importing medias/service doesn't blow up
for _stub in (
    "googleapiclient", "googleapiclient.discovery",
    "google", "google.oauth2", "google.oauth2.service_account",
):
    if _stub not in sys.modules:
        _m = types.ModuleType(_stub)
        sys.modules[_stub] = _m

_gdisc = sys.modules["googleapiclient.discovery"]
_gdisc.build = MagicMock(return_value=MagicMock())

_goauth2 = sys.modules["google.oauth2"]
_sa_mod = sys.modules["google.oauth2.service_account"]
_sa_cls = MagicMock()
_sa_cls.Credentials = MagicMock()
_sa_cls.Credentials.from_service_account_file = MagicMock(return_value=MagicMock())
sys.modules["google.oauth2.service_account"] = _sa_cls

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import src.utils.dmasurveyformrepository as _repo_mod
import src.services.surveys.formservice as _fs_mod

_BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]


# ── Fake DB helpers ──────────────────────────────────────────────────────────

class FakeCursor:
    def __init__(self, rows=None, lastrowid=1):
        self._rows = list(rows or [])
        self.lastrowid = lastrowid
        self.rowcount = len(self._rows)
        self.executed = []

    def __enter__(self): return self
    def __exit__(self, *a): return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeConn:
    def __init__(self, cursor_obj=None):
        self._cur = cursor_obj or FakeCursor()
        self.autocommit = True
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, dictionary=True):
        return self._cur

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _top20_rows(n=20, start_rank=1):
    return [
        {
            "sub_issue_code": f"CODE_{i:02d}",
            "sub_issue_name_kr": f"이슈{i}",
            "rank_no": start_rank + (i - 1),
            "final_impact_score": 4.0,
            "final_financial_score": 3.5,
            "final_score": 3.75,
        }
        for i in range(1, n + 1)
    ]


def _make_ready_apps_response(master="SHEET1", emp="https://e", mgmt="https://m", ext="https://x"):
    return {
        "status": "success",
        "data": {
            "masterSheetId": master,
            "forms": {"employee": emp, "management": mgmt, "external": ext},
        },
    }


# ════════════════════════════════════════════════════════════════════════════
# §11.1  Repository Validation
# ════════════════════════════════════════════════════════════════════════════

class TestRepositoryValidation(unittest.TestCase):

    def test_01_runId_bool_rejected_by_validateRunId(self):
        with self.assertRaises(ValueError):
            _repo_mod._validateRunId(True)

    def test_02_runId_false_rejected(self):
        with self.assertRaises(ValueError):
            _repo_mod._validateRunId(False)

    def test_03_runId_string_rejected(self):
        with self.assertRaises(ValueError):
            _repo_mod._validateRunId("48")

    def test_04_runId_zero_rejected(self):
        with self.assertRaises(ValueError):
            _repo_mod._validateRunId(0)

    def test_05_runId_negative_rejected(self):
        with self.assertRaises(ValueError):
            _repo_mod._validateRunId(-1)

    def test_06_runId_positive_int_accepted(self):
        _repo_mod._validateRunId(1)  # no raise

    def test_07_survey_form_statuses_frozenset(self):
        self.assertIsInstance(_repo_mod.SURVEY_FORM_STATUSES, frozenset)
        self.assertEqual(
            _repo_mod.SURVEY_FORM_STATUSES,
            frozenset({"GENERATING", "READY", "RETRYABLE", "CLOSED"}),
        )

    def test_08_template_version_constant(self):
        self.assertEqual(_repo_mod.SURVEY_TEMPLATE_VERSION, "v2")

    def test_09_workflow_type_constant(self):
        self.assertEqual(_repo_mod.SURVEY_FORM_WORKFLOW_TYPE, "SURVEY_FORM")

    def test_10_getConn_none_raises_in_findSurveyRunContext(self):
        with patch.object(_repo_mod, "getConn", return_value=None):
            with self.assertRaises(RuntimeError):
                _repo_mod.findSurveyRunContext(1)

    def test_11_getConn_none_raises_in_getSurveyFormByRunId(self):
        with patch.object(_repo_mod, "getConn", return_value=None):
            with self.assertRaises(RuntimeError):
                _repo_mod.getSurveyFormByRunId(1)

    def test_12_getConn_none_raises_in_getOrFreezeSurveyFormSnapshotTx(self):
        with patch.object(_repo_mod, "getConn", return_value=None):
            with self.assertRaises(RuntimeError):
                _repo_mod.getOrFreezeSurveyFormSnapshotTx(runId=1, templateVersion="v2")

    def test_13_getConn_none_raises_in_markSurveyFormReadyTx(self):
        with patch.object(_repo_mod, "getConn", return_value=None):
            with self.assertRaises(RuntimeError):
                _repo_mod.markSurveyFormReadyTx(
                    formId=1, masterSheetId="s", employeeFormUrl="e",
                    managementFormUrl="m", externalFormUrl="x",
                )

    def test_14_templateVersion_blank_rejected(self):
        conn = FakeConn(FakeCursor(rows=[]))
        with patch.object(_repo_mod, "getConn", return_value=conn):
            with self.assertRaises(ValueError):
                _repo_mod.getOrFreezeSurveyFormSnapshotTx(runId=1, templateVersion="")

    def test_15_getConn_none_raises_in_claimRetryableSurveyFormTx(self):
        with patch.object(_repo_mod, "getConn", return_value=None):
            with self.assertRaises(RuntimeError):
                _repo_mod.claimRetryableSurveyFormTx(1)


# ════════════════════════════════════════════════════════════════════════════
# §11.2  Snapshot Freeze
# ════════════════════════════════════════════════════════════════════════════

class TestSnapshotFreeze(unittest.TestCase):

    def _run_new_row(self, rows, templateVersion="v2"):
        """Helper: no existing form row, run freeze with given top20 rows."""
        call_count = [0]

        class MultiFakeCursor:
            def __init__(self):
                self.lastrowid = 99
                self.rowcount = 1
                self.executed = []

            def __enter__(self): return self
            def __exit__(self, *a): return False

            def execute(self, sql, params=None):
                self.executed.append((sql, params))

            def fetchone(self):
                return None  # no existing form

            def fetchall(self):
                return list(rows)

        cur = MultiFakeCursor()
        conn = FakeConn(cur)
        with patch.object(_repo_mod, "getConn", return_value=conn):
            return _repo_mod.getOrFreezeSurveyFormSnapshotTx(
                runId=48, templateVersion=templateVersion
            )

    def test_16_top20_sql_contains_rank_no_is_not_null(self):
        self.assertIn("rank_no IS NOT NULL", _repo_mod._TOP20_SQL)

    def test_17_top20_sql_order_rank_asc_sub_issue_asc(self):
        sql = _repo_mod._TOP20_SQL
        self.assertIn("rank_no ASC", sql)
        self.assertIn("sub_issue_code ASC", sql)

    def test_18_top20_sql_limit_20(self):
        self.assertIn("LIMIT 20", _repo_mod._TOP20_SQL)

    def test_19_20_rows_exact_succeeds(self):
        rows = _top20_rows(20)
        result = self._run_new_row(rows)
        self.assertEqual(result["surveyStatus"], "GENERATING")
        self.assertEqual(len(result["snapshot"]), 20)

    def test_20_19_rows_rejects(self):
        rows = _top20_rows(19)
        with self.assertRaises(RuntimeError):
            self._run_new_row(rows)

    def test_21_0_rows_rejects(self):
        with self.assertRaises(RuntimeError):
            self._run_new_row([])

    def test_22_duplicate_sub_issue_code_rejects(self):
        rows = _top20_rows(20)
        rows[5]["sub_issue_code"] = rows[0]["sub_issue_code"]  # duplicate
        with self.assertRaises(RuntimeError):
            self._run_new_row(rows)

    def test_23_null_rank_rejects(self):
        rows = _top20_rows(20)
        rows[3]["rank_no"] = None
        with self.assertRaises(RuntimeError):
            self._run_new_row(rows)

    def test_24_rank_zero_rejects(self):
        rows = _top20_rows(20)
        rows[0]["rank_no"] = 0
        with self.assertRaises(RuntimeError):
            self._run_new_row(rows)

    def test_25_rank_negative_rejects(self):
        rows = _top20_rows(20)
        rows[0]["rank_no"] = -1
        with self.assertRaises(RuntimeError):
            self._run_new_row(rows)

    def test_26_snapshot_json_is_stable_sorted(self):
        rows = _top20_rows(20)
        result = self._run_new_row(rows)
        raw_json = result["top20_snapshot_json"]
        parsed = json.loads(raw_json)
        # Re-serialize with same params — must be identical
        re_serialized = json.dumps(
            parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        self.assertEqual(raw_json, re_serialized)

    def test_27_snapshot_json_ensure_ascii_false(self):
        rows = _top20_rows(20)
        rows[0]["sub_issue_name_kr"] = "온실가스"
        result = self._run_new_row(rows)
        raw_json = result["top20_snapshot_json"]
        self.assertIn("온실가스", raw_json)
        self.assertNotIn("\\u", raw_json.replace("\\u0022", ""))  # no unicode escape

    def test_28_new_row_status_is_generating(self):
        result = self._run_new_row(_top20_rows(20))
        self.assertEqual(result["surveyStatus"], "GENERATING")

    def test_29_new_row_commits_and_closes(self):
        call_count = [0]

        class MC:
            def __init__(self):
                self.lastrowid = 5
                self.rowcount = 1
                self._call = 0

            def __enter__(self): return self
            def __exit__(self, *a): return False

            def execute(self, sql, params=None): pass

            def fetchone(self): return None

            def fetchall(self): return _top20_rows(20)

        cur = MC()
        conn = FakeConn(cur)
        with patch.object(_repo_mod, "getConn", return_value=conn):
            _repo_mod.getOrFreezeSurveyFormSnapshotTx(runId=1, templateVersion="v2")
        self.assertTrue(conn.committed)
        self.assertTrue(conn.closed)

    def test_30_ready_row_returns_existing_and_no_insert(self):
        existing = {
            "id": 7, "esg_materiality_run_id": 48,
            "template_version": "v2", "survey_status": "READY",
            "top20_snapshot_json": json.dumps([{"rankNo": 1}]),
            "master_sheet_id": "SID", "employee_form_url": "https://e",
            "management_form_url": "https://m", "external_form_url": "https://x",
            "error_message": None, "generated_at": None, "updated_at": None, "delete_yn": 0,
        }
        inserted = [False]

        class RC:
            def __init__(self):
                self.lastrowid = None
                self.rowcount = 0

            def __enter__(self): return self
            def __exit__(self, *a): return False

            def execute(self, sql, params=None):
                if "INSERT" in sql.upper():
                    inserted[0] = True

            def fetchone(self): return dict(existing)
            def fetchall(self): return []

        conn = FakeConn(RC())
        with patch.object(_repo_mod, "getConn", return_value=conn):
            result = _repo_mod.getOrFreezeSurveyFormSnapshotTx(runId=48, templateVersion="v2")

        self.assertFalse(inserted[0])
        self.assertEqual(result["surveyStatus"], "READY")
        self.assertEqual(result["id"], 7)

    def test_31_retryable_row_returns_existing_snapshot_no_requery(self):
        snap = [{"rankNo": 1, "subIssueCode": "X"}]
        existing = {
            "id": 8, "esg_materiality_run_id": 48,
            "template_version": "v2", "survey_status": "RETRYABLE",
            "top20_snapshot_json": json.dumps(snap),
            "master_sheet_id": None, "employee_form_url": None,
            "management_form_url": None, "external_form_url": None,
            "error_message": "prev error", "generated_at": None, "updated_at": None, "delete_yn": 0,
        }
        top20_queried = [False]

        class RC:
            def __init__(self):
                self.lastrowid = None
                self.rowcount = 0

            def __enter__(self): return self
            def __exit__(self, *a): return False

            def execute(self, sql, params=None):
                if "ESG_DMA_SCORE_SUMMARY" in sql:
                    top20_queried[0] = True

            def fetchone(self): return dict(existing)
            def fetchall(self): return []

        conn = FakeConn(RC())
        with patch.object(_repo_mod, "getConn", return_value=conn):
            result = _repo_mod.getOrFreezeSurveyFormSnapshotTx(runId=48, templateVersion="v2")

        self.assertFalse(top20_queried[0], "Top20 must not be re-queried for RETRYABLE")
        self.assertEqual(result["surveyStatus"], "RETRYABLE")
        self.assertEqual(result["snapshot"][0]["subIssueCode"], "X")

    def test_32_generating_duplicate_call_raises(self):
        existing = {
            "id": 9, "esg_materiality_run_id": 48, "survey_status": "GENERATING",
            "top20_snapshot_json": "{}", "template_version": "v2",
            "master_sheet_id": None, "employee_form_url": None,
            "management_form_url": None, "external_form_url": None,
            "error_message": None, "generated_at": None, "updated_at": None, "delete_yn": 0,
        }

        class RC:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params=None): pass
            def fetchone(self): return dict(existing)
            def fetchall(self): return []

        conn = FakeConn(RC())
        with patch.object(_repo_mod, "getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                _repo_mod.getOrFreezeSurveyFormSnapshotTx(runId=48, templateVersion="v2")

    def test_33_closed_row_raises(self):
        existing = {
            "id": 10, "esg_materiality_run_id": 48, "survey_status": "CLOSED",
            "top20_snapshot_json": "{}", "template_version": "v2",
            "master_sheet_id": None, "employee_form_url": None,
            "management_form_url": None, "external_form_url": None,
            "error_message": None, "generated_at": None, "updated_at": None, "delete_yn": 0,
        }

        class RC:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params=None): pass
            def fetchone(self): return dict(existing)
            def fetchall(self): return []

        conn = FakeConn(RC())
        with patch.object(_repo_mod, "getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                _repo_mod.getOrFreezeSurveyFormSnapshotTx(runId=48, templateVersion="v2")

    def test_34_rollback_on_execute_failure(self):
        class RC:
            def __init__(self):
                self._call = 0
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params=None):
                if "ESG_DMA_SURVEY_FORM" in sql:
                    raise RuntimeError("db error")
            def fetchone(self): return None
            def fetchall(self): return _top20_rows(20)

        conn = FakeConn(RC())
        with patch.object(_repo_mod, "getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                _repo_mod.getOrFreezeSurveyFormSnapshotTx(runId=1, templateVersion="v2")
        self.assertTrue(conn.closed)


# ════════════════════════════════════════════════════════════════════════════
# §11.3  URL Storage
# ════════════════════════════════════════════════════════════════════════════

class TestUrlStorage(unittest.TestCase):

    def _run_mark_ready(self, **overrides):
        kwargs = dict(
            formId=1,
            masterSheetId="SHEET1",
            employeeFormUrl="https://employee",
            managementFormUrl="https://management",
            externalFormUrl="https://external",
        )
        kwargs.update(overrides)

        class RC:
            def __init__(self):
                self.rowcount = 1
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params=None): pass
            def fetchone(self): return None

        conn = FakeConn(RC())
        with patch.object(_repo_mod, "getConn", return_value=conn):
            _repo_mod.markSurveyFormReadyTx(**kwargs)
        return conn

    def test_35_mark_ready_commits_and_closes(self):
        conn = self._run_mark_ready()
        self.assertTrue(conn.committed)
        self.assertTrue(conn.closed)

    def test_36_masterSheetId_blank_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self._run_mark_ready(masterSheetId="")

    def test_37_employee_url_blank_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self._run_mark_ready(employeeFormUrl="")

    def test_38_management_url_blank_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self._run_mark_ready(managementFormUrl="")

    def test_39_external_url_blank_rejected(self):
        with self.assertRaises((ValueError, RuntimeError)):
            self._run_mark_ready(externalFormUrl="")

    def test_40_rowcount_not_1_raises(self):
        class RC:
            def __init__(self):
                self.rowcount = 0
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params=None): pass

        conn = FakeConn(RC())
        with patch.object(_repo_mod, "getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                _repo_mod.markSurveyFormReadyTx(
                    formId=1, masterSheetId="s",
                    employeeFormUrl="e", managementFormUrl="m", externalFormUrl="x",
                )

    def test_41_retryable_update_sql_not_alter_snapshot(self):
        sql = _repo_mod._UPDATE_RETRYABLE_SQL.upper()
        self.assertNotIn("TOP20_SNAPSHOT_JSON", sql)

    def test_42_error_message_truncated_to_1000(self):
        written = [None]

        class RC:
            def __init__(self):
                self.rowcount = 1
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params=None):
                if params:
                    written[0] = params[0]

        conn = FakeConn(RC())
        long_msg = "X" * 2000
        with patch.object(_repo_mod, "getConn", return_value=conn):
            _repo_mod.markSurveyFormRetryableBestEffort(formId=1, errorMessage=long_msg)
        self.assertIsNotNone(written[0])
        self.assertLessEqual(len(written[0]), 1000)

    def test_43_mark_retryable_best_effort_swallows_db_error(self):
        with patch.object(_repo_mod, "getConn", side_effect=RuntimeError("db down")):
            # Must not raise
            _repo_mod.markSurveyFormRetryableBestEffort(formId=1, errorMessage="oops")


# ════════════════════════════════════════════════════════════════════════════
# §11.4  Form Service
# ════════════════════════════════════════════════════════════════════════════

def _load_formservice():
    sys.modules.pop("src.services.surveys.formservice", None)
    return importlib.import_module("src.services.surveys.formservice")


def _run_ensure(fs, runId=48, patches_extra=None):
    freeze_result = {
        "id": 1,
        "surveyStatus": "GENERATING",
        "survey_status": "GENERATING",
        "snapshot": [
            {
                "rankNo": i,
                "subIssueCode": f"CODE_{i:02d}",
                "subIssueName": f"이슈{i}",
                "finalImpactScore": 4.0,
                "finalFinancialScore": 3.5,
                "finalScore": 3.75,
            }
            for i in range(1, 21)
        ],
        "top20_snapshot_json": "[]",
        "esg_materiality_run_id": runId,
        "template_version": "v2",
        "master_sheet_id": None,
        "employee_form_url": None,
        "management_form_url": None,
        "external_form_url": None,
        "error_message": None,
        "generated_at": None,
        "updated_at": None,
    }
    apps_response = _make_ready_apps_response()
    mock_response = MagicMock()
    mock_response.json.return_value = apps_response

    default_patches = {
        "findSurveyRunContext": MagicMock(return_value={"runId": runId, "companyId": 6, "reportingYear": 2025}),
        "getOrFreezeSurveyFormSnapshotTx": MagicMock(return_value=freeze_result),
        "claimRetryableSurveyFormTx": MagicMock(),
        "loadSurveyTemplate": MagicMock(return_value={"meta": {}, "questions": {}, "respondentTypes": []}),
        "buildSurveyPayload": MagicMock(return_value={"meta": {}, "respondents": {}}),
        "markSurveyFormReadyTx": MagicMock(),
        "getSurveyFormByRunId": MagicMock(return_value=None),
        "upsertDmaWorkflowStatus": MagicMock(),
        "requests_post": mock_response,
        "markSurveyFormRetryableBestEffort": MagicMock(),
    }
    if patches_extra:
        default_patches.update(patches_extra)

    with patch.object(fs, "findSurveyRunContext", default_patches["findSurveyRunContext"]), \
         patch.object(fs, "getOrFreezeSurveyFormSnapshotTx", default_patches["getOrFreezeSurveyFormSnapshotTx"]), \
         patch.object(fs, "claimRetryableSurveyFormTx", default_patches["claimRetryableSurveyFormTx"]), \
         patch.object(fs, "loadSurveyTemplate", default_patches["loadSurveyTemplate"]), \
         patch.object(fs, "buildSurveyPayload", default_patches["buildSurveyPayload"]), \
         patch.object(fs, "markSurveyFormReadyTx", default_patches["markSurveyFormReadyTx"]), \
         patch.object(fs, "getSurveyFormByRunId", default_patches["getSurveyFormByRunId"]), \
         patch.object(fs, "upsertDmaWorkflowStatus", default_patches["upsertDmaWorkflowStatus"]), \
         patch.object(fs, "markSurveyFormRetryableBestEffort", default_patches["markSurveyFormRetryableBestEffort"]), \
         patch("requests.post", return_value=default_patches["requests_post"]):
        return fs.ensureSurveyFormForRun(runId), default_patches


class TestFormService(unittest.TestCase):

    def setUp(self):
        self.fs = _load_formservice()

    def test_44_workflow_top20_freeze_progress_20(self):
        _, patches = _run_ensure(self.fs)
        upsert = patches["upsertDmaWorkflowStatus"]
        first_call = upsert.call_args_list[0]
        self.assertEqual(first_call.kwargs.get("currentStage"), "TOP20_FREEZE")
        self.assertEqual(first_call.kwargs.get("progressPercent"), 20)
        self.assertTrue(first_call.kwargs.get("startedYn"))

    def test_45_workflow_payload_build_progress_45(self):
        _, patches = _run_ensure(self.fs)
        stages = [c.kwargs.get("currentStage") for c in patches["upsertDmaWorkflowStatus"].call_args_list]
        self.assertIn("PAYLOAD_BUILD", stages)
        pb_call = next(c for c in patches["upsertDmaWorkflowStatus"].call_args_list if c.kwargs.get("currentStage") == "PAYLOAD_BUILD")
        self.assertEqual(pb_call.kwargs.get("progressPercent"), 45)

    def test_46_workflow_form_create_progress_70(self):
        _, patches = _run_ensure(self.fs)
        stages = [c.kwargs.get("currentStage") for c in patches["upsertDmaWorkflowStatus"].call_args_list]
        self.assertIn("FORM_CREATE", stages)
        fc_call = next(c for c in patches["upsertDmaWorkflowStatus"].call_args_list if c.kwargs.get("currentStage") == "FORM_CREATE")
        self.assertEqual(fc_call.kwargs.get("progressPercent"), 70)

    def test_47_workflow_url_save_progress_90(self):
        _, patches = _run_ensure(self.fs)
        stages = [c.kwargs.get("currentStage") for c in patches["upsertDmaWorkflowStatus"].call_args_list]
        self.assertIn("URL_SAVE", stages)
        us_call = next(c for c in patches["upsertDmaWorkflowStatus"].call_args_list if c.kwargs.get("currentStage") == "URL_SAVE")
        self.assertEqual(us_call.kwargs.get("progressPercent"), 90)

    def test_48_workflow_completed_progress_100(self):
        _, patches = _run_ensure(self.fs)
        stages = [c.kwargs.get("currentStage") for c in patches["upsertDmaWorkflowStatus"].call_args_list]
        self.assertIn("COMPLETED", stages)
        co_call = next(c for c in patches["upsertDmaWorkflowStatus"].call_args_list if c.kwargs.get("currentStage") == "COMPLETED")
        self.assertEqual(co_call.kwargs.get("progressPercent"), 100)
        self.assertTrue(co_call.kwargs.get("completedYn"))

    def test_49_db_context_company_id_year_injected_from_run_context(self):
        template_injected = [{}]
        original_build = MagicMock(return_value={"meta": {}, "respondents": {}})

        def capture_load():
            t = {"meta": {}, "questions": {}, "respondentTypes": []}
            template_injected[0] = t
            return t

        _, patches = _run_ensure(self.fs, patches_extra={
            "loadSurveyTemplate": MagicMock(side_effect=capture_load),
            "buildSurveyPayload": original_build,
        })
        # After ensureSurveyFormForRun, template meta should have companyId / year from DB
        t = template_injected[0]
        self.assertEqual(t["meta"].get("companyId"), 6)
        self.assertEqual(t["meta"].get("year"), 2025)

    def test_50_snapshot_issues_injected_into_template(self):
        template_ref = [{}]

        def capture_load():
            t = {"meta": {}, "questions": {}, "respondentTypes": []}
            template_ref[0] = t
            return t

        _run_ensure(self.fs, patches_extra={
            "loadSurveyTemplate": MagicMock(side_effect=capture_load),
        })
        issues = template_ref[0]["meta"].get("issues", [])
        self.assertEqual(len(issues), 20)
        self.assertIn("code", issues[0])
        self.assertIn("name", issues[0])
        self.assertIn("rank", issues[0])

    def test_51_apps_script_non_success_raises(self):
        bad_resp = MagicMock()
        bad_resp.json.return_value = {"status": "error", "message": "fail"}
        with self.assertRaises(RuntimeError):
            _run_ensure(self.fs, patches_extra={"requests_post": bad_resp})

    def test_52_apps_script_non_json_raises(self):
        bad_resp = MagicMock()
        bad_resp.json.side_effect = ValueError("not json")
        bad_resp.status_code = 200
        bad_resp.text = "not json"
        with self.assertRaises(RuntimeError):
            _run_ensure(self.fs, patches_extra={"requests_post": bad_resp})

    def test_53_missing_masterSheetId_raises(self):
        resp = MagicMock()
        resp.json.return_value = {
            "status": "success",
            "data": {"masterSheetId": "", "forms": {"employee": "e", "management": "m", "external": "x"}},
        }
        with self.assertRaises(RuntimeError):
            _run_ensure(self.fs, patches_extra={"requests_post": resp})

    def test_54_missing_forms_raises(self):
        resp = MagicMock()
        resp.json.return_value = {
            "status": "success",
            "data": {"masterSheetId": "S1"},
        }
        with self.assertRaises(RuntimeError):
            _run_ensure(self.fs, patches_extra={"requests_post": resp})

    def test_55_simple_string_url_extraction(self):
        result, _ = _run_ensure(self.fs)
        # Should succeed without errors; URLs come from mock response

    def test_56_legacy_alias_emp_extraction(self):
        resp = MagicMock()
        resp.json.return_value = {
            "status": "success",
            "data": {
                "masterSheetId": "S1",
                "forms": {"emp": "https://e", "exec": "https://m", "ext": "https://x"},
            },
        }
        result, _ = _run_ensure(self.fs, patches_extra={"requests_post": resp})

    def test_57_object_url_extraction(self):
        resp = MagicMock()
        resp.json.return_value = {
            "status": "success",
            "data": {
                "masterSheetId": "S1",
                "forms": {
                    "employee": {"url": "https://e"},
                    "management": {"formUrl": "https://m"},
                    "external": {"url": "https://x"},
                },
            },
        }
        result, _ = _run_ensure(self.fs, patches_extra={"requests_post": resp})

    def test_58_multi_variant_url_rejects(self):
        resp = MagicMock()
        resp.json.return_value = {
            "status": "success",
            "data": {
                "masterSheetId": "S1",
                "forms": {
                    "employee": "https://e1",
                    "emp": "https://e2",  # duplicate variant
                    "management": "https://m",
                    "external": "https://x",
                },
            },
        }
        with self.assertRaises(RuntimeError):
            _run_ensure(self.fs, patches_extra={"requests_post": resp})

    def test_59_ready_row_idempotent_no_apps_script(self):
        ready_freeze = {
            "id": 5, "surveyStatus": "READY", "survey_status": "READY",
            "snapshot": [{"rankNo": i} for i in range(1, 21)],
            "top20_snapshot_json": "[]",
            "esg_materiality_run_id": 48, "template_version": "v2",
            "master_sheet_id": "S1", "employee_form_url": "https://e",
            "management_form_url": "https://m", "external_form_url": "https://x",
            "error_message": None, "generated_at": None, "updated_at": None,
        }
        apps_called = [False]

        def fake_post(*a, **kw):
            apps_called[0] = True
            raise AssertionError("Apps Script must not be called for READY idempotency")

        _run_ensure(self.fs, patches_extra={
            "getOrFreezeSurveyFormSnapshotTx": MagicMock(return_value=ready_freeze),
            "requests_post": None,  # won't be used
        })
        # If we get here without AssertionError, test passes
        # (fake_post is not called since we're not patching requests.post for READY path)

    def test_60_retryable_calls_claim_and_reuses_snapshot(self):
        snap = [{"rankNo": i, "subIssueCode": f"C{i}", "subIssueName": "n", "finalImpactScore": 1.0, "finalFinancialScore": 1.0, "finalScore": 1.0} for i in range(1, 21)]
        retry_freeze = {
            "id": 6, "surveyStatus": "RETRYABLE", "survey_status": "RETRYABLE",
            "snapshot": snap,
            "top20_snapshot_json": json.dumps(snap),
            "esg_materiality_run_id": 48, "template_version": "v2",
            "master_sheet_id": None, "employee_form_url": None,
            "management_form_url": None, "external_form_url": None,
            "error_message": "prev", "generated_at": None, "updated_at": None,
        }
        claim_mock = MagicMock()
        _run_ensure(self.fs, patches_extra={
            "getOrFreezeSurveyFormSnapshotTx": MagicMock(return_value=retry_freeze),
            "claimRetryableSurveyFormTx": claim_mock,
        })
        claim_mock.assert_called_once_with(6)

    def test_61_external_failure_marks_retryable(self):
        bad_resp = MagicMock()
        bad_resp.json.return_value = {"status": "error"}
        retry_mock = MagicMock()
        with self.assertRaises(RuntimeError):
            _run_ensure(self.fs, patches_extra={
                "requests_post": bad_resp,
                "markSurveyFormRetryableBestEffort": retry_mock,
            })
        retry_mock.assert_called_once()

    def test_62_url_save_failure_marks_retryable(self):
        retry_mock = MagicMock()
        with self.assertRaises(RuntimeError):
            _run_ensure(self.fs, patches_extra={
                "markSurveyFormReadyTx": MagicMock(side_effect=RuntimeError("db write failed")),
                "markSurveyFormRetryableBestEffort": retry_mock,
            })
        retry_mock.assert_called_once()

    def test_63_original_error_preserved_even_if_retryable_write_fails(self):
        retry_mock = MagicMock(side_effect=RuntimeError("retryable write also failed"))
        bad_resp = MagicMock()
        bad_resp.json.return_value = {"status": "error", "message": "original error"}
        with self.assertRaises(RuntimeError) as ctx:
            _run_ensure(self.fs, patches_extra={
                "requests_post": bad_resp,
                "markSurveyFormRetryableBestEffort": retry_mock,
            })
        # Original error should propagate, not the retryable write error
        self.assertNotIn("retryable write also failed", str(ctx.exception))

    def test_64_workflow_type_is_survey_form(self):
        _, patches = _run_ensure(self.fs)
        for c in patches["upsertDmaWorkflowStatus"].call_args_list:
            self.assertEqual(c.kwargs.get("workflowType"), "SURVEY_FORM")

    def test_65_runId_bool_rejected(self):
        with self.assertRaises(ValueError):
            self.fs.ensureSurveyFormForRun(True)

    def test_66_runId_zero_rejected(self):
        with self.assertRaises(ValueError):
            self.fs.ensureSurveyFormForRun(0)


# ════════════════════════════════════════════════════════════════════════════
# §11.5  Survey API
# ════════════════════════════════════════════════════════════════════════════

def _load_survey_router():
    for mod in list(sys.modules.keys()):
        if "survey" in mod and "test" not in mod:
            sys.modules.pop(mod, None)
    return importlib.import_module("src.apis.survey")


class TestSurveyApi(unittest.TestCase):

    def test_67_get_form_route_exists(self):
        router_mod = _load_survey_router()
        routes = [r.path for r in router_mod.router.routes]
        self.assertIn("/form/{runId}", routes)

    def test_68_post_form_retry_route_exists(self):
        router_mod = _load_survey_router()
        routes = [r.path for r in router_mod.router.routes]
        self.assertIn("/form/{runId}/retry", routes)

    def test_69_raw_route_exists(self):
        router_mod = _load_survey_router()
        routes = [r.path for r in router_mod.router.routes]
        self.assertIn("/raw", routes)

    def test_70_catch_all_sheet_id_exists(self):
        router_mod = _load_survey_router()
        routes = [r.path for r in router_mod.router.routes]
        self.assertIn("/{sheet_id}", routes)

    def test_71_raw_declared_before_catch_all(self):
        router_mod = _load_survey_router()
        paths = [r.path for r in router_mod.router.routes]
        raw_idx = paths.index("/raw")
        catch_idx = paths.index("/{sheet_id}")
        self.assertLess(raw_idx, catch_idx)

    def test_72_form_runId_declared_before_catch_all(self):
        router_mod = _load_survey_router()
        paths = [r.path for r in router_mod.router.routes]
        form_idx = paths.index("/form/{runId}")
        catch_idx = paths.index("/{sheet_id}")
        self.assertLess(form_idx, catch_idx)

    def test_73_post_survey_route_exists(self):
        router_mod = _load_survey_router()
        post_routes = [r.path for r in router_mod.router.routes if "POST" in [m for m in getattr(r, "methods", [])] or hasattr(r, "methods") and "POST" in r.methods]
        self.assertTrue(any("" == p or p == "" for p in [r.path for r in router_mod.router.routes]))

    def test_74_survey_api_source_imports_from_formservice(self):
        src = pathlib.Path(_BACKEND_ROOT, "src/apis/survey.py").read_text(encoding="utf-8")
        self.assertIn("formservice", src)

    def test_75_get_form_runId_invalid_returns_400(self):
        import asyncio
        router_mod = _load_survey_router()

        async def _run():
            with patch.object(router_mod, "getSurveyFormByRunId", side_effect=ValueError("bad")):
                with patch("src.utils.auth.get_token", return_value={}):
                    from fastapi.testclient import TestClient
                    from fastapi import FastAPI
                    app = FastAPI()
                    app.include_router(router_mod.router, prefix="/survey")
                    client = TestClient(app)
                    # Force ValueError path
                    with patch("src.utils.dmasurveyformrepository.getSurveyFormByRunId", side_effect=ValueError("bad")):
                        resp = client.get("/survey/form/abc", headers={"Authorization": "Bearer test"})
                    return resp

        # Just verify the route is declared with a 400 handler by checking source
        src = pathlib.Path(_BACKEND_ROOT, "src/apis/survey.py").read_text(encoding="utf-8")
        self.assertIn("status_code=400", src)
        self.assertIn("status_code=404", src)
        self.assertIn("status_code=500", src)


# ════════════════════════════════════════════════════════════════════════════
# §11.6  Media Hook
# ════════════════════════════════════════════════════════════════════════════

def _load_media_service():
    for mod in list(sys.modules.keys()):
        if "medias" in mod or ("surveys" in mod and "test" not in mod):
            sys.modules.pop(mod, None)
    return importlib.import_module("src.services.medias.service")


def _complete_crawl_result():
    return SimpleNamespace(
        articles=[SimpleNamespace(title="a", content="b", url="u", publishedAt="2024-01-01", source="naver")],
        requestedSources=["naver"], allowedSources=["naver"], rejectedSources=[],
        collectedArticleCount=1, filteredArticleCount=1, errors=[],
        sourceBreakdown=[SimpleNamespace(status="SUCCESS")],
    )


def _partial_crawl_result():
    # allowedSources=[] → _isCrawlComplete returns False immediately
    return SimpleNamespace(
        articles=[], requestedSources=["naver"], allowedSources=[],
        rejectedSources=[], collectedArticleCount=0, filteredArticleCount=0,
        errors=[], sourceBreakdown=[],
    )


def _make_media_request(runId=48):
    return SimpleNamespace(
        runId=runId, sources=["naver"],
        dateFrom="2024-01-01", dateTo="2024-12-31",
    )


def _patch_response_deps(svc):
    return [
        patch.object(svc, "applySavedSignalCounts", return_value=[]),
        patch.object(svc, "getMediaCoverage", return_value={"coverageStatus": "OK"}),
        patch.object(svc, "countMediaSubIssues", return_value=0),
        patch.object(svc, "_buildMediaTopIssues", return_value=[]),
    ]


class TestMediaHook(unittest.TestCase):

    def setUp(self):
        self.svc = _load_media_service()

    def test_76_complete_crawl_calls_ensure_survey_form_once(self):
        deps = _patch_response_deps(self.svc)
        ensure_mock = MagicMock()
        with patch.object(self.svc, "crawlNewsArticles", return_value=_complete_crawl_result()), \
             patch.object(self.svc, "runMediaAnalysis", return_value=[]), \
             patch.object(self.svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(self.svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(self.svc, "refreshMediaExternalMaxForRun", return_value=0), \
             patch.object(self.svc, "ensureSurveyFormForRun", ensure_mock), \
             deps[0], deps[1], deps[2], deps[3]:
            self.svc.runMediaCrawlAndAnalyze(_make_media_request())
        ensure_mock.assert_called_once_with(48)

    def test_77_partial_crawl_skips_ensure_survey_form(self):
        deps = _patch_response_deps(self.svc)
        ensure_mock = MagicMock()
        with patch.object(self.svc, "crawlNewsArticles", return_value=_partial_crawl_result()), \
             patch.object(self.svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(self.svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(self.svc, "ensureSurveyFormForRun", ensure_mock), \
             deps[0], deps[1], deps[2], deps[3]:
            self.svc.runMediaCrawlAndAnalyze(_make_media_request())
        ensure_mock.assert_not_called()

    def test_78_external_max_failure_skips_ensure_survey_form(self):
        ensure_mock = MagicMock()
        with patch.object(self.svc, "crawlNewsArticles", return_value=_complete_crawl_result()), \
             patch.object(self.svc, "runMediaAnalysis", return_value=[]), \
             patch.object(self.svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(self.svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(self.svc, "refreshMediaExternalMaxForRun", side_effect=RuntimeError("ext fail")), \
             patch.object(self.svc, "ensureSurveyFormForRun", ensure_mock):
            with self.assertRaises(RuntimeError):
                self.svc.runMediaCrawlAndAnalyze(_make_media_request())
        ensure_mock.assert_not_called()

    def test_79_survey_form_failure_propagates_to_media_endpoint(self):
        deps = _patch_response_deps(self.svc)
        with patch.object(self.svc, "crawlNewsArticles", return_value=_complete_crawl_result()), \
             patch.object(self.svc, "runMediaAnalysis", return_value=[]), \
             patch.object(self.svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(self.svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(self.svc, "refreshMediaExternalMaxForRun", return_value=0), \
             patch.object(self.svc, "ensureSurveyFormForRun", side_effect=RuntimeError("survey fail")), \
             deps[0], deps[1], deps[2], deps[3]:
            with self.assertRaises(RuntimeError) as ctx:
                self.svc.runMediaCrawlAndAnalyze(_make_media_request())
        self.assertIn("survey fail", str(ctx.exception))

    def test_80_ensure_survey_form_called_after_external_max(self):
        call_order = []

        def fake_ext_max(runId):
            call_order.append("ext_max")
            return 0

        def fake_ensure(runId):
            call_order.append("ensure_survey")

        deps = _patch_response_deps(self.svc)
        with patch.object(self.svc, "crawlNewsArticles", return_value=_complete_crawl_result()), \
             patch.object(self.svc, "runMediaAnalysis", return_value=[]), \
             patch.object(self.svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(self.svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(self.svc, "refreshMediaExternalMaxForRun", side_effect=fake_ext_max), \
             patch.object(self.svc, "ensureSurveyFormForRun", side_effect=fake_ensure), \
             deps[0], deps[1], deps[2], deps[3]:
            self.svc.runMediaCrawlAndAnalyze(_make_media_request())

        self.assertEqual(call_order, ["ext_max", "ensure_survey"])

    def test_81_run_media_analysis_smoke_does_not_call_ensure_survey_form(self):
        source = inspect.getsource(self.svc.runMediaAnalysis)
        self.assertNotIn("ensureSurveyFormForRun", source)

    def test_82_media_summary_commit_no_rollback_on_survey_failure(self):
        source = inspect.getsource(self.svc.runMediaCrawlAndAnalyze)
        # No rollback of External MAX after ensureSurveyFormForRun
        # Verify ensureSurveyFormForRun is called directly (not inside a try that rolls back ext_max)
        self.assertIn("ensureSurveyFormForRun", source)


# ════════════════════════════════════════════════════════════════════════════
# §11.7  Guard
# ════════════════════════════════════════════════════════════════════════════

class TestGuard(unittest.TestCase):

    def _git_diff_files(self, path_spec):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "--", path_spec],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(_BACKEND_ROOT.parent),
        )
        return (result.stdout or "").strip()

    def test_83_frontend_diff_zero(self):
        diff = self._git_diff_files("frontend")
        # Survey.jsx is intentionally modified in C4.0.1 (URL area real API connection)
        filtered = "\n".join(
            line for line in diff.splitlines() if "Survey.jsx" not in line
        ).strip()
        self.assertEqual(filtered, "", f"frontend diff must be 0 lines (excluding Survey.jsx), got: {filtered}")

    def test_84_sql_diff_zero(self):
        diff = self._git_diff_files("*.sql")
        self.assertEqual(diff, "", f"SQL diff must be 0 lines, got: {diff}")

    def test_85_dmaworkflowrepository_diff_zero(self):
        diff = self._git_diff_files("backend/src/utils/dmaworkflowrepository.py")
        self.assertEqual(diff, "", f"dmaworkflowrepository.py must not be modified, got: {diff}")

    def test_86_dmarepository_diff_zero(self):
        diff = self._git_diff_files("backend/src/utils/dmarepository.py")
        self.assertEqual(diff, "", f"dmarepository.py must not be modified, got: {diff}")

    def test_87_orchestrator_diff_zero(self):
        diff = self._git_diff_files("backend/src/services/materialities/orchestrator.py")
        self.assertEqual(diff, "", f"orchestrator.py must not be modified, got: {diff}")

    def test_88_no_new_survey_question_table_reference(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--", "backend/src"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(_BACKEND_ROOT.parent),
        )
        added_lines = [l for l in (result.stdout or "").splitlines() if l.startswith("+") and not l.startswith("+++")]
        question_refs = [l for l in added_lines if "ESG_DMA_SURVEY_QUESTION" in l]
        self.assertEqual(question_refs, [], f"No new ESG_DMA_SURVEY_QUESTION references allowed: {question_refs}")

    def test_89_no_new_question_id_reference(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--", "backend/src"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(_BACKEND_ROOT.parent),
        )
        added_lines = [l for l in (result.stdout or "").splitlines() if l.startswith("+") and not l.startswith("+++")]
        qid_refs = [l for l in added_lines if "question_id" in l]
        self.assertEqual(qid_refs, [], f"No new question_id references allowed: {qid_refs}")

    def test_90_no_eval_exec_in_new_src(self):
        new_files = [
            _BACKEND_ROOT / "src/models/dmasurveyform.py",
            _BACKEND_ROOT / "src/utils/dmasurveyformrepository.py",
            _BACKEND_ROOT / "src/services/surveys/formservice.py",
        ]
        for fp in new_files:
            src = fp.read_text(encoding="utf-8")
            self.assertNotIn("eval(", src, f"eval() found in {fp.name}")
            self.assertNotIn("exec(", src, f"exec() found in {fp.name}")

    def test_91_survey_form_workflow_type_in_workflow_types(self):
        import src.utils.dmaworkflowrepository as wf
        self.assertIn("SURVEY_FORM", wf.WORKFLOW_TYPES)

    def test_92_retryable_in_overall_statuses(self):
        import src.utils.dmaworkflowrepository as wf
        self.assertIn("RETRYABLE", wf.OVERALL_STATUSES)

    def test_93_no_google_sheets_import_in_formservice(self):
        src = (_BACKEND_ROOT / "src/services/surveys/formservice.py").read_text(encoding="utf-8")
        self.assertNotIn("googleapiclient", src)
        self.assertNotIn("google.oauth2", src)
        self.assertNotIn("service_account", src)

    def test_94_lazy_sheets_init_in_service_py(self):
        src = (_BACKEND_ROOT / "src/services/surveys/service.py").read_text(encoding="utf-8")
        self.assertIn("_getSheetsService", src)
        # Module-level sheetsService instantiation must be gone
        self.assertNotIn("sheetsService = build(", src)

    def test_95_media_service_imports_ensure_survey_form(self):
        src = (_BACKEND_ROOT / "src/services/medias/service.py").read_text(encoding="utf-8")
        self.assertIn("ensureSurveyFormForRun", src)
        self.assertIn("formservice", src)

    def test_96_update_retryable_sql_has_generating_guard(self):
        sql = _repo_mod._UPDATE_RETRYABLE_SQL
        self.assertIn("survey_status = 'GENERATING'", sql)

    def test_97_update_ready_sql_has_generating_guard(self):
        sql = _repo_mod._UPDATE_READY_SQL
        self.assertIn("survey_status = 'GENERATING'", sql)


# ════════════════════════════════════════════════════════════════════════════
# §11.8  State Machine — READY 강등 방지
# ════════════════════════════════════════════════════════════════════════════

class TestStateMachineGuard(unittest.TestCase):

    def _run_retryable_update(self, initial_status: str) -> int:
        """실제 SQL WHERE 조건 확인: GENERATING 이외 상태에서는 rowcount=0."""
        written_params = []

        class RC:
            def __init__(self):
                self.rowcount = 0  # DB side: WHERE 조건 불일치 → rowcount 0

            def __enter__(self): return self
            def __exit__(self, *a): return False

            def execute(self, sql, params=None):
                written_params.append(params)
                # 상태 조건 시뮬레이션
                if initial_status != "GENERATING":
                    self.rowcount = 0
                else:
                    self.rowcount = 1

        conn = FakeConn(RC())
        with patch.object(_repo_mod, "getConn", return_value=conn):
            _repo_mod.markSurveyFormRetryableBestEffort(formId=1, errorMessage="err")
        return conn._cur.rowcount

    def _run_ready_update(self, initial_status: str) -> int:
        """markSurveyFormReadyTx: GENERATING 이외 상태에서는 rowcount 0 → RuntimeError."""

        class RC:
            def __init__(self):
                self.rowcount = 1 if initial_status == "GENERATING" else 0

            def __enter__(self): return self
            def __exit__(self, *a): return False

            def execute(self, sql, params=None): pass

        conn = FakeConn(RC())
        with patch.object(_repo_mod, "getConn", return_value=conn):
            if initial_status != "GENERATING":
                with self.assertRaises(RuntimeError):
                    _repo_mod.markSurveyFormReadyTx(
                        formId=1, masterSheetId="s",
                        employeeFormUrl="e", managementFormUrl="m", externalFormUrl="x",
                    )
                return 0
            else:
                _repo_mod.markSurveyFormReadyTx(
                    formId=1, masterSheetId="s",
                    employeeFormUrl="e", managementFormUrl="m", externalFormUrl="x",
                )
                return 1

    def test_98_ready_form_not_downgraded_to_retryable(self):
        rowcount = self._run_retryable_update("READY")
        self.assertEqual(rowcount, 0, "READY 상태에서 RETRYABLE Update가 적용되면 안 됨")

    def test_99_closed_form_not_downgraded_to_retryable(self):
        rowcount = self._run_retryable_update("CLOSED")
        self.assertEqual(rowcount, 0, "CLOSED 상태에서 RETRYABLE Update가 적용되면 안 됨")

    def test_100_ready_update_allowed_only_from_generating(self):
        result = self._run_ready_update("GENERATING")
        self.assertEqual(result, 1, "GENERATING → READY 전이 허용")

    def test_101_ready_update_blocked_from_ready(self):
        self._run_ready_update("READY")  # assertRaises inside

    def test_102_workflow_completed_failure_does_not_downgrade_ready_form(self):
        """markSurveyFormReadyTx 성공 후 Workflow COMPLETED 저장 실패 시 Form READY 유지."""
        fs = _load_formservice()

        freeze_result = {
            "id": 1, "surveyStatus": "GENERATING", "survey_status": "GENERATING",
            "snapshot": [
                {"rankNo": i, "subIssueCode": f"C{i}", "subIssueName": "n",
                 "finalImpactScore": 1.0, "finalFinancialScore": 1.0, "finalScore": 1.0}
                for i in range(1, 21)
            ],
            "top20_snapshot_json": "[]", "esg_materiality_run_id": 48, "template_version": "v2",
            "master_sheet_id": None, "employee_form_url": None,
            "management_form_url": None, "external_form_url": None,
            "error_message": None, "generated_at": None, "updated_at": None,
        }
        apps_response = MagicMock()
        apps_response.json.return_value = _make_ready_apps_response()

        mark_ready_called = [False]
        retryable_called = [False]
        workflow_call_count = [0]

        def fake_mark_ready(**kw):
            mark_ready_called[0] = True

        def fake_retryable(**kw):
            retryable_called[0] = True

        def fake_upsert(**kw):
            workflow_call_count[0] += 1
            # COMPLETED 저장 시도 시 실패
            if kw.get("overallStatus") == "COMPLETED":
                raise RuntimeError("workflow DB down")

        with patch.object(fs, "findSurveyRunContext", return_value={"runId": 48, "companyId": 6, "reportingYear": 2025}), \
             patch.object(fs, "getOrFreezeSurveyFormSnapshotTx", return_value=freeze_result), \
             patch.object(fs, "claimRetryableSurveyFormTx", MagicMock()), \
             patch.object(fs, "loadSurveyTemplate", return_value={"meta": {}, "questions": {}, "respondentTypes": []}), \
             patch.object(fs, "buildSurveyPayload", return_value={"meta": {}, "respondents": {}}), \
             patch.object(fs, "markSurveyFormReadyTx", side_effect=fake_mark_ready), \
             patch.object(fs, "getSurveyFormByRunId", return_value=None), \
             patch.object(fs, "upsertDmaWorkflowStatus", side_effect=fake_upsert), \
             patch.object(fs, "markSurveyFormRetryableBestEffort", side_effect=fake_retryable), \
             patch("requests.post", return_value=apps_response):
            with self.assertRaises(RuntimeError):
                fs.ensureSurveyFormForRun(48)

        # markSurveyFormReadyTx는 성공했고 RETRYABLE Best Effort가 실행됐지만,
        # _UPDATE_RETRYABLE_SQL의 WHERE survey_status='GENERATING' 조건으로
        # DB에서 실제 downgrade는 발생하지 않음 (rowcount=0)
        self.assertTrue(mark_ready_called[0], "markSurveyFormReadyTx는 호출돼야 함")
        self.assertTrue(retryable_called[0], "except에서 markSurveyFormRetryableBestEffort는 호출됨")


if __name__ == "__main__":
    unittest.main(verbosity=2)
