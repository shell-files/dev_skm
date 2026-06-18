# DEV_SKM 컨벤션

> Version: 1.3

---

## 목차

1. [공통 원칙](#1-공통-원칙)
2. [Backend 컨벤션](#2-backend-컨벤션)
   - [네이밍 규칙](#네이밍-규칙)
   - [파일 및 폴더 규칙](#파일-및-폴더-규칙)
   - [모듈화 규칙](#모듈화-규칙)
   - [파일 크기 규칙](#파일-크기-규칙)
   - [API 계층 규칙](#api-계층-규칙)
   - [Repository 위치](#repository-위치)
   - [RESTful API 규칙](#restful-api-규칙)
   - [Response 규칙](#response-규칙)
   - [DELETE 규칙](#delete-규칙)
   - [Utils 규칙](#utils-규칙)
3. [Frontend 컨벤션](#3-frontend-컨벤션)
   - [네이밍 규칙](#네이밍-규칙-1)
   - [컴포넌트 규칙](#컴포넌트-규칙)
   - [파일 크기 규칙](#파일-크기-규칙-1)
   - [Import 규칙](#import-규칙)
4. [주석 규칙](#4-주석-규칙)
5. [함수 작성 규칙](#5-함수-작성-규칙)
6. [아키텍처 규칙](#6-아키텍처-규칙)
   - [순환 참조 금지](#순환-참조-금지)
   - [Service 간 직접 의존 최소화](#service-간-직접-의존-최소화)
   - [환경변수 접근 규칙](#환경변수-접근-규칙)
   - [중복 코드 최소화](#중복-코드-최소화)
7. [AI / RAG](#7-ai--rag)
8. [Batch / Scheduler 규칙](#8-batch--scheduler-규칙)
9. [Redis 규칙](#9-redis-규칙)
10. [리팩토링 우선순위](#10-리팩토링-우선순위)
11. [변경 이력](#11-변경-이력)

---

## 1. 공통 원칙

- 현재 프로젝트 트리 구조는 최대한 유지한다.
- 구조 변경보다는 기능 분리와 코드 가독성 향상을 우선한다.
- 기능 중심 개발을 지향한다.
- 과도한 Class 사용은 지양하고 함수 기반 모듈화를 우선한다.
- 동일한 기능이 비대해질 경우 폴더 단위로 분리한다.
- 리팩토링의 목적은 "구조 개선"보다 "유지보수성 향상"에 둔다.
- 기존 코드 스타일과 프로젝트 컨벤션을 존중한다.

---

## 2. Backend 컨벤션

### 네이밍 규칙

#### 변수 / 함수

프로젝트 내부 변수 및 함수는 **camelCase**를 사용한다.

```python
companyId
reportData
createReport()
getCompany()
updateMateriality()
```

#### Boolean 변수

`is` / `has` / `can` 접두어를 사용한다.

```python
isDeleted
isCompleted
hasPermission
canEdit
```

#### 예외

Python 표준 라이브러리, 외부 라이브러리, DB 컬럼명, 환경설정 키 등은 원본 규칙을 따른다.

| 대상 | 규칙 |
|------|------|
| 프로젝트 내부 변수 및 함수 | camelCase |
| DB 컬럼명 | snake_case (원본 유지) |
| 외부 라이브러리 함수 | 라이브러리 원본 유지 |

```python
# DB 컬럼 - 원본 유지
delete_yn
created_at
updated_at

# 외부 라이브러리 - 원본 유지
os.getenv()
json.dumps()
```

> **Lint 도구 관련**
> 현재 프로젝트는 스타일 linter(Ruff 등)를 사용하지 않으므로 camelCase 사용 시 오류가 발생하지 않는다.
> 추후 lint 도구를 도입하거나 설정을 변경할 경우, 현재 컨벤션과 충돌하지 않도록 설정을 검토해야 한다.

---

### 파일 및 폴더 규칙

#### 파일

- 소문자
- 단수형

```
company.py
report.py
materiality.py
```

#### 폴더

- 소문자
- 복수형

```
services/
apis/
models/
repositories/
```

---

### 모듈화 규칙

- 기능별 모듈화
- Class 사용 지양
- 함수 기반 개발 우선

```
services/materialities/
├── calculate.py
├── workflow.py
├── benchmark.py
└── materiality.py
```

---

### 파일 크기 규칙

| 기준 | 조치 |
|------|------|
| 300줄 이상 | 분리 검토 |
| 500줄 이상 | 분리 권장 |

- 줄 수보다 **기능 단위 분리**를 우선한다.
- 하나의 파일에 여러 책임이 존재하면 분리한다.

---

### API 계층 규칙

```
API
 ↓
Service
 ↓
Repository
 ↓
DB
```

#### API 계층

| 항목 | 내용 |
|------|------|
| 담당 | Request 수신, Validation, Response 반환 |
| 금지 | SQL 작성, DB 직접 접근, Repository 직접 호출 |

#### Service 계층

| 항목 | 내용 |
|------|------|
| 담당 | 비즈니스 로직 처리 |
| 금지 | SQL 작성 |

#### Repository 계층

| 항목 | 내용 |
|------|------|
| 담당 | DB 조회, DB 저장, DB 수정, DB 삭제 |
| 규칙 | DB 접근은 Repository에서만 수행 |

> Repository는 반드시 `repositories/` 폴더에 생성한다. `utils/`에 생성하지 않는다.

---

### Repository 위치

```
src/
├── apis/
├── services/
├── repositories/      ← Repository 전용 폴더
├── models/
├── utils/
└── resources/
```

```
repositories/
├── company.py
├── materiality.py
├── report.py
├── survey.py
```

> 기존 `utils/`에 위치한 Repository는 점진적으로 `repositories/`로 이전한다.
> 신규 Repository는 반드시 `repositories/`에 생성한다.

---

### RESTful API 규칙

#### HTTP Method

| Method | 용도 |
|--------|------|
| `GET` | 조회 |
| `POST` | 생성 |
| `PUT` | 전체 수정 또는 Upsert |
| `PATCH` | 부분 수정 |
| `DELETE` | 삭제 |

#### URL

```http
# 권장
GET  /api/companies
GET  /api/companies/{id}
POST /api/materialities
PUT  /api/reports/{id}

# 비권장
/getCompany
/createCompany
/deleteCompany
```

---

### Response 규칙

모든 API 응답은 공통 `ResponseModel`을 사용한다.

```python
def ResponseModel(
    status: bool,
    message: str = "",
    data: dict | None = None
):
    return {
        "status": status,
        "message": message,
        "data": data or {}
    }
```

#### 성공 응답

```json
{
  "status": true,
  "message": "조회 성공",
  "data": {}
}
```

#### 실패 응답

```json
{
  "status": false,
  "message": "회사 정보를 찾을 수 없습니다.",
  "data": {}
}
```

#### 응답 규칙

- `status` 필드를 사용한다. (`success` 사용 금지)
- 모든 API 응답은 `ResponseModel` 기준으로 통일한다.
- HTTP Status Code는 상황에 맞게 반환한다.

```python
return JSONResponse(
    status_code=404,
    content=ResponseModel(
        status=False,
        message="데이터를 찾을 수 없습니다."
    )
)
```

#### HTTP Status Code 기준

| 상황 | Status Code |
|------|-------------|
| 성공 | 200 |
| 인증 실패 | 401 |
| 권한 없음 | 403 |
| 리소스 없음 | 404 |
| 서버 오류 | 500 |

---

### DELETE 규칙

물리 삭제를 지양하고 논리 삭제를 사용한다.

| 위치 | 표현 |
|------|------|
| DB 컬럼 | `delete_yn = '0'` (기본) / `'1'` (삭제) |
| Backend / Frontend 변수 | `isDeleted = True` |

---

### Utils 규칙

#### 허용

공통 유틸 함수만 허용한다.

```python
formatDate()
convertNumber()
generateUuid()
```

#### 금지

비즈니스 로직은 Service 계층으로 이동한다.

```python
# 금지 - utils에 작성 불가
createReport()
createSurvey()
processMateriality()
```

---

## 3. Frontend 컨벤션

### 네이밍 규칙

#### 변수 / 함수

camelCase를 사용한다.

```javascript
companyData
reportList
handleSubmit()
loadData()
```

#### 파일

PascalCase, 단수형을 사용한다.

```
Dashboard.jsx
Login.jsx
MaterialityResult.jsx
```

#### 폴더

소문자, 복수형을 사용한다.

```
components/
homes/
reports/
hooks/
```

---

### 컴포넌트 규칙

#### 공통 컴포넌트

2회 이상 재사용되는 컴포넌트는 `components/`에 위치한다.

```
components/
├── Button.jsx
├── Modal.jsx
├── PageHeader.jsx
└── DataTable.jsx
```

#### 페이지 전용 컴포넌트

특정 화면에서만 사용하는 컴포넌트는 해당 페이지 내부에 위치한다.

```
homes/reports/Result/
├── Result.jsx
├── SummaryCard.jsx
└── BenchmarkTable.jsx
```

---

### 파일 크기 규칙

| 기준 | 조치 |
|------|------|
| 300줄 이상 | 분리 검토 |
| 500줄 이상 | 분리 권장 |

분리 예시

```
Result/
├── index.jsx
├── SummarySection.jsx
├── BenchmarkSection.jsx
└── ChartSection.jsx
```

---

### Import 규칙

상대경로 사용을 최소화하고 Alias를 사용한다.

#### Alias 규칙

중분류 단위 기준으로 Alias를 정의하며, `vite.config.js` 기준으로 관리한다.

```javascript
// 권장
import ReportResult from "@reports/Result";
import PageHeader from "@components/PageHeader";
import { useAuth } from "@hooks/AuthContext";

// 비권장
import ReportResult from "../../../../homes/reports/Result";
```

#### Alias 목록

| Alias | 실제 경로 |
|-------|-----------|
| `@reports` | `src/homes/reports` |
| `@components` | `src/components` |
| `@hooks` | `src/hooks` |
| `@utils` | `src/utils` |
| `@stores` | `src/stores` |

---

## 4. 주석 규칙

**"무엇을 하는지"가 아니라 "왜 하는지"를 작성한다.**

```python
# 비권장 - 무엇을 하는지 설명
company = getCompany()

# 권장 - 왜 하는지 설명
# 외부 API 호출 비용 절감을 위해 캐시 우선 조회
company = getCompany()
```

---

## 5. 함수 작성 규칙

### 단일 책임 원칙

하나의 함수는 하나의 책임만 가진다.

```python
# 비권장 - 하나의 함수에 여러 책임
def generateReport():
    # DB 조회
    # 벡터 검색
    # LLM 호출
    # 결과 저장
    # 로그 저장
    ...

# 권장 - 책임별 분리
def getReportData(): ...
def searchContext(): ...
def generateDraft(): ...
def saveDraft(): ...
def writeLog(): ...
```

---

## 6. 아키텍처 규칙

### 순환 참조 금지

서비스, 리포지토리, 유틸 간 순환 참조를 생성하지 않는다.

금지 예시

```
reportService
 ↓
materialityService
 ↓
reportService
```

규칙

- Service ↔ Service 순환 참조 금지
- Repository ↔ Repository 순환 참조 금지
- Service ↔ Repository 순환 참조 금지

필요 시 공통 기능은 별도 모듈로 분리한다.

```
utils/
```

---

### Service 간 직접 의존 최소화

Service는 다른 Service에 대한 직접 의존을 최소화한다.

비권장

```
reportService
 ├─ surveyService
 ├─ benchmarkService
 ├─ workflowService
 └─ materialityService
```

권장

```
orchestrator
 ↓
각 Service
```

규칙

- Service는 자신의 도메인 책임에 집중한다.
- 여러 Service를 조합해야 하는 경우 Orchestrator 패턴을 우선 고려한다.
- Service 간 호출은 필요한 경우에만 최소화한다.

목적

- 결합도 감소
- 테스트 용이성 향상
- 순환 참조 방지

---

### 환경변수 접근 규칙

환경변수 접근은 `settings.py`를 통해서만 수행한다.

권장

```python
settings.dbHost
settings.redisHost
settings.apiKey
```

비권장

```python
os.getenv(...)
dotenv.get(...)
```

규칙

- 서비스 또는 비즈니스 로직 내부에서 직접 환경변수를 조회하지 않는다.
- 환경변수는 settings 객체를 통해 접근한다.
- 환경설정 관리 책임은 `settings.py`에 집중한다.

---

### 중복 코드 최소화

동일한 로직이 여러 곳에서 반복될 경우 공통화를 검토한다.

기준

- 동일 로직이 3회 이상 반복될 경우 공통 함수 또는 모듈화 검토
- 동일 Validation 로직은 공통 함수로 분리
- 동일 Response 생성 로직은 공통 함수 사용
- 동일 Repository 처리 로직은 재사용 가능한 함수로 분리

예시

```python
validateCompany(companyId)
createErrorResponse(message)
```

주의

- 과도한 추상화는 지양한다.
- 가독성과 유지보수성을 우선한다.

---

## 7. AI / RAG

### 계층 구조

```
utils/ai.py         ← AI 인프라 계층
 ↓
LLM 호출, 임베딩, 벡터 검색

services/ai/        ← AI 비즈니스 로직 계층
 ↓
보고서 생성, 워크플로우, 저장 및 상태 관리
```

### 규칙

- `utils/ai.py`는 LLM 호출, 임베딩, 벡터 검색 등 인프라 관심사만 담당한다.
- `services/ai/`는 보고서 생성 흐름, 저장, 추적 등 비즈니스 관심사만 담당한다.
- 다른 서비스는 `utils/ai.py`를 직접 호출하지 않는다.
- AI 관련 기능이 필요한 경우 `services/ai/`를 통해 접근한다.
- 안정적으로 운영 중인 구조는 불필요하게 변경하지 않는다.
- 성능 또는 유지보수 이슈가 발생할 경우에만 개선을 검토한다.

---

## 8. Batch / Scheduler 규칙

### 계층 구조

```
services/rollups/   ← 배치 처리
 ↓
airflow/dags/       ← 스케줄링 및 오케스트레이션
```

### 권장 패턴

```
create
 ↓
execute
 ↓
getStatus
```

### 규칙

- 배치 상태는 반드시 DB에 저장한다.
- 배치는 재실행 가능하도록 멱등성을 보장한다.
- 상태 조회 API를 제공한다.
- 실패 시 `FAILED` 상태를 DB에 저장한다.
- Airflow DAG는 외부 데이터 수집 및 대용량 전처리만 담당한다.
- Airflow DAG에서 서비스 레이어를 직접 호출하지 않는다.

---

## 9. Redis 규칙

Redis 접근은 `utils/rediscl.py`를 통해서만 수행한다.

### DB 파티션 기준

| DB  | 용도 |
|-----|------|
| db1 | 세션 / 토큰 |
| db2 | 비밀번호 재설정 |
| db3 | 초대 / 회사 컨텍스트 |

### 규칙

- 서비스 레이어에서 Redis 클라이언트를 직접 사용하지 않는다.
- Redis 접근 로직은 `rediscl.py`에 집중한다.
- 토큰, 비밀번호, 초대 데이터는 TTL을 반드시 설정한다.
- DB 파티션 용도를 혼용하지 않는다.
- 신규 Redis 용도 추가 시 `rediscl.py`에 전용 함수로 추가한다.

---

## 10. 리팩토링 우선순위

1. 비대해진 파일 분리
2. API → Service → Repository 계층 준수
3. Repository 분리 및 정리 (`utils/` → `repositories/`)
4. Service 의존성 정리 및 순환 참조 제거
5. 중복 코드 제거
6. Utils 남용 방지
7. Frontend 페이지 분리
8. 공통 컴포넌트 재사용
9. 컨벤션 준수 및 문서화

---

## 11. 변경 이력

## v1.3

- `delete_yn` 값 표기 정정: `'0'` → `'N'` (기본) / `'Y'` (삭제)
- 아키텍처 규칙 섹션 추가
  - 순환 참조 금지
  - Service 간 직접 의존 최소화
  - 환경변수 접근 규칙 (`settings.py` 경유)
  - 중복 코드 최소화 (3회 이상 반복 시 공통화)
- AI / RAG 계층 규칙 추가 (`utils/ai.py` vs `services/ai/` 역할 분리)
- Batch / Scheduler 규칙 추가
- Redis 규칙 추가 (`rediscl.py` 경유, DB 파티션 기준, TTL 필수)
- 리팩토링 우선순위 갱신

## v1.2

- 초기 컨벤션 정의
