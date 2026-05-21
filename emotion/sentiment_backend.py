"""
sentiment_backend.py  — 백엔드 추상화 레이어
────────────────────────────────────────────────────────────────
실행 환경에 따라 자동으로 백엔드를 선택합니다.

  로컬 (인터넷 O)  →  KR-FinBert-SC  (HuggingFace)
  샌드박스/오프라인 →  규칙 기반 엔진  (동일 인터페이스)

모든 상위 스크립트는 이 파일만 import 합니다.
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Literal

PolarityType = Literal["positive", "negative", "neutral"]

LABEL_MAP = {
    "positive": "positive", "negative": "negative", "neutral": "neutral",
    "LABEL_0": "negative", "LABEL_1": "neutral", "LABEL_2": "positive",
}

# ── 규칙 기반 엔진 (오프라인 fallback) ───────────────────────
NEG_TERMS = {
    "리콜":3, "사고":3, "위반":3, "과태료":3, "소송":3, "처분":3,
    "유출":3, "결함":2, "피해":2, "논란":2, "취약":2, "의혹":2,
    "불안정":2, "우려":2, "지연":1, "손해":2, "침해":2, "부채":1,
    "높아":1, "2배":1,
}
POS_TERMS = {
    "달성":3, "감소":2, "개선":3, "강화":2, "구축":2, "확대":2,
    "선언":1, "도입":2, "절감":2, "증가":2, "신설":2, "운영":1,
    "목표":1, "A등급":3, "확립":2, "성과":2,
}
MIT_TERMS = {"개선", "대응", "완화", "보완", "패치", "예방", "목표"}


def _rule_predict(text: str) -> tuple[PolarityType, float, dict]:
    neg_score = sum(w for t, w in NEG_TERMS.items() if t in text)
    pos_score = sum(w for t, w in POS_TERMS.items() if t in text)
    mit_score = sum(1 for t in MIT_TERMS if t in text)

    neg_score = max(0, neg_score - mit_score)

    if neg_score == 0 and pos_score == 0:
        polarity, conf = "neutral", 0.68
    elif neg_score > pos_score * 1.5:
        base = min(0.65 + neg_score * 0.06, 0.95)
        polarity, conf = "negative", round(base, 4)
    elif pos_score > neg_score * 1.5:
        base = min(0.65 + pos_score * 0.06, 0.95)
        polarity, conf = "positive", round(base, 4)
    else:
        if neg_score >= pos_score:
            polarity, conf = "negative", round(0.58 + neg_score * 0.02, 4)
        else:
            polarity, conf = "positive", round(0.58 + pos_score * 0.02, 4)

    remain = 1.0 - conf
    if polarity == "negative":
        scores = {"negative": conf, "neutral": round(remain*0.6,4), "positive": round(remain*0.4,4)}
    elif polarity == "positive":
        scores = {"positive": conf, "neutral": round(remain*0.6,4), "negative": round(remain*0.4,4)}
    else:
        scores = {"neutral": conf, "negative": round(remain*0.5,4), "positive": round(remain*0.5,4)}

    return polarity, conf, scores


# ── HuggingFace 백엔드 ────────────────────────────────────────
_hf_pipe = None

def _try_load_hf():
    global _hf_pipe
    try:
        from transformers import pipeline, logging as hf_log
        hf_log.set_verbosity_error()
        _hf_pipe = pipeline(
            "text-classification",
            model="snunlp/KR-FinBert-SC",
            return_all_scores=True,
            device=-1, truncation=True, max_length=512,
        )
        return True
    except Exception:
        return False


def _hf_predict(text: str) -> tuple[PolarityType, float, dict]:
    raw = _hf_pipe(text[:512])

    # pipeline 출력 형식 정규화
    # return_all_scores=True  → [[{"label":..,"score":..}, ...]]  (리스트의 리스트)
    # 일부 버전                → [{"label":..,"score":..}]         (리스트의 딕셔너리)
    if isinstance(raw, list) and len(raw) > 0:
        inner = raw[0]
        if isinstance(inner, dict):
            # 단일 best 결과만 반환된 경우
            raw_list = [inner]
        elif isinstance(inner, list):
            # 전체 scores 반환된 경우
            raw_list = inner
        else:
            raw_list = raw
    else:
        raw_list = raw

    best       = max(raw_list, key=lambda x: x["score"])
    polarity   = LABEL_MAP.get(best["label"], "neutral")
    confidence = round(best["score"], 4)
    scores     = {LABEL_MAP.get(r["label"], r["label"]): round(r["score"], 4)
                  for r in raw_list}
    return polarity, confidence, scores


# ── 공개 API ─────────────────────────────────────────────────
_backend: str = "rule"

def init_backend(force_rule: bool = False) -> str:
    global _backend
    if force_rule:
        _backend = "rule"
        print("📐 백엔드: 규칙 기반 엔진 (force_rule=True)")
        return _backend

    print("⏳ KR-FinBert-SC 로드 시도...")
    if _try_load_hf():
        _backend = "hf"
        print("✅ 백엔드: KR-FinBert-SC (HuggingFace)")
    else:
        _backend = "rule"
        print("📐 백엔드: 규칙 기반 엔진 (HuggingFace 접근 불가)")
    return _backend


def predict(text: str) -> tuple[PolarityType, float, dict]:
    """polarity, confidence, all_scores 반환"""
    if _backend == "hf":
        return _hf_predict(text)
    return _rule_predict(text)