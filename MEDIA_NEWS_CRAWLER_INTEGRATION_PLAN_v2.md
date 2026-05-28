# Media News Crawler Integration Plan v2

## 1. 문서 목적

본 문서는 `frontend/src/homes/reports/Media.jsx`의 미디어 분석 화면과 backend 미디어 뉴스 수집/분석 API를 연결하기 위한 MVP 설계 문서다.

이번 단계의 핵심은 reference crawler의 실제 동작 방식에 맞춰 Media MVP 범위를 고정하는 것이다. reference 기준에서는 사용자가 키워드를 자유 입력해 검색하는 구조가 아니라, `crawler_manager.py`가 `impacton.crawl`, `esgeconomy.crawl`을 고정 crawler 목록으로 실행하고 각 crawler가 정해진 언론사 페이지/섹션/목록 범위를 수집한다.

따라서 MVP에서 사용자는 프론트에서 언론사와 기간만 선택한다. 회사명, 산업명, ESG 이슈 키워드, 임의 언론사 URL, 임의 검색어는 입력받지 않는다.

## 2. MVP 미디어 언론 수집 기준 재확정

### 2.1 사용자 입력/선택

Media.jsx에서 사용자가 직접 설정하는 값은 아래 3개뿐이다.

| field | 설명 |
|---|---|
| `sources` | `impacton`, `esgeconomy` 중 선택. UI가 “언론사 추가” 형태이므로 API는 배열 구조를 유지한다. |
| `dateFrom` | 수집 희망 시작일 |
| `dateTo` | 수집 희망 종료일 |

Request DTO는 향후 언론사 확장을 고려해 `sources: List[str]` 구조로 유지한다. MVP에서는 배열이어도 허용 source는 2개뿐이다.

### 2.2 사용자 입력 금지

MVP에서는 아래 값을 사용자가 입력하지 않는다.

| 입력 금지 항목 | MVP 판단 |
|---|---|
| 회사명 키워드 | 프론트 입력 금지. backend service 상수로 자동 적용 |
| 산업 키워드 | 프론트 입력 금지. backend service 상수로 자동 적용 |
| ESG 이슈 키워드 | 프론트 입력 금지. 분석 engine이 article content를 기반으로 처리 |
| 임의 언론사 URL | MVP 제외 |
| 임의 검색어 | MVP 제외 |
| 임의 crawler selector/RSS/sitemap | MVP 제외 |

### 2.3 Backend 고정/자동 값

MVP backend는 아래 값을 자동으로 적용한다.

```python
MVP_DEMO_COMPANY_KEYWORDS = ["현대자동차"]
MVP_DEMO_INDUSTRY_KEYWORDS = ["자동차부품산업"]
MVP_ALLOWED_NEWS_SOURCES = ["impacton", "esgeconomy"]
```

`현대자동차`는 시연용 하드코딩 값이다. 다만 구현 시 service 상수로 분리해 추후 selectedCompany 또는 company profile source로 교체 가능하게 둔다.

크롤러 범위는 reference crawler의 고정 기사 섹션/목록 범위를 유지한다.

## 3. Media.jsx UX 수정 방향

현재 Media.jsx의 “수집 언론사명 / 키워드” 라벨은 MVP 동작과 맞지 않는다. MVP는 키워드 입력 방식이 아니므로 다음 방향으로 수정한다.

### 3.1 수정 전

```text
수집 언론사명 / 키워드
예: 매일경제, ESG 규제, 탄소배출
```

### 3.2 수정 후

```text
수집 언론사
[Select] 임팩트온 / ESG경제

수집 희망 기간
dateFrom ~ dateTo
```

시연용 보조 문구는 아래처럼 read-only 안내로만 표시할 수 있다.

```text
자동 적용 필터: 현대자동차 · 자동차부품산업
```

이 문구는 입력칸이 아니어야 한다. badge, caption, helper text 등 read-only UI로만 표현한다.

### 3.3 Media.jsx 변경 범위

추후 React 연동 단계에서 Media.jsx는 아래처럼 정리한다.

