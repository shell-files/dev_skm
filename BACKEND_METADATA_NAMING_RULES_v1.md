# Backend Metadata Naming Rules v1

작성일: 2026-05-29

## 1. 목적

G0/DMA Phase1 백엔드 코드의 파일명, 함수명, 책임 경계를 통일해 가독성과 유지보수성을 높인다.

이번 문서는 기능 변경을 위한 문서가 아니다. 신규 코드 작성과 향후 리팩토링 전에 먼저 따라야 할 naming/metadata 기준을 고정한다.

핵심 원칙:

```text
새 이름은 먼저 metadata naming dictionary에서 조립한다.
사전에 없는 단어가 필요하면 코드를 만들기 전에 dictionary에 먼저 추가한다.
파일 context가 충분하면 함수명은 짧게 한다.
파일 context가 약하면 함수명을 길게 하기보다 파일 책임을 먼저 분리한다.
기존 public function은 즉시 삭제하지 않고 compatibility alias를 둔다.
보호영역은 naming convention 적용 대상에서 제외한다.
```

## 2. 보호영역

아래 영역은 이번 naming/refactor 작업에서 수정하지 않는다.

```text
backend/src/utils/auth.py
backend/src/utils/tokenset.py
backend/src/utils/fastset.py
backend/src/models/auth.py
로그인/로그아웃/JWT/token validation 흐름
Kafka/mail optional dependency 처리 흐름
API route path
DB schema/column
```

보호영역에는 naming convention을 강제로 적용하지 않는다.

## 3. Layer별 책임

```text
apis
- FastAPI router / endpoint only
- request/response entry point
- business logic 직접 구현 금지

services
- 업무 흐름, orchestration, business logic
- adapter/pipeline/workflow coordination
- utils/repository 호출

utils
- 공통 계산, repository, parser, mapper, reusable helper
- DB query helper/repository
- deterministic scoring/aggregation/rule helper

models
- Pydantic DTO/schema
- request/response/internal model
```

## 4. Folder Naming Rule

```text
folder: lowercase plural
```

예:

```text
apis
services
utils
models
materialities
medias
benchmarks
reports
```

## 5. File Naming Rule

```text
file: lowercase singular, no underscore
```

이 규칙은 `backend/src` 아래 Python source file 기준이다.

다음 파일은 별도 산출물/운영 규칙을 따른다.

```text
문서 파일(.md)
SQL migration / seed file
외부 전달 산출물
legacy file
```

허용:

```text
materiality.py
context.py
dmascoring.py
dmarepository.py
subissuemaster.py
financialexposure.py
```

비권장:

```text
financial_exposure.py
dma_financial.py
company_context_repository.py
```

기존 파일은 즉시 rename하지 않는다. import risk가 낮은 시점에 compatibility alias와 함께 단계적으로 migration한다.

## 6. Function / Variable / Class / Constant Naming Rule

```text
function: camelCase
variable: camelCase
class/model: PascalCase
constant: UPPER_SNAKE_CASE 허용
DB column: snake_case 유지
DTO field: camelCase 유지
API route path: 기존 fastset/router 구조 유지, 임의 변경 금지
```

함수명은 가능하면 아래 형태로 조립한다.

```text
{verb}{Object}{Qualifier}
```

파일 context가 충분하면 Object/Qualifier를 줄일 수 있다.

예:

```text
financialexposure.applyExposure()
financialexposure.applyRunExposure()
financialexposure.buildTrace()
dmascoring.calcScore()
dmarepository.saveSignal()
```

## 7. 허용 Verb Dictionary

| Verb | 의미 |
|---|---|
| `get` | DB/API에서 단건 또는 집계 조회 |
| `list` | 목록 조회 |
| `save` | insert 중심 저장 |
| `update` | update 중심 변경 |
| `upsert` | insert/update |
| `delete` | soft delete 또는 명시 delete |
| `calc` | 순수 수치 계산 |
| `build` | DTO/payload/trace 조립 |
| `apply` | 기존 객체에 rule/modifier/exposure 적용 |
| `resolve` | fallback/우선순위/scope 결정 |
| `check` | boolean 검증 |
| `parse` | JSON/string/date 파싱 |
| `normalize` | 단위/형식 정규화 |
| `map` | source -> target 변환 |
| `merge` | 여러 입력 결합 |
| `clamp` | 범위 제한 |

신규 함수는 이 verb dictionary에서 먼저 조립한다.

## 8. 허용 Object Dictionary

```text
Run
Signal
Score
Stage
Final
Rank
Basis
Factor
Exposure
Trace
Iro
Rule
Source
Scope
Unit
Evidence
Issue
SubIssue
Metric
Profile
Context
Payload
Modifier
Workflow
Status
Action
Rollup
Batch
Company
Subsidiary
Atomic
Fact
Result
Request
Transfer
Summary
```

신규 object가 필요하면 코드를 만들기 전에 이 문서에 먼저 추가한다.

## 9. 허용 Abbreviation Dictionary

```text
DMA
G0
IRO
KPI
DTO
API
DB
ESG
SR
LLM
```

약어는 팀 공통 도메인 약어만 사용한다. 임의 축약은 금지한다.

## 10. 신규 함수 생성 절차

