import json
import unittest
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import rollupbatchrepository as repository


class UnsupportedObject:
    pass


class RollupBatchRepositoryJsonTest(unittest.TestCase):
    def test_json_dumps_serializes_nested_decimal_as_precise_string(self):
        payload = {
            "sourceCompanyValues": {
                "6": Decimal("123.456789"),
                "7": [Decimal("0.000001"), {"value": Decimal("999999999999999999.123456")}],
            }
        }

        parsed = json.loads(repository._jsonDumps(payload))

        self.assertEqual(parsed["sourceCompanyValues"]["6"], "123.456789")
        self.assertEqual(parsed["sourceCompanyValues"]["7"][0], "0.000001")
        self.assertEqual(parsed["sourceCompanyValues"]["7"][1]["value"], "999999999999999999.123456")

    def test_json_dumps_preserves_builtin_json_types(self):
        payload = {
            "int": 1,
            "str": "value",
            "list": [1, "two", True],
            "dict": {"nested": None},
        }

        self.assertEqual(json.loads(repository._jsonDumps(payload)), payload)

    def test_json_dumps_rejects_unsupported_object(self):
        with self.assertRaises(TypeError):
            repository._jsonDumps({"bad": UnsupportedObject()})

    def test_result_params_serializes_decimal_trace_payloads(self):
        batch = {
            "id": 10,
            "reporting_year": 2024,
            "parent_company_id": 6,
        }
        result = {
            "groupMetricId": "M1",
            "groupAtomicMetricId": "M1__G0001",
            "groupAtomicName": "Group Atomic",
            "valueNumeric": Decimal("123.456789"),
            "valueText": None,
            "unit": "KRW",
            "formulaType": "ROLLUP_SUM",
            "sourceCompanyValues": {
                "M1__Q0001": {
                    "6": Decimal("123.456789"),
                    "7": Decimal("0.000001"),
                }
            },
            "calculationTrace": {
                "value": Decimal("999999999999999999.123456"),
                "steps": [{"ratio": Decimal("0.000001")}],
            },
        }

        params = repository.resultParams(batch, result, [6, 7], actorUserId=99)

        self.assertEqual(json.loads(params[5]), [6, 7])
        sourceCompanyValues = json.loads(params[12])
        calculationTrace = json.loads(params[14])
        self.assertEqual(sourceCompanyValues["M1__Q0001"]["6"], "123.456789")
        self.assertEqual(sourceCompanyValues["M1__Q0001"]["7"], "0.000001")
        self.assertEqual(calculationTrace["value"], "999999999999999999.123456")
        self.assertEqual(calculationTrace["steps"][0]["ratio"], "0.000001")


if __name__ == "__main__":
    unittest.main()
