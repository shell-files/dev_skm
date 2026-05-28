# DB_SCHEMA_GAP_CHECK_v1

작성일: 2026-05-28
대상 schema 파일: `SKM_ESG_v5_2_28_table.sql`

## 1. 문서 목적

현재 운영 DB, clean schema SQL, 현재 backend 코드가 서로 다르게 이해할 수 있는 schema gap을 정리한다.

2026-05-28 확인 및 적용 결과:

- 운영 DB의 `ESG_DMA_SIGNAL_DETAIL.scoring_payload_json` 존재 확인 완료.
- 운영 DB의 `ESG_DMA_SCORE_SUMMARY.context_impact_modifier`, `context_financial_modifier`를 additive 기준으로 정규화 완료.
- 운영 DB modifier 컬럼은 `DECIMAL(6,4) NOT NULL DEFAULT 0.0000`으로 변경 완료.
- clean schema SQL에도 `scoring_payload_json` 및 additive modifier default를 반영 완료.

이번 문서의 핵심은 다음 세 가지다.

- `scoring_payload_json`은 운영 DB 반영 완료로 정정한다.
- `context_impact_modifier`, `context_financial_modifier`는 additive modifier로 확정하고 default를 `0.0000`으로 수정한다.
- report edit/order 본구현 전 필요한 DDL을 고정한다.

## 2. 기준 원칙

- DB column은 snake_case를 유지한다.
- Python/Pydantic field는 camelCase를 유지한다.
- score canonical 기준은 0~5다.
- API는 `score05`, `score10`을 함께 내려준다.
- `context_impact_modifier`, `context_financial_modifier`는 multiplier가 아니다.
- context modifier는 final aggregation 이후 1회만 additive로 적용한다.
- stage score에는 context modifier를 적용하지 않는다.

## 3. Gap 요약표

| 항목 | 운영 DB | clean schema SQL | 현재 코드 | 판정 |
|---|---|---|---|---|
| `ESG_DMA_SIGNAL_DETAIL.scoring_payload_json` | 반영 완료 | 반영 완료 | 사용 중 | gap 해결 |
| `ESG_DMA_EVIDENCE.source_url` | 필요 | 존재 | 저장 보완 완료 | gap 없음 |
| `ESG_DMA_EVIDENCE.source_published_at` | 필요 | DATETIME 존재 | 저장 보완 완료 | gap 없음 |
| `ESG_DMA_SCORE_SUMMARY.context_impact_modifier` | `DEFAULT 0.0000` 반영 완료 | `DEFAULT 0.0000` 반영 완료 | 현재 0.0 고정 전달 | gap 해결 |
| `ESG_DMA_SCORE_SUMMARY.context_financial_modifier` | `DEFAULT 0.0000` 반영 완료 | `DEFAULT 0.0000` 반영 완료 | 현재 0.0 고정 전달 | gap 해결 |
| `ESG_REPORT_SECTION_DRAFT.edited_text` | 미반영 가능 | 누락 | report skeleton에서 missing field 취급 | Phase 2B DDL 필요 |
| `ESG_REPORT_SECTION_DRAFT.last_edited_by_user_id` | 미반영 가능 | 누락 | report skeleton에서 missing field 취급 | Phase 2B DDL 필요 |
| `ESG_REPORT_SECTION_DRAFT.last_edited_at` | 미반영 가능 | 누락 | report skeleton에서 missing field 취급 | Phase 2B DDL 필요 |
| `ESG_REPORT_SECTION_DRAFT.section_order` | 미반영 가능 | 누락 | `ID_ASC_FALLBACK` | Phase 2B DDL 필요 |
| `ESG_REPORT_SECTION_DRAFT.paragraph_order` | 미반영 가능 | 누락 | `ID_ASC_FALLBACK` | Phase 2B DDL 필요 |
| `TE_SR_FILE` | 환경별 확인 필요 | ESG clean schema에는 없음 | benchmark MVP 의존 가능 | benchmark 전 확인 필요 |

## 4. scoring_payload_json

### 4.1 현재 판단

운영 DB에는 아래 ALTER가 이미 반영된 것으로 본다.

```sql
ALTER TABLE ESG_DMA_SIGNAL_DETAIL
ADD COLUMN scoring_payload_json LONGTEXT NULL
COMMENT 'DMASignal camelCase payload and evidence trace JSON';
```

따라서 runtime 기준으로는 완료다.

### 4.2 clean schema 반영 필요

`SKM_ESG_v5_2_28_table.sql`의 `ESG_DMA_SIGNAL_DETAIL` 정의에는 `scoring_payload_json`을 반영 완료했다. 이전 clean schema 또는 이미 배포된 구버전 DB에는 없을 수 있으므로 migration DDL은 유지한다.

권장 clean schema 반영 위치:

```sql
CREATE TABLE IF NOT EXISTS ESG_DMA_SIGNAL_DETAIL (
    ...
    judge_reason TEXT NULL,
    scoring_payload_json LONGTEXT NULL
      COMMENT 'DMASignal camelCase payload and evidence trace JSON',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    ...
);
```

