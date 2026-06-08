import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.apis import onboardingApproval
from src.models.onboarding import OnboardingApprovalDetailResponseDto
from src.services.onboardings import service
from src.utils import onboardingapprovalrepository as approvalRepo


SUMMARY = {
    "companyId": 6,
    "reportingYear": 2026,
    "metricId": "E1-06",
    "metricName": "Climate disclosure",
    "cycleType": "POST_DMA_DISCLOSURE",
    "issueDomain": "environmental",
    "approvalStatus": "SUBMITTED",
    "inputUserId": 18,
    "assigneeUserId": 18,
    "cycleId": 17,
    "assignmentId": 42,
    "requiredAtomicCount": 1,
    "completedAtomicCount": 1,
    "submittedAtomicCount": 1,
    "approvedAtomicCount": 0,
    "missingAtomicMetricIds": [],
    "selfSubmittedYn": False,
    "actionSupportedYn": True,
}


def detail_response():
    return OnboardingApprovalDetailResponseDto(
        data=service.detailDto(
            SUMMARY,
            [
                {
                    "atomic_metric_id": "E1-06__Q0001",
                    "atomic_name": "Energy use",
                    "data_value_type": "QUANT",
                    "atomic_data_role": "INPUT",
                    "value_numeric": 123.45,
                    "unit": "kWh",
                    "input_status": "submitted",
                    "updated_at": "2026-06-08 10:00:00",
                    "evidence_count": 0,
                }
            ],
            {"id": 18, "role": "EMPLOYEE"},
        )
    )


class OnboardingApprovalDetailRouteTest(unittest.TestCase):
    def test_detail_route_calls_service_wrapper(self):
        expected = detail_response()
        with patch.object(onboardingApproval, "getApprovalDetail", return_value=expected) as mocked:
            result = asyncio.run(
                onboardingApproval.getApprovalDetailRoute(
                    companyId=6,
                    reportingYear=2026,
                    metricId="E1-06",
                    cycleType="POST_DMA_DISCLOSURE",
                    userModel={"id": 18},
                )
            )

        self.assertEqual(result, expected)
        mocked.assert_called_once()

    def test_detail_route_maps_permission_error_to_403(self):
        with patch.object(onboardingApproval, "getApprovalDetail", side_effect=PermissionError("forbidden")):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(
                    onboardingApproval.getApprovalDetailRoute(
                        companyId=6,
                        reportingYear=2026,
                        metricId="E1-06",
                        userModel={"id": 18},
                    )
                )

        self.assertEqual(context.exception.status_code, 403)


class OnboardingApprovalDetailServiceTest(unittest.TestCase):
    def test_service_returns_atomic_items(self):
        with patch.object(service, "checkScope"), \
            patch.object(service, "requireCycle", return_value={"id": 17, "cycle_type": "POST_DMA_DISCLOSURE"}), \
            patch.object(service.approvalService, "buildMetricApprovalSummary", return_value=SUMMARY), \
            patch.object(service, "checkMetricStatusPermission", return_value=True), \
            patch.object(service.repo, "listMetricScopes", return_value=[{"metric_id": "E1-06"}]), \
            patch.object(
                service.repo,
                "listApprovalAtomicDetailRows",
                return_value=[
                    {
                        "atomic_metric_id": "E1-06__Q0001",
                        "atomic_name": "Energy use",
                        "data_value_type": "QUANT",
                        "atomic_data_role": "INPUT",
                        "value_numeric": 123.45,
                        "unit": "kWh",
                        "input_status": "submitted",
                        "updated_at": "2026-06-08 10:00:00",
                        "evidence_count": 0,
                    }
                ],
            ):
            result = service.getApprovalDetail(6, 2026, "E1-06", "POST_DMA_DISCLOSURE", {"id": 18})

        self.assertEqual(result.data.metricId, "E1-06")
        self.assertEqual(result.data.cycleType, "POST_DMA_DISCLOSURE")
        self.assertEqual(len(result.data.atomicItems), 1)
        self.assertEqual(result.data.atomicItems[0].atomicMetricId, "E1-06__Q0001")
        self.assertEqual(result.data.atomicItems[0].evidenceCount, 0)

    def test_service_blocks_unauthorized_user(self):
        with patch.object(service, "checkScope"), \
            patch.object(service, "requireCycle", return_value={"id": 17, "cycle_type": "POST_DMA_DISCLOSURE"}), \
            patch.object(service.approvalService, "buildMetricApprovalSummary", return_value=SUMMARY), \
            patch.object(service, "checkMetricStatusPermission", return_value=False):
            with self.assertRaises(PermissionError):
                service.getApprovalDetail(6, 2026, "E1-06", "POST_DMA_DISCLOSURE", {"id": 99})


class OnboardingApprovalDetailRepositoryTest(unittest.TestCase):
    def test_repository_prefers_input_value_over_kpi_fact(self):
        with patch.object(approvalRepo.scopeRepo, "listMetricScopes", return_value=[{"metric_id": "E1-06"}]), \
            patch.object(
                approvalRepo.scopeRepo,
                "listAtomicMaster",
                return_value=[
                    {
                        "metric_id": "E1-06",
                        "atomic_metric_id": "E1-06__Q0001",
                        "atomic_name_kr": "Energy use",
                        "data_value_type": "QUANT",
                        "atomic_data_role": "INPUT",
                        "unit": "kWh",
                    }
                ],
            ), \
            patch.object(
                approvalRepo,
                "listApprovalInputRows",
                return_value=[
                    {
                        "atomic_metric_id": "E1-06__Q0001",
                        "value_text": None,
                        "value_numeric": 200,
                        "unit": "kWh",
                        "input_status": "submitted",
                        "updated_at": None,
                    }
                ],
            ), \
            patch.object(
                approvalRepo,
                "listApprovalFactRows",
                return_value=[
                    {
                        "atomic_metric_id": "E1-06__Q0001",
                        "value_text": None,
                        "value_numeric": 100,
                        "unit": "kWh",
                        "input_status": "approved",
                        "updated_at": None,
                    }
                ],
            ):
            rows = approvalRepo.listApprovalAtomicDetailRows(6, 2026, 17, "E1-06")

        self.assertEqual(rows[0]["value_numeric"], 200.0)
        self.assertEqual(rows[0]["input_status"], "submitted")

    def test_repository_falls_back_to_kpi_fact(self):
        with patch.object(approvalRepo.scopeRepo, "listMetricScopes", return_value=[{"metric_id": "E1-06"}]), \
            patch.object(
                approvalRepo.scopeRepo,
                "listAtomicMaster",
                return_value=[
                    {
                        "metric_id": "E1-06",
                        "atomic_metric_id": "E1-06__Q0001",
                        "atomic_name_kr": "Energy use",
                        "data_value_type": "QUANT",
                        "atomic_data_role": "INPUT",
                        "unit": "kWh",
                    }
                ],
            ), \
            patch.object(approvalRepo, "listApprovalInputRows", return_value=[]), \
            patch.object(
                approvalRepo,
                "listApprovalFactRows",
                return_value=[
                    {
                        "atomic_metric_id": "E1-06__Q0001",
                        "value_text": None,
                        "value_numeric": 100,
                        "unit": "kWh",
                        "input_status": "approved",
                        "updated_at": None,
                    }
                ],
            ):
            rows = approvalRepo.listApprovalAtomicDetailRows(6, 2026, 17, "E1-06")

        self.assertEqual(rows[0]["value_numeric"], 100.0)
        self.assertEqual(rows[0]["input_status"], "approved")


if __name__ == "__main__":
    unittest.main()
