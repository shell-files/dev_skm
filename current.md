# 🚀 DMA v8.2 엔진 개발 현황 (현재까지의 작업 요약)
**목적:** 새로운 AI 에이전트가 채팅창을 열었을 때, 이전 작업 맥락을 100% 이해하고 다음 작업을 즉시 이어나갈 수 있도록 돕는 핸드오버(Hand-over) 문서입니다.

## 1. 아키텍처 핵심 철학 (v8.2)
- **LLM의 역할 축소 (Extraction Only)**: LLM(Gemini)에게 직접 1~5점 점수를 매기게 하던 기존 방식을 폐기했습니다. 환각(Hallucination)을 막기 위해 LLM은 오직 문서 내의 원문 표현(`raw_label`), 위험/기회 힌트(`iro_hint`), 단기/장기 여부(`time_horizon_hint`), 그리고 가장 중요한 **근거 문장(`evidence_spans`)**만 추출하도록 강제합니다 (`LLMExtractorOutput` 스키마 사용).
- **Rule-based Python 채점 (Scoring)**: LLM이 뽑은 증거의 개수 및 출처를 바탕으로 파이썬이 엄격한 수학 공식으로 기초 심각도 점수(Severity)를 계산합니다 (`calculate_evidence_severity`).

## 2. 지금까지 완료된 작업 상세 내역

### ✅ 1. 시맨틱 임베딩(RAG) 파이프라인 완전 통합 완료
- **파일 위치**: `backend/src/utils/ocrai_v8.py`, `backend/src/utils/subissuemaster_v8.py`
- 팀원이 `feature/ai_embeding_lch` 브랜치에서 만든 임베딩 기반 의미 매칭 로직을 현재 `ocrai_v8.py`에 이식했습니다.
- `uv`를 통해 `sentence-transformers`, `torch`, `scikit-learn` 등의 패키지를 백엔드에 설치 완료했습니다.
- `subissuemaster_v8.py`에 정의된 62개 이슈의 구체적 설명문(Sentence)을 서버 구동 시 한 번만 `SentenceTransformer` 모델로 임베딩하여 메모리에 캐싱합니다 (`_ISSUE_VECTORS`).
- LLM이 추출해 온 `raw_label`을 실시간 임베딩하여 62개 마스터 벡터와 **코사인 유사도(Cosine Similarity)**를 계산한 후, 유사도 0.35 이상인 상위 3개(top-k=3) 이슈에 가중치(alpha=1.5 제곱)를 똑똑하게 분배합니다 (`normalize_mapping_weights`).

### ✅ 2. 세밀한 감사 추적(Audit) 및 IRO 분리 설계 완료
- `ocrai_v8.py` 엔진 내부에서 최종 점수를 낼 때, `iro_hint` 값에 따라 환경/사회적 중대성(`ImpactAssessment`)과 재무적 중대성(`FinancialAssessment`)을 완벽히 분리하여 저장합니다.
- `DMAScoreDetail`이라는 상세 Pydantic 모델을 사용하여 "누가, 왜, 어떤 문장(evidence) 때문에 이 유사도와 점수가 나왔는지" DB 저장용 메타데이터를 꼼꼼하게 남깁니다. (API 응답 시에는 프론트엔드를 위해 가벼운 Dict 형태로 반환).

## 3. 남은 작업 (Next Steps)
다음 AI 에이전트는 이어서 아래의 작업(Phase D 연동 등)을 수행해야 합니다.

1. **API & Pipeline Integration (Phase D)**: 
   - `ocrai_v8.py` 모듈을 실제 백엔드 API(예: 프론트엔드에서 호출하는 Endpoint)에 연결.
   - 더미 설문조사(Survey) 결과나 외부 이해관계자 데이터를 엔진 파이프라인에 결합하기.
2. **테스트 및 검증**:
   - `backend/test_ocrai.py` 등을 활용하여 실제 PDF를 넣었을 때 임베딩 매칭부터 점수 쪼개기(Weight Distribution), 최종 API JSON 반환까지 정상적으로 렌더링되는지 E2E 테스트 수행.
3. **DB 저장 로직 연동**:
   - `DMAScoreDetail` 객체를 실제 MariaDB 테이블 구조에 맞게 `insert` 하는 로직 추가 필요.

---
**💡 다음 AI 에이전트 행동 지침:**
이 문서를 읽었다면, 사용자가 원하는 다음 단계 작업을 물어보고 즉시 실행 계획(Implementation Plan)을 수립하세요!
`ocrai_v8.py` 내의 임베딩 로직(SentenceTransformer)과 점수 분배 로직(Rule-based Scorer)을 절대 훼손하지 않도록 주의하세요.
