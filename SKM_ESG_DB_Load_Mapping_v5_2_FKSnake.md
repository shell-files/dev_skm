# SKM ESG DB Load Mapping v5.2 — FKSnake MinOps

## 0. 목적

본 문서는 `MVP_ESG_Integrated_Quant_Qual_AllMetric_Map_v5_1_MinOps.xlsx`를 `SKM_ESG_Onboarding_Integrated_DDL_v5_2_FKSnake_MariaDB.sql` 기준 DB에 적재하기 위한 매핑서다.

v5.1 seed dataset은 MVP 개발/시연용 롤백 기준본이다. 시트명, 컬럼명, `atomic_metric_id`는 변경하지 않는다.

## 1. 적재 전제

1. 기존 legacy 테이블은 변경하지 않는다.
2. `COMPANY.id`는 BIGINT이다.
3. v5.1 workbook의 `company_id` 값 `A_GROUP/B_SUB_KR/C_SUB_EU/D_SUB_US`는 DB의 실제 `COMPANY.id`가 아니라 시연용 회사 코드다.
4. 실제 insert 시에는 `ESG_COMPANY_PROFILE`에서 `company_code → company_id` 매핑 후 BIGINT `company_id`를 넣는다.
5. A_GROUP도 ENTITY 입력값을 가진다.
6. `A_GROUP_CONSOLIDATED`는 `ESG_GROUP_ROLLUP_RESULT`에만 저장한다.



## 1.1 v5.2 변경 반영

v5.2에서는 DDL 구조상 다음 차이가 있다.

| 항목 | v5.1 | v5.2 |
|---|---|---|
| 회사 관계 | `ESG_COMPANY_COMPANY` | `ESG_COMPANY_ROLLUP_SCOPE` |
| 지분율 | `ownership_ratio` 존재 | 삭제 |
| 관계유형 | `relationship_type` 존재 | 삭제 |
| 감사로그 | 선택 성격 | 보고서 문단/문장 단위 감사추적용 필수 유지 |
| 제출 중복 | UK 없음 | `(esg_onboarding_cycle_id, company_id, metric_id)` UK |
| 승인 task FK | logical 중심 | `esg_onboarding_submission_id` physical FK |

`ESG_COMPANY_PROFILE`은 회사 마스터가 아니라 최소 매핑 테이블이다. `company_id`, `company_code`, `company_scope_type`, `active_yn` 중심으로만 사용한다.

## 2. 파일/시트 구조

| 시트 | 범위 | 용도 |
|---|---:|---|
| `00_README` | A1:B9 | 파일 설명 |
| `01_MASTER_ATOMIC_ALL` | A1:AE180 | master atomic 179개 |
| `02_DUMMY_INPUT_FACT_3YR` | A1:Z1396 | A/B/C/D 3개년 fact seed |
| `03_GROUP_ROLLUP_3YR` | A1:T115 | A_GROUP consolidated rollup |
| `04_NARRATIVE_TEMPLATE_TOKEN` | A1:L7 | narrative template/token |
| `05_NARRATIVE_DRAFT_3YR` | A1:Q19 | 3개년 report draft |
| `06_REFERENCE_EVIDENCE` | A1:M11 | evidence/reference |
| `07_QA_SUMMARY` | A1:D13 | QA result |

## 3. 권장 적재 순서

