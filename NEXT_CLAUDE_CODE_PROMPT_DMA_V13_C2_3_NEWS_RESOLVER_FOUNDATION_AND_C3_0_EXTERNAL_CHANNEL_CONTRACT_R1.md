# NEXT CLAUDE CODE PROMPT
# DMA v1.3 Phase C2.3 — media_external.news Resolver Policy Approval / Event Resolution Trace DTO / Pure Function Foundation
# + C3.0 Pre-Design — agency / regulation Input & Scoring Contract Freeze
# R1

## 0. 작업 목적

현재 DMA v1.3 `media_external.news` 경로는 아래까지 완료되었다.

```text
C2.0
→ News Fact-only Resolver Foundation

C2.0.1
→ Nested Similarity Metadata Sanitization

C2.1
→ News Fact Shadow Replace-Active Runtime Wiring

C2.1.1
→ 정상 빈 Crawl Empty Replace
→ FAILED / PARTIAL_FAILED / Source 전체 거부 보호

C2.1.2
→ Non-empty Partial Crawl Shadow Protection
→ Legacy 저장 유지
→ Shadow Replace Skip

C2.2
→ Event Fact Resolver / Canonical IRO / Event Dedup Contract Freeze
→ Test-only Hardening 1건
```

현재 기준 Branch / HEAD:

```text
branch:
feature/DAM_score_ljb

HEAD:
7a3e5551cd0d8c9d849870666e9da665908d362c
```

현재 보고된 전체 Backend 기준:

```text
341 passed
1 skipped
```

이번 작업은 두 영역으로 분리한다.

```text
Phase C2.3
→ media_event_resolver_policy.json 실제 추가
→ Event Resolution Trace DTO 실제 추가
→ News Pure Function Foundation 구현
→ Runtime / DB Wiring 없음

C3.0 Pre-Design
→ agency / regulation 입력·점수 계약 문서 고정
→ KCGS 3개년 등급 입력 구조 확정
→ KIS 입력 계약 및 Capability Pending 범위 확정
→ Regulation Regime ↔ Sub-Issue Mapping 입력 구조 확정
→ 구현 없음
```

완료 후 멈춰라.

---

## 1. 이번 작업의 경계

이번 단계는 **News Canonical Pure Function Foundation**까지만 구현한다.

```text
허용:
- media_event_resolver_policy.json 신규 추가
- manifest.json runtimePolicyFiles 등록
- manifest capability 상태는 CONFIG_PENDING 유지
- dmaruleregistry.py 등록 최소 보정
- Event Resolution Trace DTO 추가
- Pure Resolver 함수 최대 3개 추가
- News Resolver 단위 테스트 추가
- agency / regulation 입력·점수 계약 문서 작성

금지:
- runMediaAnalysis() Runtime Wiring
- News Canonical Shadow Namespace 상수 추가
- News Canonical Repository Writer 추가
- ESG_DMA_SIGNAL_DETAIL Canonical Shadow INSERT
- ESG_DMA_SCORE_SUMMARY 변경
- final_score / rank_no 변경
- Top20 변경
- agency Runtime 구현
- regulation Runtime 구현
- KCGS Runtime 구현
- KIS Runtime 구현
- externalMax Runtime Wiring
- 신규 Table / Column / FK / Index
- SQL / DDL 변경
- API / frontend 변경
```

이번 Phase C2.3의 Production 구현은 Pure Function만 허용한다.

---

## 2. 시작 전 Preflight

현재 위치가 `backend` 폴더라면:

```bash
git status --short
git branch --show-current
git rev-parse HEAD

python -m compileall src -q
python -m pytest tests -q
```

프로젝트 루트라면:

```bash
git status --short
git branch --show-current
git rev-parse HEAD

python -m compileall backend/src -q
python -m pytest backend/tests -q
```

Expected:

```text
branch:
feature/DAM_score_ljb

HEAD:
7a3e5551cd0d8c9d849870666e9da665908d362c

전체 Backend:
341 passed
1 skipped
```

Working Tree에 아래 문서가 남아 있을 수 있다.

```text
NEXT_CLAUDE_CODE_PROMPT_DMA_V13_C2_2_MEDIA_NEWS_EVENT_RESOLVER_DEDUP_CONTRACT_R1.md
12_PHASE_C2_2_MEDIA_NEWS_EVENT_RESOLVER_DEDUP_CONTRACT_RESULT.md
```

reset하지 마라.
문서 이동 또는 정리는 별도 기록한다.

이번 작업 중 아래는 수행하지 마라.

```text
git add
git commit
git push
```

