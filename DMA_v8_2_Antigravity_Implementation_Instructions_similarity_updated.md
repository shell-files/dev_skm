# DMA v8.2 구현 기획 및 개발 지시서 — Antigravity 의뢰용

작성일: 2026-05-25  
프로젝트: ESG 보고서 자동 생성 플랫폼 / 이중중대성평가(Double Materiality Assessment, DMA) 에이전트  
목적: 기존 v8.0/v8.1 기획, `ocrai_v8.py`, `dma_engine.py`, 온보딩 DB/지표 매핑 구조를 기반으로 **실제 서비스 확장 가능한 이중중대성평가 로직 v8.2**를 구현한다. MVP에서는 5개 sub_issue를 고정 더미로 시연할 수 있으나, 백엔드/DB/API 구조는 반드시 실제 벤치마킹·미디어·설문 기반 평가로 확장 가능해야 한다.

---

## 0. Antigravity 작업자에게 전달할 핵심 요약

이번 작업은 단순히 `impact_score`, `financial_score`를 LLM이 직접 산출하게 만드는 작업이 아니다. 목표는 다음 구조를 구현하는 것이다.

```text
G0 경영일반 데이터 해석
→ 기업 Context Profile 생성
→ 62개 확정 sub_issue 기준 IRO / time horizon / modifier 설정
→ Step 1 벤치마킹 분석
→ Step 2 미디어·외부평가 분석
→ Step 3 이해관계자 설문
→ 최종 impact / financial matrix 산출
→ 최종 15개 sub_issue 표시
→ 사용자가 5~10개 선택
→ 선택 sub_issue에 매핑된 onboarding atomic metric만 호출
→ 온보딩 입력
→ 지속가능경영보고서 이중중대성평가 챕터 생성
```

현재 MVP에서는 5개 sub_issue를 고정 선택하여 더미 설문을 진행할 수 있다. 단, 점수 로직·DB 스키마·API 흐름은 고정 더미 전용으로 만들면 안 된다. 반드시 실제 평가 데이터가 들어왔을 때 같은 경로로 동작해야 한다.

---

## 1. 반드시 지켜야 할 설계 원칙

### 1.1 62개 sub_issue는 고정 기준 풀이다

플랫폼에는 이미 62개의 sub_issue set이 존재한다. 모든 벤치마킹, 미디어, 규제, 전문기관, 설문 데이터는 반드시 이 62개 sub_issue 중 하나 또는 복수에 매핑되어야 한다.

금지 사항:

- LLM이 새로운 sub_issue를 임의 생성하는 것
- 보고서나 뉴스에 나온 표현을 그대로 신규 이슈로 저장하는 것
- 62개 sub_issue dictionary 밖의 값을 최종 후보로 올리는 것

허용 사항:

- 원문 표현을 `raw_issue_text` 또는 `source_label`로 저장
- 62개 sub_issue와의 유사도/근거를 함께 저장
- 관련성이 낮으면 `unmapped` 또는 `low_confidence`로 제외

### 1.2 G0 Context Agent는 기준을 새로 만드는 것이 아니라 보정한다

G0 경영일반 지표에는 가치사슬, 기업활동, 매출 구성, 주력 제품, 사업지역, 자회사/해외법인 여부, 규제 노출 등이 포함된다.

AI 에이전트는 이를 읽고 기업 맞춤형 Context Profile을 만든다. 다만 AI가 회사별로 루브릭을 새로 만들어서는 안 된다. 기본 루브릭은 산업 기준으로 고정하고, AI는 sub_issue별 modifier와 IRO/time horizon 적용 방향을 제한적으로 조정한다.

기본 원칙:

```text
산업 기본 루브릭 고정
→ G0 Context Agent가 기업 특성 해석
→ sub_issue별 IRO 유형, time horizon, context modifier 생성
→ 이후 Step 1/2/3 점수 계산에 적용
```

MVP 산업은 자동차부품이다. 따라서 초기 v8.2에서는 자동차부품 산업 기준 루브릭을 기본값으로 둔다. 단, 코드 구조는 향후 다른 산업으로 확장할 수 있게 `industry_profile` 기반으로 분리한다.

### 1.3 IRO와 time horizon은 점수축이 아니라 분류축이다

기회/리스크/장기/단기는 독립 점수항목으로 만들지 않는다. 이들은 Financial/Impact 점수를 산출할 때 적용되는 분류축이다.

IRO 유형:

```text
financial_risk
financial_opportunity
negative_impact
positive_impact
context
```

Time horizon 기본값:

```text
short: 0~1년
mid: 1~3년
long: 3년 이상
```

자동차부품 MVP 예시:

```text
제품안전 / 리콜 / 품질 클레임: short financial_risk, short negative_impact
중대재해 / 산업안전: short negative_impact, short financial_risk
전동화 전환 지연: mid~long financial_risk, long financial_opportunity
공급망 실사 / EU 규제: mid financial_risk, mid negative_impact
기후전환 / 탄소규제: mid~long financial_risk, long negative_impact
자원순환 / 재활용 소재: mid~long positive_impact, financial_opportunity
```


### 1.4 Sub-issue Similarity Mapping은 점수 배분 가중치다

Benchmark / Media External 원천 데이터는 62개 sub_issue dictionary에 매핑되어야 한다. 이때 단순 1:1 매핑이 아니라, 각 원천 텍스트와 62개 sub_issue 간 `similarity_score`를 산출하고 threshold를 통과한 top-k sub_issue에 점수를 배분한다.

