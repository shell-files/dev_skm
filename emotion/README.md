# DMA v6 감정분석 툴킷 (KR-FinBert-SC)

DMA v6 A4 Polarity/IRO/Time Agent에 KR-FinBert-SC를 연결하기 위한 코드 모음입니다.

## 파일 구성

| 파일 | 역할 | 먼저 실행? |
|------|------|-----------|
| `01_model_test.py` | 모델 로드 & 샘플 문장 테스트 | ✅ 먼저 |
| `02_csv_eval.py` | CSV 전체 정확도 평가 | 2번째 |
| `03_a4_agent.py` | DMA A4 3단 파이프라인 전체 | 3번째 |
| `04_gold_set_builder.py` | Gold Set draft CSV 생성 | 마지막 |

## 빠른 시작

```bash
# 1. 의존성 설치
pip install transformers torch sentencepiece

# 2. 모델 기본 테스트 (샘플 7문장)
python 01_model_test.py

# 3. CSV 전체 평가
python 02_csv_eval.py --csv esg_sentiment_dataset.csv

# 4. A4 에이전트 전체 파이프라인
python 03_a4_agent.py
python 03_a4_agent.py --text "원하는 텍스트 입력"

# 5. Gold Set draft 생성
python 04_gold_set_builder.py \
    --input  esg_sentiment_dataset.csv \
    --output gold_set_draft.csv
```

## 3단 파이프라인 흐름

```
텍스트 입력
    │
    ▼
[1단계] 결정트리 (키워드)
    │ conf ≥ 0.85 → 즉시 반환
    │ conf < 0.85 ↓
    ▼
[2단계] KR-FinBert-SC
    │ conf ≥ 0.70 → 반환
    │ conf < 0.70 ↓
    ▼
[3단계] LLM fallback (stub → 실제 API 연결 필요)
```

## 출력 스키마 (A4Output)

| 필드 | 타입 | 예시 |
|------|------|------|
| `polarity` | str | positive / negative / neutral |
| `iro_type` | str | risk / opportunity / negative_impact / positive_impact / context |
| `time_horizon` | str | short / mid / long |
| `confidence` | float | 0.0 ~ 1.0 |
| `method` | str | tree / model / llm |
| `latency_ms` | float | 처리 시간 (ms) |

## DMA v6 연결 포인트

- **A4 통합**: `03_a4_agent.py`의 `run_a4()` 함수를 A4 에이전트에 직접 임포트
- **A5 연동**: `method` 필드로 source_multiplier 보정
  - tree=1.00, model=0.88, llm=0.80
- **Gold Set**: `04_gold_set_builder.py` 결과물을 컨설턴트 라벨링 후 Phase 2-C 학습에 사용

## LLM Fallback 연결 방법

`03_a4_agent.py`의 `_llm_fallback()` 함수에서 주석 해제:

```python
import anthropic
client = anthropic.Anthropic()

def _llm_fallback(text: str):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": f"다음 ESG 텍스트의 감정을 positive/negative/neutral 중 하나로만 답하시오: {text}"}]
    )
    polarity = response.content[0].text.strip().lower()
    return polarity, 0.65
```

## 참고: DMA 문서 연결 섹션

- `01_model_test.py` → Part 3.3 Polarity 결정트리
- `02_csv_eval.py`   → Part 5.1.1 Gold Set 라벨링 스키마
- `03_a4_agent.py`   → Part 2.3 A4 에이전트 입출력 스키마
- `04_gold_set_builder.py` → Part 5.1.1 + 1.1절 gold set seed
