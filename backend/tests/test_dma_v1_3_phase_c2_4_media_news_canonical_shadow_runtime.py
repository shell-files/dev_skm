"""
DMA v1.3 MVP — Phase C2.4 Canonical Shadow Runtime Wiring Tests.

48 tests across 6 sections:
  §14.1  C2.4.0 Micro Patch              (5 tests,  #01-05)
  §14.2  step4BuildTrace                  (3 tests,  #06-08)
  §14.3  Orchestrator Canonical Payloads  (12 tests, #09-20)
  §14.4  Canonical Row Serializer         (8 tests,  #21-28)
  §14.5  Bundle Transaction               (13 tests, #29-41)
  §14.6  Service Hook                     (7 tests,  #42-48)

Pure unit tests. No live DB, no runtime side-effects.
"""

import copy
import json
import unittest
from unittest.mock import MagicMock, call, patch

import src.utils.dmaruleregistry as reg
import src.utils.dmarepository as repo
from src.models.dmaengine import (
    AxisScoreTraceV13,
    ExtractedFactsV13,
    EvidenceSpanV13,
    FactorStatusV13,
    MediaNewsDedupTraceV13,
    MediaNewsEventResolutionTraceV13,
    ScorePurposeV13,
)
from src.services.materialities.orchestrator import step1BuildMediaNewsCanonicalPayloads
from src.utils.dmaruleregistry import DmaRuleValidationError, validateMediaEventResolverPolicy
from src.utils.dmarepository import (
    MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP,
    step4BuildTrace,
)


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
    confidence=0.9,
    candidateId=None,
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


def _makeAxisScore(axis="impact", polarity="negative", score=3.5) -> AxisScoreTraceV13:
    return AxisScoreTraceV13(
        axis=axis,
        polarity=polarity,
        score=score,
        status=FactorStatusV13.AUTO_CONFIRMED,
    )


def _makeMinimalResolution(
    subIssueCode="E_CLIMATE",
    resolverStatus="RESOLVED",
    dedupStatus="UNIQUE",
    candidateId=None,
) -> MediaNewsEventResolutionTraceV13:
    confirmed = f"{subIssueCode}|regulatory_action|2024-01-15" if dedupStatus in ("UNIQUE", "MERGED") else None
    return MediaNewsEventResolutionTraceV13(
        resolverStatus=resolverStatus,
        subIssueCode=subIssueCode,
        normalizedEventType="regulatory_action",
        eventDateBucket="2024-01-15",
        dedup=MediaNewsDedupTraceV13(
            eventGroupCandidateId=candidateId,
            confirmedEventGroupKey=confirmed,
            dedupStatus=dedupStatus,
        ),
    )


def _makeCanonicalPayload(
    subIssueCode="E_CLIMATE",
    axisScores=None,
    resolution=None,
    sourceChannel="media_external",
    source_type="news",
    score_purpose=ScorePurposeV13.CANONICAL_IRO,
) -> dict:
    fact = ExtractedFactsV13(subIssueCode=subIssueCode, sourceType=source_type)
    if resolution is None:
        resolution = _makeMinimalResolution(subIssueCode=subIssueCode)
    return step4BuildTrace(
        scorePurpose=score_purpose,
        sourceChannel=sourceChannel,
        subIssueCode=subIssueCode,
        extractedFacts=fact,
        axisScores=axisScores or [],
        eventResolutionTrace=resolution,
    )


# ---------------------------------------------------------------------------
# DB mock helpers
# ---------------------------------------------------------------------------

class _MockCursor:
    """Context-manager cursor with a fetchone queue; records all SQL calls."""

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


def _happyConn(fact_count=1, canonical_count=1, run_id=1):
    """Return a MockConn pre-loaded with happy-path fetchone queue."""
    cursor = _MockCursor(fetchone_queue=[
        {"id": run_id},
        {"row_count": fact_count},
        {"row_count": canonical_count},
    ])
    return _MockConn(cursor=cursor)


# =========================================================
# §14.1  C2.4.0 Micro Patch  (#01-05)
# =========================================================