핵심 원칙:

```text
similarity는 최종 중대성 점수가 아니다.
similarity는 원천 evidence/event/issue label의 점수를 어떤 sub_issue에 얼마만큼 배분할지 결정하는 mapping weight다.
```

기본 설정:

```text
similarity_score range = 0.0 ~ 1.0
similarity_threshold = 0.60
top_k = 3
alpha = 1.5
```

Mapping weight 계산:

```text
raw_mapping_weight_i
= max(0, similarity_i - similarity_threshold) ^ alpha
```

```text
normalized_mapping_weight_i
= raw_mapping_weight_i / sum(raw_mapping_weight_all)
```

점수 배분:

```text
sub_issue_score_i
= base_evidence_score
* normalized_mapping_weight_i
* source_reliability_weight
* recency_weight
* confidence_weight
```

적용 원칙:

```text
1. similarity 0.60 미만은 점수 배분에서 제외한다.
2. 하나의 source event 또는 raw issue label은 최대 3개 sub_issue까지만 배분한다.
3. 1순위 매핑 similarity가 0.80 이상이고 2순위와 0.15 이상 차이가 나면 single-primary mapping으로 처리할 수 있다.
4. 규제 데이터는 hard mapping을 우선 적용하고, hard mapping이 없을 때만 similarity mapping을 적용한다.
5. 설문 구조화 문항은 sub_issue에 직접 귀속한다.
6. 설문 자유서술형 응답만 similarity mapping을 적용한다.
7. 동일 사건이 여러 기사에서 반복 보도된 경우 event_group_id로 중복 제거한 뒤 similarity 기반 배분을 적용한다.
```

저장 필수값:

```text
issue_similarity_score
similarity_rank
similarity_threshold
mapping_weight
mapping_method
matched_dictionary_terms
```

`mapping_method` enum:

```text
dictionary_similarity
hard_mapping
manual_override
direct_survey_item
```


---

## 2. 전체 프로세스 v8.2

## Step 0. G0 Context Agent

### 목적

기업의 G0 경영일반 지표를 읽고 기업활동, 가치사슬, 매출 구조, 사업지역, 규제 노출, 자회사/해외법인 구조를 반영한 평가 보정 정보를 생성한다.

### 입력

- 기업 개요
- 가치사슬 설명
- 매출 구성
- 주요 제품/서비스
- 주요 고객군
- 지역별 사업장/법인
- EU 법인 또는 해외법인 여부
- 주요 규제 노출 정보
- 기존 온보딩 G0 지표

### 출력 예시

```json
{
  "industry_profile": "automotive_parts",
  "business_model": "B2B_auto_component_supplier",
  "value_chain_exposure": {
    "upstream": 0.75,
    "own_operation": 0.85,
    "downstream": 0.70
  },
  "revenue_exposure": {
    "ice_powertrain": 0.60,
    "ev_components": 0.25,
    "aftermarket": 0.15
  },
  "regulatory_exposure": {
    "eu_supply_chain": true,
    "product_safety": true,
    "climate_transition": true
  },
  "context_modifier_by_sub_issue": {
    "climate_transition": 1.15,
    "supply_chain_due_diligence": 1.10,
    "product_safety_quality": 1.20
  },
  "iro_horizon_hint_by_sub_issue": {
    "product_safety_quality": ["short", "financial_risk", "negative_impact"],
    "climate_transition": ["mid", "long", "financial_risk", "negative_impact"],
    "resource_circulation": ["mid", "long", "financial_opportunity", "positive_impact"]
  }
}
```

### modifier 제한

권장 범위:

```text
일반 sub_issue: 0.85 ~ 1.15
자동차부품 고위험 핵심 sub_issue: 0.80 ~ 1.25
```

AI가 1.25를 초과하는 modifier를 생성하면 Judge 또는 rule validator에서 reject한다.

---

## Step 1. Benchmarking Agent

### 목적

본인 회사, 리더그룹, 피어그룹의 지속가능경영보고서에서 이중중대성평가 결과를 파싱하고, 모든 이슈를 플랫폼의 62개 sub_issue로 매핑한다.

### 분석 대상

보고서 전체가 아니라 다음 영역을 우선 대상으로 한다.

```text
- 이중중대성평가 챕터
- 중대이슈 선정 결과 표
- Material Topic / Key Issue / Material Issue 목록
- 이슈별 영향/위험/기회 설명
- 중대성 매트릭스 또는 우선순위 표
```

### 핵심 로직

1. 자사 과거 SR에서 선정된 이슈를 62개 sub_issue로 매핑
2. 리더그룹 SR에서 선정된 이슈를 62개 sub_issue로 매핑
3. 피어그룹 SR에서 선정된 이슈를 62개 sub_issue로 매핑
4. 공통 선정 빈도 계산
5. 자사는 선정하지 않았으나 리더/피어가 반복 선정한 이슈를 `blind_spot`으로 판정
6. blind_spot 이슈에 추가 가중치 부여
7. 약 20~40개 sub_issue가 Step 1에서 유효 점수를 받도록 설계


### Benchmark Similarity Mapping

보고서에 나온 원문 이슈명(`raw_issue_label`)은 그대로 저장하되, 최종 판단은 반드시 62개 sub_issue dictionary와의 similarity mapping 결과를 사용한다.

```text
raw_issue_label
→ 62개 sub_issue similarity 계산
→ threshold 통과 top-k 추출
→ normalized_mapping_weight 산출
→ 각 sub_issue에 benchmark signal 배분
```

