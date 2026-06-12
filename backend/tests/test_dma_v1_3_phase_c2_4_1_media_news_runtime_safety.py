"""
DMA v1.3 MVP — Phase C2.4.1 Media News Runtime Safety Review Tests.

25 tests across 5 sections:
  §13.1  Deterministic MERGED Representative  (5 tests,  #01-05)
  §13.2  Legacy Isolation End-to-End          (5 tests,  #06-10)
  §13.3  Serializer Guard                     (5 tests,  #11-15)
  §13.4  Bundle TX Guard                      (6 tests,  #16-21)
  §13.5  Read Inventory Static Guard          (4 tests,  #22-25)

Pure unit tests. No live DB, no runtime side-effects.
"""

import importlib
import inspect
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import src.utils.dmaruleregistry as reg
import src.utils.dmarepository as repo
from src.models.dmaengine import (
    AxisScoreTraceV13,
    EvidenceSpanV13,
    ExtractedFactsV13,
    FactorStatusV13,
    MediaNewsDedupTraceV13,
    MediaNewsEventResolutionTraceV13,
    ScorePurposeV13,
)
from src.services.materialities.orchestrator import step1BuildMediaNewsCanonicalPayloads
from src.utils.dmarepository import (
    MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP,
    step4BuildTrace,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _resetPolicies():
    reg.resetDmaRulesForTest()


def _makeNewsFact(
    subIssueCode="E_CLIMATE",
    sourceType="news",
    eventType="regulatory_action",
    eventDate="2024-01-15",
    impactDirection="negative",
    affectedCount=1500,
    probabilityValue=0.7,
    confidence=0.8,
    candidateId="grp-001",
    **kwargs,
) -> ExtractedFactsV13:
    return ExtractedFactsV13(
        subIssueCode=subIssueCode,
        sourceType=sourceType,
        eventType=eventType,
        eventDate=eventDate,
        impactDirection=impactDirection,
        affectedCount=affectedCount,
        probabilityValue=probabilityValue,
        classificationConfidence=confidence,
        eventGroupCandidateId=candidateId,
        **kwargs,
    )


def _makeMinimalResolution(
    subIssueCode="E_CLIMATE",
    resolverStatus="RESOLVED",
    dedupStatus="UNIQUE",
) -> MediaNewsEventResolutionTraceV13:
    confirmed = (
        f"{subIssueCode}|regulatory_action|2024-01-15"
        if dedupStatus in ("UNIQUE", "MERGED")
        else None
    )
    return MediaNewsEventResolutionTraceV13(
        resolverStatus=resolverStatus,
        subIssueCode=subIssueCode,
        normalizedEventType="regulatory_action",
        eventDateBucket="2024-01-15",
        dedup=MediaNewsDedupTraceV13(
            confirmedEventGroupKey=confirmed,
            dedupStatus=dedupStatus,
        ),
    )


def _makeCanonicalPayload(
    subIssueCode="E_CLIMATE",
    axisScores=None,
    resolution=None,
    source_type="news",
) -> dict:
    fact = ExtractedFactsV13(subIssueCode=subIssueCode, sourceType=source_type)
    if resolution is None:
        resolution = _makeMinimalResolution(subIssueCode=subIssueCode)
    return step4BuildTrace(
        scorePurpose=ScorePurposeV13.CANONICAL_IRO,
        sourceChannel="media_external",
        subIssueCode=subIssueCode,
        extractedFacts=fact,
        axisScores=axisScores or [],
        eventResolutionTrace=resolution,
    )


def _makeFactPayload(subIssueCode="E_CLIMATE") -> dict:
    return step4BuildTrace(
        scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
        sourceChannel="media_external",
        subIssueCode=subIssueCode,
        extractedFacts=ExtractedFactsV13(subIssueCode=subIssueCode, sourceType="news"),
    )


# Crafted JSON that passes canonical-row validation up to the axis check.
_INVALID_AXIS_JSON = json.dumps({
    "scorePurpose": "CANONICAL_IRO",
    "sourceChannel": "media_external",
    "subIssueCode": "E_CLIMATE",
    "extractedFacts": {"subIssueCode": "E_CLIMATE", "sourceType": "news"},
    "eventResolutionTrace": {"subIssueCode": "E_CLIMATE"},
    "axisScores": [{"axis": "bad_axis"}],
})


class _MockCursor:
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


def _happyConn(fact_count=0, canonical_count=0, run_id=1):
    """MockConn with a fetchone queue for the happy-path TX (lock + fact verify + canonical verify)."""
    cur = _MockCursor(fetchone_queue=[
        {"id": run_id},
        {"row_count": fact_count},
        {"row_count": canonical_count},
    ])
    return _MockConn(cursor=cur)


# ---------------------------------------------------------------------------
# §13.1  Deterministic MERGED Representative  (#01-05)
# ---------------------------------------------------------------------------

class PhaseC241DeterministicMergedTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    def _label(self, facts) -> str:
        """Return rawIssueLabel of the single canonical representative."""
        payloads = step1BuildMediaNewsCanonicalPayloads(facts, evaluationDate="2024-06-01")
        self.assertEqual(len(payloads), 1, "Expected exactly 1 canonical payload (MERGED collapse)")
        ef = payloads[0]["extractedFacts"]
        return ef.get("rawMetadata", {}).get("rawIssueLabel", "")

    def _mergedPair(self, conf_a=0.8, conf_b=0.8, pub_a=None, pub_b=None,
                    url_a=None, url_b=None, label_a="Alpha", label_b="Zulu"):
        spans_a = [EvidenceSpanV13(textSpan="span", publishedAt=pub_a, sourceUrl=url_a)] if (pub_a or url_a) else []
        spans_b = [EvidenceSpanV13(textSpan="span", publishedAt=pub_b, sourceUrl=url_b)] if (pub_b or url_b) else []
        fact_a = _makeNewsFact(
            confidence=conf_a,
            evidenceSpans=spans_a,
            rawMetadata={"rawIssueLabel": label_a},
        )
        fact_b = _makeNewsFact(
            confidence=conf_b,
            evidenceSpans=spans_b,
            rawMetadata={"rawIssueLabel": label_b},
        )
        return fact_a, fact_b

    # --- reversed input order produces same representative (#01) ---
    def test_01_reversed_merged_input_produces_same_representative(self):
        """MERGED pair with identical conf/pub/url but different rawMetadata must yield same
        representative regardless of input order.  Fails if orig_idx is the only tie-break."""
        fact_a, fact_b = self._mergedPair(label_a="Alpha Issue", label_b="Zulu Issue")
        label_fwd = self._label([fact_a, fact_b])
        label_rev = self._label([fact_b, fact_a])
        self.assertEqual(
            label_fwd, label_rev,
            "Representative must be order-independent (stable serialized Fact tie-break required)",
        )

    # --- confidence DESC is the primary sort key (#02) ---
    def test_02_higher_confidence_fact_is_representative(self):
        fact_a, fact_b = self._mergedPair(conf_a=0.95, conf_b=0.70)
        label = self._label([fact_a, fact_b])
        self.assertEqual(label, "Alpha", "Higher-confidence fact must be the representative")

    # --- publishedAt ASC is secondary sort key (#03) ---
    def test_03_earlier_published_at_is_representative(self):
        fact_a, fact_b = self._mergedPair(
            pub_a="2024-01-01", pub_b="2024-12-31",
            url_a="http://same.example", url_b="http://same.example",
        )
        label = self._label([fact_a, fact_b])
        self.assertEqual(label, "Alpha", "Earlier publishedAt must be chosen as representative")

    # --- sourceUrl ASC is tertiary sort key (#04) ---
    def test_04_lower_source_url_is_representative(self):
        fact_a, fact_b = self._mergedPair(
            pub_a="2024-01-01", pub_b="2024-01-01",
            url_a="http://aaa.example", url_b="http://zzz.example",
        )
        label = self._label([fact_a, fact_b])
        self.assertEqual(label, "Alpha", "Lexicographically-lower sourceUrl must be chosen")

    # --- stable Fact tie-break selects lexicographically-smaller serialized fact (#05) ---
    def test_05_stable_fact_tiebreak_selects_deterministic_winner(self):
        """When conf/pub/url are all equal, the stable serialized-Fact tie-break must
        produce the same, deterministic winner regardless of input order.
        'Alpha' serializes before 'Zulu' so fact_a always wins."""
        fact_a, fact_b = self._mergedPair()  # label_a="Alpha", label_b="Zulu"
        label_fwd = self._label([fact_a, fact_b])
        label_rev = self._label([fact_b, fact_a])
        self.assertEqual(label_fwd, label_rev, "Winner must be the same regardless of order")
        self.assertEqual(label_fwd, "Alpha", "Lexicographically-smaller stable key must win")


# ---------------------------------------------------------------------------
# §13.2  Legacy Isolation End-to-End  (#06-10)
# ---------------------------------------------------------------------------

class PhaseC241LegacyIsolationTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()
        sys.modules.pop("src.services.medias.service", None)
        self._svc = importlib.import_module("src.services.medias.service")

    def _run(self, canonical_side_effect=None, tx_side_effect=None):
        svc = self._svc
        mock_signal = MagicMock()
        mock_fact = MagicMock()
        with patch.object(svc, "processMediaPipeline", return_value=["raw_article"]), \
             patch.object(svc, "convertMediaToDmaSignals", return_value=[]), \
             patch.object(svc, "applyMediaBaseline", return_value=[]), \
             patch.object(svc, "scoreSignals", return_value=[mock_signal]), \
             patch.object(svc, "saveSignals") as mock_save, \
             patch.object(svc, "step0NormalizeMediaFacts", return_value=[mock_fact]), \
             patch.object(svc, "step0BuildFactTrace", return_value={}), \
             patch.object(
                 svc, "step1BuildMediaNewsCanonicalPayloads",
                 side_effect=canonical_side_effect,
                 return_value=[],
             ) as mock_builder, \
             patch.object(
                 svc, "step4ReplaceMediaNewsShadowBundleTx",
                 side_effect=tx_side_effect,
             ) as mock_tx, \
             patch("builtins.print"):
            result = svc.runMediaAnalysis(articles=["a1"], runId=99, shadowReplaceYn=True)
        return result, mock_save, mock_builder, mock_tx

    # --- Canonical Builder failure → runMediaAnalysis still returns scoredSignals (#06) ---
    def test_06_canonical_builder_failure_does_not_raise(self):
        result, _, _, _ = self._run(canonical_side_effect=ValueError("resolver exploded"))
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1, "scoredSignals must be returned despite builder failure")

    # --- saveSignals called exactly once even when builder fails (#07) ---
    def test_07_save_signals_called_once_when_builder_fails(self):
        _, mock_save, _, _ = self._run(canonical_side_effect=ValueError("resolver exploded"))
        mock_save.assert_called_once()

    # --- Bundle TX not called when builder raises (#08) ---
    def test_08_bundle_tx_not_called_when_builder_fails(self):
        _, _, _, mock_tx = self._run(canonical_side_effect=ValueError("resolver exploded"))
        mock_tx.assert_not_called()

    # --- Bundle TX failure → runMediaAnalysis still returns scoredSignals (#09) ---
    def test_09_bundle_tx_failure_does_not_raise(self):
        result, _, _, _ = self._run(tx_side_effect=RuntimeError("TX failed"))
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1, "scoredSignals must be returned despite TX failure")

    # --- saveSignals called exactly once even when TX fails (#10) ---
    def test_10_save_signals_called_once_when_tx_fails(self):
        _, mock_save, _, _ = self._run(tx_side_effect=RuntimeError("TX failed"))
        mock_save.assert_called_once()