---

## 3. 반드시 먼저 읽을 파일

### 3.1 News Runtime

```text
backend/src/services/medias/adapter.py
backend/src/services/medias/service.py
backend/src/services/medias/pipeline.py
backend/src/services/medias/crawler.py
backend/src/services/medias/baseline.py
```

### 3.2 Canonical Core

```text
backend/src/models/dmaengine.py
backend/src/utils/dmascoring.py
backend/src/utils/dmaruleregistry.py
backend/src/utils/dmarepository.py
backend/src/services/materialities/orchestrator.py
```

### 3.3 Runtime Policy

```text
backend/src/resources/dma/v1_3_mvp/manifest.json
backend/src/resources/dma/v1_3_mvp/canonical_scoring_policy.json
backend/src/resources/dma/v1_3_mvp/ai_fact_validation_policy.json
backend/src/resources/dma/v1_3_mvp/screening_policy.json
```

### 3.4 기존 C2.2 문서

```text
12_PHASE_C2_2_MEDIA_NEWS_EVENT_RESOLVER_DEDUP_CONTRACT_RESULT.md
```

주의:
C2.2 문서에 `step2CalcCanonical()`이라는 함수명이 있으면 오기다.
실제 Canonical Core 함수는 아래다.

```text
step1CalcImpact()
step1CalcFinancial()
step1CalcAxes()
step1AggSubIssue()
```

문서 보정 시 실제 함수명으로 수정한다.

---

## 4. Mandatory Architecture Invariant

## 4.1 상위 DMA Stage는 정확히 3개

```text
benchmark
media_external
survey
```

## 4.2 media_external 내부 계층

```text
media_external
├─ news
│  ├─ impacton
│  └─ esgeconomy
│
├─ agency
│  ├─ kcgs
│  └─ kis
│
└─ regulation
   ├─ csrd
   ├─ cbam
   └─ dpp
```

아래를 독립 DMA Stage로 승격하지 마라.

```text
news
agency
regulation
kcgs
kis
csrd
cbam
dpp
externalMax
```

## 4.3 Summary Column 추가 금지

```text
ESG_DMA_SCORE_SUMMARY
→ 기존 media_external_impact_score
→ 기존 media_external_financial_score
```

아래 신규 Column 추가 금지.

```text
news_impact_score
news_financial_score
regulation_impact_score
regulation_financial_score
kcgs_score
kis_score
```

## 4.4 externalMax 의미

```text
externalMax
= media_external 내부 news / agency / regulation Trace의 축별 MAX
= 비가산적 집계
= benchmark / survey 입력 금지
```

이번 단계에서는 구현하지 마라.

---

# PART A. Phase C2.3 — News Pure Function Foundation

## 5. 신규 Runtime Policy JSON 추가

신규 파일:

```text
backend/src/resources/dma/v1_3_mvp/media_event_resolver_policy.json
```

이 파일은 **Fact → Derived Canonical Factor Candidate** 변환 Rule Card SSOT다.

`canonical_scoring_policy.json`은 Factor → Score 정책이다.
둘을 섞지 마라.

```text
media_event_resolver_policy.json
→ Fact → Factor Candidate

canonical_scoring_policy.json
→ Factor Candidate → AxisScoreTraceV13
```

## 5.1 최소 Schema

아래 구조를 기준으로 실제 JSON을 작성한다.

