from fastapi import APIRouter

from src.apis.onboardingAssignment import onboardingAssignmentRouter
from src.apis.onboardingApproval import onboardingApprovalRouter
from src.apis.onboardingInvite import onboardingInviteRouter
from src.apis.reportWorkflow import reportWorkflowRouter
from src.apis.rollup import rollupRouter


router = APIRouter()
router.include_router(onboardingAssignmentRouter, include_in_schema=False)
router.include_router(onboardingApprovalRouter, include_in_schema=False)
router.include_router(onboardingInviteRouter, include_in_schema=False)
router.include_router(reportWorkflowRouter, include_in_schema=False)
router.include_router(rollupRouter, include_in_schema=False)
