# ESG 플랫폼 Frontend G0 / Rollup 복구 작업지시서 v1

## 0. 작업 목적

현재 `total/dev_skm-feature-onboarding_final` 기준으로 백엔드 Step A, B, B.5는 남아 있으나, 프론트 리뉴얼 결과가 대부분 롤백된 상태다.

이번 작업은 **기존 브랜치에서 그대로 진행**한다.  
새 브랜치를 만들지 않는다.

핵심 목적은 다음 두 화면 흐름을 다시 복구하는 것이다.

1. 지속가능경영보고서 진입 시 보고서 발행 기준 선택
2. DMA 전 G0-only 온보딩 화면과 연결기준 롤업 흐름

첨부한 사용자 제공 온보딩 참고 이미지의 레이아웃을 기본 UI 기준으로 사용한다.

---

# 1. 현재 기준선

## 1.1 남아 있는 백엔드

다음 API는 현재 코드에 존재한다.

### Report Workflow

```text
GET  /api/v1/report-workflow/current
POST /api/v1/report-workflow/start
GET  /api/v1/report-workflow/{runId}/g0-status
```

### Rollup

```text
GET  /api/v1/rollups/subsidiaries
POST /api/v1/rollups/batches
POST /api/v1/rollups/batches/{batchId}/calculate

GET  /api/v1/rollups/requests
POST /api/v1/rollups/batches/{batchId}/sources/send
GET  /api/v1/rollups/batches/{batchId}/status
```

### 유지된 핵심 로직

```text
자회사 전송 전 롤업 계산 차단
ROLLUP_SOURCE_NOT_SENT

자회사 승인 데이터 부족 시 전송 차단
SOURCE_G0_02_NOT_READY

company scope guard
Redis cache miss 방어
```

기존 백엔드 Step A/B/B.5는 재작성하지 않는다.

---

## 1.2 현재 유실된 프론트

다음 항목은 현재 코드에서 복구가 필요하다.

```text
보고서 발행 기준 선택 modal
지속가능경영보고서 nav 진입 gate
ENTITY / CONSOLIDATED 분기
이미지 기반 OnBoard1 shell
PRE_DMA_G0 mode
지주사 자회사 요청 modal
자회사 지주사 전송 modal
지주사 롤업 요약
롤업 실행 CTA
DMA 진행 CTA
reload 복구
프론트 API client
reportbasis asset 적용
```

---

# 2. 공통 작업 원칙

## 2.1 기존 브랜치 사용

현재 작업 중인 기존 브랜치에서 그대로 진행한다.

```text
새 branch 생성 금지
강제 reset 금지
다른 branch checkout 금지
```

작업 전 반드시:

```bash
git status --short
git branch --show-current
git log --oneline -5
```

출력 결과를 보고한다.

---

## 2.2 단계별 커밋

한 번에 전체 UI를 만들지 않는다.

각 단계 종료 시 반드시 커밋한다.

```text
Phase 0: audit only
Phase 1: frontend API client
Phase 2: report entry gate + modal
Phase 3: PRE_DMA_G0 OnBoard1 shell
Phase 4: parent rollup UI
Phase 5: subsidiary transfer UI
Phase 6: reload recovery
Phase 7: final verification
```

각 단계에서:

```text
점검
→ 작업
→ 확인
→ commit
```

순서로 진행한다.

---

## 2.3 보호영역

절대 수정하지 않는다.

```text
backend/src/utils/auth.py
backend/src/utils/tokenset.py
backend/src/utils/fastset.py
backend/src/models/auth.py
로그인 / 로그아웃 / JWT / token validation 흐름
```

기능 목적 없이 수정하지 않는다.

```text
backend/src/utils/dmascoring.py
backend/src/utils/dmaaggregator.py
backend/src/services/benchmarks/service.py
backend/src/services/medias/service.py
backend/src/services/materialities/financialexposure.py
DB schema
SQL migration
```

---

# 3. Phase 0 — 현황 점검

## 3.1 목적

수정 전에 현재 프론트와 백엔드 상태를 정확히 고정한다.

## 3.2 점검 대상

### Backend API 존재 여부

```text
backend/src/apis/reportworkflow.py
backend/src/apis/rollup.py
backend/src/apis/api.py
backend/src/services/reportworkflows/service.py
backend/src/services/rollups/service.py
backend/src/utils/companyscope.py
```

### Frontend 현재 상태

```text
frontend/src/components/Layout/SidebarNav.jsx
frontend/src/components/UI/ServiceAlert.jsx
frontend/src/homes/onboards/OnBoard1.jsx
frontend/src/styles/onboarding1.css
frontend/src/apis/
frontend/src/components/reports/
frontend/src/styles/
frontend/src/assets/reportbasis/
```