```json
{
  "version": "1.0",
  "ruleVersion": "media-event-resolver-v1.0",
  "scoreDecisionByAiAllowedYn": false,
  "eventTypeNormalization": {
    "unknownPolicy": "PASSTHROUGH",
    "aliases": {}
  },
  "impactScaleRules": {
    "sourceField": "affectedCount",
    "bands": [
      {"min": 1, "max": 9, "score": 1},
      {"min": 10, "max": 99, "score": 2},
      {"min": 100, "max": 999, "score": 3},
      {"min": 1000, "max": 9999, "score": 4},
      {"min": 10000, "max": null, "score": 5}
    ],
    "missingPolicy": "UNOBSERVED"
  },
  "impactScopeRules": {
    "sourceField": null,
    "missingPolicy": "UNOBSERVED"
  },
  "impactLikelihoodRules": {
    "sourceField": "probabilityValue",
    "normalization": "ZERO_TO_ONE_OR_PERCENT",
    "bands": [
      {"min": 0.0, "max": 0.05, "score": 1},
      {"min": 0.05, "max": 0.20, "score": 2},
      {"min": 0.20, "max": 0.50, "score": 3},
      {"min": 0.50, "max": 0.80, "score": 4},
      {"min": 0.80, "max": 1.0, "score": 5}
    ],
    "missingPolicy": "UNOBSERVED"
  },
  "impactIrremediabilityRules": {
    "sourceField": null,
    "missingPolicy": "UNOBSERVED"
  },
  "financialMagnitudeRules": {
    "primarySource": "ratioValue",
    "fallbackSource": null,
    "canonicalBandsRef": "canonical_scoring_policy.financialMagnitudeRatioBands",
    "financialAmountDirectScoringAllowedYn": false,
    "missingPolicy": "UNOBSERVED"
  },
  "financialLikelihoodRules": {
    "sourceField": "probabilityValue",
    "normalization": "ZERO_TO_ONE_OR_PERCENT",
    "bandsRef": "impactLikelihoodRules.bands",
    "missingPolicy": "UNOBSERVED"
  },
  "timeHorizonRules": {
    "referenceDatePolicy": "EVALUATION_DATE_REQUIRED",
    "sourcePriority": ["deadlineDate", "effectiveDate", "eventDate"],
    "shortMaxDays": 365,
    "midMaxDays": 1095,
    "missingPolicy": "UNOBSERVED"
  },
  "eventDedupRules": {
    "candidateHintField": "eventGroupCandidateId",
    "candidateHintPolicy": "ADVISORY_ONLY",
    "mandatoryKeys": ["subIssueCode", "normalizedEventType", "eventDateBucket"],
    "optionalKeys": ["normalizedEntity", "normalizedLocation", "amountBucket"],
    "missingMandatoryPolicy": "UNRESOLVED",
    "conflictPolicy": "CONFLICTED"
  },
  "missingPolicy": {
    "requiredFactorMissing": "UNOBSERVED",
    "missingAsZeroForbiddenYn": true
  },
  "conflictPolicy": "CONFLICTED"
}
```

## 5.2 승인 주의

위 Band 값은 MVP Rule Card 초안이다.
반드시 결과 문서에 아래를 명시한다.

```text
MVP DEFAULT
→ 운영 정책 확정값 아님
→ Runtime JSON SSOT이므로 향후 교체 가능
```

Python 코드에 숫자를 Hardcode하지 마라.

## 5.3 Manifest 등록

`manifest.json`의 `runtimePolicyFiles`에 아래를 추가한다.

```text
media_event_resolver_policy.json
```

단 Capability 상태는 유지한다.

```text
mediaEventCanonicalAdapter = CONFIG_PENDING
```

`READY`로 바꾸지 마라.

이유:

```text
Pure Function Foundation만 구현
Runtime Wiring 없음
Canonical Shadow 저장 없음
```

## 5.4 Registry 등록

`dmaruleregistry.py`에 기존 Registry Style을 따라 최소 등록한다.

금지:

```text
Service 직접 json.load()
중복 Loader 추가
범용 Config Framework 추가
```

---

## 6. Event Resolution Trace DTO 추가

수정 파일:

```text
backend/src/models/dmaengine.py
```

`ExtractedFactsV13.rawMetadata`에 Derived Decision을 넣지 마라.

## 6.1 신규 DTO

최소 DTO Proposal:

```python
class MediaNewsResolvedAxisCandidateV13(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    polarity: Optional[str] = None
    scale: Optional[float] = None
    scope: Optional[float] = None
    likelihood: Optional[float] = None
    irremediability: Optional[float] = None
    magnitude: Optional[float] = None
    timeHorizon: Optional[str] = Field(None, alias="time_horizon")
    explicitNoUrgencyYn: Optional[TriState] = Field(None, alias="explicit_no_urgency_yn")
    ruleTrace: List[Dict[str, Any]] = Field(default_factory=list, alias="rule_trace")


class MediaNewsDedupTraceV13(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    eventGroupCandidateId: Optional[str] = Field(None, alias="event_group_candidate_id")
    confirmedEventGroupKey: Optional[str] = Field(None, alias="confirmed_event_group_key")
    dedupStatus: Literal["UNRESOLVED", "UNIQUE", "MERGED", "CONFLICTED", "REJECTED"] = Field(
        "UNRESOLVED", alias="dedup_status"
    )
    ruleTrace: List[Dict[str, Any]] = Field(default_factory=list, alias="rule_trace")


class MediaNewsEventResolutionTraceV13(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resolverStatus: Literal["RESOLVED", "PARTIAL", "UNOBSERVED", "CONFLICTED", "REJECTED"] = Field(
        ..., alias="resolver_status"
    )
    subIssueCode: str = Field(..., alias="sub_issue_code")
    normalizedEventType: Optional[str] = Field(None, alias="normalized_event_type")
    eventDateBucket: Optional[str] = Field(None, alias="event_date_bucket")
    impact: Optional[MediaNewsResolvedAxisCandidateV13] = None
    financial: Optional[MediaNewsResolvedAxisCandidateV13] = None
    dedup: MediaNewsDedupTraceV13 = Field(default_factory=MediaNewsDedupTraceV13)
```

