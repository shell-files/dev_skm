# DMA v6: 이중중대성 평가 점수화 멀티에이전트 운영 설계안

작성일: 2026-05-18
대상: ESG 보고서 자동 생성 플랫폼 (esg_sr_harness)
선행 문서: DMA v5 / Atomic Master v4.4 / Keyword Dictionary v4.3
포지셔닝: **Phase 2 진입 의사결정 검토안 (D-006 후보)**

---

## 0. 이 문서의 목적

DMA v5의 점수화 로직(Financial/Impact 분리, polarity-IRO-time, 산식)을 **AI 멀티에이전트가 운영 환경에서 분류 + 점수화 + 비교 + 선정을 수행할 수 있는 수준**으로 고도화한다.

특히 사용자 요구는 다음 세 가지다.

```text
요구 1. 멀티에이전트가 서브이슈를 분류할 때, 점수 영향도까지 함께 제시한다.
요구 2. Benchmark / Media / Survey 3단계 점수를 비교해 최종 sub_issue를 선정한다.
요구 3. 위 둘이 "실무 운영 수준"으로 동작해야 한다 (PoC 아님).
```

이를 만족하려면 v5의 "이래야 한다"는 규범 문서를 "어떻게 그렇게 하는지"의 실행 문서로 바꿔야 한다.

---

## 0.1 GitHub repo와의 정합성 (중요)

`esg_sr_harness`의 결정 로그에는 다음 두 결정이 있다.

- **D-004**: Graph DB 후순위
- **D-005**: Phase 1 핵심 4축은 KPI 정확성 / Evidence 품질 / Sub-topic 구조 / Prompt 통제 설계
- **00_core_principles §8**: Phase 1에서 멀티 에이전트 병렬 구조는 **구현 금지**

따라서 본 문서는 다음과 같이 명시적으로 포지셔닝한다.

```text
본 문서는 Phase 2 entry decision(=D-006 후보)을 위한 설계 검토안이다.
Phase 1의 KPI 정확성 / Evidence 품질 / Sub-topic 구조 / Prompt 통제 4축이
검증된 후에 단계적으로 적용한다.
멀티에이전트를 단번에 다 켜는 것이 아니라,
Classifier → Scorer → Polarity → Calibrator → Judge 순으로 한 명씩 도입한다.
```

이 원칙은 본문 전체에서 일관되게 따른다.

---

# Part 1. 현황 진단

## 1.1 현재 보유 자산 (Asset Inventory)

| 자산 | 위치 | 운영 가치 | 비고 |
|---|---|---|---|
| 62개 sub_issue 사전 (keyword/sentence/negative_keyword) | `07_..._Dictionary_v4_3 / 02_SubIssue_Keyword_Dict` | **상** | 분류기 학습 즉시 활용 가능 |
| `scoring_axis_allowed` 컬럼 | 동 사전 | **최상** | sub_issue마다 허용 점수축 메타데이터 — negative constraint로 즉시 사용 가능 |
| `embedding_text` 컬럼 | 동 사전 `08_RAG_Export` | **상** | RAG retriever에 그대로 인덱싱 |
| 16개 scoring_axis (governance_quality, financial_risk, transition_risk, …) | 동 사전 | **상** | 점수화 라벨 공간 확정 |
| `ontology_relation_path` (IssueGroup→SubIssue→Metric→Atomic) | 동 사전 | **중** | 점수 → metric 자동 연결 가능 |
| Impact/Financial Rubric (0~5) | `DMA_v4 / 03,04 시트` | **상** | LLM 프롬프트 그대로 사용 가능 |
| Polarity × IRO × Time horizon × urgency multiplier 매트릭스 | `DMA_v4 / 05` | **상** | 결정 트리화 |
| Source multiplier 테이블 (regulation 1.0 / DART 0.9 / SR 0.85 / expert 0.7 / news 0.5) | `DMA_v4 / 06` | **상** | 즉시 적용 |
| 자동차부품 driver map | `DMA_v4 / 11` | **중** | 업종 weight 보정용 |
| 현대모비스/HL만도/한온/위아 간이 검증셋 | `DMA_v4 / 12` | **중** | gold set seed |
| `dma_benchmark_signal` / `dma_media_signal` / `dma_final_score` DB 필드 정의 | `DMA_v4 / 13` | **상** | DDL 즉시 생성 가능 |
| 62개 synthetic Agent Test Set | `사전 / 09` | **하** | 형태만 있고 실제 사용 수준 X — 재구축 필요 |
| 905개 atomic_metric / 246개 metric / dimension_table 구조 | `Atomic_Master_v4_4` | **상** | score→fact 연결 인프라 |

## 1.2 운영 단계 도달까지의 Gap

| Gap | 의미 | 영향 |
|---|---|---|
| 에이전트별 R&R 미정의 | 분류·점수화·polarity·confidence를 한 LLM에 몰아 시킴 | 5-layer 원칙 위배. trace 불가 |
| 6개 점수 변수의 산출 알고리즘 미정 | `sub_issue_similarity`, `financial_relevance` 등이 식만 있고 어떻게 뽑는지 불명확 | 점수 재현성 X |
| Prompt 템플릿 부재 | planner/architect/reviewer만 있고 도메인 에이전트 프롬프트 없음 | 일관성 X |
| `scoring_axis_allowed`의 강제 미사용 | 메타데이터는 있는데 시스템이 안 씀 | hallucination 가능 |
| 3단계(Benchmark/Media/Survey) 비교 로직 부재 | 가중합 공식만 있고 conflict resolution 없음 | "왜 선정/탈락?" 설명 불가 |
| CTX modifier의 산식 부재 | CTX는 modifier로 쓴다는 원칙만 있고 곱셈식 정의 없음 | 실제로는 무시되거나 직접 점수로 들어감 |
| Confidence / abstention 기준 부재 | 모호한 chunk에도 점수 부여 | calibration error 누적 |
| Gold set 부족 | synthetic 62개 + 간이검증 6개뿐 | precision/recall 측정 불가 |
| Trace JSON 스펙 부재 | scoring_result에 trace 컬럼은 있는데 형식 없음 | drill-down UI 불가 |
| Judge / Human-in-the-Loop 미설계 | 검토 단계 없음 | 운영 위험 |

이 Gap을 메우는 것이 **Part 2~7**의 내용이다.

---

# Part 2. 멀티에이전트 아키텍처

## 2.1 설계 원칙

```text
원칙 1. 한 에이전트는 한 가지 책임만 진다 (single responsibility).
원칙 2. 모든 에이전트의 입력과 출력은 JSON schema로 고정한다.
원칙 3. 모든 점수에는 trace_json이 따라붙는다 (어떤 chunk에서, 어떤 근거로 나왔는지).
원칙 4. 각 단계 사이에 게이트(gate)가 있다 — confidence/coverage가 임계치 미만이면 다음 단계로 못 간다.
원칙 5. Judge 에이전트는 산식이 아니라 규칙 위반을 잡는다 (scoring_axis_allowed 위반, polarity 모순 등).
원칙 6. Human-in-the-Loop가 항상 마지막에 있다.
```

## 2.2 6개 에이전트와 R&R

```
┌─────────────────────────────────────────────────────────────────────────┐
│  INPUT: source_chunk (news / SR / DART / KIS / KCGS / survey response) │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────┐
        │ A1. Retriever Agent                         │
        │   - 임베딩 + 키워드 hit                       │
        │   - sub_issue 후보군 top-K (K=5)             │
        │   - sub_issue_similarity (0~1) 산출          │
        └─────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────┐
        │ A2. Classifier Agent                        │
        │   - 후보군 중 정답 sub_issue 1~3개 선택        │
        │   - issue_relevance (0~1) 산출               │
        │   - negative_keyword 적용                    │
        │   - scoring_axis_allowed로 라벨 공간 제약     │
        └─────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────┐
        │ A3. Scorer Agent (Impact + Financial)       │
        │   - Rubric(0~5)으로 impact_relevance,        │
        │     financial_relevance 산출                 │
        │   - signal_strength 산출                     │
        │   - 각 점수에 인용 근거 첨부                  │
        └─────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────┐
        │ A4. Polarity / IRO / Time Agent             │
        │   - polarity (pos/neg/neu)                  │
        │   - iro_type (risk/opp/pos_imp/neg_imp/ctx) │
        │   - time_horizon (short/mid/long)           │
        │   - mitigation_terms 적용                   │
        └─────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────┐
        │ A5. Calibrator Agent                        │
        │   - source_multiplier 곱                     │
        │   - confidence 계산                          │
        │   - urgency_multiplier 적용                  │
        │   - chunk_magnitude 최종 산출                │
        └─────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────┐
        │ A6. Judge Agent (Rule-based + LLM critic)   │
        │   - scoring_axis_allowed 위반 차단           │
        │   - polarity-IRO 모순 차단                   │
        │   - confidence 임계 통과 여부                │
        │   - 통과 시 chunk_score 확정, 실패 시 HITL   │
        └─────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────┐
        │ AGGREGATOR (deterministic Python, not LLM)  │
        │   - sub_issue × stage 단위로 bucket 누적     │
        │   - benchmark/media/survey 단계별 stage_score│
        │   - final_financial / final_impact / priority│
        └─────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────┐
        │ Stage Comparator + Selector (Part 4)        │
        │   - 3단계 일치도 / conflict resolution        │
        │   - 최종 sub_issue 선정                       │
        └─────────────────────────────────────────────┘
                                  │
                                  ▼
                            HITL Review
```