class PhaseC240MicroPatchTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()
        self._policy = reg.getPolicy("media_event_resolver_policy")

    # --- CONFLICTED dedup: confirmedEventGroupKey must be None (#01) ---
    def test_01_conflicted_confirmed_key_is_none(self):
        from src.services.medias.eventresolver import resolveMediaNewsEventGroup

        r1 = MediaNewsEventResolutionTraceV13(
            resolverStatus="RESOLVED",
            subIssueCode="E_CLIMATE",
            normalizedEventType="regulatory_action",
            eventDateBucket="2024-01-15",
            dedup=MediaNewsDedupTraceV13(eventGroupCandidateId=None, dedupStatus="UNRESOLVED"),
        )
        r2 = copy.deepcopy(r1)
        results = resolveMediaNewsEventGroup([r1, r2], self._policy)
        # Both have same composite key; candidateId=None for both → CONFLICTED
        for r in results:
            self.assertEqual(r.dedup.dedupStatus, "CONFLICTED")
            self.assertIsNone(r.dedup.confirmedEventGroupKey)

    # --- CONFLICTED ruleTrace preserves candidateCompositeKey (#02) ---
    def test_02_conflicted_rule_trace_has_candidate_composite_key(self):
        from src.services.medias.eventresolver import resolveMediaNewsEventGroup

        r1 = MediaNewsEventResolutionTraceV13(
            resolverStatus="RESOLVED",
            subIssueCode="E_WATER",
            normalizedEventType="spill_event",
            eventDateBucket="2024-03-10",
            dedup=MediaNewsDedupTraceV13(eventGroupCandidateId="cand-A", dedupStatus="UNRESOLVED"),
        )
        r2 = copy.deepcopy(r1)
        r2 = r2.model_copy(update={
            "dedup": MediaNewsDedupTraceV13(eventGroupCandidateId="cand-B", dedupStatus="UNRESOLVED")
        })
        results = resolveMediaNewsEventGroup([r1, r2], self._policy)
        for r in results:
            self.assertEqual(r.dedup.dedupStatus, "CONFLICTED")
            trace = r.dedup.ruleTrace
            self.assertTrue(len(trace) > 0)
            self.assertIn("candidateCompositeKey", trace[0])

    # --- MERGED dedup: confirmedEventGroupKey is NOT None (#03) ---
    def test_03_merged_confirmed_key_is_populated(self):
        from src.services.medias.eventresolver import resolveMediaNewsEventGroup

        r1 = MediaNewsEventResolutionTraceV13(
            resolverStatus="RESOLVED",
            subIssueCode="E_CLIMATE",
            normalizedEventType="regulatory_action",
            eventDateBucket="2024-01-15",
            dedup=MediaNewsDedupTraceV13(eventGroupCandidateId="grp-001", dedupStatus="UNRESOLVED"),
        )
        r2 = copy.deepcopy(r1)
        results = resolveMediaNewsEventGroup([r1, r2], self._policy)
        for r in results:
            self.assertEqual(r.dedup.dedupStatus, "MERGED")
            self.assertIsNotNone(r.dedup.confirmedEventGroupKey)

    # --- Band boundary duplicate → DmaRuleValidationError (#04) ---
    def test_04_band_boundary_duplicate_raises_error(self):
        policy = copy.deepcopy(reg.getAllPolicies()["media_event_resolver_policy.json"])
        # maxExclusive=False → band[0] includes 10; minInclusive=True → band[1] also includes 10
        policy["impactScaleRules"]["bands"] = [
            {"min": 1, "max": 10, "minInclusive": True, "maxExclusive": False, "score": 1},
            {"min": 10, "max": 100, "minInclusive": True, "maxExclusive": True, "score": 2},
            {"min": 100, "max": None, "minInclusive": True, "maxExclusive": False, "score": 3},
        ]
        with self.assertRaises(DmaRuleValidationError) as ctx:
            validateMediaEventResolverPolicy(policy)
        self.assertIn("boundary duplicate", str(ctx.exception))

    # --- Band boundary gap → DmaRuleValidationError (#05) ---
    def test_05_band_boundary_gap_raises_error(self):
        policy = copy.deepcopy(reg.getAllPolicies()["media_event_resolver_policy.json"])
        # maxExclusive=True → band[0] excludes 10; minInclusive=False → band[1] also excludes 10
        policy["impactScaleRules"]["bands"] = [
            {"min": 1, "max": 10, "minInclusive": True, "maxExclusive": True, "score": 1},
            {"min": 10, "max": 100, "minInclusive": False, "maxExclusive": True, "score": 2},
            {"min": 100, "max": None, "minInclusive": True, "maxExclusive": False, "score": 3},
        ]
        with self.assertRaises(DmaRuleValidationError) as ctx:
            validateMediaEventResolverPolicy(policy)
        self.assertIn("boundary gap", str(ctx.exception))


