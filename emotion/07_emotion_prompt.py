"""
07_emotion_prompt.py — Ollama LLM 프롬프트 기반 ESG 감정분석 서버
─────────────────────────────────────────────────────────────────────
실행:
    uv run python 07_emotion_prompt.py

Swagger UI:
    http://localhost:8100/docs

백엔드: Ollama (qwen2.5:7b) → 실패 시 규칙 기반 자동 대체
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn, os, json
import httpx
# import re as _re  # 규칙 기반 비활성화로 미사용
from datetime import datetime

app = FastAPI(
    title="DMA v7 ESG 감정분석 서버 (Ollama)",
    description="Ollama LLM 프롬프트 기반 ESG 기회/리스크 스코어링 API",
    version="2.0.0",
)

# ── 상태 ──────────────────────────────────────────────────────────
_backend = "rule"

# ── 규칙 기반 키워드 (Ollama 오류 시 fallback) ────────────────────
NEG_W = {"리콜":3,"사고":3,"위반":3,"과태료":3,"소송":3,"처분":3,
         "유출":3,"결함":2,"피해":2,"논란":2,"취약":2,"의혹":2,
         "불안정":2,"우려":2,"지연":1,"손해":2,"침해":2,"부채":1}
POS_W = {"달성":3,"감소":2,"개선":3,"강화":2,"구축":2,"확대":2,
         "선언":1,"도입":2,"절감":2,"증가":2,"신설":2,"목표":1,
         "A등급":3,"확립":2,"성과":2,"운영":1}
MIT   = {"개선","대응","완화","보완","패치","예방","목표"}

SCALE_HIGH  = {"억원","만명","만대","대규모","전면","전체","전사"}
SCALE_MID   = {"수백","수천","수십","상당"}
SCOPE_HIGH  = {"전국","글로벌","업계","전체","모든","국내외"}
SCOPE_MID   = {"지역","다수","여러","복수"}
PROB_HIGH   = {"발생","적발","처분","소송","유출","사고","위반","확정"}
PROB_MID    = {"우려","위험","가능성","예상","전망","논란"}
IRREV_HIGH  = {"폐업","파산","사망","인명","영구","취소","박탈"}
IRREV_MID   = {"소송","행정처분","과태료","리콜","충당부채"}
IRREV_LOW   = {"개선","보완","패치","대응","완화"}

FIN_SCALE_HIGH_KW = {"매출증대","시장점유율","대형수주","독점","압도적"}
FIN_SCALE_MID_KW  = {"CAPEX","설비투자","원가절감","수주","납품","비용절감"}
FIN_PROB_HIGH_KW  = {"계약체결","수주확정","납품확정","처분확정","손실확정","배상판결","과징금확정","부과","징수"}
FIN_PROB_MID_KW   = {"계약예정","수주예상","협의중","입찰","전망","기대","예상매출","추진","논의","검토중"}
FIN_PROB_LOW_KW   = {"검토","계획","구상","가능성","탐색","모색"}

SHORT_KW = {"즉시","즉각","긴급","당일","올해","이번분기","단기","빠른","신속","조기","곧","최근","현재","1년","2년","수개월","패치","수습"}
LONG_KW  = {"2030","2035","2040","2045","2050","넷제로","탄소중립","로드맵","중장기","장기","10년","20년","중기","장기계획","비전","목표연도","단계적","장기적","미래"}

# ── Ollama 설정 ───────────────────────────────────────────────────
OLLAMA_URL   = "http://localhost:11434/api/chat"
# OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_MODEL = "qwen3:8b"

OLLAMA_SYSTEM = """당신은 ESG 전문 분석가입니다.
특정 키워드 없이 문장 전체의 맥락과 의미를 이해해서 판단하세요. 반드시 아래 JSON 형식으로만 응답하세요.

{
  "polarity": "positive 또는 negative",
  "confidence": 0.5~0.95,
  "scale": 1~3,
  "scope": 1~3,
  "probability": 1~3,
  "irreversibility": 1~3,
  "fin_scale": 1~3,
  "fin_prob": 1~3,
  "fin_effect": 1~5,
  "fin_year": 1~5,  
  "time_horizon": "단기 또는 장기"
}

