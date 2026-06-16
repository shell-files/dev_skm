# 기술 스택 및 용어집 (Tech Glossary)
> SKM ESG 지속가능경영 플랫폼 | 포트폴리오 첨부용

---

## 📋 기술 스택 요약표

| 카테고리 | 기술 | 버전 | 한 줄 정의 |
|---|---|---|---|
| Frontend | React | 19.2.0 | 화면을 컴포넌트 단위로 쪼개어 효율적으로 관리하는 UI 라이브러리 |
| Frontend | Redux Toolkit | 2.12.0 | 여러 화면이 공유해야 하는 데이터를 한 곳에서 통일적으로 관리하는 상태관리 도구 |
| Frontend | React Router | 7.15.0 | 페이지 이동(URL 라우팅)을 새로고침 없이 처리하는 SPA 라우팅 라이브러리 |
| Frontend | Vite | 7.2.4 | 개발 서버 구동·빌드를 매우 빠르게 처리하는 프론트엔드 빌드 도구 |
| Frontend | Axios | 1.16.0 | 백엔드 API와 HTTP 통신을 간편하게 처리하는 클라이언트 라이브러리 |
| Frontend | Chart.js / Recharts | 4.5.1 / 3.8.1 | 데이터를 막대·선·원 그래프로 시각화하는 차트 라이브러리 |
| Frontend | Bootstrap | 5.3.8 | 버튼·카드·레이아웃 등 UI 구성 요소를 빠르게 구현하는 CSS 프레임워크 |
| Frontend | SweetAlert2 | 11.26.24 | 팝업·알림·확인 다이얼로그를 미려하게 표시하는 알림 라이브러리 |
| Frontend | docx / jspdf / pptxgenjs | 9.7.1 / 4.2.1 / 4.0.1 | 브라우저에서 Word·PDF·PPT 파일을 직접 생성·다운로드하는 문서 출력 라이브러리 |
| Frontend | xlsx (SheetJS) | latest | 엑셀 파일을 읽고 쓰는 스프레드시트 파싱 라이브러리 |
| Backend | FastAPI | 0.136.1+ | 파이썬으로 빠르게 REST API 서버를 만드는 고성능 웹 프레임워크 |
| Backend | Uvicorn | 0.47.0+ | FastAPI 애플리케이션을 실제 서버에서 실행시키는 ASGI 서버 |
| Backend | Pydantic Settings | 2.14.0+ | 환경변수·설정값을 타입 안전하게 불러오고 검증하는 설정 관리 라이브러리 |
| Backend | jwcrypto | 1.5.7+ | RSA 공개키/개인키 기반으로 토큰을 암호화·복호화하는 JWE 보안 라이브러리 |
| Backend | fastapi-mail | 1.6.2+ | FastAPI에서 이메일을 발송하는 메일 전송 라이브러리 |
| Backend | PyMuPDF / pypdf | 1.27+ / 6.11+ | PDF 파일을 읽고 텍스트를 추출하는 문서 파싱 라이브러리 |
| Backend | Prometheus Instrumentator | 7.1.0+ | API 요청 수·응답 시간 등 서버 성능 지표를 자동 수집·모니터링하는 도구 |
| Database & Cache | MariaDB | 1.1.14 (driver) | 관계형 데이터베이스. 사용자·회사·온보딩·보고서 등 핵심 업무 데이터 저장 |
| Database & Cache | PostgreSQL + pgvector | 3.3.4 (driver) | 벡터 검색을 지원하는 관계형 DB. AI 보고서 생성용 문서 임베딩 저장 |
| Database & Cache | Redis | 7.4.0+ (client) | 메모리 기반 초고속 저장소. 세션 토큰·임시 비밀번호·초대 링크 토큰 관리 |
| Data Pipeline & AI | Apache Kafka | 2.3.1+ (python) | 서버 간 메시지를 비동기로 전달하는 분산 메시지 큐. 이메일 발송 파이프라인 처리 |
| Data Pipeline & AI | Google Gemini API | 2.4.0+ | 구글의 멀티모달 대형언어모델. PDF 문서를 업로드 후 ESG 이슈 추출 |
| Data Pipeline & AI | Ollama (LangChain) | 0.6.2+ / 1.1.0+ | 로컬 서버에서 LLM을 실행하는 오픈소스 플랫폼. ESG 보고서 문단 생성 |
| Data Pipeline & AI | Sentence Transformers | 5.5.1+ | 텍스트를 벡터(숫자 배열)로 변환하는 임베딩 모델. ESG 이슈 유사도 검색 |
| Data Pipeline & AI | scikit-learn | 1.8.0+ | 머신러닝 알고리즘 라이브러리. DMA(이중중대성평가) 점수 산정 계산에 활용 |
| Data Pipeline & AI | tiktoken | 0.7.0+ | LLM에 보낼 텍스트의 토큰 수를 계산·제한하는 토크나이저 |
| Infrastructure & DevOps | Vite Proxy | - | 개발 환경에서 CORS 문제 없이 백엔드 API를 호출하도록 중계하는 프록시 설정 |
| Security & Auth | JWE (RSA-OAEP + A256GCM) | - | RSA 공개키로 암호화한 토큰. 사용자 세션 정보를 안전하게 보호 |
| Security & Auth | HttpOnly Cookie | - | 자바스크립트로 접근 불가한 쿠키에 토큰을 저장해 XSS 공격을 차단하는 보안 방식 |
| Security & Auth | pydantic-settings (.env) | 2.14.0+ | DB 비밀번호·API 키 등 민감 정보를 코드 외부(.env)에서 관리하는 환경변수 설정 |

