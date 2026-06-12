# NEXT CLAUDE CODE PROMPT
# DMA v1.3 Phase C2.3.1 — Media News Resolver Guard / Policy Hardening
# R1

## 0. 작업 목적

현재 `feature/DAM_score_ljb` 브랜치에는 Phase C2.3 Pure Function Foundation이 반영되어 있다.

현재까지 완료된 범위:

```text
Phase C2.0
→ media_external.news Fact-only Adapter Foundation

Phase C2.0.1
→ Nested Similarity Metadata Allowlist Sanitization

Phase C2.1
→ News Fact Shadow Replace-Active Runtime Wiring

Phase C2.1.1
→ 정상 빈 Crawl 결과 Empty Replace
→ FAILED / PARTIAL_FAILED 시 기존 활성 Shadow Set 보호

Phase C2.1.2
→ 기사 존재 + 일부 Source FAILED 시
   Legacy 저장 유지
   Shadow Replace Skip

Phase C2.2
→ Event Fact Resolver / Canonical IRO / Event Dedup 계약 설계
→ Partial Crawl 회귀 테스트 1건 추가

Phase C2.3
→ media_event_resolver_policy.json 추가
→ Event Resolution Trace DTO 추가
→ Pure Resolver 3개 구현
→ ScoringPayloadV13.eventResolutionTrace 추가
```

현재 원격 기준 Branch / HEAD:

```text
branch:
feature/DAM_score_ljb

HEAD:
fbc4c29077d3a7a2a20752afe21f7179dc7e6036
```

하지만 C2.3 원격 Commit에는 아래 안전성 결함이 남아 있다.

```text
1. backend/.gitignore에 tests/가 추가되어 신규 테스트 파일이 Git Tracking에서 누락됨
2. 신규 C2.3 테스트 36건이 원격 Repository에 없음
3. Registry / Test 주석이 5 policy files로 남아 있음
4. media_event_resolver_policy.json 필수 Key 검증이 없음
5. 확률 Band 경계가 inclusive-inclusive라서 0.05, 0.20, 0.50, 0.80 경계 해석이 불명확함
6. Event Dedup이 subIssueCode + eventType + 월 단위 날짜만으로 자동 MERGED 처리되어 과병합 위험이 있음
7. Dedup Date Bucket 우선순위가 deadlineDate → effectiveDate → eventDate로 되어 있어 사건 식별 목적과 맞지 않음
8. ratioValue 단위 계약이 불명확함
9. impactScopeRules는 존재하지만 ExtractedFactsV13에 scopeValue가 없어 Dead Config 상태임
10. C3.0 KCGS 문서의 점수 방향과 screening_policy.json gradeRisk 방향이 충돌함
```

이번 단계는 **Phase C2.3.1 Guard / Policy Hardening**이다.

이번 단계에서는 Runtime Wiring으로 넘어가지 않는다.

```text
금지:
- runMediaAnalysis() Canonical Runtime 연결
- Canonical Shadow Namespace 추가
- Repository Writer 추가
- ESG_DMA_SCORE_SUMMARY 반영
- final_score / rank_no / Top20 변경
- API / Frontend 변경
- DB / SQL / DDL 변경
- Agency / Regulation / KCGS / KIS Runtime 구현
```

완료 후 멈춰라.

---

## 1. 작업 성격

```text
Phase C2.3.1
= Git Tracking 복구
+ Resolver Policy Fail-Fast
+ Dedup 과병합 방지
+ Ratio / Scope 계약 고정
+ 주석 정합성 보정
+ Guard Test 보강
```

이번 단계는 C2.4 Runtime Wiring 전에 반드시 통과해야 하는 안정화 단계다.

---

## 2. Preflight

Repo Root에서 아래를 실행한다.

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short

