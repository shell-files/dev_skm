"""
03_a4_agent.py — DMA v6 A4 Agent 3단 파이프라인
사용법:
    python 03_a4_agent.py
    python 03_a4_agent.py --text "원하는 텍스트"
    python 03_a4_agent.py --csv esg_sentiment_dataset.csv
"""
from __future__ import annotations
import argparse, csv, time
from dataclasses import dataclass, asdict
from typing import Literal
import sentiment_backend as sb

PolarityType = Literal["positive","negative","neutral"]
IROType      = Literal["risk","opportunity","negative_impact","positive_impact","context"]
TimeHorizon  = Literal["short","mid","long"]
Method       = Literal["tree","model","llm"]

@dataclass
class A4Output:
    text:         str
    polarity:     PolarityType
    iro_type:     IROType
    time_horizon: TimeHorizon
    confidence:   float
    method:       Method
    latency_ms:   float
    note:         str = ""

NEG_TERMS = {"리콜","사고","위반","과태료","소송","처분","유출","결함","피해","논란","취약","의혹","불안정","우려","침해"}
POS_TERMS = {"달성","감소","개선","강화","구축","확대","선언","도입","절감","증가","신설","목표","A등급"}
MIT_TERMS = {"개선","대응","완화","보완","패치","예방","목표"}
SHORT_TERMS = {"즉각","즉시","긴급","당일","올해","이번 분기","패치"}
LONG_TERMS  = {"2040","2050","넷제로","로드맵","중장기","전략","10년","20년"}

def _tree(text: str) -> tuple[PolarityType|None, float]:
    neg = sum(1 for t in NEG_TERMS if t in text)
    pos = sum(1 for t in POS_TERMS if t in text)
    mit = sum(1 for t in MIT_TERMS if t in text)
    net_neg = max(0, neg - mit)

    if net_neg >= 2 and pos == 0: return "negative", 0.92
    if net_neg >= 1 and pos == 0: return "negative", 0.82
    if pos >= 2 and net_neg == 0: return "positive", 0.90
    if pos >= 1 and net_neg == 0: return "positive", 0.80
    if neg == 0 and pos == 0:     return "neutral",  0.72
    return None, 0.0   # 혼합 → 모델로

def _iro(text: str, pol: PolarityType) -> IROType:
    if pol == "negative":
        return "risk" if any(t in text for t in {"소송","처분","과태료","결함","위반"}) else "negative_impact"
    if pol == "positive":
        return "opportunity" if any(t in text for t in {"수주","확대","전환","기대","목표"}) else "positive_impact"
    return "context"

def _time(text: str) -> TimeHorizon:
    if any(t in text for t in SHORT_TERMS): return "short"
    if any(t in text for t in LONG_TERMS):  return "long"
    return "mid"

def _llm_stub(text: str) -> tuple[PolarityType, float]:
    # TODO: 실제 LLM 연결
    # from anthropic import Anthropic
    # client = Anthropic()
    # res = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=10,
    #     messages=[{"role":"user","content":f"감정을 positive/negative/neutral 중 하나만: {text}"}])
    # return res.content[0].text.strip(), 0.65
    return "neutral", 0.55

METHOD_WEIGHT = {"tree":1.00, "model":0.88, "llm":0.80}  # A5 Calibrator용

def run_a4(text: str, threshold: float = 0.70) -> A4Output:
    t0 = time.perf_counter()

    # 1단계: 결정트리
    pol, conf = _tree(text)
    if pol and conf >= 0.85:
        ms = round((time.perf_counter()-t0)*1000, 1)
        return A4Output(text, pol, _iro(text,pol), _time(text), conf, "tree", ms, "결정트리 처리")

    # 2단계: 감정분석 모델
    pol_m, conf_m, _ = sb.predict(text)
    calibrated = round(conf_m * METHOD_WEIGHT["model"], 4)
    if calibrated >= threshold:
        ms = round((time.perf_counter()-t0)*1000, 1)
        return A4Output(text, pol_m, _iro(text,pol_m), _time(text), calibrated, "model", ms,
                        f"KR-FinBert-SC raw={conf_m:.3f} → calib={calibrated:.3f}")

    # 3단계: LLM fallback
    pol_l, conf_l = _llm_stub(text)
    ms = round((time.perf_counter()-t0)*1000, 1)
    return A4Output(text, pol_l, _iro(text,pol_l), _time(text), conf_l, "llm", ms,
                    f"모델 calib={calibrated:.3f} < {threshold} → LLM")

# ── CLI ──────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--text",      default=None)
parser.add_argument("--csv",       default=None)
parser.add_argument("--threshold", type=float, default=0.70)
args = parser.parse_args()

backend = sb.init_backend()
M_ICON = {"tree":"🌲","model":"🤖","llm":"💬"}
P_ICON = {"positive":"🟢","negative":"🔴","neutral":"⚪"}

if args.csv:
    with open(args.csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    texts = [r["text"] for r in rows]
else:
    texts = [args.text] if args.text else [
        "현대모비스, 리콜 50만대 실시 - 충당부채 200억원 설정",
        "HL만도 온실가스 배출량 전년 대비 15% 감소 달성",
        "탄소중립 로드맵 발표했으나, 구체적 실행 계획 미흡 지적",
        "사이버 보안 취약점 발견, 긴급 패치 배포",
        "기후변화로 인한 원자재 공급망 불안정, 원가 상승 우려",
    ]

print(f"\n{'='*75}")
print(f" A4 Agent  3단 파이프라인  |  백엔드: [{backend}]  |  threshold={args.threshold}")
print(f"{'='*75}")
print(f"{'텍스트':<42} {'극성':<10} {'IRO':<22} {'시간'} {'방법'} {'신뢰도'} {'ms'}")
print("-"*95)

tree_c, model_c, llm_c = 0, 0, 0
for text in texts:
    o = run_a4(text, args.threshold)
    if o.method=="tree":  tree_c+=1
    elif o.method=="model": model_c+=1
    else: llm_c+=1
    short = text[:40]+"…" if len(text)>42 else text
    print(f"{short:<42} {P_ICON[o.polarity]}{o.polarity:<9} {o.iro_type:<22} "
          f"{o.time_horizon:<5} {M_ICON[o.method]}{o.method:<6} {o.confidence:.3f}  {o.latency_ms}")

print("-"*95)
n = len(texts)
print(f"  처리: 🌲결정트리 {tree_c}건({tree_c/n*100:.0f}%)  "
      f"🤖모델 {model_c}건({model_c/n*100:.0f}%)  "
      f"💬LLM {llm_c}건({llm_c/n*100:.0f}%)")
print(f"  ※ 결정트리+모델 처리율 = LLM 절감율: {(tree_c+model_c)/n*100:.0f}%")