Benchmark 단계에서는 `selected issue 여부`가 강한 신호이므로, similarity는 선정 여부 점수를 분배하는 역할을 한다.

```text
benchmark_signal_by_sub_issue
= issue_selection_strength
* normalized_mapping_weight
* company_group_weight
```

권장 `company_group_weight`:

```text
self_past = 0.90
peer = 1.00
leader = 1.10
```

자사는 미선정했지만 leader/peer에서 반복 선정된 경우에는 `blind_spot` 보너스를 별도 적용한다.


### 권장 산식

```text
leader_coverage = 해당 sub_issue를 선정한 리더그룹 회사 수 / 전체 리더그룹 회사 수
peer_coverage = 해당 sub_issue를 선정한 피어그룹 회사 수 / 전체 피어그룹 회사 수
self_selected = 자사 과거 SR에서 해당 sub_issue 선정 여부
blind_spot = 1 if self_selected = 0 and (leader_coverage + peer_coverage) >= threshold else 0
```

```text
benchmark_base_score
= 100 * (
    0.40 * leader_coverage
  + 0.35 * peer_coverage
  + 0.25 * blind_spot
)
```

Financial/Impact 분리는 원문에서 IRO 성격과 context hint를 함께 반영한다.

```text
benchmark_impact = benchmark_base_score * impact_axis_applicability
benchmark_financial = benchmark_base_score * financial_axis_applicability
```

### 저장해야 할 상세 정보

- source company type: self / leader / peer
- source company name
- source report year
- raw issue label
- mapped sub_issue_code
- mapping confidence
- issue_similarity_score
- similarity_rank
- mapping_weight
- mapping_method
- selected issue 여부
- evidence text
- page number
- blind_spot 여부

---

## Step 2. Media & External Agent

### 목적

외부 환경에서 해당 기업 및 자동차부품 산업에 대한 이슈 신호를 수집하고, 이를 62개 sub_issue에 매핑하여 Financial/Impact 점수로 축적한다.

Step 2는 별도 세부 축 3개를 가진다.

```text
1. 언론/뉴스 분석
2. 전문기관/외부평가 분석
3. 규제 노출/규제 리스크 분석
```

주의: 규제와 전문기관은 별도 DMA 단계가 아니라 Step 2 내부 하위 모듈이다.


### Step 2 공통 Similarity Mapping 원칙

Step 2의 뉴스, 전문기관, 규제 데이터는 모두 62개 sub_issue 기준으로 귀속되어야 한다.

뉴스/전문기관 텍스트는 similarity mapping을 기본 적용한다.

```text
source_text 또는 event_summary
→ 62개 sub_issue similarity 계산
→ threshold 통과 top-k 추출
→ normalized_mapping_weight 산출
→ event score를 sub_issue별로 배분
```

규제 데이터는 사전 정의된 hard mapping을 우선 적용한다.

```text
if regulation_sub_issue_hard_map exists:
    mapping_method = "hard_mapping"
    use predefined hard_map_weight
else:
    mapping_method = "dictionary_similarity"
    use normalized_mapping_weight
```


### Step 2-1. News Analysis

#### 입력

- 조직명 기반 기사 검색 결과
- 자회사/브랜드/주요 제품명 기반 기사 검색 결과
- 자동차부품 산업 공통 이슈 기사

#### 처리 원칙

뉴스는 기사 단위로 무한 누적하지 않는다. 동일 사건을 여러 매체가 반복 보도할 수 있으므로 `event_group_id`로 중복 제거해야 한다.

```text
news_event_score_by_sub_issue
= micro_score
* normalized_mapping_weight
* confidence_score
* source_credibility_weight
* recency_weight
```

여기서 `normalized_mapping_weight`는 62개 sub_issue dictionary와의 similarity를 threshold/top-k/normalization 처리한 값이다.

여러 이벤트는 포화형 합산을 사용한다.

```text
news_score = 100 * (1 - Π(1 - event_score_i / 100))
```

### Step 2-2. Agency / External Rating Analysis

#### 대상 예시

- KCGS 3개년 등급 추세
- ESG 평가기관의 산업별 평가 의견
- 신용평가사의 자동차부품 산업 평가론
- 산업 리포트의 구조적 리스크/기회

#### 현재 상태

구체 로직은 아직 미완성이다. MVP에서는 최소한 아래 수준으로 rule-based prototype을 만든다.

```text
KCGS 등급 하락: 관련 G sub_issue 또는 전체 governance score 보정
산업 리포트에서 반복 언급되는 리스크: 해당 sub_issue에 agency signal 부여
신용평가사 산업전망 부정: financial_risk 쪽 score 보정
```

### Step 2-3. Regulation Analysis

#### 목적

자동차부품사에 위험도가 높은 규제를 사전에 3단계로 분류하고, 해당 규제와 연결되는 sub_issue에 Financial/Impact 가중치를 부여한다.

#### 규제 위험도 단계

```text
Level 1: 모니터링 필요. 낮은 직접 영향.
Level 2: 관리 필요. 벌금/거래요건/고객사 요구와 연결 가능.
Level 3: 고위험. 벌금, 영업정지, 공급망 배제, 제품판매 제한, 중대한 평판 훼손 가능.
```

#### 자동차부품 MVP 우선 검토 규제 예시