```text
1. legacy COMPANY/USER/ROLE/USER_ROLE/INVITE 데이터 준비
2. ESG_COMPANY_PROFILE 적재: company_code → COMPANY.id 매핑
3. ESG_COMPANY_ROLLUP_SCOPE 적재: A_GROUP parent + A/B/C/D 롤업 포함 범위
4. ESG_SUB_ISSUE_MASTER 62개 적재
5. ESG_METRIC_MASTER 적재
6. ESG_ATOMIC_METRIC_MASTER 적재
7. ESG_SUB_ISSUE_METRIC_MAP / ESG_SUB_ISSUE_ATOMIC_MAP 적재
8. ESG_MATERIALITY_RUN / SCORE / SELECTED / SELECTED_ONBOARDING_SCOPE 적재
9. ESG_ONBOARDING_CYCLE 적재
10. ESG_METRIC_ASSIGNMENT 적재
11. ESG_ONBOARDING_INPUT_VALUE 적재
12. ESG_ONBOARDING_SUBMISSION / APPROVAL_TASK / APPROVAL_LOG 적재
13. ESG_FACT_CANDIDATE 적재
14. ESG_KPI_FACT 적재
15. ESG_CALCULATION_RULE / SOURCE 적재
16. ESG_ROLLUP_BATCH 적재
17. ESG_GROUP_ROLLUP_RESULT 적재
18. ESG_SOURCE_DOCUMENT / ESG_EVIDENCE_CHUNK 적재
19. ESG_NARRATIVE_TEMPLATE / TOKEN 적재
20. ESG_REPORT_CONTEXT_SNAPSHOT 적재
21. ESG_REPORT_SECTION_DRAFT 적재
22. ESG_NARRATIVE_REFERENCE 적재
23. ESG_SEED_QA_RESULT 적재
```

## 4. 시트별 DB 매핑

### 4.1 `01_MASTER_ATOMIC_ALL` → `ESG_METRIC_MASTER`, `ESG_ATOMIC_METRIC_MASTER`

`01_MASTER_ATOMIC_ALL`은 metric과 atomic master를 동시에 포함한다. `metric_id` 기준 distinct row는 `ESG_METRIC_MASTER`로, 전체 row는 `ESG_ATOMIC_METRIC_MASTER`로 적재한다.

| Sheet column | ESG_ATOMIC_METRIC_MASTER column | 비고 |
|---|---|---|
| `topic_code` | `topic_code` | 그대로 |
| `materiality_topic` | `materiality_topic` | 그대로 |
| `sub_issue` | `sub_issue_code` | 명칭값이면 코드 변환 필요. MVP는 명칭 그대로도 가능하나 운영은 code 권장 |
| `owner_metric_id` | `owner_metric_id` | 그대로 |
| `metric_id` | `metric_id` | 그대로 |
| `metric_name_kr` | `metric_name_kr` | 그대로 |
| `atomic_metric_id` | `atomic_metric_id` | primary business key |
| `atomic_name_kr` | `atomic_name_kr` | 그대로 |
| `atomic_name_en` | `atomic_name_en` | 그대로 |
| `description` | `description` | 그대로 |
| `data_value_type` | `data_value_type` | 정성/정량 |
| `atomic_data_role` | `atomic_data_role` | INPUT/DERIVED/REFERENCE |
| `token_role` | `token_role` | Q/QL/EV 등 |
| `onboarding_input_yn` | `onboarding_input_yn` | Y/N → 1/0 |
| `q_token_yn` | `q_token_yn` | Y/N → 1/0 |
| `ql_token_yn` | `ql_token_yn` | Y/N → 1/0 |
| `ev_token_yn` | `ev_token_yn` | Y/N → 1/0 |
| `event_token_yn` | `event_token_yn` | Y/N → 1/0 |
| `applicable_company_scope` | `applicable_company_scope` | 그대로 |
| `group_link_type_code` | `group_link_type_code` | 그대로 |
| `rollup_required_yn` | `rollup_required_yn` | Y/N → 1/0 |
| `rollup_role` | `rollup_role` | 그대로 |
| `rollup_formula` | `rollup_formula` | 그대로 |
| `source_atomic_metric_ids` | `source_atomic_metric_ids` | ; separated |
| `calculation_formula` | `calculation_formula` | 사람용 수식 |
| `reference_source_atomic_metric_id` | `reference_source_atomic_metric_id` | 그대로 |
| `unit` | `unit` | 그대로 |
| `evidence_required_yn` | `evidence_required_yn` | Y/N → 1/0 |
| `target_db_table` | `target_db_table` | logical table name. physical table은 uppercase ESG_* |
| `narrative_template_owner_yn` | `narrative_template_owner_yn` | Y/N → 1/0 |
| `qa_rule` | `qa_rule` | 그대로 |

