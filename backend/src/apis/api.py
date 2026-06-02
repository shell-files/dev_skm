from fastapi import APIRouter

from src.apis.onboardingassignment import onboardingAssignmentRouter
from src.apis.companyprofile import companyProfileRouter
from src.apis.onboardingapproval import onboardingApprovalRouter
from src.apis.onboardinginvite import onboardingInviteRouter
from src.apis.reportworkflow import reportWorkflowRouter
from src.apis.rollup import rollupRouter


router = APIRouter()
router.include_router(companyProfileRouter)
router.include_router(onboardingAssignmentRouter)
router.include_router(onboardingApprovalRouter)
router.include_router(onboardingInviteRouter)
router.include_router(reportWorkflowRouter)
router.include_router(rollupRouter)
