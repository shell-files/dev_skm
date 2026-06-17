# DEV_SKM 리팩토링 로그

> 기준 컨벤션: [CONVENTIONS.md](./CONVENTIONS.md) v1.2
> 시작일: 2026-06-17
> 작업 브랜치: `Feature/refactoring_lch`

---

## 커밋 이력

| # | 커밋 메시지 | 상태 |
|---|------------|------|
| 1 | `[BE] utils/*repository.py 파일 repositories/ 폴더로 계층 분리 (#257)` | ✅ 완료 |
| 2 | `[BE] utils/rollupcalculator.py를 services/rollups/calculator.py로 이동 (#257)` | ✅ 완료 |
| 3 | `[BE] 개발 컨벤션 및 리팩토링 계획 문서 추가 (#257)` | 🔲 예정 |

---

## 진행 현황

| 우선순위 | 항목 | 상태 |
|----------|------|------|
| 1 | 비대해진 파일 분리 | 🔲 대기 |
| 2 | API → Service → Repository 계층 준수 | 🔲 대기 |
| **3** | **Repository 분리 및 정리** | **✅ 완료** |
| **4** | **Utils 남용 방지** | **✅ 완료** |
| 5 | Frontend 페이지 분리 | 🔲 대기 |
| 6 | 공통 컴포넌트 재사용 | 🔲 대기 |
| 7 | 컨벤션 준수 및 문서화 | 🔲 대기 |

---

## 완료된 작업

---

### ✅ [우선순위 3] Repository 분리 — 2026-06-17

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

### ✅ [우선순위 4] Utils 남용 방지 — 2026-06-17

**목적:** `utils/`에 있던 비즈니스 로직 파일을 적절한 계층으로 이동

#### 검토 대상 5개 파일

| 파일 | 줄 수 | 판단 | 처리 |
|------|-------|------|------|
| `utils/rollupcalculator.py` | 604 | 비즈니스 로직 (rollup 전용) | ✅ 이동 |
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

## 대기 중인 작업

---

### 🔲 [우선순위 1] 비대한 파일 분리

500줄 이상 파일 중 분리가 필요한 대상 (subissuemaster.py 제외 — 현 구조 유지)

| 파일 | 줄 수 | 비고 |
|------|-------|------|
| `services/rollups/service.py` | 1,360 | 분리 필요 |
| `services/onboardings/service.py` | 1,179 | 분리 필요 |
| `services/materialities/financialexposure.py` | 820 | 분리 검토 |
| `services/materialities/service.py` | 819 | 분리 검토 |
| `services/surveys/importservice.py` | 751 | 분리 검토 |
| `services/materialities/orchestrator.py` | 736 | 분리 검토 |
| `services/materialities/context.py` | 715 | 분리 검토 |
| `services/onboardings/approval_service.py` | 634 | 분리 검토 |
| `utils/dmaruleregistry.py` | 623 | 분리 검토 |
| `services/medias/service.py` | 533 | 분리 검토 |

---

### 🔲 [우선순위 2] API → Service → Repository 계층 준수

계층 위반 여부 전수 검사 필요

- API가 Repository를 직접 호출하는 경우
- Service가 SQL을 직접 작성하는 경우
- Utils에 비즈니스 로직이 남아있는 경우

---

### 🔲 [우선순위 5] Frontend 페이지 분리

300줄 이상 파일 분리 검토 필요 (미진단)

---

### 🔲 [우선순위 6] 공통 컴포넌트 재사용

2회 이상 반복 사용 컴포넌트 추출 필요 (미진단)

---

## 구조 변경 금지 목록

아래 파일은 AI/RAG 안정성 원칙 또는 팀 결정에 의해 현 구조를 유지한다.

| 파일 | 사유 |
|------|------|
| `utils/subissuemaster.py` | 팀 결정 — 현 구조 유지 |
| `utils/dmascoring.py` | LEGACY, Phase C 전환 완료 후 재검토 |
| `utils/dmaaggregator.py` | LEGACY, 신규 Orchestrator 전환 완료 후 재검토 |
