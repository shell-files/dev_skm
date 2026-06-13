"""
DMA v1.3 Phase C3.4 media_external External MAX Runtime tests.

Pure unit tests. No live DB, Redis, Kafka, Docker, external API, API router,
frontend, SQL/DDL, or KIS path is exercised.
"""

import copy
import importlib
import inspect
import json
import os
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

import src.utils.dmarepository as repo  # noqa: E402
from src.services.materialities import orchestrator  # noqa: E402
from src.utils.dmarepository import (  # noqa: E402
    MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP,
)
from src.utils.subissuemaster import subissueMaster  # noqa: E402


RUN_ID = 99
E_CODES = sorted(c for c, m in subissueMaster.items() if m.get("domain") == "E")
S_CODES = sorted(c for c, m in subissueMaster.items() if m.get("domain") == "S")
E_CODE = E_CODES[0]
E_CODE2 = E_CODES[1]
S_CODE = S_CODES[0]

NEWS_STEP = MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP
REG_STEP = MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP
KCGS_STEP = MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP
EXT_MAX_STEP = MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP

EXT_MAX_NAMESPACE = "media_external_v13_external_max_shadow"


def _resetPolicies():
    from src.utils import dmaruleregistry as reg
    reg.resetDmaRulesForTest()


def _newsRow(subIssueCode=E_CODE, impactSignal=3.5, financialSignal=4.0, rowId=1):
    return {
        "id": rowId,
        "subIssueCode": subIssueCode,
        "rawIssueLabel": None,
        "sourceStep": NEWS_STEP,
        "sourceType": "news",
        "impactSignal": impactSignal,
        "financialSignal": financialSignal,
    }


def _regRow(subIssueCode=E_CODE, rawIssueLabel="CSRD", impactSignal=3.0, financialSignal=4.0, rowId=2):
    return {
        "id": rowId,
        "subIssueCode": subIssueCode,
        "rawIssueLabel": rawIssueLabel,
        "sourceStep": REG_STEP,
        "sourceType": "regulation",
        "impactSignal": impactSignal,
        "financialSignal": financialSignal,
    }


def _kcgsRow(subIssueCode=E_CODE, impactSignal=3.5, financialSignal=3.5, rowId=3):
    return {
        "id": rowId,
        "subIssueCode": subIssueCode,
        "rawIssueLabel": None,
        "sourceStep": KCGS_STEP,
        "sourceType": "agency",
        "impactSignal": impactSignal,
        "financialSignal": financialSignal,
    }


def _craftedExternalMaxDict(subIssueCode=E_CODE, impactSignal=3.5, financialSignal=4.0):
    return {
        "scorePurpose": "PRESURVEY_SCREENING",
        "sourceChannel": "media_external",
        "subIssueCode": subIssueCode,
        "screeningTrace": [{
            "channel": "external_screening_max",
            "scorePurpose": "PRESURVEY_SCREENING",
            "impactSignal": impactSignal,
            "financialSignal": financialSignal,
            "status": "OBSERVED",
            "capability": None,
            "rawInputs": {
                "additiveYn": False,
                "contributingChannels": ["news_canonical"],
                "impactObservedCount": 1,
                "financialObservedCount": 1,
            },
        }],
    }


def _serializeExternalMaxCrafted(mutator=None, subIssueCode=E_CODE):
    data = _craftedExternalMaxDict(subIssueCode=subIssueCode)
    if mutator:
        mutator(data)
    with patch("src.utils.dmarepository.step4WriteTrace", return_value=json.dumps(data)):
        return repo._buildMediaExternalMaxShadowRows(RUN_ID, [{}])


def _buildPayloads(rows):
    _resetPolicies()
    return orchestrator.step2BuildMediaExternalMaxPayloads(rows)


def _buildOneValidPayload(subIssueCode=E_CODE, impactSignal=3.5, financialSignal=4.0):
    return _buildPayloads([_newsRow(subIssueCode, impactSignal, financialSignal)])[0]


class _TxCursor:
    def __init__(self, conn):
        self.conn = conn
        self.sqlLog = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.sqlLog.append(sql.strip())
        if self.conn.executeError:
            raise self.conn.executeError
        self.conn.executeCalls.append((sql, params))

    def executemany(self, sql, rows):
        self.conn.executemanyCalls.append((sql, list(rows)))

    def fetchone(self):
        lastSql = self.sqlLog[-1] if self.sqlLog else ""
        if "FOR UPDATE" in lastSql:
            return self.conn.lockRow
        if "row_count" in lastSql:
            return {"row_count": self.conn.shadowVerifyCount}
        if "observed_count" in lastSql:
            return {"observed_count": self.conn.observedVerifyCount}
        return None

    def fetchall(self):
        lastSql = self.sqlLog[-1] if self.sqlLog else ""
        if "benchmark_impact_score" in lastSql:
            return list(self.conn.summaryAllRows)
        if "final_score IS NOT NULL" in lastSql:
            return list(self.conn.rankRows)
        return []


