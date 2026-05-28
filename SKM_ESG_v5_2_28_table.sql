/* =====================================================================
   SKM ESG v5.2 CLEAN_SCHEMA_v2 - MariaDB
   목적:
     - ESG 서비스 테이블을 28개 운영 구조로 재정리
     - 온보딩 Core 15개 + DMA Agent 9개 + Report/Narrative 4개
     - 기존 with.USER/ROLE/TOKEN/USER_ROLE, skm.COMPANY/LICENSE_FILE/TE_*는 생성하지 않음
     - 물리 FK는 최소화하고, 운영 관계는 business key/logical FK 중심으로 관리
   ===================================================================== */

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

/* ---------------------------------------------------------------------
   A. Onboarding Core 15
   --------------------------------------------------------------------- */

CREATE TABLE IF NOT EXISTS ESG_COMPANY_PROFILE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK. 실제 회사명 표시는 COMPANY.company_name을 aes_d로 복호화',
    company_code VARCHAR(50) NOT NULL COMMENT 'ESG 내부 식별 코드/slug. 사용자 표시명 아님',
    company_scope_type VARCHAR(30) NOT NULL DEFAULT 'ENTITY' COMMENT 'PARENT/SUBSIDIARY/ENTITY 등 ESG 관점 회사 역할',
    active_yn TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'ESG 서비스 사용 여부',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_company_profile_company (company_id),
    UNIQUE KEY uk_esg_company_profile_code (company_code),
    KEY idx_esg_company_profile_scope (company_scope_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 도메인 회사 프로필. COMPANY의 확장 프로필';

CREATE TABLE IF NOT EXISTS ESG_COMPANY_ROLLUP_SCOPE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    parent_company_id BIGINT NOT NULL COMMENT '롤업 요청 가능 주체 COMPANY.id',
    source_company_id BIGINT NOT NULL COMMENT '롤업 후보/포함 가능 회사 COMPANY.id',
    source_company_code VARCHAR(50) NULL COMMENT 'seed/debug용 내부 코드. 운영 표시는 COMPANY 복호화 사용',
    rollup_include_yn TINYINT(1) NOT NULL DEFAULT 1 COMMENT '기본 롤업 후보 포함 여부. 실제 batch별 포함은 ESG_ROLLUP_BATCH.included_company_ids_json 참조',
    effective_from_year INT NULL COMMENT '적용 시작 보고연도',
    effective_to_year INT NULL COMMENT '적용 종료 보고연도',
    note TEXT NULL COMMENT '비고',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_rollup_scope (parent_company_id, source_company_id, effective_from_year),
    KEY idx_esg_rollup_scope_source (source_company_id),
    KEY idx_esg_rollup_scope_parent (parent_company_id, rollup_include_yn)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='지주사-자회사 롤업 가능 관계/후보 범위';

CREATE TABLE IF NOT EXISTS ESG_SUB_ISSUE_MASTER (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    issue_group_code VARCHAR(80) NOT NULL COMMENT '상위 issue group 코드',
    issue_group_name_kr VARCHAR(200) NULL COMMENT '상위 issue group 한글명',
    sub_issue_code VARCHAR(120) NOT NULL COMMENT '62개 sub_issue 코드',
    sub_issue_name_kr VARCHAR(300) NOT NULL COMMENT 'sub_issue 한글명',
    sub_issue_name_en VARCHAR(300) NULL COMMENT 'sub_issue 영문명',
    materiality_issue_pool_yn TINYINT(1) NOT NULL DEFAULT 1 COMMENT '이중중대성평가 pool 포함 여부',
    sort_order INT NULL,
    active_yn TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_sub_issue_code (sub_issue_code),
    KEY idx_esg_sub_issue_group (issue_group_code),
    KEY idx_esg_sub_issue_pool (materiality_issue_pool_yn, active_yn)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='62개 sub_issue 마스터';

CREATE TABLE IF NOT EXISTS ESG_METRIC_MASTER (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    topic_code VARCHAR(50) NULL,
    materiality_topic VARCHAR(200) NULL,
    sub_issue_code VARCHAR(120) NULL COMMENT '대표 sub_issue_code',
    owner_metric_id VARCHAR(50) NULL,
    metric_id VARCHAR(50) NOT NULL COMMENT '상위 지표 ID',
    metric_name_kr VARCHAR(300) NOT NULL COMMENT '지표명',
    metric_description TEXT NULL,
    mandatory_context_yn TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'G0 등 항상 포함 context 여부',
    active_yn TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_metric_id (metric_id),
    KEY idx_esg_metric_sub_issue (sub_issue_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='상위 지표 마스터';

CREATE TABLE IF NOT EXISTS ESG_ATOMIC_METRIC_MASTER (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    topic_code VARCHAR(50) NULL,
    materiality_topic VARCHAR(200) NULL,
    sub_issue_code VARCHAR(120) NULL,
    owner_metric_id VARCHAR(50) NULL,
    metric_id VARCHAR(50) NOT NULL COMMENT '상위 지표 ID',
    metric_name_kr VARCHAR(300) NULL,
    atomic_metric_id VARCHAR(80) NOT NULL COMMENT '실제 입력/계산 최소 단위 ID',
    atomic_name_kr VARCHAR(300) NOT NULL,
    atomic_name_en VARCHAR(300) NULL,
    description TEXT NULL,
    data_value_type VARCHAR(30) NOT NULL COMMENT 'QUANT/QUAL_TEXT/EVIDENCE_TEXT 등',
    atomic_data_role VARCHAR(30) NOT NULL COMMENT 'INPUT/DERIVED/REFERENCE',
    token_role VARCHAR(20) NULL COMMENT 'Q/QL/EV/EVENT/ROLLUP',
    onboarding_input_yn TINYINT(1) NOT NULL DEFAULT 0,
    q_token_yn TINYINT(1) NOT NULL DEFAULT 0,
    ql_token_yn TINYINT(1) NOT NULL DEFAULT 0,
    ev_token_yn TINYINT(1) NOT NULL DEFAULT 0,
    event_token_yn TINYINT(1) NOT NULL DEFAULT 0,
    applicable_company_scope VARCHAR(200) NULL,
    group_link_type_code VARCHAR(50) NULL,
    rollup_required_yn TINYINT(1) NOT NULL DEFAULT 0,
    rollup_role VARCHAR(50) NULL,
    rollup_formula TEXT NULL,
    source_atomic_metric_ids TEXT NULL,
    calculation_formula TEXT NULL COMMENT '사람이 이해하는 계산식',
    calculation_rule_code VARCHAR(100) NULL COMMENT 'ESG_CALCULATION_RULE.calculation_rule_code logical FK',
    reference_source_atomic_metric_id VARCHAR(80) NULL,
    unit VARCHAR(50) NULL,
    evidence_required_yn TINYINT(1) NOT NULL DEFAULT 0,
    target_db_table VARCHAR(100) NULL,
    narrative_template_owner_yn TINYINT(1) NOT NULL DEFAULT 0,
    qa_rule TEXT NULL,
    active_yn TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_atomic_metric_id (atomic_metric_id),
    KEY idx_esg_atomic_metric (metric_id),
    KEY idx_esg_atomic_sub_issue (sub_issue_code),
    KEY idx_esg_atomic_role (atomic_data_role, onboarding_input_yn),
    KEY idx_esg_atomic_calc_rule (calculation_rule_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Atomic 지표 마스터';

CREATE TABLE IF NOT EXISTS ESG_SUB_ISSUE_ATOMIC_MAP (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    sub_issue_code VARCHAR(120) NOT NULL,
    metric_id VARCHAR(50) NOT NULL,
    atomic_metric_id VARCHAR(80) NOT NULL,
    map_scope VARCHAR(30) NOT NULL DEFAULT 'MVP',
    required_yn TINYINT(1) NOT NULL DEFAULT 1 COMMENT '해당 sub_issue 선택 시 온보딩 필수 여부',
    sort_order INT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_sub_atomic_map (sub_issue_code, metric_id, atomic_metric_id, map_scope),
    KEY idx_esg_sub_atomic_metric (metric_id),
    KEY idx_esg_sub_atomic_atomic (atomic_metric_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='sub_issue와 atomic 입력/계산값 연결';

CREATE TABLE IF NOT EXISTS ESG_ONBOARDING_CYCLE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    reporting_year INT NOT NULL,
    cycle_name VARCHAR(200) NOT NULL,
    cycle_type VARCHAR(40) NOT NULL DEFAULT 'regular' COMMENT 'regular/rollup_request/materiality_based/correction',
    cycle_status VARCHAR(30) NOT NULL DEFAULT 'open' COMMENT 'open/collecting/submitted/in_review/approved/closed/rejected',
    source_materiality_run_id BIGINT NULL COMMENT 'DMA 기반 온보딩일 경우 ESG_MATERIALITY_RUN.id',
    created_by_user_id BIGINT NULL COMMENT 'USER.id logical FK',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_cycle (company_id, reporting_year, cycle_type),
    KEY idx_esg_cycle_status (cycle_status),
    KEY idx_esg_cycle_materiality (source_materiality_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='회사/연도별 온보딩 회차';

CREATE TABLE IF NOT EXISTS ESG_METRIC_ASSIGNMENT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_onboarding_cycle_id BIGINT NOT NULL,
    company_id BIGINT NOT NULL COMMENT 'COMPANY.id logical FK',
    metric_id VARCHAR(50) NOT NULL,
    invite_id BIGINT NULL,
    assignee_user_id BIGINT NULL COMMENT 'USER.id logical FK',
    assignee_email VARCHAR(255) NULL,
    assignment_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    assignment_source_type VARCHAR(40) NOT NULL DEFAULT 'regular' COMMENT 'regular/rollup_request/materiality_based',
    source_materiality_run_id BIGINT NULL,
    source_selected_sub_issue_id BIGINT NULL,
    due_date DATE NULL,
    created_by_user_id BIGINT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_assignment (esg_onboarding_cycle_id, company_id, metric_id),
    KEY idx_esg_assignment_company (company_id, metric_id),
    KEY idx_esg_assignment_assignee (assignee_user_id),
    KEY idx_esg_assignment_source (assignment_source_type, source_materiality_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='회사/회차별 입력 지표 배정';

CREATE TABLE IF NOT EXISTS ESG_ONBOARDING_INPUT_VALUE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_metric_assignment_id BIGINT NULL,
    esg_onboarding_cycle_id BIGINT NULL,
    company_id BIGINT NOT NULL,
    reporting_year INT NOT NULL,
    company_scope_type VARCHAR(30) NOT NULL DEFAULT 'ENTITY',
    metric_id VARCHAR(50) NOT NULL,
    atomic_metric_id VARCHAR(80) NOT NULL,
    value_numeric DECIMAL(30,6) NULL,
    value_text LONGTEXT NULL,
    unit VARCHAR(50) NULL,
    value_source_type VARCHAR(30) NULL DEFAULT 'manual_input',
    input_status VARCHAR(30) NOT NULL DEFAULT 'draft',
    input_user_id BIGINT NULL,
    approved_by_user_id BIGINT NULL,
    approved_at DATETIME NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_input_value (company_id, reporting_year, atomic_metric_id),
    KEY idx_esg_input_cycle (esg_onboarding_cycle_id),
    KEY idx_esg_input_assignment (esg_metric_assignment_id),
    KEY idx_esg_input_metric (metric_id, atomic_metric_id),
    KEY idx_esg_input_status (input_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='온보딩 원천 입력값. 정성은 value_text, 정량은 value_numeric';

CREATE TABLE IF NOT EXISTS ESG_ONBOARDING_APPROVAL_HISTORY (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_onboarding_cycle_id BIGINT NOT NULL,
    esg_metric_assignment_id BIGINT NULL,
    company_id BIGINT NOT NULL,
    reporting_year INT NOT NULL,
    metric_id VARCHAR(50) NULL,
    atomic_metric_id VARCHAR(80) NULL,
    action_type VARCHAR(30) NOT NULL COMMENT 'submit/approve/reject/comment',
    action_status VARCHAR(30) NOT NULL COMMENT 'submitted/approved/rejected/commented',
    actor_user_id BIGINT NULL COMMENT '행위자 USER.id',
    assignee_user_id BIGINT NULL COMMENT '처리 대상 USER.id',
    comment_text TEXT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_esg_approval_cycle (esg_onboarding_cycle_id),
    KEY idx_esg_approval_company_metric (company_id, reporting_year, metric_id),
    KEY idx_esg_approval_actor (actor_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='온보딩 제출/승인/반려 단순 이력';

CREATE TABLE IF NOT EXISTS ESG_KPI_FACT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    source_input_value_id BIGINT NULL COMMENT 'ESG_ONBOARDING_INPUT_VALUE.id logical FK',
    company_id BIGINT NOT NULL,
    reporting_year INT NOT NULL,
    company_scope_type VARCHAR(30) NOT NULL DEFAULT 'ENTITY',
    metric_id VARCHAR(50) NOT NULL,
    atomic_metric_id VARCHAR(80) NOT NULL,
    value_numeric DECIMAL(30,6) NULL,
    value_text LONGTEXT NULL,
    unit VARCHAR(50) NULL,
    value_source_type VARCHAR(30) NULL,
    approval_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    approved_by_user_id BIGINT NULL,
    approved_at DATETIME NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_kpi_fact (company_id, reporting_year, atomic_metric_id),
    KEY idx_esg_kpi_metric (metric_id, atomic_metric_id),
    KEY idx_esg_kpi_approval (approval_status),
    KEY idx_esg_kpi_source_input (source_input_value_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='승인된 회사별 공식 KPI fact. 정량/정성 모두 저장';

CREATE TABLE IF NOT EXISTS ESG_CALCULATION_RULE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    calculation_rule_code VARCHAR(100) NOT NULL,
    target_atomic_metric_id VARCHAR(80) NOT NULL,
    target_atomic_name_kr VARCHAR(300) NULL,
    metric_id VARCHAR(50) NULL,
    formula_type VARCHAR(50) NOT NULL,
    execution_scope VARCHAR(30) NOT NULL,
    applicable_company_scope VARCHAR(200) NULL,
    source_atomic_metric_ids TEXT NULL,
    numerator_atomic_metric_ids TEXT NULL,
    denominator_atomic_metric_ids TEXT NULL,
    calculation_formula_label TEXT NULL,
    sql_template LONGTEXT NOT NULL,
    zero_division_policy VARCHAR(50) NULL,
    rounding_policy VARCHAR(50) NULL,
    result_table VARCHAR(100) NULL,
    output_unit VARCHAR(50) NULL,
    execution_order INT NULL,
    active_yn TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_calc_rule_code (calculation_rule_code),
    KEY idx_esg_calc_rule_target (target_atomic_metric_id),
    KEY idx_esg_calc_rule_exec (execution_scope, formula_type, execution_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='계산 규칙 마스터. 계산 실행은 백엔드/배치가 수행';

CREATE TABLE IF NOT EXISTS ESG_CALCULATION_RULE_SOURCE (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    calculation_rule_code VARCHAR(100) NOT NULL,
    target_atomic_metric_id VARCHAR(80) NOT NULL,
    source_atomic_metric_id VARCHAR(80) NOT NULL,
    source_role VARCHAR(30) NULL,
    source_scope VARCHAR(30) NULL,
    source_metric_id VARCHAR(50) NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_esg_calc_source_rule (calculation_rule_code),
    KEY idx_esg_calc_source_target (target_atomic_metric_id),
    KEY idx_esg_calc_source_atomic (source_atomic_metric_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='계산 규칙별 원천 atomic 매핑';

CREATE TABLE IF NOT EXISTS ESG_ROLLUP_BATCH (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    rollup_batch_code VARCHAR(100) NOT NULL,
    parent_company_id BIGINT NOT NULL,
    reporting_year INT NOT NULL,
    report_scope_type VARCHAR(30) NOT NULL DEFAULT 'CONSOLIDATED' COMMENT 'standalone/consolidated',
    included_company_ids_json LONGTEXT NULL COMMENT '이번 batch에 포함한 COMPANY.id 목록 JSON',
    batch_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    requested_by_user_id BIGINT NULL,
    completed_at DATETIME NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_rollup_batch_code (rollup_batch_code),
    KEY idx_esg_rollup_batch_company (parent_company_id, reporting_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='지주사 롤업 실행 배치';

CREATE TABLE IF NOT EXISTS ESG_GROUP_ROLLUP_RESULT (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT '고유ID',
    esg_rollup_batch_id BIGINT NOT NULL,
    rollup_result_code VARCHAR(120) NULL,
    reporting_year INT NOT NULL,
    parent_company_id BIGINT NOT NULL,
    parent_company_scope_type VARCHAR(30) NOT NULL DEFAULT 'CONSOLIDATED',
    included_company_ids TEXT NULL COMMENT '포함 COMPANY.id/code 목록. v2에서는 batch json 우선',
    group_metric_id VARCHAR(50) NOT NULL,
    group_atomic_metric_id VARCHAR(80) NOT NULL,
    group_atomic_name VARCHAR(300) NULL,
    value_numeric DECIMAL(30,6) NULL,
    value_text LONGTEXT NULL,
    unit VARCHAR(50) NULL,
    source_company_values_json LONGTEXT NULL COMMENT '회사별 원천값 trace',
    rollup_method VARCHAR(50) NULL,
    calculation_trace TEXT NULL,
    rollup_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    approved_by_user_id BIGINT NULL,
    approved_at DATETIME NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_esg_rollup_result (esg_rollup_batch_id, group_atomic_metric_id),
    KEY idx_esg_rollup_result_parent (parent_company_id, reporting_year),
    KEY idx_esg_rollup_result_metric (group_metric_id, group_atomic_metric_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='지주사 연결 롤업 결과';

/* ---------------------------------------------------------------------
   B. DMA Agent 9
   --------------------------------------------------------------------- */

CREATE TABLE IF NOT EXISTS ESG_MATERIALITY_RUN (
    id BIGINT NOT NULL AUTO_INCREMENT,
    company_id BIGINT NOT NULL,
    reporting_year INT NOT NULL,
    run_name VARCHAR(200) NOT NULL,
    industry_profile VARCHAR(100) NULL,
    run_status VARCHAR(30) NOT NULL DEFAULT 'draft',
    scoring_rule_version VARCHAR(50) NULL,
    model_version VARCHAR(100) NULL,
    created_by_user_id BIGINT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_materiality_run_company (company_id, reporting_year),
    KEY idx_materiality_run_status (run_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='이중중대성평가 실행 단위';

CREATE TABLE IF NOT EXISTS ESG_DMA_CONTEXT_PROFILE (
    id BIGINT NOT NULL AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    company_id BIGINT NOT NULL,
    reporting_year INT NOT NULL,
    industry_profile VARCHAR(100) NULL,
    business_model VARCHAR(200) NULL,
    context_json LONGTEXT NULL,
    modifier_json LONGTEXT NULL,
    confidence_score DECIMAL(8,4) NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_dma_context_run (esg_materiality_run_id),
    KEY idx_dma_context_company (company_id, reporting_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='G0 기반 회사 context/profile';

CREATE TABLE IF NOT EXISTS ESG_DMA_SUB_ISSUE_DICTIONARY_TERM (
    id BIGINT NOT NULL AUTO_INCREMENT,
    sub_issue_code VARCHAR(120) NOT NULL,
    dictionary_term VARCHAR(300) NOT NULL,
    term_lang VARCHAR(10) NULL COMMENT 'ko/en/mixed',
    term_type VARCHAR(30) NULL COMMENT 'keyword/synonym/standard_label',
    active_yn TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_dma_dict_term (sub_issue_code, dictionary_term),
    KEY idx_dma_dict_sub_issue (sub_issue_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='62개 sub_issue 매칭용 단순 사전';

CREATE TABLE IF NOT EXISTS ESG_DMA_EVIDENCE (
    id BIGINT NOT NULL AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    source_step VARCHAR(30) NOT NULL COMMENT 'benchmark/media_external/survey',
    source_type VARCHAR(30) NOT NULL COMMENT 'own_sr/leader_sr/peer_sr/news/regulation/agency',
    source_title VARCHAR(500) NULL,
    source_url VARCHAR(1000) NULL,
    source_file_id BIGINT NULL,
    source_page_no INT NULL,
    source_published_at DATETIME NULL,
    event_group_key VARCHAR(200) NULL,
    text_span LONGTEXT NULL,
    summary_text TEXT NULL,
    source_credibility_score DECIMAL(8,4) NULL,
    te_sr_file_id BIGINT NULL,
    te_crawling_id BIGINT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_dma_evidence_run (esg_materiality_run_id),
    KEY idx_dma_evidence_source (source_step, source_type),
    KEY idx_dma_evidence_event (event_group_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='DMA 수집/분석 근거 통합 테이블';

CREATE TABLE IF NOT EXISTS ESG_DMA_SIGNAL_DETAIL (
    id BIGINT NOT NULL AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    evidence_id BIGINT NULL,
    raw_issue_label VARCHAR(500) NULL,
    sub_issue_code VARCHAR(120) NOT NULL,
    similarity_score DECIMAL(8,4) NULL,
    similarity_rank INT NULL,
    mapping_weight DECIMAL(10,6) NULL,
    mapping_method VARCHAR(40) NULL,
    source_step VARCHAR(30) NOT NULL,
    source_type VARCHAR(30) NOT NULL,
    iro_type VARCHAR(40) NULL,
    time_horizon VARCHAR(20) NULL,
    impact_scale DECIMAL(8,4) NULL,
    impact_scope DECIMAL(8,4) NULL,
    impact_irremediability DECIMAL(8,4) NULL,
    impact_likelihood DECIMAL(8,4) NULL,
    impact_score DECIMAL(8,4) NULL,
    financial_revenue DECIMAL(8,4) NULL,
    financial_cost DECIMAL(8,4) NULL,
    financial_capex DECIMAL(8,4) NULL,
    financial_asset_liability DECIMAL(8,4) NULL,
    financial_financing DECIMAL(8,4) NULL,
    financial_legal_regulatory DECIMAL(8,4) NULL,
    financial_likelihood DECIMAL(8,4) NULL,
    financial_score DECIMAL(8,4) NULL,
    confidence_score DECIMAL(8,4) NULL,
    judge_status VARCHAR(30) NULL,
    judge_reason TEXT NULL,
    scoring_payload_json LONGTEXT NULL COMMENT 'DMASignal camelCase payload and evidence trace JSON',
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_dma_signal_run_sub (esg_materiality_run_id, sub_issue_code),
    KEY idx_dma_signal_evidence (evidence_id),
    KEY idx_dma_signal_source (source_step, source_type),
    KEY idx_dma_signal_rank (similarity_rank)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Evidence→sub_issue mapping과 점수 신호 상세 ledger';

CREATE TABLE IF NOT EXISTS ESG_DMA_SCORE_SUMMARY (
    id BIGINT NOT NULL AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    sub_issue_code VARCHAR(120) NOT NULL,
    benchmark_impact_score DECIMAL(8,4) NULL,
    benchmark_financial_score DECIMAL(8,4) NULL,
    media_external_impact_score DECIMAL(8,4) NULL,
    media_external_financial_score DECIMAL(8,4) NULL,
    survey_impact_score DECIMAL(8,4) NULL,
    survey_financial_score DECIMAL(8,4) NULL,
    context_impact_modifier DECIMAL(6,4) NOT NULL DEFAULT 0.0000 COMMENT 'Additive company context modifier for final impact score, range -0.5 to +0.5',
    context_financial_modifier DECIMAL(6,4) NOT NULL DEFAULT 0.0000 COMMENT 'Additive company context modifier for final financial score, range -0.5 to +0.5',
    survey_reliability_modifier DECIMAL(8,4) NULL DEFAULT 1.0000,
    final_impact_score DECIMAL(8,4) NULL,
    final_financial_score DECIMAL(8,4) NULL,
    final_score DECIMAL(8,4) NULL,
    rank_no INT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_dma_score_summary (esg_materiality_run_id, sub_issue_code),
    KEY idx_dma_score_rank (esg_materiality_run_id, rank_no),
    KEY idx_dma_score_final (final_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='DMA sub_issue별 점수 집계 summary';

CREATE TABLE IF NOT EXISTS ESG_DMA_SURVEY_QUESTION (
    id BIGINT NOT NULL AUTO_INCREMENT,
    sub_issue_code VARCHAR(120) NULL,
    respondent_group VARCHAR(30) NOT NULL COMMENT 'employee/management/external',
    question_type VARCHAR(30) NOT NULL COMMENT 'common/dynamic',
    mapped_axis VARCHAR(30) NOT NULL COMMENT 'impact/financial/iro/horizon/ranking',
    question_text TEXT NOT NULL,
    scale_min INT NULL DEFAULT 1,
    scale_max INT NULL DEFAULT 5,
    active_yn TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_dma_survey_question_sub (sub_issue_code),
    KEY idx_dma_survey_question_group (respondent_group, question_type, mapped_axis)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='DMA 설문 문항 마스터';

CREATE TABLE IF NOT EXISTS ESG_DMA_SURVEY_RESPONSE (
    id BIGINT NOT NULL AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL,
    respondent_group VARCHAR(30) NOT NULL,
    respondent_user_id BIGINT NULL,
    department_code VARCHAR(50) NULL,
    sub_issue_code VARCHAR(120) NULL,
    answer_numeric DECIMAL(8,4) NULL,
    answer_text LONGTEXT NULL,
    normalized_score DECIMAL(8,4) NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_dma_survey_response_run (esg_materiality_run_id),
    KEY idx_dma_survey_response_question (question_id),
    KEY idx_dma_survey_response_sub (sub_issue_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='DMA 설문 응답값';

CREATE TABLE IF NOT EXISTS ESG_MATERIALITY_SELECTED_SUB_ISSUE (
    id BIGINT NOT NULL AUTO_INCREMENT,
    esg_materiality_run_id BIGINT NOT NULL,
    sub_issue_code VARCHAR(120) NOT NULL,
    selected_rank_no INT NULL,
    selection_type VARCHAR(40) NOT NULL DEFAULT 'user_confirmed',
    selection_reason TEXT NULL,
    selected_by_user_id BIGINT NULL,
    selected_at DATETIME NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_materiality_selected (esg_materiality_run_id, sub_issue_code),
    KEY idx_materiality_selected_rank (esg_materiality_run_id, selected_rank_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='최종 선택된 sub_issue source-of-truth';

/* ---------------------------------------------------------------------
   C. Report / Narrative 4
   --------------------------------------------------------------------- */

CREATE TABLE IF NOT EXISTS ESG_REPORT_RUN (
    id BIGINT NOT NULL AUTO_INCREMENT,
    company_id BIGINT NOT NULL,
    reporting_year INT NOT NULL,
    report_type VARCHAR(30) NOT NULL DEFAULT 'standalone' COMMENT 'standalone/consolidated',
    source_onboarding_cycle_id BIGINT NULL,
    source_rollup_batch_id BIGINT NULL,
    source_materiality_run_id BIGINT NULL,
    report_status VARCHAR(30) NOT NULL DEFAULT 'draft',
    context_snapshot_json LONGTEXT NULL,
    prompt_version VARCHAR(50) NULL,
    model_version VARCHAR(100) NULL,
    created_by_user_id BIGINT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_report_run_company (company_id, reporting_year, report_type),
    KEY idx_report_run_status (report_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='보고서 생성 실행 단위';

CREATE TABLE IF NOT EXISTS ESG_NARRATIVE_TEMPLATE (
    id BIGINT NOT NULL AUTO_INCREMENT,
    template_code VARCHAR(100) NOT NULL,
    section_code VARCHAR(100) NULL,
    owner_metric_id VARCHAR(50) NULL,
    sub_issue_code VARCHAR(120) NULL,
    template_text LONGTEXT NOT NULL,
    token_schema_json LONGTEXT NULL,
    expected_output_structure TEXT NULL,
    active_yn TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_narrative_template_code (template_code),
    KEY idx_narrative_template_metric (owner_metric_id),
    KEY idx_narrative_template_sub (sub_issue_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='보고서 문장/문단 템플릿';

CREATE TABLE IF NOT EXISTS ESG_REPORT_SECTION_DRAFT (
    id BIGINT NOT NULL AUTO_INCREMENT,
    report_run_id BIGINT NOT NULL,
    section_code VARCHAR(100) NULL,
    sub_issue_code VARCHAR(120) NULL,
    owner_metric_id VARCHAR(50) NULL,
    template_id BIGINT NULL,
    generated_text LONGTEXT NOT NULL,
    qa_score DECIMAL(8,4) NULL,
    qa_status VARCHAR(30) NULL,
    approval_status VARCHAR(30) NOT NULL DEFAULT 'draft',
    reviewer_comment TEXT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_report_draft_run (report_run_id),
    KEY idx_report_draft_sub (sub_issue_code),
    KEY idx_report_draft_status (approval_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 생성 보고서 문단 초안';

CREATE TABLE IF NOT EXISTS ESG_REPORT_REFERENCE (
    id BIGINT NOT NULL AUTO_INCREMENT,
    report_section_draft_id BIGINT NOT NULL,
    reference_type VARCHAR(40) NOT NULL COMMENT 'kpi_fact/rollup_result/dma_evidence/onboarding_input',
    reference_id BIGINT NOT NULL,
    atomic_metric_id VARCHAR(80) NULL,
    trace_label_json LONGTEXT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    delete_yn TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_report_reference_draft (report_section_draft_id),
    KEY idx_report_reference_type (reference_type, reference_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='보고서 문단의 fact/evidence 참조 trace';

/* ---------------------------------------------------------------------
   Views
   --------------------------------------------------------------------- */

CREATE OR REPLACE VIEW ESG_V_SUB_ISSUE_METRIC_MAP AS
SELECT DISTINCT
    sam.sub_issue_code,
    amm.metric_id
FROM ESG_SUB_ISSUE_ATOMIC_MAP sam
JOIN ESG_ATOMIC_METRIC_MASTER amm
  ON amm.atomic_metric_id = sam.atomic_metric_id
WHERE sam.delete_yn = 0
  AND amm.delete_yn = 0;

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'SKM ESG v5.2 CLEAN_SCHEMA_v2 created: 28 ESG tables + 1 view' AS status;
