<div align="center">
  <img src="https://github.com/user-attachments/assets/691c27ab-811f-41c8-9ae3-d07aa51d470a" width="180" align="right" />
  <div align="left">
    <h1>[SKM] 지속가능경영보고서 자동화 시스템 구축</h1>
    <p>공공 데이터와 기업 내부 데이터를 활용하여 지속가능경영보고서 작성을 자동화하는 시스템입니다.</p>
    <img width="739" height="366" alt="image" src="https://github.com/user-attachments/assets/6531176b-3b65-410e-bbc2-05058a146001" />
  </div>
</div>


## 1. 프로젝트 개요
*   **팀명:** SKM
*   **프로젝트명:** 지속가능경영보고서 자동화 시스템 구축
*   **핵심 가치:** 이중 중대성 평가 기반의 데이터 수집부터 LLM 기반 보고서 초안 생성까지의 전 과정 자동화


## 2. 주요 기능

* **이중 중대성 평가 자동화:** 벤치마킹 데이터, 이해관계자 설문, 미디어 크롤링 데이터를 종합 분석하여 핵심 이슈(Top Issue) 산출

* **OCR 기반 데이터 정형화:** Google Cloud Vision OCR을 활용해 비정형 문서(PDF 등)에서 표 및 문단 단위의 텍스트 추출

* **AI 보고서 생성 파이프라인:** RAG(Retrieval-Augmented Generation)와 Multi-Agent 아키텍처를 결합한 섹션별 보고서 초안 작성

* **실시간 모니터링 & 대시보드:** 규제 대응률(GRI, ESRS 등) 시각화 및 Prometheus/Grafana를 통한 시스템 상태 모니터링

## 3. 기술 스택

### Frontend

* React, Nginx, Stomp(WebSocket)

### Backend

* FastAPI, Kafka, Redis
* JWE (RSA-OAEP, A256GCM)
* Google API (Cloud Vision OCR, Sheets/Forms, SMTP)
* OpenAPI (공공 데이터 포털)
* Prometheus & Grafana

### AI & Data Engineering

* vLLM / Ollama, LangChain & LangGraph
* Neo4j (Graph DB), RAG & Multi-Agent Architecture
* Pandas, Data Crawling

### Database

* MariaDB, MySQL
* PostgreSQL (pgvector)

### Infrastructure & DevOps

* AWS EC2, Docker, GitHub Actions

## 4. 시스템 아키텍처

[System Architecture]
- 추가 예정
## 5. 팀원 소개

| 이름 | 역할 | 담당 업무 및 기술 기여 |
| --- | --- | --- |
| [최수아](https://github.com/sooah-0208) | 팀장 | PM, GitHub/브랜치 전략 수립, 응답 구조 설계, DB 설계 및 구축 |
| [이채훈](https://github.com/chaehun0i) | 팀원 | AI 모델 학습 데이터 수집 / 로직 구축, 데이터 벡터화(Embedding),  |
| [이정빈](https://github.com/leeej9801-max) | 팀원 | AI 모델 학습 로직 구축, 데이터 정의서 및 ERD 작성, 페르소나 정의, 발표 자료(PPT) 구성 |
| [김하영](https://github.com/luniana217) | 팀원 | 기능 정의서 및 화면 레이아웃 설계 |
- 이름 클릭시 github 링크 이동

---

### **참고사항**

* **기술적 특징:** 단순 LLM 호출이 아닌 **LangGraph**를 이용한 워크플로우 제어와 **pgvector**를 활용한 벡터 검색 시스템을 결합했습니다.
* **보안:** JWE를 활용한 데이터 암호화로 보고서 생성 과정의 보안성을 강화했습니다.
