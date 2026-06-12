# NEXT CLAUDE CODE PROMPT
# DMA v1.3 Phase C3.1.2 — media_external.regulation Runtime Safety Review
# R1

## 0. 작업 목적

현재 `feature/DAM_score_ljb` 브랜치는 Regulation Shadow Runtime Wiring과 Reader Fail-Closed Micro Patch까지 완료된 상태다.

현재 원격 기준:

```text
branch:
feature/DAM_score_ljb

HEAD:
82dcb9fd0e202e0c71dba4eb17a1fd0ce8480c4d
```

현재 Regulation Runtime 흐름:

```text
ESG_MATERIALITY_RUN
→ findRegulationRunContext()

ESG_DMA_REGULATION__INPUT
→ listApprovedRegulationInputs()

ESG_DMA_REGULATION_SUB_ISSUE_MAP
→ listApprovedActiveRegulationMappings()

Approved Input + Approved Active Mapping
→ step2BuildRegulationScreeningPayloads()

Payloads
→ _buildRegulationShadowRows()

Rows
→ step4ReplaceRegulationShadowTracesTx()

Persist
→ ESG_DMA_SIGNAL_DETAIL
→ source_step = media_external_regulation_v13_shadow
```

현재 Reader Fail-Closed 보정:

```text
_findOneRegulationRowOrRaise()
_findAllRegulationRowsOrRaise()

DB 장애
→ RuntimeError

정상 0건 조회
→ [] 또는 None
```

이번 Phase C3.1.2 목적:

```text
1. Regulation Runtime Safety Review
2. Reader / Serializer / TX / Service Hook 방어 테스트 강화
3. Shadow Read Inventory 고정
4. 정상 Empty Clear와 Reader Failure 분리 재검증
5. Regime ↔ Trace Channel 정합성 검증
6. Snapshot Atomicity 제한 문서화
7. 실제 결함이 확인된 경우 최소 Micro Patch만 허용
```

이번 단계 완료 후 멈춰라.

기한이 촉박하므로 구조 리팩토링이나 공통 DB Layer 전면 개편은 하지 마라.
Blocking 결함만 최소 Patch로 닫고, 나머지는 문서화 후 Phase C3.2 KCGS로 넘긴다.

---

## 1. Mandatory Architecture Invariant

### 1.1 DMA 상위 Stage

상위 DMA Stage는 아래 3개만 유지한다.

```text
benchmark
media_external
survey
```

Regulation은 독립 Stage가 아니다.

```text
media_external
└─ regulation
   ├─ CSRD
   ├─ CBAM
   └─ DPP
```

금지:

```text
regulation_impact_score 신규 Summary 컬럼
regulation_financial_score 신규 Summary 컬럼
ESG_DMA_SCORE_SUMMARY.regulation_*
독립 regulation Stage
```

### 1.2 Shadow-only 유지

이번 단계에서 Regulation은 Shadow Snapshot만 다룬다.

```text
ESG_DMA_SIGNAL_DETAIL
source_step = media_external_regulation_v13_shadow
source_type = regulation
```

금지:

```text
ESG_DMA_SCORE_SUMMARY 반영
recalcStage()
upsertStage()
recalcFinal()
updateRanks()
externalMax
Top20
Survey
KCGS 계산
KIS 계산
API 변경
Frontend 변경
SQL / DDL 변경
```

### 1.3 Existing DB Contract 유지

실제 DB 테이블명:

```text
ESG_DMA_REGULATION__INPUT
                       ^^
이중 언더스코어 유지

ESG_DMA_REGULATION_SUB_ISSUE_MAP
```

실제 DB 컬럼:

```text
ESG_DMA_SIGNAL_DETAIL.source_step
→ VARCHAR(80)
```

DDL을 다시 추가하거나 변경하지 마라.

---

## 2. Preflight

Repo Root에서 실행:

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short

python -m compileall backend/src -q
python -m pytest backend/tests -q
```

Expected:

```text
branch:
feature/DAM_score_ljb

