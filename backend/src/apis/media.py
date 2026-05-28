from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from src.services.medias.service import runMediaAnalysis
from src.utils.auth import get_token
from src.utils.dmarepository import getTopIssuesByMediaScore, getMediaCoverageFromSummary
from src.utils.subissuemaster import getSubIssueDisplayName
from src.utils.dmascoring import SCORE_UI_MULTIPLIER

router = APIRouter(tags=["media"])

class MediaAnalyzeRequest(BaseModel):
    runId: int
    articles: List[dict]
    keywords: Optional[List[str]] = []

class MediaTopIssue(BaseModel):
    subIssueCode: str
    displaySubIssueName: str
    mediaImpactScore05: Optional[float]
    mediaFinancialScore05: Optional[float]
    mediaAvgScore05: Optional[float]
    mediaAvgScore10: Optional[float]
    finalScore05: Optional[float]
    rankNo: Optional[int]

class MediaAnalyzeResponse(BaseModel):
    articleCount: int
    observedSubIssueCount: int
    savedSignalCount: int
    topIssues: List[MediaTopIssue]
    coverageStatus: str
    coverageDetail: dict

@router.post("/news/analyze", response_model=MediaAnalyzeResponse, summary="언론 기사 분석 및 저장")
async def analyze_media_news(request: MediaAnalyzeRequest, userModel = Depends(get_token)):
    try:
        # 1. 분석 실행 (pipeline → signal → score → DB 저장)
        scoredSignals = runMediaAnalysis(request.articles, request.runId, request.keywords)
        
        articleCount = len(request.articles)
        savedSignalCount = len(scoredSignals) if scoredSignals else 0
        
        # 2. topIssues: DB summary에서 media_external stage score 기준 조회
        topIssueRows = getTopIssuesByMediaScore(request.runId, limit=5)
        
        topIssues = []
        for row in topIssueRows:
            code = row.get("sub_issue_code", "")
            mediaImp = float(row["media_external_impact_score"]) if row.get("media_external_impact_score") is not None else None
            mediaFin = float(row["media_external_financial_score"]) if row.get("media_external_financial_score") is not None else None
            mediaAvg = float(row["media_avg_score"]) if row.get("media_avg_score") is not None else None
            finalScore = float(row["final_score"]) if row.get("final_score") is not None else None
            rankNo = int(row["rank_no"]) if row.get("rank_no") is not None else None
            
            topIssues.append(MediaTopIssue(
                subIssueCode=code,
                displaySubIssueName=getSubIssueDisplayName(code),
                mediaImpactScore05=mediaImp,
                mediaFinancialScore05=mediaFin,
                mediaAvgScore05=mediaAvg,
                mediaAvgScore10=round(mediaAvg * SCORE_UI_MULTIPLIER, 2) if mediaAvg is not None else None,
                finalScore05=finalScore,
                rankNo=rankNo
            ))
        
        observedSubIssueCount = len(topIssueRows)
        
        # 3. coverage: DB summary에서 실제 관측 stage 수 기반
        coverageInfo = getMediaCoverageFromSummary(request.runId)
        
        return MediaAnalyzeResponse(
            articleCount=articleCount,
            observedSubIssueCount=observedSubIssueCount,
            savedSignalCount=savedSignalCount,
            topIssues=topIssues,
            coverageStatus=coverageInfo["coverageStatus"],
            coverageDetail=coverageInfo
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