**중요한 설계 결정**: Aggregator와 Stage Comparator는 **LLM이 아니라 deterministic Python**으로 만든다. 산식은 결정적이어야 하고, 재현 가능해야 한다. LLM은 자연어 chunk를 라벨/숫자로 바꾸는 일까지만 한다.

## 2.3 각 에이전트의 입출력 스키마

### A1. Retriever Agent

```python
# input
{
  "chunk_id": "CHK_20250318_001",
  "chunk_text": "...본문...",
  "source_type": "news",   # news / SR / DART / regulation / KIS / KCGS / survey
  "company_id": "C_HMOBIS",
  "industry_code": "auto_parts"
}

# output
{
  "chunk_id": "CHK_20250318_001",
  "candidates": [
    {"sub_issue_id": "S_PRODUCT_SAFETY__리콜_품질",
     "similarity": 0.91,
     "keyword_hits": ["리콜", "결함", "보증"],
     "embedding_score": 0.87},
    {"sub_issue_id": "G_LEGAL_COMPLIANCE",
     "similarity": 0.42, ...},
    ...
  ],
  "negative_keyword_hits": [],   # 비어있어야 통과
  "abstain": false
}
```

산출 방법:

```python
similarity = 0.6 * embedding_cosine(chunk_emb, sub_issue_emb)
           + 0.4 * keyword_jaccard(chunk_tokens, sub_issue_keywords)

# negative_keyword가 hit하면 후보에서 제외
if any(nk in chunk_text for nk in sub_issue.negative_keywords):
    drop_candidate()
```

게이트:
- top1 similarity < 0.35 → `abstain=true` (Classifier에 안 넘김)
- top1과 top2 차이 < 0.05 → `requires_classifier=true` (ambiguous flag)

### A2. Classifier Agent

```python
# input
{
  "chunk_id": "...",
  "chunk_text": "...",
  "candidates": [...top-K with similarity...],
}

# output
{
  "chunk_id": "...",
  "classified_sub_issues": [
    {"sub_issue_id": "S_PRODUCT_SAFETY__리콜_품질",
     "issue_relevance": 0.92,
     "rationale": "본문에 '대규모 리콜', '충당부채 200억원' 등 직접 명시",
     "evidence_spans": [{"start": 42, "end": 78, "text": "..."}]
    }
  ],
  "allowed_axes": ["legal_risk", "consumer_safety_risk", "financial_risk", "negative_impact"],
  // ↑ 분류된 sub_issue들의 scoring_axis_allowed 합집합. 이후 단계는 이 안에서만 점수화.
  "confidence": 0.88
}
```

핵심: **`allowed_axes`를 출력에 명시**해서 다음 에이전트(Scorer)가 라벨 공간을 벗어나지 못하게 한다.

### A3. Scorer Agent (Impact + Financial)

```python
# input
{
  "chunk_text": "...",
  "classified_sub_issues": [...],
  "allowed_axes": [...]
}

# output
{
  "scores": [
    {
      "sub_issue_id": "S_PRODUCT_SAFETY__리콜_품질",
      "impact_relevance": 4,         # 0~5 Impact rubric
      "impact_rubric_match": "범위·반복성 큼 (다수 차량 영향)",
      "financial_relevance": 5,      # 0~5 Financial rubric
      "financial_rubric_match": "기업가치 훼손 가능 (대규모 리콜+고객 신뢰)",
      "signal_strength": 4,          # 0~5
      "signal_evidence": ["충당부채 200억", "리콜 50만대"],
      "confidence_raw": 0.85
    }
  ]
}
```

게이트:
- `impact_relevance == 0` AND `financial_relevance == 0` → drop chunk
- 둘 다 점수가 있는데 인용 근거(evidence) 없음 → Judge에서 reject

### A4. Polarity / IRO / Time Agent

```python
# input
{
  "chunk_text": "...",
  "scores": [...],
  "allowed_axes": [...]
}

# output
{
  "labels": [
    {
      "sub_issue_id": "S_PRODUCT_SAFETY__리콜_품질",
      "polarity": "negative",
      "iro_type": "risk",              # risk / opportunity / negative_impact / positive_impact / context
      "time_horizon": "short",         # short / mid / long
      "polarity_trigger_terms": ["리콜", "결함"],
      "mitigation_terms_found": [],
      "intensity_terms": ["대규모", "200억"],
      "decision_path": "negative_triggers(2) > mitigation(0); intensity high; immediate event → short"
    }
  ]
}
```

A4는 **결정 트리 + LLM 동시 적용**. 결정 트리가 명확히 답하면 LLM은 호출하지 않는다 (cost 절감).

```python
def polarity_decision_tree(chunk, sub_issue):
    neg_hits = count(chunk, sub_issue.negative_trigger_terms)
    pos_hits = count(chunk, sub_issue.positive_trigger_terms)
    mit_hits = count(chunk, sub_issue.mitigation_terms)

    if neg_hits >= 2 and mit_hits == 0:
        return "negative", confidence=0.9
    if pos_hits >= 2 and neg_hits == 0:
        return "positive", confidence=0.9
    if neg_hits == 0 and pos_hits == 0:
        return "neutral", confidence=0.7
    # 모호한 경우만 LLM
    return llm_polarity_classify(chunk, sub_issue), confidence=0.6
```

### A5. Calibrator Agent

LLM 아님. **순수 산식.**

```python
def calibrate(chunk_record):
    sm = SOURCE_MULTIPLIER[chunk_record.source_type]
    rec_weight = recency_weight(chunk_record.source_date)
    cr = company_relevance(chunk_record)
    conf = chunk_record.confidence_raw * source_quality_factor(chunk_record.source_type)

    chunk_financial_magnitude = (
        chunk_record.similarity *
        chunk_record.issue_relevance *
        chunk_record.financial_relevance *  # 0~5
        chunk_record.signal_strength *      # 0~5
        sm * rec_weight * cr * conf
    )
    chunk_impact_magnitude = (
        chunk_record.similarity *
        chunk_record.issue_relevance *
        chunk_record.impact_relevance *
        chunk_record.signal_strength *
        sm * rec_weight * cr * conf
    )

    urgency = URGENCY_MULTIPLIER[(chunk_record.polarity, chunk_record.iro_type, chunk_record.time_horizon)]

    return ChunkScore(
        financial_magnitude=chunk_financial_magnitude,
        impact_magnitude=chunk_impact_magnitude,
        urgency_multiplier=urgency,
        confidence_final=conf,
        # bucket 할당
        bucket=resolve_bucket(chunk_record.polarity, chunk_record.iro_type)
    )
```

### A6. Judge Agent

규칙 기반 검증을 먼저 돌리고, 통과 시 LLM critic이 sanity check.

**Rule-based checks (Python, fail → reject):**

1. `iro_type ∈ classified_sub_issue.scoring_axis_allowed` 위반 여부
2. `polarity == "negative"` 인데 `iro_type ∈ {opportunity, positive_impact}` 모순
3. `polarity == "positive"` 인데 `iro_type ∈ {risk, negative_impact}` 모순
4. `confidence_final < 0.5` → HITL queue
5. `signal_strength >= 4` 인데 `evidence_spans` 비어있음 → reject
6. CTX_* sub_issue가 직접 final_score 계산에 들어가려 함 → reject (modifier로만 사용)

**LLM critic (통과한 chunk만):**

```text
SYSTEM: You are a DMA scoring auditor. Given:
- chunk_text
- assigned sub_issue
- impact_relevance, financial_relevance, polarity, iro_type
Identify any of:
- relevance overestimate (typical sign: weak language, single mention)
- relevance underestimate (typical sign: explicit financial figures present)
- polarity flip (mitigation terms ignored)
Return JSON: {"verdict": "pass" | "revise" | "reject", "reason": "..."}
```

`revise` 시 점수를 ±1 보정하고 다시 Calibrator로 넘긴다 (최대 1회 루프).

## 2.4 단계 간 게이트 요약

| 게이트 | 통과 조건 | 실패 시 처리 |
|---|---|---|
| Retriever → Classifier | top1 similarity >= 0.35 | abstain (chunk drop, log) |
| Classifier → Scorer | issue_relevance >= 0.5 | abstain |
| Scorer → Polarity | (impact_relevance + financial_relevance) >= 2 | drop |
| Polarity → Calibrator | polarity != "neutral" 또는 issue_relevance >= 0.8 | context_only bucket |
| Calibrator → Judge | 항상 통과 | — |
| Judge → Aggregator | rule pass + LLM verdict ∈ {pass, revise(1회)} | HITL queue |

## 2.5 왜 6개로 쪼개나? (자주 나오는 반론 대응)

```text
반론: "한 LLM에 한 번에 다 시키면 빠르고 cheap"
답변:
  - trace 불가능 (어디서 틀렸는지 모름)
  - scoring_axis_allowed 제약을 시스템이 강제 못함
  - 6개 출력 중 1개만 틀려도 전체 reject — debugging 비용 ↑
  - 단계별 게이트로 abstain하면 LLM call 30~50% 절감 가능
  - Phase 2 핵심 가치인 explainability/auditability가 무너짐
```

운영에서는 **Retriever (Agent 1)**과 **Calibrator (Agent 5)**는 LLM 호출이 거의 없거나 0회다. 실제 LLM 비용이 큰 건 Classifier / Scorer / Polarity / Judge 4개인데, 게이트로 abstain하면 후속 단계가 안 돌아간다.

---

# Part 3. 점수화 로직 운영 고도화

DMA v5가 "산식의 모양"을 정의했다면, v6는 그 산식에 들어가는 **6개 변수 각각이 어떻게 계산되는지의 알고리즘 명세**가 핵심이다.

