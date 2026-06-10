"""
DMA v1.3 MVP Slim Engine — Screening + Selection helper tests.

Covers Acceptance Test Plan cases:
  Screening 35-48
  Selection 49-56

Pure unit tests. No live DB, no historical fixture, no DB connection.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import dmaruleregistry as reg
from src.utils import dmascreening as scr
from src.utils import dmaselection as sel


class ScreeningTest(unittest.TestCase):
    def setUp(self):
        reg.reset_cache()
        self.policy = reg.get_policy("screening_policy")

    # 35-37. benchmark NONE / COMMON / BLIND_SPOT
    def test_35_benchmark_none(self):
        self.assertEqual(scr.calculate_benchmark_screening_v13("NONE", self.policy).impactSignal, 0.0)

    def test_36_benchmark_common(self):
        self.assertEqual(scr.calculate_benchmark_screening_v13("COMMON_ISSUE", self.policy).impactSignal, 3.0)

    def test_37_benchmark_blind_spot(self):
        self.assertEqual(scr.calculate_benchmark_screening_v13("BLIND_SPOT", self.policy).impactSignal, 4.0)

    # 38. benchmark MAX aggregation
    def test_38_benchmark_max(self):
        signals = [
            scr.calculate_benchmark_screening_v13("NONE", self.policy),
            scr.calculate_benchmark_screening_v13("COMMON_ISSUE", self.policy),
            scr.calculate_benchmark_screening_v13("BLIND_SPOT", self.policy),
        ]
        agg = scr.aggregate_external_screening_by_max_v13(signals, self.policy)
        self.assertEqual(agg.impactSignal, 4.0)
        self.assertEqual(agg.financialSignal, 4.0)

    # 39. CSRD base rule
    def test_39_csrd_base_rule(self):
        r = scr.calculate_regulation_base_screening_v13("CSRD", "DIRECT_MANDATORY", self.policy)
        self.assertEqual((r.impactSignal, r.financialSignal), (3.0, 4.0))

    # 40. CBAM base rule
    def test_40_cbam_base_rule(self):
        r = scr.calculate_regulation_base_screening_v13("CBAM", "DIRECT_MANDATORY", self.policy)
        self.assertEqual((r.impactSignal, r.financialSignal), (4.0, 5.0))

    # 41. DPP base rule
    def test_41_dpp_base_rule(self):
        r = scr.calculate_regulation_base_screening_v13("DPP", "MATERIAL_VALUE_CHAIN", self.policy)
        self.assertEqual((r.impactSignal, r.financialSignal), (3.0, 3.0))

    # 42. regulation UNKNOWN -> UNOBSERVED
    def test_42_regulation_unknown_unobserved(self):
        r = scr.calculate_regulation_base_screening_v13("CSRD", "UNKNOWN", self.policy)
        self.assertIsNone(r.impactSignal)
        self.assertIsNone(r.financialSignal)
        self.assertEqual(r.status, scr.STATUS_UNOBSERVED)

    # 43. regulation NOT_APPLICABLE -> observed 0
    def test_43_regulation_not_applicable_zero(self):
        r = scr.calculate_regulation_base_screening_v13("CBAM", "NOT_APPLICABLE", self.policy)
        self.assertEqual((r.impactSignal, r.financialSignal), (0.0, 0.0))
        self.assertEqual(r.status, scr.STATUS_OBSERVED)

    # 44. KCGS grade map
    def test_44_kcgs_grade_map(self):
        self.assertEqual(scr.calculate_kcgs_pillar_signal_v13("D", "flat", self.policy)["pillarSignal"], 5.0)
        self.assertEqual(scr.calculate_kcgs_pillar_signal_v13("S", "flat", self.policy)["pillarSignal"], 0.0)
        self.assertEqual(scr.calculate_kcgs_pillar_signal_v13("A+", "flat", self.policy)["pillarSignal"], 0.5)

    # 45. KCGS trend modifier
    def test_45_kcgs_trend_modifier(self):
        self.assertEqual(scr.calculate_kcgs_pillar_signal_v13("B", "downgradeTwoOrMore", self.policy)["pillarSignal"], 4.0)
        self.assertEqual(scr.calculate_kcgs_pillar_signal_v13("B", "downgradeOne", self.policy)["pillarSignal"], 3.5)
        insuff = scr.calculate_kcgs_pillar_signal_v13("B", "insufficientData", self.policy)
        self.assertIsNone(insuff["pillarSignal"])
        self.assertEqual(insuff["status"], scr.STATUS_UNOBSERVED)

    # 46. KCGS boost max 1.0
    def test_46_kcgs_boost_max(self):
        # pillar signal 4.5 * 0.20 = 0.9 (under cap)
        self.assertAlmostEqual(scr.calculate_kcgs_subissue_boost_v13(4.5, self.policy), 0.9, places=4)
        # large pillar signal capped at 1.0
        self.assertEqual(scr.calculate_kcgs_subissue_boost_v13(10.0, self.policy), 1.0)
        # unobserved pillar signal -> None
        self.assertIsNone(scr.calculate_kcgs_subissue_boost_v13(None, self.policy))

    # 47. KIS pending capability
    def test_47_kis_pending_capability(self):
        r = scr.calculate_kis_financial_resilience_capability_v13(self.policy)
        self.assertEqual(r.status, scr.STATUS_CAPABILITY_PENDING)
        self.assertEqual(r.capability, "DATA_EXPORT_REQUIRED")
        self.assertIsNone(r.impactSignal)
        self.assertIsNone(r.financialSignal)

    # 48. external MAX (non-additive across channels)
    def test_48_external_max(self):
        signals = [
            scr.calculate_benchmark_screening_v13("COMMON_ISSUE", self.policy),   # 3 / 3
            scr.calculate_regulation_base_screening_v13("CBAM", "DIRECT_MANDATORY", self.policy),  # 4 / 5
            scr.calculate_regulation_base_screening_v13("CSRD", "UNKNOWN", self.policy),  # None / None
        ]
        agg = scr.aggregate_external_screening_by_max_v13(signals, self.policy)
        self.assertEqual(agg.impactSignal, 4.0)     # max(3,4)
        self.assertEqual(agg.financialSignal, 5.0)  # max(3,5)


class SelectionTest(unittest.TestCase):
    def setUp(self):
        reg.reset_cache()
        self.policy = reg.get_policy("selection_policy")

    # 49. canonical axis MAX sort key
    def test_49_max_axis_sort_key(self):
        items = [
            {"subIssueCode": "LOW", "impactScore": 3.0, "financialScore": 3.1},
            {"subIssueCode": "HIGH", "impactScore": 4.8, "financialScore": 3.0},
        ]
        ordered = sel.sort_selection_candidates_v13(sel.build_selection_candidates_v13(items, self.policy), self.policy)
        self.assertEqual(ordered[0]["subIssueCode"], "HIGH")

    # 50. candidate threshold either axis >= 3
    def test_50_candidate_threshold_either_axis(self):
        items = [
            {"subIssueCode": "A", "impactScore": 3.0, "financialScore": 1.0},  # in (impact)
            {"subIssueCode": "B", "impactScore": 1.0, "financialScore": 3.5},  # in (financial)
            {"subIssueCode": "C", "impactScore": 2.9, "financialScore": 2.9},  # out
            {"subIssueCode": "D", "impactScore": None, "financialScore": None},  # out
        ]
        codes = {c["subIssueCode"] for c in sel.build_selection_candidates_v13(items, self.policy)}
        self.assertEqual(codes, {"A", "B"})

    # 51. tie break MIN axis
    def test_51_tie_break_min_axis(self):
        items = [
            {"subIssueCode": "WIDE", "impactScore": 5.0, "financialScore": 3.0},  # max 5, min 3
            {"subIssueCode": "BAL", "impactScore": 5.0, "financialScore": 4.0},   # max 5, min 4
        ]
        ordered = sel.sort_selection_candidates_v13(sel.build_selection_candidates_v13(items, self.policy), self.policy)
        self.assertEqual(ordered[0]["subIssueCode"], "BAL")

    # 52. tie break survey priority rate
    def test_52_tie_break_survey_priority_rate(self):
        items = [
            {"subIssueCode": "LOWP", "impactScore": 4.0, "financialScore": 4.0, "surveyPriorityRate": 0.2},
            {"subIssueCode": "HIGHP", "impactScore": 4.0, "financialScore": 4.0, "surveyPriorityRate": 0.9},
        ]
        ordered = sel.sort_selection_candidates_v13(sel.build_selection_candidates_v13(items, self.policy), self.policy)
        self.assertEqual(ordered[0]["subIssueCode"], "HIGHP")

    # 53. tie break sub-issue code (final, deterministic)
    def test_53_tie_break_sub_issue_code(self):
        items = [
            {"subIssueCode": "ZZZ", "impactScore": 4.0, "financialScore": 4.0, "surveyPriorityRate": 0.5},
            {"subIssueCode": "AAA", "impactScore": 4.0, "financialScore": 4.0, "surveyPriorityRate": 0.5},
        ]
        ordered = sel.sort_selection_candidates_v13(sel.build_selection_candidates_v13(items, self.policy), self.policy)
        self.assertEqual(ordered[0]["subIssueCode"], "AAA")

    # 54. Top10
    def test_54_top10(self):
        items = [{"subIssueCode": f"S{i:02d}", "impactScore": 3.0 + i * 0.1, "financialScore": 3.0} for i in range(15)]
        res = sel.run_selection_v13(items, self.policy)
        self.assertEqual(len(res["recommendedTop10"]), 10)
        # highest impact first
        self.assertEqual(res["recommendedTop10"][0]["subIssueCode"], "S14")

    # 55. Top5
    def test_55_top5(self):
        items = [{"subIssueCode": f"S{i:02d}", "impactScore": 3.0 + i * 0.1, "financialScore": 3.0} for i in range(15)]
        res = sel.run_selection_v13(items, self.policy)
        self.assertEqual(len(res["recommendedTop5"]), 5)

    # 56. manual score override forbidden
    def test_56_manual_score_override_forbidden(self):
        with self.assertRaises(sel.SelectionGovernanceError):
            sel.apply_manual_selection_action_v13(
                {"subIssueCode": "A", "selectionType": "MANUAL_ADD", "overrideScore": 5.0}, self.policy
            )
        # manual ADD / EXCLUDE without a score is allowed
        ok = sel.apply_manual_selection_action_v13(
            {"subIssueCode": "A", "selectionType": "MANUAL_EXCLUDE", "selectionReason": "duplicate"}, self.policy
        )
        self.assertEqual(ok["selectionType"], "MANUAL_EXCLUDE")
        # an unknown selection action is rejected
        with self.assertRaises(sel.SelectionGovernanceError):
            sel.apply_manual_selection_action_v13({"subIssueCode": "A", "selectionType": "AUTO_FORCE"}, self.policy)


if __name__ == "__main__":
    unittest.main()
