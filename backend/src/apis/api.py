<<<<<<< HEAD
"""
api.py
레이어: API Router
역할: 서브라우터 통합 — onboardingAssignment, onboardingApproval, reportWorkflow, rollup 라우터를 include_in_schema=False로 통합.
"""
=======
>>>>>>> origin/skm_test
from fastapi import APIRouter

from src.apis.onboardingAssignment import onboardingAssignmentRouter
from src.apis.onboardingApproval import onboardingApprovalRouter
from src.apis.reportWorkflow import reportWorkflowRouter
from src.apis.rollup import rollupRouter


router = APIRouter()
router.include_router(onboardingAssignmentRouter, include_in_schema=False)
router.include_router(onboardingApprovalRouter, include_in_schema=False)
router.include_router(reportWorkflowRouter, include_in_schema=False)
router.include_router(rollupRouter, include_in_schema=False)
