from fastapi import APIRouter

from src.apis.reportworkflow import reportWorkflowRouter
from src.apis.rollup import rollupRouter
from src.apis.companyprofile import companyProfileRouter


router = APIRouter(tags=["api"])
router.include_router(reportWorkflowRouter)
router.include_router(rollupRouter)
router.include_router(companyProfileRouter)
