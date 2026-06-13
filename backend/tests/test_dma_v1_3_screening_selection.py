"""
DMA v1.3 MVP Slim Engine — Screening + Selection helper tests.

Covers Acceptance Test Plan cases:
  Screening  35-48
  Selection  49-56
  A.1 Patch  63-66 (minAxis missing, KCGS clamp)

Pure unit tests. No live DB, no historical fixture, no DB connection.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import dmaruleregistry as reg
from src.utils import dmascoring as sc


class ScreeningTest(unittest.TestCase):
    def setUp(self):
        reg.resetDmaRulesForTest()
        self.policy = reg.getPolicy("screening_policy")

    # 35-37. benchmark NONE / COMMON / BLIND_SPOT
    def test_35_benchmark_none(self):
        self.assertEqual(sc.step2CalcBenchmark("NONE", self.policy).impactSignal, 0.0)

    def test_36_benchmark_common(self):
        self.assertEqual(sc.step2CalcBenchmark("COMMON_ISSUE", self.policy).impactSignal, 3.0)

    def test_37_benchmark_blind_spot(self):
        self.assertEqual(sc.step2CalcBenchmark("BLIND_SPOT", self.policy).impactSignal, 4.0)

    # 38. benchmark MAX aggregation
    def test_38_benchmark_max(self):
        signals = [
            sc.step2CalcBenchmark("NONE", self.policy),
            sc.step2CalcBenchmark("COMMON_ISSUE", self.policy),
            sc.step2CalcBenchmark("BLIND_SPOT", self.policy),
        ]
        agg = sc.step2CalcExternalMax(signals, self.policy)
        self.assertEqual(agg.impactSignal, 4.0)
        self.assertEqual(agg.financialSignal, 4.0)

    # 39. CSRD base rule
    def test_39_csrd_base_rule(self):
        r = sc.step2CalcRegulation("CSRD", "DIRECT_MANDATORY", self.policy)
        self.assertEqual((r.impactSignal, r.financialSignal), (3.0, 4.0))

    # 40. CBAM base rule
    def test_40_cbam_base_rule(self):
        r = sc.step2CalcRegulation("CBAM", "DIRECT_MANDATORY", self.policy)
        self.assertEqual((r.impactSignal, r.financialSignal), (4.0, 5.0))

    # 41. DPP base rule
    def test_41_dpp_base_rule(self):
        r = sc.step2CalcRegulation("DPP", "MATERIAL_VALUE_CHAIN", self.policy)
        self.assertEqual((r.impactSignal, r.financialSignal), (3.0, 3.0))

    # 42. regulation UNKNOWN -> UNOBSERVED
    def test_42_regulation_unknown_unobserved(self):
        r = sc.step2CalcRegulation("CSRD", "UNKNOWN", self.policy)
        self.assertIsNone(r.impactSignal)
        self.assertIsNone(r.financialSignal)
        self.assertEqual(r.status, sc.STATUS_UNOBSERVED)

    # 43. regulation NOT_APPLICABLE -> observed 0
    def test_43_regulation_not_applicable_zero(self):
        r = sc.step2CalcRegulation("CBAM", "NOT_APPLICABLE", self.policy)
        self.assertEqual((r.impactSignal, r.financialSignal), (0.0, 0.0))
        self.assertEqual(r.status, sc.STATUS_OBSERVED)

    # 44. KCGS grade map
    def test_44_kcgs_grade_map(self):
        self.assertEqual(sc.step2CalcKcgs("D", "flat", self.policy)["pillarSignal"], 5.0)
        self.assertEqual(sc.step2CalcKcgs("S", "flat", self.policy)["pillarSignal"], 0.0)
        self.assertEqual(sc.step2CalcKcgs("A+", "flat", self.policy)["pillarSignal"], 0.5)

    # 45. KCGS trend modifier
    def test_45_kcgs_trend_modifier(self):
        self.assertEqual(sc.step2CalcKcgs("B", "downgradeTwoOrMore", self.policy)["pillarSignal"], 4.0)
        self.assertEqual(sc.step2CalcKcgs("B", "downgradeOne", self.policy)["pillarSignal"], 3.5)
        insuff = sc.step2CalcKcgs("B", "insufficientData", self.policy)
        self.assertIsNone(insuff["pillarSignal"])
        self.assertEqual(insuff["status"], sc.STATUS_UNOBSERVED)

    # 46. KCGS boost max 1.0
    def test_46_kcgs_boost_max(self):
        self.assertAlmostEqual(sc.step2CalcKcgsBoost(4.5, self.policy), 0.9, places=4)
        self.assertEqual(sc.step2CalcKcgsBoost(10.0, self.policy), 1.0)
        self.assertIsNone(sc.step2CalcKcgsBoost(None, self.policy))

    # 47. KIS pending capability
    def test_47_kis_pending_capability(self):
        r = sc.step2GetKisState(self.policy)
        self.assertEqual(r.status, sc.STATUS_CAPABILITY_PENDING)
        self.assertEqual(r.capability, "DATA_EXPORT_REQUIRED")
        self.assertIsNone(r.impactSignal)
        self.assertIsNone(r.financialSignal)

    # 48. external MAX (non-additive across channels)
    def test_48_external_max(self):
        signals = [
            sc.step2CalcBenchmark("COMMON_ISSUE", self.policy),
            sc.step2CalcRegulation("CBAM", "DIRECT_MANDATORY", self.policy),
            sc.step2CalcRegulation("CSRD", "UNKNOWN", self.policy),
        ]
        agg = sc.step2CalcExternalMax(signals, self.policy)
        self.assertEqual(agg.impactSignal, 4.0)
        self.assertEqual(agg.financialSignal, 5.0)


class SelectionTest(unittest.TestCase):
    def setUp(self):
        reg.resetDmaRulesForTest()
        self.policy = reg.getPolicy("selection_policy")

    # 49. canonical axis MAX sort key
    def test_49_max_axis_sort_key(self):
        items = [
            {"subIssueCode": "LOW", "impactScore": 3.0, "financialScore": 3.1},
            {"subIssueCode": "HIGH", "impactScore": 4.8, "financialScore": 3.0},
        ]
        ordered = sc.step3RankIssues(sc.step3BuildCandidates(items, self.policy), self.policy)
        self.assertEqual(ordered[0]["subIssueCode"], "HIGH")

    # 50. candidate threshold either axis >= 3
    def test_50_candidate_threshold_either_axis(self):
        items = [
            {"subIssueCode": "A", "impactScore": 3.0, "financialScore": 1.0},
            {"subIssueCode": "B", "impactScore": 1.0, "financialScore": 3.5},
            {"subIssueCode": "C", "impactScore": 2.9, "financialScore": 2.9},
            {"subIssueCode": "D", "impactScore": None, "financialScore": None},
        ]
        codes = {c["subIssueCode"] for c in sc.step3BuildCandidates(items, self.policy)}
        self.assertEqual(codes, {"A", "B"})

    # 51. tie break MIN axis
    def test_51_tie_break_min_axis(self):
        items = [
            {"subIssueCode": "WIDE", "impactScore": 5.0, "financialScore": 3.0},
            {"subIssueCode": "BAL", "impactScore": 5.0, "financialScore": 4.0},
        ]
        ordered = sc.step3RankIssues(sc.step3BuildCandidates(items, self.policy), self.policy)
        self.assertEqual(ordered[0]["subIssueCode"], "BAL")

    # 52. tie break survey priority rate
    def test_52_tie_break_survey_priority_rate(self):
        items = [
            {"subIssueCode": "LOWP", "impactScore": 4.0, "financialScore": 4.0, "surveyPriorityRate": 0.2},
            {"subIssueCode": "HIGHP", "impactScore": 4.0, "financialScore": 4.0, "surveyPriorityRate": 0.9},
        ]
        ordered = sc.step3RankIssues(sc.step3BuildCandidates(items, self.policy), self.policy)
        self.assertEqual(ordered[0]["subIssueCode"], "HIGHP")

    # 53. tie break sub-issue code (final, deterministic)
    def test_53_tie_break_sub_issue_code(self):
        items = [
            {"subIssueCode": "ZZZ", "impactScore": 4.0, "financialScore": 4.0, "surveyPriorityRate": 0.5},
            {"subIssueCode": "AAA", "impactScore": 4.0, "financialScore": 4.0, "surveyPriorityRate": 0.5},
        ]
        ordered = sc.step3RankIssues(sc.step3BuildCandidates(items, self.policy), self.policy)
        self.assertEqual(ordered[0]["subIssueCode"], "AAA")

    # 54. Top10
    def test_54_top10(self):
        items = [{"subIssueCode": f"S{i:02d}", "impactScore": 3.0 + i * 0.1, "financialScore": 3.0} for i in range(15)]
        res = sc.step3RunSelection(items, self.policy)
        self.assertEqual(len(res["recommendedTop10"]), 10)
        self.assertEqual(res["recommendedTop10"][0]["subIssueCode"], "S14")

    # 55. Top5
    def test_55_top5(self):
        items = [{"subIssueCode": f"S{i:02d}", "impactScore": 3.0 + i * 0.1, "financialScore": 3.0} for i in range(15)]
        res = sc.step3RunSelection(items, self.policy)
        self.assertEqual(len(res["recommendedTop5"]), 5)

    # 56. manual score override forbidden
    def test_56_manual_score_override_forbidden(self):
        with self.assertRaises(sc.SelectionGovernanceError):
            sc.step3ApplyDecision(
                {"subIssueCode": "A", "selectionType": "MANUAL_ADD", "overrideScore": 5.0}, self.policy
            )
        ok = sc.step3ApplyDecision(
            {"subIssueCode": "A", "selectionType": "MANUAL_EXCLUDE", "selectionReason": "duplicate"}, self.policy
        )
        self.assertEqual(ok["selectionType"], "MANUAL_EXCLUDE")
        with self.assertRaises(sc.SelectionGovernanceError):
            sc.step3ApplyDecision({"subIssueCode": "A", "selectionType": "AUTO_FORCE"}, self.policy)


class A1CorrectnessTest(unittest.TestCase):
    """Phase A.1 Correctness Patch — cases 63-66."""

    def setUp(self):
        reg.resetDmaRulesForTest()
        self.selPolicy = reg.getPolicy("selection_policy")
        self.scrPolicy = reg.getPolicy("screening_policy")

    # 63. Impact=5.0 / Financial=None → sortMinAxis=0.0, financialScore remains None
    def test_63_missing_axis_sort_value(self):
        items = [{"subIssueCode": "SINGLE", "impactScore": 5.0, "financialScore": None}]
        ordered = sc.step3RankIssues(sc.step3BuildCandidates(items, self.selPolicy), self.selPolicy)
        self.assertEqual(len(ordered), 1)
        # 정렬 보조값은 0.0이어야 한다. Canonical score는 None 유지.
        self.assertEqual(ordered[0]["sortMinAxis"], 0.0)
        self.assertIsNone(ordered[0]["financialScore"])

    # 64. Impact=5.0 / Financial=3.0 → sortMinAxis=3.0 (두 축 모두 관측)
    def test_64_both_axes_min(self):
        items = [{"subIssueCode": "BOTH", "impactScore": 5.0, "financialScore": 3.0}]
        ordered = sc.step3RankIssues(sc.step3BuildCandidates(items, self.selPolicy), self.selPolicy)
        self.assertAlmostEqual(ordered[0]["sortMinAxis"], 3.0, places=4)

    # 65. KCGS D + downgradeTwoOrMore → pillarSignal=5.0, 6.0 금지
    def test_65_kcgs_pillar_signal_clamp(self):
        # D gradeRisk=5.0, downgradeTwoOrMore trendModifier=1.0 → raw=6.0 → clamped to 5.0
        result = sc.step2CalcKcgs("D", "downgradeTwoOrMore", self.scrPolicy)
        self.assertEqual(result["status"], sc.STATUS_OBSERVED)
        self.assertEqual(result["pillarSignal"], 5.0, "pillarSignal must not exceed pillarSignalMax=5.0")

    # 66. A+ + downgradeTwoOrMore → pillarSignal=1.5 (below cap, no clamp)
    def test_66_kcgs_below_cap_no_clamp(self):
        # A+ gradeRisk=0.5, downgradeTwoOrMore=1.0 → 1.5 < 5.0 → no clamp
        result = sc.step2CalcKcgs("A+", "downgradeTwoOrMore", self.scrPolicy)
        self.assertAlmostEqual(result["pillarSignal"], 1.5, places=4)


if __name__ == "__main__":
    unittest.main()
