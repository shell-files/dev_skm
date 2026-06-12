# NEXT CLAUDE CODE PROMPT
# DMA v1.3 Phase C2.2 — media_external.news Event Fact Resolver / Canonical IRO / Event Dedup Contract Review
# R1

## 0. 작업 목적

현재 DMA v1.3 `media_external.news` Shadow Runtime은 아래까지 완료되었다.

```text
Phase C2.0
→ News Fact-only Resolver Foundation

Phase C2.0.1
→ Nested Similarity Metadata Allowlist Sanitization

Phase C2.1
→ News Fact Shadow Replace-Active Runtime Wiring

Phase C2.1.1
→ 정상 빈 Crawl 결과 Empty Replace
→ FAILED / PARTIAL_FAILED / Source 전체 거부 시 기존 Shadow Set 유지

Phase C2.1.2
→ 기사 일부 존재 + 일부 Source FAILED / PARTIAL_FAILED 시
   Legacy 저장 유지
   Shadow Replace Skip
```

현재 원격 기준 Branch / HEAD:

```text
branch:
feature/DAM_score_ljb

HEAD:
8f1ec72303f35a06b29c049cd109bb4ddc605ee0
```

현재 보고된 전체 Backend 회귀 기준:

```text
340 passed
1 skipped
```

이번 Phase C2.2의 목적은 **Production Canonical Scoring Runtime을 구현하는 것**이 아니다.

이번 단계는 아래 두 작업만 수행한다.

```text
A. C2.1.2 권장 회귀 테스트 1건 추가
   → Partial Crawl에서도 Legacy saveSignals()는 유지되고
      News Shadow Replace TX만 Skip되는지 직접 검증

B. media_external.news Event Fact Resolver,
   Canonical IRO 연결,
   Event-level Dedup 계약 설계
   → 구현 없이 문서로 고정
```

완료 후 멈춰라.

---

## 1. 이번 Phase의 성격

```text
Phase C2.2
= Design / Contract Freeze
+ Test-only Hardening 1건
```

이번 단계에서는 아래를 구현하지 마라.

```text
금지:
- News Canonical Resolver Production 함수 추가
- Event Dedup Production 함수 추가
- Canonical Score Runtime Wiring
- 신규 Shadow Namespace Runtime 연결
- 신규 Repository Writer
- 신규 DB Table / Column / FK / Index
- ESG_DMA_SCORE_SUMMARY 변경
- final_score / rank_no 변경
- Survey / G0 / Top20 변경
- agency / regulation / KCGS / KIS Runtime
- externalMax Runtime Wiring
- API / frontend 변경
- Runtime JSON 실제 추가 또는 수정
- Manifest Capability READY 전환
```

이번 단계에서 허용되는 코드 변경은 Test 파일 1개뿐이다.

---

## 2. 시작 전 Preflight

현재 작업 위치가 `backend` 폴더라면 아래를 실행한다.

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

Expected Baseline:

```text
branch:
feature/DAM_score_ljb

HEAD:
8f1ec72303f35a06b29c049cd109bb4ddc605ee0

전체 Backend:
340 passed
1 skipped
```

HEAD 또는 Working Tree가 다르면 reset하지 마라.
Baseline Diff로 문서에 기록한다.

이번 작업 중 아래를 수행하지 마라.

```text
git add
git commit
git push
```

---

## 3. 반드시 읽을 파일

### 3.1 News Runtime

```text
backend/src/services/medias/adapter.py
backend/src/services/medias/service.py
backend/src/services/medias/pipeline.py
backend/src/services/medias/crawler.py
backend/src/services/medias/baseline.py
```

### 3.2 v1.3 Canonical Core

```text
backend/src/models/dmaengine.py
backend/src/utils/dmascoring.py
backend/src/utils/dmarepository.py
backend/src/utils/dmaruleregistry.py
backend/src/services/materialities/orchestrator.py
```

### 3.3 Runtime Policy SSOT

```text
backend/src/resources/dma/v1_3_mvp/manifest.json
backend/src/resources/dma/v1_3_mvp/canonical_scoring_policy.json
backend/src/resources/dma/v1_3_mvp/ai_fact_validation_policy.json
backend/src/resources/dma/v1_3_mvp/screening_policy.json
```