## 3.1 6개 점수 변수의 산출 알고리즘

| 변수 | 범위 | 산출 주체 | 계산 방식 |
|---|---|---|---|
| `sub_issue_similarity` | 0~1 | Retriever | embedding cosine + keyword Jaccard 가중합 |
| `issue_relevance` | 0~1 | Classifier | LLM rubric 기반 + negative_keyword penalty |
| `impact_relevance` | 0~5 | Scorer | Impact Rubric 매칭 + evidence quality |
| `financial_relevance` | 0~5 | Scorer | Financial Rubric 매칭 + evidence quality |
| `signal_strength` | 0~5 | Scorer | event/figure/regulation 강도 점수 |
| `confidence` | 0~1 | Calibrator | 위 5개의 분산 + source quality |

### 3.1.1 sub_issue_similarity (Retriever)

```python
def sub_issue_similarity(chunk_text, sub_issue):
    # 1. Embedding cosine (사전의 embedding_text 사용)
    chunk_emb = embed(chunk_text)
    sub_emb = embed(sub_issue.embedding_text)
    emb_sim = cosine(chunk_emb, sub_emb)  # 0~1

    # 2. Keyword Jaccard (양쪽 키워드의 형태소 매칭)
    chunk_tokens = tokenize(chunk_text)
    kw_tokens = tokenize(sub_issue.keyword_kr + ";" + sub_issue.keyword_foreign_en)
    kw_jaccard = len(chunk_tokens & kw_tokens) / max(len(kw_tokens), 1)

    # 3. Negative keyword penalty
    neg_hit = any(nk in chunk_text for nk in sub_issue.negative_keyword_kr.split(';'))
    if neg_hit:
        return 0.0

    return 0.6 * emb_sim + 0.4 * min(kw_jaccard * 2, 1.0)
```

운영 팁:
- `sub_issue.embedding_text`는 이미 사전에 있다 (`08_RAG_Export` 시트). 별도 생성 X.
- 임베딩 모델은 한국어 강한 모델 사용 (예: `BAAI/bge-m3`, `intfloat/multilingual-e5-large`).
- 임베딩은 pgvector에 캐싱. chunk 임베딩은 ingestion 단계에서 1회 계산.

### 3.1.2 issue_relevance (Classifier)

LLM에 다음 rubric을 준다:

```text
0.9~1.0: chunk가 sub_issue의 정의를 직접·구체적으로 다룸 (수치/사건/정책 등 명시)
0.7~0.9: chunk가 sub_issue를 명시적으로 언급하지만 깊이가 얕음
0.5~0.7: 같은 도메인이지만 sub_issue의 핵심 개념이 부분적으로만 등장
0.3~0.5: 같은 issue_group이지만 다른 sub_issue로 분류하는 게 더 정확
0.0~0.3: 관련 없음
```

LLM 출력 후 후처리:

```python
# negative_keyword가 본문에 있으면 페널티
if neg_keyword_hit:
    issue_relevance *= 0.3

# sentence 패턴이 매우 강하게 hit하면 보정
if sub_issue.sentence_pattern_match_score >= 0.8:
    issue_relevance = max(issue_relevance, 0.7)
```

### 3.1.3 impact_relevance / financial_relevance (Scorer)

Rubric을 LLM에 그대로 system prompt로 넣는다 (이미 사전에 정의됨, `DMA_v4/03,04` 시트).

```text
SYSTEM:
당신은 ESG 이중중대성 평가의 Scorer입니다.
다음 Impact Rubric을 사용하여 0~5 점수를 부여하세요.

[Impact Rubric]
0: 영향 없음 (단순 사업 소개, 조직도)
1: 간접·약한 영향 (관리체계, 정책 존재, 선언 수준)
2: 잠재 영향 가능성 (직접 피해 없으나 가능성 있음)
3: 실제 운영 영향 (회사 운영·제품·공급망에서 실제 영향)
4: 범위·반복성 큼 (다수 이해관계자·가치사슬·반복 노출)
5: 중대·회복 어려움 (인명·권리·환경에 중대하고 회복 어려운 영향)

[Financial Rubric] ... (위와 동일 패턴)

규칙:
- 점수를 부여한 근거 문구를 evidence_spans에 포함하세요.
- 본문에 명시되지 않은 추론은 금지합니다 (Evidence-first).
- 두 axis는 독립적으로 평가합니다.
- 둘 다 0이면 chunk는 폐기됩니다.

OUTPUT JSON:
{
  "impact_relevance": <int 0-5>,
  "impact_evidence": "<인용>",
  "impact_rubric_level": "<rubric 설명>",
  "financial_relevance": <int 0-5>,
  "financial_evidence": "<인용>",
  "financial_rubric_level": "<rubric 설명>",
  "signal_strength": <int 0-5>,
  "signal_evidence": ["<수치/사건>", ...]
}
```

### 3.1.4 signal_strength (Scorer)

별도 rubric:

```text
0: 사건·수치·규제·평가 없음
1: 약한 언급 (예: "관리하고 있습니다")
2: 구체적 활동 언급 (예: "분기별 점검")
3: 수치 또는 사건 1건 (예: "재해율 0.3%")
4: 다수의 수치/사건 또는 명확한 규제·등급 (예: "벌금 5억원 + 정부조사")
5: 중대 사건 + 규제 + 다수 출처 (예: "리콜 50만대 + 충당부채 200억 + DART 공시 + 언론 다수")
```

### 3.1.5 confidence (Calibrator)

```python
def confidence_final(chunk_record):
    # 1. 점수들의 일관성 (variance가 낮을수록 높은 신뢰)
    relevance_consistency = 1.0 - abs(
        chunk_record.impact_relevance - chunk_record.financial_relevance
    ) / 5.0

    # 2. polarity-iro 일치도
    polarity_iro_match = 1.0 if polarity_iro_consistent(chunk_record) else 0.5

    # 3. source quality
    src_q = SOURCE_QUALITY[chunk_record.source_type]  # 0.5~1.0

    # 4. evidence 존재 여부
    has_evidence = 1.0 if chunk_record.evidence_spans else 0.4

    return (
        0.3 * chunk_record.issue_relevance +
        0.2 * relevance_consistency +
        0.2 * polarity_iro_match +
        0.15 * src_q +
        0.15 * has_evidence
    )
```

## 3.2 scoring_axis_allowed 기반 제약 (Negative Constraint)

**핵심 통찰**: 사전에 있는 `scoring_axis_allowed`는 **negative constraint(허용된 축 외 라벨 부여 금지)**로 사용해야 한다.

```python
# 예: 기후 거버넌스 sub_issue
sub_issue.scoring_axis_allowed = {"governance_quality", "risk_management_maturity"}

# Polarity 에이전트가 "negative_impact" 라벨을 시도
if "negative_impact" not in sub_issue.scoring_axis_allowed:
    raise AxisViolation(
        f"sub_issue {sub_issue.id} does not allow 'negative_impact' axis. "
        f"Allowed: {sub_issue.scoring_axis_allowed}"
    )
    # → Judge가 reject. HITL queue에 들어감.
```

이 제약은 **시스템이 강제**한다 (LLM에 prompt로 넣는 것만으로는 부족, 코드 검증 필수).

### 3.2.1 16개 scoring_axis와 iro_type 매핑

```python
AXIS_TO_IRO = {
    "financial_risk":        {"risk"},
    "financial_opportunity": {"opportunity"},
    "transition_risk":       {"risk"},
    "physical_risk":         {"risk"},
    "legal_risk":            {"risk"},
    "negative_impact":       {"negative_impact"},
    "positive_impact":       {"positive_impact"},
    "consumer_safety_risk":  {"risk", "negative_impact"},
    "consumer_rights":       {"negative_impact"},
    "customer_trust":        {"risk", "opportunity"},
    "human_rights_risk":     {"risk", "negative_impact"},
    "community_impact":      {"negative_impact", "positive_impact"},
    "value_chain_risk":      {"risk", "negative_impact"},
    "governance_quality":    {"context", "risk"},
    "risk_management_maturity": {"context", "risk"},
    "target_progress":       {"opportunity", "context"},
}

def is_iro_allowed(sub_issue, iro_type):
    allowed_iros = set()
    for axis in sub_issue.scoring_axis_allowed:
        allowed_iros |= AXIS_TO_IRO.get(axis, set())
    return iro_type in allowed_iros
```

## 3.3 Polarity / IRO 결정 트리

이미 Part 2에서 의사코드를 보였지만, 운영 환경에서는 다음 표를 lookup으로 코드화한다.

| polarity | intensity terms 존재 | mitigation terms 존재 | scoring_axis_allowed에 risk/opp 둘 다 | 결과 iro_type |
|---|---|---|---|---|
| negative | Y | N | risk만 허용 | risk |
| negative | Y | N | negative_impact만 허용 | negative_impact |
| negative | Y | N | 둘 다 허용 | financial_relevance가 더 높으면 risk, 아니면 negative_impact |
| negative | Y | Y (mitigation 2+) | — | 점수 ×0.6 후 재평가 |
| positive | Y | — | opp만 허용 | opportunity |
| positive | Y | — | positive_impact만 허용 | positive_impact |
| positive | Y | — | 둘 다 허용 | financial_relevance가 더 높으면 opportunity, 아니면 positive_impact |
| neutral | — | — | context 허용 | context |
| neutral | — | — | context 미허용 | drop chunk |

## 3.4 Mixed / Multi-label 처리

