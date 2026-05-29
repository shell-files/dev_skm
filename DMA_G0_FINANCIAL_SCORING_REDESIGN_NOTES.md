# DMA G0 Financial Scoring Redesign Notes

작성일: 2026-05-29

## 1. 문서 목적

이 문서는 G0/DMA phase1 작업 중 논의한 DMA financial scoring(재무 점수 산정) 문제, 확인한 코드/데이터 근거, 수정이 필요한 이유, 그리고 앞으로의 구현 계획을 정리한다.

핵심 결론은 다음과 같다.

- DMA signal별 financial score는 계속 필요하다.
- 다만 benchmark/media가 재무 magnitude(규모)를 하드코딩해서 만들면 안 된다.
- financial magnitude는 G0 company profile의 재무 기준값과 회사 노출도를 기준으로 산정해야 한다.
- G0에 추가할 재무 항목은 MVP 범위에서는 `G0-02` 아래로 정리한다.
- AP-E-06 등 DMA 선정 이후 할당되는 본 온보딩 지표는 DMA 선정 전 financial score 기준으로 쓰면 안 된다.

## 2. 기존 작업 범위 재정리

이번 phase의 목적은 auth/user/token 리팩토링이 아니라 G0/DMA phase1 API 연결과 router 단위 smoke, G0/context API 보강이었다.

기존에 보호하기로 한 영역은 다음과 같다.

- 기존 auth/user/token/kafa 도메인
- 기존 `model.py` 인증/사용자 DTO
- 기존 `src/utils/auth.py`
- 기존 `fastset.py`
- 기존 로그인/로그아웃 동작
- 기존 JWT/token validation 로직
- 기존 권한/회사 선택 로직

이 영역은 `skm_test` 기준과 다르면 안 되며, phase1 API 연결을 위해 auth를 고치는 방식은 금지한다.

## 3. 현재 G0/companyprofile 라우터 방향

기존 `fastset.py` prefix 규칙은 수정하지 않는 방향으로 정리했다.

현재 company profile router는 다음처럼 사용하는 방향이다.

```text
GET    /companyprofile/g0/{companyId}
POST   /companyprofile/g0/{companyId}
PATCH  /companyprofile/g0/{companyId}
GET    /companyprofile/g0/{companyId}/status
```

`/company-profile`처럼 하이픈 경로를 만들기 위해 `fastset.py`의 prefix 자동 변환을 수정하지 않는다.

## 4. 기존 DMA 점수 구조 요약

현재 DMA 점수 흐름은 대략 다음 구조다.

```text
adapter.py
-> DMASignal 생성
-> baseline 또는 AI-derived factor 부여
-> dmascoring.py에서 impact/financial 0~5 점수 계산
-> dmaaggregator.py에서 stage별 점수 집계
-> dmarepository.py에서 DB 저장, stage/final/rank 재계산
```

주요 객체는 `backend/src/models/dmaengine.py`의 `DMASignal`, `ImpactFactor`, `FinancialFactor`이다.

`FinancialFactor`는 현재 다음 재무 magnitude 후보를 가진다.

```text
revenueMagnitude
costMagnitude
capexMagnitude
assetLiabilityMagnitude
financingMagnitude
legalRegulatoryMagnitude
likelihood
timeHorizon
```

## 5. 확인한 주요 문제

### 5.1 financial magnitude가 하드코딩에 가깝다

현재 `backend/src/utils/dmascoring.py`는 `FinancialFactor`의 여러 magnitude 중 가장 큰 값을 `base_mag`로 사용한다.

```python
magnitudes = [
    factor.revenueMagnitude,
    factor.costMagnitude,
    factor.capexMagnitude,
    factor.assetLiabilityMagnitude,
    factor.financingMagnitude,
    factor.legalRegulatoryMagnitude,
]
base_mag = float(max(valid_mags)) if valid_mags else 0.0
```

문제는 `base_mag`가 어떤 항목에서 나왔는지 저장하지 않는다는 점이다.

예를 들어 `legalRegulatoryMagnitude = 5`가 가장 커서 `base_mag = 5`가 되더라도, 현재 결과에는 "규제/법무 영향이 지배적이었다"는 설명이 남지 않는다.