### 3.4 Existing Tests

```text
backend/tests/test_dma_v1_3_phase_c2_media_external_news_fact_resolver.py
backend/tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py
backend/tests/test_dma_v1_3_phase_b_adapter_orchestrator.py
```

### 3.5 Schema Reference

현재 Repository Writer와 실제 Schema Reference에서 아래를 확인한다.

```text
ESG_DMA_SIGNAL_DETAIL
scoring_payload_json
source_step
source_type
delete_yn
```

DDL 변경은 금지한다.

---

## 4. Mandatory Architecture Invariant

## 4.1 DMA 상위 Stage는 3개만 유지

```text
1. benchmark
2. media_external
3. survey
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

`ESG_DMA_SCORE_SUMMARY`에는 기존 Stage Column만 사용한다.

```text
benchmark_impact_score
benchmark_financial_score
media_external_impact_score
media_external_financial_score
survey_impact_score
survey_financial_score
```

아래 전용 Column 추가 금지.

```text
news_impact_score
news_financial_score
regulation_impact_score
regulation_financial_score
kcgs_score
kis_score
```

## 4.4 externalMax 의미 유지

```text
externalMax
= media_external 내부 Source Type / Provider Trace의 축별 MAX 집계 Helper
```

이번 C2.2에서는 구현하지 마라.

---

## 5. 현재 Canonical Core에서 이미 고정된 사실

반드시 문서에 아래 내용을 확인하여 적는다.

## 5.1 AI는 Facts만 출력한다

현재 `ExtractedFactsV13`는 Fact-only DTO다.

허용 Fact 예시:

```text
subIssueCode
eventType
impactDirection
financialIroType
actualYn
officialConfirmedYn
explicitImmediateActionYn
explicitNoUrgencyYn
affectedCount
financialAmount
ratioValue
probabilityValue
eventDate
effectiveDate
deadlineDate
sourceType
classificationConfidence
eventGroupCandidateId
evidenceSpans
rawMetadata
```

금지:

```text
scale
scope
likelihood
irremediability
urgency
magnitude
revenueMagnitude
costMagnitude
capexMagnitude
assetLiabilityMagnitude
financingMagnitude
legalRegulatoryMagnitude
impactFactor
financialFactor
impactScore
financialScore
finalScore
sameEventGroupId
deduplicatedEventGroupId
scoreOverride
```

AI가 점수 또는 확정 Dedup 결정을 내리면 안 된다.

## 5.2 `eventGroupCandidateId`는 Hint다

```text
eventGroupCandidateId
= AI 또는 Upstream의 Candidate Hint
= 확정 Event Group ID 아님
= 단독 Merge Key로 사용 금지
```

금지:

```text
eventGroupCandidateId 동일
→ 자동으로 같은 Event로 확정
```

## 5.3 Similarity Score는 Factor가 아니다

```text
classificationConfidence
similarityScore
mappingWeight
```

는 Sub-Issue 분류 신뢰도다.

금지:

```text
classificationConfidence
→ scale 변환

similarityScore
→ likelihood 변환

mappingWeight
→ magnitude 변환
```

## 5.4 기사 개수는 Canonical Factor가 아니다

금지:

```text
기사 수
중복 기사 수
Provider 수
기사 빈도
→ scale / likelihood / magnitude 점수로 직접 변환
```

기사 수는 Evidence Coverage 또는 Provenance Trace로만 사용할 수 있다.

---

## 6. Canonical IRO 연결 전제

현재 `canonical_scoring_policy.json` 기준 Required Factor는 아래다.

```text
Impact Negative
required:
- scale
- likelihood

Impact Positive
required:
- scale
- likelihood

Financial Risk
required:
- magnitude

Financial Opportunity
required:
- magnitude
```

Optional Factor:

```text
Impact
- scope
- irremediability
- urgency