### 4.2 `02_DUMMY_INPUT_FACT_3YR` → `ESG_ONBOARDING_INPUT_VALUE`, `ESG_FACT_CANDIDATE`, `ESG_KPI_FACT`

1개 row는 온보딩 입력값, fact 후보, 확정 fact로 단계별 적재할 수 있다. MVP seed에서는 `approval_status = approved`이므로 세 테이블에 동시에 넣을 수 있다.

| Sheet column | INPUT_VALUE | FACT_CANDIDATE | KPI_FACT | 비고 |
|---|---|---|---|---|
| `fact_row_id` | - | - | - | 필요 시 source trace로 별도 보관 |
| `reporting_year` | `reporting_year` | `reporting_year` | `reporting_year` | 그대로 |
| `company_id` | `company_id` | `company_id` | `company_id` | company_code → COMPANY.id 변환 필요 |
| `company_scope_type` | `company_scope_type` | `company_scope_type` | `company_scope_type` | ENTITY |
| `metric_id` | `metric_id` | `metric_id` | `metric_id` | 그대로 |
| `atomic_metric_id` | `atomic_metric_id` | `atomic_metric_id` | `atomic_metric_id` | 그대로 |
| `value_numeric` | `value_numeric` | `value_numeric` | `value_numeric` | 정량 |
| `value_text` | `value_text` | `value_text` | `value_text` | 정성 |
| `unit` | `unit` | `unit` | `unit` | 그대로 |
| `value_source_type` | `value_source_type` | `value_source_type` | `value_source_type` | manual_input/calculated/reference_copy |
| `approval_status` | `input_status` | `candidate_status` | `approval_status` | approved |
| `approved_by_user_id` | `approved_by_user_id` | `approved_by_user_id` | `approved_by_user_id` | seed user ID 매핑 필요 |
| `approved_at` | `approved_at` | `approved_at` | `approved_at` | Excel serial date 변환 필요 |

주의: `atomic_data_role = DERIVED/REFERENCE` row는 실제 운영에서는 계산/참조 batch가 생성해야 한다. MVP seed에서는 이미 계산된 값을 seed로 넣어도 되지만, 운영 API에서는 `ESG_CALCULATION_RULE`을 통해 생성해야 한다.

### 4.3 `03_GROUP_ROLLUP_3YR` → `ESG_ROLLUP_BATCH`, `ESG_GROUP_ROLLUP_RESULT`

`esg_rollup_batch_id` distinct row를 `ESG_ROLLUP_BATCH`로 먼저 적재하고, 전체 row를 `ESG_GROUP_ROLLUP_RESULT`로 적재한다.

| Sheet column | DB column | 비고 |
|---|---|---|
| `rollup_result_id` | `rollup_result_code` | 그대로 |
| `esg_rollup_batch_id` | `rollup_batch_code` / batch lookup | batch code |
| `reporting_year` | `reporting_year` | 그대로 |
| `parent_company_id` | `parent_company_id` | A_GROUP code → COMPANY.id |
| `parent_company_scope_type` | `parent_company_scope_type` | CONSOLIDATED |
| `included_company_ids` | `included_company_ids` | company_code list → ESG_COMPANY_PROFILE 조회 후 실제 company_id list로 변환 권장 |
| `group_metric_id` | `group_metric_id` | 그대로 |
| `group_atomic_metric_id` | `group_atomic_metric_id` | 그대로 |
| `group_atomic_name` | `group_atomic_name` | 그대로 |
| `value_numeric` | `value_numeric` | 정량 롤업값 |
| `value_text` | `value_text` | 정성 롤업값 |
| `unit` | `unit` | 그대로 |
| `source_company_values_json` | `source_company_values_json` | JSON_VALID 필요. code key를 유지해도 MVP 가능 |
| `rollup_method` | `rollup_method` | SUM/RECALCULATE 등 |
| `calculation_trace` | `calculation_trace` | 그대로 |
| `rollup_status` | `rollup_status` | approved |
| `approved_by_user_id` | `approved_by_user_id` | seed user ID 매핑 필요 |
| `approved_at` | `approved_at` | date 변환 |