HEAD:
82dcb9fd0e202e0c71dba4eb17a1fd0ce8480c4d
```

전체 테스트 개수는 로컬 환경에 따라 async 관련 무관 이슈가 있을 수 있으므로 숫자를 하드코딩하지 마라.

반드시 기록:

```text
- passed
- skipped
- failed
- async 환경 이슈 여부
```

주의:

```text
- Working Tree가 깨끗하지 않으면 기존 Diff를 먼저 보고하고 멈춘다.
- reset 금지
- checkout 금지
- rebase 금지
- git add / commit / push 금지
- 실제 DB / Redis / Kafka / Docker / 외부 API 접근 금지
```

---

## 3. 반드시 읽을 파일

### 3.1 Regulation Runtime

```text
backend/src/utils/dmarepository.py
backend/src/services/medias/service.py
backend/src/services/materialities/orchestrator.py
backend/src/models/dmaengine.py
backend/src/utils/dmascoring.py
```

### 3.2 Existing Test

```text
backend/tests/test_dma_v1_3_phase_c3_1_regulation_screening_foundation.py
backend/tests/test_dma_v1_3_phase_c3_1_1_regulation_shadow_runtime.py
backend/tests/test_dma_v1_3_phase_c2_4_media_news_canonical_shadow_runtime.py
backend/tests/test_dma_v1_3_phase_c2_4_1_media_news_runtime_safety.py
```

### 3.3 Existing Generic Trace Reader

```text
backend/src/utils/dmarepository.py
```

특히 아래를 읽는다.

```text
step4ReadTrace()
listSignalCounts()
countObservedSubIssues()
```

---

## 4. 이번 Phase의 성격

```text
Phase C3.1.2
= Safety Review
+ Test Hardening
+ Shadow Read Inventory
+ Minimal Blocking Defect Patch Only
```

이번 단계에서 신규 기능을 구현하지 마라.

허용:

```text
- 신규 Test 파일 1개
- 기존 Regulation Runtime Test 보강
- 실제 결함이 확인된 경우 dmarepository.py 최소 수정
- 실제 결함이 확인된 경우 service.py 최소 수정
- 로컬 결과 문서 작성
```

금지:

```text
- 신규 Production 파일
- 공통 db.py 전면 리팩토링
- Repository Package 분할
- API 추가
- Frontend 추가
- DB Table 추가
- DDL
- Summary / Rank
- externalMax
- KCGS / KIS
- Top20 / Survey
```

---

## 5. Shadow Read Inventory

결과 문서에 아래 Inventory를 반드시 고정한다.

| Reader / API | Data Source | Regulation Shadow 직접 Read 여부 | Active Runtime 여부 | 판정 |
|---|---|---:|---:|---|
| `step4ReadTrace()` | `scoring_payload_json` | 가능 | Generic Trace | 허용 |
| `listSignalCounts()` | `ESG_DMA_SIGNAL_DETAIL`, `source_step=?` | 가능 | Audit / Debug | 허용 |
| `countObservedSubIssues()` | `ESG_DMA_SIGNAL_DETAIL`, `source_step=?` | 가능 | Audit / Debug | 허용 |
| `listSignals()` | `ESG_DMA_SIGNAL_DETAIL`, `source_step=?` | Generic 인자상 가능 | Legacy Stage Aggregation | Regulation Namespace 사용 금지 |
| `recalcStage()` | `listSignals()` | 직접 Read 아님 | Legacy Summary 계산 | Regulation Namespace 호출 금지 |
| `listResults()` | `ESG_DMA_SCORE_SUMMARY` | 없음 | Result API | 기존 Summary 유지 |
| `listTopMediaIssues()` | `ESG_DMA_SCORE_SUMMARY` | 없음 | Media API | 기존 Summary 유지 |
| `getMediaCoverage()` | `ESG_DMA_SCORE_SUMMARY` | 없음 | Media API | 기존 Summary 유지 |
| `countMediaSubIssues()` | `ESG_DMA_SCORE_SUMMARY` | 없음 | Media API | 기존 Summary 유지 |

핵심 결론:

```text
Regulation Shadow Active Summary Reader
= 없음

Regulation Shadow Audit Reader
= Generic Trace Helper만 허용

