# NEXT CLAUDE CODE PROMPT
# DMA Benchmark F1-A — Front API Wiring
# Branch: feature/dma_bench_api_ljb
# R1

## 0. 목적

벤치마킹 화면의 Dummy 실행을 실제 Backend API에 연결한다.

이번 단계는 **API 연결만** 수행한다.

```text
POST /benchmk
→ PDF 업로드

PUT /benchmk
→ 업로드된 PDF 분석 실행

GET /materiality/benchmark/{runId}
→ 벤치마킹 결과 조회
```

Progress Polling은 다음 단계 F1-B에서 구현한다.

이번 단계에서는 Media, Survey, Workflow Polling, SQL, DDL을 수정하지 않는다.

---

## 1. Preflight

현재 작업 브랜치는 사용자가 새로 생성한 로컬 브랜치다.

```text
feature/dma_bench_api_ljb
```

작업 시작 전에 반드시 실행한다.

```bash
git branch --show-current
git rev-parse HEAD
git status --short
```

PASS 기준:

```text
branch
→ feature/dma_bench_api_ljb

status
→ clean
```

주의:

```text
git reset 금지
git restore 금지
git stash 금지
git checkout 금지
git add / commit / push 금지
```

현재 HEAD는 결과 문서에 Baseline으로 기록한다.
기존 지시문의 고정 SHA를 재사용하지 않는다.

---

## 2. 현재 계약

### 2.1 Backend API

기존 API는 이미 있다.

```text
POST /benchmk
PUT  /benchmk
GET  /materiality/benchmark/{runId}
```

Auto Router Loader 기준 파일명 `benchmk.py`가 URL Prefix `/benchmk`가 된다.

금지:

```text
/api/v1/benchmark/analyze
POST("skm", ...)
```

### 2.2 Frontend 현재 문제

수정 대상:

```text
frontend/src/homes/reports/BenchMarking.jsx
```

현재 문제:

```text
USE_DUMMY = true
Fake Timer 기반 Progress
POST("skm", "/api/v1/benchmark/analyze", payload)
Network.js wrapper 인자 계약 불일치
File 객체를 Analyze API에 직접 전달
```

이번 단계에서는 API 연결 후 Fake Timer를 완전히 제거하지 않아도 된다.
단, Polling 구현 전 임시로 아래 최소 상태만 사용한다.

```text
업로드 시작
→ 5

업로드 완료
→ 15

분석 실행 중
→ 50

결과 조회 완료
→ 100
```

Interval 기반 가짜 증가는 금지한다.

---

## 3. Frontend Network Helper

수정:

```text
frontend/src/utils/Network.js
```

추가:

```javascript
export const POST_FORM = (url, formData) => {
  const config = initConfig();
  const headers = { ...(config.headers || {}) };
  delete headers["Content-Type"];

  return request({
    ...config,
    headers,
    method: "POST",
    url,
    data: formData,
  });
};
```

이유:

```text
multipart/form-data boundary
→ Axios / Browser 자동 생성

application/json 강제
→ 금지
```

기존 `GET`, `POST`, `PUT` 동작은 수정하지 않는다.

---

## 4. BenchMarking.jsx 실제 API 연결

수정:

```text
frontend/src/homes/reports/BenchMarking.jsx
```

### 4.1 Import

```javascript
import { GET, POST_FORM, PUT } from "@utils/Network";
import { useSelector } from "react-redux";
```

### 4.2 Run Context

Redux:

```javascript
const currentRunId = useSelector((state) => state.report.currentRunId);
```

실행 직전:

```javascript
const runId = Number(currentRunId);

if (!Number.isInteger(runId) || runId <= 0) {
  showDefaultAlert(
    "프로젝트 선택 필요",
    "현재 보고서 프로젝트를 먼저 선택해주세요.",
    "warning"
  );
  return;
}
```

Hardcode 금지:

```text
runId = 1
runId = 39
runId = 48
```

### 4.3 Dummy Mode

기존:

```javascript
const USE_DUMMY = true;
```

폐기.

개발용 명시적 환경 변수만 허용:

```javascript
const USE_DUMMY =
  import.meta.env.DEV &&
  import.meta.env.VITE_BENCHMARK_DUMMY === "true";
```

기본 동작:

```text
실제 API
```

실제 API 실패 시 Dummy 결과로 자동 전환 금지.

### 4.4 그룹 의미 정합성

Frontend 내부 key는 최소 수정으로 유지 가능:

```text
leader
peer
sub
```

하지만 Backend 계약은 아래다.

