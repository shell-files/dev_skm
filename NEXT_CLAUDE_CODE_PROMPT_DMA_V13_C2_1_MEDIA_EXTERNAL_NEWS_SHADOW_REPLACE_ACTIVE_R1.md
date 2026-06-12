# NEXT CLAUDE CODE PROMPT
# DMA v1.3 Phase C2.1 — media_external.news Shadow Replace-Active Runtime Wiring
# R1

## 0. 작업 목적

현재 DMA v1.3 Benchmark Shadow Runtime은 MVP 기준으로 완료되었다.

`media_external.news` Fact Resolver Foundation도 아래 범위까지 완료되었다.

```text
media_external.news 원본 분석 결과
→ step0NormalizeMediaFacts()
→ ExtractedFactsV13 Fact-only DTO
→ sourceType = "news"
→ providerKey Metadata 분리
→ Event Fact passthrough
→ Similarity Score 비점수화
→ Top-level Score / Factor 오염 차단
→ issueSimilarityMatches Nested Allowlist Sanitization
```

현재 전체 Backend 회귀 기준:

```text
298 passed
1 skipped
```

이번 Phase C2.1의 목적은 현재 Legacy Media Runtime을 유지한 채,
`media_external.news` Fact-only Payload를 `ESG_DMA_SIGNAL_DETAIL`에 Shadow Row로 저장하는 것이다.

Benchmark에서 확정한 Replace-Active Transaction 원칙을 재사용한다.

단, News Shadow는 Benchmark Screening Snapshot과 성격이 다르다.

```text
Benchmark
→ Fact Shadow + Screening Shadow
→ Universe 62개 NONE Backfill 필요

media_external.news
→ 관측된 News Fact Shadow만 저장
→ Universe NONE Backfill 금지
→ Screening 집계 금지
```

이번 단계에서는 News Fact Shadow Replace-Active Runtime Wiring까지만 구현한다.

완료 후 멈춰라.

---

## 1. 시작 전 Preflight

먼저 아래 명령을 실행하고 결과 문서에 기록한다.

현재 작업 위치가 `backend` 폴더라면 아래 명령을 사용한다.

```bash
git status --short
git branch --show-current
git rev-parse HEAD

python -m compileall src -q
python -m pytest tests -q
```

기준 브랜치:

```text
feature/DAM_score_ljb
```

예상 기준 HEAD:

```text
42091567c24cf7515240fc832a1c6e29aa5ab16d
```

예상 전체 회귀:

```text
298 passed
1 skipped
```

HEAD가 달라졌거나 Working Tree에 기존 변경이 있으면
절대 reset하지 말고 Baseline Diff로 기록한다.

이번 작업 중 아래는 수행하지 마라.

```text
git add
git commit
git push
```

---

## 2. 반드시 유지할 Architecture Invariant

## 2.1 DMA 상위 Stage는 정확히 3개다

```text
1. benchmark
2. media_external
3. survey
```

독립 Stage 추가 금지.

## 2.2 media_external 내부 계층

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

## 2.3 Stage 승격 금지

아래 값은 독립 DMA Stage가 아니다.

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

내부 Helper, Trace Channel, Provider Metadata 분리는 허용한다.
단, 내부 분리는 DB Summary Stage 추가를 의미하지 않는다.

## 2.4 Summary Column 추가 금지

`ESG_DMA_SCORE_SUMMARY`에는 기존 컬럼만 사용한다.

```text
benchmark_impact_score
benchmark_financial_score
media_external_impact_score
media_external_financial_score
survey_impact_score
survey_financial_score
```

아래 전용 컬럼 추가 금지.

```text
news_impact_score
news_financial_score
regulation_impact_score
regulation_financial_score
kcgs_score
kis_score
```

이번 C2.1에서는 `ESG_DMA_SCORE_SUMMARY` 자체를 수정하지 마라.

## 2.5 externalMax 의미

```text
externalMax
= media_external 내부 Source Type / Provider Trace의 축별 MAX 집계 Helper
```

이번 단계에서는 externalMax를 호출하거나 구현하지 마라.

---

## 3. Pre-Survey Top20 Invariant 유지

