"""
DMA v1.3 Phase C1.3 — Benchmark Shadow Replace-Active Transaction tests.

Pure unit tests. No live DB, API smoke, Redis, Kafka, Docker, or external API path
is exercised.

Coverage:
- _buildBenchmarkShadowRows: row serialization SSOT
- step4ReplaceBenchmarkShadowTracesTx: lock / soft-delete / insert / verify / commit / rollback
- step2BuildBenchmarkScreeningPayloads: in-memory observation aggregation + NONE Backfill
"""

import asyncio
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

from src.models.dmaengine import ExtractedFactsV13  # noqa: E402
from src.services.benchmarks.adapter import step0NormalizeBenchmarkFacts  # noqa: E402
from src.services.materialities import orchestrator  # noqa: E402
from src.utils import dmarepository, dmaruleregistry  # noqa: E402
from src.utils.subissuemaster import subissueMaster  # noqa: E402


# ── helpers ─────────────────────────────────────────────────────────────────

def buildFact(**overrides):
    data = {
        "subIssueCode": "E-01",
        "sourceType": "leader_sr",
        "classificationConfidence": 0.90,
        "rawMetadata": {"rawIssueLabel": "climate", "teSrFileId": 1},
    }
    data.update(overrides)
    return ExtractedFactsV13(**data)


def buildFactPayload(**factOverrides):
    return orchestrator.step0BuildFactTrace(
        extractedFact=buildFact(**factOverrides),
        sourceChannel="benchmark",
    )


# ── FakeCursor that supports execute + fetchone + executemany ────────────────

class FakeTxCursor:
    """Fake cursor for transaction tests. Configurable fetchone sequences."""

    def __init__(self, fetchone_map=None):
        self.executed = []       # (sql, params) tuples from execute()
        self.many_executed = []  # (sql, rows) tuples from executemany()
        self._fetchone_map = fetchone_map or {}  # keyword → return value
        self._next_fetchone = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        self.executed.append((sql, params))
        self._next_fetchone = None
        for keyword, row in self._fetchone_map.items():
            if keyword in sql:
                self._next_fetchone = row
                break

    def executemany(self, sql, params):
        self.many_executed.append((sql, list(params)))

    def fetchone(self):
        return self._next_fetchone


class FakeTxConnection:
    def __init__(self, fetchone_map=None):
        self.cursor_obj = FakeTxCursor(fetchone_map=fetchone_map)
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.autocommit = True  # starts True; transaction code must set False

    def cursor(self, dictionary=True):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def makeConn(expectedCount=3):
    return FakeTxConnection(fetchone_map={
        "FOR UPDATE": {"id": 99},
        "COUNT(": {"row_count": expectedCount, "distinct_count": expectedCount},
    })


# ── _buildBenchmarkShadowRows ─────────────────────────────────────────────────

class PhaseC13BuildShadowRowsTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()

    def test_fact_row_uses_benchmark_shadow_source_step(self):
        payload = buildFactPayload()
        rows = dmarepository._buildBenchmarkShadowRows(99, [payload], "fact")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], dmarepository.BENCHMARK_V13_SHADOW_SOURCE_STEP)

    def test_fact_row_has_no_evidence_id_or_scores(self):
        rows = dmarepository._buildBenchmarkShadowRows(99, [buildFactPayload()], "fact")
        row = rows[0]
        self.assertIsNone(row[1])   # evidence_id
        self.assertIsNone(row[6])   # impact_score
        self.assertIsNone(row[7])   # financial_score

    def test_fact_row_run_id_is_passed_correctly(self):
        rows = dmarepository._buildBenchmarkShadowRows(42, [buildFactPayload()], "fact")
        self.assertEqual(rows[0][0], 42)

    def test_fact_row_payload_json_is_valid_v13(self):
        rows = dmarepository._buildBenchmarkShadowRows(99, [buildFactPayload()], "fact")
        payload = json.loads(rows[0][9])
        self.assertEqual(payload["factorPayloadSchemaVersion"], "1.3")
        self.assertIn("extractedFacts", payload)

    def test_screening_row_uses_screening_shadow_source_step(self):
        sp = orchestrator.step2RunScreening("benchmark", {
            "subIssueCode": "E-01",
            "observation": "NONE",
            "leaderObserved": False,
            "peerObserved": False,
            "ownObserved": False,
        })
        rows = dmarepository._buildBenchmarkShadowRows(99, [sp], "screening")
        self.assertEqual(rows[0][4], dmarepository.BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP)

    def test_empty_payloads_returns_empty_list(self):
        self.assertEqual(dmarepository._buildBenchmarkShadowRows(99, [], "fact"), [])
        self.assertEqual(dmarepository._buildBenchmarkShadowRows(99, [], "screening"), [])

    def test_invalid_shadow_kind_raises(self):
        with self.assertRaises(ValueError):
            dmarepository._buildBenchmarkShadowRows(99, [buildFactPayload()], "unknown")

    def test_fact_missing_sub_issue_code_raises(self):
        payload = buildFactPayload(subIssueCode=None)
        with self.assertRaises(ValueError):
            dmarepository._buildBenchmarkShadowRows(99, [payload], "fact")

    def test_fact_missing_extracted_facts_raises(self):
        payload = buildFactPayload()
        payload["extractedFacts"] = None
        with self.assertRaises(ValueError):
            dmarepository._buildBenchmarkShadowRows(99, [payload], "fact")