### 5.2 benchmark 쪽 financial factor는 회사 G0와 무관하다

`backend/src/utils/ocraiv8.py`의 `get_baseline_factors()`는 subIssueCode에 따라 `mag`를 정한다.

이후 financial factor를 만들 때 다음처럼 넣는다.

```python
FinancialFactor(
    revenueMagnitude=mag,
    costMagnitude=mag,
    capexMagnitude=0,
    assetLiabilityMagnitude=0,
    financingMagnitude=0,
    legalRegulatoryMagnitude=0,
)
```

즉 회사의 매출, 영업이익, 순이익, CAPEX 등 G0 재무값과 연결되지 않는다.

### 5.3 media baseline도 일부 subIssue에 하드코딩 magnitude를 넣는다

`backend/src/services/medias/baseline.py`에는 다음 같은 baseline이 있다.

```python
FinancialFactor(financialIroType="risk", revenueMagnitude=4, likelihood=4)
FinancialFactor(financialIroType="risk", legalRegulatoryMagnitude=5, likelihood=4)
```

이 방식은 "이 subIssue는 기본적으로 4점/5점"이라는 형태가 되어 회사별 financial materiality(재무 중대성) 설명력이 약하다.

### 5.4 AI가 최종 financial score를 계산하면 안 된다

현재 방향은 다음처럼 정리했다.

```text
AI 역할:
- 문서/뉴스/보고서에서 이슈 추출
- subIssue 후보 매핑
- evidence span 추출
- IRO/time horizon hint 제공 가능

rule engine 역할:
- G0 재무값 읽기
- subIssue별 financial channel 결정
- revenue/cost/capex/legal 등 magnitude 산정
- final financial score 계산
```

AI가 `legalRegulatoryMagnitude = 5` 같은 최종 factor를 직접 결정하면 재현성과 감사 추적성이 약해진다.

### 5.5 AP-E-06 등 본 온보딩 지표는 DMA 전 scoring 기준으로 쓰면 안 된다

풀버전 엑셀에는 다음 항목이 있다.

```text
AP-E-06__Q0001 친환경 제품 매출액
AP-E-06__R0001 전체 매출액 참조
AP-E-06__D0001 친환경 제품 매출 비중
```

그러나 이 항목들은 DMA에서 해당 subIssue가 최종 선정된 뒤 할당되는 본 온보딩 지표 성격이다.

따라서 DMA 선정 전 financial score 기준으로 사용하면 다음 순서가 뒤집힌다.

```text
정상:
DMA 이슈 선정 -> 선정 이슈에 온보딩 지표 할당

문제:
선정 이후 온보딩 지표 -> DMA 이슈 선정 점수 산정
```

따라서 DMA 전 financial scoring에는 G0 항목만 사용해야 한다.

### 5.6 survey group weight가 impact/financial로 분리되어 있지 않다

현재 survey group weight는 하나만 있다.

```python
SURVEY_GROUP_WEIGHTS = {
    "employee": 0.30,
    "management": 0.40,
    "external": 0.30,
}
```

그리고 survey score가 impact와 financial에 동일하게 들어간다.

실무적으로는 다음처럼 분리하는 것이 더 자연스럽다.

```text
Impact:
- employee, external 이해관계자 비중 높음

Financial:
- management, investor/regulator 등 external 일부 비중 높음
```

다만 현재 respondent group은 `employee`, `management`, `external` 정도라 external 세분화가 먼저 필요할 수 있다.

### 5.7 commonSelection과 blindSpot bonus가 동일하다

benchmark aggregation에서 현재 두 조건 모두 `+0.10`이다.

```python
if commonSelection:
    benchmarkSignal += 0.10

if blindSpot:
    benchmarkSignal += 0.10
```

두 개념은 성격이 다르다.

- `commonSelection`: 리더/피어가 공통적으로 다루는 산업 공통 중요도
- `blindSpot`: 리더/피어는 다루는데 자사는 다루지 않는 공시/관리 공백

따라서 같은 가산점으로 처리하기보다 분리된 가중치나 별도 flag로 관리하는 것이 더 좋다.

## 6. 확인한 데이터 근거

### 6.1 현재 MVP SQL

확인 파일:

```text
SKM_ESG_v5_2_28_table.sql
SKM_ESG_v5_2_dummy_Data.sql
```

