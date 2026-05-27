# SKM ESG 플랫폼 이중중대성평가 점수 기준 로직 설계 v1

문서 버전: v1.0  
작성 목적: 이중중대성평가(DMA: Double Materiality Assessment)의 Financial Materiality와 Impact Materiality 점수 기준을 실무형으로 고정하고, 현재 MVP DB·UI·에이전트 로직에 연결 가능한 형태로 정의한다.  
적용 범위: 자동차부품 산업 MVP 기준. 단, 향후 산업별 baseline으로 확장 가능한 구조를 전제로 한다.  
주요 대상: 기획자, 백엔드 개발자, AI 에이전트 개발자, 프론트엔드 개발자, 데이터 설계 담당자.

---

## 0. 문서 요약

현재 MVP는 다음 흐름을 목표로 한다.

```text
G0 경영일반/회사 현황 읽기
→ 자동차부품 산업 baseline 기준 로드
→ 회사 상황 기반 점수 보정값 생성
→ 벤치마킹/미디어/설문 단계별 sub_issue 점수화
→ 62개 sub_issue별 Financial / Impact 점수 집계
→ 최종 이중중대성 매트릭스 도출
→ 5개 핵심 이슈 선정
→ 관련 온보딩 지표 호출
→ 보고서 초안 생성 및 근거 KPI 추적
```

점수 기준의 핵심 원칙은 다음이다.

```text
1. LLM이 최종 점수를 임의로 결정하지 않는다.
2. LLM은 증거 추출, 이슈 매핑, IRO 힌트 추출, 루브릭 근거 설명에 제한한다.
3. 최종 점수는 고정 루브릭과 rule-based formula로 계산한다.
4. Financial과 Impact는 반드시 분리해서 계산한다.
5. 벤치마킹/미디어/설문은 점수를 만드는 입력 방식은 다르지만, 최종 Financial/Impact 기준은 동일하게 유지한다.
6. 회사 상황 보정은 허용하되, 보정 폭은 제한한다. MVP 기준 -0.5 ~ +0.5점 범위를 넘지 않는다.
7. UI에서 보이는 점수는 내부 0~5 점수를 10점 또는 100점으로 환산한 결과일 수 있다. 내부 기준은 0~5를 기본으로 한다.
```

---

## 1. 현황 진단

### 1.1 현재 `ocrai_v8.py`의 성격

현재 `ocrai_v8.py`는 문서 PDF를 Gemini에 업로드하고, 1차 Classifier Agent와 2차 Scorer Agent를 호출하는 구조를 가진다. 구조적 방향은 맞지만 아직 실무형 이중중대성평가 엔진으로 보기에는 부족하다.

현재 문제는 다음과 같다.

```text
1. 62개 sub_issue 사전이 실제 DB 또는 기준 파일에서 로드되지 않고 placeholder 상태다.
2. Financial Rubric과 Impact Rubric이 placeholder 수준이다.
3. LLM이 impact_relevance, financial_relevance를 직접 부여하는 구조라 점수 재현성과 설명가능성이 약하다.
4. G0 회사 현황, 가치사슬, 재무 규모, 산업 baseline을 읽는 Context Profile 단계가 없다.
5. 벤치마킹/미디어/설문 source별로 다른 입력 특성을 점수화하는 로직이 아직 분리되어 있지 않다.
6. 현재 UI에서 필요한 단계별 결과 패널과 DB 저장값이 완전히 연결되어 있지 않다.
```

### 1.2 현재 `dma_engine.py`의 성격

현재 `dma_engine.py`에는 다음 계층이 있다.

```text
ClassifierOutput
ScorerOutput
PolarityOutput
JudgeOutput
```

이는 초기 구조로는 적절하지만, v1 점수 기준에서는 아래 schema가 더 필요하다.

```text
DMAContextProfile
FinancialRubricEvaluation
ImpactRubricEvaluation
DMASignalDetailDTO
DMAScoreSummaryDTO
BenchmarkSignalDTO
MediaSignalDTO
SurveySignalDTO
```

단, MVP에서 DB를 대규모로 갈아엎지 않기 위해 새로운 테이블을 많이 추가하기보다는 기존 `ESG_DMA_SIGNAL_DETAIL`, `ESG_DMA_SCORE_SUMMARY`, `ESG_DMA_CONTEXT_PROFILE`, `ESG_MATERIALITY_RUN`을 최대한 활용한다.

### 1.3 현재 `12implementation_plan.md`의 한계

기존 구현계획은 “2차 Scorer LLM을 붙여 루브릭 점수를 산출한다”는 방향은 맞다. 그러나 현재 최종 설계에는 다음 요소가 추가되어야 한다.

```text
1. G0 경영일반/가치사슬/재무현황 기반 Context Profile 생성
2. 자동차부품 산업 baseline 기준
3. 회사 상황 기반 context modifier
4. Financial/Impact 점수의 정량+정성 기준
5. 기회/리스크, 긍정/부정, 단기/중기/장기 IRO 분해
6. 벤치마킹/미디어/설문 source별 score generation 방식
7. DB 저장 구조와 UI 결과 화면 매핑
8. 근거 설명과 score trace 구조
```

따라서 기존 구현계획은 `DMA Scoring Framework v1` 기준으로 재작성되어야 한다.

---

## 2. 전체 DMA 점수 산정 아키텍처

### 2.1 전체 단계

```text
[Step 0] Company Context Agent
- G0 경영일반 지표, 가치사슬 설명, 매출/영업이익/순이익, 사업장, 제품군, 법인 지역, 산업 정보 읽기
- 자동차부품 산업 baseline과 회사상황을 결합해 context_modifier 생성

[Step 1] Benchmark Agent
- 리더/피어/자사 SR 보고서에서 이중중대성평가 선정 이슈 추출
- 62개 sub_issue 풀로 재매핑
- 공통 선정 이슈, 자사 blind spot 이슈 산출
- sub_issue별 benchmark_impact_score / benchmark_financial_score 계산

[Step 2] Media External Agent
- 언론 기사, 전문기관 자료, 규제 프레임 분석
- 62개 sub_issue로 매핑
- source별 signal strength, likelihood, evidence strength 산출
- sub_issue별 media_external_impact_score / media_external_financial_score 계산

[Step 3] Survey Agent
- 임직원, 경영진, 외부 이해관계자 설문 응답 집계
- 설문 문항을 Impact/Financial로 분리해 점수화
- sub_issue별 survey_impact_score / survey_financial_score 계산

[Step 4] Score Aggregation Engine
- Benchmark / Media / Survey 점수 통합
- 최종 final_impact_score / final_financial_score / final_score 계산
- rank_no 산정

[Step 5] Materiality Selection Engine
- 최종 후보군 20~25개 도출
- 최종 Top 10 또는 MVP 확정 5개 이슈 선정
- ESG_MATERIALITY_SELECTED_SUB_ISSUE 저장

[Step 6] Onboarding/Report Linkage
- 선정 sub_issue → 관련 atomic_metric 호출
- 온보딩 입력/확정 KPI_FACT 생성
- 보고서 생성 및 근거 KPI trace
```

### 2.2 점수 체계의 기본 단위

내부 점수는 0~5를 기준으로 한다.

```text
0 = 해당 없음 / 관련성 없음
1 = 매우 낮음
2 = 낮음
3 = 중간
4 = 높음
5 = 매우 높음
```

UI에서는 화면 성격에 따라 다음처럼 환산한다.

```text
0~5 내부 점수 → 0~10 UI 점수: internal_score * 2
0~5 내부 점수 → 0~100 UI 점수: internal_score * 20
```

MVP UI의 단계별 Top 이슈 표에서는 10점 만점 형태가 적절하다.

```text
예: internal 4.6점 → UI 9.2점
```

최종 matrix 계산 또는 DB 저장은 0~5 기준으로 보존한다.

---

## 3. Step 0: Company Context Profile 설계

### 3.1 목적

