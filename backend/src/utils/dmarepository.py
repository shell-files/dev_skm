"""
Domain: DMA Materiality
Layer: utils/repository
Responsibility:
- Persist DMA evidence and signal rows
- Recalculate stage/final score summaries
- Update DMA rankings
- Query persisted DMA scoring state
Public functions:
- saveSignals / saveDmaSignals
- recalcStage / recalculateStageScore
- recalcFinal / recalculateFinalScore
- updateRanks / updateDmaRankings
- listResults / getDmaResults
- listTopMediaIssues / getTopIssuesByMediaScore
- getMediaCoverage / getMediaCoverageFromSummary
- query/count helpers for materiality result APIs
Do not:
- do not mutate unrelated DB state
- do not change scoring formula unless explicitly requested
- do not change scoring formula directly
- do not change aggregation weights directly
- do not call FastAPI router directly
- do not modify auth/token/common code
"""

import copy
import json
from typing import List, Dict, Any, Optional, Sequence, Union
from collections import defaultdict
from datetime import datetime
from src.utils.db import save, addKey, findAll, findOne, getConn
from src.models.dmaengine import (
    DMASignal,
    FinalMaterialityScore,
    FactorTraceV13,
    LegacyCompatibilityV13,
    ScoringPayloadV13,
    ScorePurposeV13,
)
from src.utils.dmaaggregator import (
    aggregateMedia,
    aggregateBenchmark,
    calcFinal,
)

def saveSignals(runId: int, signals: List[DMASignal], fileId: Optional[int] = None, sourceTitle: str = ""):
    """
    DMASignal 목록을 ESG_DMA_SIGNAL_DETAIL 테이블에 저장합니다.
    scoring_payload_json을 사용하여 상세 정보를 보존하고, ESG_DMA_EVIDENCE와 함께 저장합니다.
    저장 후 연관된 sub_issue_code에 대한 Stage Aggregation을 유발합니다.
    """
    updatedSubIssues = set()
    
    for sig in signals:
        # 1. ESG_DMA_EVIDENCE 저장 (addKey 사용)
        evidenceText = " ".join(sig.evidenceSpans) if sig.evidenceSpans else ""
        currentSourceTitle = sig.sourceTitle if getattr(sig, "sourceTitle", None) else sourceTitle
        currentSourceUrl = sig.sourceUrl if getattr(sig, "sourceUrl", None) else None
        currentPublishedAt = normalizePublishedAt(
            sig.publishedAt if getattr(sig, "publishedAt", None) else None
        )
        
        evidenceId = None
        try:
            res = insertEvidence(
                runId=runId,
                sourceStep=sig.sourceStep,
                sourceType=sig.sourceType,
                sourceTitle=currentSourceTitle,
                sourceUrl=currentSourceUrl,
                sourcePublishedAt=currentPublishedAt,
                fileId=fileId,
                evidenceText=evidenceText,
            )
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
        recalcStage(runId, subIssueCode, sourceStep)

def normalizePublishedAt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d", "%Y.%m.%d %H:%M"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None