현재 MVP G0 재무 항목은 다음 정도다.

```text
G0-02__Q0001 매출액
G0-02__Q0002 영업이익
G0-02__G0001 연결 매출액
G0-02__G0002 연결 영업이익
```

테이블 구조상 신규 컬럼 추가는 필요 없어 보인다.

주요 테이블:

```text
ESG_ATOMIC_METRIC_MASTER
ESG_ONBOARDING_INPUT_VALUE
ESG_KPI_FACT
ESG_GROUP_ROLLUP_RESULT
ESG_CALCULATION_RULE
ESG_CALCULATION_RULE_SOURCE
```

`ESG_DMA_SIGNAL_DETAIL`에는 이미 signal별 financial channel 저장 컬럼이 있다.

```text
financial_revenue
financial_cost
financial_capex
financial_asset_liability
financial_financing
financial_legal_regulatory
financial_likelihood
financial_score
```

### 6.2 풀버전 엑셀

확인 파일:

```text
C:/Users/leeej/Downloads/05_QUANT_DB_LOAD_LONG.xlsx
```

시트:

```text
05_QUANT_DB_LOAD_LONG
```

주요 컬럼:

```text
company_id
company_name
company_type
region_scope
consolidation_role
metric_id
metric_name
atomic_metric_id
atomic_metric_name
data_value_type
atomic_data_role
reporting_year
value_numeric
value_text
unit
dimension_values
db_load_target_yn
report_generation_use_yn
mapping_qa_status
value_generation_method
```

풀버전에서 DMA 전 G0 financial scoring 후보로 확인한 항목:

```text
G0-24__A0001 매출액
G0-25__A0001 영업이익
G0-26__A0001 당기순이익
G0-31__A0001 capex
G0-32__A0001 depreciation
```

풀버전에서 명확하게 확인되지 않은 항목:

```text
총자산
총부채
차입금
이자비용
현금
```

따라서 이번 MVP 확장에는 위 항목들은 넣지 않는다.

## 7. 결정한 G0 재무 항목 매핑

MVP에서는 풀버전 ID를 그대로 쓰지 않고, 현재 MVP의 `G0-02 재무 개요` 아래로 정리한다.

```text
풀버전 -> MVP

G0-24__A0001 매출액       -> G0-02__Q0001 매출액
G0-25__A0001 영업이익     -> G0-02__Q0002 영업이익
G0-26__A0001 당기순이익   -> G0-02__Q0003 당기순이익
G0-31__A0001 capex        -> G0-02__Q0004 CAPEX
G0-32__A0001 depreciation -> G0-02__Q0005 감가상각비
```

연결 기준 항목:

```text
G0-02__G0001 연결 매출액
G0-02__G0002 연결 영업이익
G0-02__G0003 연결 당기순이익
G0-02__G0004 연결 CAPEX
G0-02__G0005 연결 감가상각비
```

단위 변환:

```text
풀버전 엑셀 단위: KRW_bn
MVP DB 단위: KRW
변환: value_numeric * 1,000,000,000
```

## 8. 추가 작업 범위

### 8.1 테이블 컬럼 추가 여부

현재 판단으로는 컬럼 추가는 필요 없다.

기존 범용 테이블에 row를 추가한다.

### 8.2 ESG_ATOMIC_METRIC_MASTER

신규 input atomic 3개 추가:

```text
G0-02__Q0003 당기순이익
G0-02__Q0004 CAPEX
G0-02__Q0005 감가상각비
```

신규 group/derived atomic 3개 추가:

```text
G0-02__G0003 연결 당기순이익
G0-02__G0004 연결 CAPEX
G0-02__G0005 연결 감가상각비
```

기본 속성 방향:

```text
topic_code = G0
materiality_topic = 경영일반
sub_issue_code = NULL
metric_id = G0-02
metric_name_kr = 재무 개요
data_value_type = 정량
unit = KRW
evidence_required_yn = 0
narrative_template_owner_yn = 0
```

input 항목:

```text
atomic_data_role = INPUT
token_role = Q
onboarding_input_yn = 1
q_token_yn = 1
rollup_required_yn = 1
rollup_role = source
rollup_formula = SUM
target_db_table = esg_onboarding_input_value
```