이중중대성평가 점수 기준을 모든 기업에 동일하게 적용하면 실제 기업 상황이 반영되지 않는다. 예를 들어 자동차부품 기업은 다음 이슈의 중요도가 일반 기업보다 높게 설정되어야 한다.

```text
- 기후목표·전환계획
- Scope 1·2 배출량
- Scope 3 가치사슬 배출
- 공급망 감사·시정조치
- 제품안전·품질
- 저탄소·친환경 제품
- 산업안전
- 교육훈련·역량개발
```

따라서 G0 경영일반 지표 및 재무현황을 바탕으로 회사별 context profile을 먼저 생성한다.

### 3.2 입력 데이터

Context Profile Agent가 참고해야 할 데이터는 다음이다.

```text
1. 회사 일반정보
- 회사명
- 회사 규모
- 산업분류
- 본사 위치
- 주요 법인/사업장 지역
- 국내/해외 사업장 수

2. 가치사슬 설명
- Upstream 원재료/부품 조달
- 제조/생산 공정
- Downstream 고객사/완성차 납품
- 물류/판매/AS 구조

3. 주요 제품/서비스
- 자동차부품
- 전장부품
- 모듈
- 친환경차 부품
- 기존 내연기관 부품

4. 재무현황
- 매출액
- 영업이익
- 순이익
- 주요 매출원
- 친환경 제품 매출 비중

5. 규제 노출
- EU 법인 보유 여부
- CSRD/ESRS 관련성
- CSDDD 관련성
- CBAM 관련성
- 제품안전/품질 규제 관련성
```

### 3.3 출력 데이터

Context Profile 출력 예시는 다음이다.

```json
{
  "industry_profile": "automotive_parts_manufacturing",
  "business_model": "B2B automotive supplier",
  "value_chain_exposure": {
    "upstream": "raw materials, suppliers, outsourced components",
    "operations": "manufacturing, assembly, testing",
    "downstream": "OEM customers, product safety, after-sales"
  },
  "revenue_context": {
    "annual_revenue": 17800000000000,
    "operating_profit": 956600000000,
    "currency": "KRW"
  },
  "regulatory_exposure": {
    "csrd_esrs": "medium_high",
    "csddd": "high",
    "cbam": "medium",
    "product_safety": "high"
  },
  "context_modifier_by_sub_issue": {
    "E_CLIMATE_TARGETS_TRANSITION": 0.2,
    "S_SUPPLY_CHAIN_AUDIT_CORRECTIVE_ACTION": 0.4,
    "S_PRODUCT_SAFETY_QUALITY": 0.4,
    "E_PRODUCT_ENV_PRODUCT_PERFORMANCE": 0.3,
    "S_TALENT_TRAINING_DEVELOPMENT": 0.2
  },
  "iro_horizon_hint_by_sub_issue": {
    "E_CLIMATE_TARGETS_TRANSITION": "mid_long",
    "S_SUPPLY_CHAIN_AUDIT_CORRECTIVE_ACTION": "short_mid",
    "S_PRODUCT_SAFETY_QUALITY": "short",
    "E_PRODUCT_ENV_PRODUCT_PERFORMANCE": "mid",
    "S_TALENT_TRAINING_DEVELOPMENT": "mid"
  }
}
```

### 3.4 Context Modifier 제한

Context Modifier는 기업 상황을 반영하기 위한 보정값이다. 단, AI가 자의적으로 점수를 과도하게 움직이지 못하게 범위를 제한한다.

```text
허용 범위: -0.5 ~ +0.5
기본값: 0.0
자동차부품 산업에서 매우 관련 높은 이슈: +0.2 ~ +0.4
회사 가치사슬과 직접 관련 높은 이슈: +0.1 ~ +0.3
기업 활동과 관련성이 낮은 이슈: -0.1 ~ -0.3
```

MVP에서는 `context_modifier`가 최종 점수에 직접 들어가되, 0~5 범위를 벗어나면 clamp 처리한다.

```python
final_score = min(5.0, max(0.0, raw_score + context_modifier))
```

---

## 4. Financial Materiality 점수 기준 v1

### 4.1 Financial Materiality 정의

Financial Materiality는 특정 ESG sub_issue가 기업의 재무성과, 현금흐름, 자본비용, 매출, 비용, 투자, 규제 대응, 고객사 관계, 수주 가능성, 신용도, 사업 지속성에 미치는 현재 또는 잠재 영향을 평가한다.

### 4.2 Financial IRO 구분

Financial은 리스크와 기회를 모두 다룬다.

```text
Financial Risk
- 비용 증가
- 매출 감소
- 벌금/과징금/소송
- 규제 미준수 비용
- 고객사 납품 제한
- 제품 리콜/품질 비용
- 공급망 차질
- 신용등급/자금조달 영향

Financial Opportunity
- 친환경 제품 매출 확대
- 에너지 비용 절감
- 고객사 수주 기회 증가
- 공급망 경쟁력 향상
- 저탄소 전환 투자 효과
- 브랜드/시장 접근성 향상
```

### 4.3 Financial 점수 구성요소

Financial 점수는 다음 3개 축으로 계산한다.

```text
1. Financial Magnitude: 재무 영향 규모
2. Likelihood: 발생가능성
3. Time Urgency: 시간 긴급성
```

보조적으로 `context_modifier`를 적용한다.

### 4.4 Financial Magnitude: 재무 영향 규모 0~5점

재무 영향 규모는 연매출 대비 영향률을 기본 기준으로 삼고, 영업이익/현금흐름 영향률을 보조 기준으로 삼는다. 이유는 제조업에서는 매출 대비로는 작아 보여도 영업이익에는 큰 충격을 줄 수 있기 때문이다.

| 점수 | 연매출 대비 잠재 영향 | 영업이익/현금흐름 영향 | 정성 기준 |
|---:|---:|---:|---|
| 0 | 영향 없음 | 영향 없음 | 관련성 없음 |
| 1 | 매출의 0.01% 미만 | 영업이익의 0.1% 미만 | 일반 관리비 수준, 선언적 영향 |
| 2 | 매출의 0.01% 이상 ~ 0.05% 미만 | 영업이익의 0.1% 이상 ~ 0.5% 미만 | 제한적 비용 증가, 소규모 투자 |
| 3 | 매출의 0.05% 이상 ~ 0.20% 미만 | 영업이익의 0.5% 이상 ~ 2.0% 미만 | 특정 사업부, 고객사, 공급망, 제품군에 영향 가능 |
| 4 | 매출의 0.20% 이상 ~ 1.00% 미만 | 영업이익의 2.0% 이상 ~ 10.0% 미만 | 주요 사업 또는 수익성에 의미 있는 영향 |
| 5 | 매출의 1.00% 이상 | 영업이익의 10.0% 이상 | 기업 전체 재무성과 또는 사업 지속성에 중대한 영향 |

#### 적용 원칙

```text
1. 매출 기준 점수와 영업이익 기준 점수가 모두 있으면 높은 값을 우선 적용한다.
2. 벌금, 리콜, 소송, 수주 제한처럼 정량 추정이 어려운 경우 정성 기준으로 magnitude를 산정할 수 있다.
3. 재무 데이터가 없는 경우 산업 baseline과 evidence 수준에 따라 보수적으로 1~3점 범위에서 시작한다.
4. 규제 시행 확정, 고객사 요구 확정, 제품 리콜 발생 등 명확한 사건은 정성 기준으로 4~5점까지 가능하다.
```

### 4.5 Financial Likelihood: 발생가능성 0~5점

| 점수 | 기준 | 해석 |
|---:|---|---|
| 0 | 발생 근거 없음 | 해당 없음 |
| 1 | 10년 초과에 1회 미만 | 매우 낮음 |
| 2 | 5~10년에 1회 수준 | 낮음 |
| 3 | 3~5년에 1회 수준 | 중간 |
| 4 | 1~3년에 1회 수준 | 높음 |
| 5 | 매년 발생 또는 이미 발생 중 | 매우 높음 |

#### Source별 Likelihood 해석

