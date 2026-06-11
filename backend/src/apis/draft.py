from fastapi import APIRouter, Depends

from src.utils.auth import get_token
from src.models.draft import DraftSaveRequestDto
from src.services.draft.service import (
    fetchDraftMetrics,
    fetchDraftSection,
    saveDraft,
    loadDraft,
)

router = APIRouter()


@router.get("/metrics", summary="보고서 초안 지표 조회")
async def getDraftMetrics(companyId: int, year: int, token=Depends(get_token)):
    return fetchDraftMetrics(companyId, year, token)


@router.get("/section", summary="AI 생성 서브이슈 본문 조회")
async def getDraftSection(companyId: int, year: int, subIssueId: str, token=Depends(get_token)):
    return fetchDraftSection(companyId, year, subIssueId, token)


@router.post("/save", summary="보고서 초안 편집값 저장")
async def saveDraftRoute(req: DraftSaveRequestDto, token=Depends(get_token)):
    return saveDraft(req, token)


@router.get("/load", summary="보고서 초안 편집값 불러오기")
async def loadDraftRoute(companyId: int, year: int, token=Depends(get_token)):
    return loadDraft(companyId, year, token)