1. 함수 책임이 현재 파일 context와 맞는지 확인한다.
2. 허용 verb dictionary에서 verb를 고른다.
3. 허용 object dictionary에서 object를 고른다.
4. qualifier는 필요할 때만 붙인다.
5. 사전에 없는 단어가 필요하면 먼저 dictionary에 추가한다.
6. public function이면 module metadata header의 Public functions에 추가한다.
7. 기존 긴 함수명을 대체하는 경우 즉시 삭제하지 않고 alias를 둔다.

예:

```text
buildFinancialExposureForSignalWithBasis
-> buildExposureWithBasis

canApplyFinancialExposure
-> checkIro

resolvePreferConsolidated
-> resolveScope
```

## 11. Metadata Header Template

복잡한 파일 상단에는 module docstring으로 아래 metadata header를 둔다.

```python
"""
Domain: DMA Materiality
Layer: service/workflow
Responsibility:
- ...
Public functions:
- ...
Do not:
- do not mutate unrelated DB state
- do not change scoring formula unless explicitly requested
- do not call FastAPI router directly
- do not modify auth/token/common code
"""
```

## 12. 현재 DMA 파일 Rename 후보표

이번 문서 작성 시점에는 파일 rename을 수행하지 않는다.

| 현재 파일 | 판단 | 후보 | 이번 작업 |
|---|---|---|---|
| `dmascoring.py` | keep | 유지 | rename 없음 |
| `dmarepository.py` | keep | 유지 | rename 없음 |
| `dmaaggregator.py` | candidate | `dmaaggregation.py` | not now |
| `dmafinancialrepository.py` | candidate | `dmafinancial.py` | not now |
| `companycontextrepository.py` | candidate | `dmacontext.py` | not now |
| `subissuemaster.py` | keep | 유지 | rename 없음 |
| `financial_exposure.py` | candidate | `financialexposure.py` | not now |

## 13. 현재 DMA 함수 Rename / Alias 후보표

기존 함수명은 삭제하지 않는다. 먼저 짧은 alias wrapper를 추가하고, 호출부 migration은 별도 단계에서 진행한다.

| 기존 함수 | 후보 alias |
|---|---|
| `applyG0FinancialExposure` | `applyExposure` |
| `applyG0FinancialExposureForRun` | `applyRunExposure` |
| `buildFinancialExposureForSignal` | `buildExposure` |
| `buildFinancialExposureForSignalWithBasis` | `buildExposureWithBasis` |
| `calculateChannelScore` | `calcChannelScore` |
| `sourceTypeMagnitudeBonus` | `calcSourceBonus` |
| `confidenceMagnitudeCap` | `calcConfidenceCap` |
| `dominantMagnitude` | `resolveDominant` |
| `canApplyFinancialExposure` | `checkIro` |
| `resolvePreferConsolidated` | `resolveScope` |

## 14. 단계별 Migration Strategy

### Step 1. 문서 확정

- `BACKEND_METADATA_NAMING_RULES_v1.md` 승인.
- 보호영역과 forbidden changes 확인.

### Step 2. Metadata header 추가

대상:

```text
backend/src/services/materialities/financial_exposure.py
backend/src/services/materialities/context.py
backend/src/services/materialities/context_graph.py
backend/src/utils/dmarepository.py
backend/src/utils/dmafinancialrepository.py
backend/src/utils/dmaaggregator.py
backend/src/utils/dmascoring.py
backend/src/utils/companycontextrepository.py
```

동작 변경 없이 module docstring만 추가한다.

### Step 3. 안전 alias 추가

`financial_exposure.py`에 짧은 alias wrapper를 추가한다.

- 기존 함수 삭제 금지.
- 기존 호출부 변경 금지.
- `__all__`에는 기존 함수와 alias 모두 포함.
- 동작/trace/output 변경 금지.

### Step 4. Smoke

- compileall
- import smoke
- old function import smoke
- alias import smoke
- protected file diff 없음 확인

### Step 5. 후속 rename 검토

파일 rename은 MVP 안정화 후 별도 작업으로 진행한다.

## 15. Forbidden Changes

이번 naming/refactor 작업에서 금지한다.

```text
auth/token/common 영역 수정
backend/src/utils/auth.py 수정
backend/src/utils/tokenset.py 수정
backend/src/utils/fastset.py 수정
backend/src/models/auth.py 수정
로그인/로그아웃/JWT/token validation 흐름 수정
Kafka/mail optional dependency 처리 흐름 수정
API path 변경
DB schema/column 변경
dmascoring.py 산식 변경
dmaaggregator.py final/stage weight 변경
media/benchmark adapter 연결
기존 public function 삭제
파일명 대량 rename
import 경로 대량 수정
```

## 16. Smoke Checklist

작업 후 확인한다.

```text
python -m compileall backend/src

financial_exposure.py import smoke
기존 함수명 import smoke
새 alias import smoke

금지 파일 diff 없음:
- backend/src/utils/auth.py
- backend/src/utils/tokenset.py
- backend/src/utils/fastset.py
- backend/src/models/auth.py

dmascoring.py 산식 변경 없음
dmaaggregator.py weight 변경 없음
API route 변경 없음
```

## 17. Known Risk / Next Refactor Target

`backend/src/services/materialities/context.py`는 현재 `applyCompanyContextModifiers()` flow integrity 점검이 필요하다.

관찰된 리스크:

```text
context.py applyCompanyContextModifiers flow integrity needs repair before next functional WP.
modifier 적용 로직 일부가 getCompanyContextProfile() return 뒤 unreachable code처럼 보인다.
```

이번 naming refactor는 이 구조 결함을 수정하지 않는다.

```text
This naming refactor intentionally does not change behavior.
```