```text
벤치마킹:
- 리더/피어 대부분이 최근 3년 연속 선정: 4~5
- 리더/피어 다수 선정: 3~4
- 일부 기업만 선정: 2~3
- 단발 관측: 1~2

미디어:
- 최근 반복 기사/사건 발생: 4~5
- 산업 baseline에서 반복 관측: 3~4
- 특정 규제 시행 확정 또는 적용 중: 4~5
- 단일 기사 또는 약한 간접 언급: 1~2

설문:
- 평균 4.5 이상: 5
- 평균 4.0 이상 4.5 미만: 4
- 평균 3.0 이상 4.0 미만: 3
- 평균 2.0 이상 3.0 미만: 2
- 평균 2.0 미만: 1
```

### 4.6 Financial Time Urgency: 시간 긴급성 0~5점

| 점수 | 기준 | 해석 |
|---:|---|---|
| 0 | 시점 판단 불가 | 해당 없음 |
| 1 | 10년 초과 | 장기·낮은 긴급성 |
| 2 | 5~10년 | 장기 |
| 3 | 3~5년 | 중기 |
| 4 | 1~3년 | 단기 |
| 5 | 1년 이내 또는 이미 발생 | 즉시 대응 필요 |

#### 보정 원칙

기후전환처럼 장기 이슈라도 현재 투자, 제품 포트폴리오, 고객사 요구, 규제 대응이 필요하면 `time_urgency`는 3~4로 보정할 수 있다.

### 4.7 Financial Risk 산식

리스크는 발생가능성과 긴급성을 조금 더 강하게 반영한다.

```text
financial_risk_score_0_5
= 0.45 * magnitude
+ 0.35 * likelihood
+ 0.20 * time_urgency
+ context_modifier
```

### 4.8 Financial Opportunity 산식

기회는 매출/시장/비용절감 규모를 조금 더 강하게 반영한다.

```text
financial_opportunity_score_0_5
= 0.55 * magnitude
+ 0.25 * likelihood
+ 0.20 * time_urgency
+ context_modifier
```

### 4.9 최종 Financial Score

MVP에서는 리스크와 기회 중 더 높은 값을 최종 Financial 점수로 사용한다.

```text
financial_score_0_5
= max(financial_risk_score_0_5, financial_opportunity_score_0_5)
```

단, 내부적으로는 risk_score와 opportunity_score를 모두 보존하는 것이 바람직하다. UI에는 통합 Financial만 노출해도 된다.

### 4.10 Financial Score Clamp

```python
financial_score_0_5 = max(0.0, min(5.0, financial_score_0_5))
```

---

## 5. Impact Materiality 점수 기준 v1

### 5.1 Impact Materiality 정의

Impact Materiality는 기업 활동이 환경, 사회, 사람, 고객, 공급망, 지역사회, 인권, 건강, 안전, 생태계에 미치는 긍정적 또는 부정적 영향을 평가한다.

### 5.2 Impact IRO 구분

Impact는 다음 기준으로 구분한다.

```text
Impact Direction:
- positive
- negative

Actuality:
- actual
- potential

Time Horizon:
- short
- mid
- long
```

### 5.3 Impact 점수 구성요소

Impact는 다음 축을 사용한다.

```text
1. Scale: 영향 강도
2. Scope: 영향 범위
3. Likelihood: 발생가능성
4. Irremediability: 회복불가능성, 부정 영향 중심
5. Time Urgency: 시간 긴급성
```

### 5.4 Impact Scale: 영향 강도 0~5점

| 점수 | 기준 |
|---:|---|
| 0 | 영향 없음 |
| 1 | 경미한 영향, 일상 관리 가능 |
| 2 | 일부 이해관계자 또는 일부 사업장 영향 |
| 3 | 주요 사업장 또는 다수 이해관계자에 명확한 영향 |
| 4 | 공급망, 고객, 지역사회 등 광범위한 영향 |
| 5 | 인명, 건강, 환경, 인권, 생태계에 심각한 영향 |

### 5.5 Impact Scope: 영향 범위 0~5점

| 점수 | 기준 |
|---:|---|
| 0 | 범위 없음 |
| 1 | 단일 부서 또는 단일 사업장 |
| 2 | 일부 사업장 또는 일부 협력사 |
| 3 | 다수 사업장 또는 주요 협력사 |
| 4 | 국내 전 사업장 또는 주요 가치사슬 |
| 5 | 글로벌 사업장, 전체 가치사슬, 광범위 이해관계자 |

### 5.6 Impact Likelihood: 발생가능성 0~5점

Financial Likelihood와 동일 기준을 사용한다.

| 점수 | 기준 | 해석 |
|---:|---|---|
| 0 | 발생 근거 없음 | 해당 없음 |
| 1 | 10년 초과에 1회 미만 | 매우 낮음 |
| 2 | 5~10년에 1회 수준 | 낮음 |
| 3 | 3~5년에 1회 수준 | 중간 |
| 4 | 1~3년에 1회 수준 | 높음 |
| 5 | 매년 발생 또는 이미 발생 중 | 매우 높음 |

### 5.7 Irremediability: 회복불가능성 0~5점

부정 영향에 더 강하게 적용한다.

| 점수 | 기준 |
|---:|---|
| 0 | 해당 없음 |
| 1 | 즉시 복구 가능 |
| 2 | 단기 복구 가능 |
| 3 | 복구 가능하나 비용과 시간이 필요 |
| 4 | 장기 복구 필요 또는 완전 회복 어려움 |
| 5 | 회복 불가능 또는 인명·건강·인권·생태계 중대 훼손 |

### 5.8 Impact Time Urgency: 시간 긴급성 0~5점

Financial Time Urgency와 동일 기준을 사용한다.

| 점수 | 기준 | 해석 |
|---:|---|---|
| 0 | 시점 판단 불가 | 해당 없음 |
| 1 | 10년 초과 | 장기·낮은 긴급성 |
| 2 | 5~10년 | 장기 |
| 3 | 3~5년 | 중기 |
| 4 | 1~3년 | 단기 |
| 5 | 1년 이내 또는 이미 발생 | 즉시 대응 필요 |

### 5.9 Negative Impact 산식

부정 영향은 회복불가능성을 반영한다.

```text
negative_impact_score_0_5
= 0.30 * scale
+ 0.25 * scope
+ 0.20 * likelihood
+ 0.15 * irremediability
+ 0.10 * time_urgency
+ context_modifier
```

### 5.10 Positive Impact 산식

긍정 영향은 확산 범위와 효과 규모를 더 크게 본다.

```text
positive_impact_score_0_5
= 0.35 * scale
+ 0.30 * scope
+ 0.25 * likelihood
+ 0.10 * time_urgency
+ context_modifier
```

### 5.11 최종 Impact Score

MVP에서는 긍정/부정 영향 중 더 높은 점수를 최종 Impact로 사용한다.

```text
impact_score_0_5
= max(negative_impact_score_0_5, positive_impact_score_0_5)
```

단, 내부적으로는 positive_impact_score와 negative_impact_score를 모두 보존하는 것이 바람직하다.

### 5.12 Impact Score Clamp

```python
impact_score_0_5 = max(0.0, min(5.0, impact_score_0_5))
```

---

## 6. 자동차부품 산업 Baseline v1

MVP는 자동차부품 산업을 대상으로 하므로, baseline을 먼저 둔다. 이 baseline은 최종 점수를 고정하는 것이 아니라, `context_modifier`, `default time_horizon`, `source 해석 기준`에 영향을 준다.

### 6.1 자동차부품 산업 주요 노출

```text
1. B2B 고객사 의존도 높음
2. 완성차 OEM 요구사항에 민감
3. 공급망 실사, 협력사 ESG 관리 중요
4. 제조공정 에너지 사용과 온실가스 배출 존재
5. 제품안전, 품질, 리콜 리스크 중요
6. 전동화/친환경 제품 전환 기회 존재
7. EU 규제 노출 가능성 존재
8. Scope 3 가치사슬 배출 중요성 증가
9. 인력 역량 전환, 교육훈련 중요
```