group 항목:

```text
atomic_data_role = DERIVED
token_role = Q
onboarding_input_yn = 0
q_token_yn = 1
applicable_company_scope = A_GROUP_CONSOLIDATED
group_link_type_code = GROUP_CONSOLIDATED
rollup_required_yn = 1
rollup_role = consolidated_result
target_db_table = esg_group_rollup_result
```

### 8.3 ESG_ONBOARDING_INPUT_VALUE

신규 3개 항목에 대해 더미값 추가:

```text
3개 항목 x 3개년 x 4개 회사 = 36 rows
```

대상:

```text
G0-02__Q0003
G0-02__Q0004
G0-02__Q0005
```

기존 매출액/영업이익도 풀버전 기준으로 동기화하려면 5개 항목 전체 60 rows를 update/insert 대상으로 볼 수 있다.

### 8.4 ESG_KPI_FACT

승인 fact 흐름까지 맞추려면 신규 36 rows를 추가한다.

G0 API는 `ESG_ONBOARDING_INPUT_VALUE`를 우선 읽지만, 승인/정합성 흐름을 맞추려면 `ESG_KPI_FACT`도 같이 넣는 것이 좋다.

### 8.5 ESG_GROUP_ROLLUP_RESULT

연결 기준 financial scoring을 위해 신규 3개 연결 항목의 3개년 rollup 결과를 추가한다.

```text
3개 연결 항목 x 3개년 = 9 rows
```

대상:

```text
G0-02__G0003 연결 당기순이익
G0-02__G0004 연결 CAPEX
G0-02__G0005 연결 감가상각비
```

각 값은 4개 회사 entity 값을 합산한다.

### 8.6 ESG_CALCULATION_RULE

연결 롤업 재계산용 rule 3개 추가:

```text
CR_G0_02_G0003: SUM(entity net income)
CR_G0_02_G0004: SUM(entity capex)
CR_G0_02_G0005: SUM(entity depreciation)
```

### 8.7 ESG_CALCULATION_RULE_SOURCE

rule source mapping 3개 추가:

```text
CR_G0_02_G0003 -> G0-02__Q0003
CR_G0_02_G0004 -> G0-02__Q0004
CR_G0_02_G0005 -> G0-02__Q0005
```

### 8.8 ESG_SUB_ISSUE_ATOMIC_MAP

추가하지 않는다.

이유:

- G0-02는 DMA 이후 특정 subIssue에 할당되는 본 온보딩 지표가 아니다.
- `sub_issue_code = NULL`로 유지한다.
- `ESG_SUB_ISSUE_ATOMIC_MAP`에 넣지 않으면 보고서 생성/선정 이슈 지표 할당에 섞이지 않는다.

## 9. G0 status 영향

현재 G0 API status는 `onboarding_input_yn`을 required 여부로 본다.

즉 `ESG_ATOMIC_METRIC_MASTER.onboarding_input_yn = 1`인 항목이 required item이다.

값이 없으면:

```text
필수 항목 수 > 입력 완료 항목 수
-> g0ProfileStatus = IN_PROGRESS
```

이번 추가 항목은 G0/DMA financial scoring에 필요하므로 `onboarding_input_yn = 1`로 두는 것이 맞다.

단, 3개년 x 4개 회사 더미값을 모두 넣어야 기존 G0 status가 깨지지 않는다.

## 10. financial_exposure 계산기 방향

DB에 G0 값을 추가하는 것만으로 financial score가 자동 개선되지는 않는다.

별도 계산기가 필요하다.

예상 신규 파일:

```text
backend/src/services/materialities/financial_exposure.py
```

또는 repository 성격을 분리한다면:

```text
backend/src/utils/dmafinancialrepository.py
backend/src/services/materialities/financial_exposure.py
```

역할:

```text
1. companyId/reportingYear/runId 기준 G0 financial basis 조회
2. revenue, operatingProfit, netIncome, capex, depreciation 구성
3. signal의 subIssueCode/sourceStep/sourceType/confidence/timeHorizon 확인
4. subIssue별 financial channel mapping 적용
5. G0 재무 기준값 대비 magnitude 산정
6. FinancialFactor 생성
7. dmascoring.py의 calculateFinancialScore로 signal financial score 계산
```

