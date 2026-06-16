"""
PG Pipeline — PostgreSQL esg_chunks 기반 미디어 분석 파이프라인.

processMediaPipeline() 과 동일한 출력 형식을 반환합니다.
크롤링·임베딩·SentenceTransformer 없이 PostgreSQL에 이미 적재된 데이터를 사용합니다.

필드 매핑:
  esg_chunks.best_sub_issue_id  → bestSubIssueId  (없으면 sub_issue_id 사용)
  esg_chunks.sub_issue_name     → bestSubIssueNameKr
  esg_chunks.best_similarity_score → bestSimilarityScore  (null → DEFAULT 0.5)
  esg_chunks.source             → source
  esg_chunks.title              → title
  esg_chunks.chunk              → chunk
  esg_chunks.created_at         → publishedAt
"""

from src.utils.pgdb import pgFindAll
from src.utils.subissuemaster import getSubIssueDisplayName

_DEFAULT_SIMILARITY: float = 0.5


def fetchMediaChunksFromPg() -> list[dict]:
    """
    esg_chunks 테이블에서 pre-processed 미디어 데이터를 조회해
    processMediaPipeline() 출력과 동일한 형식으로 변환·반환합니다.

    - best_sub_issue_id 우선, null이면 sub_issue_id 사용
    - best_similarity_score null → 0.5 기본값
    - 두 컬럼 모두 null인 행은 건너뜀
    """
    sql = """
        SELECT
            source,
            title,
            chunk,
            sub_issue_id,
            sub_issue_name,
            best_sub_issue_id,
            best_similarity_score,
            created_at
        FROM esg_chunks
        WHERE best_sub_issue_id IS NOT NULL
           OR sub_issue_id IS NOT NULL
        ORDER BY id
    """
    rows = pgFindAll(sql)
    results: list[dict] = []

    for row in rows:
        sub_id: str | None = row.get("best_sub_issue_id") or row.get("sub_issue_id")
        if not sub_id:
            continue

        raw_score = row.get("best_similarity_score")
        sim_score: float = float(raw_score) if raw_score is not None else _DEFAULT_SIMILARITY

        sub_name: str = row.get("sub_issue_name") or getSubIssueDisplayName(sub_id) or sub_id

        created_at = row.get("created_at")
        published_at: str = (
            created_at.isoformat()
            if hasattr(created_at, "isoformat")
            else str(created_at or "")
        )

        results.append({
            "source": row.get("source") or "news",
            "title": row.get("title") or "",
            "url": "",
            "publishedAt": published_at,
            "chunk": row.get("chunk") or "",
            "bestSubIssueId": sub_id,
            "bestSubIssueNameKr": sub_name,
            "bestSimilarityScore": sim_score,
            "issueSimilarityMatches": [
                {
                    "issueId": sub_id,
                    "subIssueNameKr": sub_name,
                    "score": sim_score,
                }
            ],
        })

    print(f"[pg_pipeline] esg_chunks 조회 완료: {len(results)}건")
    return results
