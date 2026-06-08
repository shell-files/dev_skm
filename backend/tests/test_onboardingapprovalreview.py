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

class OnboardingInputPermissionTest(unittest.TestCase):
    def setUp(self):
        self.cycle = {"id": 1}
        self.companyId = 6
        self.metricId = "G0-01"

    @patch("src.services.onboardings.service.assignmentRepo.listAssignmentRows")
    def test_manager_bypasses_assignment(self, mock_list):
        userModel = {"id": 1, "role": "ESG"}
        # 1 & 2. ESG 담당자는 assignment 없이 save 및 submit (input check) 가능
        mock_list.return_value = []
        service.checkMetricInputPermission(cycle=self.cycle, companyId=self.companyId, metricId=self.metricId, userModel=userModel)
        
        # 3. ESG 담당자는 타인에게 할당된 Metric도 save/submit 가능
        mock_list.return_value = [{"metric_id": "G0-01", "assignment_status": "assigned", "assignee_user_id": 999}]
        service.checkMetricInputPermission(cycle=self.cycle, companyId=self.companyId, metricId=self.metricId, userModel=userModel)

    @patch("src.services.onboardings.service.assignmentRepo.listAssignmentRows")
    def test_employee_assignment_rules(self, mock_list):
        userModel = {"id": 100, "role": "EMPLOYEE"}

        # 5. 일반 담당자는 미지정 Metric save/submit 차단
        mock_list.return_value = []
        with self.assertRaises(PermissionError):
            service.checkMetricInputPermission(cycle=self.cycle, companyId=self.companyId, metricId=self.metricId, userModel=userModel)

        # 6. 일반 담당자는 타인 할당 Metric save/submit 차단
        mock_list.return_value = [{"metric_id": "G0-01", "assignment_status": "assigned", "assignee_user_id": 999}]
        with self.assertRaises(PermissionError):
            service.checkMetricInputPermission(cycle=self.cycle, companyId=self.companyId, metricId=self.metricId, userModel=userModel)

        # 4 & 8. 일반 담당자는 본인 ASSIGNED Metric만 save/submit 가능
        mock_list.return_value = [{"metric_id": "G0-01", "assignment_status": "assigned", "assignee_user_id": 100}]
        service.checkMetricInputPermission(cycle=self.cycle, companyId=self.companyId, metricId=self.metricId, userModel=userModel)

    def test_consultant_blocked(self):
        # 7. 컨설턴트 save/submit 차단
        userModel = {"id": 200, "role": "CONSULTANT"}
        with self.assertRaises(PermissionError):
            service.checkMetricInputPermission(cycle=self.cycle, companyId=self.companyId, metricId=self.metricId, userModel=userModel)


if __name__ == "__main__":
    unittest.main()