중요한 점:

- AI가 financial score를 직접 결정하지 않는다.
- benchmark/media는 evidence, mapping, 관측 강도, confidence를 제공한다.
- G0는 회사별 재무 기준값과 노출도를 제공한다.
- rule engine이 financialFactor를 산정한다.

## 11. financial score 산정 예시

예시: 제품 안전/품질 이슈

```text
signal:
- subIssueCode = S_PRODUCT_RESP__PRODUCT_SAFETY_QUALITY
- sourceStep = media_external
- confidenceScore = 0.85
- timeHorizon = short

G0:
- 연결 매출액
- 연결 영업이익
- 연결 당기순이익
- 주요 제품/서비스

rule:
- 제품 안전 이슈는 legal/regulatory, cost, revenue channel 후보
- short horizon이면 urgency 높음
- media confidence가 높으면 likelihood 보정 가능

result:
- legalRegulatoryMagnitude
- costMagnitude
- revenueMagnitude
- likelihood
- financialScore05
```

이때 magnitude는 "제품안전이면 무조건 5"가 아니라 G0 재무 기준값 대비 영향률을 바탕으로 산정해야 한다.

## 12. 앞으로의 수정 계획 요청

### 12.1 SQL/data 작업

다음 파일을 수정 대상으로 본다.

```text
SKM_ESG_v5_2_28_table.sql
SKM_ESG_v5_2_dummy_Data.sql
```

작업:

```text
1. ESG_ATOMIC_METRIC_MASTER에 G0-02 신규 Q/G atomic 추가
2. 05_QUANT_DB_LOAD_LONG.xlsx의 풀버전 값을 MVP G0-02 ID로 변환
3. ESG_ONBOARDING_INPUT_VALUE에 3개 신규 항목 36 rows 추가
4. ESG_KPI_FACT에 동일 신규 항목 36 rows 추가
5. ESG_GROUP_ROLLUP_RESULT에 신규 연결 항목 9 rows 추가
6. ESG_CALCULATION_RULE 3 rows 추가
7. ESG_CALCULATION_RULE_SOURCE 3 rows 추가
```

### 12.2 코드 작업

작업:

```text
1. G0 financial basis 조회 함수 추가
2. financial_exposure.py 신규 작성
3. benchmark/media signal 저장 전 financialFactor를 G0 기반으로 보강
4. 기존 media baseline financial hardcoding은 fallback으로 격하
5. benchmark의 ocraiv8 mag 기반 financial factor는 fallback 또는 제거 검토
6. scoring_payload_json에 financial exposure trace 저장
```

trace에 남길 정보 후보:

```text
dominantMagnitudeType
dominantMagnitudeValue
financialBasisRevenue
financialBasisOperatingProfit
financialBasisNetIncome
financialBasisCapex
financialBasisDepreciation
calculationReason
sourceConfidence
timeHorizon
```

### 12.3 후속 개선

이번 MVP 범위 이후 검토할 항목:

```text
1. 총자산/총부채/차입금/이자비용/현금 source 확보 후 G0 확장
2. survey group weight를 impact/financial로 분리
3. external respondent를 investor/regulator/customer/supplier 등으로 세분화
4. commonSelection/blindSpot bonus 분리
5. benchmark stage baseline이 signals[0]에 의존하는 문제 개선
6. base_mag max 방식 대신 weighted channel score 또는 dominant channel trace 적용
```

## 13. 작업 시 주의사항

다음 파일/영역은 이 작업을 위해 수정하지 않는다.

```text
backend/src/models/model.py
backend/src/models/auth.py
backend/src/models/user.py
backend/src/utils/auth.py
backend/src/utils/fastset.py
backend/src/utils/kafkasv.py
backend/src/utils/tokenset.py
backend/src/utils/validatetok.py
기존 로그인/로그아웃/JWT/token validation/권한/회사 선택 로직
```

G0/DMA financial scoring 작업은 기존 auth/user/token 도메인과 분리한다.

## 14. 현재 결론

이번 수정의 핵심은 다음 한 문장으로 요약된다.

```text
signal별 financial score는 유지하되, 그 점수의 재무 magnitude는 benchmark/media 하드코딩이 아니라 G0-02 재무 기준값을 기반으로 산정한다.
```

