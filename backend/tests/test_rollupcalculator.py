import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.rollup import (
    RollupBatchRequestDto,
    RollupBatchStatusDto,
    RollupCalculateResponseDto,
    RollupCalculateStatusDto,
    RollupResultDto,
)
from src.services.rollups import service as rollupService
from src.utils import rollupcalculator as calculator
from src.utils import rollupscoperepository as scopeRepository


def rule(code, target, formula, metricId="M1", order=10):
    return {
        "calculation_rule_code": code,
        "target_atomic_metric_id": target,
        "formula_type": formula,
        "metric_id": metricId,
        "execution_order": order,
    }


def source(code, atomic, role="SOURCE", sourceId=1):
    return {
        "id": sourceId,
        "calculation_rule_code": code,
        "source_atomic_metric_id": atomic,
        "source_role": role,
    }


def fact(companyId, atomic, value):
    return {
        "companyId": companyId,
        "atomicMetricId": atomic,
        "valueNumeric": value,
    }


def factMap(facts):
    return calculator.buildMultiCompanyFactMap(
        sorted({item["companyId"] for item in facts}),
        sorted({item["atomicMetricId"] for item in facts}),
        facts,
    )


def calculate(rules, sources, currentFacts, priorFacts=None, companyIds=None):
    companyIds = companyIds or [1, 2]
    currentMap = calculator.buildMultiCompanyFactMap(
        companyIds,
        sorted({item["atomicMetricId"] for item in currentFacts}),
        currentFacts,
    )
    priorFacts = priorFacts or []
    priorMap = calculator.buildMultiCompanyFactMap(
        companyIds,
        sorted({item["atomicMetricId"] for item in priorFacts}),
        priorFacts,
    )
    return calculator.calculateConsolidatedRules(rules, sources, currentMap, priorMap, companyIds)


class FakeCursor:
    def __init__(self):
        self.fetchoneValue = {"id": 77}

    def __enter__(self):
        return self

    def __exit__(self, excType, exc, tb):
        return False

    def execute(self, *args, **kwargs):
        return None

    def fetchone(self):
        return self.fetchoneValue


class FakeConn:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=True):
        return FakeCursor()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        return None


class FakeRepository:
    ROLLUP_PURPOSE_DMA_PRECHECK = "DMA_PRECHECK"
    ROLLUP_PURPOSE_REPORT_DISCLOSURE = "REPORT_DISCLOSURE"
    METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
    METRIC_SCOPE_SELECTED_DISCLOSURE = "SELECTED_DISCLOSURE"
    TRANSFER_STATUS_RECEIVED = "received"
    TRANSFER_STATUS_SENT = "sent"

    def __init__(self):
        self.conn = FakeConn()
        self.persistCalls = []

    def getBatch(self, batchId):
        return {
            "id": batchId,
            "parent_company_id": 6,
            "reporting_year": 2024,
            "included_company_ids_json": "[6, 7]",
            "rollup_purpose_code": "DMA_PRECHECK",
            "metric_scope_code": "G0_02_FINANCIAL_BASIS",
            "batch_status": "pending",
            "dma_ready_yn": 0,
            "report_ready_yn": 0,
        }

    def listSources(self, batchId):
        return [
            {"parent_company_id": 6, "source_company_id": 6, "transfer_status": "received"},
            {"parent_company_id": 6, "source_company_id": 7, "transfer_status": "sent"},
        ]

    def getConn(self):
        return self.conn

    def listScope(self, batchId):
        return [{"metric_id": "G0-02"}]

    def listBatchRules(self, metricIds):
        return [rule("R1", "T1", "ROLLUP_SUM")]

    def listBatchRuleSources(self, ruleCodes):
        return [source("R1", "S1")]

    def resolveConsolidatedRuleClosure(self, metricIds):
        return self.listBatchRules(metricIds), self.listBatchRuleSources(["R1"])

    def resolveRequiredSourceAtomicIdsTx(self, cur, batchId):
        return ["S1"]

    def resolveExternalEntitySourceAtomicIdsTx(self, cur, batchId):
        return ["S1"]

    def listApprovedFactsByCompany(self, companyIds, reportingYear, atomicIds):
        return []

    def listPriorYearApprovedFactsByCompany(self, companyIds, reportingYear, atomicIds):
        return []

    def upsertGroupRollupResultsTx(self, *args):
        self.persistCalls.append("upsert")

    def updateSourceStatusTx(self, *args):
        self.persistCalls.append("sourceStatus")

    def finalizeDmaPrecheckTx(self, *args):
        self.persistCalls.append("finalizeDma")

    def finalizeReportDisclosureTx(self, *args):
        self.persistCalls.append("finalizeReport")