필드명은 현재 Coding Convention에 맞춰 최소 조정 가능하다.

과분리 금지.

## 6.2 ScoringPayloadV13 확장

`ScoringPayloadV13`에 Optional 필드 1개만 추가한다.

```python
eventResolutionTrace: Optional[MediaNewsEventResolutionTraceV13] = Field(
    None,
    alias="event_resolution_trace",
)
```

기존 Payload 호환성을 깨지 마라.

```text
기존 Payload
→ eventResolutionTrace 없음
→ 정상 Validation
```

---

## 7. Pure Function Foundation 구현

신규 Production 파일 1개 허용:

```text
backend/src/services/medias/eventresolver.py
```

신규 Public Function은 최대 3개만 허용한다.

```python
resolveMediaNewsEventObservation(
    fact: ExtractedFactsV13,
    policy: Mapping[str, Any],
    *,
    evaluationDate: Optional[str] = None,
) -> MediaNewsEventResolutionTraceV13

resolveMediaNewsCanonicalFactors(
    resolution: MediaNewsEventResolutionTraceV13,
    canonicalPolicy: Mapping[str, Any],
) -> Dict[str, Optional[AxisScoreTraceV13]]

resolveMediaNewsEventGroup(
    resolutions: Sequence[MediaNewsEventResolutionTraceV13],
    policy: Mapping[str, Any],
) -> list[MediaNewsEventResolutionTraceV13]
```

## 7.1 Function 1 — Observation Resolver

역할:

```text
ExtractedFactsV13
→ normalizedEventType
→ affectedCount band → impact.scale 후보
→ probabilityValue normalize → likelihood 후보
→ ratioValue → financial.magnitude 후보
→ 날짜 + evaluationDate → timeHorizon 후보
→ explicitNoUrgencyYn TRUE → urgency 0 후보를 Trace로 표시
→ Event Dedup Candidate Hint 보존
→ Resolver Status 결정
```

금지:

```text
classificationConfidence를 Factor로 사용
기사 수를 Factor로 사용
provider 수를 Factor로 사용
financialAmount를 직접 magnitude 점수로 변환
AI score 값 수용
```

## 7.2 Function 2 — Canonical Factor → Axis Trace

역할:

```text
MediaNewsEventResolutionTraceV13
→ step1CalcAxes()
→ AxisScoreTraceV13
```

반드시 기존 Core를 재사용한다.

금지:

```text
Canonical 계산식 복제
새 점수 계산식 작성
Missing → 0 변환
```

## 7.3 Function 3 — Event Group Resolver

역할:

```text
복수 Resolution
→ Confirmed Merge Key 생성 가능 여부 검토
→ UNIQUE / MERGED / UNRESOLVED / CONFLICTED
→ 동일 Event Group Resolution Trace 정리
```

이번 Foundation에서는 보수적으로 구현한다.

```text
mandatoryKeys 모두 존재
AND
Composite Key 동일
→ MERGED

mandatoryKeys 누락
→ UNRESOLVED

eventGroupCandidateId만 동일
→ Merge 금지
```

기사 개수에 따라 점수 가산 금지.

---

## 8. Resolver Status 정책

아래를 문서와 테스트로 고정한다.

```text
CONFLICTED
→ conflict 발생

REJECTED
→ Policy 위반 또는 Validation 실패

UNOBSERVED
→ Required Factor 전부 미해결

PARTIAL
→ 일부 Fact / Optional Factor만 해결
→ Required Factor 일부 누락

RESOLVED
→ Canonical Required Factor 충족 가능한 Axis가 최소 1개 존재
```

축별 판단은 `step1CalcAxes()` 결과를 우선한다.

```text
required missing
→ AxisScoreTraceV13.status = UNOBSERVED
→ score = None
```

---

## 9. 신규 테스트

신규 파일:

```text
backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py
```

## 9.1 Policy / Registry

```text
1. media_event_resolver_policy.json 존재
2. manifest runtimePolicyFiles 등록
3. mediaEventCanonicalAdapter = CONFIG_PENDING 유지
4. Registry에서 policy 조회 가능
5. Service 직접 JSON Load 없음
```

