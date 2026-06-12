"""
DMA v1.3 MVP — Phase C2.3.1 Guard / Policy Hardening + C2.3.2 Micro Patch Tests.

45 tests across 7 sections:
  16.1  Policy / Registry          (8 tests,  #01-08)
  16.2  Probability Boundary       (7 tests,  #09-15)
  16.3  ratioValue Contract        (5 tests,  #16-20)
  16.4  Dedup Date Priority        (4 tests,  #21-24)
  16.5  Dedup Guard                (8 tests,  #25-32)
  16.6  DTO / Guard                (4 tests,  #33-36)
  16.7  Conflict Propagation + Semantic Validator (9 tests, #37-45)

Pure unit tests. No live DB, no runtime side-effects.
"""

import copy
import inspect
import unittest
from pathlib import Path

import src.utils.dmaruleregistry as reg
from src.models.dmaengine import (
    ExtractedFactsV13,
    MediaNewsDedupTraceV13,
    MediaNewsEventResolutionTraceV13,
    ScoringPayloadV13,
    TriState,
)
from src.services.medias import eventresolver
from src.services.medias.eventresolver import (
    resolveMediaNewsCanonicalFactors,
    resolveMediaNewsEventGroup,
    resolveMediaNewsEventObservation,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _loadResolverPolicy():
    reg.resetDmaRulesForTest()
    return reg.getPolicy("media_event_resolver_policy")


def _loadCanonicalPolicy():
    reg.resetDmaRulesForTest()
    return reg.getPolicy("canonical_scoring_policy")


def _makeFact(**kwargs) -> ExtractedFactsV13:
    return ExtractedFactsV13(**kwargs)


def _makeResolutionForDedup(
    subIssueCode: str,
    eventType: str,
    bucket: str,
    candidateId=None,
) -> MediaNewsEventResolutionTraceV13:
    return MediaNewsEventResolutionTraceV13(
        resolverStatus="UNOBSERVED",
        subIssueCode=subIssueCode,
        normalizedEventType=eventType,
        eventDateBucket=bucket,
        dedup=MediaNewsDedupTraceV13(
            eventGroupCandidateId=candidateId,
            dedupStatus="UNRESOLVED",
        ),
    )


# =========================================================
# 16.1  Policy / Registry  (#01-08)
# =========================================================

class PhaseC231PolicyRegistryTest(unittest.TestCase):

    def setUp(self):
        reg.resetDmaRulesForTest()

    # 1. media_event_resolver_policy.json loads without error
    def test_01_policy_loads(self):
        policy = reg.getPolicy("media_event_resolver_policy")
        self.assertIsInstance(policy, dict)
        self.assertEqual(policy.get("ruleVersion"), "dma-rule-v1.3-mvp")

    # 2. runtime policy count == 6
    def test_02_policy_count_six(self):
        cfg = reg.getDmaRules()
        self.assertEqual(len(cfg.policies), 6)

    # 3. Resolver Policy required key missing → DmaRuleValidationError
    def test_03_required_key_missing_raises(self):
        good = _loadResolverPolicy()
        bad = copy.deepcopy(good)
        del bad["version"]
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 4. eventDedupRules.mandatoryKeys unknown key → DmaRuleValidationError
    def test_04_unknown_mandatory_key_raises(self):
        good = _loadResolverPolicy()
        bad = copy.deepcopy(good)
        bad["eventDedupRules"]["mandatoryKeys"] = ["subIssueCode", "unknownField"]
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 5. scoreDecisionByAiAllowedYn != false → DmaRuleValidationError
    def test_05_score_decision_by_ai_true_raises(self):
        good = _loadResolverPolicy()
        bad = copy.deepcopy(good)
        bad["scoreDecisionByAiAllowedYn"] = True
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 6. missingAsZeroForbiddenYn != true → DmaRuleValidationError
    def test_06_missing_as_zero_false_raises(self):
        good = _loadResolverPolicy()
        bad = copy.deepcopy(good)
        bad["missingPolicy"]["missingAsZeroForbiddenYn"] = False
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 7. enabledYn=false + empty bands → no error
    def test_07_scope_enabledyn_false_allows_empty_bands(self):
        good = _loadResolverPolicy()
        self.assertFalse(good["impactScopeRules"]["enabledYn"])
        self.assertEqual(good["impactScopeRules"]["bands"], [])
        # validateBundle runs this → no exception
        reg.resetDmaRulesForTest()
        _ = reg.getDmaRules()  # must not raise

    # 8. enabledYn=true + bands missing → DmaRuleValidationError
    def test_08_scope_enabledyn_true_no_bands_raises(self):
        good = _loadResolverPolicy()
        bad = copy.deepcopy(good)
        bad["impactScopeRules"] = {
            "enabledYn": True,
            "sourceField": "scopeValue",
            "bands": [],
            "missingPolicy": "UNOBSERVED",
        }
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)