한 chunk가 여러 sub_issue에 동시 매핑되는 것은 정상이다 (현실에서 자주 발생). 처리 규칙:

```python
# Classifier에서 issue_relevance >= 0.5인 sub_issue 모두 통과
for sub_issue in classified_sub_issues:
    # Scorer는 sub_issue별로 별도 점수 계산
    score = scorer.score(chunk, sub_issue)
    # 각 sub_issue의 fact row가 별도 생성됨
    save_chunk_score(chunk_id, sub_issue.id, score)

# Aggregator는 sub_issue × stage 단위로 합산
# → 한 chunk가 sub_issue A에 60점, sub_issue B에 40점 기여하는 형태 정상
```

**주의**: chunk_magnitude를 sub_issue 수로 나누지 않는다. 한 사건이 정말 두 이슈에 영향을 준 거라면 둘 다에 기여하는 게 맞다.

## 3.5 CTX modifier 처리 알고리즘

CTX_BUSINESS_MODEL / CTX_FINANCIAL_PRODUCTION 같은 컨텍스트 sub_issue는 **다른 sub_issue의 financial_relevance를 보정**하는 modifier 역할만 한다.

```python
def apply_ctx_modifier(target_sub_issue_score, company_ctx_signals):
    """
    company_ctx_signals = {
      "internal_combustion_dependency": 0.7,  # 0~1
      "ev_revenue_share": 0.1,                # 0~1
      "rnd_investment_capacity": 0.3,         # 0~1
      "customer_concentration": 0.8,          # 0~1
    }
    """
    modifier = 1.0

    if target_sub_issue.id == "E_CLIMATE_RISK":
        # 내연기관 의존도가 높을수록 climate risk financial이 커짐
        modifier *= (1 + 0.3 * company_ctx_signals["internal_combustion_dependency"])
        # EV 매출 비중이 높으면 risk 감소 / opportunity 증가
        modifier *= (1 - 0.2 * company_ctx_signals["ev_revenue_share"])

    if target_sub_issue.id in ["E_PRODUCT_ECO", "E_GREEN_INVESTMENT"]:
        # R&D 투자여력이 낮으면 opportunity 점수 감소
        modifier *= (0.5 + 0.5 * company_ctx_signals["rnd_investment_capacity"])

    if "_FINANCIAL" in target_sub_issue.id or "financial_risk" in target_sub_issue.scoring_axis_allowed:
        # 고객 집중도가 높으면 financial risk 증폭
        modifier *= (1 + 0.25 * company_ctx_signals["customer_concentration"])

    return target_sub_issue_score.financial_score * modifier
```

`company_ctx_signals`는 **온보딩 단계에서 입력**받거나 (KIS 방법론 기반), **DART 사업보고서 파싱**으로 자동 산출한다. Atomic Master에서 신규 atomic_metric_id (예: `CTX-01__A_EV_REVENUE_SHARE`)로 정의해 fact로 저장.

CTX sub_issue는 **final_financial_score 산출에 직접 포함되지 않고**, 다른 sub_issue 점수의 modifier로만 작용한다. 이건 코드로 강제한다:

```python
def compute_final_score(sub_issue):
    if sub_issue.id.startswith("CTX_"):
        raise NotApplicableError("CTX_* sub_issues are modifiers, not scored independently.")
```

## 3.6 trace JSON 스펙

모든 점수에는 trace_json이 따라붙는다. 보고서 explainability + audit log에 직접 사용.

```json
{
  "score_id": "SCORE_C_HMOBIS_2026_S_PRODUCT_SAFETY_v1",
  "computed_at": "2026-05-18T14:32:15Z",
  "score_version": "DMA_v6.0",
  "company_id": "C_HMOBIS",
  "assessment_year": 2026,
  "sub_issue_id": "S_PRODUCT_SAFETY__리콜_품질",
  "final_financial_score": 91.6,
  "final_impact_score": 88.8,
  "priority_score": 113.275,

  "components": {
    "benchmark": {
      "score_f": 88, "score_i": 82,
      "input_chunk_count": 14,
      "leader_frequency": 0.80, "peer_frequency": 0.86, "self_frequency": 0.40,
      "gap_score": 43, "trend_momentum": 1.0,
      "evidence_quality": 0.85,
      "top_chunks": ["CHK_2024_HMC_SR_p32", "CHK_2024_HL_SR_p28", ...]
    },
    "media": {
      "score_f": 92, "score_i": 90,
      "input_chunk_count": 27,
      "source_breakdown": {"news": 18, "regulation": 2, "DART": 5, "expert": 2},
      "polarity_breakdown": {"negative": 23, "positive": 1, "neutral": 3},
      "iro_breakdown": {"risk": 16, "negative_impact": 7, "context": 4},
      "top_chunks": ["CHK_20250318_001", ...]
    },
    "survey": {
      "score_f": 94, "score_i": 92,
      "respondent_count": 28,
      "respondent_groups": {"executive": 5, "employee": 12, "external": 11},
      "question_axis_breakdown": {"financial_high": 4.7, "impact_high": 4.5, "negative_short_risk": 4.8}
    }
  },

  "polarity_distribution": {
    "negative_count": 23, "positive_count": 1, "neutral_count": 3
  },
  "buckets": {
    "financial_risk_score": 78.2,
    "financial_opportunity_score": 3.4,
    "impact_negative_score": 85.1,
    "impact_positive_score": 3.7
  },
  "dominant_iro_type": "risk",
  "dominant_time_horizon": "short",
  "urgency_multiplier": 1.25,

  "ctx_modifiers_applied": [
    {"ctx_signal": "customer_concentration", "value": 0.8, "factor": 1.20}
  ],

  "agent_runs": [
    {"agent": "retriever", "version": "v1.0", "duration_ms": 120, "llm_calls": 0},
    {"agent": "classifier", "version": "v1.0", "duration_ms": 2300, "llm_calls": 14, "model": "claude-sonnet-4-6"},
    {"agent": "scorer", "version": "v1.0", "duration_ms": 5100, "llm_calls": 14},
    {"agent": "polarity", "version": "v1.0", "duration_ms": 1800, "llm_calls": 4},
    {"agent": "calibrator", "version": "v1.0", "duration_ms": 30, "llm_calls": 0},
    {"agent": "judge", "version": "v1.0", "duration_ms": 1200, "llm_calls": 14, "rejected_count": 2}
  ],

  "human_overrides": [],

  "linked_metrics": ["S5-04", "S5-06"],
  "linked_atomic_metrics": ["S5-04__A0331", "S5-04__E0008"]
}
```

이 trace는 보고서 UI의 drill-down에 그대로 사용된다. "이 sub_issue가 왜 1순위?" 질문에 chunk 단위까지 추적 가능.

---

# Part 4. 3단계 비교 및 sub_issue 선정 로직

DMA v5는 단순 가중합 (F = 0.30B + 0.30M + 0.40S) 공식만 정의했다. 운영 수준에서는 그것만으로는 **"왜 선정/탈락?"**의 설명이 약하다.

v6은 가중합 + **3단계 일치도 분석(Cross-Stage Concordance Analysis)**을 결합한다.

## 4.1 일치도 매트릭스

각 sub_issue에 대해 3단계 점수를 threshold로 이진화한 다음 패턴을 본다.

```python
def classify_concordance(bench_f, bench_i, media_f, media_i, survey_f, survey_i, T=60):
    bench_high = (bench_f >= T) or (bench_i >= T)
    media_high = (media_f >= T) or (media_i >= T)
    survey_high = (survey_f >= T) or (survey_i >= T)

    pattern = (bench_high, media_high, survey_high)

    return {
        (True, True, True):    "CONFIRMED",         # 3개 모두 high
        (True, True, False):   "EXTERNAL_DRIVEN",   # 외부는 강한데 내부 인식 약함 → 인식 격차
        (True, False, True):   "MEDIA_BLIND_SPOT",  # 미디어에 안 잡혔지만 동종업계+자사 둘 다 high
        (False, True, True):   "EMERGING",          # 자사 처음 인식, 미디어+설문 동조
        (True, False, False):  "PEER_ONLY",         # peer만 선정 — 자사에 진짜 해당하는지 재검토
        (False, True, False):  "MEDIA_HYPE",        # 미디어만 — 단발성 가능성, 신중 검토
        (False, False, True):  "INTERNAL_ONLY",     # 설문만 — 내부 자기방어 가능성, 외부 근거 보강 필요
        (False, False, False): "REJECTED",          # 어디서도 안 잡힘
    }[pattern]
```

이 패턴은 **선정 기준의 핵심**이 된다.

## 4.2 선정 규칙 (Selection Rule)

```python
def select_sub_issues(scored_sub_issues, target_count=10):
    """
    최종 선정 규칙:
    1. CONFIRMED는 자동 선정 (단, top N개 제한)
    2. EXTERNAL_DRIVEN / EMERGING은 priority_score 상위면 선정 + HITL 플래그
    3. MEDIA_BLIND_SPOT은 자동 선정 (자사가 인지하지만 PR 부족)
    4. PEER_ONLY는 자사 사업모델과의 적합성 검토 (HITL 필수)
    5. MEDIA_HYPE는 단발성 검증 후 결정 (HITL)
    6. INTERNAL_ONLY는 외부 근거 추가 수집 권고
    7. REJECTED는 제외
    """
    selected = []
    for s in sorted(scored_sub_issues, key=lambda x: x.priority_score, reverse=True):
        concordance = classify_concordance(...)

        if concordance == "CONFIRMED":
            selected.append((s, "auto_select", "3-stage agreement"))
        elif concordance == "MEDIA_BLIND_SPOT":
            selected.append((s, "auto_select", "self+peer agreement, low media"))
        elif concordance in {"EXTERNAL_DRIVEN", "EMERGING"}:
            if s.priority_score >= top_quartile_threshold:
                selected.append((s, "select_with_review", concordance))
        elif concordance == "PEER_ONLY":
            selected.append((s, "hitl_required", "peer-only signal"))
        elif concordance == "MEDIA_HYPE":
            selected.append((s, "hitl_required", "media-only spike"))
        elif concordance == "INTERNAL_ONLY":
            selected.append((s, "hitl_required", "needs external evidence"))
        # REJECTED는 selected에 들어가지 않음

        if count_auto_selected(selected) >= target_count:
            break

    return selected
```

