"""
model_server.py — KR-FinBert-SC 상시 서버 + 전체 분석 API
─────────────────────────────────────────────────────────────────────
실행:
    pip install fastapi uvicorn httpx psycopg2-binary
    python model_server.py

Swagger UI:
    http://localhost:8100/docs

주요 엔드포인트:
    GET  /health              서버 상태 확인
    POST /predict             단일 텍스트 감정 분석
    POST /predict/batch       여러 텍스트 일괄 분석
    POST /analyze             DB 연결 → 기회/리스크 전체 분석
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn, os
from datetime import datetime
from collections import defaultdict

app = FastAPI(
    title="DMA v6 ESG 감정분석 서버",
    description="KR-FinBert-SC 기반 ESG 기회/리스크 스코어링 API",
    version="1.0.0",
)

# ── 모델 로드 ─────────────────────────────────────────────────────
_pipe    = None
_backend = "rule"

LBL = {"positive":"positive","negative":"negative","neutral":"neutral",
       "LABEL_0":"negative","LABEL_1":"neutral","LABEL_2":"positive"}
NEG_W = {"리콜":3,"사고":3,"위반":3,"과태료":3,"소송":3,"처분":3,
         "유출":3,"결함":2,"피해":2,"논란":2,"취약":2,"의혹":2,
         "불안정":2,"우려":2,"지연":1,"손해":2,"침해":2,"부채":1}
POS_W = {"달성":3,"감소":2,"개선":3,"강화":2,"구축":2,"확대":2,
         "선언":1,"도입":2,"절감":2,"증가":2,"신설":2,"목표":1,
         "A등급":3,"확립":2,"성과":2,"운영":1}
MIT   = {"개선","대응","완화","보완","패치","예방","목표"}

@app.on_event("startup")
async def startup():
    global _pipe, _backend
    try:
        from transformers import pipeline, logging as hl
        hl.set_verbosity_error()
        print("⏳ KR-FinBert-SC 로딩 중...")
        _pipe = pipeline(
            "text-classification",
            # model="snunlp/KR-FinBert-SC",
            # model="nlp04/korean_sentiment_analysis_kcelectra",
            # model ="klue/roberta-base",
            model = DataWizardd/finbert-sentiment-ko,
            top_k=None, device=-1,
            truncation=True, max_length=512,
        )
        _backend = "hf"
        print("✅ KR-FinBert-SC 로드 완료")
    except Exception as e:
        _backend = "rule"
        print(f"⚠️  모델 로드 실패 ({e}) → 규칙 기반 엔진 사용")


# ── 내부 함수 ─────────────────────────────────────────────────────
def _model_predict(text: str):
    output = _pipe(text[:512])
    first  = output[0]
    raw    = first if isinstance(first, list) else output
    if not isinstance(raw[0], dict):
        return "neutral", 0.68
    best = max(raw, key=lambda x: x["score"])
    return LBL.get(best["label"], "neutral"), round(best["score"], 4)

def _rule_predict(text: str):
    neg = max(0, sum(w for t,w in NEG_W.items() if t in text)
                - sum(1 for t in MIT if t in text))
    pos = sum(w for t,w in POS_W.items() if t in text)
    if   neg==0 and pos==0: return "neutral",  0.68
    elif neg > pos*1.5:     return "negative", round(min(0.65+neg*0.06,0.95),4)
    elif pos > neg*1.5:     return "positive", round(min(0.65+pos*0.06,0.95),4)
    else: return ("negative" if neg>=pos else "positive"), 0.60

def _predict(text: str):
    if _pipe: return _model_predict(text)
    return _rule_predict(text)

def _predict_no_neutral(text: str):
    """
    neutral 이 나오면 모델 전체 점수 중
    negative vs positive 중 높은 쪽으로 강제 배정.
    confidence 는 두 번째로 높은 점수로 낮춰서 반환.
    """
    if not text or not isinstance(text, str):
        return "negative", 0.50

    # 모델 사용 시
    if _pipe:
        output = _pipe(text[:512])
        first  = output[0]
        raw    = first if isinstance(first, list) else output
        if not isinstance(raw[0], dict):
            return "negative", 0.50

        scores = {LBL.get(r["label"], r["label"]): r["score"] for r in raw}
        pol    = LBL.get(max(raw, key=lambda x: x["score"])["label"], "neutral")

        if pol != "neutral":
            return pol, round(scores.get(pol, 0.68), 4)

        # neutral 일 때 → negative/positive 중 높은 쪽
        neg_sc = scores.get("negative", 0)
        pos_sc = scores.get("positive", 0)
        if neg_sc >= pos_sc:
            return "negative", round(neg_sc, 4)
        return "positive", round(pos_sc, 4)

    # 규칙 기반
    pol, conf = _rule_predict(text)
    if pol != "neutral":
        return pol, conf

    # neutral 일 때 → 부정 키워드 vs 긍정 키워드 원점수로 판단
    neg = sum(w for t, w in NEG_W.items() if t in text)
    pos = sum(w for t, w in POS_W.items() if t in text)
    return ("negative" if neg >= pos else "positive"), 0.55

# 영향 평가 기준
SCALE_HIGH={"억원","만명","만대","대규모","전면","전체","전사"}
SCALE_MID={"수백","수천","수십","상당"}
SCOPE_HIGH={"전국","글로벌","업계","전체","모든","국내외"}
SCOPE_MID={"지역","다수","여러","복수"}
PROB_HIGH={"발생","적발","처분","소송","유출","사고","위반","확정"}
PROB_MID={"우려","위험","가능성","예상","전망","논란"}
IRREV_HIGH={"폐업","파산","사망","인명","영구","취소","박탈"}
IRREV_MID={"소송","행정처분","과태료","리콜","충당부채"}
IRREV_LOW={"개선","보완","패치","대응","완화"}

def _impact(text, pol: str, conf: float) -> dict:
    if not text or not isinstance(text, str):
        return {"scale":1,"scope":1,"probability":1,"irreversibility":1,"impact_score":0.0}
    scale = 3 if any(t in text for t in SCALE_HIGH) else 2 if any(t in text for t in SCALE_MID) else 1
    scope = 3 if any(t in text for t in SCOPE_HIGH) else 2 if any(t in text for t in SCOPE_MID) else 1
    prob  = 3 if any(t in text for t in PROB_HIGH)  else 2 if any(t in text for t in PROB_MID)  else 1
    irrev = 3 if any(t in text for t in IRREV_HIGH) else 2 if any(t in text for t in IRREV_MID) else 1 if any(t in text for t in IRREV_LOW) else 1
    score = round((prob*0.30 + scale*0.30 + scope*0.20 + irrev*0.20) / 3.0 * conf, 4)
    return {"scale":scale,"scope":scope,"probability":prob,"irreversibility":irrev,"impact_score":score}

# ── 재무 평가 기준 ─────────────────────────────────────────────────
import re as _re

# 잠재규모 키워드 (숫자 없는 경우 보조)
FIN_SCALE_HIGH_KW = {"매출증대","시장점유율","대형수주","독점","압도적"}
FIN_SCALE_MID_KW  = {"CAPEX","설비투자","원가절감","수주","납품","비용절감"}
FIN_SCALE_LOW_KW  = {"비용발생","소규모투자","일부비용","운영비"}

# 재무 발생가능성 키워드
FIN_PROB_HIGH_KW  = {"계약체결","수주확정","납품확정","처분확정","손실확정",
                     "배상판결","과징금확정","부과","징수"}
FIN_PROB_MID_KW   = {"계약예정","수주예상","협의중","입찰","전망","기대",
                     "예상매출","추진","논의","검토중"}
FIN_PROB_LOW_KW   = {"검토","계획","구상","가능성","탐색","모색"}

def _extract_amount_eok(text) -> float:
    """
    텍스트에서 금액을 억원 단위로 추출
    예) 500억원 → 500   /   1조2000억 → 12000
        3.5조 → 35000   /   5000만원 → 0.5
    """
    if not text or not isinstance(text, str):
        return 0.0
    total = 0.0
    used_pos = set()  # 이미 처리한 위치 추적 (중복 합산 방지)

    # 1) 조+억 혼합  예) 1조2000억, 2조5000억
    for m in _re.finditer(r'(\d+(?:\.\d+)?)\s*조\s*(\d+)\s*억', text):
        total += float(m.group(1)) * 10000 + float(m.group(2))
        used_pos.update(range(m.start(), m.end()))

    # 2) 조 단위 (단독)  예) 3.5조, 1조
    for m in _re.finditer(r'(\d+(?:\.\d+)?)\s*조', text):
        if not used_pos.intersection(range(m.start(), m.end())):
            total += float(m.group(1)) * 10000
            used_pos.update(range(m.start(), m.end()))

    # 3) 억 단위  예) 200억, 1,200억원
    for m in _re.finditer(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*억', text):
        if not used_pos.intersection(range(m.start(), m.end())):
            total += float(m.group(1).replace(',', ''))
            used_pos.update(range(m.start(), m.end()))

    # 4) 천만/만원 단위  예) 5000만원 → 0.5억
    for m in _re.finditer(r'(\d+(?:\.\d+)?)\s*천만', text):
        if not used_pos.intersection(range(m.start(), m.end())):
            total += float(m.group(1)) * 0.1
    for m in _re.finditer(r'(\d+(?:\.\d+)?)\s*만\s*원', text):
        if not used_pos.intersection(range(m.start(), m.end())):
            total += float(m.group(1)) / 10000

    return round(total, 4)

def _financial(text, pol: str, conf: float) -> dict:
    """
    재무 평가 2기준
      fin_scale : 잠재규모     1~3
      fin_prob  : 발생가능성   1~3
      financial_score : 0~1
    결정 우선순위: 숫자 금액 → 키워드 순
    """
    if not text or not isinstance(text, str):
        return {"fin_scale": 1, "fin_prob": 1,
                "financial_score": 0.0, "detected_amount": 0.0}
    # ── 잠재규모: 숫자 우선 ──────────────────────────────────────
    amount = _extract_amount_eok(text)
    if amount >= 5000 or any(t in text for t in FIN_SCALE_HIGH_KW):
        fin_scale = 3   # 5000억(0.5조) 이상
    elif amount >= 50 or any(t in text for t in FIN_SCALE_MID_KW):
        fin_scale = 2   # 50억 이상
    elif amount > 0 or any(t in text for t in FIN_SCALE_LOW_KW):
        fin_scale = 1   # 금액 언급 있음
    else:
        fin_scale = 1   # 기본값

    # ── 재무 발생가능성: 키워드 우선 ────────────────────────────
    if   any(t in text for t in FIN_PROB_HIGH_KW): fin_prob = 3
    elif any(t in text for t in FIN_PROB_MID_KW):  fin_prob = 2
    elif any(t in text for t in FIN_PROB_LOW_KW):  fin_prob = 1
    else:
        # 키워드 없으면 금액 크기로 보조 판단
        fin_prob = 2 if amount >= 50 else 1

    score = round((fin_scale*0.60 + fin_prob*0.40) / 3.0 * conf, 4)
    return {
        "fin_scale":       fin_scale,
        "fin_prob":        fin_prob,
        "financial_score": score,
        "detected_amount": amount,
        "_text":           text,     # _time_horizon 에서 참조용
    }

# ── 시간 지평 키워드 ─────────────────────────────────────────────
# 단기: 즉각적·긴급·단기 실현 가능한 키워드
SHORT_KW = {
    "즉시","즉각","긴급","당일","올해","이번분기","이번 분기","단기",
    "빠른","신속","조기","곧","최근","현재","올해안","올해 안",
    "1년","2년","수개월","패치","수습","긴급대응","단기간",
}
# 장기: 중장기·미래 지향·계획 키워드
LONG_KW = {
    "2030","2035","2040","2045","2050","넷제로","net zero","탄소중립",
    "로드맵","중장기","장기","전략","10년","20년","중기","장기계획",
    "비전","목표연도","단계적","단계별","장기적","미래","중기계획",
}

def _time_horizon(text: str, fin_prob: int) -> str:
    """
    단기 / 장기 판정
    키워드 우선, 없으면 재무 발생가능성으로 보조 판단
      fin_prob=3(확정) → 단기
      fin_prob=1(계획) → 장기
    """
    if not text or not isinstance(text, str):
        return "단기" if fin_prob >= 2 else "장기"

    short_hit = sum(1 for t in SHORT_KW if t in text)
    long_hit  = sum(1 for t in LONG_KW  if t in text)

    if short_hit > long_hit:   return "단기"
    if long_hit  > short_hit:  return "장기"

    # 동점이거나 둘 다 0 → fin_prob 로 판단
    return "단기" if fin_prob >= 2 else "장기"


def _iro(pol, conf, sim, impact, financial):
    base  = round(conf * min(float(sim or 0.5), 1.0), 4)
    # base 35% + 영향평가 35% + 재무평가 30%
    final = round(base * 0.35
                  + impact["impact_score"]      * 0.35
                  + financial["financial_score"] * 0.30, 4)

    direction = "기회" if pol == "positive" else "리스크"
    horizon   = _time_horizon(
        financial.get("_text", ""), financial["fin_prob"])
    label = f"{direction}_{horizon}"   # 기회_단기 / 기회_장기 / 리스크_단기 / 리스크_장기
    return label, final, base


# ── 스키마 ────────────────────────────────────────────────────────
class PredictReq(BaseModel):
    text: str = Field(..., example="현대모비스 리콜 50만대, 충당부채 200억 설정")

class PredictRes(BaseModel):
    polarity:   str
    confidence: float
    backend:    str

class AnalyzeReq(BaseModel):
    db_url:  str = Field(
        ...,
        example="postgresql://postgres:1234@192.168.0.106:5432/postgres",
        description="PostgreSQL 접속 URL"
    )
    schema:  str = Field(default="public",      example="public")
    table:   str = Field(default="esg_chunks",  example="esg_chunks")
    limit:   Optional[int]  = Field(default=None,  example=100,   description="가져올 건수 (없으면 전체)")
    offset:  Optional[int]  = Field(default=None,  example=0,     description="시작 위치 (0부터, id 순 정렬 기준)")
    id_from: Optional[int]  = Field(default=None,  example=1,     description="시작 id (이 id 이상)")
    id_to:   Optional[int]  = Field(default=None,  example=1000,  description="끝 id (이 id 이하)")
    order:   str            = Field(default="asc",                description="정렬 방향: asc(id 오름차순) / desc(최신순) / random(랜덤)")
    domain:  Optional[str]  = Field(default=None,  example="E",   description="E / S / G 필터")
    export:  Optional[bool] = Field(default=True,                 description="CSV 파일 저장 여부")

class IROItem(BaseModel):
    idx:             int
    db_id:           Optional[int]   # DB 원본 id (숫자형)
    iro:             str              # 기회_단기 / 기회_장기 / 리스크_단기 / 리스크_장기
    time_horizon:    str              # 단기 / 장기
    direction:       str              # 기회 / 리스크
    final_score:     float
    base_score:      float
    impact_score:    float
    scale:           int
    scope:           int
    probability:     int
    irreversibility: int
    polarity:        str
    confidence:      float
    similarity:      float
    issue_group:     str
    domain:          str
    sub_issue_name:  str
    text:            str
    fin_scale:       int
    fin_prob:         int
    financial_score:  float


class AnalyzeRes(BaseModel):
    total:               int
    기회_단기_cnt:         int
    기회_장기_cnt:         int
    리스크_단기_cnt:        int
    리스크_장기_cnt:        int
    기회_score:           float
    리스크_score:          float
    backend:           str
    elapsed_sec:       float
    csv_file:          Optional[str]
    items:             list[IROItem]


# ── 엔드포인트 ────────────────────────────────────────────────────
@app.get("/health", summary="서버 상태 확인")
def health():
    return {"status": "ok", "backend": _backend}


@app.post("/predict", response_model=PredictRes, summary="단일 텍스트 감정 분석")
def predict(req: PredictReq):
    pol, conf = _predict(req.text)
    return PredictRes(polarity=pol, confidence=conf, backend=_backend)


@app.post("/predict/batch", summary="여러 텍스트 일괄 감정 분석")
def predict_batch(items: list[PredictReq]):
    return [{"polarity": p, "confidence": c, "text": it.text}
            for it in items for p, c in [_predict(it.text)]]


@app.post("/analyze", response_model=AnalyzeRes, summary="DB 연결 → 기회/리스크 전체 분석")
def analyze(req: AnalyzeReq):
    import time
    from urllib.parse import urlparse

    # DB 연결
    p = urlparse(req.db_url)
    try:
        import psycopg2, psycopg2.extras
        conn = psycopg2.connect(
            host=p.hostname, port=p.port or 5432,
            dbname=p.path.lstrip("/"), user=p.username,
            password=p.password, connect_timeout=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 연결 실패: {e}")

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema=%s AND table_name=%s
                   ORDER BY ordinal_position""", (req.schema, req.table))
    cols = [r["column_name"] for r in cur.fetchall()]
    sel  = [col for col in cols if col != "chunk_embedding"]

    # WHERE 조건 빌드 (파라미터 바인딩으로 SQL 인젝션 방지)
    where_parts, params = [], []
    if req.domain:
        where_parts.append("issue_group_domain ILIKE %s")
        params.append(f"%{req.domain}%")
    if req.id_from is not None:
        where_parts.append("id >= %s")
        params.append(req.id_from)
    if req.id_to is not None:
        where_parts.append("id <= %s")
        params.append(req.id_to)
    w_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    # 정렬 방향
    order_lower = req.order.lower()
    if order_lower == "random":
        order_sql = "ORDER BY RANDOM()"
    else:
        order_dir = "ASC" if order_lower == "asc" else "DESC"
        order_col = "id" if "id" in cols else (cols[0] if cols else "id")
        order_sql = f"ORDER BY {order_col} {order_dir}"

    # LIMIT / OFFSET
    page_parts = []
    if req.limit  is not None: page_parts.append(f"LIMIT {req.limit}")
    if req.offset is not None: page_parts.append(f"OFFSET {req.offset}")
    page_sql = " ".join(page_parts)

    sql = (f"SELECT {', '.join(sel)} FROM {req.schema}.{req.table} "
           f"{w_sql} {order_sql} {page_sql}")
    print(f"  [쿼리] {sql[:120]}  params={params}")
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()

    # 원본 ID 컬럼 자동 감지
    # 우선순위: id → chunk_id → doc_id → record_id → 첫 번째 컬럼
    ID_CANDIDATES = ["id", "chunk_id", "doc_id", "record_id", "uid"]
    id_col = next((c for c in ID_CANDIDATES if c in cols), cols[0] if cols else None)
    print(f"  [ID 컬럼] 감지됨: '{id_col}'  (전체 컬럼: {cols})")

    # 분석
    t0      = time.time()
    results = []
    
    for i, r in enumerate(rows):
        raw_chunk   = r.get("chunk")
        text        = str(raw_chunk).strip()[:400] if raw_chunk is not None else ""
        ig          = str(r.get("issue_group") or "")
        domain      = str(r.get("issue_group_domain") or "")
        sub_nm      = str(r.get("sub_issue_name") or "")
        sub_id      = str(r.get("sub_issue_id") or "")
        sim         = float(r.get("best_similarity_score") or 0.5)
        raw_id = r.get(id_col) if id_col else None
        try:
            db_id = int(raw_id) if raw_id is not None else None
        except (ValueError, TypeError):
            db_id = None

        pol, conf        = _predict_no_neutral(text)
        impact           = _impact(text, pol, conf)
        financial        = _financial(text, pol, conf)
        iro, fs, bs      = _iro(pol, conf, sim, impact, financial)
        
        direction = "기회" if pol == "positive" else "리스크"
        horizon   = _time_horizon(text, financial["fin_prob"])
        results.append(IROItem(
            idx=i+1, db_id=db_id,
            iro=iro, time_horizon=horizon, direction=direction,
            final_score=fs, base_score=bs,
            impact_score=impact["impact_score"],
            scale=impact["scale"], scope=impact["scope"],
            probability=impact["probability"],
            irreversibility=impact["irreversibility"],
            polarity=pol, confidence=conf, similarity=sim,
            issue_group=ig, domain=domain,
            sub_issue_name=sub_nm, text=text,
            fin_scale=financial["fin_scale"],
            fin_prob=financial["fin_prob"],
            financial_score=financial["financial_score"],
        ))

    n       = len(results)
    elapsed = round(time.time() - t0, 2)
    g_short  = [r for r in results if r.iro == "기회_단기"]
    g_long   = [r for r in results if r.iro == "기회_장기"]
    r_short  = [r for r in results if r.iro == "리스크_단기"]
    r_long   = [r for r in results if r.iro == "리스크_장기"]
    opp_all  = g_short + g_long
    risk_all = r_short + r_long
    opp_sc   = round(sum(r.final_score for r in opp_all)  / n, 4) if n else 0
    risk_sc  = round(sum(r.final_score for r in risk_all) / n, 4) if n else 0

    # CSV 저장
    csv_file = None
    if req.export:
        import csv
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"result_{ts}.csv"
        print(f"  💾 CSV 저장 중: {csv_file}", flush=True)
        fields   = ["idx","db_id","iro","time_horizon","direction","final_score","base_score","impact_score",
                    "scale","scope","probability","irreversibility",
                    "fin_scale","fin_prob","financial_score",
                    "polarity","confidence","similarity",
                    "issue_group","domain","sub_issue_name","text"]
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in results:
                w.writerow({
                    "idx":             r.idx,
                    "db_id":           r.db_id,
                    "iro":             r.iro,
                    "time_horizon":    r.time_horizon,
                    "direction":       r.direction,
                    "final_score":     r.final_score,
                    "base_score":      r.base_score,
                    "impact_score":    r.impact_score,
                    "scale":           r.scale,
                    "scope":           r.scope,
                    "probability":     r.probability,
                    "irreversibility": r.irreversibility,
                    "fin_scale":       r.fin_scale,
                    "fin_prob":        r.fin_prob,
                    "financial_score": r.financial_score,
                    "polarity":        r.polarity,
                    "confidence":      r.confidence,
                    "similarity":      r.similarity,
                    "issue_group":     r.issue_group,
                    "domain":          r.domain,
                    "sub_issue_name":  r.sub_issue_name,
                    "text":            r.text,
                })

   
    return AnalyzeRes(
        total=n,
        기회_단기_cnt=len(g_short),
        기회_장기_cnt=len(g_long),
        리스크_단기_cnt=len(r_short),
        리스크_장기_cnt=len(r_long),
        기회_score=opp_sc,
        리스크_score=risk_sc,
        backend=_backend, elapsed_sec=elapsed,
        csv_file=csv_file, items=results,
    )


@app.get("/download/{filename}", summary="저장된 CSV 다운로드")
def download(filename: str):
    if not filename.endswith(".csv") or "/" in filename:
        raise HTTPException(status_code=400, detail="잘못된 파일명")
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="파일 없음")
    return FileResponse(filename, media_type="text/csv",
                        filename=filename)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)