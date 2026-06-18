# DEV_SKM 리팩토링 로그

> 기준 컨벤션: [CONVENTIONS.md](./CONVENTIONS.md) v1.3
> 시작일: 2026-06-17
> 작업 브랜치: `Feature/refactoring_lch`

---

## 커밋 이력

| # | 커밋 메시지 | 상태 |
|---|------------|------|
| 1 | `[BE] utils/*repository.py 파일 repositories/ 폴더로 계층 분리 (#257)` |  완료 |
| 2 | `[BE] utils/rollupcalculator.py를 services/rollups/calculator.py로 이동 (#257)` |  완료 |
| 3 | `[BE] 개발 컨벤션 및 리팩토링 계획 문서 추가 (#257)` |  완료 |
| 4 | `[BE] API-Service-Repository 계층 위반 수정 (#257)` |  완료 |
| 5 | `[BE] 중복 유틸 함수 typeutils로 통합 (#257)` |  완료 |
| 6 | `[BE] README WBS 정리 및 scratch 파일 제거 (#257)` |  완료 |
| 7 | `[BE] media 뉴스 분석 서비스 newsservice.py로 분리 및 중복 함수 통합 (#257)` |  완료 |
| 8 | `[BE] rollups/service.py 분리 — rollupbuilder, rollupbaseline, rollupexceptions (#257)` |  완료 |
| 9 | `[BE] onboardings/service.py 분리 — assignmentService, approvalHandler, approvalService (#257)` |  완료 |
| 10 | `materialities/service.py 분리 — materialitybuilder로 빌더 함수 추출 (#257)` |  완료 |
| 11 | `materialities/financialexposure.py 분리 — financialexposurecalc으로 계산 로직 추출 (#257)` |  완료 |
| 12 | `surveys/importservice.py 분리 — importmeta, importparser로 추출 (#257)` |  완료 |
| 13 | `materialities/orchestrator.py 분리 — screeningbuilder로 배치 빌더 추출 (#257)` |  완료 |
| 14 | `materialities/context.py 분리 — contextbuilder로 프로파일/수정자 계산 추출 (#257)` |  완료 |
| 15 | `onboardings/approvalservice.py 분리 — approvalcycle로 사이클/스코프 헬퍼 추출 (#257)` |  완료 |
| 16 | `utils/dmaruleregistry.py 분리 — dmarulevalidator로 정책 검증 로직 추출 (#257)` |  완료 |
| 17 | `중복 함수 통합 — medias/service 삭제, asFloat/dedupeItems/validateRunId 공통화 (#257)` |  완료 |
| 18 | `중복 함수 추가 통합 — maskEmail/inviteExpireSeconds 공통화, listMetricScopesTx 중복 정의 제거 (#257)` |  완료 |
| 19 | `Draft.jsx 분리 — TrendChart/buildMetricsFromEdits/export 로직 추출 (#257)` |  완료 |
| 20 | `OnBoard.jsx 분리 — OnboardingStatCards/WorkflowCta/MetricTable 추출 (#257)` |  완료 |

---

## 진행 현황

| 우선순위 | 항목 | 상태 |
|----------|------|------|
| **1** | **비대해진 파일 분리** | ** 완료** |
| 2 | API → Service → Repository 계층 준수 |  완료 |
| **3** | **Repository 분리 및 정리** | ** 완료** |
| 4 | Service 의존성 정리 및 순환 참조 제거 |  대기 |
| 5 | 중복 코드 제거 |  완료 (46→32개, 나머지는 의도적 패턴) |
| **6** | **Utils 남용 방지** | ** 완료** |
| 7 | Frontend 페이지 분리 |  진행 중 |
| 8 | 공통 컴포넌트 재사용 |  대기 |
| 9 | 컨벤션 준수 및 문서화 |  대기 |

---

## 완료된 작업

---

###  [우선순위 3] Repository 분리 — 2026-06-17

**목적:** `utils/`에 혼재하던 Repository 파일 20개를 `repositories/` 전용 폴더로 이전

#### 변경 내용

```
src/
├── repositories/      ← 신규 생성
│   ├── calculationrepository.py
│   ├── companycontextrepository.py
│   ├── dmarepository.py
│   ├── dmasurveyformrepository.py
│   ├── dmasurveyresponserepository.py
│   ├── dmasurveyscorerepository.py
│   ├── dmasurveytargetrepository.py
│   ├── dmaworkflowrepository.py
│   ├── draftrepository.py
│   ├── financialbasisrepository.py
│   ├── onboardingapprovalrepository.py
│   ├── onboardingassignmentrepository.py
│   ├── onboardinginputrepository.py
│   ├── onboardingrepository.py
│   ├── onboardingscoperepository.py
│   ├── reportrepository.py
│   ├── reportworkflowrepository.py
│   ├── rollupbatchrepository.py
│   ├── rolluprepository.py
│   └── rollupscoperepository.py
└── utils/             ← 위 20개 파일 삭제됨
```