- EU 공급망 실사 관련 규제
- EU CSRD/ESRS 연결 공시 요구
- 제품 안전/리콜 관련 규제
- 기후/탄소 관련 규제
- 배터리/전동화 부품 관련 규제
- 산업안전/중대재해 관련 규제
- 폐기물/자원순환/유해물질 관련 규제

규제 점수는 LLM이 자유 채점하지 않는다. 사전에 정의한 `regulation_sub_issue_map`과 `regulation_risk_level` 기반으로 rule-based 점수를 부여한다.

### Step 2 내부 통합 산식

```text
media_external_impact
= 0.60 * news_impact
+ 0.25 * regulation_impact
+ 0.15 * agency_impact
```

```text
media_external_financial
= 0.35 * news_financial
+ 0.40 * regulation_financial
+ 0.25 * agency_financial
```

---

## Step 3. Stakeholder Survey Engine

### 목적

Step 1과 Step 2를 통해 중간평가된 Top 20~25개 sub_issue를 대상으로 이해관계자 설문을 생성하고, 설문 결과를 최종 Impact/Financial 점수에 반영한다.

### 설문 유형

```text
1. 임직원 설문
2. 경영진 설문
3. 외부 이해관계자 설문
```

### 설문 생성 방식

플랫폼에는 62개 sub_issue 전체에 대한 설문 문항셋이 저장되어 있어야 한다. 실제 설문 단계에서는 Step 1+2 중간평가 결과 상위 20~25개 sub_issue에 대한 문항만 활성화한다.

단, 공통 질문은 항상 포함한다.

### 공통 질문 예시

```text
- 62개 sub_issue 중 가장 중요하다고 생각하는 이슈 10개 선택
- 선택한 10개 이슈의 우선순위 정렬
- 향후 3년 내 가장 커질 리스크 선택
- 향후 3년 내 가장 커질 기회 선택
```

### 동적 질문 예시

각 Top 20~25개 sub_issue별로 다음 질문을 구성한다.

```text
- 이 이슈가 회사의 재무성과에 미칠 영향은 어느 정도인가?
- 이 이슈가 환경/사회/이해관계자에게 미칠 영향은 어느 정도인가?
- 이 이슈는 단기/중기/장기 중 어느 기간에 가장 중요해질 것으로 보는가?
- 이 이슈는 회사에 주로 리스크인가, 기회인가, 또는 둘 다인가?
```

응답 척도는 1~5 또는 1~10 중 하나로 통일한다. 내부 계산 시에는 모두 0~100으로 정규화한다.


### 설문 응답과 Similarity 적용 범위

설문 구조화 문항은 이미 특정 sub_issue에 귀속되어 있으므로 similarity mapping을 적용하지 않는다.

```text
structured survey item → direct_survey_item mapping
```

단, 자유서술형 응답은 62개 sub_issue dictionary와의 similarity mapping을 적용한다.

```text
free_text_answer
→ 62개 sub_issue similarity 계산
→ threshold 통과 top-k 추출
→ normalized_mapping_weight 산출
→ 보조 signal로 저장
```

자유서술형 점수는 최종 설문 점수의 주된 산식에 직접 과도 반영하지 말고, `qualitative_signal` 또는 `survey_comment_signal`로 별도 저장하여 설명/QA에 활용한다.


### 설문 내부 가중치

Impact 설문 점수:

```text
survey_impact
= 0.30 * employee_score
+ 0.25 * management_score
+ 0.45 * external_stakeholder_score
```

Financial 설문 점수:

```text
survey_financial
= 0.20 * employee_score
+ 0.50 * management_score
+ 0.30 * external_stakeholder_score
```

설문이 최종 단계에서 가장 높은 단일 비중을 가져야 한다. 다만 과도하게 지배해서는 안 된다.

---

## 3. 최종 점수 산식

## 3.1 후보군 생성 단계: 설문 전

설문 전에는 Benchmark와 Media External만으로 Top 20~25개 sub_issue를 도출한다.

```text
pre_survey_impact_score
= 0.45 * benchmark_impact
+ 0.55 * media_external_impact
```

```text
pre_survey_financial_score
= 0.40 * benchmark_financial
+ 0.60 * media_external_financial
```

Top 20~25개는 다음 기준 중 하나로 선정한다.

```text
candidate_score = max(pre_survey_impact_score, pre_survey_financial_score)
또는
candidate_score = 0.5 * pre_survey_impact_score + 0.5 * pre_survey_financial_score
```

MVP에서는 두 방식을 모두 계산하고 QA 화면에 비교 표시하는 것을 권장한다.

## 3.2 최종 설문 반영 단계

설문이 끝난 뒤 최종 base score를 계산한다.

```text
final_impact_base
= 0.36 * survey_impact
+ 0.30 * benchmark_impact
+ 0.34 * media_external_impact
```

```text
final_financial_base
= 0.36 * survey_financial
+ 0.29 * benchmark_financial
+ 0.35 * media_external_financial
```

설문은 가장 높은 단일 비중이지만, 36%로 제한한다. 벤치마킹과 미디어·외부평가가 각각 29~35% 수준으로 설문을 견제한다.

## 3.3 Context Modifier 적용

Context Modifier는 별도 점수 비중으로 더하지 않는다. 최종 base score에 곱하는 보정계수로 처리한다.

```text
final_impact_score
= clamp(final_impact_base * context_impact_modifier * survey_reliability_modifier, 0, 100)
```

```text
final_financial_score
= clamp(final_financial_base * context_financial_modifier * survey_reliability_modifier, 0, 100)
```