---

## 🖥️ Frontend

### React 19.2.0
**한 줄 정의**: 화면을 독립적인 컴포넌트 단위로 만들어 재사용성과 유지보수를 높이는 UI 라이브러리

- **실제 활용**: `OnBoard.jsx`(데이터 입력 온보딩), `BenchMarking.jsx`(벤치마킹 분석), `Media.jsx`(미디어 분석), `Dashboard.jsx`(메인 대시보드) 등 플랫폼의 모든 화면이 React 함수형 컴포넌트로 구성. `useState`, `useEffect`, `useCallback`, `useMemo` 등 Hooks 패턴을 전면 사용
- **도입 배경**: ESG 보고서 작성 플랫폼 특성상 온보딩, 롤업(자회사 데이터 취합), DMA(이중중대성평가), 보고서 생성 등 복잡한 다단계 워크플로우 UI가 필요. 컴포넌트 분리로 `OnboardingModalShell`, `MetricAssignmentModal`, `RollupSummaryPanel` 같은 모달·패널을 독립적으로 관리하여 개발 효율을 높임
- **효과**: 동일 UI 요소(`PageHeader`, `ServiceAlert` 등)를 여러 페이지에서 재사용. 화면 상태와 비즈니스 로직이 분리되어 유지보수 용이

---

### Redux Toolkit (@reduxjs/toolkit) 2.12.0
**한 줄 정의**: 여러 페이지에서 공유해야 하는 데이터(사용자 정보, 보고서 진행상태 등)를 전역에서 한 번에 관리하는 상태관리 도구

- **실제 활용**:
  - `authSlice.js`: 로그인·로그아웃, 선택된 회사(`selectedCompany`), 사용자 이름·이메일을 전역 관리. `loginUser`, `logoutUser`, `checkUser` 비동기 액션으로 세션 상태 일관 처리
  - `reportSlice.js`: 보고서 워크플로우 단계(`workflow.current`), 온보딩 지표(`onboarding.metrics`), 자회사 롤업 배치 상태(`rollup.activeBatchId`), 벤치마킹·미디어 분석 진행상태(`dmaStages.benchmark`, `dmaStages.media`)를 모두 Redux 단일 store에서 관리
  - `BenchMarking.jsx`와 `Media.jsx`에서 `useSelector(selectCanRunDmaStage)`로 DMA 단계 진입 가능 여부를 판단하고, `useDispatch`로 `runBenchmarkAnalysis`, `runMediaCrawlAndAnalyze` thunk를 실행
- **도입 배경**: 온보딩 → 롤업 → DMA → 보고서 생성까지 약 10단계 이상의 워크플로우가 여러 페이지를 가로질러 진행됨. `createAsyncThunk`로 비동기 API 호출의 pending/fulfilled/rejected 상태를 일관성 있게 처리하고, `loading`·`error` 객체를 슬라이스 내부에 통합하여 중복 코드 제거
- **효과**: 30개 이상의 비동기 액션(`fetchCurrentWorkflow`, `saveOnboardingMetric`, `createRollupBatch` 등)을 단일 파일(`reportSlice.js`)에서 체계적으로 관리. 컴포넌트는 API 호출 로직 없이 dispatch만 호출하여 관심사 분리 달성

