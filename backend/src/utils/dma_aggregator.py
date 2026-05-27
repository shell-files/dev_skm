from typing import List, Tuple, Optional
from src.models.dma_engine import DMASignal, StageScore, FinalMaterialityScore
from src.utils.dma_scoring import clamp

SOURCE_WEIGHTS = {
    "news": 1.0,
    "agency": 1.2,
    "regulation": 1.3
}

def aggregate_benchmark_signals(
    leader_ratio: float,
    peer_ratio: float,
    own_ratio: float,
    common_selection: bool,
    blind_spot: bool,
    evidence_count: int,
    baseline_impact_score: float,
    baseline_financial_score: float
) -> StageScore:
    """
    벤치마킹 시그널을 집계합니다.
    """
    MIN_BENCHMARK_SIGNAL = 0.15
    
    benchmark_signal = (
        0.40 * leader_ratio
        + 0.35 * peer_ratio
        + 0.15 * own_ratio
    )
    
    if common_selection:
        benchmark_signal += 0.10
    if blind_spot:
        benchmark_signal += 0.10

    benchmark_signal = min(1.0, benchmark_signal)

    if evidence_count == 0 or benchmark_signal < MIN_BENCHMARK_SIGNAL:
        return StageScore(impact_score_0_5=None, financial_score_0_5=None)
        
    multiplier = 0.5 + 0.5 * benchmark_signal
    benchmark_impact = baseline_impact_score * multiplier
    benchmark_financial = baseline_financial_score * multiplier
    
    return StageScore(
        impact_score_0_5=clamp(benchmark_impact, 0, 5),
        financial_score_0_5=clamp(benchmark_financial, 0, 5)
    )

def aggregate_survey_scores(
    employee_score: Optional[float],
    executive_score: Optional[float],
    external_score: Optional[float]
) -> Optional[float]:
    """
    설문 점수 가중평균 (임직원 0.3, 경영진 0.4, 외부 0.3)
    """
    return weighted_avg_available([
        (employee_score, 0.3),
        (executive_score, 0.4),
        (external_score, 0.3)
    ])

def aggregate_media_signals(signals: List[DMASignal]) -> StageScore:
    """
    미디어 시그널들을 집계하여 하나의 StageScore로 변환합니다.
    Impact와 Financial의 분모를 철저히 분리하여 미관측 축이 점수를 깎지 않도록 합니다.
    """
    financial_sum, financial_weight_sum = 0.0, 0.0
    impact_sum, impact_weight_sum = 0.0, 0.0
    
    for sig in signals:
        w = SOURCE_WEIGHTS.get(sig.source_type, 1.0) * sig.confidence_score
        
        if sig.financial_score_0_5 is not None:
            financial_sum += sig.financial_score_0_5 * w
            financial_weight_sum += w
            
        if sig.impact_score_0_5 is not None:
            impact_sum += sig.impact_score_0_5 * w
            impact_weight_sum += w
            
    return StageScore(
        financial_score_0_5=financial_sum / financial_weight_sum if financial_weight_sum > 0 else None,
        impact_score_0_5=impact_sum / impact_weight_sum if impact_weight_sum > 0 else None
    )

def weighted_avg_available(items: List[Tuple[Optional[float], float]]) -> Optional[float]:
    """
    NULL을 제외하고 남은 관측치들의 재가중 평균을 계산합니다.
    """
    score_sum, weight_sum = 0.0, 0.0
    for score, weight in items:
        if score is not None:
            score_sum += score * weight
            weight_sum += weight
            
    return score_sum / weight_sum if weight_sum > 0 else None

def get_coverage_status(count: int) -> str:
    """
    관측된 스테이지 개수에 따른 커버리지 상태를 반환합니다.
    """
    if count >= 3: return "FULL"
    if count == 2: return "PARTIAL"
    if count == 1: return "LIMITED"
    return "NONE"

def calculate_final_materiality(
    sub_issue_code: str,
    survey_impact: Optional[float], survey_financial: Optional[float],
    benchmark_impact: Optional[float], benchmark_financial: Optional[float],
    media_impact: Optional[float], media_financial: Optional[float],
    context_impact_modifier: float = 0.0,
    context_financial_modifier: float = 0.0
) -> FinalMaterialityScore:
    """
    Survey, Benchmark, Media의 3개 Stage 결과를 모아서 최종 FinalMaterialityScore를 산출합니다.
    - NULL 제외 재가중 평균 적용
    - Impact/Financial 축별 커버리지 도출
    - 방어 코드 적용된 context modifier 가산
    - 결측치 처리 (단일 축 존재 여부)
    """
    
    # 1. Raw Final Aggregation (NULL 제외 가중평균)
    raw_final_impact = weighted_avg_available([
        (survey_impact, 0.36),
        (benchmark_impact, 0.32),
        (media_impact, 0.32)
    ])
    
    raw_final_financial = weighted_avg_available([
        (survey_financial, 0.36),
        (benchmark_financial, 0.32),
        (media_financial, 0.32)
    ])
    
    # 2. Coverage Calculation (Impact / Financial 분리)
    impact_count = sum(1 for x in [survey_impact, benchmark_impact, media_impact] if x is not None)
    financial_count = sum(1 for x in [survey_financial, benchmark_financial, media_financial] if x is not None)
    
    coverage = {
        "impact": {
            "benchmark_observed": benchmark_impact is not None,
            "media_observed": media_impact is not None,
            "survey_observed": survey_impact is not None,
            "available_stage_count": impact_count,
            "coverage_status": get_coverage_status(impact_count)
        },
        "financial": {
            "benchmark_observed": benchmark_financial is not None,
            "media_observed": media_financial is not None,
            "survey_observed": survey_financial is not None,
            "available_stage_count": financial_count,
            "coverage_status": get_coverage_status(financial_count)
        }
    }
    
    # 3. Context Modifier 방어 로직 적용
    if raw_final_impact is None:
        final_impact = None
    else:
        final_impact = clamp(raw_final_impact + context_impact_modifier, 0, 5)

    if raw_final_financial is None:
        final_financial = None
    else:
        final_financial = clamp(raw_final_financial + context_financial_modifier, 0, 5)

    # 4. 결측치(단일 축) 처리 기준 적용
    if final_impact is None and final_financial is None:
        final_score = None
    elif final_impact is None:
        final_score = final_financial
    elif final_financial is None:
        final_score = final_impact
    else:
        final_score = (final_impact + final_financial) / 2.0
        
    return FinalMaterialityScore(
        sub_issue_code=sub_issue_code,
        final_impact_score=final_impact,
        final_financial_score=final_financial,
        final_score=final_score,
        coverage=coverage
    )
