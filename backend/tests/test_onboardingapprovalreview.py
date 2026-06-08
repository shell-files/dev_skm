import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.apis import onboardingApproval
from src.models.onboarding import (
    OnboardingApprovalDecisionRequestDto,
    OnboardingApprovalStatusDataDto,
    OnboardingApprovalActionResponseDto,
)


def request():
    return OnboardingApprovalDecisionRequestDto(
        companyId=6,
        reportingYear=2026,
        cycleType="POST_DMA_DISCLOSURE",
        metricId="E1-06",
        commentText="reviewed",
    )


def actionResponse():
    return OnboardingApprovalActionResponseDto(
        data=OnboardingApprovalStatusDataDto(
            companyId=6,
            reportingYear=2026,
            cycleType="POST_DMA_DISCLOSURE",
            metricId="E1-06",
            approvalStatus="REVIEWED",
        ),
        message="Reviewed",
    )


class OnboardingApprovalReviewRouteTest(unittest.TestCase):
    def test_review_route_calls_service_wrapper(self):
        expected = actionResponse()
        with patch.object(onboardingApproval, "reviewApproval", return_value=expected) as mocked:
            result = asyncio.run(onboardingApproval.reviewApprovalRoute(request(), userModel={"id": 1}))

        self.assertEqual(result, expected)
        mocked.assert_called_once()

    def test_review_route_maps_permission_error_to_403(self):
        with patch.object(onboardingApproval, "reviewApproval", side_effect=PermissionError("forbidden")):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(onboardingApproval.reviewApprovalRoute(request(), userModel={"id": 1}))

        self.assertEqual(context.exception.status_code, 403)

    def test_review_route_maps_value_error_to_409(self):
        with patch.object(onboardingApproval, "reviewApproval", side_effect=ValueError("not ready")):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(onboardingApproval.reviewApprovalRoute(request(), userModel={"id": 1}))

        self.assertEqual(context.exception.status_code, 409)


from src.services.onboardings import service

class OnboardingApprovalReviewServiceTest(unittest.TestCase):
    def test_reject_allows_consultant_and_blocks_employee(self):
        mock_summary = {"companyId": 6, "reportingYear": 2026, "metricId": "E1-06", "approvalStatus": "REJECTED"}
        with patch.object(service, "checkScope"), patch.object(service.approvalService, "rejectMetricApproval", return_value=mock_summary):
            # Consultant (reviewer) allowed
            service.rejectApproval(request(), {"id": 1, "role": "CONSULTANT"})

            # Employee blocked
            with self.assertRaises(PermissionError):
                service.rejectApproval(request(), {"id": 2, "role": "EMPLOYEE"})

    def test_approve_blocks_consultant(self):
        mock_summary = {"companyId": 6, "reportingYear": 2026, "metricId": "E1-06", "approvalStatus": "APPROVED"}
        with patch.object(service, "checkScope"), patch.object(service.approvalService, "approveMetricApproval", return_value=mock_summary):
            # Consultant (not approver) blocked
            with self.assertRaises(PermissionError):
                service.approveApproval(request(), {"id": 1, "role": "CONSULTANT"})


if __name__ == "__main__":
    unittest.main()