### 6.2 MVP 핵심 5개 이슈 baseline

| sub_issue | Financial baseline | Impact baseline | 기본 horizon | context_modifier 가이드 |
|---|---:|---:|---|---:|
| 기후목표·전환계획 | 높음 | 높음 | mid/long, 투자 시 short 보정 | +0.2 ~ +0.4 |
| 공급망 감사·시정조치 | 높음 | 높음 | short/mid | +0.3 ~ +0.5 |
| 교육훈련·역량개발 | 중간 | 중간~높음 | mid | +0.1 ~ +0.3 |
| 저탄소·친환경 제품 | 높음 | 중간~높음 | mid | +0.2 ~ +0.4 |
| 소비자 건강·제품안전 | 높음 | 높음 | short | +0.3 ~ +0.5 |

---

## 7. Source별 점수 산정 방식

### 7.1 공통 원칙

벤치마킹, 미디어, 설문은 데이터 성격이 다르다. 그러나 모두 최종적으로는 동일한 Financial/Impact 기준으로 정규화되어야 한다.

```text
벤치마킹:
- 어떤 이슈가 리더/피어/자사 SR에서 선정되었는가?
- 공통 선정 이슈인가?
- 자사가 놓친 blind spot인가?

미디어:
- 외부 기사/전문기관/규제에서 어떤 signal이 관측되는가?
- source 강도, 근거 강도, 규제 확정성, issue mapping 신뢰도는 어느 정도인가?

설문:
- 이해관계자가 해당 이슈의 Impact/Financial 중요도를 어떻게 평가했는가?
- 임직원/경영진/외부 이해관계자별 차이는 무엇인가?
```

---

## 8. 벤치마킹 점수 산정 방식 v1

### 8.1 벤치마킹 입력

```text
- 리더그룹 SR 보고서 3개년 또는 N건
- 피어그룹 SR 보고서 3개년 또는 N건
- 자사 과거 SR 보고서 3개년 또는 N건
- 각 보고서의 이중중대성평가 선정 이슈 텍스트
- 62개 sub_issue dictionary
```

### 8.2 벤치마킹 처리 흐름

```text
1. 각 보고서에서 이중중대성평가 선정 이슈 영역 추출
2. 추출된 이슈명을 62개 sub_issue로 매핑
3. 리더/피어/자사 source_type별 관측 여부 계산
4. 리더/피어 공통 이슈 계산
5. 자사 미선정 blind spot 계산
6. 산업 baseline과 context profile을 결합해 benchmark_impact_score / benchmark_financial_score 산정
```

### 8.3 벤치마킹에서 하면 안 되는 것

```text
리더/피어/자사 각각의 Financial/Impact 점수를 직접 비교하면 안 된다.
```

벤치마킹은 source별 “점수”가 아니라 source별 “관측/선정 여부”를 보는 단계다.

UI에서 가능한 표현:

```text
- 리더 관측 여부
- 피어 관측 여부
- 자사 관측 여부
- 공통 선정 이슈
- 자사 blind spot
- sub_issue별 benchmark impact/financial 점수
```

UI에서 피해야 할 표현:

```text
- 리더 financial 점수
- 피어 impact 점수
- 자사 financial 점수
```

### 8.4 Benchmark Signal 계산

MVP 기준 benchmark_signal은 다음 요소로 구성한다.

```text
leader_presence_score
peer_presence_score
own_presence_score
common_issue_bonus
blind_spot_bonus
mapping_confidence
```

#### Source Presence 기준

```text
leader_presence_score:
- 리더그룹 다수 보고서에서 관측: 4~5
- 일부 리더 보고서에서 관측: 2~3
- 미관측: 0

peer_presence_score:
- 피어그룹 다수 보고서에서 관측: 4~5
- 일부 피어 보고서에서 관측: 2~3
- 미관측: 0

own_presence_score:
- 자사 과거 보고서에서 반복 선정: 3~4
- 자사 과거 보고서에서 일부 선정: 1~2
- 미선정: 0
```

#### Common Issue Bonus

```text
리더와 피어 모두에서 관측: +0.3
리더/피어/자사 모두에서 관측: +0.2
```

#### Blind Spot Bonus

```text
리더 또는 피어 다수 관측 AND 자사 미관측: +0.4
리더/피어 모두 다수 관측 AND 자사 미관측: +0.5
```

### 8.5 Benchmark 점수 산식

```text
benchmark_signal_0_5
= 0.35 * leader_presence_score
+ 0.35 * peer_presence_score
+ 0.10 * own_presence_score
+ common_issue_bonus
+ blind_spot_bonus
```

이 signal을 해당 sub_issue의 Financial/Impact baseline과 결합한다.

```text
benchmark_financial_score
= benchmark_signal_0_5 * financial_baseline_factor + context_modifier

benchmark_impact_score
= benchmark_signal_0_5 * impact_baseline_factor + context_modifier
```

MVP에서는 `financial_baseline_factor`, `impact_baseline_factor`를 0.8~1.1 범위로 제한한다.

```text
높음 baseline: 1.05
중간 baseline: 0.95
낮음 baseline: 0.85
```

최종은 0~5로 clamp한다.

### 8.6 벤치마킹 저장 데이터

`ESG_DMA_SIGNAL_DETAIL`에는 다음 성격의 데이터가 저장되어야 한다.

```json
{
  "source_step": "benchmark",
  "source_type": "leader_peer_own_sr",
  "sub_issue_code": "S_SUPPLY_CHAIN_AUDIT_CORRECTIVE_ACTION",
  "leader_observed_yn": true,
  "peer_observed_yn": true,
  "own_observed_yn": false,
  "common_issue_yn": true,
  "blind_spot_yn": true,
  "mapping_confidence": 0.91,
  "evidence_summary": "리더/피어 보고서에서 공급망 실사 및 시정조치 이슈가 반복적으로 중대 이슈로 선정됨"
}
```

`ESG_DMA_SCORE_SUMMARY`에는 다음 값이 집계된다.

```text
benchmark_impact_score
benchmark_financial_score
```

---

## 9. 미디어 분석 점수 산정 방식 v1

### 9.1 미디어 입력

MVP 미디어 source는 다음 3개 유형으로 제한한다.

```text
1. 언론 기사
- 회사명 및 자동차부품 산업 키워드 기반 수집
- 약 78건 예상
- 62개 sub_issue 중 관측 이슈 약 19개 예상

2. 전문기관 자료
- KCGS 등급 추세
- 기업지배구조보고서
- KIS 자동차산업 신용평가방법론
- 기타 MVP 지정 자료
- 약 3~4개 자료

3. 규제 프레임
- CSDDD
- CBAM
- CSRD
- ESRS
- MVP에서는 고정 rule base mapping
```

### 9.2 미디어 분석의 핵심 원칙

언론 기사 건수가 많고 전문기관/규제 자료 건수가 적다고 해서 언론의 중요도가 무조건 더 높은 것은 아니다. 규제 하나가 특정 sub_issue에 매우 큰 영향을 줄 수 있다.

따라서 source별 수집 건수와 점수 반영 강도는 분리한다.

```text
언론 기사:
- 사건성, 반복성, 외부 평판, 산업 baseline signal에 강함

전문기관 자료:
- 신용평가, ESG 평가, 지배구조, 산업위험 판단에 강함

규제 프레임:
- 법적 의무, 규제 대응 비용, 고객사 요구, 공시 의무에 강함
```

### 9.3 Source Weight

MVP source_weight는 다음을 기본값으로 한다.

| source_type | weight | 설명 |
|---|---:|---|
| news_article | 1.00 | 언론 기사 |
| professional_institution | 1.20 | KCGS, KIS, 기업지배구조보고서 등 |
| regulation_frame | 1.30 | CSDDD, CBAM, CSRD, ESRS |

### 9.4 Evidence Strength

