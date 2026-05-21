"""
05_pg_opportunity_risk.py
────────────────────────────────────────────────────────────────
PostgreSQL 임베딩 테이블 → 기회 / 리스크 스코어링
컬럼: chunk, issue_group, issue_group_domain, sub_issue_id,
      sub_issue_name, best_sub_issue_id, best_similarity_score,
      chunk_embedding, created_at

출력:
  - 전체 기회 점수 (0~1)
  - 전체 리스크 점수 (0~1)
  - sub_issue / issue_group 별 breakdown
  - 낮은 신뢰도 케이스 목록 (검토 필요)

사용법:
  1) cp .env.example .env  →  .env 에 DB 접속 정보 입력
  2) python 05_pg_opportunity_risk.py
  3) python 05_pg_opportunity_risk.py --limit 100   # 최근 100건만
  4) python 05_pg_opportunity_risk.py --group E_CLIMATE  # 특정 그룹
  5) python 05_pg_opportunity_risk.py --dry-run    # DB 없이 샘플로 테스트
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import os, sys, argparse
from collections import defaultdict
from dataclasses import dataclass
import sentiment_backend as sb

# ── 인자 ─────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--limit",    type=int,  default=None,  help="가져올 최대 행 수")
parser.add_argument("--group",    type=str,  default=None,  help="issue_group 필터")
parser.add_argument("--domain",   type=str,  default=None,  help="issue_group_domain 필터 (E/S/G)")
parser.add_argument("--conf",     type=float,default=0.65,  help="신뢰도 임계값 (default 0.65)")
parser.add_argument("--dry-run",  action="store_true",      help="DB 없이 내장 샘플로 테스트")
parser.add_argument("--detail",   action="store_true",      help="행별 상세 출력")
parser.add_argument("--export",   type=str,  default=None,  help="결과 CSV 저장 경로")
args = parser.parse_args()

# ── 출력 유틸 ─────────────────────────────────────────────────
RESET="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
RED="\033[91m"; GRN="\033[92m"; YLW="\033[93m"; BLU="\033[94m"; CYN="\033[96m"

def c(text, color): return f"{color}{text}{RESET}"
def bar(ratio, width=30, fill_c=GRN, empty_c=DIM):
    n = round(ratio * width)
    return f"{fill_c}{'█'*n}{RESET}{empty_c}{'░'*(width-n)}{RESET}"

# ── 결과 구조체 ───────────────────────────────────────────────
@dataclass
class ChunkResult:
    chunk_id:            int | str
    text:                str
    issue_group:         str
    issue_group_domain:  str
    sub_issue_id:        str
    sub_issue_name:      str
    best_similarity:     float
    polarity:            str          # positive / negative / neutral
    confidence:          float
    iro_label:           str          # opportunity / risk / context
    iro_score:           float        # 0~1  (polarity conf * similarity weight)
    method:              str

# ── polarity → IRO 매핑 ───────────────────────────────────────
def _to_iro(polarity: str, confidence: float, similarity: float) -> tuple[str, float]:
    """
    재무 영향 기준:
      positive → opportunity   (플러스 기대수익/비용절감)
      negative → risk          (마이너스 손실/비용발생)
      neutral  → context       (판단 보류)

    iro_score = confidence × similarity_weight
      similarity_weight: best_similarity_score 가 높을수록 이 chunk의
      sub_issue 연관도가 높으므로 점수에 더 반영
    """
    sim_w = min(float(similarity or 0.5), 1.0)   # 없으면 0.5 기본
    iro_score = round(confidence * sim_w, 4)

    if polarity == "positive":
        return "opportunity", iro_score
    elif polarity == "negative":
        return "risk", iro_score
    else:
        return "context", iro_score * 0.3        # neutral은 낮은 가중치


# ── DB에서 데이터 로드 ────────────────────────────────────────
def load_from_db(limit, group_filter, domain_filter) -> list[dict]:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    host   = os.getenv("POSTGRES_HOST", "192.168.0.106")
    port   = os.getenv("POSTGRES_PORT", "5432")
    db     = os.getenv("POSTGRES_DB" )
    user   = os.getenv("POSTGRES_USER" )
    pw     = os.getenv("POSTGRES_PASSWORD")
    table  = os.getenv("POSTGRES_TABLE", "esg_chunks")
    schema = os.getenv("POSTGRES_SCHEMA", "public")

    if not all([db, user, pw, table]):
        print(c("⚠️  .env 파일에 PG_DB / PG_USER / PG_PASSWORD / PG_TABLE 을 설정하세요.", YLW))
        print(c("   예시: cp .env.example .env  →  값 입력 후 재실행", DIM))
        sys.exit(1)

    try:
        import psycopg2, psycopg2.extras
    except ImportError:
        print(c("❌ psycopg2 없음: pip install psycopg2-binary", RED)); sys.exit(1)

    conn = psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pw)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # chunk_embedding 은 텍스트/벡터 모두 호환 — 불러오지 않음 (용량 절약)
    where_clauses = []
    params = []
    if group_filter:
        where_clauses.append("issue_group ILIKE %s")
        params.append(f"%{group_filter}%")
    if domain_filter:
        where_clauses.append("issue_group_domain ILIKE %s")
        params.append(f"%{domain_filter}%")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    limit_sql = f"LIMIT {limit}" if limit else ""

    sql = f"""
        SELECT
            chunk,
            issue_group,
            issue_group_domain,
            sub_issue_id,
            sub_issue_name,
            best_sub_issue_id,
            best_similarity_score,
            created_at
        FROM {schema}.{table}
        {where_sql}
        ORDER BY created_at DESC
        {limit_sql}
    """
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(r) for r in rows]


# ── 내장 샘플 (dry-run용) ─────────────────────────────────────
DRY_RUN_SAMPLES = [
    {"chunk":"현대모비스 리콜 50만대, 충당부채 200억 설정",
     "issue_group":"S_PRODUCT_SAFETY","issue_group_domain":"S",
     "sub_issue_id":"S001","sub_issue_name":"제품안전/품질",
     "best_sub_issue_id":"S001","best_similarity_score":0.91,"created_at":"2025-01-01"},
    {"chunk":"HL만도 온실가스 배출량 전년 대비 15% 감소 달성",
     "issue_group":"E_CLIMATE_RISK","issue_group_domain":"E",
     "sub_issue_id":"E001","sub_issue_name":"기후변화 대응",
     "best_sub_issue_id":"E001","best_similarity_score":0.88,"created_at":"2025-01-02"},
    {"chunk":"한온시스템, 산업재해율 업계 평균 2배 높아 논란",
     "issue_group":"S_OCCUPATIONAL_SAFETY","issue_group_domain":"S",
     "sub_issue_id":"S002","sub_issue_name":"산업안전",
     "best_sub_issue_id":"S002","best_similarity_score":0.85,"created_at":"2025-01-03"},
    {"chunk":"위아 ESG 위원회 신설, 이사회 독립 감독 구축",
     "issue_group":"G_ESG_GOVERNANCE","issue_group_domain":"G",
     "sub_issue_id":"G001","sub_issue_name":"ESG 거버넌스",
     "best_sub_issue_id":"G001","best_similarity_score":0.83,"created_at":"2025-01-04"},
    {"chunk":"전기차 부품 전환율 40% 달성, 미래 수주 확대 기대",
     "issue_group":"E_PRODUCT_ECO","issue_group_domain":"E",
     "sub_issue_id":"E002","sub_issue_name":"친환경 제품",
     "best_sub_issue_id":"E002","best_similarity_score":0.90,"created_at":"2025-01-05"},
    {"chunk":"개인정보 유출 사고, 고객 50만명 피해",
     "issue_group":"S_DATA_PRIVACY","issue_group_domain":"S",
     "sub_issue_id":"S003","sub_issue_name":"개인정보보호",
     "best_sub_issue_id":"S003","best_similarity_score":0.92,"created_at":"2025-01-06"},
    {"chunk":"탄소중립 로드맵 발표, 2040 넷제로 목표 선언",
     "issue_group":"E_CLIMATE_RISK","issue_group_domain":"E",
     "sub_issue_id":"E001","sub_issue_name":"기후변화 대응",
     "best_sub_issue_id":"E001","best_similarity_score":0.87,"created_at":"2025-01-07"},
    {"chunk":"R&D 투자 3년 연속 증가, 매출 대비 5.2%",
     "issue_group":"E_GREEN_INVESTMENT","issue_group_domain":"E",
     "sub_issue_id":"E003","sub_issue_name":"녹색투자",
     "best_sub_issue_id":"E003","best_similarity_score":0.75,"created_at":"2025-01-08"},
    {"chunk":"협력사 대금 지급 지연 개선, 상생협력 A등급",
     "issue_group":"S_SUPPLY_CHAIN","issue_group_domain":"S",
     "sub_issue_id":"S004","sub_issue_name":"공급망 관리",
     "best_sub_issue_id":"S004","best_similarity_score":0.81,"created_at":"2025-01-09"},
    {"chunk":"산업안전보건법 위반, 과태료 5000만원 부과",
     "issue_group":"S_OCCUPATIONAL_SAFETY","issue_group_domain":"S",
     "sub_issue_id":"S002","sub_issue_name":"산업안전",
     "best_sub_issue_id":"S002","best_similarity_score":0.93,"created_at":"2025-01-10"},
]


# ── 메인 ─────────────────────────────────────────────────────
def main():
    backend = sb.init_backend()

    # 데이터 로드
    if args.dry_run:
        print(c("\n🧪 dry-run 모드 — 내장 샘플 10건으로 테스트\n", YLW))
        rows = DRY_RUN_SAMPLES
    else:
        print(c("\n🔌 PostgreSQL 연결 중...", CYN))
        rows = load_from_db(args.limit, args.group, args.domain)
        print(c(f"✅ {len(rows)}건 로드 완료\n", GRN))

    if not rows:
        print(c("⚠️  데이터가 없습니다. 필터 조건을 확인하세요.", YLW))
        return

    # ── 분석 ────────────────────────────────────────────────
    results: list[ChunkResult] = []
    low_conf_rows = []

    print(f"{'No':>4}  {'IRO':<12} {'점수':>5}  {'신뢰도':>5}  {'sub_issue':<28}  텍스트")
    print("─" * 100)

    for i, row in enumerate(rows):
        text       = str(row.get("chunk") or "")[:400]
        sub_id     = str(row.get("sub_issue_id") or "")
        sub_name   = str(row.get("sub_issue_name") or "")
        ig         = str(row.get("issue_group") or "")
        domain     = str(row.get("issue_group_domain") or "")
        similarity = float(row.get("best_similarity_score") or 0.5)

        polarity, confidence, _ = sb.predict(text)
        iro_label, iro_score    = _to_iro(polarity, confidence, similarity)
        method = "model" if backend == "hf" else "rule"

        r = ChunkResult(
            chunk_id=i+1, text=text,
            issue_group=ig, issue_group_domain=domain,
            sub_issue_id=sub_id, sub_issue_name=sub_name,
            best_similarity=similarity,
            polarity=polarity, confidence=confidence,
            iro_label=iro_label, iro_score=iro_score,
            method=method,
        )
        results.append(r)

        if confidence < args.conf:
            low_conf_rows.append(r)

        PICON = {"opportunity": c("🟢 opportunity", GRN),
                 "risk":        c("🔴 risk       ", RED),
                 "context":     c("⚪ context    ", DIM)}
        label_str = PICON.get(iro_label, iro_label)
        sub_short = (sub_name[:26] + "..") if len(sub_name) > 28 else sub_name
        text_short = text[:42] + "…" if len(text) > 44 else text

        if args.detail or len(rows) <= 20:
            print(f"{i+1:>4}  {label_str}  {iro_score:>5.3f}  {confidence:>5.3f}  {sub_short:<28}  {text_short}")

    # ── 집계 ────────────────────────────────────────────────
    opp_rows  = [r for r in results if r.iro_label == "opportunity"]
    risk_rows = [r for r in results if r.iro_label == "risk"]
    ctx_rows  = [r for r in results if r.iro_label == "context"]
    n = len(results)

    # 1점 만점 스코어:  해당 그룹 iro_score 합 / 전체 건수
    opp_score  = sum(r.iro_score for r in opp_rows)  / n
    risk_score = sum(r.iro_score for r in risk_rows) / n
    ctx_score  = sum(r.iro_score for r in ctx_rows)  / n

    print("\n" + "═" * 75)
    print(c("  📊  기회 / 리스크 스코어링 결과", BOLD))
    print("═" * 75)
    print(f"  전체 분석 건수  : {c(str(n)+'건', BOLD)}  (백엔드: [{backend}])")
    print(f"  기회 (opportunity) : {c(str(len(opp_rows))+'건', GRN)}")
    print(f"  리스크 (risk)      : {c(str(len(risk_rows))+'건', RED)}")
    print(f"  판단보류 (context) : {c(str(len(ctx_rows))+'건', DIM)}")

    print(f"\n{'─'*75}")
    print(c("  1점 만점 종합 스코어  (iro_score 평균 = confidence × similarity)", BOLD))
    print(f"{'─'*75}")
    print(f"  🟢 기회   : {c(f'{opp_score:.3f}', GRN)}  {bar(opp_score, 35, GRN)}")
    print(f"  🔴 리스크 : {c(f'{risk_score:.3f}', RED)}  {bar(risk_score, 35, RED)}")
    print(f"  ⚪ 보류   : {c(f'{ctx_score:.3f}', DIM)}  {bar(ctx_score, 35)}")

    # ── ESG 도메인별 ─────────────────────────────────────────
    DOMAIN_LABEL = {"E":"환경(E)","S":"사회(S)","G":"거버넌스(G)","":"기타"}
    by_domain = defaultdict(list)
    for r in results:
        by_domain[r.issue_group_domain].append(r)

    if len(by_domain) > 1:
        print(f"\n{'─'*75}")
        print(c("  ESG 도메인별 기회 / 리스크 점수", BOLD))
        print(f"{'─'*75}")
        for domain, rows_d in sorted(by_domain.items()):
            nd = len(rows_d)
            os_ = sum(r.iro_score for r in rows_d if r.iro_label=="opportunity") / nd
            rs_ = sum(r.iro_score for r in rows_d if r.iro_label=="risk")        / nd
            dlabel = DOMAIN_LABEL.get(domain, domain)
            print(f"  [{dlabel}]  n={nd}  🟢기회={c(f'{os_:.3f}',GRN)}  🔴리스크={c(f'{rs_:.3f}',RED)}")

    # ── issue_group별 top5 ────────────────────────────────────
    by_group = defaultdict(list)
    for r in results:
        by_group[r.issue_group].append(r)

    print(f"\n{'─'*75}")
    print(c("  issue_group별 상세 (iro_score 상위 순)", BOLD))
    print(f"{'─'*75}")
    print(f"  {'issue_group':<30} {'건수':>4}  {'기회':>5}  {'리스크':>6}  {'우세'}")
    print(f"  {'─'*65}")

    group_summary = []
    for grp, rows_g in by_group.items():
        ng  = len(rows_g)
        og  = sum(r.iro_score for r in rows_g if r.iro_label=="opportunity") / ng
        rg  = sum(r.iro_score for r in rows_g if r.iro_label=="risk")        / ng
        group_summary.append((grp, ng, og, rg))

    for grp, ng, og, rg in sorted(group_summary, key=lambda x: x[2]+x[3], reverse=True):
        dominant = c("🟢 기회 우세", GRN) if og > rg else (c("🔴 리스크 우세", RED) if rg > og else "균형")
        grp_short = grp[:28] + ".." if len(grp) > 30 else grp
        print(f"  {grp_short:<30} {ng:>4}  {c(f'{og:.3f}',GRN):>14}  {c(f'{rg:.3f}',RED):>15}  {dominant}")

    # ── 낮은 신뢰도 경고 ────────────────────────────────────
    if low_conf_rows:
        print(f"\n{'─'*75}")
        print(c(f"  ⚠️  신뢰도 < {args.conf} — 수동 검토 권장 ({len(low_conf_rows)}건)", YLW))
        print(f"{'─'*75}")
        for r in low_conf_rows[:10]:
            print(f"  [{r.chunk_id:>3}] conf={r.confidence:.3f}  {r.sub_issue_name:<20}  {r.text[:50]}")
        if len(low_conf_rows) > 10:
            print(f"  ... 외 {len(low_conf_rows)-10}건")

    print(f"\n{'═'*75}\n")

    # ── CSV 내보내기 ─────────────────────────────────────────
    if args.export:
        import csv
        fields = ["chunk_id","iro_label","iro_score","polarity","confidence","method",
                  "issue_group","issue_group_domain","sub_issue_id","sub_issue_name",
                  "best_similarity","text"]
        with open(args.export, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in results:
                w.writerow({k: getattr(r, k) for k in fields})
        print(c(f"  💾 결과 저장 완료: {args.export}", GRN))


if __name__ == "__main__":
    main()