이번 MVP에서 사용할 G0 financial basis는 다음 5개로 확정한다.

```text
G0-02__Q0001 매출액
G0-02__Q0002 영업이익
G0-02__Q0003 당기순이익
G0-02__Q0004 CAPEX
G0-02__Q0005 감가상각비
```

## 15. getG0FinancialBasis() 구현 기준

`backend/src/utils/dmafinancialrepository.py`에 `getG0FinancialBasis(companyId, reportingYear, preferConsolidated=True)`를 추가한다.

목적은 DMA financial scoring redesign의 1단계로, 산식 변경 전에 회사/연도별 G0-02 재무 기준값을 안정적으로 조회하는 것이다. 이번 단계에서는 `dmascoring.py`, `dmaaggregator.py`, benchmark/media adapter를 수정하지 않는다.

```text
file: backend/src/utils/dmafinancialrepository.py
function: getG0FinancialBasis(companyId, reportingYear, preferConsolidated=True)
purpose: G0-02 financial basis 조회
```

### 15.1 사용 범위

- financial basis는 오직 `metric_id = 'G0-02'`만 사용한다.
- AP-E-06, E/S/G 본 온보딩 지표, selected subIssue 이후 할당되는 metric/atomic metric은 사용하지 않는다.
- G값과 Q값을 동시에 합산하지 않는다.
- 한 priority level에서 선택한 값만 basis로 사용한다.
- unit은 KRW로 normalize한다.
- revenue-only minimal basis를 허용하되 `trace.partialBasisYn=true`를 남긴다.

### 15.2 Atomic mapping

```text
revenue         : Q=G0-02__Q0001, G=G0-02__G0001
operatingProfit : Q=G0-02__Q0002, G=G0-02__G0002
netIncome       : Q=G0-02__Q0003, G=G0-02__G0003
capex           : Q=G0-02__Q0004, G=G0-02__G0004
depreciation    : Q=G0-02__Q0005, G=G0-02__G0005
```

### 15.3 Source priority

`preferConsolidated=True`:

```text
1. GROUP_ROLLUP_RESULT_G
2. KPI_FACT_G
3. KPI_FACT_Q
4. ONBOARDING_INPUT_Q
```

`preferConsolidated=False`:

```text
1. KPI_FACT_Q
2. ONBOARDING_INPUT_Q
3. GROUP_ROLLUP_RESULT_G
4. KPI_FACT_G
```

5개 field 중 3개 이상 존재하면 해당 priority를 채택한다. 2개 이하이면 다음 priority로 fallback하되, 모든 priority가 충분하지 않고 revenue가 있는 후보가 있으면 최소 basis로 사용할 수 있으며 `trace.partialBasisYn=true`를 남긴다.

### 15.4 Return contract

반환 field는 camelCase를 사용한다.

```json
{
  "companyId": 6,
  "reportingYear": 2025,
  "basisType": "CONSOLIDATED",
  "basisSource": "ESG_GROUP_ROLLUP_RESULT",
  "fallbackUsedYn": false,
  "unit": "KRW",
  "revenue": 12300000000000,
  "operatingProfit": 800000000000,
  "netIncome": 500000000000,
  "capex": 900000000000,
  "depreciation": 300000000000,
  "missingFields": [],
  "sourceRows": [
    {
      "sourceTable": "ESG_GROUP_ROLLUP_RESULT",
      "sourcePriority": "GROUP_ROLLUP_RESULT_G",
      "atomicMetricId": "G0-02__G0001",
      "fieldName": "revenue",
      "valueNumeric": 12300000000000,
      "unit": "KRW",
      "updatedAt": "2026-05-29T00:00:00"
    }
  ],
  "trace": {
    "priority": ["GROUP_ROLLUP_RESULT_G", "KPI_FACT_G", "KPI_FACT_Q", "ONBOARDING_INPUT_Q"],
    "selectedPriority": "GROUP_ROLLUP_RESULT_G",
    "partialBasisYn": false,
    "reason": "preferConsolidated=true and consolidated G values exist"
  }
}
```

데이터가 없으면 예외를 발생시키지 않고 `basisType="NONE"`, `missingFields` 5개, `sourceRows=[]`를 반환한다.