# ── step4ReplaceBenchmarkShadowTracesTx ─────────────────────────────────────

class PhaseC13ReplaceTransactionTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()

    def _makeScreeningPayload(self, code="E-01", observation="NONE"):
        return orchestrator.step2RunScreening("benchmark", {
            "subIssueCode": code,
            "observation": observation,
            "leaderObserved": False,
            "peerObserved": False,
            "ownObserved": False,
        })

    def test_transaction_commits_on_success(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            result = dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                runId=99,
                factPayloads=[buildFactPayload()],
                screeningPayloads=[self._makeScreeningPayload()],
                expectedScreeningCount=1,
            )
        self.assertTrue(fakeConn.committed)
        self.assertFalse(fakeConn.rolled_back)
        self.assertTrue(fakeConn.closed)
        self.assertEqual(result, 2)  # 1 fact + 1 screening

    def test_transaction_acquires_row_lock(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                runId=99,
                factPayloads=[buildFactPayload()],
                screeningPayloads=[self._makeScreeningPayload()],
                expectedScreeningCount=1,
            )
        lockSqls = [sql for sql, _ in fakeConn.cursor_obj.executed if "FOR UPDATE" in sql]
        self.assertEqual(len(lockSqls), 1)
        self.assertIn("ESG_MATERIALITY_RUN", lockSqls[0])

    def test_transaction_soft_deletes_both_namespaces(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                runId=99,
                factPayloads=[buildFactPayload()],
                screeningPayloads=[self._makeScreeningPayload()],
                expectedScreeningCount=1,
            )
        deleteSqls = [sql for sql, _ in fakeConn.cursor_obj.executed if "delete_yn = 1" in sql]
        self.assertEqual(len(deleteSqls), 1)
        params = [p for sql, p in fakeConn.cursor_obj.executed if "delete_yn = 1" in sql][0]
        self.assertIn(dmarepository.BENCHMARK_V13_SHADOW_SOURCE_STEP, params)
        self.assertIn(dmarepository.BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP, params)

    def test_transaction_inserts_fact_and_screening_rows(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                runId=99,
                factPayloads=[buildFactPayload()],
                screeningPayloads=[self._makeScreeningPayload()],
                expectedScreeningCount=1,
            )
        insertCalls = fakeConn.cursor_obj.many_executed
        self.assertEqual(len(insertCalls), 2)
        allRows = [row for _, rows in insertCalls for row in rows]
        sourceSteps = {row[4] for row in allRows}
        self.assertIn(dmarepository.BENCHMARK_V13_SHADOW_SOURCE_STEP, sourceSteps)
        self.assertIn(dmarepository.BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP, sourceSteps)

    def test_transaction_rollbacks_on_completeness_failure(self):
        # Verify query returns count != expectedScreeningCount → rollback
        fakeConn = FakeTxConnection(fetchone_map={
            "FOR UPDATE": {"id": 99},
            "COUNT(": {"row_count": 0, "distinct_count": 0},
        })
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            with self.assertRaises(RuntimeError):
                dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                    runId=99,
                    factPayloads=[buildFactPayload()],
                    screeningPayloads=[self._makeScreeningPayload()],
                    expectedScreeningCount=1,
                )
        self.assertFalse(fakeConn.committed)
        self.assertTrue(fakeConn.rolled_back)
        self.assertTrue(fakeConn.closed)

    def test_transaction_rollbacks_on_missing_run_row(self):
        fakeConn = FakeTxConnection(fetchone_map={
            "FOR UPDATE": None,
            "COUNT(": {"row_count": 1, "distinct_count": 1},
        })
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            with self.assertRaises(RuntimeError):
                dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                    runId=99,
                    factPayloads=[],
                    screeningPayloads=[self._makeScreeningPayload()],
                    expectedScreeningCount=1,
                )
        self.assertTrue(fakeConn.rolled_back)

    def test_empty_fact_payloads_skips_fact_insert(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                runId=99,
                factPayloads=[],
                screeningPayloads=[self._makeScreeningPayload()],
                expectedScreeningCount=1,
            )
        insertCalls = fakeConn.cursor_obj.many_executed
        sourceStepsInserted = {row[4] for _, rows in insertCalls for row in rows}
        self.assertNotIn(dmarepository.BENCHMARK_V13_SHADOW_SOURCE_STEP, sourceStepsInserted)
        self.assertIn(dmarepository.BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP, sourceStepsInserted)

    def test_transaction_sets_autocommit_false(self):
        fakeConn = makeConn(expectedCount=1)
        self.assertTrue(fakeConn.autocommit)  # starts True
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                runId=99,
                factPayloads=[buildFactPayload()],
                screeningPayloads=[self._makeScreeningPayload()],
                expectedScreeningCount=1,
            )
        self.assertFalse(fakeConn.autocommit)  # must be set False before any SQL

    def test_zero_expected_screening_count_raises_before_conn(self):
        getConnCalled = []
        def fakeGetConn():
            getConnCalled.append(True)
            return makeConn(expectedCount=0)
        with patch.object(dmarepository, "getConn", side_effect=fakeGetConn):
            with self.assertRaises(ValueError):
                dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                    runId=99, factPayloads=[], screeningPayloads=[], expectedScreeningCount=0
                )
        self.assertEqual(len(getConnCalled), 0, "getConn must NOT be called when expectedScreeningCount=0")

    def test_screening_payloads_count_mismatch_raises_before_conn(self):
        getConnCalled = []
        def fakeGetConn():
            getConnCalled.append(True)
            return makeConn(expectedCount=2)
        sp = self._makeScreeningPayload()
        with patch.object(dmarepository, "getConn", side_effect=fakeGetConn):
            with self.assertRaises(ValueError):
                dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                    runId=99, factPayloads=[], screeningPayloads=[sp], expectedScreeningCount=2
                )
        self.assertEqual(len(getConnCalled), 0, "getConn must NOT be called when payload count mismatches")

    def test_transaction_does_not_call_legacy_side_effects(self):
        import inspect
        source = inspect.getsource(dmarepository.step4ReplaceBenchmarkShadowTracesTx)
        for banned in ("saveSignals(", "insertEvidence(", "recalcStage(", "recalcFinal(", "updateRanks("):
            self.assertNotIn(banned, source)
        self.assertNotIn("ESG_DMA_SCORE_SUMMARY", source)
        self.assertNotIn("ESG_MATERIALITY_SELECTED_SUB_ISSUE", source)

    def test_conn_none_raises_runtime_error(self):
        sp = self._makeScreeningPayload()
        with patch.object(dmarepository, "getConn", return_value=None):
            with self.assertRaises(RuntimeError):
                dmarepository.step4ReplaceBenchmarkShadowTracesTx(
                    runId=99, factPayloads=[], screeningPayloads=[sp], expectedScreeningCount=1
                )