| 항목 | 변경 방향 |
|---|---|
| keyword input | 제거 |
| “수집 언론사명 / 키워드” 라벨 | “수집 언론사”로 변경 |
| source 선택 UI | select 또는 “언론사 추가” UX 내 source picker로 변경 |
| options | `impacton` = 임팩트온, `esgeconomy` = ESG경제 |
| 기간 입력 | `dateFrom`, `dateTo` 유지 |
| 자동 필터 안내 | `현대자동차 · 자동차부품산업` read-only 표시 가능 |

## 4. API 역할 분리

### 4.1 기존 수동 분석 API 유지

```http
POST /media/news/analyze
```

역할:

- 이미 수집된 `articles[]`를 직접 전달해 분석한다.
- smoke test, fallback, 개발자 수동 검증용 API다.
- React Media.jsx 메인 UX와 직접 연결하지 않는다.
- 기존 API는 유지한다.

### 4.2 신규 Media.jsx 메인 API

```http
POST /media/news/crawl-and-analyze
```

역할:

- Media.jsx의 언론사 선택 및 기간 입력 UX와 연결하는 MVP 메인 API다.
- 요청받은 `sources`를 source registry 기준으로 검증한다.
- `impacton`, `esgeconomy` crawler만 실행한다.
- `dateFrom`, `dateTo`로 수집 결과를 필터링한다.
- backend service 상수로 고정된 회사/산업 필터를 자동 적용한다.
- 필터링된 articles를 기존 production media analysis pipeline에 전달한다.
- DMASignal 저장, score summary 재계산, media result response 반환까지 연결한다.

외부 문서상 호출 경로는 `/api/v1/media/news/crawl-and-analyze`로 표기할 수 있다. 실제 backend router 내부에서는 `fastset.py`의 모듈명 기반 prefix 자동 부여 구조를 유지하며 `APIRouter(prefix="/media")`를 중복 선언하지 않는다.

## 5. Request DTO

`POST /media/news/crawl-and-analyze` request는 reference crawler 기준에 맞춰 단순하게 유지한다.

```json
{
  "runId": 1,
  "sources": ["impacton", "esgeconomy"],
  "dateFrom": "2024-01-01",
  "dateTo": "2025-12-31"
}
```

| field | type | required | 설명 |
|---|---|---:|---|
| `runId` | int | Y | `ESG_MATERIALITY_RUN.id` |
| `sources` | list[string] | Y | `impacton`, `esgeconomy`만 허용 |
| `dateFrom` | string | Y | 수집/필터 시작일. 기존 `TARGET_DATE`를 외부화한 값 |
| `dateTo` | string | Y | 수집/필터 종료일. production 이식 시 추가 필터로 적용 |

아래 field는 request에 넣지 않는다.

| 제외 field | 사유 |
|---|---|
| `companyKeywords` | backend service 상수 `["현대자동차"]`로 자동 적용 |
| `industryKeywords` | backend service 상수 `["자동차부품산업"]`로 자동 적용 |
| `maxArticlesPerSource` | reference crawler의 고정 범위 및 source별 내부 제한을 우선 유지 |
| `esgIssueKeywords` | MVP 제외 |
| `customUrl` | MVP 제외 |

## 6. Backend 처리 흐름

`POST /media/news/crawl-and-analyze`는 아래 순서로 처리한다.

1. `sources`가 `allowedSources`에 있는지 검증한다.
2. `impacton`, `esgeconomy` crawler만 실행한다.
3. crawler별 reference 고정 목록/섹션 범위를 유지한다.
4. `dateFrom`, `dateTo`로 수집 결과를 필터링한다.
5. article title/body/content/paragraphs 중 `companyKeywords = ["현대자동차"]` 또는 `industryKeywords = ["자동차부품산업"]` 중 하나 이상이 포함되는지 OR 조건으로 필터링한다.
6. 회사명과 산업 키워드를 모두 필수 포함해야 하는 AND 조건으로 처리하지 않는다.
7. 중복 URL을 제거한다.
8. 남은 articles를 `processMediaPipeline`에 전달한다.
9. `convertMediaToDmaSignals`를 수행한다.
10. `applyMediaBaseline`을 수행한다.
11. `scoreDmaSignals`를 수행한다.
12. `saveDmaSignals`를 수행한다.
13. `ESG_DMA_SCORE_SUMMARY`를 재계산한다.
14. media result response를 반환한다.

