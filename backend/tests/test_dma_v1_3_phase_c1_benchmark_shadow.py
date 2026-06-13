"""
DMA v1.3 Phase C1 benchmark shadow trace tests.

Pure unit tests. No live DB, API smoke, Redis, Kafka, Docker, or external API path
is exercised.
"""

import inspect
import asyncio
import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


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

from src.models.dmaengine import ExtractedFactsV13, ScorePurposeV13  # noqa: E402
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
        self.rolled_back = False
        self.closed = False

    def cursor(self, dictionary=True):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def buildFact(**overrides):
    data = {
        "subIssueCode": "G0-02",
        "sourceType": "leader_sr",
        "classificationConfidence": 0.82,
        "rawMetadata": {"rawIssueLabel": "finance", "teSrFileId": 17},
    }
    data.update(overrides)
    return ExtractedFactsV13(**data)


def buildPayload(**factOverrides):
    return orchestrator.step0BuildFactTrace(
        extractedFact=buildFact(**factOverrides),
        sourceChannel="benchmark",
    )


class PhaseC1FactTraceBuilderTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()

    def test_step0_build_fact_trace_wraps_extracted_fact_without_scores(self):
        payload = buildPayload()

        self.assertEqual(payload["factorPayloadSchemaVersion"], "1.3")
        self.assertEqual(payload["ruleVersion"], dmaruleregistry.EXPECTED_RULE_VERSION)
        self.assertTrue(payload["configHash"].startswith("sha256:"))
        self.assertEqual(payload["scorePurpose"], ScorePurposeV13.PRESURVEY_SCREENING.value)
        self.assertEqual(payload["sourceChannel"], "benchmark")
        self.assertEqual(payload["subIssueCode"], "G0-02")
        self.assertEqual(payload["extractedFacts"]["subIssueCode"], "G0-02")
        self.assertEqual(payload["axisScores"], [])
        self.assertEqual(payload["screeningTrace"], [])
        self.assertEqual(payload["factorTrace"], [])


class PhaseC1BenchmarkShadowWriterTest(unittest.TestCase):
    def savePayloads(self, payloads):
        fakeConn = FakeConnection()
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            count = dmarepository.step4SaveBenchmarkShadowTraces(99, payloads)
        return count, fakeConn

    def test_shadow_writer_uses_reserved_source_step(self):
        count, conn = self.savePayloads([buildPayload()])

        self.assertEqual(count, 1)
        self.assertEqual(conn.cursor_obj.params[0][4], dmarepository.BENCHMARK_V13_SHADOW_SOURCE_STEP)

    def test_shadow_writer_does_not_store_scores_or_evidence(self):
        _, conn = self.savePayloads([buildPayload()])
        row = conn.cursor_obj.params[0]

        self.assertIsNone(row[1])
        self.assertIsNone(row[6])
        self.assertIsNone(row[7])

    def test_shadow_writer_stores_top_level_v13_payload_json(self):
        _, conn = self.savePayloads([buildPayload()])
        payload = json.loads(conn.cursor_obj.params[0][9])

        self.assertEqual(payload["factorPayloadSchemaVersion"], "1.3")
        self.assertIn("ruleVersion", payload)
        self.assertIn("extractedFacts", payload)
        self.assertNotIn("v13Shadow", payload)

    def test_shadow_writer_empty_payloads_returns_zero_without_insert(self):
        count, conn = self.savePayloads([])

        self.assertEqual(count, 0)
        self.assertIsNone(conn.cursor_obj.params)
        self.assertFalse(conn.committed)

    def test_shadow_writer_requires_extracted_facts_and_sub_issue(self):
        payload = buildPayload()
        payload["extractedFacts"] = None
        with self.assertRaises(ValueError):
            self.savePayloads([payload])

        payload = buildPayload(subIssueCode=None)
        with self.assertRaises(ValueError):
            self.savePayloads([payload])

    def test_shadow_writer_does_not_call_legacy_side_effects(self):
        source = inspect.getsource(dmarepository.step4SaveBenchmarkShadowTraces)

        for banned in ("saveSignals(", "insertEvidence(", "recalcStage(", "recalcFinal(", "updateRanks("):
            self.assertNotIn(banned, source)
        self.assertNotIn("ESG_DMA_SCORE_SUMMARY", source)
        self.assertNotIn("ESG_MATERIALITY_SELECTED_SUB_ISSUE", source)