Financial
- likelihood
- urgency
```

현재 News Fact DTO에는 `scale`, `scope`, `likelihood`, `irremediability`, `magnitude`, `urgency`를 직접 저장하지 않는다.

따라서 아래 흐름이 필요하다.

```text
News Raw Result
→ ExtractedFactsV13
→ Event Fact Resolver
→ Derived Canonical Factor Candidate
→ Canonical step1CalcAxes()
→ AxisScoreTraceV13
```

중요:

```text
Fact
!=
Derived Factor
!=
Canonical Axis Score
!=
Final DMA Rank
```

이번 C2.2에서는 이 경계만 문서로 고정한다.

---

## 7. 필수 설계 산출물 A — Event Fact Resolver Contract

아래 계약을 문서에 작성한다.

## 7.1 입력

```text
Input:
- ExtractedFactsV13
- Source Provenance
- canonical_scoring_policy.json
- 향후 media_event_resolver_policy.json Proposal
```

## 7.2 출력 Proposal

Production DTO를 추가하지 말고, 문서에서 아래 Conceptual Shape만 정의한다.

```json
{
  "resolverStatus": "RESOLVED | PARTIAL | UNOBSERVED | CONFLICTED | REJECTED",
  "subIssueCode": "string",
  "eventKeyCandidate": "string|null",
  "impact": {
    "impactDirection": "negative|positive|null",
    "scale": "float|null",
    "scope": "float|null",
    "likelihood": "float|null",
    "irremediability": "float|null",
    "timeHorizon": "short|mid|long|null",
    "explicitNoUrgencyYn": "TRUE|FALSE|UNKNOWN|null",
    "ruleTrace": []
  },
  "financial": {
    "financialIroType": "risk|opportunity|null",
    "magnitude": "float|null",
    "likelihood": "float|null",
    "timeHorizon": "short|mid|long|null",
    "explicitNoUrgencyYn": "TRUE|FALSE|UNKNOWN|null",
    "ruleTrace": []
  },
  "dedup": {
    "eventGroupCandidateId": "string|null",
    "confirmedEventGroupKey": "string|null",
    "dedupStatus": "UNRESOLVED | UNIQUE | MERGED | CONFLICTED",
    "ruleTrace": []
  }
}
```

이 Shape는 설계용 Proposal이다.
이번 Phase에서 Pydantic DTO를 추가하지 마라.

## 7.3 Resolver Rule의 SSOT 위치 Proposal

향후 아래 Runtime JSON 추가 여부를 검토한다.

```text
backend/src/resources/dma/v1_3_mvp/media_event_resolver_policy.json
```

이번 C2.2에서는 실제 파일을 추가하지 마라.

문서에 Proposal Schema를 작성한다.

최소 섹션:

```text
version
ruleVersion
eventTypeNormalization
impactScaleRules
impactScopeRules
impactLikelihoodRules
impactIrremediabilityRules
financialMagnitudeRules
financialLikelihoodRules
timeHorizonRules
eventDedupRules
missingPolicy
conflictPolicy
```

## 7.4 Missing 처리

반드시 아래를 유지한다.

```text
Required Factor Missing
→ AxisScoreTraceV13.status = UNOBSERVED
→ score = None