Legacy Stage Aggregation
= Regulation Shadow Namespace 금지
```

신규 Audit Reader는 이번 단계에서 추가하지 마라.

---

## 6. C3.1.2-A — Strict Reader Safety Review

현재 Strict Helper:

```text
_findOneRegulationRowOrRaise()
_findAllRegulationRowsOrRaise()
```

검증 목표:

```text
정상 Empty
→ Empty Clear 허용

DB Failure
→ RuntimeError
→ Writer 미호출
→ 기존 Shadow Set 유지
```

### 6.1 추가 Test

아래 Test를 추가한다.

```text
#61 Run Context Reader getConn() = None → RuntimeError
#62 Run Context Reader execute() 실패 → RuntimeError
#63 Input Reader fetchall() 실패 → RuntimeError
#64 Mapping Reader fetchall() 실패 → RuntimeError
#65 Strict One Reader 성공 시 close() 호출
#66 Strict All Reader 성공 시 close() 호출
#67 Strict One Reader 실패 시 close() 호출
#68 Strict All Reader 실패 시 close() 호출
```

### 6.2 Service-level Fail-Closed Test

```text
#69 Run Context Reader 실패 → Writer 미호출
#70 Input Reader 실패 → Writer 미호출
#71 Mapping Reader 실패 → Writer 미호출
#72 Builder 실패 → Writer 미호출
```

규칙:

```text
Reader 실패를 정상 Empty로 바꾸지 마라.
```

---

## 7. C3.1.2-B — Empty Clear Semantics Review

현재 계약:

```text
Approved Input 0건
또는
Approved Active Mapping 0건

→ payloads = []
→ Replace-Active TX
→ 기존 Regulation Shadow soft-delete
→ 신규 INSERT 없음
→ COMMIT
```

이 계약은 유지한다.

### 7.1 추가 Test

```text
#73 정상 Empty Input → Writer([])
#74 정상 Empty Mapping → Writer([])
#75 Writer([]) → soft-delete 실행
#76 Writer([]) → INSERT 0회
#77 Writer([]) → COUNT(*) == 0
#78 Writer([]) → COMMIT
```

### 7.2 문서화

결과 문서에 아래를 명시한다.

```text
정상 Empty Clear
→ 승인 입력이 실제로 0건이거나
→ 활성 승인 Mapping이 실제로 0건일 때만 허용

Reader 장애
→ Empty Clear 금지
```

---

## 8. C3.1.2-C — Regime ↔ Trace Channel 정합성

현재 Serializer는 아래만 검사한다.

```text
channel.startswith("regulation_")
rawInputs.regime 존재
```

안전성 관점에서 아래 정합성을 검증해야 한다.

```text
channel
= "regulation_" + regime.lower()
```

예:

```text
regime = CSRD
channel = regulation_csrd

regime = CBAM
channel = regulation_cbam

regime = DPP
channel = regulation_dpp
```

### 8.1 신규 Test

```text
#79 CSRD + regulation_csrd → PASS
#80 CBAM + regulation_cbam → PASS
#81 DPP + regulation_dpp → PASS
#82 regime=CBAM + channel=regulation_csrd → ValueError
#83 regime=CSRD + channel=regulation_unknown → ValueError
```

### 8.2 테스트 실패 시 최소 Patch

수정 허용:

```text
backend/src/utils/dmarepository.py
```

`_buildRegulationShadowRows()` 안에 아래 검증만 추가한다.

```python
expectedChannel = f"regulation_{str(regime).lower()}"
if channel != expectedChannel:
    raise ValueError(
        f"Regulation Shadow channel/regime mismatch: "
        f"expected={expectedChannel!r}, got={channel!r}"
    )