class PhaseC1BenchmarkServiceHookTest(unittest.TestCase):
    def loadService(self):
        fakeOcraiv8 = types.ModuleType("src.utils.ocraiv8")

        async def fakeGemini(results, filePaths):
            return {"status": True, "data": []}

        fakeOcraiv8.gemini = fakeGemini
        sys.modules["src.utils.ocraiv8"] = fakeOcraiv8
        sys.modules.pop("src.services.benchmarks.service", None)
        return importlib.import_module("src.services.benchmarks.service")

    def test_service_hook_runs_after_legacy_save_and_is_failure_isolated(self):
        root = Path(__file__).resolve().parents[1]
        source = Path(root, "src/services/benchmarks/service.py").read_text(encoding="utf-8")

        self.assertLess(source.index("saveSignals("), source.index("step4ReplaceBenchmarkShadowTracesTx("))
        self.assertIn("Warning: Benchmark v1.3 shadow", source)
        self.assertNotIn("benchmark_v13_shadow", source)
        # Legacy append-only writer must NOT be imported in runtime service
        self.assertNotIn("step4SaveBenchmarkShadowTraces", source)

    def test_transaction_failure_keeps_legacy_success_response(self):
        service = self.loadService()
        finalResult = {
            "status": True,
            "data": [{"fileName": "a.pdf", "result": [{"subIssueCode": "G0-02"}]}],
        }

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.pdf").write_text("pdf", encoding="utf-8")
            service.settings.file_dir = tmp
            fileFindModel = SimpleNamespace(
                file=["a.pdf"], page="SR", esgMaterialityRunId=99, sourceType="leader_sr", sourceStep="benchmark"
            )
            userModel = SimpleNamespace(id=7)
            with patch.object(service, "findOne", return_value={
                "id": 17, "origin": "A", "file_name": "a.pdf", "type": "leader_sr", "company_name": "C",
            }), patch.object(service, "gemini", AsyncMock(return_value=finalResult)), patch.object(
                service, "convertToDmaSignals", return_value=[]
            ), patch.object(service, "scoreSignals", return_value=[]), patch.object(
                service, "saveSignals", return_value=None
            ), patch.object(service, "step0NormalizeBenchmarkFacts", return_value=[buildFact()]), patch.object(
                service, "step0BuildFactTrace", return_value=buildPayload()
            ), patch.object(
                service, "step2BuildBenchmarkScreeningPayloads", return_value=[]
            ), patch.object(
                service, "step4ReplaceBenchmarkShadowTracesTx", side_effect=RuntimeError("tx failed")
            ) as writer, patch("builtins.print") as printed:
                response = asyncio.run(service.findSr(fileFindModel, userModel))

        self.assertTrue(response["status"])
        self.assertEqual(writer.call_count, 1)
        self.assertIn("shadow replace transaction failed", printed.call_args[0][0])

    def test_legacy_save_failure_skips_replace_transaction(self):
        service = self.loadService()
        finalResult = {
            "status": True,
            "data": [{"fileName": "a.pdf", "result": [{"subIssueCode": "G0-02"}]}],
        }

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.pdf").write_text("pdf", encoding="utf-8")
            service.settings.file_dir = tmp
            fileFindModel = SimpleNamespace(
                file=["a.pdf"], page="SR", esgMaterialityRunId=99, sourceType="leader_sr", sourceStep="benchmark"
            )
            userModel = SimpleNamespace(id=7)
            with patch.object(service, "findOne", return_value={
                "id": 17, "origin": "A", "file_name": "a.pdf", "type": "leader_sr", "company_name": "C",
            }), patch.object(service, "gemini", AsyncMock(return_value=finalResult)), patch.object(
                service, "convertToDmaSignals", return_value=[]
            ), patch.object(service, "scoreSignals", return_value=[]), patch.object(
                service, "saveSignals", side_effect=RuntimeError("legacy failed")
            ), patch.object(service, "step4ReplaceBenchmarkShadowTracesTx") as writer:
                with self.assertRaises(Exception):
                    asyncio.run(service.findSr(fileFindModel, userModel))

        writer.assert_not_called()

    def test_fact_build_failure_skips_replace_transaction(self):
        service = self.loadService()
        finalResult = {
            "status": True,
            "data": [{"fileName": "a.pdf", "result": [{"subIssueCode": "G0-02"}]}],
        }

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.pdf").write_text("pdf", encoding="utf-8")
            service.settings.file_dir = tmp
            fileFindModel = SimpleNamespace(
                file=["a.pdf"], page="SR", esgMaterialityRunId=99, sourceType="leader_sr", sourceStep="benchmark"
            )
            userModel = SimpleNamespace(id=7)
            with patch.object(service, "findOne", return_value={
                "id": 17, "origin": "A", "file_name": "a.pdf", "type": "leader_sr", "company_name": "C",
            }), patch.object(service, "gemini", AsyncMock(return_value=finalResult)), patch.object(
                service, "convertToDmaSignals", return_value=[]
            ), patch.object(service, "scoreSignals", return_value=[]), patch.object(
                service, "saveSignals", return_value=None
            ), patch.object(
                service, "step0NormalizeBenchmarkFacts", side_effect=RuntimeError("fact build exploded")
            ), patch.object(service, "step4ReplaceBenchmarkShadowTracesTx") as txWriter, patch(
                "builtins.print"
            ) as printed:
                response = asyncio.run(service.findSr(fileFindModel, userModel))

        # Legacy response succeeds — shadow failure is isolated
        self.assertTrue(response["status"])
        # Replace Transaction must be skipped when fact build fails
        txWriter.assert_not_called()
        # Warning must be emitted
        warning_messages = [call[0][0] for call in printed.call_args_list if call[0]]
        self.assertTrue(
            any("shadow replace skipped" in m for m in warning_messages),
            f"Expected 'shadow replace skipped' warning, got: {warning_messages}",
        )

    def test_replace_transaction_runs_once_per_request_after_multiple_files(self):
        service = self.loadService()
        finalResult = {
            "status": True,
            "data": [
                {"fileName": "a.pdf", "result": [{"subIssueCode": "G0-02"}]},
                {"fileName": "b.pdf", "result": [{"subIssueCode": "G0-02"}]},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.pdf").write_text("pdf", encoding="utf-8")
            Path(tmp, "b.pdf").write_text("pdf", encoding="utf-8")
            service.settings.file_dir = tmp
            fileFindModel = SimpleNamespace(
                file=["a.pdf", "b.pdf"], page="SR", esgMaterialityRunId=99, sourceType="leader_sr", sourceStep="benchmark"
            )
            userModel = SimpleNamespace(id=7)
            records = [
                {"id": 17, "origin": "A", "file_name": "a.pdf", "type": "leader_sr", "company_name": "C"},
                {"id": 18, "origin": "B", "file_name": "b.pdf", "type": "peer_sr", "company_name": "C"},
            ]
            with patch.object(service, "findOne", side_effect=records), patch.object(
                service, "gemini", AsyncMock(return_value=finalResult)
            ), patch.object(service, "convertToDmaSignals", return_value=[]), patch.object(
                service, "scoreSignals", return_value=[]
            ), patch.object(service, "saveSignals", return_value=None), patch.object(
                service, "step0NormalizeBenchmarkFacts", return_value=[buildFact()]
            ), patch.object(service, "step0BuildFactTrace", return_value=buildPayload()), patch.object(
                service, "step2BuildBenchmarkScreeningPayloads", return_value=[buildPayload()]
            ) as buildScreening, patch.object(
                service, "step4ReplaceBenchmarkShadowTracesTx", return_value=3
            ) as txWriter:
                response = asyncio.run(service.findSr(fileFindModel, userModel))

        self.assertTrue(response["status"])
        # Replace Transaction은 요청당 정확히 1회
        self.assertEqual(txWriter.call_count, 1)
        # runId=99로 호출됨
        txCall = txWriter.call_args
        self.assertEqual(txCall.kwargs["runId"], 99)
        # 2개 파일 × 파일당 1개 fact = factPayloads 2건 전달
        self.assertEqual(len(txCall.kwargs["factPayloads"]), 2)
        # listBenchmarkShadowObservationRows는 service.py에서 더 이상 import하지 않음
        self.assertFalse(hasattr(service, "listBenchmarkShadowObservationRows"))


if __name__ == "__main__":
    unittest.main()