## 3.4 Override Rule

설문 비중이 높아지면 일반 응답자가 잘 모르는 고위험 규제/사고 이슈가 낮게 나올 수 있다. 따라서 다음 override rule이 필요하다.

```text
if regulation_risk_level == 3 and regulation_score >= 80:
    force_include = true
    final_financial_score = max(final_financial_score, 70)

if severe_negative_impact_score >= 90:
    force_include = true
    final_impact_score = max(final_impact_score, 75)

if media_event_severity >= 5 and confidence_score >= 0.8:
    force_include = true
```

Override로 포함된 이슈는 UI에서 반드시 `강제 포함 사유`를 표시해야 한다.

---

## 4. Impact / Financial 하위 점수 구조

## 4.1 Impact Materiality

Impact 점수는 다음 요소를 분리해 저장한다.

```text
impact_direction: positive / negative
actuality: actual / potential
scale: 0~5
scope: 0~5
irremediability: 0~5, negative impact 중심
likelihood: 0~5, potential impact 중심
time_horizon: short / mid / long
```

권장 계산:

```text
impact_severity
= 0.60 * max(scale, scope, irremediability)
+ 0.40 * average(scale, scope, irremediability)
```

```text
actual impact:
impact_score = impact_severity

potential impact:
impact_score = impact_severity * likelihood_factor
```

```text
likelihood_factor:
0점 = 0.0
1점 = 0.2
2점 = 0.4
3점 = 0.6
4점 = 0.8
5점 = 1.0
```

## 4.2 Financial Materiality

Financial 점수는 다음 요소를 분리해 저장한다.

```text
financial_iro_type: risk / opportunity
revenue_magnitude: 0~5
cost_magnitude: 0~5
capex_magnitude: 0~5
asset_liability_magnitude: 0~5
financing_magnitude: 0~5
legal_regulatory_magnitude: 0~5
likelihood: 0~5
time_horizon: short / mid / long
```

권장 계산:

```text
financial_magnitude
= 0.70 * max(revenue, cost, capex, asset_liability, financing, legal_regulatory)
+ 0.30 * average(non_zero_channels)
```

```text
financial_score
= financial_magnitude * likelihood_factor
```

Risk와 Opportunity는 같은 구조로 계산하되 저장 필드는 분리한다.

```text
financial_risk_score
financial_opportunity_score
```

---

## 5. ocrai_v8.py / dma_engine.py 리팩토링 지시

## 5.1 현재 문제

현재 `ocrai_v8.py`는 Classifier와 Scorer 중심으로 구성되어 있으며, 62개 이슈 dictionary와 rubric이 TODO placeholder로 남아 있다. 현재 구조는 LLM이 `impact_relevance`, `financial_relevance`를 직접 산출하는 형태에 가깝다.

v8.2에서는 LLM이 최종 점수를 직접 결정하는 구조를 피한다.

권장 방향:

```text
LLM 역할:
- text span 추출
- 62개 sub_issue 매핑 후보 제시
- IRO label 추출
- time horizon hint 추출
- rubric evidence 추출
- confidence 제시

Rule-based Python 역할:
- 하위 점수 계산
- source별 가중치 적용
- context modifier 적용
- override rule 적용
- final impact/financial score 산출
```

## 5.2 권장 Agent Pipeline

```text
1. Retriever / Chunker
2. Classifier
3. IRO Labeler
4. Axis Evidence Extractor
5. Rule-based Scorer
6. Calibrator
7. Judge
8. Aggregator
```

### Judge 필수 조건

다음 경우 reject 또는 revise 처리한다.

```text
- 62개 sub_issue dictionary 밖의 이슈를 생성한 경우
- financial 4점 이상인데 비용/매출/벌금/소송/조업차질/고객이탈/자금조달 근거가 없는 경우
- impact 4점 이상인데 피해 규모/범위/회복불가능성/이해관계자 피해 근거가 없는 경우
- confidence가 기준 미만인 경우
- evidence span이 비어 있는 경우
```

## 5.3 Pydantic Schema 확장안

```python
class DMAContextProfile(BaseModel):
    company_id: int
    reporting_year: int
    industry_profile: str
    business_model: str
    value_chain_exposure: dict
    revenue_exposure: dict
    regulatory_exposure: dict
    context_modifier_by_sub_issue: dict
    iro_horizon_hint_by_sub_issue: dict
    confidence: float

class ImpactAssessment(BaseModel):
    impact_direction: Literal["positive", "negative"]
    actuality: Literal["actual", "potential"]
    scale: int = Field(..., ge=0, le=5)
    scope: int = Field(..., ge=0, le=5)
    irremediability: Optional[int] = Field(None, ge=0, le=5)
    likelihood: Optional[int] = Field(None, ge=0, le=5)
    time_horizon: Literal["short", "mid", "long"]
    impact_score: float
    evidence_spans: List[str]

class FinancialAssessment(BaseModel):
    financial_iro_type: Literal["risk", "opportunity"]
    revenue_magnitude: int = Field(..., ge=0, le=5)
    cost_magnitude: int = Field(..., ge=0, le=5)
    capex_magnitude: int = Field(..., ge=0, le=5)
    asset_liability_magnitude: int = Field(..., ge=0, le=5)
    financing_magnitude: int = Field(..., ge=0, le=5)
    legal_regulatory_magnitude: int = Field(..., ge=0, le=5)
    likelihood: int = Field(..., ge=0, le=5)
    time_horizon: Literal["short", "mid", "long"]
    financial_score: float
    evidence_spans: List[str]

class DMAScoreDetail(BaseModel):
    sub_issue_code: str
    issue_similarity_score: float
    similarity_rank: Optional[int]
    similarity_threshold: float = 0.60
    mapping_weight: float
    mapping_method: Literal["dictionary_similarity", "hard_mapping", "manual_override", "direct_survey_item"]
    matched_dictionary_terms: List[str]
    source_step: Literal["benchmark", "media_external", "survey"]
    source_type: str
    iro_type: Literal["financial_risk", "financial_opportunity", "negative_impact", "positive_impact", "context"]
    time_horizon: Literal["short", "mid", "long"]
    impacts: List[ImpactAssessment]
    financials: List[FinancialAssessment]
    confidence_score: float
    evidence_id: Optional[str]
    judge_status: Literal["pass", "revise", "reject"]
    judge_reason: Optional[str]
```

