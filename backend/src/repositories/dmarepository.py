"""
dmarepository.py
레이어: Repository
역할: DMA 중요성 분석 신호·점수·순위 저장 및 집계.
"""

import copy
import json
from typing import List, Dict, Any, Optional, Sequence, Union, Literal
from collections import defaultdict
from datetime import datetime
from src.utils.db import save, addKey, findAll, findOne, getConn
from src.utils.typeutils import safeFloat as _safeFloatBase
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
from src.utils.subissuemaster import subissueMaster

# DMA 신호 목록 저장 — 증거·신호 INSERT 후 변경 서브이슈 Stage 집계 트리거
def saveSignals(runId: int, signals: List[DMASignal], fileId: Optional[int] = None, sourceTitle: str = ""):
    if not signals:
        return

    updatedSubIssues = set()
    conn = getConn()
    if not conn:
        print("saveSignals: MariaDB 연결 실패")
        return

    try:
        conn.autocommit = True
        with conn.cursor(dictionary=True) as cur:
            for sig in signals:
                evidenceText = " ".join(sig.evidenceSpans) if sig.evidenceSpans else ""
                currentSourceTitle = sig.sourceTitle if getattr(sig, "sourceTitle", None) else sourceTitle
                currentSourceUrl = sig.sourceUrl if getattr(sig, "sourceUrl", None) else None
                currentPublishedAt = normalizePublishedAt(
                    sig.publishedAt if getattr(sig, "publishedAt", None) else None
                )

                # 1. ESG_DMA_EVIDENCE INSERT (같은 연결에서 LAST_INSERT_ID 사용)
                evidenceId = None
                try:
                    cur.execute("""
                        INSERT INTO ESG_DMA_EVIDENCE (
                            esg_materiality_run_id, source_step, source_type,
                            source_title, source_url, source_published_at, te_sr_file_id, text_span
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (runId, sig.sourceStep, sig.sourceType, currentSourceTitle,
                          currentSourceUrl, currentPublishedAt, fileId, evidenceText))
                    cur.execute("SELECT LAST_INSERT_ID() as id")
                    data = cur.fetchone()
                    if data:
                        evidenceId = data["id"]
                        sig.evidenceId = str(evidenceId)
                except Exception as e:
                    errorMessage = str(e)
                    if "source_url" in errorMessage or "source_published_at" in errorMessage:
                        print("Warning: ESG_DMA_EVIDENCE source_url/source_published_at columns missing. Using fallback.")
                        try:
                            cur.execute("""
                                INSERT INTO ESG_DMA_EVIDENCE (
                                    esg_materiality_run_id, source_step, source_type,
                                    source_title, te_sr_file_id, text_span
                                ) VALUES (?, ?, ?, ?, ?, ?)
                            """, (runId, sig.sourceStep, sig.sourceType,
                                  currentSourceTitle, fileId, evidenceText))
                            cur.execute("SELECT LAST_INSERT_ID() as id")
                            data = cur.fetchone()
                            if data:
                                evidenceId = data["id"]
                                sig.evidenceId = str(evidenceId)
                        except Exception as fallbackErr:
                            print(f"Error saving evidence (fallback): {fallbackErr}")
                    else:
                        print(f"Error saving evidence: {e}")

                # 2. ESG_DMA_SIGNAL_DETAIL INSERT
                payload = sig.model_dump(by_alias=False)
                payloadJson = json.dumps(payload, ensure_ascii=False)
                impactScore = sig.impactScore05 if sig.impactScore05 is not None else None
                financialScore = sig.financialScore05 if sig.financialScore05 is not None else None

                try:
                    cur.execute("""
                        INSERT INTO ESG_DMA_SIGNAL_DETAIL (
                            esg_materiality_run_id, evidence_id, raw_issue_label, sub_issue_code,
                            source_step, source_type, impact_score, financial_score,
                            confidence_score, scoring_payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (runId, evidenceId, sig.rawIssueLabel, sig.subIssueCode,
                          sig.sourceStep, sig.sourceType, impactScore, financialScore,
                          sig.confidenceScore, payloadJson))
                    updatedSubIssues.add((sig.subIssueCode, sig.sourceStep))
                except Exception as e:
                    raise Exception(f"Failed to save signal: {e}")
    finally:
        conn.close()

    # 3. 변경된 subIssueCode 단위로 Stage Aggregation 수행
    for subIssueCode, sourceStep in updatedSubIssues:
        recalcStage(runId, subIssueCode, sourceStep)

# 발행일 문자열 정규화 — 다양한 날짜 형식을 YYYY-MM-DD HH:MM:SS로 변환
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

# DMA 증거 행 INSERT — source_url 컬럼 없으면 레거시 폴백
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

    conn = getConn()
    if not conn:
        raise RuntimeError("insertEvidence: MariaDB 연결 실패")
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(evidenceSql, evidenceParams)
            cur.execute("SELECT LAST_INSERT_ID() as id")
            data = cur.fetchone()
        conn.commit()
        return [True, data["id"] if data else 0]
    except Exception as e:
        conn.rollback()
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
    finally:
        conn.close()

# runId·이슈·스테이지 기준 신호 상세 행 조회 및 DMASignal 목록 반환
def listSignals(runId: int, subIssueCode: str, sourceStep: str) -> List[DMASignal]:
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

# 스테이지 점수 재계산 후 UPSERT — Final Score 트리거
def recalcStage(runId: int, subIssueCode: str, sourceStep: str):
    signals = listSignals(runId, subIssueCode, sourceStep)
    
    if not signals:
        return
        
    impactScore = None
    financialScore = None
    
    if sourceStep == "benchmark":
        leaderFiles = set(s.teSrFileId for s in signals if s.sourceType == "leader_sr" and s.teSrFileId is not None)
        peerFiles = set(s.teSrFileId for s in signals if s.sourceType == "peer_sr" and s.teSrFileId is not None)
        ownFiles = set(s.teSrFileId for s in signals if s.sourceType == "own_sr" and s.teSrFileId is not None)

        allFileIds = leaderFiles | peerFiles | ownFiles
        if allFileIds:
            # 업로드 모드: 이 런의 evidence에 연결된 파일 중 delete_yn=0인 것만 집계
            from src.utils.settings import settings
            placeholders = ",".join("?" * len(allFileIds))
            totalSql = f"""
                SELECT aes_d(type, '{settings.maria_db_key}') as raw_source_type
                FROM TE_SR_FILE
                WHERE id IN ({placeholders}) AND delete_yn = 0
            """
            rows = findAll(totalSql, tuple(allFileIds))
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
        else:
            # PG 모드: te_sr_file_id 없음 — source_type 별 시그널 존재 여부로 커버리지 판단
            leaderSigs = [s for s in signals if s.sourceType == "leader_sr"]
            peerSigs = [s for s in signals if s.sourceType == "peer_sr"]
            ownSigs = [s for s in signals if s.sourceType == "own_sr"]
            leaderRatio = 1.0 if leaderSigs else 0.0
            peerRatio = 1.0 if peerSigs else 0.0
            ownRatio = 1.0 if ownSigs else 0.0
        
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

# 스테이지별 점수 UPSERT — benchmark/media_external/survey 분기 처리
def upsertStage(runId: int, subIssueCode: str, stage: str, impactScore: Optional[float], financialScore: Optional[float]):
    if stage == "benchmark":
        sql = """
            INSERT INTO ESG_DMA_SCORE_SUMMARY (esg_materiality_run_id, sub_issue_code, benchmark_impact_score, benchmark_financial_score, delete_yn)
            VALUES (?, ?, ?, ?, 0)
            ON DUPLICATE KEY UPDATE
            benchmark_impact_score = VALUES(benchmark_impact_score),
            benchmark_financial_score = VALUES(benchmark_financial_score),
            delete_yn = 0
        """
    elif stage == "media_external":
        sql = """
            INSERT INTO ESG_DMA_SCORE_SUMMARY (esg_materiality_run_id, sub_issue_code, media_external_impact_score, media_external_financial_score, delete_yn)
            VALUES (?, ?, ?, ?, 0)
            ON DUPLICATE KEY UPDATE
            media_external_impact_score = VALUES(media_external_impact_score),
            media_external_financial_score = VALUES(media_external_financial_score),
            delete_yn = 0
        """
    elif stage == "survey":
        sql = """
            INSERT INTO ESG_DMA_SCORE_SUMMARY (esg_materiality_run_id, sub_issue_code, survey_impact_score, survey_financial_score, delete_yn)
            VALUES (?, ?, ?, ?, 0)
            ON DUPLICATE KEY UPDATE
            survey_impact_score = VALUES(survey_impact_score),
            survey_financial_score = VALUES(survey_financial_score),
            delete_yn = 0
        """
    else:
        return

    try:
        save(sql, (runId, subIssueCode, impactScore, financialScore))
    except Exception as e:
        print(f"Error upserting stage summary for {subIssueCode}: {e}")

# _safeFloatBase 래퍼 — 기본값 0.0
def safeFloat(value, default=0.0):
    return _safeFloatBase(value, default=default)

# _safeFloatBase 래퍼 — 기본값 None
def safeFloatOrNone(value):
    return _safeFloatBase(value, default=None)

# 최종 점수 재계산 및 UPSERT — 옵션으로 순위도 업데이트
def recalcFinal(runId: int, subIssueCode: str, updateRankingsYn: bool = True):
    sql = """
        SELECT
            benchmark_impact_score, benchmark_financial_score,
            media_external_impact_score, media_external_financial_score,
            survey_impact_score, survey_financial_score,
            context_impact_modifier, context_financial_modifier
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ? AND sub_issue_code = ? AND delete_yn = 0
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

# 컨텍스트 수정자 -0.5~0.5 범위 클램프
def clampContextModifier(value):
    parsed = safeFloat(value, 0.0)
    if parsed < -0.5:
        return -0.5
    if parsed > 0.5:
        return 0.5
    return parsed

# final_score 내림차순으로 전체 서브이슈 순위 재부여
def updateRanks(runId: int):
    sql = """
        SELECT id
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ? AND final_score IS NOT NULL AND delete_yn = 0
        ORDER BY final_score DESC
    """
    rows = findAll(sql, (runId,))
    if not rows:
        return
        
    updateSql = "UPDATE ESG_DMA_SCORE_SUMMARY SET rank_no = ? WHERE id = ?"
    params = [(idx + 1, row["id"]) for idx, row in enumerate(rows)]
    
    from src.utils.db import saveMany
    saveMany(updateSql, params)

# 최종 점수 점수요약 테이블 UPSERT
def upsertFinal(runId: int, score: FinalMaterialityScore):
    sql = """
        INSERT INTO ESG_DMA_SCORE_SUMMARY (
            esg_materiality_run_id, sub_issue_code,
            final_impact_score, final_financial_score, final_score, delete_yn
        )
        VALUES (?, ?, ?, ?, ?, 0)
        ON DUPLICATE KEY UPDATE
        final_impact_score = VALUES(final_impact_score),
        final_financial_score = VALUES(final_financial_score),
        final_score = VALUES(final_score),
        delete_yn = 0
    """
    params = (
        runId, score.subIssueCode, 
        score.finalImpactScore, score.finalFinancialScore, score.finalScore
    )
    try:
        save(sql, params)
    except Exception as e:
        print(f"Error upserting final DMA Summary {score.subIssueCode}: {e}")

# runId 기준 전체 점수 요약 행 조회 — 순위 있는 행 우선 rank_no ASC 정렬
def listResults(runId: int) -> list:
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
        WHERE esg_materiality_run_id = ? AND delete_yn = 0
        ORDER BY
            CASE WHEN rank_no IS NULL THEN 1 ELSE 0 END,
            rank_no ASC
    """
    rows = findAll(sql, (runId,))
    return rows if rows else []

# media_external 평균 점수 기준 상위 이슈 목록 조회 — limit 지원
def listTopMediaIssues(runId: int, limit: int = 5) -> list:
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
          AND delete_yn = 0
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
        WHERE esg_materiality_run_id = ? AND delete_yn = 0
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
          AND delete_yn = 0
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


def listFinalTopSubIssues(runId: int, limit: int = 5) -> list:
    sql = """
        SELECT
            sub_issue_code,
            rank_no,
            final_score,
            final_impact_score,
            final_financial_score
        FROM ESG_DMA_SCORE_SUMMARY
        WHERE esg_materiality_run_id = ?
          AND final_score IS NOT NULL
        ORDER BY
            CASE WHEN rank_no IS NULL THEN 1 ELSE 0 END,
            rank_no ASC,
            final_score DESC,
            sub_issue_code ASC
        LIMIT ?
    """
    return findAll(sql, (runId, limit)) or []


def replaceSelectedSubIssuesTx(runId: int, selectedRows: list, userId=None) -> None:
    """
    Hard DELETE + INSERT for ESG_MATERIALITY_SELECTED_SUB_ISSUE.
    Cannot use soft delete: unique key (esg_materiality_run_id, sub_issue_code) does not
    include delete_yn, so soft-deleting then re-inserting the same sub_issue_code would
    cause a duplicate key error.
    """
    conn = getConn()
    if conn is None:
        raise RuntimeError("DB connection is not available for finalize transaction")
    try:
        conn.autocommit = False
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "DELETE FROM ESG_MATERIALITY_SELECTED_SUB_ISSUE WHERE esg_materiality_run_id = ?",
                (runId,),
            )
            insertSql = """
                INSERT INTO ESG_MATERIALITY_SELECTED_SUB_ISSUE (
                    esg_materiality_run_id,
                    sub_issue_code,
                    selected_rank_no,
                    selection_type,
                    selection_reason,
                    selected_by_user_id,
                    selected_at,
                    delete_yn
                ) VALUES (?, ?, ?, ?, ?, ?, NOW(), 0)
            """
            for row in selectedRows:
                cur.execute(insertSql, (
                    runId,
                    row["sub_issue_code"],
                    row["selected_rank_no"],
                    row.get("selection_type", "rank_based"),
                    row.get("selection_reason", "최종 DMA 점수 기준 Top 5 자동 선정"),
                    userId,
                ))
        conn.commit()
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        if hasattr(conn, "close"):
            conn.close()


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
            e.source_type,
            COUNT(*) AS evidence_count,
            COUNT(DISTINCT CASE WHEN (f.id IS NULL OR f.delete_yn = 0) THEN e.te_sr_file_id END) AS report_count
        FROM ESG_DMA_EVIDENCE e
        LEFT JOIN skm.TE_SR_FILE f ON f.id = e.te_sr_file_id
        WHERE e.esg_materiality_run_id = ?
          AND e.source_step = ?
          AND e.delete_yn = 0
        GROUP BY e.source_type
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
            COUNT(DISTINCT source_response_key) AS response_count,
            COUNT(DISTINCT source_response_key) AS unique_respondent_count
        FROM ESG_DMA_SURVEY_RESPONSE
        WHERE esg_materiality_run_id = ?
          AND delete_yn = 0
          AND source_response_key IS NOT NULL
        GROUP BY respondent_group
    """
    return findAll(sql, (runId,)) or []

def listSurveyScores(runId: int) -> list:
    sql = """
        SELECT
            sub_issue_code,
            respondent_group,
            mapped_axis,
            AVG(normalized_score) AS avg_score,
            COUNT(*) AS response_count
        FROM ESG_DMA_SURVEY_RESPONSE
        WHERE esg_materiality_run_id = ?
          AND sub_issue_code IS NOT NULL
          AND mapped_axis IN ('impact', 'financial')
          AND normalized_score IS NOT NULL
          AND delete_yn = 0
        GROUP BY sub_issue_code, respondent_group, mapped_axis
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



