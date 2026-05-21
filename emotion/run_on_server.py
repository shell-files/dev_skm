"""
run_on_server.py — 기회/리스크 스코어링 + 영향 평가 4기준
─────────────────────────────────────────────────────────────────────
실행 전 model_server.py 를 먼저 켜두세요.

    터미널1: python model_server.py   (계속 켜둠)
    터미널2: python run_on_server.py --url "postgresql://..."

옵션:
    --url      DB 접속 URL
    --limit    가져올 건수 (없으면 전체)
    --domain   E / S / G 필터
    --export   결과 CSV 저장 (기본: result.csv, 타임스탬프 자동 추가)
    --detail   행별 상세 출력
    --server   모델 서버 주소 (기본: http://localhost:8100)
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import os, sys, argparse, time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

# ── CLI ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--url",      default=None)
parser.add_argument("--host",     default="192.168.0.106")
parser.add_argument("--port",     default="5432")
parser.add_argument("--db",       default="postgres")
parser.add_argument("--user",     default="postgres")
parser.add_argument("--password", default="1234")
parser.add_argument("--schema",   default="public")
parser.add_argument("--table",    default="esg_chunks")
parser.add_argument("--limit",    type=int, default=None)
parser.add_argument("--domain",   default=None)
parser.add_argument("--group",    default=None)
parser.add_argument("--conf",     type=float, default=0.65)
parser.add_argument("--export",   default="result.csv")
parser.add_argument("--detail",   action="store_true")
parser.add_argument("--server",   default="http://localhost:8100")
args = parser.parse_args()

# ── URL 파싱 ─────────────────────────────────────────────────────
def parse_url(url):
    from urllib.parse import urlparse
    p = urlparse(url)
    return (p.hostname or "localhost", str(p.port or 5432),
            p.path.lstrip("/") or "postgres",
            p.username or "postgres", p.password or "")

if args.url:
    host, port, db, user, password = parse_url(args.url)
else:
    host, port, db, user, password = (
        args.host, args.port, args.db, args.user, args.password)

schema, table = args.schema, args.table

# ── 컬러 출력 ─────────────────────────────────────────────────────
R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
RED="\033[91m"; GRN="\033[92m"; YLW="\033[93m"; CYN="\033[96m"
def c(t, col): return f"{col}{t}{R}"
def bar(r, w=30, fc=GRN):
    n = round(r * w)
    return f"{fc}{'█'*n}{R}{DIM}{'░'*(w-n)}{R}"

# ── 감정분석 (모델 서버 우선, 없으면 규칙) ───────────────────────
NEG_W = {"리콜":3,"사고":3,"위반":3,"과태료":3,"소송":3,"처분":3,
         "유출":3,"결함":2,"피해":2,"논란":2,"취약":2,"의혹":2,
         "불안정":2,"우려":2,"지연":1,"손해":2,"침해":2,"부채":1}
POS_W = {"달성":3,"감소":2,"개선":3,"강화":2,"구축":2,"확대":2,
         "선언":1,"도입":2,"절감":2,"증가":2,"신설":2,"목표":1,
         "A등급":3,"확립":2,"성과":2,"운영":1}
MIT   = {"개선","대응","완화","보완","패치","예방","목표"}

_use_server = False

def _check_server():
    global _use_server
    try:
        import httpx
        r = httpx.get(f"{args.server}/health", timeout=3)
        if r.status_code == 200:
            info = r.json()
            _use_server = True
            print(c(f"✅ 모델 서버 연결 성공  백엔드: [{info['backend']}]", GRN))
            return
    except Exception:
        pass
    print(c("⚠️  모델 서버 없음 → 규칙 기반 엔진 사용", YLW))
    print(c(f"   (서버 시작: python model_server.py)", DIM))

def _server_predict(text: str):
    import httpx
    r = httpx.post(f"{args.server}/predict",
                   json={"text": text[:512]}, timeout=10)
    d = r.json()
    return d["polarity"], d["confidence"]

def _rule_predict(text: str):
    neg = max(0, sum(w for t,w in NEG_W.items() if t in text)
                - sum(1 for t in MIT if t in text))
    pos = sum(w for t,w in POS_W.items() if t in text)
    if   neg==0 and pos==0: return "neutral",  0.68
    elif neg > pos*1.5:     return "negative", round(min(0.65+neg*0.06,0.95),4)
    elif pos > neg*1.5:     return "positive", round(min(0.65+pos*0.06,0.95),4)
    else: return ("negative" if neg>=pos else "positive"), 0.60

def predict(text: str):
    if _use_server:
        return _server_predict(text)
    return _rule_predict(text)

# ── 영향 평가 4기준 ───────────────────────────────────────────────
# 각 기준: 0~3점
# 0=없음  1=낮음  2=중간  3=높음

# 영향규모 — 수치/금액/건수 키워드
SCALE_HIGH  = {"억원","만명","만대","대규모","전면","전체","전사"}
SCALE_MID   = {"수백","수천","수십","일부","상당"}
SCALE_LOW   = {"소규모","일부","일시"}

# 영향범위 — 대상 범위 키워드
SCOPE_HIGH  = {"전국","글로벌","업계","전체","모든","국내외"}
SCOPE_MID   = {"지역","다수","여러","복수"}
SCOPE_LOW   = {"단일","특정","일부"}

# 발생가능성 — 확정/진행 vs 가능성 키워드
PROB_HIGH   = {"발생","적발","처분","소송","유출","사고","위반","확정"}
PROB_MID    = {"우려","위험","가능성","예상","전망","논란"}
PROB_LOW    = {"검토","계획","목표","예정"}

# 회복불가능성 — 돌이킬 수 없는 키워드
IRREV_HIGH  = {"폐업","파산","사망","인명","영구","취소","박탈"}
IRREV_MID   = {"소송","행정처분","과태료","리콜","충당부채"}
IRREV_LOW   = {"개선","보완","패치","대응","완화"}


def score_impact(text: str, pol: str, conf: float) -> dict:
    """
    영향 평가 4기준 계산
    반환: {scale, scope, probability, irreversibility, impact_score}
    """
    # 1) 영향규모
    if   any(t in text for t in SCALE_HIGH): scale = 3
    elif any(t in text for t in SCALE_MID):  scale = 2
    elif any(t in text for t in SCALE_LOW):  scale = 1
    else: scale = 1  # 기본값

    # 2) 영향범위
    if   any(t in text for t in SCOPE_HIGH): scope = 3
    elif any(t in text for t in SCOPE_MID):  scope = 2
    elif any(t in text for t in SCOPE_LOW):  scope = 1
    else: scope = 1

    # 3) 발생가능성
    if   any(t in text for t in PROB_HIGH): prob = 3
    elif any(t in text for t in PROB_MID):  prob = 2
    elif any(t in text for t in PROB_LOW):  prob = 1
    else: prob = 2  # 기본 중간

    # 4) 회복불가능성
    if   any(t in text for t in IRREV_HIGH): irrev = 3
    elif any(t in text for t in IRREV_MID):  irrev = 2
    elif any(t in text for t in IRREV_LOW):  irrev = 1
    else: irrev = 1

    # neutral 이면 영향도 낮춤
    pol_weight = 1.0 if pol != "neutral" else 0.4

    # 영향도 점수 (0~1)
    # 가중치: 발생가능성 30%, 영향규모 30%, 영향범위 20%, 회복불가능성 20%
    raw = (prob*0.30 + scale*0.30 + scope*0.20 + irrev*0.20) / 3.0
    impact_score = round(raw * pol_weight * conf, 4)

    return {
        "scale":         scale,   # 영향규모
        "scope":         scope,   # 영향범위
        "probability":   prob,    # 발생가능성
        "irreversibility": irrev, # 회복불가능성
        "impact_score":  impact_score,
    }


def to_iro(pol: str, conf: float, sim: float, impact: dict):
    """
    기존 score + 영향도 보정
    final_score = score(conf×sim) × 0.6 + impact_score × 0.4
    """
    base_score  = round(conf * min(float(sim or 0.5), 1.0), 4)
    final_score = round(base_score * 0.6 + impact["impact_score"] * 0.4, 4)

    if pol == "positive": iro = "opportunity"
    elif pol == "negative": iro = "risk"
    else: iro = "context"

    return iro, final_score, base_score


# ── DB 로드 ───────────────────────────────────────────────────────
def load_db():
    try:
        import psycopg2, psycopg2.extras
    except ImportError:
        print(c("❌ psycopg2 없음: pip install psycopg2-binary", RED))
        sys.exit(1)

    print(c(f"🔌 {user}@{host}:{port}/{db}  →  {schema}.{table}", DIM))
    try:
        conn = psycopg2.connect(
            host=host, port=int(port), dbname=db,
            user=user, password=password, connect_timeout=10)
    except Exception as e:
        print(c(f"❌ 연결 실패: {e}", RED))
        sys.exit(1)

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema=%s AND table_name=%s
                   ORDER BY ordinal_position""", (schema, table))
    cols = [r["column_name"] for r in cur.fetchall()]
    sel  = [col for col in cols if col != "chunk_embedding"]

    where, params = [], []
    if args.domain: where.append("issue_group_domain ILIKE %s"); params.append(f"%{args.domain}%")
    if args.group:  where.append("issue_group ILIKE %s");        params.append(f"%{args.group}%")
    w_sql = ("WHERE " + " AND ".join(where)) if where else ""
    l_sql = f"LIMIT {args.limit}" if args.limit else ""

    cur.execute(
        f"SELECT {', '.join(sel)} FROM {schema}.{table} "
        f"{w_sql} ORDER BY created_at DESC {l_sql}", params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


# ── 결과 구조체 ───────────────────────────────────────────────────
@dataclass
class Row:
    idx: int; text: str; ig: str; domain: str
    sub_id: str; sub_name: str; sim: float
    pol: str; conf: float
    iro: str; final_score: float; base_score: float
    scale: int; scope: int; probability: int; irreversibility: int
    impact_score: float


# ── 메인 ─────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*70}")
    print(c("  DMA v6  기회 / 리스크 스코어링  +  영향 평가 4기준", BOLD))
    print(f"{'='*70}\n")

    _check_server()
    rows_raw = load_db()
    n = len(rows_raw)
    print(c(f"\n✅ {n:,}건 로드. 분석 시작...\n", GRN))

    if args.detail or n <= 30:
        print(f"{'No':>5}  {'IRO':<13} {'최종':>5}  {'기본':>5}  {'conf':>5}  "
              f"{'규모':>2} {'범위':>2} {'확률':>2} {'회복':>2}  {'sub_issue':<22}  텍스트")
        print("─" * 110)

    results: list[Row] = []
    t0 = time.time()

    for i, r in enumerate(rows_raw):
        text    = str(r.get("chunk") or "")[:400]
        ig      = str(r.get("issue_group") or "")
        domain  = str(r.get("issue_group_domain") or "")
        sub_id  = str(r.get("sub_issue_id") or "")
        sub_nm  = str(r.get("sub_issue_name") or "")
        sim     = float(r.get("best_similarity_score") or 0.5)

        pol, conf     = predict(text)
        impact        = score_impact(text, pol, conf)
        iro, fs, bs   = to_iro(pol, conf, sim, impact)

        results.append(Row(
            idx=i+1, text=text, ig=ig, domain=domain,
            sub_id=sub_id, sub_name=sub_nm, sim=sim,
            pol=pol, conf=conf,
            iro=iro, final_score=fs, base_score=bs,
            scale=impact["scale"], scope=impact["scope"],
            probability=impact["probability"],
            irreversibility=impact["irreversibility"],
            impact_score=impact["impact_score"],
        ))

        if args.detail or n <= 30:
            PI = {"opportunity": c("🟢 opportunity", GRN),
                  "risk":        c("🔴 risk       ", RED),
                  "context":     c("⚪ context    ", DIM)}
            print(f"{i+1:>5}  {PI[iro]}  {fs:>5.3f}  {bs:>5.3f}  {conf:>5.3f}  "
                  f"{impact['scale']:>2} {impact['scope']:>2} "
                  f"{impact['probability']:>2} {impact['irreversibility']:>2}  "
                  f"{sub_nm[:20]:<22}  {text[:38]}")

        if (i+1) % 500 == 0:
            elapsed = time.time() - t0
            speed   = (i+1) / elapsed
            remain  = (n-i-1) / speed if speed > 0 else 0
            print(c(f"  ... {i+1:,}/{n:,}건  {speed:.0f}건/초  남은 {remain:.0f}초", DIM))

    # ── 집계 ─────────────────────────────────────────────────────
    opp  = [r for r in results if r.iro == "opportunity"]
    risk = [r for r in results if r.iro == "risk"]
    ctx  = [r for r in results if r.iro == "context"]
    opp_sc  = sum(r.final_score for r in opp)  / n
    risk_sc = sum(r.final_score for r in risk) / n
    ctx_sc  = sum(r.final_score for r in ctx)  / n

    print(f"\n{'═'*70}")
    print(c("  📊  결과  (1점 만점 / 영향 평가 반영)", BOLD))
    print(f"{'═'*70}")
    print(f"  분석 건수 : {c(f'{n:,}건', BOLD)}  ({time.time()-t0:.1f}초)")
    print(f"  기회 {len(opp):,}건  /  리스크 {len(risk):,}건  /  보류 {len(ctx):,}건\n")
    print(f"  🟢 기회   {c(f'{opp_sc:.3f}', GRN)}  {bar(opp_sc, 35, GRN)}")
    print(f"  🔴 리스크 {c(f'{risk_sc:.3f}', RED)}  {bar(risk_sc, 35, RED)}")
    print(f"  ⚪ 보류   {c(f'{ctx_sc:.3f}', DIM)}  {bar(ctx_sc, 35)}")

    # 영향 평가 평균
    print(f"\n{'─'*70}")
    print(c("  영향 평가 4기준 평균 (전체)", BOLD))
    print(f"{'─'*70}")
    avg = lambda key: sum(getattr(r, key) for r in results) / n
    for label, key in [("영향규모    ","scale"),
                       ("영향범위    ","scope"),
                       ("발생가능성  ","probability"),
                       ("회복불가능성","irreversibility")]:
        v = avg(key)
        print(f"  {label} : {v:.2f} / 3.0  {bar(v/3, 25)}")

    # 영향도 높은 상위 5건
    sorted_risk = sorted([r for r in results if r.iro=="risk"],
                         key=lambda x: x.final_score, reverse=True)
    if sorted_risk:
        print(f"\n{'─'*70}")
        print(c("  리스크 상위 5건 (영향도 기준)", BOLD))
        print(f"{'─'*70}")
        for r in sorted_risk[:5]:
            print(f"  [{r.idx:>4}] 최종={r.final_score:.3f}  "
                  f"규모={r.scale} 범위={r.scope} "
                  f"확률={r.probability} 회복={r.irreversibility}")
            print(f"         {r.text[:60]}")

    # ESG 도메인별
    by_domain = defaultdict(list)
    for r in results: by_domain[r.domain].append(r)
    if len(by_domain) > 1:
        DN = {"E":"환경(E)","S":"사회(S)","G":"거버넌스(G)"}
        print(f"\n{'─'*70}")
        print(c("  ESG 도메인별", BOLD))
        print(f"{'─'*70}")
        for d, rows_d in sorted(by_domain.items()):
            nd  = len(rows_d)
            os_ = sum(r.final_score for r in rows_d if r.iro=="opportunity") / nd
            rs_ = sum(r.final_score for r in rows_d if r.iro=="risk")        / nd
            print(f"  [{DN.get(d,d)}]  n={nd:,}  "
                  f"🟢기회={c(f'{os_:.3f}', GRN)}  "
                  f"🔴리스크={c(f'{rs_:.3f}', RED)}")

    # issue_group별
    by_grp = defaultdict(list)
    for r in results: by_grp[r.ig].append(r)
    print(f"\n{'─'*70}")
    print(c("  issue_group별", BOLD))
    print(f"{'─'*70}")
    print(f"  {'issue_group':<30} {'건수':>5}  {'기회':>6}  {'리스크':>7}  우세")
    print(f"  {'─'*62}")
    for grp, rows_g in sorted(by_grp.items(),
                               key=lambda x: sum(r.final_score for r in x[1]),
                               reverse=True):
        ng  = len(rows_g)
        og  = sum(r.final_score for r in rows_g if r.iro=="opportunity") / ng
        rg  = sum(r.final_score for r in rows_g if r.iro=="risk")        / ng
        dom = (c("🟢 기회", GRN) if og > rg
               else c("🔴 리스크", RED) if rg > og else "균형")
        gs  = grp[:28] + "…" if len(grp) > 30 else grp
        print(f"  {gs:<30} {ng:>5}  "
              f"{c(f'{og:.3f}', GRN):>15}  "
              f"{c(f'{rg:.3f}', RED):>16}  {dom}")

    # 낮은 신뢰도
    low = [r for r in results if r.conf < args.conf]
    if low:
        print(f"\n{'─'*70}")
        print(c(f"  ⚠️  신뢰도 < {args.conf} 검토 권장: {len(low):,}건", YLW))
        for r in low[:5]:
            print(f"  [{r.idx:>4}] conf={r.conf:.3f}  {r.sub_name:<18}  {r.text[:50]}")
        if len(low) > 5: print(f"  ... 외 {len(low)-5:,}건")

    print(f"\n{'═'*70}\n")

    # ── CSV 저장 ─────────────────────────────────────────────────
    if args.export:
        import csv
        base, ext   = os.path.splitext(args.export)
        timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path   = f"{base}_{timestamp}{ext}"

        fields = ["idx","iro","final_score","base_score","impact_score",
                  "scale","scope","probability","irreversibility",
                  "pol","conf","sim","ig","domain",
                  "sub_id","sub_name","text"]
        with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in results:
                w.writerow({
                    "idx":r.idx,"iro":r.iro,
                    "final_score":r.final_score,
                    "base_score":r.base_score,
                    "impact_score":r.impact_score,
                    "scale":r.scale,"scope":r.scope,
                    "probability":r.probability,
                    "irreversibility":r.irreversibility,
                    "pol":r.pol,"conf":r.conf,"sim":r.sim,
                    "ig":r.ig,"domain":r.domain,
                    "sub_id":r.sub_id,"sub_name":r.sub_name,
                    "text":r.text,
                })
        print(c(f"  💾 CSV 저장 완료: {save_path}\n", GRN))


if __name__ == "__main__":
    import sys
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path  = f"output_{timestamp}.txt"

    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj); f.flush()
        def flush(self):
            for f in self.files:
                f.flush()

    log = open(log_path, "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log)
    main()
    log.close()
    sys.__stdout__.write(c(f"\n  📄 로그 저장 완료: {log_path}\n", GRN))