---

### React Router 7.15.0
**한 줄 정의**: 페이지 전환 시 새로고침 없이 URL을 바꾸고 원하는 컴포넌트를 표시하는 SPA 라우팅 라이브러리

- **실제 활용**: `App.jsx`에서 `/dashboard`, `/onb`(온보딩), `/benchmk`(벤치마킹), `/media`(미디어 분석), `/result`, `/draft` 등 플랫폼 전 페이지의 URL 매핑 관리. `BenchMarking.jsx`·`Media.jsx` 내부의 단계 네비게이션에서 `useNavigate` 훅으로 분석 완료 후 자동 이동 구현
- **도입 배경**: 로그인 → 회사 선택 → 대시보드 → 온보딩 → DMA → 보고서 생성의 다단계 흐름을 페이지 새로고침 없이 매끄럽게 연결하기 위해 도입

---

### Vite 7.2.4
**한 줄 정의**: 개발 중 코드 수정 사항을 즉각 반영하고, 배포용 번들을 빠르게 만드는 프론트엔드 빌드 도구

- **실제 활용**: `vite.config.js`에서 `/api` 경로를 `http://main.weareithero.cloud` 백엔드로 프록시 설정. `@stores`, `@components`, `@reports`, `@hooks` 등 8개 경로 별칭(alias)을 등록하여 컴포넌트 간 import 경로를 단순화
- **도입 배경**: 개발 서버를 `0.0.0.0:80`으로 바인딩하여 팀 개발 환경에서 외부 접속 허용. 프록시 설정으로 CORS 문제 없이 백엔드 API 호출

---

### Axios 1.16.0
**한 줄 정의**: 백엔드 API와 HTTP 통신(GET/POST/PUT/PATCH/DELETE)을 간편하게 처리하는 비동기 통신 라이브러리

- **실제 활용**: `frontend/src/utils/Network.js`에서 `GET`, `POST`, `POST_FORM`, `PUT`, `PATCH`, `DELETE` 함수를 Axios 기반으로 공통 래핑. `reportSlice.js`의 모든 thunk에서 이 함수들을 호출하며, `authSlice.js`에서도 로그인·로그아웃 API 호출에 사용

---

### Chart.js 4.5.1 / Recharts 3.8.1
**한 줄 정의**: 데이터를 막대·선·원 등 차트로 시각화하는 그래프 라이브러리

- **실제 활용**: `BenchMarking.jsx`의 벤치마킹 결과 대시보드(리더/피어/자사 보고서 비교 차트, 공통 이슈 매트릭스)와 `Media.jsx`의 미디어 분석 결과(언론 기사·전문기관·규제 소스별 이슈 분포)를 시각화

---

### docx / jspdf / pptxgenjs 문서 출력 라이브러리
**한 줄 정의**: 서버 없이 브라우저에서 직접 Word·PDF·PPT 파일을 생성하고 다운로드하는 문서 출력 도구

- **실제 활용**: `Draft.jsx`(보고서 초안 화면)에서 AI가 생성한 ESG 보고서 내용을 Word 문서(.docx), PDF, PowerPoint 형식으로 내보내는 기능 구현. `html2canvas`와 결합하여 차트·테이블이 포함된 화면을 이미지로 캡처하여 PDF에 삽입
- **도입 배경**: 최종 보고서를 사용자가 즉시 기업 내부 문서로 활용할 수 있도록 다양한 포맷 지원이 필요

---

### SweetAlert2 11.26.24
**한 줄 정의**: 기본 브라우저 alert 창 대신 디자인이 적용된 팝업·확인 다이얼로그를 표시하는 알림 라이브러리

- **실제 활용**: `components/UI/ServiceAlert.jsx`의 `showDefaultAlert`, `showConfirmAlert` 함수로 공통 래핑하여 온보딩 저장 성공/실패, 벤치마킹 분석 시작 확인, 로그인 실패 등 플랫폼 전반의 알림에 사용

---

## ⚙️ Backend