금지:
Missing
→ 0점 대체
```

Optional Factor Missing은 Core 정책대로 관측된 값만 Reweight한다.

## 7.5 Hardcode 금지

금지:

```text
Python 코드 내부에 Event Type별 점수표 Hardcode
if eventType == "...": scale = 5
```

Rule Card는 Runtime JSON SSOT Proposal로 설계한다.

---

## 8. 필수 설계 산출물 B — Fact → Factor Mapping Decision Matrix

문서에 아래 표를 작성한다.

| Fact Field | Derived Factor 후보 | 현재 즉시 연결 가능 여부 | 필요한 추가 Rule Card | Missing 처리 | 비고 |
|---|---|---|---|---|---|
| `impactDirection` | Impact Polarity | 검토 | normalization rule | UNOBSERVED | AI Hint를 그대로 확정할지 검토 |
| `financialIroType` | Financial Polarity | 검토 | normalization rule | UNOBSERVED | risk/opportunity |
| `affectedCount` | scale 또는 scope 후보 | 직접 연결 금지 | band rule 필요 | UNOBSERVED | 임계치 SSOT 필요 |
| `financialAmount` | magnitude 후보 | 직접 연결 금지 | denominator 또는 absolute band 정책 필요 | UNOBSERVED | 금액만으로 임의 점수화 금지 |
| `ratioValue` | magnitude 후보 | 조건부 | ratio band 정책 | UNOBSERVED | 기존 financialMagnitudeRatioBands 재사용 가능성 검토 |
| `probabilityValue` | likelihood 후보 | 직접 연결 금지 | probability band 정책 필요 | UNOBSERVED | 0~1 또는 % normalize 필요 |
| `eventDate` | timeHorizon 후보 | 조건부 | 기준일 및 기간 band 정책 필요 | UNOBSERVED | reporting date 기준 필요 |
| `effectiveDate` | timeHorizon 후보 | 조건부 | 기준일 및 기간 band 정책 필요 | UNOBSERVED | |
| `deadlineDate` | urgency 후보 | 조건부 | 기준일 및 기간 band 정책 필요 | UNOBSERVED | |
| `explicitNoUrgencyYn` | urgency 0 후보 | 조건부 | TRUE만 허용 | UNOBSERVED | FALSE와 UNKNOWN 구분 |
| `actualYn` | resolver context | 직접 Factor 아님 | rule trace | UNKNOWN 유지 | |
| `officialConfirmedYn` | resolver confidence/context | 직접 Factor 아님 | rule trace | UNKNOWN 유지 | |
| `classificationConfidence` | Mapping confidence | Factor 사용 금지 | 없음 | None 유지 | |
| `eventGroupCandidateId` | Dedup 후보 Hint | 확정 Key 사용 금지 | dedup policy 필요 | UNRESOLVED | |

문서에서 각 Row를 실제 코드·정책 파일 기준으로 검토하고 결론을 기록한다.

---

## 9. 필수 설계 산출물 C — Event Dedup Contract

News 기사 중복 제거와 Event-level Dedup을 구분한다.

## 9.1 URL 중복 제거

현재 Crawler에서 URL Normalize 후 중복 제거가 존재한다.

```text
normalizedUrl
→ seenUrls
→ 동일 URL 기사 Skip
```

이것은 Article Dedup이다.

## 9.2 Event-level Dedup

Event-level Dedup은 아래 문제를 해결한다.

```text
서로 다른 URL
서로 다른 Provider
서로 다른 제목
하지만 실제로는 동일 사건
```

예:

```text
impacton 기사 A
esgeconomy 기사 B
→ 동일 공급망 사고를 보도
```

이 경우 Canonical Score를 기사 수만큼 중복 계산하면 안 된다.

## 9.3 확정 Merge Key Proposal

문서에서 아래 기준을 검토하고 결론을 작성한다.

```text
Mandatory 후보:
- runId 또는 company context
- subIssueCode
- normalized eventType
- normalized event date bucket
- normalized entity / subject key
- source-independent event fingerprint

Optional 보조:
- normalized location
- normalized counterparty
- normalized regulatory regime
- normalized amount bucket
- title/body similarity
- eventGroupCandidateId
```

금지:

```text
URL만 같음
→ Event-level Merge 확정

eventGroupCandidateId만 같음
→ Event-level Merge 확정

