"""
PG Benchmark Service — PostgreSQL ai_sr 기반 벤치마킹 분석.

findSr() (Gemini PDF 경로) 대신 ai_sr 테이블에 이미 적재된 데이터를 사용합니다.

ai_sr 필드 매핑:
  type        → sourceType 레이블 (자회사 → own_sr 등)
  year        → 보고서 연도
  page        → 페이지 번호
  text        → 본문 텍스트 (evidenceSpan)
  mapped_issues (JSONB) → [{domain, subIssueId, subIssueName, issueGroupName}, ...]

반환값: (signals, rawResultList, sourceTitle)
  signals        → baseline factor 적용된 DMASignal 목록  →  scoreSignals → saveSignals
  rawResultList  → step0NormalizeBenchmarkFacts 입력용 raw dict 목록 (shadow trace)
  sourceTitle    → saveSignals sourceTitle 레이블
"""

import json
from typing import Optional

from src.models.dmaengine import DMASignal, ImpactFactor, FinancialFactor
from src.utils.pgdb import pgFindAll
from src.utils.subissuemaster import getSubIssueDisplayName, getScoringAllowedIros

_DEFAULT_CONFIDENCE: float = 0.9
_EVIDENCE_TEXT_LIMIT: int = 500

# recalcStage의 파일-비율 계산(leaderRatio/peerRatio/ownRatio)이 teSrFileId 기반이므로
# PG 모드 신호에는 sourceType별 가상 음수 ID를 부여해 비율이 0이 되지 않도록 한다.
_PG_VIRTUAL_FILE_ID: dict[str, int] = {
    "own_sr":    -1,
    "leader_sr": -2,
    "peer_sr":   -3,
}

# ai_sr.type 값 → DMA sourceType 정규화
_SR_TYPE_MAP: dict[str, str] = {
    "자회사": "own_sr",
    "자사": "own_sr",
    "Own": "own_sr",
    "own": "own_sr",
    "owner": "own_sr",
    "Leader": "leader_sr",
    "leader": "leader_sr",
    "리더": "leader_sr",
    "Peer": "peer_sr",
    "peer": "peer_sr",
    "피어": "peer_sr",
}


def _normalizeSrType(raw: str | None) -> str:
    if not raw:
        return "own_sr"
    return _SR_TYPE_MAP.get(raw.strip(), raw.strip())


def _resolveBaselineFactors(
    subIssueCode: str,
) -> tuple[ImpactFactor | None, FinancialFactor | None]:
    """
    subissuemaster scoring_axis_allowed 기반 최소 baseline factor 생성.
    AI 추출 값이 없으므로 scale/likelihood 등은 중간값(3)으로 고정.
    """
    allowed = getScoringAllowedIros(subIssueCode)

    impact_dir: str | None = None
    fin_type: str | None = None

    if "negative_impact" in allowed:
        impact_dir = "negative"
    elif "positive_impact" in allowed:
        impact_dir = "positive"

    if "financial_risk" in allowed:
        fin_type = "risk"
    elif "financial_opportunity" in allowed:
        fin_type = "opportunity"

    impact = (
        ImpactFactor(
            impactDirection=impact_dir,
            actuality="potential",
            scale=3,
            scope=3,
            timeHorizon="mid",
        )
        if impact_dir
        else None
    )
    financial = (
        FinancialFactor(
            financialIroType=fin_type,
            timeHorizon="mid",
            likelihood=3,
        )
        if fin_type
        else None
    )
    return impact, financial


def fetchBenchmarkFromPg(
    srType: Optional[str] = None,
    srYear: Optional[str] = None,
) -> tuple[list[DMASignal], list[dict], str]:
    """
    ai_sr 테이블에서 pre-processed 벤치마킹 데이터를 조회합니다.

    Args:
        srType: ai_sr.type 필터 (예: "자회사", "Leader"). None이면 전체.
        srYear: ai_sr.year 필터 (예: "2022"). None이면 전체.

    Returns:
        (signals, rawResultList, sourceTitle)
    """
    conditions = ["mapped_issues IS NOT NULL"]
    params: list = []

    if srType:
        conditions.append("type = %s")
        params.append(srType)
    if srYear:
        conditions.append("year = %s")
        params.append(srYear)

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT id, type, year, page, text, mapped_issues
        FROM ai_sr
        WHERE {where_clause}
        ORDER BY id
    """
    rows = pgFindAll(sql, params if params else None)

    type_label: str = srType or "benchmark"
    year_label: str = srYear or ""
    source_title: str = f"{type_label} {year_label}".strip()
    source_type: str = _normalizeSrType(srType)

    signals: list[DMASignal] = []
    raw_results: list[dict] = []

    for row in rows:
        raw_issues = row.get("mapped_issues")
        if not raw_issues:
            continue

        # psycopg3 JSONB → 이미 list/dict; str 타입이면 파싱
        if isinstance(raw_issues, str):
            try:
                issues: list = json.loads(raw_issues)
            except Exception:
                continue
        else:
            issues = raw_issues

        page_text: str = (row.get("text") or "")[:_EVIDENCE_TEXT_LIMIT]
        page_no = row.get("page")
        page_no_int: int | None = int(page_no) if page_no is not None else None

        for issue in (issues or []):
            sub_id: str | None = issue.get("subIssueId")
            if not sub_id:
                continue

            sub_name: str = (
                issue.get("subIssueName") or getSubIssueDisplayName(sub_id) or sub_id
            )
            impact_f, financial_f = _resolveBaselineFactors(sub_id)

            # shadow trace용 raw dict
            raw_results.append({
                "subIssueCode": sub_id,
                "rawIssueLabel": sub_name,
                "classificationConfidence": _DEFAULT_CONFIDENCE,
                "sourceType": source_type,
                "evidenceSpans": [
                    {
                        "textSpan": page_text,
                        "sourceType": source_type,
                        "sourceTitle": source_title,
                        "sourcePageNo": page_no_int,
                    }
                ],
            })

            # 스코어링용 DMASignal
            signals.append(
                DMASignal(
                    subIssueCode=sub_id,
                    sourceStep="benchmark",
                    sourceType=source_type,
                    confidenceScore=_DEFAULT_CONFIDENCE,
                    similarityScore=_DEFAULT_CONFIDENCE,
                    mappingWeight=_DEFAULT_CONFIDENCE,
                    displaySubIssueName=sub_name,
                    rawIssueLabel=sub_name,
                    evidenceSpans=[page_text] if page_text else [],
                    sourceTitle=source_title,
                    impactFactor=impact_f,
                    financialFactor=financial_f,
                    teSrFileId=_PG_VIRTUAL_FILE_ID.get(source_type),
                    scoringPayloadJson={
                        "pgSourceType": srType,
                        "pgYear": srYear,
                        "pageNo": page_no_int,
                    },
                )
            )

    print(
        f"[pg_benchmark] ai_sr 조회: {len(rows)}페이지 → {len(signals)}건 signals "
        f"(type={srType!r}, year={srYear!r})"
    )
    return signals, raw_results, source_title
