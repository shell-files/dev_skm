"""
media.py
레이어: API Router
역할: 미디어 크롤링·분석 및 KCGS ESG 등급 저장 엔드포인트.

엔드포인트:
  POST /news/crawl-and-analyze  — MVP 고정 언론사 크롤링 및 미디어 분석
  POST /kcgs/grades             — KCGS ESG 등급 입력 저장 (APPROVED)
"""
from fastapi import APIRouter, Depends, HTTPException

from src.models.media import (
    MediaNewsCrawlAnalyzeRequest,
    MediaNewsCrawlAnalyzeResponse,
)
from src.models.dmakcgsgrade import KcgsGradeSaveRequest, KcgsGradeSaveResponse
from src.services.medias.newsservice import (
    runMediaCrawlAndAnalyze,
    saveKcgsGradeInputs,
)
from src.utils.auth import get_token


router = APIRouter(tags=["media"])


@router.post(
    "/news/crawl-and-analyze",
    response_model=MediaNewsCrawlAnalyzeResponse,
    summary="MVP 고정 언론사 크롤링 및 미디어 분석",
)
async def crawl_and_analyze_media_news(
    request: MediaNewsCrawlAnalyzeRequest,
    userModel=Depends(get_token),
):
    try:
        return runMediaCrawlAndAnalyze(request, userModel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/kcgs/grades",
    response_model=KcgsGradeSaveResponse,
    summary="KCGS ESG 등급 입력 저장(APPROVED)",
)
async def save_kcgs_grades(request: KcgsGradeSaveRequest, userModel=Depends(get_token)):
    try:
        saved = saveKcgsGradeInputs(request, userModel)
        return KcgsGradeSaveResponse(
            companyId=request.companyId,
            savedCount=saved,
            reviewStatus="APPROVED",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