python -m compileall backend/src -q
python -m pytest backend/tests -q
```

Expected Branch:

```text
feature/DAM_score_ljb
```

Expected Baseline HEAD:

```text
fbc4c29077d3a7a2a20752afe21f7179dc7e6036
```

주의:

- HEAD가 다르면 reset하지 않는다.
- Working Tree에 기존 Diff가 있으면 임의 원복하지 않는다.
- 기존 Diff 목록을 먼저 보고하고 멈춘다.
- 브랜치를 임의 생성하거나 checkout하지 않는다.
- git add / commit / push는 수행하지 않는다.

---

## 3. 반드시 읽을 파일

### 3.1 C2.3 Production Foundation

```text
backend/src/resources/dma/v1_3_mvp/media_event_resolver_policy.json
backend/src/services/medias/eventresolver.py
backend/src/models/dmaengine.py
backend/src/resources/dma/v1_3_mvp/manifest.json
backend/src/utils/dmaruleregistry.py
```

### 3.2 Canonical Core / Screening SSOT

```text
backend/src/resources/dma/v1_3_mvp/canonical_scoring_policy.json
backend/src/resources/dma/v1_3_mvp/screening_policy.json
backend/src/utils/dmascoring.py
```

### 3.3 Existing Test

```text
backend/tests/test_dma_v1_3_slim_registry.py
backend/tests/test_dma_v1_3_phase_c2_media_external_news_fact_resolver.py
backend/tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py
```

### 3.4 Git Ignore

```text
.gitignore
backend/.gitignore
```

### 3.5 Local Only Reference

현재 로컬에 아래 신규 테스트 파일이 있는지 확인한다.

```text
backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py
```

없다면 C2.3 Rule Card와 Production Foundation을 기준으로 신규 작성한다.

### 3.6 C3.0 계약 문서

로컬 문서가 존재하면 읽는다.

```text
docs/dma/v1_3_mvp/14_PHASE_C3_0_EXTERNAL_CHANNEL_INPUT_SCORING_CONTRACT_RESULT.md
```

docs가 ignore 상태라면 Git Tracking을 강제로 변경하지 않는다.
문서 보정은 로컬 산출물로만 남겨도 된다.

---

## 4. 기존 개발 규칙 유지

### 4.1 Naming

Python 신규·수정 Public 함수:

```text
lowerCamelCase
외부 호출 주요 함수만 step0~step4 접두어 허용
```

Private Helper:

```text
_ 접두어
짧고 책임이 명확한 이름
불필요한 Helper 과분리 금지
```

### 4.2 SSOT

```text
정책 숫자
→ JSON

정책 Key
→ JSON

계산 알고리즘
→ Python

Config Validation
→ dmaruleregistry.py
```

금지:

```text
Python에 점수 Band 중복 하드코딩
JSON 문자열 수식 실행
eval()
exec()
서비스가 JSON 직접 읽기
Adapter가 Registry 직접 호출
```

### 4.3 유지보수성

이번 Patch에서도 과도한 함수 세분화를 금지한다.

권장:

```text
Validator Public 함수 1개
필요한 Private Helper 최대 2~3개
```

금지:

```text
Key 1개마다 Helper 1개 생성
Band 1개마다 Helper 생성
범용 Framework 신규 도입
Wrapper / Re-export 파일 추가
```

---

## 5. 허용 수정 범위

수정 허용:

```text
backend/.gitignore

backend/src/resources/dma/v1_3_mvp/media_event_resolver_policy.json
backend/src/services/medias/eventresolver.py
backend/src/models/dmaengine.py
backend/src/utils/dmaruleregistry.py