## 4.3 임계치(Threshold) 자동 보정

target_count(예: top 10)와 도메인 균형(E:S:G ≥ 2:2:2)을 만족하도록 threshold T를 자동 보정한다.

```python
def auto_calibrate_threshold(all_scores, target_count=10, min_per_domain=2):
    # 1. T를 점진적으로 낮추며 selection 시뮬레이션
    for T in [70, 65, 60, 55, 50, 45]:
        selection = select_sub_issues(all_scores, threshold=T)
        n_auto = sum(1 for s in selection if s[1] == "auto_select")
        n_e = count_domain(selection, "E")
        n_s = count_domain(selection, "S")
        n_g = count_domain(selection, "G")
        if n_auto >= target_count and min(n_e, n_s, n_g) >= min_per_domain:
            return T, selection
    # 2. 그래도 안 되면 최저 T(45)로 + HITL 권고
    return 45, select_sub_issues(all_scores, threshold=45)
```

## 4.4 Conflict Resolution

3단계가 서로 충돌할 때(예: media는 negative risk라는데 survey는 positive opportunity), 다음 규칙:

```python
def resolve_iro_conflict(bench_iro, media_iro, survey_iro):
    # 1. 다수결
    votes = Counter([bench_iro, media_iro, survey_iro])
    most_common, count = votes.most_common(1)[0]
    if count >= 2:
        return most_common, "majority"

    # 2. 출처 신뢰도 가중 (media는 source_multiplier에서 이미 반영됨)
    # 동률이면 negative 우선 (보수적)
    if "risk" in [bench_iro, media_iro, survey_iro]:
        return "risk", "conservative_negative_priority"
    if "negative_impact" in [bench_iro, media_iro, survey_iro]:
        return "negative_impact", "conservative_negative_priority"

    # 3. 그래도 안 되면 "mixed"
    return "mixed", "no_consensus"
```

## 4.5 운영 산출물

최종 selection 결과는 다음 형태로 저장:

```json
{
  "selection_run_id": "SEL_C_HMOBIS_2026_v1",
  "company_id": "C_HMOBIS",
  "assessment_year": 2026,
  "threshold_used": 60,
  "selection": [
    {
      "rank": 1,
      "sub_issue_id": "S_PRODUCT_SAFETY__리콜_품질",
      "priority_score": 113.275,
      "final_financial_score": 91.6,
      "final_impact_score": 88.8,
      "dominant_iro_type": "risk",
      "concordance_pattern": "CONFIRMED",
      "selection_decision": "auto_select",
      "selection_reason": "3-stage agreement; negative/risk/short",
      "hitl_required": false,
      "linked_metrics": ["S5-04"],
      "trace_link": "SCORE_C_HMOBIS_2026_S_PRODUCT_SAFETY_v1"
    },
    {
      "rank": 2, ...
    }
  ],
  "rejected_with_reasons": [
    {
      "sub_issue_id": "G_BOARD_ESG",
      "concordance_pattern": "INTERNAL_ONLY",
      "selection_decision": "hitl_required",
      "reason": "설문만 high (4.2/5), 미디어/벤치마킹에서 근거 부족"
    }
  ]
}
```

---

# Part 5. 학습 데이터 & 평가 체계

운영 수준의 에이전트가 되려면 합당한 정답셋과 평가 메트릭이 필요하다. 현재 `09_Agent_Test_Set`은 synthetic 62개로, "실무 학습용"이라 보긴 어렵다.

## 5.1 Gold Set 구축 계획

3단계로 구축한다.

### 5.1.1 Stage 1: Seed Gold Set (200건 — 컨설턴트 라벨링)

| 구성 | 건수 | 출처 |
|---|---:|---|
| 자동차부품 peer SR 발췌 (모비스/만도/한온/위아) | 80 | 실제 보고서 PDF |
| DART 사업보고서 리스크 요인 발췌 | 40 | DART 공시 |
| 환경/안전 규제 위반 사례 (뉴스) | 30 | 언론 보도 |
| KCGS 등급 변동 코멘트 | 20 | KCGS 요약 |
| KIS 자동차부품 평가방법론 발췌 | 20 | KIS 방법론 |
| Hard negative (관련 없는 문단 — IT/금융/일반 뉴스) | 10 | 다른 산업 |

라벨링 스키마:

```json
{
  "chunk_id": "GOLD_001",
  "chunk_text": "...",
  "source_type": "SR",
  "company_id": "C_HMOBIS",
  "expected": {
    "sub_issues": [
      {
        "sub_issue_id": "S_PRODUCT_SAFETY__리콜_품질",
        "issue_relevance": 0.95,
        "impact_relevance": 4,
        "financial_relevance": 5,
        "signal_strength": 4,
        "polarity": "negative",
        "iro_type": "risk",
        "time_horizon": "short",
        "rationale": "본문 line 3에 '리콜 50만대 + 충당부채 200억' 명시"
      }
    ],
    "allowed_axes_check": ["legal_risk", "consumer_safety_risk", "financial_risk", "negative_impact"]
  },
  "labeler_id": "consultant_01",
  "labeled_at": "2026-06-01",
  "inter_annotator_agreement": 0.85   // 2명이 라벨 후 카파 계수
}
```

운영 팁:
- **2명 라벨 → Cohen's Kappa ≥ 0.7**인 chunk만 gold에 채택.
- 불일치 chunk는 3rd reviewer로 결정 (이 chunk들은 "hard cases" 풀로 별도 보관).

### 5.1.2 Stage 2: Active Learning Loop (200 → 500건)

운영 첫 분기 동안 에이전트가 자신 없어하는 chunk(`confidence < 0.7`)와 Judge가 reject한 chunk를 HITL queue로 보내고, 컨설턴트가 라벨링하여 gold set에 추가.

```python
def select_for_labeling(chunks_processed_last_week):
    candidates = []
    for c in chunks_processed_last_week:
        # 1. 낮은 confidence
        if c.confidence < 0.7:
            candidates.append((c, "low_confidence"))
        # 2. Judge가 reject
        if c.judge_verdict == "reject":
            candidates.append((c, "judge_reject"))
        # 3. axis_violation (allowed_axes 위반)
        if c.has_axis_violation:
            candidates.append((c, "axis_violation"))
        # 4. polarity conflict (3단계 간 불일치)
        if c.cross_stage_polarity_conflict:
            candidates.append((c, "polarity_conflict"))
    # 1주일에 50건씩만 sample (라벨링 capacity 제한)
    return stratified_sample(candidates, n=50)
```

이게 **데이터 plywheel**이다 — 운영하면서 gold set이 늘어나고, 모델/프롬프트가 점점 정확해진다.

### 5.1.3 Stage 3: Synthetic Augmentation (500 → 2000건)

기존 gold set에서 LLM으로 변형 chunk를 생성하되, 라벨은 유지.

```text
PROMPT: 다음 chunk와 같은 sub_issue, polarity, iro_type을 유지하면서
        다른 회사/연도/구체적 수치로 변형한 5가지 버전을 만들어라.
        sub_issue_id의 핵심 의미를 잃지 말아야 한다.
```

생성된 chunk는 별도 검증 (라벨이 유지되는지 sampling check) 후 채택.

## 5.2 평가 메트릭

| 단계 | 메트릭 | 합격선 (Phase 2 Entry) | 합격선 (운영) |
|---|---|---|---|
| Retriever | sub_issue_similarity Recall@5 | ≥ 0.85 | ≥ 0.92 |
| Classifier | sub_issue Precision (top-1) | ≥ 0.75 | ≥ 0.88 |
| Classifier | sub_issue F1 (multi-label) | ≥ 0.70 | ≥ 0.85 |
| Scorer | impact_relevance MAE (0~5) | ≤ 0.8 | ≤ 0.5 |
| Scorer | financial_relevance MAE | ≤ 0.8 | ≤ 0.5 |
| Scorer | signal_strength MAE | ≤ 0.9 | ≤ 0.6 |
| Polarity | polarity Accuracy | ≥ 0.85 | ≥ 0.92 |
| Polarity | iro_type Accuracy | ≥ 0.75 | ≥ 0.87 |
| Calibrator | Calibration Error (ECE) | ≤ 0.15 | ≤ 0.08 |
| Judge | False Reject Rate | ≤ 0.10 | ≤ 0.05 |
| End-to-End | sub_issue 선정 Top-10 IoU vs Gold | ≥ 0.60 | ≥ 0.80 |

**Phase 2 Entry**의 합격선은 **모든 메트릭이 entry 기준을 통과**해야 한다. 하나라도 미달이면 해당 에이전트만 따로 개선.

## 5.3 Inter-Stage Consistency 평가

3단계(B/M/S)의 결과가 서로 비교 가능하려면 같은 척도를 써야 한다.