이번 단계에서 Top20 로직을 수정하지 마라.

향후 Survey Runtime Wiring에서는 아래 정책을 유지한다.

```text
ESG_DMA_SCORE_SUMMARY
= Sub-Issue별 단계 점수 집계 SSOT

별도 Top20 Summary Table 생성 금지
별도 Top20 Score Column 생성 금지
별도 Top20 Batch Table 생성 금지

설문 생성 직전:
Benchmark + Media External 반영 Summary
→ final_score
→ rank_no
→ rank_no IS NOT NULL
→ final_score IS NOT NULL
→ ORDER BY rank_no ASC
→ LIMIT 20

설문 생성 시:
대상 Sub-Issue 20개 Freeze

Survey 응답 반영 후:
Final Score / Rank 재계산
기존 설문 대상 20개 목록은 유지
```

---

## 4. 현재 Runtime 기준점

반드시 아래 파일을 먼저 읽어라.

```text
backend/src/services/medias/adapter.py
backend/src/services/medias/service.py
backend/src/services/medias/pipeline.py
backend/src/services/medias/crawler.py

backend/src/services/materialities/orchestrator.py
backend/src/utils/dmarepository.py
backend/src/models/dmaengine.py

backend/tests/test_dma_v1_3_phase_c1_3_benchmark_shadow_replace_active.py
backend/tests/test_dma_v1_3_phase_c1_benchmark_shadow.py
backend/tests/test_dma_v1_3_phase_c2_media_external_news_fact_resolver.py
```

현재 Legacy Media Runtime:

```text
runMediaAnalysis()
→ processMediaPipeline()
→ convertMediaToDmaSignals()
→ applyMediaBaseline()
→ scoreSignals()
→ saveSignals()
→ return scoredSignals
```

이번 작업 이후에도 Legacy 반환값과 Legacy 저장 흐름은 유지해야 한다.

신규 Shadow Hook은 Legacy 성공 이후에만 실행한다.

---

## 5. 이번 단계의 정확한 범위

## 5.1 구현할 흐름

```text
runMediaAnalysis()
→ processMediaPipeline()
→ Legacy convertMediaToDmaSignals()
→ Legacy applyMediaBaseline()
→ Legacy scoreSignals()
→ Legacy saveSignals()             # scoredSignals가 존재할 때 기존대로 실행

→ Shadow Hook
   → step0NormalizeMediaFacts(pipelineResults)
   → step0BuildFactTrace(
         extractedFact=fact,
         sourceChannel="media_external",
     )
   → step4ReplaceMediaNewsShadowTracesTx(
         runId=runId,
         factPayloads=factPayloads,
     )

→ return scoredSignals
```

중요:

```text
Shadow Fact는 pipelineResults에서 생성한다.
scoredSignals 또는 DMASignal에서 역변환하지 않는다.
```

이유:

```text
scoredSignals에는 Legacy Factor / Score가 포함될 수 있음
→ Fact-only DTO 오염 위험
```

## 5.2 Shadow Hook 실패 격리

Shadow Hook 전체를 `try / except`로 격리한다.

```text
Media Fact Normalize 실패
→ Warning 출력
→ Replace Transaction 미호출
→ 기존 활성 News Shadow Set 유지
→ Legacy 성공 응답 유지

Media Trace Build 실패
→ Warning 출력
→ Replace Transaction 미호출
→ 기존 활성 News Shadow Set 유지
→ Legacy 성공 응답 유지

News Shadow Replace TX 실패
→ ROLLBACK
→ Warning 출력
→ 기존 활성 News Shadow Set 유지
→ Legacy 성공 응답 유지
```

Legacy 실패는 그대로 유지한다.

```text
Legacy saveSignals() 실패
→ 기존 실패 전파
→ Shadow Hook 미호출
```

## 5.3 정상적인 빈 결과

아래 경우는 오류가 아니다.

```text
processMediaPipeline() 성공
→ pipelineResults = []
→ factPayloads = []
```

이 경우에도 Replace Transaction을 호출한다.

```text
기존 활성 News Shadow Row soft-delete
→ 신규 INSERT 0건
→ 활성 News Shadow Set = 빈 집합
→ COMMIT
```