기존 DB migration용 DDL:

```sql
ALTER TABLE ESG_DMA_SIGNAL_DETAIL
ADD COLUMN scoring_payload_json LONGTEXT NULL
COMMENT 'DMASignal camelCase payload and evidence trace JSON';
```

이미 존재하는 DB에서는 중복 실행하지 않는다.

## 5. context modifier default gap

### 5.1 확정 semantics

`context_impact_modifier`, `context_financial_modifier`는 additive modifier다.

공식:

```text
final_impact_score =
  clamp(raw_final_impact_score + context_impact_modifier, 0, 5)

final_financial_score =
  clamp(raw_final_financial_score + context_financial_modifier, 0, 5)
```

기본값:

```text
context_impact_modifier = 0.0000
context_financial_modifier = 0.0000
```

허용 범위:

```text
-0.5 ~ +0.5
```

적용 위치:

- final aggregation 직후 1회
- stage score에는 적용하지 않음
- benchmark/media/survey 개별 점수에는 적용하지 않음

### 5.2 현재 schema 문제

수정 전 schema 파일은 다음처럼 보였다.

```sql
context_impact_modifier DECIMAL(8,4) NULL DEFAULT 1.0000,
context_financial_modifier DECIMAL(8,4) NULL DEFAULT 1.0000,
```

`1.0000`은 multiplier default처럼 해석될 수 있어 현재 확정된 additive 의미와 맞지 않았다. 운영 DB와 clean schema는 `0.0000` default로 수정 완료했다.

### 5.3 권장 migration DDL

기존 값이 아직 실제 modifier로 사용된 적이 없는 MVP 데이터로 보고 `1.0000`과 `NULL`은 `0.0000`으로 정규화한다.

```sql
UPDATE ESG_DMA_SCORE_SUMMARY
SET context_impact_modifier = 0.0000
WHERE context_impact_modifier IS NULL
   OR context_impact_modifier = 1.0000;

UPDATE ESG_DMA_SCORE_SUMMARY
SET context_financial_modifier = 0.0000
WHERE context_financial_modifier IS NULL
   OR context_financial_modifier = 1.0000;
```

컬럼 정의 수정:

```sql
ALTER TABLE ESG_DMA_SCORE_SUMMARY
MODIFY COLUMN context_impact_modifier DECIMAL(6,4) NOT NULL DEFAULT 0.0000
COMMENT 'Additive company context modifier for final impact score, range -0.5 to +0.5';

ALTER TABLE ESG_DMA_SCORE_SUMMARY
MODIFY COLUMN context_financial_modifier DECIMAL(6,4) NOT NULL DEFAULT 0.0000
COMMENT 'Additive company context modifier for final financial score, range -0.5 to +0.5';
```

MariaDB CHECK constraint는 운영 버전 호환성을 확인한 뒤 선택 적용한다.

```sql
ALTER TABLE ESG_DMA_SCORE_SUMMARY
ADD CONSTRAINT chk_dma_context_impact_modifier
CHECK (context_impact_modifier BETWEEN -0.5000 AND 0.5000);

ALTER TABLE ESG_DMA_SCORE_SUMMARY
ADD CONSTRAINT chk_dma_context_financial_modifier
CHECK (context_financial_modifier BETWEEN -0.5000 AND 0.5000);
```

CHECK를 적용하지 않는 경우 service/rule engine에서 반드시 clamp한다.

## 6. ESG_DMA_CONTEXT_PROFILE

현재 schema에는 `ESG_DMA_CONTEXT_PROFILE`이 존재한다.

```text
context_json LONGTEXT
modifier_json LONGTEXT
confidence_score DECIMAL(8,4)
```

Company Context Modifier v1은 신규 table을 먼저 만들기보다 이 테이블을 우선 사용한다.

권장 사용 방식:

- `context_json`: AI가 만든 구조화 profile 저장
- `modifier_json`: rule engine 산출 결과와 rule hit 저장
- `confidence_score`: profile 신뢰도 또는 coverage 점수 저장

향후 modifier 변경 이력 또는 승인 workflow가 필요해지면 별도 history table을 검토한다.

## 7. Media evidence URL/date

### 7.1 schema 상태

`ESG_DMA_EVIDENCE`에는 다음 컬럼이 존재한다.

```sql
source_url VARCHAR(1000) NULL,
source_published_at DATETIME NULL,
```

따라서 이전 handoff의 `source_published_at VARCHAR(50)` 후보는 폐기한다. 날짜는 `DATETIME` 기준으로 유지한다.

### 7.2 코드 상태

현재 media crawler/adapter에서 article의 URL과 발행일을 evidence payload로 전달하고, repository 저장 로직은 다음 컬럼에 저장한다.

- `ESG_DMA_EVIDENCE.source_url`
- `ESG_DMA_EVIDENCE.source_published_at`

