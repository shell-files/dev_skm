import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from unittest.mock import patch, MagicMock

# We mock jwcrypto and other missing packages so we can import service
import sys
sys.modules['jwcrypto'] = MagicMock()

from src.services.onboardings.service import checkMetricInputPermission

class DummyUser:
    def __init__(self, role, user_id=None):
        self.role = role
        self.user_id = user_id

    def get(self, key):
        if key == "role":
            return self.role
        if key == "id":
            return self.user_id
        return None

def _setup_roles(mock_read_user_field, role):
    def side_effect(userModel, field):
        if field == "role":
            return role
        if field == "role_name":
            return None
        return getattr(userModel, field, None)
    mock_read_user_field.side_effect = side_effect

class TestOnboardingInputPermission(unittest.TestCase):
    def setUp(self):
        self.patcher_get_actor = patch("src.services.onboardings.service.getActorUserId")
        self.patcher_read_user = patch("src.services.onboardings.service.readUserField")
        self.patcher_repo = patch("src.services.onboardings.service.assignmentRepo")
        
        self.mock_get_actor_user_id = self.patcher_get_actor.start()
        self.mock_read_user_field = self.patcher_read_user.start()
        self.mock_assignment_repo = self.patcher_repo.start()
        self.mock_assignment_repo.ASSIGNMENT_STATUS_ASSIGNED = "assigned"

    def tearDown(self):
        self.patcher_get_actor.stop()
        self.patcher_read_user.stop()
        self.patcher_repo.stop()

    def test_esg_manager_can_input_without_assignment(self):
        user = DummyUser("ESG", 1)
        _setup_roles(self.mock_read_user_field, "ESG")
        self.mock_assignment_repo.listAssignmentRows.return_value = []
        checkMetricInputPermission(cycle={"id": 1}, companyId=1, metricId="M1", userModel=user)

    def test_admin_can_input_without_assignment(self):
        user = DummyUser("ADMIN", 1)
        _setup_roles(self.mock_read_user_field, "ADMIN")
        self.mock_assignment_repo.listAssignmentRows.return_value = []
        checkMetricInputPermission(cycle={"id": 1}, companyId=1, metricId="M1", userModel=user)

    def test_esg_manager_can_input_other_assignment(self):
        user = DummyUser("ESG", 1)
        _setup_roles(self.mock_read_user_field, "ESG")
        self.mock_assignment_repo.listAssignmentRows.return_value = [
            {"metric_id": "M1", "assignment_status": "ASSIGNED", "assignee_user_id": 999}
        ]
        checkMetricInputPermission(cycle={"id": 1}, companyId=1, metricId="M1", userModel=user)

    def test_employee_can_input_own_assigned_metric(self):
        user = DummyUser("EMPLOYEE", 100)
        _setup_roles(self.mock_read_user_field, "EMPLOYEE")
        self.mock_get_actor_user_id.return_value = 100
        self.mock_assignment_repo.listAssignmentRows.return_value = [
            {"metric_id": "M1", "assignment_status": "ASSIGNED", "assignee_user_id": 100}
        ]
        checkMetricInputPermission(cycle={"id": 1}, companyId=1, metricId="M1", userModel=user)

    def test_employee_cannot_input_unassigned_metric(self):
        user = DummyUser("EMPLOYEE", 100)
        _setup_roles(self.mock_read_user_field, "EMPLOYEE")
        self.mock_get_actor_user_id.return_value = 100
        self.mock_assignment_repo.listAssignmentRows.return_value = []
        with self.assertRaisesRegex(PermissionError, "Metric assignment is required"):
            checkMetricInputPermission(cycle={"id": 1}, companyId=1, metricId="M1", userModel=user)

    def test_employee_cannot_input_pending_assignment(self):
        user = DummyUser("EMPLOYEE", 100)
        _setup_roles(self.mock_read_user_field, "EMPLOYEE")
        self.mock_get_actor_user_id.return_value = 100
        self.mock_assignment_repo.listAssignmentRows.return_value = [
            {"metric_id": "M1", "assignment_status": "PENDING", "assignee_user_id": 100}
        ]
        with self.assertRaisesRegex(PermissionError, "Metric assignment must be assigned before input"):
            checkMetricInputPermission(cycle={"id": 1}, companyId=1, metricId="M1", userModel=user)

    def test_employee_cannot_input_other_assignment(self):
        user = DummyUser("EMPLOYEE", 100)
        _setup_roles(self.mock_read_user_field, "EMPLOYEE")
        self.mock_get_actor_user_id.return_value = 100
        self.mock_assignment_repo.listAssignmentRows.return_value = [
            {"metric_id": "M1", "assignment_status": "ASSIGNED", "assignee_user_id": 999}
        ]
        with self.assertRaisesRegex(PermissionError, "Only the assigned user can input"):
            checkMetricInputPermission(cycle={"id": 1}, companyId=1, metricId="M1", userModel=user)

    def test_consultant_cannot_input(self):
        user = DummyUser("CONSULTANT", 1)
        _setup_roles(self.mock_read_user_field, "CONSULTANT")
        with self.assertRaisesRegex(PermissionError, "Consultants cannot input onboarding metrics"):
            checkMetricInputPermission(cycle={"id": 1}, companyId=1, metricId="M1", userModel=user)

    @patch("src.services.onboardings.service.validateMetricValues")
    def test_save_validation_applies_guard(self, mock_validate):
        from src.services.onboardings.service import saveMetricValues
        from src.models.onboarding import OnboardingMetricValuesRequestDto
        
        req = OnboardingMetricValuesRequestDto(companyId=1, reportingYear=2024, cycleType="PRE_DMA_G0", values=[])
        mock_validate.side_effect = PermissionError("Consultants cannot input onboarding metrics")
        with self.assertRaisesRegex(PermissionError, "Consultants cannot input"):
            saveMetricValues(metricId="M1", request=req, userModel=DummyUser("CONSULTANT", 1))

    @patch("src.services.onboardings.service.checkMetricInputPermission")
    @patch("src.services.onboardings.service.requireCycle")
    @patch("src.services.onboardings.service.checkScope")
    @patch("src.services.onboardings.approval_service.submitMetricApproval")
    def test_submit_applies_guard(self, mock_submit, mock_scope, mock_cycle, mock_check):
        from src.services.onboardings.service import submitApproval
        from src.models.onboarding import OnboardingApprovalRequestDto
        
        mock_check.side_effect = PermissionError("Consultants cannot input onboarding metrics")
        req = OnboardingApprovalRequestDto(companyId=1, reportingYear=2024, cycleType="PRE_DMA_G0", metricId="M1")
        with self.assertRaisesRegex(PermissionError, "Consultants cannot input"):
            submitApproval(request=req, userModel=DummyUser("CONSULTANT", 1))

if __name__ == '__main__':
    unittest.main()
