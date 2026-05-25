# DMA 시스템 고도화 실행 계획 (v8.2 기반)

**분석 문서**: `DMA_v8_2_Antigravity_Implementation_Instructions_similarity_updated.md`
**작성일**: 2026-05-25

## 📌 핵심 분석 요약 (v8.1 ➡ v8.2 패러다임 전환)
새로운 v8.2 기획의 가장 중요한 차이점은 **"LLM의 자의적 채점 권한 박탈"**과 **"유사도(Similarity) 기반의 점수 배분(Mapping Weight)"**입니다.
1. **LLM의 역할 축소**: LLM은 본문을 읽고 점수(1~5점)를 직접 매기지 않습니다. 오직 '근거 텍스트 추출', 'IRO 분류', '62개 이슈 중 후보 제시'만 수행합니다.
2. **Rule-based 파워 강화**: LLM이 뽑아온 근거와 유사도 점수(0.6 이상)를 바탕으로, Python 백엔드가 사전에 정의된 가중치(리더/피어 여부, 규제 하드매핑, 유사도 배분율)를 곱해 최종 점수를 산출합니다.
3. **감사 추적(Audit) DB 도입**: 기존 Summary 중심 테이블 외에, 텍스트의 출처부터 유사도 가중치, 최종 점수까지 추적 가능한 Detail Ledger DB(4개 신규 테이블)가 추가됩니다.

---

## 🛠️ 개발 실행 계획 (Phases)

기획서의 지시에 따라 다음 순서로 개발을 진행할 것을 제안합니다.

### Phase 1: 기반 아키텍처 및 DB 스키마 확정 (가장 먼저 수행)
기존에 만들었던 `dma_engine.py`와 `ocrai_v8.py`를 v8.2 사양에 맞게 완전히 뒤엎어야 합니다.
- `[ ]` **Pydantic 스키마 전면 개편**: 지시서 5.3절에 명시된 `DMAContextProfile`, `ImpactAssessment`, `FinancialAssessment`, `DMAScoreDetail` 모델을 `dma_engine.py`에 구현합니다.
- `[ ]` **DB DDL 반영**: 6.1절에 명시된 4개의 신규 테이블(`ESG_DMA_CONTEXT_PROFILE`, `ESG_DMA_SCORE_DETAIL`, `ESG_DMA_EVIDENCE`, `ESG_DMA_SURVEY_RESPONSE`) 쿼리를 백엔드 DB에 적용할 준비를 합니다.

### Phase 2: 마이크로 엔진 (ocrai_v8.py) 리팩토링 (LLM ➡ Rule 기반 전환)
LLM이 직접 채점하던 기존 코드를 지시서 5.2절의 **8단계 파이프라인**으로 쪼갭니다.
- `[ ]` **LLM 추출기 구현 (Classifier & Extractor)**: 텍스트를 읽고 62개 `sub_issue_map.xlsx` 기반 후보군과 IRO Label, Evidence만 JSON으로 뽑아내는 프롬프트 작성.
- `[ ]` **유사도 맵퍼 (Similarity Mapper) 구현**: LLM이 뽑은 후보와 실제 62개 사전을 비교해 Threshold(0.60) 통과 여부 검사 및 `mapping_weight` 분배 Python 로직 구현.
- `[ ]` **Rule-based Scorer 구현**: 매핑 가중치, 출처 신뢰도, G0 Context Modifier를 곱해 최종 산술 점수를 계산하는 Python 로직 구현.

### Phase 3: 매크로 워크플로우 (LangGraph) 및 API 연결
Phase 2에서 만든 단일 기계를 4개의 API 엔드포인트(8.1 ~ 8.5)에 맞물립니다.
- `[ ]` **Context API**: G0 데이터를 읽고 `context_modifier` 0.85~1.25 배수 산출 로직 구현.
- `[ ]` **Benchmark & Media API**: 자사/타사 PDF, 뉴스를 수집해 Phase 2 엔진에 태우고 Detail DB에 저장하는 로직.
- `[ ]` **최종 Matrix 연결**: 점수 합산 후 온보딩 Scope(필수 입력 지표)로 데이터를 넘겨주는 모듈 연동.

---

## 🙋‍♂️ User Review Required (피드백 요청)
> [!IMPORTANT]
> 기획 내용이 방대하여 한 번에 모두 구현하기보다는 **가장 핵심이 되는 '엔진(Core)'부터 동작을 확인**하는 것이 좋습니다.
> 
> **다음 중 어디부터 코드를 짜서 테스트해 볼까요?**
> 
> 1. **(추천) DB 및 Pydantic 뼈대 공사**: 먼저 v8.2 스키마(`dma_engine.py`)를 새로 짜고, 신규 테이블 4개 DDL을 DB에 반영할까요? (뼈대가 있어야 데이터가 돕니다.)
> 2. **유사도 기반 Rule-based 엔진 구축**: DB 연동은 미루고, `ocrai_v8.py`를 파이프라인 8단계(LLM 추출 ➡ Python 채점)로 리팩토링하는 작업부터 할까요?