```

과도한 Helper 추가 금지.

---

## 9. C3.1.2-D — Serializer Boundary 보강

추가 Test:

```text
#84 rawInputs.sourceStep != media_external → ValueError
#85 rawInputs.sourceType != regulation → ValueError
#86 companyId bool → ValueError
#87 reportingYear bool → ValueError
#88 regime 누락 → ValueError
#89 applicability 누락 → ValueError
#90 screeningTrace[0] non-dict → ValueError
```

Production Patch는 테스트가 실제 결함을 증명한 경우에만 허용한다.

---

## 10. C3.1.2-E — Replace-Active TX 보강

추가 Test:

```text
#91 executemany() 실패 → rollback + close
#92 COUNT(*) query 실패 → rollback + close
#93 COUNT mismatch → rollback + close
#94 run row 없음 → rollback + close
#95 soft-delete SQL은 Regulation Namespace만 대상
#96 COUNT(DISTINCT sub_issue_code) 사용 금지
#97 동일 subIssueCode가 CSRD + CBAM 두 regime에 매핑 → Row 2건 보존
#98 동일 subIssueCode 2 regime → COUNT(*) 2건으로 검증
#99 Serializer 실패 → getConn() 미호출
#100 Happy Path → commit + close
```

중요:

```text
Regulation Shadow는 Regime Trace 보존이 목적이다.

동일 Sub-Issue:
CSRD + CBAM
→ 2 rows 허용

COUNT(DISTINCT sub_issue_code)
→ 금지
```

---

## 11. C3.1.2-F — Service Hook 독립성

추가 Test:

```text
#101 News Crawl SUCCESS + Regulation Refresh 성공 → 1회 호출
#102 News Crawl FAILED + Regulation Refresh 성공 → 1회 호출
#103 News 정상 Empty + Regulation Refresh 성공 → 1회 호출
#104 Regulation Refresh 실패 → 기존 Media 응답 유지
#105 Regulation Refresh 실패 → Warning 출력
#106 runMediaAnalysis() 내부에서는 Regulation Refresh 미호출
#107 runMediaCrawlAndAnalyze() 응답 조립 이전에 Regulation Refresh 위치 유지
```

금지:

```text
runMediaAnalysis()
→ refreshRegulationShadowForRun()

중복 호출
→ 금지
```

---

## 12. C3.1.2-G — Snapshot Atomicity 제한 문서화

현재 Runtime은 Reader를 순차 호출한다.

```text
1. findRegulationRunContext()
2. listApprovedRegulationInputs()
3. listApprovedActiveRegulationMappings()
4. Builder
5. Replace TX
```

각 Reader는 별도 Connection을 사용한다.

따라서 아래 제한이 있다.

```text
Input 조회 직후
+
Mapping 조회 직전

관리자가 승인 상태를 바꾸면
→ 서로 다른 시점의 Snapshot 조합 가능
```

이번 MVP에서는 이 제한을 코드로 해결하지 마라.

결과 문서에 아래를 명시한다.

```text
Current Limitation:
Reader Snapshot Atomicity 없음

MVP Operational Guard:
Regulation 승인 변경과 DMA 재분석 동시 실행을 운영상 제한