| 점수 | 기준 |
|---:|---|
| 0 | 근거 없음 |
| 1 | 단순 언급 |
| 2 | 관련 내용이 있으나 영향 불명확 |
| 3 | sub_issue와 명확히 연결된 사건/자료 |
| 4 | 반복적으로 관측되거나 정량/규제 근거 존재 |
| 5 | 직접적 규제, 벌금, 사고, 평가 하락, 고객사 요구 등 강한 근거 |

### 9.5 Mapping Confidence

LLM 또는 dictionary matching이 해당 evidence를 62개 sub_issue에 매핑한 신뢰도다.

```text
0.00 ~ 1.00
```

점수 계산에는 보수적으로 사용한다.

```text
adjusted_signal = raw_signal * mapping_confidence
```

단, mapping_confidence가 0.6 미만이면 UI 반영 대상에서는 제외하거나 검토 상태로 둔다.

### 9.6 Media Signal 산식

```text
media_raw_signal_0_5
= source_weight
* evidence_strength
* mapping_confidence
```

source_weight 때문에 5를 초과할 수 있으므로 clamp한다.

```python
media_raw_signal_0_5 = min(5.0, media_raw_signal_0_5)
```

이 raw signal을 Financial/Impact 루브릭 요소로 변환한다.

```text
media_financial_score:
- evidence가 규제/벌금/비용/수주/신용도에 연결되면 Financial magnitude 상승
- source_type이 regulation_frame 또는 professional_institution이면 Financial 가중 해석 가능

media_impact_score:
- evidence가 환경/사회/인권/안전/고객/공급망 영향에 연결되면 Impact scale/scope 상승
- 사건성 기사, 고객 안전, 환경사고, 협력사 인권 이슈는 Impact 가중 해석 가능
```

MVP 간소화 산식:

```text
media_financial_score
= media_raw_signal_0_5 * financial_relevance_factor + context_modifier

media_impact_score
= media_raw_signal_0_5 * impact_relevance_factor + context_modifier
```

`financial_relevance_factor`, `impact_relevance_factor`는 sub_issue baseline과 source_type으로 결정한다.

### 9.7 규제 프레임 고정 매핑 예시

| 규제 | 주요 sub_issue | Financial 영향 | Impact 영향 |
|---|---|---:|---:|
| CSDDD | 공급망 감사·시정조치, 인권, 협력사 관리 | 높음 | 높음 |
| CBAM | 탄소배출, 전환계획, Scope 3, 공급망 탄소 | 중간~높음 | 중간~높음 |
| CSRD | 공시 투명성, 데이터 관리, ESG governance | 중간 | 중간 |
| ESRS | 환경/사회 공시 전반, 이중중대성, 데이터 품질 | 중간 | 중간~높음 |

### 9.8 미디어 저장 데이터

`ESG_DMA_SIGNAL_DETAIL` 예시:

```json
{
  "source_step": "media_external",
  "source_type": "regulation_frame",
  "source_name": "CSDDD",
  "sub_issue_code": "S_SUPPLY_CHAIN_AUDIT_CORRECTIVE_ACTION",
  "evidence_strength": 5,
  "mapping_confidence": 0.95,
  "financial_magnitude_hint": 4,
  "financial_likelihood_hint": 5,
  "impact_scale_hint": 4,
  "impact_scope_hint": 4,
  "evidence_summary": "EU 공급망 실사 규제에 따라 협력사 ESG 감사 및 시정조치 관리 필요성이 증가함"
}
```

`ESG_DMA_SCORE_SUMMARY` 집계 필드:

```text
media_external_impact_score
media_external_financial_score
```

---

## 10. 이해관계자 설문 점수 산정 방식 v1

### 10.1 설문 입력

이해관계자 설문은 3개 그룹으로 구분한다.

```text
1. 임직원
2. 경영진
3. 외부 이해관계자
```

설문은 원칙적으로 Impact와 Financial을 분리해서 묻는다.

```text
Impact 문항 예:
이 이슈가 환경·사회·이해관계자에 미치는 영향은 얼마나 중요하다고 보십니까?

Financial 문항 예:
이 이슈가 회사의 매출, 비용, 투자, 리스크, 사업기회에 미치는 영향은 얼마나 크다고 보십니까?
```

응답 스케일은 MVP 기준 1~5점이다.

### 10.2 그룹 가중치

MVP 기본값은 다음과 같다.

| 그룹 | weight | 설명 |
|---|---:|---|
| 임직원 | 0.30 | 현장/조직 내부 영향 인식 |
| 경영진 | 0.35 | 전략/재무/리스크 판단 |
| 외부 이해관계자 | 0.35 | 외부 사회적 기대와 영향 인식 |

### 10.3 설문 점수 산식

```text
survey_impact_score
= 0.30 * employee_impact_avg
+ 0.35 * executive_impact_avg
+ 0.35 * external_impact_avg

survey_financial_score
= 0.30 * employee_financial_avg
+ 0.35 * executive_financial_avg
+ 0.35 * external_financial_avg
```

각 평균은 1~5 응답 평균이다. 내부 0~5 스케일과 맞추기 위해 1점 응답을 그대로 1로 쓰는 방식이 가능하다. 단, 0점은 “해당 없음/미관측”일 때만 사용한다.

### 10.4 설문 응답 수 보정

MVP에서는 복잡한 통계 보정은 제외한다. 단, 응답 수가 지나치게 낮은 그룹은 경고를 표시할 수 있다.

```text
응답 수가 목표의 50% 미만인 그룹:
- UI에 응답 부족 표시
- 점수는 산출하되 신뢰도 낮음 표시
```

DB에 설문 발송 대상 수가 없는 경우, 목표 응답 수는 config 또는 프론트 설정값으로 관리한다.

### 10.5 설문 저장 데이터

`ESG_DMA_SURVEY_RESPONSE`에는 다음 성격의 데이터가 필요하다.

```text
run_id
respondent_group
sub_issue_code
question_axis: impact / financial
score_value: 1~5
```

`ESG_DMA_SCORE_SUMMARY` 집계 필드:

```text
survey_impact_score
survey_financial_score
```

---

## 11. 최종 점수 통합 방식 v1

### 11.1 기본 원칙

설문은 가장 높은 비중을 주되, 과도하게 높이지 않는다. 벤치마킹과 미디어는 각각 외부 비교와 외부 signal을 보완한다.

### 11.2 최종 Impact 산식

```text
final_impact_score
= 0.36 * survey_impact_score
+ 0.32 * benchmark_impact_score
+ 0.32 * media_external_impact_score
```

### 11.3 최종 Financial 산식

```text
final_financial_score
= 0.36 * survey_financial_score
+ 0.32 * benchmark_financial_score
+ 0.32 * media_external_financial_score
```

### 11.4 최종 종합 점수

최종 순위 산정용 `final_score`는 Impact와 Financial을 동일 비중으로 합산한다.

```text
final_score
= 0.50 * final_impact_score
+ 0.50 * final_financial_score
```

향후 조정 가능성:

```text
- 환경/사회 영향 중심 보고서이면 Impact 비중을 0.55까지 상향 가능
- 투자자/재무리스크 중심 프로젝트이면 Financial 비중을 0.55까지 상향 가능
- MVP에서는 0.50/0.50 고정
```

### 11.5 후보군 및 최종 선정

```text
1. 62개 sub_issue 전체에 final_impact_score, final_financial_score 계산
2. final_score 기준 Top 20~25 후보군 생성
3. High-High 영역 이슈 우선 고려
4. 한 축이 높고 다른 축이 중간 이상인 이슈 포함 가능
5. 최종 10개 또는 MVP 5개 이슈 선정
```

MVP에서는 이미 5개 이슈가 선정되는 결과를 보여줄 수 있으므로, scoring은 그 결과를 설명 가능한 형태로 맞추는 것이 중요하다.

---

## 12. DB 저장 구조 v1

### 12.1 핵심 테이블

현재 MVP에서 사용해야 하는 DMA 핵심 테이블은 다음이다.

```text
ESG_MATERIALITY_RUN
ESG_DMA_CONTEXT_PROFILE
ESG_DMA_SIGNAL_DETAIL
ESG_DMA_SCORE_SUMMARY
ESG_MATERIALITY_SELECTED_SUB_ISSUE
ESG_DMA_SURVEY_QUESTION
ESG_DMA_SURVEY_RESPONSE
```