```python
def inter_stage_consistency_metric(score_history):
    """
    각 sub_issue에 대해 B/M/S 점수의 분산을 본다.
    분산이 너무 크면 단계별 척도가 다른 것일 수 있음.
    """
    consistencies = []
    for sub_issue, scores in score_history.groupby("sub_issue_id"):
        b, m, s = scores[["bench_f", "media_f", "survey_f"]].mean()
        # 정규화된 분산 (max 100 기준)
        var = np.var([b, m, s]) / (100 ** 2)
        consistencies.append(var)
    avg_var = np.mean(consistencies)
    # 0.04 (= std dev 약 20점) 이하 권장
    return avg_var
```

## 5.4 Drift Monitoring

운영 중에는 다음을 매주 모니터링:

| 모니터링 항목 | 기준 |
|---|---|
| Confidence 분포 평균 | 0.75 이하로 떨어지면 alert |
| HITL queue 크기 | 주간 100건 초과 시 alert (라벨링 capacity 검토) |
| Axis violation rate | 1% 초과 시 alert (사전 업데이트 필요) |
| 단계별 source_type 분포 | 갑작스러운 변화 시 alert (예: news 비중 급증) |
| sub_issue별 priority_score 분산 (월간) | 표준편차 30 이상이면 alert (산식 안정성 의심) |

---

# Part 6. 데이터 모델 추가/확장

기존 `dma_benchmark_signal`, `dma_media_signal`, `dma_final_score`에 추가로 필요한 테이블.

## 6.1 신규 테이블

### 6.1.1 `agent_run` — 에이전트 실행 기록

```sql
CREATE TABLE agent_run (
    run_id              UUID PRIMARY KEY,
    chunk_id            VARCHAR(64) NOT NULL,
    agent_name          VARCHAR(32) NOT NULL,    -- retriever / classifier / scorer / polarity / calibrator / judge
    agent_version       VARCHAR(16) NOT NULL,
    model_name          VARCHAR(64),             -- claude-sonnet-4-6 / gpt-4o / null(deterministic)
    input_json          JSONB NOT NULL,
    output_json         JSONB NOT NULL,
    duration_ms         INTEGER,
    llm_calls           INTEGER DEFAULT 0,
    token_input         INTEGER,
    token_output        INTEGER,
    cost_usd            NUMERIC(10, 6),
    status              VARCHAR(16) NOT NULL,    -- success / failure / abstain / timeout
    error_message       TEXT,
    company_id          VARCHAR(32) NOT NULL,
    created_at          TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_agent_run_chunk ON agent_run(chunk_id);
CREATE INDEX idx_agent_run_agent_status ON agent_run(agent_name, status);
```

### 6.1.2 `chunk_classification` — Classifier 결과

```sql
CREATE TABLE chunk_classification (
    classification_id   UUID PRIMARY KEY,
    chunk_id            VARCHAR(64) NOT NULL,
    sub_issue_id        VARCHAR(64) NOT NULL,
    issue_relevance     NUMERIC(4, 3),           -- 0~1
    rationale           TEXT,
    evidence_spans      JSONB,                   -- [{"start":42, "end":78, "text":"..."}, ...]
    allowed_axes        TEXT[],                  -- 이 chunk가 다음 단계에서 받을 수 있는 axis들
    classifier_version  VARCHAR(16) NOT NULL,
    company_id          VARCHAR(32) NOT NULL,
    created_at          TIMESTAMP DEFAULT NOW(),
    UNIQUE (chunk_id, sub_issue_id, classifier_version)
);
```

### 6.1.3 `chunk_score_component` — Scorer 결과 (raw)

```sql
CREATE TABLE chunk_score_component (
    component_id        UUID PRIMARY KEY,
    chunk_id            VARCHAR(64) NOT NULL,
    sub_issue_id        VARCHAR(64) NOT NULL,
    -- Scorer 산출
    impact_relevance        SMALLINT NOT NULL CHECK (impact_relevance BETWEEN 0 AND 5),
    impact_evidence         TEXT,
    impact_rubric_level     VARCHAR(64),
    financial_relevance     SMALLINT NOT NULL CHECK (financial_relevance BETWEEN 0 AND 5),
    financial_evidence      TEXT,
    financial_rubric_level  VARCHAR(64),
    signal_strength         SMALLINT NOT NULL CHECK (signal_strength BETWEEN 0 AND 5),
    signal_evidence         TEXT[],
    -- Polarity Agent 산출
    polarity                VARCHAR(16) NOT NULL,    -- positive / negative / neutral
    iro_type                VARCHAR(32) NOT NULL,    -- risk / opportunity / negative_impact / positive_impact / context
    time_horizon            VARCHAR(8) NOT NULL,     -- short / mid / long
    polarity_decision_path  TEXT,
    -- Calibrator 산출
    source_multiplier       NUMERIC(4, 3),
    recency_weight          NUMERIC(4, 3),
    company_relevance       NUMERIC(4, 3),
    confidence_final        NUMERIC(4, 3),
    urgency_multiplier      NUMERIC(4, 3),
    chunk_financial_magnitude NUMERIC(10, 4),
    chunk_impact_magnitude    NUMERIC(10, 4),
    bucket                  VARCHAR(32) NOT NULL,    -- financial_risk / financial_opportunity / impact_negative / impact_positive / context
    -- Judge 산출
    judge_verdict           VARCHAR(16),             -- pass / revise / reject
    judge_reason            TEXT,
    axis_violation          BOOLEAN DEFAULT FALSE,
    polarity_iro_conflict   BOOLEAN DEFAULT FALSE,
    -- Audit
    score_version           VARCHAR(16) NOT NULL,
    company_id              VARCHAR(32) NOT NULL,
    assessment_year         INTEGER NOT NULL,
    source_type             VARCHAR(32) NOT NULL,    -- benchmark / media / survey (3 stages)
    created_at              TIMESTAMP DEFAULT NOW(),
    UNIQUE (chunk_id, sub_issue_id, score_version)
);

CREATE INDEX idx_csc_sub_issue_stage ON chunk_score_component(sub_issue_id, source_type, company_id, assessment_year);
CREATE INDEX idx_csc_company_year ON chunk_score_component(company_id, assessment_year);
```

### 6.1.4 `stage_score` — sub_issue × stage 단위 집계

```sql
CREATE TABLE stage_score (
    stage_score_id      UUID PRIMARY KEY,
    company_id          VARCHAR(32) NOT NULL,
    assessment_year     INTEGER NOT NULL,
    sub_issue_id        VARCHAR(64) NOT NULL,
    stage               VARCHAR(16) NOT NULL,        -- benchmark / media / survey
    -- 합산 결과
    financial_risk_score        NUMERIC(8, 3) DEFAULT 0,
    financial_opportunity_score NUMERIC(8, 3) DEFAULT 0,
    impact_negative_score       NUMERIC(8, 3) DEFAULT 0,
    impact_positive_score       NUMERIC(8, 3) DEFAULT 0,
    neutral_score               NUMERIC(8, 3) DEFAULT 0,
    -- 최종 stage score
    stage_financial_score   NUMERIC(8, 3) NOT NULL,  -- 0~100
    stage_impact_score      NUMERIC(8, 3) NOT NULL,
    -- 메타
    chunk_count             INTEGER NOT NULL,
    avg_confidence          NUMERIC(4, 3),
    dominant_iro_type       VARCHAR(32),
    dominant_time_horizon   VARCHAR(8),
    -- Audit
    score_version           VARCHAR(16) NOT NULL,
    computed_at             TIMESTAMP DEFAULT NOW(),
    UNIQUE (company_id, assessment_year, sub_issue_id, stage, score_version)
);
```

### 6.1.5 `concordance_analysis` — 3단계 일치도 분석

```sql
CREATE TABLE concordance_analysis (
    analysis_id             UUID PRIMARY KEY,
    company_id              VARCHAR(32) NOT NULL,
    assessment_year         INTEGER NOT NULL,
    sub_issue_id            VARCHAR(64) NOT NULL,
    -- 단계별 high/low (threshold 적용 결과)
    bench_high              BOOLEAN NOT NULL,
    media_high              BOOLEAN NOT NULL,
    survey_high             BOOLEAN NOT NULL,
    threshold_used          NUMERIC(5, 2) NOT NULL,
    -- 패턴
    concordance_pattern     VARCHAR(32) NOT NULL,    -- CONFIRMED / EXTERNAL_DRIVEN / ...
    -- IRO 충돌
    bench_iro_type          VARCHAR(32),
    media_iro_type          VARCHAR(32),
    survey_iro_type         VARCHAR(32),
    resolved_iro_type       VARCHAR(32),
    iro_resolution_method   VARCHAR(64),             -- majority / conservative / no_consensus
    computed_at             TIMESTAMP DEFAULT NOW(),
    UNIQUE (company_id, assessment_year, sub_issue_id)
);
```

### 6.1.6 `selection_result` — 최종 선정