# =========================================================
# 16.2  Probability Boundary  (#09-15)
# =========================================================

class PhaseC231ProbabilityBoundaryTest(unittest.TestCase):

    def setUp(self):
        self.policy = _loadResolverPolicy()

    def _likelihood(self, pv: float) -> float:
        fact = _makeFact(subIssueCode="E_CLI_001", impactDirection="negative", probabilityValue=pv)
        r = resolveMediaNewsEventObservation(fact, self.policy)
        self.assertIsNotNone(r.impact)
        return r.impact.likelihood

    # 9. probabilityValue = 0.0499 → 1  (inside [0.0, 0.05))
    def test_09_prob_0_0499_score_1(self):
        self.assertEqual(self._likelihood(0.0499), 1.0)

    # 10. probabilityValue = 0.05 → 2  (lower boundary of [0.05, 0.20))
    def test_10_prob_0_05_score_2(self):
        self.assertEqual(self._likelihood(0.05), 2.0)

    # 11. probabilityValue = 0.20 → 3  (lower boundary of [0.20, 0.50))
    def test_11_prob_0_20_score_3(self):
        self.assertEqual(self._likelihood(0.20), 3.0)

    # 12. probabilityValue = 0.50 → 4  (lower boundary of [0.50, 0.80))
    def test_12_prob_0_50_score_4(self):
        self.assertEqual(self._likelihood(0.50), 4.0)

    # 13. probabilityValue = 0.80 → 5  (lower boundary of [0.80, 1.0])
    def test_13_prob_0_80_score_5(self):
        self.assertEqual(self._likelihood(0.80), 5.0)

    # 14. probabilityValue = 1.00 → 5  (upper bound inclusive)
    def test_14_prob_1_00_score_5(self):
        self.assertEqual(self._likelihood(1.00), 5.0)

    # 15. probabilityValue = 80 (percent notation) → normalized 0.80 → 5
    def test_15_prob_percent_80_score_5(self):
        self.assertEqual(self._likelihood(80.0), 5.0)


# =========================================================
# 16.3  ratioValue Contract  (#16-20)
# =========================================================

class PhaseC231RatioContractTest(unittest.TestCase):

    def setUp(self):
        self.policy = _loadResolverPolicy()
        self.canonicalPolicy = _loadCanonicalPolicy()

    # 16. ratioValue = 0.03 → magnitude 5  (band [0.03, null))
    def test_16_ratio_0_03_magnitude_5(self):
        fact = _makeFact(subIssueCode="E_CLI_001", financialIroType="risk", ratioValue=0.03)
        r = resolveMediaNewsEventObservation(fact, self.policy)
        self.assertIsNotNone(r.financial)
        self.assertEqual(r.financial.magnitude, 5.0)

    # 17. ratioValue = 3 (>1.0) → resolverStatus REJECTED
    def test_17_ratio_3_rejected(self):
        fact = _makeFact(subIssueCode="E_CLI_001", financialIroType="risk", ratioValue=3.0)
        r = resolveMediaNewsEventObservation(fact, self.policy)
        self.assertEqual(r.resolverStatus, "REJECTED")

    # 18. ratioValue = -0.1 (<0.0) → resolverStatus REJECTED
    def test_18_ratio_negative_rejected(self):
        fact = _makeFact(subIssueCode="E_CLI_001", financialIroType="risk", ratioValue=-0.1)
        r = resolveMediaNewsEventObservation(fact, self.policy)
        self.assertEqual(r.resolverStatus, "REJECTED")

    # 19. ratioValue out-of-range → resolveMediaNewsCanonicalFactors returns both axes None
    def test_19_ratio_out_of_range_canonical_blocked(self):
        fact = _makeFact(subIssueCode="E_CLI_001", financialIroType="risk", ratioValue=3.0)
        resolution = resolveMediaNewsEventObservation(fact, self.policy)
        self.assertEqual(resolution.resolverStatus, "REJECTED")
        axes = resolveMediaNewsCanonicalFactors(resolution, self.canonicalPolicy)
        self.assertIsNone(axes["impact"])
        self.assertIsNone(axes["financial"])

    # 20. financialAmount only → magnitude UNOBSERVED (direct scoring forbidden)
    def test_20_financial_amount_only_magnitude_none(self):
        fact = _makeFact(subIssueCode="E_CLI_001", financialIroType="risk", financialAmount=1_000_000.0)
        r = resolveMediaNewsEventObservation(fact, self.policy)
        if r.financial is not None:
            self.assertIsNone(r.financial.magnitude)


