# Feature/refactoring_lch 작업 요약

> 브랜치: `Feature/refactoring_lch` | 이슈: `#257`
> 기간: 2026-06-17 ~ 2026-06-18
> 기준 컨벤션: CONVENTIONS.md v1.3

---

## 작업 목표

코드베이스 전반의 구조를 CONVENTIONS.md 기준에 맞게 정리.
비대해진 파일 분리, 계층 준수, 중복 제거, 프론트엔드 페이지 컴포넌트 분리.

---

## 백엔드 작업 (커밋 1 ~ 18)

### [우선순위 3] Repository 계층 분리

**목적:** `utils/`에 혼재하던 Repository 파일 20개를 `repositories/` 전용 폴더로 이전

| 변경 | 내용 |
|------|------|
| 신규 폴더 | `src/repositories/` 생성 |
| 이동 파일 | 20개 `*repository.py` → `repositories/` |
| import 업데이트 | 35개 파일 (`src.utils.*` → `src.repositories.*`) |

---

### [우선순위 4] Utils 남용 방지

| 파일 | 처리 |
|------|------|
| `utils/rollupcalculator.py` | `services/rollups/calculator.py`로 이동 |
| `utils/dmascoring.py` | LEGACY — 유지 |
| `utils/dmaruleregistry.py` | 설정/캐시 인프라 — 유지 |
| `utils/calculationengine.py` | 공통 수식 엔진 — 유지 |
| `utils/dmaaggregator.py` | LEGACY — 유지 |

---

### [우선순위 5] 중복 코드 제거

| 함수 | 처리 |
|------|------|
| `firstPresent` | `utils/typeutils.py`로 통합 (adapter 3개에서 제거) |
| `asFloat` / `dedupeItems` / `validateRunId` | `typeutils.py`로 공통화 |
| `maskEmail` / `inviteExpireSeconds` | 공통화 |
| `listMetricScopesTx` | 중복 정의 제거 |
| `services/medias/service.py` (기존) | 삭제 — `newsservice.py`로 대체 |

---

### [우선순위 2] API → Service → Repository 계층 위반 수정

| 위반 파일 | 위반 내용 | 처리 |
|-----------|-----------|------|
| `repositories/onboardingapprovalrepository.py` | Repository → Service 순환 의존 | `_deprecated.py`로 이동 |
| `repositories/onboardingassignmentrepository.py` | Repository → Service (`requireWritableCycleTx`) | `scopeRepo`로 경로 변경 |
| `apis/materiality.py` | API → Repository 직접 호출 | `service.getWorkflowStatus` wrapper 추가 |
| `apis/survey.py` | API → Repository 직접 호출 | `formservice.getSurveyFormDetail` wrapper 추가 |

---

### [우선순위 1] 비대한 파일 분리

| 파일 | 전 | 후 | 추출 내용 |
|------|----|----|-----------|
| `services/rollups/service.py` | 1,354줄 | 889줄 | `rollupbuilder.py`, `rollupbaseline.py`, `rollupexceptions.py` |
| `services/onboardings/service.py` | 1,179줄 | 735줄 | `assignmentService.py`, `approvalHandler.py`, `approvalService.py` |
| `services/materialities/service.py` | 819줄 | 472줄 | `materialitybuilder.py` |
| `services/materialities/financialexposure.py` | 820줄 | 424줄 | `financialexposurecalc.py` |
| `services/surveys/importservice.py` | 751줄 | 78줄 | `importmeta.py`, `importparser.py` |
| `services/materialities/orchestrator.py` | 736줄 | 190줄 | `screeningbuilder.py` |
| `services/materialities/context.py` | 715줄 | 230줄 | `contextbuilder.py` |
| `services/onboardings/approvalservice.py` | 634줄 | 429줄 | `approvalcycle.py` |
| `utils/dmaruleregistry.py` | 623줄 | 186줄 | `dmarulevalidator.py` |
| `services/medias/service.py` | 533줄 | 459줄 | `newsservice.py` |

---

## 프론트엔드 작업 (커밋 19 ~ 24)

### [우선순위 7] Frontend 페이지 분리

**컨벤션 규칙:** 페이지별 서브 컴포넌트는 `homes/reports/<pagename>/` 폴더로 분리.
메인 파일명 유지 (`index.jsx` 아님).

| 파일 | 전 | 후 | 추출 파일 |
|------|----|----|-----------|
| `Draft.jsx` | 908줄 | - | `srTemplates/core/TrendChart.jsx`, `srTemplates/core/draftExport.js` |
| `OnBoard.jsx` | 1,570줄 | 1,177줄 | `OnboardingStatCards.jsx`, `OnboardingWorkflowCta.jsx`, `OnboardingMetricTable.jsx` |
| `Result.jsx` | 1,399줄 | 817줄 | `result/DoubleMaterialityChart.jsx`, `result/ImportanceBadge.jsx` |
| `Media.jsx` | 1,323줄 | 997줄 | `media/mediaData.jsx`, `media/MediaResultDashboard.jsx` |
| `BenchMarking.jsx` | 819줄 | 543줄 | `bench/benchConfig.js`, `bench/BenchResultDashboard.jsx` |
| `Survey.jsx` | 847줄 | 577줄 | `survey/surveyConstants.jsx`, `survey/SurveyResultDashboard.jsx` |