### 15.5 Smoke result

2026-05-29 기준 backend smoke:

- `preferConsolidated=True`, companyId 6, reportingYear 2024: `ESG_GROUP_ROLLUP_RESULT` G values 선택, `basisType=CONSOLIDATED`.
- `preferConsolidated=False`, companyId 6, reportingYear 2024: `ESG_KPI_FACT` Q values 선택, `basisType=ENTITY`.
- partial fixture: `missingFields`와 `trace.partialBasisYn=true` 확인.
- no data fixture: `basisType=NONE`, `sourceRows=[]` 확인.
- unit normalization: `KRW` 그대로, `백만원` x1,000,000, `억원` x100,000,000, unknown unit warning 확인.
- `sourceRows` trace에는 `sourcePriority`, `updatedAt`을 포함한다.

## 16. Financial Exposure Rule Design

`getG0FinancialBasis()` 다음 단계는 바로 구현이 아니라 rule design 확정이다.

설계 문서:

```text
FINANCIAL_EXPOSURE_RULE_DESIGN_v1.md
```

문서에서 확정할 내용:

- `FinancialFactor` 6개 channel 의미와 denominator.
- ratio 기반 magnitude 0~5 변환 기준. MVP에서는 channel별 threshold를 나누지 않고 공통 threshold 하나를 사용한다.
- MVP 주요 subIssue별 financial channel mapping.
- sourceType/timeHorizon/confidence adjustment.
- `scoring_payload_json.financialExposureTrace` 구조.

유지 원칙:

- G0-02 financial basis만 사용한다.
- AP-E-06 등 DMA 이후 본 온보딩 지표는 사용하지 않는다.
- AI는 financial score를 직접 산정하지 않는다.
- rule engine이 `FinancialFactor` magnitude를 산정한다.
- `dmascoring.py`의 `calculateFinancialScore()` 산식은 유지한다.
- media/benchmark adapter 연결은 rule design 승인 후 별도 작업으로 진행한다.
- ISSB/IFRS S1, ESRS는 재무영향 범주 rationale로 사용하되, ratio threshold 자체는 SKM MVP 내부 scoring methodology로 명시한다.

### 16.1 financial_exposure.py 1차 구현

2026-05-29 기준 `backend/src/services/materialities/financial_exposure.py`를 pure function 모듈로 추가했다.

구현 함수:

```text
buildFinancialExposureForSignal()
applyG0FinancialExposure()
applyG0FinancialExposureForRun()
buildFinancialExposureForSignalWithBasis()
canApplyFinancialExposure()
ratioToMagnitude()
calculateChannelScore()
dominantMagnitude()
resolvePreferConsolidated()
```

구현 범위:

- `getG0FinancialBasis()` 결과를 입력으로 사용.
- subIssue rule mapping 기반 channel별 ratio/magnitude 산정.
- sourceType adjustment:
  - regulation: legalRegulatoryMagnitude +1, max 5
  - agency: confidence >= 0.75이면 산정된 channel +1, max 5
  - news/benchmark: 중립
  - survey: MVP 제외
- confidence cap:
  - `<0.4`: magnitude max 2, warning
  - `0.4~0.7`: magnitude max 4
- dominant magnitude trace 생성.
- `DMASignal.scoringPayloadJson.financialExposureTrace`에 trace 부착.
- `sourceRows` 외 signal trace 위치는 `updatedSignal.scoringPayloadJson.financialExposureTrace`.
- channelScores에는 `previousMagnitude`, `overrideYn`을 포함한다.
- subIssue allowed IRO guard는 `getScoringAllowedIros()`를 사용한다.
- runId wrapper는 `getMaterialityRunContext(runId)`에서 companyId/reportingYear/company_scope_type을 조회한다.
- `company_scope_type=PARENT/GROUP/HOLDING/CONSOLIDATED`이면 consolidated basis를 우선하고, `SUBSIDIARY/ENTITY/STANDALONE/COMPANY`이면 entity basis를 우선한다.

아직 연결하지 않은 항목:

- media/benchmark adapter 호출부.
- DB 저장 smoke.
- `dmascoring.py` 산식 변경.
- `FinancialFactor` DTO 변경.