### 12.2 ESG_MATERIALITY_RUN

평가 실행 단위다.

권장 저장값:

```text
run_id
company_id
reporting_year
industry_profile
scoring_version_code = DMA_SCORING_V1
weighting_config_json
run_status
created_at
```

`weighting_config_json` 예시:

```json
{
  "stage_weights": {
    "survey": 0.36,
    "benchmark": 0.32,
    "media_external": 0.32
  },
  "financial_formula": {
    "risk": {"magnitude": 0.45, "likelihood": 0.35, "time_urgency": 0.20},
    "opportunity": {"magnitude": 0.55, "likelihood": 0.25, "time_urgency": 0.20}
  },
  "impact_formula": {
    "negative": {"scale": 0.30, "scope": 0.25, "likelihood": 0.20, "irremediability": 0.15, "time_urgency": 0.10},
    "positive": {"scale": 0.35, "scope": 0.30, "likelihood": 0.25, "time_urgency": 0.10}
  },
  "context_modifier_range": [-0.5, 0.5]
}
```

### 12.3 ESG_DMA_CONTEXT_PROFILE

회사 상황 및 산업 baseline 보정값을 저장한다.

권장 저장값:

```text
run_id
company_id
industry_profile
business_model
value_chain_summary
revenue_context_json
regulatory_exposure_json
context_modifier_json
iro_horizon_hint_json
```

### 12.4 ESG_DMA_SIGNAL_DETAIL

벤치마킹/미디어/설문 source별 signal 상세를 저장한다.

권장 저장값:

```text
run_id
source_step
source_type
source_name
sub_issue_code
mapping_confidence
impact_axis_json
financial_axis_json
evidence_summary
evidence_ref_id
raw_signal_score
created_at
```

`impact_axis_json` 예시:

```json
{
  "direction": "negative",
  "actuality": "potential",
  "time_horizon": "short",
  "scale": 4,
  "scope": 4,
  "likelihood": 5,
  "irremediability": 3,
  "time_urgency": 4
}
```

`financial_axis_json` 예시:

```json
{
  "iro_type": "risk",
  "time_horizon": "short",
  "magnitude": 4,
  "likelihood": 5,
  "time_urgency": 4,
  "revenue_impact_ratio_hint": "0.20%~1.00%",
  "basis": "regulatory compliance cost and customer requirement risk"
}
```

### 12.5 ESG_DMA_SCORE_SUMMARY

62개 sub_issue별 단계 점수와 최종 점수를 저장한다.

권장 저장값:

```text
run_id
sub_issue_code
benchmark_impact_score
benchmark_financial_score
media_external_impact_score
media_external_financial_score
survey_impact_score
survey_financial_score
final_impact_score
final_financial_score
final_score
rank_no
score_explain_json
```

`score_explain_json` 예시:

```json
{
  "primary_drivers": ["survey", "media_external", "benchmark"],
  "financial_reason": "CSDDD regulation and OEM customer requirements increase compliance cost and supplier audit burden.",
  "impact_reason": "Supplier audit and corrective action affect labor, human rights, and environmental management across the value chain.",
  "context_modifier": 0.4
}
```

### 12.6 ESG_MATERIALITY_SELECTED_SUB_ISSUE

최종 선정된 sub_issue를 저장한다.

권장 저장값:

```text
run_id
sub_issue_code
selection_rank
final_impact_score
final_financial_score
final_score
selection_reason
selected_yn
created_at
```

---

## 13. UI 매핑 기준

### 13.1 벤치마킹 결과 UI

UI 구성:

```text
상단 카드:
- 분석 보고서 수
- 식별 이슈 수
- 공통 이슈 수
- 자사 Blind Spot 수

표 1:
- 벤치마킹 Top 이슈 점수
- 순위 / Sub Issue / Impact / Financial

표 2:
- 공통 선정 이슈
- Sub Issue / 리더 / 피어 / 자사

패널:
- 자사 Blind Spot 요약
```

DB 매핑:

```text
ESG_DMA_SIGNAL_DETAIL
ESG_DMA_SCORE_SUMMARY
ESG_SUB_ISSUE_MASTER
```

주의:

```text
리더/피어/자사별 점수를 보여주지 않는다.
관측 여부만 보여준다.
```

### 13.2 미디어 분석 결과 UI

UI 구성:

```text
상단 카드:
- 언론 기사 수
- 전문기관 자료 수
- 규제 프레임 수
- 종합 관측 이슈 수

표 1:
- Source별 반영 현황

표 2:
- 미디어 Top 이슈 점수
- 순위 / Sub Issue / Impact / Financial / Source / Evidence

패널:
- 반영 방식 안내
```

DB 매핑:

```text
ESG_DMA_SIGNAL_DETAIL
ESG_DMA_SCORE_SUMMARY
ESG_DMA_EVIDENCE
```

주의:

```text
자사 직접 기사/산업 기사 분리를 전면 노출하지 않는다.
MVP에서는 언론 기사 전체 + 관측 이슈 형태로 표현한다.
전문기관과 규제는 적은 자료 수라도 반영 강도가 높을 수 있음을 설명한다.
```

### 13.3 이해관계자 설문 결과 UI

UI 구성:

```text
상단 카드:
- 임직원 응답 수
- 경영진 응답 수
- 외부 응답 수
- 전체 응답률

표:
- 설문 Top 이슈 점수
- 순위 / Sub Issue / Total Impact / Total Financial / 임직원 Impact·Financial / 경영진 Impact·Financial / 외부 Impact·Financial

패널:
- 이해관계자 그룹별 관점 차이
```

DB 매핑:

```text
ESG_DMA_SURVEY_RESPONSE
ESG_DMA_SURVEY_QUESTION
ESG_DMA_SCORE_SUMMARY
```

주의:

```text
발송 목표 수는 DB에 별도 campaign/recipient 테이블이 없으면 config로 관리한다.
```

### 13.4 전체 결과 UI

UI 구성:

```text
- 최종 선정 요약
- Top 이슈 점수 분해
- 분석축 기여도
- 후보군 → 최종 선정 과정
- 최종 선정/제외 사유
- 필요 온보딩 지표
```

DB 매핑:

```text
ESG_DMA_SCORE_SUMMARY
ESG_MATERIALITY_SELECTED_SUB_ISSUE
ESG_SUB_ISSUE_ATOMIC_MAP
ESG_ATOMIC_METRIC_MASTER
```

### 13.5 보고서 생성 UI

MVP 범위:

```text
- 보고서 생성 확인 1개 탭만 운영
- 5개 이슈별 보고서 페이지 생성
- AI 원문/수정본 분리 저장
- AI 원문 기준 데이터 추적
- 그룹 통합 지표 / 직접 지표 유형별 데이터 추적 패널
- PDF/DOCX 다운로드
```

MVP 제외:

```text
- Fact Data Book
- 온보딩 데이터 이상치 점검
- 수정본 기준 근거 재추적
```

---

## 14. 보고서 생성과 데이터 추적 연결

### 14.1 보고서 생성 대상 이슈

MVP 보고서 초안은 다음 5개 이슈를 대상으로 한다.

```text
1. 기후목표·전환계획
2. 공급망 감사·시정조치
3. 교육훈련·역량개발
4. 저탄소·친환경 제품
5. 소비자 건강·제품안전
```

### 14.2 보고서 데이터 추적 원칙

```text
1. 보고서 본문에는 내부 DB 용어를 노출하지 않는다.
2. 회사 스코프, 롤업 방식, source table은 본문에 넣지 않는다.
3. 데이터 추적 패널에서만 metric_id, atomic_metric_id, 회사별 구성, 계산식을 보여준다.
4. 수정본은 MVP에서 추적하지 않는다. AI 원문 기준으로만 trace한다.
```

### 14.3 ESG_REPORT_SECTION_DRAFT 추가 컬럼