## 3.3 확인 항목

아래 표 형태로 보고한다.

```text
항목 | 현재 존재 여부 | 파일 | 상태 | 다음 작업 필요 여부
```

반드시 확인:

```text
ReportBasisSelectModal.jsx 존재 여부
reportBasisSelectModal.css 존재 여부
frontend/src/apis/reportworkflow.js 존재 여부
frontend/src/apis/rollup.js 존재 여부
assets/reportbasis 존재 여부
SidebarNav 지속가능경영보고서 클릭 동작
OnBoard1이 기존 대시보드형인지 이미지 기반 shell인지
ServiceAlert에 기준 선택 modal 코드가 있는지
```

## 3.4 금지

Phase 0에서는 코드 수정 금지.

## 3.5 완료 보고

```text
Phase 0 audit 완료.

현재 branch:
git status:
최근 commit:

Backend Step A:
Backend Step B:
Backend Step B.5:

Frontend 유실 항목:
Frontend 남아 있는 항목:

수정 시작 가능 여부:
```

---

# 4. Phase 1 — Front API client 복구

## 4.1 목적

UI보다 먼저 API client를 추가한다.

## 4.2 신규 파일

프로젝트의 기존 axios helper 규칙을 우선 확인한다.

권장 파일:

```text
frontend/src/apis/reportworkflow.js
frontend/src/apis/rollup.js
```

## 4.3 reportworkflow.js

compact function 이름 사용:

```text
getCurrent
startWorkflow
getG0Status
```

연결 API:

```text
GET  /api/v1/report-workflow/current
POST /api/v1/report-workflow/start
GET  /api/v1/report-workflow/{runId}/g0-status
```

## 4.4 rollup.js

compact function 이름 사용:

```text
listSubsidiaries
saveBatch
listRequests
sendSource
getStatus
calcBatch
```

연결 API:

```text
GET  /api/v1/rollups/subsidiaries
POST /api/v1/rollups/batches
GET  /api/v1/rollups/requests
POST /api/v1/rollups/batches/{batchId}/sources/send
GET  /api/v1/rollups/batches/{batchId}/status
POST /api/v1/rollups/batches/{batchId}/calculate
```

## 4.5 구현 원칙

```text
UI 수정 금지
dummy state 수정 금지
localStorage 수정 금지
backend 수정 금지
```

## 4.6 확인

```text
frontend build 또는 npm run build
API client import smoke
eslint 가능하면 실행
```

## 4.7 commit

```text
feat: add report workflow and rollup api clients
```

---

# 5. Phase 2 — 지속가능경영보고서 nav gate + 발행 기준 선택 modal

## 5.1 목적

지속가능경영보고서 nav 클릭 시 바로 `/benchmk`로 이동하는 기존 흐름을 제거한다.

## 5.2 수정 대상

```text
frontend/src/components/Layout/SidebarNav.jsx
frontend/src/components/reports/ReportBasisSelectModal.jsx
frontend/src/styles/reportBasisSelectModal.css
```

필요 시:

```text
frontend/src/homes/App.jsx
```

## 5.3 nav 동작

```text
지속가능경영보고서 nav 클릭
→ GET /api/v1/report-workflow/current
```

분기:

```text
workflowStep = NO_RUN
→ 기준 선택 modal open

기존 run 존재
→ nextAction 기준으로 OnBoard1 또는 후속 화면 이동
```

## 5.4 modal 기능

modal은 `ServiceAlert.jsx` 내부 HTML 문자열로 만들지 않는다.

전용 React 컴포넌트로 구현한다.

```text
ReportBasisSelectModal.jsx
reportBasisSelectModal.css
```

### 선택 옵션

```text
독립기준 ENTITY
연결기준 CONSOLIDATED
```

### 선택 완료

```text
POST /api/v1/report-workflow/start
```

성공 후:

```text
/onb 이동
```

## 5.5 디자인

처음에는 기능을 우선 구현한다.

asset 없이도 되는 최소 UI:

```text
제목
설명
ENTITY 카드
CONSOLIDATED 카드
취소
선택 완료
```

일러스트와 아이콘은 기능 검증 후 별도 단계로 적용한다.

## 5.6 확인

```text
NO_RUN 시 modal open
ENTITY 선택 후 start 호출
CONSOLIDATED 선택 후 start 호출
API 성공 후 /onb 이동
API 실패 시 modal 유지
```

## 5.7 commit

```text
feat: add report basis selection gate
```

---

# 6. Phase 3 — PRE_DMA_G0 OnBoard1 shell 복구

## 6.1 목적