class _TxConn:
    def __init__(
        self,
        *,
        lockRow=None,
        shadowVerifyCount=0,
        observedVerifyCount=0,
        executeError=None,
        summaryAllRows=None,
        rankRows=None,
    ):
        self.lockRow = lockRow if lockRow is not None else {"id": RUN_ID}
        self.shadowVerifyCount = shadowVerifyCount
        self.observedVerifyCount = observedVerifyCount
        self.executeError = executeError
        self.summaryAllRows = summaryAllRows or []
        self.rankRows = rankRows or []
        self.autocommit = True
        self.executeCalls = []
        self.executemanyCalls = []
        self.commitCount = 0
        self.rollbackCount = 0
        self.closeCount = 0

    def cursor(self, dictionary=True):
        return _TxCursor(self)

    def commit(self):
        self.commitCount += 1

    def rollback(self):
        self.rollbackCount += 1

    def close(self):
        self.closeCount += 1


def _installMediaServiceImportStubs():
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


# ─── Group 1: Reader ──────────────────────────────────────────────────────────

class ExternalMaxReaderTest(unittest.TestCase):
    def _captureSql(self):
        capture = {}

        def fakeFind(sql, params):
            capture["sql"] = sql
            capture["params"] = params
            return []

        with patch("src.utils.dmarepository._findAllRegulationRowsOrRaise", side_effect=fakeFind):
            repo.listExternalMaxEligibleMediaRows(RUN_ID)
        return capture

    def test_01_sql_contains_canonical_step(self):
        cap = self._captureSql()
        self.assertIn(NEWS_STEP, cap["params"])

    def test_02_sql_contains_regulation_step(self):
        cap = self._captureSql()
        self.assertIn(REG_STEP, cap["params"])

    def test_03_sql_contains_kcgs_step(self):
        cap = self._captureSql()
        self.assertIn(KCGS_STEP, cap["params"])

    def test_04_kis_step_absent_from_params(self):
        cap = self._captureSql()
        for p in cap["params"]:
            self.assertNotIn("kis", str(p).lower())

    def test_05_news_fact_shadow_absent_from_params(self):
        cap = self._captureSql()
        self.assertNotIn("media_external_news_v13_shadow", cap["params"])

    def test_06_sql_filters_delete_yn_zero(self):
        cap = self._captureSql()
        self.assertIn("delete_yn = 0", cap["sql"])

    def test_07_sql_orders_by_sub_issue_code(self):
        cap = self._captureSql()
        self.assertIn("sub_issue_code", cap["sql"].lower())
        self.assertIn("ORDER BY", cap["sql"])

    def test_08_params_starts_with_run_id(self):
        cap = self._captureSql()
        self.assertEqual(cap["params"][0], RUN_ID)

    def test_09_returns_empty_list_on_no_rows(self):
        with patch("src.utils.dmarepository._findAllRegulationRowsOrRaise", return_value=[]):
            self.assertEqual(repo.listExternalMaxEligibleMediaRows(RUN_ID), [])

    def test_10_runtime_error_propagates_from_strict_reader(self):
        with patch(
            "src.utils.dmarepository._findAllRegulationRowsOrRaise",
            side_effect=RuntimeError("db fail"),
        ):
            with self.assertRaises(RuntimeError):
                repo.listExternalMaxEligibleMediaRows(RUN_ID)


# ─── Group 2: External MAX Shadow Serializer ──────────────────────────────────

class ExternalMaxSerializerTest(unittest.TestCase):
    def test_11_valid_payload_produces_one_row(self):
        self.assertEqual(len(_serializeExternalMaxCrafted()), 1)

    def test_12_row_index_0_is_run_id(self):
        row = _serializeExternalMaxCrafted()[0]
        self.assertEqual(row[0], RUN_ID)

    def test_13_row_index_1_is_none(self):
        row = _serializeExternalMaxCrafted()[0]
        self.assertIsNone(row[1])

    def test_14_row_index_2_is_external_screening_max(self):
        row = _serializeExternalMaxCrafted()[0]
        self.assertEqual(row[2], "external_screening_max")

    def test_15_row_index_3_is_sub_issue_code(self):
        row = _serializeExternalMaxCrafted()[0]
        self.assertEqual(row[3], E_CODE)

    def test_16_row_index_4_is_ext_max_source_step(self):
        row = _serializeExternalMaxCrafted()[0]
        self.assertEqual(row[4], EXT_MAX_STEP)

    def test_17_row_index_5_is_external_max_source_type(self):
        row = _serializeExternalMaxCrafted()[0]
        self.assertEqual(row[5], "external_max")

    def test_18_row_index_6_is_impact_signal(self):
        row = _serializeExternalMaxCrafted()[0]
        self.assertEqual(row[6], 3.5)

    def test_19_row_index_7_is_financial_signal(self):
        row = _serializeExternalMaxCrafted()[0]
        self.assertEqual(row[7], 4.0)

    def test_20_row_index_8_is_none(self):
        row = _serializeExternalMaxCrafted()[0]
        self.assertIsNone(row[8])

    def test_21_row_index_9_is_valid_json(self):
        row = _serializeExternalMaxCrafted()[0]
        payload = json.loads(row[9])
        self.assertIn("screeningTrace", payload)


