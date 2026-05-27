# DMA Core Stabilization & Media Integration Plan

이 문서는 사용자께서 제시하신 6단계 확장 전략에 기반하여, "DMA Core 마감 보정"부터 "미디어 언론 E2E 개통 및 확장"까지의 전체 구현 계획을 정리한 문서입니다.

## User Review Required

> [!WARNING]
> `ESG_DMA_SIGNAL_DETAIL.scoring_payload_json`에 저장되는 JSON 구조를 기존 snake_case(alias 기준)에서 camelCase(필드명 기준)로 변경할 계획입니다. 이는 시스템 전체의 "내부/API camelCase 통일" 원칙을 준수하기 위함입니다. DB audit 데이터까지 camelCase로 저장되는 것에 동의하시는지 확인이 필요합니다.

## Proposed Changes

---

### 1. DMA Core 마감 보정 (우선 실행)

DMA 핵심 산식 및 데이터 정합성을 미디어 통합 전에 보정합니다.

#### [MODIFY] `src/utils/dmascoring.py`
- `calculateImpactScore` 및 `calculateFinancialScore` 내 regulation 하드 매핑 로직에서 `"공급망 관리"`, `"기후변화"` 등 한글 문자열 비교를 제거하고, `SUPPLY_CHAIN`, `CLIMATE`, `DATA_SECURITY` 등 영문 key(SubIssueCode) 기준으로만 매핑하도록 변경합니다.
- `likelihood`와 `irremediability` 값이 0인 경우를 None(결측치)과 올바르게 구분하도록 `if factor.likelihood:` 구조를 `if factor.likelihood is not None:` 구조로 수정합니다.

#### [MODIFY] `src/utils/dmarepository.py`
- **Total Count Normalization**: `recalculateStageScore`의 벤치마크 계산 시 `TE_SR_FILE`의 type을 그대로 그룹핑하지 않고, 'Leader', '리더' 등을 `leader_sr`로 통일하는 정규화(Normalization) 과정을 거친 후 count를 합산하도록 개선합니다.
- **JSON Serialization**: `payload = sig.model_dump(by_alias=True)`를 `payload = sig.model_dump(by_alias=False)`(혹은 `by_alias` 생략)로 변경하여 `scoring_payload_json`을 camelCase로 직렬화합니다.

---

### 2. Media News E2E 백엔드 구현

미디어 언론 분석을 위한 실질적인 파이프라인 및 어댑터를 구현하여 E2E 흐름을 개통합니다.

#### [MODIFY] `src/services/medias/pipeline.py`
- 기존 `embading` 레포의 RAG/Embedding 로직을 이식하여 `processMediaPipeline` 함수를 구현합니다.
- 문서 청킹, 임베딩, 유사도 기반 `bestSubIssueId`(SubIssueCode 매핑) 추출 로직을 포함합니다.

#### [MODIFY] `src/services/medias/baseline.py`
- MVP 5개 이슈(`CLIMATE`, `SUPPLY_CHAIN` 등)에 대한 미디어 전용 Baseline(ImpactFactor, FinancialFactor) 정적 매핑을 `MEDIA_BASELINE_BY_SUB_ISSUE` 형태로 구현합니다.

#### [MODIFY] `src/services/medias/adapter.py`
- `pipeline`의 결과를 `DMASignal` 모델로 변환하는 로직을 구현합니다.
- `similarityScore`를 산출하되, 이를 Impact/Financial 점수로 직결시키지 않고 `mappingConfidence`/`confidenceScore`로만 활용하도록 매핑합니다. (점수는 Baseline을 따름)

#### [MODIFY] `src/services/medias/service.py`
- `pipeline` ➔ `adapter` ➔ `baseline` ➔ `scoreDmaSignals` ➔ `saveDmaSignals` 전체 흐름을 주석 해제 및 활성화하여 DB 저장을 유발합니다.

---

### 3. Media API 구현

프론트엔드 연동을 위한 API 엔드포인트를 구현합니다.

#### [MODIFY] `src/apis/media.py`
- `POST /media/news/analyze` 또는 `POST /dma/runs/{runId}/media/news/analyze` 형태의 분석 트리거 API를 신규 작성합니다.
- 분석 완료 후 `articleCount`, `observedSubIssueCount`, `savedSignalCount`, `topIssues` 등의 Summary Response를 반환하도록 설계합니다.

---

### 4. 프론트엔드 (Media.jsx) 연동

UI에서 실제 백엔드 API를 호출하도록 수정합니다.

#### [MODIFY] 프론트엔드 `Media.jsx` 및 관련 네트워크 파일 (정확한 경로는 추후 확인)
- 기존 `setTimeout` 기반의 mock 로직과 하드코딩된("14건, 언론 8건...") 결과 문구를 제거합니다.
- 새로 작성한 POST API를 호출하여 상태를 업데이트하고, 받아온 `articleCount` 등을 렌더링하도록 연동합니다. (규제/기관은 UI상 '준비 중' 유지)

---

## Verification Plan

### 1. DB E2E 검증 (작업 2~4 완료 시점)
다음 SQL 쿼리를 통해 미디어 언론 시그널이 올바르게 DB에 적재되고, Aggregation(Stage/Final)이 수행되었는지 확인합니다.

1. **Signal Detail 확인**
   ```sql
   SELECT source_step, source_type, COUNT(*)
   FROM ESG_DMA_SIGNAL_DETAIL
   WHERE esg_materiality_run_id = ?
   GROUP BY source_step, source_type;
   ```
2. **Score Summary 및 랭킹 갱신 확인**
   ```sql
   SELECT sub_issue_code, media_external_impact_score, media_external_financial_score,
          final_impact_score, final_financial_score, final_score, rank_no
   FROM ESG_DMA_SCORE_SUMMARY
   WHERE esg_materiality_run_id = ? ORDER BY rank_no;
   ```
3. **Evidence 확인**
   ```sql
   SELECT evidence_id, source_step, source_type, source_title, text_span
   FROM ESG_DMA_EVIDENCE
   WHERE esg_materiality_run_id = ? ORDER BY evidence_id DESC;
   ```

### 2. 이후 확장 프로세스 (향후 과제)
미디어 파이프라인 검증이 완료된 이후 다음 순서로 확장을 진행합니다.
1. `regulation` (CSDDD 등 Rule 매핑 어댑터)
2. `agency` (KCGS, 등 신용평가방법론 어댑터)
3. `survey` (응답 구조 분리 및 정교화)
4. `benchmark` (비율 정교화)