## 9.2 DTO

```text
6. ScoringPayloadV13 기존 Payload 호환
7. eventResolutionTrace Optional 직렬화
8. Derived Decision이 extractedFacts.rawMetadata로 들어가지 않음
```

## 9.3 Observation Resolver

```text
9. affectedCount band → impact.scale
10. probabilityValue 0~1 → likelihood
11. probabilityValue 0~100 percent → normalize 후 likelihood
12. ratioValue → canonical ratio band 기반 magnitude 후보
13. missing affectedCount → scale None
14. missing probability → likelihood None
15. financialAmount direct scoring 금지
16. classificationConfidence factor 미사용
17. eventGroupCandidateId advisory 보존
18. explicitNoUrgencyYn TRUE Trace 보존
19. evaluationDate 없음 → timeHorizon UNOBSERVED
20. deadlineDate + evaluationDate → short/mid/long
```

## 9.4 Canonical Factor Resolver

```text
21. required impact factor 누락 → impact score None / UNOBSERVED
22. financial ratio magnitude 존재 → financial Axis Trace 생성
23. step1CalcAxes() 재사용 검증
24. missing → 0 대체 없음
```

## 9.5 Dedup

```text
25. Composite Mandatory Key 동일 → MERGED
26. URL만 동일 → Event-level merge 근거로 사용하지 않음
27. eventGroupCandidateId만 동일 → MERGED 금지
28. Mandatory Key 누락 → UNRESOLVED
29. 복수 Provider Evidence라도 점수 가산 없음
```

## 9.6 Guard

```text
30. Runtime Wiring 없음
31. Repository Writer 없음
32. Canonical Shadow Namespace 상수 없음
33. Summary / Rank 변경 없음
34. API / frontend 변경 없음
35. 신규 Production 파일 정확히 1개
36. 신규 Public Resolver 함수 최대 3개
```

---

# PART B. C3.0 Pre-Design — Agency / Regulation Input & Scoring Contract Freeze

## 10. 왜 C3.0 Pre-Design이 필요한가

`media_external` Stage 완료를 위해서는 아래가 필요하다.

```text
media_external
├─ news
├─ agency
└─ regulation

internal traces
→ externalMax
→ media_external_impact_score
→ media_external_financial_score
```

News만 구현하고 C3로 바로 들어가면 안 된다.

반드시 먼저 아래를 정해야 한다.

```text
1. agency.kcgs 입력 출처
2. agency.kcgs 3개년 등급 구조
3. agency.kcgs 추세 판정 방식
4. agency.kcgs Pillar → Sub-Issue Mapping
5. agency.kis 입력 계약
6. regulation Regime ↔ Sub-Issue Mapping
7. regulation applicability 입력 방식
8. agency / regulation Trace 저장 방식
9. externalMax 입력 Universe
```

이번 작업에서는 구현하지 않고 문서로 고정한다.

---

## 11. Regulation 계약

현재 `screening_policy.json`에는 아래 Rule Card가 이미 있다.

```text
CSRD
CBAM
DPP
```

Applicability:

```text
DIRECT_MANDATORY
MATERIAL_VALUE_CHAIN
MONITORING_ONLY
NOT_APPLICABLE
UNKNOWN
```

축별 Screening Signal이 이미 정책 JSON에 있다.

이번 C3.0 문서에서 아래 입력 구조를 확정한다.

## 11.1 Regulation Input DTO Proposal

```json
{
  "companyId": "string|int",
  "reportingYear": 2026,
  "regime": "CSRD | CBAM | DPP",
  "subIssueCode": "string",
  "applicability": "DIRECT_MANDATORY | MATERIAL_VALUE_CHAIN | MONITORING_ONLY | NOT_APPLICABLE | UNKNOWN",
  "effectiveDate": "YYYY-MM-DD|null",
  "deadlineDate": "YYYY-MM-DD|null",
  "evidenceRef": "string|null",
  "sourceType": "regulation",
  "providerKey": "internal_policy | consultant_input | system_seed",
  "inputMethod": "MANUAL | POLICY_SEED | IMPORT",
  "reviewStatus": "DRAFT | REVIEWED | APPROVED"
}
```

## 11.2 Regulation 입력 방식 Proposal

MVP 권장:

```text
Regime ↔ Sub-Issue Mapping
→ 정책 Seed

회사별 applicability
→ Onboarding 또는 Admin 화면에서 승인 입력

결과
→ step2CalcRegulation(regime, applicability, policy)
```

주의:

```text
Regulation
= media_external 내부 sourceType
= 독립 Stage 아님
```