이유:

```text
재분석 결과 관측 News Fact가 0건이면
이전 활성 News Fact를 유지하면 안 됨
```

오류와 정상 빈 결과를 혼동하지 마라.

---

## 6. Production 변경 허용 파일

기본 허용:

```text
backend/src/services/medias/service.py
backend/src/utils/dmarepository.py
```

C2.0.1 선택 보완을 포함할 경우 조건부 허용:

```text
backend/src/services/medias/adapter.py
```

그 외 Production 파일 변경 금지.

특히 아래는 수정하지 마라.

```text
backend/src/services/medias/pipeline.py
backend/src/services/medias/crawler.py
backend/src/services/medias/baseline.py
backend/src/utils/dmascoring.py
backend/src/services/materialities/orchestrator.py
backend/src/models/dmaengine.py
backend/src/resources/dma/v1_3_mvp/*.json
backend/src/apis/**
frontend/**
SQL / DDL
```

---

## 7. C2.1-A 선택 보완 — Similarity Metadata Scalar Normalization

C2.0.1에서 Nested Allowlist는 적용됐다.

현재 허용 키:

```text
issueId
subIssueNameKr
score
```

다만 허용 키 내부 값이 dict 또는 list인 경우까지 Scalar로 정규화하면 더 안전하다.

이번 C2.1에서 기존 `_sanitizeIssueSimilarityMatches()` 함수 내부만 최소 보정하라.

신규 Helper를 만들지 마라.

권장 계약:

```python
def _sanitizeIssueSimilarityMatches(rawMatches) -> list:
    if not isinstance(rawMatches, list):
        return []

    sanitized = []

    for match in rawMatches:
        if not isinstance(match, Mapping):
            continue

        issueId = match.get("issueId")
        subIssueNameKr = match.get("subIssueNameKr")
        score = asFloat(match.get("score"))

        sanitized.append({
            "issueId": str(issueId) if issueId is not None and not isinstance(issueId, (dict, list, tuple, set)) else None,
            "subIssueNameKr": str(subIssueNameKr) if subIssueNameKr is not None and not isinstance(subIssueNameKr, (dict, list, tuple, set)) else None,
            "score": score,
        })

    return sanitized
```

핵심 원칙:

```text
허용 키 내부 Nested Object도 rawMetadata에 남기지 않는다.
```

이 보완은 Runtime Wiring과 함께 수행해도 된다.

---

## 8. Repository 구현 계약

## 8.1 Namespace SSOT 추가

`backend/src/utils/dmarepository.py`에 아래 상수를 한 번만 선언한다.

```python
MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP = "media_external_news_v13_shadow"
```

문자열 Literal을 Service, Test Helper, 다른 파일에 반복 작성하지 마라.

Runtime Code는 반드시 Repository 상수를 Import하여 사용한다.

## 8.2 기존 SQL 재사용

기존 `_SHADOW_INSERT_SQL`을 재사용한다.

새 INSERT SQL 상수를 만들지 마라.

## 8.3 Private Row Serializer 추가

Private Helper 최대 1개 추가 허용:

```python
_buildMediaNewsShadowRows(
    runId: int,
    payloads: Sequence[Dict[str, Any]],
) -> list[tuple]
```

역할:

```text
ScoringPayloadV13 검증
→ JSON 직렬화
→ extractedFacts 필수 검증
→ subIssueCode 필수 검증
→ sourceType == "news" 검증
→ ESG_DMA_SIGNAL_DETAIL INSERT tuple 생성
```

Row 계약:

```text
esg_materiality_run_id = runId
evidence_id             = NULL
raw_issue_label         = extractedFacts.rawMetadata.rawIssueLabel | ""
sub_issue_code          = extractedFacts.subIssueCode
source_step             = MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP
source_type             = "news"
impact_score            = NULL
financial_score         = NULL
confidence_score        = extractedFacts.classificationConfidence
scoring_payload_json    = ScoringPayloadV13 top-level JSON
```

금지:

```text
v13Shadow wrapper 추가
Legacy DMASignal 저장
Impact / Financial Score Column 기록
Summary 갱신
Rank 갱신
Selection 갱신
```