def insertEvidence(
    runId: int,
    sourceStep: str,
    sourceType: str,
    sourceTitle: Optional[str],
    sourceUrl: Optional[str],
    sourcePublishedAt: Optional[str],
    fileId: Optional[int],
    evidenceText: str,
):
    evidenceSql = """
        INSERT INTO ESG_DMA_EVIDENCE (
            esg_materiality_run_id, source_step, source_type,
            source_title, source_url, source_published_at, te_sr_file_id, text_span
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    evidenceParams = (
        runId,
        sourceStep,
        sourceType,
        sourceTitle,
        sourceUrl,
        sourcePublishedAt,
        fileId,
        evidenceText,
    )

    try:
        with getConn() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(evidenceSql, evidenceParams)
                cur.execute("SELECT LAST_INSERT_ID() as id")
                data = cur.fetchone()
                conn.commit()
                return [True, data["id"] if data else 0]
    except Exception as e:
        errorMessage = str(e)
        if "source_url" not in errorMessage and "source_published_at" not in errorMessage:
            raise

        fallbackSql = """
            INSERT INTO ESG_DMA_EVIDENCE (
                esg_materiality_run_id, source_step, source_type,
                source_title, te_sr_file_id, text_span
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        fallbackParams = (
            runId,
            sourceStep,
            sourceType,
            sourceTitle,
            fileId,
            evidenceText,
        )
        print("Warning: ESG_DMA_EVIDENCE source_url/source_published_at columns are missing. Falling back to legacy evidence insert.")
        return addKey(fallbackSql, fallbackParams)

def listSignals(runId: int, subIssueCode: str, sourceStep: str) -> List[DMASignal]:
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

def recalcStage(runId: int, subIssueCode: str, sourceStep: str):
    """
    DB에 저장된 Signal들을 기반으로 Stage Score를 다시 계산하고 UPSERT합니다.
    그 후 Final Score 산출을 트리거합니다.
    """
    signals = listSignals(runId, subIssueCode, sourceStep)
    
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
        
        stageScore = aggregateBenchmark(
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
        stageScore = aggregateMedia(signals)
        impactScore = stageScore.impactScore05
        financialScore = stageScore.financialScore05
        
    if sourceStep in ["benchmark", "media_external"]:
        upsertStage(runId, subIssueCode, sourceStep, impactScore, financialScore)
        
    elif sourceStep == "survey":
        recalcSurvey(runId, subIssueCode)
        
    recalcFinal(runId, subIssueCode)

def recalcSurvey(runId: int, subIssueCode: str):
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
    
    from src.utils.dmaaggregator import aggregateSurvey
    finalSurveyScore = aggregateSurvey(
        employeeScore=float(employeeScore) if employeeScore else None,
        executiveScore=float(executiveScore) if executiveScore else None,
        externalScore=float(externalScore) if externalScore else None
    )
    
    upsertStage(runId, subIssueCode, "survey", finalSurveyScore, finalSurveyScore)

def upsertStage(runId: int, subIssueCode: str, stage: str, impactScore: Optional[float], financialScore: Optional[float]):
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

def safeFloatOrNone(value):
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None

def recalcFinal(runId: int, subIssueCode: str, updateRankingsYn: bool = True):
    sql = """
        SELECT 
            benchmark_impact_score, benchmark_financial_score,
            media_external_impact_score, media_external_financial_score,
            survey_impact_score, survey_financial_score,
            context_impact_modifier, context_financial_modifier
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ? AND sub_issue_code = ?
    """
    row = findOne(sql, (runId, subIssueCode))
    if not row:
        return
        
    finalScoreObj = calcFinal(
        subIssueCode=subIssueCode,
        surveyImpact=safeFloatOrNone(row.get("survey_impact_score")),
        surveyFinancial=safeFloatOrNone(row.get("survey_financial_score")),
        benchmarkImpact=safeFloatOrNone(row.get("benchmark_impact_score")),
        benchmarkFinancial=safeFloatOrNone(row.get("benchmark_financial_score")),
        mediaImpact=safeFloatOrNone(row.get("media_external_impact_score")),
        mediaFinancial=safeFloatOrNone(row.get("media_external_financial_score")),
        contextImpactModifier=clampContextModifier(row.get("context_impact_modifier")),
        contextFinancialModifier=clampContextModifier(row.get("context_financial_modifier"))
    )
    
    upsertFinal(runId, finalScoreObj)
    if updateRankingsYn:
        updateRanks(runId)

def clampContextModifier(value):
    parsed = safeFloat(value, 0.0)
    if parsed < -0.5:
        return -0.5
    if parsed > 0.5:
        return 0.5
    return parsed

def updateRanks(runId: int):
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

def upsertFinal(runId: int, score: FinalMaterialityScore):
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

# ──────────────────────────────────────────────
# Result API / Media API 조회 함수
# ──────────────────────────────────────────────

def listResults(runId: int) -> list:
    """
    통합 결과 조회 API용.
    ESG_DMA_SCORE_SUMMARY에서 runId 기준 전체 행을 rank_no ASC로 반환합니다.
    final_score가 NULL인 행도 포함하되, rank_no가 있는 행이 먼저 나옵니다.
    """
    sql = """
        SELECT 
            sub_issue_code,
            benchmark_impact_score,
            benchmark_financial_score,
            media_external_impact_score,
            media_external_financial_score,
            survey_impact_score,
            survey_financial_score,
            final_impact_score,
            final_financial_score,
            final_score,
            rank_no
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ?
        ORDER BY 
            CASE WHEN rank_no IS NULL THEN 1 ELSE 0 END,
            rank_no ASC
    """
    rows = findAll(sql, (runId,))
    return rows if rows else []

def listTopMediaIssues(runId: int, limit: int = 5) -> list:
    """
    Media API topIssues용.
    media_external stage score 기준으로 정렬합니다 (final_score 아님).
    media impact/financial 중 non-null 평균을 기준으로 내림차순 정렬.
    """
    sql = """
        SELECT 
            sub_issue_code,
            media_external_impact_score,
            media_external_financial_score,
            final_impact_score,
            final_financial_score,
            final_score,
            rank_no,
            (
                (COALESCE(media_external_impact_score, 0) + COALESCE(media_external_financial_score, 0))
                / CASE
                    WHEN media_external_impact_score IS NOT NULL AND media_external_financial_score IS NOT NULL THEN 2
                    WHEN media_external_impact_score IS NOT NULL OR media_external_financial_score IS NOT NULL THEN 1
                    ELSE 1
                  END
            ) AS media_avg_score
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ?
          AND (media_external_impact_score IS NOT NULL OR media_external_financial_score IS NOT NULL)
        ORDER BY media_avg_score DESC
        LIMIT ?
    """
    rows = findAll(sql, (runId, limit))
    return rows if rows else []

def getMediaCoverage(runId: int) -> dict:
    """
    Media API coverage용.
    해당 runId에서 각 stage별로 scored 이슈가 존재하는지 확인하여
    전체 coverage 상태를 반환합니다.
    """
    sql = """
        SELECT 
            SUM(CASE WHEN media_external_impact_score IS NOT NULL OR media_external_financial_score IS NOT NULL THEN 1 ELSE 0 END) AS media_count,
            SUM(CASE WHEN benchmark_impact_score IS NOT NULL OR benchmark_financial_score IS NOT NULL THEN 1 ELSE 0 END) AS benchmark_count,
            SUM(CASE WHEN survey_impact_score IS NOT NULL OR survey_financial_score IS NOT NULL THEN 1 ELSE 0 END) AS survey_count
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ?
    """
    row = findOne(sql, (runId,))
    if not row:
        return {"stageCount": 0, "coverageStatus": "NO_DATA"}
    
    from src.utils.dmaaggregator import getCoverageStatus
    stageCount = sum(1 for k in ["media_count", "benchmark_count", "survey_count"] 
                     if row.get(k) and int(row.get(k, 0)) > 0)
    return {
        "stageCount": stageCount,
        "coverageStatus": getCoverageStatus(stageCount),
        "mediaObserved": int(row.get("media_count", 0) or 0) > 0,
        "benchmarkObserved": int(row.get("benchmark_count", 0) or 0) > 0,
        "surveyObserved": int(row.get("survey_count", 0) or 0) > 0
    }

def countMediaSubIssues(runId: int) -> int:
    """
    ESG_DMA_SCORE_SUMMARY 기준 media_external score가 존재하는 전체 subIssue 수를 반환합니다.
    """
    sql = """
        SELECT COUNT(*) AS cnt
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ?
          AND (
            media_external_impact_score IS NOT NULL
            OR media_external_financial_score IS NOT NULL
          )
    """
    row = findOne(sql, (runId,))
    if row and "cnt" in row:
        return int(row["cnt"])
    elif row and list(row.values())[0] is not None:
        return int(list(row.values())[0])
    return 0

def getRunInfo(runId: int) -> dict:
    sql = """
        SELECT id, company_id, reporting_year, run_status
        FROM ESG_MATERIALITY_RUN
        WHERE id = ? AND delete_yn = 0
    """
    return findOne(sql, (runId,)) or {}

def listSelectedSubIssues(runId: int) -> list:
    sql = """
        SELECT
            sub_issue_code,
            selected_rank_no,
            selection_type,
            selection_reason
        FROM ESG_MATERIALITY_SELECTED_SUB_ISSUE
        WHERE esg_materiality_run_id = ? AND delete_yn = 0
        ORDER BY
            CASE WHEN selected_rank_no IS NULL THEN 1 ELSE 0 END,
            selected_rank_no ASC
    """
    return findAll(sql, (runId,)) or []

def listTopStageIssues(runId: int, stage: str, limit: int = 10) -> list:
    stageColumns = {
        "benchmark": ("benchmark_impact_score", "benchmark_financial_score"),
        "media_external": ("media_external_impact_score", "media_external_financial_score"),
        "survey": ("survey_impact_score", "survey_financial_score"),
    }
    if stage not in stageColumns:
        return []

    impactColumn, financialColumn = stageColumns[stage]
    sql = f"""
        SELECT
            sub_issue_code,
            {impactColumn} AS impact_score,
            {financialColumn} AS financial_score,
            rank_no,
            (
                (COALESCE({impactColumn}, 0) + COALESCE({financialColumn}, 0))
                / CASE
                    WHEN {impactColumn} IS NOT NULL AND {financialColumn} IS NOT NULL THEN 2
                    WHEN {impactColumn} IS NOT NULL OR {financialColumn} IS NOT NULL THEN 1
                    ELSE 1
                  END
            ) AS avg_score
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ?
          AND ({impactColumn} IS NOT NULL OR {financialColumn} IS NOT NULL)
        ORDER BY avg_score DESC
        LIMIT ?
    """
    return findAll(sql, (runId, limit)) or []

def listSignalCounts(runId: int, sourceStep: str) -> list:
    sql = """
        SELECT
            sub_issue_code,
            source_type,
            COUNT(*) AS signal_count,
            COUNT(DISTINCT evidence_id) AS evidence_count
        FROM ESG_DMA_SIGNAL_DETAIL
        WHERE esg_materiality_run_id = ?
          AND source_step = ?
          AND delete_yn = 0
        GROUP BY sub_issue_code, source_type
    """
    return findAll(sql, (runId, sourceStep)) or []

def countObservedSubIssues(runId: int, sourceStep: str) -> int:
    sql = """
        SELECT COUNT(DISTINCT sub_issue_code) AS cnt
        FROM ESG_DMA_SIGNAL_DETAIL
        WHERE esg_materiality_run_id = ?
          AND source_step = ?
          AND delete_yn = 0
    """
    row = findOne(sql, (runId, sourceStep)) or {}
    return int(row.get("cnt") or 0)

def listEvidenceCounts(runId: int, sourceStep: str) -> list:
    sql = """
        SELECT
            source_type,
            COUNT(*) AS evidence_count,
            COUNT(DISTINCT te_sr_file_id) AS report_count
        FROM ESG_DMA_EVIDENCE
        WHERE esg_materiality_run_id = ?
          AND source_step = ?
          AND delete_yn = 0
        GROUP BY source_type
    """
    return findAll(sql, (runId, sourceStep)) or []

def listEvidenceSamples(runId: int, sourceStep: str, limit: int = 10) -> list:
    sql = """
        SELECT
            id,
            source_step,
            source_type,
            source_title,
            source_url,
            source_published_at,
            te_sr_file_id,
            text_span,
            summary_text
        FROM ESG_DMA_EVIDENCE
        WHERE esg_materiality_run_id = ?
          AND source_step = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT ?
    """
    return findAll(sql, (runId, sourceStep, limit)) or []

def listSurveyCounts(runId: int) -> list:
    sql = """
        SELECT
            respondent_group,
            COUNT(*) AS response_count,
            COUNT(DISTINCT respondent_user_id) AS unique_respondent_count
        FROM ESG_DMA_SURVEY_RESPONSE
        WHERE esg_materiality_run_id = ?
          AND delete_yn = 0
        GROUP BY respondent_group
    """
    return findAll(sql, (runId,)) or []

def listSurveyScores(runId: int) -> list:
    sql = """
        SELECT
            sub_issue_code,
            respondent_group,
            AVG(normalized_score) AS avg_score,
            COUNT(*) AS response_count
        FROM ESG_DMA_SURVEY_RESPONSE
        WHERE esg_materiality_run_id = ?
          AND sub_issue_code IS NOT NULL
          AND delete_yn = 0
        GROUP BY sub_issue_code, respondent_group
    """
    return findAll(sql, (runId,)) or []

def countRequiredMetrics(subIssueCodes: list[str]) -> int:
    if not subIssueCodes:
        return 0
    placeholders = ",".join(["?"] * len(subIssueCodes))
    sql = f"""
        SELECT COUNT(DISTINCT atomic_metric_id) AS cnt
        FROM ESG_SUB_ISSUE_ATOMIC_MAP
        WHERE sub_issue_code IN ({placeholders})
          AND map_scope = 'MVP_SELECTED'
          AND required_yn = 1
          AND delete_yn = 0
    """
    row = findOne(sql, tuple(subIssueCodes)) or {}
    return int(row.get("cnt") or 0)

def countMissingMetrics(runId: int, subIssueCodes: list[str]) -> int:
    if not subIssueCodes:
        return 0

    runInfo = getRunInfo(runId)
    companyId = runInfo.get("company_id")
    reportingYear = runInfo.get("reporting_year")
    if companyId is None or reportingYear is None:
        return 0

    placeholders = ",".join(["?"] * len(subIssueCodes))
    sql = f"""
        SELECT COUNT(DISTINCT sam.atomic_metric_id) AS cnt
        FROM ESG_SUB_ISSUE_ATOMIC_MAP sam
        LEFT JOIN ESG_KPI_FACT kf
          ON kf.metric_id = sam.metric_id
         AND kf.atomic_metric_id = sam.atomic_metric_id
         AND kf.company_id = ?
         AND kf.reporting_year = ?
         AND LOWER(COALESCE(kf.approval_status, '')) = 'approved'
         AND kf.delete_yn = 0
        WHERE sam.sub_issue_code IN ({placeholders})
          AND sam.map_scope = 'MVP_SELECTED'
          AND sam.required_yn = 1
          AND sam.delete_yn = 0
          AND kf.id IS NULL
    """
    row = findOne(sql, tuple([companyId, reportingYear] + subIssueCodes)) or {}
    return int(row.get("cnt") or 0)

def getLatestReportRun(runId: int) -> dict:
    sql = """
        SELECT id, report_status, created_at
        FROM ESG_REPORT_RUN
        WHERE source_materiality_run_id = ?
          AND delete_yn = 0
        ORDER BY id DESC
        LIMIT 1
    """
    return findOne(sql, (runId,)) or {}


# Compatibility wrappers for pre-canonical public names.
def saveDmaSignals(runId: int, signals: List[DMASignal], fileId: Optional[int] = None, sourceTitle: str = ""):
    return saveSignals(runId, signals, fileId, sourceTitle)


def normalizeEvidencePublishedAt(value: Optional[str]) -> Optional[str]:
    return normalizePublishedAt(value)


def insertDmaEvidence(
    runId: int,
    sourceStep: str,
    sourceType: str,
    sourceTitle: Optional[str],
    sourceUrl: Optional[str],
    sourcePublishedAt: Optional[str],
    fileId: Optional[int],
    evidenceText: str,
):
    return insertEvidence(
        runId,
        sourceStep,
        sourceType,
        sourceTitle,
        sourceUrl,
        sourcePublishedAt,
        fileId,
        evidenceText,
    )


def getSignalsByGroup(runId: int, subIssueCode: str, sourceStep: str) -> List[DMASignal]:
    return listSignals(runId, subIssueCode, sourceStep)


def recalculateStageScore(runId: int, subIssueCode: str, sourceStep: str):
    return recalcStage(runId, subIssueCode, sourceStep)


def recalculateSurveyScore(runId: int, subIssueCode: str):
    return recalcSurvey(runId, subIssueCode)


def upsertStageScoreSummary(
    runId: int,
    subIssueCode: str,
    stage: str,
    impactScore: Optional[float],
    financialScore: Optional[float],
):
    return upsertStage(runId, subIssueCode, stage, impactScore, financialScore)


def recalculateFinalScore(runId: int, subIssueCode: str, updateRankingsYn: bool = True):
    return recalcFinal(runId, subIssueCode, updateRankingsYn)


def updateDmaRankings(runId: int):
    return updateRanks(runId)


def upsertFinalScoreSummary(runId: int, score: FinalMaterialityScore):
    return upsertFinal(runId, score)


def getDmaResults(runId: int) -> list:
    return listResults(runId)


def getTopIssuesByMediaScore(runId: int, limit: int = 5) -> list:
    return listTopMediaIssues(runId, limit)


def getMediaCoverageFromSummary(runId: int) -> dict:
    return getMediaCoverage(runId)


def getMediaObservedSubIssueCount(runId: int) -> int:
    return countMediaSubIssues(runId)


def getMaterialityRunInfo(runId: int) -> dict:
    return getRunInfo(runId)


def getSelectedSubIssues(runId: int) -> list:
    return listSelectedSubIssues(runId)


def getTopIssuesByStageScore(runId: int, stage: str, limit: int = 10) -> list:
    return listTopStageIssues(runId, stage, limit)


def getSignalObservationCounts(runId: int, sourceStep: str) -> list:
    return listSignalCounts(runId, sourceStep)


def getDistinctObservedSubIssueCount(runId: int, sourceStep: str) -> int:
    return countObservedSubIssues(runId, sourceStep)


def getEvidenceCountsBySource(runId: int, sourceStep: str) -> list:
    return listEvidenceCounts(runId, sourceStep)


def getEvidenceSamples(runId: int, sourceStep: str, limit: int = 10) -> list:
    return listEvidenceSamples(runId, sourceStep, limit)


def getSurveyGroupCounts(runId: int) -> list:
    return listSurveyCounts(runId)


def getSurveyGroupScores(runId: int) -> list:
    return listSurveyScores(runId)


def getRequiredMetricCountForSubIssues(subIssueCodes: list[str]) -> int:
    return countRequiredMetrics(subIssueCodes)


def getMissingRequiredMetricCount(runId: int, subIssueCodes: list[str]) -> int:
    return countMissingMetrics(runId, subIssueCodes)


def getLatestReportRunByMaterialityRun(runId: int) -> dict:
    return getLatestReportRun(runId)


# =====================================================================================
# DMA v1.3 MVP Slim — Payload Trace Helpers (PARALLEL ADDITION, NO DB EXECUTION)
# =====================================================================================
# These helpers BUILD / READ the v1.3 canonical payload that will (in Phase C) live in
# the EXISTING column ESG_DMA_SIGNAL_DETAIL.scoring_payload_json. No new table/column.
#
# Phase A guarantees enforced here:
#   - PURE builders: none of these functions execute SQL / open a DB connection.
#   - Legacy payloads are NEVER auto-migrated, their scores NEVER reused, NEVER updated.
#   - Reads are read-only; legacy payloads are detected, not rewritten.
# DB persistence of these payloads is intentionally deferred to Phase C.
# =====================================================================================

_V13_RULE_VERSION = "dma-rule-v1.3-mvp"


def _coerce_payload_dict(raw: Union[str, Dict[str, Any], None]) -> Optional[Dict[str, Any]]:
    """Parse a scoring_payload_json value (JSON str or dict) into a dict, or None."""
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None
    if isinstance(raw, dict):
        return raw
    return None


def is_legacy_scoring_payload(raw: Union[str, Dict[str, Any], None]) -> bool:
    """
    True if a scoring_payload_json value is NOT a v1.3 canonical payload.

    A v1.3 payload is identified by ``factorPayloadSchemaVersion`` present AND
    ``ruleVersion == 'dma-rule-v1.3-mvp'``. Anything else (legacy DMASignal dump,
    empty, unparseable) is treated as legacy.
    """
    payload = _coerce_payload_dict(raw)
    if not payload:
        return True
    has_schema = "factorPayloadSchemaVersion" in payload
    is_v13_rule = payload.get("ruleVersion") == _V13_RULE_VERSION
    return not (has_schema and is_v13_rule)


def build_scoring_payload_v13(
    *,
    score_purpose: Union[ScorePurposeV13, str] = ScorePurposeV13.CANONICAL_IRO,
    source_channel: Optional[str] = None,
    sub_issue_code: Optional[str] = None,
    extracted_facts: Any = None,
    factor_trace: Optional[Sequence[Any]] = None,
    axis_scores: Optional[Sequence[Any]] = None,
    screening_trace: Optional[Sequence[Any]] = None,
    aggregation_trace: Any = None,
    legacy_compatibility: Any = None,
    rule_version: Optional[str] = None,
    config_hash: Optional[str] = None,
    evaluated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a JSON-serializable v1.3 canonical payload dict (camelCase keys).

    rule_version / config_hash default to the loaded slim runtime config (Registry).
    Inputs may be pydantic models or plain dicts; pydantic validates them (and the
    ExtractedFactsV13 ``extra='forbid'`` guard still rejects any AI score field here).
    This does not touch a DB.
    """
    if rule_version is None or config_hash is None:
        # Lazy import to avoid any import cycle and to keep this a pure builder.
        from src.utils import dmaruleregistry
        if rule_version is None:
            rule_version = dmaruleregistry.get_rule_version()
        if config_hash is None:
            config_hash = dmaruleregistry.get_config_hash()

    payload = ScoringPayloadV13(
        ruleVersion=rule_version,
        configHash=config_hash,
        scorePurpose=score_purpose,
        sourceChannel=source_channel,
        subIssueCode=sub_issue_code,
        extractedFacts=extracted_facts,
        factorTrace=list(factor_trace) if factor_trace else [],
        axisScores=list(axis_scores) if axis_scores else [],
        screeningTrace=list(screening_trace) if screening_trace else [],
        aggregationTrace=aggregation_trace,
        legacyCompatibility=legacy_compatibility or LegacyCompatibilityV13(),
        evaluatedAt=evaluated_at,
    )
    return payload.model_dump(mode="json", by_alias=False)


def write_scoring_payload_v13(
    payload: Union[ScoringPayloadV13, Dict[str, Any]],
    *,
    as_json: bool = False,
) -> Union[Dict[str, Any], str]:
    """
    Produce the serialized v1.3 payload destined for ESG_DMA_SIGNAL_DETAIL.scoring_payload_json.

    Phase A: this returns the payload only — it does NOT execute any SQL or open a DB
    connection. Actual persistence is wired in Phase C. ``as_json=True`` returns a JSON
    string instead of a dict.
    """
    if isinstance(payload, ScoringPayloadV13):
        data = payload.model_dump(mode="json", by_alias=False)
    elif isinstance(payload, dict):
        # Validate/normalize through the model so we never persist a malformed payload.
        data = ScoringPayloadV13(**payload).model_dump(mode="json", by_alias=False)
    else:
        raise TypeError("payload must be a ScoringPayloadV13 or dict")
    if as_json:
        return json.dumps(data, ensure_ascii=False)
    return data


def read_scoring_payload_v13(raw: Union[str, Dict[str, Any], None]) -> Optional[Dict[str, Any]]:
    """
    Read-only parse of a scoring_payload_json value into a normalized v1.3 payload dict.

    Returns None if the value is legacy / missing / not a valid v1.3 payload. Never
    rewrites or migrates the source.
    """
    if is_legacy_scoring_payload(raw):
        return None
    payload = _coerce_payload_dict(raw)
    try:
        return ScoringPayloadV13(**payload).model_dump(mode="json", by_alias=False)
    except Exception:
        return None


def build_updated_factor_trace_payload_v13(
    existing_v13_payload: Union[str, Dict[str, Any]],
    new_factor_traces: Sequence[Any],
) -> Dict[str, Any]:
    """
    Append factor traces to an EXISTING v1.3 payload and return a NEW dict.

    Raises ValueError if the input is a legacy payload (legacy is never migrated here).
    The input is deep-copied; legacy/score fields are never created or reused.
    """
    if is_legacy_scoring_payload(existing_v13_payload):
        raise ValueError("Refusing to update factor trace on a legacy payload (no legacy migration)")
    payload = copy.deepcopy(_coerce_payload_dict(existing_v13_payload)) or {}
    traces = list(payload.get("factorTrace", []))
    for trace in new_factor_traces:
        if isinstance(trace, FactorTraceV13):
            traces.append(trace.model_dump(mode="json", by_alias=False))
        elif isinstance(trace, dict):
            traces.append(FactorTraceV13(**trace).model_dump(mode="json", by_alias=False))
        else:
            raise TypeError("new_factor_traces items must be FactorTraceV13 or dict")
    payload["factorTrace"] = traces
    return payload


def update_signal_factor_trace_v13(
    existing_raw_payload: Union[str, Dict[str, Any], None],
    new_factor_traces: Sequence[Any],
    *,
    score_purpose: Union[ScorePurposeV13, str] = ScorePurposeV13.CANONICAL_IRO,
    source_channel: Optional[str] = None,
    sub_issue_code: Optional[str] = None,
    rule_version: Optional[str] = None,
    config_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Produce the v1.3 payload that WOULD be written back for a signal's factor trace.

    - If the existing payload is already v1.3: append the new traces (no legacy touch).
    - If it is legacy / missing: build a FRESH v1.3 payload (legacy is NOT migrated and
      its score is NOT reused); legacyCompatibility records that a legacy payload existed.

    Phase A: PURE builder — returns the payload dict; performs NO DB write.
    """
    if not is_legacy_scoring_payload(existing_raw_payload):
        return build_updated_factor_trace_payload_v13(existing_raw_payload, new_factor_traces)

    legacy_present = _coerce_payload_dict(existing_raw_payload) is not None
    legacy_compat = LegacyCompatibilityV13(
        legacyScoringPayloadPresentYn=legacy_present,
        legacyMigratedYn=False,
        legacyScoreReusedYn=False,
        legacyUpdatedYn=False,
    )
    return build_scoring_payload_v13(
        score_purpose=score_purpose,
        source_channel=source_channel,
        sub_issue_code=sub_issue_code,
        factor_trace=list(new_factor_traces),
        legacy_compatibility=legacy_compat,
        rule_version=rule_version,
        config_hash=config_hash,
    )


__all__ = [
    "saveSignals",
    "saveDmaSignals",
    "normalizePublishedAt",
    "normalizeEvidencePublishedAt",
    "insertEvidence",
    "insertDmaEvidence",
    "listSignals",
    "getSignalsByGroup",
    "recalcStage",
    "recalculateStageScore",
    "recalcSurvey",
    "recalculateSurveyScore",
    "upsertStage",
    "upsertStageScoreSummary",
    "safeFloat",
    "safeFloatOrNone",
    "recalcFinal",
    "recalculateFinalScore",
    "clampContextModifier",
    "updateRanks",
    "updateDmaRankings",
    "upsertFinal",
    "upsertFinalScoreSummary",
    "listResults",
    "getDmaResults",
    "listTopMediaIssues",
    "getTopIssuesByMediaScore",
    "getMediaCoverage",
    "getMediaCoverageFromSummary",
    "countMediaSubIssues",
    "getMediaObservedSubIssueCount",
    "getRunInfo",
    "getMaterialityRunInfo",
    "listSelectedSubIssues",
    "getSelectedSubIssues",
    "listTopStageIssues",
    "getTopIssuesByStageScore",
    "listSignalCounts",
    "getSignalObservationCounts",
    "countObservedSubIssues",
    "getDistinctObservedSubIssueCount",
    "listEvidenceCounts",
    "getEvidenceCountsBySource",
    "listEvidenceSamples",
    "getEvidenceSamples",
    "listSurveyCounts",
    "getSurveyGroupCounts",
    "listSurveyScores",
    "getSurveyGroupScores",
    "countRequiredMetrics",
    "getRequiredMetricCountForSubIssues",
    "countMissingMetrics",
    "getMissingRequiredMetricCount",
    "getLatestReportRun",
    "getLatestReportRunByMaterialityRun",
    # v1.3 MVP slim payload trace helpers (no DB execution in Phase A)
    "is_legacy_scoring_payload",
    "build_scoring_payload_v13",
    "write_scoring_payload_v13",
    "read_scoring_payload_v13",
    "build_updated_factor_trace_payload_v13",
    "update_signal_factor_trace_v13",
]