# =========================================================
# §14.2  step4BuildTrace  (#06-08)
# =========================================================

class PhaseC24Step4BuildTraceTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    # --- eventResolutionTrace stored in payload dict (#06) ---
    def test_06_event_resolution_trace_stored_in_payload(self):
        resolution = _makeMinimalResolution()
        payload = step4BuildTrace(
            scorePurpose=ScorePurposeV13.CANONICAL_IRO,
            sourceChannel="media_external",
            subIssueCode="E_CLIMATE",
            extractedFacts=_makeNewsFact(),
            eventResolutionTrace=resolution,
        )
        self.assertIn("eventResolutionTrace", payload)
        self.assertIsNotNone(payload["eventResolutionTrace"])

    # --- eventResolutionTrace serialized at top level of JSON (#07) ---
    def test_07_event_resolution_trace_in_top_level_json(self):
        resolution = _makeMinimalResolution(subIssueCode="E_WATER")
        payload = step4BuildTrace(
            scorePurpose=ScorePurposeV13.CANONICAL_IRO,
            sourceChannel="media_external",
            subIssueCode="E_WATER",
            extractedFacts=ExtractedFactsV13(subIssueCode="E_WATER", sourceType="news"),
            eventResolutionTrace=resolution,
        )
        payload_json = json.dumps(payload)
        parsed = json.loads(payload_json)
        self.assertIn("eventResolutionTrace", parsed)
        ert = parsed["eventResolutionTrace"]
        self.assertEqual(ert["subIssueCode"], "E_WATER")

    # --- eventResolutionTrace is not double-wrapped (#08) ---
    def test_08_event_resolution_trace_is_not_double_wrapped(self):
        resolution = _makeMinimalResolution()
        payload = step4BuildTrace(
            scorePurpose=ScorePurposeV13.CANONICAL_IRO,
            sourceChannel="media_external",
            subIssueCode="E_CLIMATE",
            extractedFacts=_makeNewsFact(),
            eventResolutionTrace=resolution,
        )
        ert = payload["eventResolutionTrace"]
        # Must be a dict, not a list or further nested wrapper
        self.assertIsInstance(ert, dict)
        self.assertNotIn("eventResolutionTrace", ert)


# =========================================================
# §14.3  Orchestrator Canonical Payloads  (#09-20)
# =========================================================

