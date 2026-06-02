"""
Domain: DMA Materiality
Layer: utils/aggregation
Responsibility:
- Aggregate media/benchmark/survey stage scores
- Calculate final materiality score from stage scores
- Apply additive context modifier only at final aggregation
- Preserve None-as-unobserved behavior
Public functions:
- aggregateMedia
- aggregateMediaSignals
- aggregateBenchmark
- aggregateBenchmarkSignals
- aggregateSurvey
- aggregateSurveyScores
- calcWeightedAvg
- weightedAvgAvailable
- calcFinal
- calculateFinalMateriality
Do not:
- do not mutate unrelated DB state
- do not change scoring formula unless explicitly requested
- do not change final/stage weights in this step
- do not treat unobserved score as zero
- do not call DB directly unless already existing behavior
- do not call FastAPI router directly
- do not modify auth/token/common code

DMA Aggregator v1 (Freeze)

Stage별 시그널 집계 및 Final Materiality Score 산출 모듈.
- DB/API canonical score = 0~5
- NULL 제외 재가중 평균(weightedAvgAvailable) 적용
- benchmark ratio/blind spot 산식은 v1 provisional (후속 정교화 예정)
"""

from typing import List, Tuple, Optional
from src.models.dmaengine import DMASignal, StageScore, FinalMaterialityScore
from src.utils.dmascoring import clamp

# ──────────────────────────────────────────────
# 가중치 상수 (v1 Freeze 확정)
# ──────────────────────────────────────────────

# media_external 내부 sourceType 가중치
MEDIA_SOURCE_TYPE_WEIGHTS = {
    "news": 1.0,
    "agency": 1.2,
    "regulation": 1.3
}

# final stage 가중치 (survey > benchmark > media_external)
FINAL_STAGE_WEIGHTS = {
    "survey": 0.40,
    "benchmark": 0.35,
    "media_external": 0.25
}

# survey 내부 그룹 가중치 (현행 유지, axis 분리 설문 도입 시 재검토)
SURVEY_GROUP_WEIGHTS = {
    "employee": 0.30,
    "management": 0.40,
    "external": 0.30
}

# ──────────────────────────────────────────────
# Benchmark Aggregation (v1 provisional)
# ──────────────────────────────────────────────

def aggregateBenchmark(
    leaderRatio: float,
    peerRatio: float,
    ownRatio: float,
    commonSelection: bool,
    blindSpot: bool,
    evidenceCount: int,
    baselineImpactScore: float,
    baselineFinancialScore: float
) -> StageScore:
    """
    벤치마킹 시그널을 집계합니다.
    [v1 provisional] ratio/blind spot 산식은 후속 benchmark 정교화 단계에서 별도 개선 예정.
    """
    MIN_BENCHMARK_SIGNAL = 0.15
    
    benchmarkSignal = (
        0.40 * leaderRatio
        + 0.35 * peerRatio
        + 0.15 * ownRatio
    )
    
    if commonSelection:
        benchmarkSignal += 0.10
    if blindSpot:
        benchmarkSignal += 0.10

    benchmarkSignal = min(1.0, benchmarkSignal)

    if evidenceCount == 0 or benchmarkSignal < MIN_BENCHMARK_SIGNAL:
        return StageScore(impactScore05=None, financialScore05=None)
        
    multiplier = 0.5 + 0.5 * benchmarkSignal
    benchmarkImpact = baselineImpactScore * multiplier
    benchmarkFinancial = baselineFinancialScore * multiplier
    
    return StageScore(
        impactScore05=clamp(benchmarkImpact, 0, 5),
        financialScore05=clamp(benchmarkFinancial, 0, 5)
    )

# ──────────────────────────────────────────────
# Survey Aggregation
# ──────────────────────────────────────────────

def aggregateSurvey(
    employeeScore: Optional[float],
    executiveScore: Optional[float],
    externalScore: Optional[float]
) -> Optional[float]:
    """
    설문 점수 가중평균.
    weight: employee=0.30, management=0.40, external=0.30 (v1 확정)
    axis 분리 설문 도입 시 재검토 예정.
    """
    return calcWeightedAvg([
        (employeeScore, SURVEY_GROUP_WEIGHTS["employee"]),
        (executiveScore, SURVEY_GROUP_WEIGHTS["management"]),
        (externalScore, SURVEY_GROUP_WEIGHTS["external"])
    ])

