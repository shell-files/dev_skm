"""
DMA v1.3 Phase C3.1.2 regulation runtime safety review tests.

Pure unit tests. No live DB, Redis, Kafka, Docker, external API, API router,
frontend, SQL/DDL, Summary/Rank, KCGS/KIS, or externalMax path is exercised.
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


_DUMMY_ENV = {
    "host_ip": "127.0.0.1",
    "domain": "test",
    "skm_domain": "test",
    "file_dir": "/tmp",
    "gemini_api_key": "test",
    "gemini_model": "test",
    "kafka_server": "test",
    "kafka_topic": "test",
    "mail_username": "test",
    "mail_password": "test",
    "mail_from": "test@test",
    "access_token_expire_minutes": "1",
    "refresh_token_expire_days": "1",
    "invite_token_expire_days": "1",
    "redis_host": "test",
    "redis_port": "6379",
    "redis_db1": "0",
    "redis_db2": "1",
    "redis_db3": "2",
    "service_key": "test",
    "maria_db_user": "test",
    "maria_db_password": "test",
    "maria_db_host": "test",
    "maria_db_database": "test",
    "maria_db_port": "3306",
    "maria_db_key": "test",
    "cookie_key": "test",
    "APPS_SCRIPT_URL": "test",
    "pg_db_host": "test",
    "pg_db_port": "5432",
    "pg_db_database": "test",
    "pg_db_user": "test",
    "pg_db_password": "test",
    "ollama_url": "http://test",
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
RUN_ID = 7
CSRD_SUB = "G_DATA_GOVERNANCE__DISCLOSURE_ASSURANCE"
CBAM_SUB = "E_CLIMATE__GHG_SCOPE12_EMISSIONS"
DPP_SUB = "E_CIRCULARITY__RECYCLING_RECOVERY"


def _resetPolicies():
    reg.resetDmaRulesForTest()


def _approvedInput(
    regime="CSRD",
    applicability="DIRECT_MANDATORY",
    companyId=1001,
    reportingYear=2026,
):
    return {
        "companyId": companyId,
        "reportingYear": reportingYear,
        "regime": regime,
        "applicability": applicability,
        "inputMethod": "MANUAL",
        "sourceDocumentRef": "board-minutes-1",
        "reviewStatus": "APPROVED",
        "reviewerComment": "approved for runtime safety test",
    }


def _approvedMapping(regime="CSRD", subIssueCode=CSRD_SUB):
    return {
        "regime": regime,
        "subIssueCode": subIssueCode,
        "mappingReason": "screening seed relation",
        "activeYn": True,
        "reviewStatus": "APPROVED",
    }


def _regPayload(
    regime="CSRD",
    applicability="DIRECT_MANDATORY",
    subIssueCode=CSRD_SUB,
    companyId=1001,
    reportingYear=2026,
):
    payloads = orchestrator.step2BuildRegulationScreeningPayloads(
        [
            _approvedInput(
                regime=regime,
                applicability=applicability,
                companyId=companyId,
                reportingYear=reportingYear,
            )
        ],
        [_approvedMapping(regime=regime, subIssueCode=subIssueCode)],
    )
    assert len(payloads) == 1
    return payloads[0]


def _craftedRegDict(regime="CSRD", channel="regulation_csrd", subIssueCode=CSRD_SUB):
    return {
        "scorePurpose": "PRESURVEY_SCREENING",
        "sourceChannel": "media_external",
        "subIssueCode": subIssueCode,
        "screeningTrace": [
            {
                "channel": channel,
                "scorePurpose": "PRESURVEY_SCREENING",
                "impactSignal": 3.0,
                "financialSignal": 4.0,
                "status": "OBSERVED",
                "rawInputs": {
                    "regime": regime,
                    "applicability": "DIRECT_MANDATORY",
                    "sourceStep": "media_external",
                    "sourceType": "regulation",
                    "companyId": 1001,
                    "reportingYear": 2026,
                },
            }
        ],
    }


def _serializeCrafted(mutator=None, regime="CSRD", channel="regulation_csrd"):
    data = _craftedRegDict(regime=regime, channel=channel)
    if mutator:
        mutator(data)
    with patch("src.utils.dmarepository.step4WriteTrace", return_value=json.dumps(data)):
        return repo._buildRegulationShadowRows(RUN_ID, [{}])


def _installMediaServiceImportStubs():
    """Keep service hook tests pure; do not import NLP/native pipeline dependencies."""
    adapter = types.ModuleType("src.services.medias.adapter")
    adapter.convertMediaToDmaSignals = lambda pipelineResults: []
    adapter.step0NormalizeMediaFacts = lambda pipelineResults: []
    sys.modules["src.services.medias.adapter"] = adapter

    baseline = types.ModuleType("src.services.medias.baseline")
    baseline.applyMediaBaseline = lambda signals: signals
    sys.modules["src.services.medias.baseline"] = baseline

    crawler = types.ModuleType("src.services.medias.crawler")
    crawler.applySavedSignalCounts = lambda sourceBreakdown, savedSignalCountsBySource: sourceBreakdown
    crawler.crawlNewsArticles = lambda **kwargs: None
    sys.modules["src.services.medias.crawler"] = crawler

    pipeline = types.ModuleType("src.services.medias.pipeline")
    pipeline.processMediaPipeline = lambda articles, companyKeywords=None, industryKeywords=None: []
    sys.modules["src.services.medias.pipeline"] = pipeline


class _ReaderCursor:
    def __init__(
        self,
        fetchone_result=None,
        fetchall_result=None,
        execute_error=None,
        fetchone_error=None,
        fetchall_error=None,
    ):
        self.sql_log = []
        self.fetchone_result = fetchone_result
        self.fetchall_result = fetchall_result
        self.execute_error = execute_error
        self.fetchone_error = fetchone_error
        self.fetchall_error = fetchall_error

    def execute(self, sql, params=None):
        self.sql_log.append((sql.strip(), params))
        if self.execute_error:
            raise self.execute_error

    def fetchone(self):
        if self.fetchone_error:
            raise self.fetchone_error
        return self.fetchone_result

    def fetchall(self):
        if self.fetchall_error:
            raise self.fetchall_error
        return self.fetchall_result

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _TxCursor:
    def __init__(
        self,
        fetchone_queue=None,
        executemany_error=None,
        count_error=None,
        update_error=None,
    ):
        self.sql_log = []
        self._queue = list(fetchone_queue or [])
        self.executemany_error = executemany_error
        self.count_error = count_error
        self.update_error = update_error

    def execute(self, sql, params=None):
        text = sql.strip()
        self.sql_log.append(("x", text, params))
        if self.update_error and "UPDATE" in text and "delete_yn" in text:
            raise self.update_error
        if self.count_error and "COUNT(*)" in text:
            raise self.count_error

    def executemany(self, sql, rows):
        self.sql_log.append(("xm", sql.strip(), rows))
        if self.executemany_error:
            raise self.executemany_error

    def fetchone(self):
        return self._queue.pop(0) if self._queue else None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _MockConn:
    def __init__(self, cursor):
        self.autocommit = True
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self._cursor = cursor

    def cursor(self, **kwargs):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _conn(cursor):
    return _MockConn(cursor=cursor)


def _runTx(payloads, queue):
    cursor = _TxCursor(fetchone_queue=queue)
    conn = _conn(cursor)
    with patch("src.utils.dmarepository.getConn", return_value=conn):
        result = repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, payloads)
    return result, conn


class PhaseC312StrictReaderTest(unittest.TestCase):
    def test_61_run_context_reader_none_conn_raises_runtime_error(self):
        with patch("src.utils.dmarepository.getConn", return_value=None):
            with self.assertRaises(RuntimeError):
                repo.findRegulationRunContext(RUN_ID)

    def test_62_run_context_reader_execute_failure_raises_runtime_error(self):
        conn = _conn(_ReaderCursor(execute_error=RuntimeError("execute failed")))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.findRegulationRunContext(RUN_ID)

    def test_63_input_reader_fetchall_failure_raises_runtime_error(self):
        conn = _conn(_ReaderCursor(fetchall_error=RuntimeError("fetchall failed")))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.listApprovedRegulationInputs(1001, 2026)

    def test_64_mapping_reader_fetchall_failure_raises_runtime_error(self):
        conn = _conn(_ReaderCursor(fetchall_error=RuntimeError("fetchall failed")))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.listApprovedActiveRegulationMappings()

    def test_65_strict_one_reader_success_closes_connection(self):
        conn = _conn(_ReaderCursor(fetchone_result={"runId": RUN_ID}))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo._findOneRegulationRowOrRaise("SELECT 1")
        self.assertTrue(conn.closed)

    def test_66_strict_all_reader_success_closes_connection(self):
        conn = _conn(_ReaderCursor(fetchall_result=[]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo._findAllRegulationRowsOrRaise("SELECT 1")
        self.assertTrue(conn.closed)

    def test_67_strict_one_reader_failure_closes_connection(self):
        conn = _conn(_ReaderCursor(execute_error=RuntimeError("execute failed")))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo._findOneRegulationRowOrRaise("SELECT 1")
        self.assertTrue(conn.closed)

    def test_68_strict_all_reader_failure_closes_connection(self):
        conn = _conn(_ReaderCursor(fetchall_error=RuntimeError("fetchall failed")))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo._findAllRegulationRowsOrRaise("SELECT 1")
        self.assertTrue(conn.closed)


class PhaseC312ServiceFailClosedAndEmptyClearTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()
        _installMediaServiceImportStubs()
        sys.modules.pop("src.services.medias.service", None)
        self.svc = importlib.import_module("src.services.medias.service")

    def test_69_run_context_reader_failure_skips_writer(self):
        with patch.object(self.svc, "findRegulationRunContext", side_effect=RuntimeError("broken")), \
             patch.object(self.svc, "step4ReplaceRegulationShadowTracesTx") as writer:
            with self.assertRaises(RuntimeError):
                self.svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_not_called()

    def test_70_input_reader_failure_skips_writer(self):
        with patch.object(
            self.svc,
            "findRegulationRunContext",
            return_value={"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026},
        ), \
             patch.object(self.svc, "listApprovedRegulationInputs", side_effect=RuntimeError("broken")), \
             patch.object(self.svc, "step4ReplaceRegulationShadowTracesTx") as writer:
            with self.assertRaises(RuntimeError):
                self.svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_not_called()

    def test_71_mapping_reader_failure_skips_writer(self):
        with patch.object(
            self.svc,
            "findRegulationRunContext",
            return_value={"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026},
        ), \
             patch.object(self.svc, "listApprovedRegulationInputs", return_value=[_approvedInput()]), \
             patch.object(self.svc, "listApprovedActiveRegulationMappings", side_effect=RuntimeError("broken")), \
             patch.object(self.svc, "step4ReplaceRegulationShadowTracesTx") as writer:
            with self.assertRaises(RuntimeError):
                self.svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_not_called()

    def test_72_builder_failure_skips_writer(self):
        with patch.object(
            self.svc,
            "findRegulationRunContext",
            return_value={"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026},
        ), \
             patch.object(self.svc, "listApprovedRegulationInputs", return_value=[_approvedInput()]), \
             patch.object(self.svc, "listApprovedActiveRegulationMappings", return_value=[_approvedMapping()]), \
             patch.object(self.svc, "step2BuildRegulationScreeningPayloads", side_effect=ValueError("broken")), \
             patch.object(self.svc, "step4ReplaceRegulationShadowTracesTx") as writer:
            with self.assertRaises(ValueError):
                self.svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_not_called()

    def test_73_normal_empty_input_writes_empty_payloads(self):
        with patch.object(
            self.svc,
            "findRegulationRunContext",
            return_value={"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026},
        ), \
             patch.object(self.svc, "listApprovedRegulationInputs", return_value=[]), \
             patch.object(self.svc, "listApprovedActiveRegulationMappings", return_value=[_approvedMapping()]), \
             patch.object(self.svc, "step4ReplaceRegulationShadowTracesTx", return_value=0) as writer:
            self.svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_called_once_with(RUN_ID, [])

    def test_74_normal_empty_mapping_writes_empty_payloads(self):
        with patch.object(
            self.svc,
            "findRegulationRunContext",
            return_value={"runId": RUN_ID, "companyId": 1001, "reportingYear": 2026},
        ), \
             patch.object(self.svc, "listApprovedRegulationInputs", return_value=[_approvedInput()]), \
             patch.object(self.svc, "listApprovedActiveRegulationMappings", return_value=[]), \
             patch.object(self.svc, "step4ReplaceRegulationShadowTracesTx", return_value=0) as writer:
            self.svc.refreshRegulationShadowForRun(RUN_ID)
        writer.assert_called_once_with(RUN_ID, [])

    def test_75_writer_empty_soft_deletes_prior_active_set(self):
        _, conn = _runTx([], [{"id": RUN_ID}, {"row_count": 0}])
        self.assertTrue(any("SET delete_yn = 1" in sql for kind, sql, _ in conn._cursor.sql_log))

    def test_76_writer_empty_inserts_zero_rows(self):
        _, conn = _runTx([], [{"id": RUN_ID}, {"row_count": 0}])
        self.assertEqual([call for call in conn._cursor.sql_log if call[0] == "xm"], [])

    def test_77_writer_empty_verifies_count_star_zero(self):
        _, conn = _runTx([], [{"id": RUN_ID}, {"row_count": 0}])
        count_sql = [sql for kind, sql, _ in conn._cursor.sql_log if "COUNT(*)" in sql]
        self.assertEqual(len(count_sql), 1)

    def test_78_writer_empty_commits(self):
        result, conn = _runTx([], [{"id": RUN_ID}, {"row_count": 0}])
        self.assertEqual(result, 0)
        self.assertTrue(conn.committed)
        self.assertFalse(conn.rolled_back)


class PhaseC312SerializerTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()

    def test_79_csrd_channel_regime_exact_match_passes(self):
        rows = _serializeCrafted(regime="CSRD", channel="regulation_csrd")
        self.assertEqual(len(rows), 1)

    def test_80_cbam_channel_regime_exact_match_passes(self):
        rows = _serializeCrafted(regime="CBAM", channel="regulation_cbam")
        self.assertEqual(len(rows), 1)

    def test_81_dpp_channel_regime_exact_match_passes(self):
        rows = _serializeCrafted(regime="DPP", channel="regulation_dpp")
        self.assertEqual(len(rows), 1)

    def test_82_cbam_with_csrd_channel_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            _serializeCrafted(regime="CBAM", channel="regulation_csrd")
        self.assertIn("channel/regime mismatch", str(ctx.exception))

    def test_83_csrd_with_unknown_regulation_channel_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            _serializeCrafted(regime="CSRD", channel="regulation_unknown")
        self.assertIn("channel/regime mismatch", str(ctx.exception))

    def test_84_raw_inputs_source_step_mismatch_raises_value_error(self):
        with self.assertRaises(ValueError):
            _serializeCrafted(lambda d: d["screeningTrace"][0]["rawInputs"].__setitem__("sourceStep", "benchmark"))

    def test_85_raw_inputs_source_type_mismatch_raises_value_error(self):
        with self.assertRaises(ValueError):
            _serializeCrafted(lambda d: d["screeningTrace"][0]["rawInputs"].__setitem__("sourceType", "news"))

    def test_86_company_id_bool_raises_value_error(self):
        with self.assertRaises(ValueError):
            _serializeCrafted(lambda d: d["screeningTrace"][0]["rawInputs"].__setitem__("companyId", True))

    def test_87_reporting_year_bool_raises_value_error(self):
        with self.assertRaises(ValueError):
            _serializeCrafted(lambda d: d["screeningTrace"][0]["rawInputs"].__setitem__("reportingYear", False))

    def test_88_missing_regime_raises_value_error(self):
        with self.assertRaises(ValueError):
            _serializeCrafted(lambda d: d["screeningTrace"][0]["rawInputs"].pop("regime"))

    def test_89_missing_applicability_raises_value_error(self):
        with self.assertRaises(ValueError):
            _serializeCrafted(lambda d: d["screeningTrace"][0]["rawInputs"].pop("applicability"))

    def test_90_non_dict_screening_trace_item_raises_value_error(self):
        with self.assertRaises(ValueError):
            _serializeCrafted(lambda d: d.__setitem__("screeningTrace", ["not-a-dict"]))


class PhaseC312ReplaceActiveTxTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()

    def test_91_executemany_failure_rolls_back_and_closes(self):
        conn = _conn(_TxCursor(
            fetchone_queue=[{"id": RUN_ID}],
            executemany_error=RuntimeError("insert failed"),
        ))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, [_regPayload()])
        self.assertTrue(conn.rolled_back)
        self.assertTrue(conn.closed)

    def test_92_count_query_failure_rolls_back_and_closes(self):
        conn = _conn(_TxCursor(
            fetchone_queue=[{"id": RUN_ID}],
            count_error=RuntimeError("count failed"),
        ))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, [_regPayload()])
        self.assertTrue(conn.rolled_back)
        self.assertTrue(conn.closed)

    def test_93_count_mismatch_rolls_back_and_closes(self):
        conn = _conn(_TxCursor(fetchone_queue=[{"id": RUN_ID}, {"row_count": 99}]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, [_regPayload()])
        self.assertTrue(conn.rolled_back)
        self.assertTrue(conn.closed)

    def test_94_missing_run_row_rolls_back_and_closes(self):
        conn = _conn(_TxCursor(fetchone_queue=[None]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, [])
        self.assertTrue(conn.rolled_back)
        self.assertTrue(conn.closed)

    def test_95_soft_delete_sql_targets_only_regulation_namespace(self):
        _, conn = _runTx([_regPayload()], [{"id": RUN_ID}, {"row_count": 1}])
        updates = [
            (sql, params)
            for kind, sql, params in conn._cursor.sql_log
            if kind == "x" and "SET delete_yn = 1" in sql
        ]
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0][1], (RUN_ID, MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP))

    def test_96_count_distinct_is_not_used_in_regulation_tx(self):
        source = inspect.getsource(repo.step4ReplaceRegulationShadowTracesTx)
        self.assertNotIn("COUNT(DISTINCT", source)

    def test_97_same_sub_issue_multi_regime_rows_are_preserved(self):
        payloads = [
            _regPayload(regime="CSRD", subIssueCode=CSRD_SUB),
            _regPayload(regime="CBAM", subIssueCode=CSRD_SUB),
        ]
        rows = repo._buildRegulationShadowRows(RUN_ID, payloads)
        self.assertEqual(len(rows), 2)
        self.assertEqual([row[3] for row in rows], [CSRD_SUB, CSRD_SUB])
        self.assertEqual(sorted(row[2] for row in rows), ["CBAM", "CSRD"])

    def test_98_same_sub_issue_multi_regime_tx_count_star_two(self):
        payloads = [
            _regPayload(regime="CSRD", subIssueCode=CSRD_SUB),
            _regPayload(regime="CBAM", subIssueCode=CSRD_SUB),
        ]
        result, conn = _runTx(payloads, [{"id": RUN_ID}, {"row_count": 2}])
        self.assertEqual(result, 2)
        self.assertTrue(any("COUNT(*)" in sql for kind, sql, _ in conn._cursor.sql_log))

    def test_99_serializer_failure_skips_getconn(self):
        bad_json = json.dumps(_craftedRegDict() | {"sourceChannel": "benchmark"})
        with patch("src.utils.dmarepository.step4WriteTrace", return_value=bad_json), \
             patch("src.utils.dmarepository.getConn") as get_conn:
            with self.assertRaises(ValueError):
                repo.step4ReplaceRegulationShadowTracesTx(RUN_ID, [{}])
        get_conn.assert_not_called()

    def test_100_happy_path_commits_and_closes(self):
        result, conn = _runTx([_regPayload()], [{"id": RUN_ID}, {"row_count": 1}])
        self.assertEqual(result, 1)
        self.assertTrue(conn.committed)
        self.assertFalse(conn.rolled_back)
        self.assertTrue(conn.closed)


class PhaseC312ServiceHookTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()
        _installMediaServiceImportStubs()
        sys.modules.pop("src.services.medias.service", None)
        self.svc = importlib.import_module("src.services.medias.service")

    def _request(self):
        from src.models.media import MediaNewsCrawlAnalyzeRequest

        return MediaNewsCrawlAnalyzeRequest(
            runId=RUN_ID,
            sources=["naver"],
            dateFrom="2026-01-01",
            dateTo="2026-01-31",
        )

    def _crawlResult(self, articles=None, allowedSources=None, errors=None, sourceBreakdown=None):
        return types.SimpleNamespace(
            articles=articles or [],
            allowedSources=allowedSources or [],
            errors=errors or [],
            sourceBreakdown=sourceBreakdown or [],
            requestedSources=["naver"],
            rejectedSources=[],
            collectedArticleCount=len(articles or []),
            filteredArticleCount=len(articles or []),
        )

    def _patchResponseDeps(self, svc):
        return (
            patch.object(svc, "applySavedSignalCounts", return_value=[]),
            patch.object(svc, "getMediaCoverage", return_value={"coverageStatus": "NO_DATA"}),
            patch.object(svc, "countMediaSubIssues", return_value=0),
            patch.object(svc, "_buildMediaTopIssues", return_value=[]),
        )

    def test_101_news_success_refreshes_regulation_once(self):
        svc = self.svc
        crawl = self._crawlResult(
            articles=["article"],
            allowedSources=["naver"],
            sourceBreakdown=[types.SimpleNamespace(status="SUCCESS")],
        )
        deps = self._patchResponseDeps(svc)
        with patch.object(svc, "crawlNewsArticles", return_value=crawl), \
             patch.object(svc, "runMediaAnalysis", return_value=[]), \
             deps[0], deps[1], deps[2], deps[3], \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0) as refresh, \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun", return_value=0), \
             patch.object(svc, "ensureSurveyFormForRun", return_value=None):
            svc.runMediaCrawlAndAnalyze(self._request())
        refresh.assert_called_once_with(RUN_ID)

    def test_102_news_failed_refreshes_regulation_once(self):
        svc = self.svc
        crawl = self._crawlResult(
            allowedSources=["naver"],
            errors=[{"sourceKey": "naver", "message": "timeout"}],
        )
        deps = self._patchResponseDeps(svc)
        with patch.object(svc, "crawlNewsArticles", return_value=crawl), \
             deps[0], deps[1], deps[2], deps[3], \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0) as refresh, \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun", return_value=0):
            svc.runMediaCrawlAndAnalyze(self._request())
        refresh.assert_called_once_with(RUN_ID)

    def test_103_news_empty_complete_refreshes_regulation_once(self):
        svc = self.svc
        crawl = self._crawlResult(
            allowedSources=["naver"],
            sourceBreakdown=[types.SimpleNamespace(status="SUCCESS")],
        )
        deps = self._patchResponseDeps(svc)
        with patch.object(svc, "crawlNewsArticles", return_value=crawl), \
             patch.object(svc, "_replaceMediaNewsShadowFromPipelineResults"), \
             deps[0], deps[1], deps[2], deps[3], \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0) as refresh, \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun", return_value=0), \
             patch.object(svc, "ensureSurveyFormForRun", return_value=None):
            svc.runMediaCrawlAndAnalyze(self._request())
        refresh.assert_called_once_with(RUN_ID)

    def test_104_regulation_refresh_failure_aborts_external_max(self):
        svc = self.svc
        crawl = self._crawlResult(
            articles=["article"],
            allowedSources=["naver"],
            sourceBreakdown=[types.SimpleNamespace(status="SUCCESS")],
        )
        deps = self._patchResponseDeps(svc)
        with patch.object(svc, "crawlNewsArticles", return_value=crawl), \
             deps[0], deps[1], deps[2], deps[3], \
             patch.object(svc, "runMediaAnalysis", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", side_effect=RuntimeError("broken")), \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun") as ext_max:
            with self.assertRaises(RuntimeError):
                svc.runMediaCrawlAndAnalyze(self._request())
        ext_max.assert_not_called()

    def test_105_kcgs_refresh_failure_aborts_external_max(self):
        svc = self.svc
        crawl = self._crawlResult(
            articles=["article"],
            allowedSources=["naver"],
            sourceBreakdown=[types.SimpleNamespace(status="SUCCESS")],
        )
        deps = self._patchResponseDeps(svc)
        with patch.object(svc, "crawlNewsArticles", return_value=crawl), \
             deps[0], deps[1], deps[2], deps[3], \
             patch.object(svc, "runMediaAnalysis", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(svc, "refreshKcgsShadowForRun", side_effect=RuntimeError("kcgs broken")), \
             patch.object(svc, "refreshMediaExternalMaxForRun") as ext_max:
            with self.assertRaises(RuntimeError):
                svc.runMediaCrawlAndAnalyze(self._request())
        ext_max.assert_not_called()

    def test_106_run_media_analysis_does_not_refresh_regulation(self):
        svc = self.svc
        with patch.object(svc, "processMediaPipeline", return_value=[]), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=[]), \
             patch.object(svc, "_replaceMediaNewsShadowFromPipelineResults"), \
             patch.object(svc, "refreshRegulationShadowForRun") as refresh:
            svc.runMediaAnalysis(articles=[], runId=RUN_ID, shadowReplaceYn=True)
        refresh.assert_not_called()
        self.assertNotIn("refreshRegulationShadowForRun", inspect.getsource(svc.runMediaAnalysis))

    def test_107_refresh_happens_before_response_coverage_read(self):
        svc = self.svc
        call_order = []
        crawl = self._crawlResult()
        with patch.object(svc, "crawlNewsArticles", return_value=crawl), \
             patch.object(svc, "applySavedSignalCounts", return_value=[]), \
             patch.object(svc, "countMediaSubIssues", return_value=0), \
             patch.object(svc, "_buildMediaTopIssues", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", side_effect=lambda runId: call_order.append("refresh")), \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun", return_value=0), \
             patch.object(
                 svc,
                 "getMediaCoverage",
                 side_effect=lambda runId: call_order.append("coverage") or {"coverageStatus": "NO_DATA"},
             ):
            svc.runMediaCrawlAndAnalyze(self._request())
        self.assertEqual(call_order[:2], ["refresh", "coverage"])


class PhaseC312StaticGuardTest(unittest.TestCase):
    def _regulationRuntimeSource(self):
        _installMediaServiceImportStubs()
        sys.modules.pop("src.services.medias.service", None)
        svc = importlib.import_module("src.services.medias.service")
        return "\n".join([
            inspect.getsource(repo.findRegulationRunContext),
            inspect.getsource(repo.listApprovedRegulationInputs),
            inspect.getsource(repo.listApprovedActiveRegulationMappings),
            inspect.getsource(repo._buildRegulationShadowRows),
            inspect.getsource(repo.step4ReplaceRegulationShadowTracesTx),
            inspect.getsource(svc.refreshRegulationShadowForRun),
        ])

    def test_108_regulation_path_does_not_call_recalc_stage(self):
        self.assertNotIn("recalcStage(", self._regulationRuntimeSource())

    def test_109_regulation_path_does_not_call_upsert_stage(self):
        self.assertNotIn("upsertStage(", self._regulationRuntimeSource())

    def test_110_regulation_path_does_not_call_recalc_final(self):
        self.assertNotIn("recalcFinal(", self._regulationRuntimeSource())

    def test_111_regulation_path_does_not_call_update_ranks(self):
        self.assertNotIn("updateRanks(", self._regulationRuntimeSource())

    def test_112_regulation_path_does_not_call_external_max(self):
        self.assertNotIn("externalMax", self._regulationRuntimeSource())

    def test_113_no_regulation_summary_columns_or_dynamic_exec_in_src(self):
        offenders = []
        for py_file in (ROOT / "src").rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            if "regulation_impact_score" in text or "regulation_financial_score" in text:
                offenders.append(str(py_file.relative_to(ROOT)))
        self.assertEqual(offenders, [])
        try:
            result = subprocess.run(
                ["rg", "-n", r"eval\(|exec\(", "backend/src"],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.stdout.strip(), "")
            self.assertIn(result.returncode, (0, 1))
        except FileNotFoundError:
            pass  # rg not available in this environment; skip ripgrep check


if __name__ == "__main__":
    unittest.main()
