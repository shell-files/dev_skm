"""
01_model_test.py — 모델 로드 & 기본 테스트
"""
import sentiment_backend as sb

print("=" * 65)
print(" DMA v6  KR-FinBert-SC  — 기본 테스트")
print("=" * 65)

backend = sb.init_backend()
print()

samples = [
    ("현대모비스, 리콜 50만대 실시 - 충당부채 200억원 설정",       "negative"),
    ("HL만도 온실가스 배출량 전년 대비 15% 감소 달성",             "positive"),
    ("한온시스템, 산업재해율 업계 평균 대비 2배 높아 논란",         "negative"),
    ("위아 ESG 위원회 신설, 이사회 내 독립적 감독 체계 구축",       "positive"),
    ("탄소중립 로드맵 발표했으나, 구체적 실행 계획 미흡 지적",      "negative"),
    ("기후변화로 인한 원자재 공급망 불안정, 원가 상승 우려",        "negative"),
    ("이사회 내 여성 비율 25% 달성, 다양성 강화",                  "positive"),
]

ICON = {"positive":"🟢","negative":"🔴","neutral":"⚪"}
correct = 0

print(f"{'텍스트':<44} {'정답':<10} {'예측':<10} {'신뢰도'}")
print("-" * 65)
for text, gold in samples:
    polarity, conf, scores = sb.predict(text)
    ok = "✅" if polarity == gold else "❌"
    if polarity == gold: correct += 1
    short = text[:42] + ".." if len(text) > 44 else text
    print(f"{short:<44} {ICON[gold]}{gold:<9} {ok}{ICON[polarity]}{polarity:<8} {conf:.3f}")

print("-" * 65)
print(f"정확도: {correct}/{len(samples)} ({correct/len(samples)*100:.0f}%)")
print(f"백엔드: [{backend}]")
print()
print("▶ 상세 점수 (첫 2개):")
for text, _ in samples[:2]:
    p, c, s = sb.predict(text)
    print(f"  {text[:45]}")
    print(f"    → {s}")