Pipeline 이후 처리는 기존 production media engine을 그대로 사용한다. 신규 crawler API는 crawler orchestration과 source validation을 추가하는 역할이며, scoring/aggregation 산식은 변경하지 않는다.

## 7. Source Registry 설계

MVP에서는 허용 source를 registry로 고정한다.

```python
MEDIA_NEWS_SOURCE_REGISTRY = {
    "impacton": {
        "label": "임팩트온",
        "enabled": True,
        "mvpFixedScope": True,
        "crawler": "impacton"
    },
    "esgeconomy": {
        "label": "ESG경제",
        "enabled": True,
        "mvpFixedScope": True,
        "crawler": "esgeconomy"
    }
}
```

검증 규칙:

1. 요청 `sources`가 registry에 없으면 `rejectedSources`로 반환하고 실행하지 않는다.
2. registry에 있어도 `enabled=False`이면 실행하지 않는다.
3. 한 언론사 crawler가 실패해도 다른 언론사 crawler는 계속 실행한다.
4. 허용 source가 0개이면 crawler를 실행하지 않고 graceful empty response를 반환한다.
5. 중복 source 요청은 한 번만 실행한다.
6. 임의 언론사명, 임의 URL, 임의 검색어는 registry 검증을 통과할 수 없다.

## 8. Reference 기준 이식 방식

reference 코드를 그대로 복사하지 않는다. 다만 기준 동작은 유지한다.

### 8.1 이식 대상 reference

| reference file | production 이식 기준 |
|---|---|
| `references/embadingmedia/crawler_manager.py` | crawler 목록 실행 방식, source별 rows/errors 수집 방식 |
| `references/embadingmedia/crawlers/impacton.py` | 임팩트온 URL/섹션 구조, title/date/link 수집, article body paragraph 수집 |
| `references/embadingmedia/crawlers/esgeconomy.py` | ESG경제 목록/본문 구조, paragraph 수집 |

### 8.2 impacton 기준

reference `impacton.py`는 `TARGET_DATE`, `MAX_PAGE`, `sc_sub_section_code=S2N14`가 코드 안에 고정되어 있다.

MVP production 이식 기준:

- 임팩트온 URL/섹션 구조를 유지한다.
- `sc_sub_section_code=S2N14` 기반 고정 섹션 수집 방식을 유지한다.
- `MAX_PAGE` 등 crawler 내부 안전 제한은 유지할 수 있다.
- `TARGET_DATE`는 `dateFrom`으로 외부화한다.
- `dateTo` 필터를 추가한다.
- keyword search crawler로 바꾸지 않는다.

### 8.3 esgeconomy 기준

reference `esgeconomy.py`는 `TARGET_DATE` 기준으로 목록 페이지를 순회하고, 기준일 이전 기사에 도달하면 중단한다.

MVP production 이식 기준:

- ESG경제 목록/본문 구조를 유지한다.
- 목록 페이지 순회 방식과 본문 paragraph 수집 방식을 유지한다.
- `TARGET_DATE`는 `dateFrom`으로 외부화한다.
- 기준일 이전 기사 도달 시 중단하는 동작은 유지한다.
- `dateTo` 필터를 추가한다.
- keyword search crawler로 바꾸지 않는다.

## 9. Production 파일 구조

production으로 옮길 위치는 아래와 같다.

```text
backend/src/models/media.py
backend/src/apis/media.py
backend/src/services/medias/service.py
backend/src/services/medias/crawler.py
backend/src/services/medias/crawlers/base.py
backend/src/services/medias/crawlers/impacton.py
backend/src/services/medias/crawlers/esgeconomy.py
```

| file | 역할 |
|---|---|
| `backend/src/models/media.py` | `MediaNewsCrawlAnalyzeRequest`, response DTO, sourceBreakdown DTO |
| `backend/src/apis/media.py` | `/news/analyze`, `/news/crawl-and-analyze` endpoint. router thin layer만 담당 |
| `backend/src/services/medias/service.py` | crawler 결과를 existing media pipeline, scoring, repository로 연결 |
| `backend/src/services/medias/crawler.py` | source registry 검증, source별 crawler 실행, dedup, partial success response 조립 |
| `backend/src/services/medias/crawlers/base.py` | crawler interface, normalized article DTO |
| `backend/src/services/medias/crawlers/impacton.py` | 임팩트온 fixed scope crawler |
| `backend/src/services/medias/crawlers/esgeconomy.py` | ESG경제 fixed scope crawler |