### FastAPI 0.136.1+
**한 줄 정의**: 파이썬으로 빠르게 REST API 서버를 만들 수 있는 고성능 웹 프레임워크

- **실제 활용**: `backend/src/apis/` 디렉토리 아래 `ai.py`(보고서 생성), `benchmk.py`(벤치마킹), `media.py`(미디어 분석), `onboarding.py`(온보딩), `rollup.py`(롤업/자회사 데이터 취합), `auth.py`(인증), `survey.py`(설문) 등 20개 이상의 API Router로 기능을 분리 구성. `api.py`에서 API v1 라우터를 통합 등록
- **도입 배경**: Pydantic 모델 기반의 자동 입력 유효성 검사, `Depends(get_token)`을 통한 의존성 주입 방식의 인증 미들웨어, `async def` 비동기 엔드포인트 지원 등이 ESG 플랫폼 구축에 적합
- **효과**: `@router.post("")` 데코레이터 하나로 API 등록부터 문서화(Swagger)까지 자동화. 인증이 필요한 모든 엔드포인트에 `token=Depends(get_token)` 하나만 추가하면 인증 처리 완료

---

### Uvicorn 0.47.0+
**한 줄 정의**: FastAPI 서버를 실제로 구동시키는 ASGI(비동기 웹) 서버

- **실제 활용**: 프로덕션 환경(`skm.weareithero.cloud`)에서 FastAPI 애플리케이션을 실행하는 서버 런타임. Kafka 컨슈머 스레드 시작(`startConsumer()`) 등 서버 시작 시 초기화 로직과 함께 동작

---

### Pydantic Settings 2.14.0+
**한 줄 정의**: 환경변수(.env 파일)를 파이썬 타입 안전 객체로 불러와 설정을 중앙에서 관리하는 라이브러리

- **실제 활용**: `backend/src/utils/settings.py`의 `Settings` 클래스에서 DB 접속 정보(`maria_db_host`, `pg_db_host`), Redis 설정(`redis_host`, `redis_port`), Kafka 서버 주소(`kafka_server`), Gemini/Ollama API 키, JWT 토큰 만료 시간(`access_token_expire_minutes`, `refresh_token_expire_days`) 등 모든 민감 설정값을 `.env` 파일에서 읽어 타입 검증 후 주입
- **효과**: `settings.maria_db_host`처럼 어디서든 단일 `settings` 객체로 접근. 코드에 비밀번호·API키가 하드코딩될 위험 제거

---

## 🗄️ Database & Cache

### MariaDB (mariadb 1.1.14 드라이버)
**한 줄 정의**: 기업 업무 데이터를 테이블 형태로 저장하는 관계형 데이터베이스

- **실제 활용**: `backend/src/utils/db.py`에서 `findOne`, `findAll`, `save`, `saveMany`, `executeTransaction`, `getPageList` 등 범용 쿼리 함수로 추상화하여 전 서비스에서 사용. 사용자(USER), 회사(COMPANY), ESG KPI 실적(ESG_KPI_FACT), AI 보고서 실행 이력(ESG_REPORT_AI_RUN/SECTION), 토큰(TOKEN), 온보딩 지표, 롤업 결과(ESG_GROUP_ROLLUP_RESULT) 등 핵심 업무 데이터 저장. AES 암호화 함수(`aes_d`)를 SQL 내에서 직접 호출하여 회사명 등 민감 데이터를 DB 레벨에서 복호화
- **도입 배경**: MySQL 호환 오픈소스 RDBMS로 복잡한 ESG 지표·보고서 워크플로우의 관계형 데이터 모델링에 적합. `executeTransaction`으로 다단계 승인·롤업 처리를 원자적으로 보장

---

### PostgreSQL + pgvector (psycopg 3.3.4 + pgvector 0.4.2)
**한 줄 정의**: 일반 데이터베이스에 벡터(숫자 배열) 검색 기능을 추가한 AI용 특수 데이터베이스

- **실제 활용**: `backend/src/utils/ai.py`의 `searchSrKnowledgeHybrid()` 함수에서 Sentence Transformer로 변환한 ESG 이슈 쿼리 벡터를 PostgreSQL의 `ai_sr` 테이블에 저장된 과거 지속가능경영보고서(SR) 임베딩과 코사인 유사도(`<=>` 연산자)로 비교하여 가장 관련성 높은 보고서 문단을 검색. LLM 보고서 생성 시 참조 컨텍스트로 활용
- **도입 배경**: "기후목표·전환계획" 같은 ESG 이슈와 유사한 기존 보고서 문단을 키워드 검색이 아닌 의미 기반으로 찾아야 하므로 벡터 검색 필요. pgvector 확장으로 PostgreSQL 단일 인프라에서 구현