## 8.4 Public Replace Transaction 함수 추가

신규 Public Production 함수는 정확히 1개만 허용한다.

```python
step4ReplaceMediaNewsShadowTracesTx(
    runId: int,
    factPayloads: Sequence[Dict[str, Any]],
) -> int
```

Transaction 내부 순서:

```text
1. Payload Row 사전 직렬화
2. getConn()
3. conn.autocommit = False
4. SELECT ESG_MATERIALITY_RUN Row FOR UPDATE
5. 기존 활성 media_external.news Shadow Row만 soft-delete
6. 신규 Fact Row INSERT
7. 활성 News Shadow Row Count 검증
8. 성공 시 COMMIT
9. 실패 시 ROLLBACK
10. finally close
```

Row Lock:

```sql
SELECT id
FROM ESG_MATERIALITY_RUN
WHERE id = ?
FOR UPDATE
```

Soft-delete 대상:

```sql
UPDATE ESG_DMA_SIGNAL_DETAIL
SET delete_yn = 1
WHERE esg_materiality_run_id = ?
  AND source_step = ?
  AND delete_yn = 0
```

파라미터:

```text
runId
MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP
```

검증 Query:

```sql
SELECT COUNT(*) AS row_count
FROM ESG_DMA_SIGNAL_DETAIL
WHERE esg_materiality_run_id = ?
  AND source_step = ?
  AND delete_yn = 0
```

검증 조건:

```text
row_count == len(factRows)
```

주의:

```text
COUNT(DISTINCT sub_issue_code) == row_count
```

검증은 금지한다.

News Fact는 동일 Sub-Issue에 복수 기사·복수 Chunk가 존재할 수 있다.
중복 Sub-Issue Row는 정상이다.

## 8.5 정상 빈 결과 허용

```text
factPayloads = []
```

를 허용한다.

빈 배열이면:

```text
기존 활성 News Shadow Row soft-delete
INSERT 생략
row_count == 0 검증
COMMIT
return 0
```

`factPayloads`가 비었다는 이유로 조기 return하지 마라.

## 8.6 Transaction Mode

`conn.autocommit = False`는 반드시 `try` 블록 내부에 둔다.

```python
conn = getConn()

if conn is None:
    raise RuntimeError(...)

try:
    conn.autocommit = False
    ...
finally:
    if hasattr(conn, "close"):
        conn.close()
```

## 8.7 Legacy Side Effect 금지

신규 Repository 함수 내부에서 아래를 호출하지 마라.

```text
saveSignals
recalcStage
recalcFinal
updateRanks
ESG_DMA_SCORE_SUMMARY
ESG_MATERIALITY_SELECTED_SUB_ISSUE
ESG_DMA_EVIDENCE INSERT
```

---

## 9. Service 구현 계약

`backend/src/services/medias/service.py`에서 기존 Legacy 흐름은 그대로 유지한다.

필요 Import:

```python
from src.services.medias.adapter import (
    convertMediaToDmaSignals,
    step0NormalizeMediaFacts,
)

from src.services.materialities.orchestrator import step0BuildFactTrace

from src.utils.dmarepository import (
    ...
    step4ReplaceMediaNewsShadowTracesTx,
)
```

Shadow Hook은 Legacy 저장 이후에만 실행한다.

권장 형태:

```python
    if scoredSignals:
        saveSignals(
            runId=runId,
            signals=scoredSignals,
            fileId=None,
            sourceTitle="Media Analysis",
        )

    try:
        shadowFacts = step0NormalizeMediaFacts(pipelineResults)

        factPayloads = [
            step0BuildFactTrace(
                extractedFact=fact,
                sourceChannel="media_external",
            )
            for fact in shadowFacts
        ]

        step4ReplaceMediaNewsShadowTracesTx(
            runId=runId,
            factPayloads=factPayloads,
        )

    except Exception as shadowError:
        print(
            "Warning: media_external.news v1.3 shadow replace failed: "
            f"{shadowError}"
        )

    return scoredSignals
```

주의:

```text
step0NormalizeMediaFacts()
→ 반드시 pipelineResults 입력

step0BuildFactTrace()
→ sourceChannel = "media_external"

ExtractedFactsV13.sourceType
→ adapter가 "news"로 유지
```

