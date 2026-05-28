"""
DMA 통합 결과 조회 API (Result API Freeze)

ESG_DMA_SCORE_SUMMARY 기반으로 최종 결과를 반환합니다.
- DB canonical score: 0~5
- UI display score: score05 * SCORE_UI_MULTIPLIER (0~10)
- coverage: impact/financial 축별 분리
- 정렬: rank_no ASC (final_score DESC 기준 산출된 순위)

fastset.py가 모듈명 기준 prefix="/materiality"를 자동 부여하므로
라우터에 prefix를 중복 선언하지 않습니다.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from src.utils.auth import get_token
from src.utils.dmarepository import getDmaResults
from src.utils.dmascoring import SCORE_UI_MULTIPLIER
from src.utils.dmaaggregator import getCoverageStatus
from src.utils.subissuemaster import getSubIssueDisplayName

router = APIRouter(tags=["materiality"])


# ──────────────────────────────────────────────
# Response Models
# ──────────────────────────────────────────────

class CoverageDetail(BaseModel):
    impactCoverageStatus: str
    financialCoverageStatus: str
    benchmarkObserved: bool
    mediaObserved: bool
    surveyObserved: bool

class DmaResultItem(BaseModel):
    rankNo: Optional[int]
    subIssueCode: str
    displaySubIssueName: str
    # Stage scores (0~5 canonical)
    benchmarkImpactScore05: Optional[float]
    benchmarkFinancialScore05: Optional[float]
    mediaImpactScore05: Optional[float]
    mediaFinancialScore05: Optional[float]
    surveyImpactScore05: Optional[float]
    surveyFinancialScore05: Optional[float]
    # Final scores (0~5 canonical)
    finalImpactScore05: Optional[float]
    finalFinancialScore05: Optional[float]
    finalScore05: Optional[float]
    # Final scores (0~10 UI display)
    finalImpactScore10: Optional[float]
    finalFinancialScore10: Optional[float]
    finalScore10: Optional[float]
    # Coverage (축별 분리)
    coverage: CoverageDetail

class DmaResultResponse(BaseModel):
    runId: int
    totalSubIssueCount: int
    scoredSubIssueCount: int
    items: List[DmaResultItem]


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────

def _toScore10(score05: Optional[float]) -> Optional[float]:
    """0~5 canonical score를 0~10 UI display score로 환산"""
    if score05 is None:
        return None
    return round(score05 * SCORE_UI_MULTIPLIER, 2)

def _safeFloat(value) -> Optional[float]:
    """DB row 값을 안전하게 float으로 변환"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ──────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────

@router.get("/results/{runId}", response_model=DmaResultResponse, summary="DMA 통합 결과 조회")
async def get_dma_results(runId: int, userModel=Depends(get_token)):
    """
    ESG_DMA_SCORE_SUMMARY 기반 통합 결과를 반환합니다.
    - rankNo, finalScore05/10, stage별 score, coverage (축별 분리)
    - 정렬: rank_no ASC
    """
    try:
        rows = getDmaResults(runId)

        items = []
        for row in rows:
            subIssueCode = row.get("sub_issue_code", "")

            # Stage scores
            benchImp = _safeFloat(row.get("benchmark_impact_score"))
            benchFin = _safeFloat(row.get("benchmark_financial_score"))
            mediaImp = _safeFloat(row.get("media_external_impact_score"))
            mediaFin = _safeFloat(row.get("media_external_financial_score"))
            surveyImp = _safeFloat(row.get("survey_impact_score"))
            surveyFin = _safeFloat(row.get("survey_financial_score"))

            # Final scores
            finalImp = _safeFloat(row.get("final_impact_score"))
            finalFin = _safeFloat(row.get("final_financial_score"))
            finalScore = _safeFloat(row.get("final_score"))

            # Coverage: impact/financial 축별 분리
            impactCount = sum(1 for x in [surveyImp, benchImp, mediaImp] if x is not None)
            financialCount = sum(1 for x in [surveyFin, benchFin, mediaFin] if x is not None)

            coverage = CoverageDetail(
                impactCoverageStatus=getCoverageStatus(impactCount),
                financialCoverageStatus=getCoverageStatus(financialCount),
                benchmarkObserved=(benchImp is not None or benchFin is not None),
                mediaObserved=(mediaImp is not None or mediaFin is not None),
                surveyObserved=(surveyImp is not None or surveyFin is not None)
            )

            rankNo = row.get("rank_no")
            if rankNo is not None:
                rankNo = int(rankNo)

            items.append(DmaResultItem(
                rankNo=rankNo,
                subIssueCode=subIssueCode,
                displaySubIssueName=getSubIssueDisplayName(subIssueCode),
                benchmarkImpactScore05=benchImp,
                benchmarkFinancialScore05=benchFin,
                mediaImpactScore05=mediaImp,
                mediaFinancialScore05=mediaFin,
                surveyImpactScore05=surveyImp,
                surveyFinancialScore05=surveyFin,
                finalImpactScore05=finalImp,
                finalFinancialScore05=finalFin,
                finalScore05=finalScore,
                finalImpactScore10=_toScore10(finalImp),
                finalFinancialScore10=_toScore10(finalFin),
                finalScore10=_toScore10(finalScore),
                coverage=coverage
            ))

        scoredCount = sum(1 for item in items if item.finalScore05 is not None)

        return DmaResultResponse(
            runId=runId,
            totalSubIssueCount=len(items),
            scoredSubIssueCount=scoredCount,
            items=items
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