---

### Redis (redis 7.4.0+ 클라이언트)
**한 줄 정의**: 메모리에 데이터를 저장하는 초고속 임시 저장소. 세션·캐시·임시 데이터 관리에 사용

- **실제 활용**: `backend/src/utils/rediscl.py`에서 3개의 DB(db1/db2/db3)를 용도별로 분리 운영
  - `client1` (db1): 로그인 세션 토큰(UUID → JWE 암호화 액세스 토큰) 저장/조회/삭제, 토큰 갱신 시 구 UUID → 신 UUID 매핑(`rotated:` 키) 30초 임시 보관으로 동시 요청 Race Condition 방지
  - `client2` (db2): 비밀번호 초기화 시 발급한 임시 비밀번호(tempPwd → email) 매핑 저장
  - `client3` (db3): 선택된 회사 ID(UUID → companyId) 및 초대 링크 토큰 저장, 만료 시간(`ex=expireSeconds`) 설정으로 링크 자동 만료
- **도입 배경**: 세션 토큰을 DB에 저장하면 매 API 요청마다 DB 조회가 발생하여 성능 저하. Redis는 메모리 접근이므로 수 ms 이내 응답 가능. 토큰 갱신 시 짧은 유예 기간(30초) 로직도 Redis TTL로 간단히 구현

---

## 🤖 Data Pipeline & AI

### Apache Kafka (kafka-python 2.3.1+)
**한 줄 정의**: 서비스 간에 메시지를 비동기로 주고받는 분산 메시지 큐. "주문서를 편지함에 넣으면 담당자가 꺼내서 처리"하는 구조

- **실제 활용**: `backend/src/utils/kafkasv.py`에서 이메일 발송 파이프라인 구현
  - **Producer**: `sendToKafka(data)` 함수로 사내 직원 초대, 컨설턴트 초대, 임시 비밀번호 발송, 협력사 초대 등 4가지 타입의 이메일 발송 요청을 Kafka 토픽에 발행
  - **Consumer**: `runEmailConsumer()`가 별도 데몬 스레드(`startConsumer()`)로 실행되어 Kafka 메시지를 구독하고, `handleEmailJob()`에서 `fastapi-mail`을 통해 실제 이메일 발송 처리
- **도입 배경**: 회원 초대·임시 비밀번호 발송은 이메일 서버 응답을 기다릴 필요가 없는 비동기 처리가 적합. API 서버는 Kafka에 메시지를 넣고 즉시 응답을 반환하며, 이메일 발송은 백그라운드 컨슈머가 독립적으로 처리하여 API 응답 속도 향상

---

### Google Gemini API (google-genai 2.4.0+)
**한 줄 정의**: 구글의 멀티모달 대형언어모델 API. PDF 문서를 직접 이해하고 정보를 추출할 수 있음

- **실제 활용**: `backend/src/utils/ocrai.py`에서 벤치마킹 단계의 PDF 분석에 사용. 경쟁사 및 자사의 ESG 보고서 PDF를 Gemini File API로 업로드한 후, DMA 컨설턴트 역할 프롬프트로 5~15개의 핵심 ESG 이슈를 JSON 형태로 추출. 비동기 세마포어(`asyncio.Semaphore`)로 동시 처리 건수를 제한하고, 최대 3회 재시도 로직으로 안정성 확보. 여러 API 키를 순환하여 할당량(Rate Limit) 초과 방지
- **도입 배경**: 벤치마킹 분석에서 리더·피어·자사 보고서 PDF를 사람이 직접 읽지 않고 AI가 자동으로 ESG 이슈를 추출해야 하는 요구사항. PDF를 텍스트로 추출 후 처리하는 방식보다 멀티모달 모델이 레이아웃·표·이미지를 함께 이해하여 정확도 향상

---

### Ollama + LangChain-Ollama (ollama 0.6.2+ / langchain-ollama 1.1.0+)
**한 줄 정의**: 인터넷 없이 자체 서버에서 오픈소스 LLM(대형언어모델)을 실행하는 플랫폼