제목 유사도만 높음
→ Event-level Merge 확정
```

## 9.4 Dedup 상태 Proposal

```text
UNRESOLVED
UNIQUE
MERGED
CONFLICTED
REJECTED
```

## 9.5 Score Inflation 방지

반드시 아래 계약을 고정한다.

```text
동일 Event Group
→ EvidenceSpan은 합칠 수 있음
→ Provenance Source는 복수 보존
→ Canonical Factor는 사건 단위로 1회 Resolution
→ Canonical Axis Score는 사건 단위로 1회 계산
→ 기사 수에 따라 점수 가산 금지
```

Sub-Issue 최종 집계는 기존 Core 원칙을 유지한다.

```text
복수 Event Group
→ Impact 축 MAX
→ Financial 축 MAX
→ Offsetting 금지
```

---

## 10. 필수 설계 산출물 D — Trace / Storage Contract

현재 `ScoringPayloadV13`는 기존 컬럼에 저장된다.

```text
ESG_DMA_SIGNAL_DETAIL.scoring_payload_json
```

현재 Payload 구성:

```text
extractedFacts
factorTrace
axisScores
screeningTrace
aggregationTrace
legacyCompatibility
```

현재 Payload에는 Event Dedup 전용 Trace가 없다.

따라서 문서에서 아래 Option을 비교한다.

### Option A — ScoringPayloadV13에 Optional Event Resolution Trace 추가

```text
향후 Optional DTO:
eventResolutionTrace
```

장점:

```text
DB DDL 변경 없음
기존 scoring_payload_json 재사용
Fact와 Derived Decision 분리 가능
```

주의:

```text
이번 C2.2에서는 DTO 추가 금지
향후 C2.3 승인 후 구현
```

### Option B — rawMetadata 내부 기록

```text
ExtractedFactsV13.rawMetadata.eventDedupTrace
```

판정:

```text
비권장
```

이유:

```text
Derived Decision이 Source Fact Metadata에 섞임
Fact / Resolution 경계 오염
```

### Option C — 신규 Table / Column

판정:

```text
C2.2 범위 밖
MVP에서는 우선 금지
```

문서에 권장안과 이유를 작성한다.

기본 권장:

```text
Option A
```

---

## 11. 필수 설계 산출물 E — Namespace / Runtime 단계 Proposal

현재 Fact Shadow Namespace:

```text
MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP
= "media_external_news_v13_shadow"
```

현재 Namespace는 Fact Shadow 전용이다.

향후 Canonical Resolution Shadow를 연결할 경우, Fact Row를 덮어쓰지 않는다.

문서에서 아래 Namespace Proposal을 검토한다.

```text
media_external_news_v13_canonical_shadow
```

주의:

```text
이번 C2.2에서는 상수 추가 금지
Repository Writer 추가 금지
Runtime 연결 금지
```

설계 문서에서만 Proposal로 작성한다.

향후 권장 단계:

```text
C2.3
→ media_event_resolver_policy.json 승인
→ Resolver DTO / Pure Function Foundation
→ Event Resolution Trace DTO 결정

C2.4
→ News Canonical Shadow Replace-Active Runtime Wiring
→ Fact Shadow와 Canonical Shadow 분리
→ Summary / Rank 비침투 유지

C3
→ media_external 내부 Screening 집계
→ news / agency / regulation 내부 Trace
→ externalMax
```

---

## 12. C2.1.2 권장 회귀 테스트 1건 추가

이번 Phase에서 허용되는 유일한 Code 변경이다.

수정 허용 파일:

```text
backend/tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py
```

Production Code 변경 금지.

## 12.1 검증 목적

아래 계약을 직접 증명한다.

```text
기사 존재
+
일부 Source FAILED
+
Legacy scoredSignals 존재

→ Legacy saveSignals() 1회 호출
→ News Shadow Replace TX 미호출
```

현재 기존 테스트는 Shadow TX 미호출만 검증한다.
Legacy saveSignals 유지까지 직접 검증하지 않는다.

## 12.2 테스트명 권장

```python
test_articles_with_failed_source_keeps_legacy_save_and_skips_shadow_replace
```

## 12.3 구현 방식

기존 `PhaseC212PartialCrawlProtectionTest` 내부에 추가한다.

권장 형태:

```python
def test_articles_with_failed_source_keeps_legacy_save_and_skips_shadow_replace(self):
    crawlResult = self._CrawlExecutionResult(
        requestedSources=["impacton", "esgeconomy"],
        allowedSources=["impacton", "esgeconomy"],
        sourceBreakdown=[
            self._makeBreakdown("impacton", "SUCCESS"),
            self._makeBreakdown(
                "esgeconomy",
                "FAILED",
                error="network error",
            ),
        ],
        articles=[buildNewsResult()],
        errors=[
            self._MediaCrawlerError(
                sourceKey="esgeconomy",
                message="network error",
            )
        ],
    )

    legacySignal = object()

    with patch.object(svc, "crawlNewsArticles", return_value=crawlResult), \
         patch.object(svc, "processMediaPipeline", return_value=[buildNewsResult()]), \
         patch.object(svc, "convertMediaToDmaSignals", return_value=[legacySignal]), \
         patch.object(svc, "applyMediaBaseline", return_value=[legacySignal]), \
         patch.object(svc, "scoreSignals", return_value=[legacySignal]), \
         patch.object(svc, "saveSignals") as saveMock, \
         patch.object(svc, "step4ReplaceMediaNewsShadowTracesTx") as txMock:
        svc.runMediaCrawlAndAnalyze(self._makeRequest())

    saveMock.assert_called_once_with(
        runId=99,
        signals=[legacySignal],
        fileId=None,
        sourceTitle="Media Analysis",
    )

    txMock.assert_not_called()
