from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from src.services.medias.service import runMediaAnalysis
from src.utils.auth import get_token
from src.utils.dmaaggregator import getCoverageStatus

router = APIRouter(tags=["media"])

class MediaAnalyzeRequest(BaseModel):
    runId: int
    articles: List[dict]
    keywords: Optional[List[str]] = []

class MediaAnalyzeResponse(BaseModel):
    articleCount: int
    observedSubIssueCount: int
    savedSignalCount: int
    topIssues: List[dict]
    coverageStatus: str

@router.post("/news/analyze", response_model=MediaAnalyzeResponse, summary="언론 기사 분석 및 저장")
async def analyze_media_news(request: MediaAnalyzeRequest, userModel = Depends(get_token)):
    try:
        # 동기 함수인 runMediaAnalysis를 호출 (키워드 전달)
        scoredSignals = runMediaAnalysis(request.articles, request.runId, request.keywords)
        
        articleCount = len(request.articles)
        savedSignalCount = len(scoredSignals) if scoredSignals else 0
        
        issue_counts = {}
        if scoredSignals:
            for sig in scoredSignals:
                code = sig.subIssueCode
                name = sig.displaySubIssueName
                if code not in issue_counts:
                    issue_counts[code] = {"code": code, "name": name, "count": 0, "score_sum": 0.0}
                issue_counts[code]["count"] += 1
                issue_counts[code]["score_sum"] += sig.confidenceScore
            
        observedSubIssueCount = len(issue_counts)
        
        sorted_issues = sorted(
            issue_counts.values(), 
            key=lambda x: (x["count"], x["score_sum"]), 
            reverse=True
        )
        
        topIssues = sorted_issues[:5]
        
        # Coverage: media만 관측된 상태이므로 LIMITED (1개 stage)
        # DB 컬럼 추가 없이 API에서 재계산
        stageCount = 1 if savedSignalCount > 0 else 0
        coverageStatus = getCoverageStatus(stageCount)
        
        return MediaAnalyzeResponse(
            articleCount=articleCount,
            observedSubIssueCount=observedSubIssueCount,
            savedSignalCount=savedSignalCount,
            topIssues=topIssues,
            coverageStatus=coverageStatus
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