```text
leader_sr
peer_sr
own_sr
```

Mapping:

```javascript
const BENCHMARK_GROUP_CONFIG = {
  leader: { fileType: "Leader", label: "리더" },
  peer:   { fileType: "Peer",   label: "피어" },
  sub:    { fileType: "Own",    label: "자사" },
};
```

화면 문구:

```text
자회사
→ 자사
```

금지:

```text
Subsidiary 신규 source type
sub_sr 신규 source type
Backend normalizeSourceType 변경
```

### 4.5 업로드

각 그룹마다 1회 호출한다.

```javascript
const uploadBenchmarkGroup = async (groupKey) => {
  const group = BENCHMARK_GROUP_CONFIG[groupKey];
  const files = fileStorage[groupKey] || [];

  if (files.length !== 3) {
    throw new Error(`${group.label} 보고서 PDF 3개를 등록해주세요.`);
  }

  const companyName = String(companyNames[groupKey] || "").trim();

  if (!companyName) {
    throw new Error(`${group.label} 기업명을 입력해주세요.`);
  }

  const formData = new FormData();

  files.forEach((file) => {
    formData.append("file", file);
  });

  formData.append("fileType", group.fileType);
  formData.append("companyName", companyName);
  formData.append("page", "SR");

  const response = await POST_FORM("/benchmk", formData);

  if (!response || response.status === false) {
    throw new Error(response?.message || `${group.label} 업로드에 실패했습니다.`);
  }

  const storedFiles = response.data?.files || [];

  if (storedFiles.length !== files.length) {
    throw new Error(`${group.label} 업로드 파일 수가 일치하지 않습니다.`);
  }

  return storedFiles.map((item) => item.fileName);
};
```

실행 순서:

```javascript
const uploadedFileNames = [];

for (const groupKey of ["leader", "peer", "sub"]) {
  const storedNames = await uploadBenchmarkGroup(groupKey);
  uploadedFileNames.push(...storedNames);
}
```

Expected:

```text
Leader 3
Peer 3
Own 3
→ 총 9개 저장 파일명
```

### 4.6 분석 실행

```javascript
const analyzeResponse = await PUT("/benchmk", {
  file: uploadedFileNames,
  page: "SR",
  esgMaterialityRunId: runId,
  sourceStep: "benchmark",
});
```

검증:

```javascript
if (!analyzeResponse || analyzeResponse.status === false) {
  throw new Error(
    analyzeResponse?.message ||
    "벤치마킹 분석에 실패했습니다."
  );
}
```

### 4.7 결과 조회

```javascript
const resultResponse = await GET(
  `/materiality/benchmark/${runId}`
);
```

실제 Backend DTO를 먼저 확인하고, Dashboard Mapper를 작성한다.

Mapper 원칙:

```text
Backend DTO 필드 우선
Dummy shape 강제 금지
null 안전 처리
subIssueCode fallback
```

예시:

```javascript
const mapBenchmarkResultToDashboard = (dto) => ({
  stats: {
    reports: dto.summary?.analyzedReportCount ?? 0,
    leaderCount: dto.summary?.leaderReportCount ?? 0,
    peerCount: dto.summary?.peerReportCount ?? 0,
    ownCount: dto.summary?.ownReportCount ?? 0,
    identifiedIssues: dto.summary?.identifiedIssueCount ?? 0,
    commonIssues: dto.summary?.commonIssueCount ?? 0,
    blindSpots: dto.summary?.blindSpotCount ?? 0,
  },

  topIssues: (dto.topIssues || []).map((item) => ({
    rank: item.rankNo,
    name: item.displaySubIssueName || item.subIssueCode,
    impact:
      item.benchmarkImpactScore10 ??
      item.benchmarkImpactScore05 ??
      0,
    financial:
      item.benchmarkFinancialScore10 ??
      item.benchmarkFinancialScore05 ??
      0,
  })),

  commonIssues: (dto.commonIssues || []).map((item) => ({
    name: item.displaySubIssueName || item.subIssueCode,
    leader: Boolean(item.leaderObserved),
    peer: Boolean(item.peerObserved),
    own: Boolean(item.ownObserved),
  })),

  blindSpots: (dto.blindSpotIssues || []).map((item) => ({
    title: item.displaySubIssueName || item.subIssueCode,
    desc:
      item.summary ||
      "리더·피어 보고서 대비 자사 보고서에서 관측되지 않은 이슈입니다.",
  })),
});
```

주의:

```text
실제 DTO가 다르면 DTO 기준으로 수정
존재하지 않는 필드 억지 추가 금지
```

