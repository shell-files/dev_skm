from fastapi import APIRouter

from src.apis.companyprofile import companyProfileRouter
from src.apis.onboardingapproval import onboardingApprovalRouter
from src.apis.reportworkflow import reportWorkflowRouter
from src.apis.rollup import rollupRouter


router = APIRouter(tags=["api"])
router.include_router(companyProfileRouter)
router.include_router(onboardingApprovalRouter)
router.include_router(reportWorkflowRouter)
router.include_router(rollupRouter)