## 10. Response DTO

`POST /media/news/crawl-and-analyze` response 초안은 아래와 같다.

```json
{
  "runId": 1,
  "requestedSources": ["impacton", "esgeconomy"],
  "allowedSources": ["impacton", "esgeconomy"],
  "rejectedSources": [],
  "companyKeywords": ["현대자동차"],
  "industryKeywords": ["자동차부품산업"],
  "keywordSource": "MVP_SERVICE_CONSTANT",
  "collectedArticleCount": 78,
  "filteredArticleCount": 78,
  "savedSignalCount": 120,
  "observedSubIssueCount": 19,
  "sourceBreakdown": [
    {
      "sourceKey": "impacton",
      "sourceLabel": "임팩트온",
      "requestedYn": true,
      "executedYn": true,
      "collectedCount": 38,
      "filteredCount": 38,
      "savedSignalCount": 59,
      "status": "SUCCESS",
      "errorMessage": null
    },
    {
      "sourceKey": "esgeconomy",
      "sourceLabel": "ESG경제",
      "requestedYn": true,
      "executedYn": true,
      "collectedCount": 40,
      "filteredCount": 40,
      "savedSignalCount": 61,
      "status": "SUCCESS",
      "errorMessage": null
    }
  ],
  "topIssues": [],
  "coverage": {},
  "errors": []
}
```

### 10.1 `sourceBreakdown[]`

각 source별 breakdown은 아래 field를 포함한다.

| field | type | 설명 |
|---|---|---|
| `sourceKey` | string | `impacton`, `esgeconomy` |
| `sourceLabel` | string | 화면 표시명 |
| `requestedYn` | bool | 사용자가 요청한 source인지 여부 |
| `executedYn` | bool | 실제 crawler를 실행했는지 여부 |
| `collectedCount` | int | crawler가 수집한 article count |
| `filteredCount` | int | date/company/industry/dedup 이후 남은 article count |
| `savedSignalCount` | int | 저장된 media signal count |
| `status` | string | `SUCCESS`, `PARTIAL_FAILED`, `FAILED`, `SKIPPED` |
| `errorMessage` | string/null | source별 실패 사유. 성공 시 null |

`status` 기준:

| status | 의미 |
|---|---|
| `SUCCESS` | crawler 실행, 필터링, pipeline 저장까지 정상 완료 |
| `PARTIAL_FAILED` | crawler는 일부 결과를 만들었으나 본문 일부 실패, 일부 저장 실패 등 복구 가능한 부분 실패 |
| `FAILED` | source crawler 실행 또는 pipeline 처리 실패 |
| `SKIPPED` | registry 미등록, disabled, 중복 요청, 허용 source 없음 등으로 실행하지 않음 |

### 10.2 `rejectedSources[]`

```json
{
  "sourceKey": "unknown_source",
  "reason": "NOT_REGISTERED",
  "message": "MVP allows only impacton and esgeconomy."
}
```

`reason` 예시:

| reason | 의미 |
|---|---|
| `NOT_REGISTERED` | registry에 없는 source |
| `DISABLED` | registry에는 있으나 enabled=False |
| `DUPLICATE_REQUEST` | 중복 요청 source |

### 10.3 `errors[]`

source별 실패는 전체 API 실패로 올리지 않고 `errors[]` 및 `sourceBreakdown[].status`로 표현한다.

```json
{
  "sourceKey": "impacton",
  "message": "crawler timeout",
  "recoverableYn": true
}
```

## 11. Article Normalization

source crawler는 각자 사이트 구조를 처리하되 service에 반환하는 article shape은 통일한다.

```json
{
  "sourceType": "news",
  "sourceKey": "impacton",
  "sourceLabel": "임팩트온",
  "title": "기사 제목",
  "url": "https://www.impacton.net/...",
  "publishedAt": "2025-01-15",
  "content": "기사 본문 전체 또는 paragraph 결합 텍스트",
  "paragraphs": [
    "본문 paragraph 1",
    "본문 paragraph 2"
  ]
}
```

기존 media pipeline이 요구하는 `articles[]` 입력 형태가 다를 경우 `services/medias/service.py`에서 pipeline 입력 형태로 변환한다.