## 11.3 Regulation 저장 검토

문서에서 아래 Option을 비교한다.

```text
Option A
→ 기존 ESG_DMA_SIGNAL_DETAIL.scoring_payload_json 내부 rawInputs

Option B
→ 회사별 Regulation Applicability 입력 테이블 신규 설계

Option C
→ Onboarding 입력 테이블 재사용
```

결론을 작성한다.

MVP 권장:

```text
회사별 applicability는 운영 입력 데이터이므로
전용 입력 위치가 필요함

단,
이번 C2.3에서는 DDL 작성 금지
C3.0 Schema Decision으로 넘김
```

---

## 12. Agency — KCGS 계약

현재 `screening_policy.json`에는 KCGS Rule Card가 이미 있다.

```text
gradeRisk:
S  = 0.0
A+ = 0.5
A  = 1.0
B+ = 2.0
B  = 3.0
C  = 4.0
D  = 5.0

trendModifier:
downgradeTwoOrMore = 1.0
downgradeOne       = 0.5
flat               = 0.0
upgrade            = 0.0
insufficientData   = UNOBSERVED

pillarSignalMax  = 5.0
maxSubIssueBoost = 1.0
boostMultiplier  = 0.20
```

KCGS는 독립 Stage가 아니다.

```text
media_external
└─ agency
   └─ kcgs
```

## 12.1 KCGS 3개년 입력 구조 Proposal

MVP에서는 최소 3개년 Pillar 등급을 입력한다.

```json
{
  "companyId": "string|int",
  "providerKey": "kcgs",
  "ratingYear": 2024,
  "overallGrade": "A+|A|B+|B|C|D|S|null",
  "pillarGrades": {
    "E": "A+|A|B+|B|C|D|S|null",
    "S": "A+|A|B+|B|C|D|S|null",
    "G": "A+|A|B+|B|C|D|S|null"
  },
  "sourceDocumentRef": "string|null",
  "inputMethod": "MANUAL | IMPORT | PROVIDER_API",
  "reviewStatus": "DRAFT | REVIEWED | APPROVED"
}
```

연도 예시:

```text
reportingYear = 2026
→ 2024
→ 2025
→ 2026
```

또는 최신 공시 지연을 고려할 경우:

```text
latestAvailableYear 기준 최근 3개년
```

이번 문서에서 어느 정책을 사용할지 결정한다.

MVP 권장:

```text
latestAvailableYear 기준 최근 3개년
```

이유:

```text
KCGS 평가 결과는 reportingYear와 정확히 일치하지 않을 수 있음
```

## 12.2 Trend 판정 Proposal

등급 Ordinal Rank를 JSON Policy 또는 별도 Mapping으로 고정한다.

```text
S  > A+ > A > B+ > B > C > D
```

최근 연도와 직전 연도의 등급 차이를 기준으로 한다.

```text
최근 연도 - 직전 연도
2단계 이상 하락
→ downgradeTwoOrMore

1단계 하락
→ downgradeOne

동일
→ flat

상승
→ upgrade

최근 2개년 미만
→ insufficientData
```

3개년은 아래 용도로 사용한다.

```text
최신 등급
→ gradeRisk

최신 vs 직전
→ trendModifier

3개년 전체
→ Trace / 품질 검증 / 급격한 변동 확인
```

## 12.3 Pillar → Sub-Issue Mapping Proposal

KCGS는 Pillar 단위 등급이다.
Sub-Issue까지 그대로 내려갈 수 없다.

따라서 아래 Mapping Seed가 필요하다.

```json
{
  "providerKey": "kcgs",
  "pillar": "E|S|G",
  "subIssueCode": "string",
  "boostApplicableYn": true,
  "mappingReason": "string",
  "activeYn": true
}
```

MVP 원칙:

```text
KCGS
→ Pillar Signal
→ bounded boost-only
→ Mapping된 Sub-Issue에만 전파
→ Canonical Final 직접 점수화 금지
```

현재 `screening_policy.json`의 아래 계약을 유지한다.

```text
directCanonicalFinalAllowedYn = false
```

## 12.4 KCGS 입력 UI / Import Proposal

문서에서 아래를 비교한다.

```text
Option A
→ Admin 수기 입력 UI

Option B
→ CSV Import

Option C
→ Provider API
```

MVP 권장:

```text
CSV Import + Admin 검토
```

이유:

```text
3개년 E/S/G Pillar 등급을 반복 입력해야 함
단순 수기 UI만으로는 오류 가능성이 높음
Provider API는 후속 확장
```

---

## 13. Agency — KIS 계약