- **실제 활용**: `backend/src/utils/ai.py`에서 ESG 보고서 본문 문단 생성에 사용. `ChatOllama(model="gemma4:e4b")`로 로컬 Ollama 서버에 연결하고, `ChatPromptTemplate`으로 구성한 프롬프트(ESG 컨설턴트 시스템 역할, KPI 수치가 채워진 템플릿, 과거 SR 참고 컨텍스트)를 LangChain 체인(`prompt | llm | StrOutputParser()`)으로 실행하여 보고서 문단 1개를 생성. 생성된 문단은 DB(ESG_REPORT_AI_SECTION)에 저장
- **도입 배경**: 기업 ESG 데이터(KPI 수치, 회사명 등 민감 정보)를 외부 API로 보내지 않고 내부 서버에서 처리하기 위해 로컬 LLM 채택. LangChain으로 프롬프트 템플릿과 LLM 호출을 체이닝하여 코드 가독성 향상

---

### Sentence Transformers (sentence-transformers 5.5.1+)
**한 줄 정의**: 문장의 의미를 숫자 벡터로 변환하여 비슷한 의미의 문장을 찾아내는 AI 임베딩 모델

- **실제 활용**:
  - `backend/src/utils/ai.py`: `SentenceTransformer("snunlp/KR-SBERT-V40K-klueNLI-augSTS")` 한국어 SBERT 모델로 ESG 이슈명을 벡터로 변환하고, PostgreSQL pgvector로 과거 SR 문서와 하이브리드 유사도 검색 수행
  - `backend/src/services/medias/pipeline.py`: 미디어 크롤링으로 수집한 뉴스 기사 텍스트를 청크로 나눠 ESG 서브이슈 마스터 벡터와 코사인 유사도 비교하여 관련 ESG 이슈 자동 매핑
- **도입 배경**: 뉴스 기사 "탄소 배출 감소 목표" → ESG 이슈 "기후목표·전환계획" 연결을 키워드 일치가 아닌 의미 기반으로 처리. 한국어 ESG 도메인에 특화된 KR-SBERT 모델 선택으로 정확도 향상

---

### scikit-learn (1.8.0+)
**한 줄 정의**: 머신러닝 알고리즘(분류, 회귀, 군집화, 정규화 등)을 제공하는 파이썬 ML 라이브러리

- **실제 활용**: `backend/src/utils/dmascoring.py`, `backend/src/services/materialities/` 등 DMA(이중중대성평가) 점수 산정 파이프라인에서 활용. 벤치마킹·미디어·설문 시그널 데이터를 통합하여 ESG 서브이슈별 재무 영향도·사회적 영향도 점수를 계산하는 스코어링 로직에 활용

---

### PyMuPDF / pypdf (pymupdf 1.27+ / pypdf 6.11+)
**한 줄 정의**: PDF 파일에서 텍스트·이미지를 추출하는 문서 파싱 라이브러리

- **실제 활용**: `backend/src/utils/ocr.py`, `backend/src/utils/ocraiv8.py`에서 벤치마킹용 PDF 파일에서 텍스트를 추출하거나 Gemini API 업로드 전 파일 전처리에 사용. PDF 병렬 파싱으로 대량 보고서 처리 속도 개선

---

## 🔐 Security & Auth

### JWE (RSA-OAEP + A256GCM) — jwcrypto 1.5.7+
**한 줄 정의**: RSA 공개키로 잠그고 개인키로만 열 수 있는 암호화 토큰. 기존 JWT보다 강력한 보안

- **실제 활용**: `backend/src/utils/tokenset.py`에서 `encryptToJwe(payload)`와 `decryptFromJwe(token)` 구현. 로그인 시 사용자 정보(`UserModel`)를 RSA-OAEP(키 암호화) + A256GCM(데이터 암호화) 방식으로 이중 암호화한 JWE 토큰 생성. 액세스 토큰·리프레시 토큰·초대 링크 토큰 모두 JWE로 발급. `secrets/authpr.pem`(개인키), `secrets/authpb.pem`(공개키) RSA 키 파일로 암복호화
- **도입 배경**: 일반 JWT는 Base64로 디코딩하면 페이로드가 평문으로 노출됨. ESG 플랫폼의 사용자 이름·이메일·권한 정보를 토큰에 담으면서도 탈취 시 내용을 알 수 없도록 JWE 암호화 채택

