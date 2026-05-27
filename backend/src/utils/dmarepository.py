import json
from typing import List, Dict, Any, Optional
from collections import defaultdict
from src.utils.db import save, addKey, findAll, findOne
from src.models.dmaengine import DMASignal, FinalMaterialityScore
from src.utils.dmaaggregator import (
    aggregateMediaSignals, 
    aggregateBenchmarkSignals, 
    calculateFinalMateriality
)

def saveDmaSignals(runId: int, signals: List[DMASignal], fileId: Optional[int] = None, sourceTitle: str = ""):
    """
    DMASignal 목록을 ESG_DMA_SIGNAL_DETAIL 테이블에 저장합니다.
    scoring_payload_json을 사용하여 상세 정보를 보존하고, ESG_DMA_EVIDENCE와 함께 저장합니다.
    저장 후 연관된 sub_issue_code에 대한 Stage Aggregation을 유발합니다.
    """
    updatedSubIssues = set()
    
    for sig in signals:
        # 1. ESG_DMA_EVIDENCE 저장 (addKey 사용)
        evidenceText = " ".join(sig.evidenceSpans) if sig.evidenceSpans else ""
        evidenceSql = """
            INSERT INTO ESG_DMA_EVIDENCE (
                esg_materiality_run_id, source_step, source_type, 
                source_title, te_sr_file_id, text_span
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        evidenceParams = (
            runId, sig.sourceStep, sig.sourceType,
            sourceTitle, fileId, evidenceText
        )
        
        evidenceId = None
        try:
            res = addKey(evidenceSql, evidenceParams)
            if res[0]:
                evidenceId = res[1]
                sig.evidenceId = str(evidenceId)
        except Exception as e:
            print(f"Error saving evidence: {e}")

        # 2. JSON 직렬화 및 ESG_DMA_SIGNAL_DETAIL 저장
        payload = sig.model_dump(by_alias=False)
        payloadJson = json.dumps(payload, ensure_ascii=False)
        
        impactScore = sig.impactScore05 if sig.impactScore05 is not None else None
        financialScore = sig.financialScore05 if sig.financialScore05 is not None else None
        
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
            runId,
            evidenceId,
            sig.rawIssueLabel,
            sig.subIssueCode,
            sig.sourceStep,
            sig.sourceType,
            impactScore,
            financialScore,
            sig.confidenceScore,
            payloadJson
        )
        try:
            save(sql, params)
            updatedSubIssues.add((sig.subIssueCode, sig.sourceStep))
        except Exception as e:
            print(f"Error saving DMA Signal {sig.subIssueCode}: {e}")
            raise Exception(f"Failed to save signal: {e}")

    # 3. 변경된 subIssueCode 단위로 Stage Aggregation 수행
    for subIssueCode, sourceStep in updatedSubIssues:
        recalculateStageScore(runId, subIssueCode, sourceStep)

def getSignalsByGroup(runId: int, subIssueCode: str, sourceStep: str) -> List[DMASignal]:
    """
    특정 런의 특정 이슈, 특정 스테이지에 해당하는 모든 Signal Detail을 DB에서 가져와 DMASignal 객체 리스트로 반환합니다.
    """
    sql = """
        SELECT scoring_payload_json 
        FROM ESG_DMA_SIGNAL_DETAIL 
        WHERE esg_materiality_run_id = ? AND sub_issue_code = ? AND source_step = ? AND delete_yn = 0
    """
    rows = findAll(sql, (runId, subIssueCode, sourceStep))
    signals = []
    if rows:
        for row in rows:
            try:
                payload = json.loads(row["scoring_payload_json"])
                signals.append(DMASignal(**payload))
            except Exception as e:
                print(f"Error parsing JSON payload for {subIssueCode}: {e}")
    return signals

def recalculateStageScore(runId: int, subIssueCode: str, sourceStep: str):
    """
    DB에 저장된 Signal들을 기반으로 Stage Score를 다시 계산하고 UPSERT합니다.
    그 후 Final Score 산출을 트리거합니다.
    """
    signals = getSignalsByGroup(runId, subIssueCode, sourceStep)
    
    if not signals:
        return
        
    impactScore = None
    financialScore = None
    
    if sourceStep == "benchmark":
        leaderFiles = set(s.teSrFileId for s in signals if s.sourceType == "leader_sr" and s.teSrFileId is not None)
        peerFiles = set(s.teSrFileId for s in signals if s.sourceType == "peer_sr" and s.teSrFileId is not None)
        ownFiles = set(s.teSrFileId for s in signals if s.sourceType == "own_sr" and s.teSrFileId is not None)
        
        from src.utils.settings import settings
        totalSql = f"""
            SELECT aes_d(type, '{settings.maria_db_key}') as raw_source_type
            FROM TE_SR_FILE
            WHERE delete_yn = 0
        """
        rows = findAll(totalSql)
        
        typeCounts = {"leader_sr": 0, "peer_sr": 0, "own_sr": 0}
        for row in rows:
            raw_type = str(row.get("raw_source_type", "")).lower()
            if "leader" in raw_type or "리더" in raw_type:
                typeCounts["leader_sr"] += 1
            elif "peer" in raw_type or "피어" in raw_type or "동종" in raw_type:
                typeCounts["peer_sr"] += 1
            elif "own" in raw_type or "자사" in raw_type:
                typeCounts["own_sr"] += 1
        
        totalLeader = max(1, typeCounts.get("leader_sr", 1))
        totalPeer = max(1, typeCounts.get("peer_sr", 1))
        totalOwn = max(1, typeCounts.get("own_sr", 1))
        
        leaderRatio = min(1.0, len(leaderFiles) / totalLeader)
        peerRatio = min(1.0, len(peerFiles) / totalPeer)
        ownRatio = min(1.0, len(ownFiles) / totalOwn)
        
        commonSelection = (leaderRatio > 0.5 and peerRatio > 0.5)
        blindSpot = (leaderRatio > 0.5 and ownRatio == 0.0)
        
        baselineImp = signals[0].impactScore05 if signals[0].impactScore05 else 3.0
        baselineFin = signals[0].financialScore05 if signals[0].financialScore05 else 3.0
        
        stageScore = aggregateBenchmarkSignals(
            leaderRatio=leaderRatio,
            peerRatio=peerRatio,
            ownRatio=ownRatio,
            commonSelection=commonSelection,
            blindSpot=blindSpot,
            evidenceCount=len(signals),
            baselineImpactScore=baselineImp,
            baselineFinancialScore=baselineFin
        )
        impactScore = stageScore.impactScore05
        financialScore = stageScore.financialScore05
        
    elif sourceStep == "media_external":
        stageScore = aggregateMediaSignals(signals)
        impactScore = stageScore.impactScore05
        financialScore = stageScore.financialScore05
        
    if sourceStep in ["benchmark", "media_external"]:
        upsertStageScoreSummary(runId, subIssueCode, sourceStep, impactScore, financialScore)
        
    elif sourceStep == "survey":
        recalculateSurveyScore(runId, subIssueCode)
        
    recalculateFinalScore(runId, subIssueCode)

def recalculateSurveyScore(runId: int, subIssueCode: str):
    """
    ESG_DMA_SURVEY_RESPONSE 테이블을 조회하여 그룹별 가중 평균을 내어 Stage Score를 계산합니다.
    """
    sql = """
        SELECT respondent_group, AVG(normalized_score) as avg_score
        FROM ESG_DMA_SURVEY_RESPONSE
        WHERE esg_materiality_run_id = ? AND sub_issue_code = ? AND delete_yn = 0
        GROUP BY respondent_group
    """
    rows = findAll(sql, (runId, subIssueCode))
    
    if not rows:
        return
        
    groupScores = {row["respondent_group"]: row["avg_score"] for row in rows}
    
    employeeScore = groupScores.get("employee", None)
    executiveScore = groupScores.get("management", None)
    externalScore = groupScores.get("external", None)
    
    from src.utils.dmaaggregator import aggregateSurveyScores
    finalSurveyScore = aggregateSurveyScores(
        employeeScore=float(employeeScore) if employeeScore else None,
        executiveScore=float(executiveScore) if executiveScore else None,
        externalScore=float(externalScore) if externalScore else None
    )
    
    upsertStageScoreSummary(runId, subIssueCode, "survey", finalSurveyScore, finalSurveyScore)

def upsertStageScoreSummary(runId: int, subIssueCode: str, stage: str, impactScore: Optional[float], financialScore: Optional[float]):
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
        save(sql, (runId, subIssueCode, impactScore, financialScore))
    except Exception as e:
        print(f"Error upserting stage summary for {subIssueCode}: {e}")

def safeFloat(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default

def recalculateFinalScore(runId: int, subIssueCode: str):
    sql = """
        SELECT 
            benchmark_impact_score, benchmark_financial_score,
            media_external_impact_score, media_external_financial_score,
            survey_impact_score, survey_financial_score
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ? AND sub_issue_code = ?
    """
    row = findOne(sql, (runId, subIssueCode))
    if not row:
        return
        
    finalScoreObj = calculateFinalMateriality(
        subIssueCode=subIssueCode,
        surveyImpact=row.get("survey_impact_score"), 
        surveyFinancial=row.get("survey_financial_score"),
        benchmarkImpact=row.get("benchmark_impact_score"), 
        benchmarkFinancial=row.get("benchmark_financial_score"),
        mediaImpact=row.get("media_external_impact_score"), 
        mediaFinancial=row.get("media_external_financial_score"),
        contextImpactModifier=0.0,
        contextFinancialModifier=0.0
    )
    
    upsertFinalScoreSummary(runId, finalScoreObj)
    updateDmaRankings(runId)

def updateDmaRankings(runId: int):
    sql = """
        SELECT id
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ? AND final_score IS NOT NULL
        ORDER BY final_score DESC
    """
    rows = findAll(sql, (runId,))
    if not rows:
        return
        
    updateSql = "UPDATE ESG_DMA_SCORE_SUMMARY SET rank_no = ? WHERE id = ?"
    params = [(idx + 1, row["id"]) for idx, row in enumerate(rows)]
    
    from src.utils.db import saveMany
    saveMany(updateSql, params)

def upsertFinalScoreSummary(runId: int, score: FinalMaterialityScore):
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
        runId, score.subIssueCode, 
        score.finalImpactScore, score.finalFinancialScore, score.finalScore
    )
    try:
        save(sql, params)
    except Exception as e:
        print(f"Error upserting final DMA Summary {score.subIssueCode}: {e}")
