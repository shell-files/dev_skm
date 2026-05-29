from fastapi import APIRouter, Depends, HTTPException

from src.models.media import (
    MediaAnalyzeRequest,
    MediaAnalyzeResponse,
    MediaNewsCrawlAnalyzeRequest,
    MediaNewsCrawlAnalyzeResponse,
)
from src.services.medias.service import (
    buildMediaAnalyzeResponse,
    runMediaAnalysis,
    runMediaCrawlAndAnalyze,
)
from src.utils.auth import get_token


router = APIRouter(tags=["media"])


@router.post(
    "/news/analyze",
    response_model=MediaAnalyzeResponse,
    summary="언론 기사 수동 분석 및 저장",
)
async def analyze_media_news(request: MediaAnalyzeRequest, userModel=Depends(get_token)):
    try:
        scoredSignals = runMediaAnalysis(request.articles, request.runId, request.keywords)
        return buildMediaAnalyzeResponse(
            runId=request.runId,
            articleCount=len(request.articles),
            savedSignalCount=len(scoredSignals) if scoredSignals else 0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        return runMediaCrawlAndAnalyze(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