### 4.4 `04_NARRATIVE_TEMPLATE_TOKEN` → `ESG_NARRATIVE_TEMPLATE`, `ESG_NARRATIVE_TEMPLATE_TOKEN`

| Sheet column | ESG_NARRATIVE_TEMPLATE column |
|---|---|
| `narrative_template_id` | `narrative_template_id` |
| `owner_metric_id` | `owner_metric_id` |
| `owner_metric_name` | `owner_metric_name` |
| `materiality_topic` | `materiality_topic` |
| `sub_issue` | `sub_issue_code` |
| `related_metric_ids` | `related_metric_ids` |
| `template_text_with_atomic_tokens` | `template_text_with_atomic_tokens` |
| `expected_output_structure` | `expected_output_structure` |
| `report_section_hint` | `report_section_hint` |
| `template_status` | `template_status` |

`token_atomic_metric_ids`는 세미콜론으로 split하여 `ESG_NARRATIVE_TEMPLATE_TOKEN`에 1:N 적재한다.

### 4.5 `05_NARRATIVE_DRAFT_3YR` → `ESG_REPORT_SECTION_DRAFT`, `ESG_NARRATIVE_REFERENCE`

| Sheet column | ESG_REPORT_SECTION_DRAFT column |
|---|---|
| `draft_id` | `draft_id` |
| `reporting_year` | `reporting_year` |
| `company_id` | `company_id` code → COMPANY.id |
| `company_scope_type` | `company_scope_type` |
| `materiality_topic` | `materiality_topic` |
| `sub_issue` | `sub_issue_code` |
| `owner_metric_id` | `owner_metric_id` |
| `narrative_template_id` | `narrative_template_id` |
| `internal_management_summary` | `internal_management_summary` |
| `report_narrative_draft` | `report_narrative_draft` |
| `used_q_atomic_ids` | `used_q_atomic_ids` |
| `used_ql_atomic_ids` | `used_ql_atomic_ids` |
| `used_ev_atomic_ids` | `used_ev_atomic_ids` |
| `used_rollup_atomic_ids` | `used_rollup_atomic_ids` |
| `qa_score` | `qa_score` |
| `qa_status` | `qa_status` |

### 4.6 `06_REFERENCE_EVIDENCE` → `ESG_SOURCE_DOCUMENT`, `ESG_EVIDENCE_CHUNK`, `ESG_NARRATIVE_REFERENCE`

| Sheet column | DB target |
|---|---|
| `source_document_id` | `ESG_SOURCE_DOCUMENT.source_document_id` |
| `source_document_title` | `ESG_SOURCE_DOCUMENT.source_document_title` |
| `section_title` | `ESG_EVIDENCE_CHUNK.section_title` |
| `page_no` | `ESG_EVIDENCE_CHUNK.page_no` |
| `evidence_summary` | `ESG_EVIDENCE_CHUNK.quote_summary` |
| `evidence_role` | `ESG_EVIDENCE_CHUNK.evidence_role` |
| `used_in_template_id` | narrative template reference |
| `atomic_metric_id` | `ESG_NARRATIVE_REFERENCE.atomic_metric_id` |

### 4.7 `07_QA_SUMMARY` → `ESG_SEED_QA_RESULT`

`qa_item`, `status`, `detail` 성격 컬럼을 `ESG_SEED_QA_RESULT`에 적재한다. 컬럼명이 실제 파일과 다를 수 있으므로 insert 생성 단계에서 header를 기준으로 재확인한다.

## 5. Calculation Rule SQL 매핑