class PhaseC24OrchestratorTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    # --- UNIQUE + RESOLVED → can_compute → non-empty axisScores (#09) ---
    def test_09_unique_resolved_produces_axis_scores(self):
        # affectedCount=1500 → scale=4; probabilityValue=0.7 → likelihood=4 → RESOLVED
        fact = _makeNewsFact()
        payloads = step1BuildMediaNewsCanonicalPayloads([fact], evaluationDate="2024-06-01")
        self.assertEqual(len(payloads), 1)
        self.assertNotEqual(payloads[0]["axisScores"], [])

    # --- MERGED consistent → 1 row for 2 facts (#10) ---
    def test_10_merged_consistent_produces_one_canonical_row(self):
        fact1 = _makeNewsFact(candidateId="grp-001", confidence=0.95)
        fact2 = _makeNewsFact(candidateId="grp-001", confidence=0.70)
        payloads = step1BuildMediaNewsCanonicalPayloads([fact1, fact2], evaluationDate="2024-06-01")
        # Two MERGED facts → 1 canonical row (not 2)
        self.assertEqual(len(payloads), 1)

    # --- MERGED consistent → representative is highest-confidence fact (#11) ---
    def test_11_merged_representative_selected_by_confidence(self):
        fact1 = _makeNewsFact(candidateId="grp-001", confidence=0.95)
        fact2 = _makeNewsFact(candidateId="grp-001", confidence=0.70)
        payloads = step1BuildMediaNewsCanonicalPayloads([fact1, fact2], evaluationDate="2024-06-01")
        self.assertEqual(len(payloads), 1)
        ef = payloads[0]["extractedFacts"]
        self.assertAlmostEqual(ef["classificationConfidence"], 0.95)

    # --- MERGED inconsistent fingerprint → demoted to CONFLICTED audit rows (#12) ---
    def test_12_merged_inconsistent_fingerprint_demotes_to_conflicted(self):
        # Different affectedCount → different scale → inconsistent fingerprints
        fact1 = _makeNewsFact(candidateId="grp-001", affectedCount=1500)
        fact2 = _makeNewsFact(candidateId="grp-001", affectedCount=500)
        payloads = step1BuildMediaNewsCanonicalPayloads([fact1, fact2], evaluationDate="2024-06-01")
        # Both demoted → 2 audit rows with axisScores=[]
        self.assertEqual(len(payloads), 2)
        for p in payloads:
            self.assertEqual(p["axisScores"], [])

    # --- CONFLICTED dedup → audit row, no axis scores (#13) ---
    def test_13_conflicted_dedup_produces_audit_row(self):
        # Two facts with same composite key, different candidateIds → CONFLICTED
        fact1 = _makeNewsFact(candidateId="cand-A")
        fact2 = _makeNewsFact(candidateId="cand-B")
        payloads = step1BuildMediaNewsCanonicalPayloads([fact1, fact2], evaluationDate="2024-06-01")
        for p in payloads:
            self.assertEqual(p["axisScores"], [])

    # --- UNRESOLVED (missing composite key) → audit row (#14) ---
    def test_14_unresolved_produces_audit_row(self):
        # subIssueCode=None → composite key missing → UNRESOLVED
        fact = _makeNewsFact(subIssueCode=None)
        payloads = step1BuildMediaNewsCanonicalPayloads([fact], evaluationDate="2024-06-01")
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["axisScores"], [])

    # --- REJECTED (ratioValue out of range) → audit row (#15) ---
    def test_15_rejected_ratio_value_produces_audit_row(self):
        # ratioValue=5.0 exceeds [0,1] → REJECTED
        fact = _makeNewsFact(ratioValue=5.0)
        payloads = step1BuildMediaNewsCanonicalPayloads([fact], evaluationDate="2024-06-01")
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["axisScores"], [])

    # --- UNIQUE + PARTIAL resolverStatus → can_compute → scorePurpose=CANONICAL_IRO (#16) ---
    def test_16_unique_partial_produces_canonical_iro_payload(self):
        # impactDirection only, no affectedCount/probabilityValue → PARTIAL
        fact = ExtractedFactsV13(
            subIssueCode="E_CLIMATE",
            sourceType="news",
            eventType="regulatory_action",
            eventDate="2024-01-15",
            impactDirection="negative",
        )
        payloads = step1BuildMediaNewsCanonicalPayloads([fact], evaluationDate="2024-06-01")
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["scorePurpose"], "CANONICAL_IRO")

    # --- sourceChannel is always "media_external" (#17) ---
    def test_17_source_channel_is_media_external(self):
        fact = _makeNewsFact()
        payloads = step1BuildMediaNewsCanonicalPayloads([fact], evaluationDate="2024-06-01")
        self.assertEqual(payloads[0]["sourceChannel"], "media_external")

    # --- scorePurpose is always CANONICAL_IRO (#18) ---
    def test_18_score_purpose_is_canonical_iro(self):
        fact = _makeNewsFact()
        payloads = step1BuildMediaNewsCanonicalPayloads([fact], evaluationDate="2024-06-01")
        self.assertEqual(payloads[0]["scorePurpose"], "CANONICAL_IRO")

    # --- extractedFacts preserved in canonical payload (#19) ---
    def test_19_extracted_facts_preserved_in_payload(self):
        fact = _makeNewsFact(subIssueCode="E_BIODIVERSITY")
        payloads = step1BuildMediaNewsCanonicalPayloads([fact], evaluationDate="2024-06-01")
        ef = payloads[0]["extractedFacts"]
        self.assertEqual(ef["subIssueCode"], "E_BIODIVERSITY")
        self.assertEqual(ef["sourceType"], "news")

    # --- Empty facts input returns empty list (#20) ---
    def test_20_empty_facts_returns_empty_list(self):
        payloads = step1BuildMediaNewsCanonicalPayloads([], evaluationDate="2024-06-01")
        self.assertEqual(payloads, [])


# =========================================================
# §14.4  Canonical Row Serializer  (#21-28)
# =========================================================

