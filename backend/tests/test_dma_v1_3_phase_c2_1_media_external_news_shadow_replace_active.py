"""
DMA v1.3 Phase C2.1 — media_external.news Shadow Replace-Active Runtime Wiring tests.

Pure unit tests. No live DB, Redis, Kafka, Docker, or external API.

Coverage:
- _buildMediaNewsShadowRows: row serialization, validation
- step4ReplaceMediaNewsShadowTracesTx: lock / soft-delete / insert / count / commit / rollback
- service.py shadow hook wiring
- adapter._sanitizeIssueSimilarityMatches scalar normalization
- guard assertions
"""

import inspect
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

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
from src.services.medias.adapter import _sanitizeIssueSimilarityMatches, step0NormalizeMediaFacts  # noqa: E402
from src.services.materialities import orchestrator  # noqa: E402
from src.utils import dmarepository, dmaruleregistry  # noqa: E402


# ── fake DB helpers ──────────────────────────────────────────────────────────

class FakeTxCursor:
    def __init__(self, fetchone_map=None):
        self.executed = []
        self.many_executed = []
        self._fetchone_map = fetchone_map or {}
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
        self.autocommit = True

    def cursor(self, dictionary=True):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def makeConn(expectedCount=1):
    return FakeTxConnection(fetchone_map={
        "FOR UPDATE": {"id": 99},
        "COUNT(*)": {"row_count": expectedCount},
    })


# ── news fact payload helper ─────────────────────────────────────────────────

def buildNewsResult(**overrides):
    base = {
        "source": "impacton",
        "title": "뉴스 기사",
        "url": "https://example.test/news",
        "publishedAt": "2026-06-11",
        "chunk": "본문 근거",
        "bestSubIssueId": "E_CLIMATE__CLIMATE_TARGETS_TRANSITION",
        "bestSubIssueNameKr": "기후변화 대응",
        "bestSimilarityScore": 0.71,
        "issueSimilarityMatches": [],
    }
    base.update(overrides)
    return base


def buildNewsFactPayload(**resultOverrides):
    dmaruleregistry.resetDmaRulesForTest()
    facts = step0NormalizeMediaFacts([buildNewsResult(**resultOverrides)])
    return orchestrator.step0BuildFactTrace(extractedFact=facts[0], sourceChannel="media_external")


# ── Repository tests ─────────────────────────────────────────────────────────