`MVP_ESG_v5_CALCULATION_RULE_SQL_MariaDB_v5_1_FKSnake.sql`은 다음 테이블에 적재한다.

| SQL source | DB table |
|---|---|
| calculation rule master INSERT | `ESG_CALCULATION_RULE` |
| source atomic map INSERT | `ESG_CALCULATION_RULE_SOURCE` |

실행 규칙:

1. `REFERENCE_COPY`
2. `ENTITY_SUM`
3. `ENTITY_RATIO`
4. `ENTITY_DIVIDE`
5. `ROLLUP_SUM`
6. `ROLLUP_RATIO_RECALC`
7. `ROLLUP_YOY_DIFF`
8. `ROLLUP_YOY_RATE`

## 6. 개발 구현상 주의

### 6.1 company code 변환

v5.1 workbook의 `company_id`는 코드값이다. insert 생성 시 반드시 `ESG_COMPANY_PROFILE.company_code`를 조회해서 실제 `COMPANY.id`를 넣어야 한다.

```sql
SELECT company_id
FROM ESG_COMPANY_PROFILE
WHERE company_code = ?;
```



### 6.1.1 ESG_COMPANY_ROLLUP_SCOPE 적재

v5.2에서는 지분율 기반 회사관계를 쓰지 않는다. 아래처럼 롤업 범위만 적재한다.

| column | value |
|---|---|
| `parent_company_id` | A_GROUP의 실제 `COMPANY.id` |
| `source_company_id` | A_GROUP/B_SUB_KR/C_SUB_EU/D_SUB_US의 실제 `COMPANY.id` |
| `source_company_code` | A_GROUP/B_SUB_KR/C_SUB_EU/D_SUB_US |
| `rollup_include_yn` | 1 |
| `effective_from_year` | 2022 |
| `effective_to_year` | NULL |

A_GROUP 본인도 source company로 포함한다. 즉 A_GROUP 연결값은 A_GROUP ENTITY + B/C/D ENTITY 승인값으로 산출된다.

### 6.2 approved seed 처리

MVP seed는 이미 승인된 상태이므로 insert 시 다음 값을 사용한다.

```text
input_status = approved
candidate_status = approved
approval_status = approved
```

### 6.3 DERIVED/REFERENCE row

MVP seed에는 계산값이 들어 있지만, 운영에서는 계산 SQL로 생성한다. 개발/시연 편의를 위해 seed insert는 허용한다.

### 6.4 narrative reference

보고서 문단은 반드시 `ESG_NARRATIVE_REFERENCE`를 통해 kpi_fact, rollup_result, evidence_chunk 중 하나 이상을 참조해야 한다.



### 6.5 ESG_AUDIT_LOG 감사추적

`ESG_AUDIT_LOG`는 삭제하지 않는다. 보고서 문단/문장별 데이터 추적 라벨을 위해 사용한다.

권장 적재 이벤트:

| event_type | 생성 시점 |
|---|---|
| `input_value_seeded` | `ESG_ONBOARDING_INPUT_VALUE` seed 적재 |
| `fact_approved` | `ESG_KPI_FACT` 확정 |
| `rollup_calculated` | `ESG_GROUP_ROLLUP_RESULT` 생성 |
| `report_draft_generated` | `ESG_REPORT_SECTION_DRAFT` 생성 |
| `narrative_reference_linked` | `ESG_NARRATIVE_REFERENCE` 연결 |

`draft_id`, `atomic_metric_id`, `reference_type`, `reference_id`, `trace_label_json`은 보고서 화면의 숨은 감사추적 라벨에 사용한다.

## 7. 다음 작업 산출물

다음 단계에서 생성할 파일은 다음이다.

```text
SKM_ESG_Create_All_Tables_v5_2.sql
SKM_ESG_Insert_MVP_v5_1_Seed_v5_2Schema.sql
SKM_ESG_Insert_MVP_v5_1_Seed_v5_2Schema_QA.md
```