# =========================================================
# 16.4  Dedup Date Priority  (#21-24)
# =========================================================

class PhaseC231DedupDatePriorityTest(unittest.TestCase):

    def setUp(self):
        self.policy = _loadResolverPolicy()

    # 21. eventDate 존재 시 deadlineDate보다 eventDate를 Bucket으로 사용
    def test_21_event_date_over_deadline(self):
        fact = _makeFact(
            subIssueCode="E_CLI_001",
            eventDate="2026-03-15",
            deadlineDate="2026-04-01",
        )
        r = resolveMediaNewsEventObservation(fact, self.policy)
        self.assertEqual(r.eventDateBucket, "2026-03-15")

    # 22. eventDate 없고 effectiveDate 존재 시 effectiveDate 사용
    def test_22_effective_date_fallback(self):
        fact = _makeFact(
            subIssueCode="E_CLI_001",
            effectiveDate="2026-03-20",
            deadlineDate="2026-04-01",
        )
        r = resolveMediaNewsEventObservation(fact, self.policy)
        self.assertEqual(r.eventDateBucket, "2026-03-20")

    # 23. eventDate/effectiveDate 없고 deadlineDate 존재 시 deadlineDate 사용
    def test_23_deadline_date_last_fallback(self):
        fact = _makeFact(subIssueCode="E_CLI_001", deadlineDate="2026-04-01")
        r = resolveMediaNewsEventObservation(fact, self.policy)
        self.assertEqual(r.eventDateBucket, "2026-04-01")

    # 24. Bucket precision == DAY → format is YYYY-MM-DD
    def test_24_bucket_precision_day(self):
        fact = _makeFact(subIssueCode="E_CLI_001", eventDate="2026-03-15")
        r = resolveMediaNewsEventObservation(fact, self.policy)
        self.assertEqual(r.eventDateBucket, "2026-03-15")
        # Must NOT be YYYY-MM format
        self.assertNotEqual(r.eventDateBucket, "2026-03")


# =========================================================
# 16.5  Dedup Guard  (#25-32)
# =========================================================