# ──────────────────────────────────────────────
# Media Aggregation
# ──────────────────────────────────────────────

def aggregateMedia(signals: List[DMASignal]) -> StageScore:
    """
    미디어 시그널들을 집계하여 하나의 StageScore로 반환합니다.
    Impact와 Financial의 분모를 철저히 분리하여 미관측 축이 점수를 깎지 않도록 합니다.
    sourceType별 가중치: news=1.0, agency=1.2, regulation=1.3
    """
    financialSum, financialWeightSum = 0.0, 0.0
    impactSum, impactWeightSum = 0.0, 0.0
    
    for sig in signals:
        w = MEDIA_SOURCE_TYPE_WEIGHTS.get(sig.sourceType, 1.0) * sig.confidenceScore
        
        if sig.financialScore05 is not None:
            financialSum += sig.financialScore05 * w
            financialWeightSum += w
            
        if sig.impactScore05 is not None:
            impactSum += sig.impactScore05 * w
            impactWeightSum += w
            
    return StageScore(
        financialScore05=financialSum / financialWeightSum if financialWeightSum > 0 else None,
        impactScore05=impactSum / impactWeightSum if impactWeightSum > 0 else None
    )

# ──────────────────────────────────────────────
# 공통 유틸
# ──────────────────────────────────────────────

def calcWeightedAvg(items: List[Tuple[Optional[float], float]]) -> Optional[float]:
    """
    NULL을 제외하고 관측치들의 가중 평균을 계산합니다.
    미관측 stage는 0점 처리하지 않고 분모에서 제외합니다.
    """
    scoreSum, weightSum = 0.0, 0.0
    for score, weight in items:
        if score is not None:
            scoreSum += score * weight
            weightSum += weight
            
    return scoreSum / weightSum if weightSum > 0 else None

def getCoverageStatus(count: int) -> str:
    """
    관측된 스테이지 개수에 따른 커버리지 상태를 반환합니다.
    FULL: benchmark + media + survey 모두 있음
    PARTIAL: 2개 stage 있음
    LIMITED: 1개 stage만 있음
    NO_DATA: 없음
    """
    if count >= 3: return "FULL"
    if count == 2: return "PARTIAL"
    if count == 1: return "LIMITED"
    return "NO_DATA"

# ──────────────────────────────────────────────
# Final Materiality Score
# ──────────────────────────────────────────────