# ---------------------------------------------------------------------------
# §13.3  Serializer Guard  (#11-15)
# ---------------------------------------------------------------------------

class PhaseC241SerializerGuardTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    # --- extractedFacts missing from payload → ValueError (#11) ---
    def test_11_missing_extracted_facts_raises_value_error(self):
        payload = step4BuildTrace(
            scorePurpose=ScorePurposeV13.CANONICAL_IRO,
            sourceChannel="media_external",
            subIssueCode="E_CLIMATE",
            extractedFacts=None,
            eventResolutionTrace=_makeMinimalResolution(),
        )
        with self.assertRaises(ValueError) as ctx:
            repo._buildMediaNewsCanonicalShadowRows(1, [payload])
        self.assertIn("extractedFacts", str(ctx.exception))

    # --- eventResolutionTrace missing from payload → ValueError (#12) ---
    def test_12_missing_event_resolution_trace_raises_value_error(self):
        payload = step4BuildTrace(
            scorePurpose=ScorePurposeV13.CANONICAL_IRO,
            sourceChannel="media_external",
            subIssueCode="E_CLIMATE",
            extractedFacts=ExtractedFactsV13(subIssueCode="E_CLIMATE", sourceType="news"),
            eventResolutionTrace=None,
        )
        with self.assertRaises(ValueError) as ctx:
            repo._buildMediaNewsCanonicalShadowRows(1, [payload])
        self.assertIn("eventResolutionTrace", str(ctx.exception))

    # --- extractedFacts.subIssueCode ≠ payload.subIssueCode → ValueError (#13) ---
    def test_13_extracted_facts_sub_issue_mismatch_raises_value_error(self):
        payload = step4BuildTrace(
            scorePurpose=ScorePurposeV13.CANONICAL_IRO,
            sourceChannel="media_external",
            subIssueCode="E_CLIMATE",
            extractedFacts=ExtractedFactsV13(subIssueCode="E_WATER", sourceType="news"),
            eventResolutionTrace=_makeMinimalResolution(subIssueCode="E_CLIMATE"),
        )
        with self.assertRaises(ValueError) as ctx:
            repo._buildMediaNewsCanonicalShadowRows(1, [payload])
        self.assertIn("mismatch", str(ctx.exception))
        self.assertIn("E_WATER", str(ctx.exception))

    # --- eventResolutionTrace.subIssueCode ≠ payload.subIssueCode → ValueError (#14) ---
    def test_14_ert_sub_issue_mismatch_raises_value_error(self):
        payload = step4BuildTrace(
            scorePurpose=ScorePurposeV13.CANONICAL_IRO,
            sourceChannel="media_external",
            subIssueCode="E_CLIMATE",
            extractedFacts=ExtractedFactsV13(subIssueCode="E_CLIMATE", sourceType="news"),
            eventResolutionTrace=_makeMinimalResolution(subIssueCode="E_WATER"),
        )
        with self.assertRaises(ValueError) as ctx:
            repo._buildMediaNewsCanonicalShadowRows(1, [payload])
        self.assertIn("mismatch", str(ctx.exception))
        self.assertIn("E_WATER", str(ctx.exception))

    # --- invalid axis in serialized payload → ValueError (#15) ---
    def test_15_invalid_axis_in_serialized_payload_raises_value_error(self):
        with patch("src.utils.dmarepository.step4WriteTrace", return_value=_INVALID_AXIS_JSON):
            with self.assertRaises(ValueError) as ctx:
                repo._buildMediaNewsCanonicalShadowRows(1, [{}])
        self.assertIn("Invalid axis", str(ctx.exception))
        self.assertIn("bad_axis", str(ctx.exception))