class PhaseC24CanonicalRowSerializerTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    def _basePayload(self, subIssueCode="E_CLIMATE", axisScores=None):
        return _makeCanonicalPayload(subIssueCode=subIssueCode, axisScores=axisScores)

    # --- source_step namespace is the Canonical Shadow constant (#21) ---
    def test_21_canonical_row_has_correct_namespace(self):
        rows = repo._buildMediaNewsCanonicalShadowRows(1, [self._basePayload()])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP)

    # --- impact score extracted from axisScores (#22) ---
    def test_22_impact_score_extracted_from_axis_scores(self):
        rows = repo._buildMediaNewsCanonicalShadowRows(1, [
            self._basePayload(axisScores=[_makeAxisScore(axis="impact", score=3.5)])
        ])
        self.assertAlmostEqual(rows[0][6], 3.5)

    # --- financial score extracted from axisScores (#23) ---
    def test_23_financial_score_extracted_from_axis_scores(self):
        rows = repo._buildMediaNewsCanonicalShadowRows(1, [
            self._basePayload(axisScores=[_makeAxisScore(axis="financial", polarity="risk", score=2.0)])
        ])
        self.assertAlmostEqual(rows[0][7], 2.0)

    # --- audit row (no axisScores) → impact=None, financial=None (#24) ---
    def test_24_audit_row_has_null_scores(self):
        rows = repo._buildMediaNewsCanonicalShadowRows(1, [self._basePayload(axisScores=[])])
        self.assertIsNone(rows[0][6])
        self.assertIsNone(rows[0][7])

    # --- scorePurpose != CANONICAL_IRO → ValueError (#25) ---
    def test_25_wrong_score_purpose_raises_value_error(self):
        payload = _makeCanonicalPayload(score_purpose=ScorePurposeV13.PRESURVEY_SCREENING)
        with self.assertRaises(ValueError) as ctx:
            repo._buildMediaNewsCanonicalShadowRows(1, [payload])
        self.assertIn("scorePurpose", str(ctx.exception))

    # --- sourceChannel != media_external → ValueError (#26) ---
    def test_26_wrong_source_channel_raises_value_error(self):
        payload = _makeCanonicalPayload(sourceChannel="benchmark")
        with self.assertRaises(ValueError) as ctx:
            repo._buildMediaNewsCanonicalShadowRows(1, [payload])
        self.assertIn("sourceChannel", str(ctx.exception))

    # --- sourceType != news → ValueError (#27) ---
    def test_27_wrong_source_type_raises_value_error(self):
        payload = _makeCanonicalPayload(source_type="leader_sr")
        with self.assertRaises(ValueError) as ctx:
            repo._buildMediaNewsCanonicalShadowRows(1, [payload])
        self.assertIn("sourceType", str(ctx.exception))

    # --- duplicate axis in axisScores → ValueError (#28) ---
    def test_28_duplicate_axis_raises_value_error(self):
        payload = self._basePayload()
        payload_dup = copy.deepcopy(payload)
        payload_dup["axisScores"] = [
            {"axis": "impact", "polarity": "negative", "score": 3.5, "status": "AUTO_CONFIRMED"},
            {"axis": "impact", "polarity": "negative", "score": 2.0, "status": "AUTO_CONFIRMED"},
        ]
        with self.assertRaises(ValueError) as ctx:
            repo._buildMediaNewsCanonicalShadowRows(1, [payload_dup])
        self.assertIn("Duplicate axis", str(ctx.exception))


# =========================================================
# §14.5  Bundle Transaction  (#29-41)
# =========================================================