보고서 수정 기능을 위해 다음 컬럼 추가가 필요하다.

```sql
ALTER TABLE ESG_REPORT_SECTION_DRAFT
  ADD COLUMN original_generated_text LONGTEXT NULL COMMENT 'AI 최초 생성 원문',
  ADD COLUMN edited_text LONGTEXT NULL COMMENT '사용자 편집본',
  ADD COLUMN last_edited_by_user_id BIGINT NULL COMMENT '마지막 수정 사용자 ID',
  ADD COLUMN last_edited_at DATETIME NULL COMMENT '마지막 수정 일시';
```

표시 규칙:

```text
표시 텍스트 = edited_text가 있으면 edited_text, 없으면 original_generated_text
근거 추적 = original_generated_text 기준으로만 수행
```

### 14.4 ESG_REPORT_REFERENCE trace_label_json

문장/구절 hover trace는 별도 테이블을 만들지 않고, `ESG_REPORT_REFERENCE.trace_label_json`에 저장한다.

예시:

```json
{
  "used_text": "전년 대비 4.2% 감축",
  "metric_id": "E1-06",
  "atomic_metric_id": "E1-06__G0005",
  "reference_type": "rollup_result",
  "reference_id": 102,
  "display_label": "연결 전년 대비 온실가스 감축률",
  "value_2024": 4.2,
  "unit": "%",
  "rationale": "온실가스 감축 성과를 직접 설명하는 핵심 수치이므로 본 문장에 사용되었습니다."
}
```

---

## 15. 에이전트 역할 분담

### 15.1 Context Agent

```text
입력:
- G0 회사 일반정보
- 가치사슬 설명
- 재무 지표
- 사업장/법인 정보
- 산업 baseline

출력:
- ESG_DMA_CONTEXT_PROFILE
- context_modifier_json
- iro_horizon_hint_json
```

### 15.2 Dictionary Mapper Agent

```text
입력:
- 텍스트 chunk
- 62개 sub_issue dictionary

출력:
- sub_issue_code
- mapping_confidence
- evidence_span
- rationale
```

### 15.3 IRO Hint Agent

```text
입력:
- evidence_span
- sub_issue definition
- context profile

출력:
- financial risk/opportunity hint
- positive/negative impact hint
- time_horizon hint
- likelihood hint
```

### 15.4 Scoring Engine

```text
입력:
- IRO hint
- source type
- evidence strength
- mapping confidence
- context modifier
- financial/impact rubric

출력:
- Financial axis scores
- Impact axis scores
- stage score
```

### 15.5 Aggregation Engine

```text
입력:
- benchmark score
- media score
- survey score

출력:
- final_impact_score
- final_financial_score
- final_score
- rank_no
```

### 15.6 Judge Agent

```text
입력:
- score detail
- evidence
- rubric 기준

출력:
- pass/revise/reject
- reason
```

Judge Agent는 MVP에서는 필수는 아니지만, 점수 설명 품질 검증용으로 남겨둘 수 있다.

---

## 16. API Input/Output 설계안

### 16.1 Context Profile API

```http
POST /dma/context-profile
```

Input:

```json
{
  "company_id": 6,
  "reporting_year": 2024,
  "industry_profile": "automotive_parts",
  "use_onboarding_g0": true
}
```

Output:

```json
{
  "run_id": 1,
  "context_profile_id": 10,
  "industry_profile": "automotive_parts_manufacturing",
  "context_modifier_by_sub_issue": {
    "E_CLIMATE_TARGETS_TRANSITION": 0.2,
    "S_SUPPLY_CHAIN_AUDIT_CORRECTIVE_ACTION": 0.4
  }
}
```

### 16.2 Benchmark Score API

```http
POST /dma/benchmark/analyze
```

Input:

```json
{
  "run_id": 1,
  "source_files": [1, 2, 3],
  "issue_dictionary_version": "SUB_ISSUE_62_V1"
}
```

Output:

```json
{
  "observed_issue_count": 28,
  "common_issue_count": 19,
  "blind_spot_count": 9,
  "top_scores": [
    {
      "sub_issue_code": "E_CLIMATE_TARGETS_TRANSITION",
      "benchmark_impact_score": 4.6,
      "benchmark_financial_score": 4.35
    }
  ]
}
```

### 16.3 Media Score API

```http
POST /dma/media/analyze
```

Input:

```json
{
  "run_id": 1,
  "news_count": 78,
  "institution_sources": ["KCGS", "KIS", "Corporate Governance Report"],
  "regulation_frames": ["CSDDD", "CBAM", "CSRD", "ESRS"]
}
```

Output:

```json
{
  "news_count": 78,
  "institution_count": 4,
  "regulation_count": 4,
  "observed_issue_count": 21,
  "top_scores": [
    {
      "sub_issue_code": "S_PRODUCT_SAFETY_QUALITY",
      "media_impact_score": 4.2,
      "media_financial_score": 4.5,
      "primary_source": "news/regulation"
    }
  ]
}
```

### 16.4 Survey Score API

```http
POST /dma/survey/aggregate
```

Input:

```json
{
  "run_id": 1,
  "survey_response_batch_id": 20
}
```

Output:

```json
{
  "employee_count": 124,
  "executive_count": 18,
  "external_count": 45,
  "top_scores": [
    {
      "sub_issue_code": "E_CLIMATE_TARGETS_TRANSITION",
      "survey_impact_score": 4.7,
      "survey_financial_score": 4.4
    }
  ]
}
```

### 16.5 Final Score API

```http
POST /dma/finalize
```

Input:

```json
{
  "run_id": 1,
  "selection_count": 10,
  "mvp_fixed_issue_count": 5
}
```

Output:

```json
{
  "evaluated_sub_issue_count": 62,
  "candidate_count": 25,
  "selected_count": 10,
  "selected_issues": [
    {
      "rank_no": 1,
      "sub_issue_code": "E_CLIMATE_TARGETS_TRANSITION",
      "final_impact_score": 4.61,
      "final_financial_score": 4.75,
      "final_score": 4.68
    }
  ]
}
```

---

## 17. 구현 우선순위

### 17.1 1차 MVP 필수

```text
1. 62개 sub_issue dictionary 실제 로드
2. G0 기반 context profile 생성
3. Financial/Impact 0~5 루브릭 고정
4. 벤치마킹 source별 관측 여부 계산
5. 미디어 source별 signal 계산
6. 설문 group별 Impact/Financial 평균 계산
7. ESG_DMA_SCORE_SUMMARY 저장
8. 최종 결과 UI에 필요한 DTO 제공
```

### 17.2 1차 MVP에서 제외

```text
1. 대규모 규제 자동 탐색
2. MSCI/S&P/EcoVadis 유료 데이터 직접 반영
3. 고급 통계 기반 설문 보정
4. 이상치 탐지
5. Fact Data Book
6. 수정본 근거 재추적
```

### 17.3 2차 고도화

```text
1. 산업별 baseline 확장
2. 규제 자동 탐색 및 업데이트
3. source 신뢰도 자동 평가
4. score explain 자동 생성 고도화
5. 데이터 품질/이상치 탐지
6. 보고서 근거 trace 세분화
```

---

## 18. 코드 수정 방향

### 18.1 `dma_engine.py`

현재 schema에 다음을 추가 또는 확장한다.

```python
class FinancialRubricEvaluation(BaseModel):
    iro_type: Literal["risk", "opportunity"]
    magnitude: int = Field(..., ge=0, le=5)
    likelihood: int = Field(..., ge=0, le=5)
    time_urgency: int = Field(..., ge=0, le=5)
    time_horizon: Literal["short", "mid", "long", "unknown"]
    rationale: str

class ImpactRubricEvaluation(BaseModel):
    direction: Literal["positive", "negative"]
    actuality: Literal["actual", "potential", "unknown"]
    scale: int = Field(..., ge=0, le=5)
    scope: int = Field(..., ge=0, le=5)
    likelihood: int = Field(..., ge=0, le=5)
    irremediability: int = Field(..., ge=0, le=5)
    time_urgency: int = Field(..., ge=0, le=5)
    time_horizon: Literal["short", "mid", "long", "unknown"]
    rationale: str
```

