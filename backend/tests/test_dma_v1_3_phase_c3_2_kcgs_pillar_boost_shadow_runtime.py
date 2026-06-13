"""
DMA v1.3 Phase C3.2 KCGS pillar boost shadow runtime tests.

Pure unit tests. No live DB, Redis, Kafka, Docker, external API, API router,
frontend, SQL/DDL, KIS, externalMax, Summary, Rank, or final_score path is
exercised.
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

import src.utils.dmaruleregistry as reg  # noqa: E402
import src.utils.dmarepository as repo  # noqa: E402
from src.services.materialities import orchestrator  # noqa: E402
from src.utils import dmascoring as sc  # noqa: E402
from src.utils.dmarepository import (  # noqa: E402
    MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP,
)
from src.utils.subissuemaster import subissueMaster  # noqa: E402


RUN_ID = 77
COMPANY_ID = 1001
KCGS_NAMESPACE = "media_external_agency_kcgs_v13_shadow"

DOMAIN_CODES = {
    pillar: sorted(code for code, meta in subissueMaster.items() if meta.get("domain") == pillar)
    for pillar in ("E", "S", "G")
}
DOMAIN_COUNTS = {pillar: len(codes) for pillar, codes in DOMAIN_CODES.items()}
TOTAL_DOMAIN_COUNT = sum(DOMAIN_COUNTS.values())
E_CODE = DOMAIN_CODES["E"][0]
S_CODE = DOMAIN_CODES["S"][0]
G_CODE = DOMAIN_CODES["G"][0]


def _resetPolicies():
    reg.resetDmaRulesForTest()


def _approvedRows(
    *,
    companyId=COMPANY_ID,
    years=(2024, 2025, 2026),
    reviewStatus="APPROVED",
    inputSourceType="MANUAL",
):
    rows = []
    grades = [
        ("A", "A", "A", "B+"),
        ("A", "B+", "A", "B"),
        ("B+", "B", "A+", "C"),
    ]
    for idx, year in enumerate(years):
        overallGrade, environmentGrade, socialGrade, governanceGrade = grades[idx]
        rows.append({
            "companyId": companyId,
            "ratingYear": year,
            "overallGrade": overallGrade,
            "environmentGrade": environmentGrade,
            "socialGrade": socialGrade,
            "governanceGrade": governanceGrade,
            "inputSourceType": inputSourceType,
            "sourceDocumentRef": f"kcgs-{year}.pdf",
            "reviewStatus": reviewStatus,
        })
    return rows


def _buildPayloads(rows=None):
    _resetPolicies()
    return orchestrator.step2BuildKcgsPillarBoostPayloads(rows or _approvedRows())


def _firstByPillar(payloads, pillar):
    for payload in payloads:
        trace = payload["screeningTrace"][0]
        if trace["rawInputs"]["pillar"] == pillar:
            return payload
    raise AssertionError(f"pillar not found: {pillar}")


def _trace(payload):
    return payload["screeningTrace"][0]


def _raw(payload):
    return _trace(payload)["rawInputs"]


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


def _craftedKcgsDict(subIssueCode=E_CODE, pillar="E"):
    return {
        "scorePurpose": "PRESURVEY_SCREENING",
        "sourceChannel": "media_external",
        "subIssueCode": subIssueCode,
        "screeningTrace": [{
            "channel": "kcgs_pillar_boost",
            "scorePurpose": "PRESURVEY_SCREENING",
            "impactSignal": None,
            "financialSignal": None,
            "status": "OBSERVED",
            "capability": "READY",
            "rawInputs": {
                "sourceStep": "media_external",
                "sourceType": "agency",
                "providerKey": "kcgs",
                "companyId": COMPANY_ID,
                "ratingYears": [2024, 2025, 2026],
                "overallGradeHistory": [
                    {"ratingYear": 2024, "grade": "A"},
                    {"ratingYear": 2025, "grade": "A"},
                    {"ratingYear": 2026, "grade": "B+"},
                ],
                "pillar": pillar,
                "pillarGradeHistory": [
                    {"ratingYear": 2024, "grade": "A"},
                    {"ratingYear": 2025, "grade": "B+"},
                    {"ratingYear": 2026, "grade": "B"},
                ],
                "previousGrade": "B+",
                "latestGrade": "B",
                "trend": "downgradeOne",
                "stepDifference": 1,
                "gradeRisk": 3.0,
                "trendModifier": 0.5,
                "pillarSignal": 3.5,
                "subIssueBoost": 0.7,
                "propagationMode": "ALL_SUB_ISSUES_IN_PILLAR_DOMAIN",
                "overallGradeTraceOnlyYn": True,
                "externalMaxEligibleYn": False,
                "top20BoostOnlyYn": True,
                "directCanonicalFinalAllowedYn": False,
            },
        }],
    }


def _serializeCrafted(mutator=None, *, subIssueCode=E_CODE, pillar="E"):
    data = _craftedKcgsDict(subIssueCode=subIssueCode, pillar=pillar)
    if mutator:
        mutator(data)
    with patch("src.utils.dmarepository.step4WriteTrace", return_value=json.dumps(data)):
        return repo._buildKcgsShadowRows(RUN_ID, [{}])


class _TxCursor:
    def __init__(self, conn):
        self.conn = conn
        self.sqlLog = []
        self.paramsLog = []

    def __enter__(self):
        return self

    def __exit__(self, excType, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.sqlLog.append(sql.strip())
        self.paramsLog.append(params)
        if self.conn.executeError:
            raise self.conn.executeError
        self.conn.executeCalls.append((sql, params))

    def executemany(self, sql, rows):
        self.conn.executemanyCalls.append((sql, list(rows)))

    def fetchone(self):
        lastSql = self.sqlLog[-1] if self.sqlLog else ""
        if "FOR UPDATE" in lastSql:
            return self.conn.lockRow
        if "COUNT(*) AS row_count" in lastSql:
            return {"row_count": self.conn.verifyCount}
        return None


class _TxConn:
    def __init__(self, *, lockRow=None, verifyCount=0, executeError=None):
        self.lockRow = lockRow if lockRow is not None else {"id": RUN_ID}
        self.verifyCount = verifyCount
        self.executeError = executeError
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


class KcgsPolicyValidationTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()

    def policy(self):
        return reg.getPolicy("screening_policy")

    def test_01_policy_validator_accepts_baseline(self):
        reg.validateKcgsScreeningPolicy(self.policy())

    def test_02_policy_metadata_present(self):
        kcgs = self.policy()["kcgs"]
        self.assertEqual(kcgs["gradeOrderBestToWorst"], ["S", "A+", "A", "B+", "B", "C", "D"])
        self.assertEqual(kcgs["pillars"], ["E", "S", "G"])
        self.assertFalse(kcgs["externalMaxEligibleYn"])
        self.assertTrue(kcgs["top20BoostOnlyYn"])


def _makePolicyValidatorTest(name, mutator):
    def test(self):
        _resetPolicies()
        policy = reg.getPolicy("screening_policy")
        broken = copy.deepcopy(policy)
        mutator(broken)
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateKcgsScreeningPolicy(broken)
    test.__name__ = name
    return test


_POLICY_MUTATORS = {
    "test_03_missing_kcgs_rejected": lambda p: p.pop("kcgs"),
    "test_04_grade_order_rejected": lambda p: p["kcgs"].update({"gradeOrderBestToWorst": ["A", "S"]}),
    "test_05_missing_grade_risk_rejected": lambda p: p["kcgs"].pop("gradeRisk"),
    "test_06_grade_risk_key_mismatch_rejected": lambda p: p["kcgs"]["gradeRisk"].pop("D"),
    "test_07_missing_trend_modifier_rejected": lambda p: p["kcgs"].pop("trendModifier"),
    "test_08_missing_trend_key_rejected": lambda p: p["kcgs"]["trendModifier"].pop("flat"),
    "test_09_insufficient_data_sentinel_rejected": lambda p: p["kcgs"]["trendModifier"].update({"insufficientData": None}),
    "test_10_pillars_rejected": lambda p: p["kcgs"].update({"pillars": ["E", "S"]}),
    "test_11_propagation_mode_rejected": lambda p: p["kcgs"].update({"propagationMode": "DIRECT"}),
    "test_12_overall_trace_flag_rejected": lambda p: p["kcgs"].update({"overallGradeTraceOnlyYn": False}),
    "test_13_external_max_flag_rejected": lambda p: p["kcgs"].update({"externalMaxEligibleYn": True}),
    "test_14_top20_flag_rejected": lambda p: p["kcgs"].update({"top20BoostOnlyYn": False}),
    "test_15_direct_canonical_flag_rejected": lambda p: p["kcgs"].update({"directCanonicalFinalAllowedYn": True}),
    "test_16_pillar_signal_max_rejected": lambda p: p["kcgs"].update({"pillarSignalMax": 4.0}),
    "test_17_max_boost_rejected": lambda p: p["kcgs"].update({"maxSubIssueBoost": 2.0}),
    "test_18_boost_multiplier_rejected": lambda p: p["kcgs"].update({"boostMultiplier": 0.25}),
}
for _name, _mutator in _POLICY_MUTATORS.items():
    setattr(KcgsPolicyValidationTest, _name, _makePolicyValidatorTest(_name, _mutator))


class KcgsTrendResolverTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()
        self.policy = reg.getPolicy("screening_policy")

    def assertTrend(self, previousGrade, latestGrade, expectedTrend, expectedDiff):
        result = sc.step2ResolveKcgsTrend(previousGrade, latestGrade, self.policy)
        self.assertEqual(result["trend"], expectedTrend)
        self.assertEqual(result["stepDifference"], expectedDiff)

    def test_19_flat(self):
        self.assertTrend("B", "B", "flat", 0)

    def test_20_downgrade_one(self):
        self.assertTrend("B+", "B", "downgradeOne", 1)

    def test_21_downgrade_two_or_more(self):
        self.assertTrend("A+", "B", "downgradeTwoOrMore", 3)

    def test_22_upgrade(self):
        self.assertTrend("C", "B", "upgrade", -1)

    def test_23_unknown_previous_rejected(self):
        with self.assertRaises(ValueError):
            sc.step2ResolveKcgsTrend("Z", "B", self.policy)

    def test_24_unknown_latest_rejected(self):
        with self.assertRaises(ValueError):
            sc.step2ResolveKcgsTrend("B", "Z", self.policy)


class KcgsBuilderTest(unittest.TestCase):
    def setUp(self):
        _resetPolicies()

    def test_25_empty_rows_empty_clear(self):
        self.assertEqual(orchestrator.step2BuildKcgsPillarBoostPayloads([]), [])

    def test_26_draft_reviewed_rows_empty_clear(self):
        rows = _approvedRows(reviewStatus="DRAFT") + _approvedRows(reviewStatus="REVIEWED")
        self.assertEqual(orchestrator.step2BuildKcgsPillarBoostPayloads(rows), [])

    def test_27_exact_three_approved_builds_domain_universe(self):
        self.assertEqual(len(_buildPayloads()), TOTAL_DOMAIN_COUNT)

    def test_28_payloads_are_media_external_shadow_metadata(self):
        payload = _buildPayloads()[0]
        self.assertEqual(payload["sourceChannel"], "media_external")
        self.assertEqual(payload["scorePurpose"], "PRESURVEY_SCREENING")
        self.assertIsNone(_trace(payload)["impactSignal"])
        self.assertIsNone(_trace(payload)["financialSignal"])

    def test_29_payload_counts_match_pillar_domains(self):
        payloads = _buildPayloads()
        counts = {"E": 0, "S": 0, "G": 0}
        for payload in payloads:
            counts[_raw(payload)["pillar"]] += 1
        self.assertEqual(counts, DOMAIN_COUNTS)

    def test_30_e_pillar_trend_and_boost(self):
        raw = _raw(_firstByPillar(_buildPayloads(), "E"))
        self.assertEqual(raw["trend"], "downgradeOne")
        self.assertEqual(raw["stepDifference"], 1)
        self.assertEqual(raw["latestGrade"], "B")
        self.assertAlmostEqual(raw["pillarSignal"], 3.5)
        self.assertAlmostEqual(raw["subIssueBoost"], 0.7)

    def test_31_s_pillar_upgrade_trace_only(self):
        raw = _raw(_firstByPillar(_buildPayloads(), "S"))
        self.assertEqual(raw["trend"], "upgrade")
        self.assertEqual(raw["latestGrade"], "A+")
        self.assertAlmostEqual(raw["subIssueBoost"], 0.1)

    def test_32_g_pillar_downgrade_trace(self):
        raw = _raw(_firstByPillar(_buildPayloads(), "G"))
        self.assertEqual(raw["trend"], "downgradeOne")
        self.assertEqual(raw["latestGrade"], "C")
        self.assertAlmostEqual(raw["subIssueBoost"], 0.9)

    def test_33_history_metadata_is_preserved(self):
        raw = _raw(_buildPayloads()[0])
        self.assertEqual(raw["ratingYears"], [2024, 2025, 2026])
        self.assertEqual(len(raw["overallGradeHistory"]), 3)
        self.assertEqual(len(raw["pillarGradeHistory"]), 3)
        self.assertEqual(len(raw["sourceDocumentRefs"]), 3)

    def test_34_policy_metadata_flags_are_preserved(self):
        raw = _raw(_buildPayloads()[0])
        self.assertEqual(raw["propagationMode"], "ALL_SUB_ISSUES_IN_PILLAR_DOMAIN")
        self.assertTrue(raw["overallGradeTraceOnlyYn"])
        self.assertFalse(raw["externalMaxEligibleYn"])
        self.assertTrue(raw["top20BoostOnlyYn"])
        self.assertFalse(raw["directCanonicalFinalAllowedYn"])

    def test_35_partial_one_approved_rejected(self):
        with self.assertRaises(ValueError):
            orchestrator.step2BuildKcgsPillarBoostPayloads(_approvedRows()[:1])

    def test_36_partial_two_approved_rejected(self):
        with self.assertRaises(ValueError):
            orchestrator.step2BuildKcgsPillarBoostPayloads(_approvedRows()[:2])

    def test_37_four_approved_rejected(self):
        rows = _approvedRows() + [_approvedRows(years=(2027, 2028, 2029))[0]]
        with self.assertRaises(ValueError):
            orchestrator.step2BuildKcgsPillarBoostPayloads(rows)

    def test_38_duplicate_year_rejected(self):
        rows = _approvedRows(years=(2024, 2025, 2025))
        with self.assertRaises(ValueError):
            orchestrator.step2BuildKcgsPillarBoostPayloads(rows)

    def test_39_non_consecutive_years_rejected(self):
        rows = _approvedRows(years=(2023, 2025, 2026))
        with self.assertRaises(ValueError):
            orchestrator.step2BuildKcgsPillarBoostPayloads(rows)

    def test_40_mixed_company_rejected(self):
        rows = _approvedRows()
        rows[2]["companyId"] = COMPANY_ID + 1
        with self.assertRaises(ValueError):
            orchestrator.step2BuildKcgsPillarBoostPayloads(rows)

    def test_41_invalid_grade_rejected(self):
        rows = _approvedRows()
        rows[2]["environmentGrade"] = "Z"
        with self.assertRaises(ValueError):
            orchestrator.step2BuildKcgsPillarBoostPayloads(rows)

    def test_42_invalid_input_source_type_rejected(self):
        rows = _approvedRows(inputSourceType="API")
        with self.assertRaises(ValueError):
            orchestrator.step2BuildKcgsPillarBoostPayloads(rows)

    def test_43_invalid_review_status_rejected(self):
        rows = _approvedRows(reviewStatus="PUBLISHED")
        with self.assertRaises(ValueError):
            orchestrator.step2BuildKcgsPillarBoostPayloads(rows)

    def test_44_sub_issue_domain_matches_pillar(self):
        for payload in _buildPayloads():
            raw = _raw(payload)
            self.assertEqual(subissueMaster[payload["subIssueCode"]]["domain"], raw["pillar"])


class KcgsSerializerTest(unittest.TestCase):
    def test_45_valid_serializer_maps_shadow_row(self):
        rows = _serializeCrafted()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row[0], RUN_ID)
        self.assertEqual(row[2], "KCGS:E")
        self.assertEqual(row[3], E_CODE)
        self.assertEqual(row[4], MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP)
        self.assertEqual(row[5], "agency")
        self.assertIsNone(row[6])
        self.assertIsNone(row[7])
        self.assertIsNone(row[8])
        payload = json.loads(row[9])
        self.assertEqual(payload["screeningTrace"][0]["rawInputs"]["subIssueBoost"], 0.7)


def _makeSerializerRejectTest(name, mutator):
    def test(self):
        with self.assertRaises(ValueError):
            _serializeCrafted(mutator)
    test.__name__ = name
    return test


_SERIALIZER_MUTATORS = {
    "test_46_score_purpose_rejected": lambda d: d.update({"scorePurpose": "CANONICAL_IRO"}),
    "test_47_source_channel_rejected": lambda d: d.update({"sourceChannel": "benchmark"}),
    "test_48_missing_sub_issue_rejected": lambda d: d.pop("subIssueCode"),
    "test_49_unknown_sub_issue_rejected": lambda d: d.update({"subIssueCode": "UNKNOWN"}),
    "test_50_screening_trace_not_list_rejected": lambda d: d.update({"screeningTrace": {}}),
    "test_51_empty_screening_trace_rejected": lambda d: d.update({"screeningTrace": []}),
    "test_52_multi_screening_trace_rejected": lambda d: d["screeningTrace"].append(copy.deepcopy(d["screeningTrace"][0])),
    "test_53_trace_not_dict_rejected": lambda d: d.update({"screeningTrace": ["bad"]}),
    "test_54_channel_rejected": lambda d: d["screeningTrace"][0].update({"channel": "kcgs"}),
    "test_55_impact_signal_rejected": lambda d: d["screeningTrace"][0].update({"impactSignal": 0.0}),
    "test_56_financial_signal_rejected": lambda d: d["screeningTrace"][0].update({"financialSignal": 0.0}),
    "test_57_raw_inputs_rejected": lambda d: d["screeningTrace"][0].update({"rawInputs": None}),
    "test_58_source_step_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"sourceStep": "kcgs"}),
    "test_59_source_type_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"sourceType": "kcgs"}),
    "test_60_provider_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"providerKey": "kis"}),
    "test_61_company_string_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"companyId": "1001"}),
    "test_62_company_bool_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"companyId": True}),
    "test_63_company_zero_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"companyId": 0}),
    "test_64_pillar_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"pillar": "X"}),
    "test_65_domain_mismatch_rejected": lambda d: d.update({"subIssueCode": S_CODE}),
    "test_66_boost_bool_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"subIssueBoost": True}),
    "test_67_boost_string_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"subIssueBoost": "0.7"}),
    "test_68_boost_low_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"subIssueBoost": -0.1}),
    "test_69_boost_high_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"subIssueBoost": 1.1}),
    "test_70_external_max_flag_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"externalMaxEligibleYn": True}),
    "test_71_top20_flag_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"top20BoostOnlyYn": False}),
    "test_72_direct_canonical_flag_rejected": lambda d: d["screeningTrace"][0]["rawInputs"].update({"directCanonicalFinalAllowedYn": True}),
}
for _name, _mutator in _SERIALIZER_MUTATORS.items():
    setattr(KcgsSerializerTest, _name, _makeSerializerRejectTest(_name, _mutator))


class KcgsReaderTxServiceTest(unittest.TestCase):
    def test_73_reader_uses_kcgs_table_latest_three(self):
        capture = {}

        def fakeFind(sql, params):
            capture["sql"] = sql
            capture["params"] = params
            return []

        with patch("src.utils.dmarepository._findAllRegulationRowsOrRaise", side_effect=fakeFind):
            self.assertEqual(repo.listApprovedKcgsGradeInputs(COMPANY_ID), [])
        self.assertIn("ESG_DMA_KCGS_GRADE_INPUT", capture["sql"])
        self.assertIn("review_status = 'APPROVED'", capture["sql"])
        self.assertIn("ORDER BY rating_year DESC", capture["sql"])
        self.assertIn("LIMIT 3", capture["sql"])
        self.assertEqual(capture["params"], (COMPANY_ID,))

    def test_74_tx_serializer_failure_before_get_conn(self):
        bad = _craftedKcgsDict()
        bad["scorePurpose"] = "CANONICAL_IRO"
        with patch("src.utils.dmarepository.step4WriteTrace", return_value=json.dumps(bad)):
            with patch("src.utils.dmarepository.getConn") as getConn:
                with self.assertRaises(ValueError):
                    repo.step4ReplaceKcgsShadowTracesTx(RUN_ID, [{}])
        getConn.assert_not_called()

    def test_75_tx_empty_clear_commits(self):
        conn = _TxConn(verifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            self.assertEqual(repo.step4ReplaceKcgsShadowTracesTx(RUN_ID, []), 0)
        self.assertEqual(conn.commitCount, 1)
        self.assertEqual(conn.rollbackCount, 0)
        self.assertEqual(conn.executemanyCalls, [])
        self.assertFalse(conn.autocommit)

    def test_76_tx_success_inserts_and_commits(self):
        payloads = _buildPayloads()[:2]
        conn = _TxConn(verifyCount=2)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            self.assertEqual(repo.step4ReplaceKcgsShadowTracesTx(RUN_ID, payloads), 2)
        self.assertEqual(conn.commitCount, 1)
        self.assertEqual(conn.rollbackCount, 0)
        self.assertEqual(len(conn.executemanyCalls[0][1]), 2)

    def test_77_tx_missing_run_rolls_back(self):
        conn = _TxConn(lockRow=None, verifyCount=0)
        conn.lockRow = None
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceKcgsShadowTracesTx(RUN_ID, [])
        self.assertEqual(conn.commitCount, 0)
        self.assertEqual(conn.rollbackCount, 1)

    def test_78_tx_verify_mismatch_rolls_back(self):
        payloads = _buildPayloads()[:1]
        conn = _TxConn(verifyCount=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceKcgsShadowTracesTx(RUN_ID, payloads)
        self.assertEqual(conn.commitCount, 0)
        self.assertEqual(conn.rollbackCount, 1)

    def test_79_service_refresh_wires_reader_builder_writer(self):
        _installMediaServiceImportStubs()
        service = importlib.import_module("src.services.medias.service")
        rows = _approvedRows()
        payloads = [{"ok": True}]
        with patch.object(service, "findRegulationRunContext", return_value={"companyId": COMPANY_ID}):
            with patch.object(service, "listApprovedKcgsGradeInputs", return_value=rows) as reader:
                with patch.object(service, "step2BuildKcgsPillarBoostPayloads", return_value=payloads) as builder:
                    with patch.object(service, "step4ReplaceKcgsShadowTracesTx", return_value=3) as writer:
                        self.assertEqual(service.refreshKcgsShadowForRun(RUN_ID), 3)
        reader.assert_called_once_with(COMPANY_ID)
        builder.assert_called_once_with(rows)
        writer.assert_called_once_with(RUN_ID, payloads)

    def test_80_service_empty_clear_calls_writer(self):
        _installMediaServiceImportStubs()
        service = importlib.import_module("src.services.medias.service")
        with patch.object(service, "findRegulationRunContext", return_value={"companyId": COMPANY_ID}):
            with patch.object(service, "listApprovedKcgsGradeInputs", return_value=[]):
                with patch.object(service, "step2BuildKcgsPillarBoostPayloads", return_value=[]):
                    with patch.object(service, "step4ReplaceKcgsShadowTracesTx", return_value=0) as writer:
                        self.assertEqual(service.refreshKcgsShadowForRun(RUN_ID), 0)
        writer.assert_called_once_with(RUN_ID, [])

    def test_81_service_builder_failure_does_not_call_writer(self):
        _installMediaServiceImportStubs()
        service = importlib.import_module("src.services.medias.service")
        with patch.object(service, "findRegulationRunContext", return_value={"companyId": COMPANY_ID}):
            with patch.object(service, "listApprovedKcgsGradeInputs", return_value=_approvedRows()[:2]):
                with patch.object(service, "step2BuildKcgsPillarBoostPayloads", side_effect=ValueError("partial")):
                    with patch.object(service, "step4ReplaceKcgsShadowTracesTx") as writer:
                        with self.assertRaises(ValueError):
                            service.refreshKcgsShadowForRun(RUN_ID)
        writer.assert_not_called()

    def test_82_run_media_analysis_has_no_kcgs_hook(self):
        _installMediaServiceImportStubs()
        service = importlib.import_module("src.services.medias.service")
        self.assertNotIn("refreshKcgsShadowForRun", inspect.getsource(service.runMediaAnalysis))

    def test_83_crawl_hook_keeps_regulation_and_kcgs_independent(self):
        _installMediaServiceImportStubs()
        service = importlib.import_module("src.services.medias.service")
        source = inspect.getsource(service.runMediaCrawlAndAnalyze)
        self.assertLess(source.index("refreshRegulationShadowForRun"), source.index("refreshKcgsShadowForRun"))
        self.assertIn("Warning: media_external.agency.kcgs", source)


class KcgsStaticInventoryTest(unittest.TestCase):
    def test_84_manifest_policy_files_unchanged(self):
        manifest = reg.getManifest()
        self.assertEqual(len(manifest["runtimePolicyFiles"]), 6)
        self.assertEqual(manifest["capabilities"]["kcgsPillarSignal"], "READY")
        self.assertEqual(manifest["capabilities"]["kcgsPillarBoostPropagation"], "DATA_EXPORT_REQUIRED")

    def test_85_source_step_literal_declared_once_in_src(self):
        matches = []
        for path in (ROOT / "src").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if KCGS_NAMESPACE in text:
                matches.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(matches, ["src/utils/dmarepository.py"])

    def test_86_no_api_frontend_or_sql_diff(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "--", "backend/src/apis", "frontend", "*.sql"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_87_root_prompt_cleanup(self):
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        trackedPrompts = [line for line in result.stdout.splitlines() if line.startswith("NEXT_CLAUDE_CODE_PROMPT")]
        self.assertEqual(trackedPrompts, [])

    def test_88_new_prompt_not_copied_to_root(self):
        prompt = REPO / "NEXT_CLAUDE_CODE_PROMPT_DMA_V13_C3_2_KCGS_PILLAR_BOOST_SHADOW_RUNTIME_R1.md"
        self.assertFalse(prompt.exists())

    def test_89_orchestrator_kcgs_branch_does_not_call_external_max(self):
        source = Path(ROOT, "src/services/materialities/orchestrator.py").read_text(encoding="utf-8")
        kcgsStart = source.index('if normalizedChannel == "kcgs":')
        externalStart = source.index('if normalizedChannel == "externalMax":')
        kcgsBranch = source[kcgsStart:externalStart]
        self.assertNotIn("step2CalcExternalMax", kcgsBranch)
        self.assertNotIn("final_score", kcgsBranch)
        self.assertNotIn("recalcFinal", kcgsBranch)

    def test_90_repository_kcgs_writer_does_not_recalc_or_rank(self):
        source = Path(ROOT, "src/utils/dmarepository.py").read_text(encoding="utf-8")
        start = source.index("def step4ReplaceKcgsShadowTracesTx")
        end = source.index("def step4ReadTrace")
        kcgsBlock = source[start:end]
        for forbidden in ("recalcStage(", "upsertStage(", "recalcFinal(", "updateRanks("):
            self.assertNotIn(forbidden, kcgsBlock)

    def test_91_kcgs_table_name_is_correct(self):
        source = inspect.getsource(repo.listApprovedKcgsGradeInputs)
        self.assertIn("ESG_DMA_KCGS_GRADE_INPUT", source)
        self.assertNotIn("ESG_GROUP_ROLLUP_BATCH", source)


if __name__ == "__main__":
    unittest.main()