판단 기준 (키워드가 없어도 문맥으로 추론):
- polarity: 이 사건/상황이 기업에 전반적으로 이로우면 positive, 해로우면 negative
- confidence: 판단의 확신 정도 (명확할수록 높게, 모호할수록 낮게)
- scale: 영향받는 규모
    1=개인·소수·단일 부서 수준
    2=사업부·지역·수백~수천 명 수준
    3=전사·산업·사회 전반에 걸치는 수준
- scope: 영향이 퍼지는 범위
    1=내부 한 부문에 국한
    2=여러 부문 또는 특정 지역
    3=전사·업계·전국·글로벌
- probability: 이 영향이 실제로 발생할 가능성
    1=아직 구상·검토 단계
    2=추진 중이거나 발생 가능성이 있음
    3=이미 발생했거나 확정된 사실
- irreversibility: 한번 발생하면 되돌리기 얼마나 어려운가
    1=단기간에 회복·수정 가능
    2=상당한 노력과 시간이 필요
    3=인명피해·폐업·영구적 손실 등 되돌리기 불가
- fin_scale: 재무적 파급 규모
    1=운영 예산 수준의 소액
    2=수십억 규모의 투자·손실
    3=수백억 이상 또는 사업 존폐에 영향
- fin_prob: 재무 영향이 실제로 발생할 가능성
    1=계획·구상 단계
    2=추진 중·전망·예상
    3=계약 체결·처분 확정 등 이미 현실화
- fin_effect : 재무 영향 매출 
    1=재무 규모 0.01 미만
    2=재무 규모 0.01 ~ 0.03
    3=재무 규모 0.03 ~ 0.05 
    4=재무 규모 0.05 ~ 0.1
    5=재무 규모 0.1 이상
- fin_year : 재무 영향 연도
    1=발생가능성 10년 미만
    2=발생가능성 10년~ 7년
    3=발생가능성 7년~ 5년
    4=발생가능성 5년~ 2년
    5=발생가능성 2년 이상   