```sql
CREATE TABLE selection_result (
    selection_id            UUID PRIMARY KEY,
    selection_run_id        VARCHAR(64) NOT NULL,
    company_id              VARCHAR(32) NOT NULL,
    assessment_year         INTEGER NOT NULL,
    sub_issue_id            VARCHAR(64) NOT NULL,
    rank                    INTEGER,
    priority_score          NUMERIC(8, 3) NOT NULL,
    final_financial_score   NUMERIC(8, 3) NOT NULL,
    final_impact_score      NUMERIC(8, 3) NOT NULL,
    dominant_iro_type       VARCHAR(32),
    dominant_time_horizon   VARCHAR(8),
    concordance_pattern     VARCHAR(32),
    selection_decision      VARCHAR(32) NOT NULL,    -- auto_select / select_with_review / hitl_required / rejected
    selection_reason        TEXT,
    hitl_required           BOOLEAN DEFAULT FALSE,
    hitl_completed          BOOLEAN DEFAULT FALSE,
    hitl_decision           VARCHAR(32),             -- approve / override_select / override_reject
    hitl_reviewer_id        VARCHAR(32),
    hitl_decided_at         TIMESTAMP,
    -- 연결
    linked_metric_ids       TEXT[],
    linked_atomic_metric_ids TEXT[],
    trace_link              VARCHAR(64),             -- chunk_score_component 참조
    -- Audit
    score_version           VARCHAR(16) NOT NULL,
    created_at              TIMESTAMP DEFAULT NOW(),
    UNIQUE (selection_run_id, sub_issue_id)
);
```

## 6.2 기존 테이블 확장

`dma_final_score`에 다음 컬럼 추가:

```sql
ALTER TABLE dma_final_score ADD COLUMN concordance_pattern VARCHAR(32);
ALTER TABLE dma_final_score ADD COLUMN ctx_modifiers_applied JSONB;
ALTER TABLE dma_final_score ADD COLUMN agent_runs_summary JSONB;
ALTER TABLE dma_final_score ADD COLUMN human_overrides JSONB;
```

## 6.3 핵심 View

### View 1: `v_sub_issue_score_overview` (UI용)

```sql
CREATE VIEW v_sub_issue_score_overview AS
SELECT
    fs.company_id,
    fs.assessment_year,
    fs.sub_issue_id,
    si.sub_issue_name_kr,
    si.domain,
    fs.final_financial_score,
    fs.final_impact_score,
    fs.priority_score,
    fs.dominant_iro_type,
    fs.dominant_time_horizon,
    ca.concordance_pattern,
    sr.selection_decision,
    -- 단계별 점수
    bs.stage_financial_score AS bench_f,
    bs.stage_impact_score AS bench_i,
    ms.stage_financial_score AS media_f,
    ms.stage_impact_score AS media_i,
    ss.stage_financial_score AS survey_f,
    ss.stage_impact_score AS survey_i
FROM dma_final_score fs
JOIN sub_issue_master si ON fs.sub_issue_id = si.sub_issue_id
LEFT JOIN concordance_analysis ca USING (company_id, assessment_year, sub_issue_id)
LEFT JOIN selection_result sr USING (company_id, assessment_year, sub_issue_id)
LEFT JOIN stage_score bs ON bs.stage='benchmark' AND bs.company_id=fs.company_id
                         AND bs.assessment_year=fs.assessment_year
                         AND bs.sub_issue_id=fs.sub_issue_id
LEFT JOIN stage_score ms ON ms.stage='media' AND ms.company_id=fs.company_id
                         AND ms.assessment_year=fs.assessment_year
                         AND ms.sub_issue_id=fs.sub_issue_id
LEFT JOIN stage_score ss ON ss.stage='survey' AND ss.company_id=fs.company_id
                         AND ss.assessment_year=fs.assessment_year
                         AND ss.sub_issue_id=fs.sub_issue_id;
```

### View 2: `v_chunk_drill_down` (Explainability용)

```sql
CREATE VIEW v_chunk_drill_down AS
SELECT
    csc.chunk_id,
    csc.sub_issue_id,
    si.sub_issue_name_kr,
    csc.source_type,
    csc.impact_relevance,
    csc.financial_relevance,
    csc.polarity,
    csc.iro_type,
    csc.time_horizon,
    csc.chunk_financial_magnitude,
    csc.chunk_impact_magnitude,
    csc.confidence_final,
    csc.judge_verdict,
    cl.evidence_spans,
    cl.rationale,
    ar.duration_ms,
    ar.cost_usd
FROM chunk_score_component csc
JOIN chunk_classification cl USING (chunk_id, sub_issue_id)
JOIN agent_run ar ON ar.chunk_id = csc.chunk_id AND ar.agent_name='classifier'
JOIN sub_issue_master si ON csc.sub_issue_id = si.sub_issue_id;
```

## 6.4 API contract (FastAPI)

### `POST /api/dma/v6/score-chunk`

```python
# Request
{
  "chunk_id": "CHK_20250318_001",
  "chunk_text": "...",
  "source_type": "news",
  "company_id": "C_HMOBIS",
  "assessment_year": 2026
}

# Response (sync — 단일 chunk는 약 5-15초)
{
  "chunk_id": "CHK_20250318_001",
  "status": "scored",   // scored / abstained / rejected / hitl_queued
  "classifications": [
    {
      "sub_issue_id": "S_PRODUCT_SAFETY__리콜_품질",
      "issue_relevance": 0.92,
      "scores": {
        "impact_relevance": 4, "financial_relevance": 5, "signal_strength": 4,
        "polarity": "negative", "iro_type": "risk", "time_horizon": "short",
        "chunk_financial_magnitude": 87.4, "chunk_impact_magnitude": 78.2,
        "confidence_final": 0.85, "bucket": "financial_risk"
      },
      "judge_verdict": "pass"
    }
  ],
  "trace_id": "..."
}
```

### `POST /api/dma/v6/recompute-sub-issue`

```python
# 특정 sub_issue의 stage_score, final_score, concordance를 재계산
{
  "company_id": "C_HMOBIS",
  "assessment_year": 2026,
  "sub_issue_id": "S_PRODUCT_SAFETY__리콜_품질",
  "stages_to_recompute": ["benchmark", "media", "survey"]
}
```

### `POST /api/dma/v6/run-selection`

```python
{
  "company_id": "C_HMOBIS",
  "assessment_year": 2026,
  "target_count": 10,
  "min_per_domain": {"E": 2, "S": 2, "G": 2}
}
# Response
{
  "selection_run_id": "SEL_C_HMOBIS_2026_v1",
  "threshold_used": 60,
  "selected_count": 10,
  "hitl_required_count": 3,
  "selection_url": "/app/dma/selection/SEL_C_HMOBIS_2026_v1"
}
```

---

# Part 7. 구현 로드맵

D-006 의사결정으로 Phase 2 진입 시, 다음 순서로 구현한다.

## 7.1 Phase 2-A: Foundation (4주)

목표: 데이터 plywheel 시작

| 주차 | 작업 | 산출물 |
|---|---|---|
| W1 | Gold Seed Set 200건 라벨링 (자동차부품 peer SR 80건 + DART/news/KCGS) | gold_set_v1.jsonl |
| W2 | `agent_run` / `chunk_classification` / `chunk_score_component` DDL + 마이그레이션 | DB ready |
| W3 | Retriever Agent 구현 (LLM 없음, embedding+keyword만) | A1 v1.0 |
| W4 | Phase 2-A 검증 — Recall@5 ≥ 0.85 | go/no-go |

## 7.2 Phase 2-B: Classifier + Scorer (4주)

| 주차 | 작업 | 산출물 |
|---|---|---|
| W5 | Classifier Agent 프롬프트 작성 + few-shot 20개 | A2 v0.1 |
| W6 | Scorer Agent 프롬프트 (Impact + Financial rubric 주입) | A3 v0.1 |
| W7 | gold set으로 Classifier/Scorer 평가 → 미달이면 프롬프트 개선 반복 | metrics report |
| W8 | Phase 2-B 검증 — Classifier P@1 ≥ 0.75, Scorer MAE ≤ 0.8 | go/no-go |

## 7.3 Phase 2-C: Polarity + Calibrator + Judge (3주)

| 주차 | 작업 | 산출물 |
|---|---|---|
| W9 | Polarity Agent (결정트리 + LLM fallback) | A4 v0.1 |
| W10 | Calibrator (deterministic Python) + Judge Agent | A5/A6 v0.1 |
| W11 | End-to-end pipeline test on 100 hold-out chunks | pipeline ready |

## 7.4 Phase 2-D: Aggregator + Concordance + Selector (3주)

| 주차 | 작업 | 산출물 |
|---|---|---|
| W12 | Aggregator (sub_issue × stage 단위 집계) | aggregator v1.0 |
| W13 | Concordance Analysis + Selection Logic | selector v1.0 |
| W14 | HITL UI (Streamlit/React) — selection_result 검토/오버라이드 | HITL app |

## 7.5 Phase 2-E: Monitoring + Active Learning Loop (2주, 그리고 지속)

| 주차 | 작업 | 산출물 |
|---|---|---|
| W15 | Drift monitoring dashboard (Grafana / Metabase) | monitoring dash |
| W16 | Active Learning queue (low confidence → HITL → gold set 자동 추가) | AL pipeline |

## 7.6 Phase Entry/Exit Criteria

| Phase | 진입 조건 | 종료 조건 |
|---|---|---|
| 2-A | D-006 승인 + Phase 1 KPI 정확성 합격 | Gold seed 200건 + Retriever Recall@5 ≥ 0.85 |
| 2-B | Phase 2-A 종료 | Classifier P@1 ≥ 0.75, Scorer MAE ≤ 0.8 |
| 2-C | Phase 2-B 종료 | Polarity Acc ≥ 0.85, Judge FRR ≤ 0.10 |
| 2-D | Phase 2-C 종료 + 100 hold-out test 통과 | E2E IoU vs Gold ≥ 0.60 |
| 2-E | Phase 2-D 종료 | 운영 4주간 metrics drift 없음 |

## 7.7 우선 구현 컴포넌트 (Critical Path)