Service에서 Namespace 문자열을 직접 사용하지 마라.

---

## 10. Public Surface 제한

신규 Public Production 함수:

```text
정확히 1개
- step4ReplaceMediaNewsShadowTracesTx
```

신규 Private Helper:

```text
최대 1개
- _buildMediaNewsShadowRows
```

기존 `_sanitizeIssueSimilarityMatches()` 내부 보정은 신규 Helper로 세지 않는다.

신규 Production 파일:

```text
0개
```

금지:

```text
Generic Shadow Manager
Generic Snapshot Framework
Media Shadow Base Class
Wrapper
Alias
Factory
Repository 파일 분리
Benchmark Writer 대규모 리팩터링
```

Benchmark Writer를 억지로 범용화하지 마라.

현재 단계에서는 News 전용 함수가 유지보수상 더 명확하다.

---

## 11. 테스트

## 11.1 신규 테스트 파일

신규 Test 파일 1개 허용:

```text
backend/tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py
```

## 11.2 Repository 테스트 최소 항목

```text
1. MEDIA_EXTERNAL_NEWS_V13_SHADOW_SOURCE_STEP 상수
   → dmarepository.py 한 곳에서만 선언

2. _buildMediaNewsShadowRows()
   → source_step = media_external_news_v13_shadow
   → source_type = news
   → impact_score = NULL
   → financial_score = NULL
   → confidence_score 보존
   → ScoringPayloadV13 top-level JSON 저장
   → v13Shadow wrapper 없음

3. extractedFacts 누락
   → ValueError

4. subIssueCode 누락
   → ValueError

5. sourceType != news
   → ValueError

6. Replace TX
   → conn.autocommit = False

7. Replace TX
   → ESG_MATERIALITY_RUN FOR UPDATE

8. Replace TX
   → 기존 활성 News Shadow Row만 soft-delete

9. Replace TX
   → Benchmark Namespace를 soft-delete하지 않음

10. Replace TX
    → Fact Row INSERT

11. Replace TX
    → row_count == len(factRows) 검증

12. Replace TX Count mismatch
    → ROLLBACK
    → COMMIT 미호출

13. runId Row 없음
    → ROLLBACK

14. factPayloads = []
    → 기존 활성 News Shadow Row soft-delete
    → INSERT 없음
    → row_count == 0 검증
    → COMMIT
```

## 11.3 Service 테스트 최소 항목

```text
15. Legacy saveSignals 성공 후
    → News Shadow Replace TX 정확히 1회

16. Shadow Fact Build
    → pipelineResults를 사용
    → scoredSignals 역변환 금지

17. step0BuildFactTrace()
    → sourceChannel == "media_external"

18. Normalize 실패
    → Replace TX 미호출
    → Legacy scoredSignals 반환 유지

19. Replace TX 실패
    → Warning 출력
    → Legacy scoredSignals 반환 유지

20. Legacy saveSignals 실패
    → Replace TX 미호출
    → 기존 실패 유지

21. pipelineResults = []
    → Replace TX factPayloads=[]로 호출
```

## 11.4 Adapter Scalar Normalization 테스트

C2.1-A 보완을 적용하면 아래 테스트도 추가한다.

```text
22. issueSimilarityMatches가 list가 아님
    → []

23. issueId 내부 nested dict
    → None

24. subIssueNameKr 내부 nested list
    → None

25. score 내부 nested dict
    → None

26. 정상 scalar score 문자열
    → float 변환
```

## 11.5 Guard 테스트

```text
27. 신규 Repository 함수 내부에 아래 문자열 없음
    - recalcStage(
    - recalcFinal(
    - updateRanks(
    - ESG_DMA_SCORE_SUMMARY
    - ESG_MATERIALITY_SELECTED_SUB_ISSUE

28. service.py에 namespace literal 없음
    - "media_external_news_v13_shadow"

29. 신규 Production 파일 0개

30. Runtime JSON / SQL / API / frontend Diff 없음
```

---

## 12. 금지 사항

