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


def source(code, atomic, role="SOURCE", sourceId=1):
    return {
        "id": sourceId,
        "calculation_rule_code": code,
        "source_atomic_metric_id": atomic,
        "source_role": role,
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


if __name__ == "__main__":
    unittest.main()
