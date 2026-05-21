"""
02_csv_eval.py — CSV 전체 정확도 평가
사용법: python 02_csv_eval.py --csv esg_sentiment_dataset.csv
"""
import csv, argparse
from collections import defaultdict
import sentiment_backend as sb

parser = argparse.ArgumentParser()
parser.add_argument("--csv",       default="esg_sentiment_dataset.csv")
parser.add_argument("--threshold", type=float, default=0.70)
args = parser.parse_args()

backend = sb.init_backend()
print(f"\n📂 파일: {args.csv}  |  임계값: {args.threshold}  |  백엔드: [{backend}]\n")

with open(args.csv, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

ICON = {"positive":"🟢","negative":"🔴","neutral":"⚪"}
correct, wrong, low_conf = 0, [], []
by_sub = defaultdict(list)

print(f"{'No':>3}  {'상태'} {'정답':<10} {'예측':<10} {'신뢰도'} {'sub_issue':<25} 텍스트")
print("-"*95)

for i, row in enumerate(rows):
    text = row["text"]
    gold = row["label"]
    sub  = row.get("sub_issue_hint","")
    polarity, conf, _ = sb.predict(text)

    ok = polarity == gold
    if ok: correct += 1
    else:  wrong.append({"i":i+1,"text":text,"gold":gold,"pred":polarity,"conf":conf})
    if conf < args.threshold:
        low_conf.append({"i":i+1,"text":text,"gold":gold,"pred":polarity,"conf":conf})
    by_sub[sub].append({"ok":ok,"conf":conf})

    flag = "✅" if ok else "❌"
    print(f"{i+1:>3}  {flag}  {ICON[gold]}{gold:<9} {ICON[polarity]}{polarity:<9} {conf:.3f}  {sub:<25} {text[:38]}")

acc = correct/len(rows)*100
llm_rate = len(low_conf)/len(rows)*100

print("\n" + "="*70)
print("📊 평가 요약")
print("="*70)
print(f"  샘플 수      : {len(rows)}건")
print(f"  정확도       : {correct}/{len(rows)} = {acc:.1f}%")
print(f"  LLM 위임 예상: {len(low_conf)}건 ({llm_rate:.0f}%)  conf < {args.threshold}")
print(f"  오분류       : {len(wrong)}건")

if wrong:
    print("\n── 오분류 케이스 ───────────────────────────────────────────")
    for w in wrong:
        print(f"  [{w['i']:02d}] {ICON[w['gold']]}→{ICON[w['pred']]}  conf={w['conf']:.3f}")
        print(f"       {w['text']}")

if low_conf:
    print("\n── LLM fallback 대상 ───────────────────────────────────────")
    for c in low_conf:
        print(f"  [{c['i']:02d}] conf={c['conf']:.3f}  {c['text'][:55]}")

print("\n── sub_issue별 정확도 ──────────────────────────────────────")
for sub, items in sorted(by_sub.items()):
    a   = sum(1 for x in items if x["ok"])/len(items)*100
    avg = sum(x["conf"] for x in items)/len(items)
    warn = "⚠️ " if a < 75 else "  "
    print(f"  {warn}{sub:<30} acc={a:5.1f}%  avg_conf={avg:.3f}  n={len(items)}")