def _makeSerializerRejectTest(name, mutator):
    def test(self):
        with self.assertRaises(ValueError):
            _serializeExternalMaxCrafted(mutator)
    test.__name__ = name
    return test


_EXT_MAX_SERIALIZER_MUTATORS = {
    "test_22_score_purpose_rejected": lambda d: d.update({"scorePurpose": "CANONICAL_IRO"}),
    "test_23_source_channel_rejected": lambda d: d.update({"sourceChannel": "benchmark"}),
    "test_24_missing_sub_issue_rejected": lambda d: d.pop("subIssueCode"),
    "test_25_unknown_sub_issue_rejected": lambda d: d.update({"subIssueCode": "UNKNOWN"}),
    "test_26_screening_trace_not_list_rejected": lambda d: d.update({"screeningTrace": {}}),
    "test_27_empty_screening_trace_rejected": lambda d: d.update({"screeningTrace": []}),
    "test_28_multi_screening_trace_rejected": lambda d: d["screeningTrace"].append(
        copy.deepcopy(d["screeningTrace"][0])
    ),
    "test_29_trace_not_dict_rejected": lambda d: d.update({"screeningTrace": ["bad"]}),
    "test_30_channel_rejected": lambda d: d["screeningTrace"][0].update({"channel": "news_canonical"}),
    "test_31_additive_yn_true_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"additiveYn": True}),
}
for _name, _mutator in _EXT_MAX_SERIALIZER_MUTATORS.items():
    setattr(ExternalMaxSerializerTest, _name, _makeSerializerRejectTest(_name, _mutator))


# ─── Group 3: Builder ─────────────────────────────────────────────────────────

class ExternalMaxBuilderTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()

    def test_32_empty_rows_returns_empty_list(self):
        self.assertEqual(_buildPayloads([]), [])

    def test_33_non_mapping_row_rejected(self):
        with self.assertRaises((ValueError, TypeError, AttributeError)):
            _buildPayloads(["bad"])

    def test_34_missing_sub_issue_code_rejected(self):
        row = _newsRow()
        del row["subIssueCode"]
        with self.assertRaises(ValueError):
            _buildPayloads([row])

    def test_35_unknown_sub_issue_code_rejected(self):
        row = _newsRow()
        row["subIssueCode"] = "INVALID_CODE"
        with self.assertRaises(ValueError):
            _buildPayloads([row])

    def test_36_unknown_source_step_rejected(self):
        row = _newsRow()
        row["sourceStep"] = "media_external_legacy_v12"
        with self.assertRaises(ValueError):
            _buildPayloads([row])

    def test_37_news_canonical_row_produces_one_payload(self):
        payloads = _buildPayloads([_newsRow()])
        self.assertEqual(len(payloads), 1)

    def test_38_news_canonical_trace_channel(self):
        payload = _buildPayloads([_newsRow()])[0]
        traces = [t for t in payload.get("screeningTrace", [])]
        channels = [t["channel"] for t in traces if isinstance(t, dict)]
        self.assertIn("external_screening_max", channels)

    def test_39_regulation_channel_includes_lowercased_label(self):
        payload = _buildPayloads([_regRow(rawIssueLabel="CSRD")])[0]
        contributing = payload["screeningTrace"][0]["rawInputs"]["contributingChannels"]
        self.assertIn("regulation_csrd", contributing)

    def test_40_regulation_label_lowercased_in_channel(self):
        payload = _buildPayloads([_regRow(rawIssueLabel="CBAM")])[0]
        contributing = payload["screeningTrace"][0]["rawInputs"]["contributingChannels"]
        self.assertIn("regulation_cbam", contributing)

    def test_41_kcgs_row_channel_is_domain_signal(self):
        payload = _buildPayloads([_kcgsRow()])[0]
        contributing = payload["screeningTrace"][0]["rawInputs"]["contributingChannels"]
        self.assertIn("kcgs_pillar_domain_signal", contributing)

    def test_42_none_impact_yields_unobserved_when_both_none(self):
        row = _newsRow(impactSignal=None, financialSignal=None)
        payload = _buildPayloads([row])[0]
        trace = payload["screeningTrace"][0]
        self.assertIsNone(trace["impactSignal"])
        self.assertIsNone(trace["financialSignal"])
        self.assertEqual(trace["status"], "UNOBSERVED")

    def test_43_zero_impact_preserved_as_float(self):
        row = _newsRow(impactSignal=0.0, financialSignal=0.0)
        payload = _buildPayloads([row])[0]
        trace = payload["screeningTrace"][0]
        self.assertEqual(trace["impactSignal"], 0.0)
        self.assertEqual(trace["financialSignal"], 0.0)

    def test_44_zero_financial_not_treated_as_none(self):
        row = _newsRow(impactSignal=2.0, financialSignal=0.0)
        payload = _buildPayloads([row])[0]
        trace = payload["screeningTrace"][0]
        self.assertIsNotNone(trace["financialSignal"])

    def test_45_multi_rows_same_sub_issue_produces_one_payload(self):
        rows = [_newsRow(E_CODE), _regRow(E_CODE)]
        payloads = _buildPayloads(rows)
        self.assertEqual(len(payloads), 1)

    def test_46_multi_source_same_sub_issue_has_two_contributing_channels(self):
        rows = [_newsRow(E_CODE), _regRow(E_CODE)]
        payload = _buildPayloads(rows)[0]
        contributing = payload["screeningTrace"][0]["rawInputs"]["contributingChannels"]
        self.assertEqual(len(contributing), 2)

    def test_47_external_max_impact_is_max_of_signals(self):
        rows = [
            _newsRow(E_CODE, impactSignal=2.0, financialSignal=1.0),
            _regRow(E_CODE, impactSignal=4.0, financialSignal=3.0),
        ]
        payload = _buildPayloads(rows)[0]
        self.assertAlmostEqual(payload["screeningTrace"][0]["impactSignal"], 4.0)

    def test_48_external_max_financial_is_max_of_signals(self):
        rows = [
            _newsRow(E_CODE, impactSignal=2.0, financialSignal=5.0),
            _regRow(E_CODE, impactSignal=4.0, financialSignal=3.0),
        ]
        payload = _buildPayloads(rows)[0]
        self.assertAlmostEqual(payload["screeningTrace"][0]["financialSignal"], 5.0)

    def test_49_multi_sub_issues_produce_multiple_payloads(self):
        rows = [_newsRow(E_CODE), _newsRow(E_CODE2)]
        self.assertEqual(len(_buildPayloads(rows)), 2)

    def test_50_output_sorted_by_sub_issue_code_asc(self):
        rows = [_newsRow(E_CODE2), _newsRow(E_CODE)]
        payloads = _buildPayloads(rows)
        codes = [p["subIssueCode"] for p in payloads]
        self.assertEqual(codes, sorted(codes))

    def test_51_all_none_signals_yield_none_external_max(self):
        rows = [
            _newsRow(E_CODE, impactSignal=None, financialSignal=None),
            _regRow(E_CODE, impactSignal=None, financialSignal=None),
        ]
        payload = _buildPayloads(rows)[0]
        trace = payload["screeningTrace"][0]
        self.assertIsNone(trace["impactSignal"])
        self.assertIsNone(trace["financialSignal"])

    def test_52_kcgs_raw_inputs_has_provider_key(self):
        row = _kcgsRow()
        payload = _buildPayloads([row])[0]
        contributing = payload["screeningTrace"][0]["rawInputs"]["contributingChannels"]
        self.assertIn("kcgs_pillar_domain_signal", contributing)

    def test_53_output_payload_source_channel_is_media_external(self):
        payload = _buildPayloads([_newsRow()])[0]
        self.assertEqual(payload["sourceChannel"], "media_external")

    def test_54_output_payload_score_purpose_is_presurvey(self):
        payload = _buildPayloads([_newsRow()])[0]
        self.assertEqual(payload["scorePurpose"], "PRESURVEY_SCREENING")

    def test_55_output_payload_has_sub_issue_code(self):
        payload = _buildPayloads([_newsRow(E_CODE)])[0]
        self.assertEqual(payload["subIssueCode"], E_CODE)

    def test_56_kcgs_and_news_same_sub_issue_produces_one_payload(self):
        rows = [_newsRow(E_CODE, impactSignal=2.0), _kcgsRow(E_CODE, impactSignal=3.5)]
        payloads = _buildPayloads(rows)
        self.assertEqual(len(payloads), 1)

    def test_57_three_sources_same_sub_issue_impact_max(self):
        rows = [
            _newsRow(E_CODE, impactSignal=2.0, financialSignal=1.0),
            _regRow(E_CODE, impactSignal=3.0, financialSignal=2.0),
            _kcgsRow(E_CODE, impactSignal=3.5, financialSignal=3.5),
        ]
        payload = _buildPayloads(rows)[0]
        self.assertAlmostEqual(payload["screeningTrace"][0]["impactSignal"], 3.5)
        self.assertAlmostEqual(payload["screeningTrace"][0]["financialSignal"], 3.5)

    def test_58_news_partial_none_impact_max_uses_reg(self):
        rows = [
            _newsRow(E_CODE, impactSignal=None, financialSignal=4.0),
            _regRow(E_CODE, impactSignal=3.0, financialSignal=None),
        ]
        payload = _buildPayloads(rows)[0]
        trace = payload["screeningTrace"][0]
        self.assertAlmostEqual(trace["impactSignal"], 3.0)
        self.assertAlmostEqual(trace["financialSignal"], 4.0)

    def test_97_news_row_wrong_source_type_rejected(self):
        row = _newsRow()
        row["sourceType"] = "agency"
        with self.assertRaises(ValueError):
            _buildPayloads([row])

    def test_98_regulation_row_wrong_source_type_rejected(self):
        row = _regRow()
        row["sourceType"] = "news"
        with self.assertRaises(ValueError):
            _buildPayloads([row])

    def test_99_kcgs_row_wrong_source_type_rejected(self):
        row = _kcgsRow()
        row["sourceType"] = "regulation"
        with self.assertRaises(ValueError):
            _buildPayloads([row])


