import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import calculationengine as engine


def rule(code, target, formula, order=10, unit="KRW", zeroPolicy=None, rounding=None):
    return {
        "calculation_rule_code": code,
        "target_atomic_metric_id": target,
        "metric_id": target.split("__")[0],
        "formula_type": formula,
        "execution_order": order,
        "output_unit": unit,
        "zero_division_policy": zeroPolicy,
        "rounding_policy": rounding,
    }


def source(code, atomic, role="SOURCE", sourceId=1, sourceScope=""):
    return {
        "id": sourceId,
        "calculation_rule_code": code,
        "source_atomic_metric_id": atomic,
        "source_role": role,
        "source_scope": sourceScope,
    }


def fact(atomic, value, unit="KRW"):
    return {"atomic_metric_id": atomic, "value_numeric": value, "unit": unit}


def firstResult(rules, sources, facts, priorFacts=None):
    return engine.calculateRules(rules, sources, facts, priorFacts or [])[0]


class CalculationEngineTest(unittest.TestCase):
    def test_reference_copy(self):
        result = firstResult(
            [rule("R1", "M__R1", "REFERENCE_COPY")],
            [source("R1", "M__Q1")],
            [fact("M__Q1", 7)],
        )
        self.assertEqual(result["calculationStatus"], engine.STATUS_CALCULATED)
        self.assertEqual(result["valueNumeric"], 7)

    def test_entity_sum_and_rollup_add(self):
        rules = [
            rule("R1", "M__D1", "ENTITY_SUM"),
            rule("R2", "M__G1", "ROLLUP_ADD"),
        ]
        sources = [
            source("R1", "M__Q1", sourceId=1),
            source("R1", "M__Q2", sourceId=2),
            source("R2", "M__Q1", sourceId=3),
            source("R2", "M__Q2", sourceId=4),
        ]
        results = engine.calculateRules(rules, sources, [fact("M__Q1", 2), fact("M__Q2", 3)])
        self.assertEqual([result["valueNumeric"] for result in results], [5, 5])

    def test_ratio_divide_and_rounding(self):
        ratioResult = firstResult(
            [rule("R1", "M__R1", "ENTITY_RATIO", rounding="ROUND_2DP")],
            [source("R1", "M__Q1", "NUMERATOR"), source("R1", "M__Q2", "DENOMINATOR", 2)],
            [fact("M__Q1", 1), fact("M__Q2", 3)],
        )
        divideResult = firstResult(
            [rule("R2", "M__R2", "ROLLUP_DIVIDE", rounding="ROUND_0")],
            [source("R2", "M__Q1", "NUMERATOR"), source("R2", "M__Q2", "DENOMINATOR", 2)],
            [fact("M__Q1", 10), fact("M__Q2", 4)],
        )
        self.assertEqual(ratioResult["valueNumeric"], 33.33)
        self.assertEqual(divideResult["valueNumeric"], 2)

    def test_yoy_diff_and_rate(self):
        currentFacts = [fact("M__Q1", 150)]
        priorFacts = [fact("M__Q1", 100)]
        diffResult = firstResult(
            [rule("R1", "M__D1", "ENTITY_YOY_DIFF")],
            [source("R1", "M__Q1", "CURRENT")],
            currentFacts,
            priorFacts,
        )
        rateResult = firstResult(
            [rule("R2", "M__D2", "ROLLUP_YOY_RATE")],
            [source("R2", "M__Q1", "CURRENT")],
            currentFacts,
            priorFacts,
        )
        self.assertEqual(diffResult["valueNumeric"], 50)
        self.assertEqual(rateResult["valueNumeric"], 50)

    def test_zero_division_policies(self):
        flagged = firstResult(
            [rule("R1", "M__R1", "ENTITY_RATIO", zeroPolicy="RETURN_NULL_AND_FLAG")],
            [source("R1", "M__Q1", "NUMERATOR"), source("R1", "M__Q2", "DENOMINATOR", 2)],
            [fact("M__Q1", 1), fact("M__Q2", 0)],
        )
        notApplicable = firstResult(
            [rule("R2", "M__R2", "ENTITY_DIVIDE", zeroPolicy="NOT_APPLICABLE")],
            [source("R2", "M__Q1", "NUMERATOR"), source("R2", "M__Q2", "DENOMINATOR", 2)],
            [fact("M__Q1", 1), fact("M__Q2", 0)],
        )
        self.assertEqual(flagged["calculationStatus"], engine.STATUS_ZERO_DIVISION)
        self.assertEqual(notApplicable["calculationStatus"], engine.STATUS_NOT_APPLICABLE)

    def test_topological_sort_handles_execution_order_inversion(self):
        rules = [
            rule("R_TARGET", "M__D2", "ENTITY_SUM", order=10),
            rule("R_SOURCE", "M__D1", "ENTITY_SUM", order=20),
        ]
        sources = [
            source("R_SOURCE", "M__Q1"),
            source("R_TARGET", "M__D1"),
        ]
        ordered = engine.topologicalSortRules(rules, sources)
        self.assertEqual([item["calculation_rule_code"] for item in ordered], ["R_SOURCE", "R_TARGET"])

    def test_cycle_and_duplicate_target_guards(self):
        with self.assertRaisesRegex(ValueError, "CALCULATION_RULE_CYCLE"):
            engine.topologicalSortRules(
                [rule("R1", "M__D1", "ENTITY_SUM"), rule("R2", "M__D2", "ENTITY_SUM")],
                [source("R1", "M__D2"), source("R2", "M__D1")],
            )
        with self.assertRaisesRegex(ValueError, "CALCULATION_RULE_CYCLE"):
            engine.topologicalSortRules(
                [rule("R1", "M__D1", "ENTITY_SUM")],
                [source("R1", "M__D1")],
            )
        with self.assertRaisesRegex(ValueError, "CALCULATION_TARGET_DUPLICATED"):
            engine.topologicalSortRules(
                [rule("R1", "M__D1", "ENTITY_SUM"), rule("R2", "M__D1", "ENTITY_SUM")],
                [source("R1", "M__Q1"), source("R2", "M__Q2")],
            )

    def test_missing_source_guard(self):
        result = firstResult(
            [rule("R1", "M__D1", "ENTITY_SUM")],
            [source("R1", "M__Q_MISSING")],
            [],
        )
        self.assertEqual(result["calculationStatus"], engine.STATUS_SOURCE_NOT_READY)
        self.assertIsNone(result["valueNumeric"])

    def test_affected_downstream_graph(self):
        rules = [
            rule("R1", "M__D1", "ENTITY_SUM", order=10),
            rule("R2", "M__D2", "ENTITY_SUM", order=20),
            rule("R3", "M__D3", "ENTITY_SUM", order=30),
        ]
        sources = [
            source("R1", "M__Q1"),
            source("R2", "M__D1"),
            source("R3", "OTHER__Q1"),
        ]
        affected = engine.resolveAffectedRuleGraph(rules, sources, ["M__Q1"])
        self.assertEqual([item["calculation_rule_code"] for item in affected], ["R1", "R2"])

    def test_stale_target_fact_is_not_reused_downstream(self):
        rules = [
            rule("R1", "M__D1", "ENTITY_SUM", order=10),
            rule("R2", "M__D2", "ENTITY_SUM", order=20),
        ]
        sources = [
            source("R1", "M__Q1"),
            source("R2", "M__D1"),
        ]
        results = engine.calculateRules(rules, sources, [fact("M__D1", 100)])
        self.assertEqual(
            [result["calculationStatus"] for result in results],
            [engine.STATUS_SOURCE_NOT_READY, engine.STATUS_SOURCE_NOT_READY],
        )

    def test_duplicate_dependency_edge_is_deduped(self):
        rules = [
            rule("R1", "M__D1", "ENTITY_SUM", order=10),
            rule("R2", "M__D2", "ENTITY_SUM", order=20),
        ]
        sources = [
            source("R1", "M__Q1", sourceId=1),
            source("R2", "M__D1", sourceId=2),
            source("R2", "M__D1", sourceId=3),
        ]
        ordered = engine.topologicalSortRules(rules, sources)
        self.assertEqual([item["calculation_rule_code"] for item in ordered], ["R1", "R2"])

    def test_partial_calculation_results_are_not_ready(self):
        self.assertFalse(
            engine.allResultsCalculated(
                [
                    {"calculationStatus": engine.STATUS_CALCULATED},
                    {"calculationStatus": engine.STATUS_SOURCE_NOT_READY},
                ]
            )
        )
        self.assertTrue(engine.allResultsCalculated([{"calculationStatus": engine.STATUS_CALCULATED}]))

    # ── Step 12-C2-R2 new tests ──

    def test_all_results_calculated_empty_list_returns_false(self):
        """allResultsCalculated([]) must return False (§5 empty guard)."""
        self.assertFalse(engine.allResultsCalculated([]))

    def test_all_results_calculated_none_returns_false(self):
        """allResultsCalculated(None) must return False."""
        self.assertFalse(engine.allResultsCalculated(None))

    def test_repository_non_calculated_result_save_blocked(self):
        """Repository must raise ValueError when any result is not CALCULATED (§6 all-or-none)."""
        from src.utils import calculationrepository as calcRepo

        class FakeCursor:
            def execute(self, *a, **kw):
                raise AssertionError("Should not reach DB execute")
            def fetchone(self):
                return None
            def fetchall(self):
                return []

        results = [
            {"calculationStatus": "CALCULATED", "targetAtomicMetricId": "M__D1", "metricId": "M"},
            {"calculationStatus": "CALCULATION_SOURCE_NOT_READY", "targetAtomicMetricId": "M__D2", "metricId": "M"},
        ]
        with self.assertRaisesRegex(ValueError, "CALCULATION_RESULTS_NOT_READY"):
            calcRepo.upsertCalculatedEntityFactsTx(
                FakeCursor(),
                companyId=1,
                reportingYear=2025,
                results=results,
            )

    def test_repository_empty_results_returns_zero(self):
        """Repository returns 0 saved count for empty results (not an error)."""
        from src.utils import calculationrepository as calcRepo

        class FakeCursor:
            pass

        self.assertEqual(
            calcRepo.upsertCalculatedEntityFactsTx(
                FakeCursor(),
                companyId=1,
                reportingYear=2025,
                results=[],
            ),
            0,
        )

    def test_entity_invalidation_sql_contains_scope_condition(self):
        """Entity invalidation SQL must include company_scope_type ENTITY filter (§7)."""
        import inspect
        from src.utils import calculationrepository as calcRepo
        sourceCode = inspect.getsource(calcRepo.invalidateCalculatedEntityFactsTx)
        self.assertIn("company_scope_type", sourceCode)
        self.assertIn("ENTITY", sourceCode)

    def test_calculation_summary_response_shape(self):
        """calculateAffectedEntityFactsTx returns expected observability fields."""
        from src.services.calculations.service import calculateAffectedEntityFactsTx, _emptySummary
        summary = _emptySummary()
        self.assertIn("calculationReadyYn", summary)
        self.assertIn("affectedRuleCount", summary)
        self.assertIn("invalidatedFactCount", summary)
        self.assertIn("calculatedFactCount", summary)
        self.assertIn("calculationWarnings", summary)
        self.assertEqual(summary["affectedRuleCount"], 0)
        self.assertEqual(summary["calculationWarnings"], [])
        self.assertTrue(summary["calculationReadyYn"])

    def test_invalidate_affected_returns_summary(self):
        """invalidateAffectedEntityFactsTx returns expected shape for empty input."""
        from src.services.calculations.service import invalidateAffectedEntityFactsTx
        # Empty changedAtomicMetricIds should return zero counts
        result = invalidateAffectedEntityFactsTx(
            None,  # cur not used for empty input
            companyId=1,
            reportingYear=2025,
            changedAtomicMetricIds=[],
        )
        self.assertEqual(result["affectedRuleCount"], 0)
        self.assertEqual(result["invalidatedFactCount"], 0)

    def test_input_change_detection(self):
        """_atomicValueChanged correctly detects changes vs no-changes."""
        import sys
        from unittest.mock import MagicMock
        sys.modules['jwcrypto'] = MagicMock()
        from src.services.onboardings.service import _atomicValueChanged

        # New insert (oldRow=None) is always a change
        self.assertTrue(_atomicValueChanged(None, {"valueNumeric": 10}))

        # Same value -> no change
        self.assertFalse(_atomicValueChanged(
            {"value_numeric": 10, "value_text": None},
            {"valueNumeric": 10, "valueText": None},
        ))

        # Different numeric -> change
        self.assertTrue(_atomicValueChanged(
            {"value_numeric": 10, "value_text": None},
            {"valueNumeric": 20, "valueText": None},
        ))

        # Different text -> change
        self.assertTrue(_atomicValueChanged(
            {"value_numeric": None, "value_text": "old"},
            {"valueNumeric": None, "valueText": "new"},
        ))

        # Same text -> no change
        self.assertFalse(_atomicValueChanged(
            {"value_numeric": None, "value_text": "same"},
            {"valueNumeric": None, "valueText": "same"},
        ))

    def test_duplicate_sum_source_deduped(self):
        result = firstResult(
            [rule("R1", "M__D1", "ENTITY_SUM")],
            [
                source("R1", "M__Q1", sourceId=1),
                source("R1", "M__Q1", sourceId=2),
            ],
            [fact("M__Q1", 100)],
        )
        self.assertEqual(result["valueNumeric"], 100)

    def test_duplicate_ratio_numerator_source_deduped(self):
        result = firstResult(
            [rule("R1", "M__R1", "ENTITY_RATIO")],
            [
                source("R1", "M__Q1", "NUMERATOR", sourceId=1),
                source("R1", "M__Q1", "NUMERATOR", sourceId=2),
                source("R1", "M__Q2", "DENOMINATOR", sourceId=3),
            ],
            [fact("M__Q1", 50), fact("M__Q2", 100)],
        )
        self.assertEqual(result["valueNumeric"], 50)

    def test_same_atomic_different_role_maintained(self):
        result = firstResult(
            [rule("R1", "M__R1", "ENTITY_RATIO")],
            [
                source("R1", "M__Q1", "NUMERATOR", sourceId=1),
                source("R1", "M__Q1", "DENOMINATOR", sourceId=2),
            ],
            [fact("M__Q1", 50)],
        )
        self.assertEqual(result["valueNumeric"], 100)

    def test_same_atomic_different_scope_maintained(self):
        result = firstResult(
            [rule("R1", "M__D1", "ENTITY_SUM")],
            [
                source("R1", "M__Q1", sourceScope="SCOPE_A", sourceId=1),
                source("R1", "M__Q1", sourceScope="SCOPE_B", sourceId=2),
            ],
            [fact("M__Q1", 100)],
        )
        self.assertEqual(result["valueNumeric"], 200)

    def test_reference_copy_multiple_semantic_sources_ambiguous(self):
        result = firstResult(
            [rule("R1", "M__D1", "REFERENCE_COPY")],
            [
                source("R1", "M__Q1", sourceId=1),
                source("R1", "M__Q2", sourceId=2),
            ],
            [fact("M__Q1", 100), fact("M__Q2", 200)],
        )
        self.assertEqual(result["calculationStatus"], engine.STATUS_REFERENCE_SOURCE_AMBIGUOUS)

    # ── Step 12-C2-R3 YOY direction tests ──

    def _yoyRule(self, code, target, formula, direction=None):
        r = rule(code, target, formula)
        if direction is not None:
            r["yoy_direction_code"] = direction
        return r

    def test_yoy_direction_default_missing_is_current_minus_prior(self):
        """direction 미지정 → CURRENT_MINUS_PRIOR → current=90,prior=100 → diff=-10"""
        result = firstResult(
            [self._yoyRule("R1", "M__D1", "ENTITY_YOY_DIFF")],
            [source("R1", "M__Q1", "CURRENT")],
            [fact("M__Q1", 90)],
            [fact("M__Q1", 100)],
        )
        self.assertEqual(result["calculationStatus"], engine.STATUS_CALCULATED)
        self.assertEqual(result["valueNumeric"], -10)
        self.assertEqual(result["calculationTrace"]["yoyDirectionCode"], engine.YOY_DIRECTION_CURRENT_MINUS_PRIOR)

    def test_yoy_current_minus_prior_diff(self):
        """CURRENT_MINUS_PRIOR diff: current=90,prior=100 → -10"""
        result = firstResult(
            [self._yoyRule("R1", "M__D1", "ENTITY_YOY_DIFF", "CURRENT_MINUS_PRIOR")],
            [source("R1", "M__Q1", "CURRENT")],
            [fact("M__Q1", 90)],
            [fact("M__Q1", 100)],
        )
        self.assertEqual(result["valueNumeric"], -10)

    def test_yoy_current_minus_prior_rate(self):
        """CURRENT_MINUS_PRIOR rate: current=90,prior=100 → -10"""
        result = firstResult(
            [self._yoyRule("R1", "M__D1", "ENTITY_YOY_RATE", "CURRENT_MINUS_PRIOR")],
            [source("R1", "M__Q1", "CURRENT")],
            [fact("M__Q1", 90)],
            [fact("M__Q1", 100)],
        )
        self.assertEqual(result["valueNumeric"], -10)

    def test_yoy_prior_minus_current_diff(self):
        """PRIOR_MINUS_CURRENT diff: current=90,prior=100 → 10"""
        result = firstResult(
            [self._yoyRule("R1", "M__D1", "ENTITY_YOY_DIFF", "PRIOR_MINUS_CURRENT")],
            [source("R1", "M__Q1", "CURRENT")],
            [fact("M__Q1", 90)],
            [fact("M__Q1", 100)],
        )
        self.assertEqual(result["valueNumeric"], 10)
        self.assertEqual(result["calculationTrace"]["yoyDirectionCode"], engine.YOY_DIRECTION_PRIOR_MINUS_CURRENT)

    def test_yoy_prior_minus_current_rate(self):
        """PRIOR_MINUS_CURRENT rate: current=90,prior=100 → 10"""
        result = firstResult(
            [self._yoyRule("R1", "M__D1", "ENTITY_YOY_RATE", "PRIOR_MINUS_CURRENT")],
            [source("R1", "M__Q1", "CURRENT")],
            [fact("M__Q1", 90)],
            [fact("M__Q1", 100)],
        )
        self.assertEqual(result["valueNumeric"], 10)

    def test_entity_yoy_diff_direction_metadata(self):
        """ENTITY_YOY_DIFF: trace에 currentValue/priorValue/delta 포함"""
        result = firstResult(
            [self._yoyRule("R1", "M__D1", "ENTITY_YOY_DIFF", "CURRENT_MINUS_PRIOR")],
            [source("R1", "M__Q1", "CURRENT")],
            [fact("M__Q1", 90)],
            [fact("M__Q1", 100)],
        )
        trace = result["calculationTrace"]
        self.assertEqual(trace["currentValue"], 90)
        self.assertEqual(trace["priorValue"], 100)
        self.assertEqual(trace["delta"], -10)

    def test_rollup_yoy_diff_direction_metadata(self):
        """ROLLUP_YOY_DIFF: PRIOR_MINUS_CURRENT direction metadata 적용"""
        result = firstResult(
            [self._yoyRule("R1", "M__D1", "ROLLUP_YOY_DIFF", "PRIOR_MINUS_CURRENT")],
            [source("R1", "M__Q1", "CURRENT")],
            [fact("M__Q1", 90)],
            [fact("M__Q1", 100)],
        )
        self.assertEqual(result["valueNumeric"], 10)
        self.assertEqual(result["calculationTrace"]["yoyDirectionCode"], engine.YOY_DIRECTION_PRIOR_MINUS_CURRENT)


if __name__ == "__main__":
    unittest.main()