---

## 6. DB 설계 보완 지시

기존 `ESG_MATERIALITY_RUN`, `ESG_MATERIALITY_SUB_ISSUE_SCORE`, `ESG_MATERIALITY_SELECTED_SUB_ISSUE`, `ESG_SELECTED_ONBOARDING_SCOPE`, `ESG_ONBOARDING_CYCLE` 흐름은 유지한다.

다만 현재 summary 중심 구조만으로는 감사추적이 부족하므로 detail ledger 테이블을 추가한다.

## 6.1 추가 권장 테이블

### ESG_DMA_CONTEXT_PROFILE

```sql
CREATE TABLE ESG_DMA_CONTEXT_PROFILE (
    esg_dma_context_profile_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    company_id BIGINT NOT NULL,
    reporting_year INT NOT NULL,
    industry_profile VARCHAR(100) NOT NULL,
    business_model VARCHAR(255) NULL,
    context_json JSON NOT NULL,
    modifier_json JSON NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### ESG_DMA_SCORE_DETAIL

```sql
CREATE TABLE ESG_DMA_SCORE_DETAIL (
    esg_dma_score_detail_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    sub_issue_code VARCHAR(100) NOT NULL,
    source_step VARCHAR(50) NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    iro_type VARCHAR(50) NOT NULL,
    time_horizon VARCHAR(20) NOT NULL,
    issue_similarity_score DECIMAL(8,4) NULL,
    similarity_rank INT NULL,
    similarity_threshold DECIMAL(8,4) NULL,
    mapping_weight DECIMAL(10,6) NULL,
    mapping_method VARCHAR(50) NULL,
    matched_dictionary_terms JSON NULL,
    impact_scale TINYINT NULL,
    impact_scope TINYINT NULL,
    impact_irremediability TINYINT NULL,
    impact_likelihood TINYINT NULL,
    financial_revenue TINYINT NULL,
    financial_cost TINYINT NULL,
    financial_capex TINYINT NULL,
    financial_asset_liability TINYINT NULL,
    financial_financing TINYINT NULL,
    financial_legal_regulatory TINYINT NULL,
    financial_likelihood TINYINT NULL,
    impact_score DECIMAL(8,4) NULL,
    financial_score DECIMAL(8,4) NULL,
    confidence_score DECIMAL(8,4) NULL,
    evidence_id BIGINT NULL,
    scoring_rule_version VARCHAR(100) NOT NULL,
    judge_status VARCHAR(20) NOT NULL,
    judge_reason TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### ESG_DMA_EVIDENCE

```sql
CREATE TABLE ESG_DMA_EVIDENCE (
    evidence_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_type VARCHAR(100) NOT NULL,
    source_title VARCHAR(500) NULL,
    source_url TEXT NULL,
    source_document_id BIGINT NULL,
    page_no INT NULL,
    text_span TEXT NOT NULL,
    event_group_id VARCHAR(100) NULL,
    source_published_at DATETIME NULL,
    source_credibility_score DECIMAL(8,4) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### ESG_DMA_SURVEY_RESPONSE

```sql
CREATE TABLE ESG_DMA_SURVEY_RESPONSE (
    esg_dma_survey_response_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    respondent_group VARCHAR(50) NOT NULL,
    department_code VARCHAR(100) NULL,
    sub_issue_code VARCHAR(100) NULL,
    question_id VARCHAR(100) NOT NULL,
    answer_value DECIMAL(8,4) NOT NULL,
    normalized_score DECIMAL(8,4) NOT NULL,
    mapped_axis VARCHAR(50) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 6.2 Summary Table 운용

`ESG_DMA_SCORE_DETAIL`은 상세 ledger다. 기존 또는 현행 summary 테이블인 `ESG_MATERIALITY_SUB_ISSUE_SCORE`에는 집계 결과만 저장한다.

권장 summary 필드 개념:

```text
benchmark_score
media_score
stakeholder_score
impact_score
financial_score
final_score
rank_no
force_include_yn
force_include_reason
```

---

## 7. 온보딩 연계 구현 지시

최종 15개 sub_issue를 matrix에 표시하고, 사용자가 그중 5~10개를 확정 선택한다. 선택된 sub_issue는 기존 매핑 테이블을 통해 onboarding scope로 전환한다.

권장 흐름:

```text
ESG_MATERIALITY_RUN
→ ESG_MATERIALITY_SUB_ISSUE_SCORE
→ ESG_MATERIALITY_SELECTED_SUB_ISSUE
→ ESG_SELECTED_ONBOARDING_SCOPE
→ ESG_ONBOARDING_CYCLE
→ ESG_METRIC_ASSIGNMENT
→ ESG_ONBOARDING_INPUT_VALUE
→ ESG_FACT_CANDIDATE
→ ESG_KPI_FACT
→ ESG_REPORT_CONTEXT_SNAPSHOT
→ ESG_REPORT_SECTION_DRAFT
```

MVP에서는 5개 sub_issue를 고정 선택해도 된다. 단, 반드시 동일 흐름을 탄다.

MVP 고정 선택 처리 방식:

```text
selection_type = 'mvp_fixed'
selected_result_fixed_yn = 1
selection_reason = 'MVP demo fixed sub_issue set. Actual DMA score route preserved.'
```

금지 사항:

- MVP라고 해서 온보딩 지표를 하드코딩해서 직접 노출
- sub_issue → metric/atomic mapping을 우회
- materiality run 없이 onboarding cycle만 직접 생성
- 더미 점수만 화면에 고정 표시

---

## 8. API 설계 초안

## 8.1 Context API

```text
POST /dma/runs/{run_id}/context/generate
```

역할:

- G0 온보딩 데이터 조회
- Context Agent 실행
- ESG_DMA_CONTEXT_PROFILE 저장
- sub_issue별 modifier 반환

## 8.2 Benchmark API

```text
POST /dma/runs/{run_id}/benchmark/analyze
```

역할:

- 자사/리더/피어 SR 문서 업로드 또는 기존 source_document 조회
- DMA 챕터 파싱
- 62개 sub_issue similarity mapping
- mapping_weight 기준 benchmark signal 배분
- blind spot 계산
- ESG_DMA_SCORE_DETAIL 저장
- summary 업데이트

## 8.3 Media External API

```text
POST /dma/runs/{run_id}/media-external/analyze
```

역할:

- 뉴스/전문기관/규제 데이터 수집 또는 업로드
- event grouping
- sub_issue similarity mapping 및 regulation hard mapping
- mapping_weight 기준 news/regulation/agency 내부 점수 계산
- ESG_DMA_EVIDENCE 및 ESG_DMA_SCORE_DETAIL 저장
- summary 업데이트

## 8.4 Survey API

```text
POST /dma/runs/{run_id}/survey/generate
POST /dma/runs/{run_id}/survey/responses
POST /dma/runs/{run_id}/survey/score
```

역할:

- pre-survey score 기준 Top 20~25개 sub_issue 추출
- 62개 설문셋 중 대상 문항만 활성화
- 공통 질문 추가
- 응답 저장
- survey impact/financial 점수 계산
- summary 업데이트

## 8.5 Finalize API

```text
POST /dma/runs/{run_id}/finalize
POST /dma/runs/{run_id}/selected-sub-issues
POST /dma/runs/{run_id}/onboarding-scope/generate
```

역할:

- final impact/financial score 계산
- matrix용 Top 15 산출
- 사용자 5~10개 확정 저장
- 선택 sub_issue 기준 onboarding scope 생성

---

## 9. 화면/UX 요구사항

## 9.1 DMA 진행 화면

Stepper 형태:

```text
0. 기업 Context 설정
1. 벤치마킹 분석
2. 미디어·외부평가 분석
3. 이해관계자 설문
4. 최종 Matrix
5. 온보딩 Scope 생성
```

## 9.2 Matrix 화면

표시 요소:

```text
X축: Impact score
Y축: Financial score
점: sub_issue
색상: E/S/G 또는 issue group
크기: final score 또는 confidence
뱃지: force_include, blind_spot, high_regulation_risk
```

## 9.3 Score Explain 화면

각 sub_issue를 클릭하면 다음을 표시한다.

```text
- 최종 impact / financial 점수
- benchmark 기여도
- media external 기여도
- survey 기여도
- context modifier
- IRO 유형
- short/mid/long 판단
- 주요 evidence
- issue similarity / mapping weight / mapping method
- blind spot 여부
- override 여부
- 연결되는 onboarding metric/atomic 목록
```

---

## 10. MVP 구현 범위

## 10.1 반드시 구현

```text
- 62개 sub_issue dictionary 로드
- sub_issue similarity mapping 기본 로직 구현(threshold/top_k/alpha/normalization)
- G0 Context Profile 생성 mock 또는 semi-real 구현
- MVP fixed 5 sub_issue 선택
- 더미 설문 생성 및 응답 처리
- survey score 계산
- final matrix mock 표시
- selected sub_issue → onboarding scope 생성
- 기존 onboarding flow와 연결
```

## 10.2 가능하면 구현

```text
- benchmark report parser prototype
- SR 내 DMA 챕터 우선 파싱
- 62개 sub_issue 매핑 confidence 산출
- blind spot 계산 prototype
- media/news sample data 기반 scoring prototype
- regulation risk map prototype
```

## 10.3 MVP에서 하드코딩 가능하지만 반드시 표시할 것

```text
- mvp_fixed selection 여부
- scoring_rule_version
- model_version
- dummy_data_yn
- force_include_yn
```

---

## 11. QA / Acceptance Criteria

아래 조건을 만족해야 한다.

```text
1. 모든 score는 62개 sub_issue 중 하나에 귀속된다.
2. 62개 밖의 이슈는 최종 후보에 들어가지 않는다.
3. G0 Context Modifier는 0.80~1.25 범위를 벗어나지 않는다.
4. 설문 최종 가중치는 가장 높은 단일 비중이지만 36%를 초과하지 않는다.
5. Benchmark / Media External 원천 데이터는 similarity_threshold, top_k, mapping_weight를 거쳐 62개 sub_issue에 배분된다.
6. 규제 데이터는 hard mapping을 우선 적용하고, hard mapping이 없을 때만 similarity mapping을 적용한다.
7. 설문 구조화 문항은 direct_survey_item으로 처리하고, 자유서술형 응답만 similarity mapping을 적용한다.
8. 규제/전문기관은 별도 단계가 아니라 Step 2 media_external 내부로 집계된다.
9. Context Modifier는 별도 가중치가 아니라 multiplier로 적용된다.
10. 최종 Top 15가 impact/financial matrix에 표시된다.
11. 사용자가 5~10개 sub_issue를 선택할 수 있다.
12. 선택 sub_issue에 매핑된 onboarding atomic metric만 scope에 들어간다.
13. MVP fixed sub_issue도 실제 materiality/onboarding 경로를 우회하지 않는다.
14. evidence 없는 high score는 Judge에서 reject 또는 revise된다.
15. score detail과 summary가 분리 저장된다.
16. report draft 생성 시 narrative reference/audit 추적이 가능해야 한다.
```

---

## 12. Antigravity에 공유해야 할 참고 파일

아래 파일은 함께 전달해야 한다.

### 필수 파일

```text
1. DMA_Master_Operational_Design_v8.1_Integrated.md
   - v8.1 기준 전체 DMA 운영 기획서

2. DMA_Master_Operational_Design_v8_Integrated.md
   - v8.0 원본 기획서

3. ocrai_v8.py
   - 현재 OCR/LLM 기반 micro text scoring engine

4. dma_engine.py
   - 현재 Pydantic schema 정의

5. sub_issue_map.xlsx
   - 62개 sub_issue dictionary / keyword mapping 기준

6. SKM_ESG_Onboarding_Integrated_DDL_v5_2_FKSnake_MariaDB.sql
   - 실제 온보딩/이중중대성/보고서 생성 DB DDL 기준

7. SKM_ESG_DB_Load_Mapping_v5_2_FKSnake.md
   - DB 적재 및 테이블 매핑 설명

8. MVP_ESG_Integrated_Quant_Qual_AllMetric_Map_v5_1_MinOps.xlsx
   - sub_issue, metric, atomic, dummy input, rollup, narrative, evidence MVP seed 기준

9. MVP_ESG_v5_CALCULATION_RULE_SQL.xlsx
   - 계산형 지표 rule/source/execution/validation 기준
```

### 가능하면 함께 공유할 파일

```text
10. 01_ESG_master_standard.xlsx
    - 공시 기준/표준 맵핑 검토용

11. 03프로젝트_개요 및 설계해설.md
    - 프로젝트 전체 맥락 설명

12. 04_ESG_ERD_통합설계_v3.md
    - ERD/테이블 관계 검토용

13. 05_공통코드_통합_설계_문서_v1.md
    - 공통코드/enum 정합성 검토용
```

---

## 13. 작업 우선순위

### Phase A. 설계 정합성 고정

```text
- 62개 sub_issue dictionary 로드 방식 확정
- similarity_threshold / top_k / alpha / mapping_weight 계산 방식 확정
- regulation hard mapping 우선순위 확정
- G0 Context Profile schema 확정
- IRO/time horizon enum 확정
- Impact/Financial 하위 점수 schema 확정
- final weighting rule 확정
```

### Phase B. DB 보완

```text
- ESG_DMA_CONTEXT_PROFILE 추가
- ESG_DMA_SCORE_DETAIL 추가
- ESG_DMA_EVIDENCE 추가
- ESG_DMA_SURVEY_RESPONSE 추가
- 기존 materiality summary table과 연결
```

### Phase C. Backend 로직 구현

```text
- dma_engine.py schema 확장
- ocrai_v8.py pipeline 리팩토링
- rule-based scorer 구현
- sub_issue similarity mapper 구현
- context modifier calculator 구현
- benchmark aggregator 구현
- media external aggregator 구현
- survey scoring engine 구현
- final matrix aggregator 구현
```

### Phase D. MVP Demo 연결

```text
- fixed 5 sub_issue demo route 구현
- dummy survey response 생성
- final matrix Top 15 표시
- selected 5 sub_issue 저장
- onboarding scope 생성
- selected scope 기반 onboarding UI 연결
```

---

## 14. 최종 구현 목표

최종 목표는 “AI가 알아서 이슈 10개를 뽑았다”가 아니다. 목표는 다음과 같다.

```text
- 62개 sub_issue 기준으로만 평가한다.
- Benchmark / Media External 점수는 similarity mapping weight 또는 hard mapping weight를 통해 sub_issue에 배분한다.
- 모든 점수는 source, evidence, IRO, time horizon, confidence를 가진다.
- LLM은 evidence와 분류를 보조하고, 최종 계산은 rule-based로 한다.
- 설문은 최종 단계에서 가장 높은 단일 비중을 갖지만 과도하지 않다.
- G0 데이터는 기업 맞춤형 context modifier로 작동한다.
- MVP 더미도 실제 운영 경로를 우회하지 않는다.
- 최종 선정 sub_issue는 onboarding metric/atomic scope와 직접 연결된다.
- 이후 지속가능경영보고서 이중중대성평가 챕터 생성까지 감사추적 가능해야 한다.
```