# ---------------------------------------------------------------------------
# §13.4  Bundle TX Guard  (#16-21)
# ---------------------------------------------------------------------------

class PhaseC241BundleTxGuardTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    # --- getConn returns None → RuntimeError before any DB interaction (#16) ---
    def test_16_none_conn_raises_runtime_error(self):
        with patch("src.utils.dmarepository.getConn", return_value=None):
            with self.assertRaises(RuntimeError) as ctx:
                repo.step4ReplaceMediaNewsShadowBundleTx(1, [], [])
        self.assertIn("not available", str(ctx.exception))

    # --- Canonical serialization fails → getConn is never called (#17) ---
    def test_17_canonical_serialize_fail_prevents_conn_acquisition(self):
        bad_payload = _makeCanonicalPayload(source_type="not_news")
        with patch("src.utils.dmarepository.getConn") as mock_gc:
            with self.assertRaises(ValueError):
                repo.step4ReplaceMediaNewsShadowBundleTx(1, [], [bad_payload])
        mock_gc.assert_not_called()

    # --- Fact count mismatch → rollback + close (#18) ---
    def test_18_fact_count_mismatch_triggers_rollback_and_close(self):
        fact_p = _makeFactPayload()
        can_p = _makeCanonicalPayload()
        cur = _MockCursor(fetchone_queue=[
            {"id": 1},
            {"row_count": 99},   # wrong fact count (expected 1)
        ])
        conn = _MockConn(cursor=cur)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError) as ctx:
                repo.step4ReplaceMediaNewsShadowBundleTx(1, [fact_p], [can_p])
        self.assertIn("Fact shadow count check failed", str(ctx.exception))
        self.assertTrue(conn.rolled_back, "Connection must be rolled back on count mismatch")
        self.assertTrue(conn.closed, "Connection must be closed in finally block")

    # --- Canonical count mismatch → rollback + close (#19) ---
    def test_19_canonical_count_mismatch_triggers_rollback_and_close(self):
        fact_p = _makeFactPayload()
        can_p = _makeCanonicalPayload()
        cur = _MockCursor(fetchone_queue=[
            {"id": 1},
            {"row_count": 1},    # fact count ok
            {"row_count": 99},   # wrong canonical count (expected 1)
        ])
        conn = _MockConn(cursor=cur)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError) as ctx:
                repo.step4ReplaceMediaNewsShadowBundleTx(1, [fact_p], [can_p])
        self.assertIn("Canonical shadow count check failed", str(ctx.exception))
        self.assertTrue(conn.rolled_back)
        self.assertTrue(conn.closed)

    # --- Happy-path TX → commit and close (#20) ---
    def test_20_happy_path_commits_and_closes_connection(self):
        fact_p = _makeFactPayload()
        can_p = _makeCanonicalPayload()
        conn = _MockConn(cursor=_MockCursor(fetchone_queue=[
            {"id": 1},
            {"row_count": 1},
            {"row_count": 1},
        ]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            repo.step4ReplaceMediaNewsShadowBundleTx(1, [fact_p], [can_p])
        self.assertTrue(conn.committed, "Connection must be committed on success")
        self.assertFalse(conn.rolled_back, "Must not rollback on success")
        self.assertTrue(conn.closed, "Connection must always be closed in finally block")

    # --- Empty bundle → no INSERT calls + commit + return 0 (#21) ---
    def test_21_empty_bundle_no_inserts_commits_and_returns_zero(self):
        conn = _happyConn(fact_count=0, canonical_count=0)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            result = repo.step4ReplaceMediaNewsShadowBundleTx(1, [], [])
        insert_calls = [c for c in conn._cursor.sql_log if c[0] == "xm"]
        self.assertEqual(len(insert_calls), 0, "executemany must not be called for empty bundle")
        self.assertEqual(result, 0, "Return value must be 0 for empty bundle")
        self.assertTrue(conn.committed)
        self.assertTrue(conn.closed)


# ---------------------------------------------------------------------------
# §13.5  Read Inventory Static Guard  (#22-25)
# ---------------------------------------------------------------------------

class PhaseC241ReadInventoryGuardTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    # --- service.py active runtime calls BundleTx, never TracesTx (#22) ---
    def test_22_service_uses_bundle_tx_only(self):
        svc = importlib.import_module("src.services.medias.service")
        src_text = inspect.getsource(svc)
        self.assertIn(
            "step4ReplaceMediaNewsShadowBundleTx", src_text,
            "service.py must call step4ReplaceMediaNewsShadowBundleTx",
        )
        self.assertNotIn(
            "step4ReplaceMediaNewsShadowTracesTx", src_text,
            "service.py active runtime must NOT reference the legacy TracesTx",
        )

    # --- orchestrator + service active paths contain no Summary/Rank mutations (#23) ---
    def test_23_no_summary_or_rank_calls_in_canonical_path(self):
        orch = importlib.import_module("src.services.materialities.orchestrator")
        svc = importlib.import_module("src.services.medias.service")
        orch_src = inspect.getsource(orch)
        svc_src = inspect.getsource(svc)
        forbidden = ["recalcStage(", "upsertStage(", "recalcFinal(", "updateRanks("]
        for fn in forbidden:
            self.assertNotIn(fn, orch_src, f"orchestrator.py must not call {fn}")
            self.assertNotIn(fn, svc_src, f"service.py must not call {fn}")

    # --- Canonical namespace literal is defined only in dmarepository (SSOT) (#24) ---
    def test_24_canonical_namespace_literal_ssot_in_dmarepository(self):
        literal = "media_external_news_v13_canonical_shadow"
        violations = []
        for py_file in (_BACKEND_ROOT / "src").rglob("*.py"):
            if "dmarepository" in py_file.name:
                continue
            try:
                text = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if literal in text:
                violations.append(str(py_file.relative_to(_BACKEND_ROOT)))
        self.assertEqual(
            violations, [],
            f"Canonical namespace literal must only appear in dmarepository.py; "
            f"found in: {violations}",
        )

    # --- Manifest mediaEventCanonicalAdapter == CONFIG_PENDING (#25) ---
    def test_25_manifest_media_event_canonical_adapter_is_config_pending(self):
        manifest_path = (
            _BACKEND_ROOT / "src" / "resources" / "dma" / "v1_3_mvp" / "manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cap = manifest.get("capabilities", {}).get("mediaEventCanonicalAdapter")
        self.assertEqual(
            cap, "CONFIG_PENDING",
            f"manifest.json mediaEventCanonicalAdapter must remain CONFIG_PENDING, got {cap!r}",
        )


if __name__ == "__main__":
    unittest.main()