현재 `screening_policy.json` 상태:

```text
capability = DATA_EXPORT_REQUIRED
reason = GRID_THRESHOLDS_REQUIRED
creditRatingPredictionAllowedYn = false
officialCreditRatingLabelAllowedYn = false
```

즉 현재 KIS는 수치 점수 Runtime이 없다.

## 13.1 KIS MVP 입력 Proposal

KIS 또는 신용평가 데이터는 임의 예측 등급으로 만들지 마라.

허용 가능한 입력 Proposal:

```json
{
  "companyId": "string|int",
  "providerKey": "kis",
  "reportingYear": 2026,
  "subIssueCode": "string",
  "indicatorCode": "string",
  "indicatorValue": 0.0,
  "indicatorUnit": "string",
  "gridVersion": "string",
  "sourceDocumentRef": "string|null",
  "inputMethod": "MANUAL | IMPORT | PROVIDER_API",
  "reviewStatus": "DRAFT | REVIEWED | APPROVED"
}
```

## 13.2 KIS 원칙

```text
금지:
- 신용등급 임의 예측
- 공식 신용등급 Label 생성
- GRID 없이 점수 Hardcode

허용:
- 승인된 Indicator Grid 기반 Screening Trace
- DATA_EXPORT_REQUIRED 상태 유지
```

이번 C3.0 문서에서 아래 결론을 작성한다.

```text
KIS Runtime 구현 전제:
1. 실제 Export 필드 목록 확보
2. Grid Threshold 승인
3. Indicator ↔ Sub-Issue Mapping 승인
4. Provider 자료 사용 권한 확인
```

C3 구현 시점에도 자료가 없으면:

```text
KIS
→ STATUS_CAPABILITY_PENDING
→ externalMax 숫자 입력에서 제외
→ Trace에는 Pending 사유 보존
```

---

## 14. ExternalMax 입력 계약

C3.0 문서에서 아래를 고정한다.

```text
externalMax 입력 허용:
- regulation Screening Trace
- kcgs Sub-Issue Boost Trace
- kis Screening Trace (숫자 관측된 경우만)
- news Screening Trace (C3에서 별도 결정)

externalMax 입력 금지:
- benchmark
- survey
- Legacy score
```

축별 MAX:

```text
impact
→ MAX(observed media_external internal traces)

financial
→ MAX(observed media_external internal traces)
```

가산 금지.

```text
news + regulation + kcgs
→ SUM 금지
→ MAX
```

---

## 15. C3.0 설계 문서 산출물

신규 문서:

```text
docs/dma/v1_3_mvp/14_PHASE_C3_0_EXTERNAL_CHANNEL_INPUT_SCORING_CONTRACT_RESULT.md
```

필수 목차:

```text
1. media_external 계층 고정
2. Regulation Input DTO Proposal
3. Regulation Regime ↔ Sub-Issue Mapping Proposal
4. Regulation Applicability 입력 주체 / 승인 흐름
5. KCGS 3개년 Grade DTO Proposal
6. KCGS latestAvailableYear 정책
7. KCGS Trend 판정
8. KCGS Pillar → Sub-Issue Mapping Proposal
9. KCGS Import UI / CSV Proposal
10. KIS Capability Pending 계약
11. KIS Export / Grid Threshold 선행조건
12. ExternalMax 허용 입력 / 금지 입력
13. 저장 위치 Option 비교
14. Schema Decision 필요 항목
15. 다음 단계
```

---

## 16. C2.3 결과 문서

신규 문서:

```text
docs/dma/v1_3_mvp/13_PHASE_C2_3_MEDIA_NEWS_RESOLVER_FOUNDATION_RESULT.md
```

필수 목차:

```text
1. Baseline
2. 수정 파일 목록
3. 신규 Production 파일 수
4. 신규 Public 함수 수
5. media_event_resolver_policy.json
6. Manifest / Registry 등록
7. DTO 추가
8. Pure Function 계약
9. Missing / Conflict 정책
10. Event Dedup 보수적 Foundation
11. Fact / Derived Factor / Axis Score 경계
12. Tests
13. Guard
14. 미수행 범위
15. Next Phase
```

Next Phase:

```text
C2.4
→ News Canonical Shadow Replace-Active Runtime Wiring

C3.1
→ Regulation Input Schema Decision / Runtime Foundation

C3.2
→ KCGS 3개년 Import + Pillar Boost Foundation

C3.3
→ KIS Capability Pending 또는 Grid 승인 후 Foundation

C3.4
→ externalMax Runtime Wiring
```

---

