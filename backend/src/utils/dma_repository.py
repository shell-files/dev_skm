import json
from typing import List, Dict, Any, Optional
from collections import defaultdict
from src.utils.db import save, addKey, findAll, findOne
from src.models.dma_engine import DMASignal, FinalMaterialityScore
from src.utils.dma_aggregator import (
    aggregate_media_signals, 
    aggregate_benchmark_signals, 
    calculate_final_materiality
)

def save_dma_signals(run_id: int, signals: List[DMASignal], file_id: Optional[int] = None, source_title: str = ""):
    """
    DMASignal 목록을 ESG_DMA_SIGNAL_DETAIL 테이블에 저장합니다.
    scoring_payload_json을 활용하여 상세 정보를 보존하고, ESG_DMA_EVIDENCE도 함께 저장합니다.
    저장 후 연관된 sub_issue_code에 대해 Stage Aggregation을 유발합니다.
    """
    updated_sub_issues = set()
    
    for sig in signals:
        # 1. ESG_DMA_EVIDENCE 저장 (addKey 사용)
        evidence_text = " ".join(sig.evidence_spans) if sig.evidence_spans else ""
        evidence_sql = """
            INSERT INTO ESG_DMA_EVIDENCE (
                esg_materiality_run_id, source_step, source_type, 
                source_title, te_sr_file_id, text_span
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        evidence_params = (
            run_id, sig.source_step, sig.source_type,
            source_title, file_id, evidence_text
        )
        
        evidence_id = None
        try:
            res = addKey(evidence_sql, evidence_params)
            if res[0]:
                evidence_id = res[1]
                sig.evidence_id = evidence_id
        except Exception as e:
            print(f"Error saving evidence: {e}")

        # 2. JSON 직렬화 및 ESG_DMA_SIGNAL_DETAIL 저장
        payload = sig.model_dump()
        payload_json = json.dumps(payload, ensure_ascii=False)
        
        impact_score = sig.impact_score_0_5 if sig.impact_score_0_5 is not None else None
        financial_score = sig.financial_score_0_5 if sig.financial_score_0_5 is not None else None
        
        sql = """
        INSERT INTO ESG_DMA_SIGNAL_DETAIL (
            esg_materiality_run_id,
            evidence_id,
            raw_issue_label,
            sub_issue_code,
            source_step,
            source_type,
            impact_score,
            financial_score,
            confidence_score,
            scoring_payload_json
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """
        params = (
            run_id,
            evidence_id,
            sig.raw_issue_label,
            sig.sub_issue_code,
            sig.source_step,
            sig.source_type,
            impact_score,
            financial_score,
            sig.confidence_score,
            payload_json
        )
        try:
            save(sql, params)
            updated_sub_issues.add((sig.sub_issue_code, sig.source_step))
        except Exception as e:
            print(f"Error saving DMA Signal {sig.sub_issue_code}: {e}")
            raise Exception(f"Failed to save signal: {e}")

    # 3. 변경된 sub_issue_code 단위로 Stage Aggregation 수행
    for sub_issue_code, source_step in updated_sub_issues:
        recalculate_stage_score(run_id, sub_issue_code, source_step)

def get_signals_by_group(run_id: int, sub_issue_code: str, source_step: str) -> List[DMASignal]:
    """
    특정 런의 특정 이슈, 특정 스테이지에 해당하는 모든 Signal Detail을 DB에서 가져와 DMASignal 객체 리스트로 반환합니다.
    """
    sql = """
        SELECT scoring_payload_json 
        FROM ESG_DMA_SIGNAL_DETAIL 
        WHERE esg_materiality_run_id = ? AND sub_issue_code = ? AND source_step = ? AND delete_yn = 0
    """
    rows = findAll(sql, (run_id, sub_issue_code, source_step))
    signals = []
    if rows:
        for row in rows:
            try:
                payload = json.loads(row["scoring_payload_json"])
                signals.append(DMASignal(**payload))
            except Exception as e:
                print(f"Error parsing JSON payload for {sub_issue_code}: {e}")
    return signals

def recalculate_stage_score(run_id: int, sub_issue_code: str, source_step: str):
    """
    DB에 저장된 Signal들을 기반으로 Stage Score를 다시 계산하고 UPSERT합니다.
    그 후 Final Score 산출을 트리거합니다.
    """
    signals = get_signals_by_group(run_id, sub_issue_code, source_step)
    
    if not signals:
        return
        
    impact_score = None
    financial_score = None
    
    if source_step == "benchmark":
        # 벤치마크 고유 통계 계산 (te_sr_file_id 기준 distinct 처리)
        leader_files = set(s.te_sr_file_id for s in signals if s.source_type == "leader_sr" and s.te_sr_file_id is not None)
        peer_files = set(s.te_sr_file_id for s in signals if s.source_type == "peer_sr" and s.te_sr_file_id is not None)
        own_files = set(s.te_sr_file_id for s in signals if s.source_type == "own_sr" and s.te_sr_file_id is not None)
        
        # 실제 전체 파일 수는 DB에서 별도 조회해야 하나 MVP 임시 로직으로 구현
        # 전체 Leader/Peer/Own 보고서 수 (현재는 추출된 파일의 모수만 쓴다고 가정)
        # 추후 전체 모수 조회를 위해 TE_SR_FILE 테이블 조회가 필요함
        total_leader = max(1, len(leader_files))
        total_peer = max(1, len(peer_files))
        total_own = max(1, len(own_files))
        
        leader_ratio = min(1.0, len(leader_files) / total_leader)
        peer_ratio = min(1.0, len(peer_files) / total_peer)
        own_ratio = min(1.0, len(own_files) / total_own)
        
        common_selection = (leader_ratio > 0.5 and peer_ratio > 0.5)
        blind_spot = (leader_ratio > 0.5 and own_ratio == 0.0)
        
        # 임의의 baseline score (Signal 중 첫번째 값을 활용하거나 3.0으로 고정)
        baseline_imp = signals[0].impact_score_0_5 if signals[0].impact_score_0_5 else 3.0
        baseline_fin = signals[0].financial_score_0_5 if signals[0].financial_score_0_5 else 3.0
        
        stage_score = aggregate_benchmark_signals(
            leader_ratio=leader_ratio,
            peer_ratio=peer_ratio,
            own_ratio=own_ratio,
            common_selection=common_selection,
            blind_spot=blind_spot,
            evidence_count=len(signals),
            baseline_impact_score=baseline_imp,
            baseline_financial_score=baseline_fin
        )
        impact_score = stage_score.impact_score_0_5
        financial_score = stage_score.financial_score_0_5
        
    elif source_step == "media_external":
        stage_score = aggregate_media_signals(signals)
        impact_score = stage_score.impact_score_0_5
        financial_score = stage_score.financial_score_0_5
        
    if source_step in ["benchmark", "media_external"]:
        # Stage Score UPSERT
        upsert_stage_score_summary(run_id, sub_issue_code, source_step, impact_score, financial_score)
        
    elif source_step == "survey":
        recalculate_survey_score(run_id, sub_issue_code)
        
    # Final Score 갱신
    recalculate_final_score(run_id, sub_issue_code)

def recalculate_survey_score(run_id: int, sub_issue_code: str):
    """
    ESG_DMA_SURVEY_RESPONSE 테이블을 조회하여 그룹별 가중 평균을 내어 Stage Score를 계산합니다.
    """
    sql = """
        SELECT respondent_group, AVG(normalized_score) as avg_score
        FROM ESG_DMA_SURVEY_RESPONSE
        WHERE esg_materiality_run_id = ? AND sub_issue_code = ? AND delete_yn = 0
        GROUP BY respondent_group
    """
    rows = findAll(sql, (run_id, sub_issue_code))
    
    if not rows:
        return
        
    group_scores = {row["respondent_group"]: row["avg_score"] for row in rows}
    
    # 임직원(employee), 경영진(management), 외부(external) 등 매핑 (MVP 기준 하드코딩 또는 유연하게 처리)
    employee_score = group_scores.get("employee", None)
    executive_score = group_scores.get("management", None)
    external_score = group_scores.get("external", None)
    
    # 설문 점수는 Impact/Financial이 통합된 문항일 수 있으나, 분리되어 있다면 조건부 산출.
    # MVP에서는 단일 점수를 양쪽에 복사하여 반영
    from src.utils.dma_aggregator import aggregate_survey_scores
    final_survey_score = aggregate_survey_scores(
        employee_score=float(employee_score) if employee_score else None,
        executive_score=float(executive_score) if executive_score else None,
        external_score=float(external_score) if external_score else None
    )
    
    upsert_stage_score_summary(run_id, sub_issue_code, "survey", final_survey_score, final_survey_score)

def upsert_stage_score_summary(run_id: int, sub_issue_code: str, stage: str, impact_score: Optional[float], financial_score: Optional[float]):
    if stage == "benchmark":
        sql = """
            INSERT INTO ESG_DMA_SCORE_SUMMARY (esg_materiality_run_id, sub_issue_code, benchmark_impact_score, benchmark_financial_score)
            VALUES (?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE 
            benchmark_impact_score = VALUES(benchmark_impact_score),
            benchmark_financial_score = VALUES(benchmark_financial_score)
        """
    elif stage == "media_external":
        sql = """
            INSERT INTO ESG_DMA_SCORE_SUMMARY (esg_materiality_run_id, sub_issue_code, media_external_impact_score, media_external_financial_score)
            VALUES (?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE 
            media_external_impact_score = VALUES(media_external_impact_score),
            media_external_financial_score = VALUES(media_external_financial_score)
        """
    elif stage == "survey":
        sql = """
            INSERT INTO ESG_DMA_SCORE_SUMMARY (esg_materiality_run_id, sub_issue_code, survey_impact_score, survey_financial_score)
            VALUES (?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE 
            survey_impact_score = VALUES(survey_impact_score),
            survey_financial_score = VALUES(survey_financial_score)
        """
    else:
        return
        
    try:
        save(sql, (run_id, sub_issue_code, impact_score, financial_score))
    except Exception as e:
        print(f"Error upserting stage summary for {sub_issue_code}: {e}")

def safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default

def recalculate_final_score(run_id: int, sub_issue_code: str):
    sql = """
        SELECT 
            benchmark_impact_score, benchmark_financial_score,
            media_external_impact_score, media_external_financial_score,
            survey_impact_score, survey_financial_score
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ? AND sub_issue_code = ?
    """
    row = findOne(sql, (run_id, sub_issue_code))
    if not row:
        return
        
    final_score_obj = calculate_final_materiality(
        sub_issue_code=sub_issue_code,
        survey_impact=row.get("survey_impact_score"), 
        survey_financial=row.get("survey_financial_score"),
        benchmark_impact=row.get("benchmark_impact_score"), 
        benchmark_financial=row.get("benchmark_financial_score"),
        media_impact=row.get("media_external_impact_score"), 
        media_financial=row.get("media_external_financial_score"),
        context_impact_modifier=0.0, # MVP에서는 0.0 고정
        context_financial_modifier=0.0
    )
    
    upsert_final_score_summary(run_id, final_score_obj)
    
    # rank_no 갱신
    update_dma_rankings(run_id)

def update_dma_rankings(run_id: int):
    """
    Final Score를 기준으로 내림차순 정렬하여 rank_no를 업데이트합니다.
    """
    sql = """
        SELECT id
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ? AND final_score IS NOT NULL
        ORDER BY final_score DESC
    """
    rows = findAll(sql, (run_id,))
    if not rows:
        return
        
    update_sql = "UPDATE ESG_DMA_SCORE_SUMMARY SET rank_no = ? WHERE id = ?"
    params = [(idx + 1, row["id"]) for idx, row in enumerate(rows)]
    
    from src.utils.db import saveMany
    saveMany(update_sql, params)

def upsert_final_score_summary(run_id: int, score: FinalMaterialityScore):
    sql = """
        INSERT INTO ESG_DMA_SCORE_SUMMARY (
            esg_materiality_run_id, sub_issue_code, 
            final_impact_score, final_financial_score, final_score
        )
        VALUES (?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
        final_impact_score = VALUES(final_impact_score),
        final_financial_score = VALUES(final_financial_score),
        final_score = VALUES(final_score)
    """
    params = (
        run_id, score.sub_issue_code, 
        score.final_impact_score, score.final_financial_score, score.final_score
    )
    try:
        save(sql, params)
    except Exception as e:
        print(f"Error upserting final DMA Summary {score.sub_issue_code}: {e}")