Post-MVP Candidate:
- Read Snapshot Transaction
또는
- sourceUpdatedAt / configHash 검증
또는
- Regulation Snapshot UID
```

이 제한은 C3.2 진입 Blocker가 아니다.

---

## 13. C3.1.2-H — Summary / Rank / externalMax 비침투

Static Guard:

```text
#108 Regulation 경로에 recalcStage() 호출 없음
#109 Regulation 경로에 upsertStage() 호출 없음
#110 Regulation 경로에 recalcFinal() 호출 없음
#111 Regulation 경로에 updateRanks() 호출 없음
#112 Regulation 경로에 externalMax 호출 없음
#113 ESG_DMA_SCORE_SUMMARY 신규 Regulation 컬럼 없음
```

---

## 14. 수정 허용 범위

### 14.1 신규 Test 파일

권장:

```text
backend/tests/test_dma_v1_3_phase_c3_1_2_regulation_runtime_safety.py
```

기존 C3.1.1 Test 파일에 최소 보강해도 되지만, Phase 분리를 위해 신규 파일을 권장한다.

### 14.2 Production 최소 Patch 허용

테스트 실패가 실제 결함을 증명한 경우에만 허용:

```text
backend/src/utils/dmarepository.py
backend/src/services/medias/service.py
```

예상 가능한 최소 Patch:

```text
_buildRegulationShadowRows()
→ channel / regime exact match 검증
```

### 14.3 로컬 결과 문서

```text
docs/dma/v1_3_mvp/22_PHASE_C3_1_2_REGULATION_RUNTIME_SAFETY_REVIEW_RESULT.md
```

로컬 Ignore 정책에 따라 Git Status에 나타나지 않아도 된다.

### 14.4 수정 금지

```text
backend/src/utils/db.py
backend/src/models/dmaengine.py
backend/src/services/materialities/orchestrator.py
backend/src/utils/dmascoring.py
backend/src/utils/dmaaggregator.py
backend/src/resources/dma/v1_3_mvp/*.json
backend/src/apis/**
frontend/**
*.sql
```

---

## 15. 최소 Test 수

신규 Safety Review Test:

```text
최소 35개
```

기존 C3.1.1 Test 60개는 삭제하지 마라.

권장 Test 번호:

```text
#61 ~ #113
```

번호는 기존 파일 연속 번호를 사용해도 되고,
신규 파일에서는 별도 Section 번호를 사용해도 된다.

핵심은 Test Coverage다.

---

## 16. 정적 검증

Repo Root에서 실행:

```bash
python -m compileall backend/src -q

python -m pytest \
  backend/tests/test_dma_v1_3_phase_c3_1_regulation_screening_foundation.py \
  backend/tests/test_dma_v1_3_phase_c3_1_1_regulation_shadow_runtime.py \
  backend/tests/test_dma_v1_3_phase_c3_1_2_regulation_runtime_safety.py \
  backend/tests/test_dma_v1_3_phase_c2_4_media_news_canonical_shadow_runtime.py \
  backend/tests/test_dma_v1_3_phase_c2_4_1_media_news_runtime_safety.py \
  -q

python -m pytest backend/tests -q

git diff --check
git diff --stat
git diff --name-only
git status --short
```

### 16.1 Namespace SSOT

```bash
rg -n "media_external_regulation_v13_shadow" backend/src
```

Expected:

```text
backend/src/utils/dmarepository.py
→ 상수 선언 1곳만
```

### 16.2 Double Underscore Table Name

```bash
rg -n "ESG_DMA_REGULATION__INPUT|ESG_DMA_REGULATION_INPUT" backend/src
```

Expected:

```text
ESG_DMA_REGULATION__INPUT
→ dmarepository.py Reader SQL

ESG_DMA_REGULATION_INPUT
→ 0건
```

### 16.3 Summary / Rank / externalMax 비침투

```bash
rg -n "recalcStage\(|upsertStage\(|recalcFinal\(|updateRanks\(|externalMax" \
  backend/src/services/medias/service.py \
  backend/src/utils/dmarepository.py
```

Expected:

```text
신규 Regulation 경로
→ 0건
```

기존 Legacy 함수 정의는 존재할 수 있다.
Diff 기준으로 신규 호출이 없는지 확인한다.

### 16.4 API / Frontend / SQL 비침투

```bash
git diff --name-only -- \
  backend/src/apis \
  frontend \
  "*.sql"
```

Expected:

```text
출력 없음
```

### 16.5 eval / exec

```bash
rg -n "eval\\(|exec\\(" backend/src
```

Expected:

```text
0건
```

---

## 17. 결과 문서

작성:

```text
docs/dma/v1_3_mvp/22_PHASE_C3_1_2_REGULATION_RUNTIME_SAFETY_REVIEW_RESULT.md
```

필수 내용:

```text
1. Branch
2. Baseline HEAD
3. 작업 전 git status
4. Baseline Test
5. 수정 파일 목록
6. 신규 Production 파일 수
7. 신규 Test 파일
8. Strict Reader Safety
9. 정상 Empty Clear
10. Reader Failure Clear 차단
11. channel / regime exact match
12. Serializer Boundary
13. TX Rollback
14. Same Sub-Issue Multi-Regime Row 보존
15. COUNT(*) 사용
16. COUNT(DISTINCT) 미사용
17. Service Hook 정확히 1회
18. News Crawl 독립성
19. Legacy Media 응답 보호
20. Shadow Read Inventory
21. Regulation Shadow Active Summary Reader 없음
22. Snapshot Atomicity 제한
23. MVP Operational Guard
24. Post-MVP Candidate
25. Summary / Rank 비침투
26. externalMax 미구현
27. KCGS / KIS 미접촉
28. API / Frontend 미수정
29. SQL / DDL 미수정
30. compileall
31. 지정 테스트
32. 전체 Backend 테스트
33. git diff --check
34. eval / exec
35. 실제 DB / Redis / Kafka / Docker / 외부 API 미접근
36. git add / commit / push 미수행
37. 다음 단계
```

---

## 18. 완료 보고 형식

```text
Phase C3.1.2 완료 보고

Baseline
- branch:
- HEAD:
- 기존 전체 테스트:

Diff
- 수정 파일:
- 신규 Production 파일:
- 신규 Test 파일:
- 최소 Micro Patch:

Strict Reader
- normal empty:
- getConn None:
- execute failure:
- fetch failure:
- close on success:
- close on failure:

Empty Clear
- empty input:
- empty mapping:
- insert count:
- commit:

Serializer
- channel / regime exact match:
- sourceStep:
- sourceType:
- companyId bool:
- reportingYear bool:
- missing regime:
- missing applicability:

Transaction
- pre-DB serialization:
- row lock:
- namespace soft-delete:
- multi-regime same sub-issue:
- COUNT(*):
- COUNT(DISTINCT):
- rollback:
- happy commit:

Service Hook
- exact once:
- news success:
- news failed:
- news empty:
- regulation failure isolation:
- runMediaAnalysis direct refresh:

Shadow Read Inventory
- active summary reader:
- generic audit reader:
- listSignals regulation use:

Snapshot Atomicity
- current limitation:
- MVP operational guard:
- post-MVP candidate:

Guard
- Summary / Rank:
- externalMax:
- KCGS / KIS:
- API / Frontend:
- SQL / DDL:
- eval / exec:

Tests
- compileall:
- C3.1.2 신규:
- 지정 Suite:
- 전체 Backend:
- git diff --check:

Git
- status:
- add / commit / push:

다음 단계
- Phase C3.2 KCGS
```

완료 후 멈춰라.

---

## 19. PASS 기준

아래를 모두 충족해야 PASS다.

```text
- Branch = feature/DAM_score_ljb
- Baseline HEAD = 82dcb9fd0e202e0c71dba4eb17a1fd0ce8480c4d
- 신규 Production 파일 0
- Strict Reader 정상 Empty / Failure 구분
- Reader Failure 시 Writer 미호출
- Empty Clear 정상
- channel = regulation_{regime.lower()} exact match
- Serializer Boundary PASS
- Pre-DB Serialization
- Row Lock
- Regulation Namespace만 soft-delete
- Same Sub-Issue Multi-Regime Trace 2 rows 보존
- COUNT(*) 검증
- COUNT(DISTINCT) 미사용
- Rollback + close
- Service Hook 정확히 1회
- News Crawl SUCCESS / FAILED / EMPTY와 Regulation Refresh 독립
- Regulation Refresh 실패 시 기존 Media 응답 유지
- Regulation Shadow Active Summary Reader 없음
- Snapshot Atomicity 제한 문서화
- Summary / Rank 미침투
- externalMax 미구현
- KCGS / KIS 미접촉
- API / Frontend 미수정
- SQL / DDL 미수정
- eval / exec 0건
- compileall PASS
- 전체 Backend Regression 0
- 실제 DB / Redis / Kafka / Docker / 외부 API 미접근
- git add / commit / push 미수행
```

---

## 20. 다음 단계

C3.1.2 PASS 후:

```text
Phase C3.2
→ KCGS 3개년 등급 입력 Reader
→ KCGS Pillar Signal
→ bounded boost-only Shadow
→ Summary / Rank 비침투 유지
```

기한이 촉박하므로 C3.1.2에서 Blocking 결함이 없으면 추가 Regulation Phase를 만들지 마라.
결과 문서에 비차단 제한사항을 기록하고 바로 C3.2로 넘어간다.