```text
금지:
- ESG_DMA_SCORE_SUMMARY 변경
- final_score 변경
- rank_no 변경
- selected issue 변경
- Top20 Query 변경
- Survey 변경
- G0 변경
- agency Runtime
- regulation Runtime
- KCGS Runtime
- KIS Runtime
- externalMax Runtime Wiring
- Canonical IRO Rule 연결
- Event Dedup 구현
- Runtime JSON 변경
- manifest capability READY 전환
- 신규 Table
- 신규 Column
- 신규 FK
- 신규 Index
- SQL Migration
- API 변경
- frontend 변경
- 실 DB 접근
- Redis / Kafka / Docker 접근
- 외부 API 실호출
- git add
- git commit
- git push
```

---

## 13. 문서

아래 결과 문서를 작성한다.

```text
docs/dma/v1_3_mvp/11_PHASE_C2_1_MEDIA_EXTERNAL_NEWS_SHADOW_REPLACE_ACTIVE_RESULT.md
```

반드시 포함:

```text
1. Baseline branch / HEAD / git status
2. 수정 파일 목록
3. 신규 Production 파일 수
4. 신규 Public Production 함수 수
5. 신규 Private Helper 수
6. Namespace SSOT
7. Service Hook 위치
8. Empty Fact Set 처리
9. Transaction 순서
10. Legacy Failure Isolation
11. Summary / Rank 비침투 확인
12. Adapter Scalar Normalization 적용 여부
13. Tests 결과
14. Guard 검색 결과
15. 미수행 범위
16. 다음 단계 후보
```

다음 단계 후보는 아래로만 기록하고 구현하지 마라.

```text
Phase C2.2
→ media_external.news Event Fact Resolver Rule 연결 검토
→ Canonical IRO / Event Dedup 계약 설계

Phase C3
→ media_external 내부 news / agency / regulation Screening 집계
→ externalMax 내부 Helper 사용
→ Regulation, KCGS, KIS 독립 Stage 승격 금지
```

---

## 14. 검증 명령

현재 위치가 `backend` 폴더라면:

```bash
python -m compileall src -q

python -m pytest \
  tests/test_dma_v1_3_phase_c2_media_external_news_fact_resolver.py \
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
  backend/tests/test_dma_v1_3_phase_c2_media_external_news_fact_resolver.py \
  backend/tests/test_dma_v1_3_phase_c2_1_media_external_news_shadow_replace_active.py \
  -q

python -m pytest backend/tests -q

git diff --check
git status --short
```

예상 전체 회귀 기준:

```text
298 passed
1 skipped
```

신규 테스트 수만큼 passed가 증가하는 것은 정상이다.

---

## 15. 완료 보고 형식

아래 형식으로 보고한다.

```text
Phase C2.1 완료 보고

Baseline
- branch:
- HEAD:
- 기존 전체 테스트:

수정 파일
- 파일:
- 변경 내용:

신규 Production 파일 수:
신규 Public Production 함수 수:
신규 Private Helper 수:

Namespace SSOT
- 상수:
- literal 선언 위치:
- service literal 직접 사용 여부:

Service Wiring
- Legacy 흐름 유지:
- Shadow Hook 위치:
- fact source:
- sourceChannel:
- Empty Fact Set 처리:

Replace Transaction
- Row Lock:
- soft-delete 대상:
- Insert:
- Count 검증:
- COMMIT:
- ROLLBACK:
- close:

Legacy Failure Isolation
- normalize 실패:
- trace build 실패:
- TX 실패:
- legacy saveSignals 실패:

Adapter Scalar Normalization
- 적용 여부:
- 허용 Scalar:
- nested object 처리:

비침투 확인
- ESG_DMA_SCORE_SUMMARY:
- final_score:
- rank_no:
- selected issue:
- agency:
- regulation:
- KCGS:
- KIS:
- externalMax:
- Survey:
- G0:
- Top20:
- API / frontend:
- Runtime JSON:
- SQL / DDL:

테스트 결과
- compileall:
- 지정 suite:
- 전체 backend:
- git diff --check:
- guard 검색:

git add / commit / push:
- 미수행 여부:

다음 단계 후보
- Phase C2.2 media_external.news Event Fact Resolver Rule 연결 검토
```

완료 후 멈춰라.
