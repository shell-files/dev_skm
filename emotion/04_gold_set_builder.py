"""
04_gold_set_builder.py — Gold Set draft CSV 생성
사용법:
    python 04_gold_set_builder.py \
        --input  esg_sentiment_dataset.csv \
        --output gold_set_draft.csv
"""
import csv, argparse
import sentiment_backend as sb

parser = argparse.ArgumentParser()
parser.add_argument("--input",     default="esg_sentiment_dataset.csv")
parser.add_argument("--output",    default="gold_set_draft.csv")
parser.add_argument("--threshold", type=float, default=0.70)
args = parser.parse_args()

backend = sb.init_backend()
print(f"\n📂 {args.input}  →  {args.output}  |  백엔드: [{backend}]\n")

IRO_TIME = {"risk":"short","negative_impact":"mid","positive_impact":"mid",
            "opportunity":"long","context":"mid"}

FIELDS = ["chunk_id","text","label_gold","iro_type_gold","sub_issue_id",
          "polarity_pred","polarity_conf","all_scores",
          "issue_relevance","impact_relevance","financial_relevance",
          "signal_strength","time_horizon","rationale","evidence_spans",
          "review_needed","review_reason"]

with open(args.input, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

out_rows, needs_review = [], 0

print(f"{'No':>3}  {'상태'} {'gold':<10} {'pred':<10} {'신뢰도'}  텍스트")
print("-"*80)

for i, row in enumerate(rows):
    text  = row["text"]
    gold  = row["label"]
    iro   = row.get("iro_type","")
    sub   = row.get("sub_issue_hint","")

    pol, conf, scores = sb.predict(text)

    reasons = []
    if conf < args.threshold: reasons.append(f"낮은신뢰도({conf:.3f})")
    if pol != gold:            reasons.append(f"예측불일치({pol}≠{gold})")
    review = bool(reasons)
    if review: needs_review += 1

    icon = "⚠️ " if review else "✅ "
    PICON = {"positive":"🟢","negative":"🔴","neutral":"⚪"}
    print(f"{i+1:>3}  {icon}{PICON[gold]}{gold:<9} {PICON[pol]}{pol:<9} {conf:.3f}  {text[:42]}")

    out_rows.append({
        "chunk_id":            f"chunk_{i+1:04d}",
        "text":                text,
        "label_gold":          gold,
        "iro_type_gold":       iro,
        "sub_issue_id":        sub,
        "polarity_pred":       pol,
        "polarity_conf":       conf,
        "all_scores":          str(scores),
        "issue_relevance":     "",
        "impact_relevance":    "",
        "financial_relevance": "",
        "signal_strength":     "",
        "time_horizon":        IRO_TIME.get(iro,"mid"),
        "rationale":           "",
        "evidence_spans":      "",
        "review_needed":       "TRUE" if review else "FALSE",
        "review_reason":       " | ".join(reasons),
    })

with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(out_rows)

auto_ok = len(rows) - needs_review
print(f"""
{'='*60}
📋 Gold Set Draft 생성 완료: {args.output}
{'='*60}
  총 건수        : {len(rows)}건
  자동 확정 가능 : {auto_ok}건 ✅
  검토 필요      : {needs_review}건 ⚠️ (REVIEW_NEEDED=TRUE)

  ─ 컨설턴트 작업 순서 ──────────────────────────────
  ① review_needed=TRUE 행 polarity_pred 검토 · 수정
  ② 빈칸 필드 입력:
     issue_relevance     0.0~1.0
     impact_relevance    0~5
     financial_relevance 0~5
     signal_strength     0~5
     time_horizon        short/mid/long 재검토
     rationale           근거 서술
     evidence_spans      핵심 문구 발췌
  ③ 목표: 현재 {len(rows)}건 → 200건 이상 확장
  ─────────────────────────────────────────────────
  DMA 연결: Phase 2-C (W9-11) A4 에이전트 학습 데이터로 사용
{'='*60}
""")