#### import 업데이트

- 변경 패턴: `from src.utils.*repository` → `from src.repositories.*repository`
- 업데이트된 파일 수: **35개**

---

###  [우선순위 4] Utils 남용 방지 — 2026-06-17

**목적:** `utils/`에 있던 비즈니스 로직 파일을 적절한 계층으로 이동

#### 검토 대상 5개 파일

| 파일 | 줄 수 | 판단 | 처리 |
|------|-------|------|------|
| `utils/rollupcalculator.py` | 604 | 비즈니스 로직 (rollup 전용) |  이동 |
| `utils/dmascoring.py` | 778 | LEGACY + 여러 services 공통 사용 | 유지 |
| `utils/dmaruleregistry.py` | 623 | 설정/캐시 인프라 | 유지 |
| `utils/calculationengine.py` | 512 | 공통 수식 엔진 (여러 계층 공통) | 유지 |
| `utils/dmaaggregator.py` | 355 | LEGACY + 여러 레이어 공통 | 유지 |

#### 변경 내용

```
utils/rollupcalculator.py
  → services/rollups/calculator.py  (이동)

services/rollups/service.py
  loadCalculator() 내 import 경로 수정
  from src.utils import rollupcalculator
  → from src.services.rollups import calculator
```

---

###  media 뉴스 분석 서비스 분리 및 중복 함수 통합 — 2026-06-17

**목적:** media 서비스 계층 분리 및 3개 adapter 파일의 중복 `firstPresent` 통합

#### 변경 내용

| 파일 | 변경 내용 |
|------|-----------|
| `services/medias/newsservice.py` | 신규 생성 — `runMediaCrawlAndAnalyze`, `saveKcgsGradeInputs` 및 내부 헬퍼 |
| `apis/media.py` | import 경로: `service` → `newsservice` |
| `repositories/dmarepository.py` | `countTop20RankedSubIssues`, `saveKcgsGradeInputRows` 신규 추가 |
| `utils/typeutils.py` | `firstPresent` 함수 추가 (`Mapping[str, Any]` 키 우선 탐색) |
| `services/benchmarks/adapter.py` | 로컬 `firstPresent` 제거 → `typeutils` import |
| `services/medias/adapter.py` | 로컬 `firstPresent` 제거 → `typeutils` import |
| `services/surveys/adapter.py` | 로컬 `firstPresent` 제거 → `typeutils` import |

---

###  rollups/service.py 분리 — 2026-06-18

**목적:** 1,354줄 대형 파일을 책임 단위로 분리

#### 변경 내용

| 파일 | 줄 수 | 비고 |
|------|-------|------|
| `services/rollups/rollupexceptions.py` | 10 | 신규 — `RollupError` 단일 정의 |
| `services/rollups/rollupbuilder.py` | 290 | 신규 — 빌더/헬퍼 함수 + `loadRepository`, `loadCalculator` |
| `services/rollups/rollupbaseline.py` | 203 | 신규 — `getBaselineRequirements`, `saveBaselineValues`, `resolveBaselineRequirementTuples` |
| `services/rollups/service.py` | 889 (-465) | 수정 — 주요 서비스 함수만 유지, 위 3파일 import |
| `services/rollups/calculator.py` | 598 (-8) | `ruleCode`, `targetAtomicMetricId` 로컬 중복 제거 → `calculationengine` import |
| `utils/calculationengine.py` | +3 | `ruleCode`, `targetAtomicMetricId`, `normalizeSources` `__all__` 추가 |

#### API 영향 없음
`apis/rollup.py`는 동일한 `service.py` 경로에서 동일한 public 함수명으로 import — 변경 불필요

---

#### 잔여 중복 (이번 커밋 미처리)

| 함수 | 파일 수 | 비고 |
|------|---------|------|
| `statusForValueError` | 4개 API 파일 | 구현이 서로 달라 즉시 통합 불가 — Priority 1 분리 시 처리 |
| `getLatestReportRunByMaterialityRun` | dmarepository + reportrepository | SELECT 컬럼 상이 — 호환 분석 필요 |
| `safeFloat` | dmarepository (wrapper) | typeutils 위임 래퍼 — 의도적 유지 |

---

## 대기 중인 작업

---

###  [우선순위 1] 비대한 파일 분리

500줄 이상 파일 중 분리가 필요한 대상 (subissuemaster.py 제외 — 현 구조 유지)