class PhaseC21RepositoryTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()

    # 1. MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP 상수
    def test_namespace_constant_declared_once_in_dmarepository(self):
        self.assertEqual(
            dmarepository.MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP,
            "media_external_news_v13_shadow",
        )

    # 2a. source_step = media_external_news_v13_shadow
    def test_row_uses_news_shadow_source_step(self):
        rows = dmarepository._buildMediaNewsShadowRows(99, [buildNewsFactPayload()])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], dmarepository.MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP)

    # 2b. source_type = news
    def test_row_source_type_is_news(self):
        rows = dmarepository._buildMediaNewsShadowRows(99, [buildNewsFactPayload()])
        self.assertEqual(rows[0][5], "news")

    # 2c. impact_score = NULL, financial_score = NULL
    def test_row_has_no_impact_or_financial_score(self):
        rows = dmarepository._buildMediaNewsShadowRows(99, [buildNewsFactPayload()])
        self.assertIsNone(rows[0][6])
        self.assertIsNone(rows[0][7])

    # 2d. confidence_score 보존
    def test_row_confidence_score_preserved(self):
        rows = dmarepository._buildMediaNewsShadowRows(
            99, [buildNewsFactPayload(bestSimilarityScore=0.71)]
        )
        self.assertAlmostEqual(rows[0][8], 0.71)

    # 2e. ScoringPayloadV13 top-level JSON 저장 (v13Shadow wrapper 없음)
    def test_row_payload_json_is_top_level_v13_no_wrapper(self):
        rows = dmarepository._buildMediaNewsShadowRows(99, [buildNewsFactPayload()])
        payload = json.loads(rows[0][9])
        self.assertEqual(payload["factorPayloadSchemaVersion"], "1.3")
        self.assertIn("extractedFacts", payload)
        self.assertNotIn("v13Shadow", payload)

    # 3. extractedFacts 누락 → ValueError
    def test_missing_extracted_facts_raises(self):
        payload = buildNewsFactPayload()
        payload["extractedFacts"] = None
        with self.assertRaises(ValueError):
            dmarepository._buildMediaNewsShadowRows(99, [payload])

    # 4. subIssueCode 누락 → ValueError
    def test_missing_sub_issue_code_raises(self):
        dmaruleregistry.resetDmaRulesForTest()
        fact = ExtractedFactsV13(
            subIssueCode=None,
            sourceType="news",
            classificationConfidence=0.7,
            rawMetadata={},
        )
        payload = orchestrator.step0BuildFactTrace(extractedFact=fact, sourceChannel="media_external")
        with self.assertRaises(ValueError):
            dmarepository._buildMediaNewsShadowRows(99, [payload])

    # 5. sourceType != "news" → ValueError
    def test_wrong_source_type_raises(self):
        dmaruleregistry.resetDmaRulesForTest()
        fact = ExtractedFactsV13(
            subIssueCode="E-01",
            sourceType="leader_sr",
            classificationConfidence=0.7,
            rawMetadata={},
        )
        payload = orchestrator.step0BuildFactTrace(extractedFact=fact, sourceChannel="media_external")
        with self.assertRaises(ValueError):
            dmarepository._buildMediaNewsShadowRows(99, [payload])

    # 6. conn.autocommit = False
    def test_transaction_sets_autocommit_false(self):
        fakeConn = makeConn(expectedCount=1)
        self.assertTrue(fakeConn.autocommit)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceMediaNewsShadowTracesTx(
                runId=99, factPayloads=[buildNewsFactPayload()]
            )
        self.assertFalse(fakeConn.autocommit)

    # 7. ESG_MATERIALITY_RUN FOR UPDATE
    def test_transaction_acquires_row_lock(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceMediaNewsShadowTracesTx(
                runId=99, factPayloads=[buildNewsFactPayload()]
            )
        lockSqls = [sql for sql, _ in fakeConn.cursor_obj.executed if "FOR UPDATE" in sql]
        self.assertEqual(len(lockSqls), 1)
        self.assertIn("ESG_MATERIALITY_RUN", lockSqls[0])

    # 8. 기존 활성 News Shadow Row만 soft-delete
    def test_soft_deletes_only_news_namespace(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceMediaNewsShadowTracesTx(
                runId=99, factPayloads=[buildNewsFactPayload()]
            )
        deleteSqls = [p for sql, p in fakeConn.cursor_obj.executed if "delete_yn = 1" in sql]
        self.assertEqual(len(deleteSqls), 1)
        self.assertIn(dmarepository.MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP, deleteSqls[0])

    # 9. Benchmark Namespace를 soft-delete하지 않음
    def test_benchmark_namespace_not_deleted(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceMediaNewsShadowTracesTx(
                runId=99, factPayloads=[buildNewsFactPayload()]
            )
        allParams = [p for _, p in fakeConn.cursor_obj.executed]
        for paramTuple in allParams:
            self.assertNotIn(dmarepository.BENCHMARK_V13_SHADOW_SOURCE_STEP, paramTuple)
            self.assertNotIn(dmarepository.BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP, paramTuple)

    # 10. Fact Row INSERT
    def test_fact_rows_inserted(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            dmarepository.step4ReplaceMediaNewsShadowTracesTx(
                runId=99, factPayloads=[buildNewsFactPayload()]
            )
        self.assertEqual(len(fakeConn.cursor_obj.many_executed), 1)
        insertedRow = fakeConn.cursor_obj.many_executed[0][1][0]
        self.assertEqual(insertedRow[4], dmarepository.MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP)
        self.assertEqual(insertedRow[5], "news")

    # 11. row_count == len(factRows) 검증 → commit
    def test_transaction_commits_on_success(self):
        fakeConn = makeConn(expectedCount=1)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            result = dmarepository.step4ReplaceMediaNewsShadowTracesTx(
                runId=99, factPayloads=[buildNewsFactPayload()]
            )
        self.assertTrue(fakeConn.committed)
        self.assertFalse(fakeConn.rolled_back)
        self.assertEqual(result, 1)

    # 12. Count mismatch → ROLLBACK, COMMIT 미호출
    def test_count_mismatch_rollbacks(self):
        fakeConn = FakeTxConnection(fetchone_map={
            "FOR UPDATE": {"id": 99},
            "COUNT(*)": {"row_count": 0},
        })
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            with self.assertRaises(RuntimeError):
                dmarepository.step4ReplaceMediaNewsShadowTracesTx(
                    runId=99, factPayloads=[buildNewsFactPayload()]
                )
        self.assertFalse(fakeConn.committed)
        self.assertTrue(fakeConn.rolled_back)

    # 13. runId Row 없음 → ROLLBACK
    def test_missing_run_row_rollbacks(self):
        fakeConn = FakeTxConnection(fetchone_map={
            "FOR UPDATE": None,
            "COUNT(*)": {"row_count": 1},
        })
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            with self.assertRaises(RuntimeError):
                dmarepository.step4ReplaceMediaNewsShadowTracesTx(
                    runId=99, factPayloads=[buildNewsFactPayload()]
                )
        self.assertTrue(fakeConn.rolled_back)

    # 14. factPayloads = [] → soft-delete, INSERT 없음, row_count==0, COMMIT
    def test_empty_fact_payloads_soft_deletes_and_commits(self):
        fakeConn = makeConn(expectedCount=0)
        with patch.object(dmarepository, "getConn", return_value=fakeConn):
            result = dmarepository.step4ReplaceMediaNewsShadowTracesTx(
                runId=99, factPayloads=[]
            )
        self.assertEqual(result, 0)
        self.assertTrue(fakeConn.committed)
        self.assertEqual(len(fakeConn.cursor_obj.many_executed), 0)
        deleteSqls = [p for sql, p in fakeConn.cursor_obj.executed if "delete_yn = 1" in sql]
        self.assertEqual(len(deleteSqls), 1)


# ── Service hook tests ───────────────────────────────────────────────────────

class PhaseC21ServiceHookTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()
        import importlib
        sys.modules.pop("src.services.medias.service", None)
        self._service = importlib.import_module("src.services.medias.service")

    def _pipelineResult(self):
        return [buildNewsResult()]

    def _makeScored(self):
        m = MagicMock()
        m.scoringPayloadJson = {}
        m.sourceType = "news"
        return [m]

    def _runWithPatches(self, pipelineReturn=None, scoredReturn=None,
                        normalizeReturn=None, saveSignalsSideEffect=None,
                        txSideEffect=None):
        svc = self._service
        pipelineReturn = pipelineReturn if pipelineReturn is not None else self._pipelineResult()
        scoredReturn = scoredReturn if scoredReturn is not None else self._makeScored()

        dmaruleregistry.resetDmaRulesForTest()
        normalizeReturn = normalizeReturn if normalizeReturn is not None else step0NormalizeMediaFacts(pipelineReturn)

        with patch.object(svc, "processMediaPipeline", return_value=pipelineReturn), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=scoredReturn), \
             patch.object(svc, "saveSignals", side_effect=saveSignalsSideEffect), \
             patch.object(svc, "step0NormalizeMediaFacts", return_value=normalizeReturn) as normMock, \
             patch.object(svc, "step0BuildFactTrace", wraps=svc.step0BuildFactTrace) as traceMock, \
             patch.object(svc, "step4ReplaceMediaNewsShadowBundleTx",
                          side_effect=txSideEffect) as txMock, \
             patch("builtins.print") as printMock:
            result = svc.runMediaAnalysis(articles=[], runId=99)
        return result, normMock, traceMock, txMock, printMock

    # 15. Legacy saveSignals 성공 후 → News Shadow Replace TX 정확히 1회
    def test_shadow_tx_called_once_after_legacy_save(self):
        _, _, _, txMock, _ = self._runWithPatches()
        self.assertEqual(txMock.call_count, 1)
        self.assertEqual(txMock.call_args.kwargs["runId"], 99)

    # 16. Shadow Fact Build → pipelineResults를 사용 (scoredSignals 역변환 금지)
    def test_shadow_fact_built_from_pipeline_results_not_scored_signals(self):
        pipeline = self._pipelineResult()
        _, normMock, _, _, _ = self._runWithPatches(pipelineReturn=pipeline)
        normMock.assert_called_once_with(pipeline)

    # 17. step0BuildFactTrace() → sourceChannel == "media_external"
    def test_build_fact_trace_uses_media_external_channel(self):
        svc = self._service
        dmaruleregistry.resetDmaRulesForTest()
        normalizedFacts = step0NormalizeMediaFacts(self._pipelineResult())

        capturedChannels = []
        origBuildFactTrace = svc.step0BuildFactTrace
        def capturingBuildFactTrace(extractedFact, sourceChannel):
            capturedChannels.append(sourceChannel)
            return origBuildFactTrace(extractedFact=extractedFact, sourceChannel=sourceChannel)

        with patch.object(svc, "processMediaPipeline", return_value=self._pipelineResult()), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=self._makeScored()), \
             patch.object(svc, "saveSignals"), \
             patch.object(svc, "step0NormalizeMediaFacts", return_value=normalizedFacts), \
             patch.object(svc, "step0BuildFactTrace", side_effect=capturingBuildFactTrace), \
             patch.object(svc, "step4ReplaceMediaNewsShadowBundleTx"):
            svc.runMediaAnalysis(articles=[], runId=99)

        self.assertTrue(all(ch == "media_external" for ch in capturedChannels))
        self.assertGreater(len(capturedChannels), 0)

    # 18. Normalize 실패 → RuntimeError 전파, Replace TX 미호출
    def test_normalize_failure_propagates_as_runtime_error(self):
        svc = self._service
        scored = self._makeScored()
        with patch.object(svc, "processMediaPipeline", return_value=[]), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=scored), \
             patch.object(svc, "saveSignals"), \
             patch.object(svc, "step0NormalizeMediaFacts", side_effect=RuntimeError("norm fail")), \
             patch.object(svc, "step4ReplaceMediaNewsShadowBundleTx") as txMock:
            with self.assertRaises(RuntimeError):
                svc.runMediaAnalysis(articles=[], runId=99)
        txMock.assert_not_called()

    # 19. Replace TX 실패 → RuntimeError 전파 (complete crawl shadow replace 실패)
    def test_tx_failure_propagates_as_runtime_error(self):
        scored = self._makeScored()
        with self.assertRaises(RuntimeError):
            self._runWithPatches(
                scoredReturn=scored,
                txSideEffect=RuntimeError("tx boom"),
            )

    # 20. Legacy saveSignals 실패 → Replace TX 미호출, 기존 실패 유지
    def test_legacy_save_failure_skips_shadow_tx(self):
        svc = self._service
        with patch.object(svc, "processMediaPipeline", return_value=self._pipelineResult()), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=self._makeScored()), \
             patch.object(svc, "saveSignals", side_effect=RuntimeError("save boom")), \
             patch.object(svc, "step4ReplaceMediaNewsShadowBundleTx") as txMock:
            with self.assertRaises(RuntimeError):
                svc.runMediaAnalysis(articles=[], runId=99)
        txMock.assert_not_called()

    # 21. pipelineResults = [] → Replace TX factPayloads=[]로 호출
    def test_empty_pipeline_calls_tx_with_empty_payloads(self):
        svc = self._service
        with patch.object(svc, "processMediaPipeline", return_value=[]), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=[]), \
             patch.object(svc, "saveSignals"), \
             patch.object(svc, "step4ReplaceMediaNewsShadowBundleTx") as txMock:
            svc.runMediaAnalysis(articles=[], runId=99)
        txMock.assert_called_once()
        self.assertEqual(txMock.call_args.kwargs["factPayloads"], [])
        self.assertEqual(txMock.call_args.kwargs["canonicalPayloads"], [])