class PhaseC24BundleTxTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()
        self._fact_p = _makeCanonicalPayload.__func__ if hasattr(_makeCanonicalPayload, "__func__") else _makeCanonicalPayload
        self._fp = step4BuildTrace(
            scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
            sourceChannel="media_external",
            subIssueCode="E_CLIMATE",
            extractedFacts=ExtractedFactsV13(subIssueCode="E_CLIMATE", sourceType="news"),
        )
        self._cp = _makeCanonicalPayload()

    def _run_happy(self, fact_payloads=None, canonical_payloads=None, run_id=1):
        fp = fact_payloads if fact_payloads is not None else [self._fp]
        cp = canonical_payloads if canonical_payloads is not None else [self._cp]
        fc = len(fp)
        cc = len(cp)
        conn = _happyConn(fact_count=fc, canonical_count=cc, run_id=run_id)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            result = repo.step4ReplaceMediaNewsShadowBundleTx(run_id, fp, cp)
        return result, conn

    # --- Row lock SELECT FOR UPDATE contains runId (#29) ---
    def test_29_row_lock_select_for_update_called(self):
        _, conn = self._run_happy(run_id=42)
        log = conn._cursor.sql_log
        lock_calls = [s for kind, s, p in log if kind == "x" and "FOR UPDATE" in s]
        self.assertTrue(len(lock_calls) >= 1)
        lock_params = next(p for kind, s, p in log if kind == "x" and "FOR UPDATE" in s)
        self.assertEqual(lock_params, (42,))

    # --- conn.autocommit is set to False (#30) ---
    def test_30_autocommit_set_false(self):
        _, conn = self._run_happy()
        self.assertFalse(conn.autocommit)

    # --- Soft-delete covers BOTH namespaces in single UPDATE (#31) ---
    def test_31_soft_delete_covers_both_namespaces(self):
        _, conn = self._run_happy()
        update_calls = [(s, p) for kind, s, p in conn._cursor.sql_log
                        if kind == "x" and "SET delete_yn = 1" in s]
        self.assertEqual(len(update_calls), 1)
        _, params = update_calls[0]
        self.assertIn(MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP, params)
        self.assertIn(MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP, params)

    # --- factRows inserted via executemany (#32) ---
    def test_32_fact_rows_inserted_via_executemany(self):
        _, conn = self._run_happy()
        inserts = [(rows) for kind, s, rows in conn._cursor.sql_log if kind == "xm"]
        self.assertGreaterEqual(len(inserts), 1)
        # At least one executemany happened
        all_rows = []
        for rows in inserts:
            if isinstance(rows, list):
                all_rows.extend(rows)
        self.assertGreater(len(all_rows), 0)

    # --- canonicalRows inserted via executemany (#33) ---
    def test_33_canonical_rows_inserted_via_executemany(self):
        _, conn = self._run_happy()
        inserts = [rows for kind, s, rows in conn._cursor.sql_log if kind == "xm"]
        # Expect 2 executemany calls: one for fact, one for canonical
        self.assertEqual(len(inserts), 2)

    # --- fact count verified by SELECT COUNT (#34) ---
    def test_34_fact_count_verified(self):
        _, conn = self._run_happy()
        count_calls = [s for kind, s, p in conn._cursor.sql_log
                       if kind == "x" and "COUNT(*)" in s and MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP in str(p)]
        self.assertEqual(len(count_calls), 1)

    # --- canonical count verified by SELECT COUNT (#35) ---
    def test_35_canonical_count_verified(self):
        _, conn = self._run_happy()
        count_calls = [s for kind, s, p in conn._cursor.sql_log
                       if kind == "x" and "COUNT(*)" in s and MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP in str(p)]
        self.assertEqual(len(count_calls), 1)

    # --- empty payloads still runs row-lock + soft-delete + COMMIT (#36) ---
    def test_36_empty_payloads_still_commits(self):
        conn = _MockConn(cursor=_MockCursor(fetchone_queue=[
            {"id": 1},
            {"row_count": 0},
            {"row_count": 0},
        ]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            result = repo.step4ReplaceMediaNewsShadowBundleTx(1, [], [])
        self.assertEqual(result, 0)
        self.assertTrue(conn.committed)
        lock_calls = [s for kind, s, _ in conn._cursor.sql_log if "FOR UPDATE" in s]
        self.assertEqual(len(lock_calls), 1)

    # --- serialization failure pre-DB → raises before getConn (#37) ---
    def test_37_serialization_failure_raises_before_db_connect(self):
        # Missing extractedFacts → _buildMediaNewsShadowRows raises ValueError
        bad_payload = step4BuildTrace(
            scorePurpose=ScorePurposeV13.PRESURVEY_SCREENING,
            sourceChannel="media_external",
            subIssueCode="E_CLIMATE",
        )
        with patch("src.utils.dmarepository.getConn") as mock_get_conn:
            with self.assertRaises(ValueError):
                repo.step4ReplaceMediaNewsShadowBundleTx(1, [bad_payload], [])
            mock_get_conn.assert_not_called()

    # --- run not found → RuntimeError + rollback (#38) ---
    def test_38_run_not_found_raises_runtime_error(self):
        conn = _MockConn(cursor=_MockCursor(fetchone_queue=[None]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError) as ctx:
                repo.step4ReplaceMediaNewsShadowBundleTx(1, [], [])
        self.assertIn("not found", str(ctx.exception))
        self.assertTrue(conn.rolled_back)

    # --- fact count mismatch → RuntimeError (#39) ---
    def test_39_fact_count_mismatch_raises_runtime_error(self):
        conn = _MockConn(cursor=_MockCursor(fetchone_queue=[
            {"id": 1},
            {"row_count": 99},  # wrong fact count
        ]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError) as ctx:
                repo.step4ReplaceMediaNewsShadowBundleTx(1, [self._fp], [self._cp])
        self.assertIn("shadow count check failed", str(ctx.exception).lower())

    # --- canonical count mismatch → RuntimeError (#40) ---
    def test_40_canonical_count_mismatch_raises_runtime_error(self):
        conn = _MockConn(cursor=_MockCursor(fetchone_queue=[
            {"id": 1},
            {"row_count": 1},   # fact count OK
            {"row_count": 99},  # canonical count wrong
        ]))
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError) as ctx:
                repo.step4ReplaceMediaNewsShadowBundleTx(1, [self._fp], [self._cp])
        self.assertIn("canonical shadow count check failed", str(ctx.exception).lower())

    # --- exception during cursor → rollback AND close called (#41) ---
    def test_41_exception_during_cursor_triggers_rollback_and_close(self):
        cursor = _MockCursor(
            fetchone_queue=[{"id": 1}],
            raise_on_update=True,  # raises when soft-delete UPDATE is executed
        )
        conn = _MockConn(cursor=cursor)
        with patch("src.utils.dmarepository.getConn", return_value=conn):
            with self.assertRaises(RuntimeError):
                repo.step4ReplaceMediaNewsShadowBundleTx(1, [], [])
        self.assertTrue(conn.rolled_back)
        self.assertTrue(conn.closed)


# =========================================================
# §14.6  Service Hook  (#42-48)
# =========================================================

class PhaseC24ServiceHookTest(unittest.TestCase):

    def setUp(self):
        _resetPolicies()

    # --- Normal pipeline: BundleTx called with runId, factPayloads, canonicalPayloads (#42) ---
    def test_42_replace_shadow_calls_bundle_tx(self):
        from src.services.medias.service import _replaceMediaNewsShadowFromPipelineResults

        dummy_fact = _makeNewsFact()
        dummy_fact_payload = {"scorePurpose": "PRESURVEY_SCREENING", "sourceChannel": "media_external"}
        dummy_canonical = [{"scorePurpose": "CANONICAL_IRO", "sourceChannel": "media_external"}]

        with patch("src.services.medias.service.step0NormalizeMediaFacts", return_value=[dummy_fact]), \
             patch("src.services.medias.service.step0BuildFactTrace", return_value=dummy_fact_payload), \
             patch("src.services.medias.service.step1BuildMediaNewsCanonicalPayloads", return_value=dummy_canonical), \
             patch("src.services.medias.service.step4ReplaceMediaNewsShadowBundleTx") as mock_tx:
            _replaceMediaNewsShadowFromPipelineResults(runId=42, pipelineResults=["article"])
            mock_tx.assert_called_once()
            kwargs = mock_tx.call_args
            self.assertEqual(kwargs[1]["runId"], 42)
            self.assertEqual(kwargs[1]["factPayloads"], [dummy_fact_payload])
            self.assertEqual(kwargs[1]["canonicalPayloads"], dummy_canonical)

    # --- Empty crawl: BundleTx called with factPayloads=[] and canonicalPayloads=[] (#43) ---
    def test_43_empty_pipeline_results_calls_bundle_tx_with_empty_payloads(self):
        from src.services.medias.service import _replaceMediaNewsShadowFromPipelineResults

        with patch("src.services.medias.service.step0NormalizeMediaFacts", return_value=[]), \
             patch("src.services.medias.service.step1BuildMediaNewsCanonicalPayloads", return_value=[]), \
             patch("src.services.medias.service.step4ReplaceMediaNewsShadowBundleTx") as mock_tx:
            _replaceMediaNewsShadowFromPipelineResults(runId=1, pipelineResults=[])
            mock_tx.assert_called_once_with(runId=1, factPayloads=[], canonicalPayloads=[])

    # --- shadowReplaceYn=False → BundleTx NOT called (#44) ---
    def test_44_no_shadow_replace_when_shadow_replace_yn_false(self):
        from src.services.medias.service import runMediaAnalysis

        with patch("src.services.medias.service.processMediaPipeline", return_value=[]), \
             patch("src.services.medias.service.convertMediaToDmaSignals", return_value=[]), \
             patch("src.services.medias.service.applyMediaBaseline", return_value=[]), \
             patch("src.services.medias.service.scoreSignals", return_value=[]), \
             patch("src.services.medias.service.step4ReplaceMediaNewsShadowBundleTx") as mock_tx:
            runMediaAnalysis(articles=[], runId=1, shadowReplaceYn=False)
            mock_tx.assert_not_called()

    # --- Shadow TX exception does NOT abort runMediaAnalysis (#45) ---
    #     S5-B16 / Phase C2.4.1 Runtime Safety: News canonical shadow replace 실패는
    #     smoke/fallback 분석(scoredSignals 반환)을 중단시키지 않는다.
    #     _replaceMediaNewsShadowFromPipelineResults 자체는 여전히 예외를 전파하지만
    #     (test_46 참조), runMediaAnalysis 가 이를 흡수하고 경고만 남긴다.
    def test_45_shadow_replace_exception_does_not_abort(self):
        from src.services.medias.service import runMediaAnalysis

        with patch("src.services.medias.service.processMediaPipeline", return_value=[]), \
             patch("src.services.medias.service.convertMediaToDmaSignals", return_value=[]), \
             patch("src.services.medias.service.applyMediaBaseline", return_value=[]), \
             patch("src.services.medias.service.scoreSignals", return_value=[]), \
             patch("src.services.medias.service._replaceMediaNewsShadowFromPipelineResults",
                   side_effect=RuntimeError("TX kaboom")), \
             patch("builtins.print"):
            result = runMediaAnalysis(articles=[], runId=1, shadowReplaceYn=True)
        self.assertEqual(result, [])

    # --- step1BuildMediaNewsCanonicalPayloads failure propagates from _replaceMediaNewsShadowFromPipelineResults (#46) ---
    def test_46_canonical_build_failure_propagates(self):
        from src.services.medias.service import _replaceMediaNewsShadowFromPipelineResults

        with patch("src.services.medias.service.step0NormalizeMediaFacts", return_value=[]), \
             patch("src.services.medias.service.step1BuildMediaNewsCanonicalPayloads",
                   side_effect=ValueError("policy broken")):
            with self.assertRaises(ValueError):
                _replaceMediaNewsShadowFromPipelineResults(runId=1, pipelineResults=[])

    # --- step4ReplaceMediaNewsShadowBundleTx failure propagates from _replaceMediaNewsShadowFromPipelineResults (#47) ---
    def test_47_bundle_tx_failure_propagates(self):
        from src.services.medias.service import _replaceMediaNewsShadowFromPipelineResults

        with patch("src.services.medias.service.step0NormalizeMediaFacts", return_value=[]), \
             patch("src.services.medias.service.step1BuildMediaNewsCanonicalPayloads", return_value=[]), \
             patch("src.services.medias.service.step4ReplaceMediaNewsShadowBundleTx",
                   side_effect=RuntimeError("TX error")):
            with self.assertRaises(RuntimeError):
                _replaceMediaNewsShadowFromPipelineResults(runId=1, pipelineResults=[])

    # --- Legacy saveSignals path is unaffected by shadow replace (#48) ---
    def test_48_legacy_save_signals_not_affected_by_shadow_path(self):
        from src.services.medias.service import runMediaAnalysis

        mock_signal = MagicMock()

        with patch("src.services.medias.service.processMediaPipeline", return_value=[]), \
             patch("src.services.medias.service.convertMediaToDmaSignals", return_value=[]), \
             patch("src.services.medias.service.applyMediaBaseline", return_value=[]), \
             patch("src.services.medias.service.scoreSignals", return_value=[mock_signal]), \
             patch("src.services.medias.service.saveSignals") as mock_save, \
             patch("src.services.medias.service._replaceMediaNewsShadowFromPipelineResults"):
            runMediaAnalysis(articles=["dummy"], runId=99, shadowReplaceYn=True)
            mock_save.assert_called_once()
            save_kwargs = mock_save.call_args
            self.assertEqual(save_kwargs[1]["runId"], 99)


if __name__ == "__main__":
    unittest.main()