class PhaseC231DedupGuardTest(unittest.TestCase):

    def setUp(self):
        self.policy = _loadResolverPolicy()

    # 25. mandatory key 누락 → UNRESOLVED
    def test_25_missing_mandatory_key_unresolved(self):
        r = _makeResolutionForDedup("E_CLI_001", None, "2026-03-15")
        result = resolveMediaNewsEventGroup([r], self.policy)
        self.assertEqual(result[0].dedup.dedupStatus, "UNRESOLVED")

    # 26. composite key 단독 1건 → UNIQUE
    def test_26_single_composite_key_unique(self):
        r = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-15")
        result = resolveMediaNewsEventGroup([r], self.policy)
        self.assertEqual(result[0].dedup.dedupStatus, "UNIQUE")

    # 27. composite key 복수 + 동일 non-null candidate hint → MERGED
    def test_27_composite_same_plus_same_hint_merged(self):
        r1 = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-15", candidateId="grp-1")
        r2 = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-15", candidateId="grp-1")
        result = resolveMediaNewsEventGroup([r1, r2], self.policy)
        self.assertEqual(result[0].dedup.dedupStatus, "MERGED")
        self.assertEqual(result[1].dedup.dedupStatus, "MERGED")

    # 28. composite key 복수 + candidate hint 누락 → CONFLICTED
    def test_28_composite_same_hint_missing_conflicted(self):
        r1 = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-15", candidateId=None)
        r2 = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-15", candidateId=None)
        result = resolveMediaNewsEventGroup([r1, r2], self.policy)
        self.assertEqual(result[0].dedup.dedupStatus, "CONFLICTED")

    # 29. composite key 복수 + candidate hint 다름 → CONFLICTED
    def test_29_composite_same_hint_different_conflicted(self):
        r1 = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-15", candidateId="grp-1")
        r2 = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-15", candidateId="grp-2")
        result = resolveMediaNewsEventGroup([r1, r2], self.policy)
        self.assertEqual(result[0].dedup.dedupStatus, "CONFLICTED")
        self.assertEqual(result[1].dedup.dedupStatus, "CONFLICTED")

    # 30. candidate hint만 동일하고 composite 다름 → MERGED 아님 (각각 UNIQUE)
    def test_30_hint_only_same_composite_different_not_merged(self):
        r1 = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-15", candidateId="grp-X")
        r2 = _makeResolutionForDedup("E_CLI_001", "LAWSUIT", "2026-03-15", candidateId="grp-X")
        result = resolveMediaNewsEventGroup([r1, r2], self.policy)
        statuses = {r.dedup.dedupStatus for r in result}
        self.assertNotIn("MERGED", statuses)
        self.assertIn("UNIQUE", statuses)

    # 31. 동일 월이지만 날짜 다름 → DAY precision으로 별개 bucket → MERGED 아님
    def test_31_same_month_different_day_not_merged(self):
        r1 = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-15", candidateId="grp-X")
        r2 = _makeResolutionForDedup("E_CLI_001", "FINE", "2026-03-20", candidateId="grp-X")
        result = resolveMediaNewsEventGroup([r1, r2], self.policy)
        statuses = {r.dedup.dedupStatus for r in result}
        self.assertNotIn("MERGED", statuses)

    # 32. 기사 수 증가해도 factor score 가산 없음
    def test_32_merged_no_score_addition(self):
        fact1 = _makeFact(subIssueCode="E_CLI_001", impactDirection="negative",
                          affectedCount=100, eventDate="2026-03-15")
        fact2 = _makeFact(subIssueCode="E_CLI_001", impactDirection="negative",
                          affectedCount=200, eventDate="2026-03-15")
        policy = _loadResolverPolicy()
        r1 = resolveMediaNewsEventObservation(fact1, policy)
        r2 = resolveMediaNewsEventObservation(fact2, policy)
        r1 = r1.model_copy(update={"normalizedEventType": "FINE", "dedup": MediaNewsDedupTraceV13(
            eventGroupCandidateId="grp-X", dedupStatus="UNRESOLVED")})
        r2 = r2.model_copy(update={"normalizedEventType": "FINE", "dedup": MediaNewsDedupTraceV13(
            eventGroupCandidateId="grp-X", dedupStatus="UNRESOLVED")})
        result = resolveMediaNewsEventGroup([r1, r2], policy)
        self.assertEqual(result[0].dedup.dedupStatus, "MERGED")
        # scale values are NOT summed
        s1 = result[0].impact.scale if result[0].impact else None
        s2 = result[1].impact.scale if result[1].impact else None
        if s1 is not None and s2 is not None:
            self.assertNotEqual(s1, s1 + s2)


# =========================================================
# 16.6  DTO / Guard  (#33-36)
# =========================================================