```

기존 테스트 Fixture 구조에 맞게 최소 수정한다.

신규 Test Helper를 과도하게 추가하지 마라.

---

## 13. SKIPPED Source 정책 고정

현재 `_isCrawlComplete()`는 `sourceBreakdown` 전체가 `SUCCESS`인지 본다.

Crawler는 아래를 `SKIPPED`로 기록할 수 있다.

```text
미등록 Source
비활성 Source
중복 요청 Source
```

MVP 정책을 아래로 고정한다.

```text
정책 A — Conservative Skip

요청 Source 중 SKIPPED가 하나라도 존재
→ Crawl Complete 아님
→ News Shadow Replace Skip
→ 기존 활성 Shadow Set 유지
```

이번 C2.2에서는 Production 변경 없이 문서에 고정한다.

향후 정책 변경은 별도 승인 후 진행한다.

---

## 14. 변경 허용 범위

### 14.1 Test Code

허용:

```text
backend/tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py
```

추가:

```text
Legacy saveSignals 유지 직접 검증 테스트 1건
```

### 14.2 Docs

신규 문서:

```text
docs/dma/v1_3_mvp/12_PHASE_C2_2_MEDIA_NEWS_EVENT_RESOLVER_DEDUP_CONTRACT_RESULT.md
```

필요하면 Inventory 문서 Append 허용:

```text
docs/dma/v1_3_mvp/04_PHASE_C0_RUNTIME_MIGRATION_INVENTORY_RESULT.md
```

단, Append만 허용한다.
기존 내용 삭제 또는 대규모 재작성 금지.

### 14.3 Production Code

```text
변경 금지
```

---

## 15. 문서 필수 목차

`12_PHASE_C2_2_MEDIA_NEWS_EVENT_RESOLVER_DEDUP_CONTRACT_RESULT.md`에 아래를 포함한다.

```text
1. Baseline
   - branch
   - HEAD
   - git status
   - 기존 전체 테스트

2. C2.1.2 Test Hardening
   - 추가 테스트명
   - 검증 계약
   - Production Diff 없음 확인

3. Current Runtime Inventory
   - News Raw Result
   - ExtractedFactsV13
   - Fact Shadow
   - Existing Canonical Core
   - Missing Resolver Layer

4. Mandatory Invariants
   - top-level stages = benchmark / media_external / survey
   - news / agency / regulation 내부 계층
   - Summary Column 추가 금지
   - Top20 invariant 유지

5. Fact-only Boundary
   - Allowed Facts
   - Forbidden Scores / Factors
   - Candidate Hint vs Confirmed Decision

6. Canonical Required Factor Gap
   - Impact required
   - Financial required
   - 현재 Fact DTO Gap

7. Event Fact Resolver Contract Proposal
   - Input
   - Output Conceptual Shape
   - Resolver Status
   - Missing / Conflict 정책

8. Fact → Factor Mapping Decision Matrix
   - 각 Fact별 연결 가능성
   - 추가 Rule Card 필요 여부
   - UNOBSERVED 처리

9. media_event_resolver_policy.json Proposal
   - 신규 SSOT 필요 여부
   - Schema Proposal
   - Runtime JSON 실제 추가는 보류

10. Event-level Dedup Contract
    - Article Dedup vs Event Dedup
    - Candidate Hint
    - Confirmed Merge Criteria
    - Score Inflation 방지
    - Dedup Status

11. Trace / Storage Contract
    - Option A / B / C 비교
    - 권장안
    - DB DDL 변경 없음

12. Namespace Proposal
    - Fact Shadow 유지
    - Canonical Shadow Proposal
    - 이번 단계 구현 없음

13. SKIPPED Source Conservative Policy
    - 현재 동작
    - 정책 A 고정