# ─── Group 4: Transaction ─────────────────────────────────────────────────────

class ExternalMaxTxTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()

    def test_59_duplicate_sub_issue_codes_rejected_before_db(self):
        payload = _buildOneValidPayload()
        with patch("src.utils.dmarepository.getConn") as mockGetConn:
            with self.assertRaises(ValueError):
                repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [payload, payload])
        mockGetConn.assert_not_called()

    def test_60_empty_payloads_commits(self):
        conn = _TxConn(shadowVerifyCount=0, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        self.assertEqual(conn.commitCount, 1)

    def test_61_empty_payloads_returns_zero(self):
        conn = _TxConn(shadowVerifyCount=0, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            result = repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        self.assertEqual(result, 0)

    def test_62_autocommit_disabled(self):
        conn = _TxConn(shadowVerifyCount=0, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        self.assertFalse(conn.autocommit)

    def test_63_soft_delete_executed(self):
        conn = _TxConn(shadowVerifyCount=0, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        soft_delete_found = any(
            "delete_yn = 1" in str(sql) for sql, _ in conn.executeCalls
        )
        self.assertTrue(soft_delete_found)

    def test_64_shadow_insert_via_executemany_on_non_empty(self):
        payload = _buildOneValidPayload()
        conn = _TxConn(shadowVerifyCount=1, observedVerifyCount=1)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [payload])
        self.assertTrue(len(conn.executemanyCalls) >= 1)
        insert_found = any(
            "INSERT INTO ESG_DMA_SIGNAL_DETAIL" in str(sql)
            for sql, _ in conn.executemanyCalls
        )
        self.assertTrue(insert_found)

    def test_65_summary_null_clear_executed(self):
        conn = _TxConn(shadowVerifyCount=0, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        null_clear_found = any(
            "media_external_impact_score = NULL" in str(sql)
            or "media_external_impact_score = NULL" in str(sql)
            for sql, _ in conn.executeCalls
        )
        self.assertTrue(null_clear_found)

    def test_66_summary_upsert_executed_on_non_empty(self):
        payload = _buildOneValidPayload()
        conn = _TxConn(shadowVerifyCount=1, observedVerifyCount=1)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [payload])
        upsert_found = any(
            "ON DUPLICATE KEY UPDATE" in str(sql)
            for sql, _ in conn.executemanyCalls
        )
        self.assertTrue(upsert_found)

    def test_67_rank_no_null_reset_executed(self):
        conn = _TxConn(shadowVerifyCount=0, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        rank_null_found = any(
            "rank_no = NULL" in str(sql) for sql, _ in conn.executeCalls
        )
        self.assertTrue(rank_null_found)

    def test_68_final_score_recalculated_when_summary_row_exists(self):
        payload = _buildOneValidPayload()
        summary_row = {
            "sub_issue_code": E_CODE,
            "benchmark_impact_score": None,
            "benchmark_financial_score": None,
            "media_external_impact_score": 3.5,
            "media_external_financial_score": 4.0,
            "survey_impact_score": None,
            "survey_financial_score": None,
            "context_impact_modifier": None,
            "context_financial_modifier": None,
        }
        conn = _TxConn(
            shadowVerifyCount=1,
            observedVerifyCount=1,
            summaryAllRows=[summary_row],
        )
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [payload])
        final_update_found = any(
            "final_score = ?" in str(sql) for sql, _ in conn.executeCalls
        )
        self.assertTrue(final_update_found)

    def test_69_missing_run_raises_runtime_and_rollbacks(self):
        conn = _TxConn(lockRow=None)
        conn.lockRow = None
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        self.assertEqual(conn.commitCount, 0)
        self.assertEqual(conn.rollbackCount, 1)

    def test_70_shadow_count_mismatch_rollbacks(self):
        payload = _buildOneValidPayload()
        conn = _TxConn(shadowVerifyCount=0, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [payload])
        self.assertEqual(conn.rollbackCount, 1)

    def test_71_observed_count_mismatch_rollbacks(self):
        payload = _buildOneValidPayload()
        conn = _TxConn(shadowVerifyCount=1, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [payload])
        self.assertEqual(conn.rollbackCount, 1)

    def test_72_execute_error_triggers_rollback(self):
        conn = _TxConn(executeError=RuntimeError("db error"))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(Exception):
                repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        self.assertEqual(conn.rollbackCount, 1)

    def test_73_close_called_on_success(self):
        conn = _TxConn(shadowVerifyCount=0, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        self.assertEqual(conn.closeCount, 1)

    def test_74_close_called_on_failure(self):
        conn = _TxConn(lockRow=None)
        conn.lockRow = None
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        self.assertEqual(conn.closeCount, 1)

    def test_75_success_commits_exactly_once(self):
        conn = _TxConn(shadowVerifyCount=0, observedVerifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])
        self.assertEqual(conn.commitCount, 1)
        self.assertEqual(conn.rollbackCount, 0)

    def test_76_returns_shadow_row_count(self):
        payload = _buildOneValidPayload()
        conn = _TxConn(shadowVerifyCount=1, observedVerifyCount=1)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            result = repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [payload])
        self.assertEqual(result, 1)

    def test_77_get_conn_none_raises_runtime_error(self):
        with patch("src.utils.dmarepository.getConn", return_value=None):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [])

    def test_78_invalid_payload_raises_before_get_conn(self):
        bad = _craftedExternalMaxDict()
        bad["scorePurpose"] = "CANONICAL_IRO"
        with patch("src.utils.dmarepository.step4WriteTrace", return_value=json.dumps(bad)):
            with patch("src.utils.dmarepository.getConn") as mockGetConn:
                with self.assertRaises(ValueError):
                    repo.step4ReplaceMediaExternalMaxShadowAndSummaryTx(RUN_ID, [{}])
        mockGetConn.assert_not_called()


# ─── Group 5: Service ─────────────────────────────────────────────────────────

class ExternalMaxServiceTest(unittest.TestCase):
    def setUp(self):
        _installMediaServiceImportStubs()
        self.service = importlib.import_module("src.services.medias.service")

    def test_79_refresh_wires_reader_builder_writer(self):
        rows = [_newsRow()]
        payloads = [{"ok": True}]
        with patch.object(self.service, "listExternalMaxEligibleMediaRows", return_value=rows) as reader:
            with patch.object(self.service, "step2BuildMediaExternalMaxPayloads", return_value=payloads) as builder:
                with patch.object(self.service, "step4ReplaceMediaExternalMaxShadowAndSummaryTx", return_value=1) as writer:
                    result = self.service.refreshMediaExternalMaxForRun(RUN_ID)
        self.assertEqual(result, 1)
        reader.assert_called_once_with(RUN_ID)
        builder.assert_called_once_with(rows)
        writer.assert_called_once_with(RUN_ID, payloads)

    def test_80_crawl_hook_order_kcgs_before_external_max(self):
        source = inspect.getsource(self.service.runMediaCrawlAndAnalyze)
        self.assertLess(
            source.index("refreshKcgsShadowForRun"),
            source.index("refreshMediaExternalMaxForRun"),
        )

    def test_81_crawl_hook_contains_external_max_call(self):
        source = inspect.getsource(self.service.runMediaCrawlAndAnalyze)
        self.assertIn("refreshMediaExternalMaxForRun", source)

    def test_82_critical_path_comment_is_present(self):
        source = inspect.getsource(self.service.runMediaCrawlAndAnalyze)
        self.assertIn("critical path", source)
        crit_idx = source.index("critical path")
        max_idx = source.index("refreshMediaExternalMaxForRun")
        self.assertLess(crit_idx, max_idx)

    def test_83_runtime_error_propagates_from_refresh(self):
        with patch.object(
            self.service, "listExternalMaxEligibleMediaRows", side_effect=RuntimeError("db fail")
        ):
            with self.assertRaises(RuntimeError):
                self.service.refreshMediaExternalMaxForRun(RUN_ID)

    def test_84_refresh_called_once_per_run_id(self):
        with patch.object(self.service, "listExternalMaxEligibleMediaRows", return_value=[]) as reader:
            with patch.object(self.service, "step2BuildMediaExternalMaxPayloads", return_value=[]):
                with patch.object(self.service, "step4ReplaceMediaExternalMaxShadowAndSummaryTx", return_value=0):
                    self.service.refreshMediaExternalMaxForRun(RUN_ID)
        self.assertEqual(reader.call_count, 1)

    def test_85_not_in_run_media_analysis(self):
        source = inspect.getsource(self.service.runMediaAnalysis)
        self.assertNotIn("refreshMediaExternalMaxForRun", source)

    def test_86_service_imports_all_three_components(self):
        import src.services.medias.service as svc_module
        source = inspect.getsource(svc_module)
        self.assertIn("listExternalMaxEligibleMediaRows", source)
        self.assertIn("step2BuildMediaExternalMaxPayloads", source)
        self.assertIn("step4ReplaceMediaExternalMaxShadowAndSummaryTx", source)


# ─── Group 6: Static Inventory ────────────────────────────────────────────────

class ExternalMaxStaticInventoryTest(unittest.TestCase):
    def test_87_ext_max_step_in_repository_all(self):
        self.assertIn("MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP", repo.__all__)

    def test_88_list_eligible_rows_in_repository_all(self):
        self.assertIn("listExternalMaxEligibleMediaRows", repo.__all__)

    def test_89_step4_tx_in_repository_all(self):
        self.assertIn("step4ReplaceMediaExternalMaxShadowAndSummaryTx", repo.__all__)

    def test_90_step2_builder_in_orchestrator_all(self):
        self.assertIn("step2BuildMediaExternalMaxPayloads", orchestrator.__all__)

    def test_91_ext_max_namespace_literal_declared_once_in_src(self):
        matches = []
        for path in (ROOT / "src").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if EXT_MAX_NAMESPACE in text:
                matches.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(matches, ["src/utils/dmarepository.py"])

    def test_92_no_api_frontend_or_sql_diff(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "--", "backend/src/apis", "frontend", "*.sql"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_93_kis_namespace_absent_from_eligible_sql(self):
        capture = {}

        def fakeFind(sql, params):
            capture["sql"] = sql
            capture["params"] = params
            return []

        with patch("src.utils.dmarepository._findAllRegulationRowsOrRaise", side_effect=fakeFind):
            repo.listExternalMaxEligibleMediaRows(RUN_ID)
        for p in capture["params"]:
            self.assertNotIn("kis", str(p).lower())

    def test_94_news_fact_shadow_absent_from_eligible_sql(self):
        capture = {}

        def fakeFind(sql, params):
            capture["sql"] = sql
            capture["params"] = params
            return []

        with patch("src.utils.dmarepository._findAllRegulationRowsOrRaise", side_effect=fakeFind):
            repo.listExternalMaxEligibleMediaRows(RUN_ID)
        self.assertNotIn("media_external_news_v13_shadow", capture["params"])
        for p in capture["params"]:
            self.assertNotEqual(p, "media_external_news_v13_shadow")

    def test_95_tx_does_not_use_legacy_recalc_or_rank_helpers(self):
        source = Path(ROOT, "src/utils/dmarepository.py").read_text(encoding="utf-8")
        start = source.index("def step4ReplaceMediaExternalMaxShadowAndSummaryTx")
        end = source.index("def step4ReadTrace")
        block = source[start:end]
        for forbidden in ("recalcStage(", "upsertStage(", "recalcFinal(", "updateRanks("):
            self.assertNotIn(forbidden, block)

    def test_96_orchestrator_externalmax_branch_uses_calc_final_aggregation(self):
        source = Path(ROOT, "src/services/materialities/orchestrator.py").read_text(encoding="utf-8")
        ext_start = source.index('if normalizedChannel == "externalMax":')
        survey_start = source.index('if normalizedChannel == "surveyOverlay":')
        ext_branch = source[ext_start:survey_start]
        self.assertIn("step2CalcExternalMax", ext_branch)
        self.assertNotIn("calcFinal", ext_branch)
        self.assertNotIn("updateRanks", ext_branch)


# ─── Group 7: P0 Snapshot-Mixing Gate ────────────────────────────────────────

class ExternalMaxGateTest(unittest.TestCase):
    """Verify source-shadow refresh failures and news freshness gate block External MAX execution."""

    def setUp(self):
        _installMediaServiceImportStubs()
        self.service = importlib.import_module("src.services.medias.service")

    def _request(self):
        return types.SimpleNamespace(
            runId=RUN_ID,
            dateFrom="2025-01-01",
            dateTo="2025-01-31",
            sources=["naver"],
        )

    def _crawlResult(self):
        """Partial/failed crawl — crawlCompleteYn=False."""
        return types.SimpleNamespace(
            articles=[],
            requestedSources=[],
            allowedSources=[],
            rejectedSources=[],
            collectedArticleCount=0,
            filteredArticleCount=0,
            errors=[],
            sourceBreakdown=[],
        )

    def _completeCrawlResult(self):
        """Successful complete crawl with articles — crawlCompleteYn=True."""
        return types.SimpleNamespace(
            articles=["article"],
            requestedSources=["naver"],
            allowedSources=["naver"],
            rejectedSources=[],
            collectedArticleCount=1,
            filteredArticleCount=1,
            errors=[],
            sourceBreakdown=[types.SimpleNamespace(status="SUCCESS")],
        )

    def _patchResponseDeps(self, svc):
        return (
            patch.object(svc, "applySavedSignalCounts", return_value=[]),
            patch.object(svc, "getMediaCoverage", return_value={"coverageStatus": "NO_DATA"}),
            patch.object(svc, "countMediaSubIssues", return_value=0),
            patch.object(svc, "_buildMediaTopIssues", return_value=[]),
        )

    def test_100_regulation_failure_gates_external_max(self):
        svc = self.service
        with patch.object(svc, "crawlNewsArticles", return_value=self._completeCrawlResult()), \
             patch.object(svc, "runMediaAnalysis", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", side_effect=RuntimeError("db")), \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun") as ext_max:
            with self.assertRaises(RuntimeError):
                svc.runMediaCrawlAndAnalyze(self._request())
        ext_max.assert_not_called()

    def test_101_kcgs_failure_gates_external_max(self):
        svc = self.service
        with patch.object(svc, "crawlNewsArticles", return_value=self._completeCrawlResult()), \
             patch.object(svc, "runMediaAnalysis", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(svc, "refreshKcgsShadowForRun", side_effect=RuntimeError("kcgs db")), \
             patch.object(svc, "refreshMediaExternalMaxForRun") as ext_max:
            with self.assertRaises(RuntimeError):
                svc.runMediaCrawlAndAnalyze(self._request())
        ext_max.assert_not_called()

    def test_102_both_failures_error_message_contains_both_keys(self):
        svc = self.service
        with patch.object(svc, "crawlNewsArticles", return_value=self._completeCrawlResult()), \
             patch.object(svc, "runMediaAnalysis", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", side_effect=RuntimeError("reg fail")), \
             patch.object(svc, "refreshKcgsShadowForRun", side_effect=RuntimeError("kcgs fail")), \
             patch.object(svc, "refreshMediaExternalMaxForRun"):
            try:
                svc.runMediaCrawlAndAnalyze(self._request())
                self.fail("Expected RuntimeError")
            except RuntimeError as exc:
                self.assertIn("regulation", str(exc))
                self.assertIn("kcgs", str(exc))

    def test_103_both_source_refresh_success_calls_external_max(self):
        svc = self.service
        deps = self._patchResponseDeps(svc)
        with patch.object(svc, "crawlNewsArticles", return_value=self._completeCrawlResult()), \
             deps[0], deps[1], deps[2], deps[3], \
             patch.object(svc, "runMediaAnalysis", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun", return_value=0) as ext_max:
            svc.runMediaCrawlAndAnalyze(self._request())
        ext_max.assert_called_once_with(RUN_ID)

    def test_104_partial_crawl_skips_external_max_response_returned(self):
        svc = self.service
        deps = self._patchResponseDeps(svc)
        with patch.object(svc, "crawlNewsArticles", return_value=self._crawlResult()), \
             deps[0], deps[1], deps[2], deps[3], \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun") as ext_max:
            result = svc.runMediaCrawlAndAnalyze(self._request())
        ext_max.assert_not_called()
        self.assertIsNotNone(result)

    def test_105_news_replace_failure_on_complete_crawl_blocks_external_max(self):
        svc = self.service
        with patch.object(svc, "crawlNewsArticles", return_value=self._completeCrawlResult()), \
             patch.object(svc, "processMediaPipeline", return_value=[]), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=[]), \
             patch.object(svc, "_replaceMediaNewsShadowFromPipelineResults",
                          side_effect=RuntimeError("news shadow db error")), \
             patch.object(svc, "refreshMediaExternalMaxForRun") as ext_max:
            with self.assertRaises(RuntimeError):
                svc.runMediaCrawlAndAnalyze(self._request())
        ext_max.assert_not_called()

    def test_106_news_empty_clear_failure_on_complete_crawl_blocks_external_max(self):
        svc = self.service
        empty_complete = types.SimpleNamespace(
            articles=[],
            requestedSources=["naver"],
            allowedSources=["naver"],
            rejectedSources=[],
            collectedArticleCount=0,
            filteredArticleCount=0,
            errors=[],
            sourceBreakdown=[types.SimpleNamespace(status="SUCCESS")],
        )
        with patch.object(svc, "crawlNewsArticles", return_value=empty_complete), \
             patch.object(svc, "_replaceMediaNewsShadowFromPipelineResults",
                          side_effect=RuntimeError("empty clear failed")), \
             patch.object(svc, "refreshMediaExternalMaxForRun") as ext_max:
            with self.assertRaises(RuntimeError):
                svc.runMediaCrawlAndAnalyze(self._request())
        ext_max.assert_not_called()


if __name__ == "__main__":
    unittest.main()