#### 최종 폴더 구조

```
frontend/src/homes/reports/
├── result/
│   ├── Result.jsx
│   ├── DoubleMaterialityChart.jsx
│   └── ImportanceBadge.jsx
├── media/
│   ├── Media.jsx
│   ├── mediaData.jsx
│   └── MediaResultDashboard.jsx
├── bench/
│   ├── BenchMarking.jsx
│   ├── benchConfig.js
│   └── BenchResultDashboard.jsx
├── survey/
│   ├── Survey.jsx
│   ├── surveyConstants.jsx
│   └── SurveyResultDashboard.jsx
├── Draft.jsx
└── (기타 미분리 파일)
```

---

## 전체 커밋 이력

| # | 커밋 메시지 | 분류 |
|---|------------|------|
| 1 | `utils/*repository.py → repositories/ 계층 분리` | BE 구조 |
| 2 | `utils/rollupcalculator.py → services/rollups/calculator.py 이동` | BE 구조 |
| 3 | `개발 컨벤션 및 리팩토링 계획 문서 추가` | 문서 |
| 4 | `API-Service-Repository 계층 위반 수정` | BE 계층 |
| 5 | `중복 유틸 함수 typeutils로 통합` | 중복 제거 |
| 6 | `README WBS 정리 및 scratch 파일 제거` | 문서 |
| 7 | `media 뉴스 분석 서비스 newsservice.py로 분리 및 중복 함수 통합` | BE 분리 |
| 8 | `rollups/service.py 분리 — rollupbuilder, rollupbaseline, rollupexceptions` | BE 분리 |
| 9 | `onboardings/service.py 분리 — assignmentService, approvalHandler, approvalService` | BE 분리 |
| 10 | `materialities/service.py 분리 — materialitybuilder로 빌더 함수 추출` | BE 분리 |
| 11 | `materialities/financialexposure.py 분리 — financialexposurecalc으로 계산 로직 추출` | BE 분리 |
| 12 | `surveys/importservice.py 분리 — importmeta, importparser로 추출` | BE 분리 |
| 13 | `materialities/orchestrator.py 분리 — screeningbuilder로 배치 빌더 추출` | BE 분리 |
| 14 | `materialities/context.py 분리 — contextbuilder로 프로파일/수정자 계산 추출` | BE 분리 |
| 15 | `onboardings/approvalservice.py 분리 — approvalcycle로 사이클/스코프 헬퍼 추출` | BE 분리 |
| 16 | `utils/dmaruleregistry.py 분리 — dmarulevalidator로 정책 검증 로직 추출` | BE 분리 |
| 17 | `중복 함수 통합 — medias/service 삭제, asFloat/dedupeItems/validateRunId 공통화` | 중복 제거 |
| 18 | `중복 함수 추가 통합 — maskEmail/inviteExpireSeconds 공통화, listMetricScopesTx 중복 정의 제거` | 중복 제거 |
| 19 | `Draft.jsx 분리 — TrendChart/buildMetricsFromEdits/export 로직 추출` | FE 분리 |
| 20 | `OnBoard.jsx 분리 — OnboardingStatCards/WorkflowCta/MetricTable 추출` | FE 분리 |
| 21 | `Result.jsx 분리 — DoubleMaterialityChart/ImportanceBadge 추출 및 result/ 폴더 정리` | FE 분리 |
| 22 | `Media.jsx 분리 — MediaResultDashboard/mediaData 추출 및 media/ 폴더 정리` | FE 분리 |
| 23 | `BenchMarking.jsx 분리 — BenchResultDashboard/benchConfig 추출 및 bench/ 폴더 정리` | FE 분리 |
| 24 | `Survey.jsx 분리 — SurveyResultDashboard/surveyConstants 추출 및 survey/ 폴더 정리` | FE 분리 |

---

## 잔여 작업

### Priority 7 — 프론트엔드 미분리 파일

| 파일 | 줄 수 | 비고 |
|------|-------|------|
| `ManagerData.jsx` | 733 | `mains/` 소속 |
| `OnboardingModalShell.jsx` | 652 | `onboards/` 소속 |
| `Signup.jsx` | 607 | `logins/` 소속 |
| `DataTab.jsx` | 606 | |
| `reportSlice.js` | 1,854 | Redux slice — 별도 검토 필요 |

### 구조 변경 금지 목록

| 파일 | 사유 |
|------|------|
| `utils/subissuemaster.py` | 팀 결정 — 현 구조 유지 |
| `utils/dmascoring.py` | LEGACY, Phase C 전환 완료 후 재검토 |
| `utils/dmaaggregator.py` | LEGACY, 신규 Orchestrator 전환 완료 후 재검토 |