def calcFinal(
    subIssueCode: str,
    surveyImpact: Optional[float], surveyFinancial: Optional[float],
    benchmarkImpact: Optional[float], benchmarkFinancial: Optional[float],
    mediaImpact: Optional[float], mediaFinancial: Optional[float],
    contextImpactModifier: float = 0.0,
    contextFinancialModifier: float = 0.0
) -> FinalMaterialityScore:
    """
    Survey, Benchmark, Media의 3개 Stage 결과를 모아서 최종 FinalMaterialityScore를 산출합니다.
    - NULL 제외 가중 평균 적용 (weightedAvgAvailable)
    - final weight: survey=0.40, benchmark=0.35, media_external=0.25 (v1 확정)
    - Impact/Financial 축별 커버리지 도출
    - 방어 코드 적용, context modifier 가산, 결측치 처리
    """
    
    # 1. Raw Final Aggregation (NULL 제외 가중평균)
    rawFinalImpact = calcWeightedAvg([
        (surveyImpact, FINAL_STAGE_WEIGHTS["survey"]),
        (benchmarkImpact, FINAL_STAGE_WEIGHTS["benchmark"]),
        (mediaImpact, FINAL_STAGE_WEIGHTS["media_external"])
    ])
    
    rawFinalFinancial = calcWeightedAvg([
        (surveyFinancial, FINAL_STAGE_WEIGHTS["survey"]),
        (benchmarkFinancial, FINAL_STAGE_WEIGHTS["benchmark"]),
        (mediaFinancial, FINAL_STAGE_WEIGHTS["media_external"])
    ])
    
    # 2. Coverage Calculation (Impact / Financial 분리)
    impactCount = sum(1 for x in [surveyImpact, benchmarkImpact, mediaImpact] if x is not None)
    financialCount = sum(1 for x in [surveyFinancial, benchmarkFinancial, mediaFinancial] if x is not None)
    
    coverage = {
        "impact": {
            "benchmark_observed": benchmarkImpact is not None,
            "media_observed": mediaImpact is not None,
            "survey_observed": surveyImpact is not None,
            "available_stage_count": impactCount,
            "coverage_status": getCoverageStatus(impactCount)
        },
        "financial": {
            "benchmark_observed": benchmarkFinancial is not None,
            "media_observed": mediaFinancial is not None,
            "survey_observed": surveyFinancial is not None,
            "available_stage_count": financialCount,
            "coverage_status": getCoverageStatus(financialCount)
        }
    }
    
    # 3. Context Modifier 방어 로직 적용
    if rawFinalImpact is None:
        finalImpact = None
    else:
        finalImpact = clamp(rawFinalImpact + contextImpactModifier, 0, 5)

    if rawFinalFinancial is None:
        finalFinancial = None
    else:
        finalFinancial = clamp(rawFinalFinancial + contextFinancialModifier, 0, 5)

    # 4. 결측치 단일 축 처리 기준 적용
    if finalImpact is None and finalFinancial is None:
        finalScore = None
    elif finalImpact is None:
        finalScore = finalFinancial
    elif finalFinancial is None:
        finalScore = finalImpact
    else:
        finalScore = (finalImpact + finalFinancial) / 2.0
        
    return FinalMaterialityScore(
        subIssueCode=subIssueCode,
        finalImpactScore=finalImpact,
        finalFinancialScore=finalFinancial,
        finalScore=finalScore,
        coverage=coverage
    )


# Compatibility wrappers for previous public names

def aggregateBenchmarkSignals(
    leaderRatio: float,
    peerRatio: float,
    ownRatio: float,
    commonSelection: bool,
    blindSpot: bool,
    evidenceCount: int,
    baselineImpactScore: float,
    baselineFinancialScore: float,
) -> StageScore:
    return aggregateBenchmark(
        leaderRatio,
        peerRatio,
        ownRatio,
        commonSelection,
        blindSpot,
        evidenceCount,
        baselineImpactScore,
        baselineFinancialScore,
    )


def aggregateSurveyScores(
    employeeScore: Optional[float],
    executiveScore: Optional[float],
    externalScore: Optional[float],
) -> Optional[float]:
    return aggregateSurvey(employeeScore, executiveScore, externalScore)


def aggregateMediaSignals(signals: List[DMASignal]) -> StageScore:
    return aggregateMedia(signals)


def weightedAvgAvailable(items: List[Tuple[Optional[float], float]]) -> Optional[float]:
    return calcWeightedAvg(items)


def calculateFinalMateriality(
    subIssueCode: str,
    surveyImpact: Optional[float], surveyFinancial: Optional[float],
    benchmarkImpact: Optional[float], benchmarkFinancial: Optional[float],
    mediaImpact: Optional[float], mediaFinancial: Optional[float],
    contextImpactModifier: float = 0.0,
    contextFinancialModifier: float = 0.0,
) -> FinalMaterialityScore:
    return calcFinal(
        subIssueCode,
        surveyImpact,
        surveyFinancial,
        benchmarkImpact,
        benchmarkFinancial,
        mediaImpact,
        mediaFinancial,
        contextImpactModifier,
        contextFinancialModifier,
    )


__all__ = [
    "MEDIA_SOURCE_TYPE_WEIGHTS",
    "FINAL_STAGE_WEIGHTS",
    "SURVEY_GROUP_WEIGHTS",
    "aggregateBenchmark",
    "aggregateBenchmarkSignals",
    "aggregateSurvey",
    "aggregateSurveyScores",
    "aggregateMedia",
    "aggregateMediaSignals",
    "calcWeightedAvg",
    "weightedAvgAvailable",
    "getCoverageStatus",
    "calcFinal",
    "calculateFinalMateriality",
]