## 12. Dedup 및 필터 정책

### 12.1 Date filter

- `dateFrom`과 `dateTo`는 crawler URL 검색 조건이 아니다.
- reference crawler의 fixed section/list crawling 구조를 유지한다.
- 각 article의 `publishedAt` 또는 원본 date text를 파싱한 뒤 `dateFrom <= articleDate <= dateTo` 기준으로 수집 후 필터링한다.
- 날짜 파싱 실패 article은 MVP에서는 제외하고, source별 `errorMessage` 또는 `errors[]`에 count를 남긴다.
- `dateFrom`은 기존 reference의 `TARGET_DATE` 역할을 대체하되, 임의 검색 쿼리 파라미터로 쓰지 않는다.

### 12.2 Company/industry filter

- `companyKeywords = ["현대자동차"]`를 backend에서 자동 적용한다.
- `industryKeywords = ["자동차부품산업"]`를 backend에서 자동 적용한다.
- 이 값은 프론트에서 받지 않는다.
- 구현 시 service 상수로 분리해 추후 company profile 기반으로 교체 가능하게 둔다.
- article title/body/content/paragraphs 중 회사명 또는 산업 키워드 중 하나 이상 포함되면 통과시킨다.
- 회사명과 산업 키워드를 모두 반드시 포함해야 하는 조건으로 만들지 않는다.
- ESG subIssue 관련성은 이후 `processMediaPipeline`에서 `subissuemaster.py` 기준으로 판단한다.

### 12.3 URL dedup

중복 제거 기준은 URL이다.

1. URL trim
2. fragment 제거
3. trailing slash 정리
4. 같은 URL이 여러 source에서 수집되면 먼저 성공한 source를 유지
5. title/content가 같아도 URL이 다르면 MVP에서는 별도 기사로 본다

## 13. 부분 성공 응답 정책

API는 source별 부분 성공을 허용한다.

예:

- `impacton`: SUCCESS, 38건 수집
- `esgeconomy`: FAILED, timeout
- 전체 response: HTTP 200
- `errors[]`에 ESG경제 실패 기록
- `sourceBreakdown[].status`로 source별 상태 표시

HTTP 500은 registry 검증 실패나 개별 crawler 실패가 아니라 API 자체가 response를 만들 수 없는 예외에만 사용한다.

기사 0건인 경우에도 graceful empty response를 반환한다.

```json
{
  "runId": 1,
  "requestedSources": ["impacton"],
  "allowedSources": ["impacton"],
  "rejectedSources": [],
  "collectedArticleCount": 0,
  "filteredArticleCount": 0,
  "savedSignalCount": 0,
  "observedSubIssueCount": 0,
  "sourceBreakdown": [
    {
      "sourceKey": "impacton",
      "sourceLabel": "임팩트온",
      "requestedYn": true,
      "executedYn": true,
      "collectedCount": 0,
      "filteredCount": 0,
      "savedSignalCount": 0,
      "status": "SUCCESS",
      "errorMessage": null
    }
  ],
  "topIssues": [],
  "coverage": {},
  "errors": []
}
```

## 14. Frontend 연결 필드

Media.jsx에서 사용할 field는 아래와 같다.

| UI 목적 | API/field |
|---|---|
| 선택 가능한 언론사 목록 | MVP frontend 상수 또는 추후 `GET /media/news/sources` |
| 사용자가 추가/선택한 언론사 | request `sources[]` |
| 수집 희망 기간 | request `dateFrom`, `dateTo` |
| source 표시명 | registry label, response `sourceBreakdown[].sourceLabel` |
| source별 실행 여부 | `sourceBreakdown[].executedYn` |
| source별 상태 | `sourceBreakdown[].status` |
| source별 오류 | `sourceBreakdown[].errorMessage` |
| source별 수집 건수 | `sourceBreakdown[].collectedCount` |
| source별 필터 후 건수 | `sourceBreakdown[].filteredCount` |
| source별 저장 signal 수 | `sourceBreakdown[].savedSignalCount` |
| 자동 적용 필터 안내 | response `companyKeywords`, `industryKeywords`, `keywordSource` 또는 frontend 상수 |
| 전체 수집/저장 요약 | `collectedArticleCount`, `filteredArticleCount`, `savedSignalCount`, `observedSubIssueCount` |
| 결과 Top Issues | `topIssues[]` |