14. Tests
    - compileall
    - 신규 테스트
    - C2.1 파일
    - 전체 Backend
    - git diff --check

15. Guard Result
    - Production Diff 0개
    - Runtime JSON Diff 0개
    - SQL / DDL Diff 0개
    - API / frontend Diff 0개
    - Manifest capability 유지

16. Unresolved Decisions
    - event type normalization vocabulary
    - affectedCount band
    - probability band
    - financialAmount denominator / absolute band
    - date 기준일
    - entity / subject normalization
    - Event Dedup fingerprint
    - Event Resolution Trace DTO

17. Next Phase
    - Phase C2.3 Resolver Policy Approval + Pure Function Foundation
```

---

## 16. Manifest Capability 유지

현재 Manifest:

```text
mediaEventCanonicalAdapter
= CONFIG_PENDING
```

이번 C2.2에서도 유지한다.

금지:

```text
CONFIG_PENDING
→ READY 변경
```

이유:

```text
Resolver Rule Card 미승인
Event Dedup Contract만 설계됨
Production Resolver 미구현
```

---

## 17. 유지보수 규칙

이번 설계에서 향후 구현 규칙도 고정한다.

```text
1. SSOT는 Runtime JSON 1곳
2. Python은 Rule Card 실행만 담당
3. AI Fact와 Derived Factor 분리
4. Confirmed Dedup Decision은 Fact Metadata에 섞지 않음
5. 범용 Framework 과잉 도입 금지
6. 작은 Helper 과분리 금지
7. Resolver 함수는 향후 최대 2~3개 수준으로 제한
8. Repository Writer는 Fact / Canonical 목적을 명확히 분리
9. Summary / Rank는 Shadow 검증 전 침투 금지
```

금지 예시:

```text
resolveScaleFromAffectedCount()
resolveScaleFromEventType()
resolveLikelihoodFromProbability()
resolveUrgencyFromDeadline()
resolveMagnitudeFromRatio()
resolveDedupByTitle()
resolveDedupByDate()
resolveDedupByCandidate()
...
```

처럼 한 줄 분기마다 Helper를 쪼개지 마라.

향후 권장 구조 Proposal:

```text
resolveMediaNewsEventObservation(...)
resolveMediaNewsCanonicalFactors(...)
resolveMediaNewsEventGroup(...)
```

최대 3개 수준으로 유지한다.

---

## 18. 검증 명령

현재 위치가 `backend`라면:

```bash
python -m compileall src -q

python -m pytest \
  tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py \
  -q

python -m pytest tests -q

git diff --check
git status --short
```

프로젝트 루트라면:

```bash
python -m compileall backend/src -q

python -m pytest \
  backend/tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py \
  -q

python -m pytest backend/tests -q

git diff --check
git status --short
```

Expected:

```text
C2.1 테스트 파일:
기존 42 passed
→ 신규 1건 추가 후 43 passed 예상

전체 Backend:
기존 340 passed, 1 skipped
→ 신규 1건 추가 후 341 passed, 1 skipped 예상
```

---

## 19. 완료 보고 형식

아래 형식으로 보고한다.

```text
Phase C2.2 완료 보고

Baseline
- branch:
- HEAD:
- 기존 전체 테스트:

Test Hardening
- 수정 파일:
- 추가 테스트명:
- 검증 계약:
- 신규 Production 함수:
- Production Diff:

Contract Review
- Fact-only Boundary:
- Canonical Required Factor Gap:
- Resolver Policy SSOT Proposal:
- Event Dedup Candidate Hint:
- Confirmed Dedup Decision:
- Score Inflation 방지:
- Storage 권장안:
- Canonical Shadow Namespace Proposal:
- SKIPPED Source 정책:

Manifest
- mediaEventCanonicalAdapter:

Unresolved Decision
- 항목:

테스트 결과
- compileall:
- C2.1 테스트 파일:
- 전체 backend:
- git diff --check:
- git status:

Guard
- Production Diff:
- Runtime JSON Diff:
- SQL / DDL Diff:
- API / frontend Diff:
- git add / commit / push:

다음 단계
- Phase C2.3 Resolver Policy Approval + Pure Function Foundation
```

완료 후 멈춰라.