---

### HttpOnly Cookie + 세션 갱신 Race Condition 방어
**한 줄 정의**: 자바스크립트로 접근 불가능한 쿠키에 인증 토큰을 저장하여 XSS 공격을 차단하는 보안 방식

- **실제 활용**: `backend/src/utils/auth.py`의 `get_token()` 함수에서 구현
  - `APIKeyCookie(name=settings.cookie_key)`로 쿠키에서 UUID를 추출
  - UUID로 Redis(db1)에서 JWE 토큰 조회 → RSA 복호화 → `UserModel` 반환
  - 다중 도메인 지원: `get_domain()` 함수로 요청 도메인을 판별하여 `.weareithero.cloud` 또는 `.skm.myapp.com`에 알맞은 쿠키 도메인 동적 설정
  - 토큰 갱신 시 구 UUID로 30초간 요청을 허용하는 `rotated:` 키 조회 로직으로 동시 요청 Race Condition 방어
- **도입 배경**: 사용자 인증 토큰을 localStorage에 저장하면 XSS로 탈취 가능. `httponly=True, samesite="lax"` 쿠키로 저장하여 스크립트 접근 차단

---

### FastAPI Dependency Injection 인증 미들웨어
**한 줄 정의**: API 엔드포인트마다 인증 코드를 반복 작성하지 않고 의존성 주입으로 자동 처리하는 FastAPI 패턴

- **실제 활용**: `ai.py`, `benchmk.py`, `media.py` 등 모든 보호 API 라우터에서 `token=Depends(get_token)`을 함수 파라미터로 선언하는 것만으로 인증 완료. `get_token()` 함수가 쿠키 추출 → Redis 조회 → JWE 복호화 → `UserModel` 반환까지 자동 처리

---

## 🏗️ Infrastructure & DevOps

### Vite Proxy (개발 환경)
**한 줄 정의**: 개발 환경에서 프론트엔드와 백엔드가 다른 주소에 있을 때 CORS(교차 출처 오류) 없이 통신하도록 중계하는 설정

- **실제 활용**: `vite.config.js`에서 `/api` 경로로 들어오는 모든 요청을 `http://main.weareithero.cloud` 백엔드로 전달하도록 프록시 설정. 경로 재작성(`rewrite`)으로 `/api/v1/rollups` → `/v1/rollups`로 변환. `allowedHosts`에 `skm.weareithero.cloud` 등 허용 도메인 명시

---

### Prometheus Fastapi Instrumentator (7.1.0+)
**한 줄 정의**: API별 요청 수·응답 시간·에러율 등 성능 지표를 자동으로 수집하고 Prometheus 형식으로 노출하는 모니터링 도구

- **실제 활용**: FastAPI 앱 초기화 시 instrumentator를 등록하여 `/metrics` 엔드포인트를 통해 모든 API의 성능 데이터를 실시간 수집. ESG 보고서 생성(`ai.py`)처럼 시간이 오래 걸리는 엔드포인트의 응답 시간을 측정하여 병목 진단에 활용 (`[TOTAL TIME] {end - start:.3f}s` 로그와 병행)

---

### Google Apps Script 연동 (surveyTemplate)
**한 줄 정의**: 구글 스프레드시트·폼과 연동하여 이해관계자 설문을 자동화하는 서버리스 스크립트 플랫폼

- **실제 활용**: `settings.py`의 `APPS_SCRIPT_URL` 설정값으로 Google Apps Script 웹앱 URL을 관리. `survey/` 서비스에서 이해관계자 설문 폼 생성·응답 수집·점수 집계 자동화에 활용. `surveyTemplate.json`으로 설문 양식 구조 관리

---

*본 문서는 실제 소스 코드 (`frontend/src/stores/reportSlice.js`, `authSlice.js`, `backend/src/utils/db.py`, `rediscl.py`, `kafkasv.py`, `auth.py`, `tokenset.py`, `ai.py`, `settings.py`, `frontend/src/homes/reports/BenchMarking.jsx`, `Media.jsx`, `onboards/OnBoard.jsx`) 분석을 기반으로 작성되었습니다.*
