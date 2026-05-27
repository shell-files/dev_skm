from typing import List, Tuple, Optional
from src.models.dmaengine import DMASignal, StageScore, FinalMaterialityScore
from src.utils.dmascoring import clamp

SOURCE_WEIGHTS = {
    "news": 1.0,
    "agency": 1.2,
    "regulation": 1.3
}

def aggregateBenchmarkSignals(
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

def aggregateSurveyScores(
    employeeScore: Optional[float],
    executiveScore: Optional[float],
    externalScore: Optional[float]
) -> Optional[float]:
    """
    설문 점수 가중평균 (임직원 0.3, 경영진 0.4, 외부 0.3)
    """
    return weightedAvgAvailable([
        (employeeScore, 0.3),
        (executiveScore, 0.4),
        (externalScore, 0.3)
    ])

def aggregateMediaSignals(signals: List[DMASignal]) -> StageScore:
    """
    미디어 시그널들을 집계하여 하나의 StageScore로 반환합니다.
    Impact와 Financial의 분모를 철저히 분리하여 미관측 축이 점수를 깎지 않도록 합니다.
    """
    financialSum, financialWeightSum = 0.0, 0.0
    impactSum, impactWeightSum = 0.0, 0.0
    
    for sig in signals:
        w = SOURCE_WEIGHTS.get(sig.sourceType, 1.0) * sig.confidenceScore
        
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

def weightedAvgAvailable(items: List[Tuple[Optional[float], float]]) -> Optional[float]:
    """
    NULL을 제외하고 단일 관측치들의 가중 평균을 계산합니다.
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
    """
    if count >= 3: return "FULL"
    if count == 2: return "PARTIAL"
    if count == 1: return "LIMITED"
    return "NONE"

def calculateFinalMateriality(
    subIssueCode: str,
    surveyImpact: Optional[float], surveyFinancial: Optional[float],
    benchmarkImpact: Optional[float], benchmarkFinancial: Optional[float],
    mediaImpact: Optional[float], mediaFinancial: Optional[float],
    contextImpactModifier: float = 0.0,
    contextFinancialModifier: float = 0.0
) -> FinalMaterialityScore:
    """
    Survey, Benchmark, Media의 3개 Stage 결과를 모아서 최종 FinalMaterialityScore를 산출합니다.
    - NULL 제외 가중 평균 적용
    - Impact/Financial 축별 커버리지 도출
    - 방어 코드 적용, context modifier 가산, 결측치 처리 (단일 축 존재 여부)
    """
    
    # 1. Raw Final Aggregation (NULL 제외 가중평균)
    rawFinalImpact = weightedAvgAvailable([
        (surveyImpact, 0.36),
        (benchmarkImpact, 0.32),
        (mediaImpact, 0.32)
    ])
    
    rawFinalFinancial = weightedAvgAvailable([
        (surveyFinancial, 0.36),
        (benchmarkFinancial, 0.32),
        (mediaFinancial, 0.32)
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
