"""
DMA v1.3 Phase C1.1 benchmark observation and screening shadow tests.

Pure unit tests. No live DB, API smoke, Redis, Kafka, Docker, or external API path
is exercised.
"""

import inspect
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


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
    mariadb = types.ModuleType("mariadb")
    mariadb.Error = Exception
    mariadb.connect = lambda **kwargs: None
    sys.modules["mariadb"] = mariadb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.dmaengine import ScorePurposeV13  # noqa: E402
from src.services.materialities import orchestrator  # noqa: E402
from src.utils import dmarepository, dmaruleregistry  # noqa: E402


class FakeCursor:
    def __init__(self):
        self.sql = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def executemany(self, sql, params):
        self.sql = sql
        self.params = list(params)


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self, dictionary=True):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        self.closed = True


def screeningPayload(observation="BLIND_SPOT"):
    return orchestrator.step2RunScreening("benchmark", {
        "subIssueCode": "G0-02",
        "observation": observation,
        "leaderObserved": True,
        "peerObserved": True,
        "ownObserved": False,
    })


class PhaseC11BenchmarkObservationResolverTest(unittest.TestCase):
    def test_resolver_observation_truth_table(self):
        cases = [
            (1, 1, 0, "BLIND_SPOT"),
            (1, 1, 1, "COMMON_ISSUE"),
            (1, 0, 0, "NONE"),
            (0, 1, 0, "NONE"),
            (0, 0, 1, "NONE"),
            (1, 0, 1, "NONE"),
            (0, 1, 1, "NONE"),
            (0, 0, 0, "NONE"),
        ]
        for leader, peer, own, expected in cases:
            with self.subTest(leader=leader, peer=peer, own=own):
                self.assertEqual(orchestrator.step2ResolveBenchmarkObservation({
                    "sub_issue_code": "G0-02",
                    "leader_observed": leader,
                    "peer_observed": peer,
                    "own_observed": own,
                }), expected)

    def test_resolver_requires_sub_issue_and_normalizes_string_flags(self):
        with self.assertRaises(ValueError):
            orchestrator.step2ResolveBenchmarkObservation({
                "leader_observed": 1,
                "peer_observed": 1,
                "own_observed": 0,
            })

        self.assertEqual(orchestrator.step2ResolveBenchmarkObservation({
            "sub_issue_code": "G0-02",
            "leader_observed": "1",
            "peer_observed": "1",
            "own_observed": "0",
        }), "BLIND_SPOT")


class PhaseC11RepositoryObservationQueryTest(unittest.TestCase):
    def test_observation_query_reads_only_fact_shadow_namespace(self):
        with patch.object(dmarepository, "findAll", return_value=[]) as findAll:
            rows = dmarepository.listBenchmarkShadowObservationRows(99)

        self.assertEqual(rows, [])
        sql, params = findAll.call_args.args
        self.assertIn("ESG_DMA_SIGNAL_DETAIL", sql)
        self.assertIn("source_step = ?", sql)
        self.assertIn("delete_yn = 0", sql)
        self.assertIn("GROUP BY sub_issue_code", sql)
        self.assertEqual(params, (99, dmarepository.BENCHMARK_V13_SHADOW_SOURCE_STEP))
        self.assertNotIn(dmarepository.BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP, params)


class PhaseC11ScreeningTracePayloadTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()

    def test_benchmark_screening_trace_preserves_sub_issue_and_observation_flags(self):
        payload = screeningPayload()

        self.assertEqual(payload["factorPayloadSchemaVersion"], "1.3")
        self.assertEqual(payload["scorePurpose"], ScorePurposeV13.PRESURVEY_SCREENING.value)
        self.assertEqual(payload["sourceChannel"], "benchmark")
        self.assertEqual(payload["subIssueCode"], "G0-02")
        self.assertEqual(len(payload["screeningTrace"]), 1)
        self.assertEqual(payload["axisScores"], [])
        self.assertEqual(payload["factorTrace"], [])
        rawInputs = payload["screeningTrace"][0]["rawInputs"]
        self.assertEqual(rawInputs["observation"], "BLIND_SPOT")
        self.assertIs(rawInputs["leaderObserved"], True)
        self.assertIs(rawInputs["peerObserved"], True)
        self.assertIs(rawInputs["ownObserved"], False)


class PhaseC11ScreeningShadowWriterTest(unittest.TestCase):
    def savePayloads(self, payloads):
        fakeConn = FakeConnection()
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            count = dmarepository.step4SaveBenchmarkShadowTraces(99, payloads, shadowKind="screening")
        return count, fakeConn

    def test_screening_shadow_writer_uses_screening_namespace_and_no_score_columns(self):
        count, conn = self.savePayloads([screeningPayload()])
        row = conn.cursor_obj.params[0]
        payload = json.loads(row[9])

        self.assertEqual(count, 1)
        self.assertIsNone(row[1])
        self.assertEqual(row[4], dmarepository.BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP)
        self.assertEqual(row[5], "benchmark")
        self.assertIsNone(row[6])
        self.assertIsNone(row[7])
        self.assertIsNone(row[8])
        self.assertEqual(payload["factorPayloadSchemaVersion"], "1.3")
        self.assertIn("screeningTrace", payload)
        self.assertNotIn("v13Shadow", payload)

    def test_screening_shadow_writer_requires_sub_issue_and_screening_trace(self):
        payload = screeningPayload()
        payload["subIssueCode"] = None
        with self.assertRaises(ValueError):
            self.savePayloads([payload])

        payload = screeningPayload()
        payload["screeningTrace"] = []
        with self.assertRaises(ValueError):
            self.savePayloads([payload])

        with self.assertRaises(ValueError):
            dmarepository.step4SaveBenchmarkShadowTraces(99, [screeningPayload()], shadowKind="bad")

    def test_screening_shadow_writer_does_not_call_legacy_side_effects(self):
        source = inspect.getsource(dmarepository.step4SaveBenchmarkShadowTraces)

        for banned in ("saveSignals(", "insertEvidence(", "recalcStage(", "recalcFinal(", "updateRanks("):
            self.assertNotIn(banned, source)
        self.assertNotIn("ESG_DMA_SCORE_SUMMARY", source)
        self.assertNotIn("ESG_MATERIALITY_SELECTED_SUB_ISSUE", source)


if __name__ == "__main__":
    unittest.main()
