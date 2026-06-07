import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.rollups import service


class FakeRepository:
    ROLLUP_PURPOSE_DMA_PRECHECK = "DMA_PRECHECK"
    ROLLUP_PURPOSE_REPORT_DISCLOSURE = "REPORT_DISCLOSURE"
    METRIC_SCOPE_G0_02_FINANCIAL_BASIS = "G0_02_FINANCIAL_BASIS"
    METRIC_SCOPE_SELECTED_DISCLOSURE = "SELECTED_DISCLOSURE"

    def __init__(self):
        self.listRequestsArgs = None
        self.requestedMetricIdsFromBatchScope = []
        self.workspace = {}
        self.workspaceArgs = None

    def listRequests(self, sourceCompanyId, purposeCode, scopeCode, includeSentYn=True, transferStatus=None):
        self.listRequestsArgs = (sourceCompanyId, purposeCode, scopeCode, includeSentYn, transferStatus)
        return [
            {
                "batchId": 10,
                "sourceCycleId": 17,
                "parentCompanyId": 6,
                "reportingYear": 2025,
                "rollupPurposeCode": purposeCode,
                "metricScopeCode": scopeCode,
                "requestStatus": "sent",
                "inputStatus": "approved",
                "approvalStatus": "approved",
                "transferStatus": "sent",
            }
        ]

    def buildSourceReadiness(self, batchId, sourceCompanyIds, reportingYear):
        return {
            "readyYn": False,
            "requiredAtomicCount": 2,
            "missingByCompany": {str(sourceCompanyIds[0]): ["M2__Q1"]},
        }

    def listScope(self, batchId):
        return [
            {
                "metric_id": "M1",
                "group_atomic_metric_id": "M1__G1",
                "sourceAtomicMetricIds": ["M1__Q1", "M1__G1"],
            },
            {
                "metric_id": "M2",
                "group_atomic_metric_id": "M2__G1",
                "sourceAtomicMetricIds": ["M2__Q1"],
            },
        ]

    def listAtomicMetadata(self, atomicMetricIds):
        return [
            {"metricId": "M1", "metricName": "Metric 1", "atomicMetricId": "M1__Q1"},
            {"metricId": "M2", "metricName": "Metric 2", "atomicMetricId": "M2__Q1"},
        ]

    def getBatch(self, batchId):
        return {
            "id": batchId,
            "rollup_batch_code": "RB-1",
            "parent_company_id": 6,
            "source_cycle_id": 17,
            "reporting_year": 2025,
            "rollup_purpose_code": "REPORT_DISCLOSURE",
            "metric_scope_code": "SELECTED_DISCLOSURE",
        }

    def getSource(self, batchId, sourceCompanyId):
        return {
            "esg_rollup_batch_id": batchId,
            "parent_company_id": 6,
            "source_company_id": sourceCompanyId,
            "request_status": "requested",
            "input_status": "submitted",
            "approval_status": "submitted",
            "transfer_status": "not_sent",
        }

    def getCompanyProfile(self, companyId):
        return {"companyId": companyId, "companyCode": f"C{companyId}", "companyName": f"C{companyId}"}

    def listRequestedMetricIdsFromBatchScope(self, batchId):
        return self.requestedMetricIdsFromBatchScope

    def findActiveInputWorkspace(self, companyId, reportingYear, requestedMetricIds):
        self.workspaceArgs = (companyId, reportingYear, requestedMetricIds)
        return self.workspace

    def listSourceDetails(self, batchId):
        return [
            {
                "parent_company_id": 6,
                "source_company_id": 6,
                "sourceCompanyCode": "C6",
                "sourceCompanyName": "C6",
            },
            {
                "parent_company_id": 6,
                "source_company_id": 7,
                "sourceCompanyCode": "C7",
                "sourceCompanyName": "C7",
                "request_status": "requested",
                "input_status": "submitted",
                "approval_status": "submitted",
                "transfer_status": "not_sent",
            },
        ]

    def resolveConsolidatedRuleClosure(self, metricIds):
        return (
            [{"calculation_rule_code": "R1", "target_atomic_metric_id": "M1__G1"}],
            [{"calculation_rule_code": "R1", "source_atomic_metric_id": "M1__Q1"}],
        )