### 18.2 `ocrai_v8.py`

역할을 줄인다.

기존:

```text
문서 업로드 + 분류 + 직접 점수 산정 + UI 변환
```

수정:

```text
문서 업로드 + evidence 추출 + sub_issue 매핑 + IRO hint 생성
```

점수 계산은 별도 `dma_scoring_service.py` 또는 `dma_engine.py`의 rule-based 함수에서 수행한다.

### 18.3 Rule-based Scoring 함수 예시

```python
def calc_financial_risk_score(magnitude, likelihood, time_urgency, context_modifier=0.0):
    score = 0.45 * magnitude + 0.35 * likelihood + 0.20 * time_urgency + context_modifier
    return max(0.0, min(5.0, score))


def calc_financial_opportunity_score(magnitude, likelihood, time_urgency, context_modifier=0.0):
    score = 0.55 * magnitude + 0.25 * likelihood + 0.20 * time_urgency + context_modifier
    return max(0.0, min(5.0, score))


def calc_negative_impact_score(scale, scope, likelihood, irremediability, time_urgency, context_modifier=0.0):
    score = (
        0.30 * scale
        + 0.25 * scope
        + 0.20 * likelihood
        + 0.15 * irremediability
        + 0.10 * time_urgency
        + context_modifier
    )
    return max(0.0, min(5.0, score))


def calc_positive_impact_score(scale, scope, likelihood, time_urgency, context_modifier=0.0):
    score = 0.35 * scale + 0.30 * scope + 0.25 * likelihood + 0.10 * time_urgency + context_modifier
    return max(0.0, min(5.0, score))
```

---

## 19. MVP 5개 이슈 점수 해석 예시

### 19.1 기후목표·전환계획

```text
Financial:
- 에너지 비용, 설비 투자, 고객사 요구, 저탄소 제품 전환과 연결
- magnitude 3~4
- likelihood 4
- time urgency 3~4

Impact:
- 온실가스 배출 감축, 기후변화 완화에 직접 영향
- scale 4
- scope 4
- likelihood 4
- time urgency 3~4
```

### 19.2 공급망 감사·시정조치

```text
Financial:
- CSDDD, 고객사 공급망 요구, 납품 리스크, 감사 비용과 연결
- magnitude 4
- likelihood 4~5
- time urgency 4

Impact:
- 협력사 노동, 인권, 환경 관리와 연결
- scale 4
- scope 4~5
- likelihood 4~5
- irremediability 3
```

### 19.3 교육훈련·역량개발

```text
Financial:
- 인력 역량, 생산성, 전환 대응 역량과 연결
- magnitude 2~3
- likelihood 3~4
- time urgency 3

Impact:
- 임직원 역량 개발, 고용 안정성, 조직 성장과 연결
- scale 3
- scope 3
- likelihood 4
```

### 19.4 저탄소·친환경 제품

```text
Financial:
- 친환경 제품 매출 확대, 고객사 전동화 요구, 시장기회와 연결
- opportunity magnitude 4
- likelihood 4
- time urgency 3~4

Impact:
- 제품 사용 단계 배출 저감, 친환경 전환에 긍정 영향
- scale 3~4
- scope 3~4
- likelihood 4
```

### 19.5 소비자 건강·제품안전

```text
Financial:
- 리콜, 품질 비용, 고객사 신뢰, 수주 리스크와 연결
- risk magnitude 4~5
- likelihood 3~4
- time urgency 4~5

Impact:
- 고객 안전, 소비자 건강, 제품책임에 직접 영향
- scale 4~5
- scope 3~4
- likelihood 3~4
- irremediability 4
```

---

## 20. QA 및 검증 기준

### 20.1 점수 검증

```text
1. 모든 sub_issue는 Financial/Impact 점수가 각각 존재해야 한다.
2. 점수는 0~5 범위여야 한다.
3. source별 점수와 최종 점수의 산식이 일관되어야 한다.
4. context_modifier는 -0.5~+0.5를 넘지 않아야 한다.
5. 벤치마킹은 리더/피어/자사별 점수를 생성하지 않아야 한다.
6. 미디어는 기사 수만으로 점수를 올리지 않아야 한다.
7. 설문은 Impact와 Financial 문항을 분리해야 한다.
```

### 20.2 근거 검증

```text
1. 3점 이상 점수는 반드시 evidence_summary가 있어야 한다.
2. 4점 이상 Financial 점수는 재무 영향 유형이 명확해야 한다.
3. 4점 이상 Impact 점수는 영향 대상과 범위가 명확해야 한다.
4. 규제 기반 점수는 규제명과 연결 sub_issue가 명확해야 한다.
5. AI가 evidence 없이 점수를 임의 생성하면 reject 처리한다.
```

### 20.3 UI 검증

```text
1. 벤치마킹 결과 UI는 관측 여부 중심이어야 한다.
2. 미디어 결과 UI는 source별 반영 현황을 보여야 한다.
3. 설문 결과 UI는 그룹별 Impact/Financial 점수를 보여야 한다.
4. 전체 결과 UI는 최종 선정 과정과 점수 분해를 보여야 한다.
5. 보고서 생성 UI는 AI 원문 기준 근거 추적만 제공해야 한다.
```

---

## 21. 확정 사항과 미확정 사항

### 21.1 확정 사항

```text
1. 내부 점수 기준은 0~5로 한다.
2. Financial과 Impact는 분리 계산한다.
3. Financial은 magnitude, likelihood, time_urgency를 사용한다.
4. Impact는 scale, scope, likelihood, irremediability, time_urgency를 사용한다.
5. Survey는 최종 통합에서 가장 높은 비중을 갖되 0.36으로 제한한다.
6. Benchmark와 Media는 각각 0.32로 둔다.
7. Context Modifier는 -0.5~+0.5로 제한한다.
8. 벤치마킹은 source별 점수가 아니라 source별 관측 여부와 sub_issue 점수를 산출한다.
9. 미디어 규제 분석은 MVP에서 CSDDD, CBAM, CSRD, ESRS 고정 rule base로 한다.
10. 보고서 생성에서는 Fact Data Book과 이상치 점검을 MVP에서 제외한다.
```

### 21.2 미확정 또는 추후 고도화 사항

```text
1. 산업별 baseline 상세 테이블화 여부
2. source 신뢰도 자동 산정 방식
3. 규제 프레임 자동 업데이트 방식
4. 설문 응답률 보정 방식
5. 외부 유료 평가기관 데이터 연동 여부
6. score explain 자동 문장 품질 검증 방식
7. 고급 이상치 탐지 및 데이터 품질 점검 기능
```

---

## 22. 최종 결론

DMA Scoring Framework v1은 “AI가 점수를 만들어내는 구조”가 아니라, “AI가 근거와 IRO 힌트를 추출하고, 고정된 실무형 루브릭과 산식이 점수를 계산하는 구조”다.

이 구조의 장점은 다음과 같다.

```text
1. 재현 가능하다.
2. 설명 가능하다.
3. UI에 점수 근거를 표시할 수 있다.
4. 벤치마킹/미디어/설문이 서로 다른 데이터임에도 같은 기준으로 통합할 수 있다.
5. 자동차부품 MVP에 맞으면서도 향후 산업별 확장이 가능하다.
6. 현재 v2 DB와 9장 UI 결과 화면, 보고서 생성 흐름과 충돌하지 않는다.
```

따라서 v1 구현의 핵심은 다음이다.

```text
G0 Context Profile 생성
+ Financial/Impact 0~5 루브릭 고정
+ Source별 signal 생성
+ Rule-based score calculation
+ ESG_DMA_SCORE_SUMMARY 저장
+ UI 결과 패널 연결
```

이 문서를 기준으로 다음 작업은 `ocrai_v8.py`, `dma_engine.py`, `12implementation_plan.md`를 `DMA_SCORING_V1` 구조에 맞춰 수정하는 것이다.