### 4.8 실행 함수

최소 흐름:

```text
검증
→ 업로드 3회
→ PUT 분석 1회
→ GET 결과 1회
→ Dashboard 표시
```

오류:

```text
Polling 없음
Fake fallback 없음
명시적 Alert
isAnalyzing false
showResult false
```

---

## 5. Backend Benchmark Fail-Closed Patch

수정:

```text
backend/src/services/benchmarks/service.py
```

현재 Warning-only 경로를 닫는다.

### 5.1 Shadow Fact Build 실패

기존:

```text
Warning 출력
Replace TX Skip
Success Response 가능
```

수정:

```text
RuntimeError 전파
Success Response 금지
```

### 5.2 Shadow Replace TX 실패

기존:

```text
Warning 출력
Success Response 가능
```

수정:

```text
RuntimeError 전파
Success Response 금지
```

### 5.3 유지할 범위

```text
Legacy saveSignals
→ 기존 동작 유지

Partial Legacy Save 가능성
→ Post-MVP Debt 기록
```

이번 단계에서는 Legacy Transaction 통합 리팩토링 금지.

---

## 6. 수정 허용 범위

Frontend:

```text
frontend/src/utils/Network.js
frontend/src/homes/reports/BenchMarking.jsx
```

Backend:

```text
backend/src/services/benchmarks/service.py
```

Tests:

```text
backend/tests/test_dma_benchmark_f1_a_api_wiring.py
```

Docs:

```text
docs/dma/v1_3_mvp/26_PHASE_F1_A_BENCHMARK_API_WIRING_RESULT.md
```

수정 금지:

```text
frontend/src/homes/reports/Media.jsx
frontend/src/homes/reports/Survey.jsx
backend/src/services/medias/**
backend/src/services/materialities/orchestrator.py
backend/src/utils/dmarepository.py
backend/src/resources/dma/v1_3_mvp/*.json
*.sql
```

---

## 7. 테스트

신규:

```text
backend/tests/test_dma_benchmark_f1_a_api_wiring.py
```

최소 35개.

### 7.1 Backend Fail-Closed

```text
Fact Normalize 실패 → RuntimeError
Screening Payload Build 실패 → RuntimeError
Replace TX 실패 → RuntimeError
성공 시 Replace TX 정확히 1회
성공 응답은 Replace TX 성공 후에만 반환
```

### 7.2 Frontend Static Contract

```text
POST_FORM 존재
POST_FORM Content-Type 제거
POST_FORM("/benchmk"
PUT("/benchmk"
GET(`/materiality/benchmark/
POST("skm" 없음
/api/v1/benchmark/analyze 없음
USE_DUMMY = true 없음
VITE_BENCHMARK_DUMMY 명시적 Flag
currentRunId selector
runId positive integer 검증
FormData
file append
Leader / Peer / Own Mapping
자사 화면 문구
Interval 기반 fake progress 없음
Media.jsx diff 없음
Survey.jsx diff 없음
SQL diff 없음
```

---

## 8. 검증

Backend:

```bash
python -m compileall backend/src -q
python -m compileall backend/tests -q

python -m pytest \
  backend/tests/test_dma_benchmark_f1_a_api_wiring.py \
  backend/tests/test_dma_v1_3_phase_c1_benchmark_shadow.py \
  backend/tests/test_dma_v1_3_phase_c1_1_benchmark_screening.py \
  backend/tests/test_dma_v1_3_phase_c1_3_benchmark_shadow_replace_active.py \
  -q
```

Frontend:

```bash
cd frontend
npm run build
```

Root:

```bash
git diff --check
git diff --stat
git diff --name-only
git status --short

rg -n 'POST\("skm"|/api/v1/benchmark/analyze|USE_DUMMY = true' frontend/src
rg -n 'eval\(|exec\(' backend/src
```

---

## 9. 완료 보고 형식

```text
Phase F1-A Benchmark API Wiring 완료 보고

Baseline
- branch:
- HEAD:

Frontend
- POST_FORM:
- Upload:
- Analyze:
- Result GET:
- currentRunId:
- Dummy fallback:
- Own mapping:
- Fake Timer:

Backend
- Fact Build fail-closed:
- Replace TX fail-closed:
- Legacy partial-save debt:

Guard
- Media:
- Survey:
- SQL:

Tests
- compileall:
- targeted:
- frontend build:
- git diff --check:

Git
- status:
- add / commit / push:

Next
- F1-B Benchmark Workflow Progress Polling
```

완료 후 멈춰라.