class RollupCalculatorTest(unittest.TestCase):
    def test_multi_company_rollup_sum(self):
        results, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_SUM")],
            [source("R1", "S1")],
            [fact(1, "S1", 10), fact(2, "S1", 20)],
        )
        self.assertTrue(success, warnings)
        self.assertEqual(results[0]["valueNumeric"], 30)

    def test_rollup_ratio_recalc(self):
        results, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_RATIO_RECALC")],
            [source("R1", "S1", "NUMERATOR"), source("R1", "S2", "DENOMINATOR", 2)],
            [fact(1, "S1", 10), fact(2, "S1", 20), fact(1, "S2", 40), fact(2, "S2", 60)],
        )
        self.assertTrue(success, warnings)
        self.assertEqual(results[0]["valueNumeric"], 30)

    def test_rollup_divide(self):
        results, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_DIVIDE")],
            [source("R1", "S1", "NUMERATOR"), source("R1", "S2", "DENOMINATOR", 2)],
            [fact(1, "S1", 10), fact(2, "S1", 20), fact(1, "S2", 5), fact(2, "S2", 5)],
        )
        self.assertTrue(success, warnings)
        self.assertEqual(results[0]["valueNumeric"], 3)

    def test_rollup_yoy_diff(self):
        results, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_YOY_DIFF")],
            [source("R1", "S1", "CURRENT")],
            [fact(1, "S1", 10), fact(2, "S1", 20)],
            [fact(1, "S1", 5), fact(2, "S1", 15)],
        )
        self.assertTrue(success, warnings)
        self.assertEqual(results[0]["valueNumeric"], 10)

    def test_rollup_yoy_rate(self):
        results, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_YOY_RATE")],
            [source("R1", "S1", "CURRENT")],
            [fact(1, "S1", 10), fact(2, "S1", 20)],
            [fact(1, "S1", 5), fact(2, "S1", 15)],
        )
        self.assertTrue(success, warnings)
        self.assertEqual(results[0]["valueNumeric"], 50)

    def test_prior_missing(self):
        _, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_YOY_DIFF")],
            [source("R1", "S1", "CURRENT")],
            [fact(1, "S1", 10), fact(2, "S1", 20)],
            [fact(1, "S1", 5)],
        )
        self.assertFalse(success)
        self.assertIn("CALCULATION_SOURCE_NOT_READY", warnings[0]["error"])

    def test_current_company_source_missing(self):
        _, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_SUM")],
            [source("R1", "S1")],
            [fact(1, "S1", 10)],
            companyIds=[1, 2],
        )
        self.assertFalse(success)
        self.assertIn("CALCULATION_SOURCE_NOT_READY", warnings[0]["error"])

    def test_reference_copy_same_value(self):
        results, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_REFERENCE_COPY")],
            [source("R1", "S1")],
            [fact(1, "S1", 5), fact(2, "S1", 5)],
        )
        self.assertTrue(success, warnings)
        self.assertEqual(results[0]["valueNumeric"], 5)

    def test_reference_copy_different_value(self):
        _, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_REFERENCE_COPY")],
            [source("R1", "S1")],
            [fact(1, "S1", 5), fact(2, "S1", 10)],
        )
        self.assertFalse(success)
        self.assertIn("CALCULATION_REFERENCE_VALUE_AMBIGUOUS", warnings[0]["error"])

    def test_topo_dependency_uses_group_result_once(self):
        results, warnings, success = calculate(
            [rule("R2", "T2", "ROLLUP_SUM", order=20), rule("R1", "T1", "ROLLUP_SUM", order=10)],
            [source("R1", "S1"), source("R2", "T1")],
            [fact(1, "S1", 10), fact(2, "S1", 20)],
        )
        self.assertTrue(success, warnings)
        byTarget = {item["groupAtomicMetricId"]: item["valueNumeric"] for item in results}
        self.assertEqual(byTarget["T1"], 30)
        self.assertEqual(byTarget["T2"], 30)

    def test_partial_failure_all_or_none_service(self):
        fakeRepository = FakeRepository()
        originalLoadRepository = rollupService.loadRepository
        originalLoadCalculator = rollupService.loadCalculator
        originalCheckScope = rollupService.checkScope
        originalCalculate = calculator.calculateConsolidatedRules
        try:
            rollupService.loadRepository = lambda: fakeRepository
            rollupService.loadCalculator = lambda: calculator
            rollupService.checkScope = lambda companyId, userModel: None
            calculator.calculateConsolidatedRules = lambda *args, **kwargs: (
                [],
                [{"ruleCode": "R1", "error": "CALCULATION_SOURCE_NOT_READY"}],
                False,
            )
            with self.assertRaises(rollupService.RollupError) as ctx:
                rollupService.calcBatch(1, {"id": "actor"})
            self.assertEqual(ctx.exception.code, "ROLLUP_CALCULATION_NOT_READY")
            self.assertEqual(fakeRepository.persistCalls, [])
            self.assertEqual(fakeRepository.conn.commits, 0)
            self.assertEqual(fakeRepository.conn.rollbacks, 1)
        finally:
            rollupService.loadRepository = originalLoadRepository
            rollupService.loadCalculator = originalLoadCalculator
            rollupService.checkScope = originalCheckScope
            calculator.calculateConsolidatedRules = originalCalculate

    def test_duplicate_dependency_edge_deduped(self):
        results, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_SUM", order=10), rule("R2", "T2", "ROLLUP_SUM", order=20)],
            [source("R1", "S1"), source("R2", "T1", sourceId=2), source("R2", "T1", sourceId=3)],
            [fact(1, "S1", 10), fact(2, "S1", 20)],
        )
        self.assertTrue(success, warnings)
        self.assertEqual(results[-1]["valueNumeric"], 30)

    def test_self_loop_cycle(self):
        _, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_SUM")],
            [source("R1", "T1")],
            [fact(1, "T1", 10), fact(2, "T1", 20)],
        )
        self.assertFalse(success)
        self.assertIn("CALCULATION_RULE_CYCLE", warnings[0]["error"])

    def test_snake_case_fact_normalize(self):
        result = calculator.buildMultiCompanyFactMap(
            [1],
            ["S1"],
            [{"company_id": 1, "atomic_metric_id": "S1", "value_numeric": 12}],
        )
        self.assertEqual(result[(1, "S1")]["valueNumeric"], 12)

    def test_build_source_readiness_missing_by_company(self):
        originalResolve = scopeRepository.resolveExternalEntitySourceAtomicIds
        originalList = scopeRepository.listApprovedFactsByCompany
        try:
            scopeRepository.resolveExternalEntitySourceAtomicIds = lambda batchId: ["S1", "S2"]
            scopeRepository.listApprovedFactsByCompany = lambda companyIds, reportingYear, atomicIds: [
                {"companyId": 1, "atomicMetricId": "S1"},
                {"companyId": 2, "atomicMetricId": "S1"},
                {"companyId": 2, "atomicMetricId": "S2"},
            ]
            readiness = scopeRepository.buildSourceReadiness(1, [1, 2], 2024)
            self.assertEqual(readiness["requiredFactCount"], 4)
            self.assertEqual(readiness["approvedFactCount"], 3)
            self.assertEqual(readiness["missingByCompany"], {"1": ["S2"], "2": []})
            self.assertFalse(readiness["readyYn"])
        finally:
            scopeRepository.resolveExternalEntitySourceAtomicIds = originalResolve
            scopeRepository.listApprovedFactsByCompany = originalList

    def test_scope_decoder_json_array(self):
        self.assertEqual(scopeRepository.decodeAtomicIds('["A1", "A2"]'), ["A1", "A2"])

    def test_scope_decoder_plain_atomic_id(self):
        self.assertEqual(scopeRepository.decodeAtomicIds("A1"), ["A1"])

    def test_dto_response_validation(self):
        status = RollupBatchStatusDto(
            batchId=1,
            runId=None,
            sourceCycleId=17,
            rollupPurposeCode="REPORT_DISCLOSURE",
            metricScopeCode="SELECTED_DISCLOSURE",
            batchStatus="completed",
            dmaReadyYn=False,
            reportReadyYn=True,
            sourceCompanyIds=[6, 7],
        )
        payload = RollupCalculateResponseDto(
            data=RollupCalculateStatusDto(
                **status.model_dump(),
                results=[
                    RollupResultDto(
                        groupAtomicMetricId="T1",
                        sourceAtomicMetricIds=["S1"],
                        formulaType="ROLLUP_SUM",
                        valueNumeric=30,
                    )
                ],
            )
        )
        self.assertTrue(payload.success)
        self.assertEqual(payload.data.results[0].valueNumeric, 30)

    def test_internal_consolidated_target_excluded_from_external_readiness(self):
        scopes = [
            {"group_atomic_metric_id": "T1", "sourceAtomicMetricIds": ["S1"]},
            {"group_atomic_metric_id": "T2", "sourceAtomicMetricIds": ["T1"]},
        ]
        self.assertEqual(scopeRepository.resolveAllRuleSourceAtomicIdsFromScopes(scopes), ["S1", "T1"])
        self.assertEqual(scopeRepository.resolveExternalEntitySourceAtomicIdsFromScopes(scopes), ["S1"])

    def test_cross_metric_producer_closure(self):
        originalListRules = scopeRepository.listBatchRules
        originalListSources = scopeRepository.listBatchRuleSources
        originalListProducer = scopeRepository.listProducerRulesByTargetAtomicIds
        try:
            scopeRepository.listBatchRules = lambda metricIds: [
                rule("R2", "T2", "ROLLUP_SUM", metricId="MetricB", order=20)
            ]
            scopeRepository.listBatchRuleSources = lambda ruleCodes: [
                source("R1", "S1") for code in ruleCodes if code == "R1"
            ] + [
                source("R2", "T1") for code in ruleCodes if code == "R2"
            ]
            scopeRepository.listProducerRulesByTargetAtomicIds = lambda atomicIds: [
                rule("R1", "T1", "ROLLUP_SUM", metricId="MetricA", order=10)
            ] if "T1" in atomicIds else []
            rules, sources = scopeRepository.resolveConsolidatedRuleClosure(["MetricB"])
            self.assertEqual([item["calculation_rule_code"] for item in rules], ["R1", "R2"])
            self.assertEqual(sorted({item["calculation_rule_code"] for item in sources}), ["R1", "R2"])
        finally:
            scopeRepository.listBatchRules = originalListRules
            scopeRepository.listBatchRuleSources = originalListSources
            scopeRepository.listProducerRulesByTargetAtomicIds = originalListProducer

    def test_report_disclosure_parent_duplicate_reject(self):
        class ParentGuardRepository:
            ROLLUP_PURPOSE_DMA_PRECHECK = "DMA_PRECHECK"
            ROLLUP_PURPOSE_REPORT_DISCLOSURE = "REPORT_DISCLOSURE"
            METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
            METRIC_SCOPE_SELECTED_DISCLOSURE = "SELECTED_DISCLOSURE"

            def listEffectiveSourceCompanies(self, parentCompanyId, reportingYear, purposeCode):
                return [{"companyId": parentCompanyId}, {"companyId": 7}]

        originalLoadRepository = rollupService.loadRepository
        originalResolveContext = rollupService.resolveBatchContext
        originalCheckScope = rollupService.checkScope
        try:
            fakeRepository = ParentGuardRepository()
            rollupService.loadRepository = lambda: fakeRepository
            rollupService.resolveBatchContext = lambda repo, purposeCode, runId, sourceCycleId: {
                "parentCompanyId": 6,
                "reportingYear": 2024,
                "run": None,
                "cycle": {"id": 17},
            }
            rollupService.checkScope = lambda parentCompanyId, userModel: None
            request = RollupBatchRequestDto(
                sourceCycleId=17,
                sourceCompanyIds=[6, 7],
                rollupPurposeCode="REPORT_DISCLOSURE",
                metricScopeCode="SELECTED_DISCLOSURE",
            )
            with self.assertRaises(rollupService.RollupError) as ctx:
                rollupService.saveBatch(request, {"id": "actor"})
            self.assertEqual(ctx.exception.code, "ROLLUP_PARENT_SOURCE_NOT_ALLOWED")
        finally:
            rollupService.loadRepository = originalLoadRepository
            rollupService.resolveBatchContext = originalResolveContext
            rollupService.checkScope = originalCheckScope

    def test_ratio_trace_includes_numerator_and_denominator(self):
        results, warnings, success = calculate(
            [rule("R1", "T1", "ROLLUP_RATIO_RECALC")],
            [source("R1", "S1", "NUMERATOR"), source("R1", "S2", "DENOMINATOR", 2)],
            [fact(1, "S1", 10), fact(2, "S1", 20), fact(1, "S2", 40), fact(2, "S2", 60)],
        )
        self.assertTrue(success, warnings)
        self.assertEqual(results[0]["sourceCompanyValues"]["S1"], {"1": 10, "2": 20})
        self.assertEqual(results[0]["sourceCompanyValues"]["S2"], {"1": 40, "2": 60})

    def test_immutable_scope_semantic_compare(self):
        class ExistingScopeCursor:
            def __init__(self):
                self.executeCount = 0

            def execute(self, *args):
                self.executeCount += 1

            def fetchone(self):
                return {"id": 1, "source_atomic_metric_ids": '["A", "B"]'}

        cur = ExistingScopeCursor()
        scopeRepository.saveScopeFromRulesTx(
            cur,
            batchId=1,
            rules=[rule("R1", "T1", "ROLLUP_SUM")],
            sources=[source("R1", "B", sourceId=1), source("R1", "A", sourceId=2)],
            scopeReason="REPORT_DISCLOSURE",
        )
        self.assertEqual(cur.executeCount, 1)


if __name__ == "__main__":
    unittest.main()