## 15. MVP 제외 범위

아래 항목은 MVP에서 구현하지 않는다.

- 임의 언론사명 입력 후 동적 crawler 생성
- 임의 URL 입력 후 crawling
- 사용자 키워드 검색 기반 crawling
- 회사명/산업명/ESG 이슈 키워드 프론트 입력
- source registry 관리자 UI
- regulation/agency source의 실제 crawler 본구현
- 유료 매체/로그인 필요 매체 crawling
- reference crawler의 무비판적 복사
- 대규모 crawl scheduling, queue, retry dashboard

## 16. 구현 우선순위

최종 구현 순서는 아래와 같다.

1. `MEDIA_NEWS_CRAWLER_INTEGRATION_PLAN_v1.md` 수정
2. `backend/src/models/media.py` 생성
3. source registry 추가
4. production crawler `impacton`, `esgeconomy` 이식
5. `POST /media/news/crawl-and-analyze` 추가
6. service에서 crawler → existing pipeline 연결
7. Media.jsx 라벨/input/select 수정
8. smoke test

## 17. Smoke Test 기준

### 17.1 정상 요청

```json
{
  "runId": 1,
  "sources": ["impacton", "esgeconomy"],
  "dateFrom": "2024-01-01",
  "dateTo": "2025-12-31"
}
```

기대:

- `requestedSources`에 2개 source 포함
- `allowedSources`에 2개 source 포함
- `rejectedSources` 빈 배열
- 각 sourceBreakdown에 `requestedYn=true`
- crawler 성공 시 `executedYn=true`
- `companyKeywords=["현대자동차"]`
- `industryKeywords=["자동차부품산업"]`
- `keywordSource="MVP_SERVICE_CONSTANT"`

### 17.2 허용되지 않은 source

```json
{
  "runId": 1,
  "sources": ["unknown_press"],
  "dateFrom": "2024-01-01",
  "dateTo": "2025-12-31"
}
```

기대:

- `allowedSources=[]`
- `rejectedSources[0].reason="NOT_REGISTERED"`
- crawler 미실행
- graceful empty response

### 17.3 한 source 실패

기대:

- 성공 source는 저장 및 score 재계산까지 진행
- 실패 source는 `sourceBreakdown[].status="FAILED"` 또는 `PARTIAL_FAILED`
- 전체 API는 가능한 경우 HTTP 200
- `errors[]`에 source별 오류 포함

## 18. Open Questions

| id | 질문 | 권장 결정 |
|---|---|---|
| Q-001 | Media.jsx에서 source를 단일 선택으로 제한할지, 다중 선택/추가 UX로 둘지? | “언론사 추가” UX를 유지하려면 배열 기반 다중 선택 유지 |
| Q-002 | `GET /media/news/sources`가 필요한가? | MVP 초기는 frontend 상수 가능. backend registry와 동기화하려면 후속 추가 |
| Q-003 | Selenium/브라우저 런타임이 필요한 source가 있는가? | crawler 이식 시 확인. 서버 배포 환경 제약 검토 필요 |
| Q-004 | company/industry filter를 article title+body에 단순 포함으로 볼지, pipeline evidence 단계로 넘길지? | MVP는 service-level 단순 필터 우선, 필요 시 pipeline evidence와 결합 |
| Q-005 | `MAX_PAGE` 같은 crawler 내부 제한을 request로 열 것인가? | MVP에서는 열지 않음. reference fixed scope 유지 |

## 19. 최종 판단

이번 MVP 목표는 아래로 고정한다.

- 사용자는 프론트에서 언론사와 기간만 선택한다.
- 언론사는 `impacton`, `esgeconomy` 2개만 선택 가능하다.
- 백엔드는 `현대자동차`, `자동차부품산업` 필터를 자동 적용한다.
- 크롤러는 reference의 고정 기사 범위만 수집한다.
- 수집 결과를 기존 media 분석 엔진에 넘겨 점수화, DB 저장, 결과 조회까지 연결한다.

이 방식이 현재 Media.jsx의 UX 의도, reference crawler 구조, MVP 시연 범위를 가장 일관되게 맞춘다.