사용자가 제공한 참고 이미지 레이아웃을 기준으로 OnBoard1을 다시 만든다.

중요:

```text
첨부 이미지의 UI 구조를 기준으로 한다.
이미지의 ENV-01 예시 ID는 사용하지 않는다.
실제 master/API의 metric_id, atomic_metric_id를 사용한다.
```

## 6.2 수정 대상

```text
frontend/src/homes/onboards/OnBoard1.jsx
frontend/src/styles/onboarding1.css
```

## 6.3 화면 구조

### Header

```text
온보딩 [독립기준]
또는
온보딩 [연결기준]
```

설명:

```text
보고서 발행 및 이중중대성평가 진행을 위해 경영일반 G0 지표를 입력하고 승인 상태를 확인합니다.
```

### 상단 카드

```text
필수 G0 지표
입력 완료
승인 완료
미승인
```

### 왼쪽 패널

DMA 전:

```text
할당 항목

1. 경영일반 - G0
```

검색창은 숨긴다.

DMA 후 확장 대비:

```text
POST_DMA_SELECTED_SUBISSUE
→ 선정 이슈 목록
```

하지만 이번 Phase에서는 실제 구현하지 않는다.

### 오른쪽 테이블

```text
metric_id
atomic_metric_id
지표명
입력 유형
담당자
입력 기한
상태
데이터 입력
```

실제 데이터에 없는 필드는 임의 생성하지 않는다.

```text
atomic_metric_id 없음 → "-"
입력 유형 없음 → "-"
담당자 없음 → "-"
```

### 상태

DMA 전에는 기존 입력·승인 상태를 사용한다.

```text
NOT_STARTED → 미입력
DRAFT       → 입력중
SUBMITTED   → 제출완료
APPROVED    → 승인완료
```

아래 상태는 DMA 후에만 사용한다.

```text
연결 완료
미연결
```

## 6.4 CTA

### ENTITY

```text
본인 G0 승인 완료
→ [이중중대성평가 진행하기] 활성화
```

### CONSOLIDATED / PARENT

```text
본사 G0 승인 완료
→ [자회사 데이터 요청하기] 활성화
```

### CONSOLIDATED / SUBSIDIARY

```text
본인 G0 승인 완료
+ 요청 존재
→ [지주사에 데이터 전송하기] 활성화
```

## 6.5 입력 modal grouping

기존 `issueGroup` 기준으로 G0 전체가 한 번에 열리는 구조를 피한다.

```text
row 클릭
→ 해당 metric 또는 해당 metric의 atomic 목록만 open
```

## 6.6 확인

```text
참고 이미지와 동일한 shell 구조
왼쪽 경영일반 - G0 하나
상단 4개 카드
오른쪽 테이블
ENTITY / CONSOLIDATED badge
CTA 분기
row 단위 modal open
```

## 6.7 commit

```text
feat: restore pre DMA G0 onboarding shell
```

---

# 7. Phase 4 — 지주사 롤업 UI

## 7.1 목적

연결기준 지주사 흐름을 구현한다.

## 7.2 자회사 요청 modal

CTA:

```text
[자회사 데이터 요청하기]
```

호출:

```text
GET /api/v1/rollups/subsidiaries?runId={runId}
```

modal:

```text
checkbox
회사명
회사코드
```

상태, 최근 업데이트는 이번 MVP에서 넣지 않는다.

요청 전송:

```text
POST /api/v1/rollups/batches
{
  "runId": runId,
  "sourceCompanyIds": [...]
}
```

성공 후:

```text
batchId 저장
modal close
toast
rollup summary 노출
```

## 7.3 지주사 롤업 summary

호출:

```text
GET /api/v1/rollups/batches/{batchId}/status
```

화면:

```text
요청 대상 {requestedCount}개
수신 완료 {sentCount}개
대기 {pendingCount}개
```

CTA:

```text
calculateReadyYn=true
→ [롤업 실행하기] 활성화
```

실행:

```text
POST /api/v1/rollups/batches/{batchId}/calculate
```

성공 후:

```text
GET /api/v1/report-workflow/{runId}/g0-status 재호출
CONSOLIDATED_READY 확인
[이중중대성평가 진행하기] 활성화
```

## 7.4 확인

```text
자회사 목록 조회
checkbox 선택
batch 생성
batchId 저장
summary 표시
미전송 시 calculate disabled
모두 전송 시 calculate enabled
calculate 성공 후 DMA CTA enabled
```

## 7.5 commit

```text
feat: add parent G0 rollup workflow ui
```

---

# 8. Phase 5 — 자회사 전송 UI

## 8.1 목적

자회사 계정이 지주사 요청을 확인하고 데이터를 전송한다.