## 17. 변경 허용 파일

### 17.1 Production

허용:

```text
backend/src/resources/dma/v1_3_mvp/media_event_resolver_policy.json   # 신규
backend/src/resources/dma/v1_3_mvp/manifest.json
backend/src/utils/dmaruleregistry.py
backend/src/models/dmaengine.py
backend/src/services/medias/eventresolver.py                           # 신규
```

조건부 허용:

```text
backend/src/services/materialities/orchestrator.py
```

단, Pure Builder Wrapper가 반드시 필요한 경우만 허용한다.
Runtime Wiring 금지.

### 17.2 Test

허용:

```text
backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py   # 신규
backend/tests/test_dma_v1_3_phase_b_adapter_orchestrator.py           # Public Surface assertion 최소 보정 필요 시
```

### 17.3 Docs

허용:

```text
docs/dma/v1_3_mvp/12_PHASE_C2_2_MEDIA_NEWS_EVENT_RESOLVER_DEDUP_CONTRACT_RESULT.md

docs/dma/v1_3_mvp/13_PHASE_C2_3_MEDIA_NEWS_RESOLVER_FOUNDATION_RESULT.md

docs/dma/v1_3_mvp/14_PHASE_C3_0_EXTERNAL_CHANNEL_INPUT_SCORING_CONTRACT_RESULT.md
```

### 17.4 금지

```text
service.py Runtime Wiring
repository.py Writer
SQL / DDL
API
frontend
Summary / Rank
Top20
Survey
G0
agency Runtime
regulation Runtime
externalMax Runtime
```

---

## 18. Guard

반드시 검색한다.

```text
service.py Runtime Diff
Repository Writer Diff
ESG_DMA_SCORE_SUMMARY
final_score
rank_no
selected issue
media_external_news_v13_canonical_shadow
json.load(
eval(
exec(
```

Expected:

```text
service.py Runtime Diff = 0
Repository Writer Diff = 0
Summary / Rank Diff = 0
Canonical Shadow Namespace Runtime 상수 = 0
Service 직접 json.load = 0
eval / exec = 0
```

---

## 19. 검증 명령

현재 위치가 `backend`라면:

```bash
python -m compileall src -q

python -m pytest \
  tests/test_dma_v1_3_phase_c2_media_external_news_fact_resolver.py \
  tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py \
  tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py \
  -q

python -m pytest tests -q

git diff --check
git status --short
```

프로젝트 루트라면:

```bash
python -m compileall backend/src -q

python -m pytest \
  backend/tests/test_dma_v1_3_phase_c2_media_external_news_fact_resolver.py \
  backend/tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py \
  backend/tests/test_dma_v1_3_phase_c2_3_media_news_event_resolver.py \
  -q

python -m pytest backend/tests -q

git diff --check
git status --short
```

현재 Baseline:

```text
341 passed
1 skipped
```

신규 테스트 수만큼 증가하는 것은 정상이다.

---

## 20. 완료 보고 형식

```text
Phase C2.3 + C3.0 Pre-Design 완료 보고

Baseline
- branch:
- HEAD:
- 기존 전체 테스트:

C2.3 수정 파일
- 파일:
- 변경 내용:

C2.3 Production Surface
- 신규 Production 파일:
- 신규 Public 함수:
- 신규 DTO:
- Runtime Wiring 여부:

Resolver Policy
- policy 파일:
- manifest 등록:
- registry 등록:
- capability 상태:
- MVP Default Band 고지:

Pure Function
- resolveMediaNewsEventObservation:
- resolveMediaNewsCanonicalFactors:
- resolveMediaNewsEventGroup:
- Missing 처리:
- Dedup 처리:

비침투 확인
- service.py Runtime:
- repository writer:
- canonical shadow namespace runtime 상수:
- Summary:
- rank:
- Top20:
- API / frontend:
- SQL / DDL:

C3.0 Pre-Design
- Regulation 입력 구조:
- Regulation mapping:
- KCGS 3개년 구조:
- KCGS latestAvailableYear:
- KCGS trend:
- KCGS pillar mapping:
- KCGS 입력 UI / Import:
- KIS capability:
- KIS 선행조건:
- externalMax 입력:
- Schema Decision 필요 여부:

Tests
- compileall:
- 지정 suite:
- 전체 backend:
- git diff --check:
- guard:

미수행
- Runtime Wiring:
- DB 실접근:
- git add / commit / push:

다음 단계
- C2.4 News Canonical Shadow Runtime Wiring
- C3.1 Regulation Input Schema Decision / Foundation
```

완료 후 멈춰라.