backend/tests/test_dma_v1_3_slim_registry.py
backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py
```

필요 시 허용:

```text
docs/dma/v1_3_mvp/15_PHASE_C2_3_1_MEDIA_NEWS_RESOLVER_GUARD_HARDENING_RESULT.md
docs/dma/v1_3_mvp/14_PHASE_C3_0_EXTERNAL_CHANNEL_INPUT_SCORING_CONTRACT_RESULT.md
```

금지:

```text
backend/src/services/medias/service.py
backend/src/services/medias/adapter.py
backend/src/utils/dmarepository.py
backend/src/services/materialities/orchestrator.py
backend/src/apis/**
frontend/**
*.sql
```

신규 Production 파일 생성 금지.

예외:

```text
backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py
```

신규 Test 파일은 반드시 Git Tracking 가능한 상태로 만든다.

---

## 6. C2.3.1-A — 신규 Test Tracking 복구

현재 `backend/.gitignore`에 아래가 존재한다.

```gitignore
tests/
references/
```

`tests/`는 삭제한다.

수정 후:

```gitignore
model_cache/
references/
```

주의:

- 기존 Tracking Test를 rm --cached 하지 않는다.
- backend/tests 전체를 untrack하지 않는다.
- `references/`는 이번 범위에서 유지한다.
- Root `.gitignore`는 이번 작업 목적과 직접 관련 없는 경우 수정하지 않는다.

검증:

```bash
git check-ignore -v backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py
```

정상:

```text
출력 없음
```

---

## 7. C2.3.1-B — Registry / Test 주석 보정

수정:

```text
backend/src/utils/dmaruleregistry.py
backend/tests/test_dma_v1_3_slim_registry.py
```

기존:

```text
5 policy files
Runtime policy 5-file exact set
```

수정:

```text
6 policy files
Runtime policy 6-file exact set
```

Production 동작 변경은 하지 않는다.

---

## 8. C2.3.1-C — Resolver Policy Fail-Fast Validator

수정:

```text
backend/src/utils/dmaruleregistry.py
```

신규 Public 함수:

```python
def validateMediaEventResolverPolicy(policy: Mapping[str, Any]) -> None:
    ...
```

책임:

```text
media_event_resolver_policy.json 구조 검증
필수 Key 누락 시 DmaRuleValidationError
Band 구조 오류 시 DmaRuleValidationError
Unknown mandatoryKeys 입력 시 DmaRuleValidationError
Silent Default 방지
```

`validateBundle()` 또는 적절한 Registry Validation Path에서 아래 정책 파일에 대해 반드시 호출한다.

```text
media_event_resolver_policy.json
```

최소 필수 검증 대상:

```text
version
ruleVersion
resolverVersion
scoreDecisionByAiAllowedYn == false

eventTypeNormalization
eventTypeNormalization.unknownPolicy
eventTypeNormalization.aliases

impactScaleRules
impactScaleRules.bands
impactScaleRules.missingPolicy

impactScopeRules
impactScopeRules.enabledYn
impactScopeRules.missingPolicy

impactLikelihoodRules
impactLikelihoodRules.bands
impactLikelihoodRules.missingPolicy

impactIrremediabilityRules
impactIrremediabilityRules.missingPolicy

financialMagnitudeRules
financialMagnitudeRules.primarySource
financialMagnitudeRules.financialAmountDirectScoringAllowedYn == false
financialMagnitudeRules.bands
financialMagnitudeRules.missingPolicy

financialLikelihoodRules
financialLikelihoodRules.bands
financialLikelihoodRules.missingPolicy

timeHorizonRules
timeHorizonRules.sourcePriority
timeHorizonRules.shortMaxDays
timeHorizonRules.midMaxDays
timeHorizonRules.missingPolicy

eventDedupRules
eventDedupRules.mandatoryKeys
eventDedupRules.advisoryOnlyFields
eventDedupRules.mergePolicy
eventDedupRules.conflictPolicy
eventDedupRules.missingMandatoryKeyPolicy
eventDedupRules.dateBucketSourcePriority
eventDedupRules.dateBucketPrecision

ratioValueContract
ratioValueContract.normalization
ratioValueContract.min
ratioValueContract.max
ratioValueContract.outOfRangePolicy

missingPolicy
missingPolicy.requiredFactorMissing
missingPolicy.missingAsZeroForbiddenYn == true
```

허용 mandatoryKeys:

```text
subIssueCode
normalizedEventType
eventDateBucket
```

Band 검증 최소 조건:

```text
- bands는 non-empty list
- 각 band는 dict
- score 존재
- score는 0..5
- min/max는 숫자 또는 null
- minInclusive / maxExclusive 존재
- 순서 역전 금지
- overlap 금지
- gap 허용 여부는 JSON 정책에 따름
```

주의:

- Registry에서 Rule Number를 재정의하지 않는다.
- Validator는 숫자를 계산하지 않는다.
- Resolver가 조용히 `{}` Default로 흘러가지 못하게 한다.

---

## 9. C2.3.1-D — Probability Band 경계 계약 고정

수정:

```text
backend/src/resources/dma/v1_3_mvp/media_event_resolver_policy.json
backend/src/services/medias/eventresolver.py
```

현재 `impactLikelihoodRules.bands`, `financialLikelihoodRules.bands`에 경계 포함 여부가 없다.

각 Band에 아래를 명시한다.

```json
{
  "min": 0.0,
  "max": 0.05,
  "minInclusive": true,
  "maxExclusive": true,
  "score": 1
}
```

마지막 Band:

```json
{
  "min": 0.80,
  "max": 1.0,
  "minInclusive": true,
  "maxExclusive": false,
  "score": 5
}
```

권장 경계:

```text
[0.00, 0.05) → 1
[0.05, 0.20) → 2
[0.20, 0.50) → 3
[0.50, 0.80) → 4
[0.80, 1.00] → 5
```

`_applySimpleBand()`를 inclusive-inclusive 방식으로 유지하지 않는다.

중복 구현 금지.

권장:

```text
_applySimpleBand() 제거 또는 _applyRatioBand()와 통합
```

한 개의 Band Lookup Helper가 아래를 모두 처리하도록 정리한다.

```text
count
probability
ratio
```

단, Count Band의 경계도 JSON에서 명시적으로 관리한다.

예:

```text
[1, 10)       → 1
[10, 100)     → 2
[100, 1000)   → 3
[1000, 10000) → 4
[10000, null) → 5
```

---

## 10. C2.3.1-E — ratioValue 단위 계약 고정

수정:

```text
backend/src/resources/dma/v1_3_mvp/media_event_resolver_policy.json
backend/src/services/medias/eventresolver.py
```

신규 Policy Section:

```json
"ratioValueContract": {
  "normalization": "DECIMAL_RATIO_ONLY",
  "min": 0.0,
  "max": 1.0,
  "outOfRangePolicy": "REJECTED"
}
```

계약:

```text
ratioValue = 0.03
→ 3%

ratioValue = 3
→ 금지
→ REJECTED 또는 ValueError Fail-Fast
```

권장 구현:

```text
Pure Resolver 내부에서 ratioValue < 0 또는 ratioValue > 1이면
잘못된 Upstream 입력으로 처리
```

정책 선택:

```text
outOfRangePolicy == "REJECTED"
→ Resolver Candidate 생성 시 잘못된 입력을 ruleTrace에 기록
→ ResolverStatus = REJECTED
→ Canonical 점수 계산 금지
```

단순히 3을 0.03으로 자동 보정하지 않는다.

이유:

```text
3이 3%인지 300%인지 추론 금지
```

`financialAmount` 직접 점수화는 계속 금지한다.

```text
financialAmountDirectScoringAllowedYn = false
```

---

## 11. C2.3.1-F — impactScopeRules Dead Config 제거

현재 Policy에는 아래가 있다.

```text
impactScopeRules.sourceField = scopeValue
```

그러나 `ExtractedFactsV13`에는 `scopeValue`가 없다.

이번 C2.3.1에서는 DTO에 `scopeValue`를 추가하지 않는다.

이유:

```text
scopeValue 의미와 upstream 산출 계약이 아직 승인되지 않음
scope는 Canonical Optional Factor
임의 추가 시 AI Fact Boundary 오염 가능
```

Policy를 아래처럼 명시한다.

```json
"impactScopeRules": {
  "enabledYn": false,
  "sourceField": null,
  "bands": [],
  "missingPolicy": "UNOBSERVED",
  "pendingReason": "UPSTREAM_SCOPE_FACT_CONTRACT_REQUIRED"
}
```

Resolver:

```text
scope = None 유지
```

Validator:

```text
enabledYn == false
→ sourceField null 허용
→ bands 빈 배열 허용

enabledYn == true
→ sourceField 필수
→ bands non-empty 필수
```

향후 별도 Schema Decision:

```text
ExtractedFactsV13.scopeValue 추가 여부
```

이번 단계에서 결정하지 않는다.

---

## 12. C2.3.1-G — Dedup Date Priority 분리

수정:

```text
backend/src/resources/dma/v1_3_mvp/media_event_resolver_policy.json
backend/src/services/medias/eventresolver.py
```

Time Horizon 목적과 Dedup 목적의 날짜 우선순위를 분리한다.

Time Horizon:

```text
deadlineDate
→ effectiveDate
→ eventDate
```

Dedup Date Bucket:

```text
eventDate
→ effectiveDate
→ deadlineDate
```

Policy:

```json
"eventDedupRules": {
  "dateBucketSourcePriority": ["eventDate", "effectiveDate", "deadlineDate"],
  "dateBucketPrecision": "DAY"
}
```

Dedup Bucket은 월 단위가 아니라 일 단위로 변경한다.

```text
YYYY-MM-DD
```

이유:

```text
동일 월 내 서로 다른 사건 자동 병합 방지
```

---

## 13. C2.3.1-H — Dedup 과병합 방지

현재 자동 Merge 조건:

```text
subIssueCode
+ normalizedEventType
+ eventDateBucket

같으면 MERGED
```

이 조건만으로 자동 MERGED 처리하지 않는다.

정책을 아래처럼 고정한다.

```json
"eventDedupRules": {
  "mandatoryKeys": [
    "subIssueCode",
    "normalizedEventType",
    "eventDateBucket"
  ],
  "advisoryOnlyFields": [
    "eventGroupCandidateId"
  ],
  "mergePolicy": "COMPOSITE_PLUS_MATCHING_ADVISORY_HINT",
  "conflictPolicy": "CONFLICTED",
  "missingMandatoryKeyPolicy": "UNRESOLVED",
  "dateBucketSourcePriority": [
    "eventDate",
    "effectiveDate",
    "deadlineDate"
  ],
  "dateBucketPrecision": "DAY"
}
```

확정 규칙:

```text
A. mandatory key 중 하나라도 누락
→ UNRESOLVED

B. composite key가 단독 1건
→ UNIQUE

C. composite key가 복수건
   AND 모든 Row의 eventGroupCandidateId가 non-null
   AND eventGroupCandidateId가 모두 동일
→ MERGED

D. composite key가 복수건
   BUT eventGroupCandidateId 누락 또는 서로 다름
→ CONFLICTED
```

중요:

```text
eventGroupCandidateId 단독 일치
→ Merge 금지

composite key 단독 일치
→ Merge 금지

두 조건이 함께 성립
→ MERGED 가능
```

`MERGE_CANDIDATE` 신규 Enum은 이번 단계에서 추가하지 않는다.
기존 `CONFLICTED`를 보수적 보호 상태로 사용한다.

기사 수에 따른 점수 가산은 계속 금지한다.

---

## 14. C2.3.1-I — REJECTED 상태 Canonical 차단

`resolveMediaNewsCanonicalFactors()`는 아래 조건에서 Canonical 계산을 호출하지 않아야 한다.

```text
resolution.resolverStatus == "REJECTED"
resolution.resolverStatus == "CONFLICTED"
```

반환:

```python
{
    "impact": None,
    "financial": None,
}
```

또는 현재 함수 Return Contract와 맞는 동일 의미 구조.

주의:

- 0점으로 대체 금지
- 빈 점수를 정상 점수로 오해하게 만들지 않는다
- Canonical Core 산식 재구현 금지

---

## 15. C2.3.1-J — C3.0 KCGS 문서 Micro Patch

로컬 문서가 존재하는 경우 수정:

```text
docs/dma/v1_3_mvp/14_PHASE_C3_0_EXTERNAL_CHANNEL_INPUT_SCORING_CONTRACT_RESULT.md
```

현재 문서에 아래 방향이 있으면 수정한다.

기존 잘못된 방향:

```text
A+ = 5.0
A = 4.0
...
D = 0.0

등급 상승 → 양의 보정
등급 하락 → 음의 보정
```

현재 SSOT:

```text
backend/src/resources/dma/v1_3_mvp/screening_policy.json
```

SSOT 기준:

```text
KCGS는 성과 점수가 아니라 위험 Boost 전용 Signal

gradeRisk:
S  = 0.0
A+ = 0.5
A  = 1.0
B+ = 2.0
B  = 3.0
C  = 4.0
D  = 5.0

trendModifier:
downgradeTwoOrMore = +1.0
downgradeOne       = +0.5
flat               = +0.0
upgrade            = +0.0
insufficientData   = UNOBSERVED
```

문서에 아래를 명확히 기록한다.

```text
낮은 등급
→ 위험 Signal 증가

등급 하락
→ 위험 Boost 증가

등급 상승
→ 양의 성과점수 생성 금지
→ 위험 Boost 0

KCGS
→ Canonical Final 직접 반영 금지
→ media_external externalMax 축 점수 직접 주입 금지
→ Pre-Survey Top20 bounded boost-only
```

Production `screening_policy.json` 값은 이번 단계에서 변경하지 않는다.

---

## 16. 테스트

신규 또는 복구:

```text
backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py
```

최소 테스트 범위:

### 16.1 Policy / Registry

```text
1. media_event_resolver_policy.json Registry Load
2. runtime policy count == 6
3. Resolver Policy required key missing → DmaRuleValidationError
4. eventDedupRules.mandatoryKeys unknown key → DmaRuleValidationError
5. scoreDecisionByAiAllowedYn != false → DmaRuleValidationError
6. missingAsZeroForbiddenYn != true → DmaRuleValidationError
7. enabledYn=false scope config 허용
8. enabledYn=true scope bands 누락 → DmaRuleValidationError
```

### 16.2 Probability Boundary

```text
9. probabilityValue = 0.0499 → 1
10. probabilityValue = 0.05 → 2
11. probabilityValue = 0.20 → 3
12. probabilityValue = 0.50 → 4
13. probabilityValue = 0.80 → 5
14. probabilityValue = 1.00 → 5
15. probabilityValue = 80 → 5
```

`ZERO_TO_ONE_OR_PERCENT` Normalization은 probability에만 유지한다.

### 16.3 ratioValue Contract

```text
16. ratioValue = 0.03 → magnitude 5
17. ratioValue = 3 → REJECTED
18. ratioValue = -0.1 → REJECTED
19. ratioValue out-of-range → Canonical 함수 미호출 또는 axis None
20. financialAmount만 존재 → magnitude UNOBSERVED
```

### 16.4 Dedup Date Priority

```text
21. eventDate 존재 시 deadlineDate보다 eventDate를 Bucket으로 사용
22. eventDate 없고 effectiveDate 존재 시 effectiveDate 사용
23. eventDate/effectiveDate 없고 deadlineDate 존재 시 deadlineDate 사용
24. Bucket Precision == DAY
```

### 16.5 Dedup Guard

```text
25. mandatory key 누락 → UNRESOLVED
26. composite key 단독 1건 → UNIQUE
27. composite key 복수 + 동일 non-null candidate hint → MERGED
28. composite key 복수 + candidate hint 누락 → CONFLICTED
29. composite key 복수 + candidate hint 다름 → CONFLICTED
30. candidate hint만 동일하고 composite 다름 → MERGED 아님
31. 동일 월, 날짜 다름 → MERGED 아님
32. 기사 수가 증가해도 factor score 가산 없음
```

### 16.6 DTO / Guard

```text
33. ExtractedFactsV13에 scopeValue 입력 → extra="forbid"
34. ScoringPayloadV13.eventResolutionTrace optional
35. resolverStatus REJECTED → Canonical axis None
36. resolverStatus CONFLICTED → Canonical axis None
```

기존 C2.3 36건을 복구하고, 위 Hardening Test를 포함해 필요한 경우 테스트 수를 확대한다.

목표:

```text
C2.3 Resolver Test
→ 최소 36 passed

전체 Backend
→ 기존 회귀 0
```

---

## 17. 정적 검증

실행:

```bash
python -m compileall backend/src -q

python -m pytest \
  backend/tests/test_dma_v1_3_slim_registry.py \
  backend/tests/test_dma_v1_3_phase_c2_media_external_news_fact_resolver.py \
  backend/tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py \
  backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py \
  -q

python -m pytest backend/tests -q

git diff --check
git diff --stat
git diff --name-only
git status --short
```

Git Tracking 검증:

```bash
git check-ignore -v backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py
git ls-files backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py
```

정상:

```text
git check-ignore
→ 출력 없음

git ls-files
→ 신규 테스트 파일 경로 출력
```

금지 검색:

```bash
rg -n "eval\\(|exec\\(" backend/src
```

정상:

```text
0건
```

Runtime 침투 검색:

```bash
git diff --name-only -- \
  backend/src/services/medias/service.py \
  backend/src/utils/dmarepository.py \
  backend/src/services/materialities/orchestrator.py \
  backend/src/apis \
  frontend
```

정상:

```text
출력 없음
```

Summary / Rank 침투 검색:

```bash
rg -n "ESG_DMA_SCORE_SUMMARY|final_score|rank_no|Top20|recalcFinal|updateRanks" \
  backend/src/services/medias/eventresolver.py \
  backend/src/utils/dmaruleregistry.py
```

정상:

```text
0건
```

---

## 18. 결과 문서

작성:

```text
docs/dma/v1_3_mvp/15_PHASE_C2_3_1_MEDIA_NEWS_RESOLVER_GUARD_HARDENING_RESULT.md
```

필수 내용:

```text
1. Repo Path
2. Branch
3. Baseline HEAD
4. 작업 전 git status
5. 수정 파일 목록
6. 신규 Production 파일 수
7. 신규 Test 파일 Tracking 복구 결과
8. backend/.gitignore tests/ 제거 확인
9. Registry 6 policy files 주석 보정
10. validateMediaEventResolverPolicy() 설명
11. Validator 필수 Key 목록
12. Probability Band 경계 정책
13. ratioValue DECIMAL_RATIO_ONLY 계약
14. ratioValue Out-of-Range REJECTED
15. impactScopeRules enabledYn=false 결정
16. ExtractedFactsV13.scopeValue 미추가 결정
17. Dedup Date Priority 분리
18. Dedup DAY Bucket 결정
19. Dedup MERGED / CONFLICTED 규칙
20. Candidate Hint Advisory Only 유지
21. REJECTED / CONFLICTED Canonical 차단
22. C3.0 KCGS 문서 Micro Patch
23. compileall 결과
24. 지정 테스트 결과
25. 전체 Backend 테스트 결과
26. git diff --check
27. eval / exec 0건
28. Service Runtime Diff 0
29. Repository Writer Diff 0
30. Summary / Rank Diff 0
31. API / Frontend Diff 0
32. SQL / DDL Diff 0
33. DB / Redis / Kafka / Docker 미접근
34. git add / commit / push 미수행
35. 다음 단계 후보: Phase C2.4
```

---

## 19. 완료 보고 형식

완료 후 아래 순서로 보고한다.

```text
1. Branch
2. Baseline HEAD
3. 작업 전 status
4. 수정 파일 목록
5. 신규 Production 파일 수
6. 신규 Test 파일 Tracking 결과
7. backend/.gitignore tests/ 제거
8. Registry 6 policy 주석 보정
9. Resolver Policy Validator
10. Probability Band 경계
11. ratioValue 단위 계약
12. scopeValue 결정
13. Dedup Date Priority
14. Dedup DAY Bucket
15. MERGED / CONFLICTED 규칙
16. REJECTED / CONFLICTED Canonical 차단
17. C3.0 KCGS 문서 보정
18. 신규 테스트 수
19. 전체 테스트 수
20. compileall
21. git diff --check
22. 금지 검색 결과
23. Runtime 침투 없음
24. Summary / Rank 침투 없음
25. API / Frontend 변경 없음
26. SQL / DDL 변경 없음
27. DB / Redis / Kafka / Docker 미접근
28. git add / commit / push 미수행
29. 다음 단계 후보
```

---

## 20. 완료 기준

아래를 모두 충족해야 PASS다.

```text
- Branch = feature/DAM_score_ljb
- 신규 Production 파일 0
- backend/.gitignore tests/ 제거
- 신규 C2.3 Resolver Test 파일 Git Tracking 가능
- 신규 Resolver Test 파일 git ls-files 출력
- Registry 6 policy files 주석 정합성
- Resolver Policy 필수 Key Fail-Fast
- Probability Band 경계 명시
- probabilityValue 0.80 → 5
- ratioValue DECIMAL_RATIO_ONLY
- ratioValue 자동 Percent 추론 금지
- ratioValue out-of-range → REJECTED
- scopeValue DTO 미추가
- impactScopeRules.enabledYn = false
- Dedup Bucket = DAY
- Dedup Date Priority = eventDate → effectiveDate → deadlineDate
- composite 단독 일치로 자동 Merge 금지
- candidateHint 단독 일치로 자동 Merge 금지
- composite + 동일 non-null candidateHint만 MERGED
- 복수 Composite 충돌은 CONFLICTED
- REJECTED / CONFLICTED Canonical 계산 차단
- C3.0 KCGS 문서가 screening_policy gradeRisk SSOT와 정합
- Service Runtime Wiring 미수행
- Repository Writer 미수정
- ESG_DMA_SCORE_SUMMARY 미수정
- final_score / rank_no / Top20 미수정
- API / Frontend 미수정
- SQL / DDL 미수정
- DB / Redis / Kafka / Docker 미접근
- compileall PASS
- 전체 Backend Regression 0
- git diff --check PASS
- eval / exec 0건
- git add / commit / push 미수행
```

완료 후 멈춰라.

Phase C2.4 Runtime Wiring으로 넘어가지 마라.