# ── Adapter Scalar Normalization tests ───────────────────────────────────────

class PhaseC21AdapterScalarNormalizationTest(unittest.TestCase):

    # 22. issueSimilarityMatches가 list가 아님 → []
    def test_non_list_input_returns_empty(self):
        self.assertEqual(_sanitizeIssueSimilarityMatches(None), [])
        self.assertEqual(_sanitizeIssueSimilarityMatches({}), [])
        self.assertEqual(_sanitizeIssueSimilarityMatches("string"), [])

    # 23. issueId 내부 nested dict → None
    def test_nested_dict_issue_id_becomes_none(self):
        result = _sanitizeIssueSimilarityMatches([{"issueId": {"nested": "obj"}, "score": 0.5}])
        self.assertIsNone(result[0]["issueId"])

    # 24. subIssueNameKr 내부 nested list → None
    def test_nested_list_sub_issue_name_becomes_none(self):
        result = _sanitizeIssueSimilarityMatches([{"subIssueNameKr": ["a", "b"], "score": 0.5}])
        self.assertIsNone(result[0]["subIssueNameKr"])

    # 25. score 내부 nested dict → None (asFloat returns None)
    def test_nested_dict_score_becomes_none(self):
        result = _sanitizeIssueSimilarityMatches([{"score": {"val": 1}}])
        self.assertIsNone(result[0]["score"])

    # 26. 정상 scalar score 문자열 → float 변환
    def test_string_score_converted_to_float(self):
        result = _sanitizeIssueSimilarityMatches([{"issueId": "E-01", "score": "0.85"}])
        self.assertAlmostEqual(result[0]["score"], 0.85)