| 파일 | 줄 수 | 비고 |
|------|-------|------|
| ~~`services/rollups/service.py`~~ | ~~1,360~~ → 889 |  완료 |
| ~~`services/onboardings/service.py`~~ | ~~1,179~~ → 735 |  완료 |
| ~~`services/materialities/financialexposure.py`~~ | ~~820~~ → 424 |  완료 |
| ~~`services/materialities/service.py`~~ | ~~819~~ → 472 |  완료 |
| ~~`services/surveys/importservice.py`~~ | ~~751~~ → 78 |  완료 |
| ~~`services/materialities/orchestrator.py`~~ | ~~736~~ → 190 |  완료 |
| ~~`services/materialities/context.py`~~ | ~~715~~ → 230 |  완료 |
| ~~`services/onboardings/approvalservice.py`~~ | ~~634~~ → 429 |  완료 |
| ~~`utils/dmaruleregistry.py`~~ | ~~623~~ → 186 |  완료 |
| ~~`services/medias/service.py`~~ | ~~533~~ → 459 |  완료 (newsservice.py 분리 시 이미 감소) |

---

###  [우선순위 2] API → Service → Repository 계층 준수 — 2026-06-17

#### 수정된 계층 위반 4건

| 위반 파일 | 위반 내용 | 처리 |
|-----------|-----------|------|
| `repositories/onboardingapprovalrepository.py` | Repository → Service 순환 의존 (G002 wrapper 3개) | `_deprecated.py`로 이동 |
| `repositories/onboardingassignmentrepository.py` | Repository → Service (`requireWritableCycleTx`) | `scopeRepo`로 경로 변경 |
| `apis/materiality.py` | API → Repository 직접 호출 | `service.getWorkflowStatus` wrapper 추가 |
| `apis/survey.py` | API → Repository 직접 호출 | `formservice.getSurveyFormDetail` wrapper 추가 |

#### 변경 파일 목록

- `repositories/onboardingscoperepository.py` — `requireWritableCycleTx` 함수 이동 (service → repository)
- `repositories/onboardingapprovalrepository.py` — G002 wrapper 3개 제거 (→ `_deprecated.py`)
- `repositories/onboardingassignmentrepository.py` — `approval_service` import 제거, `scopeRepo` import 추가
- `repositories/_deprecated.py` — 신규 생성 (사용처 없는 dead code 보관용)
- `services/onboardings/approval_service.py` — `requireWritableCycleTx` 정의 제거, `scopeRepo` 경유 호출
- `services/onboardings/service.py` — `scopeRepo` import 추가, lazy import 제거
- `services/materialities/service.py` — `getWorkflowStatus` wrapper 추가
- `services/surveys/formservice.py` — `getSurveyFormDetail` wrapper 추가
- `apis/materiality.py` — `dmaworkflowrepository` 직접 import 제거
- `apis/survey.py` — `dmasurveyformrepository` 직접 import 제거

#### 미완료 (서비스 내 SQL 직접 작성)

7개 service 파일의 SQL 직접 작성은 규모가 크고 파일 분리와 함께 처리 예정 (우선순위 1 작업 시 동반)

---

---

###  [우선순위 7] Frontend 페이지 분리 — 진행 중

#### 완료

| 파일 | 원본 줄 수 | 추출 결과 |
|------|-----------|-----------|
| `Draft.jsx` | 908 | `TrendChart.jsx`, `draftExport.js`, `srHelpers.jsx` (+buildMetricsFromEdits) |
| `OnBoard.jsx` | 1,570 | `OnboardingStatCards.jsx`, `OnboardingWorkflowCta.jsx`, `OnboardingMetricTable.jsx` |

#### 대기 중

| 파일 | 줄 수 | 우선순위 |
|------|-------|---------|
| `Result.jsx` | 1,399 | 높음 |
| `Media.jsx` | 1,229 | 높음 |
| `Survey.jsx` | 790 | 중간 |
| `BenchMarking.jsx` | 740 | 중간 |
| `ManagerData.jsx` | 733 | 중간 |
| `OnboardingModalShell.jsx` | 652 | 중간 |
| `Signup.jsx` | 607 | 낮음 |
| `DataTab.jsx` | 606 | 낮음 |
| `reportSlice.js` | 1,854 | 별도 검토 |

---

###  [우선순위 8] 공통 컴포넌트 재사용

2회 이상 반복 사용 컴포넌트 추출 필요 (미진단)

---

## 구조 변경 금지 목록

아래 파일은 AI/RAG 안정성 원칙 또는 팀 결정에 의해 현 구조를 유지한다.

| 파일 | 사유 |
|------|------|
| `utils/subissuemaster.py` | 팀 결정 — 현 구조 유지 |
| `utils/dmascoring.py` | LEGACY, Phase C 전환 완료 후 재검토 |
| `utils/dmaaggregator.py` | LEGACY, 신규 Orchestrator 전환 완료 후 재검토 |