- time_horizon: 영향이 주로 나타나는 시간대
    단기=5년 이내에 가시적 영향
    장기=6년 이상의 중장기 계획이나 구조적 변화
    """



# ── startup ───────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global _backend
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            _backend = "ollama"
            print(f"Ollama 연결 완료 → {OLLAMA_MODEL} 사용")
            return
    except Exception:
        pass
    # _backend = "rule"
    # print("Ollama 연결 실패 → 규칙 기반 엔진 사용")


# ── 규칙 기반 함수 (비활성화) ─────────────────────────────────────
# def _rule_predict(text: str):
#     neg = max(0, sum(w for t, w in NEG_W.items() if t in text)
#                 - sum(1 for t in MIT if t in text))
#     pos = sum(w for t, w in POS_W.items() if t in text)
#     if   neg == 0 and pos == 0: return "neutral",  0.68
#     elif neg > pos * 1.5:       return "negative", round(min(0.65 + neg * 0.06, 0.95), 4)
#     elif pos > neg * 1.5:       return "positive", round(min(0.65 + pos * 0.06, 0.95), 4)
#     else: return ("negative" if neg >= pos else "positive"), 0.60
#
# def _extract_amount_eok(text) -> float:
#     if not text: return 0.0
#     total, used = 0.0, set()
#     for m in _re.finditer(r'(\d+(?:\.\d+)?)\s*조\s*(\d+)\s*억', text):
#         total += float(m.group(1)) * 10000 + float(m.group(2))
#         used.update(range(m.start(), m.end()))
#     for m in _re.finditer(r'(\d+(?:\.\d+)?)\s*조', text):
#         if not used.intersection(range(m.start(), m.end())):
#             total += float(m.group(1)) * 10000; used.update(range(m.start(), m.end()))
#     for m in _re.finditer(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*억', text):
#         if not used.intersection(range(m.start(), m.end())):
#             total += float(m.group(1).replace(',', '')); used.update(range(m.start(), m.end()))
#     for m in _re.finditer(r'(\d+(?:\.\d+)?)\s*천만', text):
#         if not used.intersection(range(m.start(), m.end())): total += float(m.group(1)) * 0.1
#     for m in _re.finditer(r'(\d+(?:\.\d+)?)\s*만\s*원', text):
#         if not used.intersection(range(m.start(), m.end())): total += float(m.group(1)) / 10000
#     return round(total, 4)
#
# def _rule_impact(text, conf):
#     scale = 3 if any(t in text for t in SCALE_HIGH) else 2 if any(t in text for t in SCALE_MID) else 1
#     scope = 3 if any(t in text for t in SCOPE_HIGH) else 2 if any(t in text for t in SCOPE_MID) else 1
#     prob  = 3 if any(t in text for t in PROB_HIGH)  else 2 if any(t in text for t in PROB_MID)  else 1
#     irrev = 3 if any(t in text for t in IRREV_HIGH) else 2 if any(t in text for t in IRREV_MID) else 1
#     return {"scale": scale, "scope": scope, "probability": prob, "irreversibility": irrev,
#             "impact_score": round((prob*0.30 + scale*0.30 + scope*0.20 + irrev*0.20) / 3.0 * conf, 4)}
#
# def _rule_financial(text, conf):
#     amount = _extract_amount_eok(text)
#     fin_scale = 3 if (amount >= 5000 or any(t in text for t in FIN_SCALE_HIGH_KW)) else \
#                 2 if (amount >= 50   or any(t in text for t in FIN_SCALE_MID_KW))  else 1
#     fin_prob  = 3 if any(t in text for t in FIN_PROB_HIGH_KW) else \
#                 2 if any(t in text for t in FIN_PROB_MID_KW)  else \
#                 1 if any(t in text for t in FIN_PROB_LOW_KW)  else (2 if amount >= 50 else 1)
#     return {"fin_scale": fin_scale, "fin_prob": fin_prob, "_text": text,
#             "financial_score": round((fin_scale*0.60 + fin_prob*0.40) / 3.0 * conf, 4)}
#
# def _time_horizon(text, fin_prob):
#     short = sum(1 for t in SHORT_KW if t in text)
#     long  = sum(1 for t in LONG_KW  if t in text)
#     if short > long: return "단기"
#     if long > short: return "장기"
#     return "단기" if fin_prob >= 2 else "장기"

def _calc_scores(conf, sim, impact, financial):
    base  = round(conf * min(float(sim or 0.5), 1.0), 4)
    final = round(base * 0.35 + impact["impact_score"] * 0.35 + financial["financial_score"] * 0.30, 4)
    return final, base


# ── Ollama 분석 ───────────────────────────────────────────────────
def _ollama_analyze(text: str) -> dict:
    try:
        resp = httpx.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": OLLAMA_SYSTEM},
                {"role": "user",   "content": f"분석할 텍스트:\n{text}"}
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1}
        }, timeout=120)
        resp.raise_for_status()
        data = json.loads(resp.json()["message"]["content"])

        pol  = data.get("polarity", "negative")
        if pol not in ("positive", "negative"):
            pol = "negative"
        conf = max(0.5, min(0.95, float(data.get("confidence", 0.68))))

        fin_scale = int(data.get("fin_scale", 1))
        fin_prob  = int(data.get("fin_prob",  1))
        scale     = int(data.get("scale",     1))
        scope     = int(data.get("scope",     1))
        prob      = int(data.get("probability", 1))
        irrev     = int(data.get("irreversibility", 1))

        return {
            "polarity":        pol,
            "confidence":      conf,
            "scale":           scale,
            "scope":           scope,
            "probability":     prob,
            "irreversibility": irrev,
            "impact_score":    round((prob*0.30 + scale*0.30 + scope*0.20 + irrev*0.20) / 3.0 * conf, 4),
            "fin_scale":       fin_scale,
            "fin_prob":        fin_prob,
            "financial_score": round((fin_scale*0.60 + fin_prob*0.40) / 3.0 * conf, 4),
            "time_horizon":    data.get("time_horizon", "단기"),
            "_text":           text,
        }
    except Exception as e:
        print(f"  [Ollama 오류] {e}")
        raise
        # ── 규칙 기반 fallback (비활성화) ──────────────────────────
        # pol, conf = _rule_predict(text)
        # if pol == "neutral":
        #     pol, conf = "negative", 0.55
        # impact    = _rule_impact(text, conf)
        # financial = _rule_financial(text, conf)
        # return {
        #     "polarity": pol, "confidence": conf,
        #     "scale": impact["scale"], "scope": impact["scope"],
        #     "probability": impact["probability"], "irreversibility": impact["irreversibility"],
        #     "impact_score": impact["impact_score"],
        #     "fin_scale": financial["fin_scale"], "fin_prob": financial["fin_prob"],
        #     "financial_score": financial["financial_score"],
        #     "time_horizon": _time_horizon(text, financial["fin_prob"]),
        #     "_text": text,
        # }


# ── 스키마 ────────────────────────────────────────────────────────
class PredictReq(BaseModel):
    text: str = Field(..., example="현대모비스 리콜 50만대, 충당부채 200억 설정")

class PredictRes(BaseModel):
    polarity:   str
    confidence: float
    backend:    str

class PredictDetailRes(BaseModel):
    polarity:        str
    confidence:      float
    scale:           int
    scope:           int
    probability:     int
    irreversibility: int
    impact_score:    float
    fin_scale:       int
    fin_prob:        int
    fin_effect:      int
    fin_year:        int
    financial_score: float
    time_horizon:    str
    direction:       str
    iro:             str
    backend:         str

class AnalyzeReq(BaseModel):
    db_url:  str           = Field(..., example="postgresql://postgres:1234@192.168.0.106:5432/postgres")
    schema:  str           = Field(default="public",     example="public")
    table:   str           = Field(default="esg_chunks", example="esg_chunks")
    limit:   Optional[int] = Field(default=None, example=100)
    offset:  Optional[int] = Field(default=None, example=0)
    id_from: Optional[int] = Field(default=None, example=1)
    id_to:   Optional[int] = Field(default=None, example=1000)
    order:   str           = Field(default="asc", description="asc / desc / random")
    domain:  Optional[str] = Field(default=None, example="E")
    export:  Optional[bool]= Field(default=True)

class IROItem(BaseModel):
    idx:             int
    db_id:           Optional[int]
    iro:             str
    time_horizon:    str
    direction:       str
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
    fin_prob:        int
    financial_score: float

class AnalyzeRes(BaseModel):
    total:          int
    기회_단기_cnt:   int
    기회_장기_cnt:   int
    리스크_단기_cnt: int
    리스크_장기_cnt: int
    기회_score:     float
    리스크_score:   float
    backend:        str
    elapsed_sec:    float
    csv_file:       Optional[str]
    items:          list[IROItem]


# ── 엔드포인트 ────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "backend": _backend, "model": OLLAMA_MODEL}


@app.post("/predict", response_model=PredictRes)
def predict(req: PredictReq):
    res = _ollama_analyze(req.text)
    return PredictRes(polarity=res["polarity"], confidence=res["confidence"], backend=_backend)


@app.post("/predict/detail", response_model=PredictDetailRes, summary="단일 텍스트 전체 점수 분석")
def predict_detail(req: PredictReq):
    res       = _ollama_analyze(req.text)
    pol       = res["polarity"]
    horizon   = res["time_horizon"]
    direction = "기회" if pol == "positive" else "리스크"
    iro       = f"{direction}_{horizon}"
    return PredictDetailRes(
        polarity=pol,
        confidence=res["confidence"],
        scale=res["scale"],
        scope=res["scope"],
        probability=res["probability"],
        irreversibility=res["irreversibility"],
        impact_score=res["impact_score"],
        fin_scale=res["fin_scale"],
        fin_prob=res["fin_prob"],
        fin_effect=res["fin_prob"],
        fin_year=res["fin_prob"],
        financial_score=res["financial_score"],
        time_horizon=horizon,
        direction=direction,
        iro=iro,
        backend=_backend,
    )


@app.post("/analyze", response_model=AnalyzeRes)
def analyze(req: AnalyzeReq):
    import time
    from urllib.parse import urlparse

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
    sel  = [c for c in cols if c != "chunk_embedding"]

    where_parts, params = [], []
    if req.domain:
        where_parts.append("issue_group_domain ILIKE %s"); params.append(f"%{req.domain}%")
    if req.id_from is not None:
        where_parts.append("id >= %s"); params.append(req.id_from)
    if req.id_to is not None:
        where_parts.append("id <= %s"); params.append(req.id_to)
    w_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    order_lower = req.order.lower()
    if order_lower == "random":
        order_sql = "ORDER BY RANDOM()"
    else:
        order_dir = "ASC" if order_lower == "asc" else "DESC"
        order_col = "id" if "id" in cols else (cols[0] if cols else "id")
        order_sql = f"ORDER BY {order_col} {order_dir}"

    page_sql = " ".join(
        ([f"LIMIT {req.limit}"]  if req.limit  is not None else []) +
        ([f"OFFSET {req.offset}"] if req.offset is not None else [])
    )

    sql = f"SELECT {', '.join(sel)} FROM {req.schema}.{req.table} {w_sql} {order_sql} {page_sql}"
    print(f"  [쿼리] {sql[:120]}  params={params}")
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()

    ID_CANDIDATES = ["id", "chunk_id", "doc_id", "record_id", "uid"]
    id_col = next((c for c in ID_CANDIDATES if c in cols), cols[0] if cols else None)

    t0, n, results = time.time(), len(rows), []
    print(f"  분석 시작: {n}건  (백엔드: {_backend})")

    for i, r in enumerate(rows):
        raw_chunk = r.get("chunk")
        text      = str(raw_chunk).strip()[:400] if raw_chunk is not None else ""
        ig        = str(r.get("issue_group") or "")
        domain    = str(r.get("issue_group_domain") or "")
        sub_nm    = str(r.get("sub_issue_name") or "")
        sim       = float(r.get("best_similarity_score") or 0.5)
        raw_id    = r.get(id_col) if id_col else None
        try:    db_id = int(raw_id) if raw_id is not None else None
        except: db_id = None

        res       = _ollama_analyze(text)
        pol       = res["polarity"]
        conf      = res["confidence"]
        horizon   = res["time_horizon"]
        direction = "기회" if pol == "positive" else "리스크"
        iro       = f"{direction}_{horizon}"
        fs, bs    = _calc_scores(conf, sim, res, res)

        results.append(IROItem(
            idx=i+1, db_id=db_id,
            iro=iro, time_horizon=horizon, direction=direction,
            final_score=fs, base_score=bs,
            impact_score=res["impact_score"],
            scale=res["scale"], scope=res["scope"],
            probability=res["probability"], irreversibility=res["irreversibility"],
            polarity=pol, confidence=conf, similarity=sim,
            issue_group=ig, domain=domain, sub_issue_name=sub_nm, text=text,
            fin_scale=res["fin_scale"], fin_prob=res["fin_prob"],
            financial_score=res["financial_score"],
        ))

    elapsed  = round(time.time() - t0, 2)
    g_short  = [r for r in results if r.iro == "기회_단기"]
    g_long   = [r for r in results if r.iro == "기회_장기"]
    r_short  = [r for r in results if r.iro == "리스크_단기"]
    r_long   = [r for r in results if r.iro == "리스크_장기"]
    opp_all  = g_short + g_long
    risk_all = r_short + r_long
    opp_sc   = round(sum(r.final_score for r in opp_all)  / n, 4) if n else 0
    risk_sc  = round(sum(r.final_score for r in risk_all) / n, 4) if n else 0

    csv_file = None
    if req.export:
        import csv
        csv_file = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        fields = ["idx","db_id","iro","time_horizon","direction","final_score","base_score",
                  "impact_score","scale","scope","probability","irreversibility",
                  "fin_scale","fin_prob","financial_score","polarity","confidence",
                  "similarity","issue_group","domain","sub_issue_name","text"]
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in results:
                w.writerow({field: getattr(r, field) for field in fields})

    return AnalyzeRes(
        total=n,
        기회_단기_cnt=len(g_short), 기회_장기_cnt=len(g_long),
        리스크_단기_cnt=len(r_short), 리스크_장기_cnt=len(r_long),
        기회_score=opp_sc, 리스크_score=risk_sc,
        backend=_backend, elapsed_sec=elapsed,
        csv_file=csv_file, items=results,
    )


@app.get("/download/{filename}")
def download(filename: str):
    if not filename.endswith(".csv") or "/" in filename:
        raise HTTPException(status_code=400, detail="잘못된 파일명")
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="파일 없음")
    return FileResponse(filename, media_type="text/csv", filename=filename)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)