# ── step2BuildBenchmarkScreeningPayloads ─────────────────────────────────────

class PhaseC13BuildScreeningPayloadsTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()

    def _getUniverse(self):
        return [
            code for code, meta in subissueMaster.items()
            if meta.get("materiality_issue_pool_yn") == "Y"
        ]

    def test_empty_facts_returns_universe_count_payloads(self):
        universe = self._getUniverse()
        payloads = orchestrator.step2BuildBenchmarkScreeningPayloads([], universe)
        self.assertEqual(len(payloads), len(universe))

    def test_empty_facts_all_payloads_have_backfilled_true(self):
        universe = self._getUniverse()
        payloads = orchestrator.step2BuildBenchmarkScreeningPayloads([], universe)
        for p in payloads:
            ri = p["screeningTrace"][0]["rawInputs"]
            self.assertTrue(ri["backfilledYn"], f"Expected backfilledYn=True for {p.get('subIssueCode')}")

    def test_observed_sub_issue_has_backfilled_false(self):
        universe = self._getUniverse()
        targetCode = universe[0]
        factPayload = buildFactPayload(subIssueCode=targetCode, sourceType="leader_sr")
        payloads = orchestrator.step2BuildBenchmarkScreeningPayloads([factPayload], universe)
        for p in payloads:
            ri = p["screeningTrace"][0]["rawInputs"]
            if p["subIssueCode"] == targetCode:
                self.assertFalse(ri["backfilledYn"])
            else:
                self.assertTrue(ri["backfilledYn"])

    def test_blind_spot_observation_when_leader_and_peer_only(self):
        universe = self._getUniverse()
        targetCode = universe[0]
        factPayloads = [
            buildFactPayload(subIssueCode=targetCode, sourceType="leader_sr"),
            buildFactPayload(subIssueCode=targetCode, sourceType="peer_sr"),
        ]
        payloads = orchestrator.step2BuildBenchmarkScreeningPayloads(factPayloads, universe)
        targetPayload = next(p for p in payloads if p["subIssueCode"] == targetCode)
        ri = targetPayload["screeningTrace"][0]["rawInputs"]
        self.assertEqual(ri["observation"], "BLIND_SPOT")

    def test_common_issue_observation_when_leader_peer_own(self):
        universe = self._getUniverse()
        targetCode = universe[0]
        factPayloads = [
            buildFactPayload(subIssueCode=targetCode, sourceType="leader_sr"),
            buildFactPayload(subIssueCode=targetCode, sourceType="peer_sr"),
            buildFactPayload(subIssueCode=targetCode, sourceType="own_sr"),
        ]
        payloads = orchestrator.step2BuildBenchmarkScreeningPayloads(factPayloads, universe)
        targetPayload = next(p for p in payloads if p["subIssueCode"] == targetCode)
        ri = targetPayload["screeningTrace"][0]["rawInputs"]
        self.assertEqual(ri["observation"], "COMMON_ISSUE")

    def test_none_observation_when_only_own(self):
        universe = self._getUniverse()
        targetCode = universe[0]
        factPayloads = [buildFactPayload(subIssueCode=targetCode, sourceType="own_sr")]
        payloads = orchestrator.step2BuildBenchmarkScreeningPayloads(factPayloads, universe)
        targetPayload = next(p for p in payloads if p["subIssueCode"] == targetCode)
        ri = targetPayload["screeningTrace"][0]["rawInputs"]
        self.assertEqual(ri["observation"], "NONE")
        self.assertFalse(ri["backfilledYn"])

    def test_each_payload_has_valid_v13_structure(self):
        universe = self._getUniverse()[:5]
        payloads = orchestrator.step2BuildBenchmarkScreeningPayloads([], universe)
        for p in payloads:
            self.assertEqual(p["factorPayloadSchemaVersion"], "1.3")
            self.assertIsInstance(p.get("screeningTrace"), list)
            self.assertEqual(len(p["screeningTrace"]), 1)

    def test_universe_62_sub_issues_all_pool_yn(self):
        universe = self._getUniverse()
        self.assertEqual(len(universe), 62)
        for code in universe:
            self.assertEqual(subissueMaster[code]["materiality_issue_pool_yn"], "Y")

    def test_no_g0_codes_in_universe(self):
        universe = self._getUniverse()
        g0Codes = [code for code in universe if code.upper().startswith("G0")]
        self.assertEqual(len(g0Codes), 0)

    def test_malformed_fact_payload_not_mapping_raises(self):
        universe = self._getUniverse()
        with self.assertRaises(ValueError):
            orchestrator.step2BuildBenchmarkScreeningPayloads(["not_a_dict"], universe)

    def test_malformed_fact_payload_missing_sub_issue_code_raises(self):
        universe = self._getUniverse()
        badPayload = buildFactPayload()
        # Remove subIssueCode from extractedFacts
        badPayload["extractedFacts"]["subIssueCode"] = None
        with self.assertRaises(ValueError):
            orchestrator.step2BuildBenchmarkScreeningPayloads([badPayload], universe)

    def test_fact_payload_outside_universe_raises(self):
        universe = self._getUniverse()
        outsiderPayload = buildFactPayload(subIssueCode="G0-FAKE-999")
        with self.assertRaises(ValueError):
            orchestrator.step2BuildBenchmarkScreeningPayloads([outsiderPayload], universe)

    def test_invalid_source_type_in_fact_payload_raises(self):
        universe = self._getUniverse()
        targetCode = universe[0]
        badPayload = buildFactPayload(subIssueCode=targetCode)
        badPayload["extractedFacts"]["sourceType"] = "unknown_channel"
        with self.assertRaises(ValueError):
            orchestrator.step2BuildBenchmarkScreeningPayloads([badPayload], universe)


# ── step0NormalizeBenchmarkFacts — Adapter Fail-Fast ─────────────────────────

class PhaseC13AdapterNormalizationTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()
        self._aiPolicy = dmaruleregistry.getPolicy("ai_fact_validation_policy")

    def test_non_mapping_row_raises(self):
        with self.assertRaises(ValueError):
            step0NormalizeBenchmarkFacts(
                resultList=["not_a_dict"],
                fileId=1,
                sourceType="leader_sr",
                aiPolicy=self._aiPolicy,
            )

    def test_missing_sub_issue_code_raises(self):
        row = {"rawIssueLabel": "climate issue", "classificationConfidence": 0.82}
        with self.assertRaises(ValueError):
            step0NormalizeBenchmarkFacts(
                resultList=[row],
                fileId=1,
                sourceType="leader_sr",
                aiPolicy=self._aiPolicy,
            )


if __name__ == "__main__":
    unittest.main()