운영 DB에 해당 컬럼이 없는 구버전 환경은 migration이 필요하지만, 현재 clean schema에는 존재하므로 신규 DDL은 필요하지 않다.

## 8. Report edit/order columns

### 8.1 현재 gap

`ESG_REPORT_SECTION_DRAFT`에는 현재 다음 컬럼이 없다.

- `edited_text`
- `last_edited_by_user_id`
- `last_edited_at`
- `section_order`
- `paragraph_order`

Phase 2A report API는 skeleton으로 유지하고, 부족한 schema는 response에서 `implementationStatus = "SKELETON"` 또는 `missingSchemaFields`로 표현한다.

### 8.2 권장 DDL

```sql
ALTER TABLE ESG_REPORT_SECTION_DRAFT
ADD COLUMN edited_text LONGTEXT NULL
COMMENT 'User edited paragraph text. NULL means use generated_text',
ADD COLUMN last_edited_by_user_id BIGINT NULL
COMMENT 'USER.id of last editor',
ADD COLUMN last_edited_at DATETIME NULL
COMMENT 'Last edit timestamp',
ADD COLUMN section_order INT NULL
COMMENT 'Display order of section within report',
ADD COLUMN paragraph_order INT NULL
COMMENT 'Display order of paragraph within section';
```

권장 index:

```sql
CREATE INDEX idx_report_draft_order
ON ESG_REPORT_SECTION_DRAFT (report_run_id, section_order, paragraph_order, id);
```

Phase 2A에서는 `id ASC` fallback을 허용하고 response에 다음을 포함한다.

```json
{
  "orderSource": "ID_ASC_FALLBACK"
}
```

## 9. TE_SR_FILE dependency

Benchmark MVP는 기존 파일 업로드/지속가능경영보고서 파일 테이블인 `TE_SR_FILE`에 의존할 수 있다.

현재 `SKM_ESG_v5_2_28_table.sql`은 ESG domain clean schema이고, `TE_SR_FILE`은 포함되어 있지 않다.

판정:

- `TE_SR_FILE`이 base app schema에 존재하면 ESG clean schema에 중복 생성하지 않는다.
- base app schema와 함께 배포되지 않는 환경이면 benchmark 실행 전 migration 또는 compatibility view가 필요하다.
- benchmark API는 table 부재 시 graceful empty/error response로 처리해야 한다.

검증 SQL:

```sql
SHOW TABLES LIKE 'TE_SR_FILE';
```

## 10. 검증 SQL

운영 DB 상태 확인:

```sql
SHOW COLUMNS FROM ESG_DMA_SIGNAL_DETAIL LIKE 'scoring_payload_json';

SHOW COLUMNS FROM ESG_DMA_EVIDENCE LIKE 'source_url';
SHOW COLUMNS FROM ESG_DMA_EVIDENCE LIKE 'source_published_at';

SHOW FULL COLUMNS FROM ESG_DMA_SCORE_SUMMARY LIKE 'context_impact_modifier';
SHOW FULL COLUMNS FROM ESG_DMA_SCORE_SUMMARY LIKE 'context_financial_modifier';

SHOW COLUMNS FROM ESG_REPORT_SECTION_DRAFT LIKE 'edited_text';
SHOW COLUMNS FROM ESG_REPORT_SECTION_DRAFT LIKE 'last_edited_by_user_id';
SHOW COLUMNS FROM ESG_REPORT_SECTION_DRAFT LIKE 'last_edited_at';
SHOW COLUMNS FROM ESG_REPORT_SECTION_DRAFT LIKE 'section_order';
SHOW COLUMNS FROM ESG_REPORT_SECTION_DRAFT LIKE 'paragraph_order';

SHOW TABLES LIKE 'TE_SR_FILE';
```

context modifier 값 점검:

```sql
SELECT
    COUNT(*) AS row_count,
    SUM(context_impact_modifier = 1.0000) AS impact_default_10000_count,
    SUM(context_financial_modifier = 1.0000) AS financial_default_10000_count,
    SUM(context_impact_modifier < -0.5 OR context_impact_modifier > 0.5) AS impact_out_of_range_count,
    SUM(context_financial_modifier < -0.5 OR context_financial_modifier > 0.5) AS financial_out_of_range_count
FROM ESG_DMA_SCORE_SUMMARY
WHERE delete_yn = 0;
```

## 11. 적용 우선순위

1. `context_*_modifier` default를 `0.0000`으로 변경. 완료.
2. `scoring_payload_json`을 clean schema에 반영. 완료.
3. report edit/order columns는 Phase 2B report edit 전에 반영.
4. `TE_SR_FILE` 존재 여부는 benchmark integration 전에 확인.

## 12. 결론

현재 가장 중요한 schema gap이었던 context modifier default는 운영 DB와 clean schema 모두 반영 완료했다.

다음 구현인 Company Context Modifier에서는 `0.0000` additive default를 전제로 진행한다.