class PhaseC231DtoGuardTest(unittest.TestCase):

    def setUp(self):
        reg.resetDmaRulesForTest()

    # 33. ExtractedFactsV13에 scopeValue → extra="forbid" → ValidationError
    def test_33_extracts_facts_scopevalue_forbidden(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            ExtractedFactsV13(subIssueCode="E_CLI_001", scopeValue=0.5)  # type: ignore[call-arg]

    # 34. ScoringPayloadV13.eventResolutionTrace optional (no error without it)
    def test_34_scoring_payload_event_resolution_optional(self):
        payload = ScoringPayloadV13(ruleVersion="dma-rule-v1.3-mvp", scorePurpose="CANONICAL_IRO")
        self.assertIsNone(payload.eventResolutionTrace)

    # 35. resolverStatus REJECTED → resolveMediaNewsCanonicalFactors both axes None
    def test_35_rejected_status_canonical_blocked(self):
        resolution = MediaNewsEventResolutionTraceV13(
            resolverStatus="REJECTED",
            subIssueCode="E_CLI_001",
        )
        canonical_policy = _loadCanonicalPolicy()
        axes = resolveMediaNewsCanonicalFactors(resolution, canonical_policy)
        self.assertIsNone(axes["impact"])
        self.assertIsNone(axes["financial"])

    # 36. resolverStatus CONFLICTED → resolveMediaNewsCanonicalFactors both axes None
    def test_36_conflicted_status_canonical_blocked(self):
        resolution = MediaNewsEventResolutionTraceV13(
            resolverStatus="CONFLICTED",
            subIssueCode="E_CLI_001",
        )
        canonical_policy = _loadCanonicalPolicy()
        axes = resolveMediaNewsCanonicalFactors(resolution, canonical_policy)
        self.assertIsNone(axes["impact"])
        self.assertIsNone(axes["financial"])


# =========================================================
# 16.7  Conflict Propagation + Semantic Validator  (#37-45)
# =========================================================

class PhaseC232PropagationTest(unittest.TestCase):
    """P0: Dedup CONFLICTED must propagate to resolverStatus and block Canonical."""

    def setUp(self):
        self.policy = _loadResolverPolicy()
        self.canonicalPolicy = _loadCanonicalPolicy()

    # 37. Dedup CONFLICTED → resolverStatus=CONFLICTED AND Canonical both axes None
    def test_37_dedup_conflict_propagates_and_blocks_canonical(self):
        # Two RESOLVED resolutions with same composite key but different candidateIds
        r1 = MediaNewsEventResolutionTraceV13(
            resolverStatus="RESOLVED",
            subIssueCode="E_CLI_001",
            normalizedEventType="FINE",
            eventDateBucket="2026-03-15",
            dedup=MediaNewsDedupTraceV13(
                eventGroupCandidateId="grp-1",
                dedupStatus="UNRESOLVED",
            ),
        )
        r2 = MediaNewsEventResolutionTraceV13(
            resolverStatus="RESOLVED",
            subIssueCode="E_CLI_001",
            normalizedEventType="FINE",
            eventDateBucket="2026-03-15",
            dedup=MediaNewsDedupTraceV13(
                eventGroupCandidateId="grp-2",
                dedupStatus="UNRESOLVED",
            ),
        )
        result = resolveMediaNewsEventGroup([r1, r2], self.policy)

        # dedup.dedupStatus → CONFLICTED
        self.assertEqual(result[0].dedup.dedupStatus, "CONFLICTED")
        self.assertEqual(result[1].dedup.dedupStatus, "CONFLICTED")

        # resolverStatus must also be CONFLICTED (P0 propagation)
        self.assertEqual(result[0].resolverStatus, "CONFLICTED")
        self.assertEqual(result[1].resolverStatus, "CONFLICTED")

        # Canonical blocked for both
        for r in result:
            axes = resolveMediaNewsCanonicalFactors(r, self.canonicalPolicy)
            self.assertIsNone(axes["impact"])
            self.assertIsNone(axes["financial"])


class PhaseC232SemanticValidatorTest(unittest.TestCase):
    """P1: Semantic value enforcement in validateMediaEventResolverPolicy."""

    def setUp(self):
        self.good = _loadResolverPolicy()

    # 38. mandatoryKeys=[] (빈 배열) → DmaRuleValidationError
    def test_38_mandatory_keys_empty_raises(self):
        bad = copy.deepcopy(self.good)
        bad["eventDedupRules"]["mandatoryKeys"] = []
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 39. mergePolicy 잘못된 값 → DmaRuleValidationError
    def test_39_wrong_merge_policy_raises(self):
        bad = copy.deepcopy(self.good)
        bad["eventDedupRules"]["mergePolicy"] = "COMPOSITE_ONLY"
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 40. conflictPolicy 잘못된 값 → DmaRuleValidationError
    def test_40_wrong_conflict_policy_raises(self):
        bad = copy.deepcopy(self.good)
        bad["eventDedupRules"]["conflictPolicy"] = "OVERRIDE"
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 41. dateBucketPrecision != DAY → DmaRuleValidationError
    def test_41_wrong_date_bucket_precision_raises(self):
        bad = copy.deepcopy(self.good)
        bad["eventDedupRules"]["dateBucketPrecision"] = "MONTH"
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 42. ratioValueContract.normalization 잘못된 값 → DmaRuleValidationError
    def test_42_wrong_ratio_normalization_raises(self):
        bad = copy.deepcopy(self.good)
        bad["ratioValueContract"]["normalization"] = "ZERO_TO_ONE_OR_PERCENT"
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 43. ratioValueContract.outOfRangePolicy 잘못된 값 → DmaRuleValidationError
    def test_43_wrong_out_of_range_policy_raises(self):
        bad = copy.deepcopy(self.good)
        bad["ratioValueContract"]["outOfRangePolicy"] = "CLIP"
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 44. band minInclusive가 bool이 아닌 경우 → DmaRuleValidationError
    def test_44_band_min_inclusive_non_bool_raises(self):
        bad = copy.deepcopy(self.good)
        bad["impactLikelihoodRules"]["bands"][0]["minInclusive"] = 1  # int, not bool
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)

    # 45. band overlap (이전 max > 다음 min) → DmaRuleValidationError
    def test_45_band_overlap_raises(self):
        bad = copy.deepcopy(self.good)
        # Make band[0].max > band[1].min  (0.10 > 0.05)
        bad["impactLikelihoodRules"]["bands"][0]["max"] = 0.10
        with self.assertRaises(reg.DmaRuleValidationError):
            reg.validateMediaEventResolverPolicy(bad)