# ── Shadow trace 함수·상수 re-export (dmatracerepository로 분리됨) ──
from src.repositories.dmatracerepository import (
    BENCHMARK_V13_SHADOW_SOURCE_STEP,
    BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP,
    MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP,
    isLegacyPayload,
    step4BuildTrace,
    step4WriteTrace,
    step4ReadTrace,
    step4UpdateTrace,
    appendFactorTrace,
    listBenchmarkShadowObservationRows,
    step4ReplaceBenchmarkShadowTracesTx,
    step4ReplaceMediaNewsShadowTracesTx,
    step4ReplaceMediaNewsShadowBundleTx,
    findRegulationRunContext,
    listApprovedRegulationInputs,
    listApprovedActiveRegulationMappings,
    step4ReplaceRegulationShadowTracesTx,
    listApprovedKcgsGradeInputs,
    step4ReplaceKcgsShadowTracesTx,
    listExternalMaxEligibleMediaRows,
    step4ReplaceMediaExternalMaxShadowAndSummaryTx,
    resetBenchmarkData,
    resetMediaData,
    countTop20RankedSubIssues,
    saveKcgsGradeInputRows,
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
    # STEP 4: v1.3 Payload Trace (re-exported from dmatracerepository)
    "BENCHMARK_V13_SHADOW_SOURCE_STEP",
    "BENCHMARK_V13_SCREENING_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_NEWS_V13_CANONICAL_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_REGULATION_V13_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_AGENCY_KCGS_V13_SHADOW_SOURCE_STEP",
    "MEDIA_EXTERNAL_V13_EXTERNAL_MAX_SHADOW_SOURCE_STEP",
    "isLegacyPayload",
    "step4BuildTrace",
    "step4WriteTrace",
    "step4ReadTrace",
    "step4UpdateTrace",
    "appendFactorTrace",
    "listBenchmarkShadowObservationRows",
    "step4ReplaceBenchmarkShadowTracesTx",
    "step4ReplaceMediaNewsShadowTracesTx",
    "step4ReplaceMediaNewsShadowBundleTx",
    "findRegulationRunContext",
    "listApprovedRegulationInputs",
    "listApprovedActiveRegulationMappings",
    "step4ReplaceRegulationShadowTracesTx",
    "listApprovedKcgsGradeInputs",
    "step4ReplaceKcgsShadowTracesTx",
    "listExternalMaxEligibleMediaRows",
    "step4ReplaceMediaExternalMaxShadowAndSummaryTx",
    "resetBenchmarkData",
    "resetMediaData",
    "countTop20RankedSubIssues",
    "saveKcgsGradeInputRows",
]