```text
Week 1-4 (Phase 2-A) → Retriever만 먼저 가동
  → 이미 Phase 1에서 chunk가 있으면, Retriever로 사람 라벨링 작업 효율 ↑
  → "이 chunk는 어떤 sub_issue 후보들인가?" 추천 UI를 컨설턴트에게 제공
Week 5-8 (Phase 2-B) → Classifier + Scorer 추가
  → 이때부터 자동 분류·점수화의 가치가 보이기 시작
Week 9-11 (Phase 2-C) → Polarity + Calibrator + Judge
  → 운영 품질 확보
Week 12-14 (Phase 2-D) → Aggregator + Selector
  → 최종 selection까지 자동화
Week 15-16+ (Phase 2-E) → Monitoring + Active Learning
  → 시간이 갈수록 좋아지는 시스템
```

각 Phase 종료 후 D-007, D-008, ... 으로 의사결정 기록을 남긴다.

---

# Part 8. 운영 체크리스트 요약

## 8.1 Phase 2 진입 직전 (D-006 회의 안건)

- [ ] Phase 1 KPI 정확성 / Evidence 품질 / Sub-topic 구조 / Prompt 통제 4축 합격 여부 확인
- [ ] Gold Seed Set 200건 라벨링 capacity 확보 (컨설턴트 2명 × 2주)
- [ ] LLM 비용 예산 확정 (chunk 1만건 처리 기준 약 $300-500/월 예상)
- [ ] pgvector 인덱스 운영 준비 (현재 미구축 시 별도 작업)
- [ ] HITL UI 운영 인원 확보 (검토자 1명, 주 20시간)

## 8.2 운영 중 매주 체크

- [ ] HITL queue 처리율 (목표: 신규 유입의 95% 이상)
- [ ] Confidence 평균이 0.75 이상 유지
- [ ] Axis violation rate < 1%
- [ ] Source diversity (단일 source에 50% 이상 의존 금지)
- [ ] Cost per chunk가 예산 내 유지

## 8.3 분기마다

- [ ] Gold set 라벨 카파 ≥ 0.7 유지 (drift 점검)
- [ ] 평가 메트릭이 운영 기준을 만족 (Part 5.2)
- [ ] 프롬프트 / threshold / urgency_multiplier 등 파라미터 튜닝 회의
- [ ] 새 산업/지역 확장 시 driver_map 추가

---

# Part 9. 최종 한 줄 정의 (v6)

```text
DMA v6는, 사전에 정의된 62개 sub_issue × 16개 scoring_axis_allowed를 negative constraint로 강제한 상태에서,
Retriever → Classifier → Scorer → Polarity → Calibrator → Judge의 6개 분리 에이전트가
chunk 단위로 sub_issue_similarity / issue_relevance / impact_relevance / financial_relevance /
signal_strength / polarity / iro_type / time_horizon / confidence를 산출하고,
deterministic Aggregator가 stage(benchmark/media/survey) × sub_issue 단위로 bucket을 누적해
3단계 점수와 일치도(concordance_pattern)를 산출한 뒤,
선정 규칙이 자동 선정과 HITL 검토를 구분하여 최종 sub_issue 우선순위를 결정하는 시스템이다.

모든 점수는 trace_json을 통해 chunk 단위까지 drill-down 가능하며,
운영 중 발생하는 low-confidence/axis-violation/polarity-conflict chunk는
HITL queue로 자동 라우팅되어 gold set을 늘리고 시스템 성능을 점진적으로 개선한다.
```

---

## 부록 A. 프롬프트 템플릿 예시

### A.1 Classifier Agent System Prompt

```text
당신은 ESG 이중중대성 평가의 Classifier입니다.

## 역할
주어진 chunk와 후보 sub_issue 목록을 보고, chunk가 어떤 sub_issue(들)에 해당하는지 분류합니다.

## 규칙
1. 후보 목록 밖의 sub_issue로 분류하지 마세요.
2. issue_relevance는 다음 rubric으로 0~1로 매깁니다:
   - 0.9~1.0: 직접·구체적으로 다룸 (수치/사건/정책 명시)
   - 0.7~0.9: 명시적이지만 얕음
   - 0.5~0.7: 핵심 개념 부분 등장
   - 0.3~0.5: 같은 issue_group이지만 다른 sub_issue가 더 정확
   - 0.0~0.3: 관련 없음 (분류하지 마세요)
3. negative_keyword가 본문에 있으면 분류 거부하세요.
4. 여러 sub_issue에 해당하는 multi-label은 정상입니다. 단, 각각 issue_relevance >= 0.5만.
5. 모든 분류에는 evidence_span(인용 시작·끝 위치)을 포함하세요.
6. 본문에 없는 정보로 추론하지 마세요.

## OUTPUT JSON
{
  "classified_sub_issues": [
    {
      "sub_issue_id": "...",
      "issue_relevance": 0.92,
      "rationale": "본문 line 3에 ... 명시",
      "evidence_spans": [{"start": 42, "end": 78, "text": "..."}]
    }
  ],
  "abstain": false,
  "abstain_reason": null
}

## 후보 sub_issue (각각 정의·키워드·negative_keyword 포함)
{candidates_with_definitions}

## 분류 대상 chunk
{chunk_text}
```

### A.2 Scorer Agent System Prompt (간략 버전)

```text
당신은 ESG 이중중대성 평가의 Scorer입니다.
주어진 chunk와 분류된 sub_issue에 대해 impact_relevance, financial_relevance, signal_strength를 0~5로 평가합니다.

## Impact Rubric (0~5)
0: 영향 없음 (단순 사업 소개)
1: 간접·약한 영향 (정책 선언)
2: 잠재 영향 가능성
3: 실제 운영 영향
4: 범위·반복성 큼
5: 중대·회복 어려움 (인명/대규모 환경/대규모 인권)

## Financial Rubric (0~5)
0: 재무 영향 없음
1: 간접 평판 영향
2: 잠재 비용·시장 영향
3: 운영비·CAPEX·수주 영향
4: 매출·수익성·신용·규제비용 영향 명확
5: 기업가치 훼손 또는 구조적 기회

## Signal Strength (0~5)
0: 사건·수치·규제·평가 없음
1: 약한 언급
2: 구체적 활동
3: 수치/사건 1건
4: 다수 수치/사건 또는 명확한 규제·등급
5: 중대 사건 + 규제 + 다수 출처

## 규칙
- impact, financial은 독립적으로 평가 (한 chunk가 한 axis에서만 높을 수 있음).
- 점수 부여 시 반드시 evidence_text(본문 인용)를 포함.
- 두 axis 모두 0이면 chunk 폐기(JSON에서 drop=true).
- 본문에 명시되지 않은 추론 금지.

## allowed_axes (이 안에 해당하는 axis만 점수 부여 가능)
{allowed_axes_list}

## OUTPUT JSON
{schema}

## chunk
{chunk_text}

## sub_issue
{sub_issue_full_definition}
```

(이하 Polarity, Judge 프롬프트도 같은 패턴으로 작성)

---

## 부록 B. 자주 묻는 질문

**Q1. 왜 LLM 한 번에 다 안 시키나? 6번 부르면 비싸지 않나?**
A. Retriever와 Calibrator는 LLM call이 거의 0. 게이트로 abstain하면 후속 단계가 안 돌아감. 실측 시 6단계가 1단계보다 오히려 cost가 낮을 가능성이 큼. 게다가 trace/explainability 가치가 훨씬 큼.

**Q2. Phase 1에서 멀티에이전트 금지 결정(D-005)과 충돌하지 않나?**
A. 본 문서는 명시적으로 Phase 2 entry decision(D-006 후보) 위치. Phase 1 4축 검증 후 진입.

**Q3. scoring_axis_allowed가 정말 모든 sub_issue에 적절히 설정되어 있나?**
A. 현재 사전(v4.3)에 16개 axis로 매핑되어 있음. Phase 2-A 첫 주에 60건 sample로 검증 권장 — 부정확한 매핑이 있으면 사전 업데이트.

**Q4. CTX modifier의 modifier 계수(예: 0.3, 0.25)는 어떻게 정하나?**
A. 초기값은 자동차부품 driver_map과 KIS 방법론 참고하여 보수적 설정. 운영 6개월 후 데이터로 회귀 분석하여 조정.

**Q5. Gold set 200건이 충분한가?**
A. 부족. Phase 2-A entry 기준일 뿐. Active learning loop로 2,000건까지 늘려가는 게 목표.

**Q6. 한 sub_issue가 여러 chunk에서 모순적 polarity를 받으면?**
A. 정상. bucket별로 별도 누적되므로 risk_score와 opportunity_score가 동시에 높을 수 있음 (Mixed). 단, dominant_iro_type은 majority/conservative 규칙으로 결정.

---

## 부록 C. 참고

- 본 문서가 기반하는 사전 문서:
  - `DMA_v5_이중중대성_평가_로직.md`
  - `ESG_Atomic_Master_v4_3_작업정리_및_향후작업계획.md`
  - `Narrative_Template_Structured_Variables_Design_v1_0.md`
  - `esg_sr_harness/docs/00_core_principles.md`, `05_scoring.md`
  - `07_ESG_IssueGroup_SubIssue_Keyword_Dictionary_v4_3` (62 sub_issue, 16 scoring_axis)
  - `DMA_v4_점수화_로직_피드백용_구글시트` (rubric, multiplier, formula)
  - `Atomic_Master_v4_4` (905 atomic, 246 metric)

- 외부 기준:
  - GRI 3: Material Topics 2021
  - IFRS S1 / S2
  - ESRS / EFRAG IG 1
  - KIS 자동차부품산업 평가방법론(2024)