class RollupReadApiServiceTest(unittest.TestCase):
    def test_list_requests_preserves_history_options(self):
        fakeRepo = FakeRepository()
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "getSource", return_value=7),
            patch.object(service, "resolveBatchRequestedMetricIds", return_value=["M1"]),
        ):
            response = service.listRequestsForSource(
                "REPORT_DISCLOSURE",
                "SELECTED_DISCLOSURE",
                includeSentYn=True,
                transferStatus="sent",
                userModel={},
            )

        self.assertEqual(fakeRepo.listRequestsArgs, (7, "REPORT_DISCLOSURE", "SELECTED_DISCLOSURE", True, "sent"))
        self.assertEqual(response.data.items[0].transferStatus, "sent")
        self.assertEqual(response.data.items[0].metricCount, 1)
        self.assertEqual(response.data.items[0].metricIds, ["M1"])
        self.assertEqual(response.data.items[0].requestedMetricIds, ["M1"])
        self.assertEqual(response.data.items[0].resolvedMetricIds, ["M1", "M2"])
        self.assertEqual(response.data.items[0].dependencyMetricIds, ["M2"])

    def test_request_detail_uses_source_scope_and_snapshot_counts(self):
        fakeRepo = FakeRepository()
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "getSource", return_value=7),
            patch.object(service, "resolveBatchRequestedMetricIds", return_value=["M1"]),
        ):
            response = service.getRequestDetail(10, userModel={})

        data = response.data
        self.assertEqual(data.sourceCompanyId, 7)
        self.assertEqual(data.requiredAtomicCount, 2)
        self.assertEqual(data.approvedAtomicCount, 1)
        self.assertEqual(data.missingAtomicMetricIds, ["M2__Q1"])
        self.assertEqual([item.metricId for item in data.items], ["M1"])
        self.assertEqual(data.sourceCycleId, 17)
        self.assertEqual(data.metricCount, 1)
        self.assertEqual(data.metricIds, ["M1"])
        self.assertEqual(data.requestedMetricIds, ["M1"])
        self.assertEqual(data.resolvedMetricIds, ["M1", "M2"])
        self.assertEqual(data.dependencyMetricIds, ["M2"])
        self.assertEqual([item.metricId for item in data.dependencyItems], ["M2"])
        self.assertEqual(data.dependencyItems[0].missingAtomicMetricIds, ["M2__Q1"])

    def test_request_detail_rejects_parent_self_source(self):
        fakeRepo = FakeRepository()
        with patch.object(service, "loadRepository", return_value=fakeRepo), patch.object(service, "getSource", return_value=6):
            with self.assertRaises(service.RollupError) as context:
                service.getRequestDetail(10, userModel={})

        self.assertEqual(context.exception.statusCode, 404)
        self.assertEqual(context.exception.code, "ROLLUP_SOURCE_REQUEST_NOT_FOUND")

    def test_batch_sources_excludes_parent_row(self):
        fakeRepo = FakeRepository()
        with patch.object(service, "loadRepository", return_value=fakeRepo), patch.object(service, "checkScope", return_value=None):
            response = service.listBatchSources(10, userModel={})

        self.assertEqual(len(response.data.items), 1)
        self.assertEqual(response.data.items[0].sourceCompanyId, 7)

    def test_scope_preview_is_read_only_closure_summary(self):
        fakeRepo = FakeRepository()
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "resolveBatchContext", return_value={"parentCompanyId": 6, "reportingYear": 2025}),
            patch.object(service, "resolvePreviewMetricIds", return_value=["M1"]),
            patch.object(service, "checkScope", return_value=None),
        ):
            response = service.getScopePreview(None, 17, "REPORT_DISCLOSURE", "SELECTED_DISCLOSURE", userModel={})

        self.assertEqual(response.data.metricIds, ["M1"])
        self.assertEqual(response.data.requiredAtomicMetricIds, ["M1__Q1"])

    def test_current_readiness_is_separated_from_snapshot_status(self):
        fakeRepo = FakeRepository()
        fakeRepo.buildSourceReadiness = lambda batchId, sourceCompanyIds, reportingYear: {
            "readyYn": True,
            "requiredAtomicCount": 2,
            "missingByCompany": {str(sourceCompanyIds[0]): []},
        }
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "getSource", return_value=7),
            patch.object(service, "resolveBatchRequestedMetricIds", return_value=["M1"]),
        ):
            response = service.getRequestDetail(10, userModel={})

        data = response.data
        self.assertEqual(data.approvalStatus, "submitted")
        self.assertEqual(data.readinessStatus, "READY")
        self.assertEqual(data.currentApprovedAtomicCount, 2)
        self.assertEqual(data.currentMissingAtomicCount, 0)

    def test_request_detail_separates_dependency_missing_items(self):
        fakeRepo = FakeRepository()
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "getSource", return_value=7),
            patch.object(service, "resolveBatchRequestedMetricIds", return_value=["M1"]),
        ):
            response = service.getRequestDetail(10, userModel={})

        data = response.data
        self.assertEqual([item.metricId for item in data.items], ["M1"])
        self.assertEqual(data.items[0].missingAtomicMetricIds, [])
        self.assertEqual([item.metricId for item in data.dependencyItems], ["M2"])
        self.assertEqual(data.dependencyItems[0].missingAtomicMetricIds, ["M2__Q1"])

    def test_requested_metric_snapshot_takes_priority(self):
        fakeRepo = FakeRepository()
        fakeRepo.requestedMetricIdsFromBatchScope = ["M1"]
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "resolvePreviewMetricIds", return_value=["M9"]),
        ):
            metricIds = service.resolveBatchRequestedMetricIds(fakeRepo.getBatch(10))

        self.assertEqual(metricIds, ["M1"])

    def test_requested_metric_legacy_fallback_uses_preview(self):
        fakeRepo = FakeRepository()
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "resolvePreviewMetricIds", return_value=["M9"]),
        ):
            metricIds = service.resolveBatchRequestedMetricIds(fakeRepo.getBatch(10))

        self.assertEqual(metricIds, ["M9"])

    def test_actionable_input_metric_ids_include_missing_dependency_metrics(self):
        fakeRepo = FakeRepository()
        fakeRepo.workspace = {
            "cycleId": 20,
            "cycleType": "POST_DMA_DISCLOSURE",
            "reportingYear": 2025,
        }
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "getSource", return_value=7),
            patch.object(service, "resolveBatchRequestedMetricIds", return_value=["M1"]),
        ):
            response = service.getRequestDetail(10, userModel={})

        self.assertEqual(response.data.actionableInputMetricIds, ["M1", "M2"])
        self.assertEqual(fakeRepo.workspaceArgs, (7, 2025, ["M1", "M2"]))

    def test_input_workspace_available(self):
        fakeRepo = FakeRepository()
        fakeRepo.workspace = {
            "cycleId": 20,
            "cycleType": "POST_DMA_DISCLOSURE",
            "reportingYear": 2025,
        }
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "getSource", return_value=7),
            patch.object(service, "resolveBatchRequestedMetricIds", return_value=["M1"]),
        ):
            response = service.getRequestDetail(10, userModel={})

        self.assertTrue(response.data.inputWorkspace.availableYn)
        self.assertEqual(response.data.inputWorkspace.cycleId, 20)
        self.assertEqual(fakeRepo.workspaceArgs, (7, 2025, ["M1", "M2"]))

    def test_input_workspace_unavailable(self):
        fakeRepo = FakeRepository()
        with (
            patch.object(service, "loadRepository", return_value=fakeRepo),
            patch.object(service, "getSource", return_value=7),
            patch.object(service, "resolveBatchRequestedMetricIds", return_value=["M1"]),
        ):
            response = service.getRequestDetail(10, userModel={})

        self.assertFalse(response.data.inputWorkspace.availableYn)
        self.assertEqual(response.data.inputWorkspace.reason, "INPUT_WORKSPACE_NOT_READY")


if __name__ == "__main__":
    unittest.main()