## 8.2 CTA

```text
[지주사에 데이터 전송하기]
```

## 8.3 요청 modal

호출:

```text
GET /api/v1/rollups/requests
```

표시:

```text
checkbox
지주사명
보고연도
전송 가능 여부
```

규칙:

```text
sendReadyYn=false
→ disabled
→ G0 입력 및 승인 완료 후 전송할 수 있습니다.
```

전송:

```text
POST /api/v1/rollups/batches/{batchId}/sources/send
```

성공 후:

```text
전송 완료 toast
버튼 상태 갱신
```

## 8.4 확인

```text
요청 없음
승인 전 disabled
승인 후 enabled
전송 성공
중복 전송 idempotent
```

## 8.5 commit

```text
feat: add subsidiary G0 transfer workflow ui
```

---

# 9. Phase 6 — reload 복구

## 9.1 목적

새로고침 또는 재접속 시 workflow 상태를 복구한다.

## 9.2 mount 시 호출

```text
GET /api/v1/report-workflow/current
GET /api/v1/report-workflow/{runId}/g0-status
```

`requiredRollupBatchId`가 존재하면:

```text
GET /api/v1/rollups/batches/{batchId}/status
```

## 9.3 원칙

```text
localStorage는 source of truth로 사용 금지
API 응답이 source of truth
localStorage는 demo fallback 또는 cache만 허용
```

## 9.4 Backend 응답 부족 시

프론트에서 임의 추론하지 말고 보고한다.

확인할 필드:

```text
requiredRollupBatchId
companyRole
g0InputReadyYn
financialBasisReadyYn
rollupReadyYn
dmaReadyYn
```

필드가 없다면:

```text
backend 최소 보완 필요 목록
```

으로 분리 보고한다.

## 9.5 commit

```text
feat: restore report workflow state on reload
```

---

# 10. Phase 7 — 최종 확인

## 10.1 build

```bash
cd frontend
npm run build
```

가능하면:

```bash
npm run lint
```

## 10.2 금지 diff 확인

```bash
git diff -- backend/src/utils/auth.py
git diff -- backend/src/utils/tokenset.py
git diff -- backend/src/utils/fastset.py
git diff -- backend/src/models/auth.py
git diff -- backend/src/utils/dmascoring.py
git diff -- backend/src/utils/dmaaggregator.py
git diff -- backend/src/services/benchmarks/service.py
git diff -- backend/src/services/medias/service.py
```

기대:

```text
diff 없음
```

## 10.3 시나리오

### ENTITY

```text
지속가능경영보고서 nav 클릭
→ 기준 선택 modal
→ ENTITY
→ G0-only 화면
→ 본인 G0 승인 완료
→ DMA CTA 활성화
```

### CONSOLIDATED / PARENT

```text
지속가능경영보고서 nav 클릭
→ CONSOLIDATED
→ G0-only 화면
→ 본사 G0 승인 완료
→ 자회사 요청
→ summary
→ 전체 전송 전 calculate disabled
→ 전체 전송 후 calculate enabled
→ calculate 성공
→ DMA CTA 활성화
```

### CONSOLIDATED / SUBSIDIARY

```text
자회사 계정 로그인
→ G0-only 화면
→ 지주사 요청 modal
→ 승인 전 disabled
→ 승인 후 전송 성공
```

## 10.4 완료 보고

```text
Frontend G0 / Rollup 복구 완료.

현재 branch:
최종 commit 목록:

Phase 0 audit:
Phase 1 API client:
Phase 2 nav gate + modal:
Phase 3 PRE_DMA_G0 shell:
Phase 4 parent rollup:
Phase 5 subsidiary transfer:
Phase 6 reload recovery:
Phase 7 final verification:

수정 파일:
신규 파일:
삭제 파일:

build:
lint:
protected diff:

backend 응답 누락 필드:
남은 후속 작업:
```

---

# 11. 이번 작업에서 구현하지 않는 범위

```text
Backend Step C
DMA start gate
benchmark/media applyRunExposure 연결
DMA 결과 화면
POST_DMA_SELECTED_SUBISSUE 실제 데이터 연결
metrics_id 담당자 지정
2차 selected disclosure 롤업
보고서 생성
```

---

# 12. 디자인 asset 적용 시점

보고서 발행 기준 선택 modal의 일러스트와 아이콘은 Phase 2 기능 검증 후 별도 commit으로 적용한다.

```text
기능 정상 확인
→ asset 적용
→ screenshot 확인
→ commit
```

asset 적용 commit:

```text
style: apply report basis modal assets
```

이번에는 UI 기능과 asset 적용을 한 커밋에 섞지 않는다.