# ── Guard tests ───────────────────────────────────────────────────────────────

class PhaseC21GuardTest(unittest.TestCase):

    # 27. 신규 Repository 함수 내부에 Legacy side-effect 없음
    def test_no_legacy_side_effects_in_repository_function(self):
        source = inspect.getsource(dmarepository.step4ReplaceMediaNewsShadowTracesTx)
        for banned in ("recalcStage(", "recalcFinal(", "updateRanks("):
            self.assertNotIn(banned, source)
        self.assertNotIn("ESG_DMA_SCORE_SUMMARY", source)
        self.assertNotIn("ESG_MATERIALITY_SELECTED_SUB_ISSUE", source)

    # 28. service.py에 namespace literal 직접 사용 없음
    def test_service_does_not_hardcode_namespace_literal(self):
        svc_path = Path(__file__).resolve().parents[1] / "src/services/medias/service.py"
        source = svc_path.read_text(encoding="utf-8")
        self.assertNotIn("media_external_news_v13_shadow", source)

    # 29. 신규 Production 파일 0개 (이번 커밋에서 추가된 src/ 파일 없음)
    def test_no_new_production_files(self):
        # service.py, adapter.py, dmarepository.py만 수정됨을 간접 확인:
        # 새 Public 함수는 dmarepository.py에만 있음
        self.assertTrue(hasattr(dmarepository, "step4ReplaceMediaNewsShadowTracesTx"))
        # 별도 media shadow module이 생기지 않았음을 확인
        import src.services.medias as medias_pkg
        import pkgutil
        module_names = [m.name for m in pkgutil.iter_modules(medias_pkg.__path__)]
        self.assertNotIn("media_shadow", module_names)
        self.assertNotIn("news_shadow", module_names)

    # 30. Runtime JSON / manifest capability 비변경
    def test_manifest_capability_still_config_pending(self):
        from pathlib import Path as _Path
        manifest_path = (
            _Path(__file__).resolve().parents[1]
            / "src/resources/dma/v1_3_mvp/manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["capabilities"]["mediaEventCanonicalAdapter"], "CONFIG_PENDING")


# ── C2.1.1 Crawl 빈 결과 처리 테스트 ─────────────────────────────────────────

class PhaseC211CrawlEmptyReplaceTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()
        import importlib
        sys.modules.pop("src.services.medias.crawler", None)
        sys.modules.pop("src.services.medias.service", None)
        self._service = importlib.import_module("src.services.medias.service")

        from src.services.medias.crawler import CrawlExecutionResult
        from src.models.media import MediaSourceBreakdown, MediaCrawlerError, MediaNewsCrawlAnalyzeRequest
        self._CrawlExecutionResult = CrawlExecutionResult
        self._MediaSourceBreakdown = MediaSourceBreakdown
        self._MediaCrawlerError = MediaCrawlerError
        self._Request = MediaNewsCrawlAnalyzeRequest

    def _makeRequest(self):
        return self._Request(
            runId=99,
            sources=["impacton"],
            dateFrom="2026-06-01",
            dateTo="2026-06-11",
        )

    def _makeSuccessBreakdown(self, source="impacton"):
        return self._MediaSourceBreakdown(
            sourceKey=source, sourceLabel="임팩트온",
            requestedYn=True, executedYn=True,
            collectedCount=0, filteredCount=0, savedSignalCount=0,
            status="SUCCESS", errorMessage=None,
        )

    def _runCrawlWithPatches(self, crawlResult, txSideEffect=None):
        svc = self._service
        with patch.object(svc, "crawlNewsArticles", return_value=crawlResult), \
             patch.object(svc, "applySavedSignalCounts", return_value=[]), \
             patch.object(svc, "getMediaCoverage", return_value={"coverageStatus": "LOW"}), \
             patch.object(svc, "countMediaSubIssues", return_value=0), \
             patch.object(svc, "listTopMediaIssues", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun", return_value=0), \
             patch.object(svc, "step4ReplaceMediaNewsShadowBundleTx",
                          side_effect=txSideEffect) as txMock, \
             patch("builtins.print") as printMock:
            result = svc.runMediaCrawlAndAnalyze(self._makeRequest())
        return result, txMock, printMock

    # 35. articles=[], 모든 Source SUCCESS, errors=[] → TX factPayloads=[] 호출
    def test_normal_empty_crawl_calls_shadow_tx_with_empty_payloads(self):
        crawlResult = self._CrawlExecutionResult(
            requestedSources=["impacton"],
            allowedSources=["impacton"],
            sourceBreakdown=[self._makeSuccessBreakdown()],
            articles=[],
            errors=[],
        )
        _, txMock, _ = self._runCrawlWithPatches(crawlResult)
        txMock.assert_called_once()
        self.assertEqual(txMock.call_args.kwargs["factPayloads"], [])
        self.assertEqual(txMock.call_args.kwargs["canonicalPayloads"], [])
        self.assertEqual(txMock.call_args.kwargs["runId"], 99)

    # 36. articles=[], Source FAILED → TX 미호출
    def test_failed_crawl_skips_shadow_tx(self):
        crawlResult = self._CrawlExecutionResult(
            requestedSources=["impacton"],
            allowedSources=["impacton"],
            sourceBreakdown=[self._MediaSourceBreakdown(
                sourceKey="impacton", sourceLabel="임팩트온",
                requestedYn=True, executedYn=True,
                collectedCount=0, filteredCount=0, savedSignalCount=0,
                status="FAILED", errorMessage="network error",
            )],
            articles=[],
            errors=[self._MediaCrawlerError(sourceKey="impacton", message="network error")],
        )
        _, txMock, _ = self._runCrawlWithPatches(crawlResult)
        txMock.assert_not_called()

    # 37. articles=[], Source PARTIAL_FAILED → TX 미호출
    def test_partial_failed_crawl_skips_shadow_tx(self):
        crawlResult = self._CrawlExecutionResult(
            requestedSources=["impacton"],
            allowedSources=["impacton"],
            sourceBreakdown=[self._MediaSourceBreakdown(
                sourceKey="impacton", sourceLabel="임팩트온",
                requestedYn=True, executedYn=True,
                collectedCount=5, filteredCount=0, savedSignalCount=0,
                status="PARTIAL_FAILED", errorMessage="dateParseFailedCount=3",
            )],
            articles=[],
            errors=[self._MediaCrawlerError(sourceKey="impacton", message="dateParseFailedCount=3")],
        )
        _, txMock, _ = self._runCrawlWithPatches(crawlResult)
        txMock.assert_not_called()

    # 38. allowedSources=[] → TX 미호출 (모든 Source 거부됨)
    def test_empty_allowed_sources_skips_shadow_tx(self):
        crawlResult = self._CrawlExecutionResult(
            requestedSources=["impacton"],
            allowedSources=[],
            sourceBreakdown=[],
            articles=[],
            errors=[],
        )
        _, txMock, _ = self._runCrawlWithPatches(crawlResult)
        txMock.assert_not_called()

    # 39. Empty Replace TX 실패 → RuntimeError 전파 (complete crawl empty-clear 실패)
    def test_empty_replace_tx_failure_propagates_as_runtime_error(self):
        crawlResult = self._CrawlExecutionResult(
            requestedSources=["impacton"],
            allowedSources=["impacton"],
            sourceBreakdown=[self._makeSuccessBreakdown()],
            articles=[],
            errors=[],
        )
        with self.assertRaises(RuntimeError):
            self._runCrawlWithPatches(
                crawlResult,
                txSideEffect=RuntimeError("tx boom"),
            )


# ── C2.1.2 Non-empty Partial Crawl Shadow Protection ─────────────────────────

class PhaseC212PartialCrawlProtectionTest(unittest.TestCase):
    def setUp(self):
        dmaruleregistry.resetDmaRulesForTest()
        import importlib
        sys.modules.pop("src.services.medias.crawler", None)
        sys.modules.pop("src.services.medias.service", None)
        self._service = importlib.import_module("src.services.medias.service")

        from src.services.medias.crawler import CrawlExecutionResult
        from src.models.media import MediaSourceBreakdown, MediaCrawlerError, MediaNewsCrawlAnalyzeRequest
        self._CrawlExecutionResult = CrawlExecutionResult
        self._MediaSourceBreakdown = MediaSourceBreakdown
        self._MediaCrawlerError = MediaCrawlerError
        self._Request = MediaNewsCrawlAnalyzeRequest

    def _makeRequest(self):
        return self._Request(runId=99, sources=["impacton", "esgeconomy"],
                             dateFrom="2026-06-01", dateTo="2026-06-11")

    def _makeBreakdown(self, source, status, error=None):
        return self._MediaSourceBreakdown(
            sourceKey=source, sourceLabel=source,
            requestedYn=True, executedYn=True,
            collectedCount=5 if status != "FAILED" else 0,
            filteredCount=5 if status == "SUCCESS" else 0,
            savedSignalCount=0,
            status=status,
            errorMessage=error,
        )

    def _runCrawlWithPatches(self, crawlResult):
        svc = self._service
        with patch.object(svc, "crawlNewsArticles", return_value=crawlResult), \
             patch.object(svc, "processMediaPipeline", return_value=[buildNewsResult()]), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=[]), \
             patch.object(svc, "saveSignals"), \
             patch.object(svc, "applySavedSignalCounts", return_value=[]), \
             patch.object(svc, "getMediaCoverage", return_value={"coverageStatus": "LOW"}), \
             patch.object(svc, "countMediaSubIssues", return_value=0), \
             patch.object(svc, "listTopMediaIssues", return_value=[]), \
             patch.object(svc, "refreshRegulationShadowForRun", return_value=0), \
             patch.object(svc, "refreshKcgsShadowForRun", return_value=0), \
             patch.object(svc, "refreshMediaExternalMaxForRun", return_value=0), \
             patch.object(svc, "step4ReplaceMediaNewsShadowBundleTx") as txMock, \
             patch("builtins.print"):
            svc.runMediaCrawlAndAnalyze(self._makeRequest())
        return txMock

    # 40. 기사 존재 + 모든 Source SUCCESS → Shadow Replace 호출
    def test_articles_with_all_success_calls_shadow_replace(self):
        crawlResult = self._CrawlExecutionResult(
            requestedSources=["impacton", "esgeconomy"],
            allowedSources=["impacton", "esgeconomy"],
            sourceBreakdown=[
                self._makeBreakdown("impacton", "SUCCESS"),
                self._makeBreakdown("esgeconomy", "SUCCESS"),
            ],
            articles=[buildNewsResult()],
            errors=[],
        )
        txMock = self._runCrawlWithPatches(crawlResult)
        txMock.assert_called_once()

    # 41. 기사 존재 + 일부 Source FAILED → Legacy 저장 유지, Shadow Replace 미호출
    def test_articles_with_failed_source_skips_shadow_replace(self):
        crawlResult = self._CrawlExecutionResult(
            requestedSources=["impacton", "esgeconomy"],
            allowedSources=["impacton", "esgeconomy"],
            sourceBreakdown=[
                self._makeBreakdown("impacton", "SUCCESS"),
                self._makeBreakdown("esgeconomy", "FAILED", error="network error"),
            ],
            articles=[buildNewsResult()],
            errors=[self._MediaCrawlerError(sourceKey="esgeconomy", message="network error")],
        )
        txMock = self._runCrawlWithPatches(crawlResult)
        txMock.assert_not_called()

    # 42. 기사 존재 + 일부 Source PARTIAL_FAILED → Legacy 저장 유지, Shadow Replace 미호출
    def test_articles_with_partial_failed_source_skips_shadow_replace(self):
        crawlResult = self._CrawlExecutionResult(
            requestedSources=["impacton", "esgeconomy"],
            allowedSources=["impacton", "esgeconomy"],
            sourceBreakdown=[
                self._makeBreakdown("impacton", "SUCCESS"),
                self._makeBreakdown("esgeconomy", "PARTIAL_FAILED", error="dateParseFailedCount=2"),
            ],
            articles=[buildNewsResult()],
            errors=[self._MediaCrawlerError(sourceKey="esgeconomy", message="dateParseFailedCount=2")],
        )
        txMock = self._runCrawlWithPatches(crawlResult)
        txMock.assert_not_called()

    # 43. C2.1.2 회귀: 기사 존재 + Source FAILED → Legacy saveSignals 1회 호출 유지 + Shadow TX 미호출
    def test_articles_with_failed_source_keeps_legacy_save_and_skips_shadow_replace(self):
        crawlResult = self._CrawlExecutionResult(
            requestedSources=["impacton", "esgeconomy"],
            allowedSources=["impacton", "esgeconomy"],
            sourceBreakdown=[
                self._makeBreakdown("impacton", "SUCCESS"),
                self._makeBreakdown("esgeconomy", "FAILED", error="network error"),
            ],
            articles=[buildNewsResult()],
            errors=[self._MediaCrawlerError(sourceKey="esgeconomy", message="network error")],
        )
        legacySignal = object()
        svc = self._service

        with patch.object(svc, "crawlNewsArticles", return_value=crawlResult), \
             patch.object(svc, "processMediaPipeline", return_value=[buildNewsResult()]), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[legacySignal]), \
             patch.object(svc, "applyMediaBaseline", return_value=[legacySignal]), \
             patch.object(svc, "scoreSignals", return_value=[legacySignal]), \
             patch.object(svc, "saveSignals") as saveMock, \
             patch.object(svc, "applySavedSignalCounts", return_value=[]), \
             patch.object(svc, "getMediaCoverage", return_value={"coverageStatus": "LOW"}), \
             patch.object(svc, "countMediaSubIssues", return_value=0), \
             patch.object(svc, "listTopMediaIssues", return_value=[]), \
             patch.object(svc, "step4ReplaceMediaNewsShadowBundleTx") as txMock:
            svc.runMediaCrawlAndAnalyze(self._makeRequest())

        saveMock.assert_called_once_with(
            runId=99,
            signals=[legacySignal],
            fileId=None,
            sourceTitle="Media Analysis",
        )
        txMock